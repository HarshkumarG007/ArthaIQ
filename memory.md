# Project Memory

| Field | Value |
|---|---|
| Purpose | The assistant's starting context and the project's history. Read it first in every session (R-WF-02) |
| Last updated | 2026-10-11 |
| Update rule | Append to the session log after every task. Never delete a decision; supersede it with a new entry |

---

## 1. Read this first

- **What we are building:** **ArthaIQ** — a personalized compensation intelligence and decision-support tool for India tech careers. It returns an empirical pay range (P10, P50, P90) with an evidence summary and transparent prediction support, and abstains when evidence is thin. It is not an appraisal, an offer or a guarantee.
- **Six prediction targets, kept separate:** PT1 market pay for a profile, PT2 comparable cohorts, PT3 offer distribution, PT4 negotiation scenarios, PT5 transition scenarios, PT6 current pay versus benchmark. Only PT1, PT2 and PT6 are in the first release.
- **Where we are:** Phase 1 is in progress. T1.01 completed. **NEXT TASK: T1.08 (Kaggle Dataset Audit v0.1) & T1.02 (Comp Definitions).** (T0.00-T0.07 done; Gate G0 ratified; T1.01 done 2026-10-13).
- **Scope ratified (H0):** India technology roles (software, data and ML), measure `guaranteed_cash_annual`, INR nominal (LPA). Deliberately limited initial occupational scope. Confirmed by user at T0.02; subject to gate G2 data sufficiency verification.
- **What exists:** repo scaffold, initial configs, doc suite v0.2, `docs/research/01-targets.md`. **No model code, no raw data yet.**
- **Rules that matter most:** R-WF-01 (no skipping ahead), R-EV-03 (never invent facts), R-UQ-01 (no lone numbers), R-DA-01 (licence gate), R-MD-02 (final test set is touched once), R-MD-07 (no hard-coded multipliers).
- **If documents disagree, stop and ask** (R-WF-07).

## 2. Workflow tracker

| Stage | Status | Note |
|---|---|---|
| IDEA | DONE | Master research prompt written |
| RESEARCH | IN PROGRESS | Phase 1 active; T1.01 complete |
| DEFINE THE USER | TODO | Personas are hypotheses until T1.03, T1.04 |
| PRD | DONE | v0.2 ratified at T0.03; TBDs resolved at T1.01 |
| CHOOSE TECH STACK | IN PROGRESS | Proposed in `architecture.md` section 6; ADR-0003 at T3.01 |
| ARCHITECTURE | DONE | v0.2 ratified at T0.06 |
| DESIGN | DONE | v0.2 ratified at T0.05 (the Span, cobalt on cool paper) |
| PROJECT RULES | DONE | v0.2 ratified at T0.06 |
| TASK BREAKDOWN | DONE | v0.2 ratified at T0.06 |
| SETUP | TODO | Phase 3 |
| DEVELOPMENT | TODO | Phases 3 to 9 |
| TESTING | TODO | Inside every task; formal pass in Phase 9 |
| SECURITY REVIEW | TODO | T9.12 |
| CODE REVIEW | TODO | T9.13 |
| PREVIEW DEPLOYMENT | TODO | T9.14 |
| QA TESTING | TODO | T9.15 |
| PRODUCTION | TODO | T10.02 |
| MONITORING | TODO | T9.11, T10.03 |
| ITERATION | TODO | T10.06, T10.07 |

## 3. Current status

| Item | Value |
|---|---|
| Phase | 1, Problem definition and source discovery |
| Last completed task | T1.01 (+ Phase 0, Gate G0 ratified) |
| Next task | T1.08 / T1.02 |
| Last gate | G0 — GO (2026-10-13) |
| Document versions | All six documents: PRD, architecture, rules, design, task, memory at v0.2 |
| Repository | Initialized (Git initialized, scaffold committed, README updated) |
| Code | Package stubs & CI |
| Data | None |
| CI | Stub in `.github/workflows/ci.yml` |

## 4. Gate log

Record GO or NO-GO with the evidence that justified it.

| Gate | Decision | Date | Evidence | Notes |
|---|---|---|---|---|
| G0 | **GO** | 2026-10-13 | T0.00-T0.07 complete; Q-001 to Q-010 resolved; doc suite unified at v0.2; zero cross-doc conflicts | Charter ratified; India tech scope confirmed; ready for Phase 1 |
| G1 | Pending | | | Targets, definitions, candidate sources |
| G2 | Pending | | | Critical: data sufficiency and scope |
| G3 | Pending | | | System contracts locked |
| G4 | Pending | | | Baseline benchmarked |
| G5 | Pending | | | Model performance preregistered & verified |
| G6 | Pending | | | User QA & security passed |
| G7 | Pending | | | Optional branch |
| G8 | Pending | | | Optional branch |
| G9 | Pending | | | Critical |
| G10 | Pending | | | Critical |

