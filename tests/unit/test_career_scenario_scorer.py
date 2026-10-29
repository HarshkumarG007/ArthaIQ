"""Unit and property-based tests for Career Architect deterministic scenario scoring engine.

Phase 15D, Task T15.23.
Adheres strictly to:
- ADR-0010 & Rule R-CR-15: Zero runtime Large Language Models on serving/scoring path.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit,
  false-flag penalties, and evidence ledger linkage.
- Rule R-CR-03: State beats score (successful attempts award 'Demonstrated' verification state).
- Rule R-CR-11: Practice, not certification (no exam or credential terminology).
- Rule R-TS-04: Property-based testing with Hypothesis.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from compintel.career.scenario_schema import (
    ArtifactLanguage,
    CandidateFlagSubmission,
    ClientScenarioChallenge,
    DefectCategory,
    DefectSeverity,
    FalseFlagPenalty,
    PracticeScenario,
    ScenarioArtifact,
    ScenarioAttemptSubmission,
    ScenarioRubric,
    ScenarioVariant,
    SeededDefect,
)
from compintel.career.scenario_scorer import (
    evaluate_scenario_attempt,
    sanitize_challenge_for_client,
)
from compintel.career.schema import (
    RoleLevel,
    TaxonomyLicense,
    TaxonomyProvenance,
    TaxonomySource,
)


@pytest.fixture(scope="module")
def provenance() -> TaxonomyProvenance:
    """Fixture providing verified statutory taxonomy provenance."""
    return TaxonomyProvenance(
        source_id=TaxonomySource.ARTHAIQ_CURATED,
        source_code="ARTHAIQ-SCEN-01",
        license=TaxonomyLicense.PROPRIETARY_INTERNAL,
        attribution_required=True,
        attribution_text="ArthaIQ Curated Technical Flaw-Finding Benchmark",
        modified_flag=False,
        curator="Data Engineering Review Board",
        curated_date="2026-10-29",
    )


@pytest.fixture(scope="module")
def artifact() -> ScenarioArtifact:
    """Fixture providing a 10-line SQL query with seeded flaws."""
    content = (
        "SELECT\n"
        "    user_id,\n"
        "    SUM(payment_amount) AS total_revenue,\n"
        "    COUNT(*) AS transaction_count,\n"
        "    SUM(payment_amount) / COUNT(user_id) AS avg_ticket,\n"
        "    MAX(event_date) OVER (PARTITION BY user_id) AS future_leakage_date\n"
        "FROM transactions\n"
        "WHERE status = 'COMPLETED'\n"
        "GROUP BY user_id, payment_amount\n"
        "ORDER BY total_revenue DESC;"
    )
    return ScenarioArtifact(
        content=content,
        language=ArtifactLanguage.SQL,
        line_count=10,
    )


@pytest.fixture(scope="module")
def defects() -> list[SeededDefect]:
    """Fixture providing two seeded defects in the SQL artifact (total points = 2.5)."""
    return [
        SeededDefect(
            id="DEF-01",
            line_number=5,
            category=DefectCategory.LOOKAHEAD_BIAS,
            severity=DefectSeverity.CRITICAL,
            title="Future Event Leakage in Partition Window",
            consequence="Leaking future event timestamps introduces severe target leakage.",
            diagnostic_explanation="Unbounded event_date window leaks future data.",
            competency_id="data.anl.l2_sql_basic",
            points=1.5,
        ),
        SeededDefect(
            id="DEF-02",
            line_number=9,
            category=DefectCategory.AGGREGATION_BIAS,
            severity=DefectSeverity.MAJOR,
            title="Payment Amount in Group By Clause",
            consequence="Grouping by payment_amount prevents aggregating transactions per user.",
            diagnostic_explanation="Only user_id should be in GROUP BY.",
            competency_id="data.anl.l2_eda",
            points=1.0,
        ),
    ]


@pytest.fixture(scope="module")
def rubric(defects: list[SeededDefect]) -> ScenarioRubric:
    """Fixture providing deterministic scenario rubric with pass threshold 1.5."""
    return ScenarioRubric(
        scenario_id="SCEN-DATA-01-SQL",
        defects=defects,
        pass_threshold_score=1.5,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )


@pytest.fixture(scope="module")
def scenario(
    artifact: ScenarioArtifact,
    rubric: ScenarioRubric,
    provenance: TaxonomyProvenance,
) -> PracticeScenario:
    """Fixture providing a full server-side practice scenario with one variant."""
    variant_rubric = ScenarioRubric(
        scenario_id="SCEN-DATA-01-SQL",
        defects=[
            SeededDefect(
                id="DEF-V1-01",
                line_number=5,
                category=DefectCategory.LOOKAHEAD_BIAS,
                severity=DefectSeverity.CRITICAL,
                title="Variant Future Leakage",
                consequence="Leaking future event timestamps introduces severe target leakage.",
                diagnostic_explanation="Unbounded event_date window leaks future data.",
                competency_id="data.anl.l2_sql_basic",
                points=2.0,
            ),
        ],
        pass_threshold_score=2.0,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.0),
    )
    variant = ScenarioVariant(
        variant_id="VAR-ECOMMERCE",
        description="E-commerce transaction table variant",
        rubric_override=variant_rubric,
    )
    return PracticeScenario(
        id="SCEN-DATA-01-SQL",
        title="Diagnostic Review: Revenue Aggregation & Window Leakage",
        description="Inspect query for lookahead leakage and aggregation grouping errors.",
        role_family="DATA",
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="data.anl.l2_sql_basic",
        secondary_competency_ids=["data.anl.l2_eda"],
        artifact=artifact,
        rubric=rubric,
        variants=[variant],
        provenance=provenance,
    )


# =============================================================================
# 1. Deterministic Unit Tests
# =============================================================================


class TestDeterministicScoringEngine:
    """Validate rubric scoring rules, partial credit, and penalty bounds."""

    def test_perfect_attempt_awards_full_credit(self, scenario: PracticeScenario) -> None:
        """Candidate flags both flaws on exact lines with correct categories."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=[
                CandidateFlagSubmission(
                    line_number=5,
                    selected_category=DefectCategory.LOOKAHEAD_BIAS,
                    justification_notes="Window function leaks future partition data.",
                ),
                CandidateFlagSubmission(
                    line_number=9,
                    selected_category=DefectCategory.AGGREGATION_BIAS,
                    justification_notes="GROUP BY includes payment_amount.",
                ),
            ],
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        assert evaluation.passed is True
        assert evaluation.score == 2.5
        assert evaluation.max_possible_score == 2.5
        assert evaluation.pass_threshold_score == 1.5
        assert evaluation.detected_defect_count == 2
        assert evaluation.total_defect_count == 2
        assert evaluation.false_flag_count == 0
        assert evaluation.false_flag_penalty_applied == 0.0

        # Verify competencies unlocked (Rule R-CR-03)
        assert evaluation.demonstrated_competency_ids == [
            "data.anl.l2_sql_basic",
            "data.anl.l2_eda",
        ]

        # Verify individual defect breakdown
        res1 = evaluation.defect_results[0]
        assert res1.defect_id == "DEF-01"
        assert res1.detected is True
        assert res1.line_matched is True
        assert res1.category_matched is True
        assert res1.awarded_points == 1.5

        res2 = evaluation.defect_results[1]
        assert res2.defect_id == "DEF-02"
        assert res2.detected is True
        assert res2.awarded_points == 1.0

    def test_partial_credit_category_misidentification(self, scenario: PracticeScenario) -> None:
        """Candidate flags exact lines but selects wrong categories (50% credit)."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=[
                CandidateFlagSubmission(
                    line_number=5,
                    selected_category=DefectCategory.NULL_HANDLING,  # Wrong category
                ),
                CandidateFlagSubmission(
                    line_number=9,
                    selected_category=DefectCategory.DATA_LEAKAGE,  # Wrong category
                ),
            ],
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        # 50% of 1.5 = 0.75; 50% of 1.0 = 0.50 => total 1.25 < pass threshold 1.5
        assert evaluation.score == 1.25
        assert evaluation.passed is False
        assert evaluation.detected_defect_count == 2
        assert evaluation.false_flag_count == 0
        # Not passed => no demonstrated competencies unlocked
        assert evaluation.demonstrated_competency_ids == []

        res1 = evaluation.defect_results[0]
        assert res1.detected is True
        assert res1.line_matched is True
        assert res1.category_matched is False
        assert res1.awarded_points == 0.75

    def test_partial_credit_adjacent_line_with_correct_category(
        self, scenario: PracticeScenario
    ) -> None:
        """Candidate flags adjacent lines (+/- 1) with exact categories (50% partial credit)."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=[
                CandidateFlagSubmission(
                    line_number=6,  # Defect is on line 5
                    selected_category=DefectCategory.LOOKAHEAD_BIAS,
                ),
                CandidateFlagSubmission(
                    line_number=8,  # Defect is on line 9
                    selected_category=DefectCategory.AGGREGATION_BIAS,
                ),
            ],
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        assert evaluation.score == 1.25
        assert evaluation.passed is False
        assert evaluation.detected_defect_count == 2
        assert evaluation.false_flag_count == 0

        res1 = evaluation.defect_results[0]
        assert res1.detected is True
        assert res1.line_matched is False
        assert res1.category_matched is True
        assert res1.awarded_points == 0.75

    def test_guessing_attempt_incurs_capped_false_flag_penalty(
        self, scenario: PracticeScenario
    ) -> None:
        """Candidate flags every single line (1..10) trying to game the rubric."""
        all_lines_flags = [
            CandidateFlagSubmission(
                line_number=line,
                selected_category=(
                    DefectCategory.LOOKAHEAD_BIAS if line == 5 else DefectCategory.AGGREGATION_BIAS
                ),
            )
            for line in range(1, 11)
        ]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=all_lines_flags,
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        # 2 correct lines (5 and 9) with full matches = 2.5 points
        # 8 false flags * 0.5 = 4.0 penalty, capped at max_penalty = 1.5
        # Net score = 2.5 - 1.5 = 1.0 < 1.5 threshold
        assert evaluation.detected_defect_count == 2
        assert evaluation.false_flag_count == 8
        assert evaluation.false_flag_penalty_applied == 1.5
        assert evaluation.score == 1.0
        assert evaluation.passed is False
        assert evaluation.demonstrated_competency_ids == []

    def test_zero_flags_attempt(self, scenario: PracticeScenario) -> None:
        """Candidate submits zero flags."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=[],
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        assert evaluation.score == 0.0
        assert evaluation.passed is False
        assert evaluation.detected_defect_count == 0
        assert evaluation.false_flag_count == 0
        assert evaluation.demonstrated_competency_ids == []

    def test_variant_rubric_override_evaluation(self, scenario: PracticeScenario) -> None:
        """Evaluation with variant_id correctly uses variant's rubric override."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            variant_id="VAR-ECOMMERCE",
            flags=[
                CandidateFlagSubmission(
                    line_number=5,
                    selected_category=DefectCategory.LOOKAHEAD_BIAS,
                ),
            ],
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        assert evaluation.variant_id == "VAR-ECOMMERCE"
        assert evaluation.max_possible_score == 2.0
        assert evaluation.pass_threshold_score == 2.0
        assert evaluation.score == 2.0
        assert evaluation.passed is True
        assert evaluation.total_defect_count == 1
        assert evaluation.demonstrated_competency_ids == ["data.anl.l2_sql_basic"]

    def test_rejects_scenario_id_mismatch(self, scenario: PracticeScenario) -> None:
        """Attempt submission targeting wrong scenario raises ValueError."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-OTHER-MISMATCH",
            flags=[],
        )
        with pytest.raises(ValueError, match="does not match target scenario"):
            evaluate_scenario_attempt(scenario, submission)

    def test_rejects_nonexistent_variant_id(self, scenario: PracticeScenario) -> None:
        """Attempt submission targeting nonexistent variant raises ValueError."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            variant_id="VAR-NONEXISTENT",
            flags=[],
        )
        with pytest.raises(ValueError, match="Variant 'VAR-NONEXISTENT' not found"):
            evaluate_scenario_attempt(scenario, submission)


