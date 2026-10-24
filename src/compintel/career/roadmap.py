"""Topological roadmap scheduler for ArthaIQ Career Architect (Phase 15C).

Generates dependency-respecting learning plans partitioned by weekly available
hours budget, expressing effort strictly as heuristic ranges per Rule R-CR-05
and Rule R-CR-01 (Anti-Causal Invariants).
"""

from __future__ import annotations

import math
from typing import Final

from compintel.career.rubric import HEURISTIC_DISCLAIMER
from compintel.career.schema import (
    CompetencyGraphManifest,
    DifficultyRubricEntry,
    DifficultyRubricsManifest,
    EffortRange,
    RoadmapMilestone,
    RoleLevel,
    ScheduledRoadmap,
)
from compintel.career.validators import validate_graph_acyclicity

DEFAULT_WEEKLY_HOURS_BUDGET: Final[float] = 10.0


def calculate_weeks_range(effort: EffortRange, weekly_hours: float) -> tuple[int, int]:
    """Calculate discrete estimated weeks range from an effort range and weekly budget.

    Args:
        effort: Calibrated heuristic effort range [min_hours, max_hours].
        weekly_hours: Available study/practice budget in hours per week.

    Returns:
        Tuple of (min_weeks, max_weeks) where each is >= 1 and min_weeks <= max_weeks.

    Raises:
        ValueError: If weekly_hours is <= 0.
    """
    if weekly_hours <= 0:
        raise ValueError(f"weekly_hours must be strictly positive, got {weekly_hours}")

    if effort.min_hours == 0 and effort.max_hours == 0:
        return (0, 0)

    min_weeks = max(1, math.ceil(effort.min_hours / weekly_hours))
    max_weeks = max(1, math.ceil(effort.max_hours / weekly_hours))
    return (min_weeks, max_weeks)


def schedule_topological_roadmap(
    gap_nodes: list[str] | set[str],
    graph: CompetencyGraphManifest,
    rubrics: DifficultyRubricsManifest | dict[str, DifficultyRubricEntry],
    target_role: str = "Data Professional",
    target_level: RoleLevel = RoleLevel.LEVEL_3_MID,
    weekly_hours_budget: float = DEFAULT_WEEKLY_HOURS_BUDGET,
    custom_disclaimer: str | None = None,
) -> ScheduledRoadmap:
    """Generate deterministic, dependency-respecting learning roadmap for open gaps.

    Enforces Rule R-CR-05 (Weekly Pacing & Effort Ranges) and Rule R-CR-01 (Anti-Causal Invariants):
    1. Topologically orders gap nodes according to canonical DAG dependencies.
    2. Guarantees prerequisite order: if P in prereqs(M) and P in gap_nodes, step(P) < step(M).
    3. Calculates discrete milestone duration ranges based on weekly_hours_budget.
    4. Sums cumulative effort conservatively [sum(min_hours), sum(max_hours)].
    5. Computes total estimated weeks [max(1, ceil(sum_min/budget)), max(1, ceil(sum_max/budget))].
    6. Injects statutory HEURISTIC_DISCLAIMER on the schedule.

    Args:
        gap_nodes: Collection of competency node IDs requiring learning/verification.
        graph: Canonical competency graph manifest.
        rubrics: Calibrated difficulty rubrics manifest or dictionary mapping node_id to entry.
        target_role: Target role designation.
        target_level: Target seniority level.
        weekly_hours_budget: Available weekly learning/practice budget in hours.
        custom_disclaimer: Optional customized statutory disclaimer satisfying anti-causal rules.

    Returns:
        ScheduledRoadmap container with ordered milestones and cumulative effort bounds.
    """
    if weekly_hours_budget < 1.0:
        raise ValueError(
            f"weekly_hours_budget must be at least 1.0 hour/week, got {weekly_hours_budget}"
        )

    gap_set: set[str] = set(gap_nodes)
    node_map = {n.id: n for n in graph.nodes}

    # Verify all gap nodes exist in the graph
    for g_id in gap_set:
        if g_id not in node_map:
            raise KeyError(f"Gap competency '{g_id}' not found in competency graph.")

    # Topologically sort the graph and filter to only open gap nodes
    full_order = validate_graph_acyclicity(graph.nodes)
    ordered_gap_ids = [n_id for n_id in full_order if n_id in gap_set]

    disclaimer_text = custom_disclaimer or HEURISTIC_DISCLAIMER

    if not ordered_gap_ids:
        return ScheduledRoadmap(
            target_role=target_role,
            target_level=target_level,
            weekly_hours_budget=weekly_hours_budget,
            total_milestones=0,
            cumulative_effort_range=None,
            estimated_total_weeks_range=(0, 0),
            milestones=[],
            is_heuristic=True,
            disclaimer=disclaimer_text,
        )

    if isinstance(rubrics, DifficultyRubricsManifest):
        rubrics_by_id = {e.node_id: e for e in rubrics.entries}
    else:
        rubrics_by_id = rubrics

    milestones: list[RoadmapMilestone] = []
    total_min_hours: int = 0
    total_max_hours: int = 0

    for step_num, node_id in enumerate(ordered_gap_ids, start=1):
        node = node_map[node_id]
        rubric_entry = rubrics_by_id.get(node_id)

        if rubric_entry is not None:
            learning_diff = rubric_entry.learning_difficulty
            app_diff = rubric_entry.application_difficulty
            effort = rubric_entry.effort_hours
        else:
            learning_diff = node.difficulty.learning_difficulty
            app_diff = node.difficulty.application_difficulty
            effort = EffortRange(min_hours=15, max_hours=25)

        total_min_hours += effort.min_hours
        total_max_hours += effort.max_hours

        weeks_range = calculate_weeks_range(effort, weekly_hours_budget)

        milestones.append(
            RoadmapMilestone(
                step_number=step_num,
                competency_id=node.id,
                title=node.title,
                category=node.category,
                target_levels=node.target_levels,
                prerequisite_ids=node.prerequisite_ids,
                learning_difficulty=learning_diff,
                application_difficulty=app_diff,
                effort_range=effort,
                estimated_weeks_range=weeks_range,
            )
        )

    cumulative_effort = EffortRange(
        min_hours=total_min_hours,
        max_hours=total_max_hours,
    )
    total_min_weeks = max(1, math.ceil(total_min_hours / weekly_hours_budget))
    total_max_weeks = max(1, math.ceil(total_max_hours / weekly_hours_budget))

    return ScheduledRoadmap(
        target_role=target_role,
        target_level=target_level,
        weekly_hours_budget=weekly_hours_budget,
        total_milestones=len(milestones),
        cumulative_effort_range=cumulative_effort,
        estimated_total_weeks_range=(total_min_weeks, total_max_weeks),
        milestones=milestones,
        is_heuristic=True,
        disclaimer=disclaimer_text,
    )
