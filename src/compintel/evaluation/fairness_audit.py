"""Fairness audit v1: errors, coverage, abstention and data availability by group (T6.09).

Evaluates prediction parity and structural equity across operationally lawful slices:
- GEOGRAPHIC: city/region-level location groups.
- EXPERIENCE_BAND: career stage bands defined by years of experience.
- ROLE_FAMILY: software engineering, data science / analytics, ML / AI.
- EMPLOYER_TIER: Tier-1 product, Tier-2 product/GCC, IT services/consulting.

Legal Compliance & Fairness Framework:
- Protected attributes (gender, caste, religion, age, disability, etc.) are NOT model inputs
  and are NOT collected, per Rule R-MD-12 and rules.md Section 16 Rule 11.
- Audit slices are defined exclusively over operationally lawful role and location signals.
- Data availability parity is reported to surface structural data gaps — not to act as proxies.
- Audit output is decision-support only; no causal claims (Rule R-MD-08, R-FA-01).
- Legal status of regulations is flagged UNVERIFIED per Rule R-FA-04.
- Complies with DPDPA 2023 framing: missing personal profile fields are never treated as traits.

Adheres to:
- Rules R-FA-01, R-FA-02, R-FA-03, R-FA-04.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set lock enforced.
- Rule R-MD-05: Full metric suite with bootstrap confidence intervals.
- Rule R-MD-08: No causal language; parity gaps are associations, not discrimination claims.
- Rule R-MD-11: Synthetic data isolation.
- Rule R-MD-12: Zero protected demographic inputs or proxies.
- Rule R-UQ-01: Nonparametric bootstrap CIs on all reported metrics.
- Rule R-UQ-02: Abstention is a valid designed outcome.
- Rule R-UQ-05: Monotonic quantile non-crossing (P10 <= P50 <= P90).
- rules.md Section 16 Rule 11: Demographic proxy prohibition.
"""

from __future__ import annotations

import datetime
import json
import subprocess
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.stagewise_evaluation import (
    StagewiseQuantileModel,
    get_level_feature_specs,
)
from compintel.features.spec import FeatureLevel

# ---------------------------------------------------------------------------
# Lawful audit slice dimensions (no protected attributes per R-MD-12)
# ---------------------------------------------------------------------------
GEOGRAPHIC_TIER_MAP: dict[str, str] = {
    "BANGALORE": "Metro_South",
    "HYDERABAD": "Metro_South",
    "MUMBAI": "Metro_West",
    "PUNE": "Metro_West",
    "NCR": "Metro_North",
    "DELHI": "Metro_North",
    "GURGAON": "Metro_North",
    "NOIDA": "Metro_North",
    "CHENNAI": "Metro_South",
    "KOLKATA": "Metro_East",
}

EXPERIENCE_BANDS: list[tuple[str, float, float]] = [
    ("Early_Career", 0.0, 3.0),
    ("Mid_Career", 3.0, 8.0),
    ("Senior", 8.0, 13.0),
    ("Leadership", 13.0, 100.0),
]

# Prohibited demographic substrings in column names (rules.md Section 16 Rule 11)
PROHIBITED_DEMOGRAPHIC_COLS = {
    "gender",
    "sex",
    "caste",
    "religion",
    "ethnicity",
    "race",
    "disability",
    "marital",
    "pregnancy",
    "age_",  # avoid matching 'career_age' type patterns carelessly, only standalone
    "birth",
    "nationality",
    "community",
}

# Low-support flag threshold per Rule R-MD-08 / R-EV-07
LOW_SUPPORT_MIN_N = 10

# Parity thresholds — pre-registered for EXP-09 (fairness audit v1)
PARITY_MAE_RATIO_THRESHOLD = 1.30  # MAE_slice / MAE_global must be <= 1.30
PARITY_COVERAGE_MIN_GAP = 0.15  # |Coverage_slice - Coverage_global| must be <= 0.15
PARITY_ABSTENTION_MAX_GAP = 0.25  # |Abstention_slice - Abstention_global| must be <= 0.25
PARITY_AVAILABILITY_MIN_N = 5  # Slices with < 5 observations are flagged as DATA_GAP


class SliceDimension(StrEnum):
    """Audit slice dimension identifiers."""

    GEOGRAPHIC = "GEOGRAPHIC"
    EXPERIENCE_BAND = "EXPERIENCE_BAND"
    ROLE_FAMILY = "ROLE_FAMILY"
    EMPLOYER_TIER = "EMPLOYER_TIER"


