"""Feature-family ablation study engine (EXP-06).

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and feature family evaluation.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-03: Temporal alignment and lookahead prohibition.
- Rule R-MD-05: Standard evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Objective business model tiers without proprietary black-box ranks.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine (EXP-07).
- Rule R-MD-15: Missingness invariant.
- Rule R-UQ-01: 95% nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Non-crossing quantile guarantee (P10 <= P50 <= P90).
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
    compute_paired_bootstrap_ci,
    get_level_feature_specs,
)
from compintel.features.spec import (
    FeatureLevel,
    FeatureSpec,
    get_feature,
)


class FamilyDispositionVerdict(StrEnum):
    """Pre-registered decision verdicts for feature families (EXP-06)."""

    KEEP = "KEEP"
    DEFER = "DEFER"
    REJECT = "REJECT"
    ACCEPTED_CORE = "ACCEPTED_CORE"


@dataclass(frozen=True)
class FamilyAblationMetrics:
    """Evaluation metrics for a specific feature set configuration."""

    model_label: str
    n_features: int
    feature_ids: list[str]
    mae: float
    mdape: float
    mean_pinball_loss: float
    pinball_q10: float
    pinball_q50: float
    pinball_q90: float
    empirical_coverage: float
    mean_interval_width: float
    crossing_rate: float


@dataclass(frozen=True)
class FamilyAblationDelta:
    """Paired difference metrics and bootstrap confidence interval."""

    delta_mean_pinball: float
    pinball_ci_lower: float
    pinball_ci_upper: float
    pinball_significant: bool
    delta_mae: float
    delta_coverage: float
    width_ratio: float


@dataclass(frozen=True)
class FamilyAblationItem:
    """Comprehensive evaluation record for a single feature family under EXP-06."""

    family_key: str
    family_name: str
    feature_ids: list[str]
    keep_threshold_pinball: float
    keep_threshold_width_ratio: float | None
    forward_addition_metrics: FamilyAblationMetrics
    forward_delta: FamilyAblationDelta
    backward_drop_metrics: FamilyAblationMetrics
    backward_delta: FamilyAblationDelta
    verdict: FamilyDispositionVerdict
    decision_rationale: str


@dataclass(frozen=True)
class FamilyAblationReport:
    """Publication-grade feature-family ablation study report (EXP-06)."""

    report_id: str
    generated_at: str
    git_commit: str
    evaluation_split: str
    n_eval_observations: int
    l0_baseline_metrics: FamilyAblationMetrics
    l1_full_metrics: FamilyAblationMetrics
    family_results: list[FamilyAblationItem]
    overall_summary: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to structured JSON-compatible dictionary."""
        return asdict(self)

    def to_markdown(self) -> str:
        """Render publication-grade Markdown documentation."""
        l0_m = self.l0_baseline_metrics
        l1_m = self.l1_full_metrics

        md: list[str] = [
            "# Feature-Family Ablation Study Report (EXP-06)",
            "",
            "> **Scope:** Systematic ablation of candidate feature families at Level 1.",
            "> **Standards:** PRD Sec 5 · Rules R-MD-01, R-MD-02, R-MD-05, R-MD-09, "
            "R-MD-11, R-MD-13, R-MD-15 · Hypothesis EXP-06.",
            "",
            "| Metadata Attribute | Value |",
            "|:---|:---|",
            f"| **Report ID** | `{self.report_id}` |",
            f"| **Generated At** | `{self.generated_at}` |",
            f"| **Git Commit** | `{self.git_commit[:8]}` |",
            f"| **Evaluation Split** | `{self.evaluation_split}` |",
            f"| **Evaluated Observations** | `{self.n_eval_observations:,}` |",
            "",
            "## 1. Executive Summary",
            "",
            self.overall_summary,
            "",
            "---",
            "",
            "## 2. Baseline Model Performance Reference",
            "",
            "| Configuration | Features | Point MAE | MdAPE | Pinball | "
            "80% Cov | Width (LPA) | Crossing |",
            "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
            (
                f"| **L0 Core Baseline** | {l0_m.n_features} | "
                f"`{l0_m.mae:.2f}` | `{l0_m.mdape * 100:.1f}%` | "
                f"`{l0_m.mean_pinball_loss:.3f}` | `{l0_m.empirical_coverage * 100:.1f}%` | "
                f"`{l0_m.mean_interval_width:.2f}` | `{l0_m.crossing_rate * 100:.2f}%` |"
            ),
            (
                f"| **L1 Full Profile** | {l1_m.n_features} | "
                f"`{l1_m.mae:.2f}` | `{l1_m.mdape * 100:.1f}%` | "
                f"`{l1_m.mean_pinball_loss:.3f}` | `{l1_m.empirical_coverage * 100:.1f}%` | "
                f"`{l1_m.mean_interval_width:.2f}` | `{l1_m.crossing_rate * 100:.2f}%` |"
            ),
            "",
            "---",
            "",
            "## 3. Pre-Registered Feature-Family Ablation Table (EXP-06)",
            "",
            "We evaluate paired differences $\\Delta = \\text{Metric}_{\\text{Augmented}} - "
            "\\text{Metric}_{\\text{Baseline}}$ with 95% nonparametric bootstrap confidence "
            "intervals (1,000 resamples). A negative $\\Delta$ indicates an accuracy or "
            "sharpness improvement.",
            "",
            "| Family | Evaluated Features | Keep Threshold | Forward Δ Pinball (95% CI) | "
            "Width Ratio | Backward Δ Pinball ($L_1 \\setminus F$) | Verdict |",
            "|:---|:---|:---:|:---:|:---:|:---:|:---:|",
        ]

        for item in self.family_results:
            ci_fwd = (
                f"[{item.forward_delta.pinball_ci_lower:+.3f}, "
                f"{item.forward_delta.pinball_ci_upper:+.3f}]"
            )
            fwd_str = f"`{item.forward_delta.delta_mean_pinball:+.3f}` {ci_fwd}"
            back_str = f"`{item.backward_delta.delta_mean_pinball:+.3f}`"
            thresh_str = f"$\\Delta \\le {item.keep_threshold_pinball:+.3f}$"
            if item.keep_threshold_width_ratio is not None:
                thresh_str += f", $R \\le {item.keep_threshold_width_ratio:.2f}$"

            feat_str = "<br>".join([f"`{fid}`" for fid in item.feature_ids])
            verdict_badge = f"**`{item.verdict.value}`**"

            md.append(
                f"| **{item.family_name}** | {feat_str} | {thresh_str} | {fwd_str} | "
                f"`{item.forward_delta.width_ratio:.3f}` | {back_str} | {verdict_badge} |"
            )

        md.extend(
            [
                "",
                "---",
                "",
                "## 4. Detailed Family Analyses & Engineering Directives",
                "",
            ]
        )

        for item in self.family_results:
            fwd_d = item.forward_delta
            bwd_d = item.backward_delta
            ci_str = f"[{fwd_d.pinball_ci_lower:+.3f}, {fwd_d.pinball_ci_upper:+.3f}]"
            f_names = ", ".join([f"`{fid}`" for fid in item.feature_ids])

            md.extend(
                [
                    f"### {item.family_name}",
                    f"- **Verdict:** `{item.verdict.value}`",
                    f"- **Features Included:** {f_names}",
                    f"- **Keep Criteria:** $\\Delta \\mathcal{{L}}_{{pinball}} \\le "
                    f"{item.keep_threshold_pinball:+.3f}\\text{{ LPA}}$",
                    (
                        f"- **Forward Addition ($L_0 + F$):** $\\Delta \\text{{Mean Pinball}} = "
                        f"{fwd_d.delta_mean_pinball:+.3f}$ LPA (95% CI: `{ci_str}`), "
                        f"Width Ratio: `{fwd_d.width_ratio:.3f}`, "
                        f"$\\Delta \\text{{Coverage}} = {fwd_d.delta_coverage * 100:+.1f}\\%$"
                    ),
                    (
                        f"- **Backward Drop ($L_1 \\setminus F$):** "
                        f"$\\Delta \\text{{Mean Pinball}} = {bwd_d.delta_mean_pinball:+.3f}$ LPA "
                        "(Damage when removed from full profile)"
                    ),
                    f"- **Decision Rationale:** {item.decision_rationale}",
                    "",
                ]
            )

        md.extend(
            [
                "---",
                "",
                (
                    "*Report generated by `compintel.evaluation.family_ablation` on "
                    f"{self.generated_at}*"
                ),
            ]
        )

        return "\n".join(md)


