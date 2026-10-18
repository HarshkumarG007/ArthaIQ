"""Unit tests for Stage-Wise Progressive Personalization Evaluation Engine (Task T6.03a).

Covers:
- Level feature spec resolution, compare-only quarantine (Rule R-MD-13, EXP-07).
- Demographic proxy prohibition guard (rules.md Section 16 Rule 11).
- Cumulative level feature specifications.
- Column name alias resolution and feature matrix preparation with missingness tokens.
- StagewiseQuantileModel fitting, predictions, conformal calibration, and fallbacks.
- Monotone rearrangement non-crossing guarantee (Rule R-UQ-05).
- Elementwise pinball loss and paired bootstrap confidence intervals (Rule R-UQ-01).
- Tier evaluation metrics calculation.
- Pairwise increment comparison with statistical verdicts (ACCEPTED, REJECTED, MARGINAL).
- Masked-missingness simulation audit (Rule R-MD-15).
- Complete pipeline runner (run_stagewise_evaluation) and test set isolation contract.
- Report serialization (to_dict, to_markdown).
"""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import polars as pl
import pytest

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.stagewise_evaluation import (
    StagewiseEvaluationReport,
    StagewiseQuantileModel,
    _compute_pinball_loss_single,
    _get_git_commit_hash,
    compute_increment_comparison,
    compute_paired_bootstrap_ci,
    evaluate_tier_predictions,
    get_cumulative_level_specs,
    get_level_feature_specs,
    prepare_feature_matrix,
    resolve_column_name,
    run_masked_missingness_audit,
    run_stagewise_evaluation,
)
from compintel.features.spec import (
    AblationDisposition,
    FeatureDataType,
    FeatureFamily,
    FeatureLevel,
    FeatureSpec,
)


def _make_dummy_spec(
    feature_id: str,
    level: FeatureLevel = FeatureLevel.L0_CORE,
    data_type: FeatureDataType = FeatureDataType.NUMERICAL_CONTINUOUS,
    is_input_feature: bool = True,
    disposition: AblationDisposition = AblationDisposition.EVALUATE_IN_PHASE_6,
) -> FeatureSpec:
    """Helper to instantiate valid FeatureSpec instances for testing."""
    return FeatureSpec(
        feature_id=feature_id,
        display_name=feature_id.replace("_", " ").title(),
        level=level,
        family=FeatureFamily.ROLE_RESPONSIBILITY,
        data_type=data_type,
        definition="Test definition",
        availability_timing="Query time",
        data_source="Test intake",
        leakage_risk="None",
        leakage_mitigations="None",
        privacy_implications="None",
        expected_utility="Testing",
        ablation_plan="Ablation test",
        ablation_threshold="None",
        is_input_feature=is_input_feature,
        disposition=disposition,
    )


