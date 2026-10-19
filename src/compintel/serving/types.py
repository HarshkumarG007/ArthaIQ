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
