"""Unit tests for Sparse Cell Benchmark Engine and CLI (T6.07, EXP-05).

Adheres to:
- PRD Section 5 & FR-04, FR-05: Sparse cell regimes and hierarchical shrinkage.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-13: Compare-only current pay quarantine.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
- Rule R-UQ-06: Prior sensitivity analysis across cell bands.
- Rule R-DA-10: Anonymization floor k_min >= 5.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_sparse_cell_benchmark import main as run_sparse_cell_benchmark_main
from scripts.run_sparse_cell_benchmark import parse_args

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.sparse_cell_benchmark import (
    SparseCellBand,
    SparseCellBenchmarkReport,
    SparseCellBenchmarkVerdict,
    evaluate_and_save_sparse_cell_benchmark,
    run_sparse_cell_benchmark,
)


@pytest.fixture
def sparse_cells_synthetic_df() -> pl.DataFrame:
    """Fixture providing 80 synthetic observations across varied cell density regimes."""
    n_rows = 80
    rng = np.random.default_rng(42)

    # Cell structure: 1 dense cell (50 rows), 1 sparse cell (20 rows), 1 rare cell (10 rows)
    roles = (["SOFTWARE"] * 50) + (["DATA"] * 20) + (["MLAI"] * 10)
    seniorities = (["MID"] * 50) + (["SENIOR"] * 20) + (["LEAD"] * 10)
    locations = (["BANGALORE"] * 50) + (["HYDERABAD"] * 20) + (["PUNE"] * 10)

    yoe = [float(i % 12) + 1.0 for i in range(n_rows)]
    salaries = [
        12.0 + (y * 1.5) + (8.0 if s in ("SENIOR", "LEAD") else 0.0) + float(rng.uniform(-1.0, 1.0))
        for y, s in zip(yoe, seniorities, strict=False)
    ]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 4) for i in range(n_rows)]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "person_cluster_id": [f"PER-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            "role_family": roles,
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "employer_cluster_id": [f"EMP-{i % 6:02d}" for i in range(n_rows)],
            "employer_tier": [
                "TIER_1_PRODUCT" if i % 2 == 0 else "TIER_2_GROWTH" for i in range(n_rows)
            ],
            "is_synthetic": [True] * n_rows,
        }
    )


def test_sparse_cell_enums() -> None:
    """Test SparseCellBand and SparseCellBenchmarkVerdict enum values."""
    assert SparseCellBand.VERY_SPARSE == "VERY_SPARSE"
    assert SparseCellBand.SPARSE == "SPARSE"
    assert SparseCellBand.DENSE == "DENSE"

    assert SparseCellBenchmarkVerdict.HYBRID_ROUTING == "HYBRID_ROUTING"
    assert SparseCellBenchmarkVerdict.UNIFIED_CONFORMAL_GBM == "UNIFIED_CONFORMAL_GBM"


def test_run_sparse_cell_benchmark_test_split_lock_violation(
    sparse_cells_synthetic_df: pl.DataFrame,
) -> None:
    """Test evaluating on 'test' split raises DataContractError (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        run_sparse_cell_benchmark(
            train_df=sparse_cells_synthetic_df,
            eval_df=sparse_cells_synthetic_df,
            calibrate_df=sparse_cells_synthetic_df,
            eval_split_name="test",
        )


def test_run_sparse_cell_benchmark_success(sparse_cells_synthetic_df: pl.DataFrame) -> None:
    """Test successful execution of sparse cell benchmark comparing Rung C vs Rung F."""
    train_df = sparse_cells_synthetic_df[:50]
    eval_df = sparse_cells_synthetic_df[50:]
    calib_df = sparse_cells_synthetic_df[25:50]

    report = run_sparse_cell_benchmark(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
    )

    assert isinstance(report, SparseCellBenchmarkReport)
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == len(eval_df)
    assert report.verdict in (
        SparseCellBenchmarkVerdict.HYBRID_ROUTING,
        SparseCellBenchmarkVerdict.UNIFIED_CONFORMAL_GBM,
    )

    # Verify band comparisons
    assert len(report.band_comparisons) > 0
    for comp in report.band_comparisons:
        assert comp.n_eval_samples > 0
        assert comp.n_unique_cells > 0
        assert comp.rung_c_metrics.crossing_rate == 0.0
        assert comp.rung_f_metrics.crossing_rate == 0.0
        assert comp.delta_pinball_ci_lower <= comp.delta_pinball_ci_upper
        assert comp.width_ratio > 0.0
        assert comp.superior_architecture in (
            "Rung C (Hierarchical)",
            "Rung F (Conformal GBM)",
            "PARITY",
        )

    # Verify prior sensitivities
    assert len(report.prior_sensitivities) > 0
    for sens in report.prior_sensitivities:
        assert sens.max_p50_shift >= 0.0
        assert -1.0 <= sens.min_rank_correlation <= 1.0

    # Serialization
    d = report.to_dict()
    assert d["report_id"].startswith("EXP05-SPARSE-")
    md = report.to_markdown()
    assert "# Hierarchical Bayes vs Conformal GBM Sparse Cell Benchmark" in md
    assert "Density Band Benchmark" in md
    assert "Architectural Synthesis & Serving Policy" in md


def test_evaluate_and_save_sparse_cell_benchmark_missing_file(tmp_path: Path) -> None:
    """Test evaluate_and_save_sparse_cell_benchmark raises validation error on missing file."""
    missing = tmp_path / "missing.parquet"
    with pytest.raises(CompIntelValidationError, match="Canonical dataset not found"):
        evaluate_and_save_sparse_cell_benchmark(canonical_path=missing)


def test_evaluate_and_save_sparse_cell_benchmark_synthetic_blocked(
    tmp_path: Path, sparse_cells_synthetic_df: pl.DataFrame
) -> None:
    """Test synthetic data is blocked without explicit allow_synthetic override (Rule R-MD-11)."""
    p = tmp_path / "canonical.parquet"
    sparse_cells_synthetic_df.write_parquet(p)

    with pytest.raises(DataContractError, match="Synthetic data detected"):
        evaluate_and_save_sparse_cell_benchmark(canonical_path=p, allow_synthetic=False)


def test_evaluate_and_save_sparse_cell_benchmark_test_split_blocked() -> None:
    """Test evaluate_and_save_sparse_cell_benchmark rejects locked test split (Rule R-MD-02)."""
    with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
        evaluate_and_save_sparse_cell_benchmark(eval_split_name="test")


def test_evaluate_and_save_sparse_cell_benchmark_success(
    tmp_path: Path, sparse_cells_synthetic_df: pl.DataFrame
) -> None:
    """Test evaluate_and_save_sparse_cell_benchmark persists Markdown and JSON report files."""
    canonical_file = tmp_path / "canonical.parquet"
    sparse_cells_synthetic_df.write_parquet(canonical_file)

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    report = evaluate_and_save_sparse_cell_benchmark(
        canonical_path=canonical_file,
        output_md=out_md,
        output_json=out_json,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
        allow_synthetic=True,
    )

    assert out_md.exists()
    assert out_json.exists()
    assert report.report_id.startswith("EXP05-SPARSE-")


def test_cli_parse_args_defaults() -> None:
    """Test CLI argument parsing default values."""
    with patch.object(sys, "argv", ["run_sparse_cell_benchmark.py"]):
        args = parse_args()
        assert args.canonical_path == "data/canonical/canonical_observations.parquet"
        assert args.output_md == "docs/research/hierarchical-vs-gbm-sparse-cells-exp05.md"
        assert args.output_json == "experiments/results/hierarchical_vs_gbm_sparse_v1.json"
        assert args.split == "select"
        assert args.n_resamples == 1000
        assert args.seed == 42
        assert args.allow_synthetic is False


def test_cli_runner_success(tmp_path: Path, sparse_cells_synthetic_df: pl.DataFrame) -> None:
    """Test successful CLI execution end-to-end."""
    synth_file = tmp_path / "canonical.parquet"
    sparse_cells_synthetic_df.write_parquet(synth_file)

    out_md = tmp_path / "cli_report.md"
    out_json = tmp_path / "cli_report.json"

    test_args = [
        "run_sparse_cell_benchmark.py",
        "--canonical-path",
        str(synth_file),
        "--output-md",
        str(out_md),
        "--output-json",
        str(out_json),
        "--split",
        "select",
        "--n-resamples",
        "50",
        "--seed",
        "42",
        "--allow-synthetic",
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_sparse_cell_benchmark_main()

    assert ret_code == 0
    assert out_md.exists()
    assert out_json.exists()


def test_cli_runner_missing_canonical_file(tmp_path: Path) -> None:
    """Test CLI exit code 1 on missing canonical file."""
    missing_file = tmp_path / "does_not_exist.parquet"
    test_args = [
        "run_sparse_cell_benchmark.py",
        "--canonical-path",
        str(missing_file),
    ]

    with patch.object(sys, "argv", test_args):
        ret_code = run_sparse_cell_benchmark_main()

    assert ret_code == 1


def test_cli_runner_fatal_exception() -> None:
    """Test CLI exit code 2 on unexpected fatal crash."""
    test_args = ["run_sparse_cell_benchmark.py"]

    with (
        patch.object(sys, "argv", test_args),
        patch(
            "scripts.run_sparse_cell_benchmark.evaluate_and_save_sparse_cell_benchmark",
            side_effect=RuntimeError("Fatal divergence crash"),
        ),
    ):
        ret_code = run_sparse_cell_benchmark_main()

    assert ret_code == 2
