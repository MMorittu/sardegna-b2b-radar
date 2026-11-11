from __future__ import annotations

from datetime import date
import pytest
from pytest_httpx import HTTPXMock

from sardegna_radar.models import NoticeSource, NoticeType, SardinianProvince
from sardegna_radar.scrapers.anac_api import ANACReverseAPIConnector
from sardegna_radar.scrapers.base import build_async_http_client
from sardegna_radar.scrapers.grants_ras_cciaa import GrantsConnector
from sardegna_radar.scrapers.sardegna_cat import SardegnaCATConnector
from sardegna_radar.scrapers.sardegna_portals import SardegnaPortalAdaptiveScraper

SAMPLE_SCAT_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:afs="http://www.aflink.it/XMLBANDI">
<channel>
<afs:totRecord>2</afs:totRecord>
<item>
  <title><![CDATA[Bando]]></title>
  <link><![CDATA[https://sardegnacat.regione.sardegna.it/portale/index.php/bandi?getdettaglio=yes&bando=109901&tipobando=Bando&RicQ=YES&VisQ=SI&tipoDoc=BANDO_GARA_PORTALE&xslt=XSLT_BANDO_GARA_PORTALE]]></link>
  <pubDate>10/11/2026</pubDate>
  <afs:Oggetto><![CDATA[Lavori di rifacimento condotta acque bianche con tubi C.A.V. e pozzetti a Macomer (NU) - CUP: J12B26000450002]]></afs:Oggetto>
  <afs:Tipo><![CDATA[Bando]]></afs:Tipo>
  <afs:EnteProponente><![CDATA[Comune di Macomer]]></afs:EnteProponente>
  <afs:Contratto><![CDATA[Lavori]]></afs:Contratto>
  <afs:a_base_asta><![CDATA[420.500,00]]></afs:a_base_asta>
  <afs:DtScadenzaBandoTecnical><![CDATA[2026-12-15T13:00:00]]></afs:DtScadenzaBandoTecnical>
  <afs:CIG><![CDATA[B49102F8AC]]></afs:CIG>
  <afs:TipoDocOriginal><![CDATA[BANDO_GARA]]></afs:TipoDocOriginal>
  <afs:IdMsg><![CDATA[109901]]></afs:IdMsg>
  <afs:bEsito><![CDATA[0]]></afs:bEsito>
  <afs:CPV><![CDATA[45231300-8 - Lavori di costruzione di condotte idriche e fognarie]]></afs:CPV>
  <afs:DtPubblicazioneTecnical><![CDATA[2026-11-10T00:00:00]]></afs:DtPubblicazioneTecnical>
</item>
<item>
  <title><![CDATA[Bando]]></title>
  <link><![CDATA[https://sardegnacat.regione.sardegna.it/portale/index.php/bandi?bando=109902]]></link>
  <afs:Oggetto><![CDATA[Servizio di pulizia uffici regionali]]></afs:Oggetto>
  <afs:Tipo><![CDATA[Bando]]></afs:Tipo>
  <afs:Contratto><![CDATA[Servizi]]></afs:Contratto>
  <afs:IdMsg><![CDATA[109902]]></afs:IdMsg>
</item>
</channel>
</rss>
"""


class TestHTTPClientConfiguration:
    def test_build_async_http_client_uses_browser_compatible_ua(self) -> None:
        client = build_async_http_client()
        assert client.timeout.read == 20.0
        assert client.timeout.connect == 30.0
        assert "Mozilla/5.0" in client.headers.get("User-Agent", "")


class TestSardegnaCATConnector:
    def test_parses_xml_rewrites_broken_portale_url_and_builds_zip_attachment_url(self) -> None:
        connector = SardegnaCATConnector()
        notices = connector.parse_rss_xml(SAMPLE_SCAT_RSS_XML)

        # Must keep Lavori and drop pure Servizi
        assert len(notices) == 1
        n = notices[0]
        assert n.source == NoticeSource.SARDEGNACAT
        assert n.notice_type == NoticeType.PUBLIC_WORKS_TENDER
        assert n.cig == "B49102F8AC"
        assert n.cup == "J12B26000450002"
        assert n.amount_eur == 420500.0
        assert n.province == SardinianProvince.NU
        assert "/portalegare/index.php/bandi" in n.url
        assert "/portale/index.php/" not in n.url
        assert n.attachment_url is not None
        assert "DownloadAttach.asp" in n.attachment_url
        assert "IDDOC=109901" in n.attachment_url
        assert n.cpv_codes == ["45231300-8"]
        assert n.deadline_date == date(2026, 12, 15)


class TestGrantsAndCUCPortals:
    @pytest.mark.asyncio
    async def test_ras_graphql_parses_published_grants(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://graphql-prod.regione.sardegna.it/graphql/",
            method="POST",
            json={
                "data": {
                    "getContents": [
                        {
                            "_id": "ras-901",
                            "slug": "bando-artigiani-2026",
                            "titolo": "Contributi a fondo perduto per investimenti produttivi imprese artigiane (ATECO 23)",
                            "breve": "Agevolazioni per acquisto macchinari e stampi.",
                            "oggetto": "",
                            "descrizione": "Bando regionale destinato alle imprese iscritte all'Albo Artigiani della Sardegna.",
                            "dataPubblicazione": "2026-11-02",
                            "dataScadenza": "2027-01-31",
                            "cig": None,
                            "cup": "E78I26000120002",
                            "tipologia": "Bandi per le imprese",
                        }
                    ]
                }
            },
        )
        connector = GrantsConnector()
        notices = await connector.fetch_ras_grants()
        assert len(notices) == 1
        assert notices[0].source == NoticeSource.RAS
        assert notices[0].notice_type == NoticeType.REGIONAL_GRANT
        assert notices[0].url == "https://www.regione.sardegna.it/atti-bandi-archivi/atti-amministrativi/bandi/bando-artigiani-2026"
        assert notices[0].cup == "E78I26000120002"

    def test_cciaa_nuoro_html_extracts_grant_links(self) -> None:
        sample_cciaa_html = """
        <html><body><main id="main">
          <ul>
            <li>
              <a href="/it/camera/bandi/contributi-attivita-promozionali/bando-doppia-transizione-2026/">
                Bando Doppia Transizione 2026: Contributi a fondo perduto per la digitalizzazione e la sostenibilità delle imprese
              </a>
            </li>
          </ul>
        </main></body></html>
        """
        connector = GrantsConnector()
        notices = connector.parse_cciaa_nuoro_html(sample_cciaa_html)
        assert len(notices) == 1
        assert notices[0].source == NoticeSource.CCIAA_NUORO
        assert notices[0].notice_type == NoticeType.REGIONAL_GRANT
        assert notices[0].url.startswith("https://nu.camcom.it/")

    def test_cuc_municipium_html_extracts_tender_documents(self) -> None:
        cuc_html = """
        <html><body><main>
          <div class="card">
            <a href="/it/documenti/bando-cimitero-bolotana-bcb16fc2f3">
              Procedura aperta lavori messa in sicurezza cimitero di Bolotana - CIG BCB16FC2F3 - € 187.389,27
            </a>
          </div>
        </main></body></html>
        """
        scraper = SardegnaPortalAdaptiveScraper(
            source=NoticeSource.CUC_LOCALE,
            base_url="https://comunitamontananuorese.it",
        )
        notices = scraper.parse_html(cuc_html, page_url="https://comunitamontananuorese.it/it/amministrazione/documenti/albo/atti/bando-di-gara")
        assert len(notices) == 1
        assert notices[0].cig == "BCB16FC2F3"
        assert notices[0].url == "https://comunitamontananuorese.it/it/documenti/bando-cimitero-bolotana-bcb16fc2f3"

    @pytest.mark.asyncio
    async def test_anac_ocds_legacy_json_still_parses(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://example.org/ocds.json",
            json={
                "releases": [
                    {
                        "id": "rel-1",
                        "date": "2026-11-10T08:00:00Z",
                        "buyer": {"name": "Comune di Silanus"},
                        "tender": {
                            "id": "B901234567",
                            "title": "Fornitura tubi C.A.V. DN 800 a Silanus",
                            "value": {"amount": 150000.0},
                            "items": [{"classification": {"id": "45231300-8"}, "deliveryAddresses": [{"locality": "Silanus", "region": "ITG2E"}]}],
                        },
                    }
                ]
            },
        )
        connector = ANACReverseAPIConnector(endpoint_url="https://example.org/ocds.json")
        notices = await connector.fetch_notices()
        assert len(notices) == 1
        assert notices[0].cig == "B901234567"
