# CompIntel

> **Working name.** Rename freely; update `pyproject.toml` and the package name accordingly.

A personalized compensation intelligence and decision-support tool. For a given role, level and location it estimates a plausible range of pay from evidence of known quality, shows how reliable the estimate is, and says plainly when the evidence is too thin to estimate at all.

---

## Status

| Item | Status |
|---|---|
| Phase | 0 — Foundation |
| Next task | T0.02 |
| Documents | v0.1 (in `docs/`) |
| Code | None yet |
| Data | None yet |

See [`docs/memory.md`](docs/memory.md) for the full status, and [`docs/task.md`](docs/task.md) for the task breakdown.

---

## What this is

- **Decision support** for people evaluating offers or benchmarking their own pay.
- **A range** (P10, P50, P90) with a stated definition, evidence summary and limitations.
- **Evidence-weighted**, and willing to abstain when evidence is thin.
- **Not** an appraisal, an offer, a guarantee, or legal or tax advice.

---

## Repository layout

```
compintel/
├── docs/                   # PRD, architecture, rules, design, task, memory, ADRs, research
├── config/                 # Source YAML, taxonomy files, thresholds.yaml
├── data/                   # gitignored; versioned by manifest or DVC
├── experiments/            # Preregistrations, configs, results
├── artifacts/              # Model bundles (gitignored)
├── notebooks/              # Exploration only; outputs stripped
├── src/compintel/          # Python source packages
├── apps/web/               # Frontend (Phase 9)
├── tests/                  # unit / property / contract / leakage / integration / e2e / fixtures
├── infra/                  # Docker, CI, deploy
├── scripts/
└── pyproject.toml  Makefile  .pre-commit-config.yaml  .env.example
```

See [`docs/architecture.md`](docs/architecture.md) section 8 for the full layout and dependency rules.

---

## Getting started

> Setup is Phase 3 (T3.01 onwards). These instructions will be filled in once the stack is pinned (ADR-0003).

```bash
# Clone
git clone <repo-url>
cd compintel

# Copy the env example and fill in values
cp .env.example .env

# Install (once stack is pinned at T3.01)
# uv sync          # or: pip install -e ".[dev]"

# Run the full checks (once CI is set up at T3.02)
# make check
```

---

## Documents

| File | Purpose |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Product requirements |
| [`docs/architecture.md`](docs/architecture.md) | System architecture |
| [`docs/design.md`](docs/design.md) | UI and design system |
| [`docs/rules.md`](docs/rules.md) | Development rules and AI guidelines |
| [`docs/task.md`](docs/task.md) | Task breakdown and phase plan |
| [`docs/memory.md`](docs/memory.md) | Project memory and session log |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`docs/research/`](docs/research/) | Research deliverables |

---

## Core principles (from `docs/rules.md`)

1. **Never skip directly from IDEA → AI → DEPLOY.** Follow the phase plan.
2. **Evidence before algorithms.** Data work precedes modelling.
3. **Ranges, never a lone point estimate.**
4. **Abstain rather than guess.**
5. **The simplest model that meets pre-registered thresholds.**

---

## Licence

> [TBD: T0.02, Q-007] Licence to be decided based on organizational form and monetization intent. No code is published until this decision is recorded.
