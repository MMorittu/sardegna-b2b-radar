"""Domain models and deterministic Italian procurement normalizers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
import functools
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoticeSource(StrEnum):
    """Supported Sardinian & national public procurement feeds."""

    ANAC_OCDS = "anac_ocds"
    SARDEGNACAT = "sardegnacat"
    RAS = "ras"
    CCIAA_NUORO = "cciaa_nuoro"
    DEMO = "demo"


class NoticeType(StrEnum):
    """Classification of procurement or regional grant opportunities."""

    PUBLIC_WORKS_TENDER = "public_works_tender"
    CONTRACT_AWARD = "contract_award"
    REGIONAL_GRANT = "regional_grant"
    SUPPLY_TENDER = "supply_tender"


class SardinianProvince(StrEnum):
    """Sardinian provinces with regional fallback."""

    NU = "NU"
    SS = "SS"
    OR = "OR"
    CA = "CA"
    SU = "SU"
    REGIONAL = "REGIONAL"


class CAVProductCategory(StrEnum):
    """Certified vibro-compressed concrete (C.A.V.) & regional SME grant product lines."""

    PIPES_CULVERTS = "Tubi C.A.V. & Condotte Idriche/Fognarie"
    MANHOLES_CHAMBERS = "Pozzetti, Caditoie & Camere d'Ispezione"
    ROAD_KERBS_PAVING = "Cordoli Stradali, Cunette & Barriere"
    VIBRO_BLOCKS_WALLS = "Blocchi Vibrocompressi & Murature"
    CEMETERY_NICHES = "Loculi Prefabbricati & Edilizia Cimiteriale"
    SME_GRANT_SUBSIDY = "Bandi Regionali RAS / SIPES / PID Imprese"


class LogisticsTier(StrEnum):
    """Road freight tiers measured from the Central Sardinia industrial hub (Silanus, NU)."""

    TIER_1_CORE = "Tier 1 (<40 km da Silanus: Marghine, Goceano, Nuorese, Alto Oristanese)"
    TIER_2_CENTRAL = "Tier 2 (40-100 km da Silanus: Sassarese, Oristano, Ogliastra, Gallura Sud)"
    TIER_3_ISLAND = "Tier 3 (>100 km da Silanus: Cagliari, Sulcis, Basso Campidano, Alta Gallura)"


@functools.lru_cache(maxsize=1)
def _compiled_normalizers() -> dict[str, re.Pattern[str]]:
    return {
        "cig_labeled": re.compile(r"\bcig\b[^A-Z0-9]{0,10}([A-Z0-9]{10})\b", re.IGNORECASE),
        "cig": re.compile(r"\b(?=[A-Z0-9]*\d)([A-Z0-9]{10})\b", re.IGNORECASE),
        "cup_labeled": re.compile(r"\bcup\b[^A-Z0-9]{0,10}([A-Z0-9]{15})\b", re.IGNORECASE),
        "cup": re.compile(r"\b(?=[A-Z0-9]*\d)([A-Z0-9]{15})\b", re.IGNORECASE),
        "currency_token": re.compile(r"(\d[\d\.,]*)"),
        "date_dmy": re.compile(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b"),
        "date_ymd": re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
        "province_paren": re.compile(r"\b(NU|SS|OR|CA|SU)\b"),
    }


_PROVINCE_KEYWORDS: tuple[tuple[SardinianProvince, tuple[str, ...]], ...] = (
    (
        SardinianProvince.NU,
        (
            "nuoro",
            "silanus",
            "macomer",
            "bolotana",
            "borore",
            "birori",
            "bortigali",
            "lei",
            "noragugume",
            "dualtchi",
            "dualchi",
            "siniscola",
            "tortoli",
            "tortolì",
            "lanusei",
            "dorgali",
            "orgosolo",
            "oliena",
            "gavoi",
            "fonni",
            "bitti",
            "orosei",
            "ottana",
            "orotelli",
            "orani",
            "sarule",
            "mamoiada",
        ),
    ),
    (
        SardinianProvince.SS,
        (
            "sassari",
            "olbia",
            "alghero",
            "porto torres",
            "ozieri",
            "bono",
            "bottidda",
            "burgos",
            "esporlatu",
            "illorai",
            "benetutti",
            "bultei",
            "anela",
            "pattada",
            "mores",
            "thiesi",
            "bonorva",
            "pozzomaggiore",
            "tempio pausania",
            "arzachena",
            "sorso",
            "ittiri",
        ),
    ),
    (
        SardinianProvince.OR,
        (
            "oristano",
            "ghilarza",
            "abbasanta",
            "paulilatino",
            "sedilo",
            "aidomaggiore",
            "norbello",
            "bosa",
            "sunia",
            "suni",
            "cuglieri",
            "scano di montiferro",
            "terralba",
            "cabras",
            "marrubiu",
            "mogoro",
            "ales",
            "samugheo",
        ),
    ),
    (
        SardinianProvince.CA,
        (
            "cagliari",
            "quartu sant'elena",
            "quartu",
            "assemini",
            "selargius",
            "monserrato",
            "capoterra",
            "sestu",
            "sinnai",
            "elmas",
            "decimomannu",
            "uta",
            "sarroch",
            "pula",
        ),
    ),
    (
        SardinianProvince.SU,
        (
            "sud sardegna",
            "carbonia",
            "iglesias",
            "villacidro",
            "sanluri",
            "guspini",
            "sant'antioco",
            "isili",
            "senorbì",
            "muravera",
            "villaputzu",
            "san gavino monreale",
        ),
    ),
)


def normalize_cig(raw_cig: str | None) -> str | None:
    """Normalize an Italian ANAC CIG identifier into a 10-char uppercase alphanumeric string."""
    if not raw_cig:
        return None
    patterns = _compiled_normalizers()
    labeled = patterns["cig_labeled"].search(raw_cig)
    if labeled:
        return labeled.group(1).upper()
    cleaned = re.sub(r"^\s*cig\s*[:\-\[\(]*\s*", "", raw_cig.strip(), flags=re.IGNORECASE)
    cleaned = cleaned.strip(" [](){}:;.,")
    if len(cleaned) == 10 and cleaned.isalnum() and any(ch.isdigit() for ch in cleaned):
        return cleaned.upper()
    match = patterns["cig"].search(cleaned)
    return match.group(1).upper() if match else None


def normalize_cup(raw_cup: str | None) -> str | None:
    """Normalize an Italian CUP public investment code into a 15-char uppercase string."""
    if not raw_cup:
        return None
    patterns = _compiled_normalizers()
    labeled = patterns["cup_labeled"].search(raw_cup)
    if labeled:
        return labeled.group(1).upper()
    cleaned = re.sub(r"^\s*cup\s*[:\-\[\(]*\s*", "", raw_cup.strip(), flags=re.IGNORECASE)
    cleaned = cleaned.strip(" [](){}:;.,")
    if len(cleaned) == 15 and cleaned.isalnum() and any(ch.isdigit() for ch in cleaned):
        return cleaned.upper()
    match = patterns["cup"].search(cleaned)
    return match.group(1).upper() if match else None


def parse_italian_currency(raw: str | float | int | None) -> float | None:
    """Parse Italian/European or plain monetary amounts into clean float EUR."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = raw.strip()
    if not text:
        return None

    match = _compiled_normalizers()["currency_token"].search(text)
    if not match:
        return None

    token = match.group(1).strip(".,")
    if not token:
        return None

    if "," in token and "." in token:
        if token.rfind(",") > token.rfind("."):
            normalized = token.replace(".", "").replace(",", ".")
        else:
            normalized = token.replace(",", "")
    elif "," in token:
        parts = token.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            normalized = token.replace(",", "")
        else:
            normalized = token.replace(",", ".")
    elif "." in token:
        parts = token.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
            normalized = token.replace(".", "")
        else:
            normalized = token
    else:
        normalized = token

    try:
        return float(normalized)
    except ValueError:
        return None


