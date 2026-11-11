from __future__ import annotations

import pytest

from sardegna_radar.matcher.cav_engine import CAVScoringEngine, compute_logistics_tier
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    LogisticsTier,
    NoticeSource,
    NoticeType,
    ProductLine,
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
            ("Nuoro", SardinianProvince.NU, LogisticsTier.TIER_1_CORE, 40),
            ("Bono", SardinianProvince.SS, LogisticsTier.TIER_1_CORE, 40),
            ("Bonorva", SardinianProvince.SS, LogisticsTier.TIER_1_CORE, 36),
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


class TestEdilmorittuCatalogScoring:
    @pytest.fixture
    def engine(self) -> CAVScoringEngine:
        return CAVScoringEngine()

    def test_linea_a_cav_pipes_and_special_precast_deliver_island_wide(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="abbanoa-ca-01",
            source=NoticeSource.SARDEGNACAT,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="Rifacimento condotta fognaria con tubi C.A.V. DN 1200, pozzetti d'ispezione e plinti portapali",
            description="Fornitura e posa tubazioni UNI EN 1916, pozzetti UNI EN 1917 e blocchi betonblock di contenimento.",
            contracting_authority="Abbanoa S.p.A.",
            cig="B102938475",
            cpv_codes=["45231300-8", "44114200-4"],
            amount_eur=850000.0,
            municipality="Cagliari",
            province=SardinianProvince.CA,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score >= 70.0
        assert ProductLine.LINEA_A in lead.assessment.matched_lines
        assert CAVProductCategory.PIPES_CULVERTS in lead.assessment.matched_categories
        assert CAVProductCategory.SPECIAL_PRECAST_CAV in lead.assessment.matched_categories
        assert lead.is_high_priority is True

    def test_linea_b_resale_scores_high_within_40km_of_silanus(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="bolotana-manut-01",
            source=NoticeSource.CUC_LOCALE,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="Messa in sicurezza edificio comunale a Macomer: impermeabilizzazione guaina, rete elettrosaldata B450C e tubi PVC SN4",
            description="Fornitura ghiaia, mattoni forati, malta per risanamento calcestruzzo e idropitture.",
            contracting_authority="Comune di Macomer",
            amount_eur=165000.0,
            municipality="Macomer",
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score >= 60.0
        assert ProductLine.LINEA_B in lead.assessment.matched_lines
        assert lead.assessment.logistics_tier == LogisticsTier.TIER_1_CORE

    def test_hard_exclusion_rejects_natural_stone_kerbs_and_paving(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="orosei-basalto-01",
            source=NoticeSource.SARDEGNACAT,
            notice_type=NoticeType.SUPPLY_TENDER,
            title="Fornitura e posa cordonate stradali in basalto e pavimentazione in lastre di marmo di Orosei e granito",
            description="Riqualificazione centro storico con cubetti in porfido e cordoli in pietra naturale.",
            contracting_authority="Comune di Orosei",
            amount_eur=240000.0,
            municipality="Orosei",
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score < 20.0
        assert CAVProductCategory.ROAD_KERBS_PAVING not in lead.assessment.matched_categories
        assert any("pietra naturale" in flag.lower() for flag in lead.assessment.negative_flags)

    def test_hard_exclusion_rejects_readymix_truck_concrete(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="cls-liquido-01",
            source=NoticeSource.SARDEGNACAT,
            notice_type=NoticeType.SUPPLY_TENDER,
            title="Accordo quadro fornitura calcestruzzo preconfezionato liquido classe S4/S5 con autobetoniera",
            description="Fornitura franco cantiere con autobetoniere e pompa per getti strutturali e platee.",
            contracting_authority="Provincia di Nuoro",
            amount_eur=300000.0,
            municipality="Nuoro",
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score < 20.0
        assert any("autobetonier" in flag.lower() or "preconfezionato" in flag.lower() for flag in lead.assessment.negative_flags)

    def test_awarded_unstarted_tender_with_cme_items_gets_top_priority(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="BCB16FC2F3",
            source=NoticeSource.ANAC_OCDS,
            notice_type=NoticeType.CONTRACT_AWARD,
            title="Interventi urgenti di messa in sicurezza del cimitero comunale di Bolotana",
            contracting_authority="COMUNE DI BOLOTANA",
            cig="BCB16FC2F3",
            amount_eur=187389.27,
            award_amount_eur=147411.79,
            discount_pct=21.62,
            winner_company="FL. COSTRUZIONI & SERVIZI S.R.L.",
            winner_tax_id="03811400922",
            rup_name="GIULIANO CORRIAS",
            contract_started=False,
            has_subcontracts=False,
            municipality="Bolotana",
            province="NU",
        )
        cme_items = [
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
            ),
            CMEItem(
                item_number=11,
                tariff_code="SAR26_PF.0008.0002.0014",
                description="Rete elettrosaldata acciaio B450C Ø10 20x20",
                unit="kg",
                quantity=2981.89,
                total_price_eur=5248.13,
                product_line=ProductLine.LINEA_B,
                category=CAVProductCategory.STEEL_REBAR_MESH,
                matched_catalog_label="Rete elettrosaldata B450C",
            ),
        ]
        lead = engine.score_notice(notice, cme_items=cme_items)
        assert lead.assessment.score >= 85.0
        assert lead.assessment.priority_unstarted_award is True
        assert "FL. COSTRUZIONI & SERVIZI S.R.L." in lead.assessment.recommended_action
        assert "03811400922" in lead.assessment.recommended_action
        assert len(lead.cme_items) == 2

    def test_artisan_and_ateco_2361_grant_scores_high(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="cciaa-nu-2026-dt",
            source=NoticeSource.CCIAA_NUORO,
            notice_type=NoticeType.REGIONAL_GRANT,
            title="Bando Doppia Transizione 2026: Contributi a fondo perduto per la digitalizzazione e la sostenibilità delle imprese",
            description="Voucher per micro, piccole e medie imprese artigiane e manifatturiere della circoscrizione CCIAA Nuoro.",
            contracting_authority="Camera di Commercio di Nuoro",
            amount_eur=10000.0,
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score >= 70.0
        assert CAVProductCategory.SME_GRANT_SUBSIDY in lead.assessment.matched_categories

    def test_pure_demolition_of_kerbs_is_excluded(self, engine: CAVScoringEngine) -> None:
        notice = TenderNotice(
            external_id="demo-kerb-01",
            source=NoticeSource.CUC_LOCALE,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="Demolizione cordoli stradali e rimozione pozzetti con conferimento a discarica",
            description="Sola demolizione e trasporto a rifiuto.",
            contracting_authority="Comune di Nuoro",
            amount_eur=45000.0,
            municipality="Nuoro",
            province=SardinianProvince.NU,
        )
        lead = engine.score_notice(notice)
        assert lead.assessment.score < 20.0
        assert lead.assessment.matched_categories == []
