#!/usr/bin/env python3
"""Antigravity Agent Rules and Configuration Linter.

Validates that:
1. Root constitution AGENTS.md exists and is within token/size limits.
2. Every rule in .agents/rules/*.md has valid YAML frontmatter, proper triggers, and does not exceed 24 KB.
3. Always-on rules do not exceed the 20,000 token budget.
4. Every skill in .agents/skills/**/SKILL.md has valid name and description.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

MAX_RULE_FILE_BYTES = 24_576  # 24 KB
MAX_ALWAYS_ON_TOKENS = 20_000
APPROX_CHARS_PER_TOKEN = 4
MAX_ALWAYS_ON_CHARS = MAX_ALWAYS_ON_TOKENS * APPROX_CHARS_PER_TOKEN
VALID_TRIGGERS = {"always_on", "glob", "model_decision", "manual"}


def parse_frontmatter(content: str, path: Path) -> tuple[dict[str, Any], str]:
    """Extract and parse YAML frontmatter from markdown content."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: Missing starting frontmatter delimiter '---'")

    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        raise ValueError(f"{path}: Missing closing frontmatter delimiter '---'")

    yaml_block = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1 :])

    try:
        data = yaml.safe_load(yaml_block)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: Frontmatter must be a YAML mapping")
        return data, body
    except Exception as e:
        raise ValueError(f"{path}: Invalid YAML in frontmatter: {e}") from e


def lint_agents_root(repo_root: Path) -> int:
    """Validate AGENTS.md at repository root."""
    agents_file = repo_root / "AGENTS.md"
    if not agents_file.is_file():
        print(f"ERROR: {agents_file} is missing", file=sys.stderr)
        return 1

    size = agents_file.stat().st_size
    if size > MAX_RULE_FILE_BYTES:
        print(
            f"ERROR: AGENTS.md size ({size} bytes) exceeds limit of {MAX_RULE_FILE_BYTES} bytes",
            file=sys.stderr,
        )
        return 1

    content = agents_file.read_text(encoding="utf-8")
    if not content.strip():
        print(f"ERROR: {agents_file} is empty", file=sys.stderr)
        return 1

    print(
        f"[OK] AGENTS.md verified ({size} bytes, ~{len(content) // APPROX_CHARS_PER_TOKEN} tokens)"
    )
    return 0


def lint_rules_dir(repo_root: Path) -> tuple[int, int]:
    """Validate all markdown rule files in .agents/rules/."""
    rules_dir = repo_root / ".agents" / "rules"
    if not rules_dir.is_dir():
        print(f"ERROR: {rules_dir} directory is missing", file=sys.stderr)
        return 1, 0

    rule_files = list(rules_dir.glob("*.md"))
    if not rule_files:
        print(f"ERROR: No rule files found in {rules_dir}", file=sys.stderr)
        return 1, 0

    errors = 0
    always_on_chars = 0

    for path in sorted(rule_files):
        size = path.stat().st_size
        if size > MAX_RULE_FILE_BYTES:
            print(
                f"ERROR: {path.name} exceeds {MAX_RULE_FILE_BYTES} bytes ({size} bytes)",
                file=sys.stderr,
            )
            errors += 1
            continue

        try:
            content = path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content, path)

            trigger = frontmatter.get("trigger")
            if trigger not in VALID_TRIGGERS:
                print(
                    f"ERROR: {path.name}: Invalid trigger '{trigger}'. Must be one of {VALID_TRIGGERS}",
                    file=sys.stderr,
                )
                errors += 1
                continue

            description = frontmatter.get("description")
            if not description or not isinstance(description, str) or not description.strip():
                print(
                    f"ERROR: {path.name}: Missing or empty 'description' in frontmatter",
                    file=sys.stderr,
                )
                errors += 1
                continue

            if trigger == "glob":
                globs = frontmatter.get("globs")
                if not globs:
                    print(
                        f"ERROR: {path.name}: 'glob' trigger requires 'globs' field",
                        file=sys.stderr,
                    )
                    errors += 1
                    continue

            if trigger == "always_on":
                always_on_chars += len(content)

            print(f"[OK] Rule: {path.name:<25} | Trigger: {trigger:<15} | Size: {size:>5} bytes")

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            errors += 1

    always_on_tokens = always_on_chars // APPROX_CHARS_PER_TOKEN
    print(
        f"\n--- Always-on Rules Budget: ~{always_on_tokens}/{MAX_ALWAYS_ON_TOKENS} tokens ({always_on_chars}/{MAX_ALWAYS_ON_CHARS} chars) ---"
    )
    if always_on_chars > MAX_ALWAYS_ON_CHARS:
        print(
            f"ERROR: Always-on rules exceed budget of {MAX_ALWAYS_ON_TOKENS} tokens!",
            file=sys.stderr,
        )
        errors += 1

    return errors, always_on_tokens


def lint_skills_dir(repo_root: Path) -> int:
    """Validate all skill SKILL.md files in .agents/skills/."""
    skills_dir = repo_root / ".agents" / "skills"
    if not skills_dir.is_dir():
        print("[NOTE] No .agents/skills directory found; skipping skills lint.")
        return 0

    skill_files = list(skills_dir.glob("**/SKILL.md"))
    errors = 0

    for path in sorted(skill_files):
        try:
            content = path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content, path)

            name = frontmatter.get("name")
            if not name or not isinstance(name, str):
                print(
                    f"ERROR: {path}: Missing or invalid 'name' in skill frontmatter",
                    file=sys.stderr,
                )
                errors += 1
                continue

            description = frontmatter.get("description")
            if not description or not isinstance(description, str):
                print(
                    f"ERROR: {path}: Missing or invalid 'description' in skill frontmatter",
                    file=sys.stderr,
                )
                errors += 1
                continue

            print(f"[OK] Skill: {name:<20} | Path: {path.relative_to(repo_root)}")
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            errors += 1

    return errors


def main() -> int:
    """Run all agent configuration linter checks."""
    repo_root = Path(__file__).resolve().parent.parent
    print("=== Antigravity Agent Configuration & Rules Linter ===")
    print(f"Target repository: {repo_root}\n")

    errs = 0
    errs += lint_agents_root(repo_root)
    rule_errs, _ = lint_rules_dir(repo_root)
    errs += rule_errs
    errs += lint_skills_dir(repo_root)

    if errs == 0:
        print(
            "\n[SUCCESS] All Antigravity agent configurations, rules, and skills passed validation cleanly."
        )
        return 0
    else:
        print(f"\n[FAILURE] Found {errs} rule configuration violation(s).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
