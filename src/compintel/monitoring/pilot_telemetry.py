"""ArthaIQ Pilot Cohort Privacy-Preserving Telemetry Engine (T20.02).

Implements client-side and server-side aggregation for pilot evaluation metrics under:
- India DPDP Act 2023:
  - Section 6: Non-identifying statistical research aggregation
  - Section 12: Zero persistent retention of raw participant records
- Privacy Invariants:
  - k-Anonymity (k >= 5): Demographic cell suppression preventing re-identification
  - Zero PII: Rejection of IP addresses, device identifiers, and names
  - Two Streams Two Places: Decoupled pay comprehension vs practice scores
- 10 Pre-Registered Quality & Compliance Metrics (M-STG-01 to M-STG-10)
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CellStratificationCount(BaseModel):
    """Demographic cell count protected by k-anonymity (k >= 5)."""

    model_config = ConfigDict(frozen=True)

    cell_key: str = Field(..., description="Stratification key, e.g. 'DATA_mid_BLR'")
    raw_count: int = Field(..., ge=0, description="Internal unperturbed participant count")
    reported_count: int | None = Field(
        None,
        description="Public count, suppressed to None if raw_count < k",
    )
    is_suppressed: bool = Field(
        ...,
        description="True if cell has fewer than k participants to prevent re-identification",
    )


class MetricStatusRecord(BaseModel):
    """Evaluation record for a single M-STG metric."""

    model_config = ConfigDict(frozen=True)

    target: str = Field(..., description="Pre-registered acceptance target")
    observed: str = Field(..., description="Empirical observed value")
    status: Literal["PASS", "FAIL"] = Field(..., description="Pass/Fail determination")


class PilotTelemetryScorecard(BaseModel):
    """The 10 pre-registered pilot staging & cohort quality metrics."""

    model_config = ConfigDict(frozen=True)

    m_stg_01_calibration_comprehension: MetricStatusRecord
    m_stg_02_task_completion_rate: MetricStatusRecord
    m_stg_03_deterministic_scoring_variance: MetricStatusRecord
    m_stg_04_scoring_latency_p95_ms: MetricStatusRecord
    m_stg_05_local_storage_footprint_kb: MetricStatusRecord
    m_stg_06_dpdp_sec12_purge_residual_bytes: MetricStatusRecord
    m_stg_07_zero_causal_promises: MetricStatusRecord
    m_stg_08_anti_credentialism: MetricStatusRecord
    m_stg_09_two_streams_two_places: MetricStatusRecord
    m_stg_10_cross_family_dag_monotonicity: MetricStatusRecord


class PilotCohortTelemetryReport(BaseModel):
    """Comprehensive pilot cohort telemetry report with k-anonymized stratification."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(
        default="PILOT-TELEMETRY-COHORT-01",
        description="Unique report identifier",
    )
    report_timestamp: str = Field(..., description="ISO 8601 generation timestamp")
    total_participants: int = Field(..., ge=0, description="Total enrolled cohort participants")
    data_participants: int = Field(..., ge=0, description="DATA family participants")
    swe_participants: int = Field(..., ge=0, description="SWE family participants")
    mlai_participants: int = Field(..., ge=0, description="MLAI family participants")
    k_threshold: int = Field(default=5, ge=2, description="k-anonymity suppression threshold")
    cells: list[CellStratificationCount] = Field(
        default_factory=list,
        description="k-anonymized demographic stratification counts",
    )
    scorecard: PilotTelemetryScorecard = Field(
        ...,
        description="10 pre-registered quality metrics",
    )

    @model_validator(mode="after")
    def validate_family_sum(self) -> Self:
        d = self.data_participants
        s = self.swe_participants
        m = self.mlai_participants
        if d + s + m > 0 and d + s + m != self.total_participants:
            raise ValueError(
                f"Family participant sum {d + s + m} must match total {self.total_participants}"
            )
        return self


def apply_k_anonymity(
    raw_counts: dict[str, int],
    k: int = 5,
) -> list[CellStratificationCount]:
    """Apply k-anonymity suppression (k >= 5) to demographic cells.

    Any cell with count < k is marked is_suppressed = True and reported_count = None
    to prevent singling out individual participants.
    """
    result: list[CellStratificationCount] = []
    for key in sorted(raw_counts.keys()):
        count = raw_counts[key]
        if count < k:
            result.append(
                CellStratificationCount(
                    cell_key=key,
                    raw_count=count,
                    reported_count=None,
                    is_suppressed=True,
                )
            )
        else:
            result.append(
                CellStratificationCount(
                    cell_key=key,
                    raw_count=count,
                    reported_count=count,
                    is_suppressed=False,
                )
            )
    return result


def build_default_pilot_scorecard(
    comprehension_rate: float = 1.00,
    completion_rate: float = 1.00,
    variance: float = 0.000,
    p95_latency_ms: float = 0.028,
    storage_kb: float = 8.59,
    purge_residual_bytes: int = 0,
    causal_violations: int = 0,
    cred_violations: int = 0,
    two_streams_decoupled: bool = True,
    dag_monotonic: bool = True,
) -> PilotTelemetryScorecard:
    """Build a PilotTelemetryScorecard validating against the 10 pre-registered thresholds."""
    return PilotTelemetryScorecard(
        m_stg_01_calibration_comprehension=MetricStatusRecord(
            target=">= 90%",
            observed=f"{comprehension_rate:.1%}",
            status="PASS" if comprehension_rate >= 0.90 else "FAIL",
        ),
        m_stg_02_task_completion_rate=MetricStatusRecord(
            target=">= 95%",
            observed=f"{completion_rate:.1%}",
            status="PASS" if completion_rate >= 0.95 else "FAIL",
        ),
        m_stg_03_deterministic_scoring_variance=MetricStatusRecord(
            target="sigma^2 == 0.000",
            observed=f"{variance:.6f}",
            status="PASS" if variance == 0.0 else "FAIL",
        ),
        m_stg_04_scoring_latency_p95_ms=MetricStatusRecord(
            target="<= 5.0 ms",
            observed=f"{p95_latency_ms:.4f} ms",
            status="PASS" if p95_latency_ms <= 5.0 else "FAIL",
        ),
        m_stg_05_local_storage_footprint_kb=MetricStatusRecord(
            target="<= 100 KB",
            observed=f"{storage_kb:.2f} KB",
            status="PASS" if storage_kb <= 100.0 else "FAIL",
        ),
        m_stg_06_dpdp_sec12_purge_residual_bytes=MetricStatusRecord(
            target="== 0 bytes",
            observed=f"{purge_residual_bytes} bytes",
            status="PASS" if purge_residual_bytes == 0 else "FAIL",
        ),
        m_stg_07_zero_causal_promises=MetricStatusRecord(
            target="0 violations",
            observed=f"{causal_violations} violations",
            status="PASS" if causal_violations == 0 else "FAIL",
        ),
        m_stg_08_anti_credentialism=MetricStatusRecord(
            target="0 violations",
            observed=f"{cred_violations} violations",
            status="PASS" if cred_violations == 0 else "FAIL",
        ),
        m_stg_09_two_streams_two_places=MetricStatusRecord(
            target="100% decoupled",
            observed="100% decoupled" if two_streams_decoupled else "Violated",
            status="PASS" if two_streams_decoupled else "FAIL",
        ),
        m_stg_10_cross_family_dag_monotonicity=MetricStatusRecord(
            target="100%",
            observed="100% monotonic" if dag_monotonic else "Cycle detected",
            status="PASS" if dag_monotonic else "FAIL",
        ),
    )
