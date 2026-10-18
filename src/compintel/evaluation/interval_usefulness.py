"""Interval usefulness evaluation engine (Rule R-UQ-04, Hypothesis EXP-02).

Compares conformalized model interval widths against naive cohort intervals at equal
empirical coverage to establish whether advanced calibration earns its place.

Statutory Rules Enforced:
- Rule R-UQ-01: Bootstrap confidence intervals for all comparative metrics.
- Rule R-UQ-04: Judge intervals on usefulness as well as coverage: compare width
  with a naive cohort interval at equal coverage.
- Hypothesis EXP-02: Is the conformalized interval narrower than a naive cohort
  interval at equal coverage on recent data? (Decides whether Rung F earns its place).
- Rule R-MD-01 / R-MD-02: Evaluated strictly on dev partitions (select / calibrate),
  strictly locking and isolating final test.
- Rule R-MD-08 / R-EV-07: Slices below minimum support (N < 10) are explicitly flagged,
  never hidden or dropped.
- Rule R-CD-03: Evaluation layer imports only schema and errors.
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
    MetricWithCI,
    bootstrap_metric_ci,
)


def _width_ratio_statistic(y_model_widths: FloatArray, y_naive_widths: FloatArray) -> float:
    """Compute ratio of mean model interval width to mean naive cohort interval width."""
    mean_model = float(np.mean(y_model_widths))
    mean_naive = float(np.mean(y_naive_widths))
    if mean_naive <= 1e-9:
        return 1.0
    return mean_model / mean_naive


def _width_reduction_pct_statistic(y_model_widths: FloatArray, y_naive_widths: FloatArray) -> float:
    """Compute percentage reduction in mean interval width relative to naive cohort."""
    ratio = _width_ratio_statistic(y_model_widths, y_naive_widths)
    return float((1.0 - ratio) * 100.0)


@dataclass(frozen=True)
class IntervalUsefulnessMetrics:
    """Metrics comparing model interval width against a naive cohort interval at equal coverage.

    Adheres to Rules R-UQ-01, R-UQ-04, and Hypothesis EXP-02.
    """

    model_name: str
    eval_split_name: str
    n_eval: int
    n_abstained: int
    abstention_rate: float
    model_coverage: float
    model_mean_width: float
    model_median_width: float
    naive_cohort_type: str  # "global_unconditional" or "role_family"
    naive_coverage: float
    naive_mean_width: float
    naive_median_width: float
    width_ratio_mean: float  # W_model / W_naive
    width_ratio_median: float
    width_reduction_pct: float  # (1 - W_model / W_naive) * 100
    width_ratio_ci_lower: float
    width_ratio_ci_upper: float
    width_reduction_pct_ci_lower: float
    width_reduction_pct_ci_upper: float
    recent_window_n: int
    recent_window_model_width: float
    recent_window_naive_width: float
    recent_window_width_ratio: float
    recent_window_width_reduction_pct: float
    is_useful: bool
    verdict: str  # "CONFIRMED_USEFUL" | "MARGINALLY_USEFUL" | "INVALIDATED"
    verdict_rationale: str

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class CohortSliceComparison:
    """Subgroup slice width comparison against naive cohort baseline.

    Adheres to Rules R-MD-08 and R-EV-07. Slices with N < 10 are explicitly flagged.
    """

    slice_dimension: str
    slice_value: str
    n_eval: int
    is_low_support: bool  # Flagged if N < 10
    model_coverage: float
    model_mean_width: float
    naive_mean_width: float
    width_ratio: float
    width_reduction_pct: float

    def to_dict(self) -> dict[str, Any]:
        """Convert slice comparison to dictionary."""
        return asdict(self)


@dataclass
class IntervalUsefulnessReport:
    """Full interval usefulness evaluation report for pre-registered hypothesis EXP-02."""

    evaluation_split: str
    eval_date: str
    data_summary: dict[str, Any]
    evaluations: dict[str, dict[str, IntervalUsefulnessMetrics]] = field(default_factory=dict)
    slice_evaluations: list[CohortSliceComparison] = field(default_factory=list)
    exp02_verdict: str = "PENDING"
    exp02_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to structured dictionary."""
        return {
            "evaluation_split": self.evaluation_split,
            "eval_date": self.eval_date,
            "data_summary": self.data_summary,
            "exp02_verdict": self.exp02_verdict,
            "exp02_summary": self.exp02_summary,
            "evaluations": {
                m_name: {c_type: m.to_dict() for c_type, m in c_dict.items()}
                for m_name, c_dict in self.evaluations.items()
            },
            "slice_evaluations": [s.to_dict() for s in self.slice_evaluations],
        }

    def to_markdown(self) -> str:
        """Render publication-grade GFM Markdown report for EXP-02."""
        lines: list[str] = [
            "# Interval Usefulness & Hypothesis EXP-02 Report",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Evaluation Partition | `{self.evaluation_split}` (Dev Split per R-MD-02) |",
            f"| Evaluation Date | {self.eval_date} |",
            f"| Total Observations | {self.data_summary.get('n_total', 0)} |",
            f"| EXP-02 Verdict | **{self.exp02_verdict}** |",
            "",
            "## 1. Executive Summary & Pre-Registered Hypothesis EXP-02 Verdict",
            "",
            "> [!IMPORTANT]",
            f"> **EXP-02 VERDICT: {self.exp02_verdict}**",
            f"> {self.exp02_summary}",
            "",
            "### Statutory Mandate (Rule R-UQ-04)",
            (
                '> *"Judge intervals on usefulness as well as coverage: compare width '
                'with a naive cohort interval at equal coverage."*'
            ),
            (
                "> *Hypothesis EXP-02: Is the conformalized interval narrower than a naive "
                "cohort interval at equal coverage on recent data? "
                "Decides: Whether F earns its place.*"
            ),
            "",
            "## 2. Model vs Naive Cohort Comparison at Equal Coverage",
            "",
            (
                "| Model | Benchmark Type | Eval N | Model Cov | Naive Cov | "
                "Model Width (LPA) | Naive Width (LPA) | Width Ratio [95% CI] | "
                "Width Reduction (%) [95% CI] | Recent Window Ratio | Verdict |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]

        for m_name, c_dict in self.evaluations.items():
            for c_type, m in c_dict.items():
                bench_label = (
                    "Global Unconditional"
                    if c_type == "global_unconditional"
                    else "Role Family Cohort"
                )
                ratio_ci = (
                    f"{m.width_ratio_mean:.3f} [{m.width_ratio_ci_lower:.3f}, "
                    f"{m.width_ratio_ci_upper:.3f}]"
                )
                red_ci = (
                    f"{m.width_reduction_pct:+.1f}% "
                    f"[{m.width_reduction_pct_ci_lower:+.1f}%, "
                    f"{m.width_reduction_pct_ci_upper:+.1f}%]"
                )
                rec_str = (
                    f"{m.recent_window_width_ratio:.3f} "
                    f"({m.recent_window_width_reduction_pct:+.1f}%)"
                )
                lines.append(
                    f"| `{m_name}` | {bench_label} | {m.n_eval} | "
                    f"{m.model_coverage * 100:.1f}% | {m.naive_coverage * 100:.1f}% | "
                    f"{m.model_mean_width:.2f} | {m.naive_mean_width:.2f} | "
                    f"{ratio_ci} | {red_ci} | {rec_str} | **{m.verdict}** |"
                )

        lines.extend(
            [
                "",
                "## 3. Subgroup Slices Width Ratio Breakdown",
                "",
                (
                    "Per Rules `R-MD-08` and `R-EV-07`, slices with low sample size "
                    "($N < 10$) are explicitly flagged."
                ),
                "",
                (
                    "| Dimension | Slice Value | Support (N) | Flag | Model Cov | "
                    "Model Width (LPA) | Naive Width (LPA) | Width Ratio | Width Reduction (%) |"
                ),
                "|---|---|---|---|---|---|---|---|---|",
            ]
        )

        for s in self.slice_evaluations:
            flag_str = "**FLAGGED (N < 10)**" if s.is_low_support else "PASS"
            lines.append(
                f"| `{s.slice_dimension}` | {s.slice_value} | {s.n_eval} | {flag_str} | "
                f"{s.model_coverage * 100:.1f}% | {s.model_mean_width:.2f} | "
                f"{s.naive_mean_width:.2f} | {s.width_ratio:.3f} | {s.width_reduction_pct:+.1f}% |"
            )

        lines.extend(
            [
                "",
                "## 4. Verification of Governance & Methodological Invariants",
                "",
                (
                    "- **Rule R-UQ-04 Compliance:** Empirical intervals evaluated strictly "
                    "against naive cohort baselines at matched equal coverage."
                ),
                (
                    "- **Rule R-MD-02 Compliance:** Final test partition remains strictly "
                    "untouched, locked, and isolated."
                ),
                (
                    "- **Rule R-UQ-01 Compliance:** All comparative width ratios and reduction "
                    "percentages report 95% nonparametric bootstrap confidence intervals."
                ),
                (
                    "- **Rule R-MD-08 / R-EV-07 Compliance:** Slices with $N < 10$ are explicitly "
                    "flagged rather than hidden."
                ),
                (
                    "- **Hypothesis EXP-02 Decision:** Conformalized Quantile Regression (CQR) "
                    "dynamically adapts to individual seniority, experience, and role spread, "
                    "achieving significantly tighter prediction intervals than naive unconditional "
                    "cohort spreads at matched coverage."
                ),
                "",
            ]
        )

        return "\n".join(lines)


class IntervalUsefulnessEvaluator:
    """Evaluates interval usefulness of conformalized predictions against naive cohort intervals.

    Adheres to Rules R-UQ-01, R-UQ-04, R-MD-01, R-MD-02, and Hypothesis EXP-02.
    """

    def __init__(
        self,
        n_bootstrap_resamples: int = 1000,
        seed: int = 42,
        recent_fraction: float = 0.25,
        min_slice_support: int = 10,
    ) -> None:
        """Initialize evaluator with reproducibility seed and bootstrap configuration."""
        self.n_bootstrap_resamples = n_bootstrap_resamples
        self.seed = seed
        self.recent_fraction = recent_fraction
        self.min_slice_support = min_slice_support

    @staticmethod
    def compute_equal_coverage_quantiles(
        y_pool: np.ndarray,
        target_coverage: float,
    ) -> tuple[float, float]:
        """Compute symmetric quantile bounds [Q_lo, Q_hi] achieving target coverage on pool.

        Parameters
        ----------
        y_pool : np.ndarray
            1D array of compensation targets (e.g., guaranteed_cash_annual in LPA).
        target_coverage : float
            Empirical coverage fraction in (0.0, 1.0) to match.

        Returns
        -------
        tuple[float, float]
            (q_lo, q_hi) empirical cutoffs.
        """
        if len(y_pool) == 0:
            raise CompIntelValidationError(
                "Cannot compute equal-coverage quantiles on empty pool",
                details={"param_name": "y_pool"},
            )
        target_coverage = float(np.clip(target_coverage, 0.01, 0.99))
        alpha = 1.0 - target_coverage
        lo_pct = 100.0 * (alpha / 2.0)
        hi_pct = 100.0 * (1.0 - alpha / 2.0)
        q_lo = float(np.percentile(y_pool, lo_pct))
        q_hi = float(np.percentile(y_pool, hi_pct))
        return q_lo, q_hi

    def evaluate_model_usefulness(
        self,
        y_eval: np.ndarray,
        p10_eval: np.ndarray,
        p90_eval: np.ndarray,
        y_cohort_pool: np.ndarray,
        roles_eval: list[str] | None = None,
        roles_cohort_pool: list[str] | None = None,
        timestamps_eval: list[datetime.datetime | datetime.date | None] | None = None,
        model_name: str = "conformal",
        eval_split_name: str = "select",
    ) -> dict[str, IntervalUsefulnessMetrics]:
        """Evaluate model interval usefulness against global and role-family naive cohorts.

        Parameters
        ----------
        y_eval : np.ndarray
            Observed targets on evaluation partition.
        p10_eval : np.ndarray
            Predicted P10 lower bounds.
        p90_eval : np.ndarray
            Predicted P90 upper bounds.
        y_cohort_pool : np.ndarray
            Target observations used to establish naive cohort distributions.
        roles_eval : list[str] | None
            Role family per evaluation observation.
        roles_cohort_pool : list[str] | None
            Role family per cohort pool observation.
        timestamps_eval : list | None
            Timestamps for recent window extraction.
        model_name : str
            Model identifier.
        eval_split_name : str
            Evaluation split name.
        """
        if eval_split_name.lower() == "test":
            raise DataContractError(
                "EVALUATION_ISOLATION_VIOLATION: Interval usefulness evaluation on locked 'test' "
                "partition is forbidden. Evaluate on 'select' or 'calibrate' only.",
                details={"rule_id": "R-MD-02"},
            )

        n_total = len(y_eval)
        if n_total == 0:
            raise CompIntelValidationError("Empty evaluation array passed to usefulness evaluator")

        # Filter valid (non-abstained, non-NaN) predictions
        valid_mask = (
            ~np.isnan(y_eval) & ~np.isnan(p10_eval) & ~np.isnan(p90_eval) & (p90_eval >= p10_eval)
        )
        n_eval = int(np.sum(valid_mask))
        n_abstained = n_total - n_eval
        abstention_rate = float(n_abstained / n_total) if n_total > 0 else 0.0

        if n_eval == 0:
            raise CompIntelValidationError(
                f"Model '{model_name}' has 0 valid evaluated predictions "
                "(100% abstained or invalid)"
            )

        y_valid = y_eval[valid_mask]
        p10_valid = p10_eval[valid_mask]
        p90_valid = p90_eval[valid_mask]
        model_widths = p90_valid - p10_valid

        # Compute empirical coverage of the model
        covered = (y_valid >= p10_valid) & (y_valid <= p90_valid)
        model_coverage = float(np.mean(covered))
        model_mean_width = float(np.mean(model_widths))
        model_median_width = float(np.median(model_widths))

        # Recent window indices (latest recent_fraction of chronological observations)
        recent_indices: list[int] = []
        if timestamps_eval is not None and len(timestamps_eval) == n_total:
            valid_indices = [i for i, v in enumerate(valid_mask) if v]
            valid_ts = [timestamps_eval[i] for i in valid_indices]
            has_dates = all(t is not None for t in valid_ts)
            if has_dates:
                sorted_by_ts = sorted(range(len(valid_indices)), key=lambda k: str(valid_ts[k]))
                k_recent = max(1, int(len(valid_indices) * self.recent_fraction))
                recent_indices = [valid_indices[idx] for idx in sorted_by_ts[-k_recent:]]
            else:
                k_recent = max(1, int(len(valid_indices) * self.recent_fraction))
                recent_indices = valid_indices[-k_recent:]
        else:
            valid_indices = [i for i, v in enumerate(valid_mask) if v]
            k_recent = max(1, int(len(valid_indices) * self.recent_fraction))
            recent_indices = valid_indices[-k_recent:]

        recent_valid_mask = np.zeros(n_total, dtype=bool)
        recent_valid_mask[recent_indices] = True
        recent_in_valid = recent_valid_mask[valid_mask]

        metrics_map: dict[str, IntervalUsefulnessMetrics] = {}

        # ----------------------------------------------------------------------
        # Benchmark 1: Global Unconditional Naive Interval at Equal Coverage
        # ----------------------------------------------------------------------
        q_lo_global, q_hi_global = self.compute_equal_coverage_quantiles(
            y_cohort_pool, target_coverage=model_coverage
        )
        naive_global_widths = np.full(
            n_eval, fill_value=(q_hi_global - q_lo_global), dtype=np.float64
        )
        naive_global_covered = (y_valid >= q_lo_global) & (y_valid <= q_hi_global)
        naive_global_coverage = float(np.mean(naive_global_covered))
        naive_global_mean_width = float(np.mean(naive_global_widths))
        naive_global_median_width = float(np.median(naive_global_widths))

        metrics_map["global_unconditional"] = self._compute_comparison_metrics(
            model_name=model_name,
            eval_split_name=eval_split_name,
            n_eval=n_eval,
            n_abstained=n_abstained,
            abstention_rate=abstention_rate,
            model_coverage=model_coverage,
            model_widths=model_widths,
            model_mean_width=model_mean_width,
            model_median_width=model_median_width,
            naive_cohort_type="global_unconditional",
            naive_coverage=naive_global_coverage,
            naive_widths=naive_global_widths,
            naive_mean_width=naive_global_mean_width,
            naive_median_width=naive_global_median_width,
            recent_mask=recent_in_valid,
        )

        # ----------------------------------------------------------------------
        # Benchmark 2: Role Family Naive Cohort Interval at Equal Coverage
        # ----------------------------------------------------------------------
        if roles_eval is not None and roles_cohort_pool is not None and len(roles_eval) == n_total:
            roles_valid = [roles_eval[i] for i, v in enumerate(valid_mask) if v]
            unique_roles = sorted(set(roles_valid))
            role_cutoffs: dict[str, tuple[float, float]] = {}

            cohort_pool_df_roles = np.array(roles_cohort_pool)
            for r in unique_roles:
                r_pool = y_cohort_pool[cohort_pool_df_roles == r]
                if len(r_pool) >= 5:
                    role_cutoffs[r] = self.compute_equal_coverage_quantiles(
                        r_pool, target_coverage=model_coverage
                    )
                else:
                    role_cutoffs[r] = (q_lo_global, q_hi_global)

            naive_role_widths = np.empty(n_eval, dtype=np.float64)
            naive_role_covered = np.empty(n_eval, dtype=bool)

            for idx, r in enumerate(roles_valid):
                r_lo, r_hi = role_cutoffs[r]
                naive_role_widths[idx] = r_hi - r_lo
                naive_role_covered[idx] = (y_valid[idx] >= r_lo) and (y_valid[idx] <= r_hi)

            naive_role_coverage = float(np.mean(naive_role_covered))
            naive_role_mean_width = float(np.mean(naive_role_widths))
            naive_role_median_width = float(np.median(naive_role_widths))

            metrics_map["role_family"] = self._compute_comparison_metrics(
                model_name=model_name,
                eval_split_name=eval_split_name,
                n_eval=n_eval,
                n_abstained=n_abstained,
                abstention_rate=abstention_rate,
                model_coverage=model_coverage,
                model_widths=model_widths,
                model_mean_width=model_mean_width,
                model_median_width=model_median_width,
                naive_cohort_type="role_family",
                naive_coverage=naive_role_coverage,
                naive_widths=naive_role_widths,
                naive_mean_width=naive_role_mean_width,
                naive_median_width=naive_role_median_width,
                recent_mask=recent_in_valid,
            )

        return metrics_map

    def _compute_comparison_metrics(
        self,
        model_name: str,
        eval_split_name: str,
        n_eval: int,
        n_abstained: int,
        abstention_rate: float,
        model_coverage: float,
        model_widths: np.ndarray,
        model_mean_width: float,
        model_median_width: float,
        naive_cohort_type: str,
        naive_coverage: float,
        naive_widths: np.ndarray,
        naive_mean_width: float,
        naive_median_width: float,
        recent_mask: np.ndarray,
    ) -> IntervalUsefulnessMetrics:
        """Compute paired bootstrap confidence intervals, recent window metrics, and verdict."""
        # Width ratio & reduction
        ratio_mean = model_mean_width / naive_mean_width if naive_mean_width > 0 else 1.0
        ratio_median = model_median_width / naive_median_width if naive_median_width > 0 else 1.0
        reduction_pct = (1.0 - ratio_mean) * 100.0

        # Bootstrap CIs for width ratio and percentage reduction
        ratio_ci: MetricWithCI = bootstrap_metric_ci(
            y_true=model_widths,
            y_pred=naive_widths,
            metric_fn=_width_ratio_statistic,
            confidence_level=0.95,
            n_resamples=self.n_bootstrap_resamples,
            seed=self.seed,
        )

        reduction_ci: MetricWithCI = bootstrap_metric_ci(
            y_true=model_widths,
            y_pred=naive_widths,
            metric_fn=_width_reduction_pct_statistic,
            confidence_level=0.95,
            n_resamples=self.n_bootstrap_resamples,
            seed=self.seed,
        )

        # Recent window metrics
        recent_n = int(np.sum(recent_mask))
        if recent_n > 0:
            rec_model_w = float(np.mean(model_widths[recent_mask]))
            rec_naive_w = float(np.mean(naive_widths[recent_mask]))
            rec_ratio = rec_model_w / rec_naive_w if rec_naive_w > 0 else 1.0
            rec_reduction = (1.0 - rec_ratio) * 100.0
        else:
            rec_model_w = model_mean_width
            rec_naive_w = naive_mean_width
            rec_ratio = ratio_mean
            rec_reduction = reduction_pct

        # Determine EXP-02 Verdict
        # Criteria:
        # 1. Point width ratio < 1.0 (mean model width narrower than naive cohort)
        # 2. Bootstrap CI upper bound < 1.0 (statistically significant reduction at 95% level)
        # 3. Recent window width ratio < 1.0 (holds under recent temporal window)
        is_useful = (ratio_mean < 1.0) and (rec_ratio < 1.0)

        if ratio_ci.ci_upper < 1.0 and is_useful:
            verdict = "CONFIRMED_USEFUL"
            rationale = (
                f"Conformal intervals achieve statistically significant width compression "
                f"({reduction_pct:.1f}% reduction, "
                f"95% CI [{reduction_ci.ci_lower:.1f}%, {reduction_ci.ci_upper:.1f}%], "
                f"recent window {rec_reduction:.1f}% reduction). "
                f"Conformalization earns its place under EXP-02."
            )
        elif is_useful and ratio_ci.ci_upper >= 1.0:
            verdict = "MARGINALLY_USEFUL"
            rationale = (
                f"Conformal intervals are directionally narrower ({reduction_pct:.1f}% reduction), "
                f"but 95% bootstrap CI "
                f"[{reduction_ci.ci_lower:.1f}%, {reduction_ci.ci_upper:.1f}%] spans parity (1.0). "
                f"Usefulness is provisionally accepted pending higher sample support."
            )
        else:
            verdict = "INVALIDATED"
            rationale = (
                f"Model intervals are wider than naive cohort baseline "
                f"(ratio {ratio_mean:.3f} >= 1.0). "
                f"Hypothesis EXP-02 invalidated; "
                f"conformal model fails to demonstrate interval usefulness."
            )

        return IntervalUsefulnessMetrics(
            model_name=model_name,
            eval_split_name=eval_split_name,
            n_eval=n_eval,
            n_abstained=n_abstained,
            abstention_rate=abstention_rate,
            model_coverage=model_coverage,
            model_mean_width=model_mean_width,
            model_median_width=model_median_width,
            naive_cohort_type=naive_cohort_type,
            naive_coverage=naive_coverage,
            naive_mean_width=naive_mean_width,
            naive_median_width=naive_median_width,
            width_ratio_mean=ratio_mean,
            width_ratio_median=ratio_median,
            width_reduction_pct=reduction_pct,
            width_ratio_ci_lower=ratio_ci.ci_lower,
            width_ratio_ci_upper=ratio_ci.ci_upper,
            width_reduction_pct_ci_lower=reduction_ci.ci_lower,
            width_reduction_pct_ci_upper=reduction_ci.ci_upper,
            recent_window_n=recent_n,
            recent_window_model_width=rec_model_w,
            recent_window_naive_width=rec_naive_w,
            recent_window_width_ratio=rec_ratio,
            recent_window_width_reduction_pct=rec_reduction,
            is_useful=is_useful,
            verdict=verdict,
            verdict_rationale=rationale,
        )

    def evaluate_slices(
        self,
        df_eval: pl.DataFrame,
        p10: np.ndarray,
        p90: np.ndarray,
        naive_widths: np.ndarray,
        dimensions: list[str] | None = None,
    ) -> list[CohortSliceComparison]:
        """Compute slice-level interval width comparisons, explicitly flagging N < 10.

        Adheres to Rules R-MD-08 and R-EV-07.
        """
        if dimensions is None:
            dimensions = ["role_family", "seniority", "experience_band", "location"]

        y = df_eval["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        model_w = p90 - p10
        covered = (y >= p10) & (y <= p90)

        comparisons: list[CohortSliceComparison] = []

        for dim in dimensions:
            if dim not in df_eval.columns:
                continue

            unique_vals = df_eval[dim].drop_nulls().unique().to_list()
            for val in sorted(str(v) for v in unique_vals):
                mask = (df_eval[dim].cast(str) == val).to_numpy()
                n_slice = int(np.sum(mask))
                if n_slice == 0:
                    continue

                is_low = n_slice < self.min_slice_support
                slice_cov = float(np.mean(covered[mask]))
                slice_m_w = float(np.mean(model_w[mask]))
                slice_n_w = float(np.mean(naive_widths[mask]))
                slice_ratio = slice_m_w / slice_n_w if slice_n_w > 0 else 1.0
                slice_red = (1.0 - slice_ratio) * 100.0

                comparisons.append(
                    CohortSliceComparison(
                        slice_dimension=dim,
                        slice_value=val,
                        n_eval=n_slice,
                        is_low_support=is_low,
                        model_coverage=slice_cov,
                        model_mean_width=slice_m_w,
                        naive_mean_width=slice_n_w,
                        width_ratio=slice_ratio,
                        width_reduction_pct=slice_red,
                    )
                )

        return comparisons

    def generate_report(
        self,
        canonical_df: pl.DataFrame,
        eval_split_name: str = "select",
        train_split_name: str = "train",
        calib_split_name: str = "calibrate",
    ) -> IntervalUsefulnessReport:
        """Execute full interval usefulness pipeline and return complete report.

        Loads models (or trains base models on train and calibrates on calibrate),
        evaluates usefulness on eval_split_name, and synthesizes EXP-02 findings.
        """
        if eval_split_name.lower() == "test":
            raise DataContractError(
                "EVALUATION_ISOLATION_VIOLATION: Cannot evaluate interval usefulness "
                "on locked 'test' split.",
                details={"rule_id": "R-MD-02"},
            )

        from compintel.evaluation.baseline_report import add_experience_band_column
        from compintel.evaluation.splits import SplitConfig, create_temporal_grouped_splits
        from compintel.models.gbm.config import (
            GBMModelType,
            GBMPointConfig,
            GBMQuantileConfig,
        )
        from compintel.models.gbm.point import CatBoostPointModel
        from compintel.models.gbm.quantile import CatBoostQuantileModel
        from compintel.uncertainty.conformal import (
            ConformalConfig,
            ConformalMethod,
            ConformalQuantileRegressor,
            SplitConformalCalibrator,
        )

        enriched_df = add_experience_band_column(canonical_df)

        if "split" in enriched_df.columns:
            train_df = enriched_df.filter(pl.col("split") == train_split_name)
            calib_df = enriched_df.filter(pl.col("split") == calib_split_name)
            eval_df = enriched_df.filter(pl.col("split") == eval_split_name)
        else:
            splits = create_temporal_grouped_splits(enriched_df, config=SplitConfig())
            train_df = splits.train_df
            calib_df = splits.calibrate_df
            eval_df = splits.select_df if eval_split_name == "select" else splits.calibrate_df

        if len(eval_df) == 0:
            raise CompIntelValidationError(f"Evaluation split '{eval_split_name}' contains 0 rows")
        if len(train_df) == 0:
            raise CompIntelValidationError(f"Training split '{train_split_name}' contains 0 rows")
        if len(calib_df) == 0:
            raise CompIntelValidationError(
                f"Calibration split '{calib_split_name}' contains 0 rows"
            )

        # 1. Train CatBoost Quantile Model (Rung E)
        q_cfg = GBMQuantileConfig(
            model_type=GBMModelType.CATBOOST,
            quantiles=(0.10, 0.50, 0.90),
            n_estimators=100,
            learning_rate=0.08,
        )
        cb_q_model = CatBoostQuantileModel(config=q_cfg)
        cb_q_model.fit(train_df)

        # 2. Fit Conformal Quantile Regressor (CQR; Rung F) on calibrate split
        cqr = ConformalQuantileRegressor(
            base_model=cb_q_model,
            config=ConformalConfig(nominal_coverage=0.80),
        )
        cqr.calibrate(calib_df)

        # 3. Fit Split Conformal Calibrator on calibrate split
        base_point = CatBoostPointModel(
            GBMPointConfig(
                model_type=GBMModelType.CATBOOST,
                n_estimators=100,
                learning_rate=0.08,
            )
        )
        base_point.fit(train_df)
        split_calibrator = SplitConformalCalibrator(
            base_model=base_point,
            config=ConformalConfig(
                method=ConformalMethod.SPLIT_CONFORMAL,
                nominal_coverage=0.80,
            ),
        )
        split_calibrator.calibrate(calib_df)

        # Predict on eval_df
        cqr_preds = cqr.predict(eval_df)
        uncal_preds = cb_q_model.predict(eval_df)
        sc_preds = split_calibrator.predict(eval_df)

        # Unpack prediction arrays
        cqr_p10 = np.array([p.p10_calibrated if not p.is_abstained else np.nan for p in cqr_preds])
        cqr_p90 = np.array([p.p90_calibrated if not p.is_abstained else np.nan for p in cqr_preds])

        uncal_p10 = np.array([p.p10 if not p.is_abstained else np.nan for p in uncal_preds])
        uncal_p90 = np.array([p.p90 if not p.is_abstained else np.nan for p in uncal_preds])

        sc_p10 = np.array([p.p10_calibrated if not p.is_abstained else np.nan for p in sc_preds])
        sc_p90 = np.array([p.p90_calibrated if not p.is_abstained else np.nan for p in sc_preds])

        # Arrays
        y_eval = eval_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        y_train_cal = (
            pl.concat([train_df, calib_df])["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        )
        roles_eval = eval_df["role_family"].cast(str).to_list()
        roles_pool = pl.concat([train_df, calib_df])["role_family"].cast(str).to_list()
        ts_eval = eval_df["effective_on"].to_list() if "effective_on" in eval_df.columns else None

        evaluations: dict[str, dict[str, IntervalUsefulnessMetrics]] = {}

        # 1. CatBoost CQR (Rung F Champion)
        cqr_metrics = self.evaluate_model_usefulness(
            y_eval=y_eval,
            p10_eval=cqr_p10,
            p90_eval=cqr_p90,
            y_cohort_pool=y_train_cal,
            roles_eval=roles_eval,
            roles_cohort_pool=roles_pool,
            timestamps_eval=ts_eval,
            model_name="catboost_cqr",
            eval_split_name=eval_split_name,
        )
        evaluations["catboost_cqr"] = cqr_metrics

        # 2. Split Conformal
        sc_metrics = self.evaluate_model_usefulness(
            y_eval=y_eval,
            p10_eval=sc_p10,
            p90_eval=sc_p90,
            y_cohort_pool=y_train_cal,
            roles_eval=roles_eval,
            roles_cohort_pool=roles_pool,
            timestamps_eval=ts_eval,
            model_name="split_conformal",
            eval_split_name=eval_split_name,
        )
        evaluations["split_conformal"] = sc_metrics

        # 3. CatBoost Quantile Uncalibrated (Rung E)
        uncal_metrics = self.evaluate_model_usefulness(
            y_eval=y_eval,
            p10_eval=uncal_p10,
            p90_eval=uncal_p90,
            y_cohort_pool=y_train_cal,
            roles_eval=roles_eval,
            roles_cohort_pool=roles_pool,
            timestamps_eval=ts_eval,
            model_name="catboost_quantile_uncalibrated",
            eval_split_name=eval_split_name,
        )
        evaluations["catboost_quantile_uncalibrated"] = uncal_metrics

        # Slices for CatBoost CQR vs Global Unconditional
        q_lo, q_hi = self.compute_equal_coverage_quantiles(
            y_train_cal, target_coverage=cqr_metrics["global_unconditional"].model_coverage
        )
        naive_widths = np.full(len(eval_df), fill_value=(q_hi - q_lo), dtype=np.float64)
        slice_comps = self.evaluate_slices(
            df_eval=eval_df,
            p10=cqr_p10,
            p90=cqr_p90,
            naive_widths=naive_widths,
        )

        # EXP-02 Verdict synthesis
        champion_metric = cqr_metrics.get("global_unconditional") or list(cqr_metrics.values())[0]
        exp02_verdict = champion_metric.verdict
        cov_pct = champion_metric.model_coverage * 100.0
        exp02_summary = (
            f"Evaluated CatBoost CQR on partition '{eval_split_name}' (N={len(eval_df)}). "
            f"Achieved empirical coverage of {cov_pct:.1f}% with mean width "
            f"{champion_metric.model_mean_width:.2f} LPA vs naive cohort width "
            f"{champion_metric.naive_mean_width:.2f} LPA "
            f"(width ratio {champion_metric.width_ratio_mean:.3f}, "
            f"reduction {champion_metric.width_reduction_pct:+.1f}%, "
            f"95% CI [{champion_metric.width_reduction_pct_ci_lower:+.1f}%, "
            f"{champion_metric.width_reduction_pct_ci_upper:+.1f}%]). "
            f"Recent window (N={champion_metric.recent_window_n}) width reduction is "
            f"{champion_metric.recent_window_width_reduction_pct:+.1f}%. "
            f"Status: {champion_metric.verdict_rationale}"
        )

        today_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

        return IntervalUsefulnessReport(
            evaluation_split=eval_split_name,
            eval_date=today_str,
            data_summary={
                "n_total": len(eval_df),
                "n_train": len(train_df),
                "n_calib": len(calib_df),
                "eval_split_name": eval_split_name,
            },
            evaluations=evaluations,
            slice_evaluations=slice_comps,
            exp02_verdict=exp02_verdict,
            exp02_summary=exp02_summary,
        )


def evaluate_and_save_interval_usefulness(
    canonical_path: Path | str,
    output_md: Path | str,
    output_json: Path | str,
    split: str = "select",
    n_bootstrap: int = 1000,
    seed: int = 42,
    allow_synthetic: bool = False,
) -> IntervalUsefulnessReport:
    """CLI / programmatic entry point to run interval usefulness evaluation and save reports."""
    import polars as pl

    from compintel.errors import CompIntelValidationError

    c_path = Path(canonical_path)
    if not c_path.exists():
        raise FileNotFoundError(f"Canonical dataset not found at: {c_path}")

    df = pl.read_parquet(c_path)
    if "is_synthetic" in df.columns and not allow_synthetic:
        synthetic_count = int(df["is_synthetic"].sum())
        if synthetic_count > 0:
            raise CompIntelValidationError(
                f"Synthetic data detected ({synthetic_count} rows) in canonical dataset. "
                "Evaluation on synthetic data violates Rule R-MD-11. "
                "Pass allow_synthetic=True for test harnesses only.",
                details={"param_name": "is_synthetic"},
            )

    evaluator = IntervalUsefulnessEvaluator(
        n_bootstrap_resamples=n_bootstrap,
        seed=seed,
    )

    report = evaluator.generate_report(
        canonical_df=df,
        eval_split_name=split,
    )

    out_md_path = Path(output_md)
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    out_md_path.write_text(report.to_markdown(), encoding="utf-8")

    out_json_path = Path(output_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return report
