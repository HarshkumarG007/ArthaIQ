"""Serving request and response types for ArthaIQ (Phase 9, Task T9.01).

Adheres to:
- architecture.md Section 11: estimate(profile, as_of) -> Estimate | Abstained.
- PRD Section 5, FR-02, FR-19: Six segregated targets, quantile spans, decoupled evidence.
- Rule R-ER-02: Expected outcomes (such as abstention) use result types, never exceptions.
- Rule R-UQ-01: Never return a lone point estimate; return P10, P50, P90 quantiles.
- Rule R-UQ-02: Abstention is an honest, structured outcome returning HTTP 200 payload.
- Rule R-MD-13: Current pay anchoring quarantine (Compare-Only architecture).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# -----------------------------------------------------------------------------
# 1. Request Types
# -----------------------------------------------------------------------------


class ExperienceInput(BaseModel):
    """Input experience structure conforming to architecture.md Section 11."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    total_years: float | None = Field(
        default=None,
        ge=0.0,
        le=50.0,
        description="Total relevant professional experience in years.",
    )
    level_id: str | None = Field(
        default=None,
        description="Standardized seniority tier (e.g., JR, MID, SR, STAFF, PRINCIPAL).",
    )


class ProfileRequest(BaseModel):
    """Profile payload submitted for compensation estimation."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    occupation_id: str = Field(
        ...,
        description="Occupation identifier or role family (e.g., SWE, DATA, MLAI).",
    )
    location_id: str = Field(
        ...,
        description="Geographic metro tech hub identifier (e.g., BENGALURU, HYDERABAD, PUNE).",
    )
    experience: ExperienceInput = Field(
        default_factory=ExperienceInput,
        description="Experience parameters including total years and seniority level.",
    )
    extras: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional L1+ feature conditioning attributes (e.g. work_arrangement).",
    )


class EstimateRequest(BaseModel):
    """Complete request payload for POST /v1/estimates."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    profile: ProfileRequest
    measure: str = Field(
        default="guaranteed_cash_annual",
        description="Compensation measure; PT1 strictly requires guaranteed_cash_annual.",
    )
    currency: str = Field(
        default="INR",
        description="Nominal currency code; ArthaIQ strictly prices in INR.",
    )
    as_of: str | None = Field(
        default=None,
        description="Point-in-time valuation anchor date in ISO-8601 format (YYYY-MM-DD).",
    )
    current_compensation: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional current pay in INR LPA for compare-only positioning (R-MD-13).",
    )


# -----------------------------------------------------------------------------
# 2. Response Sub-components
# -----------------------------------------------------------------------------


class QuantileSpan(BaseModel):
    """Empirical pay quantile span (P10, P50, P90) in nominal INR LPA."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    p10: float = Field(..., description="10th percentile conservative market floor in LPA.")
    p50: float = Field(..., description="50th percentile median benchmark in LPA.")
    p90: float = Field(..., description="90th percentile upper premium tier in LPA.")
    currency: str = Field(default="INR", description="Currency denomination.")
    period: str = Field(default="annual", description="Annualized pay period.")
    measure: str = Field(
        default="guaranteed_cash_annual", description="Contractual base compensation."
    )
    pre_tax: bool = Field(default=True, description="Pre-tax gross compensation.")
    nominal: bool = Field(default=True, description="Nominal current INR value.")


class ReliabilityInfo(BaseModel):
    """Reliability and evidence grading attached to prediction."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    grade: str = Field(..., description="Composite evidence grade: GRADE_A, GRADE_B, or GRADE_C.")
    reasons: list[str] = Field(
        default_factory=list, description="Reason codes or caveats regarding evidence."
    )


class SourceMixItem(BaseModel):
    """Observation provenance representation."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    source_type: str = Field(
        ..., description="Provenance category (e.g. statutory_filing, voluntary_intake)."
    )
    share: float = Field(
        ..., ge=0.0, le=1.0, description="Fractional share of cohort data [0.0, 1.0]."
    )


class EvidenceInfo(BaseModel):
    """Empirical cohort evidence metadata and provenance."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    cohort_n: int = Field(
        ..., ge=0, description="Verified sample count in matching occupational cohort."
    )
    source_mix: list[SourceMixItem] = Field(
        default_factory=list, description="Provenance breakdown of cohort."
    )
    median_observation_age_days: float = Field(
        ..., ge=0.0, description="Median age of cohort observations in days."
    )
    data_snapshot_id: str = Field(
        ..., description="Cryptographic canonical data lineage snapshot ID."
    )
    model_version: str = Field(..., description="Active production model version.")


