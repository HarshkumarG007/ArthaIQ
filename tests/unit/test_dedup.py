"""Unit tests for deduplication, entity resolution, and duplicate reporting."""

from __future__ import annotations

import polars as pl
import pytest

from compintel.quality.dedup import (
    DEFAULT_DEDUP_VERSION,
    DeduplicationResult,
    ExactDeduplicator,
    canonicalize_employer_name,
    compute_employer_signature,
    compute_exact_record_signature,
    compute_person_signature,
    compute_posting_signature,
    compute_source_duplicate_report,
    deduplicate_records_df,
    generate_deduplication_report_markdown,
)


@pytest.mark.unit
def test_compute_exact_record_signature_determinism() -> None:
    """Verify exact signature is invariant to dict insertion order and float rounding."""
    rec1 = {
        "source_id": "SRC-INT-VOL-01",
        "role_family": "SWE",
        "canonical_title": "Software Engineer",
        "seniority": "SR",
        "location": "BENGALURU",
        "years_experience": 7.50,
        "guaranteed_cash_annual": 3000000.0,
        "basic_annual": 1500000.0,
        "hra_annual": 750000.0,
        "special_allowance_annual": 750000.0,
        "as_of_date": "2024-06-15",
    }
    rec2 = {
        "as_of_date": "2024-06-15",
        "special_allowance_annual": 750000.00001,
        "hra_annual": 750000.0,
        "basic_annual": 1500000.0,
        "guaranteed_cash_annual": 3000000.0,
        "years_experience": 7.5,
        "location": "BENGALURU",
        "seniority": "SR",
        "canonical_title": "Software Engineer",
        "role_family": "SWE",
        "source_id": "SRC-INT-VOL-01",
    }
    sig1 = compute_exact_record_signature(rec1)
    sig2 = compute_exact_record_signature(rec2)

    assert sig1 == sig2
    assert len(sig1) == 64

    # Value sensitivity
    rec3 = dict(rec1)
    rec3["guaranteed_cash_annual"] = 3500000.0
    assert compute_exact_record_signature(rec3) != sig1


@pytest.mark.unit
def test_compute_person_signature() -> None:
    """Verify person signature clustering via explicit anonymized ID and demographic fallback."""
    # Explicit ID
    p1 = {"anonymized_employee_id": "EMP-9901", "location": "BENGALURU"}
    p2 = {"anonymized_employee_id": "EMP-9901", "location": "HYDERABAD"}
    assert compute_person_signature(p1) == compute_person_signature(p2)
    assert compute_person_signature(p1).startswith("PER-")

    # Demographic profile fallback
    prof1 = {
        "location": "PUNE",
        "role_family": "DATA",
        "education_level": "Bachelors",
        "years_experience": 4.0,
        "guaranteed_cash_annual": 1800000.0,
    }
    prof2 = dict(prof1)
    assert compute_person_signature(prof1) == compute_person_signature(prof2)

    # Distinct person
    prof3 = dict(prof1)
    prof3["location"] = "CHENNAI"
    assert compute_person_signature(prof1) != compute_person_signature(prof3)


@pytest.mark.unit
def test_canonicalize_employer_name_known_aliases() -> None:
    """Verify major Indian and multinational tech employers canonicalize to registry names."""
    cases = [
        ("Google India Pvt Ltd", "Google"),
        ("Google India Private Limited", "Google"),
        ("Google Inc", "Google"),
        ("Amazon Web Services India", "Amazon"),
        ("Amazon Development Center India Pvt Ltd", "Amazon"),
        ("Microsoft Corporation India", "Microsoft"),
        ("TCS", "Tata Consultancy Services"),
        ("Tata Consultancy Services Ltd", "Tata Consultancy Services"),
        ("Infosys Limited", "Infosys"),
        ("Infosys Technologies Ltd", "Infosys"),
        ("Wipro Technologies", "Wipro"),
        ("Flipkart Internet Pvt Ltd", "Flipkart"),
        ("Zomato Media Pvt Ltd", "Zomato"),
    ]

    for raw, expected_name in cases:
        canonical_name, cluster_id = canonicalize_employer_name(raw)
        assert canonical_name == expected_name, f"Expected {expected_name} for '{raw}'"
        assert cluster_id.startswith("EMP-")
        assert len(cluster_id) == 16  # 'EMP-' + 12 hex chars


