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
    VoluntaryIntakeConnector,
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


@pytest.fixture
def mock_plfs_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic MOSPI PLFS tables and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-IND-OFF-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    anchors_csv = (
        "nco_code,occupation_title,sector,education_filter,weighted_n,monthly_ern_p10,"
        "monthly_ern_p25,monthly_ern_p50,monthly_ern_p75,monthly_ern_p90,annual_cash_lpa_p10,"
        "annual_cash_lpa_p50,annual_cash_lpa_p90\n"
        "2512,Software Developers,Urban,Tech Degree Graduate,2240,25000,42000,75000,135000,240000,"
        "3.00,9.00,28.80\n"
    )
    layout_csv = (
        "block,item,variable_name,field_length,start_pos,description,sample_universe,weight_multiplier\n"
        "Block 5.1,Item 9,ern25,8,102,Gross earnings,Salaried,None\n"
    )

    (source_dir / "plfs_urban_tech_macro_anchors.csv").write_text(anchors_csv, encoding="utf-8")
    (source_dir / "plfs_2023_24_layout_sched_10_4.csv").write_text(layout_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.fixture
def mock_qes_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic Labour Bureau QES table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-IND-OFF-03"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    qes_csv = (
        "round_number,reference_quarter,sector_name,nic_codes,estimated_employment,"
        "regular_workers_pct,contract_workers_pct,female_workers_pct\n"
        'Round 9,Q4 FY2022-23,IT / BPO,"62, 63",3450000,88.4,11.6,35.2\n'
    )
    (source_dir / "qes_it_bpo_formal_employment.csv").write_text(qes_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.mark.contract
def test_mospi_plfs_connector_contract(mock_plfs_raw_dir: Path) -> None:
    """Contract: MOSPIPLFSConnector extracts urban tech anchors and layout spec."""
    connector = MOSPIPLFSConnector(raw_dir=mock_plfs_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 2  # 1 anchor + 1 layout spec
    for rec in records:
        assert isinstance(rec, RawRecord)
        assert rec.source_id == "SRC-IND-OFF-01"
        assert rec.license_id == "OGL-India-1.0"
        assert rec.source_version == "DDI-IND-CSO-PLFS-2023-24"
        assert len(rec.record_hash) == 64

    table_names = {r.raw_payload["table_name"] for r in records}
    assert table_names == {"macro_anchors", "layout_sched_10_4"}

    # Anchor row companion fields
    anchor_rec = next(r for r in records if r.raw_payload["table_name"] == "macro_anchors")
    assert anchor_rec.raw_payload["nco_code"] == "2512"
    assert anchor_rec.raw_payload["occupation_title"] == "Software Developers"
    assert anchor_rec.raw_payload["annual_cash_lpa_p50"] == "9.00"

    # Layout spec companion fields
    layout_rec = next(r for r in records if r.raw_payload["table_name"] == "layout_sched_10_4")
    assert layout_rec.raw_payload["variable_name"] == "ern25"
    assert layout_rec.raw_payload["block"] == "Block 5.1"


@pytest.mark.contract
def test_labour_bureau_qes_connector_contract(mock_qes_raw_dir: Path) -> None:
    """Contract: LabourBureauQESConnector extracts employment counts with OGL-India-1.0."""
    connector = LabourBureauQESConnector(raw_dir=mock_qes_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-IND-OFF-03"
    assert rec.license_id == "OGL-India-1.0"
    assert rec.raw_payload["round_number"] == "Round 9"
    assert rec.raw_payload["sector_name"] == "IT / BPO"
    assert rec.raw_payload["estimated_employment"] == "3450000"
    assert rec.raw_payload["regular_workers_pct"] == "88.4"
    assert len(rec.record_hash) == 64


@pytest.fixture
def mock_bls_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic BLS OEWS table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-USA-BLS-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    bls_csv = (
        "area_code,area_name,soc_code,occupation_title,total_employment,annual_mean_usd,"
        "annual_p10_usd,annual_p25_usd,annual_median_p50_usd,annual_p75_usd,annual_p90_usd\n"
        "000000,National (US),15-1252,Software Developers,1656880,138110,77020,101560,"
        "132270,169750,208620\n"
    )
    (source_dir / "bls_oews_tech_estimates_may2023.csv").write_text(bls_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.fixture
def mock_dol_lca_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic DOL LCA table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-USA-DOL-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    lca_csv = (
        "case_number,case_status,employer_name,job_title,soc_code,soc_title,"
        "wage_rate_from,wage_unit,prevailing_wage,worksite_city,worksite_state\n"
        "I-200-24001-000101,Certified,Google LLC,Software Engineer,15-1252,"
        "Software Developers,175000,Year,138000,Mountain View,CA\n"
    )
    (source_dir / "dol_lca_fy24_certified_tech_sample.csv").write_text(lca_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.fixture
def mock_dol_perm_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic DOL PERM table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-USA-DOL-02"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    perm_csv = (
        "case_number,case_status,employer_name,job_title,soc_code,wage_offered_from,"
        "wage_unit,min_education_demanded,min_experience_months,country_of_citizenship\n"
        "A-24001-000201,Certified,Google LLC,Staff Software Engineer,15-1252,245000,"
        "Year,Master's,60,INDIA\n"
    )
    (source_dir / "dol_perm_fy24_certified_tech_sample.csv").write_text(perm_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.fixture
def mock_aij_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic ai-jobs table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-KAG-AIJ-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    aij_csv = (
        "work_year,experience_level,employment_type,job_title,salary,salary_currency,"
        "salary_in_usd,employee_residence,remote_ratio,company_location,company_size\n"
        "2023,SE,FT,Data Engineer,150000,USD,150000,US,100,US,M\n"
    )
    (source_dir / "ai_jobs_ds_salaries_2023.csv").write_text(aij_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.fixture
def mock_so_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic Stack Overflow table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-KAG-SO-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    so_csv = (
        "ResponseId,Age,Employment,RemoteWork,EdLevel,YearsCodePro,DevType,Country,"
        "Currency,CompTotal,ConvertedCompYearly\n"
        '1,35-44 years old,"Employed, full-time",Remote,Bachelor’s degree,10,'
        '"Developer, full-stack",India,INR,3500000,42000\n'
    )
    (source_dir / "so_survey_2024_raw_sample.csv").write_text(so_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.mark.contract
def test_bls_oews_connector_contract(mock_bls_raw_dir: Path) -> None:
    """Contract: BLSOEWSConnector extracts US tech estimates with CC0-1.0."""
    connector = BLSOEWSConnector(raw_dir=mock_bls_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-USA-BLS-01"
    assert rec.license_id == "CC0-1.0"
    assert rec.source_version == "2023-05"
    assert rec.raw_payload["soc_code"] == "15-1252"
    assert rec.raw_payload["annual_median_p50_usd"] == "132270"
    assert len(rec.record_hash) == 64


@pytest.mark.contract
def test_dol_lca_connector_contract(mock_dol_lca_raw_dir: Path) -> None:
    """Contract: DOLLCAConnector extracts certified LCA filings with CC0-1.0."""
    connector = DOLLCAConnector(raw_dir=mock_dol_lca_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-USA-DOL-01"
    assert rec.license_id == "CC0-1.0"
    assert rec.source_version == "2023-2024"
    assert rec.raw_payload["employer_name"] == "Google LLC"
    assert rec.raw_payload["wage_rate_from"] == "175000"
    assert len(rec.record_hash) == 64


@pytest.mark.contract
def test_dol_perm_connector_contract(mock_dol_perm_raw_dir: Path) -> None:
    """Contract: DOLPERMConnector extracts PERM certifications with CC0-1.0."""
    connector = DOLPERMConnector(raw_dir=mock_dol_perm_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-USA-DOL-02"
    assert rec.license_id == "CC0-1.0"
    assert rec.source_version == "2023-2024"
    assert rec.raw_payload["min_experience_months"] == "60"
    assert rec.raw_payload["country_of_citizenship"] == "INDIA"
    assert len(rec.record_hash) == 64


@pytest.mark.contract
def test_ai_jobs_salaries_connector_contract(mock_aij_raw_dir: Path) -> None:
    """Contract: AIJobsSalariesConnector extracts AI salary rows with CC0-1.0."""
    connector = AIJobsSalariesConnector(raw_dir=mock_aij_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-KAG-AIJ-01"
    assert rec.license_id == "CC0-1.0"
    assert rec.raw_payload["job_title"] == "Data Engineer"
    assert rec.raw_payload["salary_in_usd"] == "150000"
    assert len(rec.record_hash) == 64


@pytest.fixture
def mock_jobs_in_data_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic Jobs in Data table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-KAG-AIJ-02"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    jid_csv = (
        "work_year,job_title,job_category,salary_currency,salary,salary_in_usd,"
        "employee_residence,experience_level,employment_type,work_setting,"
        "company_location,company_size\n"
        "2024,Data Scientist,Data Science,USD,160000,160000,US,Senior,Full-time,Remote,US,M\n"
    )
    (source_dir / "jobs_in_data_2024.csv").write_text(jid_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.mark.contract
def test_jobs_in_data_connector_contract(mock_jobs_in_data_raw_dir: Path) -> None:
    """Contract: JobsInDataConnector extracts 2024 AI salaries with CC0-1.0."""
    connector = JobsInDataConnector(raw_dir=mock_jobs_in_data_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-KAG-AIJ-02"
    assert rec.license_id == "CC0-1.0"
    assert rec.raw_payload["job_title"] == "Data Scientist"
    assert rec.raw_payload["salary_in_usd"] == "160000"
    assert len(rec.record_hash) == 64


@pytest.mark.contract
def test_stack_overflow_survey_connector_contract(mock_so_raw_dir: Path) -> None:
    """Contract: StackOverflowSurvey2024Connector extracts survey data with ODbL-1.0."""
    connector = StackOverflowSurvey2024Connector(raw_dir=mock_so_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-KAG-SO-01"
    assert rec.license_id == "ODbL-1.0"
    assert rec.raw_payload["ResponseId"] == "1"
    assert rec.raw_payload["Country"] == "India"
    assert rec.raw_payload["CompTotal"] == "3500000"
    assert len(rec.record_hash) == 64


@pytest.fixture
def mock_so_2023_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic 2023 Stack Overflow table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-KAG-SO-02"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    so_csv = (
        "ResponseId,Age,Employment,RemoteWork,EdLevel,YearsCodePro,DevType,Country,"
        "Currency,CompTotal,ConvertedCompYearly\n"
        '2,25-34 years old,"Employed, full-time",Remote,Bachelor’s degree,9,'
        '"Senior Executive",United States of America,USD,285000,285000\n'
    )
    (source_dir / "so_survey_2023_raw_sample.csv").write_text(so_csv, encoding="utf-8")

    generate_source_manifest(source_id=source_id, raw_dir=tmp_path, repo_root=repo_root)
    return tmp_path


@pytest.mark.contract
def test_stack_overflow_2023_survey_connector_contract(mock_so_2023_raw_dir: Path) -> None:
    """Contract: StackOverflowSurvey2023Connector extracts 2023 survey data with ODbL-1.0."""
    connector = StackOverflowSurvey2023Connector(raw_dir=mock_so_2023_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-KAG-SO-02"
    assert rec.license_id == "ODbL-1.0"
    assert rec.raw_payload["ResponseId"] == "2"
    assert rec.raw_payload["CompTotal"] == "285000"
    assert len(rec.record_hash) == 64


SAMPLE_VOLUNTARY_INTAKE_CSV = (
    "submission_id,submission_date,role_family,seniority_level,metro_location,yoe_total,"
    "yoe_current_role,basic_salary_monthly_inr,fixed_allowances_monthly_inr,guaranteed_cash_annual_inr,"
    "variable_bonus_target_annual_inr,equity_grant_annualized_inr,employer_pf_monthly_inr,"
    "gratuity_provision_annual_inr,total_ctc_annual_inr,take_home_monthly_inr,is_payslip_verified,"
    "cryptographic_dedup_hash\n"
    "SUB-2024-001,2024-06-15,SWE,SENIOR,BENGALURU,7.5,2.0,125000,125000,3000000,450000,1000000,"
    "15000,72150,4702150,195000,true,e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
)


@pytest.fixture
def mock_voluntary_intake_raw_dir(tmp_path: Path) -> Path:
    """Create a temporary raw directory with synthetic voluntary intake table and manifest."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    source_id = "SRC-INT-VOL-01"
    source_dir = tmp_path / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    csv_file = source_dir / "voluntary_intake_submissions.csv"
    csv_file.write_text(SAMPLE_VOLUNTARY_INTAKE_CSV, encoding="utf-8")

    generate_source_manifest(
        source_id=source_id,
        raw_dir=tmp_path,
        repo_root=repo_root,
    )
    return tmp_path


@pytest.mark.contract
def test_voluntary_intake_connector_contract(mock_voluntary_intake_raw_dir: Path) -> None:
    """Contract: VoluntaryIntakeConnector extracts submissions and rejects PII (Rule R-DA-07)."""
    connector = VoluntaryIntakeConnector(raw_dir=mock_voluntary_intake_raw_dir)
    records = list(connector.extract_raw_records())

    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, RawRecord)
    assert rec.source_id == "SRC-INT-VOL-01"
    assert rec.license_id == "PROPRIETARY-CONSENT-GRANT"
    assert rec.raw_payload["submission_id"] == "SUB-2024-001"
    assert rec.raw_payload["guaranteed_cash_annual_inr"] == "3000000"
    assert len(rec.record_hash) == 64

    # Hash determinism
    records2 = list(connector.extract_raw_records())
    assert rec.record_hash == records2[0].record_hash


@pytest.mark.contract
def test_voluntary_intake_connector_parquet(mock_voluntary_intake_raw_dir: Path) -> None:
    """Contract: VoluntaryIntakeConnector supports Parquet format when CSV is absent."""
    source_dir = mock_voluntary_intake_raw_dir / "SRC-INT-VOL-01"
    csv_file = source_dir / "voluntary_intake_submissions.csv"
    df = pl.read_csv(csv_file)
    csv_file.unlink()
    parquet_file = source_dir / "voluntary_intake_submissions.parquet"
    df.write_parquet(parquet_file)

    repo_root = Path(__file__).resolve().parent.parent.parent
    generate_source_manifest(
        source_id="SRC-INT-VOL-01",
        raw_dir=mock_voluntary_intake_raw_dir,
        repo_root=repo_root,
    )

    connector = VoluntaryIntakeConnector(raw_dir=mock_voluntary_intake_raw_dir)
    records = list(connector.extract_raw_records())
    assert len(records) == 1
    assert records[0].raw_payload["submission_id"] == "SUB-2024-001"


@pytest.mark.contract
def test_voluntary_intake_connector_rejects_forbidden_pii(
    mock_voluntary_intake_raw_dir: Path,
) -> None:
    """Rule R-DA-07: Ingestion pipeline must raise ValueError if forbidden PII keys are present."""
    source_dir = mock_voluntary_intake_raw_dir / "SRC-INT-VOL-01"
    csv_file = source_dir / "voluntary_intake_submissions.csv"
    content_with_pii = (
        "submission_id,email,pan_number,guaranteed_cash_annual_inr\n"
        "SUB-PII-01,test@example.com,ABCDE1234F,3000000\n"
    )
    csv_file.write_text(content_with_pii, encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent.parent
    generate_source_manifest(
        source_id="SRC-INT-VOL-01",
        raw_dir=mock_voluntary_intake_raw_dir,
        repo_root=repo_root,
    )

    connector = VoluntaryIntakeConnector(raw_dir=mock_voluntary_intake_raw_dir)
    with pytest.raises(ValueError, match="Forbidden PII keys detected"):
        list(connector.extract_raw_records())
