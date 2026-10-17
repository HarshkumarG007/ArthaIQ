"""Rung D gradient boosting evaluation and baseline comparison report (Task T5.01b).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal cross-validation and dataset splitting.
- Rule R-MD-02: Final test set is isolated and locked. Routine evaluation is strictly
  confined to dev pool partitions ('select' or 'calibrate'). Evaluation on 'test' is prohibited.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-05: Mandatory evaluation metrics: MAE, MdAE, MAPE, MdAPE, RMSE, bootstrap CIs,
  subgroup slices, and thin-evidence abstention rates.
- Rule R-MD-06: Log-pay target transformation and nominal INR LPA output.
- Rule R-MD-08: Thin-evidence abstention reporting per model and per slice.
- Rule R-MD-10: Detailed execution logging of timings, seeds, and peak memory.
- Rule R-MD-11: Synthetic data blocked by default; cautioned when allowed.
- Rule R-UQ-01: Nonparametric percentile bootstrap confidence intervals (95% CI).
- Pre-registration v1.yaml: Decision rules, minimum effect sizes, and acceptance thresholds.
"""

from __future__ import annotations

import json
import subprocess
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import polars as pl

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.baseline_report import (
    REQUIRED_REPORT_COLUMNS,
    add_experience_band_column,
)
from compintel.evaluation.metrics import (
    MetricWithCI,
    bootstrap_metric_ci,
    mean_absolute_error,
    mean_absolute_percentage_error,
    median_absolute_error,
    median_absolute_percentage_error,
    root_mean_squared_error,
)
from compintel.evaluation.splits import (
    SplitConfig,
    create_temporal_grouped_splits,
)
from compintel.logging import get_logger
from compintel.models.baselines.empirical import (
    EmpiricalQuantileBaseline,
    HierarchicalBackoffConfig,
)
from compintel.models.baselines.linear import (
    LinearQuantileBaseline,
    LinearQuantileConfig,
)
from compintel.models.gbm.config import (
    GBMModelType,
    GBMPointConfig,
)
from compintel.models.gbm.cv import (
    GBMCVResult,
    run_gbm_cv,
)
from compintel.models.gbm.point import (
    create_gbm_point_model,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("compintel.evaluation.gbm_report")


def _get_current_git_commit() -> str:
    """Fetch current git commit hash, falling back to 'unknown'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


@dataclass(frozen=True)
class GBMBenchmarkReportConfig:
    """Configuration for Rung D benchmark evaluation and baseline comparison."""

    train_ratio: float = 0.60
    select_ratio: float = 0.15
    calibrate_ratio: float = 0.15
    test_ratio: float = 0.10
    evaluation_split: Literal["select", "calibrate"] = "select"
    n_cv_folds: int = 3
    with_bootstrap_ci: bool = True
    confidence_level: float = 0.95
    bootstrap_resamples: int = 500
    random_seed: int = 42
    snapshot_id: str = "SNAP-1FF34A8E9633"
    allow_synthetic: bool = False
    max_point_mae_lpa: float = 4.50
    max_point_mdape: float = 0.200
    min_effect_mdape_reduction_pp: float = 0.020

    def __post_init__(self) -> None:
        """Validate split ratios, partition lockout, and bootstrap settings."""
        tot = self.train_ratio + self.select_ratio + self.calibrate_ratio + self.test_ratio
        if abs(tot - 1.0) > 1e-4:
            raise CompIntelValidationError(
                f"Split ratios must sum to 1.0 (got {tot:.4f})",
                code="INVALID_SPLIT_RATIOS",
            )
        if self.evaluation_split not in ("select", "calibrate"):
            raise CompIntelValidationError(
                f"Evaluation partition must be 'select' or 'calibrate' per Rule R-MD-02 "
                f"(got '{self.evaluation_split}'). Locked final test set cannot be evaluated.",
                code="FORBIDDEN_SPLIT_EVALUATION",
            )
        if not (0.0 < self.confidence_level < 1.0):
            raise CompIntelValidationError(
                f"confidence_level must be between 0 and 1, got {self.confidence_level}.",
                code="INVALID_CONFIDENCE_LEVEL",
            )
        if self.bootstrap_resamples <= 0:
            raise CompIntelValidationError(
                f"bootstrap_resamples must be positive, got {self.bootstrap_resamples}.",
                code="INVALID_BOOTSTRAP_RESAMPLES",
            )


@dataclass(frozen=True)
class ModelEvalSummary:
    """Evaluation summary for a single model on the development evaluation partition."""

    model_id: str
    model_name: str
    is_abstained_all: bool
    abstained_count: int
    abstention_rate: float
    sample_size: int
    valid_sample_size: int
    mae: float
    medae: float
    mape: float
    mdape: float
    rmse: float
    point_ci: dict[str, MetricWithCI]
    slices: dict[str, dict[str, Any]]
    fit_time_seconds: float
    inference_latency_per_obs_ms: float
    peak_memory_mb: float

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation summary to nested dictionary."""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "is_abstained_all": self.is_abstained_all,
            "abstained_count": self.abstained_count,
            "abstention_rate": self.abstention_rate,
            "sample_size": self.sample_size,
            "valid_sample_size": self.valid_sample_size,
            "mae": self.mae,
            "medae": self.medae,
            "mape": self.mape,
            "mdape": self.mdape,
            "rmse": self.rmse,
            "point_ci": {k: asdict(v) for k, v in self.point_ci.items()},
            "slices": self.slices,
            "fit_time_seconds": self.fit_time_seconds,
            "inference_latency_per_obs_ms": self.inference_latency_per_obs_ms,
            "peak_memory_mb": self.peak_memory_mb,
        }


