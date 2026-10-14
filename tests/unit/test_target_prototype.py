"""Unit tests for PT1 prototype target construction and exclusion accounting (Task T2.08).

Governed by rules.md (R-DA-05 No silent drops, R-MD-07 Anti-heuristic unbundling).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from compintel.quality.target_prototype import (
    _parse_comp,
    _parse_yoe,
    build_pt1_prototype,
    export_prototype_artifacts,
)


@pytest.mark.unit
def test_parse_helpers() -> None:
    """Verify raw survey experience and compensation parsing."""
    # YOE parsing
    assert _parse_yoe("Less than 1 year") == 0.5
    assert _parse_yoe("More than 50 years") == 50.0
    assert _parse_yoe("5") == 5.0
    assert _parse_yoe("0") == 0.0
    assert _parse_yoe("NA") is None
    assert _parse_yoe("") is None
    assert _parse_yoe(None) is None
    assert _parse_yoe("-5") is None

    # Comp parsing
    assert _parse_comp("1500000") == 1500000.0
    assert _parse_comp("2400000.50") == 2400000.50
    assert _parse_comp("0") == 0.0
    assert _parse_comp("NA") is None
    assert _parse_comp("") is None
    assert _parse_comp(None) is None


@pytest.mark.unit
def test_build_pt1_prototype_and_reconciliation() -> None:
    """Verify prototype construction and exact exclusion accounting (Rule R-DA-05)."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    result = build_pt1_prototype(repo_root=repo_root)

    # Check total evaluated
    assert result.total_evaluated == 648, f"Expected 648 evaluated, got {result.total_evaluated}"

    # Strict PT1 count must be exactly 0 (Rule R-MD-07 unbundled aggregate quarantine)
    assert result.strict_pt1_count == 0

    # Exploratory count must be 102
    assert result.exploratory_candidate_count == 102

    # Rule R-DA-05: Total in = Total kept + Total excluded (Zero discrepancy)
    total_excluded = sum(result.exclusion_counts.values())
    assert result.total_evaluated == result.strict_pt1_count + total_excluded

    # Ensure all primary exclusion codes are accounted for
    expected_codes = {
        "EXC_GEO_OUT_OF_SCOPE",
        "EXC_ENTERPRISE_AGGREGATE",
        "EXC_NON_FULLTIME",
        "EXC_NON_TECH_OCCUPATION",
        "EXC_MISSING_COMPENSATION",
        "EXC_CURRENCY_MISMATCH",
        "EXC_COMPENSATION_OUTLIER",
        "EXC_MISSING_EXPERIENCE",
        "EXC_UNBUNDLED_CTC_OR_AGGREGATE",
        "EXC_EXACT_OR_NEAR_DUPLICATE",
    }
    assert set(result.exclusion_counts.keys()) == expected_codes


@pytest.mark.unit
def test_export_prototype_artifacts(tmp_path: Path) -> None:
    """Verify prototype artifacts are cleanly exported to disk."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    result = build_pt1_prototype(repo_root=repo_root)

    data_dir = tmp_path / "data" / "processed"
    results_dir = tmp_path / "experiments" / "results"

    artifacts = export_prototype_artifacts(
        result, output_data_dir=data_dir, output_results_dir=results_dir
    )

    assert artifacts["strict_dataset"].exists()
    assert artifacts["exploratory_dataset"].exists()
    assert artifacts["quarantine_audit"].exists()
    assert artifacts["exclusion_report"].exists()

    # Verify strict dataset has 0 rows and correct schema
    strict_df = pl.read_parquet(artifacts["strict_dataset"])
    assert strict_df.height == 0
    assert "annual_pay_lpa" in strict_df.columns

    # Verify exploratory dataset has 102 rows
    exp_df = pl.read_parquet(artifacts["exploratory_dataset"])
    assert exp_df.height == 102
    assert "annual_pay_lpa" in exp_df.columns
    assert exp_df["is_unbundled_aggregate"].all()

    # Verify quarantine audit has 648 rows
    quar_df = pl.read_parquet(artifacts["quarantine_audit"])
    assert quar_df.height == 648

    # Verify report contents
    report_text = artifacts["exclusion_report"].read_text(encoding="utf-8")
    assert "Reconciliation Equation" in report_text
    assert "VERIFIED (0 discrepancy)" in report_text
    assert "Zero Strict Training Observations" in report_text


@pytest.mark.unit
def test_persisted_exclusion_reports() -> None:
    """Verify persisted exclusion report files exist in research and results directories."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_report = repo_root / "experiments" / "results" / "pt1_prototype_exclusion_report.md"
    research_report = repo_root / "docs" / "research" / "pt1-prototype-exclusion-report.md"

    assert results_report.exists(), (
        "Missing pt1_prototype_exclusion_report.md in experiments/results/"
    )
    assert research_report.exists(), "Missing pt1-prototype-exclusion-report.md in docs/research/"

    text = results_report.read_text(encoding="utf-8")
    assert "648" in text
    assert "EXC_UNBUNDLED_CTC_OR_AGGREGATE" in text
