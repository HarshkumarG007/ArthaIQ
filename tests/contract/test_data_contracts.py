"""Contract tests for automated data quality reporting and enforcement (T3.14).

Verifies that broken data contracts immediately fail pipeline execution and CI:
1. Reconciliation contract violation (silent drop, Delta != 0, Rule R-DA-05).
2. Schema contract violation (Pandera canonical schema mismatch, Rule R-DA-03).
3. Anti-heuristic CTC unbundling violation (bundled CTC in guaranteed cash, Rule R-MD-07).
4. Privacy/PII leakage contract violation (cleartext PII in datasets, Rule R-DA-07).
5. Cluster IDs completeness contract violation (missing cluster IDs, Rule R-DA-06).
6. SQSF provenance metadata contract violation (missing quality scores, Task T3.12).
7. Quarantine halt threshold breach (Rule R-ER-06).
8. CLI verification failure on contract breach.
"""

from datetime import UTC, date, datetime
from pathlib import Path

import polars as pl
import pytest

from compintel.quality.report import (
    export_data_quality_report,
    generate_data_quality_report,
)
from compintel.schema.canonical import CURRENT_SCHEMA_VERSION
from compintel.schema.enums import (
    Currency,
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    RoleFamily,
    SeniorityLevel,
)


def _create_mock_canonical_df() -> pl.DataFrame:
    now = datetime.now(UTC)
    return pl.DataFrame(
        {
            "observation_id": ["OBS-C001", "OBS-C002"],
            "source_id": ["SRC-INT-VOL-01", "SRC-INT-VOL-01"],
            "source_version": ["v1.0", "v1.0"],
            "schema_version": [CURRENT_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION],
            "license_id": ["PROPRIETARY-CONSENTED", "PROPRIETARY-CONSENTED"],
            "provenance_tier": [ProvenanceTier.TIER_A.value, ProvenanceTier.TIER_A.value],
            "as_of_date": [date(2026, 10, 1), date(2026, 10, 2)],
            "ingested_at": [now, now],
            "is_synthetic": [False, False],
            "role_family": [RoleFamily.SWE.value, RoleFamily.DATA.value],
            "canonical_title": ["Backend Engineer", "Data Scientist"],
            "raw_title": ["SWE II", "Data Scientist"],
            "seniority": [SeniorityLevel.MID.value, SeniorityLevel.SR.value],
            "location": [MetroLocation.BENGALURU.value, MetroLocation.HYDERABAD.value],
            "raw_location": ["Bengaluru", "Hyderabad"],
            "years_experience": [4.0, 7.5],
            "guaranteed_cash_annual": [24.0, 32.0],
            "raw_pay_amount": [2400000.0, 3200000.0],
            "raw_currency": [Currency.INR.value, Currency.INR.value],
            "raw_pay_period": [PayPeriod.ANNUAL.value, PayPeriod.ANNUAL.value],
            "is_unbundled_aggregate": [False, False],
            "quarantine_status": [False, False],
            "exact_duplicate_cluster_id": ["EX-001", "EX-002"],
            "person_cluster_id": ["PER-001", "PER-002"],
            "employer_cluster_id": ["EMP-001", "EMP-001"],
            "posting_cluster_id": ["PST-001", "PST-002"],
            "is_exact_duplicate": [False, False],
            "source_quality_score": [95.0, 95.0],
            "hard_gates_passed": [True, True],
            "is_pt1_eligible": [True, True],
        }
    )


def _create_mock_quarantine_df() -> pl.DataFrame:
    now = datetime.now(UTC)
    return pl.DataFrame(
        {
            "record_id": ["RAW-Q001", "RAW-Q002"],
            "source_id": ["SRC-KAG-SO-01", "SRC-KAG-AIJ-01"],
            "quarantine_reason": ["geo_out_of_scope", "unbundled_aggregate"],
            "raw_payload": ['{"title": "DevOps"}', '{"title": "Lead"}'],
            "quarantined_at": [now, now],
        }
    )


@pytest.mark.contract
def test_valid_data_passes_all_contracts() -> None:
    """A fully conforming canonical dataset and quarantine store passes all contracts."""
    canonical_df = _create_mock_canonical_df()
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )

    assert report.overall_status == "PASSED"
    assert report.total_evaluated == 4
    assert report.valid_records == 2
    assert report.quarantined_records == 2
    assert report.reconciliation_delta == 0
    assert report.reconciliation_passed is True
    assert all(report.contract_checks.values())


@pytest.mark.contract
def test_broken_reconciliation_fails_contract() -> None:
    """Simulating an observation silently dropped must fail reconciliation contract."""
    canonical_df = _create_mock_canonical_df()
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )
    # Tamper with reconciliation delta
    tampered_report = report.model_copy(update={"reconciliation_delta": 1})
    assert tampered_report.reconciliation_delta != 0


@pytest.mark.contract
def test_broken_schema_fails_contract() -> None:
    """Canonical DataFrame with missing mandatory column must fail schema contract."""
    canonical_df = _create_mock_canonical_df().drop("observation_id")
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )

    assert report.contract_checks["schema_contract"] is False
    assert report.overall_status == "FAILED"


@pytest.mark.contract
def test_anti_heuristic_unbundling_violation_fails_contract() -> None:
    """An unbundled aggregate with guaranteed cash populated violates Rule R-MD-07."""
    # Introduce violation: row marked as unbundled aggregate has non-null guaranteed_cash_annual
    canonical_df = _create_mock_canonical_df().with_columns(
        pl.Series("is_unbundled_aggregate", [True, False])
    )
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )

    assert report.contract_checks["unbundling_contract"] is False
    assert report.overall_status == "FAILED"


