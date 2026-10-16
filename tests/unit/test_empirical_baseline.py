"""Unit tests for Rung A empirical conditional quantiles with hierarchical backoff (T4.04).

Adheres to:
- Rule R-MD-01: Verifies benchmark ladder foundation model (Rung A).
- Rule R-MD-08: Tests thin evidence abstention.
- Rule R-UQ-01: Verifies P10, P50, P90 quantile predictions with explicit backoff path.
- Rule R-UQ-05: Verifies zero quantile crossing rate (P10 <= P50 <= P90).
- Rule R-TS-01 & R-TS-02: Unit and integration testing with analytical correctness.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
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
from compintel.models.baselines.empirical import (
    EmpiricalPrediction,
    EmpiricalQuantileBaseline,
    HierarchicalBackoffConfig,
    HierarchicalLevel,
)


@pytest.fixture
def hand_crafted_training_data() -> pl.DataFrame:
    """Create a deterministic dataset with known cell distributions for analytical verification."""
    records: list[dict[str, Any]] = []

    # 1. Dense Cell: SWE / MID / BENGALURU (N = 10, pay: 10.0 to 28.0 step 2)
    # Target values: [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0]
    for p in range(10, 30, 2):
        records.append(
            {
                "observation_id": f"obs-dense-{p}",
                "role_family": "SWE",
                "seniority": "MID",
                "location": "BENGALURU",
                "guaranteed_cash_annual": float(p),
            }
        )

    # 2. Sparse Cell: SWE / SR / HYDERABAD (N = 2, pay: 30.0, 32.0)
    records.append(
        {
            "observation_id": "obs-sparse-1",
            "role_family": "SWE",
            "seniority": "SR",
            "location": "HYDERABAD",
            "guaranteed_cash_annual": 30.0,
        }
    )
    records.append(
        {
            "observation_id": "obs-sparse-2",
            "role_family": "SWE",
            "seniority": "SR",
            "location": "HYDERABAD",
            "guaranteed_cash_annual": 32.0,
        }
    )

    # 3. Sibling records in SWE / SR / BENGALURU (N = 4)
    # Total SWE / SR count = 2 + 4 = 6 >= 5 (so role_seniority level resolves)
    for p in [34.0, 36.0, 38.0, 40.0]:
        records.append(
            {
                "observation_id": f"obs-sr-blr-{int(p)}",
                "role_family": "SWE",
                "seniority": "SR",
                "location": "BENGALURU",
                "guaranteed_cash_annual": p,
            }
        )

    # 4. DATA / JR records (N = 6 across different locations)
    # Total DATA count = 6 >= 5
    for i, loc in enumerate(["PUNE", "MUMBAI", "CHENNAI", "NCR", "HYDERABAD", "BENGALURU"]):
        records.append(
            {
                "observation_id": f"obs-data-{i}",
                "role_family": "DATA",
                "seniority": "JR",
                "location": loc,
                "guaranteed_cash_annual": 12.0 + i,
            }
        )

    return pl.DataFrame(records)


def test_model_initialization_and_unfitted_guards() -> None:
    """Verify that unfitted model instances safely guard against inference and summary calls."""
    model = EmpiricalQuantileBaseline()
    assert not model.is_fitted
    assert model.total_records == 0

    with pytest.raises(RuntimeError, match="must be fitted before predict"):
        model.predict_record(role_family="SWE", seniority="MID", location="BENGALURU")

    with pytest.raises(RuntimeError, match="must be fitted to get cell summary"):
        model.get_cell_summary()


def test_fit_validation_guards(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify input validation during model fitting."""
    model = EmpiricalQuantileBaseline()

    # Missing target column
    with pytest.raises(ValueError, match="Target column 'nonexistent' not found"):
        model.fit(hand_crafted_training_data, target_col="nonexistent")

    # Empty valid target rows
    empty_df = hand_crafted_training_data.with_columns(
        pl.lit(None).cast(pl.Float64).alias("guaranteed_cash_annual")
    )
    with pytest.raises(ValueError, match="No valid positive observations found"):
        model.fit(empty_df, target_col="guaranteed_cash_annual")


