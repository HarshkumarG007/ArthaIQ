"""Unit tests for compintel.career.effort (Task T15.18).

Verifies Rule R-CR-05 (Weekly Pacing & Effort Ranges), Rule R-CR-01 (Anti-Causal Invariants),
Rule R-UQ-01 / R-UI-02 (Zero Lone Numbers), and dual difficulty profile aggregations.
"""

from __future__ import annotations

import pytest

from compintel.career.effort import (
    DEFAULT_PACING_BUDGETS,
    estimate_role_transition_effort,
    estimate_transition_effort,
)
from compintel.career.engine import CareerEngine, FilesystemTaxonomyAdapter
from compintel.career.graph import load_data_family_graph
from compintel.career.rubric import HEURISTIC_DISCLAIMER, load_difficulty_rubrics
from compintel.career.schema import (
    CompetencyGraphManifest,
    DifficultyRubricsManifest,
    EvidenceLedger,
    EvidenceRecord,
    EvidenceType,
    RoleLevel,
    VerificationState,
)


@pytest.fixture(scope="module")
def data_graph() -> CompetencyGraphManifest:
    """Fixture providing cached DATA family competency DAG manifest."""
    return load_data_family_graph()


@pytest.fixture(scope="module")
def difficulty_rubrics() -> DifficultyRubricsManifest:
    """Fixture providing cached difficulty rubrics manifest."""
    return load_difficulty_rubrics()


