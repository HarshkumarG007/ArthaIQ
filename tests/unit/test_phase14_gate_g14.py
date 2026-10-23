"""Unit tests for Phase 14 Benchmark & Gate G14 Ratification Review.

Validates:
1. Phase 14 review report generation and pre-registered criteria audit.
2. Formal Gate G14 documentation in docs/pilot/gate-g14-review.md.
3. Evidence Register Phase 14 Claim 31 in docs/research/evidence-register.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.run_phase14_review import run_phase14_review

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_phase14_gate_g14_report_runner(tmp_path: Path) -> None:
    """Verify scripts/run_phase14_review.py executes cleanly and ratifies Gate G14 GO."""
    spec_path = REPO_ROOT / "config" / "sources" / "SRC-B2B-01.yaml"
    index_path = REPO_ROOT / "experiments" / "configs" / "charters" / "index.yaml"
    exp10_path = REPO_ROOT / "experiments" / "configs" / "charters" / "charter_exp10r_v2.yaml"
    traj_path = REPO_ROOT / "experiments" / "configs" / "charters" / "charter_career_traj_r_v2.yaml"
    out_path = tmp_path / "test_g14_report.json"

    for p in (spec_path, index_path, exp10_path, traj_path):
        assert p.exists(), f"Missing required input at {p}"

    report = run_phase14_review(
        spec_path=spec_path,
        charters_index_path=index_path,
        charter_exp10r_v2_path=exp10_path,
        charter_career_traj_v2_path=traj_path,
        output_json_path=out_path,
    )

    assert report["verdict"] == "GO"
    assert "RATIFIED / UNCONDITIONAL GO" in report["recommendation"]

    # Verify Deliverables Summary
    summary = report["deliverables_summary"]
    assert summary["SRC-B2B-01"]["specification_compliant"] is True
    assert summary["SRC-B2B-01"]["k_min_floor"] >= 5
    assert summary["SRC-B2B-01"]["dpdpa_2023_compliant"] is True
    assert summary["ingestion_and_privacy_pooling"]["privacy_pooler_passed"] is True
    assert summary["charter_preregistration"]["charters_valid"] is True
    assert summary["ui_and_operational_health"]["vitest_passing_count"] == 96


def test_gate_g14_review_doc_exists_and_valid() -> None:
    """Verify docs/pilot/gate-g14-review.md exists and documents Gate G14 GO ratification."""
    doc_path = REPO_ROOT / "docs" / "pilot" / "gate-g14-review.md"
    assert doc_path.exists(), f"Missing {doc_path}"

    content = doc_path.read_text(encoding="utf-8")
    assert "Gate G14" in content
    assert "RATIFIED GO" in content
    assert "SRC-B2B-01" in content
    assert "B2BPrivacyPooler" in content
    assert "CHARTER-EXP-10r-v2" in content
    assert "CHARTER-CAREER-TRAJ-r-v2" in content
    assert "D-025" in content


def test_evidence_register_claim_31_exists() -> None:
    """Verify Claim 31 is present in docs/research/evidence-register.csv."""
    register_path = REPO_ROOT / "docs" / "research" / "evidence-register.csv"
    assert register_path.exists(), f"Missing {register_path}"

    with open(register_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        claims = [row["claim_or_decision"] for row in reader]

    assert len(claims) >= 30, f"Expected at least 30 claims in register, found {len(claims)}"
    claim_31_matches = [c for c in claims if "SRC-B2B-01" in c or "B2B" in c]
    assert len(claim_31_matches) >= 1, "Claim regarding B2B syndication was not found in register"
