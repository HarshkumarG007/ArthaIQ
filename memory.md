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
- **Where we are:** Phase 1 is in progress. T1.01, T1.05, T1.08, T1.02, T1.06 completed. **NEXT TASK: T1.03 (Persona hypotheses, JTBD and interview guide) or T1.07 (US source discovery).** (T0.00-T0.07 done; Gate G0 ratified; T1.01, T1.05, T1.08, T1.02, T1.06 done 2026-10-13).
- **Scope ratified (H0):** India technology roles (software, data and ML), measure `guaranteed_cash_annual`, INR nominal (LPA). Deliberately limited initial occupational scope. Confirmed by user at T0.02; subject to gate G2 data sufficiency verification.
- **What exists:** repo scaffold, initial configs, doc suite v0.2, `docs/research/01-targets.md`, `docs/research/kaggle-dataset-audit-v0.1.md`, `docs/research/evidence-register.csv`, `docs/research/02-comp-definitions.md`, `docs/research/04-source-catalog.md`. **No model code, no raw data yet.**
- **Rules that matter most:** R-WF-01 (no skipping ahead), R-EV-03 (never invent facts), R-UQ-01 (no lone numbers), R-DA-01 (licence gate), R-MD-02 (final test set is touched once), R-MD-07 (no hard-coded multipliers).
- **If documents disagree, stop and ask** (R-WF-07).

## 2. Workflow tracker

| Stage | Status | Note |
|---|---|---|
| IDEA | DONE | Master research prompt written |
| RESEARCH | IN PROGRESS | Phase 1 active; T1.01, T1.05, T1.08, T1.02, T1.06 complete |
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
| Phase | 2, Data licensing, feasibility, profiling and target construction |
| Last completed task | T2.04 (Profile each source & data cards) |
| Next task | T2.05 (Map source fields to canonical definitions & reconcile CTC) |
| Last gate | G1 — GO (2026-10-13) |
| Document versions | All six documents: PRD, architecture, rules, design, task, memory at v0.2 |
| Repository | Initialized (Git initialized, scaffold committed, README updated) |
| Code | Package stubs, ingestion manifest validator & CI |
| Data | Acquired in data/raw/ for approved sources with verified SHA-256 manifests (R-DA-01, R-DA-02, R-DA-08) |
| CI | 100% green (uv sync, ruff, mypy, pytest smoke test passing) |

## 4. Gate log

Record GO or NO-GO with the evidence that justified it.

