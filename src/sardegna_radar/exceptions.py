"""Typed exception hierarchy for Sardegna B2B Radar."""

from __future__ import annotations


class RadarError(Exception):
    """Base exception for all Sardegna B2B Radar operational errors."""


class RadarNetworkError(RadarError):
    """Raised when an upstream public procurement or grant endpoint fails."""


class UrlValidationError(RadarError):
    """Raised when a candidate notice URL does not return a valid HTTP 200 page."""


class CMEParseError(RadarError):
    """Raised when a Computo Metrico Estimativo PDF or ZIP cannot be parsed."""


class StorageError(RadarError):
    """Raised when SQLite or Supabase Postgres persistence fails."""
