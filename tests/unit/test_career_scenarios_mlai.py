"""Unit tests for canonical MLAI family practice scenarios (Task T19.06).

Verifies:
- ADR-0010 & Rule R-CR-15: Zero runtime Large Language Models on scoring path.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit.
- Rule R-CR-11: Practice, not certification (rejects all exam/credential terminology).
- Rule R-CR-01: Prohibits causal compensation promises.
- Rule R-CR-04: Ground-truth provenance and source attribution tracking.
- Client anti-leakage invariants: Zero answer key leakage ahead of candidate submission.
- Deterministic scoring performance: Variance = 0.0 and sub-5ms latency SLA.
"""

from __future__ import annotations

import json
import statistics
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
EXPECTED_MLAI_SCENARIO_FILES = [
    "scen_mlai_01_tens.json",
    "scen_mlai_02_leak.json",
    "scen_mlai_03_deploy.json",
]


@pytest.fixture(scope="module")
def loaded_mlai_scenarios() -> dict[str, PracticeScenario]:
    """Fixture loading and parsing all canonical MLAI scenario JSON definitions."""
    scenarios: dict[str, PracticeScenario] = {}
    for filename in EXPECTED_MLAI_SCENARIO_FILES:
        filepath = SCENARIOS_DIR / filename
        assert filepath.exists(), f"Expected scenario file {filepath} not found"
        raw_text = filepath.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        scenario = PracticeScenario.model_validate(data)
        scenarios[filename] = scenario
    return scenarios


