"""Property-based tests for exact deduplication and person clustering (Task T3.10a).

Verifies invariants:
1. Signature determinism: Identical payload dictionary always produces identical signature.
2. Order invariance: Key ordering in dictionary does not change record signature.
3. Idempotence & single-origin: In a stream of N identical records, exactly 1 is primary and N-1 are duplicates.
4. Cluster validity: Every record receives a valid non-empty person_cluster_id starting with 'PER-'.
5. DataFrame conservation: Height of deduplicated DataFrame equals input DataFrame height.
"""

from __future__ import annotations

import random
from hypothesis import given
from hypothesis import strategies as st
import polars as pl
import pytest

from compintel.quality.dedup import (
    DEFAULT_DEDUP_VERSION,
    ExactDeduplicator,
    compute_exact_record_signature,
    compute_person_signature,
    deduplicate_records_df,
)

sample_record_strategy = st.fixed_dictionaries(
    {
        "source_id": st.sampled_from(["SRC-INT-VOL-01", "SRC-SUP-CORP-01", "SRC-KAG-SO-01"]),
        "role_family": st.sampled_from(["SWE", "DATA", "MLAI", "OTHER"]),
        "canonical_title": st.sampled_from(["Software Engineer", "Data Scientist", "DevOps Engineer"]),
        "seniority": st.sampled_from(["JR", "MID", "SR", "STAFF"]),
        "location": st.sampled_from(["BENGALURU", "HYDERABAD", "PUNE"]),
        "years_experience": st.floats(min_value=0.0, max_value=30.0, allow_nan=False),
        "guaranteed_cash_annual": st.floats(min_value=300000.0, max_value=15000000.0, allow_nan=False),
    }
)


@pytest.mark.property
@given(record=sample_record_strategy)
def test_signature_determinism_and_order_invariance(record: dict[str, object]) -> None:
    """Invariant: compute_exact_record_signature is strictly deterministic and key-order invariant."""
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
        assert res.person_cluster_id == results[0].person_cluster_id


@pytest.mark.property
@given(records=st.lists(sample_record_strategy, min_size=1, max_size=20))
def test_deduplicate_df_conservation(records: list[dict[str, object]]) -> None:
    """Invariant: deduplicate_records_df preserves row count and assigns valid cluster IDs."""
    df = pl.DataFrame(records).with_columns(
        pl.Series("observation_id", [f"ID-{i}" for i in range(len(records))])
    )
    out_df = deduplicate_records_df(df, id_column="observation_id")

    assert out_df.height == len(records)
    assert "person_cluster_id" in out_df.columns
    assert "is_exact_duplicate" in out_df.columns

    cluster_ids = out_df["person_cluster_id"].to_list()
    assert all(isinstance(cid, str) and cid.startswith("PER-") for cid in cluster_ids)

    sizes = out_df["person_cluster_size"].to_list()
    assert all(s >= 1 for s in sizes)
