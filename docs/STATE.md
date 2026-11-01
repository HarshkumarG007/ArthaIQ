# ArthaIQ Project State Snapshot (STATE.md)

| Attribute | Current Value |
|---|---|
| **System** | **ArthaIQ** — Ethical Compensation & Career Intelligence for India Tech |
| **Release Status** | **v1.2.0 Production Ready** · All 32 Gates G0–G31 Ratified GO · Cloud CI/CD Automated · Live Staging Deployment Ratified · Career Architect Graduated · Cross-Family Navigator Active · Client Security & WebCrypto Sync Active |
| **Active Milestone** | **Phase 31 Complete (Client Security & ADR-0014 WebCrypto Implementation)** |
| **Active Subphase** | **Production Launch & General Availability Complete (All 32 Phases Complete)** |
| **Current Task** | **Gate G31 Ratification Review (Ratified GO, Decision D-045)** |
| **Next Task** | **Production Launch & General Availability Complete (Phases 0–31 Complete; All Gates G0–G31 Ratified GO; Decisions D-001–D-045 Ratified)** |
| **Last Updated** | **2026-11-01** |
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
| **D-041** | 2026-11-01 | **Gate G27** | Ratified Career Architect Platform Graduation & Production Rollout Architecture: client-side zero-knowledge encrypted sync under ADR-0014 (WebCrypto AES-GCM-256, PBKDF2-SHA256, monotonic state lattice, DPDP Act 2023 Sec 12 hard wipe < 50ms), cross-family pathway synthesizer in src/compintel/career/pathways.py (topologically ordered acyclic pathways across SWE, DATA, and MLAI with bridge competencies, pruning, heuristic effort accumulation, and scenario links), and macroeconomic competency aggregation privacy specification under SPEC-MACRO-COMP-01 (k >= 10 k-anonymity floor, Laplace differential privacy, and Two Streams Two Places decoupling across 5 Metros); zero lone numbers (Rule R-UQ-01) and zero causal claims (Rule R-CR-01). |
| **D-042** | 2026-11-01 | **Gate G28** | Ratified Live Staging Deployment & Container Smoke Test: Docker Desktop engine active, 3-tier staging topology (arthaiq-staging-db, arthaiq-staging-api, arthaiq-staging-web) running and healthy under strict memory bounds (Postgres <= 256MB, API <= 512MB, Web <= 128MB); live Nginx ingress HTTP probes on http://localhost:8080 all returning HTTP 200 (/, /livez, /readyz, /v1/estimates, /v1/estimates/batch, /stream, /metrics); OWASP security headers (nosniff, DENY) and CSP with worker-src 'self' blob: verified; end-to-end compintel_batch CLI verified against live container with full [P10, P50, P90] intervals and honest abstention; experiments/results/live_staging_deployment_v1.json serialized with 0 failures; docs/pilot/gate-g28-review.md ratified; Decision D-042 approved; 4/4 Gate G28 tests passing. |
| **D-043** | 2026-11-01 | **Gate G29** | Ratified Cloud CI/CD Pipeline & Registry Automation: multi-architecture QEMU & Docker Buildx pipeline active (.github/workflows/docker-publish.yml), GHCR automated image publishing configured for arthaiq-api and web with OCI metadata, Git SHA tags, and semver tags, Hadolint static Dockerfile linter and Aqua Security Trivy vulnerability scanner gates operational, CI web-dist artifact coordination verified with upload/download-artifact in ci.yml, docker compose staging config validated; experiments/results/cicd_pipeline_verification_v1.json serialized with 0 failures; docs/pilot/gate-g29-review.md ratified; Decision D-043 approved; 6/6 Gate G29 tests passing. |
| **D-044** | 2026-11-01 | **Gate G30** | Ratified Frontend Cross-Family Career Pathway Navigator: interactive React component CrossFamilyPathwayNavigator.tsx operational across 3 canonical corridors (SWE_TO_MLAI, DATA_TO_MLAI, SWE_TO_DATA), bridge competency badges with transversal acceleration rationale, weekly pacing slider [5-20 hrs/wk] calculating calibrated duration intervals [Wmin, Wmax] weeks without solitary numbers, flaw-finding practice scenario launcher linking to 21 platform scenarios, local evidence ledger filtering, decoupled compensation overlay [P10, P50, P90] with statutory CPA 2019 disclaimer, 20/20 web test files passing with 200/200 tests, 0 Axe Core violations, clean Vite production build, and 6/6 Python tests passing. |
| **D-045** | 2026-11-01 | **Gate G31** | Ratified Client Security & ADR-0014 WebCrypto Implementation: Client-side zero-knowledge encrypted backup and cross-device sync implemented with WebCrypto API (PBKDF2-SHA256, 100k rounds, 16-byte random salt, AES-GCM-256, 12-byte IV), monotonic state lattice conflict resolution preserving demonstrated absorbing state, profile and ledger state merge, DPDP Act 2023 Section 12 hard purge < 50ms, accessible EncryptedSyncModal component, 22/22 web test files passing with 218/218 tests, 0 Axe Core violations, clean Vite production bundle, and 7/7 Python tests passing. |

### Preceding Ratified Milestone Decisions (Reference Index)
- **Gate G15D** (`D-029`): Ratified Career Progress Ledger & Local Storage Schema.
- **Gate G15E** (`D-030`): Ratified Deterministic Scenario Rubric Scorer & Practice Sandbox.
- **Gate G15F** (`D-031`): Ratified Career Architect UI & Navigation Integration.
- **Gate G16** (`D-032`): Ratified SWE Family Taxonomy & Competency Graph Inception.
- **Gate G17** (`D-033`): Ratified Multi-Family Pilot Deployment & Production Staging.
- **Gate G18** (`D-034`): Ratified SWE Practice Scenario Corpus Expansion.
- **Gate G19** (`D-035`): Ratified Machine Learning & AI (MLAI) Role Family Inception.
- **Gate G20** (`D-036`): Ratified Live Pilot Cohort Onboarding & Telemetry Dashboard.
- **Gate G21** (`D-037`): Ratified Core Compensation Engine Backlog (ENG-17 & UX-18).
- **Gate G22** (`D-038`): Ratified MLAI Scenario Corpus Expansion.
- **Gate G23** (`D-039`): Ratified Enterprise Batch REST Endpoint.
- **Gate G24** (`D-040`): Ratified Live Pilot Participant Cohort Onboarding & Field Run.

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
