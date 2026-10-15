"""Level mapping and seniority normalization engine with uncertainty quantification (T3.09).

Adheres to:
- Rule R-UQ-01: No lone numbers; uncertainty quantified via soft labels and confidence scores.
- Rule R-MD-07: Anti-heuristic rigor; unmapped and ambiguous cases are counted and
  flagged, not forced.
- Rule R-MD-09 & R-SC-07: Deterministic rule-based engine, strictly free of LLM dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import polars as pl

from compintel.schema.enums import SeniorityLevel

DEFAULT_LEVEL_MAPPING_VERSION: str = "v0.1.0"

# Explicit Level Ladder Patterns
# Matches common corporate tech level formats: L1-L7, E1-E7, IC1-IC6, MTS/SMTS/PMTS
EXPLICIT_LEVEL_PATTERNS: list[tuple[re.Pattern[str], SeniorityLevel, float]] = [
    # Principal / Distinguished (L6+)
    (
        re.compile(r"\b(l[6-9]|e[6-9]|ic[6-9]|distinguished|fellow|senior\s+principal)\b", re.I),
        SeniorityLevel.PRINCIPAL,
        0.98,
    ),
    # Staff / Principal (L5)
    (
        re.compile(
            r"\b(l5|e5|ic5|pmts|principal\s+engineer|staff\s+engineer|lead\s+architect)\b", re.I
        ),
        SeniorityLevel.STAFF,
        0.95,
    ),
    # Senior (L4)
    (
        re.compile(r"\b(l4|e4|ic4|smts|sde\s*3|sde\s*iii|swe\s*3|swe\s*iii)\b", re.I),
        SeniorityLevel.SR,
        0.95,
    ),
    # Mid-Level (L3)
    (
        re.compile(
            r"\b(l3|e3|ic3|mts\s*2|mts\s*ii|sde\s*2|sde\s*ii|swe\s*2|swe\s*ii|engineer\s*2|engineer\s*ii)\b",
            re.I,
        ),
        SeniorityLevel.MID,
        0.95,
    ),
    # Junior / Entry (L1-L2)
    (
        re.compile(
            r"\b(l[12]|e[12]|ic[12]|mts\s*1|mts\s*i|sde\s*1|sde\s*i|swe\s*1|swe\s*i|associate\s+engineer|graduate\s+engineer|trainee|intern)\b",
            re.I,
        ),
        SeniorityLevel.JR,
        0.95,
    ),
]

# Title Keyword Patterns
TITLE_SENIORITY_PATTERNS: list[
    tuple[re.Pattern[str], SeniorityLevel, float, dict[str, float], bool]
] = [
    # (pattern, primary_level, confidence, soft_labels, is_ambiguous)
    # Principal / Fellow / Distinguished
    (
        re.compile(r"\b(distinguished|fellow|senior\s+principal|chief\s+architect)\b", re.I),
        SeniorityLevel.PRINCIPAL,
        0.95,
        {"JR": 0.0, "MID": 0.0, "SR": 0.05, "STAFF": 0.15, "PRINCIPAL": 0.80, "OTHER": 0.0},
        False,
    ),
    # Staff / Architect
    (
        re.compile(r"\b(staff|principal|architect)\b", re.I),
        SeniorityLevel.STAFF,
        0.90,
        {"JR": 0.0, "MID": 0.0, "SR": 0.15, "STAFF": 0.75, "PRINCIPAL": 0.10, "OTHER": 0.0},
        False,
    ),
    # Senior
    (
        re.compile(r"\b(senior|sr\.?)\b", re.I),
        SeniorityLevel.SR,
        0.90,
        {"JR": 0.0, "MID": 0.10, "SR": 0.80, "STAFF": 0.10, "PRINCIPAL": 0.0, "OTHER": 0.0},
        False,
    ),
    # Lead / Tech Lead (often spans Senior and Staff in India tech)
    (
        re.compile(r"\b(lead|tech\s+lead|team\s+lead)\b", re.I),
        SeniorityLevel.SR,
        0.75,
        {"JR": 0.0, "MID": 0.05, "SR": 0.60, "STAFF": 0.35, "PRINCIPAL": 0.0, "OTHER": 0.0},
        True,
    ),
    # Junior / Entry / Associate
    (
        re.compile(r"\b(junior|jr\.?|associate|intern|trainee|graduate|entry)\b", re.I),
        SeniorityLevel.JR,
        0.90,
        {"JR": 0.85, "MID": 0.15, "SR": 0.0, "STAFF": 0.0, "PRINCIPAL": 0.0, "OTHER": 0.0},
        False,
    ),
    # Roman Numerals / Numbers
    (
        re.compile(r"\b(v|5)\b", re.I),
        SeniorityLevel.PRINCIPAL,
        0.85,
        {"JR": 0.0, "MID": 0.0, "SR": 0.05, "STAFF": 0.25, "PRINCIPAL": 0.70, "OTHER": 0.0},
        False,
    ),
    (
        re.compile(r"\b(iv|4)\b", re.I),
        SeniorityLevel.STAFF,
        0.85,
        {"JR": 0.0, "MID": 0.05, "SR": 0.20, "STAFF": 0.75, "PRINCIPAL": 0.0, "OTHER": 0.0},
        False,
    ),
    (
        re.compile(r"\b(iii|3)\b", re.I),
        SeniorityLevel.SR,
        0.85,
        {"JR": 0.0, "MID": 0.20, "SR": 0.75, "STAFF": 0.05, "PRINCIPAL": 0.0, "OTHER": 0.0},
        False,
    ),
    (
        re.compile(r"\b(ii|2)\b", re.I),
        SeniorityLevel.MID,
        0.90,
        {"JR": 0.10, "MID": 0.80, "SR": 0.10, "STAFF": 0.0, "PRINCIPAL": 0.0, "OTHER": 0.0},
        False,
    ),
    (
        re.compile(r"\b(i|1)\b", re.I),
        SeniorityLevel.JR,
        0.85,
        {"JR": 0.80, "MID": 0.20, "SR": 0.0, "STAFF": 0.0, "PRINCIPAL": 0.0, "OTHER": 0.0},
        False,
    ),
]


@dataclass(frozen=True)
class LevelMappingResult:
    """Standardized result of seniority level normalization with uncertainty."""

    raw_title: str | None
    explicit_level: str | None
    years_experience: float | None
    seniority: SeniorityLevel
    confidence: float
    soft_labels: dict[str, float]
    is_ambiguous: bool
    is_unmapped: bool
    mapping_method: str
    mapping_version: str = DEFAULT_LEVEL_MAPPING_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "raw_title": self.raw_title,
            "explicit_level": self.explicit_level,
            "years_experience": self.years_experience,
            "seniority": self.seniority.value,
            "confidence": self.confidence,
            "soft_labels": self.soft_labels,
            "is_ambiguous": self.is_ambiguous,
            "is_unmapped": self.is_unmapped,
            "mapping_method": self.mapping_method,
            "mapping_version": self.mapping_version,
        }


@dataclass
class LevelAmbiguityAudit:
    """Auditing summary tracking mapped, ambiguous, and unmapped seniority records."""

    total_records: int = 0
    clean_mapped_count: int = 0
    ambiguous_count: int = 0
    unmapped_count: int = 0
    seniority_counts: dict[str, int] = field(
        default_factory=lambda: {s.value: 0 for s in SeniorityLevel}
    )

    @property
    def ambiguity_rate(self) -> float:
        """Fraction of total records with ambiguous level signals."""
        return self.ambiguous_count / self.total_records if self.total_records > 0 else 0.0

    @property
    def unmapped_rate(self) -> float:
        """Fraction of total records with completely unmapped levels."""
        return self.unmapped_count / self.total_records if self.total_records > 0 else 0.0

    def record_result(self, result: LevelMappingResult) -> None:
        """Accumulate a LevelMappingResult into audit counters."""
        self.total_records += 1
        self.seniority_counts[result.seniority.value] = (
            self.seniority_counts.get(result.seniority.value, 0) + 1
        )

        if result.is_unmapped:
            self.unmapped_count += 1
        elif result.is_ambiguous:
            self.ambiguous_count += 1
        else:
            self.clean_mapped_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert audit summary to dictionary."""
        return {
            "total_records": self.total_records,
            "clean_mapped_count": self.clean_mapped_count,
            "ambiguous_count": self.ambiguous_count,
            "unmapped_count": self.unmapped_count,
            "ambiguity_rate": round(self.ambiguity_rate, 4),
            "unmapped_rate": round(self.unmapped_rate, 4),
            "seniority_counts": dict(self.seniority_counts),
        }