# ==============================================================================
# Feature Family Registry Specification for EXP-06
# ==============================================================================

EXP06_FAMILY_SPECS: list[dict[str, Any]] = [
    {
        "key": "skills",
        "name": "Skills & Depth (Family A)",
        "feature_ids": ["feat_l1_skills_primary", "feat_l1_skills_depth"],
        "threshold_pinball": -0.030,
        "threshold_width_ratio": None,
        "default_action": FamilyDispositionVerdict.REJECT,
    },
    {
        "key": "domain",
        "name": "Domain Specialization (Family B)",
        "feature_ids": ["feat_l1_domain_specialization"],
        "threshold_pinball": -0.025,
        "threshold_width_ratio": None,
        "default_action": FamilyDispositionVerdict.REJECT,
    },
    {
        "key": "employer_tier",
        "name": "Employer Archetype Tier (Family C)",
        "feature_ids": ["feat_l1_employer_tier"],
        "threshold_pinball": -0.050,
        "threshold_width_ratio": 0.90,
        "default_action": FamilyDispositionVerdict.REJECT,
    },
    {
        "key": "work_arrangement",
        "name": "Work Arrangement / Geo Mode (Family D)",
        "feature_ids": ["feat_l1_work_arrangement"],
        "threshold_pinball": -0.010,
        "threshold_width_ratio": None,
        "default_action": FamilyDispositionVerdict.DEFER,
    },
    {
        "key": "career_velocity",
        "name": "Career Velocity (Family E)",
        "feature_ids": ["feat_l1_career_velocity"],
        "threshold_pinball": -0.015,
        "threshold_width_ratio": None,
        "default_action": FamilyDispositionVerdict.REJECT,
    },
    {
        "key": "leadership_scope",
        "name": "Leadership Scope (Family F)",
        "feature_ids": ["feat_l1_leadership_scope"],
        "threshold_pinball": -0.020,
        "threshold_width_ratio": None,
        "default_action": FamilyDispositionVerdict.REJECT,
    },
    {
        "key": "macro_market",
        "name": "Macro Market Regime (Family G)",
        "feature_ids": ["feat_l1_macro_market_regime"],
        "threshold_pinball": -0.010,
        "threshold_width_ratio": None,
        "default_action": FamilyDispositionVerdict.DEFER,
    },
]


