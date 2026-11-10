from __future__ import annotations

from pathlib import Path
import sqlite3

from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.models import (
    CAVProductCategory,
    NoticeSource,
    NoticeType,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
)
from sardegna_radar.storage.repository import RadarRepository


def _make_sample_lead(
    *,
    external_id: str = "sardcat-001",
    cig: str | None = "B112233445",
    title: str = "Fornitura e posa tubi C.A.V. e pozzetti prefabbricati acquedotto",
    municipality: str = "Macomer",
    province: SardinianProvince = SardinianProvince.NU,
    amount_eur: float = 450000.0,
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
        url=f"https://www.sardegnacat.it/bandi/{external_id}",
    )
    return CAVScoringEngine().score_notice(notice)


class TestRadarRepository:
    def test_init_db_enables_wal_mode(self, temp_db_path: Path) -> None:
        repo = RadarRepository(temp_db_path)
        repo.init_db()
        assert temp_db_path.exists()

        with sqlite3.connect(temp_db_path) as conn:
            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert str(journal_mode).lower() == "wal"

    def test_upsert_lead_idempotency_and_no_duplicate_rows(self, temp_db_path: Path) -> None:
        repo = RadarRepository(temp_db_path)
        repo.init_db()

        lead = _make_sample_lead()
        is_new_first = repo.upsert_lead(lead)
        is_new_second = repo.upsert_lead(lead)

        assert is_new_first is True
        assert is_new_second is False

        all_leads = repo.list_leads(min_score=0.0)
        assert len(all_leads) == 1
        assert all_leads[0].dedup_key == lead.dedup_key
        assert all_leads[0].notice.cig == "B112233445"
        assert all_leads[0].assessment.score == lead.assessment.score

    def test_mark_notified_persists_across_duplicate_rescans(self, temp_db_path: Path) -> None:
        repo = RadarRepository(temp_db_path)
        repo.init_db()

        lead = _make_sample_lead()
        repo.upsert_lead(lead)

        unnotified_before = repo.list_leads(min_score=45.0, only_unnotified=True)
        assert len(unnotified_before) == 1

        marked = repo.mark_notified([lead.dedup_key])
        assert marked == 1

        # Re-scanning the exact same feed must NOT reset notified back to False
        is_new = repo.upsert_lead(lead)
        assert is_new is False

        unnotified_after = repo.list_leads(min_score=45.0, only_unnotified=True)
        assert len(unnotified_after) == 0

    def test_filtering_by_province_score_and_stats(self, temp_db_path: Path) -> None:
        repo = RadarRepository(temp_db_path)
        repo.init_db()

        lead_nu = _make_sample_lead(
            external_id="nu-1",
            cig="A111111111",
            municipality="Silanus",
            province=SardinianProvince.NU,
            amount_eur=500000.0,
        )
        lead_ca = _make_sample_lead(
            external_id="ca-1",
            cig="B222222222",
            municipality="Cagliari",
            province=SardinianProvince.CA,
            amount_eur=300000.0,
        )
        lead_low = _make_sample_lead(
            external_id="low-1",
            cig="C333333333",
            title="Fornitura tubi endotracheali ospedalieri sterili",
            municipality="Nuoro",
            province=SardinianProvince.NU,
            amount_eur=50000.0,
        )

        inserted, skipped = repo.upsert_many([lead_nu, lead_ca, lead_low])
        assert inserted == 3
        assert skipped == 0

        nu_high = repo.list_leads(min_score=45.0, province=SardinianProvince.NU)
        assert len(nu_high) == 1
        assert nu_high[0].notice.municipality == "Silanus"

        cav_pipes = repo.list_leads(min_score=45.0, category=CAVProductCategory.PIPES_CULVERTS)
        assert len(cav_pipes) == 2

        stats = repo.get_stats()
        assert stats["total_leads"] == 3
        assert stats["high_priority_leads"] == 2
        assert stats["unnotified_high_priority"] == 2
        assert stats["high_priority_value_eur"] == 800000.0
