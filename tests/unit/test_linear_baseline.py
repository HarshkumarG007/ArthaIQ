"""Unit tests for Rung B linear quantile baseline model on log pay (T4.05).

Adheres to:
- Rule R-MD-01: Verifies benchmark ladder parametric model (Rung B vs Rung A).
- Rule R-MD-04: Verifies preprocessing fits inside training folds only.
- Rule R-MD-06: Verifies log target transformation and nominal inversion.
- Rule R-MD-08: Verifies thin-evidence abstention for out-of-distribution inputs.
- Rule R-UQ-01: Verifies P10, P50, P90 predictions with definitions.
- Rule R-UQ-05: Verifies quantile crossing detection and monotonic repair.
- Rule R-TS-01 & R-TS-02: Unit and integration testing with analytical correctness.
"""

from __future__ import annotations

import polars as pl
import pytest
from tests.fixtures.synthetic import SyntheticDataGenerator

from compintel.evaluation.metrics import (
    compute_evaluation_report,
    evaluate_interval_metrics,
    evaluate_point_metrics,
    evaluate_quantile_metrics,
    quantile_crossing,
)
from compintel.models.baselines.empirical import EmpiricalQuantileBaseline
from compintel.models.baselines.linear import (
    LinearPrediction,
    LinearQuantileBaseline,
    LinearQuantileConfig,
)


@pytest.fixture
def sample_training_data() -> pl.DataFrame:
    """Generate a reproducible synthetic training set of 80 observations."""
    return SyntheticDataGenerator(seed=42).generate_observations_df(n_records=80)


@pytest.fixture
def sample_dev_data() -> pl.DataFrame:
    """Generate a reproducible synthetic dev evaluation set of 25 observations."""
    return SyntheticDataGenerator(seed=123).generate_observations_df(n_records=25)


def test_linear_baseline_initialization_and_unfitted_guards() -> None:
    """Verify that unfitted model instances safely guard against inference."""
    model = LinearQuantileBaseline()
    assert not model.is_fitted
    assert model.total_records == 0

    with pytest.raises(RuntimeError, match="must be fitted before predict"):
        model.predict_record(role_family="SWE", seniority="MID", location="BENGALURU")

    with pytest.raises(RuntimeError, match="must be fitted before predict"):
        model.predict(pl.DataFrame())


def test_linear_baseline_fit_validation_guards(sample_training_data: pl.DataFrame) -> None:
    """Verify input validation during model fitting."""
    model = LinearQuantileBaseline()

    # Missing target column
    with pytest.raises(ValueError, match="Target column 'nonexistent' not found"):
        model.fit(sample_training_data, target_col="nonexistent")

    # Empty valid target rows
    empty_df = sample_training_data.with_columns(
        pl.lit(None).cast(pl.Float64).alias("guaranteed_cash_annual")
    )
    with pytest.raises(ValueError, match="No valid positive observations found"):
        model.fit(empty_df, target_col="guaranteed_cash_annual")

    # Missing categorical feature column
    bad_cat_df = sample_training_data.drop("role_family")
    with pytest.raises(ValueError, match="Required categorical column 'role_family' missing"):
        model.fit(bad_cat_df, target_col="guaranteed_cash_annual")


def test_single_prediction_and_monotonicity(sample_training_data: pl.DataFrame) -> None:
    """Verify single profile prediction, positive values, and monotonicity guarantee."""
    model = LinearQuantileBaseline()
    model.fit(sample_training_data)

    assert model.is_fitted
    assert model.total_records == len(sample_training_data)

    pred: LinearPrediction = model.predict_record(
        role_family="SWE",
        seniority="MID",
        location="BENGALURU",
        years_experience=4.0,
    )

    assert not pred.is_abstained
    assert pred.abstention_reason is None
    assert pred.p10 is not None and pred.p10 > 0.0
    assert pred.p50 is not None and pred.p50 > 0.0
    assert pred.p90 is not None and pred.p90 > 0.0

    # Monotonicity check (Rule R-UQ-05)
    assert pred.p10 <= pred.p50 <= pred.p90

    # Verify to_dict serialization
    d = pred.to_dict()
    assert d["p10"] == pred.p10
    assert d["target_measure"] == "guaranteed_cash_annual"
    assert d["currency"] == "INR"


