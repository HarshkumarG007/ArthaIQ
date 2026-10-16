"""Integration tests for synthetic data generator and Rule R-MD-11 enforcement.

Verifies:
1. SyntheticDataGenerator produces schema-conforming canonical records with is_synthetic=True.
2. Core pipeline stages (normalization, dedup, SQSF, quarantine) run smoothly on synthetic data.
3. Rule R-MD-11 strictly blocks synthetic data from production metrics and quality reports.
4. CLI threshold verification halts on synthetic data inclusion.
"""

import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest
from tests.fixtures.synthetic import (
    generate_synthetic_observations_df,
    generate_synthetic_raw_records_df,
)

from compintel.errors import DataContractError
from compintel.normalization.levels import normalize_levels_df
from compintel.normalization.titles import normalize_titles_df
from compintel.quality.dedup import deduplicate_records_df
from compintel.quality.quarantine import partition_and_quarantine_df
from compintel.quality.report import (
    block_synthetic_from_metrics,
    generate_data_quality_report,
    validate_no_synthetic_data,
)
from compintel.quality.scoring import attach_source_quality_scores_df
from compintel.schema.canonical import validate_observations_df


@pytest.mark.synthetic
@pytest.mark.integration
def test_synthetic_data_generator_properties() -> None:
    """Verify synthetic data generator determinism, schema conformance, and R-MD-11 flagging."""
    # 1. Determinism with seed
    df1 = generate_synthetic_observations_df(n_records=50, seed=123)
    df2 = generate_synthetic_observations_df(n_records=50, seed=123)
    assert df1.equals(df2)

    # 2. Seed variability
    df3 = generate_synthetic_observations_df(n_records=50, seed=456)
    assert not df1.equals(df3)

    # 3. Rule R-MD-11: Every single record must have is_synthetic == True
    assert df1.height == 50
    assert df1.filter(pl.col("is_synthetic") == True).height == 50  # noqa: E712
    assert df1.filter(pl.col("is_synthetic") == False).height == 0  # noqa: E712

    # 4. Canonical Pandera schema compliance
    validated = validate_observations_df(df1)
    assert validated.height == 50
    assert "guaranteed_cash_annual" in validated.columns


@pytest.mark.synthetic
@pytest.mark.integration
def test_synthetic_raw_records_generator() -> None:
    """Verify raw intake generator produces typed intake records."""
    raw_df = generate_synthetic_raw_records_df(n_records=30, seed=99)
    assert raw_df.height == 30
    assert "submission_id" in raw_df.columns
    assert "base_pay_inr" in raw_df.columns
    assert raw_df.filter(pl.col("is_synthetic") == True).height == 30  # noqa: E712


@pytest.mark.synthetic
@pytest.mark.integration
def test_pipeline_plumbing_runs_on_synthetic_data() -> None:
    """Demonstrate that pipeline stages execute successfully on synthetic fixture data."""
    synth_df = generate_synthetic_observations_df(
        n_records=40,
        seed=42,
        inject_duplicates=5,
        inject_unbundled=3,
    )
    assert synth_df.height == 45  # 40 original + 5 injected duplicates

    # Stage 1: Title normalization
    title_norm_df = normalize_titles_df(synth_df)
    assert "canonical_title" in title_norm_df.columns
    assert "title_confidence" in title_norm_df.columns
    assert title_norm_df.height == 45

    # Stage 2: Level normalization
    level_norm_df, level_audit = normalize_levels_df(title_norm_df)
    assert "seniority" in level_norm_df.columns
    assert "level_confidence" in level_norm_df.columns
    assert level_norm_df.height == 45
    assert level_audit.total_records == 45

    # Stage 3: Deduplication and clustering
    dedup_df = deduplicate_records_df(level_norm_df)
    assert dedup_df.height == 45
    assert dedup_df.filter(pl.col("is_exact_duplicate") == True).height >= 5  # noqa: E712
    assert "exact_duplicate_cluster_id" in dedup_df.columns
    assert "person_cluster_id" in dedup_df.columns
    assert "employer_cluster_id" in dedup_df.columns
    assert "posting_cluster_id" in dedup_df.columns

    # Stage 4: Source Quality Scoring (SQSF)
    scored_df = attach_source_quality_scores_df(dedup_df)
    assert "source_quality_score" in scored_df.columns
    assert "provenance_tier" in scored_df.columns
    assert "hard_gates_passed" in scored_df.columns

    # Stage 5: Quarantine partitioning
    quar_result = partition_and_quarantine_df(scored_df)
    assert quar_result.report.is_reconciled is True
    assert quar_result.report.discrepancy_count == 0
    # Injected unbundled rows must be quarantined under R-MD-07
    assert quar_result.quarantined_df.height >= 3


