"""Manifest and licence-gate verification for raw data ingestion.

Governs Rule R-DA-01 (Licence gate) and R-DA-02 (Immutable raw zone with lineage).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


class LicenceGateError(PermissionError):
    """Raised when an attempt is made to ingest an unapproved or rejected data source."""


class ChecksumMismatchError(ValueError):
    """Raised when an existing raw file does not match its recorded manifest hash."""


def compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hex digest of a file in streaming chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_licence_gate(source_id: str, repo_root: Path) -> dict[str, Any]:
    """Verify that a source configuration exists and its status is 'approved'.

    Raises LicenceGateError if the source is rejected, restricted, or unapproved.
    """
    config_path = repo_root / "config" / "sources" / f"{source_id}.yaml"
    if not config_path.exists():
        msg = f"Licence configuration not found for source {source_id} at {config_path}"
        raise LicenceGateError(msg)

    with open(config_path, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    status = config_data.get("ingestion_status")
    if status != "approved":
        msg = f"Source {source_id} blocked by R-DA-01: status is '{status}', not 'approved'."
        raise LicenceGateError(msg)

    return config_data


def generate_source_manifest(
    source_id: str,
    raw_dir: Path,
    repo_root: Path,
    metadata_overrides: dict[str, Any] | None = None,
) -> Path:
    """Generate and write manifest.yaml inside data/raw/<source_id>/ for an approved source.

    Computes SHA-256 hashes, file sizes, and records the licence ID and retrieval timestamp.
    """
    source_config = verify_licence_gate(source_id, repo_root)

    source_raw_dir = raw_dir / source_id
    if not source_raw_dir.exists():
        msg = f"Raw directory does not exist: {source_raw_dir}"
        raise FileNotFoundError(msg)

    files_manifest: list[dict[str, Any]] = []
    for p in sorted(source_raw_dir.glob("*")):
        if p.name == "manifest.yaml" or p.is_dir():
            continue
        sha256 = compute_sha256(p)
        files_manifest.append(
            {
                "file_name": p.name,
                "file_size_bytes": p.stat().st_size,
                "sha256": sha256,
            }
        )

    licence_meta = source_config.get("licence", {})
    manifest_data: dict[str, Any] = {
        "source_id": source_id,
        "source_short_name": source_config.get("short_name"),
        "licence_id": licence_meta.get("spdx_id"),
        "licence_name": licence_meta.get("name"),
        "licence_status": source_config.get("ingestion_status"),
        "sqs": source_config.get("sqs"),
        "sqsf_tier": source_config.get("sqsf_tier"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "immutable": True,
        "files": files_manifest,
    }

    if metadata_overrides:
        manifest_data.update(metadata_overrides)

    manifest_path = source_raw_dir / "manifest.yaml"
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest_data, f, sort_keys=False)

    return manifest_path


def verify_manifest(manifest_path: Path) -> bool:
    """Verify that all files listed in a manifest exist and match their SHA-256 hashes."""
    if not manifest_path.exists():
        msg = f"Manifest not found: {manifest_path}"
        raise FileNotFoundError(msg)

    with open(manifest_path, encoding="utf-8") as f:
        manifest_data = yaml.safe_load(f)

    source_dir = manifest_path.parent
    for file_entry in manifest_data.get("files", []):
        file_name = file_entry["file_name"]
        expected_hash = file_entry["sha256"]
        target_path = source_dir / file_name

        if not target_path.exists():
            msg = f"Missing file declared in manifest: {target_path}"
            raise FileNotFoundError(msg)

        actual_hash = compute_sha256(target_path)
        if actual_hash != expected_hash:
            msg = f"Checksum mismatch for {file_name}: expected {expected_hash}, got {actual_hash}"
            raise ChecksumMismatchError(msg)

    return True
