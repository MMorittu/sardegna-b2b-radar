"""Typer + Rich CLI for the Sardegna B2B Tender & Procurement Radar."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from sardegna_radar.config import RadarSettings
from sardegna_radar.matcher.cav_engine import CAVScoringEngine
from sardegna_radar.models import (
    NoticeSource,
    SardinianProvince,
    TenderNotice,
    resolve_sardinian_province,
)
from sardegna_radar.notifiers.telegram import (
    TelegramNotifier,
    format_italian_euro,
    render_markdown_digest,
)
from sardegna_radar.scrapers.anac_api import ANACReverseAPIConnector
from sardegna_radar.scrapers.demo_feed import load_demo_notices
from sardegna_radar.scrapers.sardegna_portals import (
    SardegnaPortalAdaptiveScraper,
    create_scrapling_mcp_server,
)
from sardegna_radar.storage.repository import RadarRepository

app = typer.Typer(
    name="sardegna-radar",
    help="Sardegna B2B Tender & Procurement Radar — Precast C.A.V. & Regional Grant Intelligence",
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
    """Initialize the idempotent SQLite WAL database schema and indexes."""
    settings = _resolve_settings(db_path)
    repo = RadarRepository(settings.db_path)
    repo.init_db()
    console.print(
        f"[bold green]✓ Database SQLite WAL inizializzato:[/bold green] {settings.db_path}"
    )


async def _collect_live_notices(
    settings: RadarSettings,
    *,
    anac_url: str | None = None,
    portal_url: str | None = None,
) -> list[TenderNotice]:
    notices: list[TenderNotice] = []
    if anac_url:
        connector = ANACReverseAPIConnector(endpoint_url=anac_url, settings=settings)
        notices.extend(await connector.fetch_notices())
    if portal_url:
        scraper = SardegnaPortalAdaptiveScraper(
            source=NoticeSource.SARDEGNACAT,
            settings=settings,
        )
        notices.extend(await scraper.fetch_notices(portal_url))
    return notices


@app.command("scan")
def scan_command(
    demo: Annotated[
        bool,
        typer.Option("--demo", help="Scan curated realistic Sardinian tenders & grants dataset."),
    ] = False,
    anac_url: Annotated[
        str | None,
        typer.Option("--anac-url", help="ANAC OCDS Reverse-API JSON endpoint URL."),
    ] = None,
    portal_url: Annotated[
        str | None,
        typer.Option("--portal-url", help="SardegnaCAT / RAS HTML portal URL parsed via Scrapling."),
    ] = None,
    min_score: Annotated[
        float,
        typer.Option("--min-score", help="Minimum score (0-100) for high-priority alerting."),
    ] = 45.0,
    notify: Annotated[
        bool,
        typer.Option("--notify/--no-notify", help="Dispatch Telegram alerts for new high-priority leads."),
    ] = True,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Custom SQLite WAL database path."),
    ] = None,
) -> None:
    """Ingest procurement notices, run zero-token C.A.V. scoring, deduplicate in SQLite WAL, and alert."""
    settings = _resolve_settings(db_path)
    settings.min_alert_score = min_score
    repo = RadarRepository(settings.db_path)
    repo.init_db()

    if demo or (not anac_url and not portal_url):
        notices = load_demo_notices()
        feed_mode = "DEMO FEED (SardegnaCAT + ANAC OCDS + RAS + CCIAA Nuoro)"
    else:
        notices = asyncio.run(
            _collect_live_notices(settings, anac_url=anac_url, portal_url=portal_url)
        )
        feed_mode = "LIVE HYBRID (Reverse-API + Scrapling Adaptive)"

    engine = CAVScoringEngine()
    scored_leads = [engine.score_notice(n) for n in notices]
    inserted, deduplicated = repo.upsert_many(scored_leads)

    unnotified_high = repo.list_leads(min_score=min_score, only_unnotified=True)
    notified_count = 0
    if notify and unnotified_high and settings.telegram_enabled:
        notifier = TelegramNotifier(settings=settings)
        sent_keys = asyncio.run(notifier.dispatch_leads(unnotified_high))
        notified_count = repo.mark_notified(sent_keys)

    high_priority_total = sum(1 for lead in scored_leads if lead.assessment.score >= min_score)

    console.print(
        Panel.fit(
            f"[bold cyan]Modalità:[/bold cyan] {feed_mode}\n"
            f"[bold green]Nuovi inseriti:[/bold green] {inserted} | "
            f"[bold yellow]Duplicati ignorati:[/bold yellow] {deduplicated}\n"
            f"[bold magenta]Lead sopra soglia (>={min_score:.0f}/100):[/bold magenta] {high_priority_total} | "
            f"[bold blue]Notifiche Telegram inviate:[/bold blue] {notified_count}",
            title=f"📡 Sardegna B2B Radar — {settings.company_name}",
            border_style="cyan",
        )
    )


@app.command("leads")
def leads_command(
    min_score: Annotated[
        float,
        typer.Option("--min-score", help="Minimum C.A.V. match score (0-100)."),
    ] = 45.0,
    province: Annotated[
        str | None,
        typer.Option("--province", help="Filter by Sardinian province code (NU, SS, OR, CA, SU)."),
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
    """Display scored B2B procurement & regional grant leads in a Rich table."""
    settings = _resolve_settings(db_path)
    repo = RadarRepository(settings.db_path)
    prov_filter: SardinianProvince | None = (
        resolve_sardinian_province(province) if province else None
    )
    leads = repo.list_leads(min_score=min_score, province=prov_filter, limit=limit)

    table = Table(
        title=f"🏗 Opportunità B2B C.A.V. & Bandi PMI — {settings.company_name} (Score >= {min_score:.0f})",
        show_lines=True,
    )
    table.add_column("Score", justify="right", style="bold green", no_wrap=True)
    table.add_column("Fonte / CIG", style="cyan", no_wrap=True)
    table.add_column("Comune (Prov) & Tier", style="yellow")
    table.add_column("Importo", justify="right", style="magenta", no_wrap=True)
    table.add_column("Oggetto & Linee C.A.V.", style="white")
    table.add_column("Azione Commerciale", style="bold white")

    for lead in leads:
        n = lead.notice
        a = lead.assessment
        cig_label = f"{n.source.value}\n{n.cig or n.external_id}"
        tier_short = a.logistics_tier.value.split("(")[0].strip()
        km_str = f"{a.estimated_distance_km} km" if a.estimated_distance_km is not None else "N/D"
        loc_label = f"{n.municipality or 'Sardegna'} ({n.province.value})\n{tier_short} [{km_str}]"
        cats = ", ".join(c.value for c in a.matched_categories) or "Generale"
        title_and_cats = f"[bold]{n.title}[/bold]\n[dim]{cats}[/dim]"

        table.add_row(
            f"{a.score:.1f}",
            cig_label,
            loc_label,
            format_italian_euro(n.amount_eur),
            title_and_cats,
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
    """Show aggregate pipeline and portfolio metrics from SQLite WAL storage."""
    settings = _resolve_settings(db_path)
    repo = RadarRepository(settings.db_path)
    stats = repo.get_stats(min_priority_score=settings.min_alert_score)

    prov_breakdown = (
        ", ".join(f"{k}: {v}" for k, v in stats["high_priority_by_province"].items()) or "Nessuno"
    )
    src_breakdown = (
        ", ".join(f"{k}: {v}" for k, v in stats["leads_by_source"].items()) or "Nessuno"
    )

    console.print(
        Panel.fit(
            f"[bold white]Azienda Target:[/bold white] {settings.company_name} (P.IVA {settings.company_piva} — Base: {settings.company_base_municipality}, {settings.company_base_province})\n"
            f"[bold cyan]Totale Bandi Analizzati:[/bold cyan] {stats['total_leads']}\n"
            f"[bold green]Opportunità Qualificate (>={settings.min_alert_score:.0f}/100):[/bold green] {stats['high_priority_leads']}\n"
            f"[bold yellow]Da Notificare:[/bold yellow] {stats['unnotified_high_priority']}\n"
            f"[bold magenta]Valore Cumulato Opportunità Qualificate:[/bold magenta] {format_italian_euro(stats['high_priority_value_eur'])}\n"
            f"[bold blue]Distribuzione Province (Target):[/bold blue] {prov_breakdown}\n"
            f"[bold dim]Fonti Ingestite:[/bold dim] {src_breakdown}",
            title="📊 Sardegna B2B Radar — Statistiche Portafoglio",
            border_style="green",
        )
    )


@app.command("export")
def export_command(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output Markdown file path."),
    ] = Path("sardegna_b2b_digest.md"),
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
    repo = RadarRepository(settings.db_path)
    leads = repo.list_leads(min_score=min_score)
    markdown_text = render_markdown_digest(leads, company_name=settings.company_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_text, encoding="utf-8")
    console.print(
        f"[bold green]✓ Esportate {len(leads)} opportunità in:[/bold green] {output}"
    )


@app.command("mcp-server")
def mcp_server_command(
    http: Annotated[bool, typer.Option("--http", help="Serve Scrapling MCP over HTTP instead of stdio.")] = False,
    host: Annotated[str, typer.Option("--host", help="Bind host for HTTP mode.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Bind port for HTTP mode.")] = 8000,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print MCP config without blocking.")] = False,
) -> None:
    """Launch or inspect the Scrapling MCP Server (`ScraplingMCPServer`) for interactive AI agent scraping."""
    info = create_scrapling_mcp_server(http=http, host=host, port=port, dry_run=dry_run)
    console.print(f"[bold cyan]Scrapling MCP Server:[/bold cyan] {info}")


if __name__ == "__main__":
    app()