def _yoe_to_soft_labels(yoe: float) -> tuple[SeniorityLevel, float, dict[str, float], bool]:
    """Map years of experience to soft label probability distribution over seniority tiers.

    Based on empirical India tech career progression bands:
    - JR: 0 to 2 years
    - MID: 2 to 6 years
    - SR: 6 to 12 years
    - STAFF: 12 to 15 years
    - PRINCIPAL: 15+ years
    """
    if yoe <= 1.0:
        return (
            SeniorityLevel.JR,
            0.90,
            {"JR": 0.90, "MID": 0.10, "SR": 0.0, "STAFF": 0.0, "PRINCIPAL": 0.0, "OTHER": 0.0},
            False,
        )
    if yoe <= 2.0:
        # Borderline Junior / Mid
        return (
            SeniorityLevel.JR,
            0.70,
            {"JR": 0.65, "MID": 0.35, "SR": 0.0, "STAFF": 0.0, "PRINCIPAL": 0.0, "OTHER": 0.0},
            True,
        )
    if yoe <= 4.5:
        return (
            SeniorityLevel.MID,
            0.85,
            {"JR": 0.10, "MID": 0.80, "SR": 0.10, "STAFF": 0.0, "PRINCIPAL": 0.0, "OTHER": 0.0},
            False,
        )
    if yoe <= 6.0:
        # Borderline Mid / Senior
        return (
            SeniorityLevel.MID,
            0.65,
            {"JR": 0.05, "MID": 0.55, "SR": 0.40, "STAFF": 0.0, "PRINCIPAL": 0.0, "OTHER": 0.0},
            True,
        )
    if yoe <= 10.0:
        return (
            SeniorityLevel.SR,
            0.85,
            {"JR": 0.0, "MID": 0.10, "SR": 0.80, "STAFF": 0.10, "PRINCIPAL": 0.0, "OTHER": 0.0},
            False,
        )
    if yoe <= 12.0:
        # Borderline Senior / Staff
        return (
            SeniorityLevel.SR,
            0.65,
            {"JR": 0.0, "MID": 0.05, "SR": 0.55, "STAFF": 0.40, "PRINCIPAL": 0.0, "OTHER": 0.0},
            True,
        )
    if yoe <= 15.0:
        return (
            SeniorityLevel.STAFF,
            0.80,
            {"JR": 0.0, "MID": 0.0, "SR": 0.15, "STAFF": 0.75, "PRINCIPAL": 0.10, "OTHER": 0.0},
            False,
        )

    # 15+ years: Principal
    return (
        SeniorityLevel.PRINCIPAL,
        0.85,
        {"JR": 0.0, "MID": 0.0, "SR": 0.05, "STAFF": 0.25, "PRINCIPAL": 0.70, "OTHER": 0.0},
        False,
    )