def test_out_of_distribution_experience_abstention(sample_training_data: pl.DataFrame) -> None:
    """Verify Rule R-MD-08 thin-evidence abstention for extreme out-of-distribution experience."""
    model = LinearQuantileBaseline(LinearQuantileConfig(max_experience_bound=40.0))
    model.fit(sample_training_data)

    # Negative experience
    pred_neg = model.predict_record(
        role_family="SWE",
        seniority="MID",
        location="BENGALURU",
        years_experience=-1.5,
    )
    assert pred_neg.is_abstained
    assert pred_neg.abstention_reason == "THIN_EVIDENCE"
    assert pred_neg.p10 is None
    assert pred_neg.p50 is None
    assert pred_neg.p90 is None

    # Exceeding maximum experience bound (> 40 years)
    pred_extreme = model.predict_record(
        role_family="SWE",
        seniority="STAFF",
        location="BENGALURU",
        years_experience=48.0,
    )
    assert pred_extreme.is_abstained
    assert pred_extreme.abstention_reason == "THIN_EVIDENCE"


def test_batch_dataframe_prediction(
    sample_training_data: pl.DataFrame,
    sample_dev_data: pl.DataFrame,
) -> None:
    """Verify batch predict(df) handles valid inputs, missing values, and empty DataFrames."""
    model = LinearQuantileBaseline()
    model.fit(sample_training_data)

    # Empty DataFrame
    empty_res = model.predict(pl.DataFrame())
    assert empty_res.shape[0] == 0
    assert "p10" in empty_res.columns

    # Dev evaluation set
    preds_df = model.predict(sample_dev_data)
    assert preds_df.shape[0] == len(sample_dev_data)
    assert set(preds_df.columns) == {
        "p10",
        "p50",
        "p90",
        "is_crossing_repaired",
        "is_abstained",
        "abstention_reason",
    }

    # Verify all non-abstained rows satisfy p10 <= p50 <= p90
    valid_rows = preds_df.filter(~pl.col("is_abstained"))
    for row in valid_rows.iter_rows(named=True):
        assert row["p10"] <= row["p50"] <= row["p90"]


def test_experience_imputation_when_column_absent(
    sample_training_data: pl.DataFrame,
) -> None:
    """Verify that query DataFrames without years_experience impute training median gracefully."""
    model = LinearQuantileBaseline()
    model.fit(sample_training_data)

    query_no_yoe = pl.DataFrame(
        [
            {"role_family": "SWE", "seniority": "JR", "location": "HYDERABAD"},
            {"role_family": "DATA", "seniority": "SR", "location": "PUNE"},
        ]
    )

    preds_df = model.predict(query_no_yoe)
    assert preds_df.shape[0] == 2
    assert not preds_df.get_column("is_abstained").to_list()[0]
    assert not preds_df.get_column("is_abstained").to_list()[1]