# =============================================================================
# 2. Anti-Leakage Contract Tests
# =============================================================================


class TestAntiLeakageContracts:
    """Verify ADR-0013 and Rule R-CR-08 anti-leakage invariants."""

    def test_sanitize_challenge_strips_ground_truth(self, scenario: PracticeScenario) -> None:
        """Sanitized challenge emitted to client contains zero answer keys or point allocations."""
        challenge = sanitize_challenge_for_client(scenario)

        assert isinstance(challenge, ClientScenarioChallenge)
        assert challenge.id == scenario.id
        assert challenge.artifact.line_count == 10
        assert len(challenge.available_defect_categories) > 0

        # Client challenge schema has no defects, rubric, or scoring fields
        challenge_dict = challenge.model_dump()
        assert "rubric" not in challenge_dict
        assert "defects" not in challenge_dict
        assert "pass_threshold_score" not in challenge_dict
        assert "false_flag_penalty" not in challenge_dict

        # Serialized JSON text must not contain defect IDs or titles
        json_repr = challenge.model_dump_json()
        assert "DEF-01" not in json_repr
        assert "DEF-02" not in json_repr
        assert "Future Event Leakage" not in json_repr


# =============================================================================
# 3. Property-Based Invariant Tests (Hypothesis)
# =============================================================================


