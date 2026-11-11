"""Live RAS Apollo GraphQL & CCIAA Nuoro (`nu.camcom.it`) non-repayable SME grants connector."""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from scrapling import Selector

from sardegna_radar.config import RadarSettings
from sardegna_radar.models import (
    NoticeSource,
    NoticeType,
    SardinianProvince,
    TenderNotice,
    normalize_cig,
    normalize_cup,
)
from sardegna_radar.scrapers.base import build_async_http_client

RAS_GRAPHQL_URL = "https://graphql-prod.regione.sardegna.it/graphql/"
RAS_BANDO_DETAIL_BASE = "https://www.regione.sardegna.it/atti-bandi-archivi/atti-amministrativi/bandi/"
CCIAA_NUORO_BANDI_URL = "https://nu.camcom.it/it/camera/bandi/contributi-attivita-promozionali/"

_RAS_BANDI_QUERY = """
query {
  getContents(
    match: { tipoContenuto: "BANDO", stato: "PUBBLICATO" }
    recordsForPage: 25
    pageNumber: 1
  ) {
    _id
    slug
    titolo
    breve
    oggetto
    descrizione
    dataPubblicazione
    dataScadenza
    cig
    cup
    tipologia
  }
}
"""


def _strip_html(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple, set)):
        text = " ".join(_strip_html(x) for x in raw if x is not None)
    elif isinstance(raw, dict):
        text = " ".join(_strip_html(v) for v in raw.values() if v is not None)
    else:
        text = str(raw)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


class GrantsConnector:
    """Fetches non-repayable regional & chamber of commerce grants for EDILMORITTU S.R.L."""

    def __init__(self, settings: RadarSettings | None = None) -> None:
        self.settings = settings or RadarSettings()

    async def fetch_ras_grants(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            resp = await http_client.post(RAS_GRAPHQL_URL, json={"query": _RAS_BANDI_QUERY})
            resp.raise_for_status()
            items = (resp.json().get("data") or {}).get("getContents") or []
            notices: list[TenderNotice] = []
            for item in items:
                title = _strip_html(item.get("titolo")) or _strip_html(item.get("oggetto"))
                slug = _strip_html(item.get("slug")).lstrip("/")
                if len(title) < 5 or not slug:
                    continue
                desc = " ".join(
                    p
                    for p in (
                        _strip_html(item.get("breve")),
                        _strip_html(item.get("descrizione")),
                        _strip_html(item.get("tipologia")),
                    )
                    if p
                )
                pub_raw = _strip_html(item.get("dataPubblicazione")) or None
                scad_raw = _strip_html(item.get("dataScadenza")) or None
                notices.append(
                    TenderNotice(
                        external_id=_strip_html(item.get("_id")) or slug,
                        source=NoticeSource.RAS,
                        notice_type=NoticeType.REGIONAL_GRANT,
                        title=title,
                        description=desc[:600],
                        contracting_authority="Regione Autonoma della Sardegna",
                        cig=normalize_cig(item.get("cig")),
                        cup=normalize_cup(item.get("cup") or desc),
                        published_date=pub_raw,
                        deadline_date=scad_raw,
                        province=SardinianProvince.REGIONAL,
                        url=f"{RAS_BANDO_DETAIL_BASE}{slug}",
                    )
                )
            return notices
        finally:
            if owns_client:
                await http_client.aclose()

    async def fetch_cciaa_nuoro_grants(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            resp = await http_client.get(CCIAA_NUORO_BANDI_URL)
            resp.raise_for_status()
            return self.parse_cciaa_nuoro_html(resp.text, page_url=str(resp.url))
        finally:
            if owns_client:
                await http_client.aclose()

    def parse_cciaa_nuoro_html(
        self,
        html: str,
        page_url: str = CCIAA_NUORO_BANDI_URL,
    ) -> list[TenderNotice]:
        if not html or not html.strip():
            return []
        sel = Selector(html, url=page_url)
        containers = sel.css("#main, main, article") or [sel]
        notices: list[TenderNotice] = []
        seen_urls: set[str] = set()

        for a in containers[0].css("a[href]"):
            text = str(a.get_all_text(strip=True) or "").strip()
            href = str(a.attrib.get("href") or "").strip()
            if len(text) < 12 or not href:
                continue
            full_url = urljoin(page_url, href)
            if "/it/camera/bandi/" not in full_url:
                continue
            rel_after = full_url.split("/it/camera/bandi/", 1)[1].strip("/")
            if "/" not in rel_after:
                continue  # Skip index & category navigation pages; keep only real grant detail URLs
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            slug = rel_after.rsplit("/", 1)[-1]
            notices.append(
                TenderNotice(
                    external_id=f"cciaa-nu-{slug}",
                    source=NoticeSource.CCIAA_NUORO,
                    notice_type=NoticeType.REGIONAL_GRANT,
                    title=text,
                    description="",
                    contracting_authority="Camera di Commercio di Nuoro",
                    province=SardinianProvince.NU,
                    municipality="Nuoro",
                    url=full_url,
                )
            )
        return notices

    async def fetch_all_grants(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            ras, cciaa = await asyncio.gather(
                self.fetch_ras_grants(client=http_client),
                self.fetch_cciaa_nuoro_grants(client=http_client),
            )
            return [*cciaa, *ras]
        finally:
            if owns_client:
                await http_client.aclose()
