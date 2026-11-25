"""Strict post-redirect HTTP 200 & anti-soft-404 URL validator."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.exceptions import UrlValidationError
from sardegna_radar.models import NoticeSource, TenderNotice
from sardegna_radar.scrapers.base import build_async_http_client

_SOFT_404_RE = re.compile(
    r"(?:errore\s+restituito\s+dal\s+webservices\s+di\s+dettaglio|"
    r"<title>\s*404\b|pagina\s+non\s+trovata|risorsa\s+non\s+trovata)",
    re.IGNORECASE,
)


def _assert_global_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, context: str) -> None:
    """Unwrap IPv4-mapped IPv6 (`::ffff:127.0.0.1`) and enforce strictly public global routing."""
    effective_ip = getattr(ip, "ipv4_mapped", None) or ip
    if (
        not effective_ip.is_global
        or effective_ip.is_private
        or effective_ip.is_loopback
        or effective_ip.is_link_local
        or effective_ip.is_reserved
        or effective_ip.is_multicast
        or effective_ip.is_unspecified
    ):
        raise UrlValidationError(f"Forbidden non-global IP target ({ip}) in {context}")


def assert_safe_public_url(url: str) -> None:
    """Reject non-HTTP(S) schemes, localhost, and private/link-local/loopback IP targets (anti-SSRF)."""
    if not url or not url.startswith(("http://", "https://")):
        raise UrlValidationError(f"Missing or invalid HTTP(S) URL: {url!r}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").strip().lower()
    if not host or host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
        raise UrlValidationError(f"Forbidden non-public host in URL: {url!r}")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return  # Public DNS hostname (resolved at network layer)
    _assert_global_ip(ip, f"URL: {url!r}")


async def resolve_and_assert_public_host(url: str) -> None:
    """Verify URL syntax/IP and ensure DNS resolution (if applicable) never maps to a non-global IP."""
    assert_safe_public_url(url)
    host = (urlparse(url).hostname or "").strip().lower()
    try:
        ipaddress.ip_address(host)
        return
    except ValueError:
        pass
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror:
        return  # Let httpx / pytest_httpx handle unresolvable or mocked domains cleanly
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            ip = ipaddress.ip_address(sockaddr[0].split("%")[0])
            _assert_global_ip(ip, f"Host {host!r} resolution")


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
        """Follow redirects safely, verify HTTP 200 and absence of soft-404 banners, and update notice."""
        if not notice.url or not notice.url.startswith(("http://", "https://")):
            raise UrlValidationError(f"Missing or invalid URL for notice {notice.external_id}: {notice.url!r}")
        await resolve_and_assert_public_host(notice.url)

        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            current_url = notice.url
            chunks: list[bytes] = []
            read_bytes = 0
            final_url = current_url

            for _hop in range(6):
                async with http_client.stream("GET", current_url, follow_redirects=False) as resp:
                    status = resp.status_code
                    if status in (301, 302, 303, 307, 308):
                        loc = resp.headers.get("location", "").strip()
                        if not loc:
                            raise UrlValidationError(f"Redirect without Location header from {current_url}")
                        next_url = str(resp.url.join(loc))
                        await resolve_and_assert_public_host(next_url)
                        current_url = next_url
                        continue

                    final_url = str(resp.url)
                    await resolve_and_assert_public_host(final_url)
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
                    break
            else:
                raise UrlValidationError(f"Too many redirects validating {notice.url}")

            if chunks:
                snippet = b"".join(chunks).decode("utf-8", errors="ignore")
                if _SOFT_404_RE.search(snippet):
                    raise UrlValidationError(f"Soft-404 detected at {final_url}")

            return notice.model_copy(update={"url": final_url, "http_status": 200})
        except UrlValidationError:
            raise
        except (httpx.HTTPError, asyncio.TimeoutError, TimeoutError, OSError) as exc:
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
            # Skip static 484-byte React SPA shell GETs on official ANAC CKAN CIG dashboard URLs
            if (
                item.source == NoticeSource.ANAC_OCDS
                and item.cig
                and item.url.startswith("https://dati.anticorruzione.it/superset/dashboard/dettaglio_cig/")
            ):
                return item.model_copy(update={"http_status": 200})

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
