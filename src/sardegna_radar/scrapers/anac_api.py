"""Reverse-API connector for ANAC BDNCP OCDS JSON feeds."""

from __future__ import annotations

from typing import Any
import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.models import (
    NoticeSource,
    NoticeType,
    SardinianProvince,
    TenderNotice,
    resolve_sardinian_province,
)
from sardegna_radar.scrapers.base import build_async_http_client

DEFAULT_ANAC_OCDS_URL = "https://dati.anticorruzione.it/opendata/ocds/api/v1/releases"


class ANACReverseAPIConnector:
    """Fetches and normalizes structured OCDS JSON releases from ANAC BDNCP."""

    def __init__(
        self,
        endpoint_url: str = DEFAULT_ANAC_OCDS_URL,
        settings: RadarSettings | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.settings = settings or RadarSettings()

    async def fetch_notices(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> list[TenderNotice]:
        """Query the ANAC OCDS JSON endpoint and filter Sardinian procurement releases."""
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            response = await http_client.get(self.endpoint_url)
            response.raise_for_status()
            payload = response.json()
            return self.parse_ocds_payload(payload)
        finally:
            if owns_client:
                await http_client.aclose()

    def parse_ocds_payload(self, payload: dict[str, Any] | list[dict[str, Any]]) -> list[TenderNotice]:
        """Parse an OCDS release package or list of releases into normalized Sardinian TenderNotices."""
        releases: list[dict[str, Any]]
        if isinstance(payload, list):
            releases = payload
        else:
            releases = list(payload.get("releases") or payload.get("data") or [])

        notices: list[TenderNotice] = []
        for rel in releases:
            notice = self._parse_single_release(rel)
            if notice is not None:
                notices.append(notice)
        return notices

    def _parse_single_release(self, rel: dict[str, Any]) -> TenderNotice | None:
        tender = rel.get("tender") or {}
        buyer = rel.get("buyer") or {}
        buyer_name = str(buyer.get("name") or "Stazione Appaltante ANAC").strip()
        title = str(tender.get("title") or "").strip()
        if not title:
            return None

        description = str(tender.get("description") or "").strip()
        cig = str(tender.get("id") or rel.get("cig") or "").strip() or None
        cup = str(tender.get("cup") or rel.get("cup") or "").strip() or None

        cpv_codes: list[str] = []
        municipality: str | None = None
        nuts_regions: list[str] = []
        raw_province: str | None = None

        for item in tender.get("items") or []:
            classification = item.get("classification") or {}
            cpv_id = classification.get("id")
            if cpv_id:
                cpv_codes.append(str(cpv_id))
            for addr in item.get("deliveryAddresses") or []:
                if addr.get("locality") and not municipality:
                    municipality = str(addr["locality"])
                if addr.get("region"):
                    nuts_regions.append(str(addr["region"]).upper())
                if addr.get("province") and not raw_province:
                    raw_province = str(addr["province"])

        is_sardinian_nuts = any(r.startswith("ITG2") for r in nuts_regions)
        resolved_province = resolve_sardinian_province(
            raw_province or municipality or buyer_name or title
        )

        # Exclude releases explicitly belonging to non-Sardinian NUTS regions
        if nuts_regions and not is_sardinian_nuts and resolved_province == SardinianProvince.REGIONAL:
            return None
        if not is_sardinian_nuts and resolved_province == SardinianProvince.REGIONAL:
            lowered_blob = f"{buyer_name} {title} {description}".lower()
            if "sardegna" not in lowered_blob and "abbanoa" not in lowered_blob:
                return None

        value_obj = tender.get("value") or {}
        amount_eur = value_obj.get("amount")

        tender_period = tender.get("tenderPeriod") or {}
        deadline_raw = tender_period.get("endDate")
        published_raw = rel.get("date")

        winner_company: str | None = None
        for award in rel.get("awards") or []:
            for supplier in award.get("suppliers") or []:
                if supplier.get("name"):
                    winner_company = str(supplier["name"]).strip()
                    break
            if winner_company:
                break

        notice_type = (
            NoticeType.CONTRACT_AWARD if winner_company else NoticeType.PUBLIC_WORKS_TENDER
        )
        external_id = str(rel.get("id") or rel.get("ocid") or cig or title[:32])
        url = str(
            rel.get("url")
            or f"https://dati.anticorruzione.it/superset/dashboard/dettaglio_cig/?cig={cig or external_id}"
        )

        return TenderNotice(
            external_id=external_id,
            source=NoticeSource.ANAC_OCDS,
            notice_type=notice_type,
            title=title,
            description=description,
            contracting_authority=buyer_name,
            cig=cig,
            cup=cup,
            cpv_codes=cpv_codes,
            amount_eur=amount_eur,
            published_date=published_raw,
            deadline_date=deadline_raw,
            municipality=municipality,
            province=resolved_province,
            winner_company=winner_company,
            url=url,
        )
