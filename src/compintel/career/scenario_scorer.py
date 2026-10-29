"""Deterministic Rubric Scoring Engine for Practice Scenarios (Phase 15D, Task T15.23).

Adheres strictly to:
- ADR-0010 & Rule R-CR-15: Zero runtime Large Language Models on serving or scoring path.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit,
  false-flag penalties, and per-competency evidence generation.
- Rule R-CR-03: State beats score (successful attempts award 'Demonstrated' verification state).
- Rule R-CR-11: Practice, not certification (no exam or credential terminology).
- Rule R-CD-01: Strict type annotations, frozen models, full validation.
- Rule R-CD-03: Hexagonal architecture: Career only imports schema.
"""

from __future__ import annotations

from compintel.career.scenario_schema import (
    CandidateFlagSubmission,
    ClientScenarioChallenge,
    FalseFlagRecord,
    PracticeScenario,
    ScenarioAttemptEvaluation,
    ScenarioAttemptSubmission,
    ScenarioRubric,
    ScoredDefectResult,
)


def _resolve_scenario_rubric(
    scenario: PracticeScenario,
    variant_id: str | None,
) -> tuple[ScenarioRubric, str | None]:
    """Resolve active rubric considering optional variant overrides.

    Args:
        scenario: Full practice scenario.
        variant_id: Optional variant ID.

    Returns:
        Tuple of (active_rubric, effective_variant_id).

    Raises:
        ValueError: If variant_id is specified but not present in scenario.variants.
    """
    if variant_id is None:
        return scenario.rubric, None

    for variant in scenario.variants:
        if variant.variant_id == variant_id:
            rubric = variant.rubric_override or scenario.rubric
            return rubric, variant_id

    raise ValueError(f"Variant '{variant_id}' not found in scenario '{scenario.id}'")


