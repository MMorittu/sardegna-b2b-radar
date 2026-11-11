from __future__ import annotations

from datetime import date
from pathlib import Path
import pytest
from pydantic import ValidationError

from sardegna_radar.config import RadarSettings
from sardegna_radar.exceptions import (
    CMEParseError,
    RadarError,
    RadarNetworkError,
    StorageError,
    UrlValidationError,
)
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    CRMStatus,
    LogisticsTier,
    MatchAssessment,
    NoticeSource,
    NoticeType,
    ProductLine,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
    estimate_company_distance_from_tax_id,
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
            ("2´981,89", 2981.89),
            ("12´117,68 €", 12117.68),
            ("1´184´875,50", 1184875.50),
            ("2'981,89", 2981.89),
            ("1250000.50", 1250000.5),
            ("350.000", 350000.0),
            ("45,50 €", 45.5),
            ("0,450", 0.45),
            ("1,250", 1.25),
            (420000, 420000.0),
            (185000.25, 185000.25),
            (None, None),
            ("", None),
            ("Non determinato", None),
        ],
    )
    def test_parse_italian_currency_and_primus_numbers(
        self, raw: str | float | int | None, expected: float | None
    ) -> None:
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


class TestCigProvinceAndTaxIdDistance:
    @pytest.mark.parametrize(
        ("raw_cig", "expected"),
        [
            ("b2a94f10c8", "B2A94F10C8"),
            ("BCB16FC2F3", "BCB16FC2F3"),
            ("CIG: A04F92B11E", "A04F92B11E"),
            ("  cig [987654321a] ", "987654321A"),
            (["BCB16FC2F3"], "BCB16FC2F3"),
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
            ("NUORO", SardinianProvince.NU),
            ("Comune di Macomer (NU)", SardinianProvince.NU),
            ("Comune di Silanus", SardinianProvince.NU),
            ("Sassari", SardinianProvince.SS),
            ("Olbia", SardinianProvince.SS),
            ("Oristano (OR)", SardinianProvince.OR),
            ("Cagliari", SardinianProvince.CA),
            ("Carbonia - Sud Sardegna (SU)", SardinianProvince.SU),
            ("Comune di Atzara", SardinianProvince.NU),
            ("Messa in sicurezza caduta massi parete rocciosa", SardinianProvince.REGIONAL),
            ("Regione Autonoma della Sardegna", SardinianProvince.REGIONAL),
            (None, SardinianProvince.REGIONAL),
        ],
    )
    def test_resolve_sardinian_province(self, hint: str | None, expected: SardinianProvince) -> None:
        assert resolve_sardinian_province(hint) == expected

    @pytest.mark.parametrize(
        ("tax_id", "expected_prov", "expected_km"),
        [
            ("03811400922", "CA", 155),  # FL. Costruzioni & Servizi S.r.l. (Bolotana winner, prov CA=092)
            ("00799740915", "NU", 38),   # Edilmorittu S.r.l. (prov NU=091)
            ("01234560951", "OR", 64),   # Oristano (095)
            ("01234560902", "SS", 78),   # Sassari (090)
            ("01234560159", "EXTRA_ISOLA", 650),  # Milano (015) -> mainland contractor!
            ("MRTMSM05E17F979W", "NU", 38),  # Sole proprietor CF born/based in Nuoro (F979)
            (None, None, None),
        ],
    )
    def test_estimate_company_distance_from_tax_id(
        self, tax_id: str | None, expected_prov: str | None, expected_km: int | None
    ) -> None:
        prov, km = estimate_company_distance_from_tax_id(tax_id)
        assert prov == expected_prov
        assert km == expected_km


class TestDomainModelsAndEdilmorittuConfig:
    def test_no_demo_source_in_enum(self) -> None:
        assert "demo" not in [s.value for s in NoticeSource]

    def test_exception_hierarchy(self) -> None:
        assert issubclass(RadarNetworkError, RadarError)
        assert issubclass(UrlValidationError, RadarError)
        assert issubclass(CMEParseError, RadarError)
        assert issubclass(StorageError, RadarError)

    def test_tender_notice_v23_and_cme_items(self) -> None:
        cme_item = CMEItem(
            item_number=12,
            tariff_code="SAR26_PF.0003.0015.0002.A",
            description="Pozzetto prefabbricato in cls vibrocompresso 50x50 con griglia in ghisa",
            unit="cad.",
            quantity="8,00",
            unit_price_eur="193,04",
            total_price_eur="1´544,32",
            product_line=ProductLine.LINEA_A,
            category=CAVProductCategory.MANHOLES_CHAMBERS,
            matched_catalog_label="Pozzetti cls 50x50 + chiusini/caditoie",
        )
        assert cme_item.quantity == 8.0
        assert cme_item.total_price_eur == 1544.32

        notice = TenderNotice(
            external_id="BCB16FC2F3",
            source=NoticeSource.ANAC_OCDS,
            notice_type=NoticeType.CONTRACT_AWARD,
            title="Interventi urgenti messa in sicurezza cimitero comunale di Bolotana",
            contracting_authority="COMUNE DI BOLOTANA",
            cig="BCB16FC2F3",
            cup="I12F25000400006",
            amount_eur=187389.27,
            award_amount_eur=147411.79,
            discount_pct=21.62,
            winner_company="FL. COSTRUZIONI & SERVIZI S.R.L.",
            winner_tax_id="03811400922",
            rup_name="GIULIANO CORRIAS",
            contract_started=False,
            has_subcontracts=False,
            municipality="Bolotana",
            province="NUORO",
            url="https://dati.anticorruzione.it/opendata/dataset/cig-2026",
            http_status=200,
        )
        assert notice.winner_province == "CA"
        assert notice.winner_distance_km == 155
        assert notice.contract_started is False
        assert notice.has_subcontracts is False

        assessment = MatchAssessment(
            score=92.0,
            matched_categories=[CAVProductCategory.MANHOLES_CHAMBERS],
            matched_lines=[ProductLine.LINEA_A, ProductLine.LINEA_B],
            logistics_tier=LogisticsTier.TIER_1_CORE,
            estimated_distance_km=11,
        )
        lead = ScoredLead(
            notice=notice,
            assessment=assessment,
            cme_items=[cme_item],
            crm_status=CRMStatus.DA_CHIAMARE,
        )
        assert lead.is_high_priority is True
        assert lead.crm_status == CRMStatus.DA_CHIAMARE
        assert len(lead.cme_items) == 1

    def test_invalid_score_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            MatchAssessment(
                score=105.0,
                matched_categories=[],
                matched_keywords=[],
                logistics_tier=LogisticsTier.TIER_3_ISLAND,
            )

    def test_default_settings(self, tmp_path: Path) -> None:
        settings = RadarSettings(_env_file=None)
        assert settings.company_name == "Sardinian Precast Concrete & Construction Supplier"
        assert settings.company_piva == "00000000000"
        assert settings.company_rea == "NU-00000"
        assert settings.company_albo_artigiani == "NU-00000"
        assert settings.company_base_municipality == "Nuoro"
        assert settings.company_base_province == "NU"
        assert settings.db_path == Path("data/radar.db")
        assert settings.telegram_enabled is False
        assert settings.supabase_enabled is False
