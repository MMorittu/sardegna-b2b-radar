"""Telegram Bot API webhook dispatcher with graceful offline Markdown fallback."""

from __future__ import annotations

from collections.abc import Sequence
import html
import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.models import ScoredLead
from sardegna_radar.scrapers.base import build_async_http_client


def format_italian_euro(amount: float | None) -> str:
    """Format a float amount into Italian currency string (`€ 1.180.500,00`)."""
    if amount is None:
        return "N/D"
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {formatted}"


def format_lead_telegram_html(lead: ScoredLead) -> str:
    """Render a ScoredLead into a structured Telegram HTML notification card."""
    n = lead.notice
    a = lead.assessment
    categories_str = ", ".join(c.value for c in a.matched_categories) or "Generale"
    cig_str = n.cig or n.external_id
    amount_str = format_italian_euro(n.amount_eur)
    deadline_str = n.deadline_date.strftime("%d/%m/%Y") if n.deadline_date else "N/D"
    loc_str = f"{n.municipality or 'Sardegna'} ({n.province.value})"
    km_str = f"{a.estimated_distance_km} km da Silanus" if a.estimated_distance_km is not None else "N/D"

    lines = [
        f"🚨 <b>SARDEGNA B2B RADAR — Score {a.score:.1f}/100</b>",
        f"📌 <b>{html.escape(n.title)}</b>",
        f"🏛 <b>Ente:</b> {html.escape(n.contracting_authority)}",
        f"📍 <b>Località:</b> {html.escape(loc_str)} | 🚚 <b>{html.escape(a.logistics_tier.value.split('(')[0].strip())}</b> ({km_str})",
        f"💶 <b>Importo:</b> {amount_str} | 🆔 <b>CIG:</b> <code>{html.escape(cig_str)}</code>",
        f"📅 <b>Scadenza:</b> {deadline_str}",
        f"🏗 <b>Linee C.A.V. Match:</b> {html.escape(categories_str)}",
    ]
    if n.winner_company:
        lines.append(f"🏆 <b>Aggiudicatario:</b> {html.escape(n.winner_company)}")
    lines.append(f"🎯 <b>Azione:</b> {html.escape(a.recommended_action)}")
    if n.url:
        lines.append(f"🔗 <a href=\"{html.escape(n.url)}\">Apri Bando / Scheda Ufficiale</a>")
    return "\n".join(lines)


def render_markdown_digest(
    leads: Sequence[ScoredLead],
    company_name: str = "Sardegna Prefabbricati C.A.V. S.r.l.",
) -> str:
    """Render a sequence of ScoredLeads into a portable Markdown commercial digest."""
    lines = [
        "# Sardegna B2B Procurement & Grant Digest",
        f"**Target Commerciale:** {company_name} (Z.I. Silanus, NU)",
        f"**Opportunità Qualificate:** {len(leads)}",
        "",
    ]
    if not leads:
        lines.append("_Nessun bando qualificato sopra soglia._")
        return "\n".join(lines)

    for idx, lead in enumerate(leads, start=1):
        n = lead.notice
        a = lead.assessment
        cig_str = n.cig or n.external_id
        amount_str = format_italian_euro(n.amount_eur)
        deadline_str = n.deadline_date.strftime("%d/%m/%Y") if n.deadline_date else "N/D"
        categories_str = ", ".join(c.value for c in a.matched_categories) or "N/D"

        lines.extend(
            [
                f"## {idx}. [{a.score:.1f}/100] {n.title}",
                f"- **Fonte / CIG:** `{n.source.value}` | `{cig_str}`",
                f"- **Stazione Appaltante:** {n.contracting_authority}",
                f"- **Cantiere & Logistica:** {n.municipality or 'Sardegna'} ({n.province.value}) — {a.logistics_tier.value}",
                f"- **Importo:** {amount_str} | **Scadenza:** {deadline_str}",
                f"- **Linee C.A.V. / Bandi:** {categories_str}",
                f"- **Azione Consigliata:** {a.recommended_action}",
                f"- **Link:** {n.url}",
                "",
            ]
        )
    return "\n".join(lines)


class TelegramNotifier:
    """Asynchronous Telegram Bot API dispatcher with safe offline degradation."""

    def __init__(self, settings: RadarSettings | None = None) -> None:
        self.settings = settings or RadarSettings()

    @property
    def endpoint_url(self) -> str:
        token = self.settings.telegram_bot_token.strip()
        return f"https://api.telegram.org/bot{token}/sendMessage"

    async def dispatch_leads(
        self,
        leads: Sequence[ScoredLead],
        client: httpx.AsyncClient | None = None,
    ) -> list[str]:
        """Send Telegram alerts for leads when credentials are set; return list of notified dedup_keys."""
        if not leads or not self.settings.telegram_enabled:
            return []

        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        notified_keys: list[str] = []
        try:
            for lead in leads:
                payload = {
                    "chat_id": self.settings.telegram_chat_id.strip(),
                    "text": format_lead_telegram_html(lead),
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
                response = await http_client.post(self.endpoint_url, json=payload)
                response.raise_for_status()
                notified_keys.append(lead.dedup_key)
            return notified_keys
        finally:
            if owns_client:
                await http_client.aclose()
