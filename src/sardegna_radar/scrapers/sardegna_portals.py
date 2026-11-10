"""Adaptive Scrapling HTML parser for SardegnaCAT / RAS portals & ScraplingMCPServer helper."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from scrapling import Selector

from sardegna_radar.config import RadarSettings
from sardegna_radar.models import (
    NoticeSource,
    NoticeType,
    TenderNotice,
    normalize_cig,
    normalize_cup,
    parse_italian_currency,
    parse_italian_date,
    resolve_sardinian_province,
)
from sardegna_radar.scrapers.base import build_async_http_client

_AMOUNT_REGEX = re.compile(
    r"(?:importo[^€\d]{0,30}|€|euro)\s*(\d[\d\.,]*)",
    re.IGNORECASE,
)
_DEADLINE_REGEX = re.compile(
    r"(?:scadenza|termine[^:\d]{0,25})[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
    re.IGNORECASE,
)
_AUTHORITY_REGEX = re.compile(
    r"(?:ente|stazione\s+appaltante)\s*:\s*([^\n\r<|]+)",
    re.IGNORECASE,
)


class SardegnaPortalAdaptiveScraper:
    """Resilient HTML portal scraper powered by `scrapling.Selector(adaptive=True)`.

    First attempts canonical CSS selectors with `auto_save=True` so Scrapling persists
    structural element fingerprints. When a regional portal redesigns its layout (DOM drift),
    it automatically falls back to `adaptive=True` similarity relocation and semantic card extraction.
    """

    def __init__(
        self,
        source: NoticeSource = NoticeSource.SARDEGNACAT,
        base_url: str = "https://www.sardegnacat.it",
        storage_dir: Path | None = None,
        settings: RadarSettings | None = None,
    ) -> None:
        self.source = source
        self.base_url = base_url.rstrip("/")
        self.settings = settings or RadarSettings()
        self.storage_dir = storage_dir or self.settings.adaptive_storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_notices(
        self,
        url: str,
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        """Fetch an HTML portal page via async HTTPX and parse notices adaptively."""
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            response = await http_client.get(url)
            response.raise_for_status()
            return self.parse_html(response.text, page_url=url)
        finally:
            if owns_client:
                await http_client.aclose()

    def parse_html(self, html: str, page_url: str | None = None) -> list[TenderNotice]:
        """Parse portal HTML using Scrapling's adaptive Selector engine."""
        if not html or not html.strip():
            return []

        effective_url = page_url or self.base_url
        page = Selector(html, adaptive=True, url=effective_url)

        # Layer 1: Canonical CSS selector with auto_save=True
        cards = page.css("article.bando-item", auto_save=True)
        if not cards:
            # Layer 2: Adaptive relocation when portal changes wrapper tags/classes
            cards = page.css("article.bando-item", adaptive=True)

        if not cards:
            # Layer 3: Structural fallback for table rows or redesigned card containers
            cards = page.css(".tender-card-wrapper, tr.bando-row, article, .bando-card")

        notices: list[TenderNotice] = []
        seen_keys: set[str] = set()
        for idx, card in enumerate(cards, start=1):
            notice = self._extract_card(card, index=idx)
            if notice is not None:
                key = notice.cig or notice.external_id
                if key not in seen_keys:
                    seen_keys.add(key)
                    notices.append(notice)
        return notices

    def _extract_card(self, card: Any, *, index: int) -> TenderNotice | None:
        # Title & URL (canonical auto_save -> adaptive fallback -> generic link)
        link_nodes = card.css("h3.bando-titolo a", auto_save=True)
        if not link_nodes:
            link_nodes = card.css("h3.bando-titolo a", adaptive=True)
        if not link_nodes:
            link_nodes = card.css("a[href]")

        title = ""
        href = ""
        if link_nodes:
            first_link = link_nodes[0]
            title = str(first_link.get_all_text(strip=True) or "").strip()
            href = str(first_link.attrib.get("href") or "").strip()

        full_text = str(card.get_all_text(separator="\n", strip=True) or "").strip()
        if not title and full_text:
            first_line = full_text.splitlines()[0].strip()
            title = first_line

        if len(title) < 5:
            return None

        external_id = (
            str(card.attrib.get("data-id") or card.attrib.get("id") or "").strip()
        )
        cig = normalize_cig(full_text)
        cup = normalize_cup(full_text)
        if not external_id:
            external_id = cig or f"{self.source.value}-{index:04d}"

        # Amount extraction
        amount_nodes = card.css(".importo", auto_save=True) or card.css(".importo", adaptive=True)
        amount_text = str(amount_nodes[0].get_all_text(strip=True)) if amount_nodes else ""
        if not amount_text:
            amount_match = _AMOUNT_REGEX.search(full_text)
            amount_text = amount_match.group(1) if amount_match else ""
        amount_eur = parse_italian_currency(amount_text)

        # Deadline extraction
        deadline_nodes = card.css(".scadenza", auto_save=True) or card.css(".scadenza", adaptive=True)
        deadline_text = str(deadline_nodes[0].get_all_text(strip=True)) if deadline_nodes else ""
        if not deadline_text:
            deadline_match = _DEADLINE_REGEX.search(full_text)
            deadline_text = deadline_match.group(1) if deadline_match else ""
        deadline_date = parse_italian_date(deadline_text)

        # Authority extraction
        auth_nodes = card.css(".ente", auto_save=True) or card.css(".ente", adaptive=True)
        authority = str(auth_nodes[0].get_all_text(strip=True)) if auth_nodes else ""
        if not authority:
            auth_match = _AUTHORITY_REGEX.search(full_text)
            authority = auth_match.group(1).strip() if auth_match else "Ente Appaltante Sardegna"
        authority = re.sub(r"^(?:ente|stazione\s+appaltante)\s*:\s*", "", authority, flags=re.IGNORECASE).strip()

        # Description extraction
        desc_nodes = card.css("p.bando-descrizione, .card-summary")
        description = (
            str(desc_nodes[0].get_all_text(strip=True))
            if desc_nodes
            else " ".join(line.strip() for line in full_text.splitlines()[1:])
        )

        province = resolve_sardinian_province(f"{authority} {title}")
        full_url = urljoin(f"{self.base_url}/", href) if href else self.base_url

        notice_type = (
            NoticeType.REGIONAL_GRANT
            if self.source in (NoticeSource.RAS, NoticeSource.CCIAA_NUORO)
            and any(k in title.lower() for k in ("bando", "voucher", "contribut", "fondo perduto"))
            else NoticeType.PUBLIC_WORKS_TENDER
        )

        return TenderNotice(
            external_id=external_id,
            source=self.source,
            notice_type=notice_type,
            title=title,
            description=description,
            contracting_authority=authority,
            cig=cig,
            cup=cup,
            amount_eur=amount_eur,
            deadline_date=deadline_date,
            province=province,
            url=full_url,
        )


def create_scrapling_mcp_server(
    *,
    http: bool = False,
    host: str = "127.0.0.1",
    port: int = 8000,
    executable_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Helper to configure or launch ScraplingMCPServer (`scrapling mcp`) for interactive DOM inspection."""
    info: dict[str, Any] = {
        "cli_command": "scrapling mcp",
        "http": http,
        "host": host,
        "port": port,
        "executable_path": executable_path,
    }
    if dry_run:
        return info

    from scrapling.core.ai import ScraplingMCPServer

    server = ScraplingMCPServer(executable_path=executable_path)
    server.serve(http=http, host=host, port=port)
    return info