@pytest.mark.unit
def test_canonicalize_employer_name_fuzzy_matching() -> None:
    """Verify RapidFuzz token matching resolves minor typos and variations."""
    cases = [
        ("Googl India", "Google"),
        ("Microsft India", "Microsoft"),
        ("Infosis Technologies", "Infosys"),
        ("Amazn India", "Amazon"),
    ]

    for raw, expected_name in cases:
        canonical_name, cluster_id = canonicalize_employer_name(raw)
        assert canonical_name == expected_name, f"Expected {expected_name} for '{raw}'"
        assert cluster_id.startswith("EMP-")


@pytest.mark.unit
def test_canonicalize_employer_name_uncataloged_fallback() -> None:
    """Verify uncataloged companies strip legal suffixes and title-case."""
    name1, id1 = canonicalize_employer_name("Acme Software Solutions Private Limited")
    assert name1 == "Acme"
    assert id1.startswith("EMP-")

    name2, id2 = canonicalize_employer_name("Zenith Global Systems Ltd")
    assert name2 == "Zenith"
    assert id2.startswith("EMP-")


@pytest.mark.unit
def test_canonicalize_employer_name_empty_or_anonymous() -> None:
    """Verify missing, whitespace, or placeholder employer names map to Anonymous cluster."""
    for placeholder in [None, "", "   ", "N/A", "na", "Unknown", "anonymous", "null"]:
        name, cluster_id = canonicalize_employer_name(placeholder)
        assert name == "Anonymous / Unspecified"
        assert cluster_id == "EMP-ANONYMOUS"


@pytest.mark.unit
def test_compute_employer_signature_extraction() -> None:
    """Verify employer signature extracts from various common payload dictionary keys."""
    p1 = {"employer": "Google India"}
    p2 = {"company": "Google India"}
    p3 = {"employer_name": "Google India"}
    p4 = {"company_name": "Google India"}

    assert compute_employer_signature(p1) == compute_employer_signature(p2)
    assert compute_employer_signature(p2) == compute_employer_signature(p3)
    assert compute_employer_signature(p3) == compute_employer_signature(p4)


@pytest.mark.unit
def test_compute_posting_signature() -> None:
    """Verify posting cluster calculation from explicit IDs and fallback composite."""
    # Explicit posting ID
    p1 = {"posting_id": "JOB-10203"}
    p2 = {"job_posting_id": "JOB-10203"}
    assert compute_posting_signature(p1, "EMP-123") == compute_posting_signature(p2, "EMP-123")
    assert compute_posting_signature(p1, "EMP-123").startswith("PST-")

    # Composite fallback
    comp1 = {
        "canonical_title": "Software Engineer",
        "location": "BENGALURU",
        "as_of_date": "2024-05-01",
    }
    comp2 = dict(comp1)
    sig1 = compute_posting_signature(comp1, "EMP-123")
    sig2 = compute_posting_signature(comp2, "EMP-123")
    assert sig1 == sig2

    # Different location yields different posting cluster
    comp3 = dict(comp1)
    comp3["location"] = "HYDERABAD"
    sig3 = compute_posting_signature(comp3, "EMP-123")
    assert sig1 != sig3


