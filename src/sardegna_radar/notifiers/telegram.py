"""Ultra-compact Telegram HTML, WhatsApp text, and Markdown commercial digest formatters."""

from __future__ import annotations

from collections.abc import Sequence
import html

import httpx

from sardegna_radar.config import RadarSettings
from sardegna_radar.models import NoticeType, ScoredLead
from sardegna_radar.scrapers.base import build_async_http_client


def format_italian_number(val: float | None, decimals: int = 2) -> str:
    """Format a float with Italian thousands dots and decimal comma (`2.981,89`)."""
    if val is None:
        return "N/D"
    return f"{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_italian_euro(amount: float | None) -> str:
    """Format a float amount into Italian currency string (`€ 147.411,79`)."""
    if amount is None:
        return "N/D"
    return f"€ {format_italian_number(amount, 2)}"


def _site_status_label(lead: ScoredLead) -> str:
    n = lead.notice
    if n.notice_type == NoticeType.REGIONAL_GRANT:
        scad = n.deadline_date.strftime("%d/%m/%Y") if n.deadline_date else "Aperto"
        return f"Bando Fondo Perduto (Scad. {scad})"
    if n.notice_type == NoticeType.CONTRACT_AWARD:
        parts: list[str] = []
        if n.contract_started is False:
            parts.append("🔥 NON AVVIATO")
        elif n.contract_started is True:
            parts.append("Avviato")
        else:
            parts.append("Aggiudicata")
        if n.has_subcontracts is False:
            parts.append("0 Subappalti")
        elif n.has_subcontracts is True:
            parts.append("Subappalti presenti")
        return " | ".join(parts)
    scad = n.deadline_date.strftime("%d/%m/%Y") if n.deadline_date else "N/D"
    return f"Gara Aperta (Scad. {scad})"


def _amount_line(lead: ScoredLead) -> str:
    n = lead.notice
    base = format_italian_euro(n.amount_eur)
    if n.award_amount_eur is not None:
        rib = f" (-{format_italian_number(n.discount_pct, 2)}%)" if n.discount_pct is not None else ""
        return f"Base {base} → Agg. {format_italian_euro(n.award_amount_eur)}{rib}"
    return base


def _materials_lines(lead: ScoredLead, max_items: int = 12) -> list[str]:
    if lead.cme_items:
        out: list[str] = []
        for it in lead.cme_items[:max_items]:
            tag = "Linea A" if it.product_line.value == "linea_a" else "Linea B"
            qty_str = f"{format_italian_number(it.quantity, 2)} {it.unit}".strip()
            tot_str = f" ({format_italian_euro(it.total_price_eur)})" if it.total_price_eur else ""
            label = it.matched_catalog_label or it.description[:70]
            out.append(f"• [{tag}] {qty_str} — {label}{tot_str}")
        if len(lead.cme_items) > max_items:
            out.append(f"• ... +{len(lead.cme_items) - max_items} altre voci compatibili nel CME")
        return out
    return [f"• {cat.value}" for cat in lead.assessment.matched_categories] or ["• Da verificare su elaborati"]


def format_lead_whatsapp_text(lead: ScoredLead) -> str:
    """Render an ultra-compact, zero-fluff WhatsApp message ready for Graziano & Giovanni Antonio."""
    n = lead.notice
    a = lead.assessment
    cig_str = n.cig or n.external_id
    loc_str = f"{n.municipality or 'Sardegna'} ({n.province.value})"
    km_str = f"{a.estimated_distance_km} km da Silanus" if a.estimated_distance_km is not None else "Sardegna"

    lines = [
        f"🎯 *[{a.score:.0f}/100] {n.title}*",
        f"🏛 Ente: {n.contracting_authority}" + (f" (CUC: {n.delegated_authority})" if n.delegated_authority else ""),
        f"🆔 CIG: `{cig_str}`" + (f" | CUP: `{n.cup}`" if n.cup else "") + f" | 📍 {loc_str} ({km_str})",
        f"💶 Importo: {_amount_line(lead)}",
        f"🏗 Stato: {_site_status_label(lead)}",
    ]
    if n.winner_company:
        piva = f" | P.IVA {n.winner_tax_id}" if n.winner_tax_id else ""
        w_dist = f" | sede {n.winner_province or ''} ~{n.winner_distance_km} km".replace("  ", " ") if n.winner_distance_km else ""
        lines.append(f"🏆 Vincitore: *{n.winner_company}*{piva}{w_dist}")
    if n.rup_name:
        lines.append(f"👤 RUP: {n.rup_name}")

    lines.append("🧱 *Materiali & Misure Edilmorittu:*")
    lines.extend(_materials_lines(lead))
    if n.url:
        lines.append(f"🔗 {n.url}")
    return "\n".join(lines)


