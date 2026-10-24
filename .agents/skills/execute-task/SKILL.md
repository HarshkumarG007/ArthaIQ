---
name: execute-task
description: Run one numbered task from task.md with plan-first approval, verification, and structured handoff report
---

# Execute Task Procedure

Follow this systematic procedure for executing any numbered task from `task.md`:

1. **Context Loading:** Read `docs/STATE.md` first. Then read only the specific task entry in `task.md` and the sections it explicitly cites.
2. **Ambiguity Resolution:** If any requirement, rule, or contract is ambiguous, stop and interview the user (`/grill-me`).
3. **Plan First:** Author the Implementation Plan artifact detailing:
   - Target files to create or modify
   - Test suites to add or update
   - Risks and potential edge cases
   - Assumptions requiring verification
   - Wait for explicit user approval for M/L tasks, or tasks touching data, security, privacy, licences, migrations, dependencies or gates.
4. **Implementation in Worktree:** Implement changes adhering strictly to layer boundaries and project invariants.
5. **Incremental Verification:** Run `uv run ruff check` and `uv run mypy` after each change set.
6. **Pre-Handoff Verification:** Run full test suite (`uv run pytest`), frontend checks (`npm test --prefix apps/web -- --run`), and rules lint (`uv run python scripts/lint_agent_rules.py`).
7. **Synchronize Mirrors:** Tick the task box in `task.md`, copy to `docs/task.md`, append to `memory.md`, copy to `docs/memory.md`, and update `docs/STATE.md`. Verify 100% bit-for-bit parity across all 6 canonical mirror pairs.
8. **Handoff Report:** Report using the structured format defined in `AGENTS.md`.
