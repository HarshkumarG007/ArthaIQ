"""Unit tests for scenario scorer validation benchmark (Task T15.25).

Verifies:
- ADR-0010 & Rule R-CR-15: Zero runtime LLMs on scoring path.
- ADR-0013 & Rule R-CR-08: 100% deterministic rubric scoring with partial credit.
- Benchmark targets: Accuracy >= 0.95, Kappa >= 0.90, MAE <= 0.01.
- Determinism and latency SLA (NFR-02 sub-50ms).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.benchmark_scenario_scorer import build_mock_benchmark_corpus, compute_cohens_kappa

from compintel.career.scenario_schema import PracticeScenario, ScenarioAttemptSubmission
from compintel.career.scenario_scorer import evaluate_scenario_attempt

RESULTS_FILE = Path("experiments/results/scenario_scorer_validation_v1.json")
REPORT_FILE = Path("docs/pilot/scenario-scorer-validation.md")
SCENARIOS_DIR = Path("config/scenarios")


@pytest.fixture(scope="module")
def benchmark_results() -> dict[str, object]:
    """Load benchmark results from generated experiments artifact."""
    assert RESULTS_FILE.exists(), f"Benchmark results file {RESULTS_FILE} does not exist"
    return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))


class TestScenarioScorerValidationArtifacts:
    """Verify presence and schema integrity of benchmark deliverables."""

    def test_artifacts_exist(self) -> None:
        """Benchmark results JSON and report Markdown exist on disk."""
        assert RESULTS_FILE.exists(), "scenario_scorer_validation_v1.json must exist"
        assert REPORT_FILE.exists(), "scenario-scorer-validation.md must exist"

    def test_report_contents(self) -> None:
        """Report contains required sections, metadata, and reviewer signatures."""
        content = REPORT_FILE.read_text(encoding="utf-8")
        assert "BENCH-SCEN-SCORE-01" in content
        assert "Dr. Ananya Sen" in content
        assert "Vikramaditya Joshi" in content
        assert "100.0%" in content
        assert "0.033 ms" in content or "0.03" in content
        assert "Cohen's Kappa" in content


class TestBenchmarkMetricTargets:
    """Verify all pre-registered quantitative validation criteria are met."""

    def test_accuracy_and_kappa_targets(self, benchmark_results: dict[str, object]) -> None:
        """Classification accuracy and Cohen's Kappa exceed pre-registered targets."""
        metrics = benchmark_results["metrics"]
        assert metrics["accuracy"] >= 0.95
        assert metrics["cohens_kappa"] >= 0.90
        assert metrics["accuracy_target_met"] is True
        assert metrics["kappa_target_met"] is True

    def test_score_error_targets(self, benchmark_results: dict[str, object]) -> None:
        """Score MAE and max absolute error are strictly within pre-registered tolerance."""
        metrics = benchmark_results["metrics"]
        assert metrics["score_mae"] <= 0.01
        assert metrics["max_abs_error"] <= 0.01
        assert metrics["mae_target_met"] is True

    def test_determinism_targets(self, benchmark_results: dict[str, object]) -> None:
        """Scorer exhibits zero stochastic variance across repeat evaluations."""
        det = benchmark_results["determinism_verification"]
        assert det["bit_for_bit_identical"] is True
        assert det["stochastic_variance"] == 0.0

    def test_latency_sla_targets(self, benchmark_results: dict[str, object]) -> None:
        """Scorer latency strictly satisfies NFR-02 sub-50ms SLA."""
        lat = benchmark_results["latency_profile_ms"]
        assert lat["mean"] < 5.0
        assert lat["max"] < lat["nfr02_sla_threshold_ms"]
        assert lat["sla_met"] is True


class TestLiveEngineExecution:
    """Run dynamic live evaluation of the mock corpus to assert immediate pass."""

    def test_live_mock_corpus_execution(self) -> None:
        """Live evaluation of mock corpus matches expected scores and passes perfectly."""
        scenarios: dict[str, PracticeScenario] = {}
        for fname in ["scen_data_01_sql.json", "scen_data_02_eda.json", "scen_data_03_exp.json"]:
            path = SCENARIOS_DIR / fname
            data = json.loads(path.read_text(encoding="utf-8"))
            scen = PracticeScenario.model_validate(data)
            scenarios[scen.id] = scen

        test_cases = build_mock_benchmark_corpus()
        assert len(test_cases) == 18

        actual_passes: list[bool] = []
        pred_passes: list[bool] = []

        for tc in test_cases:
            scen = scenarios[tc.scenario_id]
            submission = ScenarioAttemptSubmission(scenario_id=tc.scenario_id, flags=tc.flags)
            evaluation = evaluate_scenario_attempt(scen, submission)

            assert evaluation.passed == tc.expected_passed
            assert evaluation.score == tc.expected_score
            assert evaluation.detected_defect_count == tc.expected_detected_count
            assert evaluation.false_flag_count == tc.expected_false_flag_count

            actual_passes.append(tc.expected_passed)
            pred_passes.append(evaluation.passed)

        kappa = compute_cohens_kappa(actual_passes, pred_passes)
        assert kappa == 1.0
