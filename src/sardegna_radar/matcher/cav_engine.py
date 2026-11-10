"""Deterministic C.A.V. product matcher & Silanus (NU) road-logistics scoring engine."""

from __future__ import annotations

from dataclasses import dataclass
import functools
import re

from sardegna_radar.models import (
    CAVProductCategory,
    LogisticsTier,
    MatchAssessment,
    NoticeType,
    SardinianProvince,
    ScoredLead,
    TenderNotice,
)


@dataclass(frozen=True, slots=True)
class _CompiledRule:
    category: CAVProductCategory
    label: str
    pattern: re.Pattern[str]
    weight: float


@dataclass(frozen=True, slots=True)
class _NegativeRule:
    label: str
    pattern: re.Pattern[str]
    penalty: float


# Approximate road distance in km from Central Sardinia industrial hub (Z.I. Silanus, NU - SS 129 / SS 131)
_SILANUS_DISTANCE_KM: dict[str, int] = {
    "silanus": 2,
    "lei": 6,
    "bolotana": 11,
    "bortigali": 9,
    "birori": 11,
    "macomer": 15,
    "dualchi": 13,
    "noragugume": 14,
    "borore": 16,
    "ottana": 24,
    "sedilo": 25,
    "aidomaggiore": 26,
    "abbasanta": 27,
    "norbello": 27,
    "ghilarza": 28,
    "pauli latino": 32,
    "paulilatino": 32,
    "bono": 28,
    "bottidda": 30,
    "burgos": 31,
    "esporlatu": 29,
    "illorai": 24,
    "orotelli": 26,
    "orani": 32,
    "sarule": 34,
    "nuoro": 38,
    "bosa": 48,
    "ozieri": 52,
    "bonorva": 35,
    "thiesi": 46,
    "oristano": 64,
    "sassari": 78,
    "porto torres": 95,
    "alghero": 88,
    "siniscola": 85,
    "dorgali": 68,
    "tortoli": 98,
    "tortolì": 98,
    "lanusei": 92,
    "olbia": 118,
    "tempio pausania": 112,
    "arzachena": 138,
    "sanluri": 115,
    "villacidro": 128,
    "cagliari": 155,
    "quartu sant'elena": 162,
    "assemini": 148,
    "iglesias": 165,
    "carbonia": 178,
}

_CPV_PREFIX_WEIGHTS: dict[str, tuple[float, CAVProductCategory, str]] = {
    "45231300": (24.0, CAVProductCategory.PIPES_CULVERTS, "CPV Condotte idriche e fognarie"),
    "45232410": (22.0, CAVProductCategory.PIPES_CULVERTS, "CPV Opere di fognatura"),
    "44114200": (25.0, CAVProductCategory.MANHOLES_CHAMBERS, "CPV Prodotti in calcestruzzo"),
    "44163100": (20.0, CAVProductCategory.PIPES_CULVERTS, "CPV Tubi e raccordi per condotte"),
    "45233140": (20.0, CAVProductCategory.ROAD_KERBS_PAVING, "CPV Lavori stradali e cordoli"),
    "45233222": (18.0, CAVProductCategory.ROAD_KERBS_PAVING, "CPV Lastricatrici e marciapiedi"),
    "45215400": (28.0, CAVProductCategory.CEMETERY_NICHES, "CPV Lavori cimiteriali"),
}


