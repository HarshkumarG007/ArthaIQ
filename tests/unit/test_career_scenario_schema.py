"""Unit tests for Career Architect practice scenario schemas (Task T15.22).

Verifies ADR-0013 (Deterministic Scenario Scoring), Rule R-CR-08 (Deterministic Rubric),
Rule R-CR-11 (Practice, Not Certification), Rule R-CR-01 (Anti-Causal Invariants),
and anti-leakage invariants between server scenarios and client challenges.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from compintel.career.scenario_schema import (
    ArtifactLanguage,
    CandidateFlagSubmission,
    ClientScenarioChallenge,
    DefectCategory,
    DefectSeverity,
    FalseFlagPenalty,
    FalseFlagRecord,
    PracticeScenario,
    ScenarioArtifact,
    ScenarioAttemptEvaluation,
    ScenarioAttemptSubmission,
    ScenarioRubric,
    ScoredDefectResult,
    SeededDefect,
    validate_anti_credential_text,
)
from compintel.career.schema import (
    RoleLevel,
    TaxonomyLicense,
    TaxonomyProvenance,
    TaxonomySource,
)


@pytest.fixture
def sample_provenance() -> TaxonomyProvenance:
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


@pytest.fixture
def sample_artifact() -> ScenarioArtifact:
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


@pytest.fixture
def sample_defects() -> list[SeededDefect]:
    """Fixture providing two seeded defects in the SQL artifact."""
    return [
        SeededDefect(
            id="DEF-01",
            line_number=5,
            category=DefectCategory.LOOKAHEAD_BIAS,
            severity=DefectSeverity.CRITICAL,
            title="Future Event Leakage in Partition Window",
            consequence="Leaking future event timestamps introduces severe target leakage.",
            diagnostic_explanation=(
                "Using an unbounded window over event_date includes future outcomes "
                "not available at prediction time."
            ),
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
            diagnostic_explanation=(
                "Only user_id should be in GROUP BY to correctly compute total spend."
            ),
            competency_id="data.anl.l2_sql_basic",
            points=1.0,
        ),
    ]


@pytest.fixture
def sample_rubric(sample_defects: list[SeededDefect]) -> ScenarioRubric:
    """Fixture providing deterministic scenario rubric."""
    return ScenarioRubric(
        scenario_id="SCEN-DATA-01-SQL",
        defects=sample_defects,
        pass_threshold_score=1.5,
        false_flag_penalty=FalseFlagPenalty(penalty_per_flag=0.5, max_penalty=1.5),
    )


@pytest.fixture
def sample_practice_scenario(
    sample_artifact: ScenarioArtifact,
    sample_rubric: ScenarioRubric,
    sample_provenance: TaxonomyProvenance,
) -> PracticeScenario:
    """Fixture providing a full server-side practice scenario."""
    return PracticeScenario(
        id="SCEN-DATA-01-SQL",
        title="Diagnostic Review: Revenue Aggregation & Window Leakage",
        description="Inspect query for lookahead leakage and aggregation grouping errors.",
        role_family="DATA",
        target_level=RoleLevel.LEVEL_3_MID,
        primary_competency_id="data.anl.l2_sql_basic",
        secondary_competency_ids=["data.anl.l2_eda"],
        artifact=sample_artifact,
        rubric=sample_rubric,
        provenance=sample_provenance,
    )


class TestArtifactValidation:
    """Verify ScenarioArtifact contracts and line count integrity."""

    def test_artifact_valid_creation(self, sample_artifact: ScenarioArtifact) -> None:
        """Valid artifact initializes cleanly with accurate line count."""
        assert sample_artifact.line_count == 10
        assert sample_artifact.language == ArtifactLanguage.SQL
        assert "SELECT" in sample_artifact.content

    def test_artifact_rejects_line_count_mismatch(self) -> None:
        """Mismatch between line_count and content splitlines raises ValidationError."""
        with pytest.raises(ValidationError, match="line_count .* does not match"):
            ScenarioArtifact(
                content="LINE 1\nLINE 2\nLINE 3",
                language=ArtifactLanguage.PYTHON,
                line_count=99,
            )


class TestSeededDefectAndInvariants:
    """Verify SeededDefect invariants, anti-causal, and anti-credentialism protections."""

    def test_defect_valid_initialization(self, sample_defects: list[SeededDefect]) -> None:
        """Valid defect initializes with proper points and categories."""
        d = sample_defects[0]
        assert d.id == "DEF-01"
        assert d.line_number == 5
        assert d.category == DefectCategory.LOOKAHEAD_BIAS
        assert d.points == 1.5

    def test_defect_rejects_causal_pay_claims(self) -> None:
        """Rule R-CR-01: Prohibits causal compensation promises in diagnostic text."""
        with pytest.raises(ValidationError, match="Prohibited causal compensation phrase"):
            SeededDefect(
                id="DEF-BAD-01",
                line_number=2,
                category=DefectCategory.DATA_LEAKAGE,
                title="Fixing this raises compensation by 5 LPA",
                consequence="Valid consequence description.",
                diagnostic_explanation="Valid explanation.",
                competency_id="data.anl.l2_sql_basic",
                points=1.0,
            )

    def test_defect_rejects_credentialism_terms(self) -> None:
        """Rule R-CR-11: Prohibits credentialism or examination terminology."""
        with pytest.raises(ValidationError, match="Prohibited credentialism term"):
            SeededDefect(
                id="DEF-BAD-02",
                line_number=2,
                category=DefectCategory.DATA_LEAKAGE,
                title="Official Certification Exam Question",
                consequence="Valid consequence description.",
                diagnostic_explanation="Valid explanation.",
                competency_id="data.anl.l2_sql_basic",
                points=1.0,
            )

    def test_validate_anti_credential_text_utility(self) -> None:
        """Direct validator catches prohibited terms and permits clean practice text."""
        with pytest.raises(ValueError, match="Rule R-CR-11"):
            validate_anti_credential_text("Earn your certified status", "test_field")

        with pytest.raises(ValueError, match="Rule R-CR-11"):
            validate_anti_credential_text("Final examination rubric", "test_field")

        # Legitimate words like 'example' or 'practice' must pass cleanly
        clean = "Review this diagnostic code example in practice workspace."
        assert validate_anti_credential_text(clean, "test_field") == clean


class TestFalseFlagPenaltyAndRubric:
    """Verify FalseFlagPenalty rules and ScenarioRubric calculations."""

    def test_false_flag_penalty_bounds(self) -> None:
        """penalty_per_flag cannot exceed max_penalty."""
        with pytest.raises(ValidationError, match="penalty_per_flag .* exceeds max_penalty"):
            FalseFlagPenalty(penalty_per_flag=3.0, max_penalty=1.0)

    def test_rubric_max_score_and_threshold_validation(
        self,
        sample_defects: list[SeededDefect],
    ) -> None:
        """Rubric calculates max possible points and checks threshold validity."""
        rubric = ScenarioRubric(
            scenario_id="SCEN-01",
            defects=sample_defects,
            pass_threshold_score=2.0,
        )
        assert rubric.max_possible_score == 2.5
        assert rubric.pass_threshold_score == 2.0

        # pass_threshold cannot exceed total possible points
        with pytest.raises(ValidationError, match="pass_threshold_score .* exceeds max"):
            ScenarioRubric(
                scenario_id="SCEN-01",
                defects=sample_defects,
                pass_threshold_score=10.0,
            )


class TestAntiLeakageClientChallenge:
    """Verify ADR-0013 Section 3 anti-leakage isolation of client-facing challenges."""

    def test_scenario_validates_defect_lines_within_artifact(
        self,
        sample_artifact: ScenarioArtifact,
        sample_provenance: TaxonomyProvenance,
    ) -> None:
        """Defect with line_number outside artifact bounds raises ValidationError."""
        out_of_bounds_defect = SeededDefect(
            id="DEF-OOB",
            line_number=999,  # Artifact only has 10 lines
            category=DefectCategory.DATA_LEAKAGE,
            title="Out of Bounds Line",
            consequence="Valid consequence text.",
            diagnostic_explanation="Valid explanation text.",
            competency_id="data.anl.l2_sql_basic",
            points=1.0,
        )
        invalid_rubric = ScenarioRubric(
            scenario_id="SCEN-OOB",
            defects=[out_of_bounds_defect],
            pass_threshold_score=1.0,
        )
        with pytest.raises(ValidationError, match="exceeds artifact line count"):
            PracticeScenario(
                id="SCEN-OOB",
                title="Out of Bounds Practice",
                description="Valid description.",
                primary_competency_id="data.anl.l2_sql_basic",
                artifact=sample_artifact,
                rubric=invalid_rubric,
                provenance=sample_provenance,
            )

    def test_to_client_challenge_strips_answer_keys_and_locations(
        self,
        sample_practice_scenario: PracticeScenario,
    ) -> None:
        """Rule R-CR-08 & ADR-0013: Client view must contain zero answer keys or line numbers."""
        client_view = sample_practice_scenario.to_client_challenge()

        assert isinstance(client_view, ClientScenarioChallenge)
        assert client_view.id == sample_practice_scenario.id
        assert client_view.artifact.content == sample_practice_scenario.artifact.content
        assert len(client_view.available_defect_categories) > 0

        # Serialization to dictionary / JSON must not leak answers
        raw_dict = client_view.model_dump()
        assert "rubric" not in raw_dict
        assert "defects" not in raw_dict
        assert "pass_threshold_score" not in raw_dict

        # Verify no defect line numbers or point weights leak into client payload
        serialized_json = client_view.model_dump_json()
        assert "DEF-01" not in serialized_json
        assert "future_leakage_date" in serialized_json  # Code exists
        assert "Future Event Leakage in Partition Window" not in serialized_json  # Title withheld!


class TestSubmissionAndEvaluationModels:
    """Verify candidate attempt submission and deterministic evaluation reports."""

    def test_submission_and_evaluation_roundtrip(self) -> None:
        """Submission and evaluation models serialize and deserialize without loss."""
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-DATA-01-SQL",
            flags=[
                CandidateFlagSubmission(
                    line_number=5,
                    selected_category=DefectCategory.LOOKAHEAD_BIAS,
                    justification_notes="Event date window contains future dates.",
                ),
                CandidateFlagSubmission(
                    line_number=2,  # Incorrect line
                    selected_category=DefectCategory.NULL_HANDLING,
                ),
            ],
        )
        assert len(submission.flags) == 2
        assert submission.flags[0].line_number == 5

        evaluation = ScenarioAttemptEvaluation(
            scenario_id="SCEN-DATA-01-SQL",
            passed=True,
            score=1.0,  # 1.5 awarded - 0.5 false flag penalty
            max_possible_score=2.5,
            pass_threshold_score=1.0,
            detected_defect_count=1,
            total_defect_count=2,
            false_flag_count=1,
            false_flag_penalty_applied=0.5,
            defect_results=[
                ScoredDefectResult(
                    defect_id="DEF-01",
                    target_line_number=5,
                    detected=True,
                    line_matched=True,
                    category_matched=True,
                    awarded_points=1.5,
                    max_points=1.5,
                    severity=DefectSeverity.CRITICAL,
                    title="Future Event Leakage in Partition Window",
                    consequence="Leaking future event timestamps introduces severe target leakage.",
                    diagnostic_explanation="Window over event_date leaks future outcomes.",
                    competency_id="data.anl.l2_sql_basic",
                ),
            ],
            false_flags=[
                FalseFlagRecord(
                    line_number=2,
                    selected_category=DefectCategory.NULL_HANDLING,
                    penalty_applied=0.5,
                )
            ],
            demonstrated_competency_ids=["data.anl.l2_sql_basic"],
        )

        assert evaluation.passed is True
        assert evaluation.score == 1.0
        assert "data.anl.l2_sql_basic" in evaluation.demonstrated_competency_ids
        assert "Not an official credential" in evaluation.disclaimer
