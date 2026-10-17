"""Unit tests for leakage and duplicate-inflation audit engine (Task T4.06, EXP-12).

Governed by:
- Rule R-MD-01: Grouped-temporal split hierarchy; random i.i.d. splits prohibited.
- Rule R-MD-02: Isolated final test set; audits operate strictly on dev partitions.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead.
- Rule R-MD-04: Adversarial leak detection and leakage audits.
- Rule R-MD-11: Synthetic data flagged and blocked from production benchmark reports.
- Rule R-UQ-01: Uncertainty quantification; no lone numbers.
- Experiment EXP-12: Measure the random-versus-grouped-temporal performance inflation gap.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
from tests.fixtures.synthetic import generate_synthetic_observations_df

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.inflation import (
    LeakageInflationAuditor,
    LeakageInflationConfig,
    LeakageInflationReport,
    run_leakage_inflation_audit,
)


@pytest.fixture
def repo_root() -> Path:
    """Return repository root path."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def sample_audit_df() -> pl.DataFrame:
    """Create a realistic, deterministic 100-record dataset for testing audit logic."""
    df = generate_synthetic_observations_df(n_records=100, seed=42)
    # Give observations spaced dates and partially overlapping person clusters
    dates = [date(2025, 1, 1) + timedelta(days=i * 3) for i in range(100)]
    # First 80 have unique person IDs; last 20 reuse some earlier person IDs to test overlap
    persons = [f"PER-{i:04d}" for i in range(80)] + [f"PER-{i % 40:04d}" for i in range(20)]
    return df.with_columns(
        [
            pl.Series("as_of_date", dates),
            pl.Series("person_cluster_id", persons),
        ]
    )


def test_leakage_inflation_config_validation() -> None:
    """Verify configuration ratio validation and default settings."""
    cfg = LeakageInflationConfig()
    assert cfg.train_ratio == 0.60
    assert cfg.select_ratio == 0.15
    assert cfg.calibrate_ratio == 0.15
    assert cfg.test_ratio == 0.10
    assert cfg.random_seed == 42
    assert cfg.allow_synthetic is False

    # Invalid ratios not summing to 1.0
    with pytest.raises(CompIntelValidationError) as exc:
        LeakageInflationConfig(train_ratio=0.50, select_ratio=0.10)
    assert exc.value.code == "INVALID_SPLIT_RATIOS"


def test_synthetic_data_isolation_guard_rule_r_md_11(sample_audit_df: pl.DataFrame) -> None:
    """Rule R-MD-11: Synthetic records are blocked by default unless allow_synthetic=True."""
    auditor_default = LeakageInflationAuditor()
    with pytest.raises(DataContractError) as exc:
        auditor_default.audit(sample_audit_df)
    assert exc.value.code == "SYNTHETIC_DATA_BLOCKED"

    # With allow_synthetic=True, succeeds and marks fixture flag
    auditor_allowed = LeakageInflationAuditor(LeakageInflationConfig(allow_synthetic=True))
    report = auditor_allowed.audit(sample_audit_df, snapshot_id="SNAP-TEST-SYN")
    assert report.is_synthetic_fixture is True
    assert "YES (TEST ONLY)" in report.to_markdown()


def test_schema_validation_and_missing_columns(sample_audit_df: pl.DataFrame) -> None:
    """Audit halts with validation error on missing required columns or empty dataset."""
    auditor = LeakageInflationAuditor(LeakageInflationConfig(allow_synthetic=True))

    # Missing person_cluster_id
    dropped_df = sample_audit_df.drop("person_cluster_id")
    with pytest.raises(CompIntelValidationError) as exc:
        auditor.audit(dropped_df)
    assert exc.value.code == "MISSING_COLUMNS"

    # Empty DataFrame
    empty_df = sample_audit_df.clear()
    with pytest.raises(CompIntelValidationError) as exc2:
        auditor.audit(empty_df)
    assert exc2.value.code == "EMPTY_DATASET"


def test_overlap_diagnostics_calculation() -> None:
    """Verify hand-computed entity cluster overlap and temporal lookahead counts."""
    auditor = LeakageInflationAuditor(LeakageInflationConfig(allow_synthetic=True))

    train_df = pl.DataFrame(
        {
            "observation_id": ["O1", "O2", "O3"],
            "person_cluster_id": ["P1", "P2", "P3"],
            "exact_duplicate_cluster_id": ["D1", "D2", "D3"],
            "as_of_date": [date(2025, 1, 1), date(2025, 1, 10), date(2025, 1, 20)],
        }
    )

    # Dev shares P2 and D2, and has an observation dated earlier than max train date
    dev_df = pl.DataFrame(
        {
            "observation_id": ["O4", "O5"],
            "person_cluster_id": ["P2", "P4"],
            "exact_duplicate_cluster_id": ["D2", "D4"],
            "as_of_date": [date(2025, 1, 15), date(2025, 1, 25)],
        }
    )

    diag = auditor._compute_overlap_diagnostics(
        protocol_name="Test Protocol",
        train_df=train_df,
        dev_df=dev_df,
    )

    assert diag.total_train_records == 3
    assert diag.total_dev_records == 2
    assert diag.total_train_persons == 3
    assert diag.total_dev_persons == 2
    assert diag.person_cluster_overlap_count == 1  # P2
    assert diag.person_cluster_leak_records == 1  # O4 has P2
    assert diag.person_cluster_leak_rate == 50.0  # 1/2 * 100
    assert diag.exact_duplicate_overlap_count == 1  # D2
    # Train O3 is dated 2025-01-20, which is after dev min date 2025-01-15
    assert diag.temporal_lookahead_violation_count == 1
    assert diag.max_train_date == "2025-01-20"
    assert diag.min_dev_date == "2025-01-15"
    assert diag.is_leakage_free is False