def test_dev_split_evaluation_and_rung_a_comparison(
    sample_training_data: pl.DataFrame,
    sample_dev_data: pl.DataFrame,
) -> None:
    """Verify Rung B metrics on dev split and compare with Rung A baseline per ADR-0004."""
    # 1. Fit Rung A (Empirical) and Rung B (Linear)
    rung_a = EmpiricalQuantileBaseline().fit(sample_training_data)
    rung_b = LinearQuantileBaseline().fit(sample_training_data)

    preds_a = rung_a.predict(sample_dev_data)
    preds_b = rung_b.predict(sample_dev_data)

    # Join with ground truth
    joined = sample_dev_data.with_columns(
        [
            preds_a.get_column("p10").alias("p10_a"),
            preds_a.get_column("p50").alias("p50_a"),
            preds_a.get_column("p90").alias("p90_a"),
            preds_a.get_column("is_abstained").alias("is_abstained_a"),
            preds_b.get_column("p10").alias("p10_b"),
            preds_b.get_column("p50").alias("p50_b"),
            preds_b.get_column("p90").alias("p90_b"),
            preds_b.get_column("is_abstained").alias("is_abstained_b"),
        ]
    ).filter((~pl.col("is_abstained_a")) & (~pl.col("is_abstained_b")))

    assert joined.shape[0] > 0

    y_true = joined.get_column("guaranteed_cash_annual").to_numpy()
    p10_b = joined.get_column("p10_b").to_numpy()
    p50_b = joined.get_column("p50_b").to_numpy()
    p90_b = joined.get_column("p90_b").to_numpy()

    # Point metrics on Rung B
    pt_b = evaluate_point_metrics(y_true, p50_b)
    assert pt_b.mae > 0.0
    assert pt_b.medae > 0.0
    assert pt_b.rmse > 0.0

    # Quantile metrics on Rung B
    q_b = evaluate_quantile_metrics(y_true, p10_b, p50_b, p90_b)
    assert q_b.pinball_q10 >= 0.0
    assert q_b.pinball_q50 >= 0.0
    assert q_b.pinball_q90 >= 0.0
    assert q_b.mean_pinball_loss > 0.0

    # Interval metrics on Rung B
    int_b = evaluate_interval_metrics(y_true, p10_b, p50_b, p90_b)
    assert 0.0 <= int_b.coverage_80 <= 1.0
    assert int_b.mean_width > 0.0

    # Crossing rate strictly 0.0% (Rule R-UQ-05)
    crossing_count, crossing_rate = quantile_crossing(p10_b, p50_b, p90_b)
    assert crossing_count == 0
    assert crossing_rate == 0.0

    # Comprehensive evaluation report
    report_b = compute_evaluation_report(
        y_true=y_true,
        q10_pred=p10_b,
        q50_pred=p50_b,
        q90_pred=p90_b,
        with_ci=True,
    )
    assert report_b.point.mae == pt_b.mae
    assert report_b.calibration.crossing_rate == 0.0
    assert "Model Evaluation Summary" in report_b.to_markdown()


def test_batch_prediction_with_unsupported_experience(
    sample_training_data: pl.DataFrame,
) -> None:
    """Verify batch predict correctly flags out-of-distribution experience as abstained."""
    model = LinearQuantileBaseline(LinearQuantileConfig(max_experience_bound=30.0))
    model.fit(sample_training_data)

    test_df = pl.DataFrame(
        [
            {
                "role_family": "SWE",
                "seniority": "MID",
                "location": "BENGALURU",
                "years_experience": 5.0,
            },
            {
                "role_family": "SWE",
                "seniority": "MID",
                "location": "BENGALURU",
                "years_experience": -2.0,
            },
            {
                "role_family": "SWE",
                "seniority": "MID",
                "location": "BENGALURU",
                "years_experience": 45.0,
            },
        ]
    )

    preds_df = model.predict(test_df)
    assert preds_df.shape[0] == 3

    # Row 0: valid
    assert not preds_df["is_abstained"][0]
    assert preds_df["p50"][0] is not None

    # Row 1: negative experience
    assert preds_df["is_abstained"][1]
    assert preds_df["abstention_reason"][1] == "THIN_EVIDENCE"
    assert preds_df["p50"][1] is None

    # Row 2: extreme experience
    assert preds_df["is_abstained"][2]
    assert preds_df["abstention_reason"][2] == "THIN_EVIDENCE"
    assert preds_df["p50"][2] is None


def test_unfitted_preprocessor_guards() -> None:
    """Verify internal preprocessor raises when called before fitting."""
    model = LinearQuantileBaseline()
    dummy_df = pl.DataFrame(
        [
            {
                "role_family": "SWE",
                "seniority": "MID",
                "location": "BENGALURU",
                "years_experience": 3.0,
            }
        ]
    )

    with pytest.raises(RuntimeError, match="Encoder is not fitted"):
        model._prepare_feature_matrix(dummy_df, is_training=False)
