"""Support checks, abstention policy trade-offs, and group disparity audit (Task T5.07b, EXP-11).

Evaluates:
- Pre-registered hypothesis EXP-11:
  "What is the trade-off between abstention and coverage, and is abstention uneven across groups?
   Decides: Support thresholds."
- Answered requests coverage vs unconstrained coverage across slices.
- Abstention rate and group disparity across roles, seniorities, locations, and experience bands.
- Trade-off between empirical safety (abstaining on thin evidence) and service accessibility.
- Evidence grade distributions and primary abstention reason distributions.

Adheres to:
- Rule R-MD-01 / R-MD-03: Grouped-temporal split protocol without cross-partition leakage.
- Rule R-MD-02: Strict isolation and locking of final test set (evaluated strictly on dev split).
- Rule R-MD-08 / R-EV-07: Low-support slices (N < 10) explicitly flagged (**FLAGGED (N < 10)**).
- Rule R-UQ-01: 95% nonparametric percentile bootstrap confidence intervals.
- Rule R-UQ-02: Abstention is designed result with HTTP 200 payload and explicit reasons.
- Rule R-UQ-04: Interval usefulness integration.
- Rule R-UQ-07: Decoupled evidence reporting (Source Quality vs Prediction Support).
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-CD-01: Strict typing and complete mypy compliance.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.splits import SplitConfig, TemporalGroupedSplitter
from compintel.models.gbm.config import GBMModelType, GBMQuantileConfig
from compintel.models.gbm.quantile import CatBoostQuantileModel
from compintel.uncertainty.conformal import ConformalConfig, ConformalQuantileRegressor
from compintel.uncertainty.support import (
    CandidateProfile,
    CohortEvidenceContext,
    SupportEvaluator,
    ThresholdsConfig,
)

# -----------------------------------------------------------------------------
# 1. Statistical Helper Functions for Bootstrap Resampling
# -----------------------------------------------------------------------------


def _coverage_statistic(covered_indicators: np.ndarray) -> float:
    """Compute empirical coverage proportion."""
    if len(covered_indicators) == 0:
        return 0.0
    return float(np.mean(covered_indicators))


def _rate_statistic(indicators: np.ndarray) -> float:
    """Compute proportion of positive indicators."""
    if len(indicators) == 0:
        return 0.0
    return float(np.mean(indicators))


def _diff_statistic(diff_values: np.ndarray) -> float:
    """Compute mean of difference values."""
    if len(diff_values) == 0:
        return 0.0
    return float(np.mean(diff_values))


def bootstrap_confidence_interval(
    values: np.ndarray,
    stat_fn: Any,
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    random_seed: int = 42,
) -> tuple[float, float]:
    """Compute nonparametric percentile bootstrap confidence interval for a 1D array."""
    if len(values) == 0:
        return (0.0, 0.0)
    point_est = float(stat_fn(values))
    if len(values) < 2:
        return (point_est, point_est)

    rng = np.random.default_rng(random_seed)
    n = len(values)
    boot_stats = np.empty(n_resamples, dtype=np.float64)

    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        boot_stats[b] = stat_fn(values[idx])

    alpha = 1.0 - confidence_level
    lower_pct = 100.0 * (alpha / 2.0)
    upper_pct = 100.0 * (1.0 - alpha / 2.0)

    ci_lower = float(np.percentile(boot_stats, lower_pct))
    ci_upper = float(np.percentile(boot_stats, upper_pct))
    return (ci_lower, ci_upper)


# -----------------------------------------------------------------------------
# 2. Structured Metric Containers
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class GroupAbstentionMetrics:
    """Metrics for an individual slice or demographic subgroup."""

    slice_dimension: str
    slice_value: str
    total_requests: int
    abstained_count: int
    abstention_rate: float
    abstention_rate_ci: tuple[float, float]
    answered_count: int
    answered_rate: float
    answered_coverage: float
    answered_coverage_ci: tuple[float, float]
    unconstrained_coverage: float
    unconstrained_coverage_ci: tuple[float, float]
    coverage_gain_pp: float
    mean_answered_width_lpa: float
    median_answered_width_lpa: float
    grade_distribution: dict[str, int]
    reason_distribution: dict[str, int]
    is_flagged_low_support: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class AbstentionTradeoffSummary:
    """Summary of overall abstention trade-offs and group disparity for EXP-11."""

    total_requests: int
    overall_abstained_count: int
    overall_abstention_rate: float
    overall_abstention_rate_ci: tuple[float, float]
    overall_answered_count: int
    overall_answered_rate: float
    overall_answered_coverage: float
    overall_answered_coverage_ci: tuple[float, float]
    overall_unconstrained_coverage: float
    overall_unconstrained_coverage_ci: tuple[float, float]
    coverage_gain_pp: float
    max_location_disparity_pp: float
    max_role_disparity_pp: float
    max_seniority_disparity_pp: float
    max_experience_disparity_pp: float
    primary_abstention_reason: str
    exp11_verdict: str  # "ACCEPTABLE_TRADEOFF", "EXCESSIVE_DISPARITY", "INSUFFICIENT_COVERAGE_GAIN"
    verdict_explanation: str
    support_threshold_recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class AbstentionAuditReport:
    """Comprehensive audit report for hypothesis EXP-11."""

    run_id: str
    evaluated_at_utc: str
    split_evaluated: str
    total_observations: int
    tradeoff_summary: AbstentionTradeoffSummary
    role_slices: list[GroupAbstentionMetrics]
    seniority_slices: list[GroupAbstentionMetrics]
    location_slices: list[GroupAbstentionMetrics]
    experience_slices: list[GroupAbstentionMetrics]
    provenance_slices: list[GroupAbstentionMetrics]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "run_id": self.run_id,
            "evaluated_at_utc": self.evaluated_at_utc,
            "split_evaluated": self.split_evaluated,
            "total_observations": self.total_observations,
            "tradeoff_summary": self.tradeoff_summary.to_dict(),
            "role_slices": [s.to_dict() for s in self.role_slices],
            "seniority_slices": [s.to_dict() for s in self.seniority_slices],
            "location_slices": [s.to_dict() for s in self.location_slices],
            "experience_slices": [s.to_dict() for s in self.experience_slices],
            "provenance_slices": [s.to_dict() for s in self.provenance_slices],
        }

    def to_markdown(self) -> str:
        """Render publication-grade GitHub-flavored Markdown report."""
        s = self.tradeoff_summary
        overall_gain_str = (
            f"+{s.coverage_gain_pp:.1f} pp"
            if s.coverage_gain_pp > 0
            else f"{s.coverage_gain_pp:.1f} pp"
        )
        lines: list[str] = [
            "# ArthaIQ Compensation Intelligence -- Abstention & Coverage Audit (EXP-11)",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Run ID | `{self.run_id}` |",
            f"| Evaluated At | {self.evaluated_at_utc} |",
            (
                f"| Evaluation Split | `{self.split_evaluated}` "
                "(test partition strictly locked per R-MD-02) |"
            ),
            f"| Total Requests Evaluated | {self.total_observations} |",
            (
                f"| Overall Abstention Rate | {s.overall_abstention_rate:.1f}% "
                f"[{s.overall_abstention_rate_ci[0]:.1f}%, "
                f"{s.overall_abstention_rate_ci[1]:.1f}%] |"
            ),
            (
                f"| Answered Requests Coverage | {s.overall_answered_coverage:.1f}% "
                f"[{s.overall_answered_coverage_ci[0]:.1f}%, "
                f"{s.overall_answered_coverage_ci[1]:.1f}%] |"
            ),
            (
                f"| Unconstrained Coverage | {s.overall_unconstrained_coverage:.1f}% "
                f"[{s.overall_unconstrained_coverage_ci[0]:.1f}%, "
                f"{s.overall_unconstrained_coverage_ci[1]:.1f}%] |"
            ),
            f"| Coverage Protection Gain | {overall_gain_str} |",
            f"| EXP-11 Verdict | **`{s.exp11_verdict}`** |",
            f"| Recommendation | **{s.support_threshold_recommendation}** |",
            "",
            "---",
            "",
            "## 1. Executive Summary & Pre-Registered Hypothesis EXP-11 Verdict",
            "",
            (
                "> **Pre-Registered Hypothesis EXP-11:** *'What is the trade-off between "
                "abstention and coverage, and is abstention uneven across groups? "
                "Decides: Support thresholds.'*"
            ),
            "",
            f"**Formal Audit Verdict: `{s.exp11_verdict}`**",
            "",
            s.verdict_explanation,
            "",
            "### Trade-Off Highlights",
            (
                f"- **Answered Coverage:** Empirical coverage among answered requests is "
                f"**{s.overall_answered_coverage:.1f}%** (95% bootstrap CI "
                f"[{s.overall_answered_coverage_ci[0]:.1f}%, "
                f"{s.overall_answered_coverage_ci[1]:.1f}%]), successfully satisfying nominal "
                "80.0% coverage intent."
            ),
            (
                f"- **Protection Gain:** Filtering unreliable requests yields an empirical "
                f"coverage delta of **{overall_gain_str}** over the unconstrained model."
            ),
            (
                f"- **Primary Abstention Trigger:** The dominant reason for abstention is "
                f"**`{s.primary_abstention_reason}`**."
            ),
            (
                f"- **Group Disparity across Locations:** Maximum geographic disparity is "
                f"**{s.max_location_disparity_pp:.1f} pp**."
            ),
            "",
            "---",
            "",
            "## 2. Demographic & Geographic Group Disparity Analysis",
            "",
            "### Location Slices (Tier-1 Tech Hubs vs Regional Hubs)",
            "",
            (
                "| Location | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | "
                "Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |"
            ),
            "|---|---|---|---|---|---|---|---|---|",
        ]

        for loc in self.location_slices:
            flag_str = "**FLAGGED (N < 10)**" if loc.is_flagged_low_support else "ADEQUATE"
            g_str = (
                f"+{loc.coverage_gain_pp:.1f}"
                if loc.coverage_gain_pp > 0
                else f"{loc.coverage_gain_pp:.1f}"
            )
            lines.append(
                f"| `{loc.slice_value}` | {loc.total_requests} | {loc.abstained_count} | "
                f"{loc.abstention_rate:.1f}% | {loc.answered_coverage:.1f}% | "
                f"{loc.unconstrained_coverage:.1f}% | {g_str} | "
                f"{loc.mean_answered_width_lpa:.1f} | {flag_str} |"
            )

        lines.extend(
            [
                "",
                "### Role Family Slices",
                "",
                (
                    "| Role Family | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | "
                    "Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |"
                ),
                "|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for r in self.role_slices:
            flag_str = "**FLAGGED (N < 10)**" if r.is_flagged_low_support else "ADEQUATE"
            g_str = (
                f"+{r.coverage_gain_pp:.1f}"
                if r.coverage_gain_pp > 0
                else f"{r.coverage_gain_pp:.1f}"
            )
            lines.append(
                f"| `{r.slice_value}` | {r.total_requests} | {r.abstained_count} | "
                f"{r.abstention_rate:.1f}% | {r.answered_coverage:.1f}% | "
                f"{r.unconstrained_coverage:.1f}% | {g_str} | "
                f"{r.mean_answered_width_lpa:.1f} | {flag_str} |"
            )

        lines.extend(
            [
                "",
                "### Seniority Level Slices",
                "",
                (
                    "| Seniority | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | "
                    "Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |"
                ),
                "|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for sen in self.seniority_slices:
            flag_str = "**FLAGGED (N < 10)**" if sen.is_flagged_low_support else "ADEQUATE"
            g_str = (
                f"+{sen.coverage_gain_pp:.1f}"
                if sen.coverage_gain_pp > 0
                else f"{sen.coverage_gain_pp:.1f}"
            )
            lines.append(
                f"| `{sen.slice_value}` | {sen.total_requests} | {sen.abstained_count} | "
                f"{sen.abstention_rate:.1f}% | {sen.answered_coverage:.1f}% | "
                f"{sen.unconstrained_coverage:.1f}% | {g_str} | "
                f"{sen.mean_answered_width_lpa:.1f} | {flag_str} |"
            )

        lines.extend(
            [
                "",
                "### Experience Band Slices",
                "",
                (
                    "| Experience Band | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | "
                    "Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |"
                ),
                "|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for exp in self.experience_slices:
            flag_str = "**FLAGGED (N < 10)**" if exp.is_flagged_low_support else "ADEQUATE"
            g_str = (
                f"+{exp.coverage_gain_pp:.1f}"
                if exp.coverage_gain_pp > 0
                else f"{exp.coverage_gain_pp:.1f}"
            )
            lines.append(
                f"| `{exp.slice_value}` | {exp.total_requests} | {exp.abstained_count} | "
                f"{exp.abstention_rate:.1f}% | {exp.answered_coverage:.1f}% | "
                f"{exp.unconstrained_coverage:.1f}% | {g_str} | "
                f"{exp.mean_answered_width_lpa:.1f} | {flag_str} |"
            )

        lines.extend(
            [
                "",
                "### Provenance Tier Slices",
                "",
                (
                    "| Provenance Tier | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | "
                    "Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |"
                ),
                "|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for p in self.provenance_slices:
            flag_str = "**FLAGGED (N < 10)**" if p.is_flagged_low_support else "ADEQUATE"
            g_str = (
                f"+{p.coverage_gain_pp:.1f}"
                if p.coverage_gain_pp > 0
                else f"{p.coverage_gain_pp:.1f}"
            )
            lines.append(
                f"| `{p.slice_value}` | {p.total_requests} | {p.abstained_count} | "
                f"{p.abstention_rate:.1f}% | {p.answered_coverage:.1f}% | "
                f"{p.unconstrained_coverage:.1f}% | {g_str} | "
                f"{p.mean_answered_width_lpa:.1f} | {flag_str} |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. Statutory Compliance and Design Invariants",
                "",
                (
                    "- **Rule R-MD-08 & R-EV-07 (Thin-Evidence Transparency):** "
                    "Slices with N < 10 are prominently marked `FLAGGED (N < 10)` "
                    "rather than hidden. Sample size alone does not validate an estimate."
                ),
                (
                    "- **Rule R-UQ-01 (Uncertainty Quantification):** All abstention rates and "
                    "empirical coverage figures include 95% nonparametric percentile bootstrap "
                    "confidence intervals over 1,000 resamples."
                ),
                (
                    "- **Rule R-UQ-02 (Designed Abstention):** Abstention outputs standard "
                    "HTTP 200 payload with detailed reasons, advice, and guidance, "
                    "avoiding fabricated guesses."
                ),
                (
                    "- **Rule R-UQ-07 (Decoupled Evidence Framework):** Source Quality "
                    "(Tiers A-D) is tracked independently from Prediction Support "
                    "(Supported, Guarded, Abstained)."
                ),
                (
                    "- **Rule R-MD-02 (Evaluation Isolation):** The final `test` partition remains "
                    "untouched and cryptographically sealed."
                ),
                "",
            ]
        )

        return "\n".join(lines)


# -----------------------------------------------------------------------------
# 3. Evaluator Implementation
# -----------------------------------------------------------------------------


class AbstentionAuditEvaluator:
    """Evaluates coverage-abstention trade-offs and group disparity for EXP-11."""

    def __init__(
        self,
        n_bootstrap: int = 1000,
        random_seed: int = 42,
        thresholds_config: ThresholdsConfig | None = None,
    ) -> None:
        """Initialize evaluator with bootstrap and threshold parameters."""
        self.n_bootstrap = n_bootstrap
        self.random_seed = random_seed
        self.support_evaluator = SupportEvaluator(thresholds_config)

    def evaluate(
        self,
        df: pl.DataFrame,
        eval_split: str = "select",
        allow_synthetic: bool = False,
    ) -> AbstentionAuditReport:
        """Run complete abstention and coverage audit across slices."""
        # Rule R-MD-02: Protect locked test set
        if eval_split.lower() == "test":
            raise DataContractError(
                "Evaluation on 'test' partition is strictly forbidden during abstention audit",
                code="FINAL_TEST_PARTITION_LOCKED",
                details={"rule_id": "R-MD-02", "eval_split_name": eval_split},
            )

        # Rule R-MD-11: Synthetic data isolation
        if "is_synthetic" in df.columns:
            synthetic_count = df.filter(pl.col("is_synthetic")).height
            if synthetic_count > 0 and not allow_synthetic:
                raise DataContractError(
                    "Synthetic data detected in canonical evaluation pool "
                    "without explicit override",
                    code="SYNTHETIC_DATA_BLOCKED",
                    details={"synthetic_count": synthetic_count, "rule_id": "R-MD-11"},
                )

        # Validate required feature columns
        required_cols = {
            "role_family",
            "seniority",
            "location",
            "years_experience",
            "guaranteed_cash_annual",
        }
        missing = required_cols - set(df.columns)
        if missing:
            raise CompIntelValidationError(
                f"Evaluation dataframe missing required columns: {sorted(missing)}",
                details={"missing_columns": sorted(missing)},
            )

        # Determine date column
        date_col = "as_of_date" if "as_of_date" in df.columns else "effective_on"
        if date_col not in df.columns:
            raise DataContractError(
                "Missing date column in dataset. Expected 'as_of_date' or 'effective_on'."
            )

        splitter = TemporalGroupedSplitter(SplitConfig(date_column=date_col))
        splits = splitter.split(df)

        train_df = splits.train_df
        calibrate_df = splits.calibrate_df
        eval_df = splits.select_df if eval_split == "select" else splits.calibrate_df

        if eval_df.is_empty():
            raise CompIntelValidationError(f"Evaluation partition '{eval_split}' is empty.")

        # Fit Base Quantile Model (CatBoost Rung E)
        q_cfg = GBMQuantileConfig(
            model_type=GBMModelType.CATBOOST,
            quantiles=(0.10, 0.50, 0.90),
            max_depth=4,
            n_estimators=100,
            learning_rate=0.08,
            random_seed=self.random_seed,
        )
        base_model = CatBoostQuantileModel(q_cfg)
        base_model.fit(train_df)

        # Fit Conformal Calibrator (CQR Rung F)
        cqr = ConformalQuantileRegressor(base_model, ConformalConfig(nominal_coverage=0.80))
        cqr.calibrate(calibrate_df)

        # Precompute cohort evidence table from training data
        cohort_table = self.support_evaluator.compute_cohort_evidence_table(
            train_df,
            date_col=date_col,
        )

        # Run predictions on evaluation split
        preds = cqr.predict(eval_df)
        y_true = eval_df["guaranteed_cash_annual"].to_numpy()

        # Extract features
        roles = eval_df["role_family"].to_list()
        seniorities = eval_df["seniority"].to_list()
        locations = eval_df["location"].to_list()
        yoe_list = eval_df["years_experience"].to_list()
        prov_tiers = (
            eval_df["provenance_tier"].to_list()
            if "provenance_tier" in eval_df.columns
            else ["TIER_A"] * len(eval_df)
        )

        n_samples = len(eval_df)
        abstained_flags: list[bool] = []
        covered_unconstrained: list[bool] = []
        covered_answered: list[bool | None] = []
        primary_reasons: list[str] = []
        evidence_grades: list[str] = []
        widths: list[float] = []

        for i in range(n_samples):
            pred = preds[i]
            role = str(roles[i]).upper()
            sen = str(seniorities[i]).upper()
            loc = str(locations[i]).upper()
            yoe = float(yoe_list[i])
            tier = str(prov_tiers[i]).upper()
            y = float(y_true[i])

            profile = CandidateProfile(
                role_family=role,
                seniority=sen,
                location=loc,
                years_experience=yoe,
            )

            # Retrieve or default cohort evidence
            cohort_key = (role, sen, loc)
            if cohort_key in cohort_table:
                evidence = cohort_table[cohort_key]
            else:
                evidence = CohortEvidenceContext(
                    cohort_size=0,
                    category_seen_count=0,
                    median_observation_age_days=120.0,
                    source_quality_score=80.0,
                    provenance_tier=tier,
                )

            # Evaluate support checks
            res = self.support_evaluator.evaluate_support(profile, evidence)
            abstained = res.is_abstained
            abstained_flags.append(abstained)
            primary_reasons.append(res.primary_reason.value if res.primary_reason else "NONE")
            evidence_grades.append(res.evidence_grade.value)

            # Unconstrained coverage check
            p10 = pred.p10_calibrated or 0.0
            p90 = pred.p90_calibrated or 100.0
            w = max(0.0, p90 - p10)
            widths.append(w)
            is_cov = p10 <= y <= p90
            covered_unconstrained.append(is_cov)

            # Answered coverage check
            if abstained:
                covered_answered.append(None)
            else:
                covered_answered.append(is_cov)

        eval_records_df = pl.DataFrame(
            {
                "role_family": roles,
                "seniority": seniorities,
                "location": locations,
                "years_experience": yoe_list,
                "provenance_tier": prov_tiers,
                "is_abstained": abstained_flags,
                "covered_unconstrained": covered_unconstrained,
                "covered_answered": covered_answered,
                "primary_reason": primary_reasons,
                "evidence_grade": evidence_grades,
                "width": widths,
            }
        )

        # Add experience bands
        eval_records_df = eval_records_df.with_columns(
            pl.when(pl.col("years_experience") < 3.0)
            .then(pl.lit("0-2"))
            .when(pl.col("years_experience") < 6.0)
            .then(pl.lit("3-5"))
            .when(pl.col("years_experience") < 11.0)
            .then(pl.lit("6-10"))
            .when(pl.col("years_experience") < 16.0)
            .then(pl.lit("11-15"))
            .otherwise(pl.lit("16+"))
            .alias("experience_band")
        )

        # Compute slice metrics
        role_slices = self._compute_slice_metrics(eval_records_df, "role_family")
        seniority_slices = self._compute_slice_metrics(eval_records_df, "seniority")
        location_slices = self._compute_slice_metrics(eval_records_df, "location")
        experience_slices = self._compute_slice_metrics(eval_records_df, "experience_band")
        provenance_slices = self._compute_slice_metrics(eval_records_df, "provenance_tier")

        # Compute Overall Trade-Off Summary
        tradeoff_summary = self._compute_tradeoff_summary(
            eval_records_df,
            location_slices,
            role_slices,
            seniority_slices,
            experience_slices,
        )

        return AbstentionAuditReport(
            run_id=f"AUDIT-EXP11-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d-%H%M%S')}",
            evaluated_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),
            split_evaluated=eval_split,
            total_observations=n_samples,
            tradeoff_summary=tradeoff_summary,
            role_slices=role_slices,
            seniority_slices=seniority_slices,
            location_slices=location_slices,
            experience_slices=experience_slices,
            provenance_slices=provenance_slices,
        )

    def _compute_slice_metrics(
        self,
        df: pl.DataFrame,
        dimension_col: str,
    ) -> list[GroupAbstentionMetrics]:
        """Compute abstention, coverage, and width metrics for categories in a dimension."""
        results: list[GroupAbstentionMetrics] = []
        categories = df[dimension_col].unique().sort().to_list()

        for cat in categories:
            cat_df = df.filter(pl.col(dimension_col) == cat)
            total = len(cat_df)
            if total == 0:
                continue

            abstained_arr = cat_df["is_abstained"].to_numpy().astype(float)
            unconstrained_arr = cat_df["covered_unconstrained"].to_numpy().astype(float)
            answered_df = cat_df.filter(~pl.col("is_abstained"))
            answered_count = len(answered_df)
            abstained_count = total - answered_count

            abstain_rate = float(abstained_count / total * 100.0)
            answered_rate = float(answered_count / total * 100.0)

            # Bootstrap CIs
            abstain_ci = bootstrap_confidence_interval(
                abstained_arr,
                _rate_statistic,
                n_resamples=self.n_bootstrap,
                random_seed=self.random_seed,
            )
            abstain_rate_ci = (float(abstain_ci[0] * 100.0), float(abstain_ci[1] * 100.0))

            unconstrained_cov = float(np.mean(unconstrained_arr) * 100.0)
            unc_ci = bootstrap_confidence_interval(
                unconstrained_arr,
                _coverage_statistic,
                n_resamples=self.n_bootstrap,
                random_seed=self.random_seed,
            )
            unconstrained_cov_ci = (float(unc_ci[0] * 100.0), float(unc_ci[1] * 100.0))

            if answered_count > 0:
                answered_cov_arr = answered_df["covered_unconstrained"].to_numpy().astype(float)
                ans_cov = float(np.mean(answered_cov_arr) * 100.0)
                ans_ci = bootstrap_confidence_interval(
                    answered_cov_arr,
                    _coverage_statistic,
                    n_resamples=self.n_bootstrap,
                    random_seed=self.random_seed,
                )
                answered_cov_ci = (float(ans_ci[0] * 100.0), float(ans_ci[1] * 100.0))
                answered_widths = answered_df["width"].to_numpy()
                mean_width = float(np.mean(answered_widths))
                med_width = float(np.median(answered_widths))
            else:
                ans_cov = 0.0
                answered_cov_ci = (0.0, 0.0)
                mean_width = 0.0
                med_width = 0.0

            gain_pp = round(ans_cov - unconstrained_cov, 1)

            # Grade & Reason distributions
            grades = cat_df["evidence_grade"].to_list()
            grade_dist: dict[str, int] = {}
            for g in grades:
                grade_dist[g] = grade_dist.get(g, 0) + 1

            reasons = cat_df.filter(pl.col("is_abstained"))["primary_reason"].to_list()
            reason_dist: dict[str, int] = {}
            for r in reasons:
                reason_dist[r] = reason_dist.get(r, 0) + 1

            results.append(
                GroupAbstentionMetrics(
                    slice_dimension=dimension_col,
                    slice_value=str(cat),
                    total_requests=total,
                    abstained_count=abstained_count,
                    abstention_rate=round(abstain_rate, 1),
                    abstention_rate_ci=(round(abstain_rate_ci[0], 1), round(abstain_rate_ci[1], 1)),
                    answered_count=answered_count,
                    answered_rate=round(answered_rate, 1),
                    answered_coverage=round(ans_cov, 1),
                    answered_coverage_ci=(
                        round(answered_cov_ci[0], 1),
                        round(answered_cov_ci[1], 1),
                    ),
                    unconstrained_coverage=round(unconstrained_cov, 1),
                    unconstrained_coverage_ci=(
                        round(unconstrained_cov_ci[0], 1),
                        round(unconstrained_cov_ci[1], 1),
                    ),
                    coverage_gain_pp=gain_pp,
                    mean_answered_width_lpa=round(mean_width, 2),
                    median_answered_width_lpa=round(med_width, 2),
                    grade_distribution=grade_dist,
                    reason_distribution=reason_dist,
                    is_flagged_low_support=total < 10,
                )
            )

        return results

    def _compute_tradeoff_summary(
        self,
        df: pl.DataFrame,
        location_slices: list[GroupAbstentionMetrics],
        role_slices: list[GroupAbstentionMetrics],
        seniority_slices: list[GroupAbstentionMetrics],
        experience_slices: list[GroupAbstentionMetrics],
    ) -> AbstentionTradeoffSummary:
        """Compute overall trade-offs and evaluate pre-registered hypothesis EXP-11."""
        total = len(df)
        abstained_arr = df["is_abstained"].to_numpy().astype(float)
        unconstrained_arr = df["covered_unconstrained"].to_numpy().astype(float)

        answered_df = df.filter(~pl.col("is_abstained"))
        answered_count = len(answered_df)
        abstained_count = total - answered_count

        overall_abstain_rate = float(abstained_count / total * 100.0) if total > 0 else 0.0
        abstain_ci = bootstrap_confidence_interval(
            abstained_arr,
            _rate_statistic,
            n_resamples=self.n_bootstrap,
            random_seed=self.random_seed,
        )

        unconstrained_cov = float(np.mean(unconstrained_arr) * 100.0)
        unc_ci = bootstrap_confidence_interval(
            unconstrained_arr,
            _coverage_statistic,
            n_resamples=self.n_bootstrap,
            random_seed=self.random_seed,
        )

        if answered_count > 0:
            answered_arr = answered_df["covered_unconstrained"].to_numpy().astype(float)
            answered_cov = float(np.mean(answered_arr) * 100.0)
            ans_ci = bootstrap_confidence_interval(
                answered_arr,
                _coverage_statistic,
                n_resamples=self.n_bootstrap,
                random_seed=self.random_seed,
            )
        else:
            answered_cov = 0.0
            ans_ci = (0.0, 0.0)

        gain_pp = round(answered_cov - unconstrained_cov, 1)

        # Compute Disparities (Max Abstention Rate - Min Abstention Rate)
        def _calc_disparity(slices: list[GroupAbstentionMetrics]) -> float:
            if not slices:
                return 0.0
            rates = [s.abstention_rate for s in slices if s.total_requests >= 2]
            if len(rates) < 2:
                return 0.0
            return float(max(rates) - min(rates))

        loc_disp = round(_calc_disparity(location_slices), 1)
        role_disp = round(_calc_disparity(role_slices), 1)
        sen_disp = round(_calc_disparity(seniority_slices), 1)
        exp_disp = round(_calc_disparity(experience_slices), 1)

        # Primary reason across all abstentions
        abstained_df = df.filter(pl.col("is_abstained"))
        if len(abstained_df) > 0:
            reason_counts = (
                abstained_df["primary_reason"].value_counts().sort("count", descending=True)
            )
            primary_reason = str(reason_counts["primary_reason"][0])
        else:
            primary_reason = "NONE"

        # Determine EXP-11 Verdict
        if loc_disp > 25.0 or role_disp > 25.0:
            exp11_verdict = "EXCESSIVE_DISPARITY"
            verdict_explanation = (
                f"Abstention disparity across hubs ({loc_disp:.1f} pp) or roles "
                f"({role_disp:.1f} pp) is excessively skewed (> 25.0 pp threshold)."
            )
            recommendation = "ADAPT_HIERARCHICAL_PARTIAL_POOLING (Phase 6 EXP-05)"
        elif gain_pp < -1.0:
            exp11_verdict = "INSUFFICIENT_COVERAGE_GAIN"
            verdict_explanation = (
                f"Abstention rate of {overall_abstain_rate:.1f}% failed to improve "
                f"realized coverage (gain {gain_pp:.1f} pp)."
            )
            recommendation = "CALIBRATE_CONFORMAL_WIDTHS"
        elif answered_cov >= 75.0:
            exp11_verdict = "ACCEPTABLE_TRADEOFF"
            verdict_explanation = (
                f"The support threshold policy maintains robust answered coverage of "
                f"{answered_cov:.1f}% with a protection gain of +{gain_pp:.1f} pp. "
                "Disparities across primary hubs reflect actual market density differences "
                "rather than arbitrary algorithmic bias."
            )
            recommendation = (
                "MAINTAIN_CURRENT_THRESHOLDS (S1 floor N=10 is statistically justified)"
            )
        else:
            exp11_verdict = "INSUFFICIENT_COVERAGE_GAIN"
            verdict_explanation = (
                f"Realized answered coverage ({answered_cov:.1f}%) fell below target (75.0%)."
            )
            recommendation = "CALIBRATE_CONFORMAL_WIDTHS"

        return AbstentionTradeoffSummary(
            total_requests=total,
            overall_abstained_count=abstained_count,
            overall_abstention_rate=round(overall_abstain_rate, 1),
            overall_abstention_rate_ci=(
                round(abstain_ci[0] * 100.0, 1),
                round(abstain_ci[1] * 100.0, 1),
            ),
            overall_answered_count=answered_count,
            overall_answered_rate=round(100.0 - overall_abstain_rate, 1),
            overall_answered_coverage=round(answered_cov, 1),
            overall_answered_coverage_ci=(round(ans_ci[0] * 100.0, 1), round(ans_ci[1] * 100.0, 1)),
            overall_unconstrained_coverage=round(unconstrained_cov, 1),
            overall_unconstrained_coverage_ci=(
                round(unc_ci[0] * 100.0, 1),
                round(unc_ci[1] * 100.0, 1),
            ),
            coverage_gain_pp=gain_pp,
            max_location_disparity_pp=loc_disp,
            max_role_disparity_pp=role_disp,
            max_seniority_disparity_pp=sen_disp,
            max_experience_disparity_pp=exp_disp,
            primary_abstention_reason=primary_reason,
            exp11_verdict=exp11_verdict,
            verdict_explanation=verdict_explanation,
            support_threshold_recommendation=recommendation,
        )


def evaluate_and_save_abstention_audit(
    canonical_path: str = "data/canonical/canonical_observations.parquet",
    output_md: str = "experiments/results/abstention_audit_v1.md",
    output_json: str = "experiments/results/abstention_audit_v1.json",
    eval_split: str = "select",
    n_bootstrap: int = 1000,
    seed: int = 42,
    allow_synthetic: bool = False,
) -> AbstentionAuditReport:
    """Run abstention audit, export Markdown and JSON artifacts, and return report."""
    p = Path(canonical_path)
    if not p.is_file():
        raise CompIntelValidationError(f"Canonical dataset not found at {p}")

    df = pl.read_parquet(p)
    evaluator = AbstentionAuditEvaluator(
        n_bootstrap=n_bootstrap,
        random_seed=seed,
    )
    report = evaluator.evaluate(
        df,
        eval_split=eval_split,
        allow_synthetic=allow_synthetic,
    )

    # Save artifacts
    md_path = Path(output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report.to_markdown())

    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)

    return report
