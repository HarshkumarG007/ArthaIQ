# ArthaIQ Project State Snapshot (STATE.md)

| Attribute | Current Value |
|---|---|
| **System** | **ArthaIQ** — Ethical Compensation & Career Intelligence for India Tech |
| **Release Status** | **v1.2.0 Production Staging Deployed** · All 20 Gates G0–G19 Ratified GO |
| **Active Milestone** | **Phase 19 Complete (Gates G0–G19 Ratified GO)** |
| **Active Subphase** | **Machine Learning & AI (MLAI) Role Family Inception Ratified** |
| **Current Task** | **T20.03 Live Pilot Cohort Telemetry & Quality Health Dashboard (Completed)** |
| **Next Task** | **Phase 20: T20.04 Run Cohort Verification Audit & Convene Gate G20 Ratification Panel** |
| **Last Updated** | **2026-10-31** |
| **Primary Reference** | `docs/research/career-architect-implementation-plan.md` |

---

## 1. Quick Context for Fresh Sessions

> **Protocol (Rule R-WF-02):** Read `docs/STATE.md` first. Only open specific sections of `task.md`, `memory.md`, or `rules.md` on demand using `@` mentions.

ArthaIQ is a statistically rigorous compensation and career decision-support platform for India technology professionals (Software Engineering, Data Science, and ML/AI in Metro Hubs). It delivers empirical quantile distributions ($P_{10}, P_{50}, P_{90}$) with finite-sample split conformal prediction intervals, auditable SQSF 10-dimension evidence scores, and explicit decoupled abstention when data density is thin. It is not an appraisal, offer, or legal commitment.

**Core Invariant:** The production champion (**Rung F Level 2 Conformal CatBoost v0.1.0** in `artifacts/champion_v0/`) remains strictly preserved and isolated from experimental extensions.

---

## 2. Hardware Profile (Legion Pro 5i Gen 9)

Audited and benchmarked under Task `T15.00` (`docs/pilot/hardware-baseline.md`):

| Component | Hardware Specification | Operational Constraints |
|:---|:---|:---|
| **Processor** | Intel Core i7-14650HX (16C/24T, 8P+8E, 30MB Cache) | Maximize test parallelism (`pytest-xdist -n 6`); parallel joblib bootstrap. |
| **GPU** | NVIDIA GeForce RTX 4060 Laptop (8GB GDDR6, 125W TGP, CUDA 13.3) | Offline fp16 embeddings & draft scenario audits; strictly zero serving path LLM. |
| **Memory** | 16 GB DDR5-5600 (Single channel; Channel B free for 32GB upgrade) | **Binding constraint:** Cap WSL2 at 8 GB (`.wslconfig`). Max 2 concurrent agent worktrees. |
| **Storage** | 1 TB NVMe SSD (148.4 GB free, 15.6%) | Keep working tree on SSD; maintain >= 20% free space. |
| **Power Plan**| Windows Balanced (Fn+Q switches to Performance) | Use Performance mode when plugged in for training and test suites. |

---

## 3. Last Five Ratified Decisions

| ID | Date | Gate | Summary & Operational Impact |
|:---|:---|:---|:---|
| **D-031** | 2026-10-30 | **Gate G15F** | Ratified integrated Career Architect: end-to-end user journey across 4 sub-views, topological roadmap pacing slider, dynamic next-step action card, decoupled market pay overlay & honest abstention, 0 axe violations, and zero causal claims. |
| **D-032** | 2026-10-30 | **Gate G16** | Ratified Software Engineering (SWE) Role Family Expansion: 15-node SWE DAG verified, practitioner consensus κ = 0.867, deterministic rubric scoring, 0 Axe violations, local-first IndexedDB verified, and zero causal claims. |
| **D-033** | 2026-10-30 | **Gate G17** | Ratified Multi-Family Pilot Deployment & Production Staging: operational runbook (N=150), Nginx CSP hardened for Web Worker, 200 synthetic journeys audited, 10/10 M-STG metrics GO, zero causal promises, 0 Axe violations, local-first IndexedDB verified. |
| **D-034** | 2026-10-31 | **Gate G18** | Ratified SWE Practice Scenario Corpus Expansion: 7 canonical SWE scenarios verified (14 total platform scenarios), practitioner consensus κ = 0.900, deterministic rubric scoring, sub-5ms latency, web UI integrated with 0 Axe violations, and 10/10 M-STG staging metrics pass. |
| **D-035** | 2026-10-31 | **Gate G19** | Ratified Machine Learning & AI (MLAI) Role Family Inception: 15-node MLAI DAG verified, practitioner consensus κ = 0.867, deterministic rubric scoring, sub-5ms latency, web UI integrated with 0 Axe violations across 163 tests, and 10/10 M-STG staging metrics pass with 17 scenarios. |

---

## 4. Active Rules & Invariants for Career Architect (R-CR)

1. **R-CR-01 (No Causal Pay Claims):** Never claim learning a skill or earning a credential increases compensation.
2. **R-CR-02 (Two Streams, Two Places):** Pay evidence and competency requirements are separate objects and panels. Zero composite scores.
3. **R-CR-03 (State Beats Score):** Ledger states (`Unproven`, `Self-reported`, `Demonstrated`), counts, and dates replace readiness percentages.
4. **R-CR-08 (Deterministic Scoring):** Practice scenarios are scored deterministically via rubrics; model feedback is purely advisory and flag-guarded.
5. **R-CR-12 (Local-First Data):** User profiles and ledgers persist in IndexedDB on-device; zero server-side profiles in MVP.
6. **R-CR-14 (Independent Utility):** Career features remain 100% useful when the compensation engine abstains or when offline.
7. **R-CR-15 (LLM Boundary - ADR-0010):** Zero runtime LLM on serving path. Offline authoring assistance only.

---

## 5. Verification Commands

```bash
# Fast Developer Loop (run after changes)
uv run ruff check src/ tests/ scripts/
uv run mypy src/compintel
uv run lint-imports

# Web App Tests (run after frontend changes)
npm test --prefix apps/web -- --run

# Comprehensive Suite (run before handoff)
uv run pytest tests/unit/ tests/contract/ tests/property/
```
