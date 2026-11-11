"""Adaptive Scrapling HTML parser for local Sardinian CUC / PA Digitale / Municipium portals."""

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

CUC_COMUNITA_MONTANA_NUORESE_URL = (
    "https://comunitamontananuorese.it/it/amministrazione/documenti/albo/atti/bando-di-gara"
)

_AMOUNT_REGEX = re.compile(r"(?:importo[^€\d]{0,30}|€|euro)\s*(\d[\d\.,\u00b4']*)", re.IGNORECASE)
_DEADLINE_REGEX = re.compile(
    r"(?:scadenza|termine[^:\d]{0,25})[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
    re.IGNORECASE,
)
_AUTHORITY_REGEX = re.compile(
    r"(?:ente|stazione\s+appaltante)\s*:\s*([^\n\r<|]+)",
    re.IGNORECASE,
)


class SardegnaPortalAdaptiveScraper:
    """Resilient HTML portal scraper for Sardinian CUC portals (e.g. Comunità Montana Nuorese)."""

    def __init__(
        self,
        source: NoticeSource = NoticeSource.CUC_LOCALE,
        base_url: str = "https://comunitamontananuorese.it",
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
        url: str = CUC_COMUNITA_MONTANA_NUORESE_URL,
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        """Fetch an HTML portal page via async HTTPX and parse notices adaptively."""
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            response = await http_client.get(url)
            response.raise_for_status()
            return self.parse_html(response.text, page_url=str(response.url))
        finally:
            if owns_client:
                await http_client.aclose()

    def parse_html(self, html: str, page_url: str | None = None) -> list[TenderNotice]:
        """Parse PA Digitale / Municipium or generic portal HTML using Scrapling."""
        if not html or not html.strip():
            return []

        effective_url = page_url or self.base_url
        page = Selector(html, adaptive=True, url=effective_url)

        # PA Digitale / Municipium document links (`/it/documenti/...`)
        doc_links = [
            a
            for a in page.css("a[href]")
            if "/it/documenti/" in str(a.attrib.get("href") or "")
        ]
        if doc_links:
            return self._parse_municipium_links(doc_links, effective_url)

        cards = (
            page.css("article.bando-item", auto_save=True)
            or page.css("article.bando-item", adaptive=True)
            or page.css(".tender-card-wrapper, tr.bando-row, article, .bando-card, .card")
        )

        notices: list[TenderNotice] = []
        seen_keys: set[str] = set()
        for idx, card in enumerate(cards, start=1):
            notice = self._extract_card(card, index=idx, effective_url=effective_url)
            if notice is not None:
                key = notice.cig or notice.external_id
                if key not in seen_keys:
                    seen_keys.add(key)
                    notices.append(notice)
        return notices

    def _parse_municipium_links(self, links: list[Any], effective_url: str) -> list[TenderNotice]:
        notices: list[TenderNotice] = []
        seen: set[str] = set()
        default_auth = (
            "Comunità Montana Nuorese Gennargentu Supramonte Barbagia"
            if "comunitamontananuorese" in effective_url
            else "CUC Locale Sardegna"
        )
        for a in links:
            title = str(a.get_all_text(strip=True) or "").strip()
            href = str(a.attrib.get("href") or "").strip()
            if len(title) < 8 or not href:
                continue
            full_url = urljoin(effective_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            slug = full_url.rstrip("/").rsplit("/", 1)[-1]
            cig = normalize_cig(title) or normalize_cig(slug)
            cup = normalize_cup(title)
            amt_match = _AMOUNT_REGEX.search(title)
            amt = parse_italian_currency(amt_match.group(1)) if amt_match else None
            is_award = any(k in title.lower() for k in ("aggiudicazion", "esito", "affidamento"))
            notices.append(
                TenderNotice(
                    external_id=cig or slug,
                    source=self.source,
                    notice_type=NoticeType.CONTRACT_AWARD if is_award else NoticeType.PUBLIC_WORKS_TENDER,
                    title=title,
                    contracting_authority=default_auth,
                    cig=cig,
                    cup=cup,
                    amount_eur=amt,
                    province=resolve_sardinian_province(f"{default_auth} {title}"),
                    url=full_url,
                )
            )
        return notices

    def _extract_card(self, card: Any, *, index: int, effective_url: str) -> TenderNotice | None:
        link_nodes = (
            card.css("h3.bando-titolo a", auto_save=True)
            or card.css("h3.bando-titolo a", adaptive=True)
            or card.css("a[href]")
        )
        title = ""
        href = ""
        if link_nodes:
            first_link = link_nodes[0]
            title = str(first_link.get_all_text(strip=True) or "").strip()
            href = str(first_link.attrib.get("href") or "").strip()

        full_text = str(card.get_all_text(separator="\n", strip=True) or "").strip()
        if not title and full_text:
            title = full_text.splitlines()[0].strip()
        if len(title) < 5:
            return None

        external_id = str(card.attrib.get("data-id") or card.attrib.get("id") or "").strip()
        cig = normalize_cig(full_text)
        cup = normalize_cup(full_text)
        if not external_id:
            external_id = cig or f"{self.source.value}-{index:04d}"

        amount_nodes = card.css(".importo", auto_save=True) or card.css(".importo", adaptive=True)
        amount_text = str(amount_nodes[0].get_all_text(strip=True)) if amount_nodes else ""
        if not amount_text:
            amount_match = _AMOUNT_REGEX.search(full_text)
            amount_text = amount_match.group(1) if amount_match else ""

        deadline_nodes = card.css(".scadenza", auto_save=True) or card.css(".scadenza", adaptive=True)
        deadline_text = str(deadline_nodes[0].get_all_text(strip=True)) if deadline_nodes else ""
        if not deadline_text:
            deadline_match = _DEADLINE_REGEX.search(full_text)
            deadline_text = deadline_match.group(1) if deadline_match else ""

        auth_nodes = card.css(".ente", auto_save=True) or card.css(".ente", adaptive=True)
        authority = str(auth_nodes[0].get_all_text(strip=True)) if auth_nodes else ""
        if not authority:
            auth_match = _AUTHORITY_REGEX.search(full_text)
            authority = auth_match.group(1).strip() if auth_match else "Ente Appaltante Sardegna"
        authority = re.sub(r"^(?:ente|stazione\s+appaltante)\s*:\s*", "", authority, flags=re.IGNORECASE).strip()

        desc_nodes = card.css("p.bando-descrizione, .card-summary")
        description = (
            str(desc_nodes[0].get_all_text(strip=True))
            if desc_nodes
            else " ".join(line.strip() for line in full_text.splitlines()[1:])
        )

        full_url = urljoin(effective_url, href) if href else effective_url
        notice_type = (
            NoticeType.REGIONAL_GRANT
            if self.source in (NoticeSource.RAS, NoticeSource.CCIAA_NUORO)
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
            amount_eur=parse_italian_currency(amount_text),
            deadline_date=parse_italian_date(deadline_text),
            province=resolve_sardinian_province(f"{authority} {title}"),
            url=full_url,
        )
