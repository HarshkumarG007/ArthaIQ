"""Unit tests for Rung D gradient boosted point models on log pay.

Adheres to Rules R-MD-04, R-MD-06, R-MD-08, R-TS-01, and R-TS-03.
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl
import pytest

from compintel.models.gbm import (
    CatBoostPointModel,
    GBMModelType,
    GBMPointConfig,
    LightGBMPointModel,
    SearchBudgetPolicy,
    create_gbm_point_model,
    sample_hyperparameters,
    tune_gbm_hyperparameters,
)


@pytest.fixture
def sample_training_df() -> pl.DataFrame:
    """Fixture providing clean training data for boosting models."""
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
    """Fixture providing test data including in-range and out-of-range records."""
    return pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "DATA", "UNKNOWN_ROLE"],
            "seniority": ["MID", "SENIOR", "NEW_LEVEL"],
            "location": ["BANGALORE", "HYDERABAD", "REMOTE"],
            "years_experience": [4.5, -2.0, 48.0],
        }
    )


# ==============================================================================
# 1. Configuration & Budget Tests
# ==============================================================================


@pytest.mark.unit
def test_gbm_point_config_defaults() -> None:
    """Verify default configuration parameters for GBM point models."""
    cfg = GBMPointConfig()
    assert cfg.model_type == GBMModelType.LIGHTGBM
    assert cfg.learning_rate == 0.05
    assert cfg.n_estimators == 100
    assert cfg.log_target is True
    assert cfg.max_experience_bound == 40.0
    assert cfg.search_budget is None


@pytest.mark.unit
def test_search_budget_policy_validation() -> None:
    """Verify SearchBudgetPolicy bounds and constraints."""
    budget = SearchBudgetPolicy(max_evals=5, timeout_seconds=10.0, cv_folds=2, random_seed=99)
    assert budget.max_evals == 5
    assert budget.timeout_seconds == 10.0
    assert budget.cv_folds == 2
    assert budget.random_seed == 99

    with pytest.raises(ValueError):  # max_evals < 1
        SearchBudgetPolicy(max_evals=0)

    with pytest.raises(ValueError):  # timeout <= 0
        SearchBudgetPolicy(timeout_seconds=0.0)


@pytest.mark.unit
def test_sample_hyperparameters() -> None:
    """Verify hyperparameter sampling for LightGBM and CatBoost."""
    rng = np.random.default_rng(123)

    lgb_params = sample_hyperparameters(GBMModelType.LIGHTGBM, rng)
    assert "learning_rate" in lgb_params
    assert "num_leaves" in lgb_params
    assert "reg_lambda" in lgb_params
    assert lgb_params["min_child_samples"] >= 2

    cb_params = sample_hyperparameters(GBMModelType.CATBOOST, rng)
    assert "learning_rate" in cb_params
    assert "iterations" in cb_params
    assert "depth" in cb_params
    assert "l2_leaf_reg" in cb_params


@pytest.mark.unit
def test_tune_gbm_hyperparameters_lightgbm(sample_training_df: pl.DataFrame) -> None:
    """Verify hyperparameter tuning under bounded budget for LightGBM."""
    p_df = sample_training_df.select(
        ["role_family", "seniority", "location", "years_experience"]
    ).to_pandas()
    y = np.log(sample_training_df.get_column("guaranteed_cash_annual").to_numpy())
    budget = SearchBudgetPolicy(max_evals=3, timeout_seconds=10.0, cv_folds=2, random_seed=42)

    result = tune_gbm_hyperparameters(GBMModelType.LIGHTGBM, p_df, y, budget)
    assert result.total_evals >= 1
    assert result.best_score <= 0.0
    assert "learning_rate" in result.best_params
    assert len(result.trials) == result.total_evals


@pytest.mark.unit
def test_tune_gbm_hyperparameters_catboost(sample_training_df: pl.DataFrame) -> None:
    """Verify hyperparameter tuning under bounded budget for CatBoost."""
    p_df = sample_training_df.select(
        ["role_family", "seniority", "location", "years_experience"]
    ).to_pandas()
    y = np.log(sample_training_df.get_column("guaranteed_cash_annual").to_numpy())
    budget = SearchBudgetPolicy(max_evals=2, timeout_seconds=10.0, cv_folds=2, random_seed=42)

    result = tune_gbm_hyperparameters(
        GBMModelType.CATBOOST,
        p_df,
        y,
        budget,
        cat_features=["role_family", "seniority", "location"],
    )
    assert result.total_evals >= 1
    assert result.best_score <= 0.0
    assert "iterations" in result.best_params


# ==============================================================================
# 2. Factory Tests
# ==============================================================================


@pytest.mark.unit
def test_create_gbm_point_model_factory() -> None:
    """Verify create_gbm_point_model factory instantiates correct classes."""
    lgb_model = create_gbm_point_model(GBMPointConfig(model_type=GBMModelType.LIGHTGBM))
    assert isinstance(lgb_model, LightGBMPointModel)
    assert lgb_model.model_name == "LightGBMPointModel"

    cb_model = create_gbm_point_model(GBMPointConfig(model_type=GBMModelType.CATBOOST))
    assert isinstance(cb_model, CatBoostPointModel)
    assert cb_model.model_name == "CatBoostPointModel"

    class MockBadType(str):
        pass

    with pytest.raises(ValueError, match="Unsupported GBM model family"):
        bad_cfg = GBMPointConfig.model_construct(model_type="unsupported_gbm")  # type: ignore[arg-type]
        create_gbm_point_model(bad_cfg)


# ==============================================================================
# 3. LightGBM Point Model Tests
# ==============================================================================


@pytest.mark.unit
def test_lightgbm_point_model_fit_and_predict(
    sample_training_df: pl.DataFrame,
    sample_test_df: pl.DataFrame,
) -> None:
    """Verify end-to-end fitting, log inversion, and abstention in LightGBMPointModel."""
    config = GBMPointConfig(
        model_type=GBMModelType.LIGHTGBM,
        n_estimators=30,
        learning_rate=0.1,
        random_seed=42,
    )
    model = LightGBMPointModel(config)
    assert not model.is_fitted
    assert model.metrics is None

    # Predict before fit raises RuntimeError
    with pytest.raises(RuntimeError, match="must be fitted before predict"):
        model.predict(sample_test_df)

    model.fit(sample_training_df)
    assert model.is_fitted
    assert model.metrics is not None
    assert model.metrics.fit_time_seconds >= 0.0
    assert model.metrics.n_train_samples == len(sample_training_df)
    assert model.metrics.n_features == 4

    predictions = model.predict(sample_test_df)
    assert len(predictions) == 3

    # Row 0: valid in-range observation
    p0 = predictions[0]
    assert not p0.is_abstained
    assert p0.abstention_reason is None
    assert p0.predicted_pay_lpa > 0.0
    assert p0.model_name == "LightGBMPointModel"

    # Row 1: negative experience -> abstains
    p1 = predictions[1]
    assert p1.is_abstained
    assert p1.abstention_reason == "THIN_EVIDENCE"
    assert math.isnan(p1.predicted_pay_lpa)

    # Row 2: experience > 40 -> abstains
    p2 = predictions[2]
    assert p2.is_abstained
    assert p2.abstention_reason == "THIN_EVIDENCE"
    assert math.isnan(p2.predicted_pay_lpa)

    # Test predict_df projection
    pred_df = model.predict_df(sample_test_df)
    assert isinstance(pred_df, pl.DataFrame)
    assert pred_df.shape == (3, 4)
    assert "predicted_pay_lpa" in pred_df.columns
    assert "is_abstained" in pred_df.columns


@pytest.mark.unit
def test_lightgbm_with_search_budget(sample_training_df: pl.DataFrame) -> None:
    """Verify LightGBMPointModel tuning execution during fit."""
    budget = SearchBudgetPolicy(max_evals=2, timeout_seconds=5.0, cv_folds=2)
    config = GBMPointConfig(
        model_type=GBMModelType.LIGHTGBM,
        search_budget=budget,
        random_seed=42,
    )
    model = LightGBMPointModel(config)
    model.fit(sample_training_df)
    assert model.is_fitted
    preds = model.predict(sample_training_df)
    assert len(preds) == len(sample_training_df)
    assert all(not p.is_abstained for p in preds)


# ==============================================================================
# 4. CatBoost Point Model Tests
# ==============================================================================


@pytest.mark.unit
def test_catboost_point_model_fit_and_predict(
    sample_training_df: pl.DataFrame,
    sample_test_df: pl.DataFrame,
) -> None:
    """Verify end-to-end fitting, log inversion, and abstention in CatBoostPointModel."""
    config = GBMPointConfig(
        model_type=GBMModelType.CATBOOST,
        n_estimators=30,
        learning_rate=0.1,
        random_seed=42,
    )
    model = CatBoostPointModel(config)
    assert not model.is_fitted

    with pytest.raises(RuntimeError, match="must be fitted before predict"):
        model.predict(sample_test_df)

    model.fit(sample_training_df)
    assert model.is_fitted
    assert model.metrics is not None
    assert model.metrics.fit_time_seconds >= 0.0
    assert model.metrics.n_train_samples == len(sample_training_df)

    predictions = model.predict(sample_test_df)
    assert len(predictions) == 3

    p0 = predictions[0]
    assert not p0.is_abstained
    assert p0.predicted_pay_lpa > 0.0
    assert p0.model_name == "CatBoostPointModel"

    p1 = predictions[1]
    assert p1.is_abstained
    assert p1.abstention_reason == "THIN_EVIDENCE"
    assert math.isnan(p1.predicted_pay_lpa)

    p2 = predictions[2]
    assert p2.is_abstained
    assert p2.abstention_reason == "THIN_EVIDENCE"
    assert math.isnan(p2.predicted_pay_lpa)

    pred_df = model.predict_df(sample_test_df)
    assert pred_df.shape == (3, 4)


@pytest.mark.unit
def test_catboost_with_search_budget(sample_training_df: pl.DataFrame) -> None:
    """Verify CatBoostPointModel tuning execution during fit."""
    budget = SearchBudgetPolicy(max_evals=2, timeout_seconds=5.0, cv_folds=2)
    config = GBMPointConfig(
        model_type=GBMModelType.CATBOOST,
        search_budget=budget,
        random_seed=42,
    )
    model = CatBoostPointModel(config)
    model.fit(sample_training_df)
    assert model.is_fitted
    preds = model.predict(sample_training_df)
    assert len(preds) == len(sample_training_df)
    assert all(not p.is_abstained for p in preds)


# ==============================================================================
# 5. Validation & Edge Cases Tests
# ==============================================================================


@pytest.mark.unit
def test_gbm_point_model_validation_errors(sample_training_df: pl.DataFrame) -> None:
    """Verify input validation and error raises across GBM point models."""
    model = LightGBMPointModel()

    # Missing target column in training
    no_target_df = sample_training_df.drop("guaranteed_cash_annual")
    with pytest.raises(ValueError, match="Target column 'guaranteed_cash_annual' not found"):
        model.fit(no_target_df)

    # Empty DataFrame in training
    empty_df = sample_training_df.clear()
    with pytest.raises(ValueError, match="Cannot fit model on empty DataFrame"):
        model.fit(empty_df)

    # Non-positive compensation target
    bad_target_df = sample_training_df.with_columns(
        pl.Series("guaranteed_cash_annual", [-5.0, 10.0, 20.0, 30.0, 40.0, 50.0])
    )
    with pytest.raises(ValueError, match="Target compensation must be strictly positive"):
        model.fit(bad_target_df)

    # Missing categorical column
    no_role_df = sample_training_df.drop("role_family")
    with pytest.raises(ValueError, match="Missing required categorical column 'role_family'"):
        model.fit(no_role_df)

    # Missing continuous experience column
    no_yoe_df = sample_training_df.drop("years_experience")
    with pytest.raises(ValueError, match="Missing required continuous column 'years_experience'"):
        model.fit(no_yoe_df)


@pytest.mark.unit
def test_gbm_point_model_empty_and_unseen_prediction(
    sample_training_df: pl.DataFrame,
) -> None:
    """Verify empty predictions and handling of nulls/unseen categories."""
    model = LightGBMPointModel(GBMPointConfig(n_estimators=10))
    model.fit(sample_training_df)

    # Empty prediction DataFrame
    empty_pred_df = sample_training_df.clear()
    preds = model.predict(empty_pred_df)
    assert preds == []
    assert model.predict_df(empty_pred_df).shape == (0, 4)

    # Prediction DataFrame with missing/None experience
    df_with_nulls = pl.DataFrame(
        {
            "role_family": ["SOFTWARE"],
            "seniority": ["MID"],
            "location": ["BANGALORE"],
            "years_experience": [None],
        }
    )
    null_preds = model.predict(df_with_nulls)
    assert len(null_preds) == 1
    assert not null_preds[0].is_abstained
    assert null_preds[0].predicted_pay_lpa > 0.0


@pytest.mark.unit
def test_gbm_point_model_linear_scale_target(sample_training_df: pl.DataFrame) -> None:
    """Verify fitting on linear pay target when log_target=False."""
    config = GBMPointConfig(
        model_type=GBMModelType.LIGHTGBM,
        n_estimators=15,
        log_target=False,
        random_seed=42,
    )
    model = LightGBMPointModel(config)
    model.fit(sample_training_df)
    preds = model.predict(sample_training_df)
    assert len(preds) == len(sample_training_df)
    assert all(p.predicted_pay_lpa > 0.0 for p in preds)


@pytest.mark.unit
def test_gbm_point_model_determinism(sample_training_df: pl.DataFrame) -> None:
    """Verify that models with identical seeds produce bitwise identical predictions."""
    cfg1 = GBMPointConfig(model_type=GBMModelType.LIGHTGBM, random_seed=77, n_estimators=20)
    cfg2 = GBMPointConfig(model_type=GBMModelType.LIGHTGBM, random_seed=77, n_estimators=20)

    m1 = LightGBMPointModel(cfg1).fit(sample_training_df)
    m2 = LightGBMPointModel(cfg2).fit(sample_training_df)

    p1 = m1.predict(sample_training_df)
    p2 = m2.predict(sample_training_df)

    for a, b in zip(p1, p2, strict=True):
        assert a.predicted_pay_lpa == pytest.approx(b.predicted_pay_lpa, rel=1e-6)


@pytest.mark.unit
def test_gbm_unfitted_predict_raw_raises() -> None:
    """Verify that calling _predict_raw directly on unfitted instances raises RuntimeError."""
    lgb_model = LightGBMPointModel()
    with pytest.raises(RuntimeError, match="has not been fitted"):
        lgb_model._predict_raw(None)  # type: ignore[arg-type]

    cb_model = CatBoostPointModel()
    with pytest.raises(RuntimeError, match="has not been fitted"):
        cb_model._predict_raw(None)  # type: ignore[arg-type]


@pytest.mark.unit
def test_tune_gbm_timeout_branch(sample_training_df: pl.DataFrame) -> None:
    """Verify that tuning breaks early when timeout threshold is hit."""
    p_df = sample_training_df.select(
        ["role_family", "seniority", "location", "years_experience"]
    ).to_pandas()
    y = np.log(sample_training_df.get_column("guaranteed_cash_annual").to_numpy())
    budget = SearchBudgetPolicy(max_evals=20, timeout_seconds=0.0001, cv_folds=2)

    result = tune_gbm_hyperparameters(GBMModelType.LIGHTGBM, p_df, y, budget)
    assert result.total_evals <= 20
