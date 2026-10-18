"""Unit tests for Hierarchical Partial Pooling Diagnostics Engine (Task T6.02b).

Tests prior predictive checks, posterior predictive checks with Bayesian p-values,
multi-level shrinkage diagnostics with k_min >= 5 employer cluster anonymization,
prior sensitivity analysis across variance scales, and report generation.

Governed by:
- Rule R-UQ-06: Bayesian outputs require prior and posterior predictive checks.
- Rule R-UQ-05: Monotone quantile ordering (P10 <= P50 <= P90).
- Rule R-DA-10: Employer cluster anonymization floor k_min >= 5 audited.
- Rule R-MD-02: Final test set is locked; evaluation restricted to dev splits.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-TS-03: Line coverage >= 90.0%.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.hierarchical_diagnostics import (
    HierarchicalDiagnosticsReport,
    PosteriorPredictiveStatistic,
    PosteriorPredictiveSummary,
    PriorPredictiveSummary,
    PriorSensitivityReport,
    ShrinkageLevelDiagnostic,
    _get_git_commit_hash,
    _spearman_rank_correlation,
    compute_shrinkage_diagnostics,
    evaluate_and_save_hierarchical_diagnostics,
    run_hierarchical_diagnostics,
    run_posterior_predictive_checks,
    run_prior_predictive_checks,
    run_prior_sensitivity_analysis,
)
from compintel.models.hierarchical.config import HierarchicalConfig
from compintel.models.hierarchical.model import HierarchicalPartialPoolingModel


@pytest.fixture
def sample_hierarchical_dataset() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Generate reproducible development training and evaluation datasets."""
    roles = ["SOFTWARE_ENGINEERING", "DATA_SCIENCE", "ML_AI"]
    seniorities = ["JR", "MID", "SR", "LEAD"]
    locations = ["BANGALORE", "HYDERABAD", "DELHI_NCR", "PUNE"]
    tiers = ["TIER_1", "TIER_2", "TIER_3"]

    def make_partition(n_rows: int, seed_offset: int) -> pl.DataFrame:
        part_rng = np.random.default_rng(42 + seed_offset)
        rows: list[dict[str, object]] = []
        for i in range(n_rows):
            role = str(part_rng.choice(roles))
            sen = str(part_rng.choice(seniorities))
            loc = str(part_rng.choice(locations))
            tier = str(part_rng.choice(tiers))

            # Experience correlated with seniority
            if sen == "JR":
                yoe = float(part_rng.uniform(0.5, 2.5))
                base_pay = 10.0
            elif sen == "MID":
                yoe = float(part_rng.uniform(2.5, 6.0))
                base_pay = 20.0
            elif sen == "SR":
                yoe = float(part_rng.uniform(6.0, 11.0))
                base_pay = 38.0
            else:
                yoe = float(part_rng.uniform(10.0, 18.0))
                base_pay = 65.0

            # Employer cluster: some dense (n >= 5), some sparse (n < 5)
            emp_cluster = f"EMP_CLUSTER_SPARSE_{i % 3}" if i % 4 == 0 else "EMP_CLUSTER_DENSE_1"

            # Log pay with noise
            noise = float(part_rng.normal(loc=0.0, scale=0.15))
            cash = max(3.0, base_pay * math_exp(noise))

            rows.append(
                {
                    "observation_id": f"OBS_{seed_offset}_{i:04d}",
                    "role_family": role,
                    "seniority": sen,
                    "location": loc,
                    "employer_tier": tier,
                    "employer_cluster_id": emp_cluster,
                    "years_experience": yoe,
                    "guaranteed_cash_annual": cash,
                    "is_synthetic": True,
                }
            )
        return pl.DataFrame(rows)

    train_df = make_partition(120, 1)
    eval_df = make_partition(40, 2)
    return train_df, eval_df


def math_exp(val: float) -> float:
    """Helper exponential."""
    return float(np.exp(val))


