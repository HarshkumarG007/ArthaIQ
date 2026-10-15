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
    ESCOTaxonomyConnector,
    ONetTaxonomyConnector,
    RBIMacroConnector,
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


@pytest.fixture
def mock_macro_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic RBI macro series and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-SUP-MAC-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    cpi_csv = "observation_date,INDCPIALLMINMEI\n2024-01-01,185.0\n2024-02-01,185.5\n"
    fx_csv = "observation_date,DEXINUS\n2024-01-02,83.15\n2024-01-03,83.20\n"

    (source_dir / "cpi_urban_monthly.csv").write_text(cpi_csv, encoding="utf-8")
    (source_dir / "inr_usd_fx_daily.csv").write_text(fx_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.fixture
def mock_onet_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic O*NET taxonomy tables and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-SUP-TAX-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    occ_csv = "onetsoc_code,title,description\n15-1252.00,Software Developers,Develop software\n"
    skills_csv = (
        "onetsoc_code,commodity_code,commodity_title,example_tool,hot_technology\n"
        "15-1252.00,43232408,Dev software,Python,Y\n"
    )

    (source_dir / "occupation_data_tech.csv").write_text(occ_csv, encoding="utf-8")
    (source_dir / "technology_skills_tech_roles.csv").write_text(skills_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.fixture
def mock_esco_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic ESCO taxonomy table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-SUP-TAX-02"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    esco_csv = (
        "concept_uri,skill_label,skill_type,reuse_level,parent_skill_group\n"
        "http://data.europa.eu/esco/skill/001,Python,knowledge,sector-specific,Programming\n"
    )
    (source_dir / "esco_skills_tech_hierarchy.csv").write_text(esco_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.mark.contract
def test_rbi_macro_connector_contract(mock_macro_raw_dir: Path) -> None:
    """Contract: RBIMacroConnector extracts both CPI and FX series with OGDL-IN licence."""
    connector = RBIMacroConnector(raw_dir=mock_macro_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 4  # 2 CPI + 2 FX
    for rec in records:
        assert isinstance(rec, RawRecord)
        assert rec.source_id == "SRC-SUP-MAC-01"
        assert rec.license_id == "OGDL-IN"
        assert len(rec.record_hash) == 64

    series_names = {r.raw_payload["series_name"] for r in records}
    assert series_names == {"cpi_urban_monthly", "inr_usd_fx_daily"}


@pytest.mark.contract
def test_onet_taxonomy_connector_contract(mock_onet_raw_dir: Path) -> None:
    """Contract: ONetTaxonomyConnector extracts occupations and skills with CC-BY-4.0 licence."""
    connector = ONetTaxonomyConnector(raw_dir=mock_onet_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 2  # 1 occupation + 1 skill
    for rec in records:
        assert isinstance(rec, RawRecord)
        assert rec.source_id == "SRC-SUP-TAX-01"
        assert rec.license_id == "CC-BY-4.0"
        assert rec.source_version == "29.0"
        assert len(rec.record_hash) == 64

    table_names = {r.raw_payload["table_name"] for r in records}
    assert table_names == {"occupations", "technology_skills"}


@pytest.mark.contract
def test_esco_taxonomy_connector_contract(mock_esco_raw_dir: Path) -> None:
    """Contract: ESCOTaxonomyConnector extracts skill hierarchy with ODbL-1.0 licence."""
    connector = ESCOTaxonomyConnector(raw_dir=mock_esco_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-SUP-TAX-02"
    assert rec.license_id == "ODbL-1.0"
    assert rec.source_version == "1.1.1"
    assert rec.raw_payload["skill_label"] == "Python"
    assert rec.raw_payload["parent_skill_group"] == "Programming"
    assert len(rec.record_hash) == 64
