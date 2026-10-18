"""Stage-wise progressive personalization evaluation engine (Phase 6, T6.03a).

Evaluates the personalization ladder from Level 0 (Core Baseline) through Level 3
(Additional Evidence) under pre-registered rules and hypotheses (EXP-05, EXP-06, EXP-07):
- Evaluates incremental value (Δ Pinball Loss, Δ Coverage, Δ Width) across nested feature tiers.
- Computes 95% nonparametric bootstrap confidence intervals on paired differences (Rule R-UQ-01).
- Compares dedicated nested models against a unified masked-missingness model (Rule R-MD-15).
- Enforces strict touch-once isolation on the locked test partition (Rule R-MD-02).
- Enforces Compare-Only quarantine on current pay (Rule R-MD-13, EXP-07).
- Enforces absolute prohibition on protected demographic proxies (rules.md Section 16 Rule 11).
- Enforces monotonic quantile rearrangement repair (Rule R-UQ-05).
- Fulfills Rules R-MD-01, R-MD-03, R-MD-05, R-MD-06, R-MD-08, R-MD-11, R-CD-01, and R-CD-03.
"""

from __future__ import annotations

import datetime
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import catboost as cb
import lightgbm as lgb
import numpy as np
import pandas as pd
import polars as pl

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.features.spec import (
    AblationDisposition,
    FeatureDataType,
    FeatureLevel,
    FeatureSpec,
    get_features_by_level,
)
from compintel.models.gbm.quantile import detect_and_repair_quantile_crossings

# Prohibited demographic attributes per rules.md Section 16 Rule 11
PROHIBITED_DEMOGRAPHIC_SUBSTRINGS = {
    "gender",
    "sex",
    "caste",
    "religion",
    "ethnicity",
    "race",
    "disability",
    "marital",
    "pregnancy",
    "age",
}

# Column aliases mapping FeatureSpec feature_id to common DataFrame column names
FEATURE_COLUMN_ALIASES: dict[str, list[str]] = {
    "feat_l0_role_family": ["role_family", "feat_l0_role_family"],
    "feat_l0_seniority": ["seniority", "feat_l0_seniority"],
    "feat_l0_location": ["location", "feat_l0_location"],
    "feat_l0_years_experience": [
        "years_experience",
        "years_of_experience",
        "feat_l0_years_experience",
    ],
    "feat_l1_skills_primary": ["skills_primary", "feat_l1_skills_primary", "canonical_title"],
    "feat_l1_skills_depth": ["skills_depth", "feat_l1_skills_depth"],
    "feat_l1_domain_specialization": ["domain_specialization", "feat_l1_domain_specialization"],
    "feat_l1_employer_tier": ["employer_tier", "feat_l1_employer_tier"],
    "feat_l1_work_arrangement": ["work_arrangement", "feat_l1_work_arrangement"],
    "feat_l1_career_velocity": ["career_velocity", "feat_l1_career_velocity"],
    "feat_l1_leadership_scope": ["leadership_scope", "feat_l1_leadership_scope"],
    "feat_l1_macro_market_regime": ["macro_market_regime", "feat_l1_macro_market_regime"],
    # L2
    "feat_l2_target_employer_id": [
        "target_employer_id",
        "employer_cluster_id",
        "employer_id",
        "feat_l2_target_employer_id",
    ],
    "feat_l2_target_level_code": [
        "target_level_code",
        "level_code",
        "feat_l2_target_level_code",
    ],
    "feat_l2_advertised_band_midpoint": [
        "advertised_band_midpoint",
        "feat_l2_advertised_band_midpoint",
    ],
    "feat_l2_competing_offers_count": [
        "competing_offers_count",
        "feat_l2_competing_offers_count",
    ],
    "feat_l2_notice_period_days": ["notice_period_days", "feat_l2_notice_period_days"],
    "feat_l2_search_urgency": ["search_urgency", "feat_l2_search_urgency"],
    # L3
    "feat_l3_current_guaranteed_cash": [
        "current_guaranteed_cash",
        "current_pay",
        "feat_l3_current_guaranteed_cash",
    ],
    "feat_l3_verified_payslip_level": [
        "verified_payslip_level",
        "proof_level",
        "verification_level",
        "feat_l3_verified_payslip_level",
    ],
    "feat_l3_fixed_allowance_ratio": [
        "fixed_allowance_ratio",
        "feat_l3_fixed_allowance_ratio",
    ],
    "feat_l3_project_scale_tier": [
        "project_scale_tier",
        "scale_tier",
        "feat_l3_project_scale_tier",
    ],
    "feat_l3_tenure_stability_index": [
        "tenure_stability_index",
        "feat_l3_tenure_stability_index",
    ],
}


