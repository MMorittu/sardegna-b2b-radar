"""Strict post-redirect HTTP 200 & anti-soft-404 URL validator."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import re

import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.exceptions import UrlValidationError
from sardegna_radar.models import TenderNotice
from sardegna_radar.scrapers.base import build_async_http_client

_SOFT_404_RE = re.compile(
    r"(?:errore\s+restituito\s+dal\s+webservices\s+di\s+dettaglio|"
    r"<title>\s*404\b|pagina\s+non\s+trovata|risorsa\s+non\s+trovata)",
    re.IGNORECASE,
)


class HttpUrlValidator:
    """Verifies that every persisted notice URL resolves to a live HTTP 200 non-error page."""

    def __init__(
        self,
        settings: RadarSettings | None = None,
        concurrency: int = 8,
    ) -> None:
        self.settings = settings or RadarSettings()
        self.concurrency = max(1, concurrency)

    async def validate_notice(
        self,
        notice: TenderNotice,
        client: httpx.AsyncClient | None = None,
    ) -> TenderNotice:
        """Follow redirects, verify HTTP 200 and absence of soft-404 banners, and update notice."""
        if not notice.url or not notice.url.startswith(("http://", "https://")):
            raise UrlValidationError(f"Missing or invalid URL for notice {notice.external_id}: {notice.url!r}")

        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            chunks: list[bytes] = []
            read_bytes = 0
            async with http_client.stream("GET", notice.url) as resp:
                status = resp.status_code
                final_url = str(resp.url)
                if status != 200:
                    raise UrlValidationError(
                        f"URL {notice.url} resolved to HTTP {status} (final: {final_url})"
                    )
                content_type = resp.headers.get("content-type", "").lower()
                if "html" in content_type or "text" in content_type or not content_type:
                    async for chunk in resp.aiter_bytes(chunk_size=4096):
                        chunks.append(chunk)
                        read_bytes += len(chunk)
                        if read_bytes >= 16384:
                            break

            if chunks:
                snippet = b"".join(chunks).decode("utf-8", errors="ignore")
                if _SOFT_404_RE.search(snippet):
                    raise UrlValidationError(f"Soft-404 detected at {final_url}")

            return notice.model_copy(update={"url": final_url, "http_status": 200})
        except UrlValidationError:
            raise
        except httpx.HTTPError as exc:
            raise UrlValidationError(f"Network error validating {notice.url}: {exc}") from exc
        finally:
            if owns_client:
                await http_client.aclose()

    async def filter_valid_notices(
        self,
        notices: Sequence[TenderNotice],
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        """Validate notices concurrently and return only verified HTTP 200 notices."""
        if not notices:
            return []

        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        sem = asyncio.Semaphore(self.concurrency)
        url_cache: dict[str, tuple[bool, str]] = {}

        async def _check(item: TenderNotice) -> TenderNotice | None:
            if item.url in url_cache:
                ok, final_u = url_cache[item.url]
                return item.model_copy(update={"url": final_u, "http_status": 200}) if ok else None
            async with sem:
                try:
                    checked = await self.validate_notice(item, client=http_client)
                    url_cache[item.url] = (True, checked.url)
                    return checked
                except UrlValidationError:
                    url_cache[item.url] = (False, item.url)
                    return None

        try:
            results = await asyncio.gather(*(_check(n) for n in notices))
            return [r for r in results if r is not None]
        finally:
            if owns_client:
                await http_client.aclose()
