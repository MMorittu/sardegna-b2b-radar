from __future__ import annotations

import json
from pathlib import Path
import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from sardegna_radar.cli import app
from sardegna_radar.config import RadarSettings
from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.notifiers.telegram import (
    TelegramNotifier,
    format_lead_telegram_html,
    render_markdown_digest,
)
from sardegna_radar.scrapers.demo_feed import load_demo_notices


runner = CliRunner()


class TestTelegramNotifier:
    def test_format_lead_telegram_html_contains_cav_and_logistics(self) -> None:
        engine = CAVScoringEngine()
        lead = engine.score_notice(load_demo_notices()[0])
        html_msg = format_lead_telegram_html(lead)

        assert "B409182736" in html_msg
        assert "Macomer" in html_msg
        assert "1.180.500,00" in html_msg
        assert "Tubi C.A.V." in html_msg
        assert "Tier 1" in html_msg

    @pytest.mark.asyncio
    async def test_dispatch_leads_sends_telegram_webhook_with_httpx_mock(
        self,
        httpx_mock: HTTPXMock,
        temp_db_path: Path,
    ) -> None:
        settings = RadarSettings(
            db_path=temp_db_path,
            telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            telegram_chat_id="-100987654321",
        )
        expected_url = (
            "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage"
        )
        httpx_mock.add_response(url=expected_url, json={"ok": True, "result": {"message_id": 42}})

        engine = CAVScoringEngine()
        lead = engine.score_notice(load_demo_notices()[0])

        notifier = TelegramNotifier(settings=settings)
        sent_keys = await notifier.dispatch_leads([lead])

        assert sent_keys == [lead.dedup_key]
        req = httpx_mock.get_request(method="POST", url=expected_url)
        assert req is not None
        body = json.loads(req.content.decode("utf-8"))
        assert body["chat_id"] == "-100987654321"
        assert body["parse_mode"] == "HTML"
        assert "B409182736" in body["text"]

    @pytest.mark.asyncio
    async def test_graceful_offline_fallback_when_token_unset(
        self,
        httpx_mock: HTTPXMock,
        temp_db_path: Path,
    ) -> None:
        settings = RadarSettings(
            db_path=temp_db_path,
            telegram_bot_token="",
            telegram_chat_id="",
        )
        engine = CAVScoringEngine()
        lead = engine.score_notice(load_demo_notices()[0])

        notifier = TelegramNotifier(settings=settings)
        sent_keys = await notifier.dispatch_leads([lead])

        assert sent_keys == []
        assert len(httpx_mock.get_requests()) == 0

        digest = render_markdown_digest([lead])
        assert "# Sardegna B2B Procurement & Grant Digest" in digest
        assert "B409182736" in digest


class TestTyperCLI:
    def test_cli_init_scan_idempotency_leads_stats_and_export(self, tmp_path: Path) -> None:
        db_file = tmp_path / "cli_radar.db"
        export_file = tmp_path / "digest.md"

        # 1. init-db
        res_init = runner.invoke(app, ["init-db", "--db-path", str(db_file)])
        assert res_init.exit_code == 0
        assert db_file.exists()

        # 2. First scan --demo
        res_scan1 = runner.invoke(app, ["scan", "--demo", "--db-path", str(db_file)])
        assert res_scan1.exit_code == 0
        assert "Nuovi inseriti: 7" in res_scan1.stdout

        # 3. Second scan --demo (must be 100% idempotent: 0 newly inserted)
        res_scan2 = runner.invoke(app, ["scan", "--demo", "--db-path", str(db_file)])
        assert res_scan2.exit_code == 0
        assert "Nuovi inseriti: 0" in res_scan2.stdout
        assert "Duplicati ignorati: 7" in res_scan2.stdout

        # 4. leads command
        res_leads = runner.invoke(
            app,
            ["leads", "--db-path", str(db_file), "--min-score", "45", "--province", "NU"],
        )
        assert res_leads.exit_code == 0
        assert "B409182736" in res_leads.stdout
        assert "A837465910" in res_leads.stdout

        # 5. stats command
        res_stats = runner.invoke(app, ["stats", "--db-path", str(db_file)])
        assert res_stats.exit_code == 0
        assert "Sardegna Prefabbricati C.A.V. S.r.l." in res_stats.stdout
        assert "Totale Bandi Analizzati" in res_stats.stdout

        # 6. export command
        res_export = runner.invoke(
            app,
            ["export", "--db-path", str(db_file), "--output", str(export_file)],
        )
        assert res_export.exit_code == 0
        assert export_file.exists()
        content = export_file.read_text(encoding="utf-8")
        assert "B409182736" in content