class ComparisonInfo(BaseModel):
    """Compare-only positioning of candidate's current compensation (PT6 / Rule R-MD-13)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    current_compensation: float = Field(
        ..., description="User-reported current base compensation in LPA."
    )
    delta_to_median_lpa: float = Field(
        ..., description="Difference from market median: current - p50."
    )
    position_category: str = Field(
        ...,
        description="Relative positioning: below_floor, below_median, median, above_median, top.",
    )
    percentile_band: str = Field(
        ...,
        description="Estimated quantile band: <P10, P10-P50, P50-P90, >P90.",
    )


class AbstentionReasonItem(BaseModel):
    """Individual reason for model abstention (Rules R-MD-08, R-UQ-02)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    code: str = Field(..., description="Machine-readable abstention code.")
    detail: str = Field(
        ..., description="Human-readable explanation of why the engine withheld estimation."
    )


class FallbackItem(BaseModel):
    """Actionable user suggestion when model abstains on thin support."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    type: str = Field(..., description="Fallback category (e.g. broader_cohort, remove_extras).")
    description: str = Field(..., description="Guidance on how to broaden search criteria.")


# -----------------------------------------------------------------------------
# 3. Primary Response Types (architecture.md Section 11)
# -----------------------------------------------------------------------------


class Estimate(BaseModel):
    """Successful compensation intelligence estimate payload (status='ok')."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    request_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique request tracing ID."
    )
    status: Literal["ok"] = "ok"
    estimate: QuantileSpan
    reliability: ReliabilityInfo
    evidence: EvidenceInfo
    profile_level_used: int = Field(
        default=0, ge=0, le=2, description="Level of personalization applied (0, 1, 2)."
    )
    warnings: list[str] = Field(
        default_factory=list, description="Non-fatal warnings or advisories."
    )
    disclaimer_id: str = Field(
        default="decision_support_v1", description="Statutory disclaimer identifier."
    )
    as_of: str = Field(..., description="Valuation effective anchor date (YYYY-MM-DD).")
    model_version: str = Field(..., description="Serving model version identifier.")
    data_snapshot_id: str = Field(..., description="Data snapshot lineage identifier.")
    comparison: ComparisonInfo | None = Field(
        default=None,
        description="Compare-only analysis if current pay provided (PT6).",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert estimate to standard dictionary."""
        return self.model_dump()


class Abstained(BaseModel):
    """Statistically defensible abstention payload (status='abstained')."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    request_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique request tracing ID."
    )
    status: Literal["abstained"] = "abstained"
    reasons: list[AbstentionReasonItem] = Field(
        ..., description="Structured reasons for abstaining."
    )
    fallbacks: list[FallbackItem] = Field(
        default_factory=list, description="Actionable query alternatives."
    )
    disclaimer_id: str = Field(
        default="decision_support_v1", description="Statutory disclaimer identifier."
    )
    as_of: str = Field(..., description="Valuation effective anchor date (YYYY-MM-DD).")
    model_version: str = Field(..., description="Serving model version identifier.")
    data_snapshot_id: str = Field(..., description="Data snapshot lineage identifier.")

    def to_dict(self) -> dict[str, Any]:
        """Convert abstention to standard dictionary."""
        return self.model_dump()


# Union result type representing the outcome of estimate()
EstimateResult = Estimate | Abstained


# -----------------------------------------------------------------------------
# 4. Taxonomy & Reference Lookup Types
# -----------------------------------------------------------------------------


class OccupationItem(BaseModel):
    """Canonical occupational role family representation."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(..., description="Role family identifier (e.g. SWE, DATA, MLAI).")
    name: str = Field(..., description="Human-readable title.")
    description: str = Field(..., description="Scope of technical discipline.")
    examples: list[str] = Field(default_factory=list, description="Common matching job titles.")


class OccupationsResponse(BaseModel):
    """Response payload for GET /v1/taxonomy/occupations."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    total: int = Field(..., ge=0, description="Total matching occupations.")
    query: str | None = Field(default=None, description="Applied search query filter.")
    items: list[OccupationItem] = Field(default_factory=list, description="Occupational items.")