def _get_git_commit_hash() -> str:
    """Retrieve current short git commit hash for audit traceability."""
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


def _evaluate_model_on_features(
    train_df: pl.DataFrame,
    eval_df: pl.DataFrame,
    calibrate_df: pl.DataFrame,
    feature_specs: list[FeatureSpec],
    model_label: str,
    seed: int = 42,
) -> tuple[FamilyAblationMetrics, np.ndarray, np.ndarray]:
    """Train StagewiseQuantileModel on feature_specs and compute evaluation metrics."""
    # Ensure compare-only features are strictly excluded (Rule R-MD-13)
    clean_specs = [s for s in feature_specs if s.is_input_feature]
    level = (
        FeatureLevel.L1_ROLE_PROFILE
        if any(s.level != FeatureLevel.L0_CORE for s in clean_specs)
        else FeatureLevel.L0_CORE
    )
    model = StagewiseQuantileModel(level=level, specs=clean_specs, seed=seed)
    model.fit(train_df, calibrate_df=calibrate_df)

    p10, p50, p90 = model.predict(eval_df)
    y_eval = eval_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)

    # Compute metrics
    mae = float(np.mean(np.abs(y_eval - p50)))
    mdape = float(np.median(np.abs(y_eval - p50) / np.maximum(y_eval, 0.5)))

    def _pinball(q: float, y: np.ndarray, pred: np.ndarray) -> np.ndarray:
        err = y - pred
        return np.asarray(np.maximum(q * err, (q - 1.0) * err), dtype=np.float64)

    pb10 = _pinball(0.10, y_eval, p10)
    pb50 = _pinball(0.50, y_eval, p50)
    pb90 = _pinball(0.90, y_eval, p90)
    mean_pb = (pb10 + pb50 + pb90) / 3.0

    in_cov = (y_eval >= p10) & (y_eval <= p90)
    coverage = float(np.mean(in_cov))
    widths = p90 - p10
    mean_width = float(np.mean(widths))

    crossings = np.sum((p10 > p50) | (p50 > p90))
    crossing_rate = float(crossings / (len(y_eval) * 2))

    metrics = FamilyAblationMetrics(
        model_label=model_label,
        n_features=len(clean_specs),
        feature_ids=[s.feature_id for s in clean_specs],
        mae=mae,
        mdape=mdape,
        mean_pinball_loss=float(np.mean(mean_pb)),
        pinball_q10=float(np.mean(pb10)),
        pinball_q50=float(np.mean(pb50)),
        pinball_q90=float(np.mean(pb90)),
        empirical_coverage=coverage,
        mean_interval_width=mean_width,
        crossing_rate=crossing_rate,
    )

    return metrics, mean_pb, widths


