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
def test_build_pt1_prototype_synthetic(tmp_path: Path) -> None:
    """Verify prototype construction, zero-discrepancy reconciliation (R-DA-05), and export

    using a fully controlled synthetic raw dataset suitable for portable CI execution (R-DA-08).
    """
    raw_dir = tmp_path / "data" / "raw"

    # 1. BLS OEWS (SRC-USA-BLS-01) -> EXC_GEO_OUT_OF_SCOPE
    bls_dir = raw_dir / "SRC-USA-BLS-01"
    bls_dir.mkdir(parents=True)
    (bls_dir / "bls_oews_tech_estimates_may2023.csv").write_text(
        "OCC_TITLE,TOT_EMP\nSoftware Developers,100\n", encoding="utf-8"
    )

    # 2. Enterprise listed IT (SRC-SUP-CORP-01) -> EXC_ENTERPRISE_AGGREGATE
    corp_dir = raw_dir / "SRC-SUP-CORP-01"
    corp_dir.mkdir(parents=True)
    (corp_dir / "listed_it_mre_fy24.csv").write_text(
        "company_name,median_remuneration_lpa\nInfosys,9.5\n", encoding="utf-8"
    )

    # 3. National macro PLFS (SRC-IND-OFF-01) -> EXC_ENTERPRISE_AGGREGATE
    plfs_dir = raw_dir / "SRC-IND-OFF-01"
    plfs_dir.mkdir(parents=True)
    (plfs_dir / "plfs_urban_tech_macro_anchors.csv").write_text(
        "nco_code,wage_median\n2512,12.0\n", encoding="utf-8"
    )

    # 4. ai-jobs (SRC-KAG-AIJ-01) -> Geo, Missing comp, Currency mismatch, Outlier, Unbundled
    aij_dir = raw_dir / "SRC-KAG-AIJ-01"
    aij_dir.mkdir(parents=True)
    aij_content = (
        "employee_residence,job_title,experience_level,salary,salary_currency\n"
        "US,Data Scientist,SE,120000,USD\n"  # EXC_GEO_OUT_OF_SCOPE
        "IN,Data Scientist,SE,NA,INR\n"  # EXC_MISSING_COMPENSATION
        "IN,Data Scientist,SE,1200000,USD\n"  # EXC_CURRENCY_MISMATCH
        "IN,Data Scientist,SE,50000,INR\n"  # EXC_COMPENSATION_OUTLIER (0.5 LPA)
        "IN,Data Scientist,SE,2500000,INR\n"  # EXC_UNBUNDLED_CTC_OR_AGGREGATE (Exploratory)
    )
    (aij_dir / "ai_jobs_ds_salaries_2023.csv").write_text(aij_content, encoding="utf-8")

    # 5. Stack Overflow Survey (SRC-KAG-SO-01) -> Various exclusions + Valid + Duplicate
    so_dir = raw_dir / "SRC-KAG-SO-01"
    so_dir.mkdir(parents=True)
    so_content = (
        "ResponseId,Country,Employment,DevType,CompTotal,Currency,YearsCodePro\n"
        "1,Germany,Employed full-time,Developer,1000000,INR,5\n"  # EXC_GEO_OUT_OF_SCOPE
        "2,India,I am not primarily employed,Developer,1000000,INR,5\n"  # EXC_NON_FULLTIME
        "3,India,Employed full-time,Other (non-tech),1000000,INR,5\n"  # EXC_NON_TECH_OCCUPATION
        "4,India,Employed full-time,Developer,1000000,INR,NA\n"  # EXC_MISSING_EXPERIENCE
        "5,India,Employed full-time,Developer,2000000,INR,5\n"  # EXC_UNBUNDLED_CTC_OR_AGGREGATE
        "6,India,Employed full-time,Developer,2000000,INR,5\n"  # EXC_EXACT_OR_NEAR_DUPLICATE
    )
    (so_dir / "so_survey_2024_raw_sample.csv").write_text(so_content, encoding="utf-8")

    result = build_pt1_prototype(repo_root=tmp_path)

    # Total evaluated: 1 + 1 + 1 + 5 + 6 = 14
    assert result.total_evaluated == 14
    assert result.strict_pt1_count == 0
    assert result.exploratory_candidate_count == 2

    # R-DA-05: Exact zero discrepancy
    total_excluded = sum(result.exclusion_counts.values())
    assert result.total_evaluated == result.strict_pt1_count + total_excluded

    # Verify all 10 exclusion codes were exercised
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
    for code in expected_codes:
        assert result.exclusion_counts[code] > 0, f"Exclusion code {code} was not exercised"

    # Test artifact export on synthetic result
    data_dir = tmp_path / "data" / "processed"
    results_dir = tmp_path / "experiments" / "results"
    artifacts = export_prototype_artifacts(
        result, output_data_dir=data_dir, output_results_dir=results_dir
    )

    assert artifacts["strict_dataset"].exists()
    assert artifacts["exploratory_dataset"].exists()
    assert artifacts["quarantine_audit"].exists()
    assert artifacts["exclusion_report"].exists()

    strict_df = pl.read_parquet(artifacts["strict_dataset"])
    assert strict_df.height == 0
    assert "annual_pay_lpa" in strict_df.columns

    exp_df = pl.read_parquet(artifacts["exploratory_dataset"])
    assert exp_df.height == 2
    assert "annual_pay_lpa" in exp_df.columns
    assert exp_df["is_unbundled_aggregate"].all()

    quar_df = pl.read_parquet(artifacts["quarantine_audit"])
    assert quar_df.height == 14

    report_text = artifacts["exclusion_report"].read_text(encoding="utf-8")
    assert "Reconciliation Equation" in report_text
    assert "VERIFIED (0 discrepancy)" in report_text
    assert "Zero Strict Training Observations" in report_text


@pytest.mark.integration
def test_build_pt1_prototype_and_reconciliation_on_acquired_raw() -> None:
    """Verify prototype construction and exclusion accounting (R-DA-05) on acquired data."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    raw_so = repo_root / "data" / "raw" / "SRC-KAG-SO-01" / "so_survey_2024_raw_sample.csv"
    if not raw_so.exists():
        pytest.skip("Raw data not acquired in data/raw/ (gitignored per R-DA-08)")

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


@pytest.mark.integration
def test_export_prototype_artifacts_on_acquired_raw(tmp_path: Path) -> None:
    """Verify prototype artifacts are cleanly exported to disk from acquired raw data."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    raw_so = repo_root / "data" / "raw" / "SRC-KAG-SO-01" / "so_survey_2024_raw_sample.csv"
    if not raw_so.exists():
        pytest.skip("Raw data not acquired in data/raw/ (gitignored per R-DA-08)")

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
