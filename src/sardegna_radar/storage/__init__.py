"""Dual-Ready storage layer (local SQLite WAL + cloud Supabase Postgres)."""

from __future__ import annotations

from sardegna_radar.storage.repository import LeadStoreProtocol, RadarRepository, build_repository
from sardegna_radar.storage.supabase_repo import SupabaseRepository

__all__ = [
    "LeadStoreProtocol",
    "RadarRepository",
    "SupabaseRepository",
    "build_repository",
]
