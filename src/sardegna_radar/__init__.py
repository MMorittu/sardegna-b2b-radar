"""Sardegna B2B Tender & Procurement Radar."""

from __future__ import annotations

from sardegna_radar.config import RadarSettings
from sardegna_radar.matcher.cav_engine import CAVScoringEngine, compute_logistics_tier
from sardegna_radar.models import (
    CAVProductCategory,
    LogisticsTier,
    MatchAssessment,
    NoticeSource,
    NoticeType,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
)
from sardegna_radar.storage.repository import RadarRepository

__all__ = [
    "CAVProductCategory",
    "CAVScoringEngine",
    "LogisticsTier",
    "MatchAssessment",
    "NoticeSource",
    "NoticeType",
    "RadarRepository",
    "RadarSettings",
    "SardinianProvince",
    "ScoredLead",
    "TenderNotice",
    "__version__",
    "compute_logistics_tier",
]
__version__ = "0.1.0"