class LocationItem(BaseModel):
    """Standardized Indian metro technology hub representation."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(..., description="Standardized metro identifier (e.g. BENGALURU).")
    name: str = Field(..., description="Primary city / metro display name.")
    state: str = Field(..., description="State or union territory.")
    tier: int = Field(..., ge=1, le=3, description="Metro city tier classification.")
    aliases: list[str] = Field(default_factory=list, description="Common aliases and acronyms.")


class LocationsResponse(BaseModel):
    """Response payload for GET /v1/taxonomy/locations."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    total: int = Field(..., ge=0, description="Total matching locations.")
    query: str | None = Field(default=None, description="Applied search query filter.")
    items: list[LocationItem] = Field(default_factory=list, description="Location items.")


class SeniorityItem(BaseModel):
    """Standardized seniority tier representation."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(..., description="Seniority code (JR, MID, SR, STAFF, PRINCIPAL).")
    name: str = Field(..., description="Display title for seniority tier.")
    typical_years: str = Field(..., description="Typical experience span in years.")
    description: str = Field(..., description="Scope of independence and technical impact.")


class SenioritiesResponse(BaseModel):
    """Response payload for GET /v1/taxonomy/seniorities."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    total: int = Field(..., ge=0, description="Total seniority levels.")
    items: list[SeniorityItem] = Field(default_factory=list, description="Seniority items.")


# -----------------------------------------------------------------------------
# 5. Model Metadata, Sources, and Evidence Types (T9.05, architecture.md Sec 11)
# -----------------------------------------------------------------------------


class CurrentModelResponse(BaseModel):
    """Runtime metadata, lineage, and card information for active champion model."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    model_version: str = Field(..., description="Active champion semantic version (e.g. 0.1.0).")
    bundle_name: str = Field(..., description="Champion bundle package name.")
    rung: str = Field(..., description="Benchmark ladder rung (e.g. Rung F).")
    target_variable: str = Field(
        ..., description="Primary compensation measure (guaranteed_cash_annual)."
    )
    target_unit: str = Field(..., description="Target currency and unit (nominal INR LPA).")
    created_at_utc: str = Field(..., description="UTC timestamp of model promotion.")
    canonical_snapshot_id: str = Field(
        ..., description="Cryptographic dataset snapshot identifier."
    )
    git_commit_hash: str = Field(..., description="Git commit hash of model training state.")
    model_family: str = Field(..., description="Statistical learning model family.")
    quantiles: list[float] = Field(
        default_factory=lambda: [0.10, 0.50, 0.90], description="Target quantile levels."
    )
    metrics_summary: dict[str, Any] = Field(
        default_factory=dict, description="Pre-registered benchmark metrics."
    )
    features: list[str] = Field(default_factory=list, description="Model input features.")
    has_rollback: bool = Field(
        default=False, description="Whether previous champion bundle is buffered for rollback."
    )
    limitations: list[str] = Field(
        default_factory=list, description="Mandatory operational limitations and assumptions."
    )
    operational_rules: list[str] = Field(
        default_factory=list, description="Governance rules enforced by serving runtime."
    )


class ModelCardResponse(BaseModel):
    """Model card full markdown and governance metadata."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    model_version: str = Field(..., description="Active champion semantic version.")
    canonical_snapshot_id: str = Field(
        ..., description="Cryptographic dataset snapshot identifier."
    )
    card_markdown: str = Field(..., description="Full model card markdown content.")


class SourceItem(BaseModel):
    """Approved data source specification and provenance metadata."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    source_id: str = Field(..., description="Unique source code (e.g. SRC-INT-VOL-01).")
    name: str = Field(..., description="Full descriptive title of data provider.")
    licence: str = Field(..., description="Legal license / consent basis under Rule R-DA-01.")
    tier: str = Field(..., description="Source Quality Scoring Framework tier (TIER_A, TIER_B).")
    training_eligible: bool = Field(
        ..., description="Whether source observations enter model training."
    )
    purpose: str = Field(..., description="Governance scope and purpose of the dataset.")
    record_count: int | None = Field(default=None, description="Observation count in snapshot.")
    freshness: str | None = Field(
        default=None, description="Observation currency / update cadence."
    )


class SourcesResponse(BaseModel):
    """Response payload for GET /v1/sources."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    total: int = Field(..., ge=0, description="Total approved data sources.")
    data_snapshot_id: str = Field(..., description="Canonical data lineage snapshot ID.")
    model_version: str = Field(..., description="Active serving model version ID.")
    sources: list[SourceItem] = Field(
        default_factory=list, description="Approved sources inventory."
    )
    policy: str = Field(..., description="Legal and licensing compliance policy statement.")
    licence_gate_status: str = Field(
        default="COMPLIANT_R_DA_01", description="Statutory license gate verification."
    )


