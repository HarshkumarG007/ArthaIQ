"""Unit tests for compintel.ingestion.connector."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
import pytest

from compintel.ingestion.connector import (
    CONNECTOR_REGISTRY,
    AIJobsSalariesConnector,
    BaseConnector,
    BLSOEWSConnector,
    CorporateDisclosuresConnector,
    DOLLCAConnector,
    DOLPERMConnector,
    ESCOTaxonomyConnector,
    JobsInDataConnector,
    LabourBureauQESConnector,
    MOSPIPLFSConnector,
    ONetTaxonomyConnector,
    RBIMacroConnector,
    StackOverflowSurvey2023Connector,
    StackOverflowSurvey2024Connector,
    compute_record_hash,
    find_repo_root,
    get_connector,
)
from compintel.ingestion.manifest import generate_source_manifest

if TYPE_CHECKING:
    from collections.abc import Iterator

    from compintel.schema.entities import RawRecord


@pytest.mark.unit
def test_find_repo_root() -> None:
    """Verify that find_repo_root locates pyproject.toml."""
    root = find_repo_root()
    assert (root / "pyproject.toml").exists()


@pytest.mark.unit
def test_compute_record_hash_properties() -> None:
    """Verify record hash determinism, key invariance, and value sensitivity."""
    dict_a = {"alpha": 10, "beta": "sample", "gamma": True}
    dict_b = {"gamma": True, "alpha": 10, "beta": "sample"}
    dict_c = {"alpha": 11, "beta": "sample", "gamma": True}

    hash_a = compute_record_hash(dict_a)
    hash_b = compute_record_hash(dict_b)
    hash_c = compute_record_hash(dict_c)

    # Invariance to dictionary key insertion order
    assert hash_a == hash_b
    assert len(hash_a) == 64

    # Sensitivity to values
    assert hash_a != hash_c


@pytest.mark.unit
def test_compute_record_hash_non_string_keys() -> None:
    """Verify compute_record_hash safely converts non-string or None keys without error."""
    payload = {1: "one", None: "none", "key": "val"}  # type: ignore[dict-item]
    h = compute_record_hash(payload)
    assert len(h) == 64


@pytest.mark.unit
def test_get_connector_success() -> None:
    """Verify get_connector retrieves registered connector for approved sources."""
    c1 = get_connector("SRC-SUP-CORP-01")
    assert isinstance(c1, CorporateDisclosuresConnector)
    assert c1.source_id == "SRC-SUP-CORP-01"

    c2 = get_connector("SRC-SUP-MAC-01")
    assert isinstance(c2, RBIMacroConnector)
    assert c2.source_id == "SRC-SUP-MAC-01"

    c3 = get_connector("SRC-SUP-TAX-01")
    assert isinstance(c3, ONetTaxonomyConnector)
    assert c3.source_id == "SRC-SUP-TAX-01"

    c4 = get_connector("SRC-SUP-TAX-02")
    assert isinstance(c4, ESCOTaxonomyConnector)
    assert c4.source_id == "SRC-SUP-TAX-02"

    c5 = get_connector("SRC-IND-OFF-01")
    assert isinstance(c5, MOSPIPLFSConnector)
    assert c5.source_id == "SRC-IND-OFF-01"

    c6 = get_connector("SRC-IND-OFF-03")
    assert isinstance(c6, LabourBureauQESConnector)
    assert c6.source_id == "SRC-IND-OFF-03"

    c7 = get_connector("SRC-USA-BLS-01")
    assert isinstance(c7, BLSOEWSConnector)
    assert c7.source_id == "SRC-USA-BLS-01"

    c8 = get_connector("SRC-USA-DOL-01")
    assert isinstance(c8, DOLLCAConnector)
    assert c8.source_id == "SRC-USA-DOL-01"

    c9 = get_connector("SRC-USA-DOL-02")
    assert isinstance(c9, DOLPERMConnector)
    assert c9.source_id == "SRC-USA-DOL-02"

    c10 = get_connector("SRC-KAG-AIJ-01")
    assert isinstance(c10, AIJobsSalariesConnector)
    assert c10.source_id == "SRC-KAG-AIJ-01"

    c11 = get_connector("SRC-KAG-AIJ-02")
    assert isinstance(c11, JobsInDataConnector)
    assert c11.source_id == "SRC-KAG-AIJ-02"

    c12 = get_connector("SRC-KAG-SO-01")
    assert isinstance(c12, StackOverflowSurvey2024Connector)
    assert c12.source_id == "SRC-KAG-SO-01"

    c13 = get_connector("SRC-KAG-SO-02")
    assert isinstance(c13, StackOverflowSurvey2023Connector)
    assert c13.source_id == "SRC-KAG-SO-02"


@pytest.mark.unit
def test_get_connector_approved_but_unimplemented_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify get_connector raises ValueError if approved source has no registered connector."""
    monkeypatch.delitem(CONNECTOR_REGISTRY, "SRC-USA-BLS-01", raising=False)
    with pytest.raises(ValueError, match="No connector implementation registered"):
        get_connector("SRC-USA-BLS-01")


@pytest.mark.unit
def test_connector_missing_manifest_raises_file_not_found(tmp_path: Path) -> None:
    """Verify verify_manifest raises FileNotFoundError when manifest.yaml is missing."""
    connector = CorporateDisclosuresConnector(raw_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Manifest not found"):
        connector.verify_manifest()


@pytest.mark.unit
def test_connector_missing_data_file_raises_file_not_found(tmp_path: Path) -> None:
    """Verify extract_raw_records raises FileNotFoundError if data file is missing."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-SUP-CORP-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy other file and generate manifest so verify_manifest passes
    dummy_file = source_dir / "other.txt"
    dummy_file.write_text("dummy", encoding="utf-8")
    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)

    connector = CorporateDisclosuresConnector(raw_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Raw data file not found"):
        list(connector.extract_raw_records())


@pytest.mark.unit
def test_to_raw_dataframe_empty() -> None:
    """Verify to_raw_dataframe returns empty DataFrame with expected schema."""

    class EmptyConnector(BaseConnector):
        source_id = "SRC-SUP-CORP-01"

        def extract_raw_records(self) -> Iterator[RawRecord]:
            return iter([])

    connector = EmptyConnector()
    df = connector.to_raw_dataframe()
    assert isinstance(df, pl.DataFrame)
    assert "source_id" in df.columns
    assert "raw_payload" in df.columns


@pytest.mark.unit
def test_plfs_connector_missing_data_files_raises_file_not_found(tmp_path: Path) -> None:
    """Verify MOSPIPLFSConnector raises FileNotFoundError when both data files are missing."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-IND-OFF-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    dummy_file = source_dir / "other.txt"
    dummy_file.write_text("dummy", encoding="utf-8")
    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)

    connector = MOSPIPLFSConnector(raw_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="No raw data files found for SRC-IND-OFF-01"):
        list(connector.extract_raw_records())


@pytest.mark.unit
def test_qes_connector_missing_data_file_raises_file_not_found(tmp_path: Path) -> None:
    """Verify LabourBureauQESConnector raises FileNotFoundError when data file is missing."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-IND-OFF-03"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    dummy_file = source_dir / "other.txt"
    dummy_file.write_text("dummy", encoding="utf-8")
    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)

    connector = LabourBureauQESConnector(raw_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Raw data file not found"):
        list(connector.extract_raw_records())
