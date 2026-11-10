"""Hybrid Reverse-API and Adaptive Scrapling connectors."""

from __future__ import annotations

from sardegna_radar.scrapers.anac_api import ANACReverseAPIConnector
from sardegna_radar.scrapers.base import build_async_http_client
from sardegna_radar.scrapers.demo_feed import load_demo_notices
from sardegna_radar.scrapers.sardegna_portals import (
    SardegnaPortalAdaptiveScraper,
    create_scrapling_mcp_server,
)

__all__ = [
    "ANACReverseAPIConnector",
    "SardegnaPortalAdaptiveScraper",
    "build_async_http_client",
    "create_scrapling_mcp_server",
    "load_demo_notices",
]
