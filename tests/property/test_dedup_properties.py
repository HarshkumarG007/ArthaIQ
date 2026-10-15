"""Property-based tests for deduplication, entity resolution, and duplicate reporting.

Verifies invariants:
1. Signature determinism: Identical payload dictionary always produces identical signature.
2. Order invariance: Key ordering in dictionary does not change record signature.
3. Idempotence: Stream of N identical records yields 1 primary and N-1 duplicates.
4. Cluster universality: Every record receives valid non-empty cluster IDs.
5. DataFrame conservation: Height of deduplicated DataFrame equals input height.
6. Metric conservation: Sum of source records equals total records, rate in [0.0, 1.0].
"""

from __future__ import annotations

import random

import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from compintel.quality.dedup import (
    DEFAULT_DEDUP_VERSION,
    ExactDeduplicator,
    canonicalize_employer_name,
    compute_exact_record_signature,
    compute_source_duplicate_report,
    deduplicate_records_df,
)

sample_record_strategy = st.fixed_dictionaries(
    {
        "source_id": st.sampled_from(["SRC-INT-VOL-01", "SRC-SUP-CORP-01", "SRC-KAG-SO-01"]),
        "role_family": st.sampled_from(["SWE", "DATA", "MLAI", "OTHER"]),
        "canonical_title": st.sampled_from(
            ["Software Engineer", "Data Scientist", "DevOps Engineer"]
        ),
        "seniority": st.sampled_from(["JR", "MID", "SR", "STAFF"]),
        "location": st.sampled_from(["BENGALURU", "HYDERABAD", "PUNE"]),
        "years_experience": st.floats(min_value=0.0, max_value=30.0, allow_nan=False),
        "guaranteed_cash_annual": st.floats(
            min_value=300000.0, max_value=15000000.0, allow_nan=False
        ),
        "employer": st.sampled_from(
            [
                "Google India Pvt Ltd",
                "Microsoft Corporation",
                "Amazon Development Center",
                "Infosys Limited",
                "Acme Tech Pvt Ltd",
                None,
                "",
            ]
        ),
    }
)


@pytest.mark.property
@given(record=sample_record_strategy)
def test_signature_determinism_and_order_invariance(record: dict[str, object]) -> None:
    """Invariant: exact signature is strictly deterministic and key-order invariant."""
    sig1 = compute_exact_record_signature(record)
    sig2 = compute_exact_record_signature(record)

    # Shuffled key order
    keys = list(record.keys())
    random.shuffle(keys)
    shuffled_record = {k: record[k] for k in keys}
    sig3 = compute_exact_record_signature(shuffled_record)

    assert sig1 == sig2 == sig3
    assert len(sig1) == 64


@pytest.mark.property
@given(employer=st.one_of(st.none(), st.text(max_size=50)))
def test_employer_canonicalization_invariants(employer: str | None) -> None:
    """Invariant: canonicalize_employer_name produces valid EMP- cluster ID."""
    name1, id1 = canonicalize_employer_name(employer)
    name2, id2 = canonicalize_employer_name(employer)

    assert name1 == name2
    assert id1 == id2
    assert id1.startswith("EMP-")
    assert len(name1) > 0


@pytest.mark.property
@given(record=sample_record_strategy, count=st.integers(min_value=2, max_value=15))
def test_deduplicator_single_primary_invariant(record: dict[str, object], count: int) -> None:
    """Invariant: Stream of identical records yields exactly 1 primary and count-1 duplicates."""
    dedup = ExactDeduplicator(dedup_version=DEFAULT_DEDUP_VERSION)
    results = [dedup.process_record(f"OBS-{i}", record) for i in range(count)]

    assert len(results) == count
    # First is primary
    assert not results[0].is_exact_duplicate
    assert results[0].exact_duplicate_of is None

    # All subsequent are exact duplicates pointing to OBS-0
    for res in results[1:]:
        assert res.is_exact_duplicate
        assert res.exact_duplicate_of == "OBS-0"
        assert res.record_signature == results[0].record_signature
        assert res.exact_duplicate_cluster_id == results[0].exact_duplicate_cluster_id
        assert res.person_cluster_id == results[0].person_cluster_id
        assert res.employer_cluster_id == results[0].employer_cluster_id


@pytest.mark.property
@given(records=st.lists(sample_record_strategy, min_size=1, max_size=20))
def test_deduplicate_df_conservation_and_cluster_universality(
    records: list[dict[str, object]],
) -> None:
    """Invariant: preserves row count and assigns valid cluster IDs to every row."""
    df = pl.DataFrame(records).with_columns(
        pl.Series("observation_id", [f"ID-{i}" for i in range(len(records))])
    )
    out_df = deduplicate_records_df(df, id_column="observation_id")

    assert out_df.height == len(records)
    assert "person_cluster_id" in out_df.columns
    assert "employer_cluster_id" in out_df.columns
    assert "posting_cluster_id" in out_df.columns
    assert "exact_duplicate_cluster_id" in out_df.columns

    # Universality of cluster IDs (Rule R-DA-04, Task T3.10b done-condition)
    person_ids = out_df["person_cluster_id"].to_list()
    assert all(isinstance(cid, str) and cid.startswith("PER-") for cid in person_ids)

    emp_ids = out_df["employer_cluster_id"].to_list()
    assert all(isinstance(eid, str) and eid.startswith("EMP-") for eid in emp_ids)

    post_ids = out_df["posting_cluster_id"].to_list()
    assert all(isinstance(pid, str) and pid.startswith("PST-") for pid in post_ids)

    dup_cluster_ids = out_df["exact_duplicate_cluster_id"].to_list()
    assert all(isinstance(did, str) and did.startswith("DUP-") for did in dup_cluster_ids)


@pytest.mark.property
@given(records=st.lists(sample_record_strategy, min_size=1, max_size=25))
def test_source_duplicate_report_conservation(records: list[dict[str, object]]) -> None:
    """Invariant: Duplicate report reconciles row counts and maintains rate bounds [0.0, 1.0]."""
    df = pl.DataFrame(records).with_columns(
        pl.Series("observation_id", [f"ID-{i}" for i in range(len(records))])
    )
    report = compute_source_duplicate_report(df, id_column="observation_id")

    assert report.total_records == len(records)
    assert sum(s.total_records for s in report.sources) == len(records)
    assert 0.0 <= report.overall_duplicate_rate <= 1.0
    for s in report.sources:
        assert 0.0 <= s.duplicate_rate <= 1.0
        assert s.total_records == s.distinct_records + s.exact_duplicates
