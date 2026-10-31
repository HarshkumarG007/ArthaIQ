# ArthaIQ Project State Snapshot (STATE.md)

| Attribute | Current Value |
|---|---|
| **System** | **ArthaIQ** — Ethical Compensation & Career Intelligence for India Tech |
| **Release Status** | **v1.2.0 Production Staging Deployed** · All 25 Gates G0–G24 Ratified GO |
| **Active Milestone** | **Phase 24 Complete (Live Pilot Participant Cohort Onboarding & Field Run)** |
| **Active Subphase** | **Post-Phase 24 Platform Evolution & Operations** |
| **Current Task** | **T24.05 Convene Gate G24 Ratification Review Panel (Completed)** |
| **Next Task** | **Post-Phase 24 Platform Evolution & Operations** |
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
| **D-036** | 2026-10-31 | **Gate G20** | Ratified Live Pilot Cohort Onboarding & Telemetry Dashboard: statutory consent gateway (DPDP Sec 6 & 9), k-anonymized telemetry aggregator (k >= 5), real-time /pilot dashboard with decoupled panels (Two Streams Two Places), 10/10 M-STG metrics GO on N=150 cohort, 0 Axe violations across 183 web tests, single-click hard wipe (DPDP Sec 12, 0 bytes). |
| **D-037** | 2026-10-31 | **Gate G21** | Ratified Core Compensation Engine Backlog (ENG-17 & UX-18): Distributed Batch Inference Pipeline operational at 46,860.8 pred/sec (> 46x SLA), split conformal calibration [P10, P50, P90] with 80% coverage, memory-capped streaming generators (heap <= 256MB), and honest abstention; Interactive Slice-Adaptive Uncertainty Visualizer with dynamic coverage slider (70%-95%), cross-slice diagnostics across 6 Metros and 4 Seniority Strata, accessible table view toggle, 0 Axe violations across 191 web tests, clean production build; zero lone numbers (Rule R-UQ-01) and zero causal claims (Rule R-CR-01). |
| **D-038** | 2026-10-31 | **Gate G22** | Ratified MLAI Scenario Corpus Expansion: 4 new canonical MLAI practice scenarios authored (`SCEN-MLAI-04-VEC` to `SCEN-MLAI-07-GUARD`) completing 7 canonical MLAI scenarios and 21 platform total across DATA, SWE, and MLAI; practitioner consensus κ = 0.900 >= 0.850; 100-repeat determinism variance σ² = 0.000000; p95 latency 0.0182ms <= 5.0ms SLA; staging audit evaluated 21 scenarios across 300 attempts confirming 10/10 M-STG metrics PASS; web UI integrated with 0 Axe violations across 192 tests; clean production build; zero lone numbers and zero causal claims. |
| **D-039** | 2026-10-31 | **Gate G23** | Ratified Enterprise Batch REST Endpoint: high-throughput batch API operational (`POST /v1/estimates/batch`, 17,845.8 pred/sec, > 17x SLA), memory-safe streaming NDJSON response verified (`POST /v1/estimates/batch/stream`, 2,754.0 pred/sec, heap <= 128MB), p95 latency 10.17ms for N=50 batches (<= 100ms SLA), split conformal calibration [P10, P50, P90] with 80% coverage, honest structured abstention returning HTTP 200 without HTTP 500 exceptions, RFC 9457 Problem Details for 422 and 503, docs/api/openapi.json synchronized with 0 drift, zero lone numbers (Rule R-UQ-01), zero causal claims (Rule R-CR-01), and zero runtime LLMs (Rule R-CR-15). |
| **D-040** | 2026-10-31 | **Gate G24** | Ratified Live Pilot Participant Cohort Onboarding & Field Run: N=150 participants onboarded across DATA (50), SWE (50), and MLAI (50) in 6 Metro Hubs; all 10 M-STG staging metrics pass (100% comprehension, 100% completion, 0.000000 variance, 0.0206ms p95 latency, 8.59KB footprint, 0 residual purge bytes, 0 causal violations, 0 credential violations, Two Streams 100% decoupled, 100% cross-family DAG monotonicity); 21 canonical flaw-finding practice scenarios operational; DPDP Act 2023 Section 12 right to erasure verified with 0 residual bytes; 192 passing web tests with 0 Axe violations; clean production build; zero lone numbers (Rule R-UQ-01) and zero causal claims (Rule R-CR-01). |

### Preceding Ratified Milestone Decisions (Reference Index)
- **Gate G15D** (`D-029`): Ratified Career Progress Ledger & Local Storage Schema.
- **Gate G15E** (`D-030`): Ratified Deterministic Scenario Rubric Scorer & Practice Sandbox.
- **Gate G15F** (`D-031`): Ratified Career Architect UI & Navigation Integration.
- **Gate G16** (`D-032`): Ratified SWE Family Taxonomy & Competency Graph Inception.
- **Gate G17** (`D-033`): Ratified Multi-Family Pilot Deployment & Production Staging.
- **Gate G18** (`D-034`): Ratified SWE Practice Scenario Corpus Expansion.
- **Gate G19** (`D-035`): Ratified Machine Learning & AI (MLAI) Role Family Inception.

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
