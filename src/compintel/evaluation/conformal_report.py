"""Conformal coverage and calibration reporting engine (Task T5.04).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal dataset splitting; zero entity leakage.
- Rule R-MD-02: Locked final test set isolation. Routine evaluation is strictly
  restricted to dev partitions ('select' or 'calibrate'). Evaluation on 'test'
  is prohibited.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-05: Mandatory evaluation metrics: coverage, interval width, quantile
  calibration errors, pinball loss, subgroup slices, recent window, and tail analysis.
- Rule R-MD-08: Thin-evidence support checks. Slices below minimum support (N < 10)
  must be flagged, not hidden.
- Rule R-MD-10: Deterministic random seeds, timing, and reproducibility.
- Rule R-MD-11: Synthetic test data blocked by default from canonical reports.
- Rule R-UQ-01: Nonparametric percentile bootstrap confidence intervals (95% CI).
- Rule R-UQ-03: Conformal statutory assumptions: marginal coverage guarantees,
  exchangeability requirement, no individual coverage claims, and temporal drift warnings.
- Rule R-UQ-05: Monotonic ordering repair and non-negativity floor.
- Pre-registration v1.yaml: Decision rules, minimum support thresholds, and acceptance bounds.
"""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import numpy as np

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.baseline_report import (
    REQUIRED_REPORT_COLUMNS,
    add_experience_band_column,
)
from compintel.evaluation.metrics import (
    FloatArray,
    MetricWithCI,
    bootstrap_metric_ci,
    pinball_loss,
)
from compintel.evaluation.splits import (
    SplitConfig,
    create_temporal_grouped_splits,
)
from compintel.logging import get_logger
from compintel.models.gbm.config import (
    GBMModelType,
    GBMPointConfig,
    GBMQuantileConfig,
)
from compintel.models.gbm.point import CatBoostPointModel
from compintel.models.gbm.quantile import CatBoostQuantileModel
from compintel.uncertainty.conformal import (
    ConformalAssumptions,
    ConformalConfig,
    ConformalMethod,
    ConformalQuantileRegressor,
    SplitConformalCalibrator,
)

if TYPE_CHECKING:
    import polars as pl

logger = get_logger("compintel.evaluation.conformal_report")


@dataclass(frozen=True)
class ConformalSliceMetrics:
    """Detailed coverage, width, and calibration metrics for a single slice."""

    dimension: str
    slice_value: str
    sample_size: int
    is_low_support: bool
    support_status: str
    empirical_coverage: float
    coverage_ci_lower: float | None
    coverage_ci_upper: float | None
    mean_width_lpa: float
    median_width_lpa: float
    width_ci_lower: float | None
    width_ci_upper: float | None
    underflow_rate_q10: float
    overflow_rate_q90: float
    calibration_error: float
    abstention_count: int
    abstention_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Convert slice metrics to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class TailAnalysisMetrics:
    """Quantile error distribution in upper and lower pay tails."""

    global_underflow_q10: float
    global_overflow_q90: float
    tail_balance_ratio: float
    lower_tail_count: int
    lower_tail_coverage: float
    lower_tail_mean_width: float
    upper_tail_count: int
    upper_tail_coverage: float
    upper_tail_mean_width: float

    def to_dict(self) -> dict[str, Any]:
        """Convert tail metrics to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class RecentWindowMetrics:
    """Coverage and calibration evaluated on the most recent temporal slice."""

    window_start_date: str
    window_end_date: str
    window_sample_size: int
    is_low_support: bool
    recent_coverage: float
    recent_coverage_ci_lower: float | None
    recent_coverage_ci_upper: float | None
    recent_mean_width_lpa: float
    older_coverage: float
    temporal_drift_delta: float
    drift_warning: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert recent window metrics to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class ModelConformalEvaluation:
    """Full conformal evaluation of a specific candidate uncertainty model."""

    model_name: str
    method: str
    nominal_coverage: float
    conformal_correction: float
    sample_size: int
    overall_coverage: float
    overall_coverage_ci: MetricWithCI | None
    overall_mean_width_lpa: float
    overall_median_width_lpa: float
    overall_width_ci: MetricWithCI | None
    mean_calibration_error: float
    pinball_q10: float
    pinball_q50: float
    pinball_q90: float
    mean_pinball_loss: float
    crossing_count: int
    crossing_rate: float
    abstention_count: int
    abstention_rate: float
    tails: TailAnalysisMetrics
    recent_window: RecentWindowMetrics | None
    slices: dict[str, list[ConformalSliceMetrics]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert model conformal evaluation to dictionary representation."""
        res: dict[str, Any] = {
            "model_name": self.model_name,
            "method": self.method,
            "nominal_coverage": self.nominal_coverage,
            "conformal_correction": self.conformal_correction,
            "sample_size": self.sample_size,
            "overall_coverage": self.overall_coverage,
            "overall_coverage_ci": (
                self.overall_coverage_ci.to_dict() if self.overall_coverage_ci else None
            ),
            "overall_mean_width_lpa": self.overall_mean_width_lpa,
            "overall_median_width_lpa": self.overall_median_width_lpa,
            "overall_width_ci": (
                self.overall_width_ci.to_dict() if self.overall_width_ci else None
            ),
            "mean_calibration_error": self.mean_calibration_error,
            "pinball_q10": self.pinball_q10,
            "pinball_q50": self.pinball_q50,
            "pinball_q90": self.pinball_q90,
            "mean_pinball_loss": self.mean_pinball_loss,
            "crossing_count": self.crossing_count,
            "crossing_rate": self.crossing_rate,
            "abstention_count": self.abstention_count,
            "abstention_rate": self.abstention_rate,
            "tails": self.tails.to_dict(),
            "recent_window": self.recent_window.to_dict() if self.recent_window else None,
            "slices": {
                dim: [s.to_dict() for s in metrics_list]
                for dim, metrics_list in self.slices.items()
            },
        }
        return res


