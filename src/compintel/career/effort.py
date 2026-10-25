"""Difficulty and heuristic effort estimator service for ArthaIQ Career Architect (Phase 15C).

Calculates cumulative heuristic effort ranges, dual difficulty profiles (learning
vs application), and multi-budget pacing projections for targeted competency transitions
under Rule R-CR-05 (Weekly Pacing & Effort Ranges), Rule R-CR-01 (Anti-Causal Invariants),
and Rule R-UQ-01 / R-UI-02 (Zero Lone Numbers).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Final

from compintel.career.gap import evaluate_competency_gap
from compintel.career.rubric import HEURISTIC_DISCLAIMER
from compintel.career.schema import (
    CompetencyGraphManifest,
    DifficultyRubricEntry,
    DifficultyRubricsManifest,
    EffortRange,
    EvidenceLedger,
    PacingOption,
    RoleLevel,
    TransitionEffortEstimate,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_PACING_BUDGETS: Final[list[float]] = [5.0, 10.0, 15.0, 20.0]


def estimate_transition_effort(
    competency_ids: Sequence[str] | set[str],
    rubrics: DifficultyRubricsManifest | dict[str, DifficultyRubricEntry],
    graph: CompetencyGraphManifest | None = None,
    target_role: str = "Data Professional",
    target_level: RoleLevel = RoleLevel.LEVEL_3_MID,
    pacing_budgets: Sequence[float] | None = None,
    custom_disclaimer: str | None = None,
) -> TransitionEffortEstimate:
    """Calculate cumulative heuristic effort range and dual difficulty profile for competencies.

    Enforces Rule R-CR-05 (Weekly Pacing & Effort Ranges) and Rule R-UQ-01 (Zero Lone Numbers):
    1. Expresses all effort strictly as calibrated intervals [min_hours, max_hours], never scalars.
    2. Computes both peak and mean learning and application difficulty.
    3. Projects discrete week intervals across requested weekly pacing budgets.
    4. Attaches mandatory statutory disclaimer.

    Args:
        competency_ids: Collection of competency node IDs targeted for transition.
        rubrics: Difficulty rubrics manifest or dictionary mapping node_id to entry.
        graph: Optional competency graph for validating competency node existence.
        target_role: Target role designation.
        target_level: Target seniority level.
        pacing_budgets: Sequence of weekly available hours budgets (default: 5, 10, 15, 20 h/wk).
        custom_disclaimer: Optional customized statutory disclaimer satisfying anti-causal rules.

    Returns:
        TransitionEffortEstimate with aggregate effort bounds, difficulty profile, and pacing.

    Raises:
        KeyError: If a requested competency is unknown to the rubrics repository.
        ValueError: If any pacing budget is <= 0.
    """
    budgets = list(pacing_budgets) if pacing_budgets is not None else DEFAULT_PACING_BUDGETS
    for b in budgets:
        if b < 1.0:
            raise ValueError(f"Weekly pacing budget must be at least 1.0 hour/week, got {b}")

    disclaimer_text = custom_disclaimer or HEURISTIC_DISCLAIMER

    target_ids = sorted(set(competency_ids))
    if not target_ids:
        return TransitionEffortEstimate(
            target_role=target_role,
            target_level=target_level,
            competency_count=0,
            cumulative_effort_range=None,
            peak_learning_difficulty=0.0,
            mean_learning_difficulty=0.0,
            peak_application_difficulty=0.0,
            mean_application_difficulty=0.0,
            pacing_options=[],
            is_heuristic=True,
            disclaimer=disclaimer_text,
        )

    if isinstance(rubrics, DifficultyRubricsManifest):
        rubrics_by_id = {e.node_id: e for e in rubrics.entries}
    else:
        rubrics_by_id = rubrics

    node_map = {n.id: n for n in graph.nodes} if graph is not None else {}

    entries: list[DifficultyRubricEntry] = []
    for c_id in target_ids:
        if c_id in rubrics_by_id:
            entries.append(rubrics_by_id[c_id])
        elif graph is not None and c_id in node_map:
            # Fallback to embedded difficulty in competency node
            node = node_map[c_id]
            entries.append(
                DifficultyRubricEntry(
                    node_id=node.id,
                    learning_difficulty=node.difficulty.learning_difficulty,
                    application_difficulty=node.difficulty.application_difficulty,
                    effort_hours=EffortRange(min_hours=15, max_hours=25),
                    learning_rationale="Estimated baseline from competency node configuration.",
                    application_rationale="Estimated baseline from competency node configuration.",
                    is_heuristic=True,
                    disclaimer=disclaimer_text,
                )
            )
        else:
            raise KeyError(
                f"Competency '{c_id}' not found in difficulty rubrics repository or graph."
            )

    total_min_hours = sum(e.effort_hours.min_hours for e in entries)
    total_max_hours = sum(e.effort_hours.max_hours for e in entries)
    cumulative_effort = EffortRange(min_hours=total_min_hours, max_hours=total_max_hours)

    learning_diffs = [e.learning_difficulty for e in entries]
    app_diffs = [e.application_difficulty for e in entries]

    peak_learning = round(max(learning_diffs), 2)
    mean_learning = round(sum(learning_diffs) / len(learning_diffs), 2)
    peak_app = round(max(app_diffs), 2)
    mean_app = round(sum(app_diffs) / len(app_diffs), 2)

    pacing_options: list[PacingOption] = []
    for budget in budgets:
        min_weeks = max(1, math.ceil(total_min_hours / budget))
        max_weeks = max(1, math.ceil(total_max_hours / budget))
        pacing_options.append(
            PacingOption(
                weekly_hours=budget,
                estimated_weeks_range=(min_weeks, max_weeks),
            )
        )

    return TransitionEffortEstimate(
        target_role=target_role,
        target_level=target_level,
        competency_count=len(entries),
        cumulative_effort_range=cumulative_effort,
        peak_learning_difficulty=peak_learning,
        mean_learning_difficulty=mean_learning,
        peak_application_difficulty=peak_app,
        mean_application_difficulty=mean_app,
        pacing_options=pacing_options,
        is_heuristic=True,
        disclaimer=disclaimer_text,
    )


def estimate_role_transition_effort(
    ledger: EvidenceLedger,
    target_level: RoleLevel,
    graph: CompetencyGraphManifest,
    rubrics: DifficultyRubricsManifest | dict[str, DifficultyRubricEntry],
    target_role: str = "Data Professional",
    pacing_budgets: Sequence[float] | None = None,
) -> TransitionEffortEstimate:
    """Evaluate candidate evidence ledger against target role and estimate transition effort.

    Combines gap evaluation with multi-budget effort estimation under Rule R-CR-05.
    """
    gap_report = evaluate_competency_gap(
        ledger=ledger,
        target_level=target_level,
        graph=graph,
        target_role=target_role,
    )

    return estimate_transition_effort(
        competency_ids=gap_report.gap_nodes,
        rubrics=rubrics,
        graph=graph,
        target_role=target_role,
        target_level=target_level,
        pacing_budgets=pacing_budgets,
    )