@functools.lru_cache(maxsize=1)
def _compiled_positive_rules() -> tuple[_CompiledRule, ...]:
    raw_rules: tuple[tuple[CAVProductCategory, str, str, float], ...] = (
        # 1. Pipes & Culverts (C.A.V.)
        (
            CAVProductCategory.PIPES_CULVERTS,
            "c.a.v. / calcestruzzo vibrocompresso",
            r"\b(?:c\.?\s*a\.?\s*v\.?|calcestruzzo\s+(?:armato\s+)?vibrocompresso|vibrocompress[oi])\b",
            36.0,
        ),
        (
            CAVProductCategory.PIPES_CULVERTS,
            "tubazioni in calcestruzzo / cemento",
            r"\b(?:tubi|tubazioni|condott[ae]|collettor[ei])\s+(?:in\s+)?(?:calcestruzzo|cemento|c\.?a\.?v\.?|prefabbricat[oi])\b",
            32.0,
        ),
        (
            CAVProductCategory.PIPES_CULVERTS,
            "rete fognaria / acquedotto / acque meteoriche",
            r"\b(?:collettore\s+fognario|condotta\s+fognaria|rete\s+fognaria|condotta\s+idrica|acquedott[oi]|acque\s+bianche|acque\s+meteoriche|fognatur[ae]|scatolar[ei]\s+prefabbricat[oi])\b",
            26.0,
        ),
        (
            CAVProductCategory.PIPES_CULVERTS,
            "diametro nominale DN / marcatura CE DoP",
            r"\b(?:dn\s*(?:200|300|400|500|600|800|1000|1200)|marcatura\s+ce|dichiarazione\s+di\s+prestazione|\bdop\b)\b",
            14.0,
        ),
        # 2. Manholes & Inspection Chambers
        (
            CAVProductCategory.MANHOLES_CHAMBERS,
            "pozzetti prefabbricati / camere d'ispezione",
            r"\b(?:pozzett[oi]|camer[ae]\s+d['’]?ispezione|caditoi[ae]|chiusin[oi]|prolunghe\s+pozzetto|raccolta\s+acque)\b",
            24.0,
        ),
        # 3. Road Kerbs, Gutters & Urban Infrastructure
        (
            CAVProductCategory.ROAD_KERBS_PAVING,
            "cordoli stradali / cunette / zanelle",
            r"\b(?:cordol[oi]\s*(?:stradal[ei]|in\s+calcestruzzo|prefabbricat[oi])?|cunett[ae]\s*(?:alla\s+francese|stradal[ei])?|zanell[ae]|new\s+jersey)\b",
            28.0,
        ),
        (
            CAVProductCategory.ROAD_KERBS_PAVING,
            "sottoservizi / piattaforma stradale / marciapiedi",
            r"\b(?:sottoservizi|urbanizzazione\s+primaria|piattaforma\s+stradale|opere\s+idrauliche\s+stradali|rifacimento\s+marciapiedi)\b",
            18.0,
        ),
        # 4. Vibro-compressed Blocks & Retaining Walls
        (
            CAVProductCategory.VIBRO_BLOCKS_WALLS,
            "blocchi vibrocompressi / manufatti in calcestruzzo",
            r"\b(?:blocchi\s+(?:in\s+calcestruzzo|vibrocompressi|da\s+intonaco|faccia\s+vista)|manufatti\s+in\s+(?:calcestruzzo|cemento)|muratur[ae]\s+portant[ei])\b",
            26.0,
        ),
        # 5. Cemetery Expansion & Prefab Burial Niches
        (
            CAVProductCategory.CEMETERY_NICHES,
            "loculi prefabbricati / cimitero comunale",
            r"\b(?:locul[oi]\s*(?:prefabbricat[oi]|cimiterial[ei])?|cimitero\s+comunale|ampliamento\s+cimiter(?:o|iale)|colombar[io]|ossar[io]|edilizia\s+cimiteriale)\b",
            38.0,
        ),
        # 6. Regional SME Grants (RAS / SIPES / CCIAA Nuoro PID)
        (
            CAVProductCategory.SME_GRANT_SUBSIDY,
            "voucher digitali PID / transizione digitale I4.0",
            r"\b(?:voucher\s+digital[ei]|\bpid\b|transizione\s+digitale|automazione\s+impianti|impianti\s+fotovoltaici|industria\s+4\.0)\b",
            34.0,
        ),
        (
            CAVProductCategory.SME_GRANT_SUBSIDY,
            "fondo perduto / SIPES / contributi PMI Sardegna",
            r"\b(?:fondo\s+perduto|\bsipes\b|bando\s+imprese|contributi\s+(?:a\s+fondo\s+perduto|pmi)|agevolazioni\s+(?:sipes|ras|industriali)|camera\s+di\s+commercio)\b",
            32.0,
        ),
    )
    return tuple(
        _CompiledRule(
            category=cat,
            label=label,
            pattern=re.compile(regex, re.IGNORECASE),
            weight=weight,
        )
        for cat, label, regex, weight in raw_rules
    )


