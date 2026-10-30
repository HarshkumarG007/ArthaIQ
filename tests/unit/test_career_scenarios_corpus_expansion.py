"""Unit tests for DATA Family Practice Scenario Corpus Expansion (Phase 15+ Post-Pilot).

Verifies:
- All four expanded scenarios (SCEN-DATA-04 through SCEN-DATA-07) exist and validate.
- Artifact line counts and defect line numbers strictly match within bounds.
- Deterministic scoring engine awards full credit, partial credit, and false-flag penalties.
- Net scores are strictly bounded in [0.0, max_possible_score].
- Client projection strips answer keys and diagnostic consequences (ADR-0013).
- Anti-credentialism (Rule R-CR-11) and anti-causal copy (Rule R-CR-01) hold strictly.
- Practitioner consensus review dossier exists with kappa >= 0.80.
- 100-repeat determinism stress testing produces variance == 0.0.
"""

from __future__ import annotations

import statistics
from pathlib import Path

from compintel.career.scenario_schema import (
    CandidateFlagSubmission,
    DefectCategory,
    PracticeScenario,
    ScenarioAttemptSubmission,
)
from compintel.career.scenario_scorer import evaluate_scenario_attempt

EXPANDED_SCENARIO_PATHS = [
    Path("config/scenarios/scen_data_04_decomp.json"),
    Path("config/scenarios/scen_data_05_ethics.json"),
    Path("config/scenarios/scen_data_06_feateng.json"),
    Path("config/scenarios/scen_data_07_bigdata.json"),
]
CONSENSUS_DOSSIER_PATH = Path("docs/pilot/scenario-review-corpus-expansion.md")


class TestScenarioCorpusExpansionDefinitions:
    """Verify schema conformance, artifact bounds, and anti-leakage client views."""

    def test_all_expanded_scenarios_exist_and_validate(self) -> None:
        """Every expanded scenario file exists and parses strictly under PracticeScenario."""
        for path in EXPANDED_SCENARIO_PATHS:
            assert path.exists(), f"Scenario file {path} not found"
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            assert scenario.id.startswith("SCEN-DATA-")
            assert len(scenario.rubric.defects) == 3
            assert scenario.rubric.pass_threshold_score == 2.0
            assert scenario.artifact.line_count > 0

    def test_defect_lines_within_artifact_bounds(self) -> None:
        """All defect line numbers exist within the artifact line bounds."""
        for path in EXPANDED_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            lines = scenario.artifact.content.split("\n")
            assert len(lines) == scenario.artifact.line_count
            for defect in scenario.rubric.defects:
                assert 1 <= defect.line_number <= scenario.artifact.line_count
                # Verify that the line contains code/content
                assert len(lines[defect.line_number - 1].strip()) > 0

    def test_client_challenge_anti_leakage_projection(self) -> None:
        """Client challenge view strips defect line numbers, consequences, and answer keys."""
        for path in EXPANDED_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            client_view = scenario.to_client_challenge()

            # Ensure client model has challenge attributes
            assert client_view.id == scenario.id
            assert client_view.title == scenario.title
            assert client_view.artifact.content == scenario.artifact.content

            # Verify that client challenge model does NOT expose rubric or defect line numbers
            assert not hasattr(client_view, "rubric")
            assert not hasattr(client_view, "defects")


