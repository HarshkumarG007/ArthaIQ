"""Unit tests for Career Architect pay-to-role resolver (Phase 15C Task T15.19).

Verifies empirical quantile interval matching, zero extrapolation, honest abstention,
nearest grounded alternatives, decoupled port integration, and statutory anti-causal
disclaimers under Rules R-CR-01, R-CR-02, R-UQ-01, R-UI-02, and R-AI-01.
"""

from __future__ import annotations

import pytest

from compintel.career.engine import (
    CareerEngine,
    FilesystemTaxonomyAdapter,
    StubCompensationAdapter,
)
from compintel.career.pay_resolver import (
    calculate_interval_overlap,
    resolve_target_pay_to_roles,
)
from compintel.career.schema import (
    CompensationEvidenceSummary,
    PayCellMatchStatus,
    RoleLevel,
    validate_anti_causal_text,
)


@pytest.fixture
def stub_comp_adapter() -> StubCompensationAdapter:
    """Fixture providing deterministic grounded compensation benchmarks across levels."""
    adapter = StubCompensationAdapter()

    # Level 2 Junior Data Scientist: [P10=8.0, P50=12.0, P90=16.0]
    adapter.register_benchmark(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_2_JUNIOR,
        location="bangalore",
        summary=CompensationEvidenceSummary(
            role_family="DATA",
            seniority=RoleLevel.LEVEL_2_JUNIOR,
            location="bangalore",
            p10=8.0,
            p50=12.0,
            p90=16.0,
            interval_width=8.0,
            evidence_grade="High",
            sample_size=120,
            as_of_date="2026-10-24",
        ),
    )

    # Level 3 Mid Data Scientist: [P10=18.0, P50=24.0, P90=30.0]
    adapter.register_benchmark(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_3_MID,
        location="bangalore",
        summary=CompensationEvidenceSummary(
            role_family="DATA",
            seniority=RoleLevel.LEVEL_3_MID,
            location="bangalore",
            p10=18.0,
            p50=24.0,
            p90=30.0,
            interval_width=12.0,
            evidence_grade="High",
            sample_size=150,
            as_of_date="2026-10-24",
        ),
    )

    # Level 4 Senior Data Scientist: [P10=32.0, P50=42.0, P90=52.0]
    adapter.register_benchmark(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_4_SENIOR,
        location="bangalore",
        summary=CompensationEvidenceSummary(
            role_family="DATA",
            seniority=RoleLevel.LEVEL_4_SENIOR,
            location="bangalore",
            p10=32.0,
            p50=42.0,
            p90=52.0,
            interval_width=20.0,
            evidence_grade="Moderate",
            sample_size=80,
            as_of_date="2026-10-24",
        ),
    )

    return adapter


def test_calculate_interval_overlap_point_queries() -> None:
    """Verify interval overlap and status classification for scalar point queries."""
    # Point contained near center
    ratio, status = calculate_interval_overlap(24.0, 24.0, 18.0, 30.0)
    assert status == PayCellMatchStatus.CONTAINED
    assert ratio >= 0.90

    # Point near boundary (within 10% of span 12 -> margin 1.2; 31.0 is 1.0 above 30.0)
    ratio, status = calculate_interval_overlap(31.0, 31.0, 18.0, 30.0)
    assert status == PayCellMatchStatus.NEAR_BOUNDARY
    assert ratio == 0.0

    # Point completely out of bounds (45.0 is far above 30.0)
    ratio, status = calculate_interval_overlap(45.0, 45.0, 18.0, 30.0)
    assert status == PayCellMatchStatus.OUT_OF_BOUNDS
    assert ratio == 0.0


def test_calculate_interval_overlap_range_queries() -> None:
    """Verify interval overlap calculation for range queries."""
    # Overlapping ranges: [20.0, 25.0] and [18.0, 30.0]
    # Intersection: [20, 25] length 5; Union: [18, 30] length 12 -> ratio = 5/12 ~ 0.4167
    ratio, status = calculate_interval_overlap(20.0, 25.0, 18.0, 30.0)
    assert status == PayCellMatchStatus.CONTAINED
    assert 0.40 <= ratio <= 0.45

    # Completely disjoint range: [35.0, 40.0] and [18.0, 30.0]
    ratio, status = calculate_interval_overlap(35.0, 40.0, 18.0, 30.0)
    assert status == PayCellMatchStatus.OUT_OF_BOUNDS
    assert ratio == 0.0


