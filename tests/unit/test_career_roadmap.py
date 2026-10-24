"""Unit and property-based tests for compintel.career.roadmap (Task T15.17).

Verifies Rule R-CR-05 (Weekly Pacing & Effort Ranges), Rule R-CR-01 (Anti-Causal Invariants),
and core mathematical properties (DAG Precedence, Range Additivity, Budget Monotonicity)
using deterministic unit tests and Hypothesis property-based testing.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from compintel.career.engine import CareerEngine, FilesystemTaxonomyAdapter
from compintel.career.graph import load_data_family_graph
from compintel.career.roadmap import (
    calculate_weeks_range,
    schedule_topological_roadmap,
)
from compintel.career.rubric import HEURISTIC_DISCLAIMER, load_difficulty_rubrics
from compintel.career.schema import (
    CompetencyGraphManifest,
    DifficultyRubricsManifest,
    EffortRange,
    EvidenceLedger,
    RoleLevel,
)

DATA_NODE_IDS = [
    "data.anl.l2_eda",
    "data.anl.l2_hygiene",
    "data.anl.l2_sql_basic",
    "data.anl.l3_dashboard",
    "data.anl.l3_sql_adv",
    "data.gen.l2_ethics",
    "data.gen.l2_prob_decomp",
    "data.gen.l3_docs",
    "data.gen.l3_stakeholder",
    "data.sci.l3_exp_design",
    "data.sci.l3_feat_eng",
    "data.sci.l3_ml_supervised",
    "data.sci.l4_bigdata",
    "data.sci.l4_causal",
]


@pytest.fixture(scope="module")
def data_graph() -> CompetencyGraphManifest:
    """Fixture providing cached DATA family competency DAG manifest."""
    return load_data_family_graph()


@pytest.fixture(scope="module")
def difficulty_rubrics() -> DifficultyRubricsManifest:
    """Fixture providing cached difficulty rubrics manifest."""
    return load_difficulty_rubrics()


def test_calculate_weeks_range() -> None:
    """Verify discrete estimated weeks range calculation."""
    # 15-25 hours at 10h/week -> (2, 3) weeks
    effort = EffortRange(min_hours=15, max_hours=25)
    w_min, w_max = calculate_weeks_range(effort, weekly_hours=10.0)
    assert w_min == 2
    assert w_max == 3

    # 30-50 hours at 5h/week -> (6, 10) weeks
    effort2 = EffortRange(min_hours=30, max_hours=50)
    w_min2, w_max2 = calculate_weeks_range(effort2, weekly_hours=5.0)
    assert w_min2 == 6
    assert w_max2 == 10

    # Minimal effort (1, 2) hours
    min_effort = EffortRange(min_hours=1, max_hours=2)
    assert calculate_weeks_range(min_effort, weekly_hours=10.0) == (1, 1)

    # Invalid budget <= 0 raises ValueError
    with pytest.raises(ValueError, match="strictly positive"):
        calculate_weeks_range(effort, weekly_hours=0.0)


def test_schedule_topological_roadmap_empty_gaps(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify scheduling with zero gaps returns empty roadmap with disclaimer."""
    roadmap = schedule_topological_roadmap(
        gap_nodes=[],
        graph=data_graph,
        rubrics=difficulty_rubrics,
        target_role="Data Scientist",
        target_level=RoleLevel.LEVEL_3_MID,
        weekly_hours_budget=10.0,
    )

    assert roadmap.total_milestones == 0
    assert len(roadmap.milestones) == 0
    assert roadmap.cumulative_effort_range is None
    assert roadmap.estimated_total_weeks_range == (0, 0)
    assert roadmap.is_heuristic is True
    assert roadmap.disclaimer == HEURISTIC_DISCLAIMER