class SourceDistributionItem(BaseModel):
    """Distribution share of an individual source type across the evidence base."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    source_id: str = Field(..., description="Source identifier.")
    source_name: str = Field(..., description="Source name.")
    provenance_tier: str = Field(..., description="SQSF provenance tier (TIER_A, TIER_B).")
    share: float = Field(..., ge=0.0, le=1.0, description="Proportion of total observations.")


class EvidenceSummaryResponse(BaseModel):
    """Global evidence base summary for GET /v1/evidence/summary."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    data_snapshot_id: str = Field(..., description="Active canonical dataset snapshot ID.")
    model_version: str = Field(..., description="Active model version ID.")
    as_of: str = Field(..., description="Valuation / release date.")
    total_verified_observations: int = Field(
        ..., ge=0, description="Total verified observations in snapshot."
    )
    occupations_covered: list[str] = Field(
        default_factory=list, description="Canonical roles represented."
    )
    locations_covered: list[str] = Field(
        default_factory=list, description="Metro tech hubs represented."
    )
    source_distribution: list[SourceDistributionItem] = Field(
        default_factory=list, description="Composition across sources."
    )
    median_observation_age_days: float = Field(
        ..., ge=0.0, description="Median age of observations in days."
    )
    evidence_grades_policy: dict[str, str] = Field(
        default_factory=dict, description="Criteria for grades A, B, C."
    )
    abstention_thresholds: dict[str, Any] = Field(
        default_factory=dict, description="Preregistered abstention cutoffs."
    )


class CohortEvidenceResponse(BaseModel):
    """Cell/cohort-level evidence lookup response for GET /v1/evidence/cohort."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    occupation_id: str = Field(..., description="Queried occupation identifier.")
    location_id: str = Field(..., description="Queried location identifier.")
    seniority: str | None = Field(default=None, description="Queried seniority tier.")
    data_snapshot_id: str = Field(..., description="Data snapshot ID.")
    model_version: str = Field(..., description="Model version ID.")
    cohort_n: int = Field(..., ge=0, description="Sample size of comparable verified records.")
    evidence_grade: str = Field(
        ..., description="Decoupled evidence grade (GRADE_A, GRADE_B, GRADE_C)."
    )
    support_status: str = Field(
        ..., description="Support status (SUPPORTED, GUARDED, THIN_SUPPORT)."
    )
    is_supported: bool = Field(
        ..., description="Whether cohort meets minimum support for estimation."
    )
    source_mix: list[SourceMixItem] = Field(
        default_factory=list, description="Breakdown of source contributions."
    )
    median_observation_age_days: float = Field(
        ..., ge=0.0, description="Median observation age in days."
    )
    newest_observation_date: str = Field(..., description="Date of newest observation in cohort.")
    disclaimer: str = Field(..., description="Statutory decision-support disclosure.")


# -----------------------------------------------------------------------------
# 8. Pilot Feedback Types (PRD Section 11, T10.01)
# -----------------------------------------------------------------------------


class FeedbackSubmissionRequest(BaseModel):
    """Anonymous pilot feedback payload for POST /v1/feedback."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    rating_clarity: int = Field(
        ...,
        ge=1,
        le=5,
        description="Clarity rating (1: completely unclear, 5: very clear).",
    )
    rating_usefulness: int = Field(
        ...,
        ge=1,
        le=5,
        description="Usefulness rating (1: not useful, 5: highly actionable).",
    )
    comprehension_confirmed: bool = Field(
        default=False,
        description=(
            "User confirmation that range is an empirical estimate, "
            "not a salary guarantee or appraisal."
        ),
    )
    feedback_text: str | None = Field(
        default=None,
        max_length=500,
        description="Optional qualitative feedback comment (max 500 characters, PII scrubbed).",
    )
    request_id: str | None = Field(
        default=None,
        description="Optional correlation request_id from prior estimate.",
    )
    surface: str = Field(
        default="estimate_screen",
        description="Product surface where feedback was submitted.",
    )


class FeedbackSubmissionResponse(BaseModel):
    """Response returned upon successful feedback submission."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    status: Literal["received"] = "received"
    feedback_id: str = Field(..., description="Unique anonymized feedback receipt ID.")
    sanitized: bool = Field(
        default=True,
        description="Whether textual comments underwent automated PII scrubbing.",
    )
    received_at_utc: str = Field(..., description="ISO 8601 timestamp in UTC.")