@pytest.mark.unit
def test_exact_deduplicator_streaming() -> None:
    """Verify ExactDeduplicator flags duplicates and tracks all entity clusters."""
    dedup = ExactDeduplicator(dedup_version="v0.1.0")

    rec_a = {
        "source_id": "SRC-INT-VOL-01",
        "role_family": "SWE",
        "canonical_title": "Software Engineer",
        "seniority": "MID",
        "location": "BENGALURU",
        "years_experience": 3.5,
        "guaranteed_cash_annual": 1800000.0,
        "employer": "Google India Pvt Ltd",
    }

    # First record: Original
    r1 = dedup.process_record("OBS-001", rec_a)
    assert not r1.is_exact_duplicate
    assert r1.exact_duplicate_of is None
    assert r1.person_cluster_size == 1
    assert r1.canonical_employer == "Google"
    assert r1.employer_cluster_id.startswith("EMP-")
    assert r1.posting_cluster_id.startswith("PST-")
    assert r1.exact_duplicate_cluster_id.startswith("DUP-")

    # Second record: Exact Duplicate
    r2 = dedup.process_record("OBS-002", rec_a)
    assert r2.is_exact_duplicate
    assert r2.exact_duplicate_of == "OBS-001"
    assert r2.record_signature == r1.record_signature
    assert r2.exact_duplicate_cluster_id == r1.exact_duplicate_cluster_id
    assert r2.person_cluster_id == r1.person_cluster_id
    assert r2.person_cluster_size == 2
    assert r2.employer_cluster_id == r1.employer_cluster_id

    # Third record: Different salary, but same person profile and employer
    rec_b = dict(rec_a)
    rec_b["guaranteed_cash_annual"] = 2200000.0
    r3 = dedup.process_record("OBS-003", rec_b)
    assert not r3.is_exact_duplicate
    assert r3.exact_duplicate_of is None
    assert r3.record_signature != r1.record_signature
    assert r3.employer_cluster_id == r1.employer_cluster_id

    assert dedup.total_seen == 2


@pytest.mark.unit
def test_deduplicate_records_df() -> None:
    """Verify batch Polars DataFrame deduplication and full entity cluster column additions."""
    df = pl.DataFrame(
        {
            "observation_id": ["OBS-1", "OBS-2", "OBS-3"],
            "source_id": ["SRC-A", "SRC-A", "SRC-B"],
            "role_family": ["SWE", "SWE", "MLAI"],
            "canonical_title": ["Software Engineer", "Software Engineer", "Data Scientist"],
            "seniority": ["MID", "MID", "SR"],
            "location": ["BENGALURU", "BENGALURU", "HYDERABAD"],
            "years_experience": [4.0, 4.0, 8.0],
            "guaranteed_cash_annual": [2000000.0, 2000000.0, 4000000.0],
            "basic_annual": [1000000.0, 1000000.0, 2000000.0],
            "hra_annual": [500000.0, 500000.0, 1000000.0],
            "special_allowance_annual": [500000.0, 500000.0, 1000000.0],
            "employer": ["Microsoft India", "Microsoft Corporation", "Amazon Development Center"],
            "as_of_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
        }
    )

    out_df = deduplicate_records_df(df, id_column="observation_id")

    assert out_df.height == 3
    expected_cols = [
        "record_signature",
        "is_exact_duplicate",
        "exact_duplicate_of",
        "exact_duplicate_cluster_id",
        "person_cluster_id",
        "person_cluster_size",
        "employer_cluster_id",
        "canonical_employer",
        "posting_cluster_id",
        "dedup_version",
    ]
    for col in expected_cols:
        assert col in out_df.columns, f"Missing column {col} in deduplicated DataFrame"

    is_dups = out_df["is_exact_duplicate"].to_list()
    dup_ofs = out_df["exact_duplicate_of"].to_list()
    person_sizes = out_df["person_cluster_size"].to_list()
    canonical_emps = out_df["canonical_employer"].to_list()
    emp_ids = out_df["employer_cluster_id"].to_list()

    assert is_dups == [False, True, False]
    assert dup_ofs == [None, "OBS-1", None]
    assert person_sizes == [2, 2, 1]
    assert canonical_emps == ["Microsoft", "Microsoft", "Amazon"]
    assert emp_ids[0] == emp_ids[1]
    assert emp_ids[0] != emp_ids[2]


@pytest.mark.unit
def test_deduplicate_records_df_empty() -> None:
    """Verify empty DataFrame handles cleanly with typed null columns."""
    df = pl.DataFrame({"observation_id": pl.Series([], dtype=pl.String)})
    out_df = deduplicate_records_df(df)
    assert out_df.height == 0
    assert "is_exact_duplicate" in out_df.columns
    assert "person_cluster_id" in out_df.columns
    assert "employer_cluster_id" in out_df.columns
    assert "posting_cluster_id" in out_df.columns


