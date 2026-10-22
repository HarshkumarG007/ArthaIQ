"""Unit tests for compintel.ingestion.manifest."""

from pathlib import Path

import pytest

from compintel.ingestion.manifest import (
    ChecksumMismatchError,
    LicenceGateError,
    generate_source_manifest,
    verify_licence_gate,
    verify_manifest,
)


@pytest.mark.unit
def test_licence_gate_blocks_rejected_source() -> None:
    """Verify that verify_licence_gate raises LicenceGateError for rejected source."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    with pytest.raises(LicenceGateError, match="status is 'rejected'"):
        verify_licence_gate("SRC-KAG-REJ-01", repo_root)


@pytest.mark.unit
def test_licence_gate_blocks_restricted_fixture() -> None:
    """Verify that verify_licence_gate raises LicenceGateError for restricted test fixture."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    with pytest.raises(LicenceGateError, match="status is 'restricted'"):
        verify_licence_gate("SRC-KAG-FIX-01", repo_root)


@pytest.mark.unit
def test_licence_gate_allows_approved_source() -> None:
    """Verify that verify_licence_gate passes for approved source."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    config = verify_licence_gate("SRC-IND-OFF-01", repo_root)
    assert config["ingestion_status"] == "approved"
    assert config["source_id"] == "SRC-IND-OFF-01"


@pytest.mark.unit
def test_manifest_generation_and_verification(tmp_path: Path) -> None:
    """Verify that generate_source_manifest computes sha256 and verify_manifest passes."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-IND-OFF-01"

    # Create dummy raw dir for the source
    source_raw_dir = tmp_path / source_id
    source_raw_dir.mkdir(parents=True)
    sample_file = source_raw_dir / "sample_data.csv"
    sample_file.write_text("id,val\n1,100\n2,200\n", encoding="utf-8")

    manifest_path = generate_source_manifest(
        source_id=source_id,
        raw_dir=tmp_path,
        repo_root=repo_root,
    )
    assert manifest_path.exists()
    assert verify_manifest(manifest_path) is True

    # Tamper with file to ensure checksum verification detects tampering
    sample_file.write_text("id,val\n1,999\n", encoding="utf-8")
    with pytest.raises(ChecksumMismatchError):
        verify_manifest(manifest_path)


@pytest.mark.integration
def test_all_acquired_raw_sources_manifests_valid() -> None:
    """Verify that every acquired source in data/raw/ has a valid, passing manifest.yaml."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_raw = repo_root / "data" / "raw"

    if not data_raw.exists():
        pytest.skip("data/raw/ directory does not exist (gitignored per R-DA-08)")

    manifest_files = list(data_raw.glob("*/manifest.yaml"))
    if not manifest_files:
        pytest.skip("No acquired raw sources in data/raw/ (gitignored per R-DA-08)")

    has_data_files = any(
        p.is_file() and p.name != "manifest.yaml" and not p.name.startswith(".")
        for p in data_raw.glob("*/*")
    )
    if not has_data_files:
        pytest.skip("Raw data files not present in data/raw/ (gitignored per R-DA-08)")

    assert len(manifest_files) >= 10, f"Expected >= 10 manifests, found {len(manifest_files)}"

    for mf in manifest_files:
        assert verify_manifest(mf) is True, f"Manifest verification failed for {mf}"