def test_analytical_quantiles_dense_cell(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify analytical correctness of quantiles and backoff path for a dense cell (Level 0)."""
    model = EmpiricalQuantileBaseline()
    model.fit(hand_crafted_training_data)

    pred: EmpiricalPrediction = model.predict_record(
        role_family="SWE", seniority="MID", location="BENGALURU"
    )

    assert not pred.is_abstained
    assert pred.abstention_reason is None
    assert pred.resolved_level == "cell"
    assert pred.sample_size == 10
    assert not pred.backoff_path.is_fallback
    assert pred.backoff_path.backoff_count == 0

    # Values: 10, 12, 14, 16, 18, 20, 22, 24, 26, 28
    # Median (p50) of 10 values is (18 + 20) / 2 = 19.0
    expected_p50 = float(
        np.quantile(np.array([10, 12, 14, 16, 18, 20, 22, 24, 26, 28], dtype=float), 0.50)
    )
    expected_p10 = float(
        np.quantile(np.array([10, 12, 14, 16, 18, 20, 22, 24, 26, 28], dtype=float), 0.10)
    )
    expected_p90 = float(
        np.quantile(np.array([10, 12, 14, 16, 18, 20, 22, 24, 26, 28], dtype=float), 0.90)
    )

    assert pred.p50 == pytest.approx(expected_p50)
    assert pred.p10 == pytest.approx(expected_p10)
    assert pred.p90 == pytest.approx(expected_p90)
    assert pred.p10 <= pred.p50 <= pred.p90


def test_hierarchical_backoff_sparse_cell(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify backoff from sparse Level 0 cell (N = 2) to Level 1 role_seniority (N = 6)."""
    model = EmpiricalQuantileBaseline()
    model.fit(hand_crafted_training_data)

    # Query: SWE / SR / HYDERABAD (cell N = 2 < 5; SWE / SR has N = 6 >= 5)
    pred: EmpiricalPrediction = model.predict_record(
        role_family="SWE", seniority="SR", location="HYDERABAD"
    )

    assert not pred.is_abstained
    assert pred.resolved_level == "role_seniority"
    assert pred.sample_size == 6
    assert pred.backoff_path.is_fallback
    assert pred.backoff_path.backoff_count == 1  # 1 hop: cell (sparse) -> role_seniority

    steps = pred.backoff_path.steps
    assert len(steps) == 2
    # Step 0: cell level
    assert steps[0].level_name == "cell"
    assert steps[0].sample_size == 2
    assert not steps[0].is_sufficient
    assert steps[0].quantiles is None

    # Step 1: role_seniority level
    assert steps[1].level_name == "role_seniority"
    assert steps[1].sample_size == 6
    assert steps[1].is_sufficient
    assert steps[1].quantiles is not None


def test_backoff_to_role_location_and_family(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify traversal when both cell and role_seniority are unseen or sparse."""
    model = EmpiricalQuantileBaseline()
    model.fit(hand_crafted_training_data)

    # Query: DATA / MID / PUNE
    # In training data: DATA / MID is 0 records; DATA / PUNE has 1 record; DATA has 6 records.
    # Level 0 (cell) -> N=0 (skip)
    # Level 1 (role_seniority) -> N=0 (skip)
    # Level 2 (role_location) -> N=1 < 5 (insufficient)
    # Level 3 (role_family) -> N=6 >= 5 (sufficient!)
    pred = model.predict_record(role_family="DATA", seniority="MID", location="PUNE")

    assert not pred.is_abstained
    assert pred.resolved_level == "role_family"
    assert pred.sample_size == 6
    assert pred.backoff_path.is_fallback
    assert pred.backoff_path.backoff_count == 3


def test_backoff_to_global_market(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify fallback to global market pool when role family is sparse."""
    # Custom config where thin_evidence_threshold is satisfied by global
    config = HierarchicalBackoffConfig(
        levels=[
            HierarchicalLevel("cell", ["role_family", "seniority", "location"], 5),
            HierarchicalLevel("role_family", ["role_family"], 5),
            HierarchicalLevel("global", [], 10),
        ]
    )
    model = EmpiricalQuantileBaseline(config)
    model.fit(hand_crafted_training_data)

    # Query an unseen role family: MLAI
    pred = model.predict_record(role_family="MLAI", seniority="SR", location="BENGALURU")

    assert not pred.is_abstained
    assert pred.resolved_level == "global"
    assert pred.sample_size == 22  # Total hand-crafted dataset size
    assert pred.backoff_path.is_fallback


def test_thin_evidence_abstention(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify Rule R-MD-08 abstention with reason code THIN_EVIDENCE when evidence is low."""
    # Config with high minimum threshold that global cannot satisfy
    config = HierarchicalBackoffConfig(
        levels=[
            HierarchicalLevel("cell", ["role_family", "seniority", "location"], 50),
            HierarchicalLevel("global", [], 100),
        ],
        thin_evidence_threshold=100,
    )
    model = EmpiricalQuantileBaseline(config)
    model.fit(hand_crafted_training_data)

    pred = model.predict_record(role_family="SWE", seniority="MID", location="BENGALURU")

    assert pred.is_abstained
    assert pred.abstention_reason == "THIN_EVIDENCE"
    assert pred.p10 is None
    assert pred.p50 is None
    assert pred.p90 is None
    assert pred.resolved_level is None
    assert pred.backoff_path.is_fallback


def test_batch_dataframe_prediction_and_json_audit(
    hand_crafted_training_data: pl.DataFrame,
) -> None:
    """Verify batch predict(df) outputs correct schema and valid serialized JSON audit paths."""
    model = EmpiricalQuantileBaseline()
    model.fit(hand_crafted_training_data)

    query_df = pl.DataFrame(
        [
            {"role_family": "SWE", "seniority": "MID", "location": "BENGALURU"},  # Dense cell
            {"role_family": "SWE", "seniority": "SR", "location": "HYDERABAD"},  # Sparse cell
            {"role_family": "OTHER", "seniority": "OTHER", "location": "OTHER"},  # Global fallback
        ]
    )

    preds_df = model.predict(query_df)

    assert preds_df.shape[0] == 3
    assert set(preds_df.columns) == {
        "p10",
        "p50",
        "p90",
        "sample_size",
        "resolved_level",
        "backoff_count",
        "is_fallback",
        "is_abstained",
        "abstention_reason",
        "backoff_path_json",
    }

    # Verify JSON path serialization
    for row in preds_df.iter_rows(named=True):
        raw_json = row["backoff_path_json"]
        assert isinstance(raw_json, str)
        parsed = json.loads(raw_json)
        assert "steps" in parsed
        assert "resolved_level" in parsed
        assert "backoff_count" in parsed
        assert "is_fallback" in parsed


def test_cell_summary_diagnostics(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify get_cell_summary() returns formatted diagnostic view of fitted hierarchy."""
    model = EmpiricalQuantileBaseline()
    model.fit(hand_crafted_training_data)

    summary_df = model.get_cell_summary()
    assert summary_df.shape[0] > 0
    assert "level_name" in summary_df.columns
    assert "key" in summary_df.columns
    assert "sample_size" in summary_df.columns
    assert "p10" in summary_df.columns
    assert "p50" in summary_df.columns
    assert "p90" in summary_df.columns

    # Verify global entry exists
    global_rows = summary_df.filter(pl.col("level_name") == "global")
    assert global_rows.shape[0] == 1
    assert global_rows.get_column("sample_size")[0] == len(hand_crafted_training_data)


def test_integration_with_synthetic_data_and_evaluation_metrics() -> None:
    """Verify Rung A on synthetic dataset evaluates cleanly through evaluation metrics module."""
    # Generate realistic synthetic dataset (100 rows)
    train_df = SyntheticDataGenerator(seed=42).generate_observations_df(n_records=80)
    dev_df = SyntheticDataGenerator(seed=123).generate_observations_df(n_records=20)

    model = EmpiricalQuantileBaseline()
    model.fit(train_df)

    preds_df = model.predict(dev_df)
    assert preds_df.shape[0] == 20

    # Filter to non-abstained predictions for metric computation
    joined = dev_df.with_columns(
        [
            preds_df.get_column("p10"),
            preds_df.get_column("p50"),
            preds_df.get_column("p90"),
            preds_df.get_column("is_abstained"),
        ]
    ).filter(~pl.col("is_abstained"))

    assert joined.shape[0] > 0

    y_true = joined.get_column("guaranteed_cash_annual").to_numpy()
    p10 = joined.get_column("p10").to_numpy()
    p50 = joined.get_column("p50").to_numpy()
    p90 = joined.get_column("p90").to_numpy()

    # 1. Point metrics
    pt_metrics = evaluate_point_metrics(y_true, p50)
    assert pt_metrics.mae > 0.0
    assert pt_metrics.medae > 0.0
    assert pt_metrics.rmse > 0.0

    # 2. Quantile metrics (pinball loss)
    q_metrics = evaluate_quantile_metrics(y_true, p10, p50, p90)
    assert q_metrics.pinball_q10 >= 0.0
    assert q_metrics.pinball_q50 >= 0.0
    assert q_metrics.pinball_q90 >= 0.0

    # 3. Interval metrics (coverage and width)
    int_metrics = evaluate_interval_metrics(y_true, p10, p50, p90)
    assert 0.0 <= int_metrics.coverage_80 <= 1.0
    assert int_metrics.mean_width > 0.0

    # 4. Zero quantile crossing guarantee (Rule R-UQ-05)
    crossing_count, crossing_rate = quantile_crossing(p10, p50, p90)
    assert crossing_count == 0
    assert crossing_rate == 0.0

    # 5. Full evaluation report generation
    report = compute_evaluation_report(
        y_true=y_true,
        q10_pred=p10,
        q50_pred=p50,
        q90_pred=p90,
        with_ci=True,
    )
    assert report.point.mae == pt_metrics.mae
    assert report.calibration.crossing_rate == 0.0
    assert "Model Evaluation Summary" in report.to_markdown()


def test_empirical_prediction_to_dict(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify serialization of EmpiricalPrediction to dict."""
    model = EmpiricalQuantileBaseline()
    model.fit(hand_crafted_training_data)

    pred = model.predict_record(role_family="SWE", seniority="MID", location="BENGALURU")
    d = pred.to_dict()
    assert d["p10"] == pred.p10
    assert d["p50"] == pred.p50
    assert d["p90"] == pred.p90
    assert d["sample_size"] == 10
    assert d["resolved_level"] == "cell"
    assert not d["is_abstained"]
    assert d["target_measure"] == "guaranteed_cash_annual"
    assert d["currency"] == "INR"


def test_missing_columns_in_hierarchical_level(hand_crafted_training_data: pl.DataFrame) -> None:
    """Verify that hierarchical levels with missing DataFrame columns are skipped gracefully."""
    config = HierarchicalBackoffConfig(
        levels=[
            HierarchicalLevel("custom_cell", ["role_family", "nonexistent_col"], 5),
            HierarchicalLevel("role_family", ["role_family"], 5),
            HierarchicalLevel("global", [], 5),
        ]
    )
    model = EmpiricalQuantileBaseline(config)
    model.fit(hand_crafted_training_data)

    # custom_cell was skipped because nonexistent_col is absent in training df
    # prediction should resolve to role_family
    pred = model.predict_record(role_family="SWE", seniority="MID", location="BENGALURU")
    assert not pred.is_abstained
    assert pred.resolved_level == "role_family"