def format_lead_telegram_html(lead: ScoredLead) -> str:
    """Render an ultra-compact, zero-fluff Telegram HTML card."""
    n = lead.notice
    a = lead.assessment
    cig_str = n.cig or n.external_id
    loc_str = f"{n.municipality or 'Sardegna'} ({n.province.value})"
    km_str = f"{a.estimated_distance_km} km da Silanus" if a.estimated_distance_km is not None else "Sardegna"

    lines = [
        f"🎯 <b>[{a.score:.0f}/100] {html.escape(n.title)}</b>",
        f"🏛 <b>Ente:</b> {html.escape(n.contracting_authority)}",
        f"🆔 <b>CIG:</b> <code>{html.escape(cig_str)}</code> | 📍 {html.escape(loc_str)} ({km_str})",
        f"💶 <b>Importo:</b> {html.escape(_amount_line(lead))}",
        f"🏗 <b>Stato:</b> {html.escape(_site_status_label(lead))}",
    ]
    if n.winner_company:
        piva = f" | P.IVA <code>{html.escape(n.winner_tax_id)}</code>" if n.winner_tax_id else ""
        w_dist = f" (sede {html.escape(n.winner_province or '')} ~{n.winner_distance_km} km)" if n.winner_distance_km else ""
        lines.append(f"🏆 <b>Vincitore:</b> {html.escape(n.winner_company)}{piva}{w_dist}")
    if n.rup_name:
        lines.append(f"👤 <b>RUP:</b> {html.escape(n.rup_name)}")

    lines.append("🧱 <b>Materiali &amp; Misure Edilmorittu:</b>")
    for m_line in _materials_lines(lead):
        lines.append(html.escape(m_line))
    if n.url:
        lines.append(f"🔗 <a href=\"{html.escape(n.url)}\">Scheda Ufficiale Verificata</a>")
    return "\n".join(lines)


def render_markdown_digest(
    leads: Sequence[ScoredLead],
    company_name: str = "EDILMORITTU S.R.L.",
) -> str:
    """Render qualified leads into a concise Markdown commercial digest (`data/leads_digest.md`)."""
    lines = [
        f"# Radar Commerciale B2B — {company_name} (P.IVA 00799740915, Silanus NU)",
        f"**Opportunità Verificate Live (`HTTP 200`):** {len(leads)}",
        "",
    ]
    if not leads:
        lines.append("_Nessuna opportunità sopra soglia rilevata._")
        return "\n".join(lines)

    for idx, lead in enumerate(leads, start=1):
        n = lead.notice
        a = lead.assessment
        cig_str = n.cig or n.external_id
        lines.extend(
            [
                f"## {idx}. [{a.score:.0f}/100] {n.title}",
                f"- **Fonte / CIG / Stato CRM:** `{n.source.value}` | `{cig_str}` | `{lead.crm_status.value}`",
                f"- **Ente:** {n.contracting_authority}" + (f" (CUC: {n.delegated_authority})" if n.delegated_authority else ""),
                f"- **Località:** {n.municipality or 'Sardegna'} ({n.province.value}) — {a.estimated_distance_km or 'N/D'} km da Silanus",
                f"- **Importo:** {_amount_line(lead)}",
                f"- **Stato Cantiere:** {_site_status_label(lead)}",
            ]
        )
        if n.winner_company:
            lines.append(
                f"- **Vincitore:** {n.winner_company}"
                + (f" — P.IVA `{n.winner_tax_id}`" if n.winner_tax_id else "")
                + (f" (sede {n.winner_province} ~{n.winner_distance_km} km da Silanus)" if n.winner_distance_km else "")
            )
        if n.rup_name:
            lines.append(f"- **RUP:** {n.rup_name}")
        lines.append("- **Materiali & Misure Edilmorittu:**")
        for m_line in _materials_lines(lead):
            lines.append(f"  {m_line}")
        status_badge = f"HTTP {n.http_status}" if n.http_status else "Non verificato"
        lines.append(f"- **URL (`{status_badge}`):** {n.url}")
        lines.append("")
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
                try:
                    response = await http_client.post(self.endpoint_url, json=payload)
                    response.raise_for_status()
                    if response.json().get("ok"):
                        notified_keys.append(lead.dedup_key)
                except httpx.HTTPError:
                    continue
            return notified_keys
        finally:
            if owns_client:
                await http_client.aclose()
