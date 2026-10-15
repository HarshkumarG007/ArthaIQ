"""Property-based tests for quarantine, count reconciliation, and halt threshold (Task T3.11).

Verifies invariants:
1. Strict row conservation: For ANY input dataset, Valid + Quarantined == Total (Rule R-DA-05).
2. Report reconciliation: Discrepancy count is strictly 0 and is_reconciled is strictly True.
3. Metric bounds: Quarantine rate is strictly bounded in [0.0, 1.0].
4. Evaluation determinism: Evaluation on identical payload yields identical decision and reason.
5. Entity validity: Every quarantined observation receives a valid deterministic 'QRN-' identifier.
"""

from __future__ import annotations

import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from compintel.quality.quarantine import (
    evaluate_record_quarantine,
    partition_and_quarantine_df,
)
from compintel.schema.enums import QuarantineReason, RoleFamily

arbitrary_record_strategy = st.fixed_dictionaries(
    {
        "source_id": st.sampled_from(["SRC-INT-VOL-01", "SRC-KAG-SO-01", "SRC-SUP-CORP-01"]),
        "role_family": st.sampled_from(
            [RoleFamily.SWE.value, RoleFamily.DATA.value, "OTHER", None]
        ),
        "canonical_title": st.sampled_from(["Software Engineer", "Data Scientist", "Unmapped"]),
        "seniority": st.sampled_from(["JR", "MID", "SR", "STAFF"]),
        "location": st.sampled_from(["BENGALURU", "HYDERABAD", "New York, USA", "UNKNOWN"]),
        "years_experience": st.one_of(
            st.none(),
            st.floats(min_value=-5.0, max_value=60.0, allow_nan=False),
        ),
        "guaranteed_cash_annual": st.one_of(
            st.none(),
            st.floats(min_value=-10.0, max_value=600.0, allow_nan=False),
        ),
        "employment_type": st.sampled_from(["full-time", "intern", "contractor", None]),
        "is_unbundled_aggregate": st.booleans(),
        "is_exact_duplicate": st.booleans(),
    }
)


@pytest.mark.property
@given(record=arbitrary_record_strategy)
def test_evaluate_record_determinism(record: dict[str, object]) -> None:
    """Invariant: Evaluation is strictly deterministic and side-effect free."""
    r1 = evaluate_record_quarantine(record)
    r2 = evaluate_record_quarantine(record)

    assert r1 == r2
    is_q, reason, detail = r1
    if is_q:
        assert isinstance(reason, QuarantineReason)
        assert detail is not None and len(detail) > 0
    else:
        assert reason is None
        assert detail is None


@pytest.mark.property
@given(records=st.lists(arbitrary_record_strategy, min_size=1, max_size=30))
def test_partition_and_quarantine_strict_conservation(
    records: list[dict[str, object]],
) -> None:
    """Invariant: Mathematical conservation Total == Valid + Quarantined (Rule R-DA-05)."""
    df = pl.DataFrame(records).with_columns(
        pl.Series("observation_id", [f"ID-{i}" for i in range(len(records))])
    )

    res = partition_and_quarantine_df(
        df,
        halt_threshold=1.0,  # Never halt during property testing to inspect full partition
        halt_on_exceed=False,
    )

    total_in = len(records)
    valid_out = res.valid_df.height
    quarantine_out = res.quarantined_df.height

    # Exact equality: Zero silent drops
    assert valid_out + quarantine_out == total_in
    assert res.report.total_input_records == total_in
    assert res.report.valid_accepted_records == valid_out
    assert res.report.quarantined_records == quarantine_out
    assert res.report.discrepancy_count == 0
    assert res.report.is_reconciled is True
    assert 0.0 <= res.report.quarantine_rate <= 1.0

    # Entity count matches quarantined height
    assert len(res.quarantine_records) == quarantine_out

    # Cluster/Quarantine identifier validation
    if quarantine_out > 0:
        q_ids = res.quarantined_df["quarantine_id"].to_list()
        assert all(isinstance(qid, str) and qid.startswith("QRN-") for qid in q_ids)
        assert all(len(qid) == 16 for qid in q_ids)