def test_resolve_target_pay_contained_match(stub_comp_adapter: StubCompensationAdapter) -> None:
    """Verify resolving target pay finds grounded empirical cell with zero fabrication."""
    res = resolve_target_pay_to_roles(
        target_pay=25.0,
        compensation_port=stub_comp_adapter,
        location_filter="bangalore",
    )

    assert res.is_abstaining is False
    assert res.abstention_reason is None
    assert len(res.matched_cells) == 1

    match = res.matched_cells[0]
    assert match.seniority == RoleLevel.LEVEL_3_MID
    assert match.location == "bangalore"
    assert match.match_status == PayCellMatchStatus.CONTAINED
    assert match.compensation.p10 == 18.0
    assert match.compensation.p50 == 24.0
    assert match.compensation.p90 == 30.0
    assert match.distance_to_median_lpa == 1.0  # 25 - 24
    assert len(res.nearest_alternatives) == 0


def test_resolve_target_pay_range_multi_match(stub_comp_adapter: StubCompensationAdapter) -> None:
    """Verify interval query overlapping multiple seniorities returns ranked matches."""
    # Query [14.0, 20.0] LPA overlaps Junior [8, 16] and Mid [18, 30]
    res = resolve_target_pay_to_roles(
        target_pay=(14.0, 20.0),
        compensation_port=stub_comp_adapter,
        location_filter="bangalore",
    )

    assert res.is_abstaining is False
    assert len(res.matched_cells) == 2

    seniorities = [m.seniority for m in res.matched_cells]
    assert RoleLevel.LEVEL_2_JUNIOR in seniorities
    assert RoleLevel.LEVEL_3_MID in seniorities
    # Ranked by overlap ratio descending
    assert res.matched_cells[0].overlap_ratio >= res.matched_cells[1].overlap_ratio


def test_resolve_target_pay_zero_extrapolation_high(
    stub_comp_adapter: StubCompensationAdapter,
) -> None:
    """Verify target pay above empirical maximum triggers clean honest abstention."""
    # Query 120 LPA (highest empirical P90 is 52 LPA)
    res = resolve_target_pay_to_roles(
        target_pay=120.0,
        compensation_port=stub_comp_adapter,
        location_filter="bangalore",
    )

    assert res.is_abstaining is True
    assert res.abstention_reason is not None
    assert "exceeds maximum empirical P90" in res.abstention_reason
    assert "Zero extrapolation permitted" in res.abstention_reason
    assert len(res.matched_cells) == 0

    # Nearest alternatives must be identified
    assert len(res.nearest_alternatives) > 0
    # The nearest should be the highest grounded role (Senior)
    assert res.nearest_alternatives[0].seniority == RoleLevel.LEVEL_4_SENIOR


def test_resolve_target_pay_zero_extrapolation_low(
    stub_comp_adapter: StubCompensationAdapter,
) -> None:
    """Verify target pay below empirical entry level triggers clean honest abstention."""
    # Query 3.0 LPA (lowest empirical P10 is 8.0 LPA)
    res = resolve_target_pay_to_roles(
        target_pay=3.0,
        compensation_port=stub_comp_adapter,
        location_filter="bangalore",
    )

    assert res.is_abstaining is True
    assert res.abstention_reason is not None
    assert "is below minimum empirical P10" in res.abstention_reason
    assert "Zero extrapolation permitted" in res.abstention_reason
    assert len(res.matched_cells) == 0

    assert len(res.nearest_alternatives) > 0
    # The nearest should be the lowest grounded role (Junior)
    assert res.nearest_alternatives[0].seniority == RoleLevel.LEVEL_2_JUNIOR


def test_resolve_target_pay_empirical_gap_abstention(
    stub_comp_adapter: StubCompensationAdapter,
) -> None:
    """Verify target pay in an empirical distribution gap between cells abstains cleanly."""
    # Gap exists between Junior P90 (16.0) and Mid P10 (18.0) -> Point 17.0 falls in margin/gap
    # Query point 17.0 with exact bounds outside either cell [8, 16] and [18, 30]
    res = resolve_target_pay_to_roles(
        target_pay=(16.8, 17.2),
        compensation_port=stub_comp_adapter,
        location_filter="bangalore",
    )

    # Neither Junior [8, 16] nor Mid [18, 30] contains [16.8, 17.2]
    assert res.is_abstaining is True
    assert res.abstention_reason is not None
    assert "distribution gap" in res.abstention_reason
    assert len(res.nearest_alternatives) >= 2


