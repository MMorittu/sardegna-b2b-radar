"""Sardegna B2B Tender & Procurement Radar (EDILMORITTU S.R.L.)."""

from __future__ import annotations

__version__ = "1.1.0"

from sardegna_radar.cme import CMEParseResult, CMEParser
from sardegna_radar.config import RadarSettings
from sardegna_radar.exceptions import (
    CMEParseError,
    RadarError,
    RadarNetworkError,
    StorageError,
    UrlValidationError,
)
from sardegna_radar.matcher.cav_engine import CAVScoringEngine, compute_logistics_tier
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    CRMStatus,
    LogisticsTier,
    MatchAssessment,
    NoticeSource,
    NoticeType,
    ProductLine,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
)
from sardegna_radar.storage.repository import RadarRepository

__all__ = [
    "CAVProductCategory",
    "CAVScoringEngine",
    "CMEItem",
    "CMEParseError",
    "CMEParseResult",
    "CMEParser",
    "CRMStatus",
    "LogisticsTier",
    "MatchAssessment",
    "NoticeSource",
    "NoticeType",
    "ProductLine",
    "RadarError",
    "RadarNetworkError",
    "RadarRepository",
    "RadarSettings",
    "SardinianProvince",
    "ScoredLead",
    "StorageError",
    "TenderNotice",
    "UrlValidationError",
    "__version__",
    "compute_logistics_tier",
]
