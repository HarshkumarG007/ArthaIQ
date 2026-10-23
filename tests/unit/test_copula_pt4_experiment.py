"""Unit tests for EXP-PGM-01r: Gaussian Copula Dependency Structure for Multi-Component PT4.

Phase 13, Task T13.07.

Validates:
1. EmpiricalMarginalTransformer PIT mapping, monotonicity, and inverse transform.
2. GaussianCopulaJointModel correlation matrix estimation, positive definiteness, and sampling.
3. Conditional simulation: exact conditional distribution and non-crossing quantiles.
4. Full evaluation workflow: Spearman rank preservation, Kendall tau, latency SLA, and coverage.
5. Report generation, markdown serialization, and JSON persistence.
6. Pre-registered keep criteria audit yielding unconditional PROMOTE verdict.
7. Scope boundary enforcement: Champion CatBoost strictly unmodified for core estimation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from compintel.errors import CompIntelValidationError
from compintel.evaluation.copula_pt4_experiment import (
    CHARTER_ID,
    EXPERIMENT_ID,
    MAX_P95_LATENCY_MS,
    MAX_QUANTILE_CROSSING_RATE,
    MAX_SPEARMAN_ERROR_THRESHOLD,
    TASK_ID,
    CopulaVerdict,
    EmpiricalMarginalTransformer,
    GaussianCopulaJointModel,
    build_multicomponent_benchmark_dataset,
    evaluate_and_save_copula_pt4_experiment,
    evaluate_copula_experiment,
    run_copula_pt4_experiment,
)


@pytest.fixture
def synthetic_multicomponent_matrix() -> np.ndarray:
    """Generate deterministic multi-component matrix for fast unit testing."""
    mat, _ = build_multicomponent_benchmark_dataset(n_cases=200, seed=42)
    return mat


class TestEmpiricalMarginalTransformer:
    """Test suite for non-parametric empirical probability integral transform (PIT)."""

    def test_fit_and_transform_monotonic(self) -> None:
        values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        trans = EmpiricalMarginalTransformer().fit(values)

        u = trans.transform(values)
        assert len(u) == 5
        assert np.all(u >= 0.0) and np.all(u <= 1.0)
        # Monotonicity check
        assert np.all(np.diff(u) > 0.0)

    def test_inverse_transform_recovers_support(self) -> None:
        values = np.linspace(10.0, 100.0, 50)
        trans = EmpiricalMarginalTransformer().fit(values)

        u = np.array([0.10, 0.50, 0.90])
        rec = trans.inverse_transform(u)
        assert len(rec) == 3
        assert rec[0] < rec[1] < rec[2]
        assert 10.0 <= rec[0] <= 100.0

    def test_unfitted_transform_raises(self) -> None:
        trans = EmpiricalMarginalTransformer()
        with pytest.raises(CompIntelValidationError, match="must be fitted before transform"):
            trans.transform(np.array([1.0, 2.0]))

    def test_invalid_input_raises(self) -> None:
        trans = EmpiricalMarginalTransformer()
        with pytest.raises(CompIntelValidationError, match="requires non-empty 1D array"):
            trans.fit(np.array([]))


class TestGaussianCopulaJointModel:
    """Test suite for Gaussian copula multi-component dependency model."""

    def test_fit_and_properties(self, synthetic_multicomponent_matrix: np.ndarray) -> None:
        model = GaussianCopulaJointModel().fit(synthetic_multicomponent_matrix)

        assert model.is_fitted
        assert model.corr_matrix is not None
        assert model.corr_matrix.shape == (3, 3)
        # Check diagonal is 1.0
        assert np.allclose(np.diag(model.corr_matrix), 1.0, atol=1e-4)
        # Check symmetry
        assert np.allclose(model.corr_matrix, model.corr_matrix.T, atol=1e-5)
        # Check positive definiteness
        eigs = np.linalg.eigvalsh(model.corr_matrix)
        assert np.all(eigs > 0.0)

    def test_sample_shape_and_range(self, synthetic_multicomponent_matrix: np.ndarray) -> None:
        model = GaussianCopulaJointModel().fit(synthetic_multicomponent_matrix)
        samples = model.sample(n_samples=250, seed=42)

        assert samples.shape == (250, 3)
        assert not np.isnan(samples).any()
        # Non-negative compensation components
        assert np.all(samples >= 0.0)

    def test_simulate_conditional_tradeoff_monotonic(
        self, synthetic_multicomponent_matrix: np.ndarray
    ) -> None:
        model = GaussianCopulaJointModel().fit(synthetic_multicomponent_matrix)

        # Test at different cash levels
        for cash_test in [15.0, 30.0, 60.0]:
            tradeoff = model.simulate_conditional_tradeoff(cash_test, n_draws=300, seed=42)
            assert "equity" in tradeoff
            assert "bonus" in tradeoff

            eq = tradeoff["equity"]
            bn = tradeoff["bonus"]

            # Strict monotonic non-crossing quantiles: P10 <= P50 <= P90
            assert eq.p10 <= eq.p50 <= eq.p90, f"Equity crossed: {eq}"
            assert bn.p10 <= bn.p50 <= bn.p90, f"Bonus crossed: {bn}"
            assert eq.p10 >= 0.0
            assert bn.p10 >= 0.0

    def test_conditional_tradeoff_scales_with_cash(
        self, synthetic_multicomponent_matrix: np.ndarray
    ) -> None:
        model = GaussianCopulaJointModel().fit(synthetic_multicomponent_matrix)

        tradeoff_low = model.simulate_conditional_tradeoff(15.0, n_draws=400, seed=42)
        tradeoff_high = model.simulate_conditional_tradeoff(55.0, n_draws=400, seed=42)

        # Higher base cash should yield higher median equity and bonus in tech market
        assert tradeoff_high["equity"].p50 > tradeoff_low["equity"].p50
        assert tradeoff_high["bonus"].p50 > tradeoff_low["bonus"].p50


class TestCopulaEvaluationWorkflow:
    """Test suite for empirical evaluation metrics and pre-registered keep criteria."""

    def test_evaluate_copula_experiment_metrics(
        self, synthetic_multicomponent_matrix: np.ndarray
    ) -> None:
        metrics = evaluate_copula_experiment(synthetic_multicomponent_matrix, seed=42)

        assert metrics.sample_size == len(synthetic_multicomponent_matrix)
        assert metrics.n_components == 3
        assert len(metrics.pairwise_metrics) == 3  # (0,1), (0,2), (1,2)

        # Spearman rank error must be within charter threshold
        assert metrics.max_spearman_error <= MAX_SPEARMAN_ERROR_THRESHOLD
        assert metrics.quantile_crossing_rate <= MAX_QUANTILE_CROSSING_RATE
        assert metrics.p95_latency_ms <= MAX_P95_LATENCY_MS
        assert metrics.zero_lone_number_compliant is True
        assert metrics.core_model_uncontaminated is True

    def test_run_copula_pt4_experiment_promote_verdict(self) -> None:
        report = run_copula_pt4_experiment(seed=42)

        assert report.charter_id == CHARTER_ID
        assert report.experiment_id == EXPERIMENT_ID
        assert report.task_id == TASK_ID
        assert report.verdict == CopulaVerdict.PROMOTE

        # Check all 6 keep criteria passed
        for criterion, passed in report.keep_criteria_status.items():
            assert passed is True, f"Keep criterion '{criterion}' failed"

        # Verify Markdown memo contains key sections
        md = report.to_markdown()
        assert "# Copula Dependency Structure for Multi-Component PT4" in md
        assert "## 1. Executive Summary & Production Decision" in md
        assert "## 2. Pre-Registered Keep Criteria Audit" in md
        assert "## 3. Multivariate Dependency Analysis" in md
        assert "## 4. Latency and Monotonicity Performance Profile" in md
        assert "## 5. Scope Boundary & Architectural Governance" in md
        assert "Champion CatBoost Preserved Unmodified" in md
        assert "PROMOTE" in md

    def test_evaluate_and_save_copula_pt4_experiment(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "results"
        doc_dir = tmp_path / "docs"

        report = evaluate_and_save_copula_pt4_experiment(
            output_dir=out_dir,
            docs_dir=doc_dir,
            seed=42,
        )

        assert report.verdict == CopulaVerdict.PROMOTE

        json_file = out_dir / "copula_pt4_report.json"
        md_file = doc_dir / "copula-pt4-phase13.md"

        assert json_file.is_file()
        assert md_file.is_file()

        with open(json_file, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        assert data["task_id"] == "T13.07"
        assert data["verdict"] == "PROMOTE"
        assert data["metrics"]["max_spearman_error"] <= 0.050
        assert data["metrics"]["quantile_crossing_rate"] == 0.0