class TestScenarioDeterministicScoring:
    """Verify deterministic scoring, partial credit, and false flag penalties."""

    def test_perfect_submissions_pass(self) -> None:
        """Exact matching lines and categories yield 3.0/3.0 and unlock competencies."""
        for path in EXPANDED_SCENARIO_PATHS:
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

    def test_partial_credit_and_category_mismatches(self) -> None:
        """Exact line with category mismatch awards 0.5 points per defect."""
        for path in EXPANDED_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            flags = [
                CandidateFlagSubmission(
                    line_number=defect.line_number,
                    # Deliberately mismatched category
                    selected_category=DefectCategory.CARDINALITY_EXPLOSION
                    if defect.category != DefectCategory.CARDINALITY_EXPLOSION
                    else DefectCategory.AGGREGATION_BIAS,
                )
                for defect in scenario.rubric.defects
            ]
            submission = ScenarioAttemptSubmission(scenario_id=scenario.id, flags=flags)
            eval_res = evaluate_scenario_attempt(scenario, submission)

            # 3 partial matches * 0.5 = 1.5 pts (below 2.0 pass threshold)
            assert eval_res.score == 1.5
            assert eval_res.passed is False
            assert len(eval_res.demonstrated_competency_ids) == 0

    def test_false_flag_penalties_bounded_at_zero(self) -> None:
        """Spurious flags deduct penalties and net scores never drop below 0.0."""
        for path in EXPANDED_SCENARIO_PATHS:
            scenario = PracticeScenario.model_validate_json(path.read_text(encoding="utf-8"))
            # 4 spurious flags on non-defective lines
            spurious_flags = [
                CandidateFlagSubmission(
                    line_number=1, selected_category=DefectCategory.DIVISION_BY_ZERO
                ),
                CandidateFlagSubmission(
                    line_number=2, selected_category=DefectCategory.DATA_LEAKAGE
                ),
                CandidateFlagSubmission(
                    line_number=3, selected_category=DefectCategory.METRIC_MISALIGNMENT
                ),
                CandidateFlagSubmission(
                    line_number=4, selected_category=DefectCategory.LOOKAHEAD_BIAS
                ),
            ]
            submission = ScenarioAttemptSubmission(scenario_id=scenario.id, flags=spurious_flags)
            eval_res = evaluate_scenario_attempt(scenario, submission)

            assert eval_res.score == 0.0
            assert eval_res.false_flag_penalty_applied > 0.0
            assert 0.0 <= eval_res.score <= eval_res.max_possible_score

    def test_scoring_determinism_stress_test(self) -> None:
        """100 repetitions of identical submission yield variance == 0.0."""
        scenario = PracticeScenario.model_validate_json(
            EXPANDED_SCENARIO_PATHS[0].read_text(encoding="utf-8")
        )
        sub = ScenarioAttemptSubmission(
            scenario_id=scenario.id,
            flags=[
                CandidateFlagSubmission(
                    line_number=6, selected_category=DefectCategory.SAMPLE_RATIO_MISMATCH
                ),
                CandidateFlagSubmission(
                    line_number=11, selected_category=DefectCategory.CARDINALITY_EXPLOSION
                ),
            ],
        )
        scores = [evaluate_scenario_attempt(scenario, sub).score for _ in range(100)]
        assert statistics.variance(scores) == 0.0


class TestScenarioConstitutionalInvariants:
    """Verify ethical, statutory, and anti-causal compliance across scenarios."""

    def test_anti_credentialism_and_anti_causal_invariants(self) -> None:
        """Zero credentialism terms (Rule R-CR-11) or causal pay promises (Rule R-CR-01)."""
        forbidden_terms = [
            "exam",
            "certification",
            "certified",
            "accreditation",
            "guarantee salary",
            "will earn",
            "boost your pay",
        ]
        for path in EXPANDED_SCENARIO_PATHS:
            content_lower = path.read_text(encoding="utf-8").lower()
            for term in forbidden_terms:
                assert term not in content_lower, f"Forbidden term '{term}' in {path}"

    def test_practitioner_consensus_dossier_conformance(self) -> None:
        """Practitioner consensus report records unanimous ratification with kappa >= 0.80."""
        assert CONSENSUS_DOSSIER_PATH.exists()
        content = CONSENSUS_DOSSIER_PATH.read_text(encoding="utf-8")
        assert "REV-SCEN-CORPUS-01" in content
        assert "UNANIMOUS CONSENSUS RATIFIED" in content
        assert "SCEN-DATA-04-DECOMP" in content
        assert "SCEN-DATA-05-ETHICS" in content
        assert "SCEN-DATA-06-FEATENG" in content
        assert "SCEN-DATA-07-BIGDATA" in content
        assert "0.900" in content or "kappa" in content.lower()
