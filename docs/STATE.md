# ArthaIQ Project State Snapshot (STATE.md)

| Attribute | Current Value |
|---|---|
| **System** | **ArthaIQ** — Ethical Compensation & Career Intelligence for India Tech |
| **Release Status** | **v1.0.0 General Availability (GA) Released** · All 15 Gates G0–G14 Ratified GO |
| **Active Milestone** | **Phase 15: Career Architect & Local Acceleration** |
| **Active Subphase** | **Phase 15C: Deterministic Engine (Evidence Ledger, Gap Calculator, Roadmap, Pay Port & API)** |
| **Current Task** | **Gate G15B DATA Family Competency Graph Ratification (Completed)** |
| **Next Task** | **Phase 15C: T15.15 Domain Engine Skeleton & Ports** |
| **Last Updated** | **2026-10-24** |
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
| **D-023** | 2026-10-23 | **Gate G12** | Promoted EXP-14 active learning for sparse cells & EXP-15 counterfactual scenario modeling. |
| **D-024** | 2026-10-23 | **Gate G13** | Promoted EXP-PGM-01r Gaussian copula to PT4 UI; rejected ensembling; deferred GNNs & trajectories. |
| **D-025** | 2026-10-24 | **Gate G14** | Ratified SRC-B2B-01 enterprise intake, differential privacy pooling ($k_{\min} \ge 5$), CCI safe harbors, and authorized v1.0.0 GA release. |
| **D-026** | 2026-10-24 | **Gate G15A** | Ratified Career Architect foundations, Legion Pro 5i baseline, AGENTS.md, .agents/rules/, PRD v1.2, ADRs 0010–0013, CHARTER-CAREER-ARCH-01, and pytest-xdist acceleration. |
| **D-027** | 2026-10-24 | **Gate G15B** | Ratified DATA family competency DAG (14 nodes, 0 cycles, 100% provenance), CI validators, practitioner consensus (κ = 0.857), and difficulty heuristic rubrics. |

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
