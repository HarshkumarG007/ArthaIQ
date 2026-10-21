"""Unit tests for Fairness Audit v2 and Final Model Card (T9.17).

Adheres to:
- PRD Section 8 NFR-09 & Section 13 (Fairness & Legal).
- Rules R-FA-01..04, R-MD-01, R-MD-02, R-MD-05, R-MD-08, R-MD-11, R-MD-12, R-MD-13,
  R-UQ-01, R-UQ-05, R-DA-10.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_fairness_audit_v2 import generate_benchmark_data
from scripts.run_fairness_audit_v2 import main as run_fairness_v2_main

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.fairness_audit_v2 import (
    FairnessAuditReportV2,
    FairnessVerdict,
    SliceDimension,
    assign_experience_band_v2,
    assign_geo_tier_v2,
    evaluate_fairness_audit_v2,
    format_markdown_report_v2,
    scan_demographic_proxies,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_scan_demographic_proxies() -> None:
    """Verify demographic proxy scanner identifies prohibited columns and passes clean features."""
    clean_cols = ["role_family", "years_experience", "seniority", "location", "employer_tier"]
    is_compliant, prohibited = scan_demographic_proxies(clean_cols)
    assert is_compliant is True
    assert prohibited == []

    tainted_cols = ["role_family", "gender_user", "caste_category", "religion_code"]
    is_compliant, prohibited = scan_demographic_proxies(tainted_cols)
    assert is_compliant is False
    assert len(prohibited) == 3
    assert "gender_user" in prohibited
    assert "caste_category" in prohibited
    assert "religion_code" in prohibited


def test_assign_geo_and_experience_bands() -> None:
    """Verify geographic mapping and experience band assignment."""
    assert assign_geo_tier_v2("Bengaluru") == "Metro_Bengaluru"
    assert assign_geo_tier_v2("BANGALORE") == "Metro_Bengaluru"
    assert assign_geo_tier_v2("GURGAON") == "Metro_NCR"
    assert assign_geo_tier_v2("PUNE") == "Metro_Pune"
    assert assign_geo_tier_v2("UNKNOWN_CITY") == "Metro_Other"
    assert assign_geo_tier_v2(None) == "Metro_Other"

    assert assign_experience_band_v2(1.0) == "Entry (0-2y)"
    assert assign_experience_band_v2(4.0) == "Mid (3-5y)"
    assert assign_experience_band_v2(8.0) == "Senior (6-10y)"
    assert assign_experience_band_v2(12.0) == "Staff (11-15y)"
    assert assign_experience_band_v2(18.0) == "Principal (16+y)"
    assert assign_experience_band_v2(-1.0) == "Unknown"
    assert assign_experience_band_v2(None) == "Unknown"


def test_evaluate_fairness_audit_v2_execution() -> None:
    """Verify end-to-end execution of fairness audit v2 engine."""
    df, y_true, p10, p50, p90 = generate_benchmark_data(n_rows=180, seed=42)

    report = evaluate_fairness_audit_v2(
        df=df,
        y_true=y_true,
        p10=p10,
        p50=p50,
        p90=p90,
        eval_split_name="select",
        model_version="1.0.0",
        n_resamples=100,
        seed=42,
    )

    assert isinstance(report, FairnessAuditReportV2)
    assert report.total_observations == 180
    assert report.demographic_proxy_compliant is True
    assert report.overall_verdict in (
        FairnessVerdict.PASS_ALL,
        FairnessVerdict.WARN_GAPS,
    )
    assert len(report.slice_audits) == 4

    dims = [a.dimension for a in report.slice_audits]
    assert SliceDimension.GEOGRAPHIC in dims
    assert SliceDimension.EXPERIENCE_BAND in dims
    assert SliceDimension.ROLE_FAMILY in dims
    assert SliceDimension.EMPLOYER_TIER in dims

    # Verify monotonic non-crossing
    assert report.global_crossing_rate == 0.0


def test_test_partition_lock_enforced() -> None:
    """Verify that evaluation on locked 'test' split raises DataContractError per R-MD-02."""
    df, y_true, p10, p50, p90 = generate_benchmark_data(n_rows=20, seed=42)

    with pytest.raises(DataContractError, match="prohibited by Rule R-MD-02"):
        evaluate_fairness_audit_v2(
            df=df,
            y_true=y_true,
            p10=p10,
            p50=p50,
            p90=p90,
            eval_split_name="test",
        )


def test_empty_observations_validation() -> None:
    """Verify that empty inputs raise validation error."""
    df = pl.DataFrame({"role_family": []})
    empty_arr = np.array([])

    with pytest.raises(CompIntelValidationError, match="empty observations"):
        evaluate_fairness_audit_v2(
            df=df,
            y_true=empty_arr,
            p10=empty_arr,
            p50=empty_arr,
            p90=empty_arr,
        )


def test_format_markdown_report_v2() -> None:
    """Verify that markdown report contains all mandatory sections and disclosures."""
    df, y_true, p10, p50, p90 = generate_benchmark_data(n_rows=50, seed=42)

    report = evaluate_fairness_audit_v2(
        df=df,
        y_true=y_true,
        p10=p10,
        p50=p50,
        p90=p90,
        n_resamples=50,
        seed=42,
    )

    md = format_markdown_report_v2(report)
    assert "# Fairness Audit v2: Subgroup Parity & Calibration Report" in md
    assert "Demographic Proxy Compliance Scan" in md
    assert "Subgroup Prediction Parity by Dimension" in md
    assert "Fairness Review Sign-Off" in md
    assert "COMPLIANT" in md


def test_final_model_card_completeness() -> None:
    """Verify that docs/model-cards/model-card-final-v1.md contains all required sections."""
    card_path = REPO_ROOT / "docs" / "model-cards" / "model-card-final-v1.md"
    assert card_path.exists(), "Final model card does not exist"

    content = card_path.read_text(encoding="utf-8")
    assert "ArthaIQ Production Champion Model Card" in content
    assert "Rung F (Champion)" in content
    assert "guaranteed_cash_annual" in content
    assert "Candidate Screening & Ranking" in content
    assert "Compare-Only Current Pay Quarantine" in content
    assert "feat_l3_current_guaranteed_cash" in content
    assert "Fairness Audit v2" in content
    assert "k_{\\min} \\ge 5" in content or "k_min" in content
    assert "RATIFIED (GO)" in content


def test_cli_runner_fairness_audit_v2(tmp_path: Path) -> None:
    """Verify CLI runner executes with options and writes reports."""
    out_md = tmp_path / "fairness_v2.md"
    out_json = tmp_path / "fairness_v2.json"

    test_args = [
        "scripts/run_fairness_audit_v2.py",
        "--canonical-path",
        str(tmp_path / "nonexistent.parquet"),
        "--output-md",
        str(out_md),
        "--output-json",
        str(out_json),
        "--n-resamples",
        "50",
        "--allow-synthetic",
    ]

    with patch("sys.argv", test_args):
        ret = run_fairness_v2_main()
        assert ret == 0

    assert out_md.exists()
    assert out_json.exists()
    assert len(out_md.read_text(encoding="utf-8")) > 500
