"""Automated Verification Suite for Gate G22 Ratification (Phase 22).

Validates:
1. Document ID REV-GATE-G22-01 exists and ratifies Decision D-038 (UNCONDITIONAL GO).
2. All 4 new canonical MLAI scenario JSON files parse into PracticeScenario with valid line bounds.
3. Multi-expert practitioner consensus dossier confirms kappa = 0.900 >= 0.850.
4. Staging simulation evaluates 21 scenarios across 300 attempts with 10/10 M-STG metrics PASS.
5. Constitutional invariants (R-UQ-01, R-CR-01, R-CR-02, R-CR-15, R-AI-08) strictly confirmed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from compintel.career.scenario_schema import PracticeScenario

GATE_REVIEW_PATH = Path("docs/pilot/gate-g22-review.md")
CONSENSUS_PATH = Path("docs/pilot/scenario-review-mlai-corpus-expansion.md")
STAGING_JSON_PATH = Path("experiments/results/career_pilot_staging_audit_v1.json")
WORKSPACE_PATH = Path("apps/web/src/components/career/PracticeWorkspace.tsx")
ROADMAP_PATH = Path("apps/web/src/components/career/RoadmapView.tsx")

NEW_SCENARIO_PATHS = [
    Path("config/scenarios/scen_mlai_04_rag.json"),
    Path("config/scenarios/scen_mlai_05_distrib.json"),
    Path("config/scenarios/scen_mlai_06_drift.json"),
    Path("config/scenarios/scen_mlai_07_guard.json"),
]


def test_gate_g22_dossier_exists_and_ratified() -> None:
    """Verify that Gate G22 review dossier exists and records Decision D-038 GO."""
    assert GATE_REVIEW_PATH.exists(), f"Missing dossier at {GATE_REVIEW_PATH}"
    content = GATE_REVIEW_PATH.read_text(encoding="utf-8")

    assert "REV-GATE-G22-01" in content
    assert "D-038" in content
    assert "RATIFIED GO" in content
    assert "UNCONDITIONAL GO" in content
    assert "Lead Quantitative ML Engineer" in content
    assert "India Compensation Economics Specialist" in content
    assert "Product & UX Design Lead" in content
    assert "Data Protection & Legal Governance Counsel" in content
    assert "Platform / SRE Operations Lead" in content


def test_all_four_new_mlai_scenarios_exist_and_validate() -> None:
    """Verify all 4 new scenario JSON files parse cleanly and adhere to line bounds."""
    for path in NEW_SCENARIO_PATHS:
        assert path.exists(), f"Scenario file {path} missing"
        data = json.loads(path.read_text(encoding="utf-8"))
        scenario = PracticeScenario(**data)
        assert scenario.role_family == "MLAI"
        assert len(scenario.rubric.defects) >= 3
        assert scenario.artifact.line_count <= 40
        assert len(scenario.artifact.content.splitlines()) == scenario.artifact.line_count


def test_practitioner_consensus_dossier_ratified() -> None:
    """Verify practitioner consensus review dossier achieves kappa >= 0.850."""
    assert CONSENSUS_PATH.exists(), f"Consensus dossier {CONSENSUS_PATH} missing"
    content = CONSENSUS_PATH.read_text(encoding="utf-8")

    assert "REV-SCEN-MLAI-CORPUS-01" in content
    assert "0.900" in content
    assert "UNCONDITIONAL APPROVAL" in content or "UNANIMOUS APPROVAL" in content
    assert "Dr. Ananya Sen" in content
    assert "Vikramaditya Joshi" in content
    assert "Dr. Rajeshwari Sundaram" in content


def test_staging_simulation_audit_21_scenarios_pass() -> None:
    """Verify staging simulation audit confirms 21 scenarios and 10/10 M-STG metrics GO."""
    assert STAGING_JSON_PATH.exists(), f"Staging audit results {STAGING_JSON_PATH} missing"
    data = json.loads(STAGING_JSON_PATH.read_text(encoding="utf-8"))

    meta = data["metadata"]
    assert meta["scenario_count"] == 21
    assert meta["attempt_count"] == 300
    assert meta["status"] == "PASS"

    scorecard = data["scorecard"]
    expected_metrics = [
        "M-STG-01_calibration_comprehension",
        "M-STG-02_task_completion_rate",
        "M-STG-03_scoring_determinism_variance",
        "M-STG-04_scoring_latency_p95_ms",
        "M-STG-05_local_storage_footprint_kb",
        "M-STG-06_dpdp_sec12_hard_purge_bytes",
        "M-STG-07_zero_causal_promises",
        "M-STG-08_anti_credentialism",
        "M-STG-09_two_streams_two_places",
        "M-STG-10_cross_family_dag_monotonicity",
    ]
    for key in expected_metrics:
        assert key in scorecard
        assert scorecard[key]["status"] == "PASS"


def test_web_ui_registration_and_roadmap_links() -> None:
    """Verify scenarios are registered in PracticeWorkspace and linked in RoadmapView."""
    ws_content = WORKSPACE_PATH.read_text(encoding="utf-8")
    roadmap_content = ROADMAP_PATH.read_text(encoding="utf-8")

    for scen_id in [
        "SCEN-MLAI-04-VEC",
        "SCEN-MLAI-05-DIST",
        "SCEN-MLAI-06-DRIFT",
        "SCEN-MLAI-07-GUARD",
    ]:
        assert scen_id in ws_content, f"Scenario {scen_id} missing in PracticeWorkspace"
        assert scen_id in roadmap_content, f"Scenario {scen_id} missing in RoadmapView"


def test_constitutional_invariants_and_zero_causal_claims() -> None:
    """Verify constitutional invariants (R-UQ-01, R-CR-01, R-CR-02, R-CR-15)."""
    dossier_text = GATE_REVIEW_PATH.read_text(encoding="utf-8").lower()

    # R-CR-01: Zero causal pay promises
    forbidden_causal = ["guaranteed salary", "boost pay", "increase your pay by", "will earn"]
    for phrase in forbidden_causal:
        assert phrase not in dossier_text, f"Forbidden causal phrase '{phrase}' in dossier"

    assert "zero lone numbers" in dossier_text
    assert "two streams two places" in dossier_text
    assert "zero runtime llms" in dossier_text


def test_bit_for_bit_mirror_parity() -> None:
    """Verify Rule R-AI-08: 100% bit-for-bit parity across all 6 canonical mirror pairs."""
    pairs = ["task.md", "memory.md", "PRD.md", "architecture.md", "design.md", "rules.md"]
    for name in pairs:
        root_file = Path(name)
        docs_file = Path("docs") / name
        assert root_file.exists(), f"Root mirror {root_file} missing"
        assert docs_file.exists(), f"Docs mirror {docs_file} missing"

        hash_root = hashlib.sha256(root_file.read_bytes()).hexdigest()
        hash_docs = hashlib.sha256(docs_file.read_bytes()).hexdigest()
        assert hash_root == hash_docs, (
            f"Mirror mismatch on {name}: root={hash_root} vs docs={hash_docs}"
        )
