from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from sardegna_radar.exceptions import UrlValidationError
from sardegna_radar.models import NoticeSource, TenderNotice
from sardegna_radar.scrapers.url_validator import HttpUrlValidator


@pytest.mark.asyncio
class TestHttpUrlValidator:
    async def test_accepts_valid_http_200_and_records_final_url(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://sardegnacat.regione.sardegna.it/portalegare/index.php/bandi?bando=100588",
            status_code=200,
            text="<html><body>" + ("Dettaglio Bando di Gara Lavori C.A.V. " * 20) + "</body></html>",
        )
        notice = TenderNotice(
            external_id="100588",
            source=NoticeSource.SARDEGNACAT,
            title="Lavori condotta idrica C.A.V.",
            url="https://sardegnacat.regione.sardegna.it/portalegare/index.php/bandi?bando=100588",
        )
        validator = HttpUrlValidator()
        validated = await validator.validate_notice(notice)
        assert validated.http_status == 200

    async def test_rejects_http_404(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://www.sardegnacat.it/esop/broken-404",
            status_code=404,
            text="Not Found",
        )
        notice = TenderNotice(
            external_id="broken-1",
            source=NoticeSource.SARDEGNACAT,
            title="Bando con link rotto 404",
            url="https://www.sardegnacat.it/esop/broken-404",
        )
        validator = HttpUrlValidator()
        with pytest.raises(UrlValidationError):
            await validator.validate_notice(notice)

    async def test_rejects_soft_404_returning_200_with_portal_error_banner(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://sardegnacat.regione.sardegna.it/portalegare/index.php/bandi?getdettaglio=yes&bando=824862",
            status_code=200,
            text="<html><body><div class='alert'>Errore restituito dal webServices di dettaglio</div></body></html>",
        )
        notice = TenderNotice(
            external_id="824862",
            source=NoticeSource.SARDEGNACAT,
            title="Bando con soft-404 webServices",
            url="https://sardegnacat.regione.sardegna.it/portalegare/index.php/bandi?getdettaglio=yes&bando=824862",
        )
        validator = HttpUrlValidator()
        valid_list = await validator.filter_valid_notices([notice])
        assert valid_list == []
