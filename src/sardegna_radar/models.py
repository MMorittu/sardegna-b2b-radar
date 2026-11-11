"""Domain models and deterministic Italian procurement normalizers (ANAC v2.3 & Catalog)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
import functools
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NoticeSource(StrEnum):
    """Supported live Sardinian & national public procurement feeds (zero demo)."""

    ANAC_OCDS = "anac_ocds"
    SARDEGNACAT = "sardegnacat"
    CUC_LOCALE = "cuc_locale"
    RAS = "ras"
    CCIAA_NUORO = "cciaa_nuoro"


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


class ProductLine(StrEnum):
    """Sardinian Precast & Construction Supplier commercial business lines."""

    LINEA_A = "linea_a"  # Produzione Propria C.A.V. & Vibrocompresso (ATECO 23.61.0 - Tutta Sardegna)
    LINEA_B = "linea_b"  # Rivendita Edile, Inerti, Ferro & Termoidraulica (ATECO 47.52 - <=40km Silanus)


class CRMStatus(StrEnum):
    """Commercial pipeline state preserved across re-scans and synced to Milestone 2 Dashboard."""

    DA_CHIAMARE = "da_chiamare"
    PREVENTIVO_INVIATO = "preventivo_inviato"
    VINTO = "vinto"
    SCARTATO = "scartato"


class CAVProductCategory(StrEnum):
    """Sardinian Precast & Construction Supplier real product catalog categories (Linea A + Linea B + Grants)."""

    # Linea A — Produzione Propria C.A.V. & Vibrocompresso (ATECO 23.61.0)
    PIPES_CULVERTS = "Tubi C.A.V. DN 150-2000 (UNI EN 1916)"
    MANHOLES_CHAMBERS = "Pozzetti, Prolunghe, Chiusini & Caditoie (UNI EN 1917)"
    ROAD_KERBS_PAVING = "Cordonate Stradali & Marciapiedi in Cls (UNI EN 1340)"
    VIBRO_BLOCKS_WALLS = "Blocchi Vibrocompressi Portanti & Muratura (UNI EN 771-3)"
    SPECIAL_PRECAST_CAV = "Betonblock, Plinti Portapali, Abbeveratoi & Canne Fumarie"
    CEMETERY_NICHES = "Loculi Prefabbricati C.A.V. & Edilizia Cimiteriale"

    # Linea B — Rivendita Edile, Inerti, Ferro & Termoidraulica (ATECO 47.52.10 / 47.52.3)
    STEEL_REBAR_MESH = "Ferro Tondino & Rete Elettrosaldata B450C"
    AGGREGATES_INERTI = "Inerti Sfusi (Ghiaia, Pietrisco, Sabbia)"
    PLUMBING_PVC_MULTILAYER = "Tubi Fogna PVC SN4 & Multistrato Termoidraulica"
    BRICKS_MASONRY_BINDERS = "Laterizi Forati, Cemento R32.5, Calce & Malte Ripristino Cls"
    WATERPROOFING_PAINTS = "Guaine Impermeabilizzanti, Idropitture & Fissativi"

    # Bersaglio 3 — Bandi / Contributi PMI & Artigiani (ATECO 23.61.0 / Artisan Registry)
    SME_GRANT_SUBSIDY = "Bandi Fondo Perduto RAS & CCIAA Nuoro (Artigiani / ATECO 23.61.0)"


class LogisticsTier(StrEnum):
    """Road freight tiers measured from Central Sardinia Logistics Hub."""

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
        "digit_thousands_sep": re.compile(r"(?<=\d)[\u00b4'’\u2019\u00a0\u202f]+(?=\d)"),
        "currency_token": re.compile(r"([+-]?\d[\d\.,]*)"),
        "date_dmy": re.compile(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})(?:[T\s]|\b)"),
        "date_ymd": re.compile(r"\b(\d{4})-(\d{2})-(\d{2})(?:[T\s]|\b)"),
        "province_paren": re.compile(r"\b(NU|SS|OR|CA|SU)\b"),
        "piva_11": re.compile(r"^\d{11}$"),
        "cf_16": re.compile(r"^[A-Z]{6}\d{2}[A-Z]\d{2}([A-Z]\d{3})[A-Z]$", re.IGNORECASE),
    }


_PROVINCE_KEYWORDS: tuple[tuple[SardinianProvince, tuple[str, ...]], ...] = (
    (
        SardinianProvince.NU,
        (
            "nuoro",
            "nuorese",
            "silanus",
            "macomer",
            "bolotana",
            "borore",
            "birori",
            "bortigali",
            "lei",
            "noragugume",
            "dualchi",
            "sindia",
            "siniscola",
            "tortoli",
            "tortolì",
            "lanusei",
            "ogliastra",
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
            "atzara",
            "sorgono",
            "tonara",
        ),
    ),
    (
        SardinianProvince.SS,
        (
            "sassari",
            "olbia",
            "gallura",
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
            "medio campidano",
            "sulcis",
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

# Italian VAT provincial office code (digits 8-10 of 11-digit P.IVA) -> (Province code, approx km from Silanus)
_PIVA_OFFICE_TO_SILANUS_KM: dict[str, tuple[str, int]] = {
    "091": ("NU", 38),
    "095": ("OR", 64),
    "090": ("SS", 78),
    "092": ("CA", 155),
}

# Common Sardinian Belfiore municipality codes in 16-char sole-proprietor Codice Fiscale -> (Prov, km from Silanus)
_BELFIORE_TO_SILANUS_KM: dict[str, tuple[str, int]] = {
    "I730": ("NU", 2),    # Silanus
    "A948": ("NU", 11),   # Bolotana
    "E788": ("NU", 15),   # Macomer
    "A987": ("NU", 9),    # Bortigali
    "A880": ("NU", 11),   # Birori
    "A978": ("NU", 16),   # Borore
    "F979": ("NU", 38),   # Nuoro
    "G191": ("NU", 24),   # Ottana
    "I751": ("NU", 85),   # Siniscola
    "D403": ("OR", 28),   # Ghilarza
    "A007": ("OR", 27),   # Abbasanta
    "G113": ("OR", 64),   # Oristano
    "A977": ("SS", 28),   # Bono
    "G203": ("SS", 52),   # Ozieri
    "I452": ("SS", 78),   # Sassari
    "G015": ("SS", 118),  # Olbia
    "A192": ("SS", 88),   # Alghero
    "B354": ("CA", 155),  # Cagliari
    "H118": ("CA", 162),  # Quartu Sant'Elena
    "B745": ("SU", 178),  # Carbonia
    "E281": ("SU", 165),  # Iglesias
}


def estimate_company_distance_from_tax_id(tax_id: str | None) -> tuple[str | None, int | None]:
    """Estimate contractor HQ province & road distance from Silanus using Italian P.IVA or CF."""
    if not tax_id:
        return None, None
    cleaned = re.sub(r"^(?:IT|CF|PIVA)[:\s\-]*", "", tax_id.strip(), flags=re.IGNORECASE).strip()
    patterns = _compiled_normalizers()

    if patterns["piva_11"].match(cleaned):
        office_code = cleaned[7:10]
        if office_code in _PIVA_OFFICE_TO_SILANUS_KM:
            return _PIVA_OFFICE_TO_SILANUS_KM[office_code]
        return "EXTRA_ISOLA", 650

    cf_match = patterns["cf_16"].match(cleaned)
    if cf_match:
        belfiore = cf_match.group(1).upper()
        if belfiore in _BELFIORE_TO_SILANUS_KM:
            return _BELFIORE_TO_SILANUS_KM[belfiore]
        if belfiore.startswith("Z"):
            return "ESTERO", 900
        return "ITALIA", 400

    return None, None


@functools.lru_cache(maxsize=1)
def _compiled_province_patterns() -> tuple[tuple[SardinianProvince, re.Pattern[str]], ...]:
    compiled: list[tuple[SardinianProvince, re.Pattern[str]]] = []
    for province, keywords in _PROVINCE_KEYWORDS:
        ordered = sorted(keywords, key=len, reverse=True)
        joined = "|".join(re.escape(kw) for kw in ordered)
        compiled.append((province, re.compile(rf"\b(?:{joined})\b", re.IGNORECASE)))
    return tuple(compiled)


def _normalize_code(raw: Any, *, kind: str, length: int) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple, set)):
        raw_str = " ".join(str(x) for x in raw if x)
    else:
        raw_str = str(raw)
    if not raw_str.strip():
        return None

    patterns = _compiled_normalizers()
    labeled = patterns[f"{kind}_labeled"].search(raw_str)
    if labeled:
        return labeled.group(1).upper()
    cleaned = re.sub(rf"^\s*{kind}\s*[:\-\[\(]*\s*", "", raw_str.strip(), flags=re.IGNORECASE)
    cleaned = cleaned.strip(" [](){}:;.,")
    if len(cleaned) == length and cleaned.isalnum() and any(ch.isdigit() for ch in cleaned):
        return cleaned.upper()
    match = patterns[kind].search(cleaned)
    return match.group(1).upper() if match else None


def normalize_cig(raw_cig: Any) -> str | None:
    """Normalize an Italian ANAC CIG identifier into a 10-char uppercase alphanumeric string."""
    return _normalize_code(raw_cig, kind="cig", length=10)


def normalize_cup(raw_cup: Any) -> str | None:
    """Normalize an Italian CUP public investment code into a 15-char uppercase string."""
    return _normalize_code(raw_cup, kind="cup", length=15)


def parse_italian_currency(raw: str | float | int | None) -> float | None:
    """Parse Italian/European, ACCA PriMus (`2´981,89`), or plain numbers into clean float."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = raw.strip()
    if not text:
        return None

    patterns = _compiled_normalizers()
    # Normalize ACCA PriMus acute accents (`´`), apostrophes, and thin spaces between digits into dots
    text = patterns["digit_thousands_sep"].sub(".", text)

    match = patterns["currency_token"].search(text)
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
        # In Italian procurement & CMEs, a sole comma is ALWAYS the decimal separator (`0,450` -> `0.45`)
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

    for province, pattern in _compiled_province_patterns():
        if pattern.search(cleaned):
            return province

    return SardinianProvince.REGIONAL


