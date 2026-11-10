from __future__ import annotations

from datetime import date
import pytest
from pydantic import ValidationError

from sardegna_radar.config import RadarSettings
from sardegna_radar.models import (
    CAVProductCategory,
    LogisticsTier,
    MatchAssessment,
    NoticeSource,
    NoticeType,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
    normalize_cig,
    parse_italian_currency,
    parse_italian_date,
    resolve_sardinian_province,
)


class TestCurrencyAndDateParsers:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("€ 1.240.500,75", 1240500.75),
            ("€ 145.200,00 oltre IVA", 145200.0),
            ("Importo a base d'asta: Euro 89.450,50 (IVA esclusa)", 89450.5),
            ("1250000.50", 1250000.5),
            ("350.000", 350000.0),
            ("45,50 €", 45.5),
            (420000, 420000.0),
            (185000.25, 185000.25),
            (None, None),
            ("", None),
            ("Non determinato", None),
        ],
    )
    def test_parse_italian_currency(self, raw: str | float | int | None, expected: float | None) -> None:
        assert parse_italian_currency(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("25/11/2026", date(2026, 11, 25)),
            ("2026-11-25", date(2026, 11, 25)),
            ("25-11-2026", date(2026, 11, 25)),
            ("25.11.2026 ore 12:00", date(2026, 11, 25)),
            ("Scadenza: 05/02/2027", date(2027, 2, 5)),
            (date(2026, 12, 1), date(2026, 12, 1)),
            (None, None),
            ("", None),
            ("data da destinarsi", None),
        ],
    )
    def test_parse_italian_date(self, raw: str | date | None, expected: date | None) -> None:
        assert parse_italian_date(raw) == expected


class TestCigAndProvinceNormalization:
    @pytest.mark.parametrize(
        ("raw_cig", "expected"),
        [
            ("b2a94f10c8", "B2A94F10C8"),
            ("CIG: A04F92B11E", "A04F92B11E"),
            ("  cig [987654321a] ", "987654321A"),
            ("SHORT", None),
            (None, None),
            ("", None),
        ],
    )
    def test_normalize_cig(self, raw_cig: str | None, expected: str | None) -> None:
        assert normalize_cig(raw_cig) == expected

    @pytest.mark.parametrize(
        ("hint", "expected"),
        [
            ("NU", SardinianProvince.NU),
            ("Nuoro", SardinianProvince.NU),
            ("Comune di Macomer (NU)", SardinianProvince.NU),
            ("Comune di Silanus", SardinianProvince.NU),
            ("Sassari", SardinianProvince.SS),
            ("Olbia", SardinianProvince.SS),
            ("Oristano (OR)", SardinianProvince.OR),
            ("Cagliari", SardinianProvince.CA),
            ("Carbonia - Sud Sardegna (SU)", SardinianProvince.SU),
            ("Regione Autonoma della Sardegna", SardinianProvince.REGIONAL),
            (None, SardinianProvince.REGIONAL),
        ],
    )
    def test_resolve_sardinian_province(self, hint: str | None, expected: SardinianProvince) -> None:
        assert resolve_sardinian_province(hint) == expected


class TestTenderNoticeAndLeadModels:
    def test_tender_notice_normalizes_fields(self) -> None:
        notice = TenderNotice(
            external_id="ras-2026-0091",
            source=NoticeSource.RAS,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="  Lavori di rifacimento condotta fognaria in C.A.V. a Macomer  ",
            description="Fornitura e posa tubazioni in calcestruzzo vibrocompresso DN 800 e pozzetti.",
            contracting_authority="Abbanoa S.p.A. - Distretto di Nuoro",
            cig="cig: b49102f8ac",
            cup="j12b26000450002",
            cpv_codes=["45231300-8", " 44114200-4 "],
            amount_eur="€ 1.240.500,75 oltre IVA",
            published_date="10/11/2026",
            deadline_date="15/12/2026 ore 13:00",
            municipality="Macomer",
            province="Nuoro",
            url="https://www.regione.sardegna.it/atti/ras-2026-0091",
        )

        assert notice.cig == "B49102F8AC"
        assert notice.cup == "J12B26000450002"
        assert notice.amount_eur == 1240500.75
        assert notice.published_date == date(2026, 11, 10)
        assert notice.deadline_date == date(2026, 12, 15)
        assert notice.province == SardinianProvince.NU
        assert notice.cpv_codes == ["45231300-8", "44114200-4"]
        assert notice.title == "Lavori di rifacimento condotta fognaria in C.A.V. a Macomer"

    def test_scored_lead_validation_and_priority(self) -> None:
        notice = TenderNotice(
            external_id="anac-991",
            source=NoticeSource.ANAC_OCDS,
            title="Ampliamento cimitero comunale loculi prefabbricati",
            contracting_authority="Comune di Bolotana",
            cig="A123456789",
            amount_eur=380000.0,
            municipality="Bolotana",
            province="NU",
            url="https://dati.anticorruzione.it/bando/A123456789",
        )
        assessment = MatchAssessment(
            score=88.5,
            matched_categories=[CAVProductCategory.CEMETERY_NICHES, CAVProductCategory.MANHOLES_CHAMBERS],
            matched_keywords=["loculi prefabbricati", "cimitero", "pozzetti"],
            cpv_bonus_applied=True,
            logistics_tier=LogisticsTier.TIER_1_CORE,
            estimated_distance_km=11,
            rationale="Direct C.A.V. cemetery expansion within 15km of Silanus plant.",
        )
        lead = ScoredLead(notice=notice, assessment=assessment)
        assert lead.is_high_priority is True
        assert lead.dedup_key == "anac_ocds:A123456789"

    def test_invalid_score_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            MatchAssessment(
                score=105.0,
                matched_categories=[],
                matched_keywords=[],
                logistics_tier=LogisticsTier.TIER_3_ISLAND,
            )

    def test_radar_settings_defaults(self, tmp_path) -> None:
        settings = RadarSettings(db_path=tmp_path / "custom.db")
        assert settings.company_name == "Sardegna Prefabbricati C.A.V. S.r.l."
        assert settings.company_piva == "00000000000"
        assert settings.company_base_municipality == "Silanus"
        assert settings.http_max_retries == 3
        assert settings.http_timeout_seconds == 15.0
        assert settings.http_connect_timeout_seconds == 30.0
        assert settings.telegram_enabled is False
