"""Sardinian Precast & Construction Supplier deterministic Gate-1 (Hard Exclusions) & Gate-2 (Linea A / Linea B) rules."""

from __future__ import annotations

from dataclasses import dataclass
import functools
import re

from sardegna_radar.models import CAVProductCategory, ProductLine


@dataclass(frozen=True, slots=True)
class CatalogRule:
    product_line: ProductLine
    category: CAVProductCategory
    label: str
    pattern: re.Pattern[str]
    weight: float


@dataclass(frozen=True, slots=True)
class ExclusionRule:
    label: str
    pattern: re.Pattern[str]


_CUBIC_METER_UNITS = {"m³", "m3", "mc", "m.c."}


@functools.lru_cache(maxsize=1)
def compiled_cme_exclusions() -> tuple[ExclusionRule, ...]:
    """Gate 1 rules evaluated BEFORE any positive catalog rule on a CME item specification."""
    raw: tuple[tuple[str, str], ...] = (
        (
            "Lavorazione pura (demolizione/rimozione/scavo/discarica)",
            r"^\s*(?:[\w'’]+\s+e\s+)?(?:rimozion[ei]|demolizion[ei]|asportazion[ei]|"
            r"spicconatur[ae]|raschiatur[ae]|scav[oi]|scarifica|fresatura|lievo|smontaggio|"
            r"trasporto\s+a\s+discarica|conferimento\s+a\s+discarica|"
            r"caratterizzazione\s+tal\s+quale|sistemazione\s+degli\s+esistenti|"
            r"pulizia\s+e\s+diserbo|taglio\s+di\s+erba)",
        ),
        (
            "Pietra naturale (basalto/marmo/granito/travertino/porfido)",
            r"\b(?:basalto|marmo(?:\s+bianco)?(?:\s+di\s+orosei)?|granit[oi]|travertino|"
            r"porfido|trachite|pietra\s+naturale|materiale\s+lapideo|lastre\s+di\s+pietra|"
            r"cubetti\s+di\s+porfido|selciat[oi]\s+in\s+basalto)\b",
        ),
        (
            "Calcestruzzo preconfezionato liquido da autobetoniera (> 1 t)",
            r"\b(?:autobetonier[ae]|calcestruzzo\s+preconfezionato|conglomerato\s+cementizio|"
            r"(?:fornitura\s+e\s+)?getto\s+(?:in|di)\s+(?:calcestruzzo|conglomerato)|"
            r"(?:classe\s+(?:di\s+)?)?consistenza\s+s[345]|\bs4\s*/\s*s5\b|"
            r"calcestruzzo\s+per\s+opere\s+(?:non\s+)?strutturali|"
            r"magroni\s+di\s+sottofondazione|calcestruzzo\s+fresco)\b",
        ),
    )
    return tuple(ExclusionRule(label=lbl, pattern=re.compile(pat, re.IGNORECASE)) for lbl, pat in raw)