def test_resolve_target_pay_unsupported_family(stub_comp_adapter: StubCompensationAdapter) -> None:
    """Verify unratified occupational family abstains per Rule R-CR-04."""
    res = resolve_target_pay_to_roles(
        target_pay=25.0,
        compensation_port=stub_comp_adapter,
        role_family="SWE",
    )

    assert res.is_abstaining is True
    assert res.abstention_reason is not None
    assert "Occupational family 'SWE' is not supported in MVP" in res.abstention_reason


def test_resolve_target_pay_sparse_location_abstains(
    stub_comp_adapter: StubCompensationAdapter,
) -> None:
    """Verify location with zero grounded cells cleanly abstains per Rule R-UQ-01."""
    res = resolve_target_pay_to_roles(
        target_pay=25.0,
        compensation_port=stub_comp_adapter,
        location_filter="chennai",  # Unregistered location
    )

    assert res.is_abstaining is True
    assert res.abstention_reason is not None
    assert "No empirically supported compensation cells found" in res.abstention_reason


def test_resolve_target_pay_invalid_arguments(stub_comp_adapter: StubCompensationAdapter) -> None:
    """Verify invalid target pay values raise descriptive exceptions."""
    with pytest.raises(ValueError, match="target_pay must be positive"):
        resolve_target_pay_to_roles(target_pay=-5.0, compensation_port=stub_comp_adapter)

    with pytest.raises(ValueError, match="target_pay must be positive"):
        resolve_target_pay_to_roles(target_pay=0.0, compensation_port=stub_comp_adapter)

    with pytest.raises(ValueError, match="min target_pay .* cannot exceed max target_pay"):
        resolve_target_pay_to_roles(target_pay=(30.0, 20.0), compensation_port=stub_comp_adapter)

    with pytest.raises(ValueError, match="interval must contain exactly 2 elements"):
        resolve_target_pay_to_roles(
            target_pay=(10.0, 20.0, 30.0), compensation_port=stub_comp_adapter
        )  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="must be float or tuple"):
        resolve_target_pay_to_roles(target_pay="twenty", compensation_port=stub_comp_adapter)  # type: ignore[arg-type]


@pytest.fixture
def filesystem_taxonomy_adapter() -> FilesystemTaxonomyAdapter:
    """Fixture providing initialized filesystem taxonomy adapter."""
    return FilesystemTaxonomyAdapter()


def test_career_engine_resolve_pay_offline_abstention(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
) -> None:
    """Verify CareerEngine without compensation port cleanly abstains per Rule R-CR-14."""
    engine = CareerEngine(taxonomy_port=filesystem_taxonomy_adapter, compensation_port=None)
    res = engine.resolve_pay_to_roles(target_pay=25.0)

    assert res.is_abstaining is True
    assert res.abstention_reason is not None
    assert "operating in offline requirements-first mode" in res.abstention_reason
    assert res.matched_cells == []


def test_career_engine_resolve_pay_with_port(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
    stub_comp_adapter: StubCompensationAdapter,
) -> None:
    """Verify CareerEngine delegates properly when compensation port is provided."""
    engine = CareerEngine(
        taxonomy_port=filesystem_taxonomy_adapter,
        compensation_port=stub_comp_adapter,
    )
    res = engine.resolve_pay_to_roles(target_pay=24.0, location_filter="bangalore")

    assert res.is_abstaining is False
    assert len(res.matched_cells) == 1
    assert res.matched_cells[0].seniority == RoleLevel.LEVEL_3_MID


def test_anti_causal_disclaimers_present(stub_comp_adapter: StubCompensationAdapter) -> None:
    """Verify statutory anti-causal disclaimers are present and pass compliance regex."""
    res = resolve_target_pay_to_roles(
        target_pay=25.0,
        compensation_port=stub_comp_adapter,
        location_filter="bangalore",
    )

    assert res.disclaimer is not None
    # Validate against forbidden causal patterns (Rule R-CR-01)
    validated = validate_anti_causal_text(res.disclaimer, "disclaimer")
    assert validated == res.disclaimer
