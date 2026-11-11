from __future__ import annotations

import json
from pathlib import Path
import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from sardegna_radar.cli import app
from sardegna_radar.config import RadarSettings
from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    CRMStatus,
    NoticeSource,
    NoticeType,
    ProductLine,
    ScoredLead,
    TenderNotice,
)
from sardegna_radar.notifiers.telegram import (
    TelegramNotifier,
    format_lead_telegram_html,
    format_lead_whatsapp_text,
    render_markdown_digest,
)
from sardegna_radar.storage.repository import RadarRepository

runner = CliRunner()

BOLOTANA_ANAC_JSON = Path(r"C:\Users\Massimiliano\Desktop\CIG_BCB16FC2F3.json")
BOLOTANA_CME_PDF = Path(
    r"C:\Users\Massimiliano\Desktop\PROGETTO_ESECUTIVO\PROGETTO_ESECUTIVO_pdf"
    r"\PE_All.B_Computo metrico-quadro economico_signed.pdf"
)
PORTABLE_ANAC_JSON = Path(__file__).parent / "fixtures" / "sample_anac_v23.json"
PORTABLE_CME_PDF = Path(__file__).parent / "fixtures" / "sample_cme.pdf"


def _sample_bolotana_lead() -> ScoredLead:
    notice = TenderNotice(
        external_id="BCB16FC2F3",
        source=NoticeSource.ANAC_OCDS,
        notice_type=NoticeType.CONTRACT_AWARD,
        title="Lavori di messa in sicurezza urgente del cimitero del Comune di Bolotana",
        contracting_authority="COMUNE DI BOLOTANA",
        delegated_authority="COMUNITA MONTANA NUORESE",
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
        province="NU",
        url="https://dati.anticorruzione.it/superset/dashboard/dettaglio_cig/?cig=BCB16FC2F3",
        http_status=200,
    )
    items = [
        CMEItem(
            item_number=12,
            tariff_code="SAR26_PF.0003.0015.0002.A",
            description="Pozzetto prefabbricato in cls vibrocompresso 50x50 con griglia ghisa",
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
            description="Rete elettrosaldata acciaio B450C Ø10 maglia 20x20",
            unit="kg",
            quantity=2981.89,
            total_price_eur=5248.13,
            product_line=ProductLine.LINEA_B,
            category=CAVProductCategory.STEEL_REBAR_MESH,
            matched_catalog_label="Rete elettrosaldata B450C",
        ),
    ]
    return CAVScoringEngine().score_notice(notice, cme_items=items)


class TestUltraCompactFormattersAndNotifier:
    def test_telegram_and_whatsapp_include_winner_piva_rup_state_and_exact_cme_measures(self) -> None:
        lead = _sample_bolotana_lead()
        tg = format_lead_telegram_html(lead)
        wa = format_lead_whatsapp_text(lead)

        for rendered in (tg, wa):
            assert "BCB16FC2F3" in rendered
            assert "FL. COSTRUZIONI" in rendered
            assert "03811400922" in rendered
            assert "147.411,79" in rendered
            assert "21,62%" in rendered
            assert "GIULIANO CORRIAS" in rendered
            assert "NON AVVIATO" in rendered
            assert "8,00 cad." in rendered
            assert "2.981,89 kg" in rendered

    @pytest.mark.asyncio
    async def test_dispatch_leads_sends_telegram_webhook_with_httpx_mock(
        self,
        httpx_mock: HTTPXMock,
        temp_db_path: Path,
    ) -> None:
        settings = RadarSettings(
            _env_file=None,
            db_path=temp_db_path,
            telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            telegram_chat_id="-100987654321",
        )
        expected_url = "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage"
        httpx_mock.add_response(url=expected_url, json={"ok": True, "result": {"message_id": 42}})

        lead = _sample_bolotana_lead()
        notifier = TelegramNotifier(settings=settings)
        sent_keys = await notifier.dispatch_leads([lead])

        assert sent_keys == [lead.dedup_key]
        req = httpx_mock.get_request(method="POST", url=expected_url)
        assert req is not None
        body = json.loads(req.content.decode("utf-8"))
        assert body["chat_id"] == "-100987654321"
        assert "BCB16FC2F3" in body["text"]

    @pytest.mark.asyncio
    async def test_offline_safety_when_telegram_unset(self, httpx_mock: HTTPXMock, temp_db_path: Path) -> None:
        settings = RadarSettings(_env_file=None, db_path=temp_db_path, telegram_bot_token="", telegram_chat_id="")
        lead = _sample_bolotana_lead()
        sent = await TelegramNotifier(settings=settings).dispatch_leads([lead])
        assert sent == []
        assert len(httpx_mock.get_requests()) == 0
        digest = render_markdown_digest([lead])
        assert "Sardinian Precast & Construction Supplier" in digest
        assert "2.981,89 kg" in digest


