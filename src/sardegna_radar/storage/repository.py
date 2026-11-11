"""Dual-Ready SQLite WAL repository (`tenders` + `cme_items` + `crm_status`) & store factory."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Protocol

from sardegna_radar.config import RadarSettings
from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    CRMStatus,
    ProductLine,
    SardinianProvince,
    ScoredLead,
)
from sardegna_radar.storage.supabase_repo import SupabaseRepository

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tenders (
    dedup_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    notice_type TEXT NOT NULL,
    cig TEXT,
    cup TEXT,
    title TEXT NOT NULL,
    contracting_authority TEXT NOT NULL,
    delegated_authority TEXT,
    province TEXT NOT NULL,
    municipality TEXT,
    amount_eur REAL,
    award_amount_eur REAL,
    discount_pct REAL,
    winner_company TEXT,
    winner_tax_id TEXT,
    winner_distance_km INTEGER,
    rup_name TEXT,
    contract_started INTEGER,
    has_subcontracts INTEGER,
    score REAL NOT NULL,
    logistics_tier TEXT NOT NULL,
    crm_status TEXT NOT NULL DEFAULT 'da_chiamare'
        CHECK (crm_status IN ('da_chiamare', 'preventivo_inviato', 'vinto', 'scartato')),
    notified INTEGER NOT NULL DEFAULT 0,
    url TEXT NOT NULL,
    attachment_url TEXT,
    http_status INTEGER,
    payload_json TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS cme_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedup_key TEXT NOT NULL REFERENCES tenders(dedup_key) ON DELETE CASCADE,
    item_number INTEGER,
    tariff_code TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0.0,
    unit_price_eur REAL,
    total_price_eur REAL,
    product_line TEXT NOT NULL,
    category TEXT NOT NULL,
    matched_catalog_label TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_cme_items_dedup_key ON cme_items(dedup_key);
CREATE INDEX IF NOT EXISTS idx_tenders_score ON tenders(score DESC);
CREATE INDEX IF NOT EXISTS idx_tenders_province ON tenders(province);
CREATE INDEX IF NOT EXISTS idx_tenders_crm_actionable ON tenders(crm_status, score DESC);
CREATE INDEX IF NOT EXISTS idx_tenders_notified ON tenders(notified, score DESC);
CREATE INDEX IF NOT EXISTS idx_tenders_cig ON tenders(cig);
"""


class LeadStoreProtocol(Protocol):
    """Common storage interface shared by local SQLite WAL and Supabase Postgres."""

    def init_db(self) -> None: ...
    def upsert_lead(self, lead: ScoredLead) -> bool: ...
    def upsert_many(self, leads: Iterable[ScoredLead]) -> tuple[int, int]: ...
    def list_leads(
        self,
        *,
        min_score: float = 0.0,
        province: SardinianProvince | None = None,
        category: CAVProductCategory | None = None,
        crm_status: CRMStatus | None = None,
        only_unnotified: bool = False,
        limit: int = 100,
    ) -> list[ScoredLead]: ...
    def update_crm_status(self, identifier: str, status: CRMStatus) -> bool: ...
    def mark_notified(self, dedup_keys: Sequence[str]) -> int: ...
    def get_stats(self, min_priority_score: float = 45.0) -> dict[str, Any]: ...


def build_repository(settings: RadarSettings | None = None) -> LeadStoreProtocol:
    """Return SupabaseRepository when cloud credentials are set, else local SQLite RadarRepository."""
    cfg = settings or RadarSettings()
    if cfg.supabase_enabled:
        return SupabaseRepository(cfg)
    return RadarRepository(cfg.db_path)


