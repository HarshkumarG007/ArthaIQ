"""Integration tests for canonical data reproduction pipeline (Task T3.13).

Governed by:
- Rule R-DA-01: Ingestion refuses unapproved sources.
- Rule R-DA-02: Lineage tracking (commit, config, manifests, schema).
- Rule R-DA-05: Count reconciliation (Total = Valid + Quarantined, Delta = 0).
- Rule R-DA-06: Deduplication before split.
- Rule R-DA-08: Data is gitignored; manifests are committed.
- ADR-0006: Deterministic snapshot identifier and idempotent clean runs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest
from scripts.reproduce_data import build_canonical_dataset

from compintel.schema.canonical import canonical_dataframe_schema


@pytest.fixture
def repo_root() -> Path:
    """Return repository root path."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def require_raw_manifests(repo_root: Path) -> None:
    """Require acquired raw source manifests to be present locally (R-DA-08)."""
    raw_dir = repo_root / "data" / "raw"
    if not raw_dir.exists() or not any(raw_dir.glob("*/manifest.yaml")):
        pytest.skip(
            "Local raw data store not present in clean checkout (Rule R-DA-08). "
            "Run 'make reproduce-data' locally."
        )


@pytest.fixture
def require_canonical_parquet(repo_root: Path) -> None:
    """Require canonical observations parquet to be present locally (R-DA-08)."""
    parquet_path = repo_root / "data" / "canonical" / "canonical_observations.parquet"
    if not parquet_path.exists():
        pytest.skip(
            "Canonical parquet store not present in clean checkout (Rule R-DA-08). "
            "Run 'make reproduce-data' locally."
        )


@pytest.fixture
def require_quarantine_parquet(repo_root: Path) -> None:
    """Require quarantine parquet to be present locally (R-DA-08)."""
    quar_path = repo_root / "data" / "quarantine" / "quarantine_records.parquet"
    if not quar_path.exists():
        pytest.skip(
            "Quarantine parquet store not present in clean checkout (Rule R-DA-08). "
            "Run 'make reproduce-data' locally."
        )


@pytest.mark.integration
def test_reproduce_data_idempotency_and_reconciliation(
    repo_root: Path, require_raw_manifests: None
) -> None:
    """Two clean runs produce identical snapshot and data hashes (ADR-0006, R-DA-05)."""
    run1 = build_canonical_dataset(repo_root=repo_root)
    run2 = build_canonical_dataset(repo_root=repo_root)

    # 1. Cryptographic and Lineage Invariants
    assert run1.snapshot_id == run2.snapshot_id, (
        f"Snapshot ID must be deterministic: {run1.snapshot_id} != {run2.snapshot_id}"
    )
    assert run1.manifest_hash == run2.manifest_hash, "Manifest hashes must match"
    assert run1.config_hash == run2.config_hash, "Config hashes must match"
    assert run1.data_hash == run2.data_hash, "Data content hashes must be bitwise identical"
    assert run1.git_commit == run2.git_commit, "Git commit must match"
    assert run1.schema_version == "1.0.0"

    # 2. Count Reconciliation Invariant (Rule R-DA-05: No silent drops)
    assert run1.reconciliation_delta == 0
    assert run2.reconciliation_delta == 0
    assert run1.total_records == run1.valid_records + run1.quarantined_records
    assert run1.valid_records == 5
    assert run1.quarantined_records == 660
    assert run1.total_records == 665

    # 3. Artifact Files Invariants
    assert run1.parquet_path.exists()
    assert run1.lineage_path.exists()

    snapshots_dir = repo_root / "data" / "canonical" / "snapshots"
    snapshot_parquet = snapshots_dir / f"{run1.snapshot_id}.parquet"
    snapshot_lineage = snapshots_dir / f"{run1.snapshot_id}_lineage.json"
    quarantine_parquet = repo_root / "data" / "quarantine" / "quarantine_records.parquet"

    assert snapshot_parquet.exists()
    assert snapshot_lineage.exists()
    assert quarantine_parquet.exists()


@pytest.mark.integration
def test_canonical_parquet_schema_and_contracts(
    repo_root: Path, require_canonical_parquet: None
) -> None:
    """Canonical observations parquet satisfies Pandera schema and quality contract invariants."""
    parquet_path = repo_root / "data" / "canonical" / "canonical_observations.parquet"
    assert parquet_path.exists(), "Canonical parquet file must exist"

    df = pl.read_parquet(parquet_path)
    assert df.height == 5

    # Bulk Pandera schema check
    validated_df = canonical_dataframe_schema.validate(df)
    assert validated_df.height == 5

    # Quality and provenance invariants
    assert "source_quality_score" in df.columns
    assert "provenance_tier" in df.columns
    assert "exact_duplicate_cluster_id" in df.columns
    assert "person_cluster_id" in df.columns
    assert "employer_cluster_id" in df.columns
    assert "posting_cluster_id" in df.columns

    # Every ground truth observation has guaranteed_cash_annual and passes hard gates
    assert df["guaranteed_cash_annual"].is_not_null().all()
    assert (df["guaranteed_cash_annual"] > 0.0).all()
    assert (df["provenance_tier"] == "A").all()
    assert (df["hard_gates_passed"] == True).all()  # noqa: E712
    assert (df["is_pt1_eligible"] == True).all()  # noqa: E712


@pytest.mark.integration
def test_quarantine_parquet_contracts(repo_root: Path, require_quarantine_parquet: None) -> None:
    """Quarantine store preserves full companion records with deterministic reason codes."""
    quar_path = repo_root / "data" / "quarantine" / "quarantine_records.parquet"
    assert quar_path.exists(), "Quarantine parquet file must exist"

    df = pl.read_parquet(quar_path)
    assert df.height == 660

    # Required columns
    assert "observation_id" in df.columns
    assert "source_id" in df.columns
    assert "source_record_id" in df.columns
    assert "quarantine_reason" in df.columns
    assert "quarantine_detail" in df.columns

    # Zero null reasons
    assert df["quarantine_reason"].is_not_null().all()
    assert df["source_id"].is_not_null().all()

    # Verify key quarantine reasons are represented
    reasons = set(df["quarantine_reason"].unique().to_list())
    assert "geo_out_of_scope" in reasons
    assert "unbundled_aggregate" in reasons
    assert "enterprise_aggregate" in reasons


@pytest.mark.integration
def test_reproduce_data_cli_execution(repo_root: Path, require_raw_manifests: None) -> None:
    """CLI execution with --verify-idempotence runs cleanly with exit code 0."""
    script_path = repo_root / "scripts" / "reproduce_data.py"
    cmd = [sys.executable, str(script_path), "--verify-idempotence"]

    res = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert res.returncode == 0, f"CLI command failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "Idempotency Verified!" in res.stdout
    assert "Delta = 0" in res.stdout
