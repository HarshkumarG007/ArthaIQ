"""Property-based tests for level mapping and ambiguity tracking (Rules R-UQ-01, R-MD-07).

Verifies invariants across seniority normalization:
1. Determinism: Same input signals always produce identical results.
2. Robustness: Never raises unhandled exceptions across arbitrary unicode text or float values.
3. Probability conservation: Soft label distributions strictly sum to 1.0.
4. Confidence bounds: Confidence is strictly in [0.0, 1.0].
5. Audit conservation: clean_mapped + ambiguous + unmapped == total_records == sum(seniority_counts).
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
import pytest

from compintel.normalization.levels import (
    DEFAULT_LEVEL_MAPPING_VERSION,
    LevelAmbiguityAudit,
    LevelMappingResult,
    map_level,
)
from compintel.schema.enums import SeniorityLevel


@pytest.mark.property
@given(
    title=st.text(max_size=100),
    explicit_lvl=st.one_of(st.none(), st.text(max_size=20)),
    yoe=st.one_of(st.none(), st.floats(min_value=-5.0, max_value=60.0, allow_nan=False)),
)
def test_level_mapping_robustness_and_invariants(
    title: str,
    explicit_lvl: str | None,
    yoe: float | None,
) -> None:
    """Invariant: map_level never crashes, bounds confidence in [0.0, 1.0], and sums soft labels to 1.0."""
    res = map_level(raw_title=title, explicit_level=explicit_lvl, years_experience=yoe)

    assert isinstance(res, LevelMappingResult)
    assert 0.0 <= res.confidence <= 1.0
    assert isinstance(res.seniority, SeniorityLevel)
    assert res.mapping_version == DEFAULT_LEVEL_MAPPING_VERSION

    # Soft label probability distribution sums to 1.0
    total_prob = sum(res.soft_labels.values())
    assert pytest.approx(total_prob, rel=1e-3, abs=1e-3) == 1.0

    # Probabilities must be non-negative
    assert all(p >= 0.0 for p in res.soft_labels.values())


@pytest.mark.property
@given(
    title=st.text(max_size=50),
    explicit_lvl=st.one_of(st.none(), st.text(max_size=10)),
    yoe=st.one_of(st.none(), st.floats(min_value=0.0, max_value=40.0, allow_nan=False)),
)
def test_level_mapping_determinism(
    title: str,
    explicit_lvl: str | None,
    yoe: float | None,
) -> None:
    """Invariant: map_level is strictly deterministic for identical inputs."""
    res1 = map_level(raw_title=title, explicit_level=explicit_lvl, years_experience=yoe)
    res2 = map_level(raw_title=title, explicit_level=explicit_lvl, years_experience=yoe)

    assert res1.seniority == res2.seniority
    assert res1.confidence == res2.confidence
    assert res1.is_ambiguous == res2.is_ambiguous
    assert res1.is_unmapped == res2.is_unmapped
    assert res1.mapping_method == res2.mapping_method
    assert res1.soft_labels == res2.soft_labels


@pytest.mark.property
@given(
    records=st.lists(
        st.tuples(
            st.text(max_size=40),
            st.one_of(st.none(), st.sampled_from(["L1", "L3", "L4", "L5", "L6"])),
            st.one_of(st.none(), st.floats(min_value=0.0, max_value=30.0, allow_nan=False)),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_audit_conservation_invariants(
    records: list[tuple[str, str | None, float | None]],
) -> None:
    """Invariant: Total audit records strictly equals clean + ambiguous + unmapped."""
    audit = LevelAmbiguityAudit()

    for title, lvl, yoe in records:
        res = map_level(raw_title=title, explicit_level=lvl, years_experience=yoe)
        audit.record_result(res)

    assert audit.total_records == len(records)
    assert audit.clean_mapped_count + audit.ambiguous_count + audit.unmapped_count == audit.total_records
    assert sum(audit.seniority_counts.values()) == audit.total_records
    assert 0.0 <= audit.ambiguity_rate <= 1.0
    assert 0.0 <= audit.unmapped_rate <= 1.0