class CMEItem(BaseModel):
    """Single Bill of Quantities (Computo Metrico Estimativo) item matched to Catalog catalog."""

    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True)

    item_number: int | None = None
    tariff_code: str = ""
    description: str = Field(min_length=2)
    unit: str = ""
    quantity: float = 0.0
    unit_price_eur: float | None = None
    total_price_eur: float | None = None
    product_line: ProductLine
    category: CAVProductCategory
    matched_catalog_label: str = ""

    @field_validator("quantity", mode="before")
    @classmethod
    def _validate_qty(cls, value: Any) -> float:
        parsed = parse_italian_currency(value)
        return parsed if parsed is not None else 0.0

    @field_validator("unit_price_eur", "total_price_eur", mode="before")
    @classmethod
    def _validate_prices(cls, value: Any) -> float | None:
        return parse_italian_currency(value)


class TenderNotice(BaseModel):
    """Normalized public procurement notice, ANAC v2.3 contract award, or regional SME grant."""

    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True)

    external_id: str = Field(min_length=1)
    source: NoticeSource
    notice_type: NoticeType = NoticeType.PUBLIC_WORKS_TENDER
    title: str = Field(min_length=3)
    description: str = ""
    contracting_authority: str = "Ente Appaltante Regione Sardegna"
    delegated_authority: str | None = None
    cig: str | None = None
    cup: str | None = None
    cpv_codes: list[str] = Field(default_factory=list)
    amount_eur: float | None = None
    award_amount_eur: float | None = None
    discount_pct: float | None = None
    published_date: date | None = None
    deadline_date: date | None = None
    award_date: date | None = None
    municipality: str | None = None
    province: SardinianProvince = SardinianProvince.REGIONAL
    winner_company: str | None = None
    winner_tax_id: str | None = None
    winner_province: str | None = None
    winner_distance_km: int | None = None
    rup_name: str | None = None
    contract_started: bool | None = None
    has_subcontracts: bool | None = None
    url: str = ""
    attachment_url: str | None = None
    http_status: int | None = None

    @field_validator("cig", mode="before")
    @classmethod
    def _validate_cig(cls, value: Any) -> str | None:
        return normalize_cig(str(value)) if value is not None else None

    @field_validator("cup", mode="before")
    @classmethod
    def _validate_cup(cls, value: Any) -> str | None:
        return normalize_cup(str(value)) if value is not None else None

    @field_validator("amount_eur", "award_amount_eur", "discount_pct", mode="before")
    @classmethod
    def _validate_amounts(cls, value: Any) -> float | None:
        return parse_italian_currency(value)

    @field_validator("published_date", "deadline_date", "award_date", mode="before")
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

    @model_validator(mode="after")
    def _populate_winner_distance(self) -> TenderNotice:
        if self.winner_tax_id and (self.winner_distance_km is None or self.winner_province is None):
            prov, km = estimate_company_distance_from_tax_id(self.winner_tax_id)
            if self.winner_province is None and prov is not None:
                self.winner_province = prov
            if self.winner_distance_km is None and km is not None:
                self.winner_distance_km = km
        return self