def test_schedule_topological_roadmap_prerequisite_ordering(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify milestones strictly follow topological dependency ordering."""
    test_gaps = [
        "data.sci.l4_bigdata",
        "data.anl.l2_sql_basic",
        "data.anl.l3_sql_adv",
        "data.anl.l2_hygiene",
    ]
    roadmap = schedule_topological_roadmap(
        gap_nodes=test_gaps,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=10.0,
    )

    assert roadmap.total_milestones == 4
    step_map = {m.competency_id: m.step_number for m in roadmap.milestones}

    # Basic SQL must precede Hygiene and Advanced SQL
    assert step_map["data.anl.l2_sql_basic"] < step_map["data.anl.l2_hygiene"]
    assert step_map["data.anl.l2_sql_basic"] < step_map["data.anl.l3_sql_adv"]
    # Advanced SQL must precede Big Data
    assert step_map["data.anl.l3_sql_adv"] < step_map["data.sci.l4_bigdata"]


def test_pacing_duration_scaling(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify that lower weekly budget yields monotonically longer week durations."""
    test_gaps = ["data.anl.l2_sql_basic", "data.anl.l3_sql_adv"]

    r_5h = schedule_topological_roadmap(
        gap_nodes=test_gaps,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=5.0,
    )
    r_10h = schedule_topological_roadmap(
        gap_nodes=test_gaps,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=10.0,
    )
    r_20h = schedule_topological_roadmap(
        gap_nodes=test_gaps,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=20.0,
    )

    # 5h/week duration >= 10h/week duration >= 20h/week duration
    assert r_5h.estimated_total_weeks_range[0] >= r_10h.estimated_total_weeks_range[0]
    assert r_5h.estimated_total_weeks_range[1] >= r_10h.estimated_total_weeks_range[1]
    assert r_10h.estimated_total_weeks_range[0] >= r_20h.estimated_total_weeks_range[0]
    assert r_10h.estimated_total_weeks_range[1] >= r_20h.estimated_total_weeks_range[1]


def test_invalid_weekly_hours_budget(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify weekly_hours_budget < 1.0 raises ValueError."""
    with pytest.raises(ValueError, match="at least 1.0"):
        schedule_topological_roadmap(
            gap_nodes=["data.anl.l2_sql_basic"],
            graph=data_graph,
            rubrics=difficulty_rubrics,
            weekly_hours_budget=0.5,
        )


def test_career_engine_generate_roadmap_integration() -> None:
    """Verify CareerEngine exposes end-to-end generate_roadmap cleanly."""
    adapter = FilesystemTaxonomyAdapter()
    engine = CareerEngine(taxonomy_port=adapter)

    empty_ledger = EvidenceLedger(records={}, last_updated="2026-10-24T12:00:00Z")
    roadmap = engine.generate_roadmap(
        ledger=empty_ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        weekly_hours_budget=10.0,
        target_role="Junior Data Analyst",
    )

    assert roadmap.target_role == "Junior Data Analyst"
    assert roadmap.target_level == RoleLevel.LEVEL_2_JUNIOR
    assert roadmap.total_milestones > 0
    assert roadmap.weekly_hours_budget == 10.0
    assert roadmap.estimated_total_weeks_range[0] >= 1
    assert roadmap.is_heuristic is True
    assert roadmap.disclaimer == HEURISTIC_DISCLAIMER


# ==============================================================================
# Property-Based Testing (Hypothesis) for Core Mathematical Invariants
# ==============================================================================


@settings(max_examples=50, deadline=None)
@given(
    gap_subset=st.lists(st.sampled_from(DATA_NODE_IDS), min_size=1, unique=True),
    budget=st.floats(min_value=1.0, max_value=40.0),
)
def test_property_dag_precedence_guarantee(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
    gap_subset: list[str],
    budget: float,
) -> None:
    """Invariant 1: For all milestones, any open prerequisite has step(P) < step(M)."""
    roadmap = schedule_topological_roadmap(
        gap_nodes=gap_subset,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=budget,
    )

    step_map = {m.competency_id: m.step_number for m in roadmap.milestones}

    for milestone in roadmap.milestones:
        for prereq_id in milestone.prerequisite_ids:
            if prereq_id in step_map:
                assert step_map[prereq_id] < milestone.step_number


@settings(max_examples=50, deadline=None)
@given(
    gap_subset=st.lists(st.sampled_from(DATA_NODE_IDS), min_size=1, unique=True),
    budget=st.floats(min_value=1.0, max_value=40.0),
)
def test_property_range_additivity_and_ordering(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
    gap_subset: list[str],
    budget: float,
) -> None:
    """Invariant 2: Cumulative effort range strictly matches conservative sum of milestones."""
    roadmap = schedule_topological_roadmap(
        gap_nodes=gap_subset,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=budget,
    )

    expected_min = sum(m.effort_range.min_hours for m in roadmap.milestones)
    expected_max = sum(m.effort_range.max_hours for m in roadmap.milestones)

    assert roadmap.cumulative_effort_range is not None
    assert roadmap.cumulative_effort_range.min_hours == expected_min
    assert roadmap.cumulative_effort_range.max_hours == expected_max
    assert roadmap.cumulative_effort_range.min_hours <= roadmap.cumulative_effort_range.max_hours

    # Discrete weeks bounds ordering
    w_min, w_max = roadmap.estimated_total_weeks_range
    assert w_min <= w_max
    assert w_min >= 1


@settings(max_examples=40, deadline=None)
@given(
    gap_subset=st.lists(st.sampled_from(DATA_NODE_IDS), min_size=1, unique=True),
    budget_low=st.floats(min_value=1.0, max_value=10.0),
    budget_multiplier=st.floats(min_value=1.5, max_value=4.0),
)
def test_property_budget_monotonicity(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
    gap_subset: list[str],
    budget_low: float,
    budget_multiplier: float,
) -> None:
    """Invariant 3: Higher weekly budget never increases estimated total weeks."""
    budget_high = budget_low * budget_multiplier

    r_low = schedule_topological_roadmap(
        gap_nodes=gap_subset,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=budget_low,
    )
    r_high = schedule_topological_roadmap(
        gap_nodes=gap_subset,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        weekly_hours_budget=budget_high,
    )

    assert r_low.estimated_total_weeks_range[0] >= r_high.estimated_total_weeks_range[0]
    assert r_low.estimated_total_weeks_range[1] >= r_high.estimated_total_weeks_range[1]