class RadarRepository:
    """Persistent SQLite WAL store for scored Sardinian tenders, CME items, and CRM status."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create `tenders` and `cme_items` tables, indexes, and enable WAL mode."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)

    def upsert_lead(self, lead: ScoredLead) -> bool:
        """Insert or update a lead while strictly preserving `crm_status` and `notified`."""
        self.init_db()
        with self._connect() as conn:
            return self._upsert_single(conn, lead)

    def upsert_many(self, leads: Iterable[ScoredLead]) -> tuple[int, int]:
        """Batch-upsert leads in a single WAL transaction."""
        self.init_db()
        inserted = 0
        deduplicated = 0
        with self._connect() as conn:
            for lead in leads:
                if self._upsert_single(conn, lead):
                    inserted += 1
                else:
                    deduplicated += 1
        return inserted, deduplicated

    @staticmethod
    def _upsert_single(conn: sqlite3.Connection, lead: ScoredLead) -> bool:
        dedup_key = lead.dedup_key
        source = lead.notice.source.value
        external_id = lead.notice.external_id
        existing = conn.execute(
            "SELECT dedup_key, crm_status, notified, payload_json FROM tenders "
            "WHERE dedup_key = ? OR (source = ? AND external_id = ?)",
            (dedup_key, source, external_id),
        ).fetchone()

        effective_key = existing["dedup_key"] if existing else dedup_key
        crm_val = existing["crm_status"] if existing else lead.crm_status.value
        notified_flag = int(bool(existing["notified"])) if existing else int(lead.notified)
        now_iso = datetime.now(UTC).isoformat()

        # Preserve previously parsed CME items AND CME-backed score if re-scanning notice metadata only
        effective_cme = list(lead.cme_items)
        effective_assessment = lead.assessment
        if not effective_cme and existing is not None:
            prev_lead = ScoredLead.model_validate_json(existing["payload_json"])
            effective_cme = prev_lead.cme_items
            if effective_cme:
                effective_assessment = CAVScoringEngine().score_notice(
                    lead.notice, cme_items=effective_cme
                ).assessment

        synced_lead = lead.model_copy(
            update={
                "assessment": effective_assessment,
                "crm_status": CRMStatus(crm_val),
                "notified": bool(notified_flag),
                "cme_items": effective_cme,
            }
        )
        n = synced_lead.notice
        a = synced_lead.assessment
        payload_json = synced_lead.model_dump_json()

        started_db = None if n.contract_started is None else int(n.contract_started)
        subs_db = None if n.has_subcontracts is None else int(n.has_subcontracts)

        if existing is None:
            conn.execute(
                """
                INSERT INTO tenders (
                    dedup_key, source, external_id, notice_type, cig, cup, title,
                    contracting_authority, delegated_authority, province, municipality,
                    amount_eur, award_amount_eur, discount_pct, winner_company, winner_tax_id,
                    winner_distance_km, rup_name, contract_started, has_subcontracts,
                    score, logistics_tier, crm_status, notified, url, attachment_url,
                    http_status, payload_json, discovered_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    effective_key,
                    source,
                    external_id,
                    n.notice_type.value,
                    n.cig,
                    n.cup,
                    n.title,
                    n.contracting_authority,
                    n.delegated_authority,
                    n.province.value,
                    n.municipality,
                    n.amount_eur,
                    n.award_amount_eur,
                    n.discount_pct,
                    n.winner_company,
                    n.winner_tax_id,
                    n.winner_distance_km,
                    n.rup_name,
                    started_db,
                    subs_db,
                    a.score,
                    a.logistics_tier.value,
                    crm_val,
                    notified_flag,
                    n.url,
                    n.attachment_url,
                    n.http_status,
                    payload_json,
                    synced_lead.discovered_at.isoformat(),
                    now_iso,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE tenders
                SET notice_type = ?, cig = ?, cup = ?, title = ?, contracting_authority = ?,
                    delegated_authority = ?, province = ?, municipality = ?, amount_eur = ?,
                    award_amount_eur = ?, discount_pct = ?, winner_company = ?, winner_tax_id = ?,
                    winner_distance_km = ?, rup_name = ?, contract_started = ?, has_subcontracts = ?,
                    score = ?, logistics_tier = ?, url = ?, attachment_url = ?, http_status = ?,
                    payload_json = ?, updated_at = ?
                WHERE dedup_key = ?
                """,
                (
                    n.notice_type.value,
                    n.cig,
                    n.cup,
                    n.title,
                    n.contracting_authority,
                    n.delegated_authority,
                    n.province.value,
                    n.municipality,
                    n.amount_eur,
                    n.award_amount_eur,
                    n.discount_pct,
                    n.winner_company,
                    n.winner_tax_id,
                    n.winner_distance_km,
                    n.rup_name,
                    started_db,
                    subs_db,
                    a.score,
                    a.logistics_tier.value,
                    n.url,
                    n.attachment_url,
                    n.http_status,
                    payload_json,
                    now_iso,
                    effective_key,
                ),
            )

        if lead.cme_items:
            conn.execute("DELETE FROM cme_items WHERE dedup_key = ?", (effective_key,))
            conn.executemany(
                """
                INSERT INTO cme_items (
                    dedup_key, item_number, tariff_code, description, unit, quantity,
                    unit_price_eur, total_price_eur, product_line, category, matched_catalog_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        effective_key,
                        it.item_number,
                        it.tariff_code,
                        it.description,
                        it.unit,
                        it.quantity,
                        it.unit_price_eur,
                        it.total_price_eur,
                        it.product_line.value,
                        it.category.value,
                        it.matched_catalog_label,
                    )
                    for it in lead.cme_items
                ],
            )

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
        """Query persisted leads with normalized `cme_items` and `crm_status`."""
        self.init_db()
        clauses = ["score >= ?"]
        params: list[Any] = [min_score]

        if province is not None:
            clauses.append("province = ?")
            params.append(province.value)
        if crm_status is not None:
            clauses.append("crm_status = ?")
            params.append(crm_status.value)
        if category is not None:
            clauses.append("payload_json LIKE ?")
            params.append(f'%"{category.value}"%')
        if only_unnotified:
            clauses.append("notified = 0")

        where_sql = " AND ".join(clauses)
        params.append(limit)

        results: list[ScoredLead] = []
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT dedup_key, payload_json, crm_status, notified
                FROM tenders
                WHERE {where_sql}
                ORDER BY score DESC, COALESCE(award_amount_eur, amount_eur, 0.0) DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

            cme_by_key: dict[str, list[CMEItem]] = {}
            if rows:
                keys = [row["dedup_key"] for row in rows]
                placeholders = ",".join("?" for _ in keys)
                all_cme_rows = conn.execute(
                    f"SELECT * FROM cme_items WHERE dedup_key IN ({placeholders}) ORDER BY item_number ASC, id ASC",
                    keys,
                ).fetchall()
                for cr in all_cme_rows:
                    cme_by_key.setdefault(cr["dedup_key"], []).append(
                        CMEItem(
                            item_number=cr["item_number"],
                            tariff_code=cr["tariff_code"],
                            description=cr["description"],
                            unit=cr["unit"],
                            quantity=cr["quantity"],
                            unit_price_eur=cr["unit_price_eur"],
                            total_price_eur=cr["total_price_eur"],
                            product_line=ProductLine(cr["product_line"]),
                            category=CAVProductCategory(cr["category"]),
                            matched_catalog_label=cr["matched_catalog_label"],
                        )
                    )

            for row in rows:
                lead = ScoredLead.model_validate_json(row["payload_json"])
                lead.crm_status = CRMStatus(row["crm_status"])
                lead.notified = bool(row["notified"])
                if row["dedup_key"] in cme_by_key:
                    lead.cme_items = cme_by_key[row["dedup_key"]]

                if category is not None and category not in lead.assessment.matched_categories:
                    continue
                results.append(lead)
        return results

    def update_crm_status(self, identifier: str, status: CRMStatus) -> bool:
        """Update CRM status by `dedup_key` or `CIG`, keeping `payload_json` synchronized."""
        self.init_db()
        clean = identifier.strip()
        now_iso = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT dedup_key, payload_json FROM tenders WHERE dedup_key = ? OR cig = ? OR external_id = ?",
                (clean, clean.upper(), clean),
            ).fetchone()
            if row is None:
                return False
            lead = ScoredLead.model_validate_json(row["payload_json"])
            lead.crm_status = status
            conn.execute(
                "UPDATE tenders SET crm_status = ?, payload_json = ?, updated_at = ? WHERE dedup_key = ?",
                (status.value, lead.model_dump_json(), now_iso, row["dedup_key"]),
            )
            return True

    def mark_notified(self, dedup_keys: Sequence[str]) -> int:
        """Mark the specified dedup_keys as notified (`notified = 1`)."""
        if not dedup_keys:
            return 0
        self.init_db()
        now_iso = datetime.now(UTC).isoformat()
        updated = 0
        with self._connect() as conn:
            for key in dedup_keys:
                row = conn.execute(
                    "SELECT payload_json FROM tenders WHERE dedup_key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    continue
                lead = ScoredLead.model_validate_json(row["payload_json"])
                lead.notified = True
                cursor = conn.execute(
                    "UPDATE tenders SET notified = 1, payload_json = ?, updated_at = ? WHERE dedup_key = ?",
                    (lead.model_dump_json(), now_iso, key),
                )
                updated += cursor.rowcount
        return updated

    def get_stats(self, min_priority_score: float = 45.0) -> dict[str, Any]:
        """Compute aggregate commercial intelligence & CRM pipeline metrics."""
        self.init_db()
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_leads,
                    SUM(CASE WHEN score >= ? THEN 1 ELSE 0 END) AS high_priority_leads,
                    SUM(CASE WHEN score >= ? AND notified = 0 THEN 1 ELSE 0 END) AS unnotified_high_priority,
                    COALESCE(SUM(CASE WHEN score >= ? THEN COALESCE(award_amount_eur, amount_eur, 0.0) ELSE 0.0 END), 0.0) AS high_priority_value_eur
                FROM tenders
                """,
                (min_priority_score, min_priority_score, min_priority_score),
            ).fetchone()

            by_province_rows = conn.execute(
                "SELECT province, COUNT(*) AS cnt FROM tenders WHERE score >= ? GROUP BY province ORDER BY cnt DESC",
                (min_priority_score,),
            ).fetchall()
            by_source_rows = conn.execute(
                "SELECT source, COUNT(*) AS cnt FROM tenders GROUP BY source ORDER BY cnt DESC"
            ).fetchall()
            by_crm_rows = conn.execute(
                "SELECT crm_status, COUNT(*) AS cnt FROM tenders GROUP BY crm_status ORDER BY cnt DESC"
            ).fetchall()

        return {
            "total_leads": int(totals["total_leads"] or 0),
            "high_priority_leads": int(totals["high_priority_leads"] or 0),
            "unnotified_high_priority": int(totals["unnotified_high_priority"] or 0),
            "high_priority_value_eur": float(totals["high_priority_value_eur"] or 0.0),
            "high_priority_by_province": {r["province"]: int(r["cnt"]) for r in by_province_rows},
            "leads_by_source": {r["source"]: int(r["cnt"]) for r in by_source_rows},
            "by_crm_status": {r["crm_status"]: int(r["cnt"]) for r in by_crm_rows},
        }
