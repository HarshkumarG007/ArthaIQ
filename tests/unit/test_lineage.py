"""Unit tests for data lineage, versioning, and snapshot hashing (T3.13).

Governed by:
- Rule R-DA-02: Derived datasets record lineage.
- Rule R-DA-08: Data is gitignored; manifests are committed.
- ADR-0006: Deterministic snapshot identifier and idempotent clean runs.
"""

from pathlib import Path

import polars as pl
import pytest
import yaml

from compintel.ingestion.lineage import (
    compute_config_hash,
    compute_dataframe_content_hash,
    compute_manifest_hash,
    compute_snapshot_id,
    create_snapshot_lineage,
    get_git_commit,
    load_lineage,
    save_lineage,
)


@pytest.fixture
def mock_pipeline_dirs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create isolated mock raw, config, canonical, and quarantine directories."""
    raw_dir = tmp_path / "raw"
    config_dir = tmp_path / "config"
    canon_dir = tmp_path / "canonical"
    quar_dir = tmp_path / "quarantine"

    raw_dir.mkdir()
    config_dir.mkdir()
    canon_dir.mkdir()
    quar_dir.mkdir()

    # Create mock source 1
    s1_dir = raw_dir / "SRC-TEST-01"
    s1_dir.mkdir()
    with open(s1_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "source_id": "SRC-TEST-01",
                "files": [{"file_name": "data1.csv", "sha256": "aaaa" * 16}],
                "generated_at_utc": "2026-10-16T00:00:00Z",
            },
            f,
        )

    # Create mock source 2
    s2_dir = raw_dir / "SRC-TEST-02"
    s2_dir.mkdir()
    with open(s2_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "source_id": "SRC-TEST-02",
                "files": [{"file_name": "data2.csv", "sha256": "bbbb" * 16}],
                "generated_at_utc": "2026-10-16T00:00:00Z",
            },
            f,
        )

    # Create mock config files
    sources_cfg = config_dir / "sources"
    sources_cfg.mkdir()
    with open(sources_cfg / "SRC-TEST-01.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"source_id": "SRC-TEST-01", "licence": {"status": "approved"}}, f)

    with open(config_dir / "thresholds.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"min_cohort_size": 5, "quality_floor": 50.0}, f)

    return raw_dir, config_dir, canon_dir, quar_dir


@pytest.mark.unit
def test_compute_manifest_hash_empty_dir(tmp_path: Path) -> None:
    """Raises ValueError when raw directory contains no source manifests."""
    empty_raw = tmp_path / "empty_raw"
    empty_raw.mkdir()
    with pytest.raises(ValueError, match="No manifest.yaml files found"):
        compute_manifest_hash(empty_raw)


@pytest.mark.unit
def test_compute_manifest_hash_missing_dir(tmp_path: Path) -> None:
    """Raises FileNotFoundError when raw directory does not exist."""
    missing = tmp_path / "non_existent_raw"
    with pytest.raises(FileNotFoundError):
        compute_manifest_hash(missing)


@pytest.mark.unit
def test_compute_manifest_hash_deterministic(
    mock_pipeline_dirs: tuple[Path, Path, Path, Path],
) -> None:
    """Computes deterministic master hash across multiple runs on identical manifests."""
    raw_dir, _, _, _ = mock_pipeline_dirs
    hash1, sources1 = compute_manifest_hash(raw_dir)
    hash2, sources2 = compute_manifest_hash(raw_dir)

    assert hash1 == hash2
    assert len(hash1) == 64
    assert set(sources1.keys()) == {"SRC-TEST-01", "SRC-TEST-02"}
    assert sources1 == sources2


@pytest.mark.unit
def test_compute_manifest_hash_tamper_detection(
    mock_pipeline_dirs: tuple[Path, Path, Path, Path],
) -> None:
    """Altering any raw manifest immediately alters the master manifest hash."""
    raw_dir, _, _, _ = mock_pipeline_dirs
    baseline_hash, _ = compute_manifest_hash(raw_dir)

    # Tamper with SRC-TEST-01 manifest
    m1 = raw_dir / "SRC-TEST-01" / "manifest.yaml"
    with open(m1, "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "source_id": "SRC-TEST-01",
                "files": [{"file_name": "data1.csv", "sha256": "cccc" * 16}],
                "generated_at_utc": "2026-10-16T00:00:00Z",
            },
            f,
        )

    tampered_hash, _ = compute_manifest_hash(raw_dir)
    assert tampered_hash != baseline_hash


@pytest.mark.unit
def test_compute_config_hash_deterministic(
    mock_pipeline_dirs: tuple[Path, Path, Path, Path],
) -> None:
    """Computes deterministic composite hash across system configuration files."""
    _, config_dir, _, _ = mock_pipeline_dirs
    h1 = compute_config_hash(config_dir)
    h2 = compute_config_hash(config_dir)

    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.unit
def test_compute_config_hash_tamper(
    mock_pipeline_dirs: tuple[Path, Path, Path, Path],
) -> None:
    """Altering any configuration file alters the configuration hash."""
    _, config_dir, _, _ = mock_pipeline_dirs
    baseline = compute_config_hash(config_dir)

    # Edit thresholds.yaml
    thresh_p = config_dir / "thresholds.yaml"
    with open(thresh_p, "w", encoding="utf-8") as f:
        yaml.dump({"min_cohort_size": 10, "quality_floor": 60.0}, f)

    modified = compute_config_hash(config_dir)
    assert modified != baseline


@pytest.mark.unit
def test_get_git_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Retrieves commit from env override, git command, or fallback."""
    # 1. Environment variable override
    monkeypatch.setenv("ARTHAIQ_COMMIT", "abcdef1234567890abcdef1234567890abcdef12")
    assert get_git_commit() == "abcdef1234567890abcdef1234567890abcdef12"

    # 2. Non-git directory fallback
    monkeypatch.delenv("ARTHAIQ_COMMIT", raising=False)
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    commit = get_git_commit(repo_root=empty_dir)
    assert len(commit) >= 7