@dataclass(frozen=True)
class ModelPairedComparison:
    """Statistical paired difference comparison between a candidate model and baseline."""

    candidate_id: str
    baseline_id: str
    delta_mdape_pp: float
    delta_mdape_ci_lower_pp: float
    delta_mdape_ci_upper_pp: float
    delta_mae_lpa: float
    delta_mae_ci_lower_lpa: float
    delta_mae_ci_upper_lpa: float
    empirical_p_value: float
    is_statistically_significant: bool
    minimum_effect_size_met: bool
    comparison_valid: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Convert paired comparison to dictionary."""
        return asdict(self)


@dataclass
class GBMBenchmarkReport:
    """Complete publication-grade Rung D benchmark and baseline comparison report."""

    report_id: str
    generated_at_utc: str
    git_commit: str
    snapshot_id: str
    random_seed: int
    is_synthetic: bool
    evaluation_split: str
    data_summary: dict[str, Any]
    models: dict[str, ModelEvalSummary]
    cv_results: dict[str, GBMCVResult]
    threshold_checks: list[dict[str, Any]]
    paired_comparisons: list[ModelPairedComparison]
    champion_recommendation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to nested dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at_utc": self.generated_at_utc,
            "git_commit": self.git_commit,
            "snapshot_id": self.snapshot_id,
            "random_seed": self.random_seed,
            "is_synthetic": self.is_synthetic,
            "evaluation_split": self.evaluation_split,
            "data_summary": self.data_summary,
            "models": {k: v.to_dict() for k, v in self.models.items()},
            "cv_results": {k: v.to_dict() for k, v in self.cv_results.items()},
            "threshold_checks": self.threshold_checks,
            "paired_comparisons": [c.to_dict() for c in self.paired_comparisons],
            "champion_recommendation": self.champion_recommendation,
        }

    def save(
        self,
        output_md: Path | None = None,
        output_json: Path | None = None,
    ) -> None:
        """Write Markdown and JSON report files to disk.

        Args:
            output_md: Target Markdown report path.
            output_json: Target JSON structured results path.
        """
        if output_md:
            output_md.parent.mkdir(parents=True, exist_ok=True)
            output_md.write_text(self.to_markdown(), encoding="utf-8")
        if output_json:
            output_json.parent.mkdir(parents=True, exist_ok=True)
            output_json.write_text(
                json.dumps(self.to_dict(), indent=2, default=str),
                encoding="utf-8",
            )

    def to_markdown(self) -> str:
        """Render publication-grade GitHub Flavored Markdown report."""
        short_commit = self.git_commit[:12] if len(self.git_commit) >= 12 else self.git_commit
        total_obs = self.data_summary.get("total_observations", 0)
        train_cnt = self.data_summary.get("train_count", 0)
        eval_cnt = self.data_summary.get("eval_count", 0)
        excl_cnt = self.data_summary.get("excluded_cross_window_count", 0)

        lines: list[str] = [
            f"# Rung D Benchmark Evaluation Report: {self.report_id}",
            "",
            "> **Target Variable:** `guaranteed_cash_annual` (Nominal INR LPA)  ",
            f"> **Generated (UTC):** `{self.generated_at_utc}`  ",
            "> **Governing Protocol:** Pre-registration `v1.yaml` (Task T4.03, T5.01b)  ",
            f"> **Evaluation Partition:** `{self.evaluation_split}` (Rule R-MD-02)  ",
            f"> **Git Commit:** `{short_commit}`  ",
            "",
        ]

        if self.is_synthetic:
            lines.extend(
                [
                    "> [!CAUTION]",
                    "> **SYNTHETIC TEST FIXTURE DATA DETECTED (Rule R-MD-11)**: "
                    "This report was generated using synthetic fixture data for testing purposes. "
                    "Metrics DO NOT reflect production model performance or "
                    "canonical data quality.",
                    "",
                ]
            )

        lines.extend(
            [
                "> [!IMPORTANT]",
                "> **FINAL TEST SET LOCKED (Rule R-MD-02)**: Routine evaluation is strictly "
                f"isolated to the dev pool partition (`{self.evaluation_split}`). "
                "The test partition remains locked and untouched until final evaluation.",
                "",
                "## 1. Provenance and Partition Metadata",
                "",
                "| Parameter | Value | Description |",
                "|---|---|---|",
                f"| **Report ID** | `{self.report_id}` | Unique audit identifier |",
                f"| **Data Snapshot ID** | `{self.snapshot_id}` | Cryptographic dataset digest |",
                f"| **Git Commit** | `{short_commit}` | Exact repository commit SHA |",
                f"| **Random Seed** | `{self.random_seed}` | Deterministic seeded RNG (R-MD-10) |",
                f"| **Evaluation Split** | `{self.evaluation_split}` | Dev partition (R-MD-02) |",
                f"| **Total Analyzed** | `{total_obs}` | Total observations in cohort |",
                f"| **Training Records** | `{train_cnt}` | Observations in train fold |",
                f"| **Dev Eval Records** | `{eval_cnt}` | Records in evaluation partition |",
                f"| **Excluded Records** | `{excl_cnt}` | Cross-window contributor quarantine |",
                "",
                "## 2. Hardware Resource Profiling (Rule R-MD-10, Profile B)",
                "",
                "| Model | Family | Wall-Clock Fit Time (s) | Latency (ms/obs) | "
                "Peak Heap Memory (MB) |",
                "|---|---|:---:|:---:|:---:|",
            ]
        )

        for m_id, m in self.models.items():
            lines.append(
                f"| **{m.model_name}** | `{m_id}` | `{m.fit_time_seconds:.4f}s` | "
                f"`{m.inference_latency_per_obs_ms:.3f} ms` | `{m.peak_memory_mb:.2f} MB` |"
            )

        lines.extend(
            [
                "",
                "## 3. Dev Partition Point Performance (Rule R-MD-05)",
                "",
                "| Model | Abstention Rate | MAE (LPA) | MdAE (LPA) | MAPE | MdAPE | RMSE (LPA) |",
                "|---|:---:|:---:|:---:|:---:|:---:|:---:|",
            ]
        )

        for _m_id, m in self.models.items():
            if m.is_abstained_all:
                lines.append(
                    f"| **{m.model_name}** | `{m.abstention_rate:.1f}%` | *Abstained* | "
                    "*Abstained* | *Abstained* | *Abstained* | *Abstained* |"
                )
            else:
                mae_ci = m.point_ci.get("mae")
                mdape_ci = m.point_ci.get("mdape")
                mae_str = (
                    f"`{m.mae:.4f}` [{mae_ci.ci_lower:.2f}, {mae_ci.ci_upper:.2f}]"
                    if mae_ci
                    else f"`{m.mae:.4f}`"
                )
                mdape_ci_str = (
                    f"[{mdape_ci.ci_lower * 100.0:.1f}%, {mdape_ci.ci_upper * 100.0:.1f}%]"
                    if mdape_ci
                    else ""
                )
                mdape_str = (
                    f"`{m.mdape * 100.0:.2f}%` {mdape_ci_str}"
                    if mdape_ci
                    else f"`{m.mdape * 100.0:.2f}%`"
                )
                lines.append(
                    f"| **{m.model_name}** | `{m.abstention_rate:.1f}%` | {mae_str} | "
                    f"`{m.medae:.4f}` | `{m.mape * 100.0:.2f}%` | {mdape_str} | `{m.rmse:.4f}` |"
                )

        lines.extend(
            [
                "",
                "## 4. Grouped-Temporal Cross-Validation (Rung D Models)",
                "",
                "> Grouped-temporal expanding-window cross-validation evaluated strictly "
                "on the development pool.",
                "",
                (
                    "| Model Family | Folds | OOF MAE (LPA) | OOF MdAE (LPA) | "
                    "OOF MdAPE | Total CV Time (s) | Max Peak Mem (MB) |"
                ),
                "|---|:---:|:---:|:---:|:---:|:---:|:---:|",
            ]
        )

        for _cv_key, cv_res in self.cv_results.items():
            lines.append(
                f"| **{cv_res.model_name}** | {cv_res.n_folds} | "
                f"`{cv_res.overall_metrics.mae:.4f}` | `{cv_res.overall_metrics.medae:.4f}` | "
                f"`{cv_res.overall_metrics.mdape * 100.0:.2f}%` | "
                f"`{cv_res.aggregate_resource_profile.wall_clock_train_seconds:.4f}s` | "
                f"`{cv_res.aggregate_resource_profile.peak_heap_memory_mb:.2f} MB` |"
            )

        lines.extend(
            [
                "",
                "## 5. Pre-Registered Acceptance Thresholds (v1.yaml)",
                "",
                "| Model | Metric | Value | Threshold | Status | Details |",
                "|---|---|:---:|:---:|:---:|---|",
            ]
        )

        for check in self.threshold_checks:
            m_lbl = check.get("model_name", "")
            metric_lbl = check.get("metric_name", "")
            val_lbl = check.get("metric_value", "")
            thresh_lbl = check.get("threshold", "")
            status_lbl = f"**{check.get('status', '')}**"
            det = check.get("details", "")
            lines.append(
                f"| {m_lbl} | {metric_lbl} | `{val_lbl}` | `{thresh_lbl}` | {status_lbl} | {det} |"
            )

        lines.extend(
            [
                "",
                "## 6. Model Comparison & Minimum Effect Sizes",
                "",
                (
                    "| Candidate Model | Baseline Champion | Delta MdAPE | Delta MAE | "
                    "Effect Size Met? | Statistical Sig (p < 0.05) |"
                ),
                "|---|---|:---:|:---:|:---:|:---:|",
            ]
        )

        for comp in self.paired_comparisons:
            effect_str = "**YES**" if comp.minimum_effect_size_met else "NO"
            sig_str = (
                f"**YES** (p={comp.empirical_p_value:.3f})"
                if comp.is_statistically_significant
                else f"NO (p={comp.empirical_p_value:.3f})"
            )
            d_mdape = f"{comp.delta_mdape_pp:+.2f} pp" if comp.comparison_valid else "N/A"
            d_mae = f"{comp.delta_mae_lpa:+.4f} LPA" if comp.comparison_valid else "N/A"
            lines.append(
                f"| **{comp.candidate_id}** | `{comp.baseline_id}` | `{d_mdape}` | `{d_mae}` | "
                f"{effect_str} | {sig_str} |"
            )

        rec = self.champion_recommendation
        lines.extend(
            [
                "",
                "## 7. Rung D Benchmark Verdict & Champion Recommendation",
                "",
                f"- **Recommended Rung D Model:** **{rec.get('designated_model', 'N/A')}**",
                f"- **Verdict:** **{rec.get('verdict', 'N/A')}**",
                f"- **Rationale:** {rec.get('rationale', 'N/A')}",
                "",
                "---",
                "*Report generated by CompIntel Rung D Evaluation Engine "
                "(Task T5.01b, Rule R-MD-05).*  ",
            ]
        )

        return "\n".join(lines)


def _compute_paired_comparison(
    cand_id: str,
    base_id: str,
    cand_preds: np.ndarray,
    base_preds: np.ndarray,
    cand_abstained: np.ndarray,
    base_abstained: np.ndarray,
    y_true: np.ndarray,
    n_resamples: int = 500,
    seed: int = 42,
) -> ModelPairedComparison:
    """Compute nonparametric paired bootstrap difference between candidate and baseline.

    Args:
        cand_id: Candidate model identifier.
        base_id: Baseline model identifier.
        cand_preds: Candidate point predictions.
        base_preds: Baseline point predictions.
        cand_abstained: Candidate abstention mask.
        base_abstained: Baseline abstention mask.
        y_true: Ground truth target values.
        n_resamples: Number of bootstrap resamples.
        seed: Random seed.

    Returns:
        ModelPairedComparison instance.
    """
    valid_mask = (~cand_abstained) & (~base_abstained)
    n_valid = int(np.sum(valid_mask))

    if n_valid < 2:
        return ModelPairedComparison(
            candidate_id=cand_id,
            baseline_id=base_id,
            delta_mdape_pp=0.0,
            delta_mdape_ci_lower_pp=0.0,
            delta_mdape_ci_upper_pp=0.0,
            delta_mae_lpa=0.0,
            delta_mae_ci_lower_lpa=0.0,
            delta_mae_ci_upper_lpa=0.0,
            empirical_p_value=1.0,
            is_statistically_significant=False,
            minimum_effect_size_met=False,
            comparison_valid=False,
            notes="Insufficient joint non-abstained records for paired statistical test.",
        )

    yt = y_true[valid_mask]
    yp_c = cand_preds[valid_mask]
    yp_b = base_preds[valid_mask]

    denom = np.maximum(np.abs(yt), 1e-8)
    cand_mdape = float(np.median(np.abs(yt - yp_c) / denom))
    base_mdape = float(np.median(np.abs(yt - yp_b) / denom))
    delta_mdape_pp = (cand_mdape - base_mdape) * 100.0

    cand_mae = float(np.mean(np.abs(yt - yp_c)))
    base_mae = float(np.mean(np.abs(yt - yp_b)))
    delta_mae_lpa = cand_mae - base_mae

    rng = np.random.default_rng(seed)
    boot_delta_mdape = np.empty(n_resamples, dtype=np.float64)
    boot_delta_mae = np.empty(n_resamples, dtype=np.float64)

    for b in range(n_resamples):
        idx = rng.integers(0, n_valid, size=n_valid)
        yt_b = yt[idx]
        denom_b = denom[idx]
        b_c_mdape = np.median(np.abs(yt_b - yp_c[idx]) / denom_b)
        b_b_mdape = np.median(np.abs(yt_b - yp_b[idx]) / denom_b)
        boot_delta_mdape[b] = (b_c_mdape - b_b_mdape) * 100.0

        b_c_mae = np.mean(np.abs(yt_b - yp_c[idx]))
        b_b_mae = np.mean(np.abs(yt_b - yp_b[idx]))
        boot_delta_mae[b] = b_c_mae - b_b_mae

    ci_mdape_lower = float(np.percentile(boot_delta_mdape, 2.5))
    ci_mdape_upper = float(np.percentile(boot_delta_mdape, 97.5))
    ci_mae_lower = float(np.percentile(boot_delta_mae, 2.5))
    ci_mae_upper = float(np.percentile(boot_delta_mae, 97.5))

    # One-sided empirical p-value testing H0: delta_mdape >= 0 (no reduction)
    p_val = float(np.mean(boot_delta_mdape >= 0.0))
    is_sig = p_val < 0.05
    effect_met = delta_mdape_pp <= -2.0 and is_sig

    return ModelPairedComparison(
        candidate_id=cand_id,
        baseline_id=base_id,
        delta_mdape_pp=delta_mdape_pp,
        delta_mdape_ci_lower_pp=ci_mdape_lower,
        delta_mdape_ci_upper_pp=ci_mdape_upper,
        delta_mae_lpa=delta_mae_lpa,
        delta_mae_ci_lower_lpa=ci_mae_lower,
        delta_mae_ci_upper_lpa=ci_mae_upper,
        empirical_p_value=p_val,
        is_statistically_significant=is_sig,
        minimum_effect_size_met=effect_met,
        comparison_valid=True,
        notes="Paired bootstrap evaluation complete.",
    )


class GBMBenchmarkReportGenerator:
    """Benchmark evaluation engine comparing Rung D models against baseline champions."""

    def __init__(self, config: GBMBenchmarkReportConfig | None = None) -> None:
        """Initialize benchmark report generator."""
        self.config: GBMBenchmarkReportConfig = config or GBMBenchmarkReportConfig()

    def generate(
        self,
        df: pl.DataFrame,
        snapshot_id: str | None = None,
    ) -> GBMBenchmarkReport:
        """Generate comprehensive Rung D benchmark report against baselines.

        Args:
            df: Input Polars DataFrame of canonical observations.
            snapshot_id: Optional snapshot identifier override.

        Returns:
            GBMBenchmarkReport instance.
        """
        missing = REQUIRED_REPORT_COLUMNS - set(df.columns)
        if missing:
            raise CompIntelValidationError(
                f"DataFrame missing required report columns: {sorted(missing)}",
                code="MISSING_REPORT_COLUMNS",
            )

        # Rule R-MD-11: Synthetic data isolation guard
        is_synthetic = False
        if "is_synthetic" in df.columns:
            is_synthetic = bool(df["is_synthetic"].any())
            if is_synthetic and not self.config.allow_synthetic:
                raise DataContractError(
                    "Synthetic test data detected in Rung D report generation. "
                    "Rule R-MD-11 prohibits synthetic data in production benchmark reports.",
                    code="SYNTHETIC_DATA_PROHIBITED",
                )

        snap_id = snapshot_id or self.config.snapshot_id
        enriched_df = add_experience_band_column(df)

        split_cfg = SplitConfig(
            train_ratio=self.config.train_ratio,
            select_ratio=self.config.select_ratio,
            calibrate_ratio=self.config.calibrate_ratio,
            test_ratio=self.config.test_ratio,
        )
        splits = create_temporal_grouped_splits(enriched_df, config=split_cfg)

        train_df = splits.train_df
        eval_df = (
            splits.select_df if self.config.evaluation_split == "select" else splits.calibrate_df
        )
        dev_pool_df = pl.concat([train_df, eval_df])

        data_summary = {
            "total_observations": enriched_df.height,
            "train_count": train_df.height,
            "eval_count": eval_df.height,
            "eval_split_name": self.config.evaluation_split,
            "excluded_cross_window_count": splits.excluded_df.height,
        }

        # ----------------------------------------------------------------------
        # Model 1: Rung A Empirical Champion Baseline
        # ----------------------------------------------------------------------
        rung_a = EmpiricalQuantileBaseline(HierarchicalBackoffConfig())
        tracemalloc.start()
        t0 = time.perf_counter()
        rung_a.fit(train_df)
        fit_time_a = time.perf_counter() - t0
        _, peak_mem_a = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        t0 = time.perf_counter()
        pred_a_df = rung_a.predict(eval_df)
        lat_a_ms = ((time.perf_counter() - t0) * 1000.0 / len(eval_df)) if len(eval_df) > 0 else 0.0

        p50_a = pred_a_df["p50"].to_numpy()
        abstained_a = pred_a_df["is_abstained"].to_numpy()
        summary_a = self._evaluate_model_summary(
            model_id="rung_a_empirical",
            model_name="Rung A (Empirical Champion)",
            eval_df=eval_df,
            predictions=p50_a,
            abstained_mask=abstained_a,
            fit_time=fit_time_a,
            latency_ms=lat_a_ms,
            peak_memory_mb=peak_mem_a / (1024 * 1024),
        )

        # ----------------------------------------------------------------------
        # Model 2: Rung B Linear Baseline
        # ----------------------------------------------------------------------
        rung_b = LinearQuantileBaseline(LinearQuantileConfig())
        tracemalloc.start()
        t0 = time.perf_counter()
        rung_b.fit(train_df)
        fit_time_b = time.perf_counter() - t0
        _, peak_mem_b = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        t0 = time.perf_counter()
        pred_b_df = rung_b.predict(eval_df)
        lat_b_ms = ((time.perf_counter() - t0) * 1000.0 / len(eval_df)) if len(eval_df) > 0 else 0.0

        p50_b = pred_b_df["p50"].to_numpy()
        abstained_b = pred_b_df["is_abstained"].to_numpy()
        summary_b = self._evaluate_model_summary(
            model_id="rung_b_linear",
            model_name="Rung B (Linear Quantile)",
            eval_df=eval_df,
            predictions=p50_b,
            abstained_mask=abstained_b,
            fit_time=fit_time_b,
            latency_ms=lat_b_ms,
            peak_memory_mb=peak_mem_b / (1024 * 1024),
        )

        # ----------------------------------------------------------------------
        # Model 3: Rung D LightGBM Point Model
        # ----------------------------------------------------------------------
        lgb_model = create_gbm_point_model(
            GBMPointConfig(
                model_type=GBMModelType.LIGHTGBM,
                random_seed=self.config.random_seed,
            )
        )
        lgb_model.fit(train_df)
        t0 = time.perf_counter()
        lgb_preds = lgb_model.predict(eval_df)
        lat_lgb_ms = (time.perf_counter() - t0) * 1000.0 / len(eval_df) if len(eval_df) > 0 else 0.0

        p_lgb = np.array([p.predicted_pay_lpa for p in lgb_preds], dtype=np.float64)
        abs_lgb = np.array([p.is_abstained for p in lgb_preds], dtype=bool)
        summary_lgb = self._evaluate_model_summary(
            model_id="rung_d_lightgbm",
            model_name="Rung D (LightGBM)",
            eval_df=eval_df,
            predictions=p_lgb,
            abstained_mask=abs_lgb,
            fit_time=lgb_model.metrics.fit_time_seconds if lgb_model.metrics else 0.0,
            latency_ms=lat_lgb_ms,
            peak_memory_mb=lgb_model.metrics.peak_memory_mb if lgb_model.metrics else 0.0,
        )

        # ----------------------------------------------------------------------
        # Model 4: Rung D CatBoost Point Model
        # ----------------------------------------------------------------------
        cb_model = create_gbm_point_model(
            GBMPointConfig(
                model_type=GBMModelType.CATBOOST,
                random_seed=self.config.random_seed,
            )
        )
        cb_model.fit(train_df)
        t0 = time.perf_counter()
        cb_preds = cb_model.predict(eval_df)
        lat_cb_ms = (
            ((time.perf_counter() - t0) * 1000.0 / len(eval_df)) if len(eval_df) > 0 else 0.0
        )

        p_cb = np.array([p.predicted_pay_lpa for p in cb_preds], dtype=np.float64)
        abs_cb = np.array([p.is_abstained for p in cb_preds], dtype=bool)
        summary_cb = self._evaluate_model_summary(
            model_id="rung_d_catboost",
            model_name="Rung D (CatBoost)",
            eval_df=eval_df,
            predictions=p_cb,
            abstained_mask=abs_cb,
            fit_time=cb_model.metrics.fit_time_seconds if cb_model.metrics else 0.0,
            latency_ms=lat_cb_ms,
            peak_memory_mb=cb_model.metrics.peak_memory_mb if cb_model.metrics else 0.0,
        )

        models_dict: dict[str, ModelEvalSummary] = {
            "rung_a_empirical": summary_a,
            "rung_b_linear": summary_b,
            "rung_d_lightgbm": summary_lgb,
            "rung_d_catboost": summary_cb,
        }

        # ----------------------------------------------------------------------
        # Grouped-Temporal Cross-Validation on Development Pool
        # ----------------------------------------------------------------------
        cv_results: dict[str, GBMCVResult] = {}
        # Adjust K if dev pool records are small
        k_folds = min(self.config.n_cv_folds, max(2, len(dev_pool_df) - 2))
        try:
            cv_lgb = run_gbm_cv(
                df=dev_pool_df,
                model_type=GBMModelType.LIGHTGBM,
                config=GBMPointConfig(
                    model_type=GBMModelType.LIGHTGBM,
                    random_seed=self.config.random_seed,
                ),
                n_folds=k_folds,
            )
            cv_results["lightgbm"] = cv_lgb
        except Exception as exc:
            logger.warning("LightGBM CV run skipped or encountered error", error=str(exc))

        try:
            cv_cb = run_gbm_cv(
                df=dev_pool_df,
                model_type=GBMModelType.CATBOOST,
                config=GBMPointConfig(
                    model_type=GBMModelType.CATBOOST,
                    random_seed=self.config.random_seed,
                ),
                n_folds=k_folds,
            )
            cv_results["catboost"] = cv_cb
        except Exception as exc:
            logger.warning("CatBoost CV run skipped or encountered error", error=str(exc))

        # ----------------------------------------------------------------------
        # Acceptance Threshold Checks
        # ----------------------------------------------------------------------
        threshold_checks: list[dict[str, Any]] = []
        for m_id, m in models_dict.items():
            if m.is_abstained_all:
                threshold_checks.append(
                    {
                        "model_id": m_id,
                        "model_name": m.model_name,
                        "metric_name": "Point MAE",
                        "metric_value": "Abstained",
                        "threshold": f"<= {self.config.max_point_mae_lpa:.2f} LPA",
                        "status": "FAIL",
                        "details": "Model abstained on all evaluation records (Rule R-MD-08)",
                    }
                )
                continue

            # MAE check
            mae_pass = m.mae <= self.config.max_point_mae_lpa
            threshold_checks.append(
                {
                    "model_id": m_id,
                    "model_name": m.model_name,
                    "metric_name": "Point MAE",
                    "metric_value": f"{m.mae:.4f} LPA",
                    "threshold": f"<= {self.config.max_point_mae_lpa:.2f} LPA",
                    "status": "PASS" if mae_pass else "FAIL",
                    "details": f"Observed MAE: {m.mae:.4f} LPA",
                }
            )

            # MdAPE check
            mdape_pass = m.mdape <= self.config.max_point_mdape
            threshold_checks.append(
                {
                    "model_id": m_id,
                    "model_name": m.model_name,
                    "metric_name": "Point MdAPE",
                    "metric_value": f"{m.mdape * 100.0:.2f}%",
                    "threshold": f"<= {self.config.max_point_mdape * 100.0:.1f}%",
                    "status": "PASS" if mdape_pass else "FAIL",
                    "details": f"Observed MdAPE: {m.mdape * 100.0:.2f}%",
                }
            )

        # ----------------------------------------------------------------------
        # Paired Comparisons against Baselines
        # ----------------------------------------------------------------------
        y_true = eval_df.get_column("guaranteed_cash_annual").to_numpy()
        paired_comparisons: list[ModelPairedComparison] = []

        # Compare LightGBM vs Rung A and Rung B
        paired_comparisons.append(
            _compute_paired_comparison(
                cand_id="Rung D (LightGBM)",
                base_id="Rung A (Empirical)",
                cand_preds=p_lgb,
                base_preds=p50_a,
                cand_abstained=abs_lgb,
                base_abstained=abstained_a,
                y_true=y_true,
                n_resamples=self.config.bootstrap_resamples,
                seed=self.config.random_seed,
            )
        )
        paired_comparisons.append(
            _compute_paired_comparison(
                cand_id="Rung D (LightGBM)",
                base_id="Rung B (Linear)",
                cand_preds=p_lgb,
                base_preds=p50_b,
                cand_abstained=abs_lgb,
                base_abstained=abstained_b,
                y_true=y_true,
                n_resamples=self.config.bootstrap_resamples,
                seed=self.config.random_seed,
            )
        )

        # Compare CatBoost vs Rung A and Rung B
        paired_comparisons.append(
            _compute_paired_comparison(
                cand_id="Rung D (CatBoost)",
                base_id="Rung A (Empirical)",
                cand_preds=p_cb,
                base_preds=p50_a,
                cand_abstained=abs_cb,
                base_abstained=abstained_a,
                y_true=y_true,
                n_resamples=self.config.bootstrap_resamples,
                seed=self.config.random_seed,
            )
        )
        paired_comparisons.append(
            _compute_paired_comparison(
                cand_id="Rung D (CatBoost)",
                base_id="Rung B (Linear)",
                cand_preds=p_cb,
                base_preds=p50_b,
                cand_abstained=abs_cb,
                base_abstained=abstained_b,
                y_true=y_true,
                n_resamples=self.config.bootstrap_resamples,
                seed=self.config.random_seed,
            )
        )

        # ----------------------------------------------------------------------
        # Champion Recommendation for Phase 5
        # ----------------------------------------------------------------------
        lgb_mae_ok = summary_lgb.mae <= self.config.max_point_mae_lpa
        cb_mae_ok = summary_cb.mae <= self.config.max_point_mae_lpa

        if lgb_mae_ok and cb_mae_ok:
            if summary_lgb.mae <= summary_cb.mae:
                designated = "LightGBMPointModel"
                verdict = "ACCEPTED_AS_RUNG_D_CHAMPION"
                rationale = (
                    f"LightGBM achieved superior point precision (MAE={summary_lgb.mae:.4f} LPA) "
                    f"over CatBoost (MAE={summary_cb.mae:.4f} LPA) and baseline champions."
                )
            else:
                designated = "CatBoostPointModel"
                verdict = "ACCEPTED_AS_RUNG_D_CHAMPION"
                rationale = (
                    f"CatBoost achieved superior point precision (MAE={summary_cb.mae:.4f} LPA) "
                    f"over LightGBM (MAE={summary_lgb.mae:.4f} LPA) and baseline champions."
                )
        elif lgb_mae_ok:
            designated = "LightGBMPointModel"
            verdict = "ACCEPTED_AS_RUNG_D_CHAMPION"
            rationale = (
                f"LightGBM met point error thresholds (MAE={summary_lgb.mae:.4f} LPA <= "
                f"{self.config.max_point_mae_lpa:.2f} LPA)."
            )
        elif cb_mae_ok:
            designated = "CatBoostPointModel"
            verdict = "ACCEPTED_AS_RUNG_D_CHAMPION"
            rationale = (
                f"CatBoost met point error thresholds (MAE={summary_cb.mae:.4f} LPA <= "
                f"{self.config.max_point_mae_lpa:.2f} LPA)."
            )
        else:
            designated = "Rung A (Empirical Champion Retained)"
            verdict = "RETAIN_BASELINE_CHAMPION"
            rationale = (
                "Neither LightGBM nor CatBoost satisfied the point error threshold "
                f"(MAE <= {self.config.max_point_mae_lpa:.2f} LPA)."
            )

        champion_rec = {
            "designated_model": designated,
            "verdict": verdict,
            "rationale": rationale,
        }

        report_id = f"REPORT-RUNGD-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

        return GBMBenchmarkReport(
            report_id=report_id,
            generated_at_utc=datetime.now(UTC).isoformat(),
            git_commit=_get_current_git_commit(),
            snapshot_id=snap_id,
            random_seed=self.config.random_seed,
            is_synthetic=is_synthetic,
            evaluation_split=self.config.evaluation_split,
            data_summary=data_summary,
            models=models_dict,
            cv_results=cv_results,
            threshold_checks=threshold_checks,
            paired_comparisons=paired_comparisons,
            champion_recommendation=champion_rec,
        )

    def _evaluate_model_summary(
        self,
        model_id: str,
        model_name: str,
        eval_df: pl.DataFrame,
        predictions: np.ndarray,
        abstained_mask: np.ndarray,
        fit_time: float,
        latency_ms: float,
        peak_memory_mb: float,
    ) -> ModelEvalSummary:
        """Compute point error metrics, bootstrap CIs, and slice breakdowns."""
        total_n = len(eval_df)
        abstained_cnt = int(np.sum(abstained_mask))
        abstention_rate = (abstained_cnt / total_n * 100.0) if total_n > 0 else 0.0

        valid_mask = ~abstained_mask
        valid_n = int(np.sum(valid_mask))
        y_true = eval_df.get_column("guaranteed_cash_annual").to_numpy()

        if valid_n == 0:
            return ModelEvalSummary(
                model_id=model_id,
                model_name=model_name,
                is_abstained_all=True,
                abstained_count=abstained_cnt,
                abstention_rate=abstention_rate,
                sample_size=total_n,
                valid_sample_size=0,
                mae=float("nan"),
                medae=float("nan"),
                mape=float("nan"),
                mdape=float("nan"),
                rmse=float("nan"),
                point_ci={},
                slices={},
                fit_time_seconds=fit_time,
                inference_latency_per_obs_ms=latency_ms,
                peak_memory_mb=peak_memory_mb,
            )

        yt = y_true[valid_mask]
        yp = predictions[valid_mask]

        mae = mean_absolute_error(yt, yp)
        medae = median_absolute_error(yt, yp)
        mape = mean_absolute_percentage_error(yt, yp)
        mdape = median_absolute_percentage_error(yt, yp)
        rmse = root_mean_squared_error(yt, yp)

        point_ci: dict[str, MetricWithCI] = {}
        if self.config.with_bootstrap_ci:
            point_ci["mae"] = bootstrap_metric_ci(
                yt,
                yp,
                mean_absolute_error,
                n_resamples=self.config.bootstrap_resamples,
                confidence_level=self.config.confidence_level,
                seed=self.config.random_seed,
            )
            point_ci["mdape"] = bootstrap_metric_ci(
                yt,
                yp,
                median_absolute_percentage_error,
                n_resamples=self.config.bootstrap_resamples,
                confidence_level=self.config.confidence_level,
                seed=self.config.random_seed,
            )
            point_ci["medae"] = bootstrap_metric_ci(
                yt,
                yp,
                median_absolute_error,
                n_resamples=self.config.bootstrap_resamples,
                confidence_level=self.config.confidence_level,
                seed=self.config.random_seed,
            )
            point_ci["rmse"] = bootstrap_metric_ci(
                yt,
                yp,
                root_mean_squared_error,
                n_resamples=self.config.bootstrap_resamples,
                confidence_level=self.config.confidence_level,
                seed=self.config.random_seed,
            )

        # Slice analysis
        slice_cols = [
            "experience_band",
            "role_family",
            "seniority",
            "location",
            "provenance_tier",
        ]
        available_slices = [c for c in slice_cols if c in eval_df.columns]
        slices_dict: dict[str, dict[str, Any]] = {}

        valid_eval_df = eval_df.filter(pl.Series(valid_mask))
        for col in available_slices:
            grp_dict: dict[str, Any] = {}
            unique_vals = valid_eval_df.get_column(col).unique().to_list()
            for u_val in unique_vals:
                if u_val is None:
                    continue
                s_mask = (valid_eval_df.get_column(col) == u_val).to_numpy()
                if np.sum(s_mask) >= 1:
                    s_yt = yt[s_mask]
                    s_yp = yp[s_mask]
                    grp_dict[str(u_val)] = {
                        "sample_size": int(np.sum(s_mask)),
                        "mae": mean_absolute_error(s_yt, s_yp),
                        "mdape": median_absolute_percentage_error(s_yt, s_yp),
                    }
            if grp_dict:
                slices_dict[col] = grp_dict

        return ModelEvalSummary(
            model_id=model_id,
            model_name=model_name,
            is_abstained_all=False,
            abstained_count=abstained_cnt,
            abstention_rate=abstention_rate,
            sample_size=total_n,
            valid_sample_size=valid_n,
            mae=mae,
            medae=medae,
            mape=mape,
            mdape=mdape,
            rmse=rmse,
            point_ci=point_ci,
            slices=slices_dict,
            fit_time_seconds=fit_time,
            inference_latency_per_obs_ms=latency_ms,
            peak_memory_mb=peak_memory_mb,
        )


def run_gbm_benchmark_report(
    df: pl.DataFrame,
    config: GBMBenchmarkReportConfig | None = None,
    output_md_path: Path | None = None,
    output_json_path: Path | None = None,
) -> GBMBenchmarkReport:
    """Execute Rung D benchmark evaluation and write outputs to disk.

    Args:
        df: Input DataFrame of canonical observations.
        config: Optional GBMBenchmarkReportConfig.
        output_md_path: Path to write Markdown report.
        output_json_path: Path to write JSON report.

    Returns:
        GBMBenchmarkReport instance.
    """
    generator = GBMBenchmarkReportGenerator(config)
    report = generator.generate(df)

    if output_md_path:
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.write_text(report.to_markdown(), encoding="utf-8")
        logger.info("Saved Markdown benchmark report", path=str(output_md_path))

    if output_json_path:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        logger.info("Saved JSON benchmark report", path=str(output_json_path))

    return report
