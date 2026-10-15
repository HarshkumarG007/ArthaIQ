"""Unit tests for deduplication and person record clustering (Task T3.10a)."""

from __future__ import annotations

import polars as pl
import pytest

from compintel.quality.dedup import (
    DEFAULT_DEDUP_VERSION,
    DeduplicationResult,
    ExactDeduplicator,
    compute_exact_record_signature,
    compute_person_signature,
    deduplicate_records_df,
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
def test_exact_deduplicator_streaming() -> None:
    """Verify ExactDeduplicator flags duplicates and tracks person clusters."""
    dedup = ExactDeduplicator(dedup_version="v0.1.0")

    rec_a = {
        "source_id": "SRC-INT-VOL-01",
        "role_family": "SWE",
        "canonical_title": "Software Engineer",
        "seniority": "MID",
        "location": "BENGALURU",
        "years_experience": 3.5,
        "guaranteed_cash_annual": 1800000.0,
    }

    # First record: Original
    r1 = dedup.process_record("OBS-001", rec_a)
    assert not r1.is_exact_duplicate
    assert r1.exact_duplicate_of is None
    assert r1.person_cluster_size == 1

    # Second record: Exact Duplicate
    r2 = dedup.process_record("OBS-002", rec_a)
    assert r2.is_exact_duplicate
    assert r2.exact_duplicate_of == "OBS-001"
    assert r2.record_signature == r1.record_signature
    assert r2.person_cluster_id == r1.person_cluster_id
    assert r2.person_cluster_size == 2

    # Third record: Different salary, but same person profile
    rec_b = dict(rec_a)
    rec_b["guaranteed_cash_annual"] = 2200000.0
    r3 = dedup.process_record("OBS-003", rec_b)
    assert not r3.is_exact_duplicate
    assert r3.exact_duplicate_of is None
    assert r3.record_signature != r1.record_signature

    assert dedup.total_seen == 2


@pytest.mark.unit
def test_deduplicate_records_df() -> None:
    """Verify batch Polars DataFrame deduplication and column additions."""
    df = pl.DataFrame(
        {
            "observation_id": ["OBS-1", "OBS-2", "OBS-3"],
            "source_id": ["SRC-A", "SRC-A", "SRC-A"],
            "role_family": ["SWE", "SWE", "MLAI"],
            "canonical_title": ["Software Engineer", "Software Engineer", "Data Scientist"],
            "seniority": ["MID", "MID", "SR"],
            "location": ["BENGALURU", "BENGALURU", "HYDERABAD"],
            "years_experience": [4.0, 4.0, 8.0],
            "guaranteed_cash_annual": [2000000.0, 2000000.0, 4000000.0],
            "basic_annual": [1000000.0, 1000000.0, 2000000.0],
            "hra_annual": [500000.0, 500000.0, 1000000.0],
            "special_allowance_annual": [500000.0, 500000.0, 1000000.0],
            "as_of_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
        }
    )

    out_df = deduplicate_records_df(df, id_column="observation_id")

    assert out_df.height == 3
    assert "record_signature" in out_df.columns
    assert "is_exact_duplicate" in out_df.columns
    assert "exact_duplicate_of" in out_df.columns
    assert "person_cluster_id" in out_df.columns
    assert "person_cluster_size" in out_df.columns

    is_dups = out_df["is_exact_duplicate"].to_list()
    dup_ofs = out_df["exact_duplicate_of"].to_list()
    person_sizes = out_df["person_cluster_size"].to_list()

    assert is_dups == [False, True, False]
    assert dup_ofs == [None, "OBS-1", None]
    assert person_sizes == [2, 2, 1]


@pytest.mark.unit
def test_deduplicate_records_df_empty() -> None:
    """Verify empty DataFrame handles cleanly."""
    df = pl.DataFrame({"observation_id": pl.Series([], dtype=pl.String)})
    out_df = deduplicate_records_df(df)
    assert out_df.height == 0
    assert "is_exact_duplicate" in out_df.columns
    assert "person_cluster_id" in out_df.columns


@pytest.mark.unit
def test_deduplication_result_to_dict() -> None:
    """Verify DeduplicationResult converts to dictionary."""
    res = DeduplicationResult(
        observation_id="OBS-100",
        record_signature="abcd1234efgh5678",
        is_exact_duplicate=True,
        exact_duplicate_of="OBS-050",
        person_cluster_id="PER-001",
        person_cluster_size=3,
        dedup_version=DEFAULT_DEDUP_VERSION,
    )
    d = res.to_dict()
    assert d["observation_id"] == "OBS-100"
    assert d["is_exact_duplicate"] is True
    assert d["exact_duplicate_of"] == "OBS-050"
    assert d["person_cluster_size"] == 3
