"""Unit tests for Phase 12 Benchmark & Gate G12 Ratification Review (Task T12.03).

Validates:
1. Phase 12 review report generation and pre-registered keep criteria audit.
2. Formal Gate G12 documentation in docs/pilot/gate-g12-review.md.
3. Model Card Phase 12 Addendum in docs/model-cards/model-card-final-v1.md.
4. Evidence Register Phase 12 claims in docs/research/evidence-register.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.run_phase12_review import run_phase12_review

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_phase12_gate_g12_report_runner(tmp_path: Path) -> None:
    """Verify scripts/run_phase12_review.py executes cleanly and ratifies Gate G12 GO."""
    al_path = REPO_ROOT / "experiments" / "results" / "active_learning_report.json"
    cf_path = REPO_ROOT / "experiments" / "results" / "counterfactual_report.json"
    out_path = tmp_path / "test_g12_report.json"

    assert al_path.exists(), f"Missing EXP-14 report at {al_path}"
    assert cf_path.exists(), f"Missing EXP-15 report at {cf_path}"

    report = run_phase12_review(
        active_learning_report_path=al_path,
        counterfactual_report_path=cf_path,
        output_json_path=out_path,
    )

    assert report["verdict"] == "GO"
    assert "UNCONDITIONAL GO" in report["recommendation"]

    # Check EXP-14 summary
    exp14 = report["charter_summaries"]["EXP-14"]
    assert exp14["verdict"] == "PROMOTE"
    assert exp14["all_criteria_passed"] is True
    assert exp14["sparse_width_reduction_pct"] >= 20.0
    assert exp14["abstention_reduction_pp"] >= 15.0
    assert 75.0 <= exp14["empirical_coverage_pct"] <= 85.0
    assert exp14["relative_cost_ratio"] <= 2.0

    # Check EXP-15 summary
    exp15 = report["charter_summaries"]["EXP-15"]
    assert exp15["verdict"] == "PROMOTE"
    assert exp15["all_criteria_passed"] is True
    assert exp15["monotonicity_satisfaction_pct"] >= 98.0
    assert 75.0 <= exp15["empirical_coverage_pct"] <= 85.0
    assert exp15["zero_lone_number_compliance_pct"] == 100.0
    assert exp15["latency_p95_ms"] <= 150.0

    # Check Phase 12 Gate GO Conditions
    gate_conds = report["phase12_gate_conditions"]
    assert gate_conds["sparse_cell_width_narrows_ge_20pct"]["passed"] is True
    assert gate_conds["pt4_monotonicity_ge_98pct"]["passed"] is True
    assert gate_conds["zero_lone_numbers_in_counterfactual_outputs"]["passed"] is True


def test_gate_g12_review_doc_exists_and_complete() -> None:
    """Verify docs/pilot/gate-g12-review.md exists and contains all required governance sections."""
    doc_path = REPO_ROOT / "docs" / "pilot" / "gate-g12-review.md"
    assert doc_path.is_file(), f"Missing {doc_path}"
    content = doc_path.read_text(encoding="utf-8")

    required_sections = [
        "# Gate G12 Milestone Review & Production Promotion",
        "## 1. Executive Determination",
        "## 2. Review Panel Membership & Signatures",
        "## 3. Quantitative Scorecard: EXP-14 Pre-Registered Keep Criteria",
        "## 4. Quantitative Scorecard: EXP-15 Pre-Registered Keep Criteria",
        "## 5. Adversarial Review Checklist (Rule R-MD-05, Section 15)",
        "## 6. Architecture Promotions & Decisions Ratified",
        "## 7. Authorization for Phase 13",
    ]
    for section in required_sections:
        assert section in content, f"Missing section '{section}' in {doc_path}"

    assert "RATIFIED GO" in content
    assert "Decision D-023" in content
    assert "Phase 13: Deferred Architecture Re-evaluation" in content


def test_model_card_phase12_addendum() -> None:
    """Verify docs/model-cards/model-card-final-v1.md includes Phase 12 Addendum and v1.2.0."""
    card_path = REPO_ROOT / "docs" / "model-cards" / "model-card-final-v1.md"
    assert card_path.is_file(), f"Missing {card_path}"
    content = card_path.read_text(encoding="utf-8")

    assert "1.2.0 (Phase 12 Promotion)" in content
    assert "Phase 12 Addendum: Active Learning & Counterfactual Scenario Intelligence" in content
    assert "compintel.acquisition.active_learning" in content
    assert "compintel.serving.counterfactual" in content
    assert "Section 115BAC" in content


def test_evidence_register_phase12_claims() -> None:
    """Verify docs/research/evidence-register.csv contains Claims 21 to 24."""
    reg_path = REPO_ROOT / "docs" / "research" / "evidence-register.csv"
    assert reg_path.is_file(), f"Missing {reg_path}"

    with reg_path.open(encoding="utf-8") as f:
        reader = list(csv.reader(f))

    # Header + 24 claims = 25 rows
    assert len(reader) >= 25, f"Expected at least 25 rows in evidence register, got {len(reader)}"

    claims_text = " ".join(" ".join(row) for row in reader)
    assert "Uncertainty-guided active learning policy (EXP-14)" in claims_text
    assert "Multi-channel targeted recruitment routing achieves 0.27x cost" in claims_text
    assert "Constrained counterfactual quantile inversion (EXP-15)" in claims_text
    assert (
        "Counterfactual scenario frontier generation strictly enforces 100% "
        "zero point-estimate compliance" in claims_text
    )
