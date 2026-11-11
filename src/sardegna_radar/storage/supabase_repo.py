"""Supabase Postgres PostgREST repository for Milestone 2 Vercel Dashboard sync."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
import json
from typing import Any

import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.exceptions import StorageError
from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    CRMStatus,
    SardinianProvince,
    ScoredLead,
)


class SupabaseRepository:
    """Dual-Ready cloud repository persisting `tenders` and `cme_items` to Supabase PostgREST."""

    def __init__(self, settings: RadarSettings) -> None:
        if not settings.supabase_enabled:
            raise StorageError("Supabase URL and Service Role Key must be configured.")
        self.settings = settings
        self.rest_base = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        self._headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            headers=self._headers,
            timeout=httpx.Timeout(self.settings.http_timeout_seconds),
        )

    def init_db(self) -> None:
        """Schema is managed via `supabase/migrations/20261110000000_init_radar_schema.sql`."""
        return None

    def upsert_lead(self, lead: ScoredLead) -> bool:
        with self._client() as client:
            return self._upsert_one(client, lead)

    def upsert_many(self, leads: Iterable[ScoredLead]) -> tuple[int, int]:
        inserted = 0
        deduplicated = 0
        with self._client() as client:
            for lead in leads:
                if self._upsert_one(client, lead):
                    inserted += 1
                else:
                    deduplicated += 1
        return inserted, deduplicated

    def _upsert_one(self, client: httpx.Client, lead: ScoredLead) -> bool:
        key = lead.dedup_key
        src_val = lead.notice.source.value
        ext_id = lead.notice.external_id
        or_clause = f"(dedup_key.eq.{key},and(source.eq.{src_val},external_id.eq.{ext_id}))"
        r_check = client.get(
            f"{self.rest_base}/tenders",
            params={"select": "dedup_key,crm_status,notified,payload", "or": or_clause},
        )
        if r_check.status_code >= 400:
            raise StorageError(f"Supabase SELECT failed ({r_check.status_code}): {r_check.text}")
        existing_rows = r_check.json()
        existing = existing_rows[0] if existing_rows else None

        effective_key = existing["dedup_key"] if existing else key
        crm_val = existing["crm_status"] if existing else lead.crm_status.value
        notified_val = bool(existing["notified"]) if existing else bool(lead.notified)
        now_iso = datetime.now(UTC).isoformat()

        effective_cme = list(lead.cme_items)
        effective_assessment = lead.assessment
        if not effective_cme and existing is not None and existing.get("payload"):
            prev_lead = ScoredLead.model_validate(existing["payload"])
            effective_cme = prev_lead.cme_items
            if effective_cme:
                effective_assessment = CAVScoringEngine().score_notice(
                    lead.notice, cme_items=effective_cme
                ).assessment

        synced_lead = lead.model_copy(
            update={
                "assessment": effective_assessment,
                "crm_status": CRMStatus(crm_val),
                "notified": notified_val,
                "cme_items": effective_cme,
            }
        )
        n = synced_lead.notice
        a = synced_lead.assessment
        row_payload = {
            "dedup_key": effective_key,
            "source": n.source.value,
            "external_id": n.external_id,
            "notice_type": n.notice_type.value,
            "cig": n.cig,
            "cup": n.cup,
            "title": n.title,
            "contracting_authority": n.contracting_authority,
            "delegated_authority": n.delegated_authority,
            "province": n.province.value,
            "municipality": n.municipality,
            "amount_eur": n.amount_eur,
            "award_amount_eur": n.award_amount_eur,
            "discount_pct": n.discount_pct,
            "winner_company": n.winner_company,
            "winner_tax_id": n.winner_tax_id,
            "winner_distance_km": n.winner_distance_km,
            "rup_name": n.rup_name,
            "contract_started": n.contract_started,
            "has_subcontracts": n.has_subcontracts,
            "score": a.score,
            "logistics_tier": a.logistics_tier.value,
            "crm_status": crm_val,
            "notified": notified_val,
            "url": n.url,
            "attachment_url": n.attachment_url,
            "http_status": n.http_status,
            "payload": json.loads(synced_lead.model_dump_json()),
            "updated_at": now_iso,
        }
        if existing is None:
            row_payload["discovered_at"] = synced_lead.discovered_at.isoformat()

        r_up = client.post(
            f"{self.rest_base}/tenders",
            params={"on_conflict": "dedup_key"},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            json=row_payload,
        )
        if r_up.status_code >= 400:
            raise StorageError(f"Supabase UPSERT failed ({r_up.status_code}): {r_up.text}")

        if lead.cme_items:
            r_del = client.delete(
                f"{self.rest_base}/cme_items", params={"dedup_key": f"eq.{effective_key}"}
            )
            if r_del.status_code >= 400:
                raise StorageError(f"Supabase CME DELETE failed ({r_del.status_code}): {r_del.text}")
            cme_rows = [
                {
                    "dedup_key": effective_key,
                    "item_number": it.item_number,
                    "tariff_code": it.tariff_code,
                    "description": it.description,
                    "unit": it.unit,
                    "quantity": it.quantity,
                    "unit_price_eur": it.unit_price_eur,
                    "total_price_eur": it.total_price_eur,
                    "product_line": it.product_line.value,
                    "category": it.category.value,
                    "matched_catalog_label": it.matched_catalog_label,
                }
                for it in lead.cme_items
            ]
            r_cme = client.post(
                f"{self.rest_base}/cme_items",
                headers={"Prefer": "return=minimal"},
                json=cme_rows,
            )
            if r_cme.status_code >= 400:
                raise StorageError(f"Supabase CME INSERT failed ({r_cme.status_code}): {r_cme.text}")

        return existing is None

    def list_leads(
        self,
        *,
        min_score: float = 0.0,
        province: SardinianProvince | None = None,
        category: CAVProductCategory | None = None,
        crm_status: CRMStatus | None = None,
        only_unnotified: bool = False,
        limit: int = 100,
    ) -> list[ScoredLead]:
        fetch_limit = max(limit * 5, 250) if category is not None else limit
        params: dict[str, str] = {
            "select": "payload,crm_status,notified,cme_items(*)",
            "score": f"gte.{min_score}",
            "order": "score.desc",
            "limit": str(fetch_limit),
        }
        if province is not None:
            params["province"] = f"eq.{province.value}"
        if crm_status is not None:
            params["crm_status"] = f"eq.{crm_status.value}"
        if only_unnotified:
            params["notified"] = "eq.false"

        with self._client() as client:
            resp = client.get(f"{self.rest_base}/tenders", params=params)
            if resp.status_code >= 400:
                raise StorageError(f"Supabase list_leads failed ({resp.status_code}): {resp.text}")
            rows = resp.json()

        results: list[ScoredLead] = []
        for row in rows:
            lead = ScoredLead.model_validate(row["payload"])
            lead.crm_status = CRMStatus(row["crm_status"])
            lead.notified = bool(row["notified"])
            if row.get("cme_items"):
                lead.cme_items = [CMEItem.model_validate(c) for c in row["cme_items"]]
            if category is not None and category not in lead.assessment.matched_categories:
                continue
            results.append(lead)
            if len(results) >= limit:
                break
        return results

    def update_crm_status(self, identifier: str, status: CRMStatus) -> bool:
        clean = identifier.strip()
        now_iso = datetime.now(UTC).isoformat()
        with self._client() as client:
            for col, val in (("dedup_key", clean), ("cig", clean.upper()), ("external_id", clean)):
                r_get = client.get(
                    f"{self.rest_base}/tenders",
                    params={"select": "dedup_key,payload", col: f"eq.{val}"},
                )
                if r_get.status_code < 400 and r_get.json():
                    row = r_get.json()[0]
                    patch_body: dict[str, Any] = {"crm_status": status.value, "updated_at": now_iso}
                    if row.get("payload"):
                        lead = ScoredLead.model_validate(row["payload"])
                        lead.crm_status = status
                        patch_body["payload"] = json.loads(lead.model_dump_json())
                    resp = client.patch(
                        f"{self.rest_base}/tenders",
                        params={"dedup_key": f"eq.{row['dedup_key']}"},
                        headers={"Prefer": "return=representation"},
                        json=patch_body,
                    )
                    if resp.status_code < 400 and resp.json():
                        return True
        return False

    def mark_notified(self, dedup_keys: Sequence[str]) -> int:
        if not dedup_keys:
            return 0
        updated = 0
        with self._client() as client:
            for key in dedup_keys:
                resp = client.patch(
                    f"{self.rest_base}/tenders",
                    params={"dedup_key": f"eq.{key}"},
                    headers={"Prefer": "return=representation"},
                    json={"notified": True, "updated_at": datetime.now(UTC).isoformat()},
                )
                if resp.status_code < 400 and resp.json():
                    updated += 1
        return updated

    def get_stats(self, min_priority_score: float = 45.0) -> dict[str, Any]:
        leads = self.list_leads(min_score=0.0, limit=1000)
        high = [l for l in leads if l.assessment.score >= min_priority_score]
        by_prov: dict[str, int] = {}
        for l in high:
            by_prov[l.notice.province.value] = by_prov.get(l.notice.province.value, 0) + 1
        by_src: dict[str, int] = {}
        by_crm: dict[str, int] = {}
        for l in leads:
            by_src[l.notice.source.value] = by_src.get(l.notice.source.value, 0) + 1
            by_crm[l.crm_status.value] = by_crm.get(l.crm_status.value, 0) + 1
        return {
            "total_leads": len(leads),
            "high_priority_leads": len(high),
            "unnotified_high_priority": sum(1 for l in high if not l.notified),
            "high_priority_value_eur": sum(
                (l.notice.award_amount_eur or l.notice.amount_eur or 0.0) for l in high
            ),
            "high_priority_by_province": by_prov,
            "leads_by_source": by_src,
            "by_crm_status": by_crm,
        }
