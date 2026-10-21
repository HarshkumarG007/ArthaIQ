"""Automated security scanning script for CompIntel repository.

Audits:
1. Python dependencies (via pip-audit / OSV)
2. Web dependencies (via npm audit --omit=dev)
3. Repository secret scanning (regex patterns for tokens, keys, credentials)
4. Static application security testing (SAST via Bandit)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScanResult:
    check_name: str
    passed: bool
    details: str
    findings_count: int


SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private cryptographic key"),
    (r"(?:AKIA|ASIA)[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}", "GitHub Personal Access Token"),
    (r"glpat-[0-9a-zA-Z\-_]{20}", "GitLab Personal Access Token"),
    (r"slack[_-]?token\s*[:=]\s*['\"]xox[baprs]-[0-9a-zA-Z]{10,48}['\"]", "Slack Token"),
    (
        r"bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*",
        "Hardcoded Bearer / JWT Token",
    ),
    (
        r"(?:password|passwd|pwd|secret)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "Hardcoded credential string",
    ),
]

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "artifacts",
}

IGNORED_EXTENSIONS = {
    ".pyc",
    ".lock",
    ".woff2",
    ".woff",
    ".ttf",
    ".png",
    ".jpg",
    ".jpeg",
    ".ico",
    ".svg",
    ".parquet",
}


def scan_for_secrets(root_dir: Path) -> ScanResult:
    """Scan all project files for hardcoded secrets and sensitive credentials."""
    findings: list[str] = []

    compiled_patterns = [(re.compile(p, re.IGNORECASE), desc) for p, desc in SECRET_PATTERNS]

    for path in root_dir.rglob("*"):
        if not path.is_file():
            continue

        # Skip ignored directories and extensions
        if any(ignored in path.parts for ignored in IGNORED_DIRECTORIES):
            continue
        if path.suffix.lower() in IGNORED_EXTENSIONS:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, desc in compiled_patterns:
            matches = pattern.finditer(content)
            for m in matches:
                matched_text = m.group(0)
                # Allow synthetic test tokens and placeholders
                if any(
                    allowed in matched_text.lower()
                    for allowed in ["test", "synthetic", "example", "placeholder", "mock"]
                ):
                    continue
                # Allow generic env var references
                if "os.getenv" in content[max(0, m.start() - 50) : min(len(content), m.end() + 50)]:
                    continue
                rel_path = path.relative_to(root_dir)
                line_no = content[: m.start()].count("\n") + 1
                findings.append(f"{rel_path}:{line_no} [{desc}] -> {matched_text[:20]}...")

    passed = len(findings) == 0
    return ScanResult(
        check_name="Secret Scan",
        passed=passed,
        details="\n".join(findings)
        if findings
        else "Zero unapproved secrets or tokens discovered.",
        findings_count=len(findings),
    )


def audit_python_dependencies() -> ScanResult:
    """Run pip-audit on current virtual environment packages."""
    try:
        res = subprocess.run(
            ["uvx", "pip-audit", "--path", ".venv/Lib/site-packages", "-f", "json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if res.returncode == 0:
            return ScanResult(
                check_name="Python Dependencies (pip-audit)",
                passed=True,
                details="Zero known vulnerabilities in Python dependencies.",
                findings_count=0,
            )
        try:
            audit_data = json.loads(res.stdout)
            vulns = audit_data.get("dependencies", [])
            vuln_count = sum(len(d.get("vulns", [])) for d in vulns)
            return ScanResult(
                check_name="Python Dependencies (pip-audit)",
                passed=vuln_count == 0,
                details=res.stdout[:500],
                findings_count=vuln_count,
            )
        except json.JSONDecodeError:
            # Check if output contains "No known vulnerabilities found"
            if (
                "No known vulnerabilities found" in res.stdout
                or "No known vulnerabilities found" in res.stderr
            ):
                return ScanResult(
                    check_name="Python Dependencies (pip-audit)",
                    passed=True,
                    details="Zero known vulnerabilities in Python dependencies.",
                    findings_count=0,
                )
            return ScanResult(
                check_name="Python Dependencies (pip-audit)",
                passed=False,
                details=f"pip-audit failed: {res.stderr or res.stdout}",
                findings_count=1,
            )
    except Exception as exc:
        return ScanResult(
            check_name="Python Dependencies (pip-audit)",
            passed=False,
            details=f"Execution error: {exc}",
            findings_count=1,
        )


def audit_node_dependencies(web_dir: Path) -> ScanResult:
    """Run npm audit on web production dependencies."""
    if not web_dir.exists() or not (web_dir / "package.json").exists():
        return ScanResult(
            check_name="Node Production Dependencies (npm audit)",
            passed=True,
            details="Web directory not present, skipped.",
            findings_count=0,
        )
    try:
        res = subprocess.run(
            ["npm", "audit", "--omit=dev", "--json"],
            cwd=web_dir,
            capture_output=True,
            text=True,
            check=False,
            shell=True,
            timeout=60,
        )
        try:
            data = json.loads(res.stdout)
            metadata = data.get("metadata", {}).get("vulnerabilities", {})
            high = metadata.get("high", 0)
            critical = metadata.get("critical", 0)
            total = high + critical
            passed = total == 0
            return ScanResult(
                check_name="Node Production Dependencies (npm audit)",
                passed=passed,
                details=f"Production vulnerabilities: High={high}, Critical={critical}, Total={metadata.get('total', 0)}",
                findings_count=total,
            )
        except json.JSONDecodeError:
            # If exit code was 0, no vulnerabilities found
            passed = res.returncode == 0
            return ScanResult(
                check_name="Node Production Dependencies (npm audit)",
                passed=passed,
                details=res.stdout[:300] or "Zero production vulnerabilities.",
                findings_count=0 if passed else 1,
            )
    except Exception as exc:
        return ScanResult(
            check_name="Node Production Dependencies (npm audit)",
            passed=False,
            details=f"Execution error: {exc}",
            findings_count=1,
        )


def run_bandit_sast(target_dir: Path) -> ScanResult:
    """Run Bandit SAST for Medium and High severity security issues."""
    try:
        res = subprocess.run(
            [".venv/Scripts/bandit.exe", "-r", str(target_dir), "-ll", "-f", "json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        stdout = res.stdout
        # Extract JSON starting from the first '{' and ending at last '}'
        start_idx = stdout.find("{")
        end_idx = stdout.rfind("}")
        if start_idx != -1 and end_idx != -1:
            json_str = stdout[start_idx : end_idx + 1]
            try:
                data = json.loads(json_str)
                metrics = data.get("metrics", {}).get("_totals", {})
                med = metrics.get("SEVERITY.MEDIUM", 0)
                high = metrics.get("SEVERITY.HIGH", 0)
                findings = med + high
                passed = findings == 0
                return ScanResult(
                    check_name="SAST (Bandit Medium/High)",
                    passed=passed,
                    details=f"Bandit findings: High={high}, Medium={med}, Total={findings}",
                    findings_count=findings,
                )
            except json.JSONDecodeError:
                pass

        passed = res.returncode == 0
        return ScanResult(
            check_name="SAST (Bandit Medium/High)",
            passed=passed,
            details=stdout[:300] if not passed else "Zero Medium or High security issues found.",
            findings_count=0 if passed else 1,
        )
    except Exception as exc:
        return ScanResult(
            check_name="SAST (Bandit Medium/High)",
            passed=False,
            details=f"Execution error: {exc}",
            findings_count=1,
        )


def main() -> int:
    root = Path.cwd()
    web_dir = root / "apps" / "web"
    src_dir = root / "src" / "compintel"

    print("=" * 60)
    print("CompIntel Security Verification Scanner (T9.12a)")
    print("=" * 60)

    results: list[ScanResult] = []

    print("\n[1/4] Scanning repository for hardcoded secrets...")
    sec_res = scan_for_secrets(root)
    results.append(sec_res)
    print(f"      Status: {'PASS' if sec_res.passed else 'FAIL'} ({sec_res.details})")

    print("\n[2/4] Auditing Python dependencies with pip-audit...")
    py_res = audit_python_dependencies()
    results.append(py_res)
    print(f"      Status: {'PASS' if py_res.passed else 'FAIL'} ({py_res.details})")

    print("\n[3/4] Auditing Node production dependencies with npm audit...")
    node_res = audit_node_dependencies(web_dir)
    results.append(node_res)
    print(f"      Status: {'PASS' if node_res.passed else 'FAIL'} ({node_res.details})")

    print("\n[4/4] Running SAST analysis with Bandit (Medium/High)...")
    bandit_res = run_bandit_sast(src_dir)
    results.append(bandit_res)
    print(f"      Status: {'PASS' if bandit_res.passed else 'FAIL'} ({bandit_res.details})")

    print("\n" + "=" * 60)
    all_passed = all(r.passed for r in results)
    print(f"Overall Security Verification: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 60)

    for r in results:
        status_symbol = "[PASS]" if r.passed else "[FAIL]"
        print(f"  {status_symbol} {r.check_name}: {r.details}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
