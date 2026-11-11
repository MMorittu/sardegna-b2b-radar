"""EDILMORITTU S.R.L. (Silanus, NU) Linea A & Linea B scoring engine with Hard Exclusions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import functools
import re

from sardegna_radar.cme.catalog_rules import compiled_catalog_rules
from sardegna_radar.models import (
    CAVProductCategory,
    CMEItem,
    LogisticsTier,
    MatchAssessment,
    NoticeType,
    ProductLine,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
)


@dataclass(frozen=True, slots=True)
class _NoticeRule:
    product_line: ProductLine | None
    category: CAVProductCategory
    label: str
    pattern: re.Pattern[str]
    weight: float


@dataclass(frozen=True, slots=True)
class _NegativeRule:
    label: str
    pattern: re.Pattern[str]
    penalty: float
    hard_block: bool = False


# Road distance in km from EDILMORITTU S.R.L. plant (SS 129 km 82,200, Silanus NU)
_SILANUS_DISTANCE_KM: dict[str, int] = {
    "silanus": 2,
    "lei": 6,
    "bortigali": 9,
    "bolotana": 11,
    "birori": 11,
    "dualchi": 13,
    "noragugume": 14,
    "macomer": 15,
    "borore": 16,
    "sindia": 23,
    "ottana": 24,
    "illorai": 24,
    "sedilo": 25,
    "aidomaggiore": 26,
    "orotelli": 26,
    "abbasanta": 27,
    "norbello": 27,
    "ghilarza": 28,
    "bono": 28,
    "esporlatu": 29,
    "bottidda": 30,
    "burgos": 31,
    "pauli latino": 32,
    "paulilatino": 32,
    "orani": 32,
    "sarule": 34,
    "bonorva": 35,
    "nuoro": 38,
    "mamoiada": 44,
    "thiesi": 46,
    "bosa": 48,
    "ozieri": 52,
    "oristano": 64,
    "dorgali": 68,
    "orosei": 72,
    "sassari": 78,
    "siniscola": 85,
    "alghero": 88,
    "lanusei": 92,
    "porto torres": 95,
    "tortoli": 98,
    "tortolì": 98,
    "tempio pausania": 112,
    "sanluri": 115,
    "olbia": 118,
    "villacidro": 128,
    "arzachena": 138,
    "assemini": 148,
    "cagliari": 155,
    "quartu sant'elena": 162,
    "iglesias": 165,
    "carbonia": 178,
}

_CPV_PREFIX_WEIGHTS: dict[str, tuple[float, ProductLine, CAVProductCategory, str]] = {
    "45231300": (24.0, ProductLine.LINEA_A, CAVProductCategory.PIPES_CULVERTS, "CPV Condotte idriche e fognarie"),
    "45232410": (22.0, ProductLine.LINEA_A, CAVProductCategory.PIPES_CULVERTS, "CPV Opere di fognatura"),
    "44114200": (25.0, ProductLine.LINEA_A, CAVProductCategory.MANHOLES_CHAMBERS, "CPV Prodotti in calcestruzzo"),
    "44163100": (20.0, ProductLine.LINEA_A, CAVProductCategory.PIPES_CULVERTS, "CPV Tubi e raccordi condotte"),
    "45233140": (18.0, ProductLine.LINEA_A, CAVProductCategory.ROAD_KERBS_PAVING, "CPV Lavori stradali"),
    "45233222": (18.0, ProductLine.LINEA_A, CAVProductCategory.ROAD_KERBS_PAVING, "CPV Marciapiedi e pavimentazioni"),
    "45215400": (26.0, ProductLine.LINEA_A, CAVProductCategory.CEMETERY_NICHES, "CPV Lavori cimiteriali"),
}


@functools.lru_cache(maxsize=1)
def _compiled_notice_rules() -> tuple[_NoticeRule, ...]:
    rules: list[_NoticeRule] = [
        _NoticeRule(
            product_line=r.product_line,
            category=r.category,
            label=r.label,
            pattern=r.pattern,
            weight=r.weight,
        )
        for r in compiled_catalog_rules()
    ]
    # Broader tender-title civil works signals (since tender titles rarely list tariff codes)
    extra: tuple[tuple[ProductLine | None, CAVProductCategory, str, str, float], ...] = (
        (
            ProductLine.LINEA_A,
            CAVProductCategory.PIPES_CULVERTS,
            "Rete fognaria / acquedotto / acque meteoriche",
            r"\b(?:collettore\s+fognario|condotta\s+fognaria|rete\s+fognaria|condotta\s+idrica|"
            r"acquedott[oi]|acque\s+bianche|acque\s+meteoriche|fognatur[ae]|mitigazione\s+rischio\s+idraulico)\b",
            28.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.MANHOLES_CHAMBERS,
            "Pozzetti / caditoie / griglie stradali",
            r"\b(?:pozzett[oi]|caditoi[ae]|chiusin[oi]|regimazione\s+acque)\b",
            24.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.ROAD_KERBS_PAVING,
            "Cordoli / marciapiedi / sistemazione stradale",
            r"\b(?:rifacimento\s+marciapied[ei]|messa\s+in\s+sicurezza\s+viabilit[àa]|"
            r"cordol[oi]\s+stradal[ei]|cunett[ae]\s+alla\s+francese)\b",
            20.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.CEMETERY_NICHES,
            "Edilizia cimiteriale / ampliamento cimitero",
            r"\b(?:ampliamento\s+cimitero|cimitero\s+comunale|edilizia\s+cimiteriale|loculi|colombari)\b",
            28.0,
        ),
        (
            ProductLine.LINEA_A,
            CAVProductCategory.SPECIAL_PRECAST_CAV,
            "Pubblica illuminazione (plinti) / infrastrutture rurali (abbeveratoi)",
            r"\b(?:pubblica\s+illuminazione|muri\s+di\s+contenimento|viabilit[àa]\s+rurale|zootecni[ca])\b",
            18.0,
        ),
        (
            None,
            CAVProductCategory.SME_GRANT_SUBSIDY,
            "Bandi Fondo Perduto RAS & CCIAA Nuoro (Artigiani / ATECO 23.61.0)",
            r"\b(?:contribut[oi]\s+a\s+fondo\s+perduto|bando\s+doppia\s+transizione|"
            r"imprese\s+artigiane|albo\s+artigiani|voucher\s+digital[ei]|transizione\s+ecologica|"
            r"investimenti\s+produttivi|acquisto\s+macchinari|efficientamento\s+energetico\s+imprese|"
            r"ateco\s*23|manifatturier[eo]|sipes|cciaa\s+nuoro|camera\s+di\s+commercio\s+di\s+nuoro)\b",
            36.0,
        ),
    )
    for line, cat, lbl, pat, w in extra:
        rules.append(_NoticeRule(line, cat, lbl, re.compile(pat, re.IGNORECASE), w))
    return tuple(rules)


@functools.lru_cache(maxsize=1)
def _compiled_negative_rules() -> tuple[_NegativeRule, ...]:
    raw_negatives: tuple[tuple[str, str, float, bool], ...] = (
        # Hard Exclusions (Edilmorittu anti-false-positives)
        (
            "Esclusione rigida: Pietra naturale (basalto/marmo/granito/travertino/porfido)",
            r"\b(?:basalto|marmo(?:\s+di\s+orosei)?|granit[oi]|travertino|porfido|trachite|pietra\s+naturale|materiale\s+lapideo)\b",
            65.0,
            True,
        ),
        (
            "Esclusione rigida: Fornitura cls preconfezionato liquido / autobetoniere",
            r"\b(?:fornitura\s+(?:di\s+)?(?:calcestruzzo|conglomerato\s+cementizio)|autobetonier[ae]|"
            r"calcestruzzo\s+(?:preconfezionato|liquido)|(?:classe\s+(?:di\s+)?)?consistenza\s+s[345]|\bs4\s*/\s*s5\b)\b",
            70.0,
            True,
        ),
        (
            "Esclusione rigida: Sola demolizione / rimozione / bonifica / discarica",
            r"^\s*(?:lavori\s+di\s+|intervent[oi]\s+di\s+|affidamento\s+(?:dei\s+)?lavori\s+di\s+)?"
            r"(?:demolizion[ei]|rimozion[ei]|bonifica\s+amianto|conferimento\s+a\s+discarica)\b",
            65.0,
            True,
        ),
        # Non-construction domains
        (
            "Forniture sanitarie / medicali",
            r"\b(?:dispositivi\s+medici|ospedalier[oi]|farmaci|chirurgic[oi]|endotracheal[ei]|diagnostica|ausili\s+sanitari)\b",
            65.0,
            True,
        ),
        (
            "Servizi IT / software puro",
            r"\b(?:licenze\s+software|cloud\s+saas|help\s+desk|cybersecurity|sviluppo\s+software)\b",
            55.0,
            True,
        ),
        (
            "Ristorazione / pulizia / servizi sociali",
            r"\b(?:mensa\s+scolastica|ristorazione\s+collettiva|pulizia\s+immobili|assistenza\s+domiciliare|educativ[oi]|trasporto\s+scolastico)\b",
            60.0,
            True,
        ),
    )
    return tuple(
        _NegativeRule(label=lbl, pattern=re.compile(pat, re.IGNORECASE), penalty=pen, hard_block=hb)
        for lbl, pat, pen, hb in raw_negatives
    )


@functools.lru_cache(maxsize=1)
def _compiled_town_distances() -> tuple[tuple[re.Pattern[str], int], ...]:
    ordered = sorted(_SILANUS_DISTANCE_KM.items(), key=lambda kv: len(kv[0]), reverse=True)
    return tuple((re.compile(rf"\b{re.escape(town)}\b", re.IGNORECASE), km) for town, km in ordered)


def compute_logistics_tier(
    municipality: str | None,
    province: SardinianProvince,
) -> tuple[LogisticsTier, int | None]:
    """Resolve freight tier & road km from EDILMORITTU S.R.L. plant in Silanus (NU)."""
    if municipality:
        cleaned = municipality.strip()
        for town_pat, km in _compiled_town_distances():
            if town_pat.search(cleaned):
                if km <= 40:
                    return LogisticsTier.TIER_1_CORE, km
                if km <= 100:
                    return LogisticsTier.TIER_2_CENTRAL, km
                return LogisticsTier.TIER_3_ISLAND, km

    if province == SardinianProvince.NU:
        return LogisticsTier.TIER_1_CORE, 35
    if province in (SardinianProvince.OR, SardinianProvince.SS, SardinianProvince.REGIONAL):
        return LogisticsTier.TIER_2_CENTRAL, 75
    return LogisticsTier.TIER_3_ISLAND, 155


def _logistics_bonus(tier: LogisticsTier, matched_lines: set[ProductLine], notice_type: NoticeType) -> float:
    if notice_type == NoticeType.REGIONAL_GRANT:
        return 12.0
    # Linea A delivers island-wide with 2 owned crane trucks; Linea B shines within <= 40 km
    if tier == LogisticsTier.TIER_1_CORE:
        return 16.0 if ProductLine.LINEA_B in matched_lines else 14.0
    if tier == LogisticsTier.TIER_2_CENTRAL:
        return 8.0 if ProductLine.LINEA_A in matched_lines else 2.0
    # Tier 3 (>100 km): profitable for Linea A precast C.A.V., unprofitable for Linea-B-only resale
    if ProductLine.LINEA_A in matched_lines:
        return 4.0
    if ProductLine.LINEA_B in matched_lines:
        return -18.0
    return 0.0


def _build_recommended_action(
    notice: TenderNotice,
    categories: list[CAVProductCategory],
    lines: list[ProductLine],
    score: float,
    priority_unstarted: bool,
) -> str:
    if score < 45.0:
        return "Scartare / Bassa priorità catalogo Edilmorittu"
    if notice.notice_type == NoticeType.REGIONAL_GRANT or CAVProductCategory.SME_GRANT_SUBSIDY in categories:
        return "Verificare requisiti bando (ATECO 23.61.0 / Albo Artigiani NU-23034) per investimento Edilmorittu S.r.l."

    line_tag = "+".join(sorted(l.value.upper().replace("_", " ") for l in lines)) or "LINEA A"
    if notice.notice_type == NoticeType.CONTRACT_AWARD or notice.winner_company:
        winner = notice.winner_company or "Impresa aggiudicataria"
        piva = f" (P.IVA {notice.winner_tax_id})" if notice.winner_tax_id else ""
        dist = (
            f" [sede ~{notice.winner_distance_km} km da Silanus]"
            if notice.winner_distance_km is not None
            else ""
        )
        prefix = "🔥 CANTIERE NON AVVIATO — Chiamare subito " if priority_unstarted else "Contattare "
        return f"{prefix}{winner}{piva}{dist} per preventivo fornitura {line_tag}"

    return f"Gara aperta: preparare offerta fornitura {line_tag} per imprese partecipanti"


class CAVScoringEngine:
    """Deterministic Edilmorittu S.R.L. Linea A + Linea B matcher & Silanus logistics scorer."""

    def score_notice(
        self,
        notice: TenderNotice,
        cme_items: Sequence[CMEItem] | None = None,
    ) -> ScoredLead:
        haystack = " ".join(
            part
            for part in (notice.title, notice.description, notice.contracting_authority, notice.municipality or "")
            if part
        )

        negative_flags: list[str] = []
        stone_blocked = False
        hard_blocked = False
        total_penalty = 0.0

        for neg in _compiled_negative_rules():
            if neg.pattern.search(haystack):
                negative_flags.append(neg.label)
                total_penalty += neg.penalty
                if "pietra naturale" in neg.label.lower():
                    stone_blocked = True
                if neg.hard_block:
                    hard_blocked = True

        raw_score = 0.0
        matched_categories: list[CAVProductCategory] = []
        matched_lines: set[ProductLine] = set()
        matched_keywords: list[str] = []
        cpv_bonus = False

        # 1. If real CME items were extracted, anchor scoring directly on verified Bill of Quantities!
        resolved_cme = list(cme_items or [])
        effective_penalty = 0.0 if resolved_cme else total_penalty
        if resolved_cme:
            for item in resolved_cme:
                matched_lines.add(item.product_line)
                if item.category not in matched_categories:
                    matched_categories.append(item.category)
                if item.matched_catalog_label and item.matched_catalog_label not in matched_keywords:
                    matched_keywords.append(item.matched_catalog_label)
            raw_score += min(55.0, 22.0 + 6.0 * len(resolved_cme))

        # 2. Notice text & CPV rules (keep stone_blocked/hard_blocked active on notice text even with CME!)
        for rule in _compiled_notice_rules():
            if stone_blocked and rule.category == CAVProductCategory.ROAD_KERBS_PAVING:
                continue
            if hard_blocked and rule.product_line is not None:
                if not re.search(r"\b(?:c\.?a\.?v\.?|vibrocompress[oi]|pozzett[oi]\s+prefabbricat[oi])\b", haystack, re.IGNORECASE):
                    continue
            if rule.pattern.search(haystack):
                raw_score += rule.weight
                if rule.category not in matched_categories:
                    matched_categories.append(rule.category)
                if rule.product_line is not None:
                    matched_lines.add(rule.product_line)
                if rule.label not in matched_keywords:
                    matched_keywords.append(rule.label)

        for cpv in notice.cpv_codes:
            prefix = cpv.strip()[:8]
            if prefix in _CPV_PREFIX_WEIGHTS and not stone_blocked:
                w, line, cat, lbl = _CPV_PREFIX_WEIGHTS[prefix]
                raw_score += w
                cpv_bonus = True
                matched_lines.add(line)
                if cat not in matched_categories:
                    matched_categories.append(cat)
                if lbl not in matched_keywords:
                    matched_keywords.append(lbl)

        if notice.notice_type == NoticeType.REGIONAL_GRANT and CAVProductCategory.SME_GRANT_SUBSIDY in matched_categories:
            raw_score += 22.0

        # Bersaglio 1 Priority Boost: Awarded works not yet started & zero subcontracts registered!
        priority_unstarted = bool(
            notice.notice_type == NoticeType.CONTRACT_AWARD
            and notice.contract_started is False
            and notice.has_subcontracts is False
        )
        if (raw_score > 0 or resolved_cme) and notice.notice_type == NoticeType.CONTRACT_AWARD:
            raw_score += 20.0 if priority_unstarted else 10.0
            # Extra commercial leverage when winner HQ is >80 km from Silanus while job site is <=40 km!
            if (notice.winner_distance_km or 0) >= 80:
                raw_score += 8.0

        tier, distance_km = compute_logistics_tier(notice.municipality, notice.province)
        if raw_score > 0:
            raw_score += _logistics_bonus(tier, matched_lines, notice.notice_type)

        final_score = round(max(0.0, min(100.0, raw_score - effective_penalty)), 1)
        ordered_lines = sorted(matched_lines, key=lambda item: item.value)

        rationale_parts: list[str] = []
        if resolved_cme:
            rationale_parts.append(f"CME verificato ({len(resolved_cme)} voci compatibili)")
        if matched_keywords:
            rationale_parts.append("Match: " + ", ".join(matched_keywords[:4]))
        if priority_unstarted:
            rationale_parts.append("Aggiudicata con avvioContratto=[] e subappalti=[]")
        if negative_flags:
            rationale_parts.append("Esclusioni: " + ", ".join(negative_flags))
        rationale_parts.append(f"Cantiere: {tier.value.split('(')[0].strip()} ({distance_km or 'N/D'} km da Silanus)")

        assessment = MatchAssessment(
            score=final_score,
            matched_categories=matched_categories,
            matched_lines=ordered_lines,
            matched_keywords=matched_keywords,
            negative_flags=negative_flags,
            cpv_bonus_applied=cpv_bonus,
            priority_unstarted_award=priority_unstarted,
            logistics_tier=tier,
            estimated_distance_km=distance_km,
            recommended_action=_build_recommended_action(
                notice, matched_categories, ordered_lines, final_score, priority_unstarted
            ),
            rationale=" | ".join(rationale_parts),
        )
        return ScoredLead(notice=notice, assessment=assessment, cme_items=resolved_cme)