def map_level(
    raw_title: str | None = None,
    explicit_level: str | None = None,
    years_experience: float | None = None,
    mapping_version: str = DEFAULT_LEVEL_MAPPING_VERSION,
) -> LevelMappingResult:
    """Map raw title, explicit level code, and experience to standardized seniority.

    Follows rigorous evidence prioritization:
    1. Explicit company level code (e.g. L4, E5, MTS II) -> highest confidence.
    2. Explicit title seniority tokens (e.g. Senior, Lead, Staff, Intern).
    3. Years of experience (YoE) soft distribution if title lacks level tokens.
    4. Unmapped fallback to SeniorityLevel.OTHER with zero confidence if no signal exists.

    Crucially, unmapped and ambiguous cases are explicitly flagged and counted,
    never forced into an arbitrary category without evidence.
    """
    # 1. Check Explicit Level Code
    if explicit_level and explicit_level.strip():
        clean_exp = explicit_level.strip().lower()
        for pattern, seniority, conf in EXPLICIT_LEVEL_PATTERNS:
            if pattern.search(clean_exp):
                soft = {s.value: 0.0 for s in SeniorityLevel}
                soft[seniority.value] = conf
                remainder = round((1.0 - conf) / (len(SeniorityLevel) - 1), 4)
                for s in SeniorityLevel:
                    if s != seniority:
                        soft[s.value] = remainder
                return LevelMappingResult(
                    raw_title=raw_title,
                    explicit_level=explicit_level,
                    years_experience=years_experience,
                    seniority=seniority,
                    confidence=conf,
                    soft_labels=soft,
                    is_ambiguous=False,
                    is_unmapped=False,
                    mapping_method="explicit_code",
                    mapping_version=mapping_version,
                )

    # 2. Check Title Seniority Tokens
    if raw_title and raw_title.strip():
        clean_title = raw_title.strip().lower()
        for pattern, seniority, conf, soft, is_amb in TITLE_SENIORITY_PATTERNS:
            if pattern.search(clean_title):
                # If YoE is also provided, check for concordance
                if years_experience is not None and years_experience >= 0.0:
                    yoe_lvl, yoe_conf, _, _ = _yoe_to_soft_labels(years_experience)
                    # Concordance reinforces confidence; contradiction increases ambiguity
                    if (
                        yoe_lvl != seniority
                        and abs(
                            list(SeniorityLevel).index(yoe_lvl)
                            - list(SeniorityLevel).index(seniority)
                        )
                        >= 2
                    ):
                        # Severe discrepancy (e.g. title says "Senior" but YoE = 0.5 yrs)
                        is_amb = True
                        conf = max(0.40, conf - 0.30)
                return LevelMappingResult(
                    raw_title=raw_title,
                    explicit_level=explicit_level,
                    years_experience=years_experience,
                    seniority=seniority,
                    confidence=conf,
                    soft_labels=soft,
                    is_ambiguous=is_amb,
                    is_unmapped=False,
                    mapping_method="title_token",
                    mapping_version=mapping_version,
                )

    # 3. Check Years of Experience as Secondary Signal
    if years_experience is not None and years_experience >= 0.0:
        seniority, conf, soft, is_amb = _yoe_to_soft_labels(years_experience)
        return LevelMappingResult(
            raw_title=raw_title,
            explicit_level=explicit_level,
            years_experience=years_experience,
            seniority=seniority,
            confidence=conf,
            soft_labels=soft,
            is_ambiguous=is_amb,
            is_unmapped=False,
            mapping_method="experience_heuristic",
            mapping_version=mapping_version,
        )

    # 4. Unmapped Case: Do NOT force an arbitrary category (Rule R-MD-07)
    unmapped_soft: dict[str, float] = {
        SeniorityLevel.JR.value: 0.25,
        SeniorityLevel.MID.value: 0.45,
        SeniorityLevel.SR.value: 0.20,
        SeniorityLevel.STAFF.value: 0.08,
        SeniorityLevel.PRINCIPAL.value: 0.02,
        SeniorityLevel.OTHER.value: 0.0,
    }
    return LevelMappingResult(
        raw_title=raw_title,
        explicit_level=explicit_level,
        years_experience=years_experience,
        seniority=SeniorityLevel.OTHER,
        confidence=0.0,
        soft_labels=unmapped_soft,
        is_ambiguous=True,
        is_unmapped=True,
        mapping_method="unmapped",
        mapping_version=mapping_version,
    )


