"""Unit tests for Master QA Plan, Automated Smoke Harness & Regression Matrix (T9.15a).

Validates:
1. Master QA plan structure, 8-tier test pyramid, pre-registered thresholds, and exit criteria.
2. scripts/run_qa_smoke.py CLI commands, tier filters, execution simulation,
   and JSON report generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from scripts.run_qa_smoke import (
    CHECKS_DEFINITIONS,
    build_parser,
    execute_qa_suite,
    main,
    run_command,
)


# -----------------------------------------------------------------------------
# 1. QA Plan Documentation Integrity Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_qa_plan_document_structure() -> None:
    """Verifies that docs/qa/qa-plan-t915.md exists and contains all required sections."""
    plan_path = Path("docs/qa/qa-plan-t915.md")
    assert plan_path.exists(), "Master QA Plan must exist at docs/qa/qa-plan-t915.md"

    content = plan_path.read_text(encoding="utf-8")

    # Thresholds Matrix
    assert "Pre-Registered Product Thresholds Matrix" in content
    assert "p95 HTTP response latency" in content
    assert "<= 50" in content or "50\\text{ ms}" in content
    assert "k \\ge 5" in content or "k_\\min" in content
    assert "DPDPA 2023" in content
    assert "90.0" in content

    # 8-Tier Pyramid
    assert "The 8-Tier Quality Test Pyramid" in content
    assert "Tier 1: Static Analysis & Architectural Boundaries" in content
    assert "Tier 2: Unit Testing" in content
    assert "Tier 3: Property-Based Testing" in content
    assert "Tier 4: Contract Testing" in content
    assert "Tier 5: Leakage & Temporal Split Audits" in content
    assert "Tier 6: Integration Testing & Migrations" in content
    assert "Tier 7: Automated End-to-End Smoke Verification" in content
    assert "Tier 8: Non-Functional & Stress Testing" in content

    # Defect Triage & Exit Criteria
    assert "Defect Classification & Triage Rubric" in content
    assert "P0 (Blocker)" in content
    assert "P1 (Critical)" in content
    assert "Exit Criteria for Public Beta Readiness" in content


# -----------------------------------------------------------------------------
# 2. run_qa_smoke.py CLI and Execution Logic Tests
# -----------------------------------------------------------------------------
@pytest.mark.unit
def test_checks_definitions_completeness() -> None:
    """Verifies all required verification tiers are declared in CHECKS_DEFINITIONS."""
    tiers = {c["tier"] for c in CHECKS_DEFINITIONS}
    assert "static" in tiers
    assert "backend" in tiers
    assert "security" in tiers
    assert "frontend" in tiers
    assert "deploy" in tiers
    assert len(CHECKS_DEFINITIONS) >= 12


@pytest.mark.unit
def test_qa_smoke_parser_arguments() -> None:
    """Tests CLI argument parsing across all supported options."""
    parser = build_parser()

    args_default = parser.parse_args([])
    assert args_default.tier == "all"
    assert args_default.dry_run is False
    assert args_default.timeout == 120.0
    assert args_default.json_out is None

    args_custom = parser.parse_args(
        [
            "--tier",
            "security",
            "--dry-run",
            "--timeout",
            "60",
            "--json-out",
            "report.json",
        ]
    )
    assert args_custom.tier == "security"
    assert args_custom.dry_run is True
    assert args_custom.timeout == 60.0
    assert args_custom.json_out == "report.json"


@pytest.mark.unit
def test_run_command_dry_run() -> None:
    """Tests run_command in dry-run mode."""
    passed, duration, snippet = run_command(["echo", "hello"], dry_run=True)
    assert passed is True
    assert duration < 0.1
    assert "DRY-RUN" in snippet


@pytest.mark.unit
@patch("subprocess.run")
def test_run_command_real_success(mock_run: MagicMock) -> None:
    """Tests run_command with successful mocked subprocess output."""
    mock_run.return_value = MagicMock(returncode=0, stdout="All checks passed", stderr="")
    passed, duration, snippet = run_command(["mock_cmd"], dry_run=False)
    assert passed is True
    assert "All checks passed" in snippet


@pytest.mark.unit
@patch("subprocess.run")
def test_run_command_real_failure(mock_run: MagicMock) -> None:
    """Tests run_command with failing mocked subprocess output."""
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error encountered")
    passed, duration, snippet = run_command(["mock_cmd"], dry_run=False)
    assert passed is False
    assert "Error encountered" in snippet


@pytest.mark.unit
def test_execute_qa_suite_tier_filter() -> None:
    """Tests executing a specific tier in dry-run mode."""
    results_static = execute_qa_suite(tier_filter="static", dry_run=True)
    assert len(results_static) >= 3
    assert all(r.tier == "static" for r in results_static)
    assert all(r.passed for r in results_static)

    results_security = execute_qa_suite(tier_filter="security", dry_run=True)
    assert len(results_security) >= 1
    assert all(r.tier == "security" for r in results_security)


@pytest.mark.unit
def test_main_entrypoint_with_json_output(tmp_path: Path) -> None:
    """Tests main entrypoint generating structured JSON output in dry-run mode."""
    json_path = tmp_path / "qa_results.json"
    exit_code = main(["--dry-run", "--tier", "static", "--json-out", str(json_path)])
    assert exit_code == 0
    assert json_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["tier_filter"] == "static"
    assert data["failed_checks"] == 0
    assert data["passed_checks"] == data["total_checks"]
    assert len(data["checks"]) == data["total_checks"]