@pytest.mark.unit
def test_compute_snapshot_id_deterministic() -> None:
    """Formula SNAP- + SHA-256(manifest:commit:config:schema)[:12] is strictly deterministic."""
    m_hash = "a" * 64
    commit = "1" * 40
    c_hash = "b" * 64
    schema_ver = "1.0.0"

    id1 = compute_snapshot_id(m_hash, commit, c_hash, schema_ver)
    id2 = compute_snapshot_id(m_hash, commit, c_hash, schema_ver)

    assert id1 == id2
    assert id1.startswith("SNAP-")
    assert len(id1) == 17  # "SNAP-" (5) + 12 chars hex


@pytest.mark.unit
def test_compute_snapshot_id_sensitivity() -> None:
    """Modifying any input parameter alters the resulting snapshot identifier."""
    base = compute_snapshot_id("a" * 64, "1" * 40, "b" * 64, "1.0.0")

    assert compute_snapshot_id("c" * 64, "1" * 40, "b" * 64, "1.0.0") != base
    assert compute_snapshot_id("a" * 64, "2" * 40, "b" * 64, "1.0.0") != base
    assert compute_snapshot_id("a" * 64, "1" * 40, "c" * 64, "1.0.0") != base
    assert compute_snapshot_id("a" * 64, "1" * 40, "b" * 64, "1.0.1") != base


@pytest.mark.unit
def test_compute_dataframe_content_hash() -> None:
    """Computes identical content hashes regardless of row order and supports nested lists."""
    df1 = pl.DataFrame(
        {
            "observation_id": ["OBS-01", "OBS-02"],
            "pay": [10.5, 25.0],
            "skills": [["Python", "SQL"], ["Rust", "Polars"]],
        }
    )
    df2 = pl.DataFrame(
        {
            "observation_id": ["OBS-02", "OBS-01"],
            "pay": [25.0, 10.5],
            "skills": [["Rust", "Polars"], ["Python", "SQL"]],
        }
    )

    h1 = compute_dataframe_content_hash(df1)
    h2 = compute_dataframe_content_hash(df2)

    assert h1 == h2
    assert len(h1) == 64

    # Empty DataFrame hash
    empty_h = compute_dataframe_content_hash(pl.DataFrame([]))
    assert len(empty_h) == 64
    assert empty_h != h1


@pytest.mark.unit
def test_lineage_serialization_roundtrip(
    mock_pipeline_dirs: tuple[Path, Path, Path, Path], tmp_path: Path
) -> None:
    """DataSnapshotLineage models can be created, saved to JSON, and reloaded identically."""
    raw_dir, config_dir, _, _ = mock_pipeline_dirs

    lineage = create_snapshot_lineage(
        raw_dir=raw_dir,
        config_dir=config_dir,
        record_count=100,
        quarantined_count=20,
        data_hash="d" * 64,
        built_at="2026-10-16T12:00:00Z",
    )

    out_file = tmp_path / "test_lineage.json"
    save_lineage(lineage, out_file)
    assert out_file.exists()

    loaded = load_lineage(out_file)
    assert loaded.snapshot_id == lineage.snapshot_id
    assert loaded.manifest_hash == lineage.manifest_hash
    assert loaded.config_hash == lineage.config_hash
    assert loaded.record_count == 100
    assert loaded.quarantined_count == 20
    assert loaded.reconciliation_delta == 0
    assert loaded.data_hash == "d" * 64
