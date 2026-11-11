"""Alerting and ultra-compact Telegram / WhatsApp / Markdown digest channels."""

from __future__ import annotations

from sardegna_radar.notifiers.telegram import (
    TelegramNotifier,
    format_italian_euro,
    format_italian_number,
    format_lead_telegram_html,
    format_lead_whatsapp_text,
    render_markdown_digest,
)

__all__ = [
    "TelegramNotifier",
    "format_italian_euro",
    "format_italian_number",
    "format_lead_telegram_html",
    "format_lead_whatsapp_text",
    "render_markdown_digest",
]
