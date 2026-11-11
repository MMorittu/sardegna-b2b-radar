"""Live ANAC BDNCP `appalto v2.3`, CKAN OpenData JSONL streamer, and OCDS connector."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
import io
import json
from pathlib import Path
import re
from typing import Any
import zipfile

import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.exceptions import RadarNetworkError
from sardegna_radar.models import (
    NoticeSource,
    NoticeType,
    SardinianProvince,
    TenderNotice,
    normalize_cig,
    normalize_cup,
    resolve_sardinian_province,
)
from sardegna_radar.scrapers.base import build_async_http_client

ANAC_CKAN_PACKAGE_SHOW_URL = "https://dati.anticorruzione.it/opendata/api/3/action/package_show"
ANAC_CIG_DASHBOARD_TPL = "https://dati.anticorruzione.it/superset/dashboard/dettaglio_cig/?cig={cig}"

_SARDINIAN_PROVINCE_NAMES = {
    "NUORO",
    "SASSARI",
    "ORISTANO",
    "CAGLIARI",
    "SUD SARDEGNA",
    "CARBONIA-IGLESIAS",
    "MEDIO CAMPIDANO",
    "OGLIASTRA",
    "OLBIA-TEMPIO",
    "NU",
    "SS",
    "OR",
    "CA",
    "SU",
}


_COMUNE_DI_RE = re.compile(r"\bCOMUNE\s+DI\s+([A-ZÀ-Ú'’\-\s]{3,35})(?:\b|$)", re.IGNORECASE)


def _extract_filtered_jsonl_rows(
    zip_bytes: bytes,
    row_filter: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Stream-decompress JSONL inside a ZIP keeping ONLY rows matching `row_filter` (<80MB RAM)."""
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".json"):
                continue
            with zf.open(name) as stream:
                for raw_line in stream:
                    line = raw_line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if row_filter(obj):
                        rows.append(obj)
    return rows


def _infer_municipality(delegante: str, title: str) -> str | None:
    for text in (delegante, title):
        m = _COMUNE_DI_RE.search(text)
        if m:
            return m.group(1).strip(" -.,;()")[:40]
    return None


def _is_sardinian_row(row: dict[str, Any]) -> bool:
    sez = str(row.get("sezione_regionale") or "").upper()
    if "SARDEGNA" in sez:
        return True
    prov = str(row.get("provincia") or row.get("SIGLA_PROVINCIA") or "").strip().upper()
    if prov in _SARDINIAN_PROVINCE_NAMES:
        return True
    istat = str(row.get("luogo_istat") or "")
    return istat.startswith(("090", "091", "092", "095", "111", "114", "02009"))


