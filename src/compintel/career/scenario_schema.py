"""Pydantic v2 schemas and contracts for practice scenarios (Phase 15D, Task T15.22).

Adheres strictly to:
- PRD Section 12 & FR-24: Deterministic flaw-finding practice workspace.
- ADR-0010 & Rule R-CR-15: Zero runtime Large Language Models on serving/scoring path.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit,
  false-flag penalties, and per-competency evidence generation.
- Rule R-CR-11: Practice, not certification (strictly prohibits 'exam', 'certified',
  'credential', 'accreditation' terms).
- Rule R-CR-01: Prohibits causal compensation promises.
- Rule R-CR-04: Ground-truth provenance and source attribution tracking.
- Rule R-CD-01: Strict type annotations, frozen where appropriate, runtime validation.
- Rule R-CD-03: Architectural boundary; career only imports schema.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from compintel.career.schema import (
    RoleLevel,
    TaxonomyProvenance,
    validate_anti_causal_text,
)
from compintel.schema.enums import RoleFamily

# Prohibited credentialism patterns under Rule R-CR-11
FORBIDDEN_CREDENTIAL_PATTERNS = [
    r"\bcertif(ied|ication|icate|y)\b",
    r"\bcredential(ed|ing|s)?\b",
    r"\baccredit(ed|ation)?\b",
    r"\bexam(ination|s)?\b",
    r"\bofficial\s+assessment\b",
    r"\blicensed?\s+practitioner\b",
]
_COMPILED_CREDENTIAL_RE = re.compile("|".join(FORBIDDEN_CREDENTIAL_PATTERNS), re.IGNORECASE)


def validate_anti_credential_text(text: str, field_name: str) -> str:
    """Validate that text does not contain credentialism or exam terminology (Rule R-CR-11).

    Args:
        text: Input string to validate.
        field_name: Name of the model field for error diagnostics.

    Returns:
        The validated text if no prohibited patterns are found.

    Raises:
        ValueError: If prohibited credentialism or exam terms are detected.
    """
    match = _COMPILED_CREDENTIAL_RE.search(text)
    if match:
        raise ValueError(
            f"Prohibited credentialism term detected in '{field_name}': '{match.group(0)}'. "
            "Rule R-CR-11 and ADR-0013 strictly prohibit credentialing, exam, or certification "
            "terminology. Career Architect provides self-directed practice and evidence, "
            "not credentials."
        )
    return text


# -----------------------------------------------------------------------------
# 1. Enums & Categorical Types
# -----------------------------------------------------------------------------


class ArtifactLanguage(StrEnum):
    """Supported syntax language classes for practice code artifacts."""

    SQL = "sql"
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    YAML = "yaml"
    JSON = "json"
    MARKDOWN = "markdown"


class DefectCategory(StrEnum):
    """Categorical taxonomy of domain defects in technical artifacts."""

    # Data science / analytics defects
    DATA_LEAKAGE = "data_leakage"
    DIVISION_BY_ZERO = "division_by_zero"
    NULL_HANDLING = "null_handling"
    LOOKAHEAD_BIAS = "lookahead_bias"
    SAMPLE_RATIO_MISMATCH = "sample_ratio_mismatch"
    METRIC_MISALIGNMENT = "metric_misalignment"
    AGGREGATION_BIAS = "aggregation_bias"
    CARDINALITY_EXPLOSION = "cardinality_explosion"

    # Software engineering defects
    RACE_CONDITION = "race_condition"
    RESOURCE_LEAK = "resource_leak"
    SQL_INJECTION = "sql_injection"
    UNBOUNDED_COLLECTION = "unbounded_collection"
    BROKEN_AUTHENTICATION = "broken_authentication"


class DefectSeverity(StrEnum):
    """Engineering impact severity of seeded defects."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


# -----------------------------------------------------------------------------
# 2. Artifact & Seeded Defect Models
# -----------------------------------------------------------------------------


