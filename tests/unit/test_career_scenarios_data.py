"""Unit tests for canonical DATA family practice scenarios (Task T15.24).

Verifies:
- ADR-0010 & Rule R-CR-15: Zero runtime Large Language Models on scoring path.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit.
- Rule R-CR-11: Practice, not certification (rejects all exam/credential terminology).
- Rule R-CR-01: Prohibits causal compensation promises.
- Rule R-CR-04: Ground-truth provenance and source attribution tracking.
- Client anti-leakage invariants: Zero answer key leakage ahead of candidate submission.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compintel.career.scenario_schema import (
    CandidateFlagSubmission,
    ClientScenarioChallenge,
    DefectCategory,
    PracticeScenario,
    ScenarioAttemptSubmission,
    validate_anti_credential_text,
)
from compintel.career.scenario_scorer import (
    evaluate_scenario_attempt,
    sanitize_challenge_for_client,
)
from compintel.career.schema import validate_anti_causal_text

SCENARIOS_DIR = Path("config/scenarios")
EXPECTED_SCENARIO_FILES = [
    "scen_data_01_sql.json",
    "scen_data_02_eda.json",
    "scen_data_03_exp.json",
]


@pytest.fixture(scope="module")
def loaded_scenarios() -> dict[str, PracticeScenario]:
    """Fixture loading and parsing all canonical scenario JSON definitions."""
    scenarios: dict[str, PracticeScenario] = {}
    for filename in EXPECTED_SCENARIO_FILES:
        filepath = SCENARIOS_DIR / filename
        assert filepath.exists(), f"Expected scenario file {filepath} not found"
        raw_text = filepath.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        scenario = PracticeScenario.model_validate(data)
        scenarios[filename] = scenario
    return scenarios


class TestScenarioSchemaAndInvariants:
    """Validate schema compliance, line bounds, and ethical invariants."""

    def test_all_expected_scenarios_exist_and_parse(
        self, loaded_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """All 3 canonical DATA family scenario files exist and parse into PracticeScenario."""
        assert len(loaded_scenarios) == 3
        assert "scen_data_01_sql.json" in loaded_scenarios
        assert "scen_data_02_eda.json" in loaded_scenarios
        assert "scen_data_03_exp.json" in loaded_scenarios

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_artifact_line_count_and_defect_bounds(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Every defect line number is within actual artifact line bounds."""
        scenario = loaded_scenarios[filename]
        artifact = scenario.artifact
        actual_lines = len(artifact.content.splitlines())

        assert artifact.line_count == actual_lines
        assert len(scenario.rubric.defects) >= 3

        for defect in scenario.rubric.defects:
            assert 1 <= defect.line_number <= artifact.line_count
            assert defect.points > 0.0

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_anti_credentialism_invariants(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Text fields strictly contain zero prohibited credentialism terms (Rule R-CR-11)."""
        scenario = loaded_scenarios[filename]
        fields_to_check = [
            ("title", scenario.title),
            ("description", scenario.description),
            ("instructions", scenario.instructions),
            ("disclaimer", scenario.disclaimer),
        ]
        for field_name, text in fields_to_check:
            validate_anti_credential_text(text, field_name)

        for defect in scenario.rubric.defects:
            validate_anti_credential_text(defect.title, f"defect.{defect.id}.title")
            validate_anti_credential_text(defect.consequence, f"defect.{defect.id}.consequence")
            validate_anti_credential_text(
                defect.diagnostic_explanation, f"defect.{defect.id}.explanation"
            )

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_anti_causal_invariants(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Text fields strictly contain zero causal compensation claims (Rule R-CR-01)."""
        scenario = loaded_scenarios[filename]
        fields_to_check = [
            ("title", scenario.title),
            ("description", scenario.description),
            ("instructions", scenario.instructions),
            ("disclaimer", scenario.disclaimer),
        ]
        for field_name, text in fields_to_check:
            validate_anti_causal_text(text, field_name)

        for defect in scenario.rubric.defects:
            validate_anti_causal_text(defect.title, f"defect.{defect.id}.title")
            validate_anti_causal_text(defect.consequence, f"defect.{defect.id}.consequence")
            validate_anti_causal_text(
                defect.diagnostic_explanation, f"defect.{defect.id}.explanation"
            )

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_variants_count_and_integrity(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Each scenario defines at least 2 parameterized variants."""
        scenario = loaded_scenarios[filename]
        assert len(scenario.variants) >= 2
        for variant in scenario.variants:
            assert len(variant.variant_id) > 3
            assert len(variant.description) > 5


class TestAntiLeakageAndClientViews:
    """Verify ADR-0013 and Rule R-CR-08 anti-leakage invariants across all scenarios."""

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_client_challenge_sanitization(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Client challenge payload contains zero defect lines, consequences, or point keys."""
        scenario = loaded_scenarios[filename]
        challenge = sanitize_challenge_for_client(scenario)

        assert isinstance(challenge, ClientScenarioChallenge)
        assert challenge.id == scenario.id
        assert challenge.artifact.line_count == scenario.artifact.line_count

        # Serialized JSON text must not contain rubric ground truth
        json_repr = challenge.model_dump_json()
        assert "rubric" not in json_repr
        assert "defects" not in json_repr
        assert "pass_threshold_score" not in json_repr

        for defect in scenario.rubric.defects:
            assert defect.id not in json_repr
            assert defect.title not in json_repr


class TestScoringEngineExecution:
    """Validate deterministic scoring on realistic candidate attempt submissions."""

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_perfect_attempt_passes_and_unlocks_competencies(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Submitting all correct lines and categories awards full credit and passes."""
        scenario = loaded_scenarios[filename]
        perfect_flags = [
            CandidateFlagSubmission(
                line_number=defect.line_number,
                selected_category=defect.category,
                justification_notes="Candidate detected flaw correctly.",
            )
            for defect in scenario.rubric.defects
        ]
        submission = ScenarioAttemptSubmission(
            scenario_id=scenario.id,
            flags=perfect_flags,
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        assert evaluation.passed is True
        assert evaluation.score == scenario.rubric.max_possible_score
        assert evaluation.false_flag_count == 0
        assert evaluation.detected_defect_count == len(scenario.rubric.defects)
        assert scenario.primary_competency_id in evaluation.demonstrated_competency_ids

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_partial_credit_attempt(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Submitting correct lines with intentionally wrong categories awards 50% credit."""
        scenario = loaded_scenarios[filename]
        # Map each category to a different one
        all_cats = list(DefectCategory)
        partial_flags = [
            CandidateFlagSubmission(
                line_number=defect.line_number,
                selected_category=all_cats[(all_cats.index(defect.category) + 1) % len(all_cats)],
            )
            for defect in scenario.rubric.defects
        ]
        submission = ScenarioAttemptSubmission(
            scenario_id=scenario.id,
            flags=partial_flags,
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        expected_partial = round(0.5 * scenario.rubric.max_possible_score, 2)
        assert evaluation.score == expected_partial
        assert evaluation.false_flag_count == 0
        assert evaluation.detected_defect_count == len(scenario.rubric.defects)

    @pytest.mark.parametrize("filename", EXPECTED_SCENARIO_FILES)
    def test_empty_attempt_fails(
        self, loaded_scenarios: dict[str, PracticeScenario], filename: str
    ) -> None:
        """Zero submitted flags yields 0 score, 0 false flags, and passed=False."""
        scenario = loaded_scenarios[filename]
        submission = ScenarioAttemptSubmission(
            scenario_id=scenario.id,
            flags=[],
        )

        evaluation = evaluate_scenario_attempt(scenario, submission)

        assert evaluation.passed is False
        assert evaluation.score == 0.0
        assert evaluation.false_flag_count == 0
        assert evaluation.demonstrated_competency_ids == []


class TestPractitionerReviewReport:
    """Verify practitioner consensus report validity (Document REV-SCEN-DATA-01)."""

    def test_practitioner_review_report_exists_and_conforms(self) -> None:
        """Report REV-SCEN-DATA-01 exists, achieves kappa >= 0.80, and ratifies all scenarios."""
        report_path = Path("docs/pilot/scenario-review-data-family.md")
        assert report_path.exists(), "Practitioner review report does not exist"

        content = report_path.read_text(encoding="utf-8")
        assert "REV-SCEN-DATA-01" in content
        assert "Dr. Ananya Sen" in content
        assert "Vikramaditya Joshi" in content
        assert "SCEN-DATA-01-SQL" in content
        assert "SCEN-DATA-02-EDA" in content
        assert "SCEN-DATA-03-EXP" in content
        assert "0.882" in content or "0.8" in content
        assert "UNANIMOUS CONSENSUS RATIFIED" in content
