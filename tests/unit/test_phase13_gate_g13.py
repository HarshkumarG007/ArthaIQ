"""Unit tests for Phase 13 Benchmark & Gate G13 Ratification Review.

Validates:
1. Phase 13 review report generation and pre-registered keep/defer/reject criteria audit.
2. Formal Gate G13 documentation in docs/pilot/gate-g13-review.md.
3. Model Card Phase 13 Addendum in docs/model-cards/model-card-final-v1.md.
4. Evidence Register Phase 13 claims in docs/research/evidence-register.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.run_phase13_review import run_phase13_review

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_phase13_gate_g13_report_runner(tmp_path: Path) -> None:
    """Verify scripts/run_phase13_review.py executes cleanly and ratifies Gate G13 GO."""
    eg_path = REPO_ROOT / "experiments" / "results" / "employer_graph_reaudit.json"
    ens_path = REPO_ROOT / "experiments" / "results" / "ensemble_reaudit.json"
    sk_path = REPO_ROOT / "experiments" / "results" / "skills_reaudit.json"
    traj_path = REPO_ROOT / "experiments" / "results" / "career_trajectory_reaudit.json"
    macro_path = REPO_ROOT / "experiments" / "results" / "macro_regimes_reaudit.json"
    cop_path = REPO_ROOT / "experiments" / "results" / "copula_pt4_report.json"
    out_path = tmp_path / "test_g13_report.json"

    for p in (eg_path, ens_path, sk_path, traj_path, macro_path, cop_path):
        assert p.exists(), f"Missing required input report at {p}"

    report = run_phase13_review(
        employer_graph_report_path=eg_path,
        ensemble_report_path=ens_path,
        skills_report_path=sk_path,
        career_trajectory_report_path=traj_path,
        macro_regimes_report_path=macro_path,
        copula_pt4_report_path=cop_path,
        output_json_path=out_path,
    )

    assert report["verdict"] == "GO"
    assert "RATIFIED / UNCONDITIONAL GO" in report["recommendation"]

    # Verify Charter Summaries
    summaries = report["charter_summaries"]
    assert summaries["EXP-10r"]["verdict"] == "DEFER"
    assert summaries["EXP-10r"]["gate1_passed"] is False
    assert summaries["EXP-10r"]["qualified_clusters"] == 16
    assert summaries["EXP-10r"]["next_trigger_condition"]

    assert summaries["EXP-ENSEMBLE-01r"]["verdict"] == "REJECT"
    assert summaries["EXP-ENSEMBLE-01r"]["delta_pinball_loss_lpa"] > 0
    assert summaries["EXP-ENSEMBLE-01r"]["interval_width_ratio"] > 1.0

    assert summaries["EXP-09r"]["verdict"] == "DEFER"
    assert summaries["EXP-09r"]["gate1_passed"] is False
    assert summaries["EXP-09r"]["achieved_power_pct"] < 80.0
    assert summaries["EXP-09r"]["next_trigger_condition"]

    assert summaries["EXP-TRAJ-r"]["verdict"] == "DEFER"
    assert summaries["EXP-TRAJ-r"]["gate1_passed"] is False
    assert summaries["EXP-TRAJ-r"]["realized_span_months"] < 12.0
    assert summaries["EXP-TRAJ-r"]["next_trigger_condition"]

    assert summaries["EXP-MACRO-01r"]["verdict"] == "DEFER"
    assert summaries["EXP-MACRO-01r"]["gate1_passed"] is False
    assert summaries["EXP-MACRO-01r"]["realized_span_months"] < 24.0
    assert summaries["EXP-MACRO-01r"]["next_trigger_condition"]

    exp_cop = summaries["EXP-PGM-01r"]
    assert exp_cop["verdict"] == "PROMOTE"
    assert exp_cop["max_spearman_error"] <= 0.050
    assert exp_cop["quantile_crossing_rate_pct"] == 0.0
    assert 75.0 <= exp_cop["empirical_joint_coverage_pct"] <= 85.0
    assert exp_cop["latency_p95_ms"] <= 25.0
    assert exp_cop["zero_lone_number_compliant"] is True
    assert exp_cop["core_model_uncontaminated"] is True

    # Check Phase 13 Gate GO Conditions
    gate_conds = report["phase13_gate_conditions"]
    for cond_name, cond in gate_conds.items():
        assert cond["passed"] is True, f"Condition {cond_name} did not pass: {cond}"


def test_gate_g13_review_doc_exists_and_complete() -> None:
    """Verify docs/pilot/gate-g13-review.md exists and contains all required governance sections."""
    doc_path = REPO_ROOT / "docs" / "pilot" / "gate-g13-review.md"
    assert doc_path.is_file(), f"Missing {doc_path}"
    content = doc_path.read_text(encoding="utf-8")

    required_sections = [
        "# Gate G13 Milestone Review & Architecture Re-evaluation",
        "## 1. Executive Determination",
        "## 2. Review Panel Membership & Signatures",
        "## 3. Quantitative Scorecard: Phase 13 Feasibility Re-audits & Trigger Registry",
        "## 4. Quantitative Scorecard: EXP-PGM-01r Gaussian Copula Keep Criteria",
        "## 5. Adversarial Review Checklist (Rule R-MD-05, Section 15)",
        "## 6. Architecture Promotions & Decisions Ratified",
        "## 7. Completion of Phase 13 & Future Roadmap",
    ]
    for section in required_sections:
        assert section in content, f"Missing section '{section}' in {doc_path}"

    assert "RATIFIED GO" in content
    assert "Decision D-024" in content
    assert content.count("| **GO** | 2026-10-23 |") >= 5

    # Verify all 14 adversarial checklist questions
    for q_idx in range(1, 15):
        assert f"{q_idx}. **" in content, (
            f"Checklist question {q_idx} not found in gate-g13-review.md"
        )


def test_model_card_phase13_addendum() -> None:
    """Verify docs/model-cards/model-card-final-v1.md includes Phase 13 Addendum and v1.3.0."""
    card_path = REPO_ROOT / "docs" / "model-cards" / "model-card-final-v1.md"
    assert card_path.is_file(), f"Missing {card_path}"
    content = card_path.read_text(encoding="utf-8")

    assert "1.3.0" in content
    assert "Phase 13 Promotion" in content
    assert (
        "Phase 13 Addendum: Multi-Component Copula Scenario Structure & Re-audit Ratification"
        in content
    )
    assert "copula_pt4_experiment.py" in content
    assert "EXP-PGM-01r" in content
    assert "EXP-ENSEMBLE-01r" in content


def test_evidence_register_phase13_claims() -> None:
    """Verify docs/research/evidence-register.csv includes Phase 13 claims (Claims 25-30)."""
    register_path = REPO_ROOT / "docs" / "research" / "evidence-register.csv"
    assert register_path.is_file(), f"Missing {register_path}"

    with register_path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Header + 29 claims = 30 rows
    assert len(rows) >= 30, f"Expected at least 30 rows in {register_path}, got {len(rows)}"

    content = register_path.read_text(encoding="utf-8")
    assert "EXP-10r" in content
    assert "CHARTER-ENSEMBLING-STACKING" in content or "Quantile Ensembling" in content
    assert "EXP-09r" in content
    assert "EXP-TRAJ" in content
    assert "EXP-MACRO" in content
    assert "EXP-PGM" in content
