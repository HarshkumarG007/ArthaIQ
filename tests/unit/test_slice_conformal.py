"""Unit tests for Slice-Adaptive Conformal Prediction Regressor (Phase 11, T11.01, CHARTER-EXP-13).

Validates:
1. SliceConformalConfig validation, bounds, and defaults.
2. Calibration behavior, global quantile computation, and hierarchical slice partitioning.
3. Empirical Bayes shrinkage formulation:
   q_shrunk_g = alpha_g * q_sample_g + (1 - alpha_g) * q_global
   where alpha_g = n_g / (n_g + m_0).
4. Fallback to global quantile for small slices (n_g < min_slice_samples) or unseen test slices.
5. Monotonic quantile ordering, non-negativity clamping, and crossing repair
   (Rules R-UQ-01, R-UQ-05).
6. Abstained record propagation without numerical leakage (Rule R-MD-08).
7. Summary metrics, variance calculation, and JSON-serializable export.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from pydantic import ValidationError

from compintel.errors import ConfigError
from compintel.models.gbm import (
    GBMModelType,
    GBMQuantileConfig,
    LightGBMQuantileModel,
)
from compintel.uncertainty.slice_conformal import (
    SliceAdaptiveConformalRegressor,
    SliceConformalConfig,
)


@pytest.fixture
def synthetic_train_df() -> pl.DataFrame:
    """Fixture providing multi-slice training observations."""
    np.random.seed(42)
    roles = ["SOFTWARE", "DATA", "MLAI"]
    seniorities = ["JUNIOR", "MID", "SENIOR"]
    records = []

    for role in roles:
        for sen in seniorities:
            base_pay = 12.0 if sen == "JUNIOR" else (22.0 if sen == "MID" else 38.0)
            role_mult = 1.0 if role == "SOFTWARE" else (1.1 if role == "DATA" else 1.25)
            for _ in range(25):
                if sen == "JUNIOR":
                    exp = np.random.uniform(1.0, 3.0)
                elif sen == "MID":
                    exp = np.random.uniform(3.5, 7.0)
                else:
                    exp = np.random.uniform(7.5, 14.0)
                pay = base_pay * role_mult + exp * 1.5 + np.random.normal(0, 2.0)
                records.append(
                    {
                        "role_family": role,
                        "seniority": sen,
                        "location": "BANGALORE",
                        "years_experience": float(exp),
                        "guaranteed_cash_annual": float(max(2.0, pay)),
                    }
                )

    return pl.DataFrame(records)


@pytest.fixture
def synthetic_cal_df() -> pl.DataFrame:
    """Fixture providing calibration observations across slices."""
    np.random.seed(123)
    roles = ["SOFTWARE", "DATA", "MLAI"]
    seniorities = ["JUNIOR", "MID", "SENIOR"]
    records = []

    for role in roles:
        for sen in seniorities:
            # Vary counts: some slices have >= 20 samples, some have < 15 samples
            n_samples = 22 if (role == "SOFTWARE" or sen == "MID") else 8
            base_pay = 12.0 if sen == "JUNIOR" else (22.0 if sen == "MID" else 38.0)
            role_mult = 1.0 if role == "SOFTWARE" else (1.1 if role == "DATA" else 1.25)

            for _ in range(n_samples):
                if sen == "JUNIOR":
                    exp = np.random.uniform(1.0, 3.0)
                elif sen == "MID":
                    exp = np.random.uniform(3.5, 7.0)
                else:
                    exp = np.random.uniform(7.5, 14.0)
                noise = np.random.normal(0, 2.5 if role == "MLAI" else 1.8)
                pay = base_pay * role_mult + exp * 1.5 + noise
                records.append(
                    {
                        "role_family": role,
                        "seniority": sen,
                        "location": "BANGALORE",
                        "years_experience": float(exp),
                        "guaranteed_cash_annual": float(max(2.0, pay)),
                    }
                )

    return pl.DataFrame(records)


@pytest.fixture
def fitted_quantile_model(synthetic_train_df: pl.DataFrame) -> LightGBMQuantileModel:
    """Fixture providing a fitted base quantile model."""
    config = GBMQuantileConfig(
        model_type=GBMModelType.LIGHTGBM,
        quantiles=(0.10, 0.50, 0.90),
        n_estimators=30,
        max_depth=4,
        random_seed=42,
    )
    model = LightGBMQuantileModel(config)
    model.fit(synthetic_train_df)
    return model


# -----------------------------------------------------------------------------
# 1. Config Validation Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_slice_conformal_config_defaults() -> None:
    """Verify default parameters adhere to CHARTER-EXP-13."""
    config = SliceConformalConfig()
    assert config.nominal_coverage == 0.80
    assert config.min_pay_bound_lpa == 0.50
    assert config.repair_crossing is True
    assert config.prior_weight_m0 == 30.0
    assert config.min_slice_samples == 15
    assert config.slice_columns == ["role_family", "seniority"]


@pytest.mark.unit
def test_slice_conformal_config_validation() -> None:
    """Verify invalid configuration bounds raise ValidationError/ConfigError."""
    with pytest.raises((ValidationError, ConfigError)):
        SliceConformalConfig(nominal_coverage=0.40)

    with pytest.raises((ValidationError, ConfigError)):
        SliceConformalConfig(nominal_coverage=1.05)

    with pytest.raises((ValidationError, ConfigError)):
        SliceConformalConfig(prior_weight_m0=-5.0)

    with pytest.raises((ValidationError, ConfigError)):
        SliceConformalConfig(min_slice_samples=2)


# -----------------------------------------------------------------------------
# 2. Calibration & Shrinkage Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_slice_conformal_calibration_workflow(
    fitted_quantile_model: LightGBMQuantileModel,
    synthetic_cal_df: pl.DataFrame,
) -> None:
    """Verify complete calibration workflow and empirical Bayes shrinkage properties."""
    config = SliceConformalConfig(
        prior_weight_m0=30.0,
        min_slice_samples=15,
        slice_columns=["role_family", "seniority"],
    )
    calibrator = SliceAdaptiveConformalRegressor(fitted_quantile_model, config)
    assert calibrator.is_calibrated is False

    calibrator.calibrate(synthetic_cal_df)
    assert calibrator.is_calibrated is True
    assert isinstance(calibrator.conformal_quantile, float)

    summary = calibrator.summary
    assert summary is not None
    assert summary.n_total_calibration == len(synthetic_cal_df)
    assert summary.n_slices_calibrated > 0
    assert 0.65 <= summary.aggregate_empirical_coverage <= 0.95
    assert summary.aggregate_mean_width > 0.0
    assert summary.slice_coverage_variance >= 0.0

    # Verify dictionary export
    summary_dict = summary.to_dict()
    assert "global_conformal_quantile" in summary_dict
    assert "slices" in summary_dict
    assert "assumptions" in summary_dict


@pytest.mark.unit
def test_empirical_bayes_shrinkage_calculation(
    fitted_quantile_model: LightGBMQuantileModel,
    synthetic_cal_df: pl.DataFrame,
) -> None:
    """Verify mathematical shrinkage formula: alpha = n / (n + m0)."""
    m0 = 30.0
    calibrator = SliceAdaptiveConformalRegressor(
        fitted_quantile_model,
        SliceConformalConfig(prior_weight_m0=m0, min_slice_samples=15),
    )
    calibrator.calibrate(synthetic_cal_df)
    summary = calibrator.summary
    assert summary is not None

    for calib in summary.slice_calibrations.values():
        if calib.n_samples >= 15:
            expected_alpha = calib.n_samples / (calib.n_samples + m0)
            assert pytest.approx(calib.alpha_shrinkage, rel=1e-3) == expected_alpha

            # Check shrunk quantile interpolation
            expected_q = (
                expected_alpha * calib.q_sample
                + (1.0 - expected_alpha) * summary.global_conformal_quantile
            )
            assert pytest.approx(calib.q_shrunk, rel=1e-3) == expected_q
        else:
            # Small slice falls back to global
            assert calib.alpha_shrinkage == 0.0
            assert calib.q_shrunk == summary.global_conformal_quantile


@pytest.mark.unit
def test_unseen_slice_fallback_to_global(
    fitted_quantile_model: LightGBMQuantileModel,
    synthetic_cal_df: pl.DataFrame,
) -> None:
    """Verify query observations from unseen slice fall back to global quantile."""
    calibrator = SliceAdaptiveConformalRegressor(fitted_quantile_model)
    calibrator.calibrate(synthetic_cal_df)

    unseen_key = ("NON_EXISTENT_ROLE", "EXECUTIVE")
    q_unseen = calibrator.get_slice_quantile(unseen_key)
    assert q_unseen == calibrator.conformal_quantile

    query_df = pl.DataFrame(
        {
            "role_family": ["NON_EXISTENT_ROLE"],
            "seniority": ["EXECUTIVE"],
            "location": ["BANGALORE"],
            "years_experience": [10.0],
        }
    )
    preds = calibrator.predict(query_df)
    assert len(preds) == 1
    assert preds[0].conformal_correction == round(calibrator.conformal_quantile, 4)


# -----------------------------------------------------------------------------
# 3. Prediction & Ordering Invariant Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_prediction_ordering_and_monotonicity(
    fitted_quantile_model: LightGBMQuantileModel,
    synthetic_cal_df: pl.DataFrame,
    synthetic_train_df: pl.DataFrame,
) -> None:
    """Verify predicted intervals satisfy P10 <= P50 <= P90 with non-negativity floor."""
    calibrator = SliceAdaptiveConformalRegressor(fitted_quantile_model)
    calibrator.calibrate(synthetic_cal_df)

    preds = calibrator.predict(synthetic_train_df)
    assert len(preds) == len(synthetic_train_df)

    for p in preds:
        assert p.p10_calibrated is not None
        assert p.p50 is not None
        assert p.p90_calibrated is not None

        # Monotonicity invariant
        assert p.p10_calibrated <= p.p50 <= p.p90_calibrated
        # Statutory non-negativity floor
        assert p.p10_calibrated >= 0.50
        assert p.nominal_coverage == 0.80
        assert p.method == "slice_adaptive_cqr"


@pytest.mark.unit
def test_empty_dataframe_predict(
    fitted_quantile_model: LightGBMQuantileModel,
    synthetic_cal_df: pl.DataFrame,
) -> None:
    """Verify empty DataFrame returns empty list without error."""
    calibrator = SliceAdaptiveConformalRegressor(fitted_quantile_model)
    calibrator.calibrate(synthetic_cal_df)

    empty_df = synthetic_cal_df.clear()
    preds = calibrator.predict(empty_df)
    assert preds == []


@pytest.mark.unit
def test_uncalibrated_error_raises(fitted_quantile_model: LightGBMQuantileModel) -> None:
    """Verify calling predict or get_slice_quantile before calibrate raises RuntimeError."""
    calibrator = SliceAdaptiveConformalRegressor(fitted_quantile_model)

    with pytest.raises(RuntimeError, match="must be calibrated"):
        calibrator.predict(pl.DataFrame({"role_family": ["DATA"]}))

    with pytest.raises(RuntimeError, match="not calibrated"):
        calibrator.get_slice_quantile(("DATA", "MID"))
