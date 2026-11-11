"""100% Live Typer + Rich CLI for Sardegna B2B Radar (zero demo)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from sardegna_radar.cme.parser import CMEParser
from sardegna_radar.config import RadarSettings
from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.models import (
    CRMStatus,
    NoticeSource,
    NoticeType,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
    resolve_sardinian_province,
)
from sardegna_radar.notifiers.telegram import (
    TelegramNotifier,
    format_italian_euro,
    format_lead_whatsapp_text,
    render_markdown_digest,
)
from sardegna_radar.scrapers.anac_api import ANACReverseAPIConnector
from sardegna_radar.scrapers.base import build_async_http_client
from sardegna_radar.scrapers.grants_ras_cciaa import GrantsConnector
from sardegna_radar.scrapers.sardegna_cat import SardegnaCATConnector
from sardegna_radar.scrapers.sardegna_portals import (
    CUC_COMUNITA_MONTANA_NUORESE_URL,
    SardegnaPortalAdaptiveScraper,
)
from sardegna_radar.scrapers.url_validator import HttpUrlValidator
from sardegna_radar.storage.repository import build_repository

app = typer.Typer(
    name="sardegna-radar",
    help="Sardegna B2B Radar — Sardinian Precast & Construction Supplier Live Tender, CME & Grant Intelligence",
    add_completion=False,
)
console = Console()


def _resolve_settings(db_path: Path | None) -> RadarSettings:
    settings = RadarSettings()
    if db_path is not None:
        settings.db_path = db_path
    return settings


@app.command("init-db")
def init_db_command(
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Initialize Dual-Ready storage (`tenders` + `cme_items` + `crm_status`)."""
    settings = _resolve_settings(db_path)
    repo = build_repository(settings)
    repo.init_db()
    target = "Supabase Postgres" if settings.supabase_enabled else str(settings.db_path)
    console.print(f"[bold green]✓ Storage inizializzato:[/bold green] {target}")


