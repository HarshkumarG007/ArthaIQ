"""Unit tests for sufficiency evaluation and bootstrap precision (Task T2.09).

Governed by experiments/preregistration/sufficiency-v1.yaml.
Tests:
- Bootstrap precision calculation, confidence intervals, half-widths, relative widths.
- Privacy Gate (k-anonymity k_min = 5 suppression).
- Naive cohort interval width ratio calculation (Rule R-UQ-04).
- 84-cell evaluation schema and completeness.
- Gate G2 decision logic (GO / CONDITIONAL-GO / NO-GO).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import polars as pl
import pytest

from compintel.quality.sufficiency import (
    compute_bootstrap_precision,
    compute_naive_cohort_widths,
    evaluate_gate_g2_decision,
    evaluate_precision_for_all_cells,
    update_coverage_map_with_c5,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
def test_bootstrap_precision_privacy_suppression() -> None:
    """Test that cells with n < k_min (k_min = 5) are suppressed."""
    # 4 observations (< 5)
    vals = np.array([10.0, 12.0, 15.0, 18.0], dtype=np.float64)
    res = compute_bootstrap_precision(vals, k_min=5)

    assert res.is_suppressed is True
    assert res.c5_pass is False
    assert res.p50 is None
    assert res.half_width_lpa is None
    assert "Privacy Gate" in str(res.suppression_reason)


@pytest.mark.unit
def test_bootstrap_precision_passing_case() -> None:
    """Test a high-precision cell where half-width <= 3.0 LPA and relative width <= 2.0."""
    # Tight distribution around 20 LPA (N = 50)
    rng = np.random.default_rng(seed=123)
    vals = rng.normal(loc=20.0, scale=1.0, size=50)

    res = compute_bootstrap_precision(
        vals,
        naive_cohort_width=25.0,
        n_bootstrap=500,
        random_seed=42,
    )

    assert res.is_suppressed is False
    assert res.p50 is not None
    assert 19.0 <= res.p50 <= 21.0
    assert res.half_width_lpa is not None
    assert res.half_width_lpa < 1.0  # Very tight half-width
    assert res.relative_interval_width is not None
    assert res.relative_interval_width < 0.5  # Very tight relative width
    assert res.c5_pass is True
    assert res.width_ratio_vs_naive is not None
    assert res.width_ratio_vs_naive < 1.0


@pytest.mark.unit
def test_bootstrap_precision_failing_half_width() -> None:
    """Test a dispersed cell where half-width > 3.0 LPA fails C5."""
    # Dispersed distribution (N = 15, scale = 15.0)
    rng = np.random.default_rng(seed=456)
    vals = rng.normal(loc=30.0, scale=15.0, size=15)
    vals = np.clip(vals, 5.0, 100.0)

    res = compute_bootstrap_precision(
        vals,
        naive_cohort_width=30.0,
        n_bootstrap=500,
        random_seed=42,
    )

    assert res.is_suppressed is False
    assert res.half_width_lpa is not None
    assert res.half_width_lpa > 3.0
    assert res.c5_pass is False


@pytest.mark.unit
def test_naive_cohort_widths() -> None:
    """Test calculation of unconditional marginal naive cohort widths."""
    data = {
        "family": ["SWE"] * 10 + ["DATA"] * 6 + ["MLAI"] * 3,
        "annual_pay_lpa": [
            10.0,
            12.0,
            14.0,
            16.0,
            18.0,
            20.0,
            22.0,
            24.0,
            26.0,
            30.0,  # SWE (N=10)
            15.0,
            18.0,
            20.0,
            25.0,
            30.0,
            35.0,  # DATA (N=6)
            20.0,
            25.0,
            30.0,  # MLAI (N=3 < 5)
        ],
    }
    df = pl.DataFrame(data)
    widths = compute_naive_cohort_widths(df)

    assert "SWE" in widths
    assert widths["SWE"] > 0.0
    assert "DATA" in widths
    assert widths["DATA"] > 0.0
    assert widths["MLAI"] == 0.0  # N < 5


@pytest.mark.unit
def test_evaluate_precision_for_all_cells_schema() -> None:
    """Test that precision dataframe evaluates exactly 84 cells with valid schema."""
    df_prec = evaluate_precision_for_all_cells(df_exploratory=None, n_bootstrap=10)

    assert len(df_prec) == 84
    expected_cols = [
        "family",
        "location",
        "band",
        "n_observations",
        "p10",
        "p50",
        "p90",
        "p50_ci_lower",
        "p50_ci_upper",
        "half_width_lpa",
        "relative_interval_width",
        "width_ratio_vs_naive",
        "c5_pass",
        "n_bootstrap",
    ]
    for col in expected_cols:
        assert col in df_prec.columns

    # With no data, all cells fail C5
    assert df_prec["c5_pass"].sum() == 0


@pytest.mark.unit
def test_update_coverage_map_with_c5() -> None:
    """Test that c5_pass joins into coverage map and affects overall_pass."""
    cov_data = {
        "family": ["SWE", "SWE"],
        "location": ["BLR", "HYD"],
        "band": ["JR", "MID"],
        "c1_pass": [True, True],
        "c2_pass": [True, True],
        "c3_pass": [True, True],
        "c4_pass": [True, True],
        "pg_pass": [True, True],
        "overall_pass": [True, True],
    }
    cov_df = pl.DataFrame(cov_data)

    prec_data = {
        "family": ["SWE", "SWE"],
        "location": ["BLR", "HYD"],
        "band": ["JR", "MID"],
        "c5_pass": [True, False],
    }
    prec_df = pl.DataFrame(prec_data)

    updated = update_coverage_map_with_c5(cov_df, prec_df)
    assert "c5_pass" in updated.columns
    assert updated.filter(pl.col("location") == "BLR")["overall_pass"][0] is True
    assert updated.filter(pl.col("location") == "HYD")["overall_pass"][0] is False


@pytest.mark.unit
def test_evaluate_gate_g2_decision_rules() -> None:
    """Test Gate G2 decision logic across NO-GO, CONDITIONAL-GO, and GO states."""
    # 1. NO-GO state (Kill Criterion 1: some core cells fail C1)
    df_no_go = pl.DataFrame(
        {
            "is_core": [True] * 12 + [False] * 72,
            "c1_pass": [False] * 12 + [False] * 72,
        }
    )
    dec_no_go = evaluate_gate_g2_decision(df_no_go)
    assert dec_no_go["verdict"] == "NO_GO"

    # 2. CONDITIONAL-GO state (all 12 core pass, extended < 30%)
    df_cond_go = pl.DataFrame(
        {
            "is_core": [True] * 12 + [False] * 72,
            "c1_pass": [True] * 12 + [True] * 10 + [False] * 62,  # 10/72 = 13.9% < 30%
        }
    )
    dec_cond_go = evaluate_gate_g2_decision(df_cond_go)
    assert dec_cond_go["verdict"] == "CONDITIONAL_GO"

    # 3. GO state (all 12 core pass, extended >= 30%)
    df_go = pl.DataFrame(
        {
            "is_core": [True] * 12 + [False] * 72,
            "c1_pass": [True] * 12 + [True] * 30 + [False] * 42,  # 30/72 = 41.7% >= 30%
        }
    )
    dec_go = evaluate_gate_g2_decision(df_go)
    assert dec_go["verdict"] == "GO"


@pytest.mark.unit
def test_export_sufficiency_artifacts(tmp_path: Path) -> None:
    """Test artifact export and markdown report generation."""
    from compintel.quality.coverage import get_canonical_cells
    from compintel.quality.sufficiency import (
        export_sufficiency_artifacts,
        generate_sufficiency_report_markdown,
    )

    cells = get_canonical_cells()
    rows = []
    for c in cells:
        rows.append(
            {
                "family": c.family,
                "location": c.location,
                "band": c.band,
                "cell_id": c.cell_id,
                "is_core": c.is_core,
                "n_raw": 0,
                "n_eff": 0.0,
                "sqs_avg": 0.0,
                "median_age_days": 0.0,
                "c1_pass": False,
                "c2_pass": False,
                "c3_pass": False,
                "c4_pass": False,
                "pg_pass": False,
                "overall_pass": False,
                "evidence_grade": "ABSTAINED",
                "n_distinct_persons": 0,
                "diagnostic_n_exploratory": 0,
            }
        )
    coverage_df = pl.DataFrame(rows)
    precision_df = evaluate_precision_for_all_cells(None, n_bootstrap=10)
    g2_decision = evaluate_gate_g2_decision(coverage_df)

    # Test markdown report generation
    md_content = generate_sufficiency_report_markdown(
        coverage_df=coverage_df,
        precision_df=precision_df,
        exploratory_precision_df=precision_df,
        g2_decision=g2_decision,
    )
    assert "KILL CRITERION 1 TRIGGERED" in md_content
    assert "experiments/preregistration/sufficiency-v1.yaml" in md_content
    assert "Gate G2 Final Decision" in md_content

    # Test export
    results_dir = tmp_path / "results"
    docs_dir = tmp_path / "docs"
    exported = export_sufficiency_artifacts(
        coverage_df=coverage_df,
        precision_df=precision_df,
        exploratory_precision_df=precision_df,
        g2_decision=g2_decision,
        results_dir=results_dir,
        docs_dir=docs_dir,
    )

    assert exported["coverage_parquet"].exists()
    assert exported["coverage_csv"].exists()
    assert exported["precision_parquet"].exists()
    assert exported["precision_csv"].exists()
    assert exported["report_markdown"].exists()
