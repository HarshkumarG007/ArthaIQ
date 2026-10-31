"""Unit tests for three-family career engine & taxonomy adapter routing (Task T19.05).

Verifies that FilesystemTaxonomyAdapter and CareerEngine seamlessly route across
DATA, SWE, and MLAI role families while preserving Rule R-CR-01 (Anti-Causal Invariants),
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
    """Fixture providing initialized three-family taxonomy adapter."""
    return FilesystemTaxonomyAdapter()


@pytest.fixture
def career_engine(taxonomy_adapter: FilesystemTaxonomyAdapter) -> CareerEngine:
    """Fixture providing CareerEngine initialized with three-family adapter."""
    return CareerEngine(taxonomy_port=taxonomy_adapter)


def test_adapter_loads_all_three_families(taxonomy_adapter: FilesystemTaxonomyAdapter) -> None:
    """Verify adapter loads DATA (14), SWE (15), and MLAI (15) graphs and rubrics."""
    data_graph = taxonomy_adapter.get_competency_graph("DATA")
    swe_graph = taxonomy_adapter.get_competency_graph("SWE")
    mlai_graph = taxonomy_adapter.get_competency_graph("MLAI")

    assert data_graph.role_family == "DATA"
    assert len(data_graph.nodes) == 14

    assert swe_graph.role_family == "SWE"
    assert len(swe_graph.nodes) == 15

    assert mlai_graph.role_family == "MLAI"
    assert len(mlai_graph.nodes) == 15

    data_rubrics = taxonomy_adapter.get_rubrics_manifest("DATA")
    swe_rubrics = taxonomy_adapter.get_rubrics_manifest("SWE")
    mlai_rubrics = taxonomy_adapter.get_rubrics_manifest("MLAI")

    assert data_rubrics.role_family == "DATA"
    assert len(data_rubrics.entries) == 14

    assert swe_rubrics.role_family == "SWE"
    assert len(swe_rubrics.entries) == 15

    assert mlai_rubrics.role_family == "MLAI"
    assert len(mlai_rubrics.entries) == 15


def test_node_and_rubric_lookup_mlai(taxonomy_adapter: FilesystemTaxonomyAdapter) -> None:
    """Verify individual node and rubric retrieval for MLAI competencies."""
    node = taxonomy_adapter.get_node("mlai.core.l3_transformer_attn", "MLAI")
    assert node is not None
    assert node.id == "mlai.core.l3_transformer_attn"
    assert "mlai.core.l2_neural_backprop" in node.prerequisite_ids

    rubric = taxonomy_adapter.get_rubric("mlai.core.l3_transformer_attn", "MLAI")
    assert rubric is not None
    assert rubric.is_heuristic is True
    assert rubric.learning_difficulty == 3.5
    assert rubric.application_difficulty == 3.5
    assert rubric.effort_hours.min_hours == 35
    assert rubric.effort_hours.max_hours == 60


def test_career_engine_mlai_graph_and_competency(career_engine: CareerEngine) -> None:
    """Verify CareerEngine methods for MLAI graph retrieval and competency resolution."""
    graph = career_engine.get_graph("MLAI")
    assert graph.role_family == "MLAI"
    assert len(graph.nodes) == 15

    node = career_engine.get_competency("mlai.ops.l4_dist_training", "MLAI")
    assert node.id == "mlai.ops.l4_dist_training"
    assert RoleLevel.LEVEL_4_SENIOR in node.target_levels

    with pytest.raises(KeyError, match="not found in 'MLAI' family taxonomy"):
        career_engine.get_competency("data.anl.l2_sql_basic", "MLAI")


def test_career_engine_mlai_gap_evaluation(career_engine: CareerEngine) -> None:
    """Verify CareerEngine gap evaluation against MLAI competency requirements."""
    # User has demonstrated linear algebra
    ledger = EvidenceLedger(
        records={
            "mlai.math.l2_linear_algebra": EvidenceRecord(
                competency_id="mlai.math.l2_linear_algebra",
                state=VerificationState.DEMONSTRATED,
                evidence_type=EvidenceType.CODE_EXERCISE,
                recorded_at="2026-10-25T10:00:00Z",
            )
        },
        last_updated="2026-10-31T12:00:00Z",
    )

    report = career_engine.evaluate_gap(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        family="MLAI",
        target_role="Machine Learning Engineer (Junior)",
    )

    assert report.total_required == 5
    assert report.demonstrated_count == 1
    # Neural backprop prerequisite is linear algebra, which is now demonstrated!
    assert "mlai.core.l2_neural_backprop" in report.actionable_gap_nodes
    assert "mlai.math.l2_convex_opt" in report.actionable_gap_nodes
    assert "mlai.ops.l2_model_registry" in report.actionable_gap_nodes
    assert "mlai.eval.l2_leakage_audit" in report.actionable_gap_nodes


def test_career_engine_mlai_roadmap_generation(career_engine: CareerEngine) -> None:
    """Verify CareerEngine topological roadmap generation for MLAI family."""
    ledger = EvidenceLedger(last_updated="2026-10-31T12:00:00Z")

    roadmap = career_engine.generate_roadmap(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        weekly_hours_budget=15.0,
        family="MLAI",
        target_role="Machine Learning Engineer (Junior)",
    )

    assert roadmap.total_milestones == 5
    assert roadmap.weekly_hours_budget == 15.0
    min_w, max_w = roadmap.estimated_total_weeks_range
    assert min_w < max_w

    # Linear algebra has no prerequisites and should be scheduled before neural backprop
    node_order = [m.competency_id for m in roadmap.milestones]
    assert "mlai.math.l2_linear_algebra" in node_order
    assert "mlai.core.l2_neural_backprop" in node_order
    assert node_order.index("mlai.math.l2_linear_algebra") < node_order.index(
        "mlai.core.l2_neural_backprop"
    )


def test_career_engine_mlai_transition_effort_estimate(career_engine: CareerEngine) -> None:
    """Verify cumulative effort ranges and difficulty profiles for MLAI transitions."""
    ledger = EvidenceLedger(last_updated="2026-10-31T12:00:00Z")

    effort = career_engine.estimate_transition_effort(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        family="MLAI",
        target_role="Machine Learning Engineer (Junior)",
        pacing_budgets=[10.0, 20.0],
    )

    assert effort.target_role == "Machine Learning Engineer (Junior)"
    assert effort.target_level == RoleLevel.LEVEL_2_JUNIOR
    assert effort.cumulative_effort_range.min_hours < effort.cumulative_effort_range.max_hours
    assert effort.cumulative_effort_range.min_hours >= 50
    assert len(effort.pacing_options) == 2
    assert effort.is_heuristic is True


def test_three_family_unsupported_family_error_handling(
    taxonomy_adapter: FilesystemTaxonomyAdapter, career_engine: CareerEngine
) -> None:
    """Verify unsupported family queries raise explicit ValueError with supported options."""
    with pytest.raises(ValueError, match="Occupational family 'CLOUD' is not supported"):
        taxonomy_adapter.get_competency_graph("CLOUD")

    with pytest.raises(ValueError, match="Occupational family 'UNKNOWN' is not supported"):
        career_engine.get_graph("UNKNOWN")