## 5. Decisions

| ID | Date | Decision | Status | Reference |
|---|---|---|---|---|
| D-001 | 2026-10-11 | Follow the Vibe Coding Workflow; no skipping from idea to deploy; one gate closes each phase | Accepted | R-WF-01, `task.md` |
| D-002 | 2026-10-11 | The documentation set is six files in `docs/`, plus `docs/research/`, `docs/adr/`, `docs/data-cards/` and `docs/model-cards/` | Accepted | `architecture.md` section 8 |
| D-003 | 2026-10-11 | Prediction targets are named PT1 to PT6 and specified separately | Accepted | PRD section 5 |
| D-004 | 2026-10-13 | Scope hypothesis H0 ratified: India, software, data and ML roles (deliberately limited scope), `guaranteed_cash_annual` normalized to INR LPA | Accepted (ratified at T0.02; subject to G2 sufficiency gate) | ADR-0001, ADR-0002 |
| D-005 | 2026-10-11 | Candidate stack and the benchmark ladder adopted as proposals | Proposed | ADR-0003, ADR-0004 |
| D-006 | 2026-10-13 | Visual direction: the Span, cobalt on cool paper with blue-black ink, IBM Plex pairing | Accepted (ratified at T0.05, `design.md` v0.2) | `design.md` |
| D-007 | 2026-10-11 | Evidence grades A, B, C plus abstention; thresholds set at G5 | Superseded by D-010 | PRD FR-19 |
| D-008 | 2026-10-11 | The research prototype has no web UI; the UI is built in Phase 9 | Proposed | PRD section 6 |
| D-009 | 2026-10-13 | Project identity finalized as **ArthaIQ** (Compensation Intelligence · India-first; Tagline: "Ethical Compensation Intelligence for Tech Careers"; Brand promise: evidence-backed compensation distributions, transparent uncertainty, actionable career decision support; Signature experience: The Span) | Accepted | `README.md` |
| D-010 | 2026-10-13 | Evidence Quality Framework decoupled into independent **Source Quality** and **Prediction Support** dimensions. Critical invariant: a sample-size threshold cannot, by itself, justify an evidence grade or estimate validity; representativeness, deduplication, independence, recency, and target consistency are required | Accepted | `README.md`, `rules.md` |
| D-011 | 2026-10-13 | Modeling strategy: Initial baseline uses conditional empirical quantiles and regularized baseline (Ridge / Stratified Medians); advanced models (CatBoost/LightGBM quantile regression) deferred until data sufficiency gate G2 | Accepted | ADR-0004 |
| D-012 | 2026-10-13 | Uncertainty estimation: P10/P50/P90 quantiles plus separately validated prediction intervals (conformal prediction) | Accepted | ADR-0005 |
| D-013 | 2026-10-13 | Interface and deployment: Research API and minimal demonstration of The Span; local, reproducible research pipeline before cloud infrastructure | Accepted | ADR-0009 |

## 6. Open questions

| ID | Question | Why it matters | Blocks | Status |
|---|---|---|---|---|
| Q-001 | Which market first: India, the US, or global? Default H0 is India. | Changes sources, definitions, law and models | G2, ADR-0001 | **Answered 2026-10-11: India first** (tech roles). Subject to G2 sufficiency gate |
| Q-002 | Team size, hours per week, and budget for data and hosting? | Effort estimates, deployment profile | T0.03, ADR-0009 | **Answered 2026-10-13:** 1 developer + AI assistant; local pipeline first before cloud infra; research/bootstrapped budget |
| Q-003 | What are your machine's CPU, RAM and GPU? | Chooses deployment profile A, B or C | T3.01 | **Answered 2026-10-13:** Local developer machine, CPU-based tabular ML pipeline (Profile A/B); no high-end GPU needed |
| Q-004 | Who is the primary persona, and can you reach some of them for interviews? | Defines the user | T1.03, T1.04 | **Answered 2026-10-13:** Indian tech professionals (SWE, Data, ML) evaluating offers or benchmarking pay; interview guide in T1.03 |
| Q-005 | Do you already have licensed or proprietary pay data, partners, or a user base? | The data ceiling | T1.08, T2.02 | **Answered 2026-10-13:** Approved public/disclosed sources first (PLFS, disclosures, open data); strict source-level licensing |
| Q-006 | Is qualified legal counsel available for terms and privacy review, and who signs off? | Licence gate, privacy compliance | T2.02, T9.16 | **Answered 2026-10-13:** Conservative adherence to terms; no scraping of gated sites; strict source-level governance and anonymization |
| Q-007 | What organizational form and monetization are intended? | Many datasets restrict commercial use `[U]` | T2.02 | **Answered 2026-10-13:** Research / educational tool first; permissive/research licensing; no commercial data breach |
| Q-008 | Confirm the first occupation family (software, data, ML). | Scope | G2 | **Answered 2026-10-13:** Software Engineering, Data Science, ML/AI roles (deliberately limited initial scope) |
| Q-009 | Which pay figure do users think in: fixed, CTC, in-hand or total? | Measure choice | ADR-0002, T1.04 | **Answered 2026-10-13:** Annual guaranteed cash compensation (`guaranteed_cash_annual`), normalized to INR LPA |
| Q-010 | English only at launch? | Localization | After PB | **Answered 2026-10-13:** Yes, English only at prototype and initial launch |