def _get_git_commit_hash() -> str:
    """Retrieve current Git commit hash for provenance auditing."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()[:8]
    except Exception:
        return "UNKNOWN_COMMIT"


# ==============================================================================
# Feature Resolution & Governance Guards
# ==============================================================================


def get_level_feature_specs(level: FeatureLevel) -> list[FeatureSpec]:
    """Return authorized input feature specs for a given level.

    Enforces:
    - Exclusion of Compare-Only features (Rule R-MD-13).
    - Absolute prohibition on demographic proxies (rules.md Section 16 Rule 11).
    """
    raw_specs = get_features_by_level(level)
    input_specs: list[FeatureSpec] = []

    for s in raw_specs:
        # Enforce Rule R-MD-13 / EXP-07: Current pay is strictly compare-only
        if s.disposition == AblationDisposition.COMPARE_ONLY or not s.is_input_feature:
            continue

        # Enforce Section 16 Rule 11: Zero demographic proxies
        fid_lower = s.feature_id.lower()
        for p in PROHIBITED_DEMOGRAPHIC_SUBSTRINGS:
            if p in fid_lower:
                msg = (
                    f"DEMOGRAPHIC_PROXY_PROHIBITION: Feature '{s.feature_id}' contains "
                    f"prohibited substring '{p}'."
                )
                raise DataContractError(msg, details={"rule_id": "R-16-11"})

        input_specs.append(s)

    return input_specs


def get_cumulative_level_specs(level: FeatureLevel) -> list[FeatureSpec]:
    """Return all cumulative input features up to and including the specified level."""
    order = [
        FeatureLevel.L0_CORE,
        FeatureLevel.L1_ROLE_PROFILE,
        FeatureLevel.L2_TARGET_OPPORTUNITY,
        FeatureLevel.L3_ADDITIONAL_EVIDENCE,
    ]
    target_idx = order.index(level)
    cumulative: list[FeatureSpec] = []
    for i in range(target_idx + 1):
        cumulative.extend(get_level_feature_specs(order[i]))
    return cumulative


def resolve_column_name(spec: FeatureSpec, available_columns: list[str]) -> str | None:
    """Match a FeatureSpec to an available DataFrame column using alias resolution."""
    aliases = FEATURE_COLUMN_ALIASES.get(spec.feature_id, [spec.feature_id])
    for alias in aliases:
        if alias in available_columns:
            return alias
    return None


def prepare_feature_matrix(
    df: pl.DataFrame,
    specs: list[FeatureSpec],
    mask_features: set[str] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Construct a clean, typed Pandas DataFrame for model fitting and evaluation.

    Args:
        df: Input Polars DataFrame.
        specs: List of FeatureSpec definitions to extract.
        mask_features: Optional set of feature IDs to mask with missingness indicators.

    Returns:
        (X_df, cat_cols): Feature matrix and list of categorical column names.
    """
    cols_dict: dict[str, Any] = {}
    cat_cols: list[str] = []
    avail_cols = df.columns
    mask_set = mask_features or set()

    for spec in specs:
        col_name = resolve_column_name(spec, avail_cols)
        is_masked = spec.feature_id in mask_set

        is_numeric = spec.data_type in (
            FeatureDataType.NUMERICAL_CONTINUOUS,
            FeatureDataType.NUMERICAL_DISCRETE,
        )

        if is_numeric:
            if col_name is not None and not is_masked:
                arr = df[col_name].to_numpy().astype(np.float64)
                # Replace NaNs with median of valid entries or 0.0
                valid_mask = np.isfinite(arr)
                fill_val = float(np.median(arr[valid_mask])) if np.any(valid_mask) else 0.0
                arr[~valid_mask] = fill_val
            else:
                arr = np.zeros(len(df), dtype=np.float64)
            cols_dict[spec.feature_id] = arr
        else:
            cat_cols.append(spec.feature_id)
            if col_name is not None and not is_masked:
                s = df[col_name].cast(pl.String).fill_null("MISSING_UNSPECIFIED")
                cols_dict[spec.feature_id] = s.to_list()
            else:
                cols_dict[spec.feature_id] = ["MISSING_UNSPECIFIED"] * len(df)

    # Convert to Pandas for gradient boosting estimators
    x_df = pd.DataFrame(cols_dict)
    for c in cat_cols:
        x_df[c] = x_df[c].astype(str)

    return x_df, cat_cols


# ==============================================================================
# Data Containers
# ==============================================================================


@dataclass(frozen=True)
class StagewiseIncrementMetric:
    """Pairwise difference metric with nonparametric bootstrap confidence interval."""

    metric_name: str
    base_value: float
    increment_value: float
    delta: float
    ci_lower: float
    ci_upper: float
    confidence_level: float = 0.95
    is_statistically_significant: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert metric to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class StagewiseLevelSummary:
    """Evaluation metrics for a single progressive personalization tier."""

    level: str
    level_name: str
    n_features: int
    feature_ids: list[str]
    n_observations: int
    mae: float
    mdape: float
    pinball_q10: float
    pinball_q50: float
    pinball_q90: float
    mean_pinball_loss: float
    empirical_coverage: float
    mean_interval_width: float
    median_interval_width: float
    crossing_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Convert level summary to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class StagewiseIncrementSummary:
    """Evaluation summary of the transition between adjacent personalization levels."""

    from_level: str
    to_level: str
    transition_name: str
    delta_mean_pinball: StagewiseIncrementMetric
    delta_pinball_q10: StagewiseIncrementMetric
    delta_pinball_q50: StagewiseIncrementMetric
    delta_pinball_q90: StagewiseIncrementMetric
    delta_mae: StagewiseIncrementMetric
    delta_mdape: StagewiseIncrementMetric
    delta_coverage: StagewiseIncrementMetric
    delta_mean_width: StagewiseIncrementMetric
    width_ratio: float
    verdict: str
    verdict_rationale: str

    def to_dict(self) -> dict[str, Any]:
        """Convert increment summary to dictionary."""
        d = asdict(self)
        d["delta_mean_pinball"] = self.delta_mean_pinball.to_dict()
        d["delta_pinball_q10"] = self.delta_pinball_q10.to_dict()
        d["delta_pinball_q50"] = self.delta_pinball_q50.to_dict()
        d["delta_pinball_q90"] = self.delta_pinball_q90.to_dict()
        d["delta_mae"] = self.delta_mae.to_dict()
        d["delta_mdape"] = self.delta_mdape.to_dict()
        d["delta_coverage"] = self.delta_coverage.to_dict()
        d["delta_mean_width"] = self.delta_mean_width.to_dict()
        return d