class MatchAssessment(BaseModel):
    """Deterministic Catalog relevance score, matched catalog lines, and Silanus logistics."""

    score: float = Field(ge=0.0, le=100.0)
    matched_categories: list[CAVProductCategory] = Field(default_factory=list)
    matched_lines: list[ProductLine] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    negative_flags: list[str] = Field(default_factory=list)
    cpv_bonus_applied: bool = False
    priority_unstarted_award: bool = False
    logistics_tier: LogisticsTier = LogisticsTier.TIER_2_CENTRAL
    estimated_distance_km: int | None = None
    recommended_action: str = "Monitoraggio commerciale"
    rationale: str = ""


class ScoredLead(BaseModel):
    """Complete B2B commercial lead combining TenderNotice, MatchAssessment, CMEItems, and CRM state."""

    notice: TenderNotice
    assessment: MatchAssessment
    cme_items: list[CMEItem] = Field(default_factory=list)
    crm_status: CRMStatus = CRMStatus.DA_CHIAMARE
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notified: bool = False

    @property
    def is_high_priority(self) -> bool:
        """Return True if the lead exceeds the commercial action threshold (>= 45/100)."""
        return self.assessment.score >= 45.0

    @property
    def dedup_key(self) -> str:
        """Canonical idempotency key preferring national CIG when available."""
        if self.notice.cig:
            return f"cig:{self.notice.cig}"
        return f"{self.notice.source.value}:{self.notice.external_id}"
