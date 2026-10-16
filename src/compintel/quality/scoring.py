"""Source-Quality Scoring Framework (SQSF) Engine (Task T3.12, Task T1.10).

Implements the 10-dimension evaluation rubric, non-compensatory hard gates,
operational tier classification, ProvenanceTier mapping, and observation-level
scoring attachment adhering to:
- Decoupled Evidence Principle (D-010, Rule R-UQ-07)
- Licence Gate & Scraping Ban (Rule R-DA-01)
- Anti-Heuristic Unbundling & Primary PT1 Eligibility (Rule R-MD-07)
- Zero Synthetic Training Data (Rule R-MD-11)
- Fact Verification & Ground Truth Discipline (Rules R-EV-01, R-EV-03, R-EV-05)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import polars as pl
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from compintel.errors import DataContractError
from compintel.schema.enums import ProvenanceTier

# ---------------------------------------------------------------------------
# Constants & Weights (docs/research/05-source-scoring.md Section 2)
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS: dict[str, float] = {
    "d1_licensing_legal": 0.15,
    "d2_target_measure": 0.15,
    "d3_upstream_provenance": 0.12,
    "d4_population_geographic": 0.12,
    "d5_sampling_frame": 0.10,
    "d6_covariate_granularity": 0.10,
    "d7_observation_independence": 0.08,
    "d8_temporal_freshness": 0.08,
    "d9_privacy_compliance": 0.05,
    "d10_validation_utility": 0.05,
}

HARD_GATE_DIMENSIONS: dict[str, int] = {
    "d1_licensing_legal": 3,
    "d2_target_measure": 3,
    "d3_upstream_provenance": 3,
}

DEFAULT_SOURCES_DIR = Path("config/sources")


# ---------------------------------------------------------------------------
# Enums & Models
# ---------------------------------------------------------------------------


class SQSFClassificationTier(StrEnum):
    """Six operational tiers defined in SQSF (05-source-scoring.md Section 3.3)."""

    TIER_1_GROUND_TRUTH = "TIER_1_GROUND_TRUTH"
    TIER_2_POPULATION_BENCHMARK = "TIER_2_POPULATION_BENCHMARK"
    TIER_3_MARKET_SIGNAL = "TIER_3_MARKET_SIGNAL"
    TIER_4_SUPPLEMENTARY = "TIER_4_SUPPLEMENTARY"
    TIER_5_TEST_FIXTURE = "TIER_5_TEST_FIXTURE"
    TIER_6_DISQUALIFIED = "TIER_6_DISQUALIFIED"


class DimensionScores(BaseModel):
    """10-Dimension Discrete Evaluation Rubric Scores (1 to 5 scale)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    d1_licensing_legal: int = Field(
        ...,
        ge=1,
        le=5,
        description="D1: Licensing & Legal Integrity (Weight: 0.15, Hard Gate >= 3)",
    )
    d2_target_measure: int = Field(
        ...,
        ge=1,
        le=5,
        description="D2: Target Measure Compatibility (Weight: 0.15, Hard Gate >= 3)",
    )
    d3_upstream_provenance: int = Field(
        ...,
        ge=1,
        le=5,
        description="D3: Upstream Provenance & Auditability (Weight: 0.12, Hard Gate >= 3)",
    )
    d4_population_geographic: int = Field(
        ...,
        ge=1,
        le=5,
        description="D4: Population & Geographic Fidelity (Weight: 0.12)",
    )
    d5_sampling_frame: int = Field(
        ...,
        ge=1,
        le=5,
        description="D5: Sampling Frame & Selection Bias (Weight: 0.10)",
    )
    d6_covariate_granularity: int = Field(
        ...,
        ge=1,
        le=5,
        description="D6: Covariate Granularity & Depth (Weight: 0.10)",
    )
    d7_observation_independence: int = Field(
        ...,
        ge=1,
        le=5,
        description="D7: Observation Independence & Deduplication (Weight: 0.08)",
    )
    d8_temporal_freshness: int = Field(
        ...,
        ge=1,
        le=5,
        description="D8: Temporal Freshness & Vintage (Weight: 0.08)",
    )
    d9_privacy_compliance: int = Field(
        ...,
        ge=1,
        le=5,
        description="D9: Privacy, Anonymity & Statutory Compliance (Weight: 0.05)",
    )
    d10_validation_utility: int = Field(
        ...,
        ge=1,
        le=5,
        description="D10: Out-of-Sample Validation Utility (Weight: 0.05)",
    )

    @field_validator("*")
    @classmethod
    def validate_dimension_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError(f"Dimension score must be integer in [1, 5], got {v}")
        return v


