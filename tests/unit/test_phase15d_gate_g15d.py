"""Unit tests for Phase 15D Gate G15D ratification verification.

Verifies:
- All five Phase 15D deliverables exist on disk.
- Decision D-029 is recorded in memory.md, task.md, and docs/STATE.md.
- Gate G15D review dossier exists and records UNCONDITIONAL GO.
- Ethical invariants (Rule R-CR-11 Anti-Credentialism and Rule R-CR-01 Anti-Causal Copy)
  are strictly maintained across all scenarios.
- Scorer validation benchmark achieves pre-registered targets (Accuracy, Kappa, Determinism).
"""

from __future__ import annotations

import json
from pathlib import Path

from compintel.career.scenario_schema import PracticeScenario, validate_anti_credential_text
from compintel.career.schema import validate_anti_causal_text

GATE_REVIEW_PATH = Path("docs/pilot/gate-g15d-review.md")
BENCHMARK_RESULTS_PATH = Path("experiments/results/scenario_scorer_validation_v1.json")
SCENARIOS_DIR = Path("config/scenarios")


class TestGateG15DDeliverables:
    """Verify presence of all artifacts and reports required for Gate G15D."""

    def test_all_subphase_15d_files_exist(self) -> None:
        """Every deliverable from T15.22 through T15.26 and Gate G15D exists on disk."""
        required_paths = [
            Path("src/compintel/career/scenario_schema.py"),
            Path("src/compintel/career/scenario_scorer.py"),
            Path("config/scenarios/scen_data_01_sql.json"),
            Path("config/scenarios/scen_data_02_eda.json"),
            Path("config/scenarios/scen_data_03_exp.json"),
            Path("docs/pilot/scenario-review-data-family.md"),
            Path("docs/pilot/scenario-scorer-validation.md"),
            Path("experiments/results/scenario_scorer_validation_v1.json"),
            Path("docs/research/sql-sandbox-spike.md"),
            Path("docs/pilot/gate-g15d-review.md"),
        ]
        for path in required_paths:
            assert path.exists(), f"Required Phase 15D file {path} not found"


class TestGateG15DRatificationRecords:
    """Verify Gate G15D formal ratification and Decision D-029 logging."""

    def test_gate_g15d_review_dossier_conformance(self) -> None:
        """Review dossier records UNCONDITIONAL GO, Decision D-029, and unanimous signatures."""
        content = GATE_REVIEW_PATH.read_text(encoding="utf-8")
        assert "REV-GATE-G15D-01" in content
        assert "RATIFIED GO" in content
        assert "UNCONDITIONAL GO" in content
        assert "Decision D-029" in content
        assert "Dr. Ananya Sen" in content or "Principal Labour Economist" in content
        assert "Vikramaditya Joshi" in content or "Infrastructure & Systems Architect" in content

    def test_decision_d029_recorded_in_state_and_memory(self) -> None:
        """Decision D-029 is indexed in docs/STATE.md and memory.md."""
        state_content = Path("docs/STATE.md").read_text(encoding="utf-8")
        memory_content = Path("memory.md").read_text(encoding="utf-8")
        task_content = Path("task.md").read_text(encoding="utf-8")

        assert "D-029" in state_content
        assert "D-029" in memory_content
        assert "Gate G15D" in task_content
        assert "RATIFIED GO" in task_content


class TestScenarioEthicalInvariants:
    """Verify absolute absence of credentialism or causal pay promises in scenarios."""

    def test_all_scenarios_strictly_pass_validators(self) -> None:
        """All 3 scenarios parse cleanly and pass regex anti-credentialism & anti-causal checks."""
        for filename in ["scen_data_01_sql.json", "scen_data_02_eda.json", "scen_data_03_exp.json"]:
            path = SCENARIOS_DIR / filename
            data = json.loads(path.read_text(encoding="utf-8"))
            scen = PracticeScenario.model_validate(data)

            # Test top-level text fields
            validate_anti_credential_text(scen.title, f"{filename}.title")
            validate_anti_credential_text(scen.description, f"{filename}.description")
            validate_anti_credential_text(scen.instructions, f"{filename}.instructions")
            validate_anti_credential_text(scen.disclaimer, f"{filename}.disclaimer")

            validate_anti_causal_text(scen.title, f"{filename}.title")
            validate_anti_causal_text(scen.description, f"{filename}.description")

            # Test defect texts
            for defect in scen.rubric.defects:
                validate_anti_credential_text(defect.title, f"{filename}.defect.{defect.id}.title")
                validate_anti_credential_text(
                    defect.consequence, f"{filename}.defect.{defect.id}.consequence"
                )
                validate_anti_credential_text(
                    defect.diagnostic_explanation, f"{filename}.defect.{defect.id}.explanation"
                )
                validate_anti_causal_text(defect.title, f"{filename}.defect.{defect.id}.title")
                validate_anti_causal_text(
                    defect.consequence, f"{filename}.defect.{defect.id}.consequence"
                )


class TestScorerBenchmarkConformance:
    """Verify quantitative criteria achieved in scenario scorer validation benchmark."""

    def test_benchmark_quantitative_conformance(self) -> None:
        """Validation benchmark results satisfy 100% accuracy, kappa=1.0, and sub-50ms latency."""
        data = json.loads(BENCHMARK_RESULTS_PATH.read_text(encoding="utf-8"))
        metrics = data["metrics"]
        lat = data["latency_profile_ms"]
        det = data["determinism_verification"]

        assert metrics["accuracy"] >= 0.95
        assert metrics["cohens_kappa"] >= 0.90
        assert metrics["score_mae"] <= 0.01
        assert lat["max"] < 50.0
        assert det["bit_for_bit_identical"] is True
