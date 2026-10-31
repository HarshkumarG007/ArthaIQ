"""Unit tests for compintel.career.engine (Task T15.15).

Verifies Hexagonal Architecture ports and adapters, filesystem taxonomy loading,
stub compensation adapter, honest abstentions, independent offline utility (Rule R-CR-14),
two-streams two-places isolation (Rule R-CR-02), and anti-causal invariants (Rule R-CR-01).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from compintel.career.engine import (
    CareerEngine,
    CompensationPort,
    FilesystemTaxonomyAdapter,
    StubCompensationAdapter,
    TaxonomyPort,
)
from compintel.career.schema import (
    CompensationEvidenceSummary,
    RoleLevel,
)


@pytest.fixture
def filesystem_taxonomy_adapter() -> FilesystemTaxonomyAdapter:
    """Fixture providing initialized filesystem taxonomy adapter."""
    return FilesystemTaxonomyAdapter()


@pytest.fixture
def stub_compensation_adapter() -> StubCompensationAdapter:
    """Fixture providing stub compensation adapter with registered test benchmarks."""
    adapter = StubCompensationAdapter()
    adapter.register_benchmark(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_3_MID,
        location="bangalore",
        summary=CompensationEvidenceSummary(
            role_family="DATA",
            seniority=RoleLevel.LEVEL_3_MID,
            location="bangalore",
            p10=14.5,
            p50=18.2,
            p90=24.8,
            interval_width=10.3,
            evidence_grade="High",
            sample_size=342,
            as_of_date="2026-10-24",
        ),
    )
    return adapter


def test_filesystem_taxonomy_adapter_protocol_conformance(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
) -> None:
    """Verify FilesystemTaxonomyAdapter conforms to TaxonomyPort protocol."""
    assert isinstance(filesystem_taxonomy_adapter, TaxonomyPort)

    manifest = filesystem_taxonomy_adapter.get_competency_graph("DATA")
    assert manifest.role_family == "DATA"
    assert len(manifest.nodes) == 14

    # Node lookup
    node = filesystem_taxonomy_adapter.get_node("data.anl.l3_sql_adv", "DATA")
    assert node is not None
    assert node.id == "data.anl.l3_sql_adv"
    assert RoleLevel.LEVEL_3_MID in node.target_levels

    # Rubric lookup
    rubric = filesystem_taxonomy_adapter.get_rubric("data.anl.l3_sql_adv")
    assert rubric is not None
    assert rubric.is_heuristic is True
    assert rubric.learning_difficulty == 3.0

    # All rubrics
    all_rubrics = filesystem_taxonomy_adapter.get_all_rubrics()
    assert len(all_rubrics) == 14
    assert "data.anl.l3_sql_adv" in all_rubrics


def test_filesystem_taxonomy_adapter_unsupported_family_error(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
) -> None:
    """Verify querying an unratified family raises ValueError."""
    with pytest.raises(ValueError, match="Occupational family 'DEVOPS' is not supported"):
        filesystem_taxonomy_adapter.get_competency_graph("DEVOPS")


def test_stub_compensation_adapter_protocol_conformance(
    stub_compensation_adapter: StubCompensationAdapter,
) -> None:
    """Verify StubCompensationAdapter conforms to CompensationPort protocol."""
    assert isinstance(stub_compensation_adapter, CompensationPort)

    # Registered cell
    evidence = stub_compensation_adapter.get_compensation_evidence(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_3_MID,
        location="bangalore",
    )
    assert evidence.p10 == 14.5
    assert evidence.p50 == 18.2
    assert evidence.p90 == 24.8
    assert evidence.evidence_grade == "High"
    assert evidence.abstention_reason is None

    # Unregistered cell -> honest abstention
    abstention = stub_compensation_adapter.get_compensation_evidence(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_4_SENIOR,
        location="coimbatore",
    )
    assert abstention.abstention_reason is not None
    assert "Sparse cell data support below minimum threshold" in abstention.abstention_reason
    assert abstention.evidence_grade == "Insufficient"
    assert abstention.p10 is None
    assert abstention.p50 is None
    assert abstention.p90 is None


def test_career_engine_initialization_and_properties(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
    stub_compensation_adapter: StubCompensationAdapter,
) -> None:
    """Verify CareerEngine dependency injection and exposed port properties."""
    engine = CareerEngine(
        taxonomy_port=filesystem_taxonomy_adapter,
        compensation_port=stub_compensation_adapter,
    )
    assert engine.taxonomy_port is filesystem_taxonomy_adapter
    assert engine.compensation_port is stub_compensation_adapter


def test_career_engine_competency_and_rubric_lookup(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
) -> None:
    """Verify CareerEngine retrieves graph nodes and rubrics, raising KeyError on misses."""
    engine = CareerEngine(taxonomy_port=filesystem_taxonomy_adapter)

    manifest = engine.get_graph("DATA")
    assert manifest.role_family == "DATA"

    node = engine.get_competency("data.anl.l2_eda")
    assert node.id == "data.anl.l2_eda"

    with pytest.raises(KeyError, match="Competency 'nonexistent.node' not found"):
        engine.get_competency("nonexistent.node")

    rubric = engine.get_rubric("data.anl.l2_eda")
    assert rubric.is_heuristic is True

    with pytest.raises(KeyError, match="Difficulty rubric for 'nonexistent.node' not found"):
        engine.get_rubric("nonexistent.node")


def test_career_engine_pay_evidence_decoupled_stream(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
    stub_compensation_adapter: StubCompensationAdapter,
) -> None:
    """Verify pay evidence is returned as a decoupled stream (Rule R-CR-02).

    Pay evidence contains empirical market quantiles and disclaimers, but no
    composite scoring or skill conditioning.
    """
    engine = CareerEngine(
        taxonomy_port=filesystem_taxonomy_adapter,
        compensation_port=stub_compensation_adapter,
    )
    pay_summary = engine.get_pay_evidence(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_3_MID,
        location="bangalore",
    )

    assert pay_summary.p50 == 18.2
    assert pay_summary.evidence_grade == "High"
    assert "Conditional statistical distribution benchmark" in pay_summary.disclaimer

    # Confirm model extra fields are forbidden (zero composite leakage)
    with pytest.raises(ValidationError):
        CompensationEvidenceSummary(  # type: ignore[call-arg]
            role_family="DATA",
            seniority=RoleLevel.LEVEL_3_MID,
            location="bangalore",
            composite_readiness_score=0.85,
        )


def test_career_engine_offline_independent_utility(
    filesystem_taxonomy_adapter: FilesystemTaxonomyAdapter,
) -> None:
    """Verify CareerEngine maintains 100% utility when compensation port is None (Rule R-CR-14)."""
    offline_engine = CareerEngine(
        taxonomy_port=filesystem_taxonomy_adapter,
        compensation_port=None,
    )

    # Competency graph fully functional
    node = offline_engine.get_competency("data.sci.l4_bigdata")
    assert "Distributed Big Data Processing with Spark" in node.title

    # Pay evidence query returns honest abstention rather than error
    pay_summary = offline_engine.get_pay_evidence(
        role_family="DATA",
        seniority=RoleLevel.LEVEL_4_SENIOR,
        location="hyderabad",
    )
    assert pay_summary.p50 is None
    assert pay_summary.evidence_grade == "Insufficient"
    assert pay_summary.abstention_reason is not None
    assert "offline local-first mode (Rule R-CR-14)" in pay_summary.abstention_reason


def test_anti_causal_disclaimer_validation_in_pay_evidence() -> None:
    """Verify Rule R-CR-01 and CPA 2019 reject causal pay claims in CompensationEvidenceSummary."""
    with pytest.raises(ValidationError, match="Prohibited causal compensation phrase detected"):
        CompensationEvidenceSummary(
            role_family="DATA",
            seniority=RoleLevel.LEVEL_3_MID,
            location="pune",
            p10=10.0,
            p50=15.0,
            p90=20.0,
            disclaimer="Completing this scenario raises compensation by 20%.",
        )


def test_monotonic_quantile_validation_in_pay_evidence() -> None:
    """Verify that quantiles must obey P10 <= P50 <= P90 when present."""
    with pytest.raises(ValidationError, match="Quantiles must be monotonically ordered"):
        CompensationEvidenceSummary(
            role_family="DATA",
            seniority=RoleLevel.LEVEL_3_MID,
            location="chennai",
            p10=25.0,
            p50=18.0,  # Invalid: P10 > P50
            p90=30.0,
        )
