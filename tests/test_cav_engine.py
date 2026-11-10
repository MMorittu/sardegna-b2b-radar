from __future__ import annotations

import pytest

from sardegna_radar.matcher.cav_engine import CAVScoringEngine, compute_logistics_tier
from sardegna_radar.models import (
    CAVProductCategory,
    LogisticsTier,
    NoticeSource,
    NoticeType,
    SardinianProvince,
    TenderNotice,
)


class TestSilanusLogisticsTiering:
    @pytest.mark.parametrize(
        ("municipality", "province", "expected_tier", "max_km"),
        [
            ("Silanus", SardinianProvince.NU, LogisticsTier.TIER_1_CORE, 5),
            ("Macomer", SardinianProvince.NU, LogisticsTier.TIER_1_CORE, 20),
            ("Bolotana", SardinianProvince.NU, LogisticsTier.TIER_1_CORE, 20),
            ("Ghilarza", SardinianProvince.OR, LogisticsTier.TIER_1_CORE, 40),
            ("Nuoro", SardinianProvince.NU, LogisticsTier.TIER_1_CORE, 45),
            ("Bono", SardinianProvince.SS, LogisticsTier.TIER_1_CORE, 40),
            ("Sassari", SardinianProvince.SS, LogisticsTier.TIER_2_CENTRAL, 100),
            ("Oristano", SardinianProvince.OR, LogisticsTier.TIER_2_CENTRAL, 100),
            ("Olbia", SardinianProvince.SS, LogisticsTier.TIER_3_ISLAND, 150),
            ("Cagliari", SardinianProvince.CA, LogisticsTier.TIER_3_ISLAND, 200),
            ("Carbonia", SardinianProvince.SU, LogisticsTier.TIER_3_ISLAND, 220),
        ],
    )
    def test_compute_logistics_tier(
        self,
        municipality: str,
        province: SardinianProvince,
        expected_tier: LogisticsTier,
        max_km: int,
    ) -> None:
        tier, distance_km = compute_logistics_tier(municipality, province)
        assert tier == expected_tier
        assert distance_km is not None
        assert distance_km <= max_km


class TestCAVScoringEngine:
    @pytest.fixture
    def engine(self) -> CAVScoringEngine:
        return CAVScoringEngine()

    def test_high_score_aqueduct_sewage_cav_tender(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="abbanoa-01",
            source=NoticeSource.SARDEGNACAT,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="Lavori di rifacimento collettore fognario e condotta idrica in tubi C.A.V. e pozzetti prefabbricati",
            description=(
                "Fornitura e posa in opera di tubazioni in calcestruzzo armato vibrocompresso "
                "DN 600/800 con marcatura CE e DoP, chiusini, caditoie stradali e camere d'ispezione."
            ),
            contracting_authority="Abbanoa S.p.A.",
            cig="B102938475",
            cpv_codes=["45231300-8", "44114200-4"],
            amount_eur=850000.0,
            municipality="Macomer",
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score >= 85.0
        assert CAVProductCategory.PIPES_CULVERTS in lead.assessment.matched_categories
        assert CAVProductCategory.MANHOLES_CHAMBERS in lead.assessment.matched_categories
        assert lead.assessment.cpv_bonus_applied is True
        assert lead.assessment.logistics_tier == LogisticsTier.TIER_1_CORE
        assert lead.is_high_priority is True

    def test_high_score_cemetery_expansion_loculi(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="comune-bolotana-cim",
            source=NoticeSource.ANAC_OCDS,
            notice_type=NoticeType.CONTRACT_AWARD,
            title="Aggiudicazione lavori di ampliamento cimitero comunale - realizzazione 120 loculi prefabbricati in C.A.V.",
            description="Costruzione nuovo blocco colombari, ossari e cordoli perimetrali in calcestruzzo.",
            contracting_authority="Comune di Bolotana",
            cig="A998877665",
            cpv_codes=["45215400-1"],
            amount_eur=295000.0,
            municipality="Bolotana",
            province=SardinianProvince.NU,
            winner_company="Impresa Costruzioni Generali Sarda S.r.l.",
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score >= 80.0
        assert CAVProductCategory.CEMETERY_NICHES in lead.assessment.matched_categories
        assert "Impresa Costruzioni Generali Sarda S.r.l." in lead.assessment.recommended_action

    def test_high_score_road_kerbs_and_drainage(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="anas-ss131",
            source=NoticeSource.ANAC_OCDS,
            title="Manutenzione straordinaria SS 131 - posa cordoli stradali, cunette alla francese e pozzetti di raccolta acque",
            description="Opere idrauliche di piattaforma stradale con elementi prefabbricati in calcestruzzo vibrocompresso.",
            contracting_authority="ANAS S.p.A. - Struttura Territoriale Sardegna",
            cpv_codes=["45233140-2"],
            amount_eur=1450000.0,
            municipality="Abbasanta",
            province=SardinianProvince.OR,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score >= 75.0
        assert CAVProductCategory.ROAD_KERBS_PAVING in lead.assessment.matched_categories
        assert lead.assessment.logistics_tier == LogisticsTier.TIER_1_CORE

    def test_regional_sme_grant_scores_high(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="cciaa-nu-pid-2026",
            source=NoticeSource.CCIAA_NUORO,
            notice_type=NoticeType.REGIONAL_GRANT,
            title="Bando Voucher Digitali I4.0 PID 2026 - Contributi a fondo perduto 68% per PMI del Nuorese",
            description=(
                "Agevolazioni SIPES / RAS e Camera di Commercio di Nuoro per transizione digitale, "
                "automazione impianti industriali, software gestionale e fotovoltaico."
            ),
            contracting_authority="CCIAA Nuoro",
            amount_eur=15000.0,
            municipality="Nuoro",
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score >= 65.0
        assert CAVProductCategory.SME_GRANT_SUBSIDY in lead.assessment.matched_categories

    @pytest.mark.parametrize(
        ("title", "description"),
        [
            (
                "Fornitura biennale di tubi endotracheali ospedalieri, cateteri e dispositivi medici sterili",
                "Gara telematica ASL Nuoro per fornitura presidi chirurgici e reagenti di laboratorio.",
            ),
            (
                "Acquisto licenze software cloud, blocchi appunti cartacei e servizio mensa scolastica",
                "Fornitura materiale di cancelleria e ristorazione collettiva per istituti comprensivi.",
            ),
            (
                "Servizio di pulizia locali comunali e manutenzione del verde pubblico",
                "Affidamento biennale spazzamento e derattizzazione uffici.",
            ),
        ],
    )
    def test_false_positive_medical_and_unrelated_tenders_score_below_20(
        self,
        engine: CAVScoringEngine,
        title: str,
        description: str,
    ) -> None:
        notice = TenderNotice(
            external_id="neg-01",
            source=NoticeSource.SARDEGNACAT,
            title=title,
            description=description,
            contracting_authority="ARES Sardegna",
            municipality="Nuoro",
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score < 20.0
        assert lead.is_high_priority is False
