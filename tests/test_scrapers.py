from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from sardegna_radar.models import NoticeSource, NoticeType, SardinianProvince
from sardegna_radar.scrapers.anac_api import ANACReverseAPIConnector
from sardegna_radar.scrapers.base import build_async_http_client
from sardegna_radar.scrapers.demo_feed import load_demo_notices
from sardegna_radar.scrapers.sardegna_portals import (
    SardegnaPortalAdaptiveScraper,
    create_scrapling_mcp_server,
)


CANONICAL_PORTAL_HTML = """
<!DOCTYPE html>
<html lang="it">
<body>
  <section id="elenco-bandi">
    <article class="bando-item" data-id="SAR-2026-101">
      <h3 class="bando-titolo">
        <a href="/portale/bandi/SAR-2026-101">Lavori di realizzazione condotta idrica e pozzetti in C.A.V. DN 800 - Lotto Silanus-Macomer</a>
      </h3>
      <div class="bando-meta">
        <span class="ente">Ente: Consorzio Industriale Provinciale Nuoro / Z.I. Macomer (NU)</span>
        <span class="cig">CIG: B778899001</span>
        <span class="cup">CUP: J34E26000110001</span>
        <span class="importo">Importo: € 680.400,00 oltre IVA</span>
        <span class="scadenza">Scadenza: 18/12/2026</span>
      </div>
      <p class="bando-descrizione">
        Fornitura e posa di tubi in calcestruzzo armato vibrocompresso, pozzetti prefabbricati d'ispezione e cordoli stradali.
      </p>
    </article>
  </section>
</body>
</html>
"""

DRIFTED_PORTAL_HTML = """
<!DOCTYPE html>
<html lang="it">
<body>
  <main class="new-portal-layout-2027">
    <div class="tender-card-wrapper" id="SAR-2026-202">
      <header>
        <a class="card-headline-link" href="https://www.sardegnacat.it/gara/SAR-2026-202">
          Ampliamento Cimitero Comunale di Bolotana (NU) - Fornitura 90 Loculi Prefabbricati in C.A.V.
        </a>
      </header>
      <ul class="card-details">
        <li>Stazione Appaltante: Comune di Bolotana (NU)</li>
        <li>Codice Gara CIG [A554433221] - Importo a base di gara € 310.000,50</li>
        <li>Termine presentazione offerte: 12/01/2027 ore 12:00</li>
      </ul>
      <div class="card-summary">
        Realizzazione blocchi colombari prefabbricati in calcestruzzo vibrocompresso certificati CE/DoP e cunette stradali.
      </div>
    </div>
  </main>
</body>
</html>
"""


class TestHTTPClientConfiguration:
    def test_build_async_http_client_timeout_and_retries(self) -> None:
        client = build_async_http_client()
        assert client.timeout.read == 15.0
        assert client.timeout.connect == 30.0
        assert "sardegna-b2b-radar" in client.headers.get("User-Agent", "").lower()


