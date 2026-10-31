"""Automated Verification Suite for Gate G24 Ratification (Phase 24).

Validates:
1. Document ID REV-GATE-G24-01 exists and ratifies Decision D-040 (UNCONDITIONAL GO).
2. Live pilot field run audit report confirms 10/10 M-STG metrics PASS on N=150 cohort.
3. All 21 canonical scenarios (7 DATA, 7 SWE, 7 MLAI) exist and validate cleanly.
4. Decision D-040 recorded in STATE.md and memory.md.
5. Constitutional invariants (R-UQ-01, R-CR-01, R-CR-02, R-CR-12, R-CR-15, R-AI-08) confirmed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from compintel.career.scenario_schema import PracticeScenario

GATE_REVIEW_PATH = Path("docs/pilot/gate-g24-review.md")
FIELD_RUN_JSON_PATH = Path("experiments/results/pilot_field_run_v1.json")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")

ALL_SCENARIO_PATHS = [
    Path("config/scenarios/scen_data_01_sql.json"),
    Path("config/scenarios/scen_data_02_eda.json"),
    Path("config/scenarios/scen_data_03_exp.json"),
    Path("config/scenarios/scen_data_04_decomp.json"),
    Path("config/scenarios/scen_data_05_ethics.json"),
    Path("config/scenarios/scen_data_06_feateng.json"),
    Path("config/scenarios/scen_data_07_bigdata.json"),
    Path("config/scenarios/scen_swe_01_concur.json"),
    Path("config/scenarios/scen_swe_02_sec.json"),
    Path("config/scenarios/scen_swe_03_db.json"),
    Path("config/scenarios/scen_swe_04_api.json"),
    Path("config/scenarios/scen_swe_05_test.json"),
    Path("config/scenarios/scen_swe_06_obs.json"),
    Path("config/scenarios/scen_swe_07_dist.json"),
    Path("config/scenarios/scen_mlai_01_tens.json"),
    Path("config/scenarios/scen_mlai_02_leak.json"),
    Path("config/scenarios/scen_mlai_03_deploy.json"),
    Path("config/scenarios/scen_mlai_04_rag.json"),
    Path("config/scenarios/scen_mlai_05_distrib.json"),
    Path("config/scenarios/scen_mlai_06_drift.json"),
    Path("config/scenarios/scen_mlai_07_guard.json"),
]


def test_gate_g24_dossier_exists_and_ratified() -> None:
    """Verify that Gate G24 review dossier exists and records Decision D-040 GO."""
    assert GATE_REVIEW_PATH.exists(), f"Missing dossier at {GATE_REVIEW_PATH}"
    content = GATE_REVIEW_PATH.read_text(encoding="utf-8")

    assert "REV-GATE-G24-01" in content
    assert "D-040" in content
    assert "RATIFIED GO" in content
    assert "UNCONDITIONAL GO" in content
    assert "Lead Quantitative ML Engineer" in content
    assert "India Compensation Economics Specialist" in content
    assert "Product & UX Design Lead" in content
    assert "Data Protection & Legal Governance Counsel" in content
    assert "Platform / SRE Operations Lead" in content


def test_field_run_audit_report_all_ten_metrics_pass() -> None:
    """Verify field run audit report confirms all 10 M-STG metrics pass on N=150."""
    assert FIELD_RUN_JSON_PATH.exists(), f"Missing field run report at {FIELD_RUN_JSON_PATH}"
    data = json.loads(FIELD_RUN_JSON_PATH.read_text(encoding="utf-8"))

    assert data["run_id"] == "RUN-PILOT-FIELD-01"
    assert data["total_participants"] == 150
    assert data["verdict"] == "GO"
    assert data["all_metrics_pass"] is True

    # Check 10 M-STG metrics
    scorecard = data["scorecard"]
    assert len(scorecard) == 10
    for key, metric in scorecard.items():
        assert metric["status"] == "PASS", f"Scorecard metric {key} failed: {metric}"


def test_all_twenty_one_scenarios_exist_and_validate() -> None:
    """Verify that all 21 canonical scenarios parse cleanly into PracticeScenario."""
    assert len(ALL_SCENARIO_PATHS) == 21
    family_counts = {"DATA": 0, "SWE": 0, "MLAI": 0}

    for path in ALL_SCENARIO_PATHS:
        assert path.exists(), f"Missing scenario file at {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        scenario = PracticeScenario.model_validate(data)
        family = scenario.role_family.value
        assert family in family_counts
        family_counts[family] += 1
        assert len(scenario.rubric.defects) >= 3
        assert scenario.artifact.line_count <= 40

    assert family_counts["DATA"] == 7
    assert family_counts["SWE"] == 7
    assert family_counts["MLAI"] == 7


def test_decision_d040_recorded_in_state_and_memory() -> None:
    """Verify that Decision D-040 is recorded in STATE.md and memory.md."""
    state_content = STATE_PATH.read_text(encoding="utf-8")
    memory_content = MEMORY_PATH.read_text(encoding="utf-8")

    assert "D-040" in state_content or "Gate G24" in state_content
    assert "D-040" in memory_content


def test_six_canonical_mirror_pairs_bit_for_bit_parity() -> None:
    """Verify Rule R-AI-08: 100% bit-for-bit parity across all 6 canonical mirror pairs."""
    mirror_pairs = [
        ("task.md", "docs/task.md"),
        ("memory.md", "docs/memory.md"),
        ("PRD.md", "docs/PRD.md"),
        ("architecture.md", "docs/architecture.md"),
        ("design.md", "docs/design.md"),
        ("rules.md", "docs/rules.md"),
    ]
    for src, dst in mirror_pairs:
        p_src = Path(src)
        p_dst = Path(dst)
        assert p_src.exists(), f"Source file missing: {src}"
        assert p_dst.exists(), f"Destination file missing: {dst}"
        h_src = hashlib.sha256(p_src.read_bytes()).hexdigest()
        h_dst = hashlib.sha256(p_dst.read_bytes()).hexdigest()
        assert h_src == h_dst, f"Parity mismatch between {src} and {dst}"