@pytest.mark.synthetic
@pytest.mark.integration
def test_synthetic_data_blocked_from_metrics_and_reports() -> None:
    """Rule R-MD-11: Metrics from synthetic data MUST NOT be reported as production performance."""
    synth_df = generate_synthetic_observations_df(n_records=20, seed=77)
    empty_quar = pl.DataFrame(
        {
            "record_id": pl.Series([], dtype=pl.String),
            "source_id": pl.Series([], dtype=pl.String),
            "quarantine_reason": pl.Series([], dtype=pl.String),
            "raw_payload": pl.Series([], dtype=pl.String),
            "quarantined_at": pl.Series([], dtype=pl.Datetime),
        }
    )

    # 1. validate_no_synthetic_data must raise DataContractError
    with pytest.raises(DataContractError) as exc_info:
        validate_no_synthetic_data(synth_df, context="model evaluation")

    assert exc_info.value.code == "SYNTHETIC_DATA_PROHIBITED"
    assert "Rule R-MD-11" in exc_info.value.message

    # 2. block_synthetic_from_metrics must strip all synthetic records
    sanitized_df = block_synthetic_from_metrics(synth_df)
    assert sanitized_df.height == 0

    # 3. generate_data_quality_report must fail synthetic_isolation_contract
    report = generate_data_quality_report(
        canonical_df=synth_df,
        quarantine_df=empty_quar,
    )
    assert report.synthetic_records_count == 20
    assert report.synthetic_isolation_passed is False
    assert report.contract_checks["synthetic_isolation_contract"] is False
    assert report.overall_status == "FAILED"

    # 4. Markdown audit must contain prominent R-MD-11 warning banner
    md_output = report.to_markdown()
    assert "Rule R-MD-11 Violation" in md_output
    assert "synthetic fixture records detected" in md_output
    assert "**FAILED**" in md_output


@pytest.mark.synthetic
@pytest.mark.integration
def test_cli_threshold_verification_fails_on_synthetic_data(tmp_path: Path) -> None:
    """CLI execution with --verify-thresholds must fail when synthetic data is present."""
    canon_p = tmp_path / "canonical.parquet"
    quar_p = tmp_path / "quarantine.parquet"
    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    # Write synthetic dataset
    synth_df = generate_synthetic_observations_df(n_records=15, seed=101)
    synth_df.write_parquet(canon_p)

    empty_quar = pl.DataFrame(
        {
            "record_id": pl.Series([], dtype=pl.String),
            "source_id": pl.Series([], dtype=pl.String),
            "quarantine_reason": pl.Series([], dtype=pl.String),
            "raw_payload": pl.Series([], dtype=pl.String),
            "quarantined_at": pl.Series([], dtype=pl.Datetime),
        }
    )
    empty_quar.write_parquet(quar_p)

    repo_root = Path(__file__).resolve().parent.parent.parent
    script_path = repo_root / "scripts" / "generate_data_quality_report.py"

    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--canonical-path",
            str(canon_p),
            "--quarantine-path",
            str(quar_p),
            "--output-md",
            str(out_md),
            "--output-json",
            str(out_json),
            "--verify-thresholds",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # Must exit with code 1 due to failed synthetic_isolation_contract
    assert proc.returncode == 1
    assert "synthetic_isolation_contract" in proc.stderr or "failed" in proc.stderr.lower()
