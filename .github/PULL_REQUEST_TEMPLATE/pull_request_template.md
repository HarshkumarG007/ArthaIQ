## Description

<!-- One sentence: what does this PR do, and why? -->

Closes # <!-- issue number if applicable -->

## Task

<!-- Which task(s) from task.md does this close? e.g. T3.04 -->

Task: T#.##

## Type of change

- [ ] Research / documentation
- [ ] Data pipeline
- [ ] Model or experiment
- [ ] API
- [ ] Frontend / UI
- [ ] Infrastructure / CI
- [ ] Bug fix
- [ ] Refactor (no behaviour change)

---

## Definition of Done (`rules.md` section 14)

**All PRs:**

- [ ] Acceptance criterion in `task.md` met and demonstrated (commands run, output summarized in the PR description)
- [ ] CI is green (lint, types, tests)
- [ ] No new warnings introduced
- [ ] `docs/memory.md` updated (session log row, decisions, issues as needed)
- [ ] `docs/task.md` updated (box ticked, `NEXT TASK` moved)
- [ ] No secrets, data files or personal information committed

**Data tasks (if applicable):**

- [ ] Licence entry is `approved` in `config/sources/<source_id>.yaml`
- [ ] Data-contract tests pass
- [ ] Lineage recorded (source ids, commit, config hash, schema version)
- [ ] Quarantine counts reported
- [ ] Data card updated or created

**Model / experiment tasks (if applicable):**

- [ ] Pre-registration exists in `experiments/preregistration/` (before any final-test run)
- [ ] Run is seeded and reproducible by one command
- [ ] Metrics per `rules.md` R-MD-05, with CIs
- [ ] Leakage tests pass
- [ ] Result logged in `memory.md` experiment index

**API tasks (if applicable):**

- [ ] OpenAPI snapshot updated
- [ ] Contract tests added
- [ ] RFC 9457 error format verified
- [ ] Rate limiting and validation in place

**UI tasks (if applicable):**

- [ ] Design tokens only (no arbitrary colours, fonts, radii)
- [ ] All states implemented (abstention, low-evidence, loading, error, stale)
- [ ] Keyboard and accessibility checks pass
- [ ] Copy follows `design.md` section 10

**Research / docs tasks (if applicable):**

- [ ] Claims tagged per `rules.md` R-EV-02 (VERIFIED FACT / MEASURED / HYPOTHESIS / ENGINEERING JUDGMENT / UNVERIFIED)
- [ ] Sources and retrieval dates in the evidence register
- [ ] Open questions logged in `memory.md`

---

## Adversarial self-check (for model PRs and gate closures)

Answer in writing below if this PR promotes a model or closes a gate:

1. Which target is this (market pay / accepted pay / offer)? Are they separated?
2. Could the improvement come from leakage, duplicates or selection bias?
3. Is a simpler model equally good?
4. Are intervals calibrated on recent, representative data?
5. Is every feature available at prediction time?

---

## Verification

<!-- Paste or link the relevant command output here. -->

```
$ make check
...
```

---

## Screenshots (UI only)

<!-- Light and dark; wide and compact (360px); loading, error and abstention states. -->