# ==============================================================================
# Prior Predictive Checks Tests
# ==============================================================================


@pytest.mark.unit
def test_prior_predictive_checks_plausibility() -> None:
    """Verify prior predictive simulations satisfy physical plausibility under R-UQ-06."""
    summary = run_prior_predictive_checks(n_simulations=500, seed=123)

    assert isinstance(summary, PriorPredictiveSummary)
    assert summary.n_simulations == 500
    assert summary.simulated_p10_nominal_lpa > 0.0
    assert summary.simulated_p10_nominal_lpa <= summary.simulated_p50_nominal_lpa
    assert summary.simulated_p50_nominal_lpa <= summary.simulated_p90_nominal_lpa
    assert summary.simulated_min_nominal_lpa >= 0.0
    assert summary.absurd_pay_rate < 0.02
    assert summary.is_physically_plausible is True
    assert "Prior generates realistic compensation spans" in summary.verdict_rationale

    as_dict = summary.to_dict()
    assert as_dict["n_simulations"] == 500
    assert "simulated_p50_nominal_lpa" in as_dict


# ==============================================================================
# Posterior Predictive Checks Tests
# ==============================================================================


@pytest.mark.unit
def test_posterior_predictive_checks_calibration(
    sample_hierarchical_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    """Verify posterior predictive checks compute valid test statistics and Bayesian p-values."""
    train_df, eval_df = sample_hierarchical_dataset

    model = HierarchicalPartialPoolingModel().fit(train_df)
    summary = run_posterior_predictive_checks(
        model=model,
        eval_df=eval_df,
        n_replications=100,
        seed=42,
    )

    assert isinstance(summary, PosteriorPredictiveSummary)
    assert summary.n_observations == len(eval_df)
    assert summary.n_replications == 100
    assert len(summary.test_statistics) >= 6

    # Verify every test statistic has a valid Bayesian p-value in [0, 1]
    for stat in summary.test_statistics:
        assert isinstance(stat, PosteriorPredictiveStatistic)
        assert 0.0 <= stat.bayesian_p_value <= 1.0
        assert stat.replicated_std >= 0.0
        assert stat.observed_value > 0.0

    # Empirical 80% coverage should be reasonable on dev
    assert 0.50 <= summary.empirical_p10_p90_coverage <= 1.00
    assert isinstance(summary.summary_verdict, str)

    as_dict = summary.to_dict()
    assert as_dict["n_observations"] == len(eval_df)
    assert len(as_dict["test_statistics"]) == len(summary.test_statistics)


@pytest.mark.unit
def test_posterior_predictive_checks_empty_validation(
    sample_hierarchical_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    """Verify posterior checks fail gracefully on empty DataFrame."""
    train_df, _ = sample_hierarchical_dataset
    model = HierarchicalPartialPoolingModel().fit(train_df)

    empty_df = pl.DataFrame(
        schema={
            "guaranteed_cash_annual": pl.Float64,
            "years_experience": pl.Float64,
            "role_family": pl.String,
            "seniority": pl.String,
            "location": pl.String,
        }
    )

    with pytest.raises(CompIntelValidationError, match="Evaluation DataFrame cannot be empty"):
        run_posterior_predictive_checks(model=model, eval_df=empty_df)


# ==============================================================================
# Shrinkage Diagnostics & k_min Floor Audit Tests
# ==============================================================================


@pytest.mark.unit
def test_compute_shrinkage_diagnostics_and_kmin(
    sample_hierarchical_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    """Verify shrinkage diagnostics inspect all levels and audit k_min >= 5 floor under R-DA-10."""
    train_df, _ = sample_hierarchical_dataset

    cfg = HierarchicalConfig(k_min_employer=5)
    model = HierarchicalPartialPoolingModel(config=cfg).fit(train_df)

    diags = compute_shrinkage_diagnostics(model)
    assert len(diags) == 5

    names = [d.level_name for d in diags]
    assert names == [
        "role_family",
        "seniority_in_role",
        "cell",
        "employer_tier",
        "employer_cluster",
    ]

    emp_diag = next(d for d in diags if d.level_name == "employer_cluster")
    assert emp_diag.k_min_compliant is True
    assert emp_diag.k_min_violations_count == 0

    # Every diagnostic should serialize cleanly to dict
    for d in diags:
        assert isinstance(d, ShrinkageLevelDiagnostic)
        assert 0.0 <= d.mean_shrinkage_factor <= 1.0
        d_dict = d.to_dict()
        assert "level_name" in d_dict
        assert "k_min_compliant" in d_dict


@pytest.mark.unit
def test_shrinkage_diagnostics_empty_model() -> None:
    """Verify shrinkage diagnostics handle unfitted model with zero groups."""
    model = HierarchicalPartialPoolingModel()
    diags = compute_shrinkage_diagnostics(model)
    assert len(diags) == 5
    for d in diags:
        assert d.n_groups == 0
        assert d.mean_sample_size == 0.0
        assert d.k_min_compliant is True


# ==============================================================================
# Prior Sensitivity Analysis Tests
# ==============================================================================


@pytest.mark.unit
def test_prior_sensitivity_analysis_robustness(
    sample_hierarchical_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    """Verify prior sensitivity analysis quantifies delta and correlation under EXP-05."""
    train_df, eval_df = sample_hierarchical_dataset

    report = run_prior_sensitivity_analysis(
        train_df=train_df,
        eval_df=eval_df,
        scales=[0.5, 1.0, 2.0],
        seed=42,
    )

    assert isinstance(report, PriorSensitivityReport)
    assert len(report.perturbations) == 3
    assert report.baseline_id == "kappa_1.00_baseline"

    # Baseline perturbation delta must be ~0.0 and correlation ~1.0
    baseline_pert = next(p for p in report.perturbations if "baseline" in p.perturbation_id)
    assert baseline_pert.mean_abs_delta_p50_vs_baseline < 1e-9
    assert abs(baseline_pert.rank_correlation_vs_baseline - 1.0) < 1e-4

    assert report.max_mean_delta_lpa >= 0.0
    assert report.min_rank_correlation >= 0.90
    assert report.robustness_verdict in ("ROBUST", "MODERATELY_SENSITIVE")

    as_dict = report.to_dict()
    assert as_dict["robustness_verdict"] == report.robustness_verdict
    assert len(as_dict["perturbations"]) == 3


@pytest.mark.unit
def test_spearman_rank_correlation_utility() -> None:
    """Verify helper Spearman rank correlation handles degenerate and identical arrays."""
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([10.0, 20.0, 30.0, 40.0])
    assert abs(_spearman_rank_correlation(a, b) - 1.0) < 1e-5

    # Reverse order
    c = np.array([40.0, 30.0, 20.0, 10.0])
    assert abs(_spearman_rank_correlation(a, c) - (-1.0)) < 1e-5

    # Constant array (zero variance)
    d = np.array([5.0, 5.0, 5.0, 5.0])
    assert abs(_spearman_rank_correlation(a, d) - 1.0) < 1e-5

    # Single-element array
    assert _spearman_rank_correlation(np.array([1.0]), np.array([2.0])) == 1.0


# ==============================================================================
# Full Diagnostics Report Orchestration Tests
# ==============================================================================


@pytest.mark.unit
def test_run_hierarchical_diagnostics_report_generation(
    sample_hierarchical_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    """Verify full hierarchical diagnostics runs all checks and renders markdown."""
    train_df, eval_df = sample_hierarchical_dataset

    report = run_hierarchical_diagnostics(
        train_df=train_df,
        eval_df=eval_df,
        eval_split_name="select",
        n_prior_simulations=200,
        n_posterior_replications=50,
        seed=42,
    )

    assert isinstance(report, HierarchicalDiagnosticsReport)
    assert report.evaluation_split == "select"
    assert report.overall_verdict in (
        "PASS_DIAGNOSTICS",
        "WARNING_CHECK_SENSITIVITY",
        "FAIL_MISCALIBRATED",
    )
    assert report.prior_checks.is_physically_plausible is True
    assert len(report.shrinkage_diagnostics) == 5

    # Verify JSON serialization
    rep_dict = report.to_dict()
    assert rep_dict["report_id"] == report.report_id
    assert "prior_checks" in rep_dict
    assert "posterior_checks" in rep_dict

    # Verify Markdown rendering
    md = report.to_markdown()
    assert "# Rung C Hierarchical Partial Pooling Model Diagnostics Report" in md
    assert "## 1. Executive Summary & Diagnostic Verdict" in md
    assert "## 2. Prior Predictive Checks" in md
    assert "## 3. Posterior Predictive Checks" in md
    assert "## 4. Multi-Level Shrinkage" in md
    assert "## 5. Prior Sensitivity Analysis" in md
    assert "## 6. Implications for Hypothesis EXP-05" in md


@pytest.mark.unit
def test_run_hierarchical_diagnostics_test_isolation_guard(
    sample_hierarchical_dataset: tuple[pl.DataFrame, pl.DataFrame],
) -> None:
    """Verify Rule R-MD-02 strictly forbids running diagnostics on locked 'test' partition."""
    train_df, eval_df = sample_hierarchical_dataset

    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        run_hierarchical_diagnostics(
            train_df=train_df,
            eval_df=eval_df,
            eval_split_name="test",
        )


@pytest.mark.unit
def test_evaluate_and_save_hierarchical_diagnostics_file_pipeline(
    sample_hierarchical_dataset: tuple[pl.DataFrame, pl.DataFrame],
    tmp_path: Path,
) -> None:
    """Verify evaluate_and_save_hierarchical_diagnostics loads parquet,
    saves .md and .json reports.
    """
    train_df, eval_df = sample_hierarchical_dataset
    full_df = pl.concat(
        [
            train_df.with_columns(pl.lit("train").alias("split")),
            eval_df.with_columns(pl.lit("select").alias("split")),
        ]
    )

    parquet_path = tmp_path / "test_canonical.parquet"
    full_df.write_parquet(parquet_path)

    out_md = tmp_path / "diagnostics.md"
    out_json = tmp_path / "diagnostics.json"

    # Synthetic check: without allow_synthetic, should raise DataContractError
    with pytest.raises(DataContractError, match="Synthetic data detected"):
        evaluate_and_save_hierarchical_diagnostics(
            canonical_path=parquet_path,
            output_md=out_md,
            output_json=out_json,
            split="select",
            allow_synthetic=False,
        )

    # With allow_synthetic=True, should succeed and write files
    report = evaluate_and_save_hierarchical_diagnostics(
        canonical_path=parquet_path,
        output_md=out_md,
        output_json=out_json,
        split="select",
        n_prior_simulations=100,
        n_posterior_replications=25,
        seed=42,
        allow_synthetic=True,
    )

    assert out_md.exists()
    assert out_json.exists()

    md_content = out_md.read_text(encoding="utf-8")
    assert "Rung C Hierarchical Partial Pooling" in md_content

    json_content = json.loads(out_json.read_text(encoding="utf-8"))
    assert json_content["report_id"] == report.report_id


@pytest.mark.unit
def test_evaluate_and_save_missing_file_guard(tmp_path: Path) -> None:
    """Verify non-existent canonical path raises CompIntelValidationError."""
    missing = tmp_path / "non_existent.parquet"
    with pytest.raises(CompIntelValidationError, match="Canonical file not found"):
        evaluate_and_save_hierarchical_diagnostics(canonical_path=missing)


@pytest.mark.unit
def test_git_commit_hash_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify git commit helper returns fallback string when git fails."""
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: (_ for _ in ()).throw(OSError))
    assert _get_git_commit_hash() == "UNKNOWN_COMMIT"
