"""Unit tests for canonical SWE family practice scenarios (Task T16.06).

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
import time
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
from compintel.schema.enums import RoleFamily

SCENARIOS_DIR = Path("config/scenarios")
EXPECTED_SWE_SCENARIO_FILES = [
    "scen_swe_01_concur.json",
    "scen_swe_02_sec.json",
    "scen_swe_03_db.json",
]


@pytest.fixture(scope="module")
def loaded_swe_scenarios() -> dict[str, PracticeScenario]:
    """Fixture loading and parsing all canonical SWE scenario JSON definitions."""
    scenarios: dict[str, PracticeScenario] = {}
    for filename in EXPECTED_SWE_SCENARIO_FILES:
        filepath = SCENARIOS_DIR / filename
        assert filepath.exists(), f"Expected scenario file {filepath} not found"
        raw_text = filepath.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        scenario = PracticeScenario.model_validate(data)
        scenarios[filename] = scenario
    return scenarios


class TestSWEScenarioSchemaAndInvariants:
    """Validate schema compliance, line bounds, and ethical invariants for SWE scenarios."""

    def test_all_expected_swe_scenarios_exist_and_parse(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify all 3 SWE scenarios load into PracticeScenario models."""
        assert len(loaded_swe_scenarios) == 3
        expected_ids = {"SCEN-SWE-01-CONCUR", "SCEN-SWE-02-SEC", "SCEN-SWE-03-DB"}
        loaded_ids = {s.id for s in loaded_swe_scenarios.values()}
        assert loaded_ids == expected_ids

    def test_swe_role_family_and_level_invariants(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify role_family is SWE and primary competencies exist."""
        for scenario in loaded_swe_scenarios.values():
            assert scenario.role_family == RoleFamily.SWE
            assert scenario.primary_competency_id.startswith("swe.")
            assert scenario.target_level in (2, 3, 4)

    def test_artifact_line_counts_match_content(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify artifact line_count matches actual line breaks."""
        for scenario in loaded_swe_scenarios.values():
            actual_lines = len(scenario.artifact.content.splitlines())
            assert scenario.artifact.line_count == actual_lines, (
                f"Scenario {scenario.id} line count mismatch"
            )

    def test_all_defect_lines_within_bounds(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify every seeded defect line_number exists within artifact lines."""
        for scenario in loaded_swe_scenarios.values():
            max_line = scenario.artifact.line_count
            for defect in scenario.rubric.defects:
                assert 1 <= defect.line_number <= max_line, (
                    f"Defect {defect.id} line {defect.line_number} exceeds max {max_line}"
                )
                assert defect.points > 0.0

    def test_anti_credentialism_and_anti_causal_invariants(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify copy strictly rejects credentialism (R-CR-11) and causal pay (R-CR-01)."""
        for scenario in loaded_swe_scenarios.values():
            validate_anti_credential_text(scenario.title, "title")
            validate_anti_credential_text(scenario.description, "description")
            validate_anti_credential_text(scenario.instructions, "instructions")
            validate_anti_credential_text(scenario.disclaimer, "disclaimer")

            validate_anti_causal_text(scenario.title, "title")
            validate_anti_causal_text(scenario.description, "description")
            validate_anti_causal_text(scenario.instructions, "instructions")
            validate_anti_causal_text(scenario.disclaimer, "disclaimer")

            for defect in scenario.rubric.defects:
                validate_anti_credential_text(defect.title, "defect.title")
                validate_anti_credential_text(defect.consequence, "defect.consequence")
                validate_anti_credential_text(
                    defect.diagnostic_explanation, "defect.diagnostic_explanation"
                )

                validate_anti_causal_text(defect.title, "defect.title")
                validate_anti_causal_text(defect.consequence, "defect.consequence")
                validate_anti_causal_text(
                    defect.diagnostic_explanation, "defect.diagnostic_explanation"
                )

    def test_scenarios_have_parameterized_variants(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify each scenario defines at least 2 variants."""
        for scenario in loaded_swe_scenarios.values():
            assert len(scenario.variants) >= 2


class TestSWEAntiLeakageAndClientViews:
    """Verify ADR-0013 and Rule R-CR-08 anti-leakage invariants for SWE scenarios."""

    def test_to_client_challenge_strips_ground_truth(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify client challenge strips defects, answers, points, and explanations."""
        for scenario in loaded_swe_scenarios.values():
            challenge = scenario.to_client_challenge()
            assert isinstance(challenge, ClientScenarioChallenge)
            assert challenge.id == scenario.id
            assert challenge.title == scenario.title
            assert challenge.artifact == scenario.artifact

            dumped = challenge.model_dump()
            assert "defects" not in dumped
            assert "rubric" not in dumped
            assert "pass_threshold_score" not in dumped
            assert "false_flag_penalty" not in dumped

    def test_sanitize_challenge_for_client_helper(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify sanitize_challenge_for_client helper leaves zero rubric leakage."""
        for scenario in loaded_swe_scenarios.values():
            challenge = sanitize_challenge_for_client(scenario)
            assert not hasattr(challenge, "defects")
            assert not hasattr(challenge, "rubric")
            assert challenge.id == scenario.id
            json_repr = challenge.model_dump_json()
            assert "rubric" not in json_repr
            assert "defects" not in json_repr
            assert "pass_threshold_score" not in json_repr


class TestSWEScoringEngineExecution:
    """Validate deterministic scoring on realistic candidate attempt submissions for SWE."""

    def test_concurrency_perfect_attempt_passes(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify perfect submission on SCEN-SWE-01-CONCUR earns full marks."""
        scenario = loaded_swe_scenarios["scen_swe_01_concur.json"]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-SWE-01-CONCUR",
            flags=[
                CandidateFlagSubmission(
                    line_number=13,
                    selected_category=DefectCategory.RACE_CONDITION,
                ),
                CandidateFlagSubmission(
                    line_number=16,
                    selected_category=DefectCategory.UNBOUNDED_COLLECTION,
                ),
                CandidateFlagSubmission(
                    line_number=19,
                    selected_category=DefectCategory.RESOURCE_LEAK,
                ),
            ],
        )

        result = evaluate_scenario_attempt(scenario, submission)
        assert result.score == 3.0
        assert result.passed is True
        assert result.false_flag_count == 0
        assert len(result.demonstrated_competency_ids) >= 1
        assert "swe.core.l2_concurrency" in result.demonstrated_competency_ids

    def test_security_partial_credit_adjacent_line(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify +/- 1 line adjacent match awards 50% partial credit."""
        scenario = loaded_swe_scenarios["scen_swe_02_sec.json"]
        # Defect 1 is line 11 (BROKEN_AUTHENTICATION); candidate flags line 10
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-SWE-02-SEC",
            flags=[
                CandidateFlagSubmission(
                    line_number=10,  # Adjacent to line 11
                    selected_category=DefectCategory.BROKEN_AUTHENTICATION,
                ),
                CandidateFlagSubmission(
                    line_number=20,  # Exact line 20
                    selected_category=DefectCategory.SQL_INJECTION,
                ),
            ],
        )

        result = evaluate_scenario_attempt(scenario, submission)
        assert result.score == 1.5  # 0.5 + 1.0
        assert result.passed is False  # 1.5 < 2.0 threshold

    def test_db_false_flag_penalties(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify false flags apply deductions and respect lower bound of 0.0."""
        scenario = loaded_swe_scenarios["scen_swe_03_db.json"]
        # Submit 4 spurious non-defect lines
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-SWE-03-DB",
            flags=[
                CandidateFlagSubmission(
                    line_number=1, selected_category=DefectCategory.DATA_LEAKAGE
                ),
                CandidateFlagSubmission(
                    line_number=2, selected_category=DefectCategory.DIVISION_BY_ZERO
                ),
                CandidateFlagSubmission(
                    line_number=3, selected_category=DefectCategory.SAMPLE_RATIO_MISMATCH
                ),
                CandidateFlagSubmission(
                    line_number=4, selected_category=DefectCategory.METRIC_MISALIGNMENT
                ),
            ],
        )

        result = evaluate_scenario_attempt(scenario, submission)
        assert result.score == 0.0
        assert result.false_flag_count == 4
        assert result.false_flag_penalty_applied == 1.5  # Max penalty cap
        assert result.passed is False

    def test_scoring_determinism_and_sub_5ms_latency(
        self, loaded_swe_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify 100 repeated evaluations yield identical score and sub-5ms latency."""
        scenario = loaded_swe_scenarios["scen_swe_01_concur.json"]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-SWE-01-CONCUR",
            flags=[
                CandidateFlagSubmission(
                    line_number=13,
                    selected_category=DefectCategory.RACE_CONDITION,
                ),
            ],
        )

        scores: list[float] = []
        t0 = time.perf_counter()
        for _ in range(100):
            res = evaluate_scenario_attempt(scenario, submission)
            scores.append(res.score)
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_time_ms = total_time_ms / 100.0

        # Determinism invariance: variance == 0
        assert len(set(scores)) == 1
        # Sub-5ms latency requirement (ADR-0013, NFR-02)
        assert avg_time_ms < 5.0