class ANACReverseAPIConnector:
    """Parses ANAC BDNCP `appalto v2.3` JSON, live CKAN 2026 JSONL streams, and OCDS packages."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        settings: RadarSettings | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.settings = settings or RadarSettings()

    def parse_appalto_v23_file(self, path: Path | str) -> TenderNotice | None:
        """Load and normalize an ANAC `appalto v2.3` JSON file (e.g. `CIG_BCB16FC2F3.json`)."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.parse_appalto_v23(payload)

    def parse_appalto_v23(self, payload: dict[str, Any]) -> TenderNotice | None:
        """Normalize an ANAC `appalto v2.3` JSON object into a rich `TenderNotice`."""
        bando = payload.get("bando") or {}
        cig = normalize_cig(str(bando.get("CIG") or ""))
        title = str(bando.get("OGGETTO_GARA") or bando.get("OGGETTO_LOTTO") or "").strip()
        if not title:
            return None

        cup_list = bando.get("CUP") or []
        cup: str | None = None
        if isinstance(cup_list, list) and cup_list:
            first_cup = cup_list[0]
            cup = normalize_cup(str(first_cup.get("CUP") if isinstance(first_cup, dict) else first_cup))
        if not cup:
            cup = normalize_cup(title)

        cpv_codes = [
            str(item.get("COD_CPV")).strip()
            for item in (bando.get("CPV") or [])
            if isinstance(item, dict) and item.get("COD_CPV")
        ]

        sa = payload.get("stazioneAppaltante") or {}
        delegante = str(
            bando.get("DENOMINAZIONE_SA_DELEGANTE")
            or sa.get("DENOMINAZIONE_AMMINISTRAZIONE_APPALTANTE")
            or "Stazione Appaltante Sardegna"
        ).strip()
        delegata = str(bando.get("DENOMINAZIONE_SA_DELEGATA") or "").strip() or None
        municipality = str(sa.get("CITTA") or "").strip() or None
        province = resolve_sardinian_province(
            str(bando.get("SIGLA_PROVINCIA") or municipality or delegante)
        )

        # RUP extraction
        rup_name: str | None = None
        for inc in payload.get("incaricati") or []:
            if str(inc.get("COD_RUOLO") or "").upper() == "RUP":
                nome = str(inc.get("NOME") or "").strip()
                cognome = str(inc.get("COGNOME") or "").strip()
                rup_name = f"{nome} {cognome}".strip() or None
                break

        # Winner extraction (`FLAG_AGGIUDICATARIO == -1` or `1`)
        winner_company: str | None = None
        winner_tax_id: str | None = None
        for part in payload.get("partecipanti") or []:
            flag = part.get("FLAG_AGGIUDICATARIO")
            if flag in (-1, 1, True, "-1", "1"):
                winner_company = str(part.get("DENOMINAZIONE") or "").strip() or None
                winner_tax_id = str(part.get("CODICE_FISCALE") or "").strip() or None
                break

        agg_list = payload.get("aggiudicazione") or []
        agg = agg_list[0] if agg_list else {}
        award_amount = agg.get("IMPORTO_AGGIUDICAZIONE")
        discount_pct = agg.get("RIBASSO_AGGIUDICAZIONE")
        award_date = agg.get("DATA_AGGIUDICAZIONE_DEFINITIVA") or bando.get("DATA_COMUNICAZIONE_ESITO")

        esito = str(bando.get("ESITO") or agg.get("ESITO") or "").upper()
        is_award = bool(esito == "AGGIUDICATA" or winner_company or award_amount)
        objeto_princ = str(bando.get("OGGETTO_PRINCIPALE_CONTRATTO") or "LAVORI").upper()
        if is_award:
            notice_type = NoticeType.CONTRACT_AWARD
        elif objeto_princ == "FORNITURE":
            notice_type = NoticeType.SUPPLY_TENDER
        else:
            notice_type = NoticeType.PUBLIC_WORKS_TENDER

        avvio = payload.get("avvioContratto")
        subappalti = payload.get("subappalti")
        contract_started = bool(avvio) if isinstance(avvio, list) else None
        has_subcontracts = bool(subappalti) if isinstance(subappalti, list) else None

        pub = payload.get("pubblicazioni") or {}
        cat_desc = ", ".join(
            str(c.get("DESCRIZIONE") or "").strip()
            for c in (payload.get("categorieOpera") or [])
            if c.get("DESCRIZIONE")
        )
        canonical_url = ANAC_CIG_DASHBOARD_TPL.format(cig=cig or bando.get("NUMERO_GARA") or "N/A")

        return TenderNotice(
            external_id=cig or str(bando.get("NUMERO_GARA") or title[:32]),
            source=NoticeSource.ANAC_OCDS,
            notice_type=notice_type,
            title=title,
            description=cat_desc,
            contracting_authority=delegante,
            delegated_authority=delegata,
            cig=cig,
            cup=cup,
            cpv_codes=cpv_codes,
            amount_eur=bando.get("IMPORTO_COMPLESSIVO_GARA") or bando.get("IMPORTO_LOTTO"),
            award_amount_eur=award_amount,
            discount_pct=discount_pct,
            published_date=pub.get("DATA_PUBBLICAZIONE") or pub.get("DATA_CREAZIONE"),
            deadline_date=bando.get("DATA_SCADENZA_OFFERTA"),
            award_date=award_date,
            municipality=municipality,
            province=province,
            winner_company=winner_company,
            winner_tax_id=winner_tax_id,
            rup_name=rup_name,
            contract_started=contract_started,
            has_subcontracts=has_subcontracts,
            url=canonical_url,
        )

    def join_ckan_records(
        self,
        cig_rows: Iterable[dict[str, Any]],
        *,
        awards_by_cig: dict[str, dict[str, Any]] | None = None,
        winners_by_cig: dict[str, dict[str, Any]] | None = None,
        started_cigs: set[str] | None = None,
        subcontract_cigs: set[str] | None = None,
    ) -> list[TenderNotice]:
        """Join ANAC monthly OpenData JSONL tables for Sardinian `LAVORI` & construction supplies."""
        awards = awards_by_cig or {}
        winners = winners_by_cig or {}
        started = started_cigs or set()
        subs = subcontract_cigs or set()
        notices: list[TenderNotice] = []

        for row in cig_rows:
            if not _is_sardinian_row(row):
                continue
            contract_kind = str(row.get("oggetto_principale_contratto") or "").upper()
            if contract_kind not in ("LAVORI", "FORNITURE"):
                continue

            cig = normalize_cig(str(row.get("cig") or ""))
            title = str(row.get("oggetto_gara") or row.get("oggetto_lotto") or "").strip()
            if not cig or len(title) < 5:
                continue

            agg = awards.get(cig, {})
            win = winners.get(cig, {})
            esito = str(row.get("ESITO") or agg.get("esito") or "").upper()
            winner_name = str(win.get("denominazione") or "").strip() or None
            winner_cf = str(win.get("codice_fiscale") or "").strip() or None
            award_amt = agg.get("importo_aggiudicazione")

            is_award = bool(esito == "AGGIUDICATA" or winner_name or award_amt)
            if is_award:
                n_type = NoticeType.CONTRACT_AWARD
            elif contract_kind == "FORNITURE":
                n_type = NoticeType.SUPPLY_TENDER
            else:
                n_type = NoticeType.PUBLIC_WORKS_TENDER

            delegante = str(
                row.get("DENOMINAZIONE_SA_DELEGANTE")
                or row.get("denominazione_amministrazione_appaltante")
                or "Stazione Appaltante Sardegna"
            ).strip()
            delegata = str(row.get("DENOMINAZIONE_SA_DELEGATA") or "").strip() or None
            cpv = str(row.get("cod_cpv") or "").strip()
            desc_cpv = str(row.get("descrizione_cpv") or "").strip()
            municipality = _infer_municipality(delegante, title)
            prov = resolve_sardinian_province(
                str(row.get("provincia") or municipality or delegante or title)
            )

            notices.append(
                TenderNotice(
                    external_id=cig,
                    source=NoticeSource.ANAC_OCDS,
                    notice_type=n_type,
                    title=title,
                    description=desc_cpv,
                    contracting_authority=delegante,
                    delegated_authority=delegata,
                    cig=cig,
                    cup=normalize_cup(title),
                    cpv_codes=[cpv] if cpv else [],
                    amount_eur=row.get("importo_complessivo_gara") or row.get("importo_lotto"),
                    award_amount_eur=award_amt,
                    discount_pct=agg.get("ribasso_aggiudicazione"),
                    published_date=row.get("data_pubblicazione"),
                    deadline_date=row.get("data_scadenza_offerta"),
                    award_date=agg.get("data_aggiudicazione_definitiva") or row.get("DATA_COMUNICAZIONE_ESITO"),
                    municipality=municipality,
                    province=prov,
                    winner_company=winner_name,
                    winner_tax_id=winner_cf,
                    contract_started=(cig in started) if is_award else None,
                    has_subcontracts=(cig in subs) if is_award else None,
                    url=ANAC_CIG_DASHBOARD_TPL.format(cig=cig),
                )
            )
        return notices

    async def _latest_ckan_json_zip_url(self, package_id: str, client: httpx.AsyncClient) -> str:
        resp = await client.get(ANAC_CKAN_PACKAGE_SHOW_URL, params={"id": package_id})
        if resp.status_code != 200:
            raise RadarNetworkError(f"ANAC CKAN package_show({package_id}) returned HTTP {resp.status_code}")
        resources = resp.json().get("result", {}).get("resources", [])
        json_urls = sorted(
            str(r["url"])
            for r in resources
            if str(r.get("url") or "").lower().endswith("_json.zip")
        )
        if not json_urls:
            raise RadarNetworkError(f"No *_json.zip resource found in ANAC package '{package_id}'")
        return json_urls[-1]

    async def fetch_ckan_sardinian_notices(
        self,
        client: httpx.AsyncClient | None = None,
        limit: int = 80,
    ) -> list[TenderNotice]:
        """Download latest monthly ANAC OpenData JSONL archives and extract Sardinian works/awards."""
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            pkg_ids = ("cig", "aggiudicazioni", "aggiudicatari", "avvio-contratto", "subappalti")
            zip_urls = await asyncio.gather(
                *(self._latest_ckan_json_zip_url(pid, http_client) for pid in pkg_ids)
            )
            cig_url, agg_url, win_url, avvio_url, sub_url = zip_urls

            # Step 1: Stream & filter ONLY Sardinian LAVORI/FORNITURE rows from `cig` first (<80 MB RAM)
            r_cig = await http_client.get(cig_url, timeout=60.0)
            r_cig.raise_for_status()
            sardinian_cig_rows = await asyncio.to_thread(
                _extract_filtered_jsonl_rows,
                r_cig.content,
                lambda r: _is_sardinian_row(r)
                and str(r.get("oggetto_principale_contratto") or "").upper() in ("LAVORI", "FORNITURE"),
            )
            del r_cig

            target_cigs = {
                c
                for r in sardinian_cig_rows
                if (c := normalize_cig(r.get("cig"))) is not None
            }
            if not target_cigs:
                return []

            def _in_targets(r: dict[str, Any]) -> bool:
                return normalize_cig(r.get("cig")) in target_cigs

            # Step 2: Filter auxiliary smaller archives sequentially keeping ONLY `target_cigs`
            aux_rows: list[list[dict[str, Any]]] = []
            for aux_url in (agg_url, win_url, avvio_url, sub_url):
                r_aux = await http_client.get(aux_url, timeout=45.0)
                r_aux.raise_for_status()
                filtered = await asyncio.to_thread(_extract_filtered_jsonl_rows, r_aux.content, _in_targets)
                aux_rows.append(filtered)
                del r_aux

            agg_rows, win_rows, avvio_rows, sub_rows = aux_rows
            awards_by_cig = {normalize_cig(r.get("cig")) or "": r for r in agg_rows}
            winners_by_cig: dict[str, dict[str, Any]] = {}
            for r in win_rows:
                c = normalize_cig(r.get("cig"))
                if c and c not in winners_by_cig:
                    winners_by_cig[c] = r
            started_cigs = {c for r in avvio_rows if (c := normalize_cig(r.get("cig"))) is not None}
            subcontract_cigs = {c for r in sub_rows if (c := normalize_cig(r.get("cig"))) is not None}

            joined = self.join_ckan_records(
                reversed(sardinian_cig_rows),
                awards_by_cig=awards_by_cig,
                winners_by_cig=winners_by_cig,
                started_cigs=started_cigs,
                subcontract_cigs=subcontract_cigs,
            )
            # Rank all Sardinian monthly works by Edilmorittu relevance BEFORE applying `limit`!
            from sardegna_radar.matcher.cav_engine import CAVScoringEngine

            scorer = CAVScoringEngine()
            joined.sort(key=lambda n: scorer.score_notice(n).assessment.score, reverse=True)
            return joined[:limit]
        finally:
            if owns_client:
                await http_client.aclose()

    async def fetch_notices(
        self,
        client: httpx.AsyncClient | None = None,
        limit: int = 80,
    ) -> list[TenderNotice]:
        """Fetch live ANAC notices: custom JSON URL if set, else live CKAN OpenData stream."""
        if not self.endpoint_url:
            return await self.fetch_ckan_sardinian_notices(client=client, limit=limit)

        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            response = await http_client.get(self.endpoint_url)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and "bando" in payload:
                single = self.parse_appalto_v23(payload)
                return [single] if single else []
            return self.parse_ocds_payload(payload)
        finally:
            if owns_client:
                await http_client.aclose()

    def parse_ocds_payload(self, payload: dict[str, Any] | list[dict[str, Any]]) -> list[TenderNotice]:
        """Parse an OCDS release package into normalized Sardinian TenderNotices."""
        releases = payload if isinstance(payload, list) else list(payload.get("releases") or payload.get("data") or [])
        notices: list[TenderNotice] = []
        for rel in releases:
            notice = self._parse_single_ocds_release(rel)
            if notice is not None:
                notices.append(notice)
        return notices

    def _parse_single_ocds_release(self, rel: dict[str, Any]) -> TenderNotice | None:
        tender = rel.get("tender") or {}
        buyer = rel.get("buyer") or {}
        buyer_name = str(buyer.get("name") or "Stazione Appaltante ANAC").strip()
        title = str(tender.get("title") or "").strip()
        if not title:
            return None

        description = str(tender.get("description") or "").strip()
        cig = normalize_cig(str(tender.get("id") or rel.get("cig") or ""))
        cup = normalize_cup(str(tender.get("cup") or rel.get("cup") or title))

        cpv_codes: list[str] = []
        municipality: str | None = None
        nuts_regions: list[str] = []
        raw_province: str | None = None

        for item in tender.get("items") or []:
            cpv_id = (item.get("classification") or {}).get("id")
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
        resolved_province = resolve_sardinian_province(raw_province or municipality or buyer_name or title)
        if nuts_regions and not is_sardinian_nuts and resolved_province == SardinianProvince.REGIONAL:
            return None
        if not is_sardinian_nuts and resolved_province == SardinianProvince.REGIONAL:
            lowered_blob = f"{buyer_name} {title} {description}".lower()
            if "sardegna" not in lowered_blob and "abbanoa" not in lowered_blob:
                return None

        winner_company: str | None = None
        for award in rel.get("awards") or []:
            for supplier in award.get("suppliers") or []:
                if supplier.get("name"):
                    winner_company = str(supplier["name"]).strip()
                    break
            if winner_company:
                break

        external_id = str(rel.get("id") or rel.get("ocid") or cig or title[:32])
        url = str(rel.get("url") or ANAC_CIG_DASHBOARD_TPL.format(cig=cig or external_id))

        return TenderNotice(
            external_id=external_id,
            source=NoticeSource.ANAC_OCDS,
            notice_type=NoticeType.CONTRACT_AWARD if winner_company else NoticeType.PUBLIC_WORKS_TENDER,
            title=title,
            description=description,
            contracting_authority=buyer_name,
            cig=cig,
            cup=cup,
            cpv_codes=cpv_codes,
            amount_eur=(tender.get("value") or {}).get("amount"),
            published_date=rel.get("date"),
            deadline_date=(tender.get("tenderPeriod") or {}).get("endDate"),
            municipality=municipality,
            province=resolved_province,
            winner_company=winner_company,
            url=url,
        )
