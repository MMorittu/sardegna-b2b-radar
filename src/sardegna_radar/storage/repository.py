"""SQLite WAL repository guaranteeing idempotent tender ingestion and deduplication."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from sardegna_radar.models import (
    CAVProductCategory,
    SardinianProvince,
    ScoredLead,
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    dedup_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    cig TEXT,
    title TEXT NOT NULL,
    contracting_authority TEXT NOT NULL,
    province TEXT NOT NULL,
    municipality TEXT,
    amount_eur REAL,
    score REAL NOT NULL,
    logistics_tier TEXT NOT NULL,
    categories_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    notified INTEGER NOT NULL DEFAULT 0,
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_province ON leads(province);
CREATE INDEX IF NOT EXISTS idx_leads_notified ON leads(notified, score DESC);
"""


class RadarRepository:
    """Persistent SQLite WAL store for scored Sardinian procurement leads."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
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
        """Create tables, indexes, and enable SQLite WAL journal mode."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)

    def upsert_lead(self, lead: ScoredLead) -> bool:
        """Insert a ScoredLead or update in-place if already seen.

        Returns True when newly inserted, False when deduplicated against an existing row.
        Existing notification status (`notified = 1`) is strictly preserved across re-scans.
        """
        self.init_db()
        with self._connect() as conn:
            return self._upsert_single(conn, lead)

    def upsert_many(self, leads: Iterable[ScoredLead]) -> tuple[int, int]:
        """Batch-upsert leads in a single WAL transaction.

        Returns `(inserted_count, deduplicated_count)`.
        """
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
            "SELECT dedup_key, notified FROM leads WHERE dedup_key = ? OR (source = ? AND external_id = ?)",
            (dedup_key, source, external_id),
        ).fetchone()

        now_iso = datetime.now(UTC).isoformat()
        categories_json = json.dumps([c.value for c in lead.assessment.matched_categories], ensure_ascii=False)
        notified_flag = int(bool(existing["notified"])) if existing else int(lead.notified)

        lead_copy = lead.model_copy(update={"notified": bool(notified_flag)})
        payload_json = lead_copy.model_dump_json()

        if existing is None:
            conn.execute(
                """
                INSERT INTO leads (
                    dedup_key, source, external_id, cig, title, contracting_authority,
                    province, municipality, amount_eur, score, logistics_tier,
                    categories_json, payload_json, notified, discovered_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dedup_key,
                    source,
                    external_id,
                    lead.notice.cig,
                    lead.notice.title,
                    lead.notice.contracting_authority,
                    lead.notice.province.value,
                    lead.notice.municipality,
                    lead.notice.amount_eur,
                    lead.assessment.score,
                    lead.assessment.logistics_tier.value,
                    categories_json,
                    payload_json,
                    notified_flag,
                    lead.discovered_at.isoformat(),
                    now_iso,
                ),
            )
            return True

        conn.execute(
            """
            UPDATE leads
            SET cig = ?,
                title = ?,
                contracting_authority = ?,
                province = ?,
                municipality = ?,
                amount_eur = ?,
                score = ?,
                logistics_tier = ?,
                categories_json = ?,
                payload_json = ?,
                updated_at = ?
            WHERE dedup_key = ?
            """,
            (
                lead.notice.cig,
                lead.notice.title,
                lead.notice.contracting_authority,
                lead.notice.province.value,
                lead.notice.municipality,
                lead.notice.amount_eur,
                lead.assessment.score,
                lead.assessment.logistics_tier.value,
                categories_json,
                payload_json,
                now_iso,
                existing["dedup_key"],
            ),
        )
        return False

    def list_leads(
        self,
        *,
        min_score: float = 0.0,
        province: SardinianProvince | None = None,
        category: CAVProductCategory | None = None,
        only_unnotified: bool = False,
        limit: int = 100,
    ) -> list[ScoredLead]:
        """Query persisted leads ordered by score descending."""
        self.init_db()
        clauses = ["score >= ?"]
        params: list[Any] = [min_score]

        if province is not None:
            clauses.append("province = ?")
            params.append(province.value)

        if only_unnotified:
            clauses.append("notified = 0")

        where_sql = " AND ".join(clauses)
        query = f"""
            SELECT payload_json, notified
            FROM leads
            WHERE {where_sql}
            ORDER BY score DESC, amount_eur DESC
            LIMIT ?
        """
        params.append(limit)

        results: list[ScoredLead] = []
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                lead = ScoredLead.model_validate_json(row["payload_json"])
                lead.notified = bool(row["notified"])
                if category is not None and category not in lead.assessment.matched_categories:
                    continue
                results.append(lead)
        return results

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
                    "SELECT payload_json FROM leads WHERE dedup_key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    continue
                lead = ScoredLead.model_validate_json(row["payload_json"])
                lead.notified = True
                cursor = conn.execute(
                    "UPDATE leads SET notified = 1, payload_json = ?, updated_at = ? WHERE dedup_key = ?",
                    (lead.model_dump_json(), now_iso, key),
                )
                updated += cursor.rowcount
        return updated

    def get_stats(self, min_priority_score: float = 45.0) -> dict[str, Any]:
        """Compute aggregate commercial intelligence statistics from the SQLite database."""
        self.init_db()
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_leads,
                    SUM(CASE WHEN score >= ? THEN 1 ELSE 0 END) AS high_priority_leads,
                    SUM(CASE WHEN score >= ? AND notified = 0 THEN 1 ELSE 0 END) AS unnotified_high_priority,
                    COALESCE(SUM(CASE WHEN score >= ? THEN amount_eur ELSE 0.0 END), 0.0) AS high_priority_value_eur
                FROM leads
                """,
                (min_priority_score, min_priority_score, min_priority_score),
            ).fetchone()

            by_province_rows = conn.execute(
                """
                SELECT province, COUNT(*) AS cnt
                FROM leads
                WHERE score >= ?
                GROUP BY province
                ORDER BY cnt DESC
                """,
                (min_priority_score,),
            ).fetchall()

            by_source_rows = conn.execute(
                """
                SELECT source, COUNT(*) AS cnt
                FROM leads
                GROUP BY source
                ORDER BY cnt DESC
                """
            ).fetchall()

        return {
            "total_leads": int(totals["total_leads"] or 0),
            "high_priority_leads": int(totals["high_priority_leads"] or 0),
            "unnotified_high_priority": int(totals["unnotified_high_priority"] or 0),
            "high_priority_value_eur": float(totals["high_priority_value_eur"] or 0.0),
            "high_priority_by_province": {r["province"]: int(r["cnt"]) for r in by_province_rows},
            "leads_by_source": {r["source"]: int(r["cnt"]) for r in by_source_rows},
        }
