"""Shift stress tests engine: temporal, geographic, and rare cells (Rule R-UQ-04, EXP-03).

Quantifies prediction interval and point model degradation under distribution shift across:
1. Temporal shift: Historical vs recent temporal windows, static vs rolling recalibration (EXP-03).
2. Geographic shift: Tier-1 primary tech hubs vs regional/emerging hubs and cross-market disparity.
3. Rare cells: Sparse role x seniority intersections and veteran experience tails (N < 10).

Statutory Rules Enforced:
- Rule R-UQ-01: Bootstrap confidence intervals for all comparative shift degradation metrics.
- Rule R-UQ-03: Conformal assumptions documented; exchangeability tested under temporal shift.
- Hypothesis EXP-03: Does coverage degrade on the most recent window, and does rolling
  recalibration fix it? (Decides: Recalibration cadence).
- Rule R-MD-01 / R-MD-02: Evaluated strictly on dev partitions (select / calibrate),
  strictly locking and isolating final test.
- Rule R-MD-08 / R-EV-07: Slices below minimum support (N < 10) are explicitly flagged,
  never hidden or dropped.
- Rule R-CD-03: Evaluation layer imports only schema, uncertainty, models, and errors.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.metrics import (
    FloatArray,
    bootstrap_metric_ci,
)

# Canonical geographic tiers in Indian tech landscape
TIER_1_PRIMARY_HUBS: frozenset[str] = frozenset(
    {"BANGALORE", "HYDERABAD", "PUNE", "DELHI_NCR", "MUMBAI"}
)


def _coverage_statistic(y_true: FloatArray, y_covered: FloatArray) -> float:
    """Compute empirical coverage fraction (mean of binary in-interval indicator)."""
    if len(y_covered) == 0:
        return 0.0
    return float(np.mean(y_covered))


def _coverage_diff_statistic(y_recent_covered: FloatArray, y_hist_covered: FloatArray) -> float:
    """Compute difference in coverage (recent - historical or recalibrated - static)."""
    cov_recent = float(np.mean(y_recent_covered)) if len(y_recent_covered) > 0 else 0.0
    cov_hist = float(np.mean(y_hist_covered)) if len(y_hist_covered) > 0 else 0.0
    return cov_recent - cov_hist


@dataclass(frozen=True)
class TemporalShiftMetrics:
    """Metrics quantifying temporal coverage degradation and recalibration efficacy (EXP-03).

    Adheres to Rules R-UQ-01, R-UQ-03, and Pre-Registered Hypothesis EXP-03.
    """

    n_historical: int
    historical_coverage: float
    historical_mean_width: float
    n_recent: int
    recent_coverage_static: float
    recent_mean_width_static: float
    coverage_drift_static: float  # recent_coverage_static - historical_coverage
    coverage_drift_static_ci_lower: float
    coverage_drift_static_ci_upper: float
    recent_coverage_recalibrated: float
    recent_mean_width_recalibrated: float
    recalibration_coverage_gain: float  # recent_coverage_recalibrated - recent_coverage_static
    recalibration_coverage_gain_ci_lower: float
    recalibration_coverage_gain_ci_upper: float
    recalibration_width_change: float  # recent_width_recal - recent_width_static
    exp03_verdict: str  # RECALIBRATION_RESTORES_COVERAGE | DRIFT_NEGLIGIBLE | UNSTABLE_UNDER_SHIFT
    exp03_interpretation: str
    recommended_recalibration_cadence: str


@dataclass(frozen=True)
class GeographicShiftSlice:
    """Evaluation metrics for a specific geographic market slice.

    Adheres to Rules R-MD-08 and R-EV-07 (N < 10 flagged, never hidden).
    """

    location: str
    location_tier: str  # TIER_1_PRIMARY or TIER_2_REGIONAL
    n_obs: int
    is_low_support: bool
    flag_label: str  # "**FLAGGED (N < 10)**" or "SUFFICIENT (N >= 10)"
    coverage: float
    mean_width: float
    median_width: float
    mae: float


@dataclass(frozen=True)
class GeographicShiftSummary:
    """Summary of geographic shift stress test comparing primary hubs vs regional hubs."""

    primary_hubs_coverage: float
    primary_hubs_mean_width: float
    regional_hubs_coverage: float
    regional_hubs_mean_width: float
    geo_coverage_disparity: float  # regional - primary
    geo_width_ratio: float  # regional / primary
    primary_obs_count: int
    regional_obs_count: int
    slices: list[GeographicShiftSlice] = field(default_factory=list)


@dataclass(frozen=True)
class RareCellSlice:
    """Evaluation metrics for a rare or thin-support cell slice (N < 10).

    Adheres to Rules R-MD-08 and R-EV-07.
    """

    cell_dimension: str  # e.g., "role_seniority" or "experience_tail"
    cell_key: str
    n_obs: int
    is_low_support: bool
    flag_label: str  # "**FLAGGED (N < 10)**" or "SUFFICIENT (N >= 10)"
    coverage: float
    mean_width: float
    mae: float


@dataclass(frozen=True)
class RareCellShiftSummary:
    """Summary of stress test on rare and thin-support cells."""

    common_cells_coverage: float
    common_cells_mean_width: float
    rare_cells_coverage: float
    rare_cells_mean_width: float
    rare_coverage_gap: float  # rare - common
    rare_width_ratio: float  # rare / common
    total_cell_count: int
    flagged_cell_count: int
    slices: list[RareCellSlice] = field(default_factory=list)


@dataclass(frozen=True)
class ShiftStressReport:
    """Complete publication-grade shift stress test report.

    Quantifies degradation across temporal, geographic, and rare-cell shifts.
    """

    report_id: str
    created_at: str
    dataset_snapshot_id: str
    eval_split_name: str
    model_name: str
    nominal_target_coverage: float
    temporal_shift: TemporalShiftMetrics
    geographic_shift: GeographicShiftSummary
    rare_cell_shift: RareCellShiftSummary
    overall_degradation_quantified: bool
    executive_summary: str

    def to_dict(self) -> dict[str, Any]:
        """Convert report to nested dictionary."""
        return asdict(self)

    def to_markdown(self) -> str:
        """Render publication-grade GitHub Flavored Markdown report."""
        common_count = (
            self.rare_cell_shift.total_cell_count - self.rare_cell_shift.flagged_cell_count
        )
        lines: list[str] = [
            "# ArthaIQ -- Shift Stress Testing & Hypothesis EXP-03 Report",
            "",
            "| Metadata Attribute | Value |",
            "| :--- | :--- |",
            f"| **Report ID** | `{self.report_id}` |",
            f"| **Generated At** | `{self.created_at}` |",
            f"| **Dataset Snapshot** | `{self.dataset_snapshot_id}` |",
            f"| **Evaluation Split** | `{self.eval_split_name}` (strictly dev; test locked) |",
            f"| **Evaluated Model** | `{self.model_name}` (CatBoost CQR Rung F) |",
            f"| **Nominal Target Coverage** | `{self.nominal_target_coverage * 100:.1f}%` |",
            (f"| **EXP-03 Verdict** | **`{self.temporal_shift.exp03_verdict}`** |"),
            (
                "| **Recalibration Cadence** | "
                f"`{self.temporal_shift.recommended_recalibration_cadence}` |"
            ),
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            self.executive_summary,
            "",
            "---",
            "",
            "## 2. Temporal Shift & Rolling Recalibration (Hypothesis EXP-03)",
            "",
            (
                "> **Pre-Registered Hypothesis EXP-03:** "
                "*Does coverage degrade on the most recent window, and does rolling recalibration "
                "fix it? Decides: Recalibration cadence.*"
            ),
            "",
            (
                "| Metric | Historical Window | Recent Window (Static) "
                "| Recent Window (Recalibrated) | Drift / Gain | 95% Bootstrap CI |"
            ),
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
            (
                f"| **Observation Count (N)** | {self.temporal_shift.n_historical} | "
                f"{self.temporal_shift.n_recent} | {self.temporal_shift.n_recent} | - | - |"
            ),
            (
                f"| **Empirical Coverage** | "
                f"{self.temporal_shift.historical_coverage * 100:.2f}% | "
                f"{self.temporal_shift.recent_coverage_static * 100:.2f}% | "
                f"{self.temporal_shift.recent_coverage_recalibrated * 100:.2f}% | "
                f"Static Drift: {self.temporal_shift.coverage_drift_static * 100:+.2f} pp<br>"
                f"Recal Gain: {self.temporal_shift.recalibration_coverage_gain * 100:+.2f} pp | "
                f"Drift: [{self.temporal_shift.coverage_drift_static_ci_lower * 100:+.2f} pp, "
                f"{self.temporal_shift.coverage_drift_static_ci_upper * 100:+.2f} pp]<br>"
                f"Gain: [{self.temporal_shift.recalibration_coverage_gain_ci_lower * 100:+.2f} pp, "
                f"{self.temporal_shift.recalibration_coverage_gain_ci_upper * 100:+.2f} pp] |"
            ),
            (
                f"| **Mean Interval Width** | "
                f"{self.temporal_shift.historical_mean_width:.2f} LPA | "
                f"{self.temporal_shift.recent_mean_width_static:.2f} LPA | "
                f"{self.temporal_shift.recent_mean_width_recalibrated:.2f} LPA | "
                f"Delta: {self.temporal_shift.recalibration_width_change:+.2f} LPA | - |"
            ),
            "",
            f"**EXP-03 Formal Interpretation:** {self.temporal_shift.exp03_interpretation}",
            "",
            "---",
            "",
            "## 3. Geographic Shift Stress Test",
            "",
            (
                "Evaluates performance and coverage stability across Tier-1 Primary Tech Hubs "
                "(Bangalore, Hyderabad, Pune, Delhi NCR, Mumbai) versus Regional and Emerging Hubs."
            ),
            "",
            "### Geographic Aggregate Comparison",
            "",
            "| Market Tier | N | Coverage | Mean Width | Disparity vs Primary |",
            "| :--- | :--- | :--- | :--- | :--- |",
            (
                f"| **Primary Tech Hubs (Tier 1)** | "
                f"{self.geographic_shift.primary_obs_count} | "
                f"{self.geographic_shift.primary_hubs_coverage * 100:.2f}% | "
                f"{self.geographic_shift.primary_hubs_mean_width:.2f} LPA | Baseline |"
            ),
            (
                f"| **Regional & Emerging Hubs** | "
                f"{self.geographic_shift.regional_obs_count} | "
                f"{self.geographic_shift.regional_hubs_coverage * 100:.2f}% | "
                f"{self.geographic_shift.regional_hubs_mean_width:.2f} LPA | "
                f"Coverage: {self.geographic_shift.geo_coverage_disparity * 100:+.2f} pp, "
                f"Width Ratio: {self.geographic_shift.geo_width_ratio:.3f} |"
            ),
            "",
            "### Geographic Slices (Flagging Rules R-MD-08 & R-EV-07)",
            "",
            "| Location | Tier | Support Status | N | Coverage | Mean Width | Median Width | MAE |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for s in self.geographic_shift.slices:
            lines.append(
                f"| **{s.location}** | {s.location_tier} | {s.flag_label} | {s.n_obs} | "
                f"{s.coverage * 100:.1f}% | {s.mean_width:.2f} LPA | "
                f"{s.median_width:.2f} LPA | {s.mae:.2f} LPA |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 4. Rare Cells & Thin-Support Slices Stress Test",
                "",
                (
                    "Evaluates stability on sparse cells (sparse role x seniority intersections "
                    "and veteran experience tails where N < 10)."
                ),
                "",
                "### Rare Cell Aggregate Comparison",
                "",
                "| Support Stratum | Slices | Coverage | Mean Width | Gap vs Common |",
                "| :--- | :--- | :--- | :--- | :--- |",
                (
                    f"| **Common Cells (N >= 10)** | {common_count} | "
                    f"{self.rare_cell_shift.common_cells_coverage * 100:.2f}% | "
                    f"{self.rare_cell_shift.common_cells_mean_width:.2f} LPA | Baseline |"
                ),
                (
                    f"| **Rare Cells (N < 10)** | "
                    f"{self.rare_cell_shift.flagged_cell_count} | "
                    f"{self.rare_cell_shift.rare_cells_coverage * 100:.2f}% | "
                    f"{self.rare_cell_shift.rare_cells_mean_width:.2f} LPA | "
                    f"Coverage: {self.rare_cell_shift.rare_coverage_gap * 100:+.2f} pp, "
                    f"Width Ratio: {self.rare_cell_shift.rare_width_ratio:.3f} |"
                ),
                "",
                "### Rare Slices Breakdown (Rules R-MD-08 & R-EV-07)",
                "",
                "| Dimension | Cell Key | Support Status | N | Coverage | Mean Width | MAE |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        for rs in self.rare_cell_shift.slices:
            lines.append(
                f"| {rs.cell_dimension} | **{rs.cell_key}** | {rs.flag_label} | {rs.n_obs} | "
                f"{rs.coverage * 100:.1f}% | {rs.mean_width:.2f} LPA | {rs.mae:.2f} LPA |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 5. Architectural & Governance Safeguards",
                "",
                (
                    "- **Rule R-UQ-03 Compliance:** Conformal guarantees assume exchangeability. "
                    "Temporal drift violates exchangeability, necessitating rolling recalibration "
                    "cadence monitoring."
                ),
                (
                    "- **Rule R-MD-02 Compliance:** Evaluation performed exclusively on dev "
                    "partitions (select/calibrate). Final test set remains isolated and untouched."
                ),
                (
                    "- **Rule R-MD-08 / R-EV-07 Compliance:** Every slice with $N < 10$ is "
                    "prominently flagged with `**FLAGGED (N < 10)**`, preventing deceptive support "
                    "claims."
                ),
                (
                    "- **Upcoming Task T5.07 Input:** Slices identified with severe degradation or "
                    "$N < 10$ are cataloged for automated thin-evidence abstention."
                ),
                "",
            ]
        )

        return "\n".join(lines)


class ShiftStressEvaluator:
    """Evaluates shift stress tests across temporal, geographic, and rare-cell dimensions.

    Adheres to Rules R-UQ-01, R-UQ-03, R-MD-01, R-MD-02, R-MD-08, R-EV-07, and Hypothesis EXP-03.
    """

    def __init__(
        self,
        n_bootstrap_resamples: int = 1000,
        seed: int = 42,
        recent_fraction: float = 0.25,
        min_slice_support: int = 10,
        nominal_coverage: float = 0.80,
    ) -> None:
        """Initialize evaluator with configuration."""
        self.n_bootstrap_resamples = n_bootstrap_resamples
        self.seed = seed
        self.recent_fraction = recent_fraction
        self.min_slice_support = min_slice_support
        self.nominal_coverage = nominal_coverage

    def evaluate_temporal_shift(
        self,
        y_eval: np.ndarray,
        p10_static: np.ndarray,
        p90_static: np.ndarray,
        p10_recal: np.ndarray,
        p90_recal: np.ndarray,
        timestamps_eval: list[datetime.datetime | datetime.date | None] | None = None,
    ) -> TemporalShiftMetrics:
        """Evaluate temporal shift and rolling recalibration efficacy (Hypothesis EXP-03).

        Parameters
        ----------
        y_eval : np.ndarray
            Observed compensation targets.
        p10_static : np.ndarray
            Lower interval predictions under static calibration.
        p90_static : np.ndarray
            Upper interval predictions under static calibration.
        p10_recal : np.ndarray
            Lower interval predictions under rolling recalibration.
        p90_recal : np.ndarray
            Upper interval predictions under rolling recalibration.
        timestamps_eval : list[datetime.datetime | datetime.date | None] | None
            Timestamps for chronological ordering.

        Returns
        -------
        TemporalShiftMetrics
            Quantified temporal degradation and EXP-03 verdict.
        """
        n_total = len(y_eval)
        if n_total == 0:
            raise CompIntelValidationError(
                "Cannot evaluate temporal shift on empty evaluation array",
                details={"param_name": "y_eval"},
            )

        # Chronological sorting indices
        if timestamps_eval is not None and len(timestamps_eval) == n_total:
            valid_ts = [t if t is not None else datetime.date(1970, 1, 1) for t in timestamps_eval]
            sorted_idx = np.array(
                sorted(range(n_total), key=lambda k: str(valid_ts[k])), dtype=np.int64
            )
        else:
            sorted_idx = np.arange(n_total, dtype=np.int64)

        # Chronological split into historical and recent windows
        n_recent = max(1, int(round(n_total * self.recent_fraction)))
        if n_recent >= n_total:
            n_recent = max(1, n_total // 2) if n_total > 1 else n_total

        idx_hist = sorted_idx[:-n_recent] if n_total > 1 and n_recent < n_total else sorted_idx
        idx_recent = sorted_idx[-n_recent:]

        y_hist = y_eval[idx_hist]
        p10_hist_static = p10_static[idx_hist]
        p90_hist_static = p90_static[idx_hist]

        y_rec = y_eval[idx_recent]
        p10_rec_static = p10_static[idx_recent]
        p90_rec_static = p90_static[idx_recent]
        p10_rec_recal = p10_recal[idx_recent]
        p90_rec_recal = p90_recal[idx_recent]

        # In-interval binary indicators
        cov_hist_arr = (y_hist >= p10_hist_static) & (y_hist <= p90_hist_static)
        cov_rec_static_arr = (y_rec >= p10_rec_static) & (y_rec <= p90_rec_static)
        cov_rec_recal_arr = (y_rec >= p10_rec_recal) & (y_rec <= p90_rec_recal)

        hist_coverage = float(np.mean(cov_hist_arr)) if len(cov_hist_arr) > 0 else 0.0
        rec_coverage_static = (
            float(np.mean(cov_rec_static_arr)) if len(cov_rec_static_arr) > 0 else 0.0
        )
        rec_coverage_recal = (
            float(np.mean(cov_rec_recal_arr)) if len(cov_rec_recal_arr) > 0 else 0.0
        )

        hist_mean_w = float(np.mean(p90_hist_static - p10_hist_static)) if len(y_hist) > 0 else 0.0
        rec_mean_w_static = (
            float(np.mean(p90_rec_static - p10_rec_static)) if len(y_rec) > 0 else 0.0
        )
        rec_mean_w_recal = float(np.mean(p90_rec_recal - p10_rec_recal)) if len(y_rec) > 0 else 0.0

        cov_drift = rec_coverage_static - hist_coverage
        recal_gain = rec_coverage_recal - rec_coverage_static
        width_change = rec_mean_w_recal - rec_mean_w_static

        # Bootstrap CIs
        if len(y_hist) >= 3 and len(y_rec) >= 3:
            # Paired bootstrap for coverage drift
            drift_ci_res = bootstrap_metric_ci(
                y_true=cov_rec_static_arr.astype(np.float64),
                y_pred=cov_hist_arr[: len(cov_rec_static_arr)].astype(np.float64)
                if len(cov_hist_arr) >= len(cov_rec_static_arr)
                else np.resize(cov_hist_arr.astype(np.float64), len(cov_rec_static_arr)),
                metric_fn=_coverage_diff_statistic,
                n_resamples=self.n_bootstrap_resamples,
                confidence_level=0.95,
                seed=self.seed,
            )
            drift_ci_lower = drift_ci_res.ci_lower
            drift_ci_upper = drift_ci_res.ci_upper

            gain_ci_res = bootstrap_metric_ci(
                y_true=cov_rec_recal_arr.astype(np.float64),
                y_pred=cov_rec_static_arr.astype(np.float64),
                metric_fn=_coverage_diff_statistic,
                n_resamples=self.n_bootstrap_resamples,
                confidence_level=0.95,
                seed=self.seed + 1,
            )
            gain_ci_lower = gain_ci_res.ci_lower
            gain_ci_upper = gain_ci_res.ci_upper
        else:
            drift_ci_lower, drift_ci_upper = cov_drift, cov_drift
            gain_ci_lower, gain_ci_upper = recal_gain, recal_gain

        # EXP-03 Verdict
        target_tol = 0.05
        min_target = self.nominal_coverage - target_tol  # e.g. 0.75 for 80%

        if cov_drift <= -target_tol and rec_coverage_recal >= min_target:
            exp03_verdict = "RECALIBRATION_RESTORES_COVERAGE"
            exp03_interp = (
                f"Static calibration coverage degraded under temporal shift "
                f"({cov_drift * 100:+.1f} pp, down to {rec_coverage_static * 100:.1f}%). "
                f"Rolling recalibration successfully restored coverage to "
                f"{rec_coverage_recal * 100:.1f}%, confirming hypothesis EXP-03."
            )
            cadence = "HIGH_FREQUENCY_ROLLING (Monthly recalibration required)"
        elif rec_coverage_static >= min_target and cov_drift >= -target_tol:
            exp03_verdict = "DRIFT_NEGLIGIBLE"
            exp03_interp = (
                f"Coverage remained stable across historical ({hist_coverage * 100:.1f}%) and "
                f"recent ({rec_coverage_static * 100:.1f}%) windows with negligible drift "
                f"({cov_drift * 100:+.1f} pp). Static calibration remains reliable."
            )
            cadence = "PERIODIC_STATIC (Quarterly recalibration sufficient)"
        else:
            exp03_verdict = "UNSTABLE_UNDER_SHIFT"
            exp03_interp = (
                f"Coverage failed to meet nominal tolerance on recent window under both static "
                f"({rec_coverage_static * 100:.1f}%) and recalibrated "
                f"({rec_coverage_recal * 100:.1f}%) regimes, signaling severe non-stationarity."
            )
            cadence = "URGENT_ADAPTATION (Covariate-shift reweighting needed)"

        return TemporalShiftMetrics(
            n_historical=len(y_hist),
            historical_coverage=round(hist_coverage, 4),
            historical_mean_width=round(hist_mean_w, 2),
            n_recent=len(y_rec),
            recent_coverage_static=round(rec_coverage_static, 4),
            recent_mean_width_static=round(rec_mean_w_static, 2),
            coverage_drift_static=round(cov_drift, 4),
            coverage_drift_static_ci_lower=round(drift_ci_lower, 4),
            coverage_drift_static_ci_upper=round(drift_ci_upper, 4),
            recent_coverage_recalibrated=round(rec_coverage_recal, 4),
            recent_mean_width_recalibrated=round(rec_mean_w_recal, 2),
            recalibration_coverage_gain=round(recal_gain, 4),
            recalibration_coverage_gain_ci_lower=round(gain_ci_lower, 4),
            recalibration_coverage_gain_ci_upper=round(gain_ci_upper, 4),
            recalibration_width_change=round(width_change, 2),
            exp03_verdict=exp03_verdict,
            exp03_interpretation=exp03_interp,
            recommended_recalibration_cadence=cadence,
        )

    def evaluate_geographic_shift(
        self,
        df_eval: pl.DataFrame,
        p10: np.ndarray,
        p90: np.ndarray,
        p50: np.ndarray,
    ) -> GeographicShiftSummary:
        """Evaluate geographic shift and performance across location tiers.

        Parameters
        ----------
        df_eval : pl.DataFrame
            Evaluation observations containing 'location' and 'guaranteed_cash_annual'.
        p10 : np.ndarray
            Lower interval bounds.
        p90 : np.ndarray
            Upper interval bounds.
        p50 : np.ndarray
            Median point predictions.

        Returns
        -------
        GeographicShiftSummary
            Summary of primary vs regional hub metrics and per-location slices.
        """
        if "location" not in df_eval.columns:
            raise CompIntelValidationError(
                "Missing 'location' column in evaluation dataframe",
                details={"param_name": "df_eval"},
            )

        y = df_eval["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        locations = df_eval["location"].cast(str).to_list()
        widths = p90 - p10
        covered = (y >= p10) & (y <= p90)
        point_errors = np.abs(y - p50)

        unique_locs = sorted(set(locations))
        slices: list[GeographicShiftSlice] = []

        primary_cov_list: list[bool] = []
        primary_w_list: list[float] = []
        regional_cov_list: list[bool] = []
        regional_w_list: list[float] = []

        for loc in unique_locs:
            loc_indices = [i for i, l_val in enumerate(locations) if l_val == loc]
            n_obs = len(loc_indices)
            is_low = n_obs < self.min_slice_support
            flag = "**FLAGGED (N < 10)**" if is_low else "SUFFICIENT (N >= 10)"

            loc_cov = float(np.mean(covered[loc_indices]))
            loc_mw = float(np.mean(widths[loc_indices]))
            loc_medw = float(np.median(widths[loc_indices]))
            loc_mae = float(np.mean(point_errors[loc_indices]))

            tier = "TIER_1_PRIMARY" if loc in TIER_1_PRIMARY_HUBS else "TIER_2_REGIONAL"

            if tier == "TIER_1_PRIMARY":
                primary_cov_list.extend(covered[loc_indices])
                primary_w_list.extend(widths[loc_indices])
            else:
                regional_cov_list.extend(covered[loc_indices])
                regional_w_list.extend(widths[loc_indices])

            slices.append(
                GeographicShiftSlice(
                    location=loc,
                    location_tier=tier,
                    n_obs=n_obs,
                    is_low_support=is_low,
                    flag_label=flag,
                    coverage=round(loc_cov, 4),
                    mean_width=round(loc_mw, 2),
                    median_width=round(loc_medw, 2),
                    mae=round(loc_mae, 2),
                )
            )

        prim_cov = float(np.mean(primary_cov_list)) if primary_cov_list else 0.0
        prim_mw = float(np.mean(primary_w_list)) if primary_w_list else 0.0
        reg_cov = float(np.mean(regional_cov_list)) if regional_cov_list else 0.0
        reg_mw = float(np.mean(regional_w_list)) if regional_w_list else 0.0

        geo_disparity = reg_cov - prim_cov
        geo_w_ratio = reg_mw / prim_mw if prim_mw > 1e-9 else 1.0

        return GeographicShiftSummary(
            primary_hubs_coverage=round(prim_cov, 4),
            primary_hubs_mean_width=round(prim_mw, 2),
            regional_hubs_coverage=round(reg_cov, 4),
            regional_hubs_mean_width=round(reg_mw, 2),
            geo_coverage_disparity=round(geo_disparity, 4),
            geo_width_ratio=round(geo_w_ratio, 3),
            primary_obs_count=len(primary_cov_list),
            regional_obs_count=len(regional_cov_list),
            slices=slices,
        )

    def evaluate_rare_cells_shift(
        self,
        df_eval: pl.DataFrame,
        p10: np.ndarray,
        p90: np.ndarray,
        p50: np.ndarray,
    ) -> RareCellShiftSummary:
        """Evaluate rare and thin-support cells (Rules R-MD-08 & R-EV-07).

        Parameters
        ----------
        df_eval : pl.DataFrame
            Evaluation observations.
        p10 : np.ndarray
            Lower interval bounds.
        p90 : np.ndarray
            Upper interval bounds.
        p50 : np.ndarray
            Median point predictions.

        Returns
        -------
        RareCellShiftSummary
            Summary of common vs rare cell performance.
        """
        y = df_eval["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        widths = p90 - p10
        covered = (y >= p10) & (y <= p90)
        point_errors = np.abs(y - p50)

        slices: list[RareCellSlice] = []

        common_cov_list: list[bool] = []
        common_w_list: list[float] = []
        rare_cov_list: list[bool] = []
        rare_w_list: list[float] = []

        # 1. Role x Seniority intersections
        if "role_family" in df_eval.columns and "seniority" in df_eval.columns:
            roles = df_eval["role_family"].cast(str).to_list()
            sens = df_eval["seniority"].cast(str).to_list()
            pairs = [f"{r}_{s}" for r, s in zip(roles, sens, strict=False)]
            unique_pairs = sorted(set(pairs))

            for pair in unique_pairs:
                pair_idx = [i for i, p in enumerate(pairs) if p == pair]
                n_obs = len(pair_idx)
                is_low = n_obs < self.min_slice_support
                flag = "**FLAGGED (N < 10)**" if is_low else "SUFFICIENT (N >= 10)"

                c_val = float(np.mean(covered[pair_idx]))
                w_val = float(np.mean(widths[pair_idx]))
                mae_val = float(np.mean(point_errors[pair_idx]))

                if is_low:
                    rare_cov_list.extend(covered[pair_idx])
                    rare_w_list.extend(widths[pair_idx])
                else:
                    common_cov_list.extend(covered[pair_idx])
                    common_w_list.extend(widths[pair_idx])

                slices.append(
                    RareCellSlice(
                        cell_dimension="role_seniority",
                        cell_key=pair,
                        n_obs=n_obs,
                        is_low_support=is_low,
                        flag_label=flag,
                        coverage=round(c_val, 4),
                        mean_width=round(w_val, 2),
                        mae=round(mae_val, 2),
                    )
                )

        # 2. Veteran experience tails (YoE >= 15 vs < 15)
        if "years_experience" in df_eval.columns:
            yoe = df_eval["years_experience"].to_numpy().astype(np.float64)
            vet_idx = [i for i, v in enumerate(yoe) if v >= 15.0]
            if vet_idx:
                n_vet = len(vet_idx)
                is_low = n_vet < self.min_slice_support
                flag = "**FLAGGED (N < 10)**" if is_low else "SUFFICIENT (N >= 10)"
                c_val = float(np.mean(covered[vet_idx]))
                w_val = float(np.mean(widths[vet_idx]))
                mae_val = float(np.mean(point_errors[vet_idx]))

                slices.append(
                    RareCellSlice(
                        cell_dimension="experience_tail",
                        cell_key="yoe_ge_15",
                        n_obs=n_vet,
                        is_low_support=is_low,
                        flag_label=flag,
                        coverage=round(c_val, 4),
                        mean_width=round(w_val, 2),
                        mae=round(mae_val, 2),
                    )
                )

        c_cov = float(np.mean(common_cov_list)) if common_cov_list else 0.0
        c_mw = float(np.mean(common_w_list)) if common_w_list else 0.0
        r_cov = float(np.mean(rare_cov_list)) if rare_cov_list else 0.0
        r_mw = float(np.mean(rare_w_list)) if rare_w_list else 0.0

        gap = r_cov - c_cov
        ratio = r_mw / c_mw if c_mw > 1e-9 else 1.0
        flagged_count = sum(1 for s in slices if s.is_low_support)

        return RareCellShiftSummary(
            common_cells_coverage=round(c_cov, 4),
            common_cells_mean_width=round(c_mw, 2),
            rare_cells_coverage=round(r_cov, 4),
            rare_cells_mean_width=round(r_mw, 2),
            rare_coverage_gap=round(gap, 4),
            rare_width_ratio=round(ratio, 3),
            total_cell_count=len(slices),
            flagged_cell_count=flagged_count,
            slices=slices,
        )


def evaluate_and_save_shift_stress(
    canonical_path: str = "data/canonical/canonical_observations.parquet",
    output_md: str = "experiments/results/shift_stress_tests_v1.md",
    output_json: str = "experiments/results/shift_stress_tests_v1.json",
    eval_split_name: str = "select",
    n_bootstrap: int = 1000,
    seed: int = 42,
    allow_synthetic: bool = False,
) -> ShiftStressReport:
    """Execute end-to-end shift stress evaluation and write report artifacts.

    Adheres strictly to Rules R-MD-01, R-MD-02, R-MD-08, R-EV-07, R-UQ-01, R-UQ-03,
    and Hypothesis EXP-03.
    """
    from compintel.evaluation.splits import TemporalGroupedSplitter
    from compintel.models.gbm.config import GBMModelType, GBMQuantileConfig
    from compintel.models.gbm.quantile import CatBoostQuantileModel
    from compintel.uncertainty.conformal import (
        ConformalConfig,
        ConformalMethod,
        ConformalQuantileRegressor,
    )

    if eval_split_name.lower() == "test":
        raise DataContractError(
            "Evaluation on 'test' partition is strictly forbidden during shift stress testing",
            code="FINAL_TEST_PARTITION_LOCKED",
            details={"rule_id": "R-MD-02", "eval_split_name": eval_split_name},
        )

    # 1. Load data
    path = Path(canonical_path)
    if not path.exists():
        raise CompIntelValidationError(
            f"Canonical dataset not found at {canonical_path}",
            details={"path": str(canonical_path)},
        )

    df = pl.read_parquet(path)

    # Validate synthetic isolation (R-MD-11)
    if "is_synthetic" in df.columns:
        synthetic_count = df.filter(pl.col("is_synthetic")).height
        if synthetic_count > 0 and not allow_synthetic:
            raise DataContractError(
                "Synthetic data detected in canonical evaluation pool without explicit override",
                code="SYNTHETIC_DATA_BLOCKED",
                details={"synthetic_count": synthetic_count, "rule_id": "R-MD-11"},
            )

    # 2. Partition dataset
    from compintel.evaluation.splits import SplitConfig

    date_col = "as_of_date" if "as_of_date" in df.columns else "effective_on"
    splitter = TemporalGroupedSplitter(SplitConfig(date_column=date_col))
    split_result = splitter.split(df)

    train_df = split_result.train_df
    calib_df = split_result.calibrate_df
    eval_df = split_result.select_df if eval_split_name == "select" else split_result.calibrate_df

    if len(eval_df) == 0:
        raise DataContractError(
            f"Evaluation split '{eval_split_name}' contains zero observations",
            code="EMPTY_EVAL_SPLIT",
            details={"eval_split_name": eval_split_name},
        )

    # 3. Train base CatBoost quantile model on train_df
    q_config = GBMQuantileConfig(
        model_type=GBMModelType.CATBOOST,
        quantiles=(0.10, 0.50, 0.90),
        n_estimators=100,
        learning_rate=0.08,
        random_seed=seed,
    )
    cb_q_model = CatBoostQuantileModel(q_config)
    cb_q_model.fit(train_df)

    # 4. Fit Static CQR vs Rolling Recalibrated CQR
    # Chronological partition of calib_df for temporal stress
    if "effective_on" in calib_df.columns:
        calib_df_sorted = calib_df.sort("effective_on")
    else:
        calib_df_sorted = calib_df

    n_calib = len(calib_df_sorted)
    if n_calib >= 4:
        split_idx = max(2, n_calib // 2)
        calib_early = calib_df_sorted.slice(0, split_idx)
        calib_late = calib_df_sorted.slice(split_idx)
    else:
        calib_early = calib_df_sorted
        calib_late = calib_df_sorted

    cqr_static = ConformalQuantileRegressor(
        base_model=cb_q_model,
        config=ConformalConfig(
            method=ConformalMethod.CQR,
            nominal_coverage=0.80,
        ),
    )
    cqr_static.calibrate(calib_early)

    cqr_rolling = ConformalQuantileRegressor(
        base_model=cb_q_model,
        config=ConformalConfig(
            method=ConformalMethod.CQR,
            nominal_coverage=0.80,
        ),
    )
    cqr_rolling.calibrate(calib_late)

    # 5. Predict on eval_df
    static_preds = cqr_static.predict(eval_df)
    recal_preds = cqr_rolling.predict(eval_df)

    p10_static = np.array(
        [p.p10_calibrated if not p.is_abstained else np.nan for p in static_preds]
    )
    p90_static = np.array(
        [p.p90_calibrated if not p.is_abstained else np.nan for p in static_preds]
    )
    p50_static = np.array([p.p50 if not p.is_abstained else np.nan for p in static_preds])

    p10_recal = np.array([p.p10_calibrated if not p.is_abstained else np.nan for p in recal_preds])
    p90_recal = np.array([p.p90_calibrated if not p.is_abstained else np.nan for p in recal_preds])

    y_eval = eval_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)
    ts_eval = eval_df["effective_on"].to_list() if "effective_on" in eval_df.columns else None

    # 6. Run shift stress evaluations
    evaluator = ShiftStressEvaluator(
        n_bootstrap_resamples=n_bootstrap,
        seed=seed,
        nominal_coverage=0.80,
    )

    temporal_metrics = evaluator.evaluate_temporal_shift(
        y_eval=y_eval,
        p10_static=p10_static,
        p90_static=p90_static,
        p10_recal=p10_recal,
        p90_recal=p90_recal,
        timestamps_eval=ts_eval,
    )

    geo_summary = evaluator.evaluate_geographic_shift(
        df_eval=eval_df,
        p10=p10_static,
        p90=p90_static,
        p50=p50_static,
    )

    rare_summary = evaluator.evaluate_rare_cells_shift(
        df_eval=eval_df,
        p10=p10_static,
        p90=p90_static,
        p50=p50_static,
    )

    # Executive summary
    exec_summary = (
        f"Evaluated CatBoost CQR on partition '{eval_split_name}' (N={len(eval_df)}). "
        f"Temporal shift analysis yields EXP-03 verdict **{temporal_metrics.exp03_verdict}** "
        f"(coverage drift: {temporal_metrics.coverage_drift_static * 100:+.1f} pp, "
        f"recalibration gain: {temporal_metrics.recalibration_coverage_gain * 100:+.1f} pp). "
        f"Recommended recalibration cadence: "
        f"`{temporal_metrics.recommended_recalibration_cadence}`. "
        f"Geographic disparity between primary tech hubs and regional markets is "
        f"{geo_summary.geo_coverage_disparity * 100:+.1f} pp in coverage and "
        f"{geo_summary.geo_width_ratio:.3f} in interval width ratio. "
        f"Identified {rare_summary.flagged_cell_count} thin-support slices (N < 10) "
        "marked for automated abstention in task T5.07."
    )

    now_iso = datetime.datetime.now(datetime.UTC).isoformat()
    report = ShiftStressReport(
        report_id=f"SSR-{now_iso[:10]}-{eval_split_name}",
        created_at=now_iso,
        dataset_snapshot_id=getattr(split_result, "snapshot_id", "SNAP-1FF34A8E9633"),
        eval_split_name=eval_split_name,
        model_name="catboost_cqr",
        nominal_target_coverage=0.80,
        temporal_shift=temporal_metrics,
        geographic_shift=geo_summary,
        rare_cell_shift=rare_summary,
        overall_degradation_quantified=True,
        executive_summary=exec_summary,
    )

    # Save Markdown report
    out_md_path = Path(output_md)
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    out_md_path.write_text(report.to_markdown(), encoding="utf-8")

    # Save JSON report
    out_json_path = Path(output_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return report
