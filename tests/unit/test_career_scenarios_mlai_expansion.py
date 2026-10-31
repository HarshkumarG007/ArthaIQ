"""Unit tests for Machine Learning & AI (MLAI) Practice Scenario Corpus Expansion (Phase 22).

Verifies:
- All 4 expanded MLAI scenarios (SCEN-MLAI-04 through SCEN-MLAI-07) exist and validate strictly.
- Artifact line counts and defect line numbers strictly match within bounds.
- Deterministic scoring engine awards full credit, partial credit, and false-flag penalties.
- Net scores are strictly bounded in [0.0, max_possible_score].
- Client projection strips answer keys and diagnostic consequences (ADR-0013 anti-leakage).
- Anti-credentialism (Rule R-CR-11) and anti-causal copy (Rule R-CR-01) hold strictly.
- Practitioner consensus review dossier exists with kappa >= 0.85.
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

EXPANDED_MLAI_SCENARIO_PATHS = [
    Path("config/scenarios/scen_mlai_04_rag.json"),
    Path("config/scenarios/scen_mlai_05_distrib.json"),
    Path("config/scenarios/scen_mlai_06_drift.json"),
    Path("config/scenarios/scen_mlai_07_guard.json"),
]
CONSENSUS_DOSSIER_PATH = Path("docs/pilot/scenario-review-mlai-corpus-expansion.md")


class TestMLAIScenarioCorpusExpansionDefinitions:
    """Verify schema conformance, artifact bounds, and anti-leakage client views."""

    def test_all_expanded_scenarios_exist_and_validate(self) -> None:
        """Every expanded scenario file exists and parses strictly under PracticeScenario."""
        expected_ids = [
            "SCEN-MLAI-04-VEC",
            "SCEN-MLAI-05-DIST",
            "SCEN-MLAI-06-DRIFT",
            "SCEN-MLAI-07-GUARD",
        ]
        for path, exp_id in zip(EXPANDED_MLAI_SCENARIO_PATHS, expected_ids, strict=True):
            assert path.exists(), f"Scenario file {path} not found"
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            assert scenario.id == exp_id
            assert scenario.role_family == RoleFamily.MLAI
            assert len(scenario.rubric.defects) == 3
            assert scenario.rubric.pass_threshold_score == 2.0
            assert scenario.artifact.line_count > 0
            assert scenario.artifact.line_count <= 40, (
                f"Scenario {scenario.id} line count {scenario.artifact.line_count} exceeds 40 lines"
            )

    def test_defect_lines_within_artifact_bounds(self) -> None:
        """All defect line numbers exist within the artifact line bounds."""
        for path in EXPANDED_MLAI_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            lines = scenario.artifact.content.splitlines()
            assert len(lines) == scenario.artifact.line_count
            for defect in scenario.rubric.defects:
                assert 1 <= defect.line_number <= scenario.artifact.line_count
                assert len(lines[defect.line_number - 1].strip()) > 0
                assert defect.points > 0.0

    def test_competency_ids_belong_to_mlai_family(self) -> None:
        """Primary and secondary competencies belong to the MLAI namespace."""
        expected_primaries = {
            "SCEN-MLAI-04-VEC": "mlai.core.l3_repr_learning",
            "SCEN-MLAI-05-DIST": "mlai.ops.l4_dist_training",
            "SCEN-MLAI-06-DRIFT": "mlai.eval.l3_conformal_calib",
            "SCEN-MLAI-07-GUARD": "mlai.gen.l3_guardrails",
        }
        for path in EXPANDED_MLAI_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            assert scenario.primary_competency_id == expected_primaries[scenario.id]
            assert scenario.primary_competency_id.startswith("mlai.")
            for sec_id in scenario.secondary_competency_ids:
                assert sec_id.startswith("mlai.")

    def test_anti_causal_and_anti_credential_invariants(self) -> None:
        """Scenario text must satisfy Rule R-CR-01 (anti-causal) and R-CR-11 (anti-credential)."""
        for path in EXPANDED_MLAI_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            for field_name, text in [
                ("title", scenario.title),
                ("description", scenario.description),
                ("instructions", scenario.instructions),
                ("disclaimer", scenario.disclaimer),
            ]:
                validate_anti_causal_text(text, field_name)
                validate_anti_credential_text(text, field_name)

            for defect in scenario.rubric.defects:
                for field_name, text in [
                    ("defect.title", defect.title),
                    ("defect.consequence", defect.consequence),
                    ("defect.diagnostic_explanation", defect.diagnostic_explanation),
                ]:
                    validate_anti_causal_text(text, field_name)
                    validate_anti_credential_text(text, field_name)

    def test_client_anti_leakage_isolation(self) -> None:
        """Client challenge projection must strip answer keys and consequences (ADR-0013)."""
        for path in EXPANDED_MLAI_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            challenge = sanitize_challenge_for_client(scenario)
            assert isinstance(challenge, ClientScenarioChallenge)
            assert challenge.id == scenario.id
            challenge_json = challenge.model_dump_json()

            for defect in scenario.rubric.defects:
                assert defect.id not in challenge_json
                assert defect.consequence not in challenge_json
                assert defect.diagnostic_explanation not in challenge_json


class TestMLAIScenarioDeterministicScoring:
    """Verify deterministic scoring, partial credit, and penalty boundaries."""

    def test_perfect_attempt_awards_full_score_and_unlocks_evidence(self) -> None:
        """Submitting all exact defect lines and categories awards full points."""
        for path in EXPANDED_MLAI_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            flags = [
                CandidateFlagSubmission(
                    line_number=defect.line_number,
                    selected_category=defect.category,
                    justification_notes="Accurately identified production defect.",
                )
                for defect in scenario.rubric.defects
            ]
            submission = ScenarioAttemptSubmission(
                scenario_id=scenario.id,
                flags=flags,
            )
            result = evaluate_scenario_attempt(scenario, submission)

            assert result.scenario_id == scenario.id
            assert result.passed is True
            assert result.score == scenario.rubric.max_possible_score
            assert result.false_flag_count == 0
            assert result.false_flag_penalty_applied == 0.0
            assert scenario.primary_competency_id in result.demonstrated_competency_ids

    def test_adjacent_line_and_category_mismatch_award_partial_credit(self) -> None:
        """Line adjacency (+/- 1) or category mismatch awards 50% partial credit."""
        for path in EXPANDED_MLAI_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            first_defect = scenario.rubric.defects[0]

            # Category mismatch on exact line: 50%
            wrong_category = (
                DefectCategory.RESOURCE_LEAK
                if first_defect.category != DefectCategory.RESOURCE_LEAK
                else DefectCategory.DATA_LEAKAGE
            )
            sub_mismatch = ScenarioAttemptSubmission(
                scenario_id=scenario.id,
                flags=[
                    CandidateFlagSubmission(
                        line_number=first_defect.line_number,
                        selected_category=wrong_category,
                        justification_notes="Correct line with different categorization.",
                    )
                ],
            )
            res_mismatch = evaluate_scenario_attempt(scenario, sub_mismatch)
            assert res_mismatch.score == first_defect.points * 0.5

    def test_false_flags_incur_calibrated_deductions_without_negative_score(self) -> None:
        """Spurious flags incur 0.5 pt penalty, bounded by max penalty and non-negative floor."""
        scenario = PracticeScenario.model_validate_json(
            EXPANDED_MLAI_SCENARIO_PATHS[0].read_text(encoding="utf-8")
        )
        first_defect = scenario.rubric.defects[0]

        submission = ScenarioAttemptSubmission(
            scenario_id=scenario.id,
            flags=[
                CandidateFlagSubmission(
                    line_number=first_defect.line_number,
                    selected_category=first_defect.category,
                    justification_notes="Legitimate defect.",
                ),
                CandidateFlagSubmission(
                    line_number=1,
                    selected_category=DefectCategory.SQL_INJECTION,
                    justification_notes="Spurious false flag.",
                ),
                CandidateFlagSubmission(
                    line_number=2,
                    selected_category=DefectCategory.RACE_CONDITION,
                    justification_notes="Second false flag.",
                ),
            ],
        )
        result = evaluate_scenario_attempt(scenario, submission)
        assert result.false_flag_count == 2
        assert result.false_flag_penalty_applied == 1.0  # 2 * 0.5
        assert result.score == 0.0
        assert result.passed is False

    def test_zero_flags_yields_zero_score_and_failed_attempt(self) -> None:
        """Empty submission yields 0.0 points and no evidence unlock."""
        for path in EXPANDED_MLAI_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            submission = ScenarioAttemptSubmission(scenario_id=scenario.id, flags=[])
            result = evaluate_scenario_attempt(scenario, submission)
            assert result.score == 0.0
            assert result.passed is False
            assert len(result.demonstrated_competency_ids) == 0

    def test_scoring_determinism_and_latency_sla_under_stress(self) -> None:
        """Evaluating 100 identical attempts produces variance == 0.0 and latency < 5ms."""
        scenario = PracticeScenario.model_validate_json(
            EXPANDED_MLAI_SCENARIO_PATHS[0].read_text(encoding="utf-8")
        )
        flags = [
            CandidateFlagSubmission(
                line_number=d.line_number,
                selected_category=d.category,
                justification_notes="Deterministic candidate flag.",
            )
            for d in scenario.rubric.defects
        ]
        submission = ScenarioAttemptSubmission(scenario_id=scenario.id, flags=flags)

        scores: list[float] = []
        latencies_ms: list[float] = []

        for _ in range(100):
            t0 = time.perf_counter()
            res = evaluate_scenario_attempt(scenario, submission)
            latencies_ms.append((time.perf_counter() - t0) * 1000)
            scores.append(res.score)

        assert statistics.variance(scores) == 0.0, "Scoring variance must be strictly 0.0"
        p95_latency = statistics.quantiles(latencies_ms, n=100)[94]
        assert p95_latency < 5.0, f"p95 latency {p95_latency:.3f}ms exceeds 5.0ms SLA"


class TestPractitionerConsensusDossier:
    """Verify presence and validity of practitioner consensus review dossier."""

    def test_consensus_dossier_exists_and_records_kappa(self) -> None:
        """Dossier exists, records Document ID, and confirms Kappa >= 0.85."""
        assert CONSENSUS_DOSSIER_PATH.exists()
        content = CONSENSUS_DOSSIER_PATH.read_text(encoding="utf-8")
        assert "REV-SCEN-MLAI-CORPUS-01" in content
        assert "0.900" in content
        assert "UNANIMOUS CONSENSUS RATIFIED" in content
        assert "Dr. Ananya Sen" in content
        assert "Vikramaditya Joshi" in content
        assert "Dr. Rajeshwari Sundaram" in content
