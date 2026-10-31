"""Unit tests for multi-family career engine & taxonomy adapter (Task T16.05).

Verifies that FilesystemTaxonomyAdapter and CareerEngine support both DATA and SWE
role families seamlessly while maintaining Rule R-CR-01 (Anti-Causal Invariants),
Rule R-CR-02 (Two Streams, Two Places), Rule R-CR-03 (State Beats Score),
and Rule R-CR-05 (Calibrated Effort Rubrics).
"""

from __future__ import annotations

import pytest

from compintel.career.engine import CareerEngine, FilesystemTaxonomyAdapter
from compintel.career.schema import (
    EvidenceLedger,
    EvidenceRecord,
    EvidenceType,
    RoleLevel,
    VerificationState,
)


@pytest.fixture
def taxonomy_adapter() -> FilesystemTaxonomyAdapter:
    """Fixture providing initialized multi-family taxonomy adapter."""
    return FilesystemTaxonomyAdapter()


@pytest.fixture
def career_engine(taxonomy_adapter: FilesystemTaxonomyAdapter) -> CareerEngine:
    """Fixture providing CareerEngine initialized with multi-family adapter."""
    return CareerEngine(taxonomy_port=taxonomy_adapter)


def test_adapter_loads_both_families(taxonomy_adapter: FilesystemTaxonomyAdapter) -> None:
    """Verify adapter loads both DATA and SWE graphs and rubrics."""
    data_graph = taxonomy_adapter.get_competency_graph("DATA")
    swe_graph = taxonomy_adapter.get_competency_graph("SWE")

    assert data_graph.role_family == "DATA"
    assert len(data_graph.nodes) == 14

    assert swe_graph.role_family == "SWE"
    assert len(swe_graph.nodes) == 15

    data_rubrics = taxonomy_adapter.get_rubrics_manifest("DATA")
    swe_rubrics = taxonomy_adapter.get_rubrics_manifest("SWE")

    assert data_rubrics.role_family == "DATA"
    assert len(data_rubrics.entries) == 14

    assert swe_rubrics.role_family == "SWE"
    assert len(swe_rubrics.entries) == 15


def test_node_and_rubric_lookup_swe(taxonomy_adapter: FilesystemTaxonomyAdapter) -> None:
    """Verify individual node and rubric retrieval for SWE competencies."""
    node = taxonomy_adapter.get_node("swe.core.l2_concurrency", "SWE")
    assert node is not None
    assert node.id == "swe.core.l2_concurrency"
    assert "swe.core.l2_data_structures" in node.prerequisite_ids

    rubric = taxonomy_adapter.get_rubric("swe.core.l2_concurrency", "SWE")
    assert rubric is not None
    assert rubric.is_heuristic is True
    assert rubric.learning_difficulty == 3.0
    assert rubric.application_difficulty == 3.0
    assert rubric.effort_hours.min_hours == 25
    assert rubric.effort_hours.max_hours == 45


def test_career_engine_swe_graph_and_competency(career_engine: CareerEngine) -> None:
    """Verify CareerEngine methods for SWE graph retrieval and competency resolution."""
    graph = career_engine.get_graph("SWE")
    assert graph.role_family == "SWE"
    assert len(graph.nodes) == 15

    node = career_engine.get_competency("swe.sys.l4_dist_consensus", "SWE")
    assert node.id == "swe.sys.l4_dist_consensus"
    assert RoleLevel.LEVEL_4_SENIOR in node.target_levels

    with pytest.raises(KeyError, match="not found in 'SWE' family taxonomy"):
        career_engine.get_competency("data.anl.l2_sql_basic", "SWE")


def test_career_engine_swe_gap_evaluation(career_engine: CareerEngine) -> None:
    """Verify CareerEngine gap evaluation against SWE competency requirements."""
    # User has demonstrated Git hygiene, but no other SWE competencies
    ledger = EvidenceLedger(
        records={
            "swe.gen.l2_git_hygiene": EvidenceRecord(
                competency_id="swe.gen.l2_git_hygiene",
                state=VerificationState.DEMONSTRATED,
                evidence_type=EvidenceType.CODE_EXERCISE,
                recorded_at="2026-10-25T10:00:00Z",
            )
        },
        last_updated="2026-10-30T12:00:00Z",
    )

    report = career_engine.evaluate_gap(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        family="SWE",
        target_role="Software Engineer (Junior)",
    )

    assert report.total_required == 6
    assert report.demonstrated_count == 1
    # Core data structures is actionable because it has no prerequisites
    assert "swe.core.l2_data_structures" in report.actionable_gap_nodes
    # Concurrency is blocked because it depends on core data structures
    assert "swe.core.l2_concurrency" in report.blocked_gap_nodes


def test_career_engine_swe_roadmap_generation(career_engine: CareerEngine) -> None:
    """Verify CareerEngine topological roadmap generation for SWE family."""
    ledger = EvidenceLedger(last_updated="2026-10-30T12:00:00Z")

    roadmap = career_engine.generate_roadmap(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        weekly_hours_budget=15.0,
        family="SWE",
        target_role="Software Engineer (Junior)",
    )

    assert roadmap.total_milestones == 6
    assert roadmap.weekly_hours_budget == 15.0
    # Must have calibrated weeks range (min < max)
    min_w, max_w = roadmap.estimated_total_weeks_range
    assert min_w < max_w

    # First milestones must have no prerequisites
    first_step = roadmap.milestones[0]
    assert len(first_step.prerequisite_ids) == 0


def test_career_engine_swe_transition_effort_estimate(career_engine: CareerEngine) -> None:
    """Verify cumulative effort ranges and difficulty profiles for SWE transitions."""
    ledger = EvidenceLedger(last_updated="2026-10-30T12:00:00Z")

    effort = career_engine.estimate_transition_effort(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        family="SWE",
        target_role="Software Engineer (Junior)",
        pacing_budgets=[10.0, 20.0],
    )

    assert effort.target_role == "Software Engineer (Junior)"
    assert effort.target_level == RoleLevel.LEVEL_2_JUNIOR
    assert effort.cumulative_effort_range.min_hours < effort.cumulative_effort_range.max_hours
    assert effort.cumulative_effort_range.min_hours >= 50
    assert len(effort.pacing_options) == 2
    assert effort.is_heuristic is True


def test_unsupported_family_error_handling(
    taxonomy_adapter: FilesystemTaxonomyAdapter, career_engine: CareerEngine
) -> None:
    """Verify unsupported family queries raise explicit ValueError with supported options."""
    with pytest.raises(ValueError, match="Occupational family 'DEVOPS' is not supported"):
        taxonomy_adapter.get_competency_graph("DEVOPS")

    with pytest.raises(ValueError, match="Occupational family 'UNKNOWN' is not supported"):
        career_engine.get_graph("UNKNOWN")
