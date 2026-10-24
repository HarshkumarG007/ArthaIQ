# Workflow & Task Execution Rules (00-workflow)

| Field | Value |
|---|---|
| Topic | Development Workflow, AI Assistance Protocols, and Version Control |
| Governing Rule Families | `R-WF`, `R-GI`, `R-AI`, RFC 2119 Keywords |
| Audience | AI Assistant, Engineers, Reviewers |

---

## 1. Workflow Rules (R-WF)

| ID | Rule | Description |
|---|---|---|
| **R-WF-01** | **Sequential Phase Order** | Never skip directly from IDEA → AI → DEPLOY. Do not write code for a task until its prerequisites in `task.md` are ticked and the preceding gate is recorded GO in `memory.md`. |
| **R-WF-02** | **Session Start & Context Hygiene** | Read `docs/STATE.md` first for current operational state, active milestone, and last ratified decisions. Then read `NEXT TASK` in `task.md`, and open specific topic rule files in `docs/rules/` or sections of `memory.md`, `PRD.md`, `architecture.md`, or `design.md` on demand using `@` mentions. Do not read or touch unrelated modules. |
| **R-WF-03** | **Task Sizing & Granularity** | One task per session or pull request. If a task is sized L, propose a split (T#.##a, T#.##b) in `task.md` and wait for approval before starting. |
| **R-WF-04** | **Plan First Protocol** | Before coding, post an Implementation Plan artifact: files to create or change, tests to add, assumptions, risks. For M and L tasks, and any task touching data, privacy, security, migrations, dependencies or gates, wait for explicit approval. |
| **R-WF-05** | **Evidence-Based Done** | A task is done only when its Definition of Done is met and shown: commands run and their output summarized. Then, and only then, tick the task box. |
| **R-WF-06** | **Session Accounting** | After each task: tick `task.md`, append a session entry to `memory.md`, and update `docs/STATE.md` with current decisions, issues, and change logs. |
| **R-WF-07** | **Documentation as Single Truth** | The documentation suite is the source of truth. If code and docs conflict, stop and raise it. Changes to `PRD.md`, `architecture.md`, `rules.md` or `design.md` require a change-log line, a `memory.md` entry, and an ADR. |
| **R-WF-08** | **Gate Governance** | Gates close phases in order. Tasks marked "parallel-safe" are the only exception to gate order. Never start a phase before the preceding gate is ratified GO. |
| **R-WF-09** | **Scope Discipline** | Build only what the PRD lists. New ideas go to the Parking Lot in `task.md`, not into code. |
| **R-WF-10** | **Pair Programming Protocol** | Treat the user as a senior technical pair programmer. Push back on violations of project invariants. |

---

## 2. Git & Commit Rules (R-GI)

| ID | Rule | Description |
|---|---|---|
| **R-GI-01** | **Conventional Commits** | All commit messages follow Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `test(scope): ...`, `chore(scope): ...`. |
| **R-GI-02** | **Atomic Commits** | One logical change per commit. Do not bundle unrelated refactors, formatting, or feature code together. |
| **R-GI-03** | **No Committing Untracked Binaries** | Never commit data files (`data/raw/`, `data/canonical/`), credentials, or temporary artifacts to Git. |
| **R-GI-04** | **Clean Working Trees** | Never leave uncommitted scratch files or dirty working trees at task handoff. |
| **R-GI-05** | **No Self-Merging** | AI assistants never merge their own pull requests or bypass branch protection rules. |

---

## 3. Assistant-Specific Rules (R-AI)

| ID | Rule | Description |
|---|---|---|
| **R-AI-01** | **Zero Fabrication** | Never fabricate URLs, citations, benchmarks, sample sizes, or salary statistics. If unknown, state `UNKNOWN`. |
| **R-AI-02** | **Explicit Assumptions** | Distinguish between `MEASURED`, `VERIFIED FACT`, `HYPOTHESIS`, and `ENGINEERING JUDGMENT`. |
| **R-AI-03** | **Preserve Comments** | Preserve all existing comments and docstrings unrelated to current code edits. |
| **R-AI-04** | **Clickable File Links** | All referenced files and code symbols must have valid clickable markdown links (`file:///...`). |
| **R-AI-05** | **No Test Deletion** | Never delete, comment out, or weaken a test to achieve a green test run. |
| **R-AI-06** | **Stop and Ask** | If requirements or constraints conflict, stop execution and clarify with the user. |
| **R-AI-07** | **Terminal Command Safety** | Run commands synchronously with sufficient wait times or monitor asynchronous jobs reactively. |
| **R-AI-08** | **Bit-for-Bit Mirroring** | Maintain 100% bit-for-bit parity across all canonical mirror pairs (`task.md`, `memory.md`, `PRD.md`, `architecture.md`, `design.md`, `rules.md` == `docs/*`). |
