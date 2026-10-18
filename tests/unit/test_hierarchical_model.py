"""Unit tests for Rung C hierarchical partial pooling model (Phase 6, T6.02a).

Validates:
- HierarchicalConfig validation and serialization.
- Fitting on structured multi-level datasets.
- Empirical Bayes shrinkage behavior (sparse cells shrink to parent, dense cells retain specifics).
- Employer cluster anonymization floor k_min >= 5 (Rule R-DA-10).
- Monotone quantile predictions P10 <= P50 <= P90 (Rule R-UQ-05).
- Thin evidence abstention on out-of-distribution experience (Rule R-MD-08).
- Batch prediction via Polars DataFrame.
- Exact bitwise model serialization (to_dict / from_dict).
- Test coverage >= 90.0% (Rule R-TS-03).
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from compintel.models.hierarchical import (
    GroupNode,
    HierarchicalConfig,
    HierarchicalCrossingDiagnostics,
    HierarchicalPartialPoolingModel,
    HierarchicalPrediction,
)


@pytest.fixture
def synthetic_hierarchy_df() -> pl.DataFrame:
    """Generate synthetic training dataset with nested role, seniority, location, and firms."""
    rng = np.random.default_rng(42)
    n_samples = 400

    roles = ["SWE", "DATA", "MLAI"]
    seniorities = ["ENTRY", "MID", "SR", "LEAD"]
    locations = ["BENGALURU", "HYDERABAD", "NCR", "PUNE"]
    tiers = ["TIER_1_PRODUCT", "GCC", "IT_SERVICES"]

    role_list: list[str] = []
    sen_list: list[str] = []
    loc_list: list[str] = []
    tier_list: list[str] = []
    emp_list: list[str] = []
    yoe_list: list[float] = []
    cash_list: list[float] = []

    for i in range(n_samples):
        role = str(rng.choice(roles))
        sen = str(rng.choice(seniorities))
        loc = str(rng.choice(locations))
        tier = str(rng.choice(tiers))

        # Create both dense employers (EMP_DENSE_1, EMP_DENSE_2) and sparse employers (EMP_SPARSE_*)
        if i < 300:
            emp = "EMP_DENSE_1" if i % 2 == 0 else "EMP_DENSE_2"
        else:
            emp = f"EMP_SPARSE_{i % 50}"

        if sen == "ENTRY":
            yoe = float(rng.uniform(0.5, 2.0))
            base_cash = 10.0
        elif sen == "MID":
            yoe = float(rng.uniform(2.5, 5.0))
            base_cash = 18.0
        elif sen == "SR":
            yoe = float(rng.uniform(5.5, 9.0))
            base_cash = 30.0
        else:
            yoe = float(rng.uniform(9.5, 14.0))
            base_cash = 45.0

        # Role premium
        if role == "MLAI":
            base_cash *= 1.25
        elif role == "DATA":
            base_cash *= 1.10

        # Tier premium
        if tier == "TIER_1_PRODUCT":
            base_cash *= 1.35
        elif tier == "IT_SERVICES":
            base_cash *= 0.70

        # Location premium
        if loc == "BENGALURU":
            base_cash *= 1.15

        # Add log-normal noise
        noise = float(rng.lognormal(mean=0.0, sigma=0.15))
        final_cash = max(float(base_cash * noise), 1.0)

        role_list.append(role)
        sen_list.append(sen)
        loc_list.append(loc)
        tier_list.append(tier)
        emp_list.append(emp)
        yoe_list.append(yoe)
        cash_list.append(final_cash)

    # Add 2 intentional sparse cell outliers: role=SWE, sen=MID, loc=PUNE with 1 observation
    role_list.append("SWE")
    sen_list.append("MID")
    loc_list.append("PUNE")
    tier_list.append("IT_SERVICES")
    emp_list.append("EMP_SPARSE_SINGLETON")
    yoe_list.append(3.0)
    cash_list.append(85.0)  # extreme outlier in sparse cell

    return pl.DataFrame(
        {
            "guaranteed_cash_annual": pl.Series(cash_list, dtype=pl.Float64),
            "years_experience": pl.Series(yoe_list, dtype=pl.Float64),
            "role_family": pl.Series(role_list, dtype=pl.String),
            "seniority": pl.Series(sen_list, dtype=pl.String),
            "location": pl.Series(loc_list, dtype=pl.String),
            "employer_tier": pl.Series(tier_list, dtype=pl.String),
            "employer_cluster_id": pl.Series(emp_list, dtype=pl.String),
        }
    )


@pytest.mark.unit
def test_hierarchical_config_validation() -> None:
    """Verify HierarchicalConfig validates parameter ranges and types."""
    cfg = HierarchicalConfig()
    assert cfg.min_cell_sample_size == 5
    assert cfg.global_thin_evidence_threshold == 5
    assert cfg.quantiles == [0.10, 0.50, 0.90]

    d = cfg.to_dict()
    assert isinstance(d, dict)
    assert d["k_min_employer"] == 5

    # Invalid min_cell_sample_size
    with pytest.raises(ValueError, match="min_cell_sample_size"):
        HierarchicalConfig(min_cell_sample_size=0)

    # Invalid global_thin_evidence_threshold
    with pytest.raises(ValueError, match="global_thin_evidence_threshold"):
        HierarchicalConfig(global_thin_evidence_threshold=0)

    # Invalid max_experience_bound
    with pytest.raises(ValueError, match="max_experience_bound"):
        HierarchicalConfig(max_experience_bound=-1.0)

    # Invalid quantiles
    with pytest.raises(ValueError, match="quantiles"):
        HierarchicalConfig(quantiles=[])
    with pytest.raises(ValueError, match="quantiles"):
        HierarchicalConfig(quantiles=[0.90, 0.10])  # unsorted

    # Invalid polynomial degree
    with pytest.raises(ValueError, match="experience_polynomial_degree"):
        HierarchicalConfig(experience_polynomial_degree=3)


@pytest.mark.unit
def test_prediction_and_diagnostics_dataclasses() -> None:
    """Verify serialization of prediction and crossing diagnostics dataclasses."""
    pred = HierarchicalPrediction(
        p10=12.0,
        p50=18.0,
        p90=26.0,
        point_estimate=18.0,
        log_mean=2.89,
        log_std=0.25,
        shrinkage_weights={"cell": 0.85},
    )
    d = pred.to_dict()
    assert d["p50"] == 18.0
    assert d["target_measure"] == "guaranteed_cash_annual"
    assert d["currency"] == "INR"

    diag = HierarchicalCrossingDiagnostics(
        pre_repair_crossing_count=0,
        pre_repair_crossing_rate=0.0,
        max_crossing_magnitude_lpa=0.0,
        post_repair_crossing_rate=0.0,
        is_crossing_free=True,
    )
    assert diag.to_dict()["is_crossing_free"] is True


@pytest.mark.unit
def test_group_node_dataclass() -> None:
    """Verify GroupNode represents shrinkage state accurately."""
    node = GroupNode(
        group_key="SWE::MID::BENGALURU",
        sample_size=25,
        raw_mean=3.10,
        shrunk_mean=3.05,
        shrinkage_factor=0.88,
        parent_mean=2.90,
    )
    d = node.to_dict()
    assert d["sample_size"] == 25
    assert d["shrinkage_factor"] == 0.88


@pytest.mark.unit
def test_model_fit_validation(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify model fit validates required columns and minimum sample size."""
    model = HierarchicalPartialPoolingModel()

    # Missing required column
    bad_df = synthetic_hierarchy_df.drop("location")
    with pytest.raises(ValueError, match="missing required columns"):
        model.fit(bad_df)

    # Insufficient samples (below global threshold)
    tiny_df = synthetic_hierarchy_df.head(2)
    model.fit(tiny_df)
    assert model.is_fitted is False


