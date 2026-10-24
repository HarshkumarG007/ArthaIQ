"""Unit test verifying Antigravity Agent Configuration and Rules Lint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_agent_rules_lint_passes() -> None:
    """Verify scripts/lint_agent_rules.py returns 0 with no errors."""
    script_path = REPO_ROOT / "scripts" / "lint_agent_rules.py"
    assert script_path.is_file(), f"Missing {script_path}"

    res = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"Linter failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "[SUCCESS]" in res.stdout