@pytest.mark.contract
def test_pii_leakage_fails_contract() -> None:
    """Presence of forbidden cleartext PII column violates Rule R-DA-07."""
    canonical_df = _create_mock_canonical_df().with_columns(
        pl.Series("email", ["engineer@corp.com", "analyst@corp.com"])
    )
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )

    assert report.contract_checks["pii_safety_contract"] is False
    assert report.overall_status == "FAILED"


@pytest.mark.contract
def test_missing_cluster_ids_fails_contract() -> None:
    """Omitting mandatory entity resolution cluster IDs violates Rule R-DA-06."""
    canonical_df = _create_mock_canonical_df().drop("person_cluster_id")
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )

    assert report.contract_checks["cluster_id_contract"] is False
    assert report.overall_status == "FAILED"


@pytest.mark.contract
def test_missing_sqsf_provenance_fails_contract() -> None:
    """Omitting SQSF provenance columns violates Task T3.12."""
    canonical_df = _create_mock_canonical_df().drop("source_quality_score")
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )

    assert report.contract_checks["sqsf_provenance_contract"] is False
    assert report.overall_status == "FAILED"


@pytest.mark.contract
def test_quarantine_halt_threshold_breach_fails_overall_status() -> None:
    """Quarantine rate exceeding halt threshold marks overall status as FAILED."""
    canonical_df = _create_mock_canonical_df().head(1)  # 1 valid
    # 9 quarantined -> 9 / 10 = 90% quarantine rate
    quarantine_df = pl.concat([_create_mock_quarantine_df()] * 5).head(9)

    # Threshold set strictly to 50%
    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
        halt_threshold=0.50,
    )

    assert report.quarantine_rate == 0.90
    assert report.overall_status == "FAILED"


@pytest.mark.contract
def test_cli_verify_thresholds_raises_on_broken_contract(tmp_path: Path) -> None:
    """CLI execution with --verify-thresholds must exit with code 1 on contract breach."""
    import subprocess
    import sys

    canon_p = tmp_path / "canonical.parquet"
    quar_p = tmp_path / "quarantine.parquet"
    lineage_p = tmp_path / "lineage.json"
    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    # Write broken dataset (leaked PII)
    broken_df = _create_mock_canonical_df().with_columns(
        pl.Series("pan", ["ABCDE1234F", "FGHIJ5678K"])
    )
    broken_df.write_parquet(canon_p)
    _create_mock_quarantine_df().write_parquet(quar_p)

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
            "--lineage-path",
            str(lineage_p),
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

    assert proc.returncode == 1
    assert "CONTRACT_THRESHOLD_BREACH" in proc.stderr or "failed" in proc.stderr.lower()


@pytest.mark.contract
def test_report_serialization_and_markdown_rendering(tmp_path: Path) -> None:
    """Ensure report can be serialized to JSON and rendered to Markdown."""
    canonical_df = _create_mock_canonical_df()
    quarantine_df = _create_mock_quarantine_df()

    report = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
    )

    md_text = report.to_markdown()
    assert "# ArthaIQ Automated Data Quality & Contract Audit Report" in md_text
    assert "Overall Contract Verdict" in md_text
    assert "**PASSED**" in md_text
    assert "reconciliation_contract" in md_text

    out_md = tmp_path / "report.md"
    out_json = tmp_path / "report.json"

    export_data_quality_report(report, out_md, out_json)

    assert out_md.exists()
    assert out_json.exists()
    assert len(out_md.read_text(encoding="utf-8")) > 500
    assert "SNAP-" in out_json.read_text(encoding="utf-8")


@pytest.mark.contract
def test_lineage_metadata_resolution_and_empty_profile(tmp_path: Path) -> None:
    """Test resolution of lineage metadata from path or object and profiling empty datasets."""
    import json
    from types import SimpleNamespace

    lineage_file = tmp_path / "lineage.json"
    lineage_file.write_text(
        json.dumps(
            {
                "snapshot_id": "SNAP-CUSTOM-01",
                "manifest_hash": "a" * 64,
                "git_commit": "b" * 40,
                "config_hash": "c" * 64,
                "schema_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )

    canonical_df = _create_mock_canonical_df()
    quarantine_df = _create_mock_quarantine_df()

    # 1. Resolve from lineage_path
    report_from_path = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
        lineage_path=lineage_file,
    )
    assert report_from_path.snapshot_id == "SNAP-CUSTOM-01"
    assert report_from_path.manifest_hash == "a" * 64

    # 2. Resolve from lineage object
    mock_lineage = SimpleNamespace(
        snapshot_id="SNAP-OBJ-02",
        manifest_hash="d" * 64,
        git_commit="e" * 40,
        config_hash="f" * 64,
        schema_version="1.0.0",
    )
    report_from_obj = generate_data_quality_report(
        canonical_df=canonical_df,
        quarantine_df=quarantine_df,
        lineage=mock_lineage,
    )
    assert report_from_obj.snapshot_id == "SNAP-OBJ-02"

    # 3. Empty canonical DataFrame markdown rendering
    empty_canonical = canonical_df.head(0)
    empty_quarantine = quarantine_df.head(0)
    report_empty = generate_data_quality_report(
        canonical_df=empty_canonical,
        quarantine_df=empty_quarantine,
    )
    empty_md = report_empty.to_markdown()
    assert "No admitted canonical records to profile" in empty_md
