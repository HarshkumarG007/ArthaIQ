"""Automated Master QA Smoke Verification Runner (Phase 9, Task T9.15a).

Orchestrates multi-tier regression tests, static checks, database migrations,
frontend builds, contrast checks, and security audits according to docs/qa/qa-plan-t915.md.

Usage:
    uv run python scripts/run_qa_smoke.py [--tier {all,static,backend,frontend,security,deploy}]
    uv run python scripts/run_qa_smoke.py --dry-run
    uv run python scripts/run_qa_smoke.py --json-out experiments/results/qa_smoke_results.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class QACheckResult:
    check_name: str
    tier: str
    command: str
    passed: bool
    duration_sec: float
    output_snippet: str


def get_npm_executable() -> str:
    """Resolves npm executable path across platforms."""
    return shutil.which("npm.cmd") or shutil.which("npm") or "npm"


CHECKS_DEFINITIONS: list[dict[str, object]] = [
    # Tier 1: Static Analysis & Architectural Boundaries
    {
        "name": "ruff_lint",
        "tier": "static",
        "cmd": [sys.executable, "-m", "ruff", "check", "src/", "tests/", "scripts/"],
    },
    {
        "name": "ruff_format",
        "tier": "static",
        "cmd": [sys.executable, "-m", "ruff", "format", "--check", "src/", "tests/", "scripts/"],
    },
    {
        "name": "mypy_types",
        "tier": "static",
        "cmd": [sys.executable, "-m", "mypy", "src/compintel"],
    },
    {
        "name": "import_linter",
        "tier": "static",
        "cmd": [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports_command; import sys; sys.exit(lint_imports_command())",
        ],
    },
    # Tier 2: Backend Unit & Property Tests
    {
        "name": "pytest_unit",
        "tier": "backend",
        "cmd": [sys.executable, "-m", "pytest", "tests/unit/", "-q"],
    },
    {
        "name": "pytest_property",
        "tier": "backend",
        "cmd": [sys.executable, "-m", "pytest", "tests/property/", "-q"],
    },
    # Tier 3: Contracts & Leakage
    {
        "name": "pytest_contracts",
        "tier": "backend",
        "cmd": [sys.executable, "-m", "pytest", "tests/contract/", "-q"],
    },
    {
        "name": "pytest_leakage",
        "tier": "backend",
        "cmd": [sys.executable, "-m", "pytest", "tests/leakage/", "-q"],
    },
    # Tier 4: Integration & Lifecycle
    {
        "name": "pytest_integration",
        "tier": "backend",
        "cmd": [sys.executable, "-m", "pytest", "tests/integration/", "-q"],
    },
    # Tier 5: Security & Governance
    {
        "name": "security_scan",
        "tier": "security",
        "cmd": [sys.executable, "scripts/run_security_scan.py"],
    },
    # Tier 6: Frontend Design Tokens & Accessibility
    {
        "name": "wcag_contrast",
        "tier": "frontend",
        "cmd": [sys.executable, "scripts/check_contrast.py"],
    },
    {
        "name": "font_verification",
        "tier": "frontend",
        "cmd": [sys.executable, "scripts/verify_fonts.py"],
    },
    # Tier 7: Frontend Build & Component Tests
    {
        "name": "web_vitest",
        "tier": "frontend",
        "cmd": [get_npm_executable(), "test", "--prefix", "apps/web"],
    },
    {
        "name": "web_build",
        "tier": "frontend",
        "cmd": [get_npm_executable(), "run", "build", "--prefix", "apps/web"],
    },
    # Tier 8: Deployment & Compose Verification
    {
        "name": "preview_harness_dry_run",
        "tier": "deploy",
        "cmd": [sys.executable, "scripts/deploy_preview.py", "--dry-run", "up"],
    },
]


def run_command(
    command_args: Sequence[str],
    dry_run: bool = False,
    timeout_sec: float = 120.0,
) -> tuple[bool, float, str]:
    """Executes a command list without shell, safely handling spaces and cross-platform paths."""
    if dry_run:
        return True, 0.01, "[DRY-RUN] Command simulated successfully"

    start = time.perf_counter()
    try:
        res = subprocess.run(
            list(command_args),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_sec,
        )
        duration = time.perf_counter() - start
        combined_output = (res.stdout + "\n" + res.stderr).strip()
        snippet = combined_output[-500:] if len(combined_output) > 500 else combined_output
        return res.returncode == 0, duration, snippet
    except subprocess.TimeoutExpired:
        duration = time.perf_counter() - start
        return False, duration, f"Command timed out after {timeout_sec}s"
    except Exception as exc:  # noqa: BLE001
        duration = time.perf_counter() - start
        return False, duration, f"Execution failed: {exc}"


def execute_qa_suite(
    tier_filter: str = "all",
    dry_run: bool = False,
    timeout_sec: float = 120.0,
) -> list[QACheckResult]:
    """Runs all QA verification checks matching the tier filter."""
    results: list[QACheckResult] = []

    selected_checks = [
        c for c in CHECKS_DEFINITIONS if tier_filter == "all" or c["tier"] == tier_filter
    ]

    print(
        f"\n[QA-SMOKE] Executing {len(selected_checks)} QA verification checks (Tier: {tier_filter})...\n"
    )

    for check in selected_checks:
        name = str(check["name"])
        tier = str(check["tier"])
        cmd_raw = check["cmd"]
        cmd_args: list[str] = (
            list(cmd_raw) if isinstance(cmd_raw, (list, tuple)) else [str(cmd_raw)]
        )
        cmd_display = " ".join(cmd_args)

        print(f" -> Running [{tier.upper()}] {name}...", end="", flush=True)
        passed, duration, snippet = run_command(cmd_args, dry_run=dry_run, timeout_sec=timeout_sec)
        status_label = "PASS" if passed else "FAIL"
        print(f" [{status_label}] ({duration:.2f}s)")

        results.append(
            QACheckResult(
                check_name=name,
                tier=tier,
                command=cmd_display,
                passed=passed,
                duration_sec=duration,
                output_snippet=snippet,
            )
        )

    return results


def print_qa_summary(results: Sequence[QACheckResult]) -> None:
    """Prints a clean tabular summary of all QA verification results."""
    print("\n" + "=" * 80)
    print("COMPINTEL MASTER QA SMOKE VERIFICATION REPORT (T9.15a)")
    print("=" * 80)
    print(f"{'Check Name':<28} {'Tier':<10} {'Status':<8} {'Time (s)':<10} Details")
    print("-" * 80)

    for r in results:
        status_tag = "[PASS]" if r.passed else "[FAIL]"
        clean_snippet = r.output_snippet.replace("\n", " ")[:24]
        print(
            f"{r.check_name:<28} {r.tier:<10} {status_tag:<8} {r.duration_sec:<10.2f} {clean_snippet}"
        )

    print("=" * 80)
    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = total - passed_count
    print(f"TOTAL: {total} | PASSED: {passed_count} | FAILED: {failed_count}")
    print("=" * 80 + "\n")


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for QA smoke runner."""
    parser = argparse.ArgumentParser(
        description="CompIntel Master QA Smoke Verification Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--tier",
        choices=["all", "static", "backend", "frontend", "security", "deploy"],
        default="all",
        help="Filter checks by architectural verification tier",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate check execution without running subprocesses",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-check timeout in seconds",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Optional path to write structured JSON execution results",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results = execute_qa_suite(
        tier_filter=args.tier,
        dry_run=args.dry_run,
        timeout_sec=args.timeout,
    )
    print_qa_summary(results)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "timestamp": time.time(),
            "tier_filter": args.tier,
            "total_checks": len(results),
            "passed_checks": sum(1 for r in results if r.passed),
            "failed_checks": sum(1 for r in results if not r.passed),
            "checks": [asdict(r) for r in results],
        }
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[QA-SMOKE] Structured report written to {out_path}")

    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