def evaluate_scenario_attempt(
    scenario: PracticeScenario,
    submission: ScenarioAttemptSubmission,
    variant_id: str | None = None,
) -> ScenarioAttemptEvaluation:
    """Deterministically score a candidate practice attempt against the scenario rubric.

    Implements ADR-0013 deterministic scoring algorithm:
    1. Full match (100% points): Exact line match AND exact defect category match.
    2. Partial match (50% points):
       - Exact line match with misidentified category, OR
       - Adjacent line match (+/- 1 line) with exact category match.
    3. False flag penalty:
       - Every uncredited flag incurs penalty_per_flag up to max_penalty.
    4. Bounded net score:
       - final_score = max(0.0, min(max_possible_score, gross_points - penalty))
    5. Competency evidence unlocking:
       - If final_score >= pass_threshold_score, returns primary competency ID
         plus IDs of all detected flaws.
       - If failed, returns empty demonstrated competencies list (Rule R-CR-03).

    Args:
        scenario: Full server-side practice scenario containing ground truth.
        submission: Candidate submission with flagged lines and categories.
        variant_id: Optional variant ID overriding submission.variant_id.

    Returns:
        ScenarioAttemptEvaluation containing granular rubric breakdown.

    Raises:
        ValueError: If submission scenario_id does not match scenario.id or variant is invalid.
    """
    if submission.scenario_id != scenario.id:
        raise ValueError(
            f"Submission scenario_id '{submission.scenario_id}' does not match "
            f"target scenario '{scenario.id}'"
        )

    effective_variant_id = variant_id if variant_id is not None else submission.variant_id
    active_rubric, matched_variant_id = _resolve_scenario_rubric(scenario, effective_variant_id)

    # Track matched status for candidates and defects
    matched_flags: set[int] = set()
    defect_matches: dict[str, tuple[CandidateFlagSubmission, float, bool, bool]] = {}

    flags = submission.flags
    defects = active_rubric.defects

    # Pass 1: Exact line AND exact category (100% full credit)
    for defect in defects:
        for idx, flag in enumerate(flags):
            if idx in matched_flags:
                continue
            if flag.line_number == defect.line_number and flag.selected_category == defect.category:
                matched_flags.add(idx)
                defect_matches[defect.id] = (flag, defect.points, True, True)
                break

    # Pass 2: Partial credit (50% points)
    # Check exact line with category mismatch first, then adjacent line with category match
    for defect in defects:
        if defect.id in defect_matches:
            continue
        # Sub-pass 2A: Exact line, category mismatch
        for idx, flag in enumerate(flags):
            if idx in matched_flags:
                continue
            if flag.line_number == defect.line_number and flag.selected_category != defect.category:
                matched_flags.add(idx)
                defect_matches[defect.id] = (flag, round(0.5 * defect.points, 2), True, False)
                break
        if defect.id in defect_matches:
            continue
        # Sub-pass 2B: Adjacent line (+/- 1), category match
        for idx, flag in enumerate(flags):
            if idx in matched_flags:
                continue
            if (
                abs(flag.line_number - defect.line_number) == 1
                and flag.selected_category == defect.category
            ):
                matched_flags.add(idx)
                defect_matches[defect.id] = (flag, round(0.5 * defect.points, 2), False, True)
                break

    # Construct granular defect results in rubric order
    defect_results: list[ScoredDefectResult] = []
    total_awarded_points = 0.0

    for defect in defects:
        if defect.id in defect_matches:
            _, pts, line_m, cat_m = defect_matches[defect.id]
            total_awarded_points += pts
            defect_results.append(
                ScoredDefectResult(
                    defect_id=defect.id,
                    target_line_number=defect.line_number,
                    detected=True,
                    line_matched=line_m,
                    category_matched=cat_m,
                    awarded_points=pts,
                    max_points=defect.points,
                    severity=defect.severity,
                    title=defect.title,
                    consequence=defect.consequence,
                    diagnostic_explanation=defect.diagnostic_explanation,
                    competency_id=defect.competency_id,
                )
            )
        else:
            defect_results.append(
                ScoredDefectResult(
                    defect_id=defect.id,
                    target_line_number=defect.line_number,
                    detected=False,
                    line_matched=False,
                    category_matched=False,
                    awarded_points=0.0,
                    max_points=defect.points,
                    severity=defect.severity,
                    title=defect.title,
                    consequence=defect.consequence,
                    diagnostic_explanation=defect.diagnostic_explanation,
                    competency_id=defect.competency_id,
                )
            )

    # Process false flags
    penalty_cfg = active_rubric.false_flag_penalty
    false_flags: list[FalseFlagRecord] = []
    for idx, flag in enumerate(flags):
        if idx not in matched_flags:
            false_flags.append(
                FalseFlagRecord(
                    line_number=flag.line_number,
                    selected_category=flag.selected_category,
                    penalty_applied=penalty_cfg.penalty_per_flag,
                )
            )

    false_flag_count = len(false_flags)
    raw_penalty = false_flag_count * penalty_cfg.penalty_per_flag
    capped_penalty = round(min(penalty_cfg.max_penalty, raw_penalty), 2)

    # Compute net score bounded in [0.0, max_possible_score]
    raw_net_score = total_awarded_points - capped_penalty
    final_score = max(0.0, min(active_rubric.max_possible_score, round(raw_net_score, 2)))

    passed = final_score >= active_rubric.pass_threshold_score

    # Competency evidence generation (Rule R-CR-03: State beats score)
    demonstrated_competencies: list[str] = []
    if passed:
        seen_comps: set[str] = set()
        demonstrated_competencies.append(scenario.primary_competency_id)
        seen_comps.add(scenario.primary_competency_id)

        for res in defect_results:
            if res.detected and res.awarded_points > 0.0 and res.competency_id not in seen_comps:
                demonstrated_competencies.append(res.competency_id)
                seen_comps.add(res.competency_id)

    detected_count = sum(1 for r in defect_results if r.detected)

    return ScenarioAttemptEvaluation(
        scenario_id=scenario.id,
        variant_id=matched_variant_id,
        passed=passed,
        score=final_score,
        max_possible_score=active_rubric.max_possible_score,
        pass_threshold_score=active_rubric.pass_threshold_score,
        detected_defect_count=detected_count,
        total_defect_count=len(defects),
        false_flag_count=false_flag_count,
        false_flag_penalty_applied=capped_penalty,
        defect_results=defect_results,
        false_flags=false_flags,
        demonstrated_competency_ids=demonstrated_competencies,
    )


def sanitize_challenge_for_client(
    scenario: PracticeScenario,
    variant_id: str | None = None,
) -> ClientScenarioChallenge:
    """Generate a client-safe practice scenario challenge view.

    Strips all defect lines, consequences, rubric points, and answers (ADR-0013).

    Args:
        scenario: The complete server-side practice scenario.
        variant_id: Optional parameterized variant ID to resolve.

    Returns:
        ClientScenarioChallenge with zero answer key leakage.
    """
    return scenario.to_client_challenge(variant_id=variant_id)
