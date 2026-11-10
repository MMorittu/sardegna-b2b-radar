"""Base HTTP/2 asynchronous client factory with retry transport and strict timeouts."""

from __future__ import annotations

import httpx

from sardegna_radar import __version__
from sardegna_radar.config import RadarSettings


def build_async_http_client(settings: RadarSettings | None = None) -> httpx.AsyncClient:
    """Create a configured httpx.AsyncClient with retries=3 and (15s read / 30s connect) timeout."""
    cfg = settings or RadarSettings()
    transport = httpx.AsyncHTTPTransport(retries=cfg.http_max_retries)
    timeout = httpx.Timeout(cfg.http_timeout_seconds, connect=cfg.http_connect_timeout_seconds)
    headers = {
        "User-Agent": f"sardegna-b2b-radar/{__version__} (+https://github.com/MMorittu/sardegna-b2b-radar)",
        "Accept": "application/json, text/html, application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    return httpx.AsyncClient(
        transport=transport,
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    )
