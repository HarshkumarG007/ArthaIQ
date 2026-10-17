"""Unit tests for Rung E gradient boosted quantile models, crossing diagnostics, and repair.

Adheres to Rules R-MD-01, R-MD-04, R-MD-06, R-MD-08, R-MD-10, R-UQ-01, R-UQ-05, R-TS-01, R-TS-03.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from compintel.models.gbm import (
    CatBoostQuantileModel,
    GBMModelType,
    GBMQuantileConfig,
    LightGBMQuantileModel,
    create_gbm_quantile_model,
    detect_and_repair_quantile_crossings,
)


@pytest.fixture
def sample_training_df() -> pl.DataFrame:
    """Fixture providing clean training data for quantile models."""
    return pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "DATA", "SOFTWARE", "MLAI", "SOFTWARE", "DATA"],
            "seniority": ["MID", "SENIOR", "JUNIOR", "STAFF", "LEAD", "MID"],
            "location": ["BANGALORE", "HYDERABAD", "BANGALORE", "PUNE", "DELHI_NCR", "BANGALORE"],
            "years_experience": [4.0, 8.5, 1.5, 12.0, 9.0, 5.0],
            "guaranteed_cash_annual": [18.0, 32.0, 10.5, 55.0, 42.0, 22.0],
        }
    )


@pytest.fixture
def sample_test_df() -> pl.DataFrame:
    """Fixture providing test data including in-range, out-of-range, and unseen categories."""
    return pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "DATA", "UNKNOWN_ROLE"],
            "seniority": ["MID", "SENIOR", "NEW_LEVEL"],
            "location": ["BANGALORE", "HYDERABAD", "REMOTE"],
            "years_experience": [4.5, -2.0, 48.0],
        }
    )


# ==============================================================================
# 1. Configuration & Validation Tests
# ==============================================================================


@pytest.mark.unit
def test_gbm_quantile_config_defaults() -> None:
    """Verify default configuration parameters for GBM quantile models."""
    cfg = GBMQuantileConfig()
    assert cfg.model_type == GBMModelType.LIGHTGBM
    assert cfg.quantiles == (0.10, 0.50, 0.90)
    assert cfg.repair_crossing is True
    assert cfg.learning_rate == 0.05
    assert cfg.n_estimators == 100
    assert cfg.max_depth == 4
    assert cfg.num_leaves == 15
    assert cfg.l2_regularization == 1.0
    assert cfg.min_child_samples == 5
    assert cfg.subsample == 0.8
    assert cfg.colsample_bytree == 0.8
    assert cfg.random_seed == 42
    assert cfg.log_target is True
    assert cfg.max_experience_bound == 40.0


@pytest.mark.unit
def test_gbm_quantile_config_validations() -> None:
    """Verify quantiles validation rules in GBMQuantileConfig."""
    # Valid custom quantiles
    cfg = GBMQuantileConfig(quantiles=(0.05, 0.25, 0.50, 0.75, 0.95))
    assert len(cfg.quantiles) == 5

    # Rejects fewer than 2 quantiles
    with pytest.raises(ValueError, match="At least 2 quantiles"):
        GBMQuantileConfig(quantiles=(0.50,))

    # Rejects quantiles outside (0, 1)
    with pytest.raises(ValueError, match="strictly in \\(0, 1\\)"):
        GBMQuantileConfig(quantiles=(0.0, 0.50, 0.90))

    with pytest.raises(ValueError, match="strictly in \\(0, 1\\)"):
        GBMQuantileConfig(quantiles=(0.10, 0.50, 1.0))

    # Rejects non-increasing quantiles
    with pytest.raises(ValueError, match="strictly monotonically increasing"):
        GBMQuantileConfig(quantiles=(0.50, 0.10, 0.90))

    with pytest.raises(ValueError, match="strictly monotonically increasing"):
        GBMQuantileConfig(quantiles=(0.10, 0.50, 0.50))


# ==============================================================================
# 2. Crossing Detection & Monotone Rearrangement Tests
# ==============================================================================


@pytest.mark.unit
def test_detect_and_repair_crossings_clean() -> None:
    """Verify detection on cleanly monotonic quantile predictions."""
    raw = np.array(
        [
            [10.0, 15.0, 25.0],
            [12.0, 18.0, 22.0],
            [8.0, 11.0, 16.0],
        ],
        dtype=np.float64,
    )
    final, is_repaired, max_viol, diag = detect_and_repair_quantile_crossings(raw, repair=True)

    np.testing.assert_allclose(final, raw)
    assert not np.any(is_repaired)
    assert np.all(max_viol == 0.0)
    assert diag.total_observations == 3
    assert diag.evaluated_observations == 3
    assert diag.raw_crossing_count == 0
    assert diag.raw_crossing_rate == 0.0
    assert diag.repaired_crossing_count == 0
    assert diag.repaired_crossing_rate == 0.0
    assert diag.max_raw_crossing_delta_lpa == 0.0


@pytest.mark.unit
def test_detect_and_repair_crossings_with_violations() -> None:
    """Verify crossing detection and monotone rearrangement repair (Rule R-UQ-05)."""
    # Row 0: p10=20 > p50=15 (crossing delta = 5.0)
    # Row 1: p50=30 > p90=25 (crossing delta = 5.0)
    # Row 2: monotonic (no crossing)
    raw = np.array(
        [
            [20.0, 15.0, 25.0],
            [18.0, 30.0, 25.0],
            [10.0, 15.0, 20.0],
        ],
        dtype=np.float64,
    )

    # 1. With repair=True
    final, is_repaired, max_viol, diag = detect_and_repair_quantile_crossings(raw, repair=True)

    expected_repaired = np.array(
        [
            [15.0, 20.0, 25.0],
            [18.0, 25.0, 30.0],
            [10.0, 15.0, 20.0],
        ],
        dtype=np.float64,
    )
    np.testing.assert_allclose(final, expected_repaired)
    assert list(is_repaired) == [True, True, False]
    assert max_viol[0] == 5.0
    assert max_viol[1] == 5.0
    assert max_viol[2] == 0.0

    assert diag.total_observations == 3
    assert diag.evaluated_observations == 3
    assert diag.raw_crossing_count == 2
    assert pytest.approx(diag.raw_crossing_rate, rel=1e-5) == 2.0 / 3.0
    # Rule R-UQ-05: Post-repair crossing MUST be 0.0
    assert diag.repaired_crossing_count == 0
    assert diag.repaired_crossing_rate == 0.0
    assert diag.max_raw_crossing_delta_lpa == 5.0

    diag_dict = diag.to_dict()
    assert diag_dict["raw_crossing_count"] == 2
    assert diag_dict["repaired_crossing_count"] == 0

    # 2. With repair=False
    final_no_rep, is_rep_no, _, diag_no_rep = detect_and_repair_quantile_crossings(
        raw, repair=False
    )
    np.testing.assert_allclose(final_no_rep, raw)
    assert list(is_rep_no) == [True, True, False]
    assert diag_no_rep.raw_crossing_count == 2
    assert diag_no_rep.repaired_crossing_count == 2
    assert pytest.approx(diag_no_rep.repaired_crossing_rate, rel=1e-5) == 2.0 / 3.0


@pytest.mark.unit
def test_detect_and_repair_crossings_evaluated_mask() -> None:
    """Verify crossing diagnostics correctly isolate evaluated rows from abstained rows."""
    raw = np.array(
        [
            [20.0, 15.0, 25.0],  # crossed, active
            [30.0, 20.0, 10.0],  # crossed, but abstained
            [10.0, 15.0, 20.0],  # monotonic, active
        ],
        dtype=np.float64,
    )
    evaluated_mask = np.array([True, False, True], dtype=bool)

    _, is_repaired, _, diag = detect_and_repair_quantile_crossings(
        raw, evaluated_mask=evaluated_mask, repair=True
    )
    assert is_repaired[0] is np.True_
    assert is_repaired[1] is np.False_  # abstained, not evaluated
    assert is_repaired[2] is np.False_

    assert diag.total_observations == 3
    assert diag.evaluated_observations == 2
    assert diag.raw_crossing_count == 1
    assert diag.raw_crossing_rate == 0.50
    assert diag.repaired_crossing_count == 0
    assert diag.repaired_crossing_rate == 0.0


@pytest.mark.unit
def test_detect_and_repair_empty() -> None:
    """Verify crossing diagnostics on empty array."""
    raw = np.empty((0, 3), dtype=np.float64)
    final, is_repaired, max_viol, diag = detect_and_repair_quantile_crossings(raw, repair=True)
    assert final.shape == (0, 3)
    assert len(is_repaired) == 0
    assert len(max_viol) == 0
    assert diag.total_observations == 0
    assert diag.evaluated_observations == 0
    assert diag.raw_crossing_count == 0


# ==============================================================================
# 3. LightGBM Quantile Model Tests
# ==============================================================================


@pytest.mark.unit
def test_lightgbm_quantile_model_lifecycle(
    sample_training_df: pl.DataFrame, sample_test_df: pl.DataFrame
) -> None:
    """Verify LightGBMQuantileModel fit, predict, resource profiling, and crossing repair."""
    cfg = GBMQuantileConfig(
        model_type=GBMModelType.LIGHTGBM,
        n_estimators=10,
        learning_rate=0.1,
        min_child_samples=1,
        repair_crossing=True,
    )
    model = LightGBMQuantileModel(cfg)
    assert model.model_name == "LightGBMQuantileModel"
    assert model.is_fitted is False
    assert model.metrics is None
    assert model.last_diagnostics is None
    assert model.quantiles == (0.10, 0.50, 0.90)

    # Fit model
    fitted = model.fit(sample_training_df)
    assert fitted is model
    assert model.is_fitted is True

    # Resource profiling metrics (Rule R-MD-10)
    metrics = model.metrics
    assert metrics is not None
    assert metrics.fit_time_seconds > 0.0
    assert metrics.peak_memory_mb >= 0.0
    assert metrics.n_train_samples == len(sample_training_df)
    assert metrics.n_features == 4

    # Predict structured list
    preds = model.predict(sample_test_df)
    assert len(preds) == len(sample_test_df)

    # Row 0: in-range valid profile
    p0 = preds[0]
    assert p0.is_abstained is False
    assert p0.abstention_reason is None
    assert p0.p10 is not None and p0.p50 is not None and p0.p90 is not None
    assert p0.p10 <= p0.p50 <= p0.p90  # Monotonicity guaranteed (Rule R-UQ-05)
    assert p0.model_name == "LightGBMQuantileModel"

    # Row 1: out-of-range YoE (-2.0) -> Thin evidence abstention (Rule R-MD-08)
    p1 = preds[1]
    assert p1.is_abstained is True
    assert p1.abstention_reason == "THIN_EVIDENCE"
    assert p1.p10 is None
    assert p1.p50 is None
    assert p1.p90 is None

    # Row 2: out-of-range YoE (48.0 > max_bound 40.0) -> Thin evidence abstention
    p2 = preds[2]
    assert p2.is_abstained is True
    assert p2.abstention_reason == "THIN_EVIDENCE"

    # Verify crossing diagnostics
    diag = model.last_diagnostics
    assert diag is not None
    assert diag.total_observations == 3
    assert diag.evaluated_observations == 1
    assert diag.repaired_crossing_count == 0
    assert diag.repaired_crossing_rate == 0.0

    # Predict Polars DataFrame
    pred_df = model.predict_df(sample_test_df)
    assert isinstance(pred_df, pl.DataFrame)
    assert pred_df.shape[0] == 3
    expected_cols = [
        "p10",
        "p50",
        "p90",
        "raw_p10",
        "raw_p50",
        "raw_p90",
        "is_crossing_repaired",
        "is_abstained",
        "abstention_reason",
        "model_name",
    ]
    for col in expected_cols:
        assert col in pred_df.columns

    # Verify to_dict on QuantilePrediction
    d0 = p0.to_dict()
    assert d0["target_measure"] == "guaranteed_cash_annual"
    assert d0["currency"] == "INR"
    assert d0["nominal_basis"] is True


# ==============================================================================
# 4. CatBoost Quantile Model Tests
# ==============================================================================


@pytest.mark.unit
def test_catboost_quantile_model_lifecycle(
    sample_training_df: pl.DataFrame, sample_test_df: pl.DataFrame
) -> None:
    """Verify CatBoostQuantileModel MultiQuantile fit, predict, and crossing repair."""
    cfg = GBMQuantileConfig(
        model_type=GBMModelType.CATBOOST,
        n_estimators=10,
        learning_rate=0.1,
        repair_crossing=True,
    )
    model = CatBoostQuantileModel(cfg)
    assert model.model_name == "CatBoostQuantileModel"
    assert model.is_fitted is False

    # Fit model
    model.fit(sample_training_df)
    assert model.is_fitted is True

    # Resource profiling
    metrics = model.metrics
    assert metrics is not None
    assert metrics.fit_time_seconds > 0.0
    assert metrics.peak_memory_mb >= 0.0

    # Predict list
    preds = model.predict(sample_test_df)
    assert len(preds) == 3

    # In-range record
    p0 = preds[0]
    assert p0.is_abstained is False
    assert p0.p10 is not None and p0.p50 is not None and p0.p90 is not None
    assert p0.p10 <= p0.p50 <= p0.p90
    assert p0.model_name == "CatBoostQuantileModel"

    # Out-of-range records
    assert preds[1].is_abstained is True
    assert preds[1].abstention_reason == "THIN_EVIDENCE"
    assert preds[2].is_abstained is True
    assert preds[2].abstention_reason == "THIN_EVIDENCE"

    # Diagnostics
    diag = model.last_diagnostics
    assert diag is not None
    assert diag.repaired_crossing_rate == 0.0

    # Polars DataFrame predict
    df_preds = model.predict_df(sample_test_df)
    assert len(df_preds) == 3
    assert df_preds["model_name"][0] == "CatBoostQuantileModel"


# ==============================================================================
# 5. Feature Isolation, Unseen Categories, and Missing Data Tests
# ==============================================================================


@pytest.mark.unit
def test_feature_isolation_and_unseen_categories(sample_training_df: pl.DataFrame) -> None:
    """Verify that unseen categories in test sets map gracefully to OTHER (Rule R-MD-04)."""
    model = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))
    model.fit(sample_training_df)

    # Completely unseen categorical values
    unseen_df = pl.DataFrame(
        {
            "role_family": ["QUANT_RESEARCH", "HARDWARE"],
            "seniority": ["FELLOW", "INTERN"],
            "location": ["CHENNAI", "AHMEDABAD"],
            "years_experience": [5.0, 2.0],
        }
    )

    preds = model.predict(unseen_df)
    assert len(preds) == 2
    for p in preds:
        assert p.is_abstained is False
        assert p.p10 is not None and p.p50 is not None and p.p90 is not None
        assert p.p10 <= p.p50 <= p.p90


@pytest.mark.unit
def test_missing_values_imputation(sample_training_df: pl.DataFrame) -> None:
    """Verify that null experience is imputed with median and null categoricals with OTHER."""
    df_with_nulls = sample_training_df.with_columns(
        [
            pl.when(pl.col("years_experience") == 1.5)
            .then(None)
            .otherwise(pl.col("years_experience"))
            .alias("years_experience"),
            pl.when(pl.col("location") == "PUNE")
            .then(None)
            .otherwise(pl.col("location"))
            .alias("location"),
        ]
    )
    model = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))
    model.fit(df_with_nulls)
    assert model.is_fitted is True

    test_df = pl.DataFrame(
        {
            "role_family": ["SOFTWARE"],
            "seniority": ["MID"],
            "location": [None],
            "years_experience": [None],
        }
    )
    preds = model.predict(test_df)
    assert len(preds) == 1
    assert preds[0].is_abstained is False


# ==============================================================================
# 6. Error Handling & Invariant Rejections
# ==============================================================================


@pytest.mark.unit
def test_unfitted_model_raises_runtime_error(sample_test_df: pl.DataFrame) -> None:
    """Verify that calling predict before fit raises RuntimeError."""
    lgb_model = LightGBMQuantileModel()
    with pytest.raises(RuntimeError, match="must be fitted before predict"):
        lgb_model.predict(sample_test_df)

    cb_model = CatBoostQuantileModel()
    with pytest.raises(RuntimeError, match="must be fitted before predict"):
        cb_model.predict(sample_test_df)


@pytest.mark.unit
def test_empty_dataframe_handling(sample_training_df: pl.DataFrame) -> None:
    """Verify empty DataFrame predictions and fit rejection."""
    model = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))

    # Fitting on empty df raises ValueError
    empty_df = sample_training_df.clear()
    with pytest.raises(ValueError, match="Cannot fit model on empty DataFrame"):
        model.fit(empty_df)

    # Predict on empty df returns empty results
    model.fit(sample_training_df)
    empty_query = pl.DataFrame(
        schema={
            "role_family": pl.String,
            "seniority": pl.String,
            "location": pl.String,
            "years_experience": pl.Float64,
        }
    )
    assert model.predict(empty_query) == []
    assert len(model.predict_df(empty_query)) == 0
    assert model.last_diagnostics is not None
    assert model.last_diagnostics.total_observations == 0


@pytest.mark.unit
def test_missing_required_columns_rejection(sample_training_df: pl.DataFrame) -> None:
    """Verify missing required feature or target columns trigger explicit ValueError."""
    model = LightGBMQuantileModel()

    # Missing target col
    df_no_target = sample_training_df.drop("guaranteed_cash_annual")
    with pytest.raises(ValueError, match="Target column 'guaranteed_cash_annual' not found"):
        model.fit(df_no_target)

    # Missing categorical col
    df_no_role = sample_training_df.drop("role_family")
    with pytest.raises(ValueError, match="Missing required categorical column 'role_family'"):
        model.fit(df_no_role)

    # Missing experience col
    df_no_yoe = sample_training_df.drop("years_experience")
    with pytest.raises(ValueError, match="Missing required continuous column 'years_experience'"):
        model.fit(df_no_yoe)


@pytest.mark.unit
def test_non_positive_target_rejection(sample_training_df: pl.DataFrame) -> None:
    """Verify non-positive compensation targets are rejected per Rule R-MD-06."""
    bad_df = sample_training_df.with_columns(pl.lit(0.0).alias("guaranteed_cash_annual"))
    model = LightGBMQuantileModel()
    with pytest.raises(ValueError, match="Target compensation must be strictly positive"):
        model.fit(bad_df)


# ==============================================================================
# 7. Model Factory Tests
# ==============================================================================


@pytest.mark.unit
def test_create_gbm_quantile_model_factory() -> None:
    """Verify factory instantiation of Rung E quantile models."""
    lgb_cfg = GBMQuantileConfig(model_type=GBMModelType.LIGHTGBM)
    lgb_mod = create_gbm_quantile_model(lgb_cfg)
    assert isinstance(lgb_mod, LightGBMQuantileModel)

    cb_cfg = GBMQuantileConfig(model_type=GBMModelType.CATBOOST)
    cb_mod = create_gbm_quantile_model(cb_cfg)
    assert isinstance(cb_mod, CatBoostQuantileModel)

    with pytest.raises(ValueError, match="Unsupported GBM model family"):
        # Bypass enum to test guard
        create_gbm_quantile_model(GBMQuantileConfig.model_construct(model_type="unsupported_type"))


# ==============================================================================
# 8. Canonical Dataset Integration Test
# ==============================================================================


@pytest.mark.unit
def test_canonical_observations_quantile_fit_and_predict() -> None:
    """Test fitting LightGBM and CatBoost quantile models on canonical data if present."""
    canonical_path = Path("data/canonical/canonical_observations.parquet")
    if not canonical_path.exists():
        pytest.skip("Canonical dataset not present on clean checkout (R-DA-08).")

    df = pl.read_parquet(canonical_path)
    if len(df) < 5:
        pytest.skip("Insufficient records in canonical parquet.")

    # 1. LightGBM Quantile
    lgb_model = LightGBMQuantileModel(
        GBMQuantileConfig(
            model_type=GBMModelType.LIGHTGBM,
            n_estimators=10,
            learning_rate=0.1,
            min_child_samples=1,
            repair_crossing=True,
        )
    )
    lgb_model.fit(df)
    preds = lgb_model.predict(df)
    assert len(preds) == len(df)
    diag = lgb_model.last_diagnostics
    assert diag is not None
    assert diag.repaired_crossing_count == 0
    assert diag.repaired_crossing_rate == 0.0

    # 2. CatBoost MultiQuantile
    cb_model = CatBoostQuantileModel(
        GBMQuantileConfig(
            model_type=GBMModelType.CATBOOST,
            n_estimators=10,
            learning_rate=0.1,
            repair_crossing=True,
        )
    )
    cb_model.fit(df)
    preds_cb = cb_model.predict(df)
    assert len(preds_cb) == len(df)
    diag_cb = cb_model.last_diagnostics
    assert diag_cb is not None
    assert diag_cb.repaired_crossing_count == 0
    assert diag_cb.repaired_crossing_rate == 0.0


@pytest.mark.unit
def test_quantile_model_internal_edge_cases() -> None:
    """Verify internal edge cases and defensive checks."""
    import pandas as pd

    # 1. _check_abstention with empty DataFrame
    lgb_model = LightGBMQuantileModel()
    mask, reasons = lgb_model._check_abstention(pl.DataFrame())
    assert len(mask) == 0
    assert len(reasons) == 0

    # 2. _predict_raw_quantiles raises RuntimeError when internal regressor is missing
    dummy_df = pd.DataFrame({"role_family": ["SOFTWARE"], "years_experience": [3.0]})
    with pytest.raises(RuntimeError, match="LightGBM quantile regressors have not been fitted"):
        lgb_model._predict_raw_quantiles(dummy_df)

    cb_model = CatBoostQuantileModel()
    with pytest.raises(RuntimeError, match="CatBoost MultiQuantile regressor has not been fitted"):
        cb_model._predict_raw_quantiles(dummy_df)