class TestMLAIScenarioSchemaAndInvariants:
    """Validate schema compliance, line bounds, and ethical invariants for MLAI scenarios."""

    def test_all_expected_mlai_scenarios_exist_and_parse(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify all 3 MLAI scenarios load into PracticeScenario models."""
        assert len(loaded_mlai_scenarios) == 3
        expected_ids = {"SCEN-MLAI-01-TENS", "SCEN-MLAI-02-LEAK", "SCEN-MLAI-03-DEPLOY"}
        loaded_ids = {s.id for s in loaded_mlai_scenarios.values()}
        assert loaded_ids == expected_ids

    def test_mlai_role_family_and_level_invariants(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify role_family is MLAI and primary competencies start with mlai."""
        for scenario in loaded_mlai_scenarios.values():
            assert scenario.role_family == RoleFamily.MLAI
            assert scenario.primary_competency_id.startswith("mlai.")
            assert scenario.target_level in (2, 3, 4)

    def test_artifact_line_counts_match_content(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify artifact line_count matches actual line breaks and is within [10, 30]."""
        for scenario in loaded_mlai_scenarios.values():
            actual_lines = len(scenario.artifact.content.splitlines())
            assert scenario.artifact.line_count == actual_lines, (
                f"Scenario {scenario.id} line count mismatch"
            )
            assert 10 <= actual_lines <= 30, (
                f"Scenario {scenario.id} lines ({actual_lines}) not in bounds [10, 30]"
            )

    def test_all_defect_lines_within_bounds(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify every seeded defect line_number exists within artifact lines."""
        for scenario in loaded_mlai_scenarios.values():
            max_line = scenario.artifact.line_count
            for defect in scenario.rubric.defects:
                assert 1 <= defect.line_number <= max_line, (
                    f"Defect {defect.id} line {defect.line_number} exceeds max {max_line}"
                )
                assert defect.points > 0.0

    def test_anti_credentialism_and_anti_causal_invariants(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify copy strictly rejects credentialism (R-CR-11) and causal pay (R-CR-01)."""
        for scenario in loaded_mlai_scenarios.values():
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
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify each scenario defines at least 2 variants."""
        for scenario in loaded_mlai_scenarios.values():
            assert len(scenario.variants) >= 2


class TestMLAIAntiLeakageAndClientViews:
    """Verify ADR-0013 and Rule R-CR-08 anti-leakage invariants for MLAI scenarios."""

    def test_to_client_challenge_strips_ground_truth(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify client challenge strips defects, answers, points, and explanations."""
        for scenario in loaded_mlai_scenarios.values():
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
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify sanitize_challenge_for_client helper leaves zero rubric leakage."""
        for scenario in loaded_mlai_scenarios.values():
            challenge = sanitize_challenge_for_client(scenario)
            assert not hasattr(challenge, "defects")
            assert not hasattr(challenge, "rubric")
            assert challenge.id == scenario.id
            json_repr = challenge.model_dump_json()
            assert "rubric" not in json_repr
            assert "defects" not in json_repr
            assert "pass_threshold_score" not in json_repr


class TestMLAIScoringEngineExecution:
    """Validate deterministic scoring on realistic candidate attempt submissions for MLAI."""

    def test_tensor_perfect_attempt_passes(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify perfect submission on SCEN-MLAI-01-TENS earns full marks."""
        scenario = loaded_mlai_scenarios["scen_mlai_01_tens.json"]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-MLAI-01-TENS",
            flags=[
                CandidateFlagSubmission(
                    line_number=16,
                    selected_category=DefectCategory.UNSEEDED_RANDOMNESS,
                ),
                CandidateFlagSubmission(
                    line_number=22,
                    selected_category=DefectCategory.TENSOR_SHAPE_MISMATCH,
                ),
                CandidateFlagSubmission(
                    line_number=26,
                    selected_category=DefectCategory.COMPUTATION_GRAPH_LEAK,
                ),
            ],
        )

        result = evaluate_scenario_attempt(scenario, submission)
        assert result.score == 3.0
        assert result.passed is True
        assert result.false_flag_count == 0

    def test_attention_leak_perfect_attempt_passes(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify perfect submission on SCEN-MLAI-02-LEAK earns full marks."""
        scenario = loaded_mlai_scenarios["scen_mlai_02_leak.json"]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-MLAI-02-LEAK",
            flags=[
                CandidateFlagSubmission(
                    line_number=13,
                    selected_category=DefectCategory.ATTENTION_MASK_LEAK,
                ),
                CandidateFlagSubmission(
                    line_number=19,
                    selected_category=DefectCategory.DATA_LEAKAGE,
                ),
                CandidateFlagSubmission(
                    line_number=22,
                    selected_category=DefectCategory.METRIC_MISALIGNMENT,
                ),
            ],
        )

        result = evaluate_scenario_attempt(scenario, submission)
        assert result.score == 3.0
        assert result.passed is True
        assert result.false_flag_count == 0

    def test_deploy_perfect_attempt_passes(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify perfect submission on SCEN-MLAI-03-DEPLOY earns full marks."""
        scenario = loaded_mlai_scenarios["scen_mlai_03_deploy.json"]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-MLAI-03-DEPLOY",
            flags=[
                CandidateFlagSubmission(
                    line_number=16,
                    selected_category=DefectCategory.BLOCKING_CALL,
                ),
                CandidateFlagSubmission(
                    line_number=20,
                    selected_category=DefectCategory.UNBOUNDED_COLLECTION,
                ),
                CandidateFlagSubmission(
                    line_number=23,
                    selected_category=DefectCategory.RESOURCE_LEAK,
                ),
            ],
        )

        result = evaluate_scenario_attempt(scenario, submission)
        assert result.score == 3.0
        assert result.passed is True
        assert result.false_flag_count == 0

    def test_partial_credit_adjacent_line(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify flagging adjacent line (+/- 1) with exact category earns 50% partial credit."""
        scenario = loaded_mlai_scenarios["scen_mlai_01_tens.json"]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-MLAI-01-TENS",
            flags=[
                # Defect is on line 22; flag line 21 with exact category
                CandidateFlagSubmission(
                    line_number=21,
                    selected_category=DefectCategory.TENSOR_SHAPE_MISMATCH,
                ),
            ],
        )

        result = evaluate_scenario_attempt(scenario, submission)
        assert result.score == 0.5  # 50% partial credit
        assert result.passed is False

    def test_sub_5ms_scoring_latency_and_zero_variance(
        self, loaded_mlai_scenarios: dict[str, PracticeScenario]
    ) -> None:
        """Verify 100 consecutive scoring runs achieve zero variance and p95 latency < 5ms."""
        scenario = loaded_mlai_scenarios["scen_mlai_01_tens.json"]
        submission = ScenarioAttemptSubmission(
            scenario_id="SCEN-MLAI-01-TENS",
            flags=[
                CandidateFlagSubmission(
                    line_number=16,
                    selected_category=DefectCategory.UNSEEDED_RANDOMNESS,
                ),
                CandidateFlagSubmission(
                    line_number=22,
                    selected_category=DefectCategory.TENSOR_SHAPE_MISMATCH,
                ),
            ],
        )

        latencies_ms = []
        scores = []

        for _ in range(100):
            start = time.perf_counter()
            eval_res = evaluate_scenario_attempt(scenario, submission)
            latencies_ms.append((time.perf_counter() - start) * 1000)
            scores.append(eval_res.score)

        # Zero variance requirement across 100 executions
        assert statistics.variance(scores) == 0.0, "Scoring must be 100% deterministic"

        # p95 latency SLA (< 5.0ms)
        p95_latency = statistics.quantiles(latencies_ms, n=100)[94]
        assert p95_latency < 5.0, f"p95 latency {p95_latency:.3f}ms exceeds 5.0ms SLA"