@pytest.mark.unit
def test_source_duplicate_reporting() -> None:
    """Verify source duplicate reporting accurately computes rates and cross-source duplicates."""
    df = pl.DataFrame(
        {
            "observation_id": ["OBS-1", "OBS-2", "OBS-3", "OBS-4", "OBS-5"],
            "source_id": [
                "SRC-INT-VOL-01",
                "SRC-INT-VOL-01",
                "SRC-INT-VOL-01",
                "SRC-KAG-SO-01",
                "SRC-KAG-SO-01",
            ],
            "role_family": ["SWE", "SWE", "DATA", "SWE", "MLAI"],
            "canonical_title": [
                "Software Engineer",
                "Software Engineer",
                "Data Analyst",
                "Software Engineer",
                "Machine Learning Engineer",
            ],
            "seniority": ["MID", "MID", "JR", "MID", "SR"],
            "location": ["BENGALURU", "BENGALURU", "PUNE", "BENGALURU", "HYDERABAD"],
            "years_experience": [4.0, 4.0, 2.0, 4.0, 6.0],
            "guaranteed_cash_annual": [2000000.0, 2000000.0, 1000000.0, 2000000.0, 3500000.0],
            "basic_annual": [1000000.0, 1000000.0, 500000.0, 1000000.0, 1750000.0],
            "hra_annual": [500000.0, 500000.0, 250000.0, 500000.0, 875000.0],
            "special_allowance_annual": [500000.0, 500000.0, 250000.0, 500000.0, 875000.0],
            "employer": ["Google", "Google", "Infosys", "Google", "NVIDIA"],
            "as_of_date": ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01"],
        }
    )

    report = compute_source_duplicate_report(df, id_column="observation_id")

    assert report.total_records == 5
    # Distinct: OBS-1, OBS-3, OBS-5 (OBS-2 intra-source dup of 1; OBS-4 cross-source dup of 1)
    assert report.distinct_records == 3
    assert report.total_exact_duplicates == 2
    assert report.overall_duplicate_rate == 0.40

    # Source metrics check
    source_map = {s.source_id: s for s in report.sources}
    assert "SRC-INT-VOL-01" in source_map
    assert "SRC-KAG-SO-01" in source_map

    vol_metrics = source_map["SRC-INT-VOL-01"]
    assert vol_metrics.total_records == 3
    assert vol_metrics.exact_duplicates == 1
    assert vol_metrics.distinct_records == 2
    assert vol_metrics.duplicate_rate == round(1 / 3, 4)
    assert vol_metrics.cross_source_duplicates == 0

    so_metrics = source_map["SRC-KAG-SO-01"]
    assert so_metrics.total_records == 2
    assert so_metrics.exact_duplicates == 1
    assert so_metrics.cross_source_duplicates == 1

    # DataFrame conversion
    report_df = report.to_dataframe()
    assert report_df.height == 2
    assert "duplicate_rate" in report_df.columns
    assert "cross_source_duplicates" in report_df.columns

    # Markdown generation
    md = generate_deduplication_report_markdown(report)
    assert "# CompIntel Data Quality: Deduplication and Entity Resolution Report" in md
    assert "SRC-INT-VOL-01" in md
    assert "SRC-KAG-SO-01" in md
    assert "Overall Duplicate Rate:" in md


@pytest.mark.unit
def test_deduplication_result_to_dict() -> None:
    """Verify DeduplicationResult converts to dictionary."""
    res = DeduplicationResult(
        observation_id="OBS-100",
        record_signature="abcd1234efgh5678",
        is_exact_duplicate=True,
        exact_duplicate_of="OBS-050",
        exact_duplicate_cluster_id="DUP-ABCD1234EFGH",
        person_cluster_id="PER-001",
        person_cluster_size=3,
        employer_cluster_id="EMP-12345",
        canonical_employer="Google",
        posting_cluster_id="PST-99999",
        dedup_version=DEFAULT_DEDUP_VERSION,
    )
    d = res.to_dict()
    assert d["observation_id"] == "OBS-100"
    assert d["is_exact_duplicate"] is True
    assert d["exact_duplicate_of"] == "OBS-050"
    assert d["exact_duplicate_cluster_id"] == "DUP-ABCD1234EFGH"
    assert d["employer_cluster_id"] == "EMP-12345"
    assert d["canonical_employer"] == "Google"
    assert d["posting_cluster_id"] == "PST-99999"
    assert d["person_cluster_size"] == 3