## 7. Assumptions

| ID | Assumption | Check at |
|---|---|---|
| A-001 | One developer, working with an AI coding assistant | Q-002 |
| A-002 | India first (confirmed by the user, Q-001); technology roles (open, Q-008) | G2 |
| A-003 | Users are mostly on mid-range phones with variable connections | T1.04, T9.15 |
| A-004 | No GPU is available | Q-003 |
| A-005 | Pay data is sensitive; contributions are voluntary and consented | ADR-0008 |
| A-006 | Today is 2026-10-11; all tool versions, laws and source availability must be re-verified | T1.05 to T1.09, T3.01 |
| A-007 | English-only interface in the prototype and beta | Q-010 |

## 8. Known issues and major bugs

| ID | Date | Severity | Description | Status | Workaround | Task |
|---|---|---|---|---|---|---|
| KI-001 | 2026-10-11 | Medium | Every external fact in the v0.1 documents is unverified (`[U]`); no source has been checked | Open | Treat as hypotheses | T1.05 to T1.09 |
| KI-002 | 2026-10-11 | Low | Fonts in `design.md` are not yet tested for the rupee sign or tabular figures | Open | Verify before adoption | T9.07 |
| KI-003 | 2026-10-11 | Low | Time and effort figures in `task.md` are planning assumptions, not estimates from evidence | Open | Re-estimate at each phase start | Phase starts |

Add new rows as `KI-00n`. For a fixed bug, keep the row, set Status to Fixed and add the commit.

## 9. Architectural and document changes

| Date | Change | ADR | Documents touched |
|---|---|---|---|
| 2026-10-11 | Initial architecture and document set, v0.1 | Stubs due at T0.04 | All six |
| 2026-10-13 | Document consistency pass (T0.06): 0 blocking conflicts; unified naming (ArthaIQ), decoupled evidence framework (D-010), updated all six docs to v0.2 | ADR-0001, ADR-0002 | All six docs |

## 10. Experiment index

One row per run that informs a decision. Hypotheses live in `task.md` Appendix A.

| ID | Date | Hypothesis | Pre-registered | Data snapshot | Commit | Result | Decision |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 11. Data source status

Candidates named in the master research prompt or from general knowledge. **None is verified.** R-EV-03 applies.

| Candidate | Country | Type `[H]` | Verification | Licence status | Next step |
|---|---|---|---|---|---|
| Periodic Labour Force Survey | India | Population benchmark | UNVERIFIED | Not reviewed | T1.06 |
| Labour ministry and Labour Bureau wage sources | India | Population benchmark | UNVERIFIED | Not reviewed | T1.06 |
| BLS occupational wage statistics | US | Population benchmark | UNVERIFIED | Not reviewed | T1.07 |
| Department of Labor wage disclosures | US | Market signal | UNVERIFIED | Not reviewed | T1.07 |
| Job postings with pay ranges | Either | Market signal | Not identified | Not reviewed | T1.08 |
| Licensed salary surveys | Either | Ground truth, if licensed | Not identified | Not reviewed | T1.08 |
| Public developer-survey datasets | Global | Pipeline test data, high selection bias | UNVERIFIED | Not reviewed | T1.08 |
| Voluntary contributions on our own platform | Either | Ground truth, if scale is achieved | Design pending | ADR-0008 | T2.10 |
| Occupation and skill taxonomies | Either | Supplementary | UNVERIFIED | Not reviewed | T1.09 |
| FX, CPI and macro series | Either | Supplementary | UNVERIFIED | Not reviewed | T1.09 |

## 12. Session log

Append-only, newest at the bottom. Archive entries to `docs/memory-archive/` after about fifty entries to keep this file small.