@functools.lru_cache(maxsize=1)
def compiled_catalog_rules() -> tuple[CatalogRule, ...]:
    """Gate 2 positive matching rules strictly grounded in Sardinian Precast & Construction Supplier COMPANY_DATA.md."""
    raw: tuple[tuple[ProductLine, CAVProductCategory, str, str, float], ...] = (
        # ==================== LINEA A: Produzione Propria C.A.V. & Vibrocompresso ====================
        (
            ProductLine.LINEA_A,
            CAVProductCategory.PIPES_CULVERTS,
            "Tubi circolari C.A.V. DN 150-2000 (UNI EN 1916)",
            r"\b(?:tubi|tubazioni|condott[ae]|collettor[ei])\s+(?:circolari\s+)?(?:in\s+)?"
            r"(?:c\.?\s*a\.?\s*v\.?|calcestruzzo(?:\s+armato)?(?:\s+vibrocompresso)?|"
            r"cemento\s+fibrorinforzat[oi]|uni\s*en\s*1916)|"
            r"\bscatolar[ei]\s+prefabbricat[oi]\s+in\s+c\.?a\.?v?\.?\b",
            36.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.MANHOLES_CHAMBERS,
            "Pozzetti cls, prolunghe, chiusini & caditoie (UNI EN 1917)",
            r"\b(?:pozzett[oi]\s+(?:prefabbricat[oi]|d['’\s]?ispezione|stradal[ei]|sifonat[oi]|in\s+calcestruzzo|in\s+c\.?a\.?v\.?)|"
            r"prolung(?:a|he)\s+per\s+pozzett[oi]|caditoi[ae]\s+stradal[ei]|"
            r"chiusin[oi]\s+e\s+caditoi[ae]|camere\s+d['’\s]?ispezione\s+prefabbricat[ae]|uni\s*en\s*1917)\b",
            34.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.ROAD_KERBS_PAVING,
            "Cordonate stradali & marciapiedi in calcestruzzo (UNI EN 1340)",
            r"\b(?:(?:cordol[oi]|cordonat[ae])\s+(?:stradal[ei]\s+|per\s+marciapied[ei]\s+)?"
            r"(?:prefabbricat[oi]\s+)?(?:in\s+)?(?:calcestruzzo|cemento|c\.?a\.?v\.?|vibrocompress[oi])|"
            r"cunett[ae]\s+(?:alla\s+francese\s+)?(?:in\s+calcestruzzo|prefabbricat[ae])|uni\s*en\s*1340)\b",
            30.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.VIBRO_BLOCKS_WALLS,
            "Blocchi vibrocompressi portanti/tamponatura (UNI EN 771-3)",
            r"\b(?:blocchi\s+(?:portanti\s+|da\s+tamponatura\s+|multiforo\s+|ad\s+incastro\s+|doppia\s+camera\s+)?"
            r"(?:in\s+)?(?:calcestruzzo\s+vibrocompresso|vibrocompress[oi]|cemento|cls)|"
            r"muratura\s+in\s+blocchi\s+di\s+(?:calcestruzzo|cemento)|uni\s*en\s*771[\-\s]*3)\b",
            30.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.SPECIAL_PRECAST_CAV,
            "Betonblock, plinti portapali, abbeveratoi C.A.V. & canne fumarie",
            r"\b(?:betonblock|blocchi\s+modulari\s+(?:in\s+cls|per\s+muri\s+di\s+contenimento)|"
            r"(?:plint[oi]|basament[oi])\s+(?:prefabbricat[oi]\s+)?portapal[oi]|"
            r"abbeveratoi[o]?\s+(?:monolitic[oi]|in\s+c\.?a\.?v\.?|prefabbricat[oi]|in\s+calcestruzzo)|"
            r"cann[ae]\s+fumari[ae]\s+(?:refrattari[ae]|in\s+pomicemento|uni\s*en\s*1858))\b",
            32.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.CEMETERY_NICHES,
            "Loculi prefabbricati C.A.V. & manufatti cimiteriali",
            r"\b(?:locul[oi]\s+prefabbricat[oi]|colombar[io]\s+prefabbricat[oi]|"
            r"ossar[io]\s+prefabbricat[oi]|cellette\s+ossario\s+in\s+c\.?a\.?v\.?)\b",
            34.0,
        ),
        # ==================== LINEA B: Rivendita Edile, Inerti, Ferro & Termoidraulica ====================
        (
            ProductLine.LINEA_B,
            CAVProductCategory.STEEL_REBAR_MESH,
            "Rete elettrosaldata & tondino B450C",
            r"\b(?:rete\s+elettrosaldata|acciaio\s+b450c|tondino\s+(?:in\s+acciaio|b450c)|"
            r"barre\s+di\s+acciaio\s+b450c|armatura\s+in\s+acciaio\s+ad\s+aderenza)\b",
            22.0,
        ),
        (
            ProductLine.LINEA_B,
            CAVProductCategory.AGGREGATES_INERTI,
            "Inerti sfusi (ghiaia, pietrisco, sabbia)",
            r"\b(?:fornitura\s+(?:e\s+posa\s+(?:in\s+opera\s+)?)?di\s+(?:ghiaia|pietrisco|sabbia|misto\s+granulare)|"
            r"\bghiaia\b|\bpietrisco\b|\bsabbia\s+lavata\b)\b",
            18.0,
        ),
        (
            ProductLine.LINEA_B,
            CAVProductCategory.PLUMBING_PVC_MULTILAYER,
            "Tubi fogna PVC SN4 & multistrato termoidraulico",
            r"\b(?:tub[oi]\s+(?:fogna\s+)?(?:in\s+)?pvc(?:\s+rigido)?(?:\s+sn[48])?|uni\s*en\s*1401|"
            r"tub[oi]\s+multistrato(?:\s+isolato)?)\b",
            20.0,
        ),
        (
            ProductLine.LINEA_B,
            CAVProductCategory.BRICKS_MASONRY_BINDERS,
            "Mattoni forati, cemento R32.5, calce & malte tecniche ripristino cls",
            r"\b(?:mattoni\s+(?:laterizi\s+)?forati|muratura\s+in\s+mattoni\s+laterizi|"
            r"risanamento\s+di\s+calcestruzzo|malta\s+(?:premiscelata|tixotropica|fibrorinforzata|cementizia\s+r\s*32\.5)|"
            r"rasatura\s+in\s+malta\s+premiscelata|intonaco\s+civile\s+formato|"
            r"cemento\s+r\s*32\.5|calce\s+idrata)\b",
            20.0,
        ),
        (
            ProductLine.LINEA_B,
            CAVProductCategory.WATERPROOFING_PAINTS,
            "Guaine impermeabilizzanti (bituminose/liquide), idropitture & fissativi",
            r"\b(?:manto\s+impermeabile|me[mn]?bran[ae]\s+(?:prefabbricat[ae]\s+)?elastoplastomeric(?:a|he)|"
            r"guain[ae]\s+(?:liquida\s+poliuretanica|bituminosa|impermeabilizzante)|"
            r"impermeabilizzazione\s+di\s+superfici.*guaina|"
            r"tinteggiatura\s+con\s+pittura|pittura\s+al\s+quarzo|idropittur[ae]|"
            r"mano\s+di\s+fissativo|impregnante\s+protettivo\s+trasparente)\b",
            18.0,
        ),
    )
    return tuple(
        CatalogRule(
            product_line=line,
            category=cat,
            label=lbl,
            pattern=re.compile(pat, re.IGNORECASE | re.DOTALL),
            weight=w,
        )
        for line, cat, lbl, pat, w in raw
    )