def parse_italian_date(raw: str | date | datetime | None) -> date | None:
    """Parse Italian (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY) or ISO (YYYY-MM-DD) dates."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw

    text = raw.strip()
    if not text:
        return None

    patterns = _compiled_normalizers()
    ymd_match = patterns["date_ymd"].search(text)
    if ymd_match:
        try:
            return date(int(ymd_match.group(1)), int(ymd_match.group(2)), int(ymd_match.group(3)))
        except ValueError:
            return None

    dmy_match = patterns["date_dmy"].search(text)
    if dmy_match:
        try:
            return date(int(dmy_match.group(3)), int(dmy_match.group(2)), int(dmy_match.group(1)))
        except ValueError:
            return None

    return None


def resolve_sardinian_province(hint: str | SardinianProvince | None) -> SardinianProvince:
    """Resolve a municipality, contracting authority, or province code to a SardinianProvince."""
    if isinstance(hint, SardinianProvince):
        return hint
    if not hint or not hint.strip():
        return SardinianProvince.REGIONAL

    cleaned = hint.strip()
    upper = cleaned.upper()
    if upper in ("NU", "SS", "OR", "CA", "SU", "REGIONAL"):
        return SardinianProvince(upper)

    paren_match = _compiled_normalizers()["province_paren"].search(cleaned)
    if paren_match:
        return SardinianProvince(paren_match.group(1))

    lowered = cleaned.lower()
    for province, keywords in _PROVINCE_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return province

    return SardinianProvince.REGIONAL


class TenderNotice(BaseModel):
    """Normalized public procurement notice, contract award, or regional SME grant."""

    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True)

    external_id: str = Field(min_length=1)
    source: NoticeSource
    notice_type: NoticeType = NoticeType.PUBLIC_WORKS_TENDER
    title: str = Field(min_length=3)
    description: str = ""
    contracting_authority: str = "Ente Appaltante Regione Sardegna"
    cig: str | None = None
    cup: str | None = None
    cpv_codes: list[str] = Field(default_factory=list)
    amount_eur: float | None = None
    published_date: date | None = None
    deadline_date: date | None = None
    municipality: str | None = None
    province: SardinianProvince = SardinianProvince.REGIONAL
    winner_company: str | None = None
    url: str = ""

    @field_validator("cig", mode="before")
    @classmethod
    def _validate_cig(cls, value: Any) -> str | None:
        return normalize_cig(str(value)) if value is not None else None

    @field_validator("cup", mode="before")
    @classmethod
    def _validate_cup(cls, value: Any) -> str | None:
        return normalize_cup(str(value)) if value is not None else None

    @field_validator("amount_eur", mode="before")
    @classmethod
    def _validate_amount(cls, value: Any) -> float | None:
        return parse_italian_currency(value)

    @field_validator("published_date", "deadline_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: Any) -> date | None:
        return parse_italian_date(value)

    @field_validator("cpv_codes", mode="before")
    @classmethod
    def _validate_cpv_codes(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [c.strip() for c in value.split(",") if c.strip()]
        return [str(c).strip() for c in value if str(c).strip()]

    @field_validator("province", mode="before")
    @classmethod
    def _validate_province(cls, value: Any, info: Any) -> SardinianProvince:
        resolved = resolve_sardinian_province(str(value) if value is not None else None)
        if resolved != SardinianProvince.REGIONAL:
            return resolved
        data = info.data or {}
        for fallback_field in ("municipality", "contracting_authority", "title"):
            fallback_val = data.get(fallback_field)
            if fallback_val:
                candidate = resolve_sardinian_province(str(fallback_val))
                if candidate != SardinianProvince.REGIONAL:
                    return candidate
        return SardinianProvince.REGIONAL


class MatchAssessment(BaseModel):
    """Deterministic C.A.V. relevance score, matched catalog lines, and Silanus road logistics."""

    score: float = Field(ge=0.0, le=100.0)
    matched_categories: list[CAVProductCategory] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    negative_flags: list[str] = Field(default_factory=list)
    cpv_bonus_applied: bool = False
    logistics_tier: LogisticsTier = LogisticsTier.TIER_2_CENTRAL
    estimated_distance_km: int | None = None
    recommended_action: str = "Monitoraggio commerciale"
    rationale: str = ""


class ScoredLead(BaseModel):
    """Complete B2B commercial lead combining a normalized TenderNotice with its MatchAssessment."""

    notice: TenderNotice
    assessment: MatchAssessment
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notified: bool = False

    @property
    def is_high_priority(self) -> bool:
        """Return True if the lead exceeds the commercial action threshold (>= 45/100)."""
        return self.assessment.score >= 45.0

    @property
    def dedup_key(self) -> str:
        """Canonical idempotency key combining source and CIG/external_id."""
        identifier = self.notice.cig or self.notice.external_id
        return f"{self.notice.source.value}:{identifier}"