@dataclass(frozen=True)
class SourceQualityEvaluation:
    """Complete Source-Quality Scoring evaluation result."""

    source_id: str
    score: float  # Composite SQS in [20.0, 100.0]
    provenance_tier: ProvenanceTier  # Canonical ProvenanceTier (TIER_A, TIER_B, TIER_C, TIER_D)
    sqsf_tier: SQSFClassificationTier  # Operational Tier 1 to 6
    hard_gates_passed: bool
    failed_gates: list[str] = field(default_factory=list)
    is_pt1_training_eligible: bool = False
    dimension_scores: DimensionScores | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Core Calculation Functions
# ---------------------------------------------------------------------------


def compute_source_quality_score(dimensions: DimensionScores) -> float:
    """Compute the Composite Source Quality Score (SQS) in [20.0, 100.0].

    Formula (05-source-scoring.md Section 3.1):
        Q(s) = 20 * sum_{d=1}^{10} w_d * D_d(s)
    """
    dim_dict = dimensions.model_dump()
    raw_weighted_sum = sum(
        DIMENSION_WEIGHTS[dim_name] * dim_dict[dim_name] for dim_name in DIMENSION_WEIGHTS
    )
    score = 20.0 * raw_weighted_sum
    # Bound strictly and round to 1 decimal place matching catalog
    bounded_score = max(20.0, min(100.0, score))
    return float(round(bounded_score, 1))


def evaluate_hard_gates(dimensions: DimensionScores) -> tuple[bool, list[str]]:
    """Evaluate non-compensatory Hard Gates (05-source-scoring.md Section 3.2).

    Gate 1: D1 >= 3 (Legal / Licensing)
    Gate 2: D2 >= 3 (Target Measure)
    Gate 3: D3 >= 3 (Provenance & Auditability)

    Returns:
        (all_passed, list_of_failed_gate_descriptions)
    """
    failed: list[str] = []
    g1_min = HARD_GATE_DIMENSIONS["d1_licensing_legal"]
    if dimensions.d1_licensing_legal < g1_min:
        failed.append(f"Gate 1 (Legal) failed: D1={dimensions.d1_licensing_legal} < {g1_min}")
    g2_min = HARD_GATE_DIMENSIONS["d2_target_measure"]
    if dimensions.d2_target_measure < g2_min:
        failed.append(f"Gate 2 (Target) failed: D2={dimensions.d2_target_measure} < {g2_min}")
    g3_min = HARD_GATE_DIMENSIONS["d3_upstream_provenance"]
    if dimensions.d3_upstream_provenance < g3_min:
        failed.append(
            f"Gate 3 (Provenance) failed: D3={dimensions.d3_upstream_provenance} < {g3_min}"
        )
    return len(failed) == 0, failed


def map_score_to_provenance_tier(
    score: float,
    hard_gates_passed: bool = True,
) -> ProvenanceTier:
    """Map Composite SQS to canonical ProvenanceTier (Rules R-UQ-07, T1.10).

    Mapping rules (enums.py):
    - TIER_A: Official population benchmarks & verified payslips (SQS >= 80.0, hard gates pass)
    - TIER_B: Statutory corporate disclosures (65.0 <= SQS < 80.0, gates pass)
    - TIER_C: Open public developer surveys (50.0 <= SQS < 65.0, legal gates pass)
    - TIER_D: Unverified job board ranges or gate failure (SQS < 50.0 or gates fail)
    """
    if not hard_gates_passed or score < 50.0:
        return ProvenanceTier.TIER_D
    if score >= 80.0:
        return ProvenanceTier.TIER_A
    if score >= 65.0:
        return ProvenanceTier.TIER_B
    return ProvenanceTier.TIER_C


def classify_sqsf_tier(
    score: float,
    hard_gates_passed: bool,
    d1_score: int = 5,
    d2_score: int = 5,
    d3_score: int = 5,
) -> SQSFClassificationTier:
    """Assign source to one of the 6 mutually exclusive operational tiers."""
    if not hard_gates_passed:
        # Check if eligible for test fixture or completely disqualified
        if d1_score < 3 or d3_score < 3:
            if d3_score >= 2 and d1_score >= 2:
                return SQSFClassificationTier.TIER_5_TEST_FIXTURE
            return SQSFClassificationTier.TIER_6_DISQUALIFIED
        if d2_score < 3:
            if d3_score >= 2:
                return SQSFClassificationTier.TIER_5_TEST_FIXTURE
            return SQSFClassificationTier.TIER_6_DISQUALIFIED

    if score >= 85.0:
        return SQSFClassificationTier.TIER_1_GROUND_TRUTH
    if score >= 75.0:
        return SQSFClassificationTier.TIER_2_POPULATION_BENCHMARK
    if score >= 65.0:
        return SQSFClassificationTier.TIER_3_MARKET_SIGNAL
    if score >= 60.0:
        return SQSFClassificationTier.TIER_4_SUPPLEMENTARY
    return SQSFClassificationTier.TIER_6_DISQUALIFIED