class TestANACReverseAPIConnector:
    @pytest.mark.asyncio
    async def test_fetch_releases_parses_ocds_json(self, httpx_mock: HTTPXMock) -> None:
        sample_ocds_payload = {
            "releases": [
                {
                    "ocid": "ocds-hu01ve-2026-001",
                    "id": "rel-2026-001",
                    "date": "2026-11-10T08:30:00Z",
                    "buyer": {"name": "Abbanoa S.p.A. - Distretto Idrico Nuoro"},
                    "tender": {
                        "id": "B901234567",
                        "title": "Rifacimento collettore fognario in tubi C.A.V. DN 1000 e pozzetti prefabbricati a Macomer",
                        "description": "Opere fognarie in calcestruzzo vibrocompresso con marcatura CE/DoP.",
                        "value": {"amount": 945200.50, "currency": "EUR"},
                        "tenderPeriod": {"endDate": "2026-12-22T12:00:00Z"},
                        "items": [
                            {
                                "classification": {"id": "45231300-8"},
                                "deliveryAddresses": [
                                    {"locality": "Macomer", "region": "ITG2E", "province": "NU"}
                                ],
                            }
                        ],
                    },
                    "awards": [
                        {
                            "status": "active",
                            "suppliers": [{"name": "Impresa Idraulica Sarda S.r.l."}],
                        }
                    ],
                },
                {
                    "ocid": "ocds-hu01ve-2026-non-sardegna",
                    "id": "rel-lombardia-999",
                    "buyer": {"name": "Comune di Milano"},
                    "tender": {
                        "id": "C111222333",
                        "title": "Manutenzione strade Milano",
                        "items": [
                            {
                                "classification": {"id": "45233140-2"},
                                "deliveryAddresses": [{"locality": "Milano", "region": "ITC4C"}],
                            }
                        ],
                    },
                },
            ]
        }

        endpoint = "https://dati.anticorruzione.it/opendata/ocds/api/v1/releases"
        httpx_mock.add_response(url=endpoint, json=sample_ocds_payload, status_code=200)

        connector = ANACReverseAPIConnector(endpoint_url=endpoint)
        notices = await connector.fetch_notices()

        assert len(notices) == 1
        notice = notices[0]
        assert notice.source == NoticeSource.ANAC_OCDS
        assert notice.cig == "B901234567"
        assert notice.amount_eur == 945200.50
        assert notice.municipality == "Macomer"
        assert notice.province == SardinianProvince.NU
        assert notice.winner_company == "Impresa Idraulica Sarda S.r.l."
        assert notice.notice_type == NoticeType.CONTRACT_AWARD
        assert "45231300-8" in notice.cpv_codes

        requests = httpx_mock.get_requests()
        assert len(requests) == 1


class TestSardegnaPortalAdaptiveScraper:
    def test_parse_canonical_and_drifted_dom_with_scrapling_adaptive(self, tmp_path) -> None:
        scraper = SardegnaPortalAdaptiveScraper(
            source=NoticeSource.SARDEGNACAT,
            base_url="https://www.sardegnacat.it",
            storage_dir=tmp_path / "adaptive",
        )

        # 1. Parse canonical HTML (saves adaptive fingerprints via auto_save=True)
        canonical_notices = scraper.parse_html(CANONICAL_PORTAL_HTML)
        assert len(canonical_notices) == 1
        first = canonical_notices[0]
        assert first.cig == "B778899001"
        assert first.cup == "J34E26000110001"
        assert first.amount_eur == 680400.0
        assert first.province == SardinianProvince.NU
        assert first.url == "https://www.sardegnacat.it/portale/bandi/SAR-2026-101"

        # 2. Parse drifted DOM where CSS classes and wrapper tags completely changed
        drifted_notices = scraper.parse_html(DRIFTED_PORTAL_HTML)
        assert len(drifted_notices) == 1
        second = drifted_notices[0]
        assert second.cig == "A554433221"
        assert second.amount_eur == 310000.5
        assert second.province == SardinianProvince.NU
        assert "Loculi Prefabbricati" in second.title

    @pytest.mark.asyncio
    async def test_fetch_and_parse_portal_html_over_httpx(self, httpx_mock: HTTPXMock, tmp_path) -> None:
        portal_url = "https://www.sardegnacat.it/esop/ita-ras-host/public/web/bandi.jst"
        httpx_mock.add_response(url=portal_url, text=CANONICAL_PORTAL_HTML, status_code=200)

        scraper = SardegnaPortalAdaptiveScraper(
            source=NoticeSource.SARDEGNACAT,
            base_url="https://www.sardegnacat.it",
            storage_dir=tmp_path / "adaptive",
        )
        notices = await scraper.fetch_notices(portal_url)
        assert len(notices) == 1
        assert notices[0].cig == "B778899001"

    def test_demo_feed_contains_diverse_sardinian_tenders(self) -> None:
        demo_notices = load_demo_notices()
        assert len(demo_notices) >= 6
        sources = {n.source for n in demo_notices}
        assert NoticeSource.ANAC_OCDS in sources
        assert NoticeSource.SARDEGNACAT in sources
        assert NoticeSource.RAS in sources
        assert NoticeSource.CCIAA_NUORO in sources

    def test_create_scrapling_mcp_server_helper(self) -> None:
        # Verify the MCP helper cleanly instantiates or reports optional dependency status
        server_info = create_scrapling_mcp_server(dry_run=True)
        assert server_info["cli_command"] == "scrapling mcp"
        assert server_info["host"] == "127.0.0.1"
        assert server_info["port"] == 8000