def normalize_levels_df(
    df: pl.DataFrame,
    title_column: str = "raw_title",
    explicit_level_column: str | None = None,
    yoe_column: str | None = "years_experience",
    mapping_version: str = DEFAULT_LEVEL_MAPPING_VERSION,
) -> tuple[pl.DataFrame, LevelAmbiguityAudit]:
    """Batch normalize seniority levels in a Polars DataFrame, returning results and audit counts.

    Appends:
    - seniority: Standard SeniorityLevel string ('JR', 'MID', 'SR', 'STAFF', 'PRINCIPAL', 'OTHER')
    - level_confidence: Mapping confidence in [0.0, 1.0]
    - is_level_ambiguous: Boolean indicating borderline or conflicting seniority signals
    - is_level_unmapped: Boolean indicating lack of seniority signals
    - level_mapping_method: Strategy used ('explicit_code', 'title_token',
      'experience_heuristic', 'unmapped')
    - level_mapping_version: Version identifier recorded for every record

    Returns:
        Tuple of (appended Polars DataFrame, LevelAmbiguityAudit summary).
    """
    audit = LevelAmbiguityAudit()

    if df.height == 0:
        empty_df = df.with_columns(
            pl.lit(None, dtype=pl.String).alias("seniority"),
            pl.lit(None, dtype=pl.Float64).alias("level_confidence"),
            pl.lit(None, dtype=pl.Boolean).alias("is_level_ambiguous"),
            pl.lit(None, dtype=pl.Boolean).alias("is_level_unmapped"),
            pl.lit(None, dtype=pl.String).alias("level_mapping_method"),
            pl.lit(None, dtype=pl.String).alias("level_mapping_version"),
        )
        return empty_df, audit

    titles = df[title_column].to_list() if title_column in df.columns else [None] * df.height
    exp_levels = (
        df[explicit_level_column].to_list()
        if explicit_level_column and explicit_level_column in df.columns
        else [None] * df.height
    )
    yoes = (
        df[yoe_column].to_list() if yoe_column and yoe_column in df.columns else [None] * df.height
    )

    results: list[LevelMappingResult] = []
    for t, el, y in zip(titles, exp_levels, yoes, strict=False):
        y_val = (
            float(y)
            if y is not None and str(y).strip() != "" and str(y).strip() != "null"
            else None
        )
        res = map_level(
            raw_title=t,
            explicit_level=el,
            years_experience=y_val,
            mapping_version=mapping_version,
        )
        results.append(res)
        audit.record_result(res)

    seniorities = [r.seniority.value for r in results]
    confidences = [r.confidence for r in results]
    ambiguities = [r.is_ambiguous for r in results]
    unmapped_flags = [r.is_unmapped for r in results]
    methods = [r.mapping_method for r in results]
    versions = [r.mapping_version for r in results]

    output_df = df.with_columns(
        pl.Series("seniority", seniorities, dtype=pl.String),
        pl.Series("level_confidence", confidences, dtype=pl.Float64),
        pl.Series("is_level_ambiguous", ambiguities, dtype=pl.Boolean),
        pl.Series("is_level_unmapped", unmapped_flags, dtype=pl.Boolean),
        pl.Series("level_mapping_method", methods, dtype=pl.String),
        pl.Series("level_mapping_version", versions, dtype=pl.String),
    )
    return output_df, audit