def test_estimate_transition_effort_empty(
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify empty competency set returns zeroed effort estimate with disclaimer."""
    estimate = estimate_transition_effort(
        competency_ids=[],
        rubrics=difficulty_rubrics,
        target_role="Data Scientist",
        target_level=RoleLevel.LEVEL_3_MID,
    )

    assert estimate.target_role == "Data Scientist"
    assert estimate.target_level == RoleLevel.LEVEL_3_MID
    assert estimate.competency_count == 0
    assert estimate.cumulative_effort_range is None
    assert estimate.peak_learning_difficulty == 0.0
    assert estimate.mean_learning_difficulty == 0.0
    assert estimate.peak_application_difficulty == 0.0
    assert estimate.mean_application_difficulty == 0.0
    assert len(estimate.pacing_options) == 0
    assert estimate.is_heuristic is True
    assert estimate.disclaimer == HEURISTIC_DISCLAIMER


def test_estimate_transition_effort_single_node(
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify single competency estimate exactly matches calibrated rubric anchors."""
    # data.anl.l2_sql_basic: learning=2.0, application=2.0, effort=25-40h
    estimate = estimate_transition_effort(
        competency_ids=["data.anl.l2_sql_basic"],
        rubrics=difficulty_rubrics,
        target_role="Data Analyst",
        target_level=RoleLevel.LEVEL_2_JUNIOR,
    )

    assert estimate.competency_count == 1
    assert estimate.cumulative_effort_range is not None
    assert estimate.cumulative_effort_range.min_hours == 25
    assert estimate.cumulative_effort_range.max_hours == 40
    assert estimate.peak_learning_difficulty == 2.0
    assert estimate.mean_learning_difficulty == 2.0
    assert estimate.peak_application_difficulty == 2.0
    assert estimate.mean_application_difficulty == 2.0

    # Pacing options match 5, 10, 15, 20 h/wk
    pacing_map = {p.weekly_hours: p.estimated_weeks_range for p in estimate.pacing_options}
    assert pacing_map[5.0] == (5, 8)  # ceil(25/5)=5, ceil(40/5)=8
    assert pacing_map[10.0] == (3, 4)  # ceil(25/10)=3, ceil(40/10)=4
    assert pacing_map[15.0] == (2, 3)  # ceil(25/15)=2, ceil(40/15)=3
    assert pacing_map[20.0] == (2, 2)  # ceil(25/20)=2, ceil(40/20)=2


def test_estimate_transition_effort_multiple_nodes(
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify aggregation across multiple competencies computes conservative sums and means."""
    nodes = ["data.anl.l2_sql_basic", "data.anl.l3_sql_adv", "data.sci.l4_bigdata"]
    # sql_basic: 25-40h, learn=2.0, app=2.0
    # sql_adv: 30-50h, learn=3.0, app=3.0
    # bigdata: 50-90h, learn=4.0, app=5.0
    estimate = estimate_transition_effort(
        competency_ids=nodes,
        rubrics=difficulty_rubrics,
        target_role="Data Engineer",
        target_level=RoleLevel.LEVEL_4_SENIOR,
    )

    assert estimate.competency_count == 3
    assert estimate.cumulative_effort_range is not None
    assert estimate.cumulative_effort_range.min_hours == 25 + 30 + 50  # 105
    assert estimate.cumulative_effort_range.max_hours == 40 + 50 + 90  # 180

    assert estimate.peak_learning_difficulty == 4.0
    assert estimate.mean_learning_difficulty == 3.0  # (2.0 + 3.0 + 4.0) / 3
    assert estimate.peak_application_difficulty == 5.0
    assert estimate.mean_application_difficulty == round((2.0 + 3.0 + 5.0) / 3, 2)  # 3.33


def test_rejection_of_single_point_estimates(
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify Rule R-UQ-01 / R-UI-02: effort and duration estimates are strictly intervals."""
    estimate = estimate_transition_effort(
        competency_ids=["data.sci.l3_ml_supervised", "data.sci.l3_feat_eng"],
        rubrics=difficulty_rubrics,
    )

    # Cumulative effort is strictly an interval with min < max
    assert estimate.cumulative_effort_range is not None
    assert estimate.cumulative_effort_range.min_hours < estimate.cumulative_effort_range.max_hours

    # Every pacing option is strictly a tuple with non-negative bounds
    for pacing in estimate.pacing_options:
        w_min, w_max = pacing.estimated_weeks_range
        assert w_min <= w_max
        assert w_min >= 1


def test_pacing_monotone_scaling(
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify that weeks decrease monotonically with higher weekly study budget."""
    estimate = estimate_transition_effort(
        competency_ids=["data.sci.l4_bigdata", "data.sci.l4_causal"],
        rubrics=difficulty_rubrics,
        pacing_budgets=[5.0, 10.0, 20.0],
    )

    p_5 = [p for p in estimate.pacing_options if p.weekly_hours == 5.0][0]
    p_10 = [p for p in estimate.pacing_options if p.weekly_hours == 10.0][0]
    p_20 = [p for p in estimate.pacing_options if p.weekly_hours == 20.0][0]

    assert p_5.estimated_weeks_range[0] >= p_10.estimated_weeks_range[0]
    assert p_5.estimated_weeks_range[1] >= p_10.estimated_weeks_range[1]
    assert p_10.estimated_weeks_range[0] >= p_20.estimated_weeks_range[0]
    assert p_10.estimated_weeks_range[1] >= p_20.estimated_weeks_range[1]


def test_unknown_competency_raises_key_error(
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify unknown competency ID raises KeyError."""
    with pytest.raises(KeyError, match="not found in difficulty rubrics"):
        estimate_transition_effort(
            competency_ids=["nonexistent.competency.node"],
            rubrics=difficulty_rubrics,
        )


def test_invalid_pacing_budget_raises_value_error(
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify budget < 1.0 raises ValueError."""
    with pytest.raises(ValueError, match="at least 1.0"):
        estimate_transition_effort(
            competency_ids=["data.anl.l2_sql_basic"],
            rubrics=difficulty_rubrics,
            pacing_budgets=[0.5],
        )


def test_estimate_role_transition_effort_with_ledger(
    data_graph: CompetencyGraphManifest,
    difficulty_rubrics: DifficultyRubricsManifest,
) -> None:
    """Verify estimate_role_transition_effort accurately isolates gap competencies."""
    # Candidate already demonstrated Level 2 SQL and EDA
    records = {
        "data.anl.l2_sql_basic": EvidenceRecord(
            competency_id="data.anl.l2_sql_basic",
            state=VerificationState.DEMONSTRATED,
            evidence_type=EvidenceType.CODE_EXERCISE,
            recorded_at="2026-09-01T12:00:00Z",
        ),
        "data.anl.l2_eda": EvidenceRecord(
            competency_id="data.anl.l2_eda",
            state=VerificationState.DEMONSTRATED,
            evidence_type=EvidenceType.CODE_EXERCISE,
            recorded_at="2026-09-01T12:00:00Z",
        ),
    }
    ledger = EvidenceLedger(records=records, last_updated="2026-10-24T12:00:00Z")

    # Target: Junior Data Analyst (requires 5 level-2 competencies)
    estimate = estimate_role_transition_effort(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        graph=data_graph,
        rubrics=difficulty_rubrics,
        target_role="Junior Data Analyst",
    )

    # 5 total junior required - 2 demonstrated = 3 gap nodes
    assert estimate.competency_count == 3
    assert estimate.cumulative_effort_range is not None
    assert estimate.cumulative_effort_range.min_hours > 0
    assert len(estimate.pacing_options) == len(DEFAULT_PACING_BUDGETS)


def test_career_engine_estimate_effort_integration() -> None:
    """Verify CareerEngine exposes estimate_transition_effort cleanly."""
    adapter = FilesystemTaxonomyAdapter()
    engine = CareerEngine(taxonomy_port=adapter)

    empty_ledger = EvidenceLedger(records={}, last_updated="2026-10-24T12:00:00Z")
    estimate = engine.estimate_transition_effort(
        ledger=empty_ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        target_role="Junior Data Analyst",
        pacing_budgets=[5.0, 10.0, 20.0],
    )

    assert estimate.target_role == "Junior Data Analyst"
    assert estimate.target_level == RoleLevel.LEVEL_2_JUNIOR
    assert estimate.competency_count == 5
    assert estimate.cumulative_effort_range is not None
    assert estimate.peak_learning_difficulty >= 1.0
    assert estimate.peak_application_difficulty >= 1.0
    assert len(estimate.pacing_options) == 3
    assert estimate.is_heuristic is True
    assert estimate.disclaimer == HEURISTIC_DISCLAIMER