# Strategy generating candidate flags bounded to lines 1..10
flag_strategy = st.builds(
    CandidateFlagSubmission,
    line_number=st.integers(min_value=1, max_value=10),
    selected_category=st.sampled_from(list(DefectCategory)),
    justification_notes=st.just(None),
)


class TestPropertyBasedInvariants:
    """Hypothesis invariant verification for deterministic scoring engine."""

    @settings(max_examples=50, deadline=None)
    @given(flags=st.lists(flag_strategy, max_size=15))
    def test_score_bounded_between_zero_and_max(
        self, scenario: PracticeScenario, flags: list[CandidateFlagSubmission]
    ) -> None:
        """Property: Final score is always strictly bounded in [0.0, max_possible_score]."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=flags,
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        assert 0.0 <= evaluation.score <= evaluation.max_possible_score
        assert evaluation.score <= scenario.rubric.max_possible_score

    @settings(max_examples=50, deadline=None)
    @given(flags=st.lists(flag_strategy, max_size=10))
    def test_penalty_monotonicity_under_irrelevant_flags(
        self, scenario: PracticeScenario, flags: list[CandidateFlagSubmission]
    ) -> None:
        """Property: Appending an irrelevant flag never increases the net score."""
        submission_base = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=flags,
        )
        eval_base = evaluate_scenario_attempt(scenario, submission_base)

        # Line 1 is not defective (defects are on lines 5 and 9) and not adjacent to 5 or 9
        irrelevant_flag = CandidateFlagSubmission(
            line_number=1,
            selected_category=DefectCategory.DIVISION_BY_ZERO,
        )
        submission_with_noise = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=[*flags, irrelevant_flag],
        )
        eval_with_noise = evaluate_scenario_attempt(scenario, submission_with_noise)

        # Score must be non-increasing when noise flag is added
        assert eval_with_noise.score <= eval_base.score

    @settings(max_examples=50, deadline=None)
    @given(flags=st.lists(flag_strategy, max_size=10))
    def test_evaluation_idempotence(
        self, scenario: PracticeScenario, flags: list[CandidateFlagSubmission]
    ) -> None:
        """Property: Evaluating identical submission twice yields identical evaluation result."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=flags,
        )

        eval1 = evaluate_scenario_attempt(scenario, submission)
        eval2 = evaluate_scenario_attempt(scenario, submission)

        assert eval1.score == eval2.score
        assert eval1.passed == eval2.passed
        assert eval1.detected_defect_count == eval2.detected_defect_count
        assert eval1.false_flag_count == eval2.false_flag_count
        assert eval1.false_flag_penalty_applied == eval2.false_flag_penalty_applied
        assert eval1.demonstrated_competency_ids == eval2.demonstrated_competency_ids

    @settings(max_examples=50, deadline=None)
    @given(flags=st.lists(flag_strategy, max_size=10))
    def test_competency_soundness(
        self, scenario: PracticeScenario, flags: list[CandidateFlagSubmission]
    ) -> None:
        """Property: If passed is False, demonstrated competencies list is strictly empty."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=flags,
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        if not evaluation.passed:
            assert evaluation.demonstrated_competency_ids == []
        else:
            assert scenario.primary_competency_id in evaluation.demonstrated_competency_ids