class ScenarioArtifact(BaseModel):
    """Raw technical code, query, or configuration artifact presented for flaw finding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content: str = Field(
        ...,
        min_length=10,
        description="Raw text of the technical artifact (code, query, pipeline YAML)",
    )
    language: ArtifactLanguage = Field(
        default=ArtifactLanguage.SQL,
        description="Syntax language of the artifact",
    )
    line_count: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Total line count in the artifact content",
    )

    @model_validator(mode="after")
    def validate_line_count(self) -> Self:
        """Verify stated line_count strictly matches actual splitlines length."""
        actual_lines = len(self.content.splitlines())
        if actual_lines != self.line_count:
            err_msg = f"line_count ({self.line_count}) does not match actual lines ({actual_lines})"
            raise ValueError(err_msg)
        return self


class SeededDefect(BaseModel):
    """Deterministic ground-truth flaw seeded in a technical practice artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., pattern=r"^[A-Z0-9_\-]+$", description="Unique defect ID (e.g. DEF-01)")
    line_number: int = Field(..., ge=1, description="1-indexed line number containing the flaw")
    category: DefectCategory = Field(..., description="Diagnostic defect classification")
    severity: DefectSeverity = Field(
        default=DefectSeverity.MAJOR, description="Engineering defect severity"
    )
    title: str = Field(..., min_length=3, max_length=120)
    consequence: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Real-world technical, statistical, or business consequence if deployed",
    )
    diagnostic_explanation: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Detailed technical reasoning why this line is flawed and how to correct it",
    )
    competency_id: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$",
        description="Canonical competency ID in DATA graph addressed by this flaw",
    )
    points: float = Field(
        default=1.0,
        gt=0.0,
        le=10.0,
        description="Credit points awarded for detecting this flaw",
    )

    @field_validator("title", "consequence", "diagnostic_explanation")
    @classmethod
    def check_invariants(cls, v: str, info: object) -> str:
        field_name = getattr(info, "field_name", "unknown")
        validate_anti_causal_text(v, field_name)
        validate_anti_credential_text(v, field_name)
        return v


class FalseFlagPenalty(BaseModel):
    """Configuration for deducting points on incorrect line flags to prevent guessing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    penalty_per_flag: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Point deduction per flagged line that is not a defect",
    )
    max_penalty: float = Field(
        default=2.0,
        ge=0.0,
        le=20.0,
        description="Maximum total false flag deduction ceiling",
    )

    @model_validator(mode="after")
    def validate_penalty_bounds(self) -> Self:
        if self.penalty_per_flag > self.max_penalty:
            err_msg = (
                f"penalty_per_flag ({self.penalty_per_flag}) exceeds "
                f"max_penalty ({self.max_penalty})"
            )
            raise ValueError(err_msg)
        return self


class ScenarioRubric(BaseModel):
    """Deterministic scoring rubric for an engineering practice scenario."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str = Field(..., min_length=3, max_length=100)
    defects: list[SeededDefect] = Field(..., min_length=1, max_length=20)
    pass_threshold_score: float = Field(
        ...,
        ge=0.0,
        description="Minimum score required to demonstrate targeted competency",
    )
    false_flag_penalty: FalseFlagPenalty = Field(default_factory=FalseFlagPenalty)

    @property
    def max_possible_score(self) -> float:
        """Total theoretical maximum points if all flaws are detected without false flags."""
        return round(sum(d.points for d in self.defects), 2)

    @model_validator(mode="after")
    def validate_threshold(self) -> Self:
        max_score = sum(d.points for d in self.defects)
        if self.pass_threshold_score > max_score:
            err_msg = (
                f"pass_threshold_score ({self.pass_threshold_score}) exceeds max ({max_score})"
            )
            raise ValueError(err_msg)
        return self


class ScenarioVariant(BaseModel):
    """Parameterized variant rotating variable names, table schemas, or metric contexts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variant_id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$")
    description: str = Field(..., min_length=5, max_length=300)
    parameters: dict[str, str] = Field(default_factory=dict)
    artifact_override: ScenarioArtifact | None = Field(default=None)
    rubric_override: ScenarioRubric | None = Field(default=None)


# -----------------------------------------------------------------------------
# 3. Server-Side Ground Truth Scenario & Anti-Leakage Client View
# -----------------------------------------------------------------------------


class ClientScenarioChallenge(BaseModel):
    """Leak-proof client-facing view of a practice scenario.

    Strictly satisfies ADR-0013 and Rule R-CR-08: Contains zero defect line numbers,
    zero answer keys, and zero scoring point allocations.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    variant_id: str | None = None
    title: str
    description: str
    role_family: str
    target_level: RoleLevel
    primary_competency_id: str
    secondary_competency_ids: list[str] = Field(default_factory=list)
    artifact: ScenarioArtifact
    available_defect_categories: list[DefectCategory]
    instructions: str
    disclaimer: str