def run_family_ablation_study(
    train_df: pl.DataFrame,
    eval_df: pl.DataFrame,
    calibrate_df: pl.DataFrame,
    eval_split_name: str = "select",
    n_resamples: int = 1000,
    seed: int = 42,
) -> FamilyAblationReport:
    """Run comprehensive feature family ablation study (EXP-06).

    Args:
        train_df: Training partition.
        eval_df: Evaluation partition (must NOT be 'test' per R-MD-02).
        calibrate_df: Conformal calibration partition.
        eval_split_name: Split name ('select' or 'calibrate').
        n_resamples: Number of bootstrap resamples for paired difference CIs.
        seed: Random seed.

    Returns:
        FamilyAblationReport with complete results and verdicts.
    """
    if eval_split_name.lower() == "test":
        raise DataContractError(
            "EVALUATION_ISOLATION_VIOLATION: Feature family ablation on locked 'test' partition "
            "is strictly forbidden. Evaluate on 'select' or 'calibrate' only.",
            details={"rule_id": "R-MD-02"},
        )

    # 1. Base specs: L0 Core and full L1 Role Profile
    l0_specs = get_level_feature_specs(FeatureLevel.L0_CORE)
    l1_specs = [
        s
        for s in get_level_feature_specs(FeatureLevel.L1_ROLE_PROFILE)
        if s.level in (FeatureLevel.L0_CORE, FeatureLevel.L1_ROLE_PROFILE)
    ]

    l0_metrics, l0_pb_arr, l0_width_arr = _evaluate_model_on_features(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calibrate_df,
        feature_specs=l0_specs,
        model_label="L0 Core Baseline",
        seed=seed,
    )

    l1_metrics, l1_pb_arr, _l1_width_arr = _evaluate_model_on_features(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calibrate_df,
        feature_specs=l1_specs,
        model_label="L1 Full Profile",
        seed=seed,
    )

    family_results: list[FamilyAblationItem] = []

    # 2. Iterate each pre-registered family under EXP-06
    for fam in EXP06_FAMILY_SPECS:
        fam_key: str = fam["key"]
        fam_name: str = fam["name"]
        fam_feature_ids: list[str] = fam["feature_ids"]
        threshold_pb: float = fam["threshold_pinball"]
        threshold_wr: float | None = fam["threshold_width_ratio"]
        default_action: FamilyDispositionVerdict = fam["default_action"]

        fam_specs = [get_feature(fid) for fid in fam_feature_ids]

        # ----------------------------------------------------------------------
        # Forward Addition: L0 + Family
        # ----------------------------------------------------------------------
        fwd_specs = l0_specs + [s for s in fam_specs if s not in l0_specs]
        fwd_metrics, fwd_pb_arr, fwd_width_arr = _evaluate_model_on_features(
            train_df=train_df,
            eval_df=eval_df,
            calibrate_df=calibrate_df,
            feature_specs=fwd_specs,
            model_label=f"L0 + {fam_name}",
            seed=seed,
        )

        delta_pb_fwd = fwd_pb_arr - l0_pb_arr
        mean_delta_fwd = float(np.mean(delta_pb_fwd))
        ci_lower_fwd, ci_upper_fwd, sig_fwd = compute_paired_bootstrap_ci(
            delta_pb_fwd, n_resamples=n_resamples, seed=seed
        )
        delta_mae_fwd = fwd_metrics.mae - l0_metrics.mae
        delta_cov_fwd = fwd_metrics.empirical_coverage - l0_metrics.empirical_coverage
        wr_fwd = (
            float(np.median(fwd_width_arr) / np.maximum(np.median(l0_width_arr), 1e-6))
            if len(l0_width_arr) > 0
            else 1.0
        )

        forward_delta = FamilyAblationDelta(
            delta_mean_pinball=mean_delta_fwd,
            pinball_ci_lower=ci_lower_fwd,
            pinball_ci_upper=ci_upper_fwd,
            pinball_significant=sig_fwd,
            delta_mae=delta_mae_fwd,
            delta_coverage=delta_cov_fwd,
            width_ratio=wr_fwd,
        )

        # ----------------------------------------------------------------------
        # Backward Drop: L1 \ Family
        # ----------------------------------------------------------------------
        bwd_specs = [s for s in l1_specs if s.feature_id not in fam_feature_ids]
        bwd_metrics, bwd_pb_arr, _ = _evaluate_model_on_features(
            train_df=train_df,
            eval_df=eval_df,
            calibrate_df=calibrate_df,
            feature_specs=bwd_specs,
            model_label=f"L1 \\ {fam_name}",
            seed=seed,
        )

        # Damage of dropping: L1 loss - (L1 \ Family) loss
        delta_pb_bwd = l1_pb_arr - bwd_pb_arr
        mean_delta_bwd = float(np.mean(delta_pb_bwd))
        ci_lower_bwd, ci_upper_bwd, sig_bwd = compute_paired_bootstrap_ci(
            delta_pb_bwd, n_resamples=n_resamples, seed=seed
        )
        backward_delta = FamilyAblationDelta(
            delta_mean_pinball=mean_delta_bwd,
            pinball_ci_lower=ci_lower_bwd,
            pinball_ci_upper=ci_upper_bwd,
            pinball_significant=sig_bwd,
            delta_mae=bwd_metrics.mae - l1_metrics.mae,
            delta_coverage=bwd_metrics.empirical_coverage - l1_metrics.empirical_coverage,
            width_ratio=1.0,
        )

        # ----------------------------------------------------------------------
        # Decision Rule Evaluation
        # ----------------------------------------------------------------------
        passed_pinball = mean_delta_fwd <= threshold_pb
        passed_width = (threshold_wr is None) or (wr_fwd <= threshold_wr)
        passed_coverage = fwd_metrics.empirical_coverage >= 0.72

        if passed_pinball and passed_width and passed_coverage:
            verdict = FamilyDispositionVerdict.KEEP
            rationale = (
                f"Meets pre-registered criteria (Δ Pinball = {mean_delta_fwd:+.3f} "
                f"<= {threshold_pb:+.3f} LPA, width ratio = {wr_fwd:.3f}, "
                f"coverage = {fwd_metrics.empirical_coverage * 100:.1f}%). "
                "Retained as accepted personalization feature family."
            )
        else:
            verdict = default_action
            if default_action == FamilyDispositionVerdict.DEFER:
                rationale = (
                    f"Marginal or deferred effect (Δ Pinball = {mean_delta_fwd:+.3f} "
                    f"vs threshold {threshold_pb:+.3f} LPA). "
                    "Deferred per pre-registered policy without polluting Core models."
                )
            else:
                rationale = (
                    f"Failed minimum effect threshold (Δ Pinball = {mean_delta_fwd:+.3f} "
                    f"vs threshold {threshold_pb:+.3f} LPA). Rejected per Rule EXP-06."
                )

        family_results.append(
            FamilyAblationItem(
                family_key=fam_key,
                family_name=fam_name,
                feature_ids=fam_feature_ids,
                keep_threshold_pinball=threshold_pb,
                keep_threshold_width_ratio=threshold_wr,
                forward_addition_metrics=fwd_metrics,
                forward_delta=forward_delta,
                backward_drop_metrics=bwd_metrics,
                backward_delta=backward_delta,
                verdict=verdict,
                decision_rationale=rationale,
            )
        )

    # Executive narrative
    n_kept = sum(1 for item in family_results if item.verdict == FamilyDispositionVerdict.KEEP)
    n_deferred = sum(1 for item in family_results if item.verdict == FamilyDispositionVerdict.DEFER)
    n_rejected = sum(
        1 for item in family_results if item.verdict == FamilyDispositionVerdict.REJECT
    )

    summary = (
        f"Ablation study EXP-06 evaluated {len(family_results)} candidate feature families "
        f"at Level 1 against the L0 Core Baseline. Results: {n_kept} family kept, "
        f"{n_deferred} deferred, and {n_rejected} rejected under pre-registered thresholds "
        "in v1.yaml. Core representations remain parsimonious while capturing high-signal "
        "personalization dimensions."
    )

    ts_now = datetime.datetime.now(datetime.UTC).isoformat()
    git_commit = _get_git_commit_hash()
    report_id = f"EXP06-ABLATION-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}"

    return FamilyAblationReport(
        report_id=report_id,
        generated_at=ts_now,
        git_commit=git_commit,
        evaluation_split=eval_split_name,
        n_eval_observations=len(eval_df),
        l0_baseline_metrics=l0_metrics,
        l1_full_metrics=l1_metrics,
        family_results=family_results,
        overall_summary=summary,
    )


def evaluate_and_save_family_ablation(
    canonical_path: str | Path = "data/canonical/canonical_observations.parquet",
    output_md: str | Path = "docs/research/feature-family-ablations.md",
    output_json: str | Path = "experiments/results/feature_family_ablations_v1.json",
    eval_split_name: str = "select",
    n_resamples: int = 1000,
    seed: int = 42,
    allow_synthetic: bool = False,
) -> FamilyAblationReport:
    """Load canonical observations, execute feature family ablation study, and save reports.

    Args:
        canonical_path: Path to canonical observations dataset.
        output_md: Path to write publication-grade Markdown report.
        output_json: Path to write structured JSON evaluation metrics.
        eval_split_name: Split to evaluate on ('select' or 'calibrate').
        n_resamples: Number of bootstrap iterations for paired delta CIs.
        seed: Random seed for reproducibility.
        allow_synthetic: Override flag permitting synthetic data (Rule R-MD-11).

    Returns:
        FamilyAblationReport holding all ablation results and decisions.
    """
    if eval_split_name.lower() == "test":
        raise DataContractError(
            "EVALUATION_ISOLATION_VIOLATION: Feature family ablation on locked 'test' partition "
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

    report = run_family_ablation_study(
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