class TestTyperCLI:
    def test_demo_flag_is_removed(self, tmp_path: Path) -> None:
        res = runner.invoke(app, ["scan", "--demo", "--db-path", str(tmp_path / "r.db")])
        assert res.exit_code != 0

    def test_parse_cme_save_requires_validated_url_when_no_anac_json(self, tmp_path: Path) -> None:
        res = runner.invoke(
            app,
            ["parse-cme", str(PORTABLE_CME_PDF), "--save", "--db-path", str(tmp_path / "r.db")],
        )
        assert res.exit_code != 0

    def test_cli_parse_cme_set_status_leads_stats_and_export(
        self, tmp_path: Path, httpx_mock: HTTPXMock
    ) -> None:
        cme_target = BOLOTANA_CME_PDF if BOLOTANA_CME_PDF.exists() else PORTABLE_CME_PDF
        anac_target = BOLOTANA_ANAC_JSON if BOLOTANA_ANAC_JSON.exists() else PORTABLE_ANAC_JSON
        db_file = tmp_path / "radar.db"
        digest_file = tmp_path / "leads_digest.md"

        httpx_mock.add_response(
            url="https://dati.anticorruzione.it/superset/dashboard/dettaglio_cig/?cig=BCB16FC2F3",
            status_code=200,
            text="<html><body>Dettaglio CIG BCB16FC2F3</body></html>",
        )

        # 1. parse-cme paired with real ANAC v2.3 JSON and saved to SQLite
        res_cme = runner.invoke(
            app,
            [
                "parse-cme",
                str(cme_target),
                "--anac-json",
                str(anac_target),
                "--save",
                "--db-path",
                str(db_file),
            ],
        )
        assert res_cme.exit_code == 0, res_cme.stdout
        assert "BCB16FC2F3" in res_cme.stdout
        assert "8,00" in res_cme.stdout

        # 2. set-status CRM command
        res_crm = runner.invoke(
            app,
            ["set-status", "BCB16FC2F3", "preventivo_inviato", "--db-path", str(db_file)],
        )
        assert res_crm.exit_code == 0
        repo = RadarRepository(db_file)
        saved = repo.list_leads(min_score=0.0)[0]
        assert saved.crm_status == CRMStatus.PREVENTIVO_INVIATO

        # 3. leads & stats & export
        res_leads = runner.invoke(app, ["leads", "--db-path", str(db_file), "--min-score", "45"])
        assert res_leads.exit_code == 0
        assert "BCB16FC2F3" in res_leads.stdout

        res_stats = runner.invoke(app, ["stats", "--db-path", str(db_file)])
        assert res_stats.exit_code == 0
        assert "Sardinian Precast" in res_stats.stdout
        assert "00000000000" in res_stats.stdout

        res_exp = runner.invoke(
            app,
            ["export", "--output", str(digest_file), "--db-path", str(db_file)],
        )
        assert res_exp.exit_code == 0
        assert digest_file.exists()
        md = digest_file.read_text(encoding="utf-8")
        assert "FL. COSTRUZIONI & SERVIZI S.R.L." in md
        assert "03811400922" in md