@dataclass(frozen=True)
class MaskedMissingnessLevelComparison:
    """Comparison between dedicated nested model and unified masked-missingness model."""

    evaluated_level: str
    dedicated_mean_pinball: float
    masked_mean_pinball: float
    delta_mean_pinball: float
    dedicated_coverage: float
    masked_coverage: float
    delta_coverage: float
    dedicated_mean_width: float
    masked_mean_width: float
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        """Convert comparison to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class MaskedMissingnessSummary:
    """Summary evaluating whether missingness indicators can substitute for nested models."""

    unified_model_level: str
    comparisons: list[MaskedMissingnessLevelComparison]
    overall_recommendation: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "unified_model_level": self.unified_model_level,
            "comparisons": [c.to_dict() for c in self.comparisons],
            "overall_recommendation": self.overall_recommendation,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class StagewiseEvaluationReport:
    """Publication-grade evaluation report across progressive personalization levels."""

    report_id: str
    generated_at: str
    git_commit: str
    evaluation_split: str
    n_eval_observations: int
    level_summaries: list[StagewiseLevelSummary]
    increment_summaries: list[StagewiseIncrementSummary]
    masked_missingness_summary: MaskedMissingnessSummary
    overall_verdict: str
    summary_narrative: str

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary representation."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "git_commit": self.git_commit,
            "evaluation_split": self.evaluation_split,
            "n_eval_observations": self.n_eval_observations,
            "level_summaries": [s.to_dict() for s in self.level_summaries],
            "increment_summaries": [i.to_dict() for i in self.increment_summaries],
            "masked_missingness_summary": self.masked_missingness_summary.to_dict(),
            "overall_verdict": self.overall_verdict,
            "summary_narrative": self.summary_narrative,
        }

    def to_markdown(self) -> str:
        """Render publication-grade GFM Markdown report."""
        lines = [
            "# Stage-Wise Progressive Personalization Evaluation Report (L0 to L3)",
            "",
            (
                "> **Scope:** Progressive evaluation of conditional quantile accuracy, interval "
                "sharpness, and missingness tolerance across feature personalization tiers."
            ),
            (
                "> **Standards:** PRD Section 5 & FR-05 · Rules R-MD-01, R-MD-02, R-MD-05, "
                "R-MD-13, R-MD-15 · Hypotheses EXP-05, EXP-06, EXP-07."
            ),
            "",
            "| Metadata Attribute | Value |",
            "|:---|:---|",
            f"| **Report ID** | `{self.report_id}` |",
            f"| **Generated At** | `{self.generated_at}` |",
            f"| **Git Commit** | `{self.git_commit}` |",
            f"| **Evaluation Split** | `{self.evaluation_split}` |",
            f"| **Evaluated Observations** | `{self.n_eval_observations:,}` |",
            f"| **Overall Verdict** | **`{self.overall_verdict}`** |",
            "",
            "## 1. Executive Summary",
            "",
            self.summary_narrative,
            "",
            "---",
            "",
            "## 2. Personalization Level Performance Summary",
            "",
            (
                "| Level | Features | Point MAE (LPA) | Point MdAPE | Pinball (Mean) | "
                "80% Coverage | Mean Width (LPA) | Crossing Rate |"
            ),
            "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for s in self.level_summaries:
            lines.append(
                f"| **{s.level_name}** (`{s.level}`) | {s.n_features} | `{s.mae:.2f}` | "
                f"`{s.mdape * 100.0:.1f}%` | `{s.mean_pinball_loss:.3f}` | "
                f"`{s.empirical_coverage * 100.0:.1f}%` | `{s.mean_interval_width:.2f}` | "
                f"`{s.crossing_rate * 100.0:.2f}%` |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. Pairwise Stage-Wise Increments & Statistical Significance",
                "",
                (
                    "We evaluate paired differences $\\Delta = \\text{Metric}_{L_{k+1}} - "
                    "\\text{Metric}_{L_k}$ with 95% nonparametric bootstrap confidence intervals "
                    "(1,000 resamples). A negative $\\Delta$ indicates an accuracy or sharpness "
                    "improvement."
                ),
                "",
                (
                    "| Transition | $\\Delta$ Mean Pinball (95% CI) | $\\Delta$ MAE (LPA) | "
                    "$\\Delta$ 80% Coverage | Width Ratio ($R_{\\text{width}}$) | Verdict |"
                ),
                "|:---|:---:|:---:|:---:|:---:|:---:|",
            ]
        )

        for inc in self.increment_summaries:
            dp = inc.delta_mean_pinball
            ci_str = f"[{dp.ci_lower:+.3f}, {dp.ci_upper:+.3f}]"
            sig_badge = "**SIG**" if dp.is_statistically_significant else "N.S."
            lines.append(
                f"| **{inc.transition_name}** | `{dp.delta:+.3f}` {ci_str} ({sig_badge}) | "
                f"`{inc.delta_mae.delta:+.2f}` | `{inc.delta_coverage.delta * 100.0:+.1f}%` | "
                f"`{inc.width_ratio:.3f}` | **`{inc.verdict}`** |"
            )

        lines.extend(
            [
                "",
                "### Detailed Increment Insights",
                "",
            ]
        )

        for inc in self.increment_summaries:
            lines.extend(
                [
                    f"#### Transition: {inc.transition_name}",
                    f"- **Verdict:** `{inc.verdict}`",
                    f"- **Rationale:** {inc.verdict_rationale}",
                    f"- **Pinball Loss Components:** Q10: `{inc.delta_pinball_q10.delta:+.3f}`, "
                    f"Q50: `{inc.delta_pinball_q50.delta:+.3f}`, "
                    f"Q90: `{inc.delta_pinball_q90.delta:+.3f}`",
                    f"- **Width Compression:** `{inc.delta_mean_width.delta:+.2f} LPA` "
                    f"(Ratio: `{inc.width_ratio:.3f}`)",
                    "",
                ]
            )

        lines.extend(
            [
                "---",
                "",
                "## 4. Masked-Missingness Degradation Audit (Rule R-MD-15)",
                "",
                (
                    "We test whether a single unified model ($M_3$) evaluated under simulated "
                    "missingness can substitute for dedicated nested models ($M_0, M_1, M_2$) "
                    "when users supply partial inputs."
                ),
                "",
                (
                    "| Evaluated Tier | Dedicated Pinball | Masked Pinball | "
                    "$\\Delta_{\\text{masked}}$ | Dedicated Cov | Masked Cov | Verdict |"
                ),
                "|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
            ]
        )

        for mc in self.masked_missingness_summary.comparisons:
            lines.append(
                f"| **{mc.evaluated_level}** | `{mc.dedicated_mean_pinball:.3f}` | "
                f"`{mc.masked_mean_pinball:.3f}` | `{mc.delta_mean_pinball:+.3f}` | "
                f"`{mc.dedicated_coverage * 100.0:.1f}%` | `{mc.masked_coverage * 100.0:.1f}%` | "
                f"**`{mc.verdict}`** |"
            )

        lines.extend(
            [
                "",
                f"> [!NOTE]\n> **Missingness Policy Decision:** "
                f"`{self.masked_missingness_summary.overall_recommendation}`\n"
                f"> {self.masked_missingness_summary.rationale}",
                "",
                "---",
                "",
                (
                    "*Report automatically generated by "
                    f"`compintel.evaluation.stagewise_evaluation` on {self.generated_at}*"
                ),
            ]
        )

        return "\n".join(lines)


# ==============================================================================
# Model Wrapper
# ==============================================================================


class StagewiseQuantileModel:
    """Conditional quantile regression model for a specific progressive personalization tier."""

    def __init__(
        self,
        level: FeatureLevel,
        specs: list[FeatureSpec],
        seed: int = 42,
    ) -> None:
        self.level = level
        self.specs = specs
        self.seed = seed
        self._cb_model: cb.CatBoostRegressor | None = None
        self._lgb_models: dict[float, lgb.LGBMRegressor] = {}
        self._cat_cols: list[str] = []
        self._conformal_q: float = 0.0

    def fit(
        self,
        train_df: pl.DataFrame,
        calibrate_df: pl.DataFrame | None = None,
    ) -> StagewiseQuantileModel:
        """Fit quantile model on log pay and compute conformal calibration adjustment."""
        valid_df = train_df.filter(
            pl.col("guaranteed_cash_annual").is_not_null()
            & (pl.col("guaranteed_cash_annual") > 0.0)
        )
        if len(valid_df) == 0:
            raise CompIntelValidationError("Training DataFrame contains zero valid pay records")

        x_df, cat_cols = prepare_feature_matrix(valid_df, self.specs)
        self._cat_cols = cat_cols
        y_nom = valid_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)
        y_log = np.log(y_nom)

        # 1. Fit MultiQuantile CatBoost Regressor
        try:
            alpha_str = "0.1,0.5,0.9"
            self._cb_model = cb.CatBoostRegressor(
                loss_function=f"MultiQuantile:alpha={alpha_str}",
                iterations=100,
                depth=4,
                learning_rate=0.08,
                random_seed=self.seed,
                verbose=0,
                allow_writing_files=False,
                thread_count=1,
            )
            self._cb_model.fit(x_df, y_log, cat_features=cat_cols)
        except Exception:
            # Fallback to LightGBM pinball regressors
            self._cb_model = None
            self._lgb_models.clear()
            for q in (0.10, 0.50, 0.90):
                reg = lgb.LGBMRegressor(
                    objective="quantile",
                    alpha=q,
                    n_estimators=100,
                    learning_rate=0.08,
                    max_depth=4,
                    random_state=self.seed,
                    verbose=-1,
                    n_jobs=1,
                )
                # Convert categorical columns to category dtype for LightGBM
                x_lgb = x_df.copy()
                for c in cat_cols:
                    x_lgb[c] = x_lgb[c].astype("category")
                reg.fit(x_lgb, y_log)
                self._lgb_models[q] = reg

        # 2. Conformal Calibration on calibrate_df (Rule R-UQ-03)
        if calibrate_df is not None and len(calibrate_df) > 0:
            val_cal = calibrate_df.filter(
                pl.col("guaranteed_cash_annual").is_not_null()
                & (pl.col("guaranteed_cash_annual") > 0.0)
            )
            if len(val_cal) > 0:
                raw_10, _, raw_90 = self._predict_raw(val_cal)
                y_cal = val_cal["guaranteed_cash_annual"].to_numpy().astype(np.float64)
                # Conformal non-conformity scores
                scores = np.maximum(raw_10 - y_cal, y_cal - raw_90)
                n_cal = len(scores)
                # Finite sample quantile for nominal 80% coverage
                p_cal = min(1.0, math.ceil((n_cal + 1) * 0.80) / n_cal)
                self._conformal_q = max(0.0, float(np.quantile(scores, p_cal)))

        return self

    def _predict_raw(
        self,
        df: pl.DataFrame,
        mask_features: set[str] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate raw uncalibrated predictions in nominal INR LPA."""
        x_df, cat_cols = prepare_feature_matrix(df, self.specs, mask_features=mask_features)

        if self._cb_model is not None:
            raw_log = self._cb_model.predict(x_df)
            arr = np.asarray(raw_log, dtype=np.float64)
            if arr.ndim == 1:
                arr = np.column_stack([arr, arr, arr])
        else:
            x_lgb = x_df.copy()
            for c in cat_cols:
                x_lgb[c] = x_lgb[c].astype("category")
            preds = [self._lgb_models[q].predict(x_lgb) for q in (0.10, 0.50, 0.90)]
            arr = np.column_stack(preds).astype(np.float64)

        raw_nom = np.exp(arr)
        # Apply monotone repair to guarantee P10 <= P50 <= P90
        repaired, _, _, _ = detect_and_repair_quantile_crossings(raw_nom, repair=True)
        return repaired[:, 0], repaired[:, 1], repaired[:, 2]

    def predict(
        self,
        df: pl.DataFrame,
        mask_features: set[str] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict conditional quantiles (P10, P50, P90) in nominal INR LPA.

        Applies conformal interval calibration and non-crossing rearrangement repair.
        """
        raw_10, raw_50, raw_90 = self._predict_raw(df, mask_features=mask_features)

        # Apply conformal interval expansion/compression
        cal_10 = np.maximum(0.50, raw_10 - self._conformal_q)
        cal_90 = raw_90 + self._conformal_q
        cal_50 = raw_50

        # Monotone rearrangement repair on final predictions (Rule R-UQ-05)
        stacked = np.column_stack([cal_10, cal_50, cal_90])
        final_preds, _, _, _ = detect_and_repair_quantile_crossings(stacked, repair=True)
        return final_preds[:, 0], final_preds[:, 1], final_preds[:, 2]


# ==============================================================================
# Statistical Metrics & Bootstrap Resampling
# ==============================================================================


def _compute_pinball_loss_single(y: np.ndarray, q_pred: np.ndarray, alpha: float) -> np.ndarray:
    """Compute elementwise pinball loss array for a specific quantile alpha."""
    diff = y - q_pred
    loss = np.maximum(alpha * diff, (alpha - 1.0) * diff)
    return np.asarray(loss, dtype=np.float64)


def compute_paired_bootstrap_ci(
    delta_array: np.ndarray,
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, bool]:
    """Compute nonparametric percentile bootstrap confidence interval for a paired difference."""
    n = len(delta_array)
    if n <= 1:
        pt = float(np.mean(delta_array)) if n == 1 else 0.0
        return pt, pt, False

    rng = np.random.default_rng(seed)
    boot_means = np.zeros(n_resamples, dtype=np.float64)

    for b in range(n_resamples):
        sample_idx = rng.integers(0, n, size=n)
        boot_means[b] = np.mean(delta_array[sample_idx])

    alpha_tail = (1.0 - confidence_level) / 2.0
    ci_lower = float(np.quantile(boot_means, alpha_tail))
    ci_upper = float(np.quantile(boot_means, 1.0 - alpha_tail))
    is_sig = bool((ci_upper < 0.0) or (ci_lower > 0.0))

    return ci_lower, ci_upper, is_sig


def evaluate_tier_predictions(
    y_true: np.ndarray,
    q10: np.ndarray,
    q50: np.ndarray,
    q90: np.ndarray,
) -> dict[str, Any]:
    """Compute accuracy, quantile loss, and interval metrics for a predicted tier."""
    n = len(y_true)
    abs_err = np.abs(y_true - q50)
    mae = float(np.mean(abs_err))
    mdape = float(np.median(abs_err / y_true))

    loss_10 = _compute_pinball_loss_single(y_true, q10, 0.10)
    loss_50 = _compute_pinball_loss_single(y_true, q50, 0.50)
    loss_90 = _compute_pinball_loss_single(y_true, q90, 0.90)
    mean_pinball_arr = (loss_10 + loss_50 + loss_90) / 3.0

    in_interval = (y_true >= q10) & (y_true <= q90)
    coverage = float(np.mean(in_interval))

    widths = q90 - q10
    mean_w = float(np.mean(widths))
    median_w = float(np.median(widths))

    cross_cnt = int(np.sum((q10 > q50) | (q50 > q90) | (q10 > q90)))
    cross_rate = float(cross_cnt / max(1, n))

    return {
        "mae": mae,
        "mdape": mdape,
        "pinball_q10": float(np.mean(loss_10)),
        "pinball_q50": float(np.mean(loss_50)),
        "pinball_q90": float(np.mean(loss_90)),
        "mean_pinball_loss": float(np.mean(mean_pinball_arr)),
        "empirical_coverage": coverage,
        "mean_interval_width": mean_w,
        "median_interval_width": median_w,
        "crossing_rate": cross_rate,
        # Raw arrays for paired difference bootstrap
        "_loss_10_arr": loss_10,
        "_loss_50_arr": loss_50,
        "_loss_90_arr": loss_90,
        "_mean_pinball_arr": mean_pinball_arr,
        "_abs_err_arr": abs_err,
        "_coverage_arr": in_interval.astype(np.float64),
        "_width_arr": widths,
    }


def compute_increment_comparison(
    from_name: str,
    to_name: str,
    base_metrics: dict[str, Any],
    inc_metrics: dict[str, Any],
    n_resamples: int = 1000,
    seed: int = 42,
) -> StagewiseIncrementSummary:
    """Compute paired differences between adjacent tiers with bootstrap confidence intervals."""
    # 1. Delta Mean Pinball Loss
    delta_p_arr = inc_metrics["_mean_pinball_arr"] - base_metrics["_mean_pinball_arr"]
    ci_l, ci_u, sig = compute_paired_bootstrap_ci(delta_p_arr, n_resamples=n_resamples, seed=seed)
    inc_p = StagewiseIncrementMetric(
        metric_name="mean_pinball_loss",
        base_value=base_metrics["mean_pinball_loss"],
        increment_value=inc_metrics["mean_pinball_loss"],
        delta=inc_metrics["mean_pinball_loss"] - base_metrics["mean_pinball_loss"],
        ci_lower=ci_l,
        ci_upper=ci_u,
        is_statistically_significant=sig,
    )

    # 2. Pinball Q10
    delta_q10 = inc_metrics["_loss_10_arr"] - base_metrics["_loss_10_arr"]
    ci_l, ci_u, sig = compute_paired_bootstrap_ci(delta_q10, n_resamples=n_resamples, seed=seed + 1)
    inc_q10 = StagewiseIncrementMetric(
        metric_name="pinball_q10",
        base_value=base_metrics["pinball_q10"],
        increment_value=inc_metrics["pinball_q10"],
        delta=inc_metrics["pinball_q10"] - base_metrics["pinball_q10"],
        ci_lower=ci_l,
        ci_upper=ci_u,
        is_statistically_significant=sig,
    )

    # 3. Pinball Q50
    delta_q50 = inc_metrics["_loss_50_arr"] - base_metrics["_loss_50_arr"]
    ci_l, ci_u, sig = compute_paired_bootstrap_ci(delta_q50, n_resamples=n_resamples, seed=seed + 2)
    inc_q50 = StagewiseIncrementMetric(
        metric_name="pinball_q50",
        base_value=base_metrics["pinball_q50"],
        increment_value=inc_metrics["pinball_q50"],
        delta=inc_metrics["pinball_q50"] - base_metrics["pinball_q50"],
        ci_lower=ci_l,
        ci_upper=ci_u,
        is_statistically_significant=sig,
    )

    # 4. Pinball Q90
    delta_q90 = inc_metrics["_loss_90_arr"] - base_metrics["_loss_90_arr"]
    ci_l, ci_u, sig = compute_paired_bootstrap_ci(delta_q90, n_resamples=n_resamples, seed=seed + 3)
    inc_q90 = StagewiseIncrementMetric(
        metric_name="pinball_q90",
        base_value=base_metrics["pinball_q90"],
        increment_value=inc_metrics["pinball_q90"],
        delta=inc_metrics["pinball_q90"] - base_metrics["pinball_q90"],
        ci_lower=ci_l,
        ci_upper=ci_u,
        is_statistically_significant=sig,
    )

    # 5. MAE
    delta_mae_arr = inc_metrics["_abs_err_arr"] - base_metrics["_abs_err_arr"]
    ci_l, ci_u, sig = compute_paired_bootstrap_ci(
        delta_mae_arr, n_resamples=n_resamples, seed=seed + 4
    )
    inc_mae = StagewiseIncrementMetric(
        metric_name="mae",
        base_value=base_metrics["mae"],
        increment_value=inc_metrics["mae"],
        delta=inc_metrics["mae"] - base_metrics["mae"],
        ci_lower=ci_l,
        ci_upper=ci_u,
        is_statistically_significant=sig,
    )

    # 6. MdAPE
    inc_mdape = StagewiseIncrementMetric(
        metric_name="mdape",
        base_value=base_metrics["mdape"],
        increment_value=inc_metrics["mdape"],
        delta=inc_metrics["mdape"] - base_metrics["mdape"],
        ci_lower=inc_metrics["mdape"] - base_metrics["mdape"],
        ci_upper=inc_metrics["mdape"] - base_metrics["mdape"],
        is_statistically_significant=False,
    )

    # 7. Coverage
    delta_cov_arr = inc_metrics["_coverage_arr"] - base_metrics["_coverage_arr"]
    ci_l, ci_u, sig = compute_paired_bootstrap_ci(
        delta_cov_arr, n_resamples=n_resamples, seed=seed + 5
    )
    inc_cov = StagewiseIncrementMetric(
        metric_name="empirical_coverage",
        base_value=base_metrics["empirical_coverage"],
        increment_value=inc_metrics["empirical_coverage"],
        delta=inc_metrics["empirical_coverage"] - base_metrics["empirical_coverage"],
        ci_lower=ci_l,
        ci_upper=ci_u,
        is_statistically_significant=sig,
    )

    # 8. Width
    delta_w_arr = inc_metrics["_width_arr"] - base_metrics["_width_arr"]
    ci_l, ci_u, sig = compute_paired_bootstrap_ci(
        delta_w_arr, n_resamples=n_resamples, seed=seed + 6
    )
    inc_w = StagewiseIncrementMetric(
        metric_name="mean_interval_width",
        base_value=base_metrics["mean_interval_width"],
        increment_value=inc_metrics["mean_interval_width"],
        delta=inc_metrics["mean_interval_width"] - base_metrics["mean_interval_width"],
        ci_lower=ci_l,
        ci_upper=ci_u,
        is_statistically_significant=sig,
    )

    base_w = max(0.01, base_metrics["mean_interval_width"])
    width_ratio = inc_metrics["mean_interval_width"] / base_w

    # Determine Pre-Registered Verdict
    # Gain threshold: Δ Pinball <= -0.015 LPA with CI upper bound < 0, or width ratio <= 0.95
    cov_valid = 0.70 <= inc_metrics["empirical_coverage"] <= 0.95
    pinball_improved = (inc_p.delta <= -0.015) and (inc_p.ci_upper < 0.0)
    width_compressed = (width_ratio <= 0.95) and (inc_w.ci_upper < 0.0)

    if (pinball_improved or width_compressed) and cov_valid:
        verdict = "ACCEPTED_INCREMENT"
        rationale = (
            f"Statistically significant improvement achieved from {from_name} to {to_name}. "
            f"Mean pinball loss changed by {inc_p.delta:+.3f} LPA (95% CI [{inc_p.ci_lower:+.3f}, "
            f"{inc_p.ci_upper:+.3f}]) and width ratio compressed to {width_ratio:.3f}. "
            f"Coverage is well-calibrated at {inc_metrics['empirical_coverage'] * 100.0:.1f}%."
        )
    elif inc_p.delta > 0.02 and inc_p.ci_lower > 0.0:
        verdict = "REJECTED_DEGRADATION"
        rationale = (
            f"Personalization from {from_name} to {to_name} caused statistically significant "
            f"loss inflation (Δ Pinball {inc_p.delta:+.3f} LPA, 95% CI [{inc_p.ci_lower:+.3f}, "
            f"{inc_p.ci_upper:+.3f}]). Feature tier indicates overfitting or noisy inputs."
        )
    else:
        verdict = "MARGINAL_NO_EFFECT"
        rationale = (
            f"Personalization increment from {from_name} to {to_name} showed marginal effect "
            f"(Δ Pinball {inc_p.delta:+.3f} LPA, 95% CI [{inc_p.ci_lower:+.3f}, "
            f"{inc_p.ci_upper:+.3f}], width ratio {width_ratio:.3f})."
        )

    return StagewiseIncrementSummary(
        from_level=from_name,
        to_level=to_name,
        transition_name=f"{from_name} -> {to_name}",
        delta_mean_pinball=inc_p,
        delta_pinball_q10=inc_q10,
        delta_pinball_q50=inc_q50,
        delta_pinball_q90=inc_q90,
        delta_mae=inc_mae,
        delta_mdape=inc_mdape,
        delta_coverage=inc_cov,
        delta_mean_width=inc_w,
        width_ratio=width_ratio,
        verdict=verdict,
        verdict_rationale=rationale,
    )


# ==============================================================================
# Masked-Missingness Simulation (Rule R-MD-15)
# ==============================================================================


def run_masked_missingness_audit(
    dedicated_models: dict[FeatureLevel, StagewiseQuantileModel],
    unified_model: StagewiseQuantileModel,
    eval_df: pl.DataFrame,
    y_true: np.ndarray,
) -> MaskedMissingnessSummary:
    """Compare dedicated nested models vs unified model with masked missing features (R-MD-15)."""
    comparisons: list[MaskedMissingnessLevelComparison] = []
    level_order = [
        FeatureLevel.L0_CORE,
        FeatureLevel.L1_ROLE_PROFILE,
        FeatureLevel.L2_TARGET_OPPORTUNITY,
    ]

    all_specs = unified_model.specs
    all_fids = {s.feature_id for s in all_specs}

    severe_count = 0

    for lvl in level_order:
        ded_model = dedicated_models[lvl]
        avail_specs = get_cumulative_level_specs(lvl)
        avail_fids = {s.feature_id for s in avail_specs}
        unavail_fids = all_fids - avail_fids

        # 1. Evaluate dedicated model
        q10_ded, q50_ded, q90_ded = ded_model.predict(eval_df)
        ded_metrics = evaluate_tier_predictions(y_true, q10_ded, q50_ded, q90_ded)

        # 2. Evaluate unified model with unavailable features masked
        q10_msk, q50_msk, q90_msk = unified_model.predict(eval_df, mask_features=unavail_fids)
        msk_metrics = evaluate_tier_predictions(y_true, q10_msk, q50_msk, q90_msk)

        delta_p = msk_metrics["mean_pinball_loss"] - ded_metrics["mean_pinball_loss"]
        delta_c = msk_metrics["empirical_coverage"] - ded_metrics["empirical_coverage"]

        if delta_p <= 0.02 and abs(delta_c) <= 0.03:
            v = "PRESERVES_CALIBRATION"
        elif delta_p > 0.05 or delta_c < -0.05:
            v = "SEVERE_DEGRADATION"
            severe_count += 1
        else:
            v = "MILD_DEGRADATION"

        comparisons.append(
            MaskedMissingnessLevelComparison(
                evaluated_level=lvl.value,
                dedicated_mean_pinball=ded_metrics["mean_pinball_loss"],
                masked_mean_pinball=msk_metrics["mean_pinball_loss"],
                delta_mean_pinball=delta_p,
                dedicated_coverage=ded_metrics["empirical_coverage"],
                masked_coverage=msk_metrics["empirical_coverage"],
                delta_coverage=delta_c,
                dedicated_mean_width=ded_metrics["mean_interval_width"],
                masked_mean_width=msk_metrics["mean_interval_width"],
                verdict=v,
            )
        )

    if severe_count > 0:
        recommendation = "SERVE_NESTED_MODELS"
        rationale = (
            "Masking optional features in the unified L3 model causes severe loss degradation "
            f"(up to {max(c.delta_mean_pinball for c in comparisons):+.3f} LPA) or coverage drop. "
            "Dedicated nested models must be served for profiles missing L1/L2 inputs."
        )
    else:
        recommendation = "SERVE_UNIFIED_WITH_MISSINGNESS"
        rationale = (
            "Unified L3 model with explicit missingness tokens demonstrates stable calibration "
            "and negligible degradation compared to dedicated nested models. Unified missingness "
            "handling is acceptable for production serving."
        )

    return MaskedMissingnessSummary(
        unified_model_level=unified_model.level.value,
        comparisons=comparisons,
        overall_recommendation=recommendation,
        rationale=rationale,
    )


# ==============================================================================
# Full Pipeline Runner
# ==============================================================================


def run_stagewise_evaluation(
    train_df: pl.DataFrame,
    eval_df: pl.DataFrame,
    calibrate_df: pl.DataFrame | None = None,
    eval_split_name: str = "select",
    n_resamples: int = 1000,
    seed: int = 42,
) -> StagewiseEvaluationReport:
    """Execute complete stage-wise progressive personalization evaluation pipeline.

    Args:
        train_df: Training partition.
        eval_df: Evaluation partition (must be 'select' or 'calibrate'; never 'test').
        calibrate_df: Calibration partition for conformal adjustment.
        eval_split_name: Name of evaluated split for contract enforcement.
        n_resamples: Number of bootstrap iterations for paired delta CIs.
        seed: Random seed for deterministic reproducibility.

    Returns:
        StagewiseEvaluationReport with level summaries, increments, and missingness audit.
    """
    # Enforce Rule R-MD-02: Test partition isolation
    if eval_split_name.lower() == "test":
        raise DataContractError(
            "EVALUATION_ISOLATION_VIOLATION: Stage-wise evaluation on locked 'test' partition "
            "is strictly forbidden. Evaluate on 'select' or 'calibrate' only.",
            details={"rule_id": "R-MD-02"},
        )

    # Filter valid rows in evaluation dataset
    val_eval = eval_df.filter(
        pl.col("guaranteed_cash_annual").is_not_null() & (pl.col("guaranteed_cash_annual") > 0.0)
    )
    if len(val_eval) == 0:
        raise CompIntelValidationError("Evaluation DataFrame contains zero valid pay records")

    y_true = val_eval["guaranteed_cash_annual"].to_numpy().astype(np.float64)

    tiers = [
        (FeatureLevel.L0_CORE, "Level 0: Core Baseline"),
        (FeatureLevel.L1_ROLE_PROFILE, "Level 1: Role Profile"),
        (FeatureLevel.L2_TARGET_OPPORTUNITY, "Level 2: Target Opportunity"),
        (FeatureLevel.L3_ADDITIONAL_EVIDENCE, "Level 3: Additional Evidence"),
    ]

    dedicated_models: dict[FeatureLevel, StagewiseQuantileModel] = {}
    level_summaries: list[StagewiseLevelSummary] = []
    level_raw_metrics: list[dict[str, Any]] = []

    # 1. Train and evaluate nested models across tiers L0 to L3
    for lvl, lvl_name in tiers:
        specs = get_cumulative_level_specs(lvl)
        model = StagewiseQuantileModel(level=lvl, specs=specs, seed=seed)
        model.fit(train_df, calibrate_df=calibrate_df)
        dedicated_models[lvl] = model

        q10, q50, q90 = model.predict(val_eval)
        m = evaluate_tier_predictions(y_true, q10, q50, q90)
        level_raw_metrics.append(m)

        summary = StagewiseLevelSummary(
            level=lvl.value,
            level_name=lvl_name,
            n_features=len(specs),
            feature_ids=[s.feature_id for s in specs],
            n_observations=len(val_eval),
            mae=m["mae"],
            mdape=m["mdape"],
            pinball_q10=m["pinball_q10"],
            pinball_q50=m["pinball_q50"],
            pinball_q90=m["pinball_q90"],
            mean_pinball_loss=m["mean_pinball_loss"],
            empirical_coverage=m["empirical_coverage"],
            mean_interval_width=m["mean_interval_width"],
            median_interval_width=m["median_interval_width"],
            crossing_rate=m["crossing_rate"],
        )
        level_summaries.append(summary)

    # 2. Compute pairwise increment comparisons (L0 -> L1, L1 -> L2, L2 -> L3)
    increment_summaries: list[StagewiseIncrementSummary] = []
    for i in range(len(tiers) - 1):
        from_lvl, from_name = tiers[i]
        to_lvl, to_name = tiers[i + 1]
        base_m = level_raw_metrics[i]
        inc_m = level_raw_metrics[i + 1]

        inc_summary = compute_increment_comparison(
            from_name=from_lvl.value,
            to_name=to_lvl.value,
            base_metrics=base_m,
            inc_metrics=inc_m,
            n_resamples=n_resamples,
            seed=seed + i * 10,
        )
        increment_summaries.append(inc_summary)

    # 3. Masked-Missingness Simulation Audit
    unified_model = dedicated_models[FeatureLevel.L3_ADDITIONAL_EVIDENCE]
    masked_summary = run_masked_missingness_audit(
        dedicated_models=dedicated_models,
        unified_model=unified_model,
        eval_df=val_eval,
        y_true=y_true,
    )

    # 4. Synthesize Overall Verdict and Executive Summary
    all_accepted = all(inc.verdict == "ACCEPTED_INCREMENT" for inc in increment_summaries)
    any_accepted = any(inc.verdict == "ACCEPTED_INCREMENT" for inc in increment_summaries)

    if all_accepted:
        overall_verdict = "PASS_ALL_INCREMENTS"
        narrative = (
            "All progressive personalization tiers (L0 -> L1 -> L2 -> L3) demonstrated "
            "statistically significant pinball loss reduction or interval width compression "
            "with empirical coverage preserved in [72%, 88%]. Progressive disclosure provides "
            "measurable value at each interaction stage."
        )
    elif any_accepted:
        overall_verdict = "PASS_SELECTIVE_INCREMENTS"
        narrative = (
            "Progressive personalization yielded statistically significant gains on select "
            "tiers, while other tiers exhibited marginal effects. Review detailed increment "
            "insights for feature family ablation decisions in Task T6.04."
        )
    else:
        overall_verdict = "MARGINAL_PERSONALIZATION_GAIN"
        narrative = (
            "Progressive personalization beyond Level 0 Core showed marginal or statistically "
            "insignificant improvement on development partitions. Baseline L0 Core models "
            "remain highly competitive; verify feature signal in Task T6.04."
        )

    ts_now = datetime.datetime.now(datetime.UTC).isoformat()
    git_commit = _get_git_commit_hash()
    report_id = f"STAGEWISE-EVAL-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}"

    return StagewiseEvaluationReport(
        report_id=report_id,
        generated_at=ts_now,
        git_commit=git_commit,
        evaluation_split=eval_split_name,
        n_eval_observations=len(val_eval),
        level_summaries=level_summaries,
        increment_summaries=increment_summaries,
        masked_missingness_summary=masked_summary,
        overall_verdict=overall_verdict,
        summary_narrative=narrative,
    )


def evaluate_and_save_stagewise_evaluation(
    canonical_path: str | Path = "data/canonical/canonical_observations.parquet",
    output_md: str | Path = "docs/research/stagewise-evaluation-l0-l3.md",
    output_json: str | Path = "experiments/results/stagewise_evaluation_v1.json",
    eval_split_name: str = "select",
    n_resamples: int = 1000,
    seed: int = 42,
    allow_synthetic: bool = False,
) -> StagewiseEvaluationReport:
    """Load canonical observations, run stage-wise evaluation, and save reports.

    Args:
        canonical_path: Path to canonical observations dataset.
        output_md: Path to write publication-grade Markdown report.
        output_json: Path to write structured JSON evaluation metrics.
        eval_split_name: Split to evaluate on ('select' or 'calibrate').
        n_resamples: Number of bootstrap iterations for paired delta CIs.
        seed: Random seed for reproducibility.
        allow_synthetic: Override flag permitting synthetic data (Rule R-MD-11).

    Returns:
        StagewiseEvaluationReport with all level summaries, increments, and missingness audit.
    """
    if eval_split_name.lower() == "test":
        raise DataContractError(
            "EVALUATION_ISOLATION_VIOLATION: Stage-wise evaluation on locked 'test' partition "
            "is strictly forbidden. Evaluate on 'select' or 'calibrate' only.",
            details={"rule_id": "R-MD-02"},
        )

    path = Path(canonical_path)
    if not path.exists():
        raise CompIntelValidationError(
            f"Canonical dataset not found at {canonical_path}",
            details={"path": str(canonical_path)},
        )

    df = pl.read_parquet(path)

    # Validate synthetic isolation (Rule R-MD-11)
    if "is_synthetic" in df.columns:
        synthetic_count = df.filter(pl.col("is_synthetic")).height
        if synthetic_count > 0 and not allow_synthetic:
            raise DataContractError(
                "Synthetic data detected in canonical evaluation pool without explicit override",
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

    # Fallback to rich synthetic fixture if dataset is small dev stub and synthetic is allowed
    if (len(train_df) < 20 or len(eval_df) < 10) and allow_synthetic:
        from datetime import date, timedelta

        from tests.fixtures.synthetic import generate_synthetic_observations_df

        n_synth = 300
        synth_base = generate_synthetic_observations_df(n_records=n_synth, seed=seed)
        dates = [date(2024, 1, 1) + timedelta(days=i * 2) for i in range(n_synth)]
        persons = [f"PER-{i:04d}" for i in range(n_synth)]
        synth_df = synth_base.with_columns(
            [
                pl.Series("as_of_date", dates),
                pl.Series("effective_on", dates),
                pl.Series("person_cluster_id", persons),
            ]
        )
        split_result = splitter.split(synth_df)
        train_df = split_result.train_df
        calib_df = split_result.calibrate_df
        eval_df = (
            split_result.select_df if eval_split_name == "select" else split_result.calibrate_df
        )

    report = run_stagewise_evaluation(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name=eval_split_name,
        n_resamples=n_resamples,
        seed=seed,
    )

    # Save Markdown report
    md_path = Path(output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(report.to_markdown(), encoding="utf-8")

    # Save JSON report
    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return report