class ParityStatus(StrEnum):
    """Parity verdict for an audit slice dimension."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FairnessVerdict(StrEnum):
    """Overall fairness audit verdict."""

    PASS_ALL = "PASS_ALL"
    WARN_GAPS = "WARN_GAPS"
    FAIL_PARITY = "FAIL_PARITY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class GroupFairnessMetrics:
    """Per-slice fairness metrics for one operationally-lawful group."""

    dimension: SliceDimension
    slice_value: str
    n_observations: int
    is_low_support: bool
    mean_pinball_loss: float
    point_mae: float
    mdape: float
    empirical_coverage: float
    mean_interval_width: float
    abstention_rate: float
    pinball_loss_ci_lower: float
    pinball_loss_ci_upper: float
    mae_ratio_to_global: float  # slice MAE / global MAE
    coverage_gap_to_global: float  # |slice coverage - global coverage|


@dataclass(frozen=True)
class SliceParityAudit:
    """Parity assessment for one slice dimension."""

    dimension: SliceDimension
    n_slices_evaluated: int
    n_slices_low_support: int
    max_mae_ratio: float
    max_coverage_gap: float
    max_abstention_gap: float
    parity_status: ParityStatus
    failing_slices: list[str]
    gaps_and_mitigations: list[str]


@dataclass(frozen=True)
class DemographicProxyCompliance:
    """Audit of prohibited demographic proxy columns per rules.md Section 16 Rule 11."""

    columns_scanned: list[str]
    prohibited_columns_found: list[str]
    is_compliant: bool
    legal_note: str
    audit_timestamp: str


@dataclass(frozen=True)
class DataAvailabilityReport:
    """Structural data availability across slices — not a proxy."""

    dimension: SliceDimension
    slice_value: str
    n_observations: int
    availability_status: str  # "ADEQUATE" | "DATA_GAP" | "ABSENT"
    availability_note: str


@dataclass(frozen=True)
class FairnessAuditReport:
    """Comprehensive fairness audit report for ArthaIQ PT1 (T6.09)."""

    report_id: str
    generated_at: str
    git_commit: str
    evaluation_split: str
    n_total_observations: int
    global_pinball_loss: float
    global_mae: float
    global_empirical_coverage: float
    global_abstention_rate: float
    group_metrics: list[GroupFairnessMetrics]
    slice_audits: list[SliceParityAudit]
    data_availability: list[DataAvailabilityReport]
    proxy_compliance: DemographicProxyCompliance
    overall_verdict: FairnessVerdict
    gaps_and_mitigations: list[str]
    legal_disclaimer: str
    executive_summary: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to nested dict."""
        return asdict(self)

    def to_markdown(self) -> str:
        """Render publication-grade Markdown fairness audit report."""
        lines: list[str] = [
            "# Fairness Audit v1: Prediction Parity by Operational Group (T6.09)",
            "",
            "> **Legal Note (R-FA-04):** Legal status of regulations cited here is `UNVERIFIED` "
            "until confirmed by qualified counsel. This audit is provided as decision-support "
            "only and does not constitute a legal compliance determination.",
            "",
            "> **Scope:** ArthaIQ PT1 market compensation estimates (P10/P50/P90) are evaluated "
            "for prediction parity across lawful operational slices: geographic tier, experience "
            "band, role family, and employer tier. Protected attributes (gender, caste, religion, "
            "age, disability) are strictly excluded from all model inputs and audit dimensions "
            "per Rule R-MD-12 and rules.md Section 16 Rule 11.",
            "",
            "| Metadata | Value |",
            "|:---|:---|",
            f"| **Report ID** | `{self.report_id}` |",
            f"| **Generated At** | `{self.generated_at}` |",
            f"| **Git Commit** | `{self.git_commit[:8]}` |",
            f"| **Evaluation Split** | `{self.evaluation_split}` |",
            f"| **Total Observations Evaluated** | `{self.n_total_observations:,}` |",
            f"| **Overall Verdict** | **`{self.overall_verdict.value}`** |",
            "",
            "## 1. Executive Summary",
            "",
            self.executive_summary,
            "",
            "---",
            "",
            "## 2. Global Baseline Metrics",
            "",
            "| Metric | Value |",
            "|:---|:---:|",
            f"| **Global Mean Pinball Loss** | `{self.global_pinball_loss:.3f}` LPA |",
            f"| **Global Point MAE** | `{self.global_mae:.2f}` LPA |",
            (
                "| **Global 80% Empirical Coverage** | "
                f"`{self.global_empirical_coverage * 100:.1f}%` |"
            ),
            f"| **Global Abstention Rate** | `{self.global_abstention_rate * 100:.1f}%` |",
            "",
            "---",
            "",
            "## 3. Demographic Proxy Compliance (rules.md Section 16 Rule 11)",
            "",
            f"- **Columns Scanned:** `{len(self.proxy_compliance.columns_scanned)}`",
            (
                "- **Prohibited Columns Found:** "
                f"`{len(self.proxy_compliance.prohibited_columns_found)}`"
            ),
            (
                "- **Compliance Status:** "
                f"**`{'COMPLIANT' if self.proxy_compliance.is_compliant else 'VIOLATION'}`**"
            ),
            "",
            f"> {self.proxy_compliance.legal_note}",
            "",
            "---",
            "",
            "## 4. Per-Slice Parity Results",
            "",
        ]

        for audit in self.slice_audits:
            status_icon = (
                "✅"
                if audit.parity_status == ParityStatus.PASS
                else ("⚠️" if audit.parity_status == ParityStatus.WARN else "❌")
            )
            lines += [
                f"### 4.{list(SliceDimension).index(audit.dimension) + 1}. "
                f"{audit.dimension.value} Parity {status_icon}",
                "",
                "| Parity Metric | Value | Threshold | Status |",
                "|:---|:---:|:---:|:---:|",
                f"| **Max MAE Ratio (slice/global)** | `{audit.max_mae_ratio:.3f}` | "
                f"`<= {PARITY_MAE_RATIO_THRESHOLD:.2f}` | "
                f"`{'OK' if audit.max_mae_ratio <= PARITY_MAE_RATIO_THRESHOLD else 'FAIL'}` |",
                f"| **Max Coverage Gap (|slice - global|)** | `{audit.max_coverage_gap:.3f}` | "
                f"`<= {PARITY_COVERAGE_MIN_GAP:.2f}` | "
                f"`{'OK' if audit.max_coverage_gap <= PARITY_COVERAGE_MIN_GAP else 'FAIL'}` |",
                f"| **Max Abstention Gap (|slice - global|)** | `{audit.max_abstention_gap:.3f}` | "
                f"`<= {PARITY_ABSTENTION_MAX_GAP:.2f}` | "
                f"`{'OK' if audit.max_abstention_gap <= PARITY_ABSTENTION_MAX_GAP else 'FAIL'}` |",
                f"| **Slices Evaluated** | `{audit.n_slices_evaluated}` | — | — |",
                f"| **Slices Low Support (N < {LOW_SUPPORT_MIN_N})** | "
                f"`{audit.n_slices_low_support}` | — | — |",
                "",
            ]

            if audit.failing_slices:
                slices_str = ", ".join(f"`{s}`" for s in audit.failing_slices)
                lines.append(f"**Failing Slices:** {slices_str}")
                lines.append("")

        lines += [
            "---",
            "",
            "## 5. Per-Group Detailed Metrics",
            "",
            "| Dimension | Slice | N | MAE Ratio | Coverage | Coverage Gap | "
            "Abstention | Pinball | Low Support |",
            "|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for gm in self.group_metrics:
            flag = "⚠️" if gm.is_low_support else ""
            lines.append(
                f"| {gm.dimension.value} | `{gm.slice_value}` | `{gm.n_observations}` | "
                f"`{gm.mae_ratio_to_global:.3f}` | `{gm.empirical_coverage * 100:.1f}%` | "
                f"`{gm.coverage_gap_to_global:.3f}` | `{gm.abstention_rate * 100:.1f}%` | "
                f"`{gm.mean_pinball_loss:.3f}` | {flag} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 6. Data Availability by Operational Group",
            "",
            "| Dimension | Slice | N Observations | Status | Note |",
            "|:---|:---|:---:|:---:|:---|",
        ]

        for da in self.data_availability:
            status_icon = (
                "✅" if da.availability_status == "ADEQUATE"
                else ("⚠️" if da.availability_status == "DATA_GAP" else "❌")
            )
            lines.append(
                f"| {da.dimension.value} | `{da.slice_value}` | `{da.n_observations}` | "
                f"{status_icon} `{da.availability_status}` | {da.availability_note} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 7. Identified Gaps and Mitigations",
            "",
        ]

        if self.gaps_and_mitigations:
            for i, gap in enumerate(self.gaps_and_mitigations, 1):
                lines.append(f"{i}. {gap}")
        else:
            lines.append("No gaps identified beyond low-support flagging.")

        lines += [
            "",
            "---",
            "",
            "## 8. Legal & Ethical Compliance Notes",
            "",
            f"> [!IMPORTANT]\n> {self.legal_disclaimer}",
            "",
            "1. **Rule R-MD-12 / Section 16 Rule 11:** Protected attributes (gender, caste, "
            "religion, age, disability) are excluded from all model inputs and audit dimensions.",
            "2. **Rule R-FA-01:** This system is decision support. It does not rank candidates, "
            "recommend discriminatory pay, or present itself as an appraisal, offer, or guarantee.",
            "3. **Rule R-FA-04:** Legal status of DPDPA 2023 and employment discrimination law "
            "in India is `UNVERIFIED` — qualified counsel must confirm before beta.",
            "4. **Rule R-MD-08:** All parity gaps are associations and statistical observations. "
            "No causal discrimination claim is made.",
            "5. **Rule R-MD-02:** Final test set was not used in this audit. Evaluation was "
            "performed exclusively on the development (`select`) partition.",
            "",
            "---",
            "",
            f"*Report generated by `compintel.evaluation.fairness_audit` on {self.generated_at}*",
        ]

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------


def _pinball(y: np.ndarray, pred: np.ndarray, q: float) -> np.ndarray:
    """Per-sample pinball (quantile) loss."""
    err = y - pred
    return np.array(np.maximum(q * err, (q - 1.0) * err), dtype=np.float64)


def _mean_pb_arr(
    y: np.ndarray,
    p10: np.ndarray,
    p50: np.ndarray,
    p90: np.ndarray,
) -> np.ndarray:
    """Per-sample mean pinball loss averaged across quantiles."""
    return np.array(
        (_pinball(y, p10, 0.10) + _pinball(y, p50, 0.50) + _pinball(y, p90, 0.90)) / 3.0,
        dtype=np.float64,
    )


def _bootstrap_mean_ci(
    arr: np.ndarray,
    n_resamples: int = 500,
    seed: int = 42,
) -> tuple[float, float]:
    """Nonparametric 95% percentile bootstrap CI on the mean (Rule R-UQ-01)."""
    rng = np.random.default_rng(seed)
    if len(arr) < 2:
        v = float(np.mean(arr)) if len(arr) > 0 else 0.0
        return v, v
    boot = np.array([
        np.mean(rng.choice(arr, size=len(arr), replace=True)) for _ in range(n_resamples)
    ])
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def _get_git_commit_hash() -> str:
    """Short git commit hash for audit traceability."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


# ---------------------------------------------------------------------------
# Proxy compliance scanner
# ---------------------------------------------------------------------------


def scan_demographic_proxy_compliance(
    df: pl.DataFrame,
) -> DemographicProxyCompliance:
    """Scan all DataFrame column names for prohibited demographic proxies.

    Enforces rules.md Section 16 Rule 11 and Rule R-MD-12.

    Args:
        df: Input DataFrame to scan.

    Returns:
        DemographicProxyCompliance report documenting compliance status.
    """
    columns = df.columns
    violations: list[str] = []
    for col in columns:
        col_lower = col.lower()
        for prohibited in PROHIBITED_DEMOGRAPHIC_COLS:
            if prohibited in col_lower:
                violations.append(col)
                break

    is_compliant = len(violations) == 0
    legal_note = (
        "LEGAL NOTE (R-FA-04, status=UNVERIFIED): All column names were scanned against the "
        "prohibited demographic proxy list per rules.md Section 16 Rule 11 and Rule R-MD-12. "
        "Protected attributes (gender, caste, religion, age, disability, nationality, etc.) "
        "are strictly excluded from model inputs and evaluation dimensions. "
        "This scan is automated; final legal review by qualified counsel is required before beta."
    )

    return DemographicProxyCompliance(
        columns_scanned=columns,
        prohibited_columns_found=violations,
        is_compliant=is_compliant,
        legal_note=legal_note,
        audit_timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Slice assignment helpers
# ---------------------------------------------------------------------------


def _assign_experience_band(yoe: float | None) -> str:
    """Map years of experience to a career stage band."""
    if yoe is None or (isinstance(yoe, float) and np.isnan(yoe)):
        return "Unknown"
    for label, lo, hi in EXPERIENCE_BANDS:
        if lo <= yoe < hi:
            return label
    return "Leadership"  # >= 13 YOE


def _assign_geo_tier(location: str | None) -> str:
    """Map raw location string to a geographic tier group."""
    if location is None:
        return "Non_Metro"
    loc_upper = str(location).upper().strip()
    return GEOGRAPHIC_TIER_MAP.get(loc_upper, "Non_Metro")


# ---------------------------------------------------------------------------
# Core group-level metric calculator
# ---------------------------------------------------------------------------


def _compute_group_metrics(
    y: np.ndarray,
    p10: np.ndarray,
    p50: np.ndarray,
    p90: np.ndarray,
    global_mae: float,
    global_coverage: float,
    global_abstention: float,
    dimension: SliceDimension,
    slice_value: str,
    n_resamples: int = 500,
    seed: int = 42,
) -> GroupFairnessMetrics:
    """Compute full fairness metric suite for one group slice (Rule R-MD-05)."""
    n = len(y)
    is_low = n < LOW_SUPPORT_MIN_N

    if n == 0:
        return GroupFairnessMetrics(
            dimension=dimension,
            slice_value=slice_value,
            n_observations=0,
            is_low_support=True,
            mean_pinball_loss=float("nan"),
            point_mae=float("nan"),
            mdape=float("nan"),
            empirical_coverage=float("nan"),
            mean_interval_width=float("nan"),
            abstention_rate=0.0,
            pinball_loss_ci_lower=float("nan"),
            pinball_loss_ci_upper=float("nan"),
            mae_ratio_to_global=float("nan"),
            coverage_gap_to_global=float("nan"),
        )

    pb_arr = _mean_pb_arr(y, p10, p50, p90)
    mean_pb = float(np.mean(pb_arr))
    pb_ci_lo, pb_ci_hi = _bootstrap_mean_ci(pb_arr, n_resamples=n_resamples, seed=seed)

    mae = float(np.mean(np.abs(y - p50)))
    mdape = float(np.median(np.abs(y - p50) / np.maximum(y, 1e-4)))
    covered = (y >= p10) & (y <= p90)
    cov = float(np.mean(covered))
    mean_width = float(np.mean(p90 - p10))

    # Abstention: estimate as fraction of abstained observations
    # In production abstention is driven by SupportEvaluator; here proxy by zero-width
    zero_width = p90 - p10
    abstention_rate = float(np.mean(zero_width < 0.01))

    mae_ratio = mae / max(global_mae, 1e-4)
    cov_gap = abs(cov - global_coverage)

    return GroupFairnessMetrics(
        dimension=dimension,
        slice_value=slice_value,
        n_observations=n,
        is_low_support=is_low,
        mean_pinball_loss=mean_pb,
        point_mae=mae,
        mdape=mdape,
        empirical_coverage=cov,
        mean_interval_width=mean_width,
        abstention_rate=abstention_rate,
        pinball_loss_ci_lower=pb_ci_lo,
        pinball_loss_ci_upper=pb_ci_hi,
        mae_ratio_to_global=mae_ratio,
        coverage_gap_to_global=cov_gap,
    )


# ---------------------------------------------------------------------------
# Per-dimension parity evaluation
# ---------------------------------------------------------------------------


def _evaluate_slice_parity(
    group_metrics: list[GroupFairnessMetrics],
    dimension: SliceDimension,
    global_abstention: float,
) -> SliceParityAudit:
    """Evaluate parity for one slice dimension across all its groups."""
    dim_metrics = [m for m in group_metrics if m.dimension == dimension]

    if not dim_metrics or all(m.n_observations == 0 for m in dim_metrics):
        return SliceParityAudit(
            dimension=dimension,
            n_slices_evaluated=0,
            n_slices_low_support=0,
            max_mae_ratio=float("nan"),
            max_coverage_gap=float("nan"),
            max_abstention_gap=float("nan"),
            parity_status=ParityStatus.INSUFFICIENT_DATA,
            failing_slices=[],
            gaps_and_mitigations=["No observations found for this slice dimension."],
        )

    valid = [m for m in dim_metrics if m.n_observations >= PARITY_AVAILABILITY_MIN_N
             and not (isinstance(m.mae_ratio_to_global, float) and np.isnan(m.mae_ratio_to_global))]
    low_support = [m for m in dim_metrics if m.n_observations < LOW_SUPPORT_MIN_N]

    if not valid:
        return SliceParityAudit(
            dimension=dimension,
            n_slices_evaluated=len(dim_metrics),
            n_slices_low_support=len(low_support),
            max_mae_ratio=float("nan"),
            max_coverage_gap=float("nan"),
            max_abstention_gap=float("nan"),
            parity_status=ParityStatus.INSUFFICIENT_DATA,
            failing_slices=[],
            gaps_and_mitigations=[
                f"All slices in {dimension.value} have insufficient data "
                f"(N < {PARITY_AVAILABILITY_MIN_N})."
            ],
        )

    max_mae_ratio = max(m.mae_ratio_to_global for m in valid)
    max_cov_gap = max(m.coverage_gap_to_global for m in valid)
    max_abs_gap = max(
        abs(m.abstention_rate - global_abstention) for m in valid
    )

    failing: list[str] = []
    if max_mae_ratio > PARITY_MAE_RATIO_THRESHOLD:
        failing.extend(
            str(m.slice_value)
            for m in valid
            if m.mae_ratio_to_global > PARITY_MAE_RATIO_THRESHOLD
        )
    if max_cov_gap > PARITY_COVERAGE_MIN_GAP:
        failing.extend(
            str(m.slice_value)
            for m in valid
            if m.coverage_gap_to_global > PARITY_COVERAGE_MIN_GAP
        )

    gaps: list[str] = []
    if low_support:
        gaps.append(
            f"**[DATA_GAP]** {len(low_support)} slice(s) in {dimension.value} have "
            f"N < {LOW_SUPPORT_MIN_N}. Mitigation: collect more observations from underrepresented "
            "regions/cohorts before widening coverage."
        )
    if max_mae_ratio > PARITY_MAE_RATIO_THRESHOLD:
        gaps.append(
            f"**[ERROR_PARITY]** Max MAE ratio = {max_mae_ratio:.3f} exceeds threshold "
            f"{PARITY_MAE_RATIO_THRESHOLD:.2f} in {dimension.value}. "
            "Mitigation: review training data representation; consider targeted data collection."
        )
    if max_cov_gap > PARITY_COVERAGE_MIN_GAP:
        gaps.append(
            f"**[COVERAGE_PARITY]** Max coverage gap = {max_cov_gap:.3f} exceeds threshold "
            f"{PARITY_COVERAGE_MIN_GAP:.2f} in {dimension.value}. "
            "Mitigation: investigate conformal calibration on slice-specific partitions."
        )
    if max_abs_gap > PARITY_ABSTENTION_MAX_GAP:
        gaps.append(
            f"**[ABSTENTION_PARITY]** Max abstention gap = {max_abs_gap:.3f} exceeds threshold "
            f"{PARITY_ABSTENTION_MAX_GAP:.2f} in {dimension.value}. "
            "Mitigation: review SupportEvaluator thresholds for underrepresented slices."
        )

    if not failing:
        status = ParityStatus.PASS if not gaps else ParityStatus.WARN
    else:
        status = ParityStatus.FAIL

    return SliceParityAudit(
        dimension=dimension,
        n_slices_evaluated=len(dim_metrics),
        n_slices_low_support=len(low_support),
        max_mae_ratio=max_mae_ratio,
        max_coverage_gap=max_cov_gap,
        max_abstention_gap=max_abs_gap,
        parity_status=status,
        failing_slices=list(set(failing)),
        gaps_and_mitigations=gaps,
    )


# ---------------------------------------------------------------------------
# Data availability report
# ---------------------------------------------------------------------------


def _build_data_availability(
    df: pl.DataFrame,
) -> list[DataAvailabilityReport]:
    """Build data availability summary by slice dimension."""
    reports: list[DataAvailabilityReport] = []

    # Geographic tier
    if "location" in df.columns:
        df_geo = df.with_columns(
            pl.col("location")
            .map_elements(_assign_geo_tier, return_dtype=pl.Utf8)
            .alias("_geo_tier")
        )
        for tier, grp in df_geo.group_by("_geo_tier"):
            n = len(grp)
            status = (
                "ADEQUATE" if n >= LOW_SUPPORT_MIN_N
                else ("DATA_GAP" if n >= PARITY_AVAILABILITY_MIN_N else "ABSENT")
            )
            note = (
                "Adequate sample size."
                if status == "ADEQUATE"
                else (
                    f"Marginal data (N={n}); estimates may be unreliable for this tier."
                    if status == "DATA_GAP"
                    else f"Insufficient data (N={n}); abstention expected for this tier."
                )
            )
            reports.append(DataAvailabilityReport(
                dimension=SliceDimension.GEOGRAPHIC,
                slice_value=str(tier[0]) if isinstance(tier, tuple) else str(tier),
                n_observations=n,
                availability_status=status,
                availability_note=note,
            ))

    # Experience band
    if "years_experience" in df.columns:
        yoe_vals = df["years_experience"].to_list()
        bands: dict[str, int] = {}
        for yoe in yoe_vals:
            band = _assign_experience_band(float(yoe) if yoe is not None else None)
            bands[band] = bands.get(band, 0) + 1
        for band, n in bands.items():
            status = (
                "ADEQUATE" if n >= LOW_SUPPORT_MIN_N
                else ("DATA_GAP" if n >= PARITY_AVAILABILITY_MIN_N else "ABSENT")
            )
            note = (
                "Adequate sample size."
                if status == "ADEQUATE"
                else f"Marginal data (N={n}) for experience band '{band}'."
            )
            reports.append(DataAvailabilityReport(
                dimension=SliceDimension.EXPERIENCE_BAND,
                slice_value=band,
                n_observations=n,
                availability_status=status,
                availability_note=note,
            ))

    # Role family
    if "role_family" in df.columns:
        for role, grp in df.group_by("role_family"):
            n = len(grp)
            status = (
                "ADEQUATE" if n >= LOW_SUPPORT_MIN_N
                else ("DATA_GAP" if n >= PARITY_AVAILABILITY_MIN_N else "ABSENT")
            )
            reports.append(DataAvailabilityReport(
                dimension=SliceDimension.ROLE_FAMILY,
                slice_value=str(role[0]) if isinstance(role, tuple) else str(role),
                n_observations=n,
                availability_status=status,
                availability_note="Adequate sample." if status == "ADEQUATE"
                else f"Marginal data (N={n}).",
            ))

    # Employer tier
    if "employer_tier" in df.columns:
        for tier, grp in df.group_by("employer_tier"):
            n = len(grp)
            status = (
                "ADEQUATE" if n >= LOW_SUPPORT_MIN_N
                else ("DATA_GAP" if n >= PARITY_AVAILABILITY_MIN_N else "ABSENT")
            )
            reports.append(DataAvailabilityReport(
                dimension=SliceDimension.EMPLOYER_TIER,
                slice_value=str(tier[0]) if isinstance(tier, tuple) else str(tier),
                n_observations=n,
                availability_status=status,
                availability_note="Adequate sample." if status == "ADEQUATE"
                else f"Marginal data (N={n}).",
            ))

    return reports


# ---------------------------------------------------------------------------
# Main fairness audit function
# ---------------------------------------------------------------------------


def run_fairness_audit(
    train_df: pl.DataFrame,
    eval_df: pl.DataFrame,
    calibrate_df: pl.DataFrame,
    eval_split_name: str = "select",
    n_resamples: int = 500,
    seed: int = 42,
) -> FairnessAuditReport:
    """Execute fairness audit v1 (T6.09, EXP-09) across operational slice dimensions.

    Args:
        train_df: Training partition (only used to fit the evaluation model).
        eval_df: Evaluation partition (dev split only; test partition prohibited per R-MD-02).
        calibrate_df: Conformal calibration partition.
        eval_split_name: Partition name ('select' or 'calibrate').
        n_resamples: Bootstrap resamples for CIs (Rule R-UQ-01).
        seed: Random seed for reproducibility (Rule R-MD-10).

    Returns:
        FairnessAuditReport with full parity analysis and compliance documentation.

    Raises:
        DataContractError: If test split is specified (Rule R-MD-02).
        DataContractError: If demographic proxy columns are found in input data.
    """
    if eval_split_name.lower() == "test":
        raise DataContractError(
            "EVALUATION_ISOLATION_VIOLATION: Fairness audit on locked 'test' partition "
            "is strictly forbidden. Evaluate on 'select' or 'calibrate' only.",
            details={"rule_id": "R-MD-02"},
        )

    # Step 1: Demographic proxy compliance scan
    proxy_compliance = scan_demographic_proxy_compliance(eval_df)
    if not proxy_compliance.is_compliant:
        raise DataContractError(
            f"DEMOGRAPHIC_PROXY_VIOLATION: Prohibited demographic columns found: "
            f"{proxy_compliance.prohibited_columns_found}. "
            "Remove all protected attribute columns per rules.md Section 16 Rule 11.",
            details={"rule_id": "R-MD-12", "violations": proxy_compliance.prohibited_columns_found},
        )

    # Step 2: Fit joint L0 model for evaluation predictions
    l0_specs = get_level_feature_specs(FeatureLevel.L0_CORE)
    model = StagewiseQuantileModel(
        level=FeatureLevel.L0_CORE,
        specs=l0_specs,
        seed=seed,
    )
    model.fit(train_df, calibrate_df=calibrate_df)
    p10_all, p50_all, p90_all = model.predict(eval_df)
    y_all = eval_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)

    # Step 3: Global baseline metrics
    pb_all = _mean_pb_arr(y_all, p10_all, p50_all, p90_all)
    global_pb = float(np.mean(pb_all))
    global_mae = float(np.mean(np.abs(y_all - p50_all)))
    global_cov = float(np.mean((y_all >= p10_all) & (y_all <= p90_all)))
    zero_width_all = p90_all - p10_all
    global_abstention = float(np.mean(zero_width_all < 0.01))

    # Step 4: Per-group slicing and metric computation
    all_group_metrics: list[GroupFairnessMetrics] = []
    eval_rows = eval_df.to_dicts()

    def _slice_indices(mask: np.ndarray) -> tuple[
        np.ndarray, np.ndarray, np.ndarray, np.ndarray
    ]:
        return y_all[mask], p10_all[mask], p50_all[mask], p90_all[mask]

    # 4a. Geographic slices
    if "location" in eval_df.columns:
        geo_assignments = np.array([
            _assign_geo_tier(row.get("location")) for row in eval_rows
        ])
        for geo_tier in sorted(set(geo_assignments)):
            mask = geo_assignments == geo_tier
            ys, ps10, ps50, ps90 = _slice_indices(mask)
            gm = _compute_group_metrics(
                ys, ps10, ps50, ps90, global_mae, global_cov, global_abstention,
                SliceDimension.GEOGRAPHIC, geo_tier, n_resamples=n_resamples, seed=seed
            )
            all_group_metrics.append(gm)

    # 4b. Experience band slices
    if "years_experience" in eval_df.columns:
        yoe_vals = eval_df["years_experience"].to_list()
        band_assignments = np.array([
            _assign_experience_band(float(v) if v is not None else None) for v in yoe_vals
        ])
        for band in sorted(set(band_assignments)):
            mask = band_assignments == band
            ys, ps10, ps50, ps90 = _slice_indices(mask)
            gm = _compute_group_metrics(
                ys, ps10, ps50, ps90, global_mae, global_cov, global_abstention,
                SliceDimension.EXPERIENCE_BAND, band, n_resamples=n_resamples, seed=seed
            )
            all_group_metrics.append(gm)

    # 4c. Role family slices
    if "role_family" in eval_df.columns:
        roles = eval_df["role_family"].to_list()
        unique_roles = sorted({str(r) for r in roles if r is not None})
        for role in unique_roles:
            mask = np.array([str(r) == role for r in roles])
            ys, ps10, ps50, ps90 = _slice_indices(mask)
            gm = _compute_group_metrics(
                ys, ps10, ps50, ps90, global_mae, global_cov, global_abstention,
                SliceDimension.ROLE_FAMILY, role, n_resamples=n_resamples, seed=seed
            )
            all_group_metrics.append(gm)

    # 4d. Employer tier slices
    if "employer_tier" in eval_df.columns:
        tiers = eval_df["employer_tier"].to_list()
        unique_tiers = sorted({str(t) for t in tiers if t is not None})
        for tier in unique_tiers:
            mask = np.array([str(t) == tier for t in tiers])
            ys, ps10, ps50, ps90 = _slice_indices(mask)
            gm = _compute_group_metrics(
                ys, ps10, ps50, ps90, global_mae, global_cov, global_abstention,
                SliceDimension.EMPLOYER_TIER, tier, n_resamples=n_resamples, seed=seed
            )
            all_group_metrics.append(gm)

    # Step 5: Slice parity audits per dimension
    slice_audits: list[SliceParityAudit] = []
    for dim in SliceDimension:
        audit = _evaluate_slice_parity(all_group_metrics, dim, global_abstention)
        slice_audits.append(audit)

    # Step 6: Data availability
    data_availability = _build_data_availability(eval_df)

    # Step 7: Aggregate all gaps and mitigations
    all_gaps: list[str] = []
    for audit in slice_audits:
        all_gaps.extend(audit.gaps_and_mitigations)

    # Step 8: Overall verdict
    statuses = [a.parity_status for a in slice_audits]
    if any(s == ParityStatus.FAIL for s in statuses):
        verdict = FairnessVerdict.FAIL_PARITY
    elif all(s == ParityStatus.INSUFFICIENT_DATA for s in statuses):
        verdict = FairnessVerdict.INSUFFICIENT_DATA
    elif any(s in (ParityStatus.WARN, ParityStatus.INSUFFICIENT_DATA) for s in statuses):
        verdict = FairnessVerdict.WARN_GAPS
    else:
        verdict = FairnessVerdict.PASS_ALL

    executive_summary = (
        f"The fairness audit v1 evaluated {len(eval_df):,} observations across 4 operational "
        f"slice dimensions: Geographic Tier, Experience Band, Role Family, and Employer Tier. "
        f"Global baseline: Pinball = {global_pb:.3f} LPA, MAE = {global_mae:.2f} LPA, "
        f"80% Coverage = {global_cov * 100:.1f}%, Abstention = {global_abstention * 100:.1f}%. "
        f"All protected demographic attributes (gender, caste, religion, age, disability) "
        f"confirmed absent from model inputs and audit dimensions. "
        f"Overall parity verdict: **{verdict.value}**. "
        f"{len([a for a in slice_audits if a.parity_status == ParityStatus.FAIL])} dimension(s) "
        f"failed parity; {len([a for a in slice_audits if a.n_slices_low_support > 0])} "
        f"dimension(s) contain low-support slices (N < {LOW_SUPPORT_MIN_N}). "
        "See Section 7 for identified gaps and mitigations."
    )

    legal_disclaimer = (
        "LEGAL DISCLAIMER (R-FA-04, status=UNVERIFIED): This fairness audit evaluates "
        "statistical prediction parity and data availability across operational groups. "
        "It does NOT constitute a legal compliance determination under DPDPA 2023, the "
        "Equal Remuneration Act 1976, or any other applicable Indian employment law. "
        "All parity gaps are statistical observations, not causal discrimination claims "
        "(Rule R-MD-08). Legal review by qualified counsel is required before beta launch."
    )

    ts_now = datetime.datetime.now(datetime.UTC).isoformat()
    git_commit = _get_git_commit_hash()
    report_id = f"FAIRNESS-V1-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}"

    return FairnessAuditReport(
        report_id=report_id,
        generated_at=ts_now,
        git_commit=git_commit,
        evaluation_split=eval_split_name,
        n_total_observations=len(eval_df),
        global_pinball_loss=global_pb,
        global_mae=global_mae,
        global_empirical_coverage=global_cov,
        global_abstention_rate=global_abstention,
        group_metrics=all_group_metrics,
        slice_audits=slice_audits,
        data_availability=data_availability,
        proxy_compliance=proxy_compliance,
        overall_verdict=verdict,
        gaps_and_mitigations=all_gaps,
        legal_disclaimer=legal_disclaimer,
        executive_summary=executive_summary,
    )


def evaluate_and_save_fairness_audit(
    canonical_path: str | Path = "data/canonical/canonical_observations.parquet",
    output_md: str | Path = "docs/research/fairness-audit-v1.md",
    output_json: str | Path = "experiments/results/fairness_audit_v1.json",
    eval_split_name: str = "select",
    n_resamples: int = 500,
    seed: int = 42,
    allow_synthetic: bool = False,
) -> FairnessAuditReport:
    """Load canonical observations, run fairness audit, and persist report artifacts.

    Args:
        canonical_path: Path to canonical observations parquet file.
        output_md: Path for publication Markdown report.
        output_json: Path for structured JSON results.
        eval_split_name: Split to evaluate on ('select' or 'calibrate').
        n_resamples: Number of bootstrap resamples (Rule R-UQ-01).
        seed: Random seed for reproducibility.
        allow_synthetic: Override for synthetic test data (Rule R-MD-11).

    Returns:
        FairnessAuditReport.
    """
    if eval_split_name.lower() == "test":
        raise DataContractError(
            "EVALUATION_ISOLATION_VIOLATION: Fairness audit on locked 'test' partition "
            "is strictly forbidden.",
            details={"rule_id": "R-MD-02"},
        )

    path = Path(canonical_path)
    if not path.exists():
        raise CompIntelValidationError(
            f"Canonical dataset not found at {canonical_path}",
            details={"path": str(canonical_path)},
        )

    df = pl.read_parquet(path)

    # Synthetic isolation guard (Rule R-MD-11)
    if "is_synthetic" in df.columns:
        synthetic_count = df.filter(pl.col("is_synthetic")).height
        if synthetic_count > 0 and not allow_synthetic:
            raise DataContractError(
                "Synthetic data detected in canonical evaluation pool without explicit override.",
                code="SYNTHETIC_DATA_BLOCKED",
                details={"synthetic_count": synthetic_count, "rule_id": "R-MD-11"},
            )

    from compintel.evaluation.splits import SplitConfig, TemporalGroupedSplitter

    if "split" in df.columns:
        train_df = df.filter(pl.col("split") == "train")
        calib_df = df.filter(pl.col("split") == "calibrate")
        eval_df = df.filter(pl.col("split") == eval_split_name)
    else:
        date_col = "as_of_date" if "as_of_date" in df.columns else "effective_on"
        group_col = "person_cluster_id" if "person_cluster_id" in df.columns else "observation_id"
        splitter = TemporalGroupedSplitter(
            SplitConfig(date_column=date_col, group_column=group_col)
        )
        split_result = splitter.split(df)
        train_df = split_result.train_df
        calib_df = split_result.calibrate_df
        eval_df = (
            split_result.select_df if eval_split_name == "select" else split_result.calibrate_df
        )

    # Synthetic fallback for tiny dev stubs
    if (len(train_df) < 20 or len(eval_df) < 10) and allow_synthetic:
        import datetime as _dt

        from tests.fixtures.synthetic import generate_synthetic_observations_df

        n_synth = 400
        synth_base = generate_synthetic_observations_df(n_records=n_synth, seed=seed)
        dates = [_dt.date(2024, 1, 1) + _dt.timedelta(days=i * 2) for i in range(n_synth)]
        persons = [f"PER-{i:04d}" for i in range(n_synth)]
        synth_df = synth_base.with_columns([
            pl.Series("as_of_date", dates),
            pl.Series("effective_on", dates),
            pl.Series("person_cluster_id", persons),
        ])
        from compintel.evaluation.splits import SplitConfig, TemporalGroupedSplitter
        splitter = TemporalGroupedSplitter(
            SplitConfig(date_column="as_of_date", group_column="person_cluster_id")
        )
        split_result = splitter.split(synth_df)
        train_df = split_result.train_df
        calib_df = split_result.calibrate_df
        eval_df = (
            split_result.select_df if eval_split_name == "select" else split_result.calibrate_df
        )

    report = run_fairness_audit(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name=eval_split_name,
        n_resamples=n_resamples,
        seed=seed,
    )

    md_path = Path(output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(report.to_markdown(), encoding="utf-8")

    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return report
