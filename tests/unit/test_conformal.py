"""Unit tests for Rung F conformal prediction (CQR and Split Conformal) and calibration.

Adheres to Rules R-MD-01, R-MD-03, R-MD-08, R-UQ-01, R-UQ-03, R-UQ-05, R-TS-01, and R-TS-03.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from compintel.models.gbm import (
    CatBoostPointModel,
    CatBoostQuantileModel,
    GBMModelType,
    GBMPointConfig,
    GBMQuantileConfig,
    LightGBMPointModel,
    LightGBMQuantileModel,
)
from compintel.uncertainty.conformal import (
    ConformalAssumptions,
    ConformalConfig,
    ConformalMethod,
    ConformalQuantileRegressor,
    SplitConformalCalibrator,
    compute_conformal_quantile,
)


@pytest.fixture
def train_df() -> pl.DataFrame:
    """Fixture providing training data."""
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
def cal_df() -> pl.DataFrame:
    """Fixture providing temporal calibration data."""
    return pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "DATA", "SOFTWARE", "MLAI", "DATA"],
            "seniority": ["MID", "JUNIOR", "SENIOR", "MID", "LEAD"],
            "location": ["BANGALORE", "BANGALORE", "HYDERABAD", "PUNE", "BANGALORE"],
            "years_experience": [3.5, 2.0, 7.0, 5.5, 10.0],
            "guaranteed_cash_annual": [17.5, 12.0, 30.0, 24.5, 40.0],
        }
    )


@pytest.fixture
def query_df() -> pl.DataFrame:
    """Fixture providing test observations including in-range, out-of-range, and unseen."""
    return pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "DATA", "UNKNOWN_ROLE"],
            "seniority": ["MID", "SENIOR", "NEW_LEVEL"],
            "location": ["BANGALORE", "HYDERABAD", "REMOTE"],
            "years_experience": [4.5, -2.0, 48.0],
        }
    )


# ==============================================================================
# 1. Configuration & Assumptions Tests
# ==============================================================================


@pytest.mark.unit
def test_conformal_config_defaults_and_validation() -> None:
    """Verify default parameters and boundary validation in ConformalConfig."""
    cfg = ConformalConfig()
    assert cfg.method == ConformalMethod.CQR
    assert cfg.nominal_coverage == 0.80
    assert cfg.min_pay_bound_lpa == 0.50
    assert cfg.repair_crossing is True

    # Valid custom config
    custom_cfg = ConformalConfig(
        method=ConformalMethod.SPLIT_CONFORMAL,
        nominal_coverage=0.90,
        min_pay_bound_lpa=1.0,
    )
    assert custom_cfg.method == ConformalMethod.SPLIT_CONFORMAL
    assert custom_cfg.nominal_coverage == 0.90

    # Coverage outside (0.50, 1.00)
    with pytest.raises(ValueError):
        ConformalConfig(nominal_coverage=0.50)

    with pytest.raises(ValueError):
        ConformalConfig(nominal_coverage=1.00)

    # Negative min pay bound
    with pytest.raises(ValueError):
        ConformalConfig(min_pay_bound_lpa=-0.5)


@pytest.mark.unit
def test_conformal_assumptions_structure() -> None:
    """Verify formal documentation of marginality and exchangeability (Rule R-UQ-03)."""
    assumptions = ConformalAssumptions()
    assert assumptions.is_marginal is True
    assert assumptions.claims_individual_coverage is False
    assert assumptions.requires_exchangeability is True
    assert assumptions.temporal_drift_warning is True
    assert assumptions.calibration_split == "calibrate"
    assert "marginal coverage" in assumptions.description

    d = assumptions.to_dict()
    assert d["is_marginal"] is True
    assert d["claims_individual_coverage"] is False


# ==============================================================================
# 2. Mathematical Non-Conformity & Quantile Calculation Tests
# ==============================================================================


@pytest.mark.unit
def test_compute_conformal_quantile_exact() -> None:
    """Verify finite-sample conformal quantile formula on exact analytical values."""
    # N = 9, alpha = 0.20 (80% coverage)
    # k = ceil((9 + 1) * 0.80) = ceil(8.0) = 8
    scores_9 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    q_val = compute_conformal_quantile(scores_9, alpha=0.20)
    assert q_val == 8.0

    # N = 4, alpha = 0.20
    # k = ceil((4 + 1) * 0.80) = ceil(4.0) = 4
    scores_4 = [10.0, 20.0, 30.0, 40.0]
    assert compute_conformal_quantile(scores_4, alpha=0.20) == 40.0

    # Small sample fallback when k > n:
    # N = 2, alpha = 0.20 -> k = ceil(3 * 0.8) = 3 > 2 -> fallback to max(scores)
    scores_2 = [5.0, 15.0]
    assert compute_conformal_quantile(scores_2, alpha=0.20) == 15.0

    # Empty array raises ValueError
    with pytest.raises(ValueError, match="Cannot compute conformal quantile on empty scores"):
        compute_conformal_quantile([], alpha=0.20)


# ==============================================================================
# 3. Conformalized Quantile Regression (CQR) Lifecycle Tests
# ==============================================================================


@pytest.mark.unit
def test_cqr_lifecycle_with_catboost(
    train_df: pl.DataFrame,
    cal_df: pl.DataFrame,
    query_df: pl.DataFrame,
) -> None:
    """Verify CQR calibration with CatBoostQuantileModel on temporal split."""
    base_model = CatBoostQuantileModel(
        GBMQuantileConfig(
            model_type=GBMModelType.CATBOOST,
            n_estimators=10,
            learning_rate=0.1,
        )
    )
    base_model.fit(train_df)

    cqr = ConformalQuantileRegressor(
        base_model=base_model,
        config=ConformalConfig(nominal_coverage=0.80),
    )
    assert cqr.is_calibrated is False
    assert cqr.summary is None

    # Calibrate on temporal calibration set
    cqr.calibrate(cal_df)
    assert cqr.is_calibrated is True

    summary = cqr.summary
    assert summary is not None
    assert summary.method == "cqr"
    assert summary.nominal_coverage == 0.80
    assert summary.n_calibration_samples == len(cal_df)
    assert summary.empirical_calibration_coverage >= 0.0
    assert summary.assumptions.is_marginal is True
    assert summary.assumptions.requires_exchangeability is True

    # Test summary serialization
    s_dict = summary.to_dict()
    assert s_dict["method"] == "cqr"
    assert "assumptions" in s_dict

    # Predict query profiles
    preds = cqr.predict(query_df)
    assert len(preds) == 3

    # Row 0: valid in-range observation
    p0 = preds[0]
    assert p0.is_abstained is False
    assert p0.p10_calibrated is not None and p0.p50 is not None and p0.p90_calibrated is not None
    # Monotonicity check (Rule R-UQ-05)
    assert p0.p10_calibrated <= p0.p50 <= p0.p90_calibrated
    # Non-negativity check
    assert p0.p10_calibrated >= 0.50
    assert p0.nominal_coverage == 0.80
    assert p0.method == "cqr"

    # Row 1: out-of-range YoE (-2.0) -> Abstention (Rule R-MD-08)
    p1 = preds[1]
    assert p1.is_abstained is True
    assert p1.abstention_reason == "THIN_EVIDENCE"
    assert p1.p10_calibrated is None

    # Row 2: out-of-range YoE (48.0 > max 40.0) -> Abstention
    p2 = preds[2]
    assert p2.is_abstained is True
    assert p2.abstention_reason == "THIN_EVIDENCE"

    # Prediction serialization
    p0_dict = p0.to_dict()
    assert p0_dict["target_measure"] == "guaranteed_cash_annual"
    assert p0_dict["nominal_basis"] is True

    # Polars DataFrame predict
    df_preds = cqr.predict_df(query_df)
    assert isinstance(df_preds, pl.DataFrame)
    assert len(df_preds) == 3
    assert "p10_calibrated" in df_preds.columns
    assert "p90_calibrated" in df_preds.columns
    assert "conformal_correction" in df_preds.columns


@pytest.mark.unit
def test_cqr_lifecycle_with_lightgbm(
    train_df: pl.DataFrame,
    cal_df: pl.DataFrame,
    query_df: pl.DataFrame,
) -> None:
    """Verify CQR calibration with LightGBMQuantileModel on temporal split."""
    base_model = LightGBMQuantileModel(
        GBMQuantileConfig(
            model_type=GBMModelType.LIGHTGBM,
            n_estimators=10,
            learning_rate=0.1,
            min_child_samples=1,
        )
    )
    base_model.fit(train_df)

    cqr = ConformalQuantileRegressor(
        base_model=base_model,
        config=ConformalConfig(nominal_coverage=0.80),
    )
    cqr.calibrate(cal_df)
    assert cqr.is_calibrated is True

    preds = cqr.predict(query_df)
    assert len(preds) == 3
    assert preds[0].p10_calibrated is not None
    assert preds[0].p50 is not None
    assert preds[0].p90_calibrated is not None
    assert preds[0].p10_calibrated <= preds[0].p50 <= preds[0].p90_calibrated


# ==============================================================================
# 4. Split Conformal Calibrator Tests
# ==============================================================================


@pytest.mark.unit
def test_split_conformal_calibrator_lifecycle(
    train_df: pl.DataFrame,
    cal_df: pl.DataFrame,
    query_df: pl.DataFrame,
) -> None:
    """Verify SplitConformalCalibrator with point prediction model."""
    base_point = CatBoostPointModel(
        GBMPointConfig(
            model_type=GBMModelType.CATBOOST,
            n_estimators=10,
            learning_rate=0.1,
        )
    )
    base_point.fit(train_df)

    calibrator = SplitConformalCalibrator(
        base_model=base_point,
        config=ConformalConfig(nominal_coverage=0.80),
    )
    assert calibrator.is_calibrated is False
    assert calibrator.conformal_radius == 0.0

    calibrator.calibrate(cal_df)
    assert calibrator.is_calibrated is True
    assert calibrator.conformal_radius > 0.0

    summary = calibrator.summary
    assert summary is not None
    assert summary.method == "split_conformal"
    assert summary.n_calibration_samples == len(cal_df)

    preds = calibrator.predict(query_df)
    assert len(preds) == 3

    # Row 0: valid prediction
    p0 = preds[0]
    assert p0.is_abstained is False
    assert p0.p10_calibrated is not None and p0.p50 is not None and p0.p90_calibrated is not None
    assert p0.p10_calibrated >= 0.50  # Non-negativity floor
    assert p0.p10_calibrated <= p0.p50 <= p0.p90_calibrated

    # Abstention on out-of-range YoE
    assert preds[1].is_abstained is True
    assert preds[1].abstention_reason == "THIN_EVIDENCE"
    assert preds[2].is_abstained is True

    # DataFrame output
    df_preds = calibrator.predict_df(query_df)
    assert len(df_preds) == 3
    assert "conformal_correction" in df_preds.columns


# ==============================================================================
# 5. Conformal Interval Expansion & Contraction Behavior
# ==============================================================================


@pytest.mark.unit
def test_cqr_expansion_when_base_undercovers(train_df: pl.DataFrame) -> None:
    """Verify that when actual pay falls outside base bounds, CQR expands intervals."""
    base_model = LightGBMQuantileModel(
        GBMQuantileConfig(
            model_type=GBMModelType.LIGHTGBM,
            n_estimators=5,
            min_child_samples=1,
        )
    )
    base_model.fit(train_df)

    # Calibration set with extreme values far outside base predictions
    extreme_cal_df = pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "SOFTWARE", "SOFTWARE", "SOFTWARE", "SOFTWARE"],
            "seniority": ["MID", "MID", "MID", "MID", "MID"],
            "location": ["BANGALORE", "BANGALORE", "BANGALORE", "BANGALORE", "BANGALORE"],
            "years_experience": [4.0, 4.0, 4.0, 4.0, 4.0],
            "guaranteed_cash_annual": [100.0, 110.0, 120.0, 130.0, 140.0],
        }
    )

    cqr = ConformalQuantileRegressor(base_model, ConformalConfig(nominal_coverage=0.80))
    cqr.calibrate(extreme_cal_df)

    # Conformal correction must be positive (expanding the interval)
    assert cqr.conformal_quantile > 0.0

    test_point = pl.DataFrame(
        {
            "role_family": ["SOFTWARE"],
            "seniority": ["MID"],
            "location": ["BANGALORE"],
            "years_experience": [4.0],
        }
    )
    pred = cqr.predict(test_point)[0]
    assert pred.p10_calibrated is not None and pred.p10_uncalibrated is not None
    assert pred.p90_calibrated is not None and pred.p90_uncalibrated is not None
    # Upper bound must be expanded
    assert pred.p90_calibrated > pred.p90_uncalibrated


# ==============================================================================
# 6. Error Handling & Invariant Rejections
# ==============================================================================


@pytest.mark.unit
def test_unfitted_base_models_rejected() -> None:
    """Verify that calibrator initialization fails if base model is not fitted."""
    unfitted_quant = LightGBMQuantileModel()
    with pytest.raises(RuntimeError, match="Base quantile model must be fitted"):
        ConformalQuantileRegressor(unfitted_quant)

    unfitted_point = LightGBMPointModel()
    with pytest.raises(RuntimeError, match="Base point model must be fitted"):
        SplitConformalCalibrator(unfitted_point)


@pytest.mark.unit
def test_uncalibrated_predict_rejected(train_df: pl.DataFrame, query_df: pl.DataFrame) -> None:
    """Verify that calling predict before calibrate raises RuntimeError."""
    base_quant = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))
    base_quant.fit(train_df)
    cqr = ConformalQuantileRegressor(base_quant)
    with pytest.raises(RuntimeError, match="must be calibrated before predict"):
        cqr.predict(query_df)

    base_point = LightGBMPointModel(GBMPointConfig(n_estimators=5, min_child_samples=1))
    base_point.fit(train_df)
    split_cal = SplitConformalCalibrator(base_point)
    with pytest.raises(RuntimeError, match="must be calibrated before predict"):
        split_cal.predict(query_df)


@pytest.mark.unit
def test_empty_dataframe_conformal_handling(train_df: pl.DataFrame, cal_df: pl.DataFrame) -> None:
    """Verify handling of empty DataFrames in calibration and prediction."""
    base_model = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))
    base_model.fit(train_df)
    cqr = ConformalQuantileRegressor(base_model)

    # Empty calibrate df raises ValueError
    empty_df = cal_df.clear()
    with pytest.raises(ValueError, match="Cannot calibrate conformal model on empty DataFrame"):
        cqr.calibrate(empty_df)

    # Empty predict df returns empty results
    cqr.calibrate(cal_df)
    empty_query = pl.DataFrame(
        schema={
            "role_family": pl.String,
            "seniority": pl.String,
            "location": pl.String,
            "years_experience": pl.Float64,
        }
    )
    assert cqr.predict(empty_query) == []
    assert len(cqr.predict_df(empty_query)) == 0


@pytest.mark.unit
def test_missing_target_conformal_rejection(train_df: pl.DataFrame, cal_df: pl.DataFrame) -> None:
    """Verify missing target column in calibration DataFrame is rejected."""
    base_model = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))
    base_model.fit(train_df)
    cqr = ConformalQuantileRegressor(base_model)

    df_no_target = cal_df.drop("guaranteed_cash_annual")
    with pytest.raises(ValueError, match="Target column 'guaranteed_cash_annual' missing"):
        cqr.calibrate(df_no_target)


@pytest.mark.unit
def test_all_abstained_calibration_rejection(train_df: pl.DataFrame) -> None:
    """Verify ValueError is raised if all records in calibration set fail support checks."""
    base_model = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))
    base_model.fit(train_df)
    cqr = ConformalQuantileRegressor(base_model)

    # All records have out-of-range YoE (< 0.0)
    abstained_cal_df = pl.DataFrame(
        {
            "role_family": ["SOFTWARE", "DATA"],
            "seniority": ["MID", "SENIOR"],
            "location": ["BANGALORE", "HYDERABAD"],
            "years_experience": [-5.0, -10.0],
            "guaranteed_cash_annual": [20.0, 30.0],
        }
    )
    with pytest.raises(ValueError, match="All calibration records were abstained"):
        cqr.calibrate(abstained_cal_df)


@pytest.mark.unit
def test_conformal_calibrator_edge_cases_and_coercion(
    train_df: pl.DataFrame, cal_df: pl.DataFrame
) -> None:
    """Verify method coercion, unfitted model rejection, uncalibrated state, and empty handling."""
    # 1. Unfitted model rejection
    unfitted_quant = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5))
    with pytest.raises(RuntimeError, match="Base quantile model must be fitted"):
        ConformalQuantileRegressor(unfitted_quant)

    unfitted_point = CatBoostPointModel(GBMPointConfig(n_estimators=5))
    with pytest.raises(RuntimeError, match="Base point model must be fitted"):
        SplitConformalCalibrator(unfitted_point)

    # 2. Config method auto-coercion
    base_quant = LightGBMQuantileModel(GBMQuantileConfig(n_estimators=5, min_child_samples=1))
    base_quant.fit(train_df)
    cqr_mismatched = ConformalQuantileRegressor(
        base_quant, ConformalConfig(method=ConformalMethod.SPLIT_CONFORMAL)
    )
    assert cqr_mismatched.config.method == ConformalMethod.CQR

    base_point = CatBoostPointModel(GBMPointConfig(n_estimators=5))
    base_point.fit(train_df)
    split_mismatched = SplitConformalCalibrator(
        base_point, ConformalConfig(method=ConformalMethod.CQR)
    )
    assert split_mismatched.config.method == ConformalMethod.SPLIT_CONFORMAL

    # 3. Uncalibrated predictions reject
    with pytest.raises(RuntimeError, match="must be calibrated before predict"):
        cqr_mismatched.predict(train_df)
    with pytest.raises(RuntimeError, match="must be calibrated before predict"):
        split_mismatched.predict(train_df)

    # 4. Empty calibration set rejects
    empty_df = cal_df.head(0)
    with pytest.raises(ValueError, match="Cannot calibrate conformal model on empty DataFrame"):
        cqr_mismatched.calibrate(empty_df)
    with pytest.raises(ValueError, match="Cannot calibrate conformal model on empty DataFrame"):
        split_mismatched.calibrate(empty_df)

    # 5. SplitConformalCalibrator missing target column and all-abstained
    df_no_target = cal_df.drop("guaranteed_cash_annual")
    with pytest.raises(ValueError, match="Target column 'guaranteed_cash_annual' missing"):
        split_mismatched.calibrate(df_no_target)

    abstained_cal_df = pl.DataFrame(
        {
            "role_family": ["SOFTWARE"],
            "seniority": ["MID"],
            "location": ["BANGALORE"],
            "years_experience": [-5.0],
            "guaranteed_cash_annual": [20.0],
        }
    )
    with pytest.raises(ValueError, match="All calibration records were abstained"):
        split_mismatched.calibrate(abstained_cal_df)

    # 6. Calibrated empty DataFrame predict returns empty list and empty DataFrame
    cqr_mismatched.calibrate(cal_df)
    assert cqr_mismatched.predict(empty_df) == []
    assert len(cqr_mismatched.predict_df(empty_df)) == 0

    split_mismatched.calibrate(cal_df)
    assert split_mismatched.predict(empty_df) == []
    assert len(split_mismatched.predict_df(empty_df)) == 0


# ==============================================================================
# 7. Canonical Dataset Conformal Integration Test
# ==============================================================================


@pytest.mark.unit
def test_canonical_dataset_conformal_pipeline() -> None:
    """Verify end-to-end conformal calibration on canonical observations if present."""
    canonical_path = Path("data/canonical/canonical_observations.parquet")
    if not canonical_path.exists():
        pytest.skip("Canonical dataset not present on clean checkout (R-DA-08).")

    df = pl.read_parquet(canonical_path)
    if len(df) < 10:
        pytest.skip("Insufficient records in canonical parquet.")

    # Split into train (60%), calibrate (20%), query (20%)
    n = len(df)
    n_train = int(n * 0.6)
    n_cal = int(n * 0.2)

    tr_df = df.slice(0, n_train)
    c_df = df.slice(n_train, n_cal)
    q_df = df.slice(n_train + n_cal)

    # 1. Base Quantile Model
    base_quant = CatBoostQuantileModel(
        GBMQuantileConfig(
            model_type=GBMModelType.CATBOOST,
            n_estimators=10,
            learning_rate=0.1,
        )
    )
    base_quant.fit(tr_df)

    # 2. CQR Calibrator
    cqr = ConformalQuantileRegressor(base_quant, ConformalConfig(nominal_coverage=0.80))
    cqr.calibrate(c_df)
    assert cqr.is_calibrated is True
    assert cqr.summary is not None
    assert cqr.summary.empirical_calibration_coverage >= 0.0

    preds = cqr.predict(q_df)
    assert len(preds) == len(q_df)
    for p in preds:
        if not p.is_abstained:
            assert p.p10_calibrated is not None
            assert p.p50 is not None
            assert p.p90_calibrated is not None
            assert p.p10_calibrated <= p.p50 <= p.p90_calibrated
            assert p.p10_calibrated >= 0.50