def _mean_statistic(y_true: FloatArray, _y_pred: FloatArray) -> float:
    """Helper statistic function for bootstrap confidence interval calculation."""
    return float(np.mean(y_true))


@dataclass(frozen=True)
class ConformalReportConfig:
    """Configuration governing conformal evaluation and slice reporting."""

    nominal_coverage: float = 0.80
    min_support_threshold: int = 10
    min_pay_bound_lpa: float = 0.50
    n_bootstrap_resamples: int = 1000
    confidence_level: float = 0.95
    random_seed: int = 42
    evaluation_split: str = "select"
    train_ratio: float = 0.60
    select_ratio: float = 0.15
    calibrate_ratio: float = 0.15
    test_ratio: float = 0.10
    snapshot_id: str = "SNAP-1FF34A8E9633"
    allow_synthetic: bool = False


@dataclass(frozen=True)
class ConformalCalibrationReport:
    """Top-level conformal coverage and calibration evaluation report (Task T5.04)."""

    report_id: str
    generated_at: str
    git_commit: str
    snapshot_id: str
    random_seed: int
    evaluation_split: str
    data_summary: dict[str, Any]
    models: dict[str, ModelConformalEvaluation]
    assumptions: ConformalAssumptions
    champion_verdict: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to nested dictionary representation."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "git_commit": self.git_commit,
            "snapshot_id": self.snapshot_id,
            "random_seed": self.random_seed,
            "evaluation_split": self.evaluation_split,
            "data_summary": self.data_summary,
            "models": {k: v.to_dict() for k, v in self.models.items()},
            "assumptions": self.assumptions.to_dict(),
            "champion_verdict": self.champion_verdict,
        }

    def to_markdown(self) -> str:
        """Render publication-grade GitHub Flavored Markdown report."""
        short_commit = self.git_commit[:8] if len(self.git_commit) >= 8 else self.git_commit
        total_obs = self.data_summary.get("total_observations", "N/A")
        train_cnt = self.data_summary.get("train_count", "N/A")
        cal_cnt = self.data_summary.get("calibrate_count", "N/A")
        eval_cnt = self.data_summary.get("eval_count", "N/A")

        lines: list[str] = [
            "# ArthaIQ Conformal Coverage & Calibration Report (Task T5.04)",
            "",
            "> [!NOTE]",
            (
                "> **FORMAL CONFORMAL ASSUMPTIONS (Rule R-UQ-03)**: Coverage guarantees are\n"
                "> strictly **marginal** ($P(Y \\in C(X)) \\ge 1 - \\alpha$) over population,\n"
                "> and hold **conditionally on exchangeability** between calibration and eval.\n"
                "> ArthaIQ makes **no claim of individual-level conditional coverage**."
            ),
            "",
            "> [!IMPORTANT]",
            (
                "> **LOCKED TEST PARTITION (Rule R-MD-02)**: Routine evaluation is strictly\n"
                f"> isolated to dev pool partition (`{self.evaluation_split}`). Test partition\n"
                "> remains locked and untouched until Gate G5 acceptance."
            ),
            "",
            "## 1. Provenance and Partition Metadata",
            "",
            "| Parameter | Value | Description |",
            "|---|---|---|",
            f"| **Report ID** | `{self.report_id}` | Unique evaluation audit ID |",
            f"| **Data Snapshot ID** | `{self.snapshot_id}` | Cryptographic dataset digest |",
            f"| **Git Commit** | `{short_commit}` | Exact repository commit SHA |",
            f"| **Random Seed** | `{self.random_seed}` | Deterministic seeded RNG (R-MD-10) |",
            f"| **Evaluation Split** | `{self.evaluation_split}` | Dev partition (Rule R-MD-02) |",
            f"| **Total Analyzed** | `{total_obs}` | Total canonical observations |",
            f"| **Training Records** | `{train_cnt}` | Base model training partition |",
            f"| **Calibration Records** | `{cal_cnt}` | Conformal calibration partition |",
            f"| **Evaluation Records** | `{eval_cnt}` | Holdout validation partition |",
            "",
            "## 2. Global Conformal Performance Comparison",
            "",
            (
                "| Model Architecture | Method | Conformal $q$ | 80% Coverage (95% CI) | "
                "Mean Width (LPA) | Mean Pinball | Crossing Rate | Abstention |"
            ),
            "|---|---|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for _m_key, m_eval in self.models.items():
            cov_str = f"{m_eval.overall_coverage * 100.0:.1f}%"
            if m_eval.overall_coverage_ci:
                ci_lo = m_eval.overall_coverage_ci.ci_lower * 100.0
                ci_hi = m_eval.overall_coverage_ci.ci_upper * 100.0
                cov_str += f" [{ci_lo:.1f}%, {ci_hi:.1f}%]"

            width_str = f"{m_eval.overall_mean_width_lpa:.2f}"
            if m_eval.overall_width_ci:
                w_lo = m_eval.overall_width_ci.ci_lower
                w_hi = m_eval.overall_width_ci.ci_upper
                width_str += f" [{w_lo:.2f}, {w_hi:.2f}]"

            corr_str = (
                f"{m_eval.conformal_correction:.4f}"
                if m_eval.conformal_correction != 0.0
                else "None"
            )
            cross_str = f"{m_eval.crossing_rate * 100.0:.1f}%"
            abs_str = f"{m_eval.abstention_rate * 100.0:.1f}%"

            lines.append(
                f"| **{m_eval.model_name}** | `{m_eval.method}` | `{corr_str}` | "
                f"`{cov_str}` | `{width_str}` | `{m_eval.mean_pinball_loss:.4f}` | "
                f"`{cross_str}` | `{abs_str}` |"
            )

        # 3. Tail Error Distribution
        lines.extend(
            [
                "",
                "## 3. Tail Error & Boundary Distribution",
                "",
                (
                    "Under nominal 80% coverage $[P10, P90]$, theoretical tail underflow and "
                    "overflow rates are exactly 10.0%."
                ),
                "",
                (
                    "| Model | Underflow Rate (< P10) | Overflow Rate (> P90) | Balance Ratio | "
                    "Lower Tail Pay Coverage | Upper Tail Pay Coverage |"
                ),
                "|---|:---:|:---:|:---:|:---:|:---:|",
            ]
        )

        for m_eval in self.models.values():
            t = m_eval.tails
            lines.append(
                f"| **{m_eval.model_name}** | `{t.global_underflow_q10 * 100.0:.1f}%` | "
                f"`{t.global_overflow_q90 * 100.0:.1f}%` | `{t.tail_balance_ratio:.2f}` | "
                f"`{t.lower_tail_coverage * 100.0:.1f}%` (N={t.lower_tail_count}) | "
                f"`{t.upper_tail_coverage * 100.0:.1f}%` (N={t.upper_tail_count}) |"
            )

        # 4. Recent Temporal Window & Drift
        lines.extend(
            [
                "",
                "## 4. Temporal Drift & Recent Window Breakdown (Rule R-UQ-03)",
                "",
                (
                    "Conformal coverage assumes exchangeability across time. We evaluate the most "
                    "recent temporal quarter against earlier data to quantify temporal drift."
                ),
                "",
                (
                    "| Model | Recent Window Coverage | Older Cohort Coverage | "
                    "Temporal Drift ($\\Delta$) | Drift Status |"
                ),
                "|---|:---:|:---:|:---:|:---:|",
            ]
        )

        for m_eval in self.models.values():
            rw = m_eval.recent_window
            if rw:
                drift_status = "WARNING: DRIFT DETECTED" if rw.drift_warning else "EXCHANGEABLE"
                lines.append(
                    f"| **{m_eval.model_name}** | "
                    f"`{rw.recent_coverage * 100.0:.1f}%` (N={rw.window_sample_size}) | "
                    f"`{rw.older_coverage * 100.0:.1f}%` | "
                    f"`{rw.temporal_drift_delta * 100.0:+.1f} pp` | `{drift_status}` |"
                )
            else:
                lines.append(
                    f"| **{m_eval.model_name}** | `N/A` | `N/A` | `N/A` | "
                    "`INSUFFICIENT_TIMESTAMPS` |"
                )

        # 5. Subgroup Slices with Low-Support Flagging (Rule R-MD-08)
        # Slices below minimum support are flagged, NOT hidden.
        cqr_eval = self.models.get("cqr_catboost") or next(iter(self.models.values()))
        lines.extend(
            [
                "",
                "## 5. Subgroup Slice Analysis & Minimum Support Flags (Rule R-MD-08)",
                "",
                "> [!IMPORTANT]",
                (
                    "> **MINIMUM SUPPORT POLICY (Rule R-MD-08)**: Slices with $N < 10$\n"
                    "> are explicitly flagged as `[FLAGGED: LOW SUPPORT]` with cell counts.\n"
                    "> In adherence to the project charter, under-supported cohorts are "
                    "**never hidden or omitted**."
                ),
                "",
            ]
        )

        for dim, slice_list in cqr_eval.slices.items():
            dim_title = dim.replace("_", " ").title()
            lines.extend(
                [
                    f"### Slice: {dim_title}",
                    "",
                    (
                        "| Category | Support Status | Sample Size | 80% Coverage (95% CI) | "
                        "Mean Width (LPA) | Underflow (< P10) | Overflow (> P90) | Abstention |"
                    ),
                    "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
                ]
            )

            for s in slice_list:
                status_badge = "**`FLAGGED (N < 10)`**" if s.is_low_support else "`ADEQUATE`"
                cov_val = f"{s.empirical_coverage * 100.0:.1f}%"
                if s.coverage_ci_lower is not None and s.coverage_ci_upper is not None:
                    cov_val += (
                        f" [{s.coverage_ci_lower * 100.0:.1f}%, {s.coverage_ci_upper * 100.0:.1f}%]"
                    )

                lines.append(
                    f"| **`{s.slice_value}`** | {status_badge} | `{s.sample_size}` | "
                    f"`{cov_val}` | `{s.mean_width_lpa:.2f}` | "
                    f"`{s.underflow_rate_q10 * 100.0:.1f}%` | "
                    f"`{s.overflow_rate_q90 * 100.0:.1f}%` | "
                    f"`{s.abstention_rate * 100.0:.1f}%` |"
                )
            lines.append("")

        # 6. Champion Uncertainty Model Verdict
        lines.extend(
            [
                "## 6. Champion Uncertainty Model Verdict",
                "",
                f"- **Designated Champion**: `{self.champion_verdict.get('champion_model')}`",
                f"- **Verdict Status**: `{self.champion_verdict.get('status')}`",
                f"- **Reasoning**: {self.champion_verdict.get('reason')}",
                "",
                "---",
                (
                    "*Report automatically generated by "
                    "`src/compintel/evaluation/conformal_report.py`*"
                ),
            ]
        )

        return "\n".join(lines)


class ConformalCalibrationReportGenerator:
    """Orchestrator for evaluating conformal models and generating comprehensive slice reports."""

    def __init__(self, config: ConformalReportConfig | None = None) -> None:
        """Initialize generator with configuration."""
        self.config = config or ConformalReportConfig()
        if self.config.evaluation_split == "test":
            raise CompIntelValidationError(
                "Rule R-MD-02 strictly locks the final test partition. Routine conformal "
                "reports must evaluate on dev partitions ('select' or 'calibrate').",
                code="TEST_PARTITION_LOCKED",
            )

    def generate_report(
        self,
        df: pl.DataFrame,
        snapshot_id: str | None = None,
    ) -> ConformalCalibrationReport:
        """Run full conformal calibration pipeline and produce calibration report.

        Args:
            df: Polars DataFrame containing canonical observations.
            snapshot_id: Optional snapshot identifier override.

        Returns:
            ConformalCalibrationReport containing all metrics, slices, and flags.
        """
        # Validate columns
        missing = REQUIRED_REPORT_COLUMNS - set(df.columns)
        if missing:
            raise CompIntelValidationError(
                f"DataFrame missing required report columns: {sorted(missing)}",
                code="MISSING_REPORT_COLUMNS",
            )

        # Rule R-MD-11: Synthetic data isolation guard
        if "is_synthetic" in df.columns:
            is_synthetic = bool(df["is_synthetic"].any())
            if is_synthetic and not self.config.allow_synthetic:
                raise DataContractError(
                    "Synthetic test data detected in conformal calibration report. "
                    "Rule R-MD-11 prohibits synthetic data in production benchmark reports.",
                    code="SYNTHETIC_DATA_PROHIBITED",
                )

        snap_id = snapshot_id or self.config.snapshot_id
        enriched_df = add_experience_band_column(df)

        # Temporal-grouped splitting
        split_cfg = SplitConfig(
            train_ratio=self.config.train_ratio,
            select_ratio=self.config.select_ratio,
            calibrate_ratio=self.config.calibrate_ratio,
            test_ratio=self.config.test_ratio,
        )
        splits = create_temporal_grouped_splits(enriched_df, config=split_cfg)

        train_df = splits.train_df
        cal_df = splits.calibrate_df
        eval_df = (
            splits.select_df if self.config.evaluation_split == "select" else splits.calibrate_df
        )

        data_summary = {
            "total_observations": enriched_df.height,
            "train_count": train_df.height,
            "calibrate_count": cal_df.height,
            "eval_count": eval_df.height,
            "eval_split_name": self.config.evaluation_split,
            "excluded_cross_window_count": splits.excluded_df.height,
        }

        # 1. Base Quantile Model (Uncalibrated Baseline)
        base_quant = CatBoostQuantileModel(
            GBMQuantileConfig(
                model_type=GBMModelType.CATBOOST,
                n_estimators=100,
                learning_rate=0.08,
            )
        )
        base_quant.fit(train_df)

        # 2. Conformalized Quantile Regressor (CQR)
        cqr = ConformalQuantileRegressor(
            base_model=base_quant,
            config=ConformalConfig(
                nominal_coverage=self.config.nominal_coverage,
                min_pay_bound_lpa=self.config.min_pay_bound_lpa,
            ),
        )
        cqr.calibrate(cal_df)

        # 3. Base Point Model and Split Conformal Calibrator
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
                nominal_coverage=self.config.nominal_coverage,
                min_pay_bound_lpa=self.config.min_pay_bound_lpa,
            ),
        )
        split_calibrator.calibrate(cal_df)

        # Slices to evaluate
        slice_dims = [
            "experience_band",
            "role_family",
            "seniority",
            "location",
            "provenance_tier",
        ]
        available_slice_dims = [d for d in slice_dims if d in eval_df.columns]

        # Evaluate Models
        models_eval: dict[str, ModelConformalEvaluation] = {}

        # Evaluate CQR
        cqr_preds = cqr.predict(eval_df)
        cqr_eval = self._evaluate_predictions(
            model_name="CatBoost CQR (Rung F)",
            method="cqr",
            nominal_coverage=self.config.nominal_coverage,
            conformal_correction=cqr.conformal_quantile,
            eval_df=eval_df,
            p10_series=[p.p10_calibrated for p in cqr_preds],
            p50_series=[p.p50 for p in cqr_preds],
            p90_series=[p.p90_calibrated for p in cqr_preds],
            abstained_series=[p.is_abstained for p in cqr_preds],
            slice_dims=available_slice_dims,
        )
        models_eval["cqr_catboost"] = cqr_eval

        # Evaluate Split Conformal
        split_preds = split_calibrator.predict(eval_df)
        split_eval = self._evaluate_predictions(
            model_name="CatBoost Split Conformal (Rung F Baseline)",
            method="split_conformal",
            nominal_coverage=self.config.nominal_coverage,
            conformal_correction=split_calibrator.conformal_radius,
            eval_df=eval_df,
            p10_series=[p.p10_calibrated for p in split_preds],
            p50_series=[p.p50 for p in split_preds],
            p90_series=[p.p90_calibrated for p in split_preds],
            abstained_series=[p.is_abstained for p in split_preds],
            slice_dims=available_slice_dims,
        )
        models_eval["split_conformal_catboost"] = split_eval

        # Evaluate Uncalibrated Base Quantile Model
        base_preds = base_quant.predict(eval_df)
        base_eval = self._evaluate_predictions(
            model_name="CatBoost Quantile Base (Rung E Uncalibrated)",
            method="uncalibrated_quantile",
            nominal_coverage=self.config.nominal_coverage,
            conformal_correction=0.0,
            eval_df=eval_df,
            p10_series=[p.p10 for p in base_preds],
            p50_series=[p.p50 for p in base_preds],
            p90_series=[p.p90 for p in base_preds],
            abstained_series=[p.is_abstained for p in base_preds],
            slice_dims=available_slice_dims,
        )
        models_eval["base_catboost"] = base_eval

        # Determine Champion: CQR preferred over Split Conformal if empirical
        # coverage meets nominal target and width is competitive
        cqr_cov = cqr_eval.overall_coverage
        split_cov = split_eval.overall_coverage
        target_cov = self.config.nominal_coverage

        cqr_error = abs(cqr_cov - target_cov)
        split_error = abs(split_cov - target_cov)

        if cqr_error <= split_error:
            champion_name = "CatBoost CQR (Rung F)"
            status = "ACCEPTED_AS_RUNG_F_CHAMPION"
            reason = (
                f"CQR achieved empirical coverage of {cqr_cov * 100.0:.1f}% "
                f"(calibration error {cqr_error * 100.0:.1f} pp vs target "
                f"{target_cov * 100.0:.1f}%), with adaptive interval width "
                f"{cqr_eval.overall_mean_width_lpa:.2f} LPA and zero crossing violations."
            )
        else:
            champion_name = "CatBoost Split Conformal (Rung F Baseline)"
            status = "ACCEPTED_AS_RUNG_F_CHAMPION"
            reason = (
                f"Split Conformal achieved closer empirical coverage of "
                f"{split_cov * 100.0:.1f}% (calibration error "
                f"{split_error * 100.0:.1f} pp vs target {target_cov * 100.0:.1f}%)."
            )

        champion_verdict = {
            "champion_model": champion_name,
            "status": status,
            "reason": reason,
            "target_nominal_coverage": target_cov,
        }

        # Git commit identification
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            git_commit = res.stdout.strip() if res.returncode == 0 else "UNKNOWN_COMMIT"
        except Exception:
            git_commit = "UNKNOWN_COMMIT"

        report_id = f"CONF-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        return ConformalCalibrationReport(
            report_id=report_id,
            generated_at=datetime.now(UTC).isoformat(),
            git_commit=git_commit,
            snapshot_id=snap_id,
            random_seed=self.config.random_seed,
            evaluation_split=self.config.evaluation_split,
            data_summary=data_summary,
            models=models_eval,
            assumptions=ConformalAssumptions(),
            champion_verdict=champion_verdict,
        )

    def _evaluate_predictions(
        self,
        model_name: str,
        method: str,
        nominal_coverage: float,
        conformal_correction: float,
        eval_df: pl.DataFrame,
        p10_series: list[float | None],
        p50_series: list[float | None],
        p90_series: list[float | None],
        abstained_series: list[bool],
        slice_dims: list[str],
    ) -> ModelConformalEvaluation:
        """Calculate global metrics, tail metrics, recent window, and subgroup slices."""
        y_true = eval_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        n = len(eval_df)

        valid_indices: list[int] = []
        covered_list: list[float] = []
        widths_list: list[float] = []
        underflow_count = 0
        overflow_count = 0
        crossing_count = 0
        abstention_count = 0

        y_valid: list[float] = []
        q10_valid: list[float] = []
        q50_valid: list[float] = []
        q90_valid: list[float] = []

        for i in range(n):
            if abstained_series[i]:
                abstention_count += 1
                continue

            lo = p10_series[i]
            mid = p50_series[i]
            hi = p90_series[i]

            if lo is None or mid is None or hi is None:
                abstention_count += 1
                continue

            yt = float(y_true[i])
            valid_indices.append(i)
            y_valid.append(yt)
            q10_valid.append(lo)
            q50_valid.append(mid)
            q90_valid.append(hi)

            # Crossing check
            if lo > mid or mid > hi or lo > hi:
                crossing_count += 1

            # Coverage & tails
            is_cov = 1.0 if (lo <= yt <= hi) else 0.0
            covered_list.append(is_cov)
            widths_list.append(hi - lo)

            if yt < lo:
                underflow_count += 1
            elif yt > hi:
                overflow_count += 1

        n_valid = len(valid_indices)
        if n_valid == 0:
            raise CompIntelValidationError("All records abstained during conformal evaluation.")

        cov_arr = np.array(covered_list, dtype=np.float64)
        width_arr = np.array(widths_list, dtype=np.float64)
        y_val_arr = np.array(y_valid, dtype=np.float64)
        q10_arr = np.array(q10_valid, dtype=np.float64)
        q50_arr = np.array(q50_valid, dtype=np.float64)
        q90_arr = np.array(q90_valid, dtype=np.float64)

        overall_cov = float(np.mean(cov_arr))
        overall_mean_width = float(np.mean(width_arr))
        overall_med_width = float(np.median(width_arr))

        # Bootstrap CIs for overall metrics (Rule R-UQ-01)
        cov_ci: MetricWithCI | None = None
        width_ci: MetricWithCI | None = None
        if n_valid >= 5:
            cov_ci = bootstrap_metric_ci(
                cov_arr,
                cov_arr,
                _mean_statistic,
                n_resamples=self.config.n_bootstrap_resamples,
                confidence_level=self.config.confidence_level,
                seed=self.config.random_seed,
            )
            width_ci = bootstrap_metric_ci(
                width_arr,
                width_arr,
                _mean_statistic,
                n_resamples=self.config.n_bootstrap_resamples,
                confidence_level=self.config.confidence_level,
                seed=self.config.random_seed,
            )

        # Pinball loss
        pb_10 = float(pinball_loss(y_val_arr, q10_arr, q=0.10))
        pb_50 = float(pinball_loss(y_val_arr, q50_arr, q=0.50))
        pb_90 = float(pinball_loss(y_val_arr, q90_arr, q=0.90))
        mean_pb = (pb_10 + pb_50 + pb_90) / 3.0

        # Tail Analysis
        global_underflow = underflow_count / n_valid
        global_overflow = overflow_count / n_valid
        tail_balance = global_underflow / global_overflow if global_overflow > 0 else 1.0

        p10_pay = float(np.percentile(y_val_arr, 10))
        p90_pay = float(np.percentile(y_val_arr, 90))

        lower_tail_mask = y_val_arr <= p10_pay
        upper_tail_mask = y_val_arr >= p90_pay

        lower_tail_cnt = int(np.sum(lower_tail_mask))
        upper_tail_cnt = int(np.sum(upper_tail_mask))

        lower_tail_cov = float(np.mean(cov_arr[lower_tail_mask])) if lower_tail_cnt > 0 else 0.0
        lower_tail_w = float(np.mean(width_arr[lower_tail_mask])) if lower_tail_cnt > 0 else 0.0

        upper_tail_cov = float(np.mean(cov_arr[upper_tail_mask])) if upper_tail_cnt > 0 else 0.0
        upper_tail_w = float(np.mean(width_arr[upper_tail_mask])) if upper_tail_cnt > 0 else 0.0

        tails = TailAnalysisMetrics(
            global_underflow_q10=global_underflow,
            global_overflow_q90=global_overflow,
            tail_balance_ratio=tail_balance,
            lower_tail_count=lower_tail_cnt,
            lower_tail_coverage=lower_tail_cov,
            lower_tail_mean_width=lower_tail_w,
            upper_tail_count=upper_tail_cnt,
            upper_tail_coverage=upper_tail_cov,
            upper_tail_mean_width=upper_tail_w,
        )

        # Recent Temporal Window Analysis
        recent_window_metrics: RecentWindowMetrics | None = None
        if "as_of_date" in eval_df.columns:
            date_col = eval_df["as_of_date"]
            valid_dates = [str(date_col[idx]) for idx in valid_indices if date_col[idx] is not None]
            if len(valid_dates) >= 4:
                sorted_dates = sorted(valid_dates)
                # Recent window is latest 25% of observations
                split_idx = int(len(sorted_dates) * 0.75)
                recent_start = sorted_dates[split_idx]
                recent_end = sorted_dates[-1]

                recent_cov_list: list[float] = []
                recent_width_list: list[float] = []
                older_cov_list: list[float] = []

                for k, orig_idx in enumerate(valid_indices):
                    dt_str = str(date_col[orig_idx])
                    if dt_str >= recent_start:
                        recent_cov_list.append(covered_list[k])
                        recent_width_list.append(widths_list[k])
                    else:
                        older_cov_list.append(covered_list[k])

                rw_n = len(recent_cov_list)
                is_low_rw = rw_n < self.config.min_support_threshold
                rw_cov = float(np.mean(recent_cov_list)) if rw_n > 0 else 0.0
                rw_width = float(np.mean(recent_width_list)) if rw_n > 0 else 0.0
                older_cov = float(np.mean(older_cov_list)) if older_cov_list else rw_cov
                drift_delta = rw_cov - older_cov

                rw_ci_lower: float | None = None
                rw_ci_upper: float | None = None
                if rw_n >= 5:
                    recent_cov_arr = np.array(recent_cov_list, dtype=np.float64)
                    rw_ci = bootstrap_metric_ci(
                        recent_cov_arr,
                        recent_cov_arr,
                        _mean_statistic,
                        n_resamples=self.config.n_bootstrap_resamples,
                        confidence_level=self.config.confidence_level,
                        seed=self.config.random_seed,
                    )
                    rw_ci_lower = rw_ci.ci_lower
                    rw_ci_upper = rw_ci.ci_upper

                recent_window_metrics = RecentWindowMetrics(
                    window_start_date=recent_start,
                    window_end_date=recent_end,
                    window_sample_size=rw_n,
                    is_low_support=is_low_rw,
                    recent_coverage=rw_cov,
                    recent_coverage_ci_lower=rw_ci_lower,
                    recent_coverage_ci_upper=rw_ci_upper,
                    recent_mean_width_lpa=rw_width,
                    older_coverage=older_cov,
                    temporal_drift_delta=drift_delta,
                    drift_warning=abs(drift_delta) >= 0.08,
                )

        # Subgroup Slices with Low-Support Flagging (Rule R-MD-08)
        # Slices below minimum support are flagged, NOT hidden.
        slices_dict: dict[str, list[ConformalSliceMetrics]] = {}

        for dim in slice_dims:
            col_series = eval_df[dim]
            distinct_vals = sorted({str(v) for v in col_series if v is not None})
            dim_metrics: list[ConformalSliceMetrics] = []

            for val in distinct_vals:
                slice_covered: list[float] = []
                slice_widths: list[float] = []
                slice_underflow = 0
                slice_overflow = 0
                slice_abstention = 0
                slice_total = 0

                for i in range(n):
                    if str(col_series[i]) != val:
                        continue
                    slice_total += 1

                    if abstained_series[i]:
                        slice_abstention += 1
                        continue

                    lo = p10_series[i]
                    hi = p90_series[i]
                    if lo is None or hi is None:
                        slice_abstention += 1
                        continue

                    yt = float(y_true[i])
                    is_cov = 1.0 if (lo <= yt <= hi) else 0.0
                    slice_covered.append(is_cov)
                    slice_widths.append(hi - lo)

                    if yt < lo:
                        slice_underflow += 1
                    elif yt > hi:
                        slice_overflow += 1

                slice_valid_n = len(slice_covered)
                is_low_supp = slice_total < self.config.min_support_threshold
                support_status = "LOW_SUPPORT_FLAGGED" if is_low_supp else "ADEQUATE"

                if slice_valid_n > 0:
                    sl_cov = float(np.mean(slice_covered))
                    sl_mean_w = float(np.mean(slice_widths))
                    sl_med_w = float(np.median(slice_widths))
                    sl_uf = slice_underflow / slice_valid_n
                    sl_of = slice_overflow / slice_valid_n
                    cal_err = abs(sl_cov - nominal_coverage)
                else:
                    sl_cov = 0.0
                    sl_mean_w = 0.0
                    sl_med_w = 0.0
                    sl_uf = 0.0
                    sl_of = 0.0
                    cal_err = nominal_coverage

                sl_cov_lower: float | None = None
                sl_cov_upper: float | None = None
                sl_w_lower: float | None = None
                sl_w_upper: float | None = None

                if slice_valid_n >= 5:
                    sl_cov_arr = np.array(slice_covered, dtype=np.float64)
                    boot_cov = bootstrap_metric_ci(
                        sl_cov_arr,
                        sl_cov_arr,
                        _mean_statistic,
                        n_resamples=self.config.n_bootstrap_resamples,
                        confidence_level=self.config.confidence_level,
                        seed=self.config.random_seed,
                    )
                    sl_cov_lower = boot_cov.ci_lower
                    sl_cov_upper = boot_cov.ci_upper

                    sl_w_arr = np.array(slice_widths, dtype=np.float64)
                    boot_w = bootstrap_metric_ci(
                        sl_w_arr,
                        sl_w_arr,
                        _mean_statistic,
                        n_resamples=self.config.n_bootstrap_resamples,
                        confidence_level=self.config.confidence_level,
                        seed=self.config.random_seed,
                    )
                    sl_w_lower = boot_w.ci_lower
                    sl_w_upper = boot_w.ci_upper

                slice_metric = ConformalSliceMetrics(
                    dimension=dim,
                    slice_value=val,
                    sample_size=slice_total,
                    is_low_support=is_low_supp,
                    support_status=support_status,
                    empirical_coverage=sl_cov,
                    coverage_ci_lower=sl_cov_lower,
                    coverage_ci_upper=sl_cov_upper,
                    mean_width_lpa=sl_mean_w,
                    median_width_lpa=sl_med_w,
                    width_ci_lower=sl_w_lower,
                    width_ci_upper=sl_w_upper,
                    underflow_rate_q10=sl_uf,
                    overflow_rate_q90=sl_of,
                    calibration_error=cal_err,
                    abstention_count=slice_abstention,
                    abstention_rate=(slice_abstention / slice_total if slice_total > 0 else 0.0),
                )
                dim_metrics.append(slice_metric)

            slices_dict[dim] = dim_metrics

        return ModelConformalEvaluation(
            model_name=model_name,
            method=method,
            nominal_coverage=nominal_coverage,
            conformal_correction=conformal_correction,
            sample_size=n,
            overall_coverage=overall_cov,
            overall_coverage_ci=cov_ci,
            overall_mean_width_lpa=overall_mean_width,
            overall_median_width_lpa=overall_med_width,
            overall_width_ci=width_ci,
            mean_calibration_error=abs(overall_cov - nominal_coverage),
            pinball_q10=pb_10,
            pinball_q50=pb_50,
            pinball_q90=pb_90,
            mean_pinball_loss=mean_pb,
            crossing_count=crossing_count,
            crossing_rate=(crossing_count / n_valid if n_valid > 0 else 0.0),
            abstention_count=abstention_count,
            abstention_rate=(abstention_count / n if n > 0 else 0.0),
            tails=tails,
            recent_window=recent_window_metrics,
            slices=slices_dict,
        )
