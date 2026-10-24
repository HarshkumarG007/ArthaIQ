---
trigger: always_on
description: Core task execution lifecycle, planning protocol, Git standards, and assistant behavior rules
---

# Workflow Rules (R-WF, R-GI, R-AI)

Consult canonical specification in `docs/rules/00-workflow.md`.

## Key Invariants
1. **R-WF-01:** Never skip ahead. Gates close phases in order. No coding without prerequisites met.
2. **R-WF-02:** Read `docs/STATE.md` first for current operational state.
3. **R-WF-04:** Plan first. Write Implementation Plan artifact and wait for approval on M/L tasks or any task touching data, security, privacy, licences, migrations, dependencies or gates.
4. **R-WF-05:** Task done only when Definition of Done is met and shown with real command outputs.
5. **R-WF-07:** The documentation is single source of truth. Any conflict requires human resolution.
6. **R-GI-01:** Conventional commits (`feat`, `fix`, `docs`, `test`, `chore`).
7. **R-GI-05:** No self-merging pull requests.
8. **R-AI-01:** Zero fabrication of data, URLs, benchmarks, or salaries.
9. **R-AI-05:** Never delete, weaken, or skip tests.
10. **R-AI-08:** Maintain 100% bit-for-bit parity across all 6 canonical mirror pairs.