@pytest.fixture
def synthetic_stagewise_df() -> pl.DataFrame:
    """Fixture providing synthetic observations populated across L0 to L3 features."""
    n_rows = 60
    rng = np.random.default_rng(42)

    roles = ["SOFTWARE", "DATA", "MLAI"] * (n_rows // 3)
    seniorities = ["JUNIOR", "MID", "SENIOR", "LEAD"] * (n_rows // 4)
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "DELHI_NCR", "MUMBAI"] * (n_rows // 5)
    yoe = [float(i % 15) + 1.0 for i in range(n_rows)]

    # Progressive pay signal based on level features
    salaries = [
        12.0
        + (y * 1.8)
        + (8.0 if s in ("SENIOR", "LEAD") else 0.0)
        + (float(rng.uniform(-1.0, 1.0)))
        for y, s in zip(yoe, seniorities, strict=False)
    ]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 5) for i in range(n_rows)]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            # L0
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            # L1
            "skills_primary": ["PYTHON", "GO", "JAVA"] * (n_rows // 3),
            "skills_depth": [3, 4, 5] * (n_rows // 3),
            "domain_specialization": ["FINTECH", "ECOMMERCE", "AI_INFRA"] * (n_rows // 3),
            "employer_tier": ["TIER_1", "TIER_2", "TIER_3"] * (n_rows // 3),
            "work_arrangement": ["HYBRID", "REMOTE", "ONSITE"] * (n_rows // 3),
            "career_velocity": [1.0, 1.2, 0.9] * (n_rows // 3),
            "leadership_scope": ["INDIVIDUAL_CONTRIBUTOR", "TEAM_LEAD"] * (n_rows // 2),
            "macro_market_regime": ["EXPANSION", "NORMAL"] * (n_rows // 2),
            # L2
            "target_employer_id": [f"ECLUST-{i % 5:02d}" for i in range(n_rows)],
            "target_level_code": ["L5", "SDE2", "MTS-3"] * (n_rows // 3),
            "company_size_bucket": ["LARGE", "MIDSIZE", "STARTUP"] * (n_rows // 3),
            "funding_stage": ["PUBLIC", "SERIES_C", "SERIES_B"] * (n_rows // 3),
            "industry_vertical": ["SAAS", "PAYMENTS", "LOGISTICS"] * (n_rows // 3),
            "competing_offers_count": [0, 1, 2] * (n_rows // 3),
            "notice_period_days": [30, 60, 90] * (n_rows // 3),
            # L3
            "verified_payslip_level": [
                "SELF_REPORTED",
                "DOCUMENT_VERIFIED",
                "ENTERPRISE_CONFIRMED",
            ]
            * (n_rows // 3),
            "fixed_allowance_ratio": [0.35, 0.45, 0.55] * (n_rows // 3),
            "project_scale_tier": ["SCALE_MODEST", "SCALE_MEDIUM", "HYPERSCALE"] * (n_rows // 3),
            "tenure_stability_index": [2.0, 3.5, 1.5] * (n_rows // 3),
            "current_guaranteed_cash": [s * 0.85 for s in salaries],  # Compare-only
            "is_synthetic": [True] * n_rows,
        }
    )


# ==============================================================================
# 1. Feature Specifications & Governance Tests
# ==============================================================================


def test_get_git_commit_hash() -> None:
    """Test git commit hash retrieval with normal and fallback paths."""
    h = _get_git_commit_hash()
    assert isinstance(h, str)
    assert len(h) > 0

    with patch("subprocess.run", side_effect=Exception("Git command failed")):
        fb = _get_git_commit_hash()
        assert fb == "UNKNOWN_COMMIT"


def test_get_level_feature_specs_excludes_compare_only() -> None:
    """Test that current pay (COMPARE_ONLY) is strictly excluded from L3 specs (Rule R-MD-13)."""
    l3_specs = get_level_feature_specs(FeatureLevel.L3_ADDITIONAL_EVIDENCE)
    feature_ids = [s.feature_id for s in l3_specs]

    # Must include input features
    assert "feat_l3_verified_payslip_level" in feature_ids
    assert "feat_l3_fixed_allowance_ratio" in feature_ids
    assert "feat_l3_project_scale_tier" in feature_ids
    assert "feat_l3_tenure_stability_index" in feature_ids

    # Rule R-MD-13 / EXP-07: Current pay must NEVER be in input feature specs
    assert "feat_l3_current_guaranteed_cash" not in feature_ids


def test_get_level_feature_specs_prohibits_demographic_proxies() -> None:
    """Test that demographic proxy prohibition throws DataContractError (Section 16 Rule 11)."""
    tainted_spec = _make_dummy_spec(
        feature_id="feat_l1_candidate_gender",
        level=FeatureLevel.L1_ROLE_PROFILE,
        data_type=FeatureDataType.CATEGORICAL,
        disposition=AblationDisposition.REJECTED,
    )

    with patch(
        "compintel.evaluation.stagewise_evaluation.get_features_by_level",
        return_value=[tainted_spec],
    ):
        with pytest.raises(DataContractError) as exc_info:
            get_level_feature_specs(FeatureLevel.L1_ROLE_PROFILE)
        assert "DEMOGRAPHIC_PROXY_PROHIBITION" in str(exc_info.value)
        assert exc_info.value.details.get("rule_id") == "R-16-11"


def test_get_cumulative_level_specs() -> None:
    """Test cumulative progression of feature specifications across tiers."""
    l0 = get_cumulative_level_specs(FeatureLevel.L0_CORE)
    l1 = get_cumulative_level_specs(FeatureLevel.L1_ROLE_PROFILE)
    l2 = get_cumulative_level_specs(FeatureLevel.L2_TARGET_OPPORTUNITY)
    l3 = get_cumulative_level_specs(FeatureLevel.L3_ADDITIONAL_EVIDENCE)

    assert len(l0) > 0
    assert len(l1) > len(l0)
    assert len(l2) > len(l1)
    assert len(l3) > len(l2)

    l0_ids = {s.feature_id for s in l0}
    l1_ids = {s.feature_id for s in l1}
    assert l0_ids.issubset(l1_ids)


def test_resolve_column_name_and_prepare_feature_matrix(
    synthetic_stagewise_df: pl.DataFrame,
) -> None:
    """Test alias resolution and matrix preparation with masking."""
    specs = get_cumulative_level_specs(FeatureLevel.L1_ROLE_PROFILE)

    # Verify column resolution
    yoe_spec = next(s for s in specs if s.feature_id == "feat_l0_years_experience")
    assert resolve_column_name(yoe_spec, synthetic_stagewise_df.columns) == "years_experience"

    # Dummy spec that cannot resolve
    dummy_spec = _make_dummy_spec("feat_non_existent")
    assert resolve_column_name(dummy_spec, synthetic_stagewise_df.columns) is None

    # Prepare feature matrix normally
    x_df, cat_cols = prepare_feature_matrix(synthetic_stagewise_df, specs)
    assert isinstance(x_df, pd.DataFrame)
    assert len(x_df) == len(synthetic_stagewise_df)
    assert "feat_l0_years_experience" in x_df.columns
    assert "feat_l0_role_family" in cat_cols

    # Prepare matrix with missingness masking
    masked_set = {"feat_l1_skills_primary", "feat_l0_years_experience"}
    x_masked, _ = prepare_feature_matrix(synthetic_stagewise_df, specs, mask_features=masked_set)
    # Masked continuous feature is set to 0.0
    assert np.all(x_masked["feat_l0_years_experience"] == 0.0)
    # Masked categorical feature is set to MISSING_UNSPECIFIED
    assert np.all(x_masked["feat_l1_skills_primary"] == "MISSING_UNSPECIFIED")


def test_prepare_feature_matrix_nan_handling() -> None:
    """Test that NaNs in numeric features are filled with median or zero."""
    df_with_nan = pl.DataFrame(
        {
            "years_experience": [1.0, 5.0, None, 9.0],
            "role_family": ["SOFTWARE", None, "DATA", "MLAI"],
        }
    )
    specs = [
        _make_dummy_spec(
            "feat_l0_years_experience", data_type=FeatureDataType.NUMERICAL_CONTINUOUS
        ),
        _make_dummy_spec("feat_l0_role_family", data_type=FeatureDataType.CATEGORICAL),
    ]
    x_df, _ = prepare_feature_matrix(df_with_nan, specs)
    # NaN replaced by median of [1, 5, 9] = 5.0
    assert x_df["feat_l0_years_experience"].iloc[2] == 5.0
    # Null category replaced by MISSING_UNSPECIFIED
    assert x_df["feat_l0_role_family"].iloc[1] == "MISSING_UNSPECIFIED"


# ==============================================================================
# 2. Model Wrapper & Non-Crossing Monotonicity Tests (Rule R-UQ-05)
# ==============================================================================


def test_stagewise_quantile_model_empty_raises(synthetic_stagewise_df: pl.DataFrame) -> None:
    """Test that training on an empty dataset raises CompIntelValidationError."""
    empty_df = synthetic_stagewise_df.filter(pl.col("guaranteed_cash_annual") < 0)
    specs = get_cumulative_level_specs(FeatureLevel.L0_CORE)
    model = StagewiseQuantileModel(level=FeatureLevel.L0_CORE, specs=specs)
    with pytest.raises(CompIntelValidationError):
        model.fit(empty_df)


def test_stagewise_quantile_model_fit_predict_and_noncrossing(
    synthetic_stagewise_df: pl.DataFrame,
) -> None:
    """Test model fitting, conformal adjustment, and monotonic non-crossing guarantees."""
    train_df = synthetic_stagewise_df[:40]
    cal_df = synthetic_stagewise_df[40:50]
    eval_df = synthetic_stagewise_df[50:]

    specs = get_cumulative_level_specs(FeatureLevel.L0_CORE)
    model = StagewiseQuantileModel(level=FeatureLevel.L0_CORE, specs=specs, seed=42)

    # Fit with calibration split
    model.fit(train_df, calibrate_df=cal_df)
    assert model._conformal_q >= 0.0

    q10, q50, q90 = model.predict(eval_df)
    assert len(q10) == len(eval_df)
    assert len(q50) == len(eval_df)
    assert len(q90) == len(eval_df)

    # Strict Monotone Non-Crossing Check (Rule R-UQ-05): P10 <= P50 <= P90
    assert np.all(q10 <= q50 + 1e-6)
    assert np.all(q50 <= q90 + 1e-6)
    assert np.all(q10 >= 0.50)  # Lower bound sanity guard


def test_stagewise_quantile_model_lightgbm_fallback(
    synthetic_stagewise_df: pl.DataFrame,
) -> None:
    """Test graceful fallback to LightGBM quantile models when CatBoost raises."""
    train_df = synthetic_stagewise_df[:40]
    specs = get_cumulative_level_specs(FeatureLevel.L0_CORE)
    model = StagewiseQuantileModel(level=FeatureLevel.L0_CORE, specs=specs, seed=42)

    with patch("catboost.CatBoostRegressor.fit", side_effect=Exception("CatBoost failed")):
        model.fit(train_df)
        assert model._cb_model is None
        assert len(model._lgb_models) == 3
        assert 0.10 in model._lgb_models
        assert 0.50 in model._lgb_models
        assert 0.90 in model._lgb_models

        q10, q50, q90 = model.predict(train_df[:10])
        assert len(q10) == 10
        assert np.all(q10 <= q50 + 1e-6)
        assert np.all(q50 <= q90 + 1e-6)


# ==============================================================================
# 3. Statistical Metrics & Paired Bootstrap Tests (Rule R-UQ-01)
# ==============================================================================


def test_pinball_loss_single_exact() -> None:
    """Test elementwise pinball loss calculation against mathematical definition."""
    y = np.array([20.0, 30.0])
    q = np.array([25.0, 25.0])  # Over-prediction, Under-prediction

    # alpha = 0.5 (Median absolute error / 2)
    l50 = _compute_pinball_loss_single(y, q, 0.5)
    # y=20, q=25 -> diff = -5 -> (0.5 - 1.0) * (-5) = 2.5
    # y=30, q=25 -> diff = 5 -> 0.5 * 5 = 2.5
    assert np.allclose(l50, [2.5, 2.5])

    # alpha = 0.1
    l10 = _compute_pinball_loss_single(y, q, 0.1)
    # y=20, q=25 -> diff = -5 -> -0.9 * (-5) = 4.5
    # y=30, q=25 -> diff = 5 -> 0.1 * 5 = 0.5
    assert np.allclose(l10, [4.5, 0.5])


def test_compute_paired_bootstrap_ci() -> None:
    """Test paired bootstrap confidence interval calculation and boundary conditions."""
    # Clearly positive delta array
    deltas = np.array([1.5, 1.2, 1.8, 1.4, 1.6, 2.0, 1.3, 1.7])
    ci_l, ci_u, is_sig = compute_paired_bootstrap_ci(deltas, n_resamples=200, seed=42)
    assert ci_l > 0.0
    assert ci_u > ci_l
    assert is_sig is True

    # Deltas crossing zero
    deltas_zero = np.array([-0.5, 0.5, -0.2, 0.3, -0.1, 0.2])
    ci_l_z, ci_u_z, is_sig_z = compute_paired_bootstrap_ci(deltas_zero, n_resamples=200, seed=42)
    assert ci_l_z < 0.0 < ci_u_z
    assert is_sig_z is False

    # Single-element boundary condition
    single = np.array([0.42])
    pt_l, pt_u, sig = compute_paired_bootstrap_ci(single)
    assert pt_l == 0.42
    assert pt_u == 0.42
    assert sig is False

    # Empty array boundary condition
    empty_ci_l, empty_ci_u, empty_sig = compute_paired_bootstrap_ci(np.array([]))
    assert empty_ci_l == 0.0
    assert empty_ci_u == 0.0
    assert empty_sig is False


def test_evaluate_tier_predictions() -> None:
    """Test evaluation metrics computation on predicted quantiles."""
    y = np.array([20.0, 30.0, 40.0])
    q10 = np.array([15.0, 25.0, 35.0])
    q50 = np.array([20.0, 30.0, 40.0])
    q90 = np.array([25.0, 35.0, 45.0])

    metrics = evaluate_tier_predictions(y, q10, q50, q90)
    assert metrics["mae"] == 0.0
    assert metrics["mdape"] == 0.0
    assert metrics["empirical_coverage"] == 1.0
    assert metrics["mean_interval_width"] == 10.0
    assert metrics["crossing_rate"] == 0.0
    assert metrics["mean_pinball_loss"] > 0.0


def test_compute_increment_comparison_verdicts() -> None:
    """Test verdict generation: ACCEPTED_INCREMENT, REJECTED_DEGRADATION, MARGINAL_NO_EFFECT."""
    n = 50
    # Case 1: ACCEPTED_INCREMENT (Significant loss reduction & coverage in range)
    base_m: dict[str, Any] = {
        "mean_pinball_loss": 2.50,
        "pinball_q10": 1.0,
        "pinball_q50": 1.0,
        "pinball_q90": 1.0,
        "mae": 3.0,
        "mdape": 0.15,
        "empirical_coverage": 0.80,
        "mean_interval_width": 10.0,
        "_mean_pinball_arr": np.full(n, 2.50),
        "_loss_10_arr": np.full(n, 1.0),
        "_loss_50_arr": np.full(n, 1.0),
        "_loss_90_arr": np.full(n, 1.0),
        "_abs_err_arr": np.full(n, 3.0),
        "_coverage_arr": np.full(n, 0.80),
        "_width_arr": np.full(n, 10.0),
    }

    inc_improved: dict[str, Any] = {
        "mean_pinball_loss": 2.20,
        "pinball_q10": 0.9,
        "pinball_q50": 0.9,
        "pinball_q90": 0.9,
        "mae": 2.5,
        "mdape": 0.12,
        "empirical_coverage": 0.82,
        "mean_interval_width": 9.0,
        "_mean_pinball_arr": np.full(n, 2.20),
        "_loss_10_arr": np.full(n, 0.9),
        "_loss_50_arr": np.full(n, 0.9),
        "_loss_90_arr": np.full(n, 0.9),
        "_abs_err_arr": np.full(n, 2.5),
        "_coverage_arr": np.full(n, 0.82),
        "_width_arr": np.full(n, 9.0),
    }

    res_acc = compute_increment_comparison("L0", "L1", base_m, inc_improved, n_resamples=50)
    assert res_acc.verdict == "ACCEPTED_INCREMENT"
    assert res_acc.width_ratio == 0.9

    # Case 2: REJECTED_DEGRADATION (Statistically significant loss inflation)
    inc_degraded: dict[str, Any] = {
        "mean_pinball_loss": 2.80,
        "pinball_q10": 1.1,
        "pinball_q50": 1.1,
        "pinball_q90": 1.1,
        "mae": 3.5,
        "mdape": 0.18,
        "empirical_coverage": 0.75,
        "mean_interval_width": 11.0,
        "_mean_pinball_arr": np.full(n, 2.80),
        "_loss_10_arr": np.full(n, 1.1),
        "_loss_50_arr": np.full(n, 1.1),
        "_loss_90_arr": np.full(n, 1.1),
        "_abs_err_arr": np.full(n, 3.5),
        "_coverage_arr": np.full(n, 0.75),
        "_width_arr": np.full(n, 11.0),
    }
    res_deg = compute_increment_comparison("L0", "L1", base_m, inc_degraded, n_resamples=50)
    assert res_deg.verdict == "REJECTED_DEGRADATION"

    # Case 3: MARGINAL_NO_EFFECT (Small delta)
    inc_marginal: dict[str, Any] = {
        "mean_pinball_loss": 2.49,
        "pinball_q10": 1.0,
        "pinball_q50": 1.0,
        "pinball_q90": 1.0,
        "mae": 3.0,
        "mdape": 0.15,
        "empirical_coverage": 0.80,
        "mean_interval_width": 9.9,
        "_mean_pinball_arr": np.full(n, 2.49),
        "_loss_10_arr": np.full(n, 1.0),
        "_loss_50_arr": np.full(n, 1.0),
        "_loss_90_arr": np.full(n, 1.0),
        "_abs_err_arr": np.full(n, 3.0),
        "_coverage_arr": np.full(n, 0.80),
        "_width_arr": np.full(n, 9.9),
    }
    res_mar = compute_increment_comparison("L0", "L1", base_m, inc_marginal, n_resamples=50)
    assert res_mar.verdict == "MARGINAL_NO_EFFECT"


# ==============================================================================
# 4. Masked Missingness Simulation Audit Tests (Rule R-MD-15)
# ==============================================================================


def test_run_masked_missingness_audit_outcomes(synthetic_stagewise_df: pl.DataFrame) -> None:
    """Test masked missingness audit with mock dedicated and unified models."""
    eval_df = synthetic_stagewise_df[:20]
    y_true = eval_df["guaranteed_cash_annual"].to_numpy().astype(np.float64)

    # Construct mock models
    mock_l0 = MagicMock(spec=StagewiseQuantileModel)
    mock_l1 = MagicMock(spec=StagewiseQuantileModel)
    mock_l2 = MagicMock(spec=StagewiseQuantileModel)
    mock_u3 = MagicMock(spec=StagewiseQuantileModel)

    mock_u3.level = FeatureLevel.L3_ADDITIONAL_EVIDENCE
    mock_u3.specs = get_cumulative_level_specs(FeatureLevel.L3_ADDITIONAL_EVIDENCE)

    # Mock predictions: dedicated models
    pred_tuple = (y_true - 5.0, y_true, y_true + 5.0)
    mock_l0.predict.return_value = pred_tuple
    mock_l1.predict.return_value = pred_tuple
    mock_l2.predict.return_value = pred_tuple

    # 1. Preserves calibration case: unified model produces close predictions
    mock_u3.predict.return_value = (y_true - 5.1, y_true, y_true + 5.1)
    dedicated = {
        FeatureLevel.L0_CORE: mock_l0,
        FeatureLevel.L1_ROLE_PROFILE: mock_l1,
        FeatureLevel.L2_TARGET_OPPORTUNITY: mock_l2,
    }

    audit_good = run_masked_missingness_audit(dedicated, mock_u3, eval_df, y_true)
    assert audit_good.overall_recommendation == "SERVE_UNIFIED_WITH_MISSINGNESS"
    assert len(audit_good.comparisons) == 3
    assert all(c.verdict == "PRESERVES_CALIBRATION" for c in audit_good.comparisons)

    # 2. Severe degradation case: unified model degrades severely
    mock_u3.predict.return_value = (y_true + 20.0, y_true + 30.0, y_true + 40.0)
    audit_bad = run_masked_missingness_audit(dedicated, mock_u3, eval_df, y_true)
    assert audit_bad.overall_recommendation == "SERVE_NESTED_MODELS"
    assert any(c.verdict == "SEVERE_DEGRADATION" for c in audit_bad.comparisons)


# ==============================================================================
# 5. Full Pipeline & Contract Violations (Rule R-MD-02)
# ==============================================================================


def test_run_stagewise_evaluation_test_split_lock_enforced(
    synthetic_stagewise_df: pl.DataFrame,
) -> None:
    """Test that evaluating on locked 'test' split raises DataContractError (Rule R-MD-02)."""
    with pytest.raises(DataContractError) as exc_info:
        run_stagewise_evaluation(
            train_df=synthetic_stagewise_df,
            eval_df=synthetic_stagewise_df,
            eval_split_name="test",
        )
    assert "EVALUATION_ISOLATION_VIOLATION" in str(exc_info.value)
    assert exc_info.value.details.get("rule_id") == "R-MD-02"


def test_run_stagewise_evaluation_empty_eval_raises(
    synthetic_stagewise_df: pl.DataFrame,
) -> None:
    """Test that empty evaluation dataframe raises CompIntelValidationError."""
    empty_df = synthetic_stagewise_df.filter(pl.col("guaranteed_cash_annual") < 0)
    with pytest.raises(CompIntelValidationError):
        run_stagewise_evaluation(
            train_df=synthetic_stagewise_df,
            eval_df=empty_df,
            eval_split_name="select",
        )


def test_run_stagewise_evaluation_pipeline_and_serialization(
    synthetic_stagewise_df: pl.DataFrame,
) -> None:
    """Test complete stage-wise evaluation pipeline, report generation, and serialization."""
    train_df = synthetic_stagewise_df[:36]
    cal_df = synthetic_stagewise_df[36:48]
    eval_df = synthetic_stagewise_df[48:]

    report = run_stagewise_evaluation(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=cal_df,
        eval_split_name="select",
        n_resamples=50,  # Fast bootstrap for unit test
        seed=42,
    )

    assert isinstance(report, StagewiseEvaluationReport)
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == len(eval_df)
    assert len(report.level_summaries) == 4  # L0, L1, L2, L3
    assert len(report.increment_summaries) == 3  # L0->L1, L1->L2, L2->L3
    assert report.masked_missingness_summary is not None
    assert report.overall_verdict in (
        "PASS_ALL_INCREMENTS",
        "PASS_SELECTIVE_INCREMENTS",
        "MARGINAL_PERSONALIZATION_GAIN",
    )

    # Test serialization to dict
    d = report.to_dict()
    assert d["report_id"] == report.report_id
    assert len(d["level_summaries"]) == 4
    assert len(d["increment_summaries"]) == 3
    assert "masked_missingness_summary" in d

    # Test serialization to markdown
    md = report.to_markdown()
    assert "# Stage-Wise Progressive Personalization Evaluation Report" in md
    assert "Level 0: Core Baseline" in md
    assert "Level 3: Additional Evidence" in md
    assert "Masked-Missingness Degradation Audit" in md
