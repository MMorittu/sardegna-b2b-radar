"""Realistic Sardinian B2B procurement & regional grant dataset for offline/demo runs."""

from __future__ import annotations

from sardegna_radar.models import (
    NoticeSource,
    NoticeType,
    SardinianProvince,
    TenderNotice,
)


def load_demo_notices() -> list[TenderNotice]:
    """Return a curated batch of realistic Sardinian tenders, contract awards, grants, and false positives."""
    return [
        TenderNotice(
            external_id="SARDEGNACAT-2026-8841",
            source=NoticeSource.SARDEGNACAT,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="Lavori di rifacimento collettore fognario intercomunale e condotta idrica in tubi C.A.V. DN 800 - Lotto Marghine",
            description=(
                "Fornitura e posa in opera di tubazioni in calcestruzzo armato vibrocompresso (C.A.V.) "
                "con giunto a bicchiere e guarnizione elastomerica certificati CE/DoP, pozzetti prefabbricati "
                "d'ispezione, caditoie stradali e chiusini in ghisa."
            ),
            contracting_authority="Abbanoa S.p.A. - Distretto n. 5 Nuoro",
            cig="B409182736",
            cup="J18B26000410005",
            cpv_codes=["45231300-8", "44114200-4"],
            amount_eur="€ 1.180.500,00 oltre IVA",
            published_date="08/11/2026",
            deadline_date="18/12/2026",
            municipality="Macomer",
            province=SardinianProvince.NU,
            url="https://www.sardegnacat.it/esop/ita-ras-host/public/web/bandi/B409182736",
        ),
        TenderNotice(
            external_id="ANAC-OCDS-2026-5512",
            source=NoticeSource.ANAC_OCDS,
            notice_type=NoticeType.CONTRACT_AWARD,
            title="Aggiudicazione definitiva: Ampliamento Cimitero Comunale - Realizzazione 140 Loculi Prefabbricati in C.A.V. e Ossari",
            description=(
                "Opere di edilizia cimiteriale con fornitura di loculi prefabbricati in calcestruzzo "
                "vibrocompresso armato, blocchi vibrocompressi per murature perimetrali e cordoli."
            ),
            contracting_authority="Comune di Bolotana (NU)",
            cig="A837465910",
            cup="F45I26000190004",
            cpv_codes=["45215400-1", "44114200-4"],
            amount_eur="€ 342.000,00",
            published_date="09/11/2026",
            deadline_date="30/11/2026",
            municipality="Bolotana",
            province=SardinianProvince.NU,
            winner_company="Impresa Edile Gennargentu Costruzioni S.r.l.",
            url="https://dati.anticorruzione.it/superset/dashboard/dettaglio_cig/?cig=A837465910",
        ),
        TenderNotice(
            external_id="ANAC-OCDS-2026-6104",
            source=NoticeSource.ANAC_OCDS,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="SS 131 Carlo Felice - Adeguamento idraulico piattaforma stradale, posa cordoli stradali, cunette alla francese e pozzetti",
            description=(
                "Manutenzione straordinaria opere idrauliche lungo la SS 131 tra Abbasanta e Paulilatino "
                "mediante manufatti prefabbricati in calcestruzzo vibrocompresso, scatolari e pozzetti raccolta acque."
            ),
            contracting_authority="ANAS S.p.A. - Struttura Territoriale Sardegna",
            cig="B718293045",
            cup="I97H26000880001",
            cpv_codes=["45233140-2", "44114200-4"],
            amount_eur="€ 890.000,00",
            published_date="10/11/2026",
            deadline_date="22/12/2026",
            municipality="Abbasanta",
            province=SardinianProvince.OR,
            url="https://dati.anticorruzione.it/superset/dashboard/dettaglio_cig/?cig=B718293045",
        ),
        TenderNotice(
            external_id="RAS-URB-2026-309",
            source=NoticeSource.RAS,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title="Completamento opere di urbanizzazione primaria, sottoservizi, rete acque bianche e blocchi in calcestruzzo Z.I. Pratosardo",
            description=(
                "Realizzazione rete drenaggio acque meteoriche con tubi C.A.V. DN 600, "
                "pozzetti d'ispezione, marciapiedi con cordoli in calcestruzzo e murature in blocchi vibrocompressi."
            ),
            contracting_authority="Consorzio Industriale Provinciale di Nuoro (CIP Nuoro)",
            cig="B654321098",
            cup="D21B26000330002",
            cpv_codes=["45232410-9"],
            amount_eur="€ 520.000,00",
            published_date="07/11/2026",
            deadline_date="14/12/2026",
            municipality="Nuoro",
            province=SardinianProvince.NU,
            url="https://www.regione.sardegna.it/atti/bando-pratosardo-2026",
        ),
        TenderNotice(
            external_id="CCIAA-NU-PID-2026-02",
            source=NoticeSource.CCIAA_NUORO,
            notice_type=NoticeType.REGIONAL_GRANT,
            title="Bando Voucher Digitali I4.0 PID 2026 - Contributi a fondo perduto 68% per PMI manifatturiere del Nuorese",
            description=(
                "Agevolazioni a fondo perduto Camera di Commercio di Nuoro e portale SIPES / RAS per "
                "transizione digitale, automazione impianti di betonaggio e vibrocompressione, ERP e cybersecurity."
            ),
            contracting_authority="Camera di Commercio di Nuoro (CCIAA Nuoro)",
            amount_eur="€ 20.000,00",
            published_date="05/11/2026",
            deadline_date="31/12/2026",
            municipality="Nuoro",
            province=SardinianProvince.NU,
            url="https://www.nu.camcom.it/bandi/voucher-digitali-pid-2026",
        ),
        TenderNotice(
            external_id="SARDEGNACAT-MED-9901",
            source=NoticeSource.SARDEGNACAT,
            notice_type=NoticeType.SUPPLY_TENDER,
            title="Fornitura triennale di tubi endotracheali ospedalieri, cateteri sterili e dispositivi medici per ASL Nuoro",
            description="Procedura aperta telematica per la fornitura di presidi chirurgici e reagenti diagnostici.",
            contracting_authority="ARES Sardegna - ASL n. 3 Nuoro",
            cig="C009988776",
            amount_eur="€ 410.000,00",
            published_date="10/11/2026",
            deadline_date="15/12/2026",
            municipality="Nuoro",
            province=SardinianProvince.NU,
            url="https://www.sardegnacat.it/esop/ita-ras-host/public/web/bandi/C009988776",
        ),
        TenderNotice(
            external_id="RAS-SCHOOL-1102",
            source=NoticeSource.RAS,
            notice_type=NoticeType.SUPPLY_TENDER,
            title="Servizio di ristorazione collettiva, mensa scolastica e fornitura blocchi appunti cancelleria",
            description="Affidamento servizio refezione scolastica e fornitura materiale cartaceo.",
            contracting_authority="Comune di Sassari",
            cig="C112233449",
            amount_eur="€ 195.000,00",
            published_date="09/11/2026",
            deadline_date="10/12/2026",
            municipality="Sassari",
            province=SardinianProvince.SS,
            url="https://www.regione.sardegna.it/atti/mensa-sassari-2026",
        ),
    ]