async def _run_live_pipeline(
    settings: RadarSettings,
    *,
    anac_bulk: bool,
    anac_url: str | None,
    portal_url: str | None,
    parse_attachments: bool,
    anac_limit: int,
) -> tuple[list[ScoredLead], int, list[str]]:
    """Fetch live sources concurrently, enforce HTTP 200 post-redirect, optionally parse CME ZIPs, and score."""
    errors: list[str] = []
    raw_notices: list[TenderNotice] = []

    async with build_async_http_client(settings) as client:
        tasks = [
            SardegnaCATConnector(settings).fetch_notices(client=client),
            GrantsConnector(settings).fetch_all_grants(client=client),
            SardegnaPortalAdaptiveScraper(
                source=NoticeSource.CUC_LOCALE,
                base_url="https://comunitamontananuorese.it",
                settings=settings,
            ).fetch_notices(portal_url or CUC_COMUNITA_MONTANA_NUORESE_URL, client=client),
        ]
        if anac_url:
            tasks.append(ANACReverseAPIConnector(endpoint_url=anac_url, settings=settings).fetch_notices(client=client))
        elif anac_bulk:
            tasks.append(
                ANACReverseAPIConnector(settings=settings).fetch_ckan_sardinian_notices(
                    client=client, limit=anac_limit
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                errors.append(str(res))
            else:
                raw_notices.extend(res)

        validator = HttpUrlValidator(settings=settings)
        verified_notices = await validator.filter_valid_notices(raw_notices, client=client)
        rejected_urls = len(raw_notices) - len(verified_notices)

        engine = CAVScoringEngine()
        cme_parser = CMEParser(settings=settings)
        scored: list[ScoredLead] = []

        for notice in verified_notices:
            cme_items = []
            if parse_attachments and notice.attachment_url:
                try:
                    parsed = await cme_parser.parse_url(notice.attachment_url, client=client)
                    cme_items = parsed.matched_items
                except Exception:
                    cme_items = []
            scored.append(engine.score_notice(notice, cme_items=cme_items))

        return scored, rejected_urls, errors


@app.command("scan")
def scan_command(
    min_score: Annotated[
        float,
        typer.Option("--min-score", help="Minimum score (0-100) for high-priority alerting & digest."),
    ] = 45.0,
    anac_bulk: Annotated[
        bool,
        typer.Option("--anac-bulk/--no-anac-bulk", help="Include live ANAC OpenData 2026 Sardinian stream."),
    ] = True,
    anac_limit: Annotated[
        int,
        typer.Option("--anac-limit", help="Max Sardinian ANAC works/awards to ingest from latest monthly ZIP."),
    ] = 80,
    anac_url: Annotated[
        str | None,
        typer.Option("--anac-url", help="Custom ANAC v2.3 / OCDS JSON URL."),
    ] = None,
    portal_url: Annotated[
        str | None,
        typer.Option("--portal-url", help="Custom CUC / PA Digitale portal URL."),
    ] = None,
    parse_attachments: Annotated[
        bool,
        typer.Option("--parse-attachments/--no-parse-attachments", help="Stream remote ZIP attachments for CME."),
    ] = False,
    digest_out: Annotated[
        Path,
        typer.Option("--digest-out", help="Auto-updated Markdown digest path."),
    ] = Path("data/leads_digest.md"),
    notify: Annotated[
        bool,
        typer.Option("--notify/--no-notify", help="Dispatch Telegram alerts for new high-priority leads."),
    ] = True,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Run 100% live Sardinian scan (ANAC + SardegnaCAT + CUC + RAS/CCIAA) with HTTP 200 enforcement."""
    settings = _resolve_settings(db_path)
    settings.min_alert_score = min_score
    repo = build_repository(settings)
    repo.init_db()

    scored_leads, rejected_urls, errors = asyncio.run(
        _run_live_pipeline(
            settings,
            anac_bulk=anac_bulk,
            anac_url=anac_url,
            portal_url=portal_url,
            parse_attachments=parse_attachments,
            anac_limit=anac_limit,
        )
    )
    inserted, deduplicated = repo.upsert_many(scored_leads)

    unnotified_high = repo.list_leads(min_score=min_score, only_unnotified=True)
    notified_count = 0
    if notify and unnotified_high and settings.telegram_enabled:
        sent_keys = asyncio.run(TelegramNotifier(settings=settings).dispatch_leads(unnotified_high))
        notified_count = repo.mark_notified(sent_keys)

    qualified = repo.list_leads(min_score=min_score, limit=100)
    digest_out.parent.mkdir(parents=True, exist_ok=True)
    digest_out.write_text(render_markdown_digest(qualified, company_name=settings.company_name), encoding="utf-8")

    err_line = f"\n[bold red]Avvisi rete ({len(errors)}):[/bold red] {'; '.join(errors[:2])}" if errors else ""
    console.print(
        Panel.fit(
            f"[bold cyan]Modalità:[/bold cyan] 100% LIVE (ANAC + SardegnaCAT + CUC + RAS + CCIAA Nuoro)\n"
            f"[bold green]URL verificati HTTP 200:[/bold green] {len(scored_leads)} "
            f"(scartati non-200/soft-404: {rejected_urls})\n"
            f"[bold green]Nuovi inseriti:[/bold green] {inserted} | "
            f"[bold yellow]Aggiornati idempotenti:[/bold yellow] {deduplicated}\n"
            f"[bold magenta]Qualificati Catalog (>={min_score:.0f}/100):[/bold magenta] {len(qualified)} | "
            f"[bold blue]Telegram inviati:[/bold blue] {notified_count}\n"
            f"[bold dim]Digest aggiornato:[/bold dim] {digest_out}{err_line}",
            title=f"📡 Sardegna B2B Radar — {settings.company_name} (P.IVA {settings.company_piva})",
            border_style="cyan",
        )
    )


@app.command("parse-cme")
def parse_cme_command(
    source: Annotated[
        str,
        typer.Argument(help="Local .pdf / .pdf.p7m / .zip path OR remote https:// URL."),
    ],
    anac_json: Annotated[
        Path | None,
        typer.Option("--anac-json", help="Optional ANAC `appalto v2.3` JSON file (e.g. CIG_BCB16FC2F3.json)."),
    ] = None,
    notice_url: Annotated[
        str | None,
        typer.Option("--notice-url", help="Official public tender URL (HTTP 200 required if --save without --anac-json)."),
    ] = None,
    save: Annotated[
        bool,
        typer.Option("--save/--no-save", help="Persist resulting ScoredLead + CME items into storage."),
    ] = False,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Parse a Computo Metrico Estimativo (.pdf/.zip/.p7m or URL) for Catalog Linea A & Linea B."""
    settings = _resolve_settings(db_path)
    parser = CMEParser(settings=settings)

    if source.startswith(("http://", "https://")):
        result = asyncio.run(parser.parse_url(source))
    else:
        result = parser.parse_path(source)

    if anac_json is not None:
        notice = ANACReverseAPIConnector(settings=settings).parse_appalto_v23_file(anac_json)
        if notice is None:
            raise typer.BadParameter(f"Impossibile estrarre gara valida da {anac_json}")
        notice = asyncio.run(HttpUrlValidator(settings=settings).validate_notice(notice))
    else:
        effective_url = notice_url or (source if source.startswith(("http://", "https://")) else "")
        if save and not effective_url:
            raise typer.BadParameter(
                "Con --save senza --anac-json è obbligatorio fornire --notice-url (HTTP 200 verificabile)."
            )
        notice = TenderNotice(
            external_id=Path(result.selected_filename).stem[:40],
            source=NoticeSource.CUC_LOCALE,
            notice_type=NoticeType.PUBLIC_WORKS_TENDER,
            title=f"Analisi CME: {result.selected_filename}",
            url=effective_url,
            http_status=None,
        )
        if save or effective_url:
            notice = asyncio.run(HttpUrlValidator(settings=settings).validate_notice(notice))

    lead = CAVScoringEngine().score_notice(notice, cme_items=result.matched_items)
    if save:
        repo = build_repository(settings)
        repo.upsert_lead(lead)

    console.print(
        Panel(
            format_lead_whatsapp_text(lead),
            title=(
                f"🧱 CME Analizzato: {result.selected_filename} "
                f"({len(result.matched_items)}/{result.total_raw_items} voci compatibili)"
            ),
            border_style="green",
        )
    )


@app.command("set-status")
def set_status_command(
    identifier: Annotated[str, typer.Argument(help="CIG (e.g. BCB16FC2F3) or dedup_key.")],
    status: Annotated[CRMStatus, typer.Argument(help="New CRM status.")],
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Update CRM pipeline status (`da_chiamare | preventivo_inviato | vinto | scartato`)."""
    settings = _resolve_settings(db_path)
    repo = build_repository(settings)
    ok = repo.update_crm_status(identifier, status)
    if not ok:
        console.print(f"[bold red]✗ Nessuna gara trovata per:[/bold red] {identifier}")
        raise typer.Exit(code=1)
    console.print(f"[bold green]✓ Stato CRM aggiornato:[/bold green] {identifier} → {status.value}")


@app.command("leads")
def leads_command(
    min_score: Annotated[
        float,
        typer.Option("--min-score", help="Minimum match score (0-100)."),
    ] = 45.0,
    province: Annotated[
        str | None,
        typer.Option("--province", help="Filter by Sardinian province code (NU, SS, OR, CA, SU)."),
    ] = None,
    crm_status: Annotated[
        CRMStatus | None,
        typer.Option("--status", help="Filter by CRM status."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of leads to display."),
    ] = 25,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Display verified B2B leads and CRM states in a Rich table."""
    settings = _resolve_settings(db_path)
    repo = build_repository(settings)
    prov_filter: SardinianProvince | None = resolve_sardinian_province(province) if province else None
    leads = repo.list_leads(min_score=min_score, province=prov_filter, crm_status=crm_status, limit=limit)

    table = Table(
        title=f"🏗 Opportunità Verificate — {settings.company_name} (Score >= {min_score:.0f})",
        show_lines=True,
    )
    table.add_column("Score", justify="right", style="bold green", no_wrap=True)
    table.add_column("Fonte / CIG / CRM", style="cyan", no_wrap=True)
    table.add_column("Comune (Prov)", style="yellow")
    table.add_column("Importo", justify="right", style="magenta", no_wrap=True)
    table.add_column("Oggetto & Vincitore", style="white")
    table.add_column("Azione Commerciale", style="bold white")

    for lead in leads:
        n = lead.notice
        a = lead.assessment
        cig_label = f"{n.source.value}\n{n.cig or n.external_id}\n[{lead.crm_status.value}]"
        km_str = f"{a.estimated_distance_km} km" if a.estimated_distance_km is not None else "N/D"
        loc_label = f"{n.municipality or 'Sardegna'} ({n.province.value})\n[{km_str}]"
        win_info = f"\n🏆 {n.winner_company} ({n.winner_tax_id or 'N/D'})" if n.winner_company else ""
        cme_info = f"\n🧱 {len(lead.cme_items)} voci CME" if lead.cme_items else ""
        amt_display = format_italian_euro(n.award_amount_eur or n.amount_eur)

        table.add_row(
            f"{a.score:.0f}",
            cig_label,
            loc_label,
            amt_display,
            f"[bold]{n.title[:95]}[/bold]{win_info}{cme_info}",
            a.recommended_action,
        )

    console.print(table)


@app.command("stats")
def stats_command(
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Show aggregate pipeline and CRM metrics."""
    settings = _resolve_settings(db_path)
    repo = build_repository(settings)
    stats = repo.get_stats(min_priority_score=settings.min_alert_score)

    prov_breakdown = ", ".join(f"{k}: {v}" for k, v in stats["high_priority_by_province"].items()) or "Nessuno"
    src_breakdown = ", ".join(f"{k}: {v}" for k, v in stats["leads_by_source"].items()) or "Nessuno"
    crm_breakdown = ", ".join(f"{k}: {v}" for k, v in stats["by_crm_status"].items()) or "Nessuno"

    console.print(
        Panel.fit(
            f"[bold white]Azienda:[/bold white] {settings.company_name} "
            f"(P.IVA {settings.company_piva} | REA {settings.company_rea} | Albo Artigiani {settings.company_albo_artigiani} — {settings.company_base_municipality} {settings.company_base_province})\n"
            f"[bold cyan]Totale Gare/Bandi Verificati:[/bold cyan] {stats['total_leads']}\n"
            f"[bold green]Opportunità Qualificate (>={settings.min_alert_score:.0f}/100):[/bold green] {stats['high_priority_leads']}\n"
            f"[bold magenta]Valore Qualificato:[/bold magenta] {format_italian_euro(stats['high_priority_value_eur'])}\n"
            f"[bold yellow]Pipeline CRM:[/bold yellow] {crm_breakdown}\n"
            f"[bold blue]Province:[/bold blue] {prov_breakdown} | [bold dim]Fonti:[/bold dim] {src_breakdown}",
            title="📊 Sardegna B2B Radar — Statistiche Portafoglio",
            border_style="green",
        )
    )


@app.command("export")
def export_command(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output Markdown file path."),
    ] = Path("data/leads_digest.md"),
    min_score: Annotated[
        float,
        typer.Option("--min-score", help="Minimum score to include in digest."),
    ] = 45.0,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Export qualified B2B leads into a clean Markdown commercial digest."""
    settings = _resolve_settings(db_path)
    repo = build_repository(settings)
    leads = repo.list_leads(min_score=min_score)
    markdown_text = render_markdown_digest(leads, company_name=settings.company_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_text, encoding="utf-8")
    console.print(f"[bold green]✓ Esportate {len(leads)} opportunità in:[/bold green] {output}")


if __name__ == "__main__":
    app()
