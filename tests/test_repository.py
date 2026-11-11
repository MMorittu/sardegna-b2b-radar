from __future__ import annotations

from pathlib import Path
import sqlite3
import pytest
from pytest_httpx import HTTPXMock

from sardegna_radar.config import RadarSettings
from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    CRMStatus,
    NoticeSource,
    NoticeType,
    ProductLine,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
)
from sardegna_radar.storage.repository import RadarRepository, build_repository
from sardegna_radar.storage.supabase_repo import SupabaseRepository


def _make_sample_lead(
    *,
    external_id: str = "sardcat-001",
    cig: str | None = "B112233445",
    title: str = "Fornitura e posa tubi C.A.V. e pozzetti prefabbricati acquedotto",
    municipality: str = "Macomer",
    province: SardinianProvince = SardinianProvince.NU,
    amount_eur: float = 450000.0,
    with_cme: bool = False,
) -> ScoredLead:
    notice = TenderNotice(
        external_id=external_id,
        source=NoticeSource.SARDEGNACAT,
        notice_type=NoticeType.PUBLIC_WORKS_TENDER,
        title=title,
        description="Lavori idraulici condotta in calcestruzzo vibrocompresso DN 600.",
        contracting_authority="Abbanoa S.p.A.",
        cig=cig,
        cpv_codes=["45231300-8"],
        amount_eur=amount_eur,
        published_date="10/11/2026",
        deadline_date="20/12/2026",
        municipality=municipality,
        province=province,
        url=f"https://sardegnacat.regione.sardegna.it/portalegare/index.php/bandi?bando={external_id}",
        http_status=200,
    )
    items = (
        [
            CMEItem(
                item_number=12,
                tariff_code="SAR26_PF.0003.0015.0002.A",
                description="Pozzetto prefabbricato in cls vibrocompresso 50x50",
                unit="cad.",
                quantity=8.0,
                total_price_eur=1544.32,
                product_line=ProductLine.LINEA_A,
                category=CAVProductCategory.MANHOLES_CHAMBERS,
                matched_catalog_label="Pozzetti cls 50x50",
            )
        ]
        if with_cme
        else []
    )
    return CAVScoringEngine().score_notice(notice, cme_items=items)


class TestSQLiteRadarRepository:
    def test_init_db_creates_tenders_and_cme_items_tables_in_wal_mode(self, temp_db_path: Path) -> None:
        repo = RadarRepository(temp_db_path)
        repo.init_db()
        assert temp_db_path.exists()

        with sqlite3.connect(temp_db_path) as conn:
            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert str(journal_mode).lower() == "wal"
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "tenders" in tables
            assert "cme_items" in tables

    def test_persists_cme_items_and_preserves_crm_status_and_notified_on_rescan(
        self, temp_db_path: Path
    ) -> None:
        repo = RadarRepository(temp_db_path)
        repo.init_db()

        lead = _make_sample_lead(with_cme=True)
        assert repo.upsert_lead(lead) is True

        # Update CRM status and notified flag
        assert repo.update_crm_status("B112233445", CRMStatus.PREVENTIVO_INVIATO) is True
        assert repo.mark_notified([lead.dedup_key]) == 1

        # Re-scan same tender with updated amount AND metadata-only (no CME): must preserve crm_status, notified, cme_items, AND CME-backed score!
        lead_rescan = _make_sample_lead(amount_eur=465000.0, with_cme=False)
        assert repo.upsert_lead(lead_rescan) is False

        stored = repo.list_leads(min_score=0.0, category=CAVProductCategory.MANHOLES_CHAMBERS)
        assert len(stored) == 1
        saved = stored[0]
        assert saved.notice.amount_eur == 465000.0
        assert saved.crm_status == CRMStatus.PREVENTIVO_INVIATO
        assert saved.notified is True
        assert len(saved.cme_items) == 1
        assert saved.cme_items[0].quantity == 8.0
        assert saved.assessment.score >= lead.assessment.score

    def test_filtering_by_province_crm_status_and_stats(self, temp_db_path: Path) -> None:
        repo = RadarRepository(temp_db_path)
        repo.init_db()

        lead_nu = _make_sample_lead(external_id="nu-1", cig="A111111111", municipality="Silanus", province=SardinianProvince.NU)
        lead_ca = _make_sample_lead(external_id="ca-1", cig="B222222222", municipality="Cagliari", province=SardinianProvince.CA)
        lead_low = _make_sample_lead(
            external_id="low-1",
            cig="C333333333",
            title="Fornitura dispositivi medici ospedalieri sterili",
            municipality="Nuoro",
            province=SardinianProvince.NU,
        )

        inserted, skipped = repo.upsert_many([lead_nu, lead_ca, lead_low])
        assert inserted == 3
        assert skipped == 0

        repo.update_crm_status("B222222222", CRMStatus.SCARTATO)
        da_chiamare = repo.list_leads(min_score=45.0, crm_status=CRMStatus.DA_CHIAMARE)
        assert [l.notice.cig for l in da_chiamare] == ["A111111111"]

        stats = repo.get_stats(min_priority_score=45.0)
        assert stats["total_leads"] == 3
        assert stats["high_priority_leads"] == 2
        assert stats["by_crm_status"]["scartato"] == 1


class TestDualReadySupabaseFactory:
    def test_build_repository_selects_sqlite_vs_supabase(self, temp_db_path: Path) -> None:
        local_cfg = RadarSettings(_env_file=None, db_path=temp_db_path)
        assert isinstance(build_repository(local_cfg), RadarRepository)

        cloud_cfg = RadarSettings(
            _env_file=None,
            db_path=temp_db_path,
            supabase_url="https://xyzcompany.supabase.co",
            supabase_service_key="sb_secret_test_key",
        )
        assert isinstance(build_repository(cloud_cfg), SupabaseRepository)

    def test_supabase_repo_upserts_via_postgrest(self, httpx_mock: HTTPXMock, temp_db_path: Path) -> None:
        cfg = RadarSettings(
            _env_file=None,
            db_path=temp_db_path,
            supabase_url="https://xyzcompany.supabase.co",
            supabase_service_key="sb_secret_test_key",
        )
        # 1. Existing check returns empty list (new record)
        httpx_mock.add_response(
            method="GET",
            json=[],
        )
        # 2. Upsert into tenders
        httpx_mock.add_response(
            method="POST",
            url="https://xyzcompany.supabase.co/rest/v1/tenders?on_conflict=dedup_key",
            status_code=201,
            json=[],
        )
        # 3. Delete old cme_items + insert new cme_items
        httpx_mock.add_response(
            method="DELETE",
            url="https://xyzcompany.supabase.co/rest/v1/cme_items?dedup_key=eq.cig%3AB112233445",
            status_code=204,
        )
        httpx_mock.add_response(
            method="POST",
            url="https://xyzcompany.supabase.co/rest/v1/cme_items",
            status_code=201,
            json=[],
        )

        repo = SupabaseRepository(cfg)
        lead = _make_sample_lead(with_cme=True)
        assert repo.upsert_lead(lead) is True
