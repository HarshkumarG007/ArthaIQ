"""Unit tests for Software Engineering (SWE) Practice Scenario Corpus Expansion (Phase 18).

Verifies:
- All 4 expanded SWE scenarios (SCEN-SWE-04 through SCEN-SWE-07) exist and validate strictly.
- Artifact line counts and defect line numbers strictly match within bounds (<= 30 lines).
- Deterministic scoring engine awards full credit, partial credit, and false-flag penalties.
- Net scores are strictly bounded in [0.0, max_possible_score].
- Client projection strips answer keys and diagnostic consequences (ADR-0013 anti-leakage).
- Anti-credentialism (Rule R-CR-11) and anti-causal copy (Rule R-CR-01) hold strictly.
- Practitioner consensus review dossier exists with kappa >= 0.80.
- 100-repeat determinism stress testing produces variance == 0.0 and latency < 5ms.
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

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

EXPANDED_SWE_SCENARIO_PATHS = [
    Path("config/scenarios/scen_swe_04_api.json"),
    Path("config/scenarios/scen_swe_05_test.json"),
    Path("config/scenarios/scen_swe_06_obs.json"),
    Path("config/scenarios/scen_swe_07_dist.json"),
]
CONSENSUS_DOSSIER_PATH = Path("docs/pilot/scenario-review-swe-corpus-expansion.md")


class TestSWEScenarioCorpusExpansionDefinitions:
    """Verify schema conformance, artifact bounds, and anti-leakage client views."""

    def test_all_expanded_scenarios_exist_and_validate(self) -> None:
        """Every expanded scenario file exists and parses strictly under PracticeScenario."""
        expected_ids = [
            "SCEN-SWE-04-API",
            "SCEN-SWE-05-TEST",
            "SCEN-SWE-06-OBS",
            "SCEN-SWE-07-DIST",
        ]
        for path, exp_id in zip(EXPANDED_SWE_SCENARIO_PATHS, expected_ids, strict=True):
            assert path.exists(), f"Scenario file {path} not found"
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            assert scenario.id == exp_id
            assert scenario.role_family == RoleFamily.SWE
            assert len(scenario.rubric.defects) == 3
            assert scenario.rubric.pass_threshold_score == 2.0
            assert scenario.artifact.line_count > 0
            assert scenario.artifact.line_count <= 30, (
                f"Scenario {scenario.id} line count {scenario.artifact.line_count} exceeds 30 lines"
            )

    def test_defect_lines_within_artifact_bounds(self) -> None:
        """All defect line numbers exist within the artifact line bounds."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            lines = scenario.artifact.content.splitlines()
            assert len(lines) == scenario.artifact.line_count
            for defect in scenario.rubric.defects:
                assert 1 <= defect.line_number <= scenario.artifact.line_count
                assert len(lines[defect.line_number - 1].strip()) > 0
                assert defect.points > 0.0

    def test_competency_ids_belong_to_swe_family(self) -> None:
        """Primary and secondary competencies belong to the SWE namespace."""
        expected_primaries = {
            "SCEN-SWE-04-API": "swe.app.l2_rest_api",
            "SCEN-SWE-05-TEST": "swe.test.l2_unit_test",
            "SCEN-SWE-06-OBS": "swe.sec.l3_auth_rbac",
            "SCEN-SWE-07-DIST": "swe.arch.l4_system_design",
        }
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            assert scenario.primary_competency_id == expected_primaries[scenario.id]
            assert scenario.primary_competency_id.startswith("swe.")
            for sec_id in scenario.secondary_competency_ids:
                assert sec_id.startswith("swe.")


class TestSWEClientAntiLeakageProjection:
    """Verify ADR-0013 and Rule R-CR-08 anti-leakage invariants for expanded SWE scenarios."""

    def test_client_challenge_anti_leakage_projection(self) -> None:
        """Client challenge view strips defect line numbers, consequences, and answer keys."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            client_view = scenario.to_client_challenge()

            assert isinstance(client_view, ClientScenarioChallenge)
            assert client_view.id == scenario.id
            assert client_view.title == scenario.title
            assert client_view.artifact.content == scenario.artifact.content

            dumped = client_view.model_dump()
            assert "defects" not in dumped
            assert "rubric" not in dumped
            assert "pass_threshold_score" not in dumped
            assert "false_flag_penalty" not in dumped

    def test_sanitize_challenge_for_client_helper(self) -> None:
        """Verify sanitize_challenge_for_client helper leaves zero rubric leakage."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            challenge = sanitize_challenge_for_client(scenario)
            assert not hasattr(challenge, "defects")
            assert not hasattr(challenge, "rubric")
            assert challenge.id == scenario.id
            json_repr = challenge.model_dump_json()
            assert "rubric" not in json_repr
            assert "defects" not in json_repr
            assert "pass_threshold_score" not in json_repr


