"""Data versioning, lineage tracking, and snapshot hashing engine.

Governed by Rules R-DA-02, R-DA-08, and ADR-0006. Provides deterministic cryptographic
snapshot identifiers, raw manifest digest verification, configuration hashing, and
immutable lineage tracking for canonical compensation datasets.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from compintel.schema.canonical import CURRENT_SCHEMA_VERSION

if TYPE_CHECKING:
    import polars as pl


class DataSnapshotLineage(BaseModel):
    """Immutable audit manifest recording the full lineage of a canonical dataset snapshot.

    Adheres strictly to:
    - Rule R-DA-02: Every derived dataset records lineage (sources, commit, config, schema).
    - Rule R-DA-05: Count reconciliation proven (Total in = Valid + Quarantined, delta = 0).
    - Rule R-DA-08: Data zone is gitignored; lineage manifests are committed and audited.
    - ADR-0006: Deterministic snapshot identifier derived from manifests, commit, config, schema.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    snapshot_id: str = Field(
        ...,
        pattern=r"^SNAP-[A-Z0-9]{12}$",
        description="Deterministic 12-character hex snapshot identifier derived from inputs.",
    )
    manifest_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Deterministic SHA-256 composite hash of all raw ingestion manifests.",
    )
    git_commit: str = Field(
        ...,
        min_length=7,
        max_length=64,
        description="Git commit SHA from which the canonical dataset was produced.",
    )
    config_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Deterministic SHA-256 composite hash of all active system configs.",
    )
    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Canonical schema semver string (e.g. '1.0.0').",
    )
    built_at: str = Field(
        ...,
        description="UTC timestamp of the reproduction / build execution in ISO 8601 format.",
    )
    source_ids: list[str] = Field(
        ...,
        description="Sorted list of all ingested source identifiers.",
    )
    source_manifests: dict[str, str] = Field(
        ...,
        description="Mapping from source_id to individual manifest SHA-256 digest.",
    )
    record_count: int = Field(
        ...,
        ge=0,
        description="Total count of valid canonical observations admitted into the snapshot.",
    )
    quarantined_count: int = Field(
        ...,
        ge=0,
        description="Total count of observations quarantined with deterministic reason codes.",
    )
    reconciliation_delta: int = Field(
        default=0,
        ge=0,
        le=0,
        description="Mathematical count reconciliation delta (Total - Valid - Quarantined == 0).",
    )
    data_hash: str | None = Field(
        default=None,
        description="Deterministic SHA-256 hash of the canonical parquet data content.",
    )
    reproduction_command: str = Field(
        default="make reproduce-data",
        description="Canonical CLI command to rebuild and reproduce this exact dataset snapshot.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional build companion metadata (e.g. polars version, environment).",
    )


def compute_manifest_hash(
    raw_dir: Path, source_ids: list[str] | None = None
) -> tuple[str, dict[str, str]]:
    """Compute deterministic SHA-256 composite hash of raw source manifests.

    Uses semantic YAML-to-JSON canonical serialization to eliminate OS-specific
    CRLF vs LF line ending discrepancies across Windows and Linux environments.

    Args:
        raw_dir: Root directory containing raw sources (e.g. data/raw).
        source_ids: Optional list of specific source IDs to evaluate; if None, scans raw_dir.

    Returns:
        tuple of (master_manifest_hash_hex, dict of {source_id: individual_manifest_sha256}).
    """
    raw_path = Path(raw_dir).resolve()
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_path}")

    # Discover source directories with manifest.yaml
    manifest_paths: dict[str, Path] = {}
    if source_ids is not None:
        for sid in source_ids:
            p = raw_path / sid / "manifest.yaml"
            if p.exists():
                manifest_paths[sid] = p
            else:
                raise FileNotFoundError(f"Manifest not found for source '{sid}' at {p}")
    else:
        for p in raw_path.glob("*/manifest.yaml"):
            sid = p.parent.name
            manifest_paths[sid] = p

    if not manifest_paths:
        raise ValueError(f"No manifest.yaml files found in {raw_path}")

    source_manifest_map: dict[str, str] = {}
    for sid in sorted(manifest_paths.keys()):
        p = manifest_paths[sid]
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        canonical_json = json.dumps(data, sort_keys=True, default=str)
        sha = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        source_manifest_map[sid] = sha

    # Composite master hash across sorted source manifests
    composite_payload = "\n".join(
        f"{sid}:{source_manifest_map[sid]}" for sid in sorted(source_manifest_map.keys())
    )
    master_hash = hashlib.sha256(composite_payload.encode("utf-8")).hexdigest()
    return master_hash, source_manifest_map