def check_cme_hard_exclusion(spec_text: str, unit: str = "", quantity: float = 0.0) -> str | None:
    """Return the exclusion reason if a CME item violates Catalog's hard boundaries, else None."""
    cleaned = spec_text.strip()
    if not cleaned:
        return "Descrizione vuota"

    for rule in compiled_cme_exclusions():
        if rule.pattern.search(cleaned):
            return rule.label

    # Extra guard: poured cast-in-place concrete in m³ > 0.45 m³ (~1 metric ton micro-batch limit)
    norm_unit = re.sub(r"\s+", "", unit.lower())
    if norm_unit in _CUBIC_METER_UNITS and quantity > 0.45:
        if re.search(r"\b(?:calcestruzzo|conglomerato)\b", cleaned, re.IGNORECASE):
            if not re.search(
                r"\b(?:prefabbricat[oi]|vibrocompress[oi]|pozzett[oi]|tub[oi]|blocchi|ghiaia|pietrisco|sabbia)\b",
                cleaned,
                re.IGNORECASE,
            ):
                return "Getto calcestruzzo liquido > 1 t (no centrale autobetoniere)"

    return None


def classify_cme_spec(spec_text: str, unit: str = "", quantity: float = 0.0) -> CatalogRule | None:
    """Apply Gate 1 (Hard Exclusions) then Gate 2 (Linea A / Linea B) to a single CME item."""
    if check_cme_hard_exclusion(spec_text, unit=unit, quantity=quantity) is not None:
        return None

    for rule in compiled_catalog_rules():
        if rule.pattern.search(spec_text):
            return rule
    return None