class TestSWEDeterministicScoring:
    """Verify deterministic scoring, partial credit, and false flag penalties."""

    def test_perfect_submissions_pass(self) -> None:
        """Exact matching lines and categories yield 3.0/3.0 and unlock competencies."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            flags = [
                CandidateFlagSubmission(
                    line_number=defect.line_number,
                    selected_category=defect.category,
                )
                for defect in scenario.rubric.defects
            ]
            submission = ScenarioAttemptSubmission(scenario_id=scenario.id, flags=flags)
            eval_res = evaluate_scenario_attempt(scenario, submission)

            assert eval_res.passed is True
            assert eval_res.score == 3.0
            assert eval_res.detected_defect_count == 3
            assert eval_res.false_flag_count == 0
            assert scenario.primary_competency_id in eval_res.demonstrated_competency_ids

    def test_partial_credit_on_adjacent_lines(self) -> None:
        """Adjacent line flagging (+/- 1 line) awards 0.5 partial credit."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            d1 = scenario.rubric.defects[0]
            # Flag line offset by +1
            adj_line = d1.line_number + 1
            if adj_line > scenario.artifact.line_count:
                adj_line = d1.line_number - 1

            flags = [
                CandidateFlagSubmission(
                    line_number=adj_line,
                    selected_category=d1.category,
                )
            ]
            submission = ScenarioAttemptSubmission(scenario_id=scenario.id, flags=flags)
            eval_res = evaluate_scenario_attempt(scenario, submission)

            assert eval_res.score == 0.5
            assert eval_res.detected_defect_count == 1
            assert eval_res.passed is False

    def test_false_flag_penalty_bounds(self) -> None:
        """False flags apply penalty and score is clamped at 0.0 minimum."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            # Submit non-defect line
            defect_lines = {d.line_number for d in scenario.rubric.defects}
            non_defect_lines = [
                i
                for i in range(1, scenario.artifact.line_count + 1)
                if i not in defect_lines
                and (i - 1) not in defect_lines
                and (i + 1) not in defect_lines
            ]
            assert len(non_defect_lines) >= 1
            false_line = non_defect_lines[0]

            flags = [
                CandidateFlagSubmission(
                    line_number=false_line,
                    selected_category=DefectCategory.DATA_LEAKAGE,
                )
            ]
            submission = ScenarioAttemptSubmission(scenario_id=scenario.id, flags=flags)
            eval_res = evaluate_scenario_attempt(scenario, submission)

            assert eval_res.score == 0.0
            assert eval_res.false_flag_count == 1
            assert eval_res.passed is False


class TestSWEDeterminismAndPerformanceSLA:
    """Validate determinism stress test and sub-5ms scoring performance."""

    def test_scoring_determinism_stress_test(self) -> None:
        """Verify 100 repeated evaluations yield identical scores with variance == 0.0."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            d1 = scenario.rubric.defects[0]
            submission = ScenarioAttemptSubmission(
                scenario_id=scenario.id,
                flags=[
                    CandidateFlagSubmission(
                        line_number=d1.line_number,
                        selected_category=d1.category,
                    )
                ],
            )
            scores: list[float] = []
            for _ in range(100):
                eval_res = evaluate_scenario_attempt(scenario, submission)
                scores.append(eval_res.score)

            assert len(scores) == 100
            assert len(set(scores)) == 1
            assert statistics.variance(scores) == 0.0

    def test_sub_5ms_latency_sla(self) -> None:
        """Verify average attempt evaluation latency is strictly below 5ms (ADR-0013)."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            d1 = scenario.rubric.defects[0]
            submission = ScenarioAttemptSubmission(
                scenario_id=scenario.id,
                flags=[
                    CandidateFlagSubmission(
                        line_number=d1.line_number,
                        selected_category=d1.category,
                    )
                ],
            )
            t0 = time.perf_counter()
            for _ in range(100):
                evaluate_scenario_attempt(scenario, submission)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 100.0
            assert elapsed_ms < 5.0, f"Evaluation latency {elapsed_ms:.2f}ms exceeds 5ms limit"


class TestSWEConstitutionalInvariants:
    """Verify adherence to ethical invariants, anti-credentialism, and consensus review."""

    def test_anti_credentialism_and_anti_causal_text(self) -> None:
        """Verify copy strictly rejects credentialism (R-CR-11) and causal pay (R-CR-01)."""
        for path in EXPANDED_SWE_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
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

    def test_practitioner_consensus_dossier_ratified(self) -> None:
        """Verify practitioner dossier exists, kappa >= 0.80, and approves 4 scenarios."""
        assert CONSENSUS_DOSSIER_PATH.exists()
        content = CONSENSUS_DOSSIER_PATH.read_text(encoding="utf-8")
        assert "REV-SCEN-SWE-CORPUS-01" in content
        assert "Cohen's Kappa" in content
        assert "0.900" in content
        assert "SCEN-SWE-04-API" in content
        assert "SCEN-SWE-05-TEST" in content
        assert "SCEN-SWE-06-OBS" in content
        assert "SCEN-SWE-07-DIST" in content
        assert "UNANIMOUS CONSENSUS RATIFIED" in content