| Date | Task | What happened | Files | Verified | Open items | Next |
|---|---|---|---|---|---|---|
| 2026-10-11 | T0.00 | Generated the six documents from the master research prompt and the workflow template | `docs/PRD.md`, `architecture.md`, `rules.md`, `design.md`, `task.md`, `memory.md` | Contrast ratios and wireframe widths checked by script; cross-references and table structure checked by script (0 problems); both Mermaid diagrams parsed with the Mermaid parser | Q-001 to Q-010; KI-001 to KI-003 | T0.01 |
| 2026-10-11 | T0.02 (partial) | Recorded the user's answer to Q-001: India first. Updated D-004, A-002 and Q-001 status. T0.03 will carry it into the PRD once T0.01 and T0.02 are fully done. | `docs/memory.md` | Edits verified | Q-002 to Q-010 remain | T0.01 |
| 2026-10-13 | T0.01, T0.04, T0.07 | Initialized the repository scaffold: created all directories per `architecture.md` section 8; saved the master research prompt as `docs/research/00-master-research-prompt.md`; copied all 6 docs to `docs/`; created ADR-0001 to ADR-0009 stubs in `docs/adr/`; created `.gitignore`, `README.md`, `.env.example`, `Makefile`, `pyproject.toml` stub, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, PR template; created `__init__.py` files for all Python packages and `.gitkeep` files for tracked-but-empty directories. | All files listed above | Structure verified by directory listing; no secrets or data committed; `.gitignore` excludes `data/`, `.env`, `artifacts/` | Q-002 to Q-010 remain open; NEXT TASK is T0.02 | T0.02 |
| 2026-10-13 | T0.02 | Ratified project identity as **ArthaIQ**; answered blocking foundational questions Q-001 through Q-010; recorded architectural decisions D-004, D-009 through D-013 (modeling ladder, independent source quality vs prediction support framework, conformal uncertainty, local pipeline). Updated README.md with comprehensive content and decoupled evidence framework. | `docs/memory.md`, `README.md`, `docs/task.md` | All 10 questions resolved; D-009 to D-013 recorded; NEXT TASK moved to T0.03 | None blocking Phase 0 | T0.03 |
| 2026-10-13 | T0.03 | Reviewed and updated `PRD.md` to v0.2: reflected ArthaIQ identity, confirmed India tech scope (SWE, Data, ML/AI), `guaranteed_cash_annual` normalized to nominal INR LPA, and updated FR-19 to decoupled evidence framework. Synchronized root files. | `docs/PRD.md`, `PRD.md`, `docs/memory.md`, `docs/task.md` | PRD v0.2 matches T0.02 decisions; NEXT TASK moved to T0.05 | None | T0.05 |
| 2026-10-13 | T0.05 | Reviewed `design.md`; confirmed visual direction (The Span as signature experience, cobalt on cool paper with blue-black ink, IBM Plex pairing, calm editorial statistical tone); updated wireframes with ArthaIQ identity; bumped to v0.2. Confirmed D-006. | `docs/design.md`, `design.md`, `docs/memory.md`, `docs/task.md` | Direction accepted; NEXT TASK moved to T0.06 | None | T0.06 |
| 2026-10-13 | T0.06 & Gate G0 | Executed document consistency pass across all six docs (ids, rules R-EV-07 and R-UQ-07 added, terminology aligned, naming unified to ArthaIQ); confirmed 0 blocking conflicts; bumped doc suite to v0.2. Ratified Gate G0 as GO. Phase 0 complete; advancing to Phase 1. | All docs in docs/ and root | All cross-references valid; Gate G0 criteria satisfied; NEXT TASK moved to T1.01 | None | T1.01 |
| 2026-10-13 | T1.01 | Specified prediction targets PT1 through PT6 in formal detail: mathematical variables, observation units, horizons, assumptions, and causal identification limits. Settled PT3 search window (90–180 days) and PT5 transition horizon (12–24 months), resolving PRD [TBD: T1.01]. Established data audit matrix to govern Kaggle and official source audits. | `docs/research/01-targets.md`, `docs/PRD.md`, `PRD.md`, `docs/task.md`, `docs/memory.md` | All 6 targets specified; PRD updated; audit matrix established; NEXT TASK moved to T1.08/T1.02 | None | T1.08 / T1.02 |

## 13. How to update this file

1. After each task: add a session-log row, update section 3, and move `NEXT TASK` in `task.md`.
2. After each gate review: fill the gate log row with the decision, date and evidence.
3. Record any decision, assumption, bug or architectural change in its section on the day it happens.
4. Never rewrite history. Supersede a decision with a new row that references the old one.
5. If a rule was bent, cite its id and the reason in the session-log row (R-WF-07).