class PracticeScenario(BaseModel):
    """Full internal server-side practice scenario definition with ground-truth rubric."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        ...,
        pattern=r"^[A-Z0-9_\-]+$",
        description="Scenario ID (e.g. SCEN-DATA-01-SQL)",
    )
    title: str = Field(..., min_length=5, max_length=120)
    description: str = Field(..., min_length=10, max_length=1000)
    role_family: Literal[RoleFamily.DATA] = Field(
        default=RoleFamily.DATA, description="DATA family in Phase 15"
    )
    target_level: RoleLevel = Field(
        default=RoleLevel.LEVEL_3_MID, description="Target seniority level"
    )
    primary_competency_id: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$",
        description="Main competency unlocked upon successful completion",
    )
    secondary_competency_ids: list[str] = Field(default_factory=list)
    artifact: ScenarioArtifact
    rubric: ScenarioRubric
    variants: list[ScenarioVariant] = Field(default_factory=list)
    instructions: str = Field(
        default=(
            "Review the technical artifact, flag line(s) containing engineering or "
            "methodological defects, and classify each flaw category."
        )
    )
    disclaimer: str = Field(
        default=(
            "Technical practice scenario for capability self-reflection. "
            "Not an examination, appraisal, or certification (Rules R-CR-08, R-CR-11)."
        )
    )
    provenance: TaxonomyProvenance

    @field_validator("title", "description", "instructions", "disclaimer")
    @classmethod
    def check_invariants(cls, v: str, info: object) -> str:
        field_name = getattr(info, "field_name", "unknown")
        validate_anti_causal_text(v, field_name)
        validate_anti_credential_text(v, field_name)
        return v

    @model_validator(mode="after")
    def validate_defect_lines_in_bounds(self) -> Self:
        """Enforce invariant that every defect line_number exists within artifact bounds."""
        for defect in self.rubric.defects:
            if defect.line_number > self.artifact.line_count:
                raise ValueError(
                    f"Defect {defect.id} line_number ({defect.line_number}) exceeds "
                    f"artifact line count ({self.artifact.line_count})"
                )
        return self

    def to_client_challenge(self, variant_id: str | None = None) -> ClientScenarioChallenge:
        """Generate client-safe challenge view stripped of answer keys (ADR-0013).

        Args:
            variant_id: Optional parameterized variant identifier.

        Returns:
            ClientScenarioChallenge containing only public challenge data.
        """
        artifact = self.artifact
        if variant_id:
            for v in self.variants:
                if v.variant_id == variant_id and v.artifact_override:
                    artifact = v.artifact_override
                    break

        return ClientScenarioChallenge(
            id=self.id,
            variant_id=variant_id,
            title=self.title,
            description=self.description,
            role_family=self.role_family.value,
            target_level=self.target_level,
            primary_competency_id=self.primary_competency_id,
            secondary_competency_ids=list(self.secondary_competency_ids),
            artifact=artifact,
            available_defect_categories=list(DefectCategory),
            instructions=self.instructions,
            disclaimer=self.disclaimer,
        )


# -----------------------------------------------------------------------------
# 4. Candidate Submission & Deterministic Evaluation Types
# -----------------------------------------------------------------------------


class CandidateFlagSubmission(BaseModel):
    """Candidate flag placed on a specific line of the practice artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    line_number: int = Field(..., ge=1, description="1-indexed line number flagged as flawed")
    selected_category: DefectCategory = Field(
        ..., description="Candidate-selected diagnostic flaw category"
    )
    justification_notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional candidate notes or rationale for self-reflection",
    )


class ScenarioAttemptSubmission(BaseModel):
    """Payload submitted by candidate for deterministic rubric evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str = Field(..., min_length=3, max_length=100)
    variant_id: str | None = Field(default=None)
    flags: list[CandidateFlagSubmission] = Field(default_factory=list)


class ScoredDefectResult(BaseModel):
    """Diagnostic outcome for a single seeded flaw following deterministic scoring."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    defect_id: str
    target_line_number: int
    detected: bool
    line_matched: bool
    category_matched: bool
    awarded_points: float
    max_points: float
    severity: DefectSeverity
    title: str
    consequence: str
    diagnostic_explanation: str
    competency_id: str


class FalseFlagRecord(BaseModel):
    """Record of an incorrect flag placed on non-defective code with penalty applied."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    line_number: int
    selected_category: DefectCategory
    penalty_applied: float


class ScenarioAttemptEvaluation(BaseModel):
    """Comprehensive deterministic evaluation report for a practice scenario attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    variant_id: str | None = None
    passed: bool = Field(
        ..., description="True if score >= pass_threshold_score, demonstrating competency"
    )
    score: float = Field(..., description="Final net score (awarded credits - false flag penalty)")
    max_possible_score: float
    pass_threshold_score: float
    detected_defect_count: int
    total_defect_count: int
    false_flag_count: int
    false_flag_penalty_applied: float
    defect_results: list[ScoredDefectResult]
    false_flags: list[FalseFlagRecord] = Field(default_factory=list)
    demonstrated_competency_ids: list[str] = Field(
        default_factory=list,
        description="Competency IDs to transition to Demonstrated in local ledger (Rule R-CR-03)",
    )
    evaluated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    disclaimer: str = Field(
        default=(
            "Deterministic rubric evaluation for capability practice. "
            "Not an official credential, exam score, or certification (Rules R-CR-08, R-CR-11)."
        )
    )