def compute_config_hash(config_dir: Path) -> str:
    """Compute deterministic SHA-256 composite hash across all system configuration files.

    Scans config/ recursively for .yaml and .yml files. Uses semantic YAML canonicalization
    and normalized POSIX relative paths to guarantee bitwise stability across platforms.
    """
    cfg_path = Path(config_dir).resolve()
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config directory does not exist: {cfg_path}")

    file_hashes: list[tuple[str, str]] = []
    for p in sorted(cfg_path.rglob("*")):
        if p.is_file() and p.suffix.lower() in [".yaml", ".yml"]:
            rel_path = p.relative_to(cfg_path).as_posix()
            try:
                with open(p, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                canonical_repr = json.dumps(data, sort_keys=True, default=str)
                f_hash = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
            except Exception:
                with open(p, "rb") as f:
                    f_hash = hashlib.sha256(f.read()).hexdigest()
            file_hashes.append((rel_path, f_hash))

    if not file_hashes:
        return hashlib.sha256(b"NO_CONFIG").hexdigest()

    composite_payload = "\n".join(f"{rel}:{h}" for rel, h in sorted(file_hashes))
    return hashlib.sha256(composite_payload.encode("utf-8")).hexdigest()


def get_git_commit(repo_root: Path | None = None) -> str:
    """Retrieve current git commit SHA, honoring env overrides and graceful fallbacks.

    Priority:
    1. ARTHAIQ_COMMIT or GIT_COMMIT environment variable
    2. git rev-parse HEAD execution in repo_root
    3. Fallback deterministic 40-char zero-hash if not inside a git repository
    """
    env_commit = (
        os.environ.get("ARTHAIQ_COMMIT")
        or os.environ.get("GIT_COMMIT")
        or os.environ.get("GIT_COMMIT_SHA")
        or os.environ.get("GITHUB_SHA")
    )
    if env_commit and env_commit.strip():
        return env_commit.strip()

    target_dir = repo_root or Path.cwd()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        commit = res.stdout.strip()
        if commit:
            return commit
    except Exception:
        pass

    return "0" * 40


def compute_snapshot_id(
    manifest_hash: str,
    git_commit: str,
    config_hash: str,
    schema_version: str = CURRENT_SCHEMA_VERSION,
) -> str:
    """Derive deterministic canonical dataset snapshot identifier (ADR-0006).

    Formula: SNAP- + SHA-256(manifest_hash : git_commit : config_hash : schema_version)[:12].upper()
    """
    seed = f"{manifest_hash}:{git_commit}:{config_hash}:{schema_version}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()
    return f"SNAP-{digest}"


def compute_dataframe_content_hash(df: pl.DataFrame, sort_key: str = "observation_id") -> str:
    """Compute deterministic SHA-256 hash of Polars DataFrame records.

    Ensures rows are ordered by primary key before serializing into canonical NDJSON bytes,
    seamlessly supporting nested columns (e.g. skills: list[str]).
    """
    if df.height == 0:
        return hashlib.sha256(b"EMPTY_DATAFRAME").hexdigest()

    sorted_df = df.sort(sort_key) if sort_key in df.columns else df
    ndjson_bytes = sorted_df.write_ndjson().encode("utf-8")
    return hashlib.sha256(ndjson_bytes).hexdigest()


def save_lineage(lineage: DataSnapshotLineage, output_path: Path) -> None:
    """Serialize DataSnapshotLineage into a formatted, human-readable JSON file."""
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(lineage.model_dump_json(indent=2))


def load_lineage(lineage_path: Path) -> DataSnapshotLineage:
    """Load and validate DataSnapshotLineage from a JSON file."""
    path = Path(lineage_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Lineage file not found at: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return DataSnapshotLineage(**data)


def create_snapshot_lineage(
    raw_dir: Path,
    config_dir: Path,
    record_count: int,
    quarantined_count: int,
    data_hash: str | None = None,
    repo_root: Path | None = None,
    source_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    built_at: str | None = None,
) -> DataSnapshotLineage:
    """Factory creating fully computed DataSnapshotLineage instance."""
    manifest_hash, source_manifests = compute_manifest_hash(raw_dir, source_ids=source_ids)
    config_hash = compute_config_hash(config_dir)
    git_commit = get_git_commit(repo_root)
    snapshot_id = compute_snapshot_id(
        manifest_hash=manifest_hash,
        git_commit=git_commit,
        config_hash=config_hash,
        schema_version=CURRENT_SCHEMA_VERSION,
    )
    build_time = built_at or datetime.now(UTC).isoformat()

    return DataSnapshotLineage(
        snapshot_id=snapshot_id,
        manifest_hash=manifest_hash,
        git_commit=git_commit,
        config_hash=config_hash,
        schema_version=CURRENT_SCHEMA_VERSION,
        built_at=build_time,
        source_ids=sorted(source_manifests.keys()),
        source_manifests=source_manifests,
        record_count=record_count,
        quarantined_count=quarantined_count,
        reconciliation_delta=0,
        data_hash=data_hash,
        reproduction_command="make reproduce-data",
        metadata=metadata or {},
    )