@functools.lru_cache(maxsize=1)
def _compiled_negative_rules() -> tuple[_NegativeRule, ...]:
    raw_negatives: tuple[tuple[str, str, float], ...] = (
        (
            "medical/hospital supplies",
            r"\b(?:endotracheal[ei]|ospedalier[oi]|cateter[ei]|chirurgic[oi]|dispositivi\s+medici|steril[ei]|reagenti|farmac[io]|siringhe|protesi)\b",
            65.0,
        ),
        (
            "school catering / stationery / pure software",
            r"\b(?:mensa\s+scolastica|ristorazione\s+collettiva|cancelleria|blocchi\s+appunti|licenze\s+software\s+cloud|derrate\s+alimentari)\b",
            55.0,
        ),
        (
            "janitorial / pest control / office cleaning",
            r"\b(?:pulizia\s+locali|derattizzazione|spazzamento\s+uffici|disinfestazione|portierato)\b",
            50.0,
        ),
    )
    return tuple(
        _NegativeRule(label=label, pattern=re.compile(regex, re.IGNORECASE), penalty=penalty)
        for label, regex, penalty in raw_negatives
    )


def compute_logistics_tier(
    municipality: str | None,
    province: SardinianProvince,
) -> tuple[LogisticsTier, int | None]:
    """Calculate road freight tier and estimated km from Central Sardinia hub in Silanus (NU)."""
    if municipality:
        lowered = municipality.strip().lower()
        for town_key, km in _SILANUS_DISTANCE_KM.items():
            if town_key in lowered:
                if km <= 40:
                    return LogisticsTier.TIER_1_CORE, km
                if km <= 100:
                    return LogisticsTier.TIER_2_CENTRAL, km
                return LogisticsTier.TIER_3_ISLAND, km

    if province == SardinianProvince.NU:
        return LogisticsTier.TIER_1_CORE, 38
    if province in (SardinianProvince.OR, SardinianProvince.SS):
        return LogisticsTier.TIER_2_CENTRAL, 70
    if province in (SardinianProvince.CA, SardinianProvince.SU):
        return LogisticsTier.TIER_3_ISLAND, 155
    return LogisticsTier.TIER_2_CENTRAL, 75


