"""Base HTTP asynchronous client factory with retry transport and browser-compatible headers."""

from __future__ import annotations

import httpx

from sardegna_radar.config import RadarSettings

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def build_async_http_client(settings: RadarSettings | None = None) -> httpx.AsyncClient:
    """Create a configured httpx.AsyncClient with retries and strict timeouts."""
    cfg = settings or RadarSettings()
    transport = httpx.AsyncHTTPTransport(retries=cfg.http_max_retries)
    timeout = httpx.Timeout(cfg.http_timeout_seconds, connect=cfg.http_connect_timeout_seconds)
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json, text/html, application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    return httpx.AsyncClient(
        transport=transport,
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    )