def evaluate_source(
    source_id: str,
    dimensions: DimensionScores,
    notes: str = "",
) -> SourceQualityEvaluation:
    """Evaluate a source fully from its 10 dimension scores."""
    score = compute_source_quality_score(dimensions)
    gates_passed, failed = evaluate_hard_gates(dimensions)
    sqsf_tier = classify_sqsf_tier(
        score=score,
        hard_gates_passed=gates_passed,
        d1_score=dimensions.d1_licensing_legal,
        d2_score=dimensions.d2_target_measure,
        d3_score=dimensions.d3_upstream_provenance,
    )
    prov_tier = map_score_to_provenance_tier(score, hard_gates_passed=gates_passed)
    # Only Tier 1 Ground Truth passing all gates is eligible for direct PT1 training
    is_pt1 = (sqsf_tier == SQSFClassificationTier.TIER_1_GROUND_TRUTH) and gates_passed

    return SourceQualityEvaluation(
        source_id=source_id,
        score=score,
        provenance_tier=prov_tier,
        sqsf_tier=sqsf_tier,
        hard_gates_passed=gates_passed,
        failed_gates=failed,
        is_pt1_training_eligible=is_pt1,
        dimension_scores=dimensions,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Default Source Registry (docs/research/05-source-scoring.md & config/sources)
# ---------------------------------------------------------------------------

DEFAULT_SOURCE_QUALITY_REGISTRY: dict[str, SourceQualityEvaluation] = {
    # 1. Primary Governed Voluntary Intake (Ground Truth)
    "SRC-INT-VOL-01": SourceQualityEvaluation(
        source_id="SRC-INT-VOL-01",
        score=96.0,
        provenance_tier=ProvenanceTier.TIER_A,
        sqsf_tier=SQSFClassificationTier.TIER_1_GROUND_TRUTH,
        hard_gates_passed=True,
        is_pt1_training_eligible=True,
        notes="Primary governed voluntary intake; itemized Basic + HRA + Special Allowance.",
    ),
    # 2. Macro Indicators & Taxonomies (Supplementary)
    "SRC-SUP-MAC-01": SourceQualityEvaluation(
        source_id="SRC-SUP-MAC-01",
        score=94.4,
        provenance_tier=ProvenanceTier.TIER_A,
        sqsf_tier=SQSFClassificationTier.TIER_4_SUPPLEMENTARY,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="RBI DBIE CPI-Urban & FX rates; temporal deflation and currency reference.",
    ),
    "SRC-SUP-TAX-01": SourceQualityEvaluation(
        source_id="SRC-SUP-TAX-01",
        score=84.4,
        provenance_tier=ProvenanceTier.TIER_A,
        sqsf_tier=SQSFClassificationTier.TIER_4_SUPPLEMENTARY,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="O*NET 29.0 taxonomy and standardized skills descriptors.",
    ),
    "SRC-SUP-TAX-02": SourceQualityEvaluation(
        source_id="SRC-SUP-TAX-02",
        score=79.8,
        provenance_tier=ProvenanceTier.TIER_B,
        sqsf_tier=SQSFClassificationTier.TIER_4_SUPPLEMENTARY,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="ESCO v1.1 European Skills/Competences taxonomy hierarchy.",
    ),
    # 3. Corporate Disclosures (Market Signal)
    "SRC-SUP-CORP-01": SourceQualityEvaluation(
        source_id="SRC-SUP-CORP-01",
        score=83.8,
        provenance_tier=ProvenanceTier.TIER_A,
        sqsf_tier=SQSFClassificationTier.TIER_3_MARKET_SIGNAL,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="BSE/NSE Sec 197(12) corporate median disclosures for listed IT firms.",
    ),
    # 4. Official Indian Labor Statistics
    "SRC-IND-OFF-01": SourceQualityEvaluation(
        source_id="SRC-IND-OFF-01",
        score=82.6,
        provenance_tier=ProvenanceTier.TIER_A,
        sqsf_tier=SQSFClassificationTier.TIER_2_POPULATION_BENCHMARK,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="MOSPI PLFS 2023-24 microdata; macro wage floor and PT6 population anchor.",
    ),
    "SRC-IND-OFF-02": SourceQualityEvaluation(
        source_id="SRC-IND-OFF-02",
        score=53.0,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_6_DISQUALIFIED,
        hard_gates_passed=False,
        failed_gates=["Gate 2 (Target) failed: manual blue-collar wages"],
        is_pt1_training_eligible=False,
        notes="Labour Bureau OWS 7th round; 8+ year stale blue-collar data, disqualified.",
    ),
    "SRC-IND-OFF-03": SourceQualityEvaluation(
        source_id="SRC-IND-OFF-03",
        score=59.2,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_6_DISQUALIFIED,
        hard_gates_passed=False,
        failed_gates=["Gate 2 (Target) failed: headcount counts only, zero wages"],
        is_pt1_training_eligible=False,
        notes="Labour Bureau QES IT/BPO employment counts; zero wage figures.",
    ),
    "SRC-IND-OFF-04": SourceQualityEvaluation(
        source_id="SRC-IND-OFF-04",
        score=56.8,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_6_DISQUALIFIED,
        hard_gates_passed=False,
        failed_gates=["Gate 2 (Target) failed: informal job vacancies"],
        is_pt1_training_eligible=False,
        notes="National Career Service (NCS) portal; non-tech, informal sector.",
    ),
    # 5. US Labor Disclosures & Benchmarks
    "SRC-USA-BLS-01": SourceQualityEvaluation(
        source_id="SRC-USA-BLS-01",
        score=78.2,
        provenance_tier=ProvenanceTier.TIER_B,
        sqsf_tier=SQSFClassificationTier.TIER_2_POPULATION_BENCHMARK,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="US BLS OEWS May 2023 tech estimates; isolated US benchmark.",
    ),
    "SRC-USA-DOL-01": SourceQualityEvaluation(
        source_id="SRC-USA-DOL-01",
        score=74.4,
        provenance_tier=ProvenanceTier.TIER_B,
        sqsf_tier=SQSFClassificationTier.TIER_3_MARKET_SIGNAL,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="US DOL OFLC H-1B LCA certified filings; expat and parent company wage parity.",
    ),
    "SRC-USA-DOL-02": SourceQualityEvaluation(
        source_id="SRC-USA-DOL-02",
        score=74.4,
        provenance_tier=ProvenanceTier.TIER_B,
        sqsf_tier=SQSFClassificationTier.TIER_3_MARKET_SIGNAL,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="US DOL OFLC PERM filings; returns to education and experience.",
    ),
    # 6. Kaggle & Community Datasets
    "SRC-KAG-SO-01": SourceQualityEvaluation(
        source_id="SRC-KAG-SO-01",
        score=72.2,
        provenance_tier=ProvenanceTier.TIER_B,
        sqsf_tier=SQSFClassificationTier.TIER_3_MARKET_SIGNAL,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="Stack Overflow Survey 2024; developer priors on YoE and tech stack.",
    ),
    "SRC-KAG-SO-02": SourceQualityEvaluation(
        source_id="SRC-KAG-SO-02",
        score=72.2,
        provenance_tier=ProvenanceTier.TIER_B,
        sqsf_tier=SQSFClassificationTier.TIER_3_MARKET_SIGNAL,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="Stack Overflow Survey 2023; multi-year drift analysis.",
    ),
    "SRC-KAG-AIJ-02": SourceQualityEvaluation(
        source_id="SRC-KAG-AIJ-02",
        score=60.8,
        provenance_tier=ProvenanceTier.TIER_C,
        sqsf_tier=SQSFClassificationTier.TIER_4_SUPPLEMENTARY,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="JobsInData 2024 global salary feed; PPP conversion exploration.",
    ),
    "SRC-KAG-AIJ-01": SourceQualityEvaluation(
        source_id="SRC-KAG-AIJ-01",
        score=60.2,
        provenance_tier=ProvenanceTier.TIER_C,
        sqsf_tier=SQSFClassificationTier.TIER_4_SUPPLEMENTARY,
        hard_gates_passed=True,
        is_pt1_training_eligible=False,
        notes="ai-jobs.net Data Science Salaries 2023; remote work spread baselines.",
    ),
    # 7. Testing Fixtures (Restricted to tests/fixtures/)
    "SRC-KAG-FIX-01": SourceQualityEvaluation(
        source_id="SRC-KAG-FIX-01",
        score=38.0,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_5_TEST_FIXTURE,
        hard_gates_passed=False,
        failed_gates=["Gate 1 & Gate 2 failed: scraped unbundled CTC strings"],
        is_pt1_training_eligible=False,
        notes="Software Industry Salaries 2022; currency & regex plumbing tests only.",
    ),
    "SRC-KAG-FIX-02": SourceQualityEvaluation(
        source_id="SRC-KAG-FIX-02",
        score=34.4,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_5_TEST_FIXTURE,
        hard_gates_passed=False,
        failed_gates=["Gate 1 & Gate 2 failed: scraped job postings"],
        is_pt1_training_eligible=False,
        notes="Jobs on Naukri.com (PromptCloud); NLP skill extraction tests only.",
    ),
    "SRC-KAG-FIX-03": SourceQualityEvaluation(
        source_id="SRC-KAG-FIX-03",
        score=32.0,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_5_TEST_FIXTURE,
        hard_gates_passed=False,
        failed_gates=["Gate 1 & Gate 2 failed: advertised pay ranges"],
        is_pt1_training_eligible=False,
        notes="India Job Market Trends 2026; PT3 schema testing only.",
    ),
    # 8. Disqualified Sources (Scraped / ToS Breaches)
    "SRC-KAG-REJ-01": SourceQualityEvaluation(
        source_id="SRC-KAG-REJ-01",
        score=26.0,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_6_DISQUALIFIED,
        hard_gates_passed=False,
        failed_gates=["Gate 1 (Legal) failed: scraped AmbitionBox portal (Rule R-DA-01)"],
        is_pt1_training_eligible=False,
        notes="Data Science Jobs in India; unauthorized scrape, disqualified.",
    ),
    "SRC-KAG-REJ-02": SourceQualityEvaluation(
        source_id="SRC-KAG-REJ-02",
        score=30.8,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_6_DISQUALIFIED,
        hard_gates_passed=False,
        failed_gates=["Gate 1 (Legal) failed: scraped Naukri portal (Rule R-DA-01)"],
        is_pt1_training_eligible=False,
        notes="Job Postings from Naukri (iqbal303); unauthorized scrape, disqualified.",
    ),
    "SRC-KAG-REJ-03": SourceQualityEvaluation(
        source_id="SRC-KAG-REJ-03",
        score=22.0,
        provenance_tier=ProvenanceTier.TIER_D,
        sqsf_tier=SQSFClassificationTier.TIER_6_DISQUALIFIED,
        hard_gates_passed=False,
        failed_gates=["Gate 1 (Legal) failed: scraped Naukri portal (Rule R-DA-01)"],
        is_pt1_training_eligible=False,
        notes="12,000 Data Science Jobs Naukri; unauthorized scrape, disqualified.",
    ),
}

DEFAULT_UNVERIFIED_EVALUATION = SourceQualityEvaluation(
    source_id="UNKNOWN",
    score=20.0,
    provenance_tier=ProvenanceTier.TIER_D,
    sqsf_tier=SQSFClassificationTier.TIER_6_DISQUALIFIED,
    hard_gates_passed=False,
    failed_gates=["Source unverified or missing from configuration catalog (Rule R-EV-01)"],
    is_pt1_training_eligible=False,
    notes="Unverified source defaulted to minimum score (Rule R-EV-01).",
)


# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------


def load_source_scoring_from_yaml(yaml_path: Path) -> SourceQualityEvaluation:
    """Load SQS score and SQSF classification from config/sources/<id>.yaml.

    Raises DataContractError if YAML is missing required scoring metadata.
    """
    if not yaml_path.exists():
        raise DataContractError(
            f"Source configuration file not found: {yaml_path}",
            code="SOURCE_CONFIG_NOT_FOUND",
            details={"path": str(yaml_path)},
        )

    try:
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        raise DataContractError(
            f"Failed to parse source YAML config: {yaml_path}: {exc}",
            code="SOURCE_CONFIG_PARSE_ERROR",
            details={"path": str(yaml_path), "error": str(exc)},
        ) from exc

    source_id = data.get("source_id", yaml_path.stem)
    score_val = data.get("sqs")
    if score_val is None:
        raise DataContractError(
            f"Source YAML {yaml_path} missing required 'sqs' field",
            code="MISSING_SQS_FIELD",
            details={"source_id": source_id},
        )

    score = float(score_val)
    tier_str = str(data.get("sqsf_tier", SQSFClassificationTier.TIER_6_DISQUALIFIED.value))

    # Normalize tier_str to standard enum
    normalized_tier: SQSFClassificationTier
    if "TIER_1" in tier_str or "GROUND_TRUTH" in tier_str:
        normalized_tier = SQSFClassificationTier.TIER_1_GROUND_TRUTH
    elif "TIER_2" in tier_str or "POPULATION_BENCHMARK" in tier_str:
        normalized_tier = SQSFClassificationTier.TIER_2_POPULATION_BENCHMARK
    elif "TIER_3" in tier_str or "MARKET_SIGNAL" in tier_str:
        normalized_tier = SQSFClassificationTier.TIER_3_MARKET_SIGNAL
    elif "TIER_4" in tier_str or "SUPPLEMENTARY" in tier_str:
        normalized_tier = SQSFClassificationTier.TIER_4_SUPPLEMENTARY
    elif "TIER_5" in tier_str or "TEST_FIXTURE" in tier_str:
        normalized_tier = SQSFClassificationTier.TIER_5_TEST_FIXTURE
    else:
        normalized_tier = SQSFClassificationTier.TIER_6_DISQUALIFIED

    # Check prohibited routing
    prohibited_routing = data.get("prohibited_routing", [])
    is_pt1 = ("PT1_direct_training" not in prohibited_routing) and (
        normalized_tier == SQSFClassificationTier.TIER_1_GROUND_TRUTH
    )

    # Hard gates determination
    hard_gates_passed = normalized_tier not in (
        SQSFClassificationTier.TIER_5_TEST_FIXTURE,
        SQSFClassificationTier.TIER_6_DISQUALIFIED,
    )
    prov_tier = map_score_to_provenance_tier(score, hard_gates_passed=hard_gates_passed)

    return SourceQualityEvaluation(
        source_id=source_id,
        score=score,
        provenance_tier=prov_tier,
        sqsf_tier=normalized_tier,
        hard_gates_passed=hard_gates_passed,
        failed_gates=[] if hard_gates_passed else ["Gate failed per configuration tier"],
        is_pt1_training_eligible=is_pt1,
        notes=data.get("notes", ""),
    )


def get_source_quality_evaluation(
    source_id: str,
    config_dir: Path | None = None,
    registry: dict[str, SourceQualityEvaluation] | None = None,
) -> SourceQualityEvaluation:
    """Retrieve SourceQualityEvaluation for a given source_id.

    Resolution order:
    1. Custom registry if provided
    2. File at <config_dir>/<source_id>.yaml if config_dir is provided and exists
    3. DEFAULT_SOURCE_QUALITY_REGISTRY
    4. DEFAULT_UNVERIFIED_EVALUATION
    """
    if registry is not None and source_id in registry:
        return registry[source_id]

    if config_dir is not None:
        yaml_file = config_dir / f"{source_id}.yaml"
        if yaml_file.exists():
            return load_source_scoring_from_yaml(yaml_file)

    if source_id in DEFAULT_SOURCE_QUALITY_REGISTRY:
        return DEFAULT_SOURCE_QUALITY_REGISTRY[source_id]

    # Fallback to unverified evaluation tagged with the requested source_id
    return SourceQualityEvaluation(
        source_id=source_id,
        score=DEFAULT_UNVERIFIED_EVALUATION.score,
        provenance_tier=DEFAULT_UNVERIFIED_EVALUATION.provenance_tier,
        sqsf_tier=DEFAULT_UNVERIFIED_EVALUATION.sqsf_tier,
        hard_gates_passed=DEFAULT_UNVERIFIED_EVALUATION.hard_gates_passed,
        failed_gates=[f"Unknown or unverified source_id '{source_id}' (Rule R-EV-01)"],
        is_pt1_training_eligible=False,
        notes="Unverified source defaulted to minimum score.",
    )


# ---------------------------------------------------------------------------
# Observation Scoring & Attachment
# ---------------------------------------------------------------------------


def score_observation(
    record: dict[str, Any],
    registry: dict[str, SourceQualityEvaluation] | None = None,
    config_dir: Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Attach source quality scores and provenance metadata to a single record dict.

    Added fields:
    - `source_quality_score`: float
    - `provenance_tier`: str ("A", "B", "C", "D")
    - `sqsf_tier`: str
    - `hard_gates_passed`: bool
    - `is_pt1_eligible`: bool

    Raises DataContractError if strict=True and source_id is unknown.
    """
    source_id = str(record.get("source_id", "UNKNOWN"))
    evaluation = get_source_quality_evaluation(
        source_id=source_id,
        config_dir=config_dir,
        registry=registry,
    )

    if strict and evaluation.failed_gates and "Unknown or unverified" in evaluation.failed_gates[0]:
        raise DataContractError(
            f"Strict source scoring rejection: unverified source '{source_id}'",
            code="UNVERIFIED_SOURCE_ERROR",
            details={"source_id": source_id, "record": record},
        )

    enriched = dict(record)
    enriched["source_quality_score"] = evaluation.score
    enriched["provenance_tier"] = evaluation.provenance_tier.value
    enriched["sqsf_tier"] = evaluation.sqsf_tier.value
    enriched["hard_gates_passed"] = evaluation.hard_gates_passed
    enriched["is_pt1_eligible"] = evaluation.is_pt1_training_eligible
    return enriched


def attach_source_quality_scores_df(
    df: pl.DataFrame,
    registry: dict[str, SourceQualityEvaluation] | None = None,
    config_dir: Path | None = None,
    strict: bool = False,
) -> pl.DataFrame:
    """Attach source quality scores and provenance metadata to a Polars DataFrame.

    Requires 'source_id' column in df.
    Preserves all original columns and row ordering with zero silent drops.

    Added columns:
    - `source_quality_score`: pl.Float64
    - `provenance_tier`: pl.String
    - `sqsf_tier`: pl.String
    - `hard_gates_passed`: pl.Boolean
    - `is_pt1_eligible`: pl.Boolean

    Raises:
        DataContractError: If 'source_id' column is missing, or if strict=True
                           and unknown/unverified sources are found.
    """
    if "source_id" not in df.columns:
        raise DataContractError(
            "DataFrame missing required 'source_id' column for source scoring",
            code="MISSING_SOURCE_ID_COLUMN",
            details={"available_columns": df.columns},
        )

    if df.height == 0:
        return df.with_columns(
            [
                pl.Series("source_quality_score", [], dtype=pl.Float64),
                pl.Series("provenance_tier", [], dtype=pl.String),
                pl.Series("sqsf_tier", [], dtype=pl.String),
                pl.Series("hard_gates_passed", [], dtype=pl.Boolean),
                pl.Series("is_pt1_eligible", [], dtype=pl.Boolean),
            ]
        )

    # Extract distinct source IDs present in the dataset
    distinct_sources = df["source_id"].unique().to_list()

    mapping_rows: list[dict[str, Any]] = []
    unverified_sources: list[str] = []

    for sid in distinct_sources:
        sid_str = str(sid) if sid is not None else "UNKNOWN"
        eval_result = get_source_quality_evaluation(
            source_id=sid_str,
            config_dir=config_dir,
            registry=registry,
        )
        if eval_result.failed_gates and "Unknown or unverified" in eval_result.failed_gates[0]:
            unverified_sources.append(sid_str)

        mapping_rows.append(
            {
                "source_id": sid,
                "source_quality_score": eval_result.score,
                "provenance_tier": eval_result.provenance_tier.value,
                "sqsf_tier": eval_result.sqsf_tier.value,
                "hard_gates_passed": eval_result.hard_gates_passed,
                "is_pt1_eligible": eval_result.is_pt1_training_eligible,
            }
        )

    if strict and unverified_sources:
        msg = (
            f"Strict source scoring rejection: {len(unverified_sources)} unverified source(s)"
            f" found: {unverified_sources}"
        )
        raise DataContractError(
            msg,
            code="UNVERIFIED_SOURCE_ERROR",
            details={"unverified_sources": unverified_sources},
        )

    scoring_table = pl.DataFrame(
        mapping_rows,
        schema={
            "source_id": df.schema["source_id"],
            "source_quality_score": pl.Float64,
            "provenance_tier": pl.String,
            "sqsf_tier": pl.String,
            "hard_gates_passed": pl.Boolean,
            "is_pt1_eligible": pl.Boolean,
        },
    )

    # Drop existing quality scoring columns if present to avoid duplicate column collisions
    cols_to_drop = [
        c
        for c in [
            "source_quality_score",
            "provenance_tier",
            "sqsf_tier",
            "hard_gates_passed",
            "is_pt1_eligible",
        ]
        if c in df.columns
    ]
    base_df = df.drop(cols_to_drop) if cols_to_drop else df

    enriched_df = base_df.join(scoring_table, on="source_id", how="left")
    return enriched_df


# ---------------------------------------------------------------------------
# Source Quality Scoring Report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceQualityReport:
    """Summary metrics of source quality scoring across an observation dataset."""

    total_observations: int
    distinct_sources: int
    mean_sqs: float
    provenance_tier_counts: dict[str, int]
    sqsf_tier_counts: dict[str, int]
    pt1_eligible_count: int
    pt1_ineligible_count: int
    per_source_summary: list[dict[str, Any]]

    def to_markdown(self) -> str:
        """Render report as a GitHub-style markdown audit table."""
        pct_eligible = self.pt1_eligible_count / max(1, self.total_observations)
        lines = [
            "# Source-Quality Scoring Audit Report",
            "",
            "| Metric | Value |",
            "|:---|:---|",
            f"| **Total Observations** | {self.total_observations:,} |",
            f"| **Distinct Sources** | {self.distinct_sources} |",
            f"| **Mean Source Quality Score (SQS)** | {self.mean_sqs:.1f} / 100.0 |",
            f"| **PT1 Eligible Observations** | {self.pt1_eligible_count:,} ({pct_eligible:.1%}) |",
            f"| **PT1 Ineligible Observations** | {self.pt1_ineligible_count:,} |",
            "",
            "## 1. Distribution by Canonical Provenance Tier (Rule R-UQ-07)",
            "",
            "| Provenance Tier | Description | Observation Count | Percentage |",
            "|:---|:---|:---:|:---:|",
        ]

        tier_descs = {
            "A": "Official population benchmarks & verified payslips (SQS >= 80)",
            "B": "Statutory corporate disclosures & employer syndication (65 <= SQS < 80)",
            "C": "Open public developer surveys (50 <= SQS < 65)",
            "D": "Unverified job board ranges or gate failure (SQS < 50)",
        }
        for t in ["A", "B", "C", "D"]:
            cnt = self.provenance_tier_counts.get(t, 0)
            pct = cnt / max(1, self.total_observations)
            lines.append(f"| **Tier {t}** | {tier_descs[t]} | {cnt:,} | {pct:.1%} |")

        lines.extend(
            [
                "",
                "## 2. Per-Source Detailed Quality Breakdown",
                "",
                "| Source ID | Count | SQS | Provenance | SQSF Tier | Hard Gates | PT1 Eligible |",
                "|:---|:---:|:---:|:---:|:---|:---:|:---:|",
            ]
        )

        for row in self.per_source_summary:
            gates_str = "PASSED" if row["hard_gates_passed"] else "FAILED"
            pt1_str = "YES" if row["is_pt1_eligible"] else "NO"
            sid = row["source_id"]
            cnt = row["count"]
            sqs = row["sqs"]
            prov = row["provenance_tier"]
            sqsf = row["sqsf_tier"]
            lines.append(
                f"| `{sid}` | {cnt:,} | {sqs:.1f} | {prov} | `{sqsf}` | {gates_str} | {pt1_str} |"
            )

        lines.append("")
        return "\n".join(lines)


def generate_source_quality_report(
    df: pl.DataFrame,
    registry: dict[str, SourceQualityEvaluation] | None = None,
    config_dir: Path | None = None,
) -> SourceQualityReport:
    """Generate a SourceQualityReport from a scored or unscored observations DataFrame."""
    if "source_quality_score" not in df.columns:
        df = attach_source_quality_scores_df(df, registry=registry, config_dir=config_dir)

    total_obs = df.height
    if total_obs == 0:
        return SourceQualityReport(
            total_observations=0,
            distinct_sources=0,
            mean_sqs=0.0,
            provenance_tier_counts={"A": 0, "B": 0, "C": 0, "D": 0},
            sqsf_tier_counts={},
            pt1_eligible_count=0,
            pt1_ineligible_count=0,
            per_source_summary=[],
        )

    distinct_srcs = df["source_id"].n_unique()
    raw_mean = df["source_quality_score"].mean()
    mean_sqs: float = float(raw_mean) if isinstance(raw_mean, int | float) else 0.0

    # Provenance counts
    prov_counts_df = df.group_by("provenance_tier").len()
    prov_counts: dict[str, int] = {
        row["provenance_tier"]: row["len"]
        for row in prov_counts_df.to_dicts()
        if row["provenance_tier"] is not None
    }

    # SQSF counts
    sqsf_counts_df = df.group_by("sqsf_tier").len()
    sqsf_counts: dict[str, int] = {
        row["sqsf_tier"]: row["len"]
        for row in sqsf_counts_df.to_dicts()
        if row["sqsf_tier"] is not None
    }

    # PT1 eligibility counts
    pt1_eligible = int(df.filter(pl.col("is_pt1_eligible")).height)
    pt1_ineligible = total_obs - pt1_eligible

    # Per source summary
    group_cols = [
        "source_id",
        "source_quality_score",
        "provenance_tier",
        "sqsf_tier",
        "hard_gates_passed",
        "is_pt1_eligible",
    ]
    per_source_df = df.group_by(group_cols).len().sort("len", descending=True)

    per_source_summary = [
        {
            "source_id": row["source_id"],
            "count": row["len"],
            "sqs": row["source_quality_score"],
            "provenance_tier": row["provenance_tier"],
            "sqsf_tier": row["sqsf_tier"],
            "hard_gates_passed": row["hard_gates_passed"],
            "is_pt1_eligible": row["is_pt1_eligible"],
        }
        for row in per_source_df.to_dicts()
    ]

    return SourceQualityReport(
        total_observations=total_obs,
        distinct_sources=distinct_srcs,
        mean_sqs=mean_sqs,
        provenance_tier_counts=prov_counts,
        sqsf_tier_counts=sqsf_counts,
        pt1_eligible_count=pt1_eligible,
        pt1_ineligible_count=pt1_ineligible,
        per_source_summary=per_source_summary,
    )
