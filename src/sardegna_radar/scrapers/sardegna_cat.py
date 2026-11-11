"""Live SardegnaCAT (AFSoluzioni PortaleGare) XML Bandi/Esiti & ZIP attachment connector."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import re
import xml.etree.ElementTree as ET

import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.models import (
    NoticeSource,
    NoticeType,
    TenderNotice,
    normalize_cig,
    normalize_cup,
    resolve_sardinian_province,
)
from sardegna_radar.scrapers.base import build_async_http_client

AFS_NS = {"afs": "http://www.aflink.it/XMLBANDI"}

SCAT_OPEN_WORKS_RSS = (
    "https://sardegnacat.regione.sardegna.it/portale/rss_bandi.asp"
    "?FilterHide=bScaduto%3D0+and+Contratto%3D%27Lavori%27&numRowForPag=40&nPag=1"
)
SCAT_OPEN_SUPPLIES_RSS = (
    "https://sardegnacat.regione.sardegna.it/portale/rss_bandi.asp"
    "?FilterHide=bScaduto%3D0+and+bEsito%3D0+and+Contratto%3D%27Forniture%27&numRowForPag=25&nPag=1"
)
SCAT_DOWNLOAD_ATTACH_TPL = (
    "https://sardegnacat.regione.sardegna.it/Application/CTL_LIBRARY/DOCUMENT/"
    "DownloadAttach.asp?TMP_DIFF={today}&DOCUMENT={doc_type}&OPERATION=DOWNLOAD&IDDOC={id_msg}"
)


def rewrite_sardegnacat_detail_url(raw_url: str) -> str:
    """Fix AFSoluzioni RSS bug where `/portale/index.php/bandi` 404s instead of `/portalegare/index.php/bandi`."""
    return raw_url.strip().replace("/portale/index.php/", "/portalegare/index.php/")


class SardegnaCATConnector:
    """Fetches open public works, construction supplies, and contract awards from SardegnaCAT."""

    def __init__(self, settings: RadarSettings | None = None) -> None:
        self.settings = settings or RadarSettings()

    async def fetch_notices(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            r_works, r_supplies = await asyncio.gather(
                http_client.get(SCAT_OPEN_WORKS_RSS),
                http_client.get(SCAT_OPEN_SUPPLIES_RSS),
            )
            r_works.raise_for_status()
            r_supplies.raise_for_status()

            merged: list[TenderNotice] = []
            seen: set[str] = set()
            for xml_body in (r_works.text, r_supplies.text):
                for notice in self.parse_rss_xml(xml_body):
                    key = notice.cig or notice.external_id
                    if key not in seen:
                        seen.add(key)
                        merged.append(notice)
            return merged
        finally:
            if owns_client:
                await http_client.aclose()

    def parse_rss_xml(self, xml_text: str) -> list[TenderNotice]:
        """Parse SardegnaCAT `XMLBANDI` RSS feed into normalized `TenderNotice` records."""
        if not xml_text or "<rss" not in xml_text:
            return []

        root = ET.fromstring(xml_text.strip())
        today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
        notices: list[TenderNotice] = []

        for item in root.findall("./channel/item"):
            contratto = (item.findtext("afs:Contratto", default="", namespaces=AFS_NS) or "").strip()
            if contratto.lower() not in ("lavori", "forniture", ""):
                continue

            oggetto = (item.findtext("afs:Oggetto", default="", namespaces=AFS_NS) or "").strip()
            titolo_doc = (item.findtext("afs:TitoloDocumento", default="", namespaces=AFS_NS) or "").strip()
            title = oggetto or titolo_doc
            if len(title) < 5:
                continue

            id_msg = (item.findtext("afs:IdMsg", default="", namespaces=AFS_NS) or "").strip()
            raw_link = (item.findtext("link", default="") or "").strip()
            fixed_url = rewrite_sardegnacat_detail_url(raw_link) if raw_link else ""

            tipo = (item.findtext("afs:Tipo", default="", namespaces=AFS_NS) or "").strip().lower()
            b_esito = (item.findtext("afs:bEsito", default="0", namespaces=AFS_NS) or "0").strip()
            if tipo == "esito" or b_esito == "1":
                notice_type = NoticeType.CONTRACT_AWARD
            elif contratto.lower() == "forniture":
                notice_type = NoticeType.SUPPLY_TENDER
            else:
                notice_type = NoticeType.PUBLIC_WORKS_TENDER

            authority = (
                item.findtext("afs:EnteProponente", default="", namespaces=AFS_NS)
                or item.findtext("afs:DenominazioneEnte", default="", namespaces=AFS_NS)
                or "Stazione Appaltante SardegnaCAT"
            ).strip()

            raw_cig = (item.findtext("afs:CIG", default="", namespaces=AFS_NS) or "").strip()
            cig = normalize_cig(raw_cig) or normalize_cig(title)
            cup = normalize_cup(title)
            base_asta = item.findtext("afs:a_base_asta", default="", namespaces=AFS_NS)
            pub_date = (
                item.findtext("afs:DtPubblicazioneTecnical", default="", namespaces=AFS_NS)
                or item.findtext("pubDate", default="")
            )
            deadline = item.findtext("afs:DtScadenzaBandoTecnical", default="", namespaces=AFS_NS)

            raw_cpv = (item.findtext("afs:CPV", default="", namespaces=AFS_NS) or "").strip()
            cpv_match = re.match(r"^(\d{8}(?:-\d)?)", raw_cpv)
            cpv_codes = [cpv_match.group(1)] if cpv_match else []

            doc_orig = (item.findtext("afs:TipoDocOriginal", default="BANDO_GARA", namespaces=AFS_NS) or "BANDO_GARA").strip()
            attach_url = (
                SCAT_DOWNLOAD_ATTACH_TPL.format(today=today_iso, doc_type=doc_orig, id_msg=id_msg)
                if id_msg
                else None
            )

            province = resolve_sardinian_province(f"{authority} {title}")
            notices.append(
                TenderNotice(
                    external_id=id_msg or cig or title[:32],
                    source=NoticeSource.SARDEGNACAT,
                    notice_type=notice_type,
                    title=title,
                    description=titolo_doc if titolo_doc != title else raw_cpv,
                    contracting_authority=authority,
                    cig=cig,
                    cup=cup,
                    cpv_codes=cpv_codes,
                    amount_eur=base_asta,
                    published_date=pub_date,
                    deadline_date=deadline,
                    province=province,
                    url=fixed_url,
                    attachment_url=attach_url,
                )
            )
        return notices
