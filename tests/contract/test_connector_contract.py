"""Contract tests for data ingestion connectors (Rules R-DA-01, R-DA-02, R-DA-03).

Verifies:
1. An unapproved or restricted source is refused by raising LicenceViolationError.
2. File tampering or manifest corruption raises ChecksumMismatchError.
3. Every connector emits valid, immutable RawRecord instances with deterministic hashes.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
import pytest

from compintel.errors import DataContractError, LicenceViolationError
from compintel.ingestion.connector import (
    BaseConnector,
    CorporateDisclosuresConnector,
    get_connector,
)
from compintel.ingestion.manifest import (
    ChecksumMismatchError,
    LicenceGateError,
    generate_source_manifest,
)
from compintel.schema.entities import RawRecord

if TYPE_CHECKING:
    from collections.abc import Iterator


SAMPLE_CORP_CSV = (
    "company_symbol,company_name,fiscal_year,median_remuneration_inr,"
    "pct_increase_mre,permanent_employee_count,director_to_mre_ratio,"
    "statutory_source_citation\n"
    "TCS,Tata Consultancy Services Limited,FY2023-24,601496,5.3,601546,415.0,Annual Report\n"
    "INFY,Infosys Limited,FY2023-24,900012,9.4,317240,669.0,Annual Report\n"
)


@pytest.fixture
def mock_corp_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic files and verified manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-SUP-CORP-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    csv_file = source_dir / "listed_it_mre_fy24.csv"
    csv_file.write_text(SAMPLE_CORP_CSV, encoding="utf-8")

    generate_source_manifest(
        source_id=source_id,
        raw_dir=tmp_path,
        repo_root=repo_root,
    )
    return tmp_path


@pytest.mark.contract
def test_unapproved_rejected_source_refused_by_licence_gate() -> None:
    """Rule R-DA-01: An unapproved/rejected source must be refused with LicenceViolationError."""
    with pytest.raises(LicenceViolationError) as exc_info:
        get_connector("SRC-KAG-REJ-01")

    assert issubclass(exc_info.type, LicenceViolationError)
    assert issubclass(exc_info.type, LicenceGateError)
    assert "rejected" in str(exc_info.value)


@pytest.mark.contract
def test_restricted_fixture_source_refused_by_licence_gate() -> None:
    """Rule R-DA-01: A restricted test fixture source must be refused with LicenceViolationError."""
    with pytest.raises(LicenceViolationError) as exc_info:
        get_connector("SRC-KAG-FIX-01")

    assert issubclass(exc_info.type, LicenceViolationError)
    assert "restricted" in str(exc_info.value)


@pytest.mark.contract
def test_nonexistent_source_refused_by_licence_gate() -> None:
    """Rule R-DA-01: An unregistered source must be refused with LicenceViolationError."""
    with pytest.raises(LicenceViolationError):
        get_connector("SRC-NONEXISTENT-99")


@pytest.mark.contract
def test_custom_connector_subclass_enforces_licence_gate() -> None:
    """Rule R-DA-01: Any BaseConnector subclass verifying licence rejects unapproved sources."""

    class UnapprovedConnector(BaseConnector):
        source_id = "SRC-KAG-REJ-02"

        def extract_raw_records(self) -> Iterator[RawRecord]:
            self.verify_licence()
            if False:
                yield  # pragma: no cover

    connector = UnapprovedConnector()
    with pytest.raises(LicenceViolationError):
        list(connector.extract_raw_records())


@pytest.mark.contract
def test_tampered_raw_file_refused_with_checksum_mismatch(mock_corp_raw_dir: Path) -> None:
    """Rule R-DA-02: Modifying raw data invalidates manifest and raises ChecksumMismatchError."""
    connector = CorporateDisclosuresConnector(raw_dir=mock_corp_raw_dir)

    # Tamper with the raw CSV file after manifest was generated
    csv_file = mock_corp_raw_dir / "SRC-SUP-CORP-01" / "listed_it_mre_fy24.csv"
    csv_file.write_text("TAMPERED_CONTENT\n", encoding="utf-8")

    with pytest.raises(ChecksumMismatchError) as exc_info:
        list(connector.extract_raw_records())

    assert issubclass(exc_info.type, DataContractError)
    assert issubclass(exc_info.type, ChecksumMismatchError)


@pytest.mark.contract
def test_corporate_disclosures_connector_contract(mock_corp_raw_dir: Path) -> None:
    """Rule R-DA-02 & R-DA-03: Connector extracts valid RawRecords with SHA-256 hashes."""
    connector = CorporateDisclosuresConnector(raw_dir=mock_corp_raw_dir)

    records = list(connector.extract_raw_records())
    assert len(records) == 2

    for rec in records:
        assert isinstance(rec, RawRecord)
        assert rec.source_id == "SRC-SUP-CORP-01"
        assert rec.license_id == "STATUTORY-PUBLIC-DISCLOSURE"
        assert rec.source_version == "FY2023-24"
        assert len(rec.record_hash) == 64  # SHA-256 hex length
        assert int(rec.record_hash, 16) > 0  # Valid hex digest

        # Verify raw companion fields are strictly preserved
        assert "company_symbol" in rec.raw_payload
        assert "median_remuneration_inr" in rec.raw_payload
        assert "statutory_source_citation" in rec.raw_payload

    # Distinct records produce distinct deterministic hashes
    assert records[0].record_hash != records[1].record_hash


@pytest.mark.contract
def test_to_raw_dataframe_projection(mock_corp_raw_dir: Path) -> None:
    """Test converting extracted records to a typed Polars DataFrame."""
    connector = CorporateDisclosuresConnector(raw_dir=mock_corp_raw_dir)
    df = connector.to_raw_dataframe()

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert set(df.columns) == {
        "source_id",
        "source_version",
        "license_id",
        "retrieved_at",
        "record_hash",
        "raw_payload",
    }