def test_end_to_end_audit_and_report_generation(sample_audit_df: pl.DataFrame) -> None:
    """Verify complete audit run comparing Grouped-Temporal (B) and Random (A) protocols."""
    config = LeakageInflationConfig(
        random_seed=42,
        allow_synthetic=True,
    )

    report = run_leakage_inflation_audit(
        df=sample_audit_df,
        config=config,
        snapshot_id="SNAP-SYNTHETIC-AUDIT",
    )

    assert isinstance(report, LeakageInflationReport)
    assert report.snapshot_id == "SNAP-SYNTHETIC-AUDIT"
    assert report.total_observations_analyzed == 100
    assert report.dev_pool_size > 0

    # Grouped-temporal integrity: zero person overlap, zero temporal violations
    assert report.grouped_temporal_diagnostics.person_cluster_overlap_count == 0
    assert report.grouped_temporal_diagnostics.temporal_lookahead_violation_count == 0
    assert report.grouped_temporal_diagnostics.is_leakage_free is True

    # Both baseline models evaluated
    assert "rung_a_empirical" in report.model_results
    assert "rung_b_linear" in report.model_results

    rung_a = report.model_results["rung_a_empirical"]
    rung_b = report.model_results["rung_b_linear"]

    assert rung_a.model_name == "Rung A: Empirical Conditional Quantiles (Hierarchical Backoff)"
    assert rung_b.model_name == "Rung B: Regularized Linear Quantile Regression (Log Pay)"

    # Markdown export includes all required sections
    md = report.to_markdown()
    assert "# Leakage and Duplicate-Inflation Audit (EXP-12)" in md
    assert "## 1. Audit Metadata" in md
    assert "## 2. Leakage and Overlap Diagnostics" in md
    assert "## 3. Baseline Model Performance Inflation (EXP-12)" in md
    assert "## 4. Key Findings and Diagnostic Implications" in md
    assert len(report.key_findings) >= 1


def test_report_json_and_markdown_persistence(
    sample_audit_df: pl.DataFrame, tmp_path: Path
) -> None:
    """Verify report serialization to JSON and Markdown file artifacts."""
    config = LeakageInflationConfig(allow_synthetic=True)
    report = run_leakage_inflation_audit(df=sample_audit_df, config=config)

    json_path = tmp_path / "audit.json"
    md_path = tmp_path / "audit.md"

    report.save_json(json_path)
    report.save_markdown(md_path)

    assert json_path.exists()
    assert md_path.exists()

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["report_id"] == report.report_id
    assert "grouped_temporal_diagnostics" in data
    assert "random_diagnostics" in data
    assert "model_results" in data

    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    assert report.report_id in md_text


def test_run_leakage_audit_cli_execution(repo_root: Path, tmp_path: Path) -> None:
    """Verify scripts/run_leakage_audit.py runs cleanly as a CLI script."""
    canonical_parquet = repo_root / "data" / "canonical" / "canonical_observations.parquet"
    if not canonical_parquet.exists():
        pytest.skip("Canonical observations parquet not present in clean checkout (Rule R-DA-08).")

    script_path = repo_root / "scripts" / "run_leakage_audit.py"
    out_json = tmp_path / "audit.json"
    out_md = tmp_path / "audit.md"
    cmd = [
        sys.executable,
        str(script_path),
        "--seed",
        "42",
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]

    res = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert res.returncode == 0, f"CLI command failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "Leakage and Duplicate-Inflation Audit (EXP-12)" in res.stdout
    assert "Saved JSON audit report" in res.stderr or "Saved JSON audit report" in res.stdout


def test_thin_evidence_abstention_handling(sample_audit_df: pl.DataFrame) -> None:
    """When models abstain on all dev records, comparisons are empty and note is rendered."""
    # Using 4 records forces sample size < 5, triggering 100% abstention on Rung A
    tiny_df = sample_audit_df.head(4)
    auditor = LeakageInflationAuditor(
        LeakageInflationConfig(
            allow_synthetic=True,
            train_ratio=0.60,
            select_ratio=0.15,
            calibrate_ratio=0.15,
            test_ratio=0.10,
        )
    )
    report = auditor.audit(tiny_df, snapshot_id="SNAP-TINY")
    md = report.to_markdown()
    assert "Thin evidence per Rule R-MD-08" in md
    assert report.model_results["rung_a_empirical"].comparisons == []


def test_edge_case_helpers_and_empty_preds() -> None:
    """Verify internal helpers handle None and empty inputs cleanly."""
    auditor = LeakageInflationAuditor(LeakageInflationConfig(allow_synthetic=True))

    empty_df = pl.DataFrame()
    rep, rate = auditor._compute_metrics_from_preds(empty_df, None)
    assert rep is None
    assert rate == 0.0

    comps = auditor._compute_comparisons(None, None)
    assert comps == []