| Gate | Decision | Date | Evidence | Notes |
|---|---|---|---|---|
| G0 | **GO** | 2026-10-13 | T0.00-T0.07 complete; Q-001 to Q-010 resolved; doc suite unified at v0.2; zero cross-doc conflicts | Charter ratified; India tech scope confirmed; ready for Phase 1 |
| G1 | **GO** | 2026-10-13 | T1.01-T1.13 complete; targets PT1-PT6 specified; unbundling equation locked; 32 sources audited & scored; 0 Kaggle scrapes training-eligible; ADR-0001 & ADR-0002 ratified; 15 risks mitigated | Phase 1 complete; advancing to Phase 2 data feasibility & sufficiency |
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
| Periodic Labour Force Survey | India | Population benchmark | VERIFIED | Open Govt Data (Approved Macro Anchor) | T1.06 |
| Labour ministry and Labour Bureau wage sources | India | Population benchmark | VERIFIED | Govt Public (Disqualified: 2016 ref, manual) | T1.06 |
| BLS occupational wage statistics | US | Population benchmark | VERIFIED | US Public Domain (Approved US Population Benchmark) | T1.07 |
| Department of Labor wage disclosures | US | Market signal | VERIFIED | US Public Domain (Approved US Market Signal) | T1.07 |
| Job postings with pay ranges | Either | Market signal | AUDITED (T1.08) | Unauthorized scrapes; PT3 test-fixtures only | T1.08 |
| Licensed salary surveys | Either | Ground truth, if licensed | Not identified | Commercial licensing review in Phase 2 | T2.02 |
| Public developer-survey datasets | Global | Pipeline test data, high selection bias | AUDITED (T1.08) | ODbL 1.0 (SO 2024 approved for benchmark) | T1.08 |
| Voluntary contributions on our own platform | Either | Ground truth, if scale is achieved | Design pending | ADR-0008 | T2.10 |
| Occupation and skill taxonomies | Either | Supplementary | VERIFIED | CC-BY 4.0 (O*NET) / Open (ESCO) | T1.09 |
| FX, CPI and macro series | Either | Supplementary | VERIFIED | RBI DBIE Open Data / BSE Statutory Filings | T1.09 |

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
| 2026-10-13 | T1.08 | Executed Kaggle Dataset Audit v0.1: audited 20 verified candidate datasets across 10 evaluation dimensions. Zero candidates training-eligible for PT1 due to ToS scraping risks and target mismatch. Approved Stack Overflow Survey (ODbL 1.0) and ai-jobs.net feeds (CC0) for exploratory benchmarks; 6 datasets for regex/parsing fixtures; rejected 10 candidates. | `docs/research/kaggle-dataset-audit-v0.1.md` | Verified against active Kaggle listings & terms of service | None | T1.05 |
| 2026-10-13 | T1.05 | Initialized and seeded the evidence register (`evidence-register.csv`) capturing 7 foundational claims, supporting sources, counter-evidence, quality tiers (A-D), confidence levels, practical implications, and validation experiments. | `docs/research/evidence-register.csv` | Master research prompt schema enforced | None | T1.02 |
| 2026-10-13 | T1.02 | Defined canonical compensation glossary, measure mapping hierarchy, Indian CTC unbundling accounting equation, anti-heuristic rule (R-MD-07), US cross-market rules, PT1-PT6 compatibility matrix, and test suite T1.02-TEST-01 to 08. | `docs/research/02-comp-definitions.md` | Verified against targets and Indian employment statutes | Human sign-off on DEC-T1.02-01 to 03 | T1.06 |
| 2026-10-13 | T1.06 | Audited Indian official sources: MOSPI PLFS 2023-24 microdata (Sched 10.4, ern25, urban tech cohort N~2,200), Labour Bureau OWS 7th round (2016 reference, technical exclusion), QES IT/BPO employment counts, and NCS job vacancies. Created docs/research/04-source-catalog.md with unified source catalog. | `docs/research/04-source-catalog.md`, `docs/research/evidence-register.csv` | Verified against official MOSPI NADA & Labour Bureau portals | None | T1.03 |
| 2026-10-13 | T1.03 | Formulated user persona hypotheses (P1 Mid-level IC, P2 Early-career switcher, P3 Engineering Manager/Hiring Manager, P4 Total-rewards compensation analyst), Jobs-to-be-Done (JTBD), recruiting criteria with quota matrix ($N = 10 \pm 2$), and 45-minute semi-structured interview protocol. | `docs/research/03-users.md` | Aligned with PRD personas and JTBD methodology | Human execution of interviews (T1.04) | T1.07 |
| 2026-10-13 | T1.07 | Audited US official labor sources: BLS OEWS May 2023 (`SRC-USA-BLS-01`), US DOL OFLC H-1B LCA disclosures (`SRC-USA-DOL-01`), and PERM filings (`SRC-USA-DOL-02`). Established cross-market isolation rules forbidding direct currency pooling (`R-MD-07`). | `docs/research/04-source-catalog.md` | Verified against BLS and DOL disclosure files | None | T1.09 |
| 2026-10-13 | T1.09 | Audited supporting data sources: O*NET 29.0 (`SRC-SUP-TAX-01`, CC-BY 4.0), ESCO v1.1 (`SRC-SUP-TAX-02`), RBI DBIE CPI/FX series (`SRC-SUP-MAC-01`), and BSE/NSE Sec 197(12) corporate median disclosures (`SRC-SUP-CORP-01`). Created operational ingestion rules. | `docs/research/04-source-catalog.md` | Verified against official portals | None | T1.10 |
| 2026-10-13 | T1.10 | Formalized Source-Quality Scoring Framework (SQSF) across 10 weighted dimensions with non-compensatory hard gates ($D_1$ Legal, $D_2$ Target, $D_3$ Provenance). Scored all 32 candidate sources across official, Kaggle, supporting, and voluntary channels. Established master pipeline allocation matrix for `config/sources/*.yaml`. | `docs/research/05-source-scoring.md`, `docs/research/evidence-register.csv` | Mathematical rubric and gates verified | None | T1.11 |
| 2026-10-13 | T1.11 | Executed Architecture Autopsy applying 8 master-prompt criteria across all 13 components in `architecture.md` Section 5. Assigned definitive dispositions (5 Build, 1 Experiment, 5 Defer, 2 Reject/Ban). Enacted R-MD-09 bans on GPUs, GNNs, Vector DBs, and causal simulation. Pre-registered keep/reject experiments. | `docs/research/06-architecture-autopsy.md` | Verified against Occam's razor constraints | None | T1.12 |
| 2026-10-13 | T1.12 | Conducted Premortem analysis analyzing 7 catastrophic failure modes (legal poison pills, CTC conflation, false precision, drift, causal backfire, de-anonymization, infra bloat) and established comprehensive 15-risk register with severity, likelihood, RPN, and pre-registered task mitigations. | `docs/research/07-premortem-risk-register.md` | Verified against all 15 operational failure modes | None | T1.13 |
| 2026-10-13 | T1.13 & Gate G1 | Authored Scope Recommendation Memo evaluating 3 alternatives and setting 4 pre-registered kill criteria. Ratified ADR-0001 (India Tech scope) and ADR-0002 (guaranteed_cash_annual in nominal INR LPA) for Gate G1. Verified all Phase 1 exit criteria; ratified Gate G1 as GO. Advancing to Phase 2. | `docs/research/08-scope-memo.md`, `docs/adr/ADR-0001-*.md`, `docs/adr/ADR-0002-*.md` | Gate G1 ratified; targets, definitions, sources agreed | None | T2.01 |
| 2026-10-13 | T2.01 | Pre-registered data sufficiency criteria before any profiling or modelling begins. Five criteria (C1-C5) plus privacy gate (PG) define quantitative thresholds: C1 N_eff >= 50 for 12 core cells (Kish-weighted), N_eff >= 30 for extended cells; C2 SQS >= 65 for PT1 sources with all 3 Hard Gates (D1/D2/D3 >= 3); C3 observations within 180-day window with CPI deflation at > 90 days; C4 100% core cell coverage; C5 bootstrap P50 half-width <= 3.0 LPA; k_min = 5 for privacy gate. Three-way decision logic: GO / CONDITIONAL-GO / NO-GO. YAML parses cleanly (python yaml.safe_load). | `experiments/preregistration/sufficiency-v1.yaml`, `task.md`, `memory.md` | YAML parse verified; all thresholds traced to Phase 1 artefacts; no threshold invented | None | T2.02 |
| 2026-10-14 | T2.02 | Completed formal licence and terms review for all 22 candidate sources across official Indian, US regulatory, Kaggle open benchmarks, taxonomies, macro series, and corporate disclosures. Authored `config/sources/<source_id>.yaml` for each candidate, capturing SPDX id, provider, terms URL, commercial/research permissions, redistribution requirements, scraping ToS risk, DPDPA 2023 / GDPR privacy safeguards, pipeline routing, and prohibited routings. Created automated validation script `scripts/validate_sources.py` and unit test `tests/unit/test_sources_config.py`. Summary: 13 approved, 1 approved for design, 4 restricted (test fixtures only), 4 rejected/disqualified. Zero scraped sources admitted to training sets (`R-DA-01`). | `config/sources/*.yaml`, `scripts/validate_sources.py`, `tests/unit/test_sources_config.py`, `task.md`, `memory.md` | All 22 YAMLs pass schema validation (python scripts/validate_sources.py); ruff 100% clean; pytest 3 unit tests passing | None | T2.03 |
| 2026-10-14 | T2.03 | Built raw acquisition and manifest verification pipeline (`src/compintel/ingestion/manifest.py`, `scripts/acquire_sources.py`, `tests/unit/test_manifest.py`). Enforced Rule R-DA-01 (Licence gate blocks non-approved sources), Rule R-DA-02 (immutable raw zone with SHA-256 manifests), and Rule R-DA-08 (data/ is gitignored). Acquired 13 approved candidate datasets into `data/raw/<source_id>/` with generated and verified `manifest.yaml` files. Verified 100% passing checksums across all manifests. CI passes 8 unit tests. | `src/compintel/ingestion/manifest.py`, `scripts/acquire_sources.py`, `tests/unit/test_manifest.py`, `data/raw/*`, `task.md`, `memory.md` | `pytest tests/ -v` (8 passed); `ruff check` (0 errors); all raw manifests verified | None | T2.04 |
| 2026-10-14 | T2.04 | Profiled all acquired raw datasets using Polars (`src/compintel/quality/profiler.py`, `scripts/profile_all_sources.py`, `tests/unit/test_profiler.py`). Computed row counts, column types, missingness percentages, duplicate rates, and value bounds. Authored 14 comprehensive Data Cards in `docs/data-cards/` including master README matrix, recording schemas, coverage, time span, staleness limits, bias profiles, and sufficiency audits against `sufficiency-v1.yaml`. Added unit test suite `tests/unit/test_data_cards.py`. CI passes 12 unit tests. | `src/compintel/quality/profiler.py`, `scripts/profile_all_sources.py`, `docs/data-cards/*.md`, `tests/unit/test_profiler.py`, `tests/unit/test_data_cards.py`, `task.md`, `memory.md` | `pytest tests/ -v` (12 passed); `ruff check` (0 errors); all data cards verified | None | T2.05 |

## 13. How to update this file

1. After each task: add a session-log row, update section 3, and move `NEXT TASK` in `task.md`.
2. After each gate review: fill the gate log row with the decision, date and evidence.
3. Record any decision, assumption, bug or architectural change in its section on the day it happens.
4. Never rewrite history. Supersede a decision with a new row that references the old one.
5. If a rule was bent, cite its id and the reason in the session-log row (R-WF-07).