class CAVScoringEngine:
    """Zero-token deterministic scoring engine tailored to precast C.A.V. product lines."""

    def score_notice(self, notice: TenderNotice) -> ScoredLead:
        """Evaluate a TenderNotice and return a ScoredLead with full MatchAssessment."""
        haystack = f"{notice.title} {notice.description} {notice.contracting_authority}".strip()

        raw_score = 0.0
        matched_categories: list[CAVProductCategory] = []
        matched_keywords: list[str] = []
        negative_flags: list[str] = []
        cpv_bonus_applied = False

        for rule in _compiled_positive_rules():
            match = rule.pattern.search(haystack)
            if match:
                raw_score += rule.weight
                matched_keywords.append(match.group(0).lower())
                if rule.category not in matched_categories:
                    matched_categories.append(rule.category)

        for cpv in notice.cpv_codes:
            prefix = cpv.split("-")[0][:8]
            if prefix in _CPV_PREFIX_WEIGHTS:
                bonus, cpv_cat, cpv_label = _CPV_PREFIX_WEIGHTS[prefix]
                raw_score += bonus
                cpv_bonus_applied = True
                matched_keywords.append(cpv_label)
                if cpv_cat not in matched_categories:
                    matched_categories.append(cpv_cat)

        for neg_rule in _compiled_negative_rules():
            if neg_rule.pattern.search(haystack):
                raw_score -= neg_rule.penalty
                negative_flags.append(neg_rule.label)

        logistics_tier, distance_km = compute_logistics_tier(notice.municipality, notice.province)

        # Apply road-logistics proximity bonus only when positive B2B signals exist
        if raw_score > 0 and not negative_flags:
            if logistics_tier == LogisticsTier.TIER_1_CORE:
                raw_score += 12.0
            elif logistics_tier == LogisticsTier.TIER_2_CENTRAL:
                raw_score += 6.0

            # High contract value boost for structural civil works (>= 250k EUR)
            if notice.amount_eur and notice.amount_eur >= 250_000.0:
                raw_score += 6.0

        final_score = round(max(0.0, min(100.0, raw_score)), 1)
        recommended_action = self._build_recommended_action(
            notice=notice,
            score=final_score,
            categories=matched_categories,
            logistics_tier=logistics_tier,
            distance_km=distance_km,
        )
        rationale = self._build_rationale(
            categories=matched_categories,
            keywords=matched_keywords,
            negative_flags=negative_flags,
            logistics_tier=logistics_tier,
            distance_km=distance_km,
        )

        assessment = MatchAssessment(
            score=final_score,
            matched_categories=matched_categories,
            matched_keywords=matched_keywords,
            negative_flags=negative_flags,
            cpv_bonus_applied=cpv_bonus_applied,
            logistics_tier=logistics_tier,
            estimated_distance_km=distance_km,
            recommended_action=recommended_action,
            rationale=rationale,
        )
        return ScoredLead(notice=notice, assessment=assessment)

    @staticmethod
    def _build_recommended_action(
        *,
        notice: TenderNotice,
        score: float,
        categories: list[CAVProductCategory],
        logistics_tier: LogisticsTier,
        distance_km: int | None,
    ) -> str:
        if score < 45.0:
            return "Scartare / Fuori target C.A.V."

        if CAVProductCategory.SME_GRANT_SUBSIDY in categories or notice.notice_type == NoticeType.REGIONAL_GRANT:
            return (
                "Preparare domanda contributo a fondo perduto PMI "
                f"con studio consulenza / CCIAA ({notice.contracting_authority})."
            )

        km_str = f" (~{distance_km} km da Silanus)" if distance_km is not None else ""
        if notice.winner_company or notice.notice_type == NoticeType.CONTRACT_AWARD:
            winner = notice.winner_company or "Impresa Aggiudicataria"
            return (
                f"Contatto commerciale diretto Ufficio Acquisti di '{winner}' "
                f"per preventivo fornitura C.A.V. certificata CE/DoP franco cantiere{km_str}."
            )

        if logistics_tier == LogisticsTier.TIER_1_CORE:
            return (
                f"Priorità Alta {km_str}: inviare listino C.A.V. CE/DoP alle imprese edili "
                f"partecipanti al bando di {notice.contracting_authority}."
            )

        return (
            f"Qualificare imprese appaltatrici per fornitura C.A.V. su cantiere "
            f"{notice.municipality or notice.province.value}{km_str}."
        )

    @staticmethod
    def _build_rationale(
        *,
        categories: list[CAVProductCategory],
        keywords: list[str],
        negative_flags: list[str],
        logistics_tier: LogisticsTier,
        distance_km: int | None,
    ) -> str:
        if negative_flags:
            return f"Penalizzato per esclusione fuori settore: {', '.join(negative_flags)}."
        if not categories:
            return "Nessun riscontro diretto con catalogo manufatti C.A.V. o bandi PMI."
        cat_names = ", ".join(c.value for c in categories)
        kw_preview = ", ".join(dict.fromkeys(keywords[:5]))
        dist_info = f"{distance_km} km da Silanus" if distance_km is not None else logistics_tier.value
        return f"Linee: [{cat_names}] | Segnali: ({kw_preview}) | Logistica: {dist_info}."
