from __future__ import annotations

from datetime import date
from pathlib import Path
import pytest

from sardegna_radar.models import NoticeSource, NoticeType, SardinianProvince
from sardegna_radar.scrapers.anac_api import ANACReverseAPIConnector

BOLOTANA_ANAC_V23_JSON = Path(r"C:\Users\Massimiliano\Desktop\CIG_BCB16FC2F3.json")
PORTABLE_ANAC_V23_FIXTURE = Path(__file__).parent / "fixtures" / "sample_anac_v23.json"


class TestANACAppaltoV23Bolotana:
    def test_parses_bolotana_appalto_v23_ground_truth(self) -> None:
        target = BOLOTANA_ANAC_V23_JSON if BOLOTANA_ANAC_V23_JSON.exists() else PORTABLE_ANAC_V23_FIXTURE
        connector = ANACReverseAPIConnector()
        notice = connector.parse_appalto_v23_file(target)

        assert notice is not None
        assert notice.source == NoticeSource.ANAC_OCDS
        assert notice.notice_type == NoticeType.CONTRACT_AWARD
        assert notice.cig == "BCB16FC2F3"
        assert notice.cup == "I12F25000400006"
        assert notice.contracting_authority == "COMUNE DI BOLOTANA"
        assert notice.delegated_authority == "COMUNITA MONTANA NUORESE GENNARGENTU SUPRAMONTE BARBAGIA"
        assert notice.municipality == "BOLOTANA"
        assert notice.province == SardinianProvince.NU
        assert notice.amount_eur == pytest.approx(187389.27)
        assert notice.award_amount_eur == pytest.approx(147411.79)
        assert notice.discount_pct == pytest.approx(21.62)
        assert notice.award_date == date(2026, 10, 15)
        assert notice.winner_company == "FL. COSTRUZIONI & SERVIZI S.R.L."
        assert notice.winner_tax_id == "03811400922"
        assert notice.winner_province == "CA"
        assert notice.winner_distance_km == 155
        assert notice.rup_name == "GIULIANO CORRIAS"
        assert notice.contract_started is False
        assert notice.has_subcontracts is False
        assert "45215400" in notice.cpv_codes

    def test_joins_ckan_jsonl_streams_for_sardinian_works(self) -> None:
        connector = ANACReverseAPIConnector()
        cig_rows = [
            {
                "cig": "BCB16FC2F3",
                "oggetto_gara": "LAVORI DI MESSA IN SICUREZZA CIMITERO DI BOLOTANA CUP: I12F25000400006",
                "importo_complessivo_gara": 187389.27,
                "oggetto_principale_contratto": "LAVORI",
                "provincia": "NUORO",
                "sezione_regionale": "SEZIONE REGIONALE SARDEGNA",
                "data_pubblicazione": "2026-08-12",
                "data_scadenza_offerta": "2026-09-15",
                "DENOMINAZIONE_SA_DELEGANTE": "COMUNE DI BOLOTANA",
                "DENOMINAZIONE_SA_DELEGATA": "COMUNITA MONTANA NUORESE",
                "cod_cpv": "45215400-1",
                "ESITO": "AGGIUDICATA",
            },
            {
                "cig": "BAAE8FBBAC",
                "oggetto_gara": "SERVIZIO SOCIAL MEDIA VENEZIA",
                "importo_complessivo_gara": 15400.0,
                "oggetto_principale_contratto": "SERVIZI",
                "provincia": "VENEZIA",
                "sezione_regionale": "SEZIONE REGIONALE VENETO",
            },
        ]
        awards_by_cig = {
            "BCB16FC2F3": {
                "importo_aggiudicazione": 147411.79,
                "ribasso_aggiudicazione": 21.62,
                "data_aggiudicazione_definitiva": "2026-10-15",
            }
        }
        winners_by_cig = {
            "BCB16FC2F3": {
                "denominazione": "FL. COSTRUZIONI & SERVIZI S.R.L.",
                "codice_fiscale": "03811400922",
            }
        }
        started_cigs: set[str] = set()
        subcontract_cigs: set[str] = set()

        notices = connector.join_ckan_records(
            cig_rows,
            awards_by_cig=awards_by_cig,
            winners_by_cig=winners_by_cig,
            started_cigs=started_cigs,
            subcontract_cigs=subcontract_cigs,
        )
        assert len(notices) == 1
        n = notices[0]
        assert n.cig == "BCB16FC2F3"
        assert n.cup == "I12F25000400006"
        assert n.winner_tax_id == "03811400922"
        assert n.winner_distance_km == 155
        assert n.contract_started is False
        assert n.has_subcontracts is False
