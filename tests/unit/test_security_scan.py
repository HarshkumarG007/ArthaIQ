"""Unit tests for automated security scan script (scripts/run_security_scan.py)."""

from pathlib import Path

import pytest
from scripts.run_security_scan import (
    SECRET_PATTERNS,
    ScanResult,
    audit_node_dependencies,
    run_bandit_sast,
    scan_for_secrets,
)


@pytest.mark.unit
def test_scan_result_dataclass() -> None:
    res = ScanResult(
        check_name="Test Check",
        passed=True,
        details="All passed",
        findings_count=0,
    )
    assert res.check_name == "Test Check"
    assert res.passed is True
    assert res.details == "All passed"
    assert res.findings_count == 0


@pytest.mark.unit
def test_scan_for_secrets_clean_directory(tmp_path: Path) -> None:
    # Create clean sample files
    (tmp_path / "sample.py").write_text("x = 42\ndef hello(): return 'world'\n", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("setting: true\nport: 8080\n", encoding="utf-8")

    result = scan_for_secrets(tmp_path)
    assert result.passed is True
    assert result.findings_count == 0
    assert "Zero unapproved secrets" in result.details


@pytest.mark.unit
def test_scan_for_secrets_detects_credentials(tmp_path: Path) -> None:
    # Inject a forbidden secret pattern dynamically so the test file itself does not match
    fake_key = "AKIA" + "1234567890ABCDEF"
    leak_file = tmp_path / "leak.py"
    leak_file.write_text(f"aws_key = '{fake_key}'\n", encoding="utf-8")

    result = scan_for_secrets(tmp_path)
    assert result.passed is False
    assert result.findings_count == 1
    assert "AWS Access Key ID" in result.details
    assert "leak.py:1" in result.details


@pytest.mark.unit
def test_scan_for_secrets_allows_synthetic_and_placeholders(tmp_path: Path) -> None:
    # Placeholders marked synthetic or test should not trigger false positives
    safe_file = tmp_path / "test_fixture.py"
    safe_file.write_text("test_secret = 'placeholder_secret_value_12345678'\n", encoding="utf-8")

    result = scan_for_secrets(tmp_path)
    assert result.passed is True
    assert result.findings_count == 0


@pytest.mark.unit
def test_secret_patterns_structure() -> None:
    assert len(SECRET_PATTERNS) >= 5
    for pattern, description in SECRET_PATTERNS:
        assert isinstance(pattern, str)
        assert isinstance(description, str)
        assert len(pattern) > 5
        assert len(description) > 3


@pytest.mark.unit
def test_audit_node_dependencies_missing_dir(tmp_path: Path) -> None:
    missing_dir = tmp_path / "nonexistent"
    result = audit_node_dependencies(missing_dir)
    assert result.passed is True
    assert result.findings_count == 0


@pytest.mark.unit
def test_run_bandit_sast_clean_dir(tmp_path: Path) -> None:
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    (tmp_path / "pure.py").write_text(code, encoding="utf-8")
    result = run_bandit_sast(tmp_path)
    assert result.passed is True
    assert result.findings_count == 0