@pytest.mark.unit
def test_empirical_bayes_shrinkage_behavior(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify that Empirical Bayes correctly shrinks sparse cells while preserving dense cells."""
    cfg = HierarchicalConfig(k_min_employer=5)
    model = HierarchicalPartialPoolingModel(config=cfg)
    model.fit(synthetic_hierarchy_df)

    assert model.is_fitted is True
    assert model.train_sample_size_ > 350
    assert model.global_mean_ > 0.0
    assert model.residual_std_ > 0.0
    assert model.tau_cell_ >= 0.0

    summary = model.get_shrinkage_summary()
    assert summary["is_fitted"] is True
    assert summary["node_counts"]["roles"] == 3
    assert summary["node_counts"]["tiers"] == 3

    # Check dense vs sparse employer shrinkage
    dense_emp = model.nodes_emp_.get("EMP_DENSE_1")
    assert dense_emp is not None
    assert dense_emp.sample_size > 50
    # Dense employer should retain most of its group signal (lambda > 0.5)
    assert dense_emp.shrinkage_factor > 0.5

    # Check sparse employer with N < k_min (k_min = 5 per R-DA-10)
    sparse_emp = model.nodes_emp_.get("EMP_SPARSE_SINGLETON")
    assert sparse_emp is not None
    assert sparse_emp.sample_size < 5
    # Sparse employer must shrink entirely to parent tier (lambda = 0.0)
    assert sparse_emp.shrinkage_factor == 0.0
    assert sparse_emp.shrunk_mean == sparse_emp.parent_mean


@pytest.mark.unit
def test_predict_single_monotonic_quantiles(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify single prediction generates monotonically ordered quantiles in nominal INR LPA."""
    model = HierarchicalPartialPoolingModel()
    model.fit(synthetic_hierarchy_df)

    pred = model.predict_single(
        years_experience=4.0,
        role_family="SWE",
        seniority="MID",
        location="BENGALURU",
        employer_tier="TIER_1_PRODUCT",
        employer_cluster_id="EMP_DENSE_1",
    )

    assert pred.is_abstained is False
    assert pred.p10 is not None
    assert pred.p50 is not None
    assert pred.p90 is not None
    assert pred.p10 > 0.50  # statutory floor
    assert pred.p10 <= pred.p50 <= pred.p90  # monotonicity guaranteed (R-UQ-05)
    assert pred.point_estimate == pred.p50
    assert "cell" in pred.shrinkage_weights
    assert "tier" in pred.shrinkage_weights
    assert "emp" in pred.shrinkage_weights


@pytest.mark.unit
def test_predict_single_fallback_hierarchies(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify prediction gracefully falls back to parent nodes when cell or employer is unseen."""
    model = HierarchicalPartialPoolingModel()
    model.fit(synthetic_hierarchy_df)

    # Query unseen cell and unseen employer
    pred = model.predict_single(
        years_experience=3.0,
        role_family="SWE",
        seniority="MID",
        location="NEW_UNKNOWN_METRO",
        employer_tier="TIER_1_PRODUCT",
        employer_cluster_id="UNKNOWN_EMPLOYER_999",
    )

    assert pred.is_abstained is False
    assert pred.p10 is not None and pred.p50 is not None and pred.p90 is not None
    assert pred.p10 <= pred.p50 <= pred.p90
    # Employer cluster not seen, should fall back to tier
    assert pred.shrunk_components["emp_effect"] == pred.shrunk_components["tier_effect"]


@pytest.mark.unit
def test_thin_evidence_abstention_out_of_bounds_experience(
    synthetic_hierarchy_df: pl.DataFrame,
) -> None:
    """Verify model returns structured abstention on out-of-range YoE (Rule R-MD-08)."""
    model = HierarchicalPartialPoolingModel()
    model.fit(synthetic_hierarchy_df)

    # Negative experience
    pred_neg = model.predict_single(
        years_experience=-1.5,
        role_family="SWE",
        seniority="ENTRY",
        location="BENGALURU",
    )
    assert pred_neg.is_abstained is True
    assert pred_neg.abstention_reason == "THIN_EVIDENCE"
    assert pred_neg.p10 is None
    assert pred_neg.p50 is None
    assert pred_neg.p90 is None

    # Extreme veteran experience > 40 years
    pred_vet = model.predict_single(
        years_experience=45.0,
        role_family="SWE",
        seniority="LEAD",
        location="BENGALURU",
    )
    assert pred_vet.is_abstained is True
    assert pred_vet.abstention_reason == "THIN_EVIDENCE"


@pytest.mark.unit
def test_unfitted_model_abstains() -> None:
    """Verify predicting on an unfitted model returns structured abstention."""
    model = HierarchicalPartialPoolingModel()
    pred = model.predict_single(
        years_experience=3.0,
        role_family="SWE",
        seniority="MID",
        location="BENGALURU",
    )
    assert pred.is_abstained is True
    assert pred.abstention_reason == "MODEL_NOT_FITTED"


@pytest.mark.unit
def test_batch_predict_polars(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify batch predict returns a Polars DataFrame conforming to contracts."""
    model = HierarchicalPartialPoolingModel()
    model.fit(synthetic_hierarchy_df)

    test_df = synthetic_hierarchy_df.head(10)
    preds_df = model.predict(test_df)

    assert isinstance(preds_df, pl.DataFrame)
    assert len(preds_df) == 10
    expected_cols = [
        "p10",
        "p50",
        "p90",
        "point_estimate",
        "is_crossing_repaired",
        "is_abstained",
        "abstention_reason",
        "shrinkage_cell",
        "shrinkage_tier",
        "shrinkage_emp",
    ]
    for col in expected_cols:
        assert col in preds_df.columns

    # Verify all P10 <= P50 <= P90
    p10 = preds_df["p10"].to_numpy()
    p50 = preds_df["p50"].to_numpy()
    p90 = preds_df["p90"].to_numpy()
    assert np.all(p10 <= p50)
    assert np.all(p50 <= p90)

    # Empty DataFrame batch test
    empty_df = pl.DataFrame(schema=synthetic_hierarchy_df.schema)
    empty_pred = model.predict(empty_df)
    assert len(empty_pred) == 0


@pytest.mark.unit
def test_model_serialization_roundtrip(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify complete model state can be serialized to dict and reconstructed without loss."""
    model = HierarchicalPartialPoolingModel()
    model.fit(synthetic_hierarchy_df)

    # Predict before serialization
    test_profile = {
        "years_experience": 5.5,
        "role_family": "MLAI",
        "seniority": "SR",
        "location": "BENGALURU",
        "employer_tier": "TIER_1_PRODUCT",
        "employer_cluster_id": "EMP_DENSE_1",
    }
    pred_orig = model.predict_single(**test_profile)

    # Roundtrip serialization
    serialized = model.to_dict()
    reconstructed = HierarchicalPartialPoolingModel.from_dict(serialized)

    assert reconstructed.is_fitted is True
    assert reconstructed.train_sample_size_ == model.train_sample_size_
    assert reconstructed.global_mean_ == model.global_mean_
    assert reconstructed.residual_std_ == model.residual_std_
    assert reconstructed.tau_cell_ == model.tau_cell_

    # Predict with reconstructed model
    pred_recon = reconstructed.predict_single(**test_profile)

    assert pred_recon.p10 == pred_orig.p10
    assert pred_recon.p50 == pred_orig.p50
    assert pred_recon.p90 == pred_orig.p90
    assert pred_recon.shrinkage_weights == pred_orig.shrinkage_weights


@pytest.mark.unit
def test_linear_experience_option(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify model functions with degree=1 (linear experience curve)."""
    cfg = HierarchicalConfig(experience_polynomial_degree=1)
    model = HierarchicalPartialPoolingModel(config=cfg)
    model.fit(synthetic_hierarchy_df)

    assert model.is_fitted is True
    assert model.beta_experience_quadratic_ == 0.0
    pred = model.predict_single(
        years_experience=4.0,
        role_family="SWE",
        seniority="MID",
        location="BENGALURU",
    )
    assert pred.p50 is not None
    assert pred.p10 <= pred.p50 <= pred.p90


@pytest.mark.unit
def test_role_only_and_unknown_role_fallback(synthetic_hierarchy_df: pl.DataFrame) -> None:
    """Verify fallback when seniority is unknown (role-only) and when role is unknown."""
    model = HierarchicalPartialPoolingModel()
    model.fit(synthetic_hierarchy_df)

    # Unknown seniority and location, known role
    pred_role = model.predict_single(
        years_experience=3.0,
        role_family="SWE",
        seniority="UNKNOWN_SENIORITY",
        location="UNKNOWN_LOCATION",
    )
    assert pred_role.is_abstained is False
    assert pred_role.p50 is not None
    assert pred_role.p10 <= pred_role.p50 <= pred_role.p90
    assert pred_role.shrunk_components["cell_effect"] == model.nodes_role_["SWE"].shrunk_mean

    # Unknown role, unknown seniority, unknown location
    pred_unknown = model.predict_single(
        years_experience=3.0,
        role_family="UNKNOWN_ROLE",
        seniority="UNKNOWN_SENIORITY",
        location="UNKNOWN_LOCATION",
    )
    assert pred_unknown.is_abstained is False
    assert pred_unknown.p50 is not None
    assert pred_unknown.shrunk_components["cell_effect"] == 0.0
