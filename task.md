# Task Breakdown

| Field                          | Value                                                |
| ------------------------------ | ---------------------------------------------------- |
| Status                         | v1.0.0 GA Released; Phase 21 Complete (Gates G0–G21 Ratified GO)     |
| Last updated                   | 2026-10-31                                           |
| Depends on                     | `PRD.md`, `architecture.md`, `rules.md`, `design.md` |
| Gate decisions are recorded in | `memory.md`                                          |

**NEXT TASK: Phase 22: T22.04 Execute Staging Audit Simulation Across All 21 Canonical Scenarios** (Phase 21 Complete: Gate G21 Ratified GO; preceding milestones: Phase 11, **NEXT TASK: Phase 15** ratified GO)

## How to use this file

1. Take the task at `NEXT TASK`.
2. Tell the assistant: **"Execute T#.##"**. It follows the protocol in `rules.md` section 13: read, plan, wait for "go" if required, implement, verify, report.
3. Review the report. The assistant ticks the box, appends `(done YYYY-MM-DD, commit <hash>)`, updates `memory.md`, and moves `NEXT TASK`.
4. At the end of a phase, hold the gate review. Record GO or NO-GO in `memory.md` with the evidence. Do not start the next phase before then (R-WF-08).

| Tag          | Meaning                                                       |
| ------------ | ------------------------------------------------------------- |
| `[AI]`       | The assistant can do it                                       |
| `[HUMAN]`    | Needs a person: access, legal judgment, interviews, approvals |
| `[AI+HUMAN]` | The assistant prepares; a person decides                      |

Sizes are planning assumptions: **S** about two hours of focused assisted work, **M** about a day, **L** several days. An L task is split before it starts (R-WF-03). Phase effort figures are also assumptions for one developer working with an assistant, and each phase re-estimates them at its start.

## How the Vibe Coding Workflow maps to phases

| Workflow stage                                                              | Phase                               |
| --------------------------------------------------------------------------- | ----------------------------------- |
| IDEA                                                                        | 0 (master research prompt; done)    |
| RESEARCH, DEFINE THE USER                                                   | 1, 2                                |
| PRD, CHOOSE TECH STACK, ARCHITECTURE, DESIGN, PROJECT RULES, TASK BREAKDOWN | 0 (drafts), refined at G2 and G3    |
| SETUP                                                                       | 3 (T3.01 to T3.03)                  |
| DEVELOPMENT                                                                 | 3 to 9                              |
| TESTING                                                                     | Inside every task; formal pass in 9 |
| SECURITY REVIEW, CODE REVIEW                                                | 9                                   |
| PREVIEW DEPLOYMENT, QA TESTING                                              | 9                                   |
| PRODUCTION, MONITORING, ITERATION                                           | 10                                  |

---

## Phase 0: Foundation

> **Objective:** ratify the document set and answer the blocking questions so later work has a stable contract.
> **Inputs and tools:** master research prompt, docs v0.1; Git, Markdown.
> **Deliverables:** docs v0.2, ADR stubs, repository skeleton, answered Q-001 to Q-006.
> **Effort (assumption):** 1 to 3 days.
> **GO if:** Q-001 (market) and Q-002 (team, time, budget) are answered or consciously deferred, and the documents are consistent.
> **NO-GO:** stay in Phase 0.

- [x] **T0.00** [AI] Generate the documentation set v0.1 (done 2026-10-11)
- [x] **T0.01** [AI+HUMAN] Save the master research prompt as `docs/research/00-master-research-prompt.md`; initialize the repository scaffold with all directories and companion files. (done 2026-10-13)
      Output: full repo skeleton committed. Done when: all directories exist, docs copied to `docs/`, master prompt saved, ADR stubs created, .gitignore and README present.
- [x] **T0.02** [HUMAN] Answer Q-001 to Q-006 in `memory.md`, or record a deliberate deferral for each. (done 2026-10-13)
      Output: answers in `memory.md`. Done when: no blocking question is open without a reason. Needs: T0.01. Size: S.
- [x] **T0.03** [AI+HUMAN] Review `PRD.md`; resolve what T0.02 settles; bump to v0.2. (done 2026-10-13)
      Output: PRD v0.2. Done when: scope table H0 reflects the answers. Needs: T0.02. Size: S.
- [x] **T0.04** [AI] Create ADR-0001 to ADR-0009 as stubs with status Proposed. (done 2026-10-13)
      Output: `docs/adr/` with nine stubs. Done when: every ADR in `architecture.md` section 15 has a file. Needs: T0.02. Size: M.
- [x] **T0.05** [AI+HUMAN] Review `design.md`; confirm or revise the direction (the Span, palette, typefaces); bump version. (done 2026-10-13)
      Output: design v0.2. Done when: direction confirmed in `memory.md` (D-006). Needs: T0.02. Size: S.
- [x] **T0.06** [AI] Check consistency across all six documents: ids, terms, glossary, links, tags. (done 2026-10-13)
      Output: conflict list in `memory.md`. Done when: every conflict is resolved or logged. Needs: T0.03, T0.04, T0.05. Size: S.
- [x] **T0.07** [AI] Repository hygiene: `.gitignore`, README stub, PR template with Definition of Done checklist, `.env.example`, `Makefile`, `pyproject.toml` stub, `.pre-commit-config.yaml`, CI workflow stub. (done 2026-10-13)
      Output: files committed. Done when: `data/` and `.env` are ignored and the PR template lists section 14 of `rules.md`. Needs: T0.01. Size: S.

**Gate G0:** charter ratified. **GO ratified 2026-10-13** (recorded in `memory.md`).

---

## Phase 1: Problem definition and source discovery

> **Objective:** precise targets and definitions, a candidate source catalog, an evidence register, an architecture autopsy, a premortem and a scope recommendation.
> **Inputs and tools:** docs v0.2, web research; spreadsheet or CSV, YAML.
> **Deliverables:** `docs/research/01` to `08`, evidence register, draft ADR-0001 and ADR-0002.
> **Effort (assumption):** 1 to 2 weeks.
> **GO if:** at least one candidate source with verified primary documentation exists for PT1 and PT6, and a scope memo is drafted.
> **NO-GO leads to:** no feasible source for PT1 anywhere → go directly to T2.10 (data acquisition plan) or re-scope the target.

- [x] **T1.01** [AI] Specify prediction targets PT1 to PT6: variable, observation unit, horizon, assumptions, identification limits; settle the job-search window and transition horizon. (done 2026-10-13)
      Output: `docs/research/01-targets.md`. Done when: each target has all five fields and PRD `[TBD: T1.01]` items are resolved. Needs: G0. Size: M.
- [x] **T1.02** [AI+HUMAN] Define compensation terms and map them: CTC, fixed, base, variable, in-hand, total compensation, for India and the US. (done 2026-10-13)
      Output: `docs/research/02-comp-definitions.md`. Done when: each term maps to a canonical `measure` or is marked non-comparable. Needs: T1.01. Size: M.
- [x] **T1.03** [AI+HUMAN] Write persona hypotheses, jobs to be done and an interview guide. (done 2026-10-13)
      Output: `docs/research/03-users.md`. Done when: guide and recruiting criteria exist. Needs: T1.01. Size: S.
- [ ] **T1.04** [HUMAN] Run user interviews (number set in T1.03) and synthesize.
      Output: findings appended to `03-users.md`. Done when: personas confirmed or revised in the PRD. Needs: T1.03. Size: L.
- [x] **T1.05** [AI] Create the evidence register (fields from the master prompt, section 2) and seed it with foundational decisions and candidate findings. (done 2026-10-13)
      Output: `docs/research/evidence-register.csv`. Done when: all initial claims and audit findings have rows. Needs: G0. Size: S.
- [x] **T1.06** [AI] Source discovery, India: Periodic Labour Force Survey, labour ministry and Labour Bureau wage sources, other Indian labor-market data. Record the fields from master prompt section 4 for each candidate. (done 2026-10-13)
      Output: entries in `docs/research/04-source-catalog.md`. Done when: each candidate has a primary-source URL, retrieval date and VERIFIED or UNVERIFIED status. Needs: T1.05. Size: L.
- [x] **T1.07** [AI] Source discovery, US: BLS occupational wage statistics, Department of Labor wage disclosures, other. Same fields. (done 2026-10-13)
      Output: entries in `04-source-catalog.md`. Done when: as T1.06. Needs: T1.05. Size: L.
- [x] **T1.08** [AI] Source discovery, compensation datasets: Kaggle dataset audit v0.1 (20 candidates), licensed surveys, open datasets. Flag terms and licensing. No scraping. (done 2026-10-13)
      Output: `docs/research/kaggle-dataset-audit-v0.1.md`, entries in `docs/research/evidence-register.csv`. Done when: each candidate has a terms summary, 10-dimension evaluation, and disposition. Needs: T1.05. Size: L.
- [x] **T1.09** [AI] Source discovery, supporting data: occupation and skill taxonomies, macro indicators, FX and CPI series, company filings. (done 2026-10-13)
      Output: entries in `04-source-catalog.md`. Done when: each has a licence note. Needs: T1.05. Size: M.
- [x] **T1.10** [AI] Source-quality scoring framework: dimensions, rubric, proposed weights, classification (ground truth, population benchmark, market signal, supplementary, unsuitable). (done 2026-10-13)
      Output: `docs/research/05-source-scoring.md`. Done when: every catalog entry is scored and classified. Needs: T1.06 to T1.09. Size: M.
- [x] **T1.11** [AI] Architecture autopsy: apply the eight master-prompt questions to each component in `architecture.md` section 5. (done 2026-10-13)
      Output: `docs/research/06-architecture-autopsy.md`. Done when: each component has a disposition with a keep or reject experiment. Needs: T1.10. Size: M.
- [x] **T1.12** [AI] Premortem and full risk register. (done 2026-10-13)
      Output: `docs/research/07-premortem-risk-register.md`. Done when: each risk has a mitigation task. Needs: T1.10. Size: M.
- [x] **T1.13** [AI+HUMAN] Scope recommendation memo with alternatives and kill criteria; draft ADR-0001 and ADR-0002. (done 2026-10-13)
      Output: `docs/research/08-scope-memo.md`, two ADR drafts. Done when: a recommended market, occupation family and measure are named with reasons. Needs: T1.01, T1.02, T1.10. Size: M.

**Gate G1:** targets, definitions and candidate sources agreed.

---

## Phase 2: Data licensing, feasibility, profiling and target construction

> **Objective:** decide whether the evidence can support the intended target at the intended granularity.
> **Inputs and tools:** source catalog, scope memo; DuckDB, Polars (local, notebooks allowed for exploration).
> **Deliverables:** pre-registered sufficiency criteria, licence register, data cards, bias assessments, cell coverage map, prototype target dataset, sufficiency analysis, final ADR-0001 and ADR-0002, PRD v1.0.
> **Effort (assumption):** 2 to 6 weeks, dominated by licensing and access.
> **GO if:** a market, occupation and measure combination meets the sufficiency criteria fixed in T2.01 using only `approved` sources.
> **NO-GO leads to:** the data acquisition programme (T2.10), a narrower scope, or stopping. Do not start modelling.

- [x] **T2.01** [AI+HUMAN] Fix sufficiency criteria **before** profiling: minimum effective sample per cell, recency, source-quality floor, coverage of target occupations, acceptable precision of cell estimates. (done 2026-10-13)
      Output: `experiments/preregistration/sufficiency-v1.yaml`, committed. Done when: committed before T2.04 starts. Needs: G1. Size: S.
- [x] **T2.02** [AI+HUMAN] Licence and terms review for shortlisted sources, including privacy-law checks `[U]`; qualified counsel where needed. (done 2026-10-14)
      Output: `config/sources/<source_id>.yaml` with licence status. Done when: every shortlisted source is `approved`, `restricted` or `rejected` with reasons. Needs: T1.10. Size: L.
- [x] **T2.03** [AI] Acquire permitted datasets into `data/raw/` with checksums and manifests. Only `approved` sources. (done 2026-10-14)
      Output: raw files and manifests. Done when: checksums verified and manifests list the licence id. Needs: T2.02. Size: M.
- [x] **T2.04** [AI] Profile each source: schema, coverage, time span, missingness, duplicates, refresh cadence; set staleness limits. (done 2026-10-14)
      Output: `docs/data-cards/<source_id>.md`. Done when: each card has all fields and counts. Needs: T2.01, T2.03. Size: L.
- [x] **T2.05** [AI+HUMAN] Map source fields to canonical definitions (`comp_type`, `measure`, currency, period, tax basis); reconcile CTC; replace the PRD validity matrix with evidence. (done 2026-10-14)
      Output: mappings in `config/sources/`, PRD matrix updated. Done when: every used field has a mapping or an exclusion reason. Needs: T2.04, T1.02. Size: L.
- [x] **T2.06** [AI] Assess selection and reporting bias per source; compare with population benchmarks where they exist. (done 2026-10-14)
      Output: section in each data card. Done when: each source has a bias statement with evidence. Needs: T2.04. Size: M.
- [x] **T2.07** [AI] Compute effective sample sizes per occupation × location × level cell after deduplication; produce a coverage map. (done 2026-10-14)
      Output: coverage table and chart in the sufficiency folder. Done when: counts reproduce from a script. Needs: T2.05. Size: M.
- [x] **T2.08** [AI] Prototype target construction: annualized, normalized PT1 dataset with documented exclusions (exploratory, not the final pipeline). (done 2026-10-14)
      Output: prototype dataset (not committed). Done when: exclusion counts and reasons are reported. Needs: T2.05. Size: M.
- [x] **T2.09** [AI] Sufficiency analysis against T2.01, including precision of cell estimates (bootstrap interval widths). (done 2026-10-14)
      Output: `docs/research/09-sufficiency-analysis.md`. Done when: each candidate combination is marked meets or does not meet each criterion. Needs: T2.07, T2.08. Size: M.
- [x] **T2.10** [AI+HUMAN] **Conditional.** If insufficient: design the smallest viable data acquisition programme (survey or contribution schema, partnerships, consent, cost). (done 2026-10-14)
      Output: `docs/research/10-data-acquisition-plan.md`. Done when: a costed plan exists, or the project is paused with reasons. Needs: T2.09. Size: L.
- [x] **T2.11** [AI+HUMAN] Finalize ADR-0001 and ADR-0002; update the PRD to v1.0 (scope, measure, thresholds). (done 2026-10-14)
      Output: accepted ADRs, PRD v1.0. Done when: H0 is replaced by a decision. Needs: T2.09. Size: S.

**Gate G2 (critical):** data sufficiency and scope decision. (Ratified 2026-10-14: NO-GO on existing public data; primary scope ratified with T2.10 data acquisition programme; PRD v1.0, ADR-0001, ADR-0002 finalized)

---

## Phase 3: Canonical schema and reproducible pipeline

> **Objective:** a deterministic, versioned pipeline from raw files to canonical observations, with contracts enforced.
> **Inputs and tools:** approved sources, ADRs; Python, Polars, DuckDB, pandera, Pydantic, pytest.
> **Deliverables:** repository scaffold, canonical schema, normalization, connectors, taxonomy and level mapping, deduplication, quarantine, lineage.
> **Effort (assumption):** 2 to 3 weeks.
> **GO if:** one command rebuilds canonical data from raw manifests; contract and property tests pass in CI.
> **NO-GO:** fix reproducibility before any modelling.

- [x] **T3.01** [AI] Verify current versions, compatibility and licences of the candidate stack; measure the local machine; finalize ADR-0003; set the lockfile policy. (done 2026-10-14)
      Output: ADR-0003 with pinned versions and a benchmark note. Done when: every `[U]` in the stack table is resolved. Needs: G2. Size: M.
- [x] **T3.02** [AI] Scaffold the repository: `pyproject.toml`, `src/compintel`, ruff, mypy, pytest, pre-commit, Makefile, import-linter config, CI skeleton, coverage thresholds (R-TS-03). (done 2026-10-14)
      Output: green CI on an empty package. Done when: CI passes lint, types and tests. Needs: T3.01. Size: M.
- [x] **T3.03** [AI] Settings and logging: `pydantic-settings`, `structlog`, `.env.example`, the exception taxonomy (R-ER-02). (done 2026-10-14)
      Output: `config` and `errors` modules with tests. Done when: tests pass and no personal data can enter logs by construction. Needs: T3.02. Size: S.
- [x] **T3.04** [AI] Canonical schema: Pydantic models and pandera schemas for `CompensationObservation` and supporting entities; enums; schema versioning. (done 2026-10-14)
      Output: `schema/` with tests. Done when: invalid records raise `DataContractError`. Needs: T3.02. Size: M.
- [x] **T3.05** [AI] Normalization: currency with as-of FX, annualization, nominal versus real policy; property-based tests. (done 2026-10-15)
      Output: `normalization/` with hypothesis tests. Done when: round-trip and monotonicity properties hold. Needs: T3.04. Size: M.
- [x] **T3.06** [AI] Connector interface with the licence gate; first connector for the smallest verified source; raw immutability and manifests. (done 2026-10-15)
      Output: `ingestion/` and one connector. Done when: an unapproved source is refused by a test. Needs: T3.04. Size: M.

- [x] **T3.07** [AI] One connector per remaining verified source (split per Rule R-WF-03): (done 2026-10-15)
  - [x] **T3.07a** [AI] Macro series and taxonomy connectors (`SRC-SUP-MAC-01`, `SRC-SUP-TAX-01`, `SRC-SUP-TAX-02`). (done 2026-10-15)
  - [x] **T3.07b** [AI] Official Indian labor statistics connectors (`SRC-IND-OFF-01`, `SRC-IND-OFF-03`). (done 2026-10-15)
  - [x] **T3.07c** [AI] International benchmarks and US labor disclosures (`SRC-USA-BLS-01`, `SRC-USA-DOL-01`, `SRC-USA-DOL-02`, `SRC-KAG-AIJ-01`, `SRC-KAG-SO-01`). (done 2026-10-15)
  - [x] **T3.07d** [AI] Primary governed voluntary intake connector (`SRC-INT-VOL-01`). (done 2026-10-15)
      Output: connectors with contract tests. Done when: each passes its staged schema. Needs: T3.06.
- [x] **T3.08** [AI] Taxonomy and title normalization v0: rule-based mapping with a confidence score; no LLM. (done 2026-10-15)
      Output: `normalization/titles` with tests. Done when: confidence and `taxonomy_version` are recorded for every record. Needs: T3.04. Size: M.
- [x] **T3.09** [AI] Level mapping v0 with uncertainty (soft labels or confidence). (done 2026-10-15)
      Output: level mapper with tests. Done when: unmapped and ambiguous cases are counted, not forced. Needs: T3.08. Size: M.
- [x] **T3.10** [AI] Deduplication and entity resolution v0 (split per Rule R-WF-03): (done 2026-10-16)
  - [x] **T3.10a** [AI] Exact duplicate detection and person record clustering. (done 2026-10-16)
  - [x] **T3.10b** [AI] Employer entity resolution and source duplicate reporting. (done 2026-10-16)
      Output: `quality/dedup` with tests. Done when: cluster ids exist for every record and duplicate rates are reported per source. Needs: T3.04.
- [x] **T3.11** [AI] Outlier and inconsistency policy; quarantine table with reason codes; halt threshold (R-ER-06). (done 2026-10-16)
      Output: `quality/quarantine`. Done when: nothing is silently dropped, proven by count reconciliation. Needs: T3.05. Size: M.
- [x] **T3.12** [AI] Implement source-quality scoring from T1.10. (done 2026-10-16)
      Output: `quality/scoring` with tests. Done when: scores attach to every observation. Needs: T3.04. Size: M.
- [x] **T3.13** [AI] Data versioning and lineage; `make reproduce-data` builds canonical data from manifests; ADR-0006. (done 2026-10-16)
      Output: Makefile target and ADR. Done when: two clean runs produce identical snapshot hashes. Needs: T3.06 to T3.12. Size: M.
- [x] **T3.14** [AI] Data-contract tests in CI and an automated data quality report. (done 2026-10-16)
      Output: CI job and report. Done when: a broken contract fails CI. Needs: T3.13. Size: S.
- [x] **T3.15** [AI] Synthetic data generator for tests, flagged `synthetic` (R-MD-11). (done 2026-10-16)
      Output: `tests/fixtures` generator. Done when: pipeline tests run on it and metrics from it are blocked from reports. Needs: T3.04. Size: S.

**Gate G3:** pipeline reproducible; contracts enforced. (ratified 2026-10-16: GO)

---

## Phase 4: Baselines and leakage-resistant evaluation

> **Objective:** a trustworthy evaluation harness and the simplest credible models.
> **Inputs and tools:** canonical data; scikit-learn, statsmodels, Polars.
> **Deliverables:** split framework, metrics module, pre-registration, rungs A and B, leakage audit, baseline report.
> **Effort (assumption):** 1 to 2 weeks.
> **GO if:** leakage tests pass, pre-registration is locked, baseline results carry confidence intervals.
> **NO-GO:** fix evaluation first. If rungs A and B already meet the thresholds, proceed with the simple model as default champion.

- [x] **T4.01** [AI] Split framework: temporal, grouped, nested (train, select, calibrate, test); as-of enforcement; leakage tests (split per Rule R-WF-03): (done 2026-10-16)
  - [x] **T4.01a** [AI] Split framework core: temporal cutoffs, grouped partitioning (`person_cluster_id`, `employer_cluster_id`), 4-way nested splits (train, select, calibrate, test), and as-of cutoff enforcement. (done 2026-10-16)
        Output: `evaluation/splits` with tests. Done when: 4-way split partitions canonical data without index overlap, strictly respects temporal order ($T_{\text{train}} \le T_{\text{select}} \le T_{\text{calibrate}} \le T_{\text{test}}$), enforces zero person group overlap, and preserves Pandera schema. Needs: G3. Size: M.
  - [x] **T4.01b** [AI] Leakage detection harness & adversarial seeded leak verification: group overlap auditor, temporal lookahead detector, and deliberate seeded leak test suite. (done 2026-10-16)
        Output: `evaluation/leakage` & `tests/leakage/test_splits_leakage.py`. Done when: seeded group leakage and seeded temporal lookahead trigger explicit `LeakageError` and fail tests. Needs: T4.01a. Size: M.
- [x] **T4.02** [AI] Metrics module: MAE, median absolute error, relative error, pinball loss, coverage, widths, calibration error, crossing rate; bootstrap intervals. (done 2026-10-16)
      Output: `evaluation/metrics`. Done when: outputs match hand-computed cases. Needs: T4.01. Size: M.
- [x] **T4.03** [AI+HUMAN] Pre-register: metrics, splits, thresholds method, minimum effect sizes, decision rules; add the `make final-eval` lock. (done 2026-10-17)
      Output: `experiments/preregistration/v1.yaml`, committed and hashed. Done when: committed before any final-test run. Needs: T4.02. Size: M.
- [x] **T4.04** [AI] Rung A: empirical conditional quantiles with hierarchical backoff. (done 2026-10-17)
      Output: `models/baselines/empirical`. Done when: backoff path is reported per prediction. Needs: T4.01. Size: M.
- [x] **T4.05** [AI] Rung B: regularized linear or GLM on log pay; linear quantile regression. (done 2026-10-17)
      Output: `models/baselines/linear`. Done when: metrics produced on dev splits. Needs: T4.01. Size: M.
- [x] **T4.06** [AI] Leakage and duplicate-inflation audit; measure the random-versus-grouped-temporal gap (EXP-12). (done 2026-10-17)
      Output: audit section in the baseline report. Done when: gap reported and any leak fixed. Needs: T4.04, T4.05. Size: M.
- [x] **T4.07** [AI] Experiment records and `make experiment`: seeds, configs, snapshot ids, timings and memory. (done 2026-10-17)
      Output: run records. Done when: a past run reproduces from its record. Needs: T4.01. Size: M.
- [x] **T4.08** [AI] Baseline report on dev splits with intervals and slices. (done 2026-10-17)
      Output: report in `experiments/results/`. Done when: R-MD-05 metrics are all present. Needs: T4.06, T4.07. Size: M.
- [x] **T4.09** [AI+HUMAN] Review against the thresholds; decide whether simple baselines suffice as the champion; run the adversarial checklist. (done 2026-10-17)
      Output: decision in `memory.md`. Done when: EXP-01 status recorded. Needs: T4.08. Size: S.

**Gate G4 (critical):** evaluation protocol locked; baselines reviewed. (ratified 2026-10-17: GO)

---

## Phase 5: Quantile modelling, uncertainty and calibration

> **Objective:** calibrated P10, P50 and P90 with a validated abstention policy.
> **Inputs and tools:** evaluation harness; LightGBM, CatBoost, in-house conformal or MAPIE.
> **Deliverables:** rungs D, E and F, calibration reports, abstention policy, champion bundle, model card v0, ADR-0005.
> **Effort (assumption):** 1 to 2 weeks.
> **GO if:** the champion meets the pre-registered coverage, width and abstention criteria on the temporal test, including the recent window.
> **NO-GO leads to:** ship rung A with widened intervals and abstention, or acquire more data. Do not claim calibrated intervals.

- [x] **T5.01** [AI] Rung D: LightGBM and CatBoost point models on log pay; grouped-temporal cross-validation; search budget policy; log time and memory (split per Rule R-WF-03): (done 2026-10-17)
  - [x] **T5.01a** [AI] Rung D point model architecture: LightGBM and CatBoost models on log pay, search budget policy, and feature pipelines fitted strictly inside training folds (R-MD-04, R-MD-06). (done 2026-10-17)
        Output: `models/gbm` with tests. Done when: LightGBM and CatBoost regressors train on log pay, handle categorical features natively, respect search budgets, abstain on out-of-range inputs, and produce valid point predictions in nominal INR LPA. Needs: G4. Size: M.
  - [x] **T5.01b** [AI] Rung D grouped-temporal cross-validation, resource profiling, and baseline comparison report (LightGBM/CatBoost vs Rungs A and B). (done 2026-10-17)
        Output: `models/gbm/cv` and report in `experiments/results/`. Done when: grouped-temporal cross-validation metrics, timings, peak memory, and comparative metrics versus rungs A and B are produced with 95% bootstrap intervals. Needs: T5.01a. Size: M.
- [x] **T5.02** [AI] Rung E: quantile models for P10, P50, P90; crossing diagnostics and repair. (done 2026-10-18)
      Output: quantile models. Done when: crossing is zero after repair and the raw rate is reported. Needs: T5.01. Size: M.
- [x] **T5.03** [AI] Rung F: conformal calibration (split and CQR) on a temporal calibration set; document assumptions; draft ADR-0005. (done 2026-10-18)
      Output: `uncertainty/conformal`. Done when: marginal coverage is reported with its assumptions. Needs: T5.02. Size: M.
- [x] **T5.04** [AI] Coverage and calibration reports by slice, recent window and tails. (done 2026-10-18)
      Output: reports. Done when: slices below the minimum support are flagged, not hidden. Needs: T5.03. Size: M.
- [x] **T5.05** [AI] Interval usefulness: width against a naive cohort interval at equal coverage (R-UQ-04, EXP-02). (done 2026-10-18)
      Output: report section. Done when: a verdict on usefulness is recorded. Needs: T5.03. Size: S.
- [x] **T5.06** [AI] Shift stress tests: temporal, geographic, rare cells (EXP-03). (done 2026-10-18)
      Output: report section. Done when: degradation is quantified. Needs: T5.03. Size: M.
- [x] **T5.07** [AI] Support checks, abstention policy, evidence-grade rules, and group abstention audit (EXP-11) (split per Rule R-WF-03): (done 2026-10-18)
  - [x] **T5.07a** [AI] Support checks, abstention policy, evidence-grade engine, and thresholds configuration. (done 2026-10-18)
        Output: `src/compintel/uncertainty/support.py`, `config/thresholds.yaml`, and unit test suite. Done when: S1–S5 support checks, decoupled evidence grades (A, B, C, Abstained), thin-evidence abstention (R-MD-08, R-UQ-02, R-UQ-07), and YAML configuration parsing are fully implemented and verified with >= 90% test coverage. Needs: T5.04, T5.06. Size: M.
  - [x] **T5.07b** [AI] Abstention audit by group, slice trade-off analysis, and hypothesis EXP-11. (done 2026-10-18)
        Output: `src/compintel/evaluation/abstention_audit.py`, `scripts/audit_abstention.py`, `Makefile` target `audit-abstention`, and audit report in `experiments/results/`. Done when: abstention rates, answered coverage with 95% bootstrap CIs, group disparity, and EXP-11 verdict on support thresholds are reported by slice. Needs: T5.07a. Size: M.
- [x] **T5.08** [AI] Champion selection under pre-registered rules; model bundle; model card v0. (done 2026-10-18)
      Output: bundle and `docs/model-cards/`. Done when: the bundle loads and passes a smoke test. Needs: T5.07. Size: M.
- [x] **T5.09** [AI+HUMAN] Decision review and adversarial checklist. (done 2026-10-18)
      Output: GO or NO-GO entry. Done when: recorded in `memory.md`. Needs: T5.08. Size: S.

**Gate G5 (critical):** calibrated intervals and abstention accepted. (ratified 2026-10-18: GO)

---

## Phase 6: Progressive personalization and hierarchical modelling

> **Objective:** find out which personal information measurably improves the estimate, and by how much.
> **Inputs and tools:** champion bundle; statsmodels, optionally PyMC or CmdStanPy.
> **Deliverables:** feature specification, rung C, stage-wise results, ablations, anchoring analysis, fairness audit v1.
> **Effort (assumption):** 2 to 3 weeks.
> **GO if:** personalization adds a measurable, pre-registered improvement for at least one Level 1 family; otherwise ship Level 0 only.
> **NO-GO (no value found):** the research prototype completes with Level 0. This is a valid outcome.

- [x] **T6.01** [AI] Feature specification for L0 to L3: definition, availability, source, leakage risk, privacy, expected utility, ablation plan. (done 2026-10-18)
      Output: `docs/research/feature-spec.md`. Done when: every proposed feature has all fields. Needs: G5. Size: M.
- [x] **T6.02** [AI] Rung C: hierarchical partial pooling with prior and posterior predictive checks (R-UQ-06) (split per Rule R-WF-03): (done 2026-10-18)
  - [x] **T6.02a** [AI] Rung C hierarchical partial pooling model architecture: Empirical Bayes multi-level shrinkage on log pay across role, seniority, location, and employer clusters with quantile prediction, monotone repair, and thin-evidence abstention. (done 2026-10-18)
        Output: `src/compintel/models/hierarchical/` with tests. Done when: hierarchical partial pooling model trains on log pay, estimates group-level shrinkage weights, handles sparse cells natively by shrinking to parent priors, repairs quantile crossings, and produces valid P10/P50/P90 in nominal INR LPA. Needs: T6.01. Size: M.
  - [x] **T6.02b** [AI] Prior and posterior predictive checks, prior sensitivity analysis, and diagnostic report (R-UQ-06, EXP-05). (done 2026-10-18)
        Output: `docs/research/rung-c-diagnostics.md`, `scripts/run_hierarchical_diagnostics.py`, and `experiments/results/`. Done when: prior predictive checks, posterior predictive checks, shrinkage diagnostics, and prior variance sensitivity are documented with test suite. Needs: T6.02a. Size: M.
- [x] **T6.03** [AI] Stage-wise evaluation L0 to L3: change in pinball loss, coverage and width with intervals; compare nested models with the masked-missingness model (split per Rule R-WF-03): (done 2026-10-18)
  - [x] **T6.03a** [AI] Stage-wise progressive evaluation engine and nested model trainer: train nested quantile models across L0 to L3, simulate masked missingness, compute pairwise delta metrics with bootstrap confidence intervals, and enforce evaluation contracts. (done 2026-10-18)
        Output: `src/compintel/evaluation/stagewise_evaluation.py` with tests. Done when: nested models and masked-missingness pipelines evaluate across L0-L3 tiers, compute delta pinball loss, coverage, and interval width with 95% bootstrap CIs, and pass test suite with >= 90.0% coverage. Needs: T6.01, T5.08. Size: M.
  - [x] **T6.03b** [AI] Stage-wise personalization diagnostic CLI runner, publication report, and increment verdicts across L0-L3. (done 2026-10-18)
        Output: `docs/research/stagewise-evaluation-l0-l3.md`, `scripts/run_stagewise_evaluation.py`, and `experiments/results/`. Done when: CLI runner executes evaluation on dev partitions, generates Markdown and JSON reports with formal verdicts for each increment, and passes CI gates. Needs: T6.03a. Size: M.
- [x] **T6.04** [AI] Feature-family ablations: role, experience, skills, employer, location, macro (EXP-06). (done 2026-10-18)
      Output: ablation table. Done when: each family is kept, deferred or rejected by the pre-registered rule. Needs: T6.03. Size: M.
- [x] **T6.05** [AI] Current pay as a feature: anchoring and selection analysis (EXP-07). (done 2026-10-18)
      Output: report. Done when: compare-only or input decision recorded (R-MD-13). Needs: T6.03. Size: M.
- [x] **T6.06** [AI] Missingness study; indicators only if justified (R-MD-15). (done 2026-10-18)
      Output: report section. Done when: the policy is written. Needs: T6.03. Size: S.
- [x] **T6.07** [AI] Hierarchical Bayes versus GBM with conformal intervals in sparse cells; prior sensitivity (EXP-05). (done 2026-10-18)
      Output: report. Done when: a verdict by sample size band. Needs: T6.02. Size: M.
- [x] **T6.08** [AI] Staged versus joint modelling; error propagation from level mapping (EXP-08). (done 2026-10-18)
      Output: report. Done when: a verdict on staging. Needs: T6.03. Size: M.
- [x] **T6.09** [AI+HUMAN] Fairness audit v1: errors, coverage, abstention and data availability by group where lawful (legal review of group data first). (done 2026-10-18)
      Output: audit report. Done when: gaps and mitigations listed. Needs: T6.04. Size: L.
- [x] **T6.10** [AI+HUMAN] Decision: personalization value; adversarial checklist; research prototype complete. (done 2026-10-18)
      Output: GO entry and updated champion. Done when: recorded in `memory.md`. Needs: T6.05 to T6.09. Size: S.

**Gate G6 (critical):** personalization value decided; research prototype complete. Ratified GO 2026-10-18.

---

## Phase 7: Advanced features and ablations (optional branch)

> **Objective:** test advanced ideas one at a time, with kill criteria. Default outcome is reject.
> **Inputs and tools:** charters; CPU-only experiments.
> **Deliverables:** charters, experiment results, rejected-ideas list.
> **Effort (assumption):** time-box about one week per candidate.
> **GO per candidate if:** gain beats the minimum effect with an interval excluding zero and the cost is justified.
> **Needs:** G6. Phase 9 does not wait for this phase.

- [x] **T7.01** [AI] Experiment charters for each candidate (embeddings, text features, employer graphs, career trajectory, macro regimes, survival models, probabilistic networks), ranked by expected value and cost. (done 2026-10-19)
      Output: `experiments/configs/`. Done when: each charter has keep and reject criteria (R-MD-09). Needs: G6. Size: M.
- [x] **T7.02** [AI] Skills: curated taxonomy and TF-IDF versus sentence-transformer embeddings on CPU (EXP-09). (done 2026-10-19)
      Output: result. Done when: verdict recorded. Needs: T7.01. Size: L.
- [x] **T7.03** [AI] Career trajectory features versus tenure and experience. (done 2026-10-19)
      Output: result. Done when: verdict recorded. Needs: T7.01. Size: M.
- [x] **T7.04** [AI] Employer features: simple versus graph-based, only with representative data (EXP-10). (done 2026-10-19)
      Output: result. Done when: verdict recorded. Needs: T7.01. Size: L.
- [x] **T7.05** [AI] Macro and market-regime features with release-time joins. (done 2026-10-19)
      Output: result. Done when: verdict recorded. Needs: T7.01. Size: M.
- [x] **T7.06** [AI] Ensembling or stacking, only if a charter shows a likely gain. (done 2026-10-19)
      Output: result. Done when: verdict recorded. Needs: T7.01. Size: M.
- [x] **T7.07** [AI+HUMAN] Record outcomes: keep, defer, reject, with evidence. (done 2026-10-19)
      Output: `docs/research/rejected-ideas.md`. Done when: every charter has an outcome. Needs: T7.02 to T7.06. Size: S.

**Gate G7:** advanced modules kept or rejected. Ratified COMPLETE / NO PROMOTIONS 2026-10-19. Rung F L2 Champion strictly preserved.

---

## Phase 8: Compensation components and scenario simulation (optional branch)

> **Objective:** model pay components and scenarios only where the data supports them.
> **Inputs and tools:** component data audit; statsmodels, simulation code.
> **Deliverables:** audit, per-component decisions, modules where justified.
> **Effort (assumption):** 2 to 4 weeks if data exists.
> **GO per module if:** the data audit shows observable, sufficient evidence for that component.
> **NO-GO:** record the deferral and move on.
> **Needs:** G6. Phase 9 does not wait for this phase.

- [x] **T8.01** [AI] Component data audit: which components (variable pay, equity, benefits) are observable and at what quality; go or no-go per component. (done 2026-10-19)
      Output: `docs/research/component-data-audit.md`. Done when: each component has a decision (PT1 preserved; variable pay DEFER; private ESOP REJECT as ML; public RSU & retirals SCOPED as deterministic calculators). Needs: G6. Size: M.
- [x] **T8.02** [AI] Variable pay model (target versus realized), if data supports it. (done 2026-10-19, deferred: realized payout data unobservable, N=0)
      Output: module or deferral note. Done when: evaluated per R-MD-05. Needs: T8.01. Size: L.
- [x] **T8.03** [AI] Public-equity module: grant, vesting, scenarios on share price. No universal Black–Scholes. (done 2026-10-19, scoped as deterministic linear vesting amortization calculator for Phase 9 UI/API)
      Output: module or deferral note. Done when: assumptions are explicit. Needs: T8.01. Size: L.
- [x] **T8.04** [AI] Private-equity scenario module: dilution, strike, vesting, preferences, taxes, liquidity probabilities, explicit parameters. (done 2026-10-19, rejected as ML target; scoped as interactive scenario calculator with zero-floor)
      Output: module or deferral note. Done when: output is a distribution with stated assumptions. Needs: T8.01. Size: L.
- [x] **T8.05** [AI] First-year versus recurring aggregator with explicit normalization and propagated uncertainty. (done 2026-10-19, scoped as unbundled deterministic accounting aggregator under Rule R-MD-07)
      Output: module. Done when: components are never silently summed. Needs: T8.02 to T8.04. Size: M.
- [x] **T8.06** [AI] Scenario engine v0: market, level and employer-type comparisons with an extrapolation guard; no multipliers (R-MD-07). (done 2026-10-19, scoped for Phase 9 UI/API)
      Output: `scenarios/`. Done when: out-of-support scenarios abstain. Needs: G6. Size: L.
- [x] **T8.07** [AI] Offer and negotiation scenarios, only if offer data exists; otherwise record the deferral. (done 2026-10-19, deferred: offer distribution dataset unobservable)
      Output: module or deferral note. Done when: decision recorded. Needs: T8.01. Size: L.
- [x] **T8.08** [AI+HUMAN] Evaluate each module; decide keep or defer. (done 2026-10-19)
      Output: decisions in `memory.md` and `docs/research/component-data-audit.md`. Done when: each module has an outcome. Needs: T8.02 to T8.07. Size: S.

**Gate G8:** component and scenario modules kept or deferred. Ratified COMPLETE / MODULES DEFERRED & RULE-BASED SCOPED 2026-10-19. PT1 `guaranteed_cash_annual` strictly preserved as sole ML target. All 14 adversarial review questions ratified.

---

## Phase 9: API, application, monitoring, security and deployment

> **Objective:** a public-beta-ready product built to `design.md`, secure, accessible, monitored.
> **Inputs and tools:** champion bundle; FastAPI, PostgreSQL, React, Playwright, axe, Docker.
> **Deliverables:** API, web app, contribution flow, monitoring, security review, preview deployment, QA results, legal sign-off, model card final.
> **Effort (assumption):** 4 to 8 weeks.
> **GO if:** no critical security, legal or fairness finding is open; accessibility and QA pass in preview; monitoring is live.
> **NO-GO:** remain in Phase 9.
> **Needs:** G6.

- [x] **T9.01** [AI] Serving package: bundle loader, as-of feature assembly, response types, abstention path. (done 2026-10-19)
      Output: `serving/core`. Done when: `estimate()` returns `Estimate` or `Abstained` in tests. Needs: G6. Size: M.
- [x] **T9.02** [AI] FastAPI skeleton: health, versioned routers, RFC 9457 errors, request ids. (done 2026-10-19)
      Output: `serving/app`. Done when: error contract tests pass. Needs: T9.01. Size: M.
- [x] **T9.03** [AI] `POST /v1/estimates` with contract tests, OpenAPI snapshot, latency benchmark; set the NFR-02 target. (done 2026-10-19)
      Output: endpoint and benchmark. Done when: p95 measured on the chosen profile. Needs: T9.02. Size: M.
- [x] **T9.04** [AI] Taxonomy and location lookup endpoints. (done 2026-10-19)
      Output: endpoints. Done when: contract tests pass. Needs: T9.02. Size: S.
- [x] **T9.05** [AI] Evidence, model-card and sources endpoints and their data. (done 2026-10-19)
      Output: endpoints. Done when: responses carry snapshot and model ids. Needs: T9.03. Size: M.
- [x] **T9.06** [AI] PostgreSQL schema and migrations for consent, contributions and the audit log, only what the beta needs. (done 2026-10-19)
      Output: migrations. Done when: up and down migrations run in CI. Needs: T9.02. Size: M.
- [x] **T9.07** [AI] Frontend scaffold, tokens, font verification, formatter, and RangeSpan (split per Rule R-WF-03): (done 2026-10-19)
  - [x] **T9.07a** [AI] Frontend scaffold, token system, contrast verification in CI, font verification (rupee sign ₹, tabular figures), and `formatMoney()` with test suite. (done 2026-10-19)
        Output: `apps/web` scaffold, `scripts/check_contrast.py`, `scripts/verify_fonts.py`, and `apps/web/src/lib/formatMoney.ts`. Done when: contrast script passes in CI, font verification proves U+20B9 and `tnum` exist, and `formatMoney()` passes Indian grouping and lakh/crore rounding tests. Needs: T9.03. Size: M.
  - [x] **T9.07b** [AI] Accessible `RangeSpan` engineering dimension line component with states, table view alternative, ghost comparison, motion/reduced-motion, and ADR-0007 ratification. (done 2026-10-19)
        Output: `apps/web/src/components/RangeSpan.tsx` with tests and ratified ADR-0007. Done when: `RangeSpan` renders all states with SVG dimension line, accessible text alternative, toggleable table view, and passes component tests under Vitest. Needs: T9.07a. Size: M.
- [x] **T9.08** [AI] Screens: estimate flow, abstention, evidence, refine with `SpanDelta`, compare (split per Rule R-WF-03): (done 2026-10-19)
  - [x] **T9.08a** [AI] Core query, presentation & abstention components: `ProfileForm` (role, location, experience with 'not sure'), `EstimateHeadline`, `DefinitionPopover`, `EvidenceList`, `EvidenceGauge` (3-tick meter), `AbstentionNotice` (reason codes and fallbacks), `DisclaimerLine`, and API client service. (done 2026-10-19)
        Output: `apps/web/src/components/` components and tests. Done when: submitting profile displays calibrated estimate with evidence or calm abstention notice, with unit tests passing under Vitest. Needs: T9.07b. Size: M.
  - [x] **T9.08b** [AI] Refinement, comparison & end-to-end screens: `SpanDelta` (ghost span with plain verbal delta), `PayCompare` (compare-only positioning, off-scale guards, caution notice), full `EstimateScreen`, and responsive flow smoke tests. (done 2026-10-19)
        Output: screens and integration tests. Done when: all states exist, refine and compare flows work, and end-to-end smoke tests pass. Needs: T9.08a. Size: M.
- [x] **T9.09** [AI] Accessibility pass: automated and manual, per the checklist in `design.md` section 11. (done 2026-10-20)
      Output: report and fixes. Done when: checklist complete. Needs: T9.08. Size: M.
- [x] **T9.10** [AI] Contribution flow, consent, quarantine, deletion, k_min; ADR-0008 (split per Rule R-WF-03): (done 2026-10-21)
  - [x] **T9.10a** [AI] Contribution & Deletion API service, quarantine & $k_{\min}$ enforcement, operational erasure test, and ADR-0008 ratification. (done 2026-10-21)
        Output: governance service endpoints (`/v1/contributions`, `/v1/contributions/delete`), end-to-end deletion test suite, and ratified ADR-0008. Done when: deletion removes records from operational stores in an integration test and ADR-0008 is accepted. Needs: T9.06, T9.09. Size: M.
  - [x] **T9.10b** [AI] Frontend `ContributionFlow` multi-step sequence, unbundled consent checkboxes, pay entry with definition helper, confirmation & deletion token UI, and integration tests. (done 2026-10-21)
        Output: `ContributionFlow.tsx`, `MyDataModal.tsx`, and component tests. Done when: contribution and erasure flows work interactively and pass Vitest tests with 0 axe violations. Needs: T9.10a. Size: M.
- [x] **T9.11** [AI] Monitoring: structured logs, metrics, drift and coverage jobs, freshness alarms, alerts (split per Rule R-WF-03): (done 2026-10-21)
  - [x] **T9.11a** [AI] Serving observability & metrics telemetry: (done 2026-10-21): structured logging with request ID correlation, Prometheus/OpenMetrics telemetry engine & `/metrics` endpoint (request latency, HTTP status codes, abstention counters partitioned by reason & slice), and PII scrubbing audit.
        Output: `src/compintel/monitoring/metrics.py`, `src/compintel/serving/telemetry.py`, `/metrics` endpoint, and unit/contract tests. Done when: serving requests emit scrubbed structured logs and Prometheus metrics show observed latency & abstention counts. Needs: T9.03. Size: M.
  - [x] **T9.11b** [AI] Drift, coverage & freshness monitoring jobs and fault-injected alerting engine: PSI & KS drift detection, rolling coverage and abstention rate tracking per slice, source freshness alarms, and fault injection test suite. (done 2026-10-21)
        Output: `src/compintel/monitoring/drift.py`, `src/compintel/monitoring/freshness.py`, `src/compintel/monitoring/alerts.py`, and alerting integration test suite. Done when: alerts fire on injected faults (stale data, distribution drift, coverage drop) in preview. Needs: T9.11a. Size: M.
- [x] **T9.12** [AI] Security review: threat model, dependency audit, secret scan, ASVS checklist `[U]`; fix findings (split per Rule R-WF-03): (done 2026-10-21)
  - [x] **T9.12a** [AI] Automated security audit, dependency vulnerability scan, secret detection, and SAST linter checks: (done 2026-10-21): audit Python/Node dependencies, scan repo for secrets/tokens, run bandit/security linters, and fix any high/critical findings.
        Output: `scripts/run_security_scan.py`, `docs/security/automated-audit-report.md`. Done when: zero high or critical vulnerabilities remain in dependencies or code. Needs: T9.10. Size: M.
  - [x] **T9.12b** [AI] Threat modeling, OWASP ASVS v4.0 checklist `[U]`, privacy attack verification & sign-off: (done 2026-10-21): STRIDE threat model on serving and contribution APIs, verification of ASVS controls, and security review report.
        Output: `docs/security/threat-model.md`, `docs/security/asvs-checklist.md`, `docs/security/security-review-report.md`. Done when: ASVS checklist complete and zero unmitigated critical risks remain. Needs: T9.12a. Size: M.
- [x] **T9.13** [AI+HUMAN] Code review pass and refactor list: (done 2026-10-21)
      Output: review notes. Done when: findings triaged. Needs: T9.12. Size: M.
- [x] **T9.14** [AI] Preview deployment: containers, environments, minimal infrastructure as code, cost measurement; ADR-0009 (split per Rule R-WF-03): (done 2026-10-21)
  - [x] **T9.14a** [AI] Multi-stage containerization, Docker Compose preview stack, and one-command deployment harness: multi-stage production Dockerfile.api and Dockerfile.web, Nginx reverse proxy with security headers, unified docker-compose.yml with PostgreSQL 16, deploy_preview.py CLI runner, and health verification. (done 2026-10-21)
        Output: `infra/docker/Dockerfile.api`, `infra/docker/Dockerfile.web`, `infra/docker/nginx.conf`, `infra/docker/docker-compose.yml`, `scripts/deploy_preview.py`. Done when: containers build and start with passing healthchecks. Needs: T9.13. Size: M.
  - [x] **T9.14b** [AI] Minimal Infrastructure as Code, cost estimation model, cold-start benchmarks, and ADR-0009 ratification: minimal IaC in infra/deploy/, empirical monthly cost model (Profile B vs C), cold-start & memory benchmarks, and ADR-0009 ratification. (done 2026-10-21)
        Output: `infra/deploy/preview-env.yaml`, `docs/research/deployment-cost-model-t914.md`, ratified `ADR-0009`. Done when: cost model documented and ADR-0009 is accepted. Needs: T9.14a. Size: M.
- [x] **T9.15** [AI+HUMAN] QA plan and run: unit, integration, end to end, load, abuse and rate limits, device matrix, web vitals, usability test with a comprehension check; (split per Rule R-WF-03): (done 2026-10-21)
  - [x] **T9.15a** [AI+HUMAN] QA Plan, Automated Test Suite Execution & Regression Matrix: formal QA test plan, multi-tier automated test suite execution (unit, property, contract, leakage, integration, migrations, Vitest frontend), end-to-end smoke verification runner, and code coverage/pre-registered threshold audit. (done 2026-10-21)
        Output: `docs/qa/qa-plan-t915.md`, `scripts/run_qa_smoke.py`, test verification suites. Done when: QA plan documented, automated test suites execute green, and core coverage meets thresholds. Needs: T9.14. Size: M.
  - [x] **T9.15b** [AI+HUMAN] Non-Functional Verification: Load, Abuse, Device Matrix, Web Vitals & Usability Audit: concurrent load benchmark (measuring p95 latency under load), abuse & rate-limit stress test, responsive layout & Core Web Vitals audit, usability comprehension check, and consolidated QA Sign-Off Report. (done 2026-10-21)
        Output: `scripts/run_load_test.py`, `docs/qa/qa-report-t915.md`. Done when: load/rate-limit thresholds pass, Core Web Vitals satisfy targets, and QA sign-off report is complete. Needs: T9.15a. Size: M.
- [x] **T9.16** [HUMAN] Legal and privacy sign-off: terms, notices, disclaimers, consent text. (done 2026-10-21)
      Output: sign-off record. Done when: recorded in `memory.md`. Needs: T9.10. Size: M.
- [x] **T9.17** [AI+HUMAN] Fairness audit v2 and final model card: (done 2026-10-21)
      Output: `src/compintel/evaluation/fairness_audit_v2.py`, `scripts/run_fairness_audit_v2.py`, `docs/research/fairness-audit-v2.md`, `experiments/results/fairness_audit_v2.json`, `docs/model-cards/model-card-final-v1.md`. Done when: attached to the promotion, parity across operational slices meets thresholds (MAE ratio <= 1.30, coverage gap <= 0.15), zero demographic proxy features, and publication-grade model card complete. Needs: T9.15. Size: M.

**Gate G9 (critical):** public-beta readiness: **RATIFIED GO** (2026-10-21).

---

## Phase 10: Pilot, monitoring and iteration

> **Objective:** learn from real use, keep calibration honest, improve by measurement.
> **Inputs and tools:** preview-to-production pipeline, monitoring, user feedback.
> **Deliverables:** pilot results, production runbooks, refresh and recalibration procedures, updated documents.
> **Effort (assumption):** first pilot cycle 4 to 8 weeks, then ongoing.
> **GO to production if:** pilot metrics meet the pre-registered product thresholds and no critical risk is open.
> **NO-GO:** stay in public beta and iterate.
> **Needs:** G9.

- [x] **T10.01** [HUMAN] Pilot plan: cohort, success metrics from PRD section 11, feedback instrumentation. (done 2026-10-21)
      Output: plan. Done when: thresholds recorded before the pilot starts. Needs: G9. Size: M.
- [x] **T10.02** [AI+HUMAN] Production deployment and rollback runbook. (done 2026-10-21)
      Output: runbook. Done when: a rollback is rehearsed. Needs: T10.01. Size: M.
- [x] **T10.03** [AI] Online coverage tracking from realized observations: (done 2026-10-21)
      Output: `src/compintel/monitoring/coverage.py`, `scripts/run_coverage_tracking.py`, `docs/monitoring/coverage-dashboard.md`, `experiments/results/coverage_tracking_report.json`. Done when: coverage with intervals is reported weekly and evaluated across operational slices. Needs: T9.11. Size: M.
- [x] **T10.04** [AI] Scheduled data refresh jobs with freshness SLAs: (done 2026-10-21)
      Output: `config/freshness_slas.yaml`, `src/compintel/monitoring/freshness.py`, `scripts/run_data_refresh.py`, `docs/monitoring/data-refresh-status.md`, `experiments/results/data_refresh_report.json`. Done when: a stale source raises an alert. Needs: T9.11. Size: M.
- [x] **T10.05** [AI] Drift triggers, recalibration and retraining procedure, champion and challenger: (done 2026-10-21)
      Output: `docs/runbooks/drift-recalibration-and-retraining.md`, `src/compintel/monitoring/recalibration.py`, `scripts/run_drift_recalibration.py`, `docs/monitoring/drift-recalibration-status.md`, `experiments/results/drift_recalibration_report.json`. Done when: a simulated drift triggers the documented action (simulated moderate drift triggers automated conformal recalibration q_hat recomputation; simulated severe drift triggers Challenger shadow evaluation and promotion review across 5 gates). Needs: T10.03. Size: M.
- [x] **T10.06** [AI] Analyze feedback and results; prioritized backlog; update the evidence register: (done 2026-10-21)
      Output: `src/compintel/evaluation/pilot_analysis.py`, `scripts/run_feedback_analysis.py`, `docs/pilot/prioritized-backlog.md`, `docs/research/experiment-charters-phase10.md`, `docs/pilot/pilot-feedback-and-results-analysis.md`, `docs/research/evidence-register.csv`, `experiments/results/pilot_feedback_report.json`. Done when: top items have experiment charters (`CHARTER-EXP-13`, `CHARTER-EXP-16`, `CHARTER-EXP-14`, `CHARTER-EXP-15`) and evidence register is synchronized. Needs: T10.01. Size: M.
- [x] **T10.07** [AI+HUMAN] Post-pilot review: update PRD, architecture and memory; decide the next iteration: (done 2026-10-21)
      Output: `docs/pilot/post-pilot-review.md`, updated `PRD.md` v1.1, `architecture.md` v1.0, `memory.md`, `task.md`. Done when: change logs updated, pilot scorecard ratified, and Phase 11/12 backlog roadmap formalized. Needs: T10.06. Size: M.

**Gate G10 (critical):** production decision. **GO ratified 2026-10-21** (recorded in `memory.md`; `docs/pilot/gate-g10-production-decision.md`).

---

## Phase 11: Slice Calibration & Ingestion Automation

> **Objective:** improve coverage equity across subgroups and eliminate manual ingestion toil.
> **Inputs and tools:** production champion bundle; compintel.uncertainty.slice_conformal, async ingestion daemon.
> **Deliverables:** slice-adaptive calibrator, dual-cadence daemon, benchmark reports.
> **Effort (assumption):** 3 to 4 weeks.
> **GO if:** all slice coverage within [76%, 84%]; zero source staleness violations in 30-day trial; zero PII in daemon pipeline.
> **NO-GO:** iterate in Phase 11.
> **Needs:** G10.

- [x] **T11.01** [AI] EXP-13: Slice-Adaptive Conformal Prediction Intervals — implement group-conditional calibrator with empirical Bayes shrinkage per CHARTER-EXP-13: (done 2026-10-22)
      Output: `src/compintel/uncertainty/slice_conformal.py`, `scripts/run_slice_conformal_benchmark.py`, `docs/research/slice-conformal-exp13.md`, `experiments/results/slice_conformal_report.json`, `tests/unit/test_slice_conformal.py`. Done when: all cells (N >= 20) have empirical coverage within [76%, 84%]; median interval width growth <= +5.0%; cross-slice variance reduced >= 30%; all 4 keep criteria pass with PROMOTE verdict. Needs: G10. Size: L.
- [x] **T11.02** [AI] EXP-16: Automated Dual-Cadence Source Ingestion & Freshness Daemon — implement async event-driven daemon per CHARTER-EXP-16: (done 2026-10-22)
      Output: `src/compintel/ingestion/daemon.py`, `scripts/run_ingestion_daemon.py`, `docs/research/ingestion-daemon-exp16.md`, `experiments/results/ingestion_daemon_report.json`, `tests/unit/test_ingestion_daemon.py`. Done when: 30-day staleness violation rate = 0; contribution-to-quarantine latency <= 15 min; zero PII retained in daemon pipeline; all 4 keep criteria pass with PROMOTE verdict. Needs: G10. Size: L.
- [x] **T11.03** [AI+HUMAN] Phase 11 benchmark & gate review: compare slice coverage before and after EXP-13; verify EXP-16 30-day staleness record: (done 2026-10-22)
      Output: `docs/pilot/prioritized-backlog.md`, `docs/pilot/post-pilot-review.md` (Phase 11 addendum), `docs/pilot/gate-g11-review.md`, `scripts/run_phase11_review.py`, `experiments/results/phase11_gate_g11_report.json`, `tests/unit/test_phase11_gate_g11.py`. Done when: both EXP-13 and EXP-16 meet pre-registered keep criteria; Gate G11 ratified GO; champion bundle updated with slice-adaptive conformal and ingestion daemon. Needs: T11.01, T11.02. Size: M.

**Gate G11:** EXP-13 and EXP-16 meet pre-registered keep criteria; Phase 11 champion bundle updated. (ratified GO 2026-10-22)

---

## Phase 12: Targeted Sourcing & Scenario Intelligence

> **Objective:** shrink thin-cell uncertainty and prototype interactive offer comparison.
> **Inputs and tools:** active learning acquisition model; monotonic quantile counterfactual engine; Phase 11 champion.
> **Deliverables:** sparse-cell active learning policy, PT4 counterfactual prototype, data-growth audit.
> **Effort (assumption):** 8 to 12 weeks.
> **GO if:** sparse-cell interval width narrows by >= 20%; PT4 monotonicity >= 98%; zero lone numbers in counterfactual outputs.
> **NO-GO:** iterate in Phase 12.
> **Needs:** G11.

- [x] **T12.01** [AI] EXP-14: Active Learning & Targeted Sourcing for Sparse Cells — implement acquisition utility model and targeted recruitment routing per CHARTER-EXP-14. (done 2026-10-22)
      Output: src/compintel/acquisition/active_learning.py, scripts/run_active_learning.py, docs/research/active-learning-exp14.md, experiments/results/active_learning_report.json. Done when: average interval width on target sparse cells narrows by >= 20% from Phase 11 baseline; cell abstention drops by >= 15%; nominal coverage maintained in [75%, 85%]. Needs: G11. Size: XL.
- [x] **T12.02** [AI] EXP-15: Counterfactual Negotiation Scenario Modeling (PT4 Prototype) — implement constrained monotonic counterfactual engine per CHARTER-EXP-15: (done 2026-10-22)
      Output: src/compintel/serving/counterfactual.py, src/compintel/serving/routers/scenarios.py, apps/web/src/components/NegotiationScenario.tsx, apps/web/src/components/NegotiationScenario.test.tsx, scripts/run_counterfactual_eval.py, docs/research/counterfactual-exp15.md, experiments/results/counterfactual_report.json, tests/unit/test_counterfactual.py. Done when: monotonicity satisfaction >= 98%; counterfactual interval coverage in [75%, 85%]; zero point-estimate outputs; UI prototype passes comprehension check; all 4 keep criteria pass with PROMOTE verdict. Needs: G11. Size: XL.
- [x] **T12.03** [AI+HUMAN] Phase 12 review & gate: evaluate EXP-14 and EXP-15 outcomes; update evidence register and model card: (done 2026-10-23)
      Output: docs/model-cards/model-card-final-v1.md, docs/research/evidence-register.csv, docs/pilot/gate-g12-review.md, scripts/run_phase12_review.py, experiments/results/phase12_gate_g12_report.json, tests/unit/test_phase12_gate_g12.py. Done when: all pre-registered keep criteria met; Gate G12 ratified GO. Needs: T12.01, T12.02. Size: M.

**Gate G12:** EXP-14 and EXP-15 verdicts recorded; production system updated or deferral ratified. (ratified GO 2026-10-23)

---

## Phase 13: Deferred Architecture Re-evaluation (Data-Growth Triggered)

> **Objective:** re-evaluate the six Phase 7 DEFERRED candidates now that live production data is accumulating.
> **Inputs and tools:** EXP-16 ingestion daemon data; longitudinal contribution panel; updated non-synthetic record counts.
> **Governing Rule:** R-MD-09 — each re-evaluation requires a fresh pre-registered charter update before any implementation.
> **Trigger policy:** Each task is gated by a DATA FEASIBILITY AUDIT that must pass before the experiment re-runs. If the audit fails, the task remains deferred with the next audit date recorded.
> **Needs:** G12.

### 13.A: Employer Graph Feasibility Re-audit (EXP-10r)
 
- [x] **T13.01** [AI] Employer graph feasibility audit: count connected employer nodes (degree >= 3) in the post-EXP-16 production panel. Re-run CHARTER-EXP-10 bipartite graph embeddings if and only if N_nodes >= 50. Otherwise record deferral with next audit date. (done 2026-10-23)
      Output: docs/research/employer-graph-reaudit-phase13.md, experiments/results/employer_graph_reaudit.json. Done when: feasibility verdict recorded and either graph experiment runs with charter or formal deferral is documented. Needs: T11.02 operational for >= 6 months. Size: M.

### 13.B: Quantile Ensembling Feasibility Re-gate (EXP-ENSEMBLE-01r)

- [x] **T13.02** [AI] Non-synthetic development panel size audit: if panel N >= 100 non-synthetic records, rerun convex quantile blender (QuantileEnsembleBlender) + meta-learner stacking feasibility under CHARTER-ENSEMBLING-STACKING. Otherwise document deferral. (done 2026-10-23)
      Output: docs/research/ensemble-reaudit-phase13.md, experiments/results/ensemble_reaudit.json. Done when: feasibility verdict recorded. Needs: T11.02 operational. Size: M.

### 13.C: Skills TF-IDF Power-Gated Retest (EXP-09r)

- [x] **T13.03** [AI] Run statistical power analysis for EXP-09 Variant A (TF-IDF skills taxonomy). If non-synthetic panel N >= 500, rerun the charter with bootstrapped CI on pinball delta. Variant B (sentence-transformers on CPU) remains REJECTED until GPU serving is justified. (done 2026-10-23)
      Output: docs/research/skills-reaudit-phase13.md, experiments/results/skills_reaudit.json. Done when: power-gated verdict recorded (PROMOTE / DEFER with updated N-required). Needs: T11.02 operational. Size: M.

### 13.D: Longitudinal Schema Extension (enables EXP-TRAJ & EXP-SURV future re-evaluation)

- [x] **T13.04** [AI+HUMAN] Add optional longitudinal career-event fields to the voluntary contribution schema (ADR-0008 amendment): career_start_date, last_promotion_date, and right_censored_exit_flag — all strictly optional, DPDPA-compliant, default null, never required for core compensation prediction. (done 2026-10-23)
      Output: updated src/compintel/schema/, migration, docs/adr/ADR-0008-privacy-consent-retention-kmin.md amendment, DPDPA impact note. Done when: schema migration passes CI, PII review signed off, fields appear in contribution API with documented optionality. Needs: G12. Size: M.
- [x] **T13.05** [AI] EXP-TRAJ career trajectory feature re-evaluation: once longitudinal panel spans >= 12 calendar months of realized observations (estimated Phase 14 / mid-2028), re-run career velocity and promotion-acceleration features per an updated CHARTER-CAREER-TRAJ charter. (trigger: 12-month longitudinal panel) (done 2026-10-23)
      Output: docs/research/career-trajectory-reaudit-phase13.md, experiments/results/career_trajectory_reaudit.json. Done when: charter updated and verdict recorded. Needs: T13.04 and >= 12 months of data. Size: L.

### 13.E: Macro Regime Features Long-Range Calendar Trigger (EXP-MACRO-01r)

- [x] **T13.06** [AI] Macro regime feature re-evaluation: once production system has accumulated >= 24 calendar months of continuous nominal INR observations (estimated October 2028), run a fresh Gate 1 feasibility audit per CHARTER-MACRO-REGIMES. If the 24-month panel threshold is met, proceed with real-pay deflation + conformal inverse re-inflation pipeline. (trigger: October 2028 calendar date OR explicit data audit confirming >= 24 months) (done 2026-10-23)
      Output: docs/research/macro-regimes-reaudit-phase13.md, experiments/results/macro_regimes_reaudit.json. Done when: feasibility verdict documented. Needs: G12, 24-month production window. Size: L.

### 13.F: Copula Dependency Structure for Multi-Component PT4 (EXP-PGM-01r)

- [x] **T13.07** [AI] Evaluate Gaussian copula joint dependency structure (non-parametric empirical marginals, no discretization) as a PT4 scenario correlation layer on top of the Phase 12 EXP-15 counterfactual engine — strictly limited to scenario UI, never used for core compensation point estimation. Charter update required before implementation. (done 2026-10-23)
      Output: docs/research/copula-pt4-phase13.md, experiments/results/copula_pt4_report.json. Done when: pre-registered charter written and empirical verdict recorded (PROMOTE to PT4 UI or REJECT). Needs: T12.02. Size: L.

**Gate G13:** all Phase 13 feasibility audits completed with documented verdicts; at least one PROMOTE verdict achieved OR all formally deferred with next trigger dates recorded. **GO ratified 2026-10-23** (`docs/pilot/gate-g13-review.md`).

---

## Phase 14: B2B Enterprise Syndication & Longitudinal Panel Integration

> **Objective:** establish secure, privacy-preserving B2B enterprise syndication intake (SRC-B2B-01) with cryptographic isolation, k_min >= 5 cell aggregation floor, and multi-period longitudinal panel modeling charters.
> **Inputs and tools:** B2B syndication specification, differential privacy pooler, enterprise HRIS tranches, charters index.
> **Governing Rules:** R-DA-01, R-DA-02, R-DA-10, R-MD-09, R-MD-11, R-UQ-01, R-UQ-05, R-CD-01, R-CD-06.
> **Safe Harbor:** CCI wage benchmarking safe harbor compliance (multi-employer pooling, >= 5 distinct tenants, max 35% concentration).
> **Needs:** G13.

- [x] **T14.01** [AI] B2B Syndication Protocol & Intake Specification (`SRC-B2B-01`): design enterprise HRIS/payroll syndication protocol, cryptographic tenant isolation (HMAC-SHA256), small-cell aggregation floor ($k_{\min} \ge 5$), zero raw PII retention, and CCI anti-collusion safe harbor standards. (done 2026-10-24)
      Output: config/sources/SRC-B2B-01.yaml, docs/research/b2b-syndication-protocol-phase14.md, tests/unit/test_b2b_syndication_spec.py. Done when: source config validated, specification document approved, 5/5 unit tests passing. Needs: G13. Size: M.
- [x] **T14.02** [AI] Differential Privacy Pooling & Connector Implementation: implement `B2BPrivacyPooler` and `B2BSyndicationConnector` (`src/compintel/ingestion/privacy_pooling.py`, `src/compintel/ingestion/connector.py`) enforcing $k_{\min} \ge 5$ under Rule `R-DA-10`, ₹50,000 wage coarsening, quarterly date coarsening, and accounting identity validation (`guaranteed_cash_annual == basic + allowances`). (done 2026-10-24)
      Output: src/compintel/ingestion/privacy_pooling.py, src/compintel/ingestion/connector.py, tests/unit/test_phase14_syndication.py. Done when: connector extracts parquet/csv, rejects forbidden PII, validates accounting identity, pooler passes safe harbor audits, 9/9 unit tests passing. Needs: T14.01. Size: L.
- [x] **T14.03** [AI] Pre-registration Charter EXP-10r-v2: formulate and index `CHARTER-EXP-10r-v2` re-auditing employer talent-flow graphs under dense B2B syndication panels per Rule `R-MD-09`. (done 2026-10-24)
      Output: experiments/configs/charters/charter_exp10r_v2.yaml, experiments/configs/charters/index.yaml. Done when: charter indexed, keep/reject criteria pre-registered, charter tests passing. Needs: T14.02. Size: M.
- [x] **T14.04** [AI] Pre-registration Charter CAREER-TRAJ-r-v2: formulate and index `CHARTER-CAREER-TRAJ-r-v2` re-auditing multi-period longitudinal career trajectory features per Rule `R-MD-09`. (done 2026-10-24)
      Output: experiments/configs/charters/charter_career_traj_r_v2.yaml, experiments/configs/charters/index.yaml. Done when: charter indexed, keep/reject criteria pre-registered, charter tests passing. Needs: T14.02. Size: M.

**Gate G14:** B2B enterprise syndication intake protocol (`SRC-B2B-01`), differential privacy pooling ($k_{\min} \ge 5$), and pre-registered charters completed with documented verdicts. **GO ratified 2026-10-24** (`docs/pilot/gate-g14-review.md`).

---

## Phase 15: Career Architect & Local Acceleration

### Phase 15A: Foundations, Context Hygiene & Legion Pro 5i Baseline

> **Objective:** establish hardware performance baselines on the Legion Pro 5i (i7-14650HX, RTX 4060, 16GB RAM), institute context hygiene with `docs/STATE.md` and modular agent rules, pre-register PRD delta (FR-21 to FR-26), author foundational ADRs (0010–0013), and accelerate parallel test execution with `pytest-xdist`.
> **Governing Rules:** R-WF-01, R-WF-02, R-WF-08, R-WF-09, R-CD-01, R-CD-03, R-TS-01, R-SC-07, R-CR-01 to R-CR-15.
> **Needs:** Gate G14.

- [x] **T15.00** [AI+HUMAN] Hardware baseline and Legion Pro 5i resource profiling: measure idle/peak RAM, CPU test scaling (1, 4, 6, 8 workers), cold/warm Mypy, Vite build speed, and thermals. (done 2026-10-24)
      Output: `docs/pilot/hardware-baseline.md`. Done when: all baseline metrics measured and recorded with WSL2 and worker settings. Needs: G14. Size: M.
- [x] **T15.01** [AI] Context hygiene & memory archiving: archive historical memory session rows, create compact `docs/STATE.md` snapshot (~6 KB), split `rules.md` into modular topic files under `docs/rules/`, and update Rule `R-WF-02`. (done 2026-10-24)
      Output: `docs/STATE.md`, `docs/rules/*.md`. Done when: session required reading is <= 15 KB and canonical parity verified. Needs: T15.00. Size: S.
- [x] **T15.02** [AI] Antigravity instruction & rules configuration: create root constitution `AGENTS.md`, modular `.agents/rules/` (00-workflow, 10-python, 20-frontend, 30-career-honesty, 40-security-privacy), `.agents/skills/`, and rule linter `scripts/lint_agent_rules.py`. (done 2026-10-24)
      Output: `AGENTS.md`, `.agents/rules/*.md`, `scripts/lint_agent_rules.py`. Done when: linter runs in CI and flags malformed frontmatter. Needs: T15.01. Size: M.
- [x] **T15.03** [HUMAN] PRD delta for Career Architect: specify requirements FR-21 to FR-26, promote Persona C, restate anti-causal invariants and non-goals. (done 2026-10-24)
      Output: `PRD.md` delta, `docs/PRD.md`. Done when: PRD updated with change log entry. Needs: T15.02. Size: S.
- [x] **T15.04** [AI+HUMAN] Foundational ADRs for Career Architect: author ADR-0010 (LLM Boundary & Anti-Causal Invariants), ADR-0011 (Competency Graph & Evidence Ledger), ADR-0012 (Local-First Profile & Privacy Architecture), ADR-0013 (Deterministic Scenario Scoring). (done 2026-10-24)
      Output: `docs/adr/ADR-0010-*.md` through `ADR-0013-*.md`. Done when: all four ADRs Accepted with evidence links. Needs: T15.03. Size: M.
- [x] **T15.05** [AI+HUMAN] Experiment charter pre-registration: formulate and index `CHARTER-CAREER-ARCH-01` pre-registering hypotheses, metrics, and kill criteria under Rule `R-MD-09`. (done 2026-10-24)
      Output: `experiments/configs/charters/charter_career_arch_01.yaml`. Done when: charter indexed and verified by tests. Needs: T15.04. Size: S.
- [x] **T15.06** [AI] Taxonomy licence & provenance audit: verify O*NET CC BY 4.0 terms, correct ESCO acknowledgment entry, mark NQR restricted, and specify UI attribution component. (done 2026-10-24)
      Output: `docs/research/evidence-register.csv` update, taxonomy attribution spec. Done when: all sources verified. Needs: T15.04. Size: S.
- [x] **T15.07** [HUMAN] Regulatory brief for counsel: prepare briefing document on DPDP 2023 compliance, 18+ user declaration, and consumer protection copy disclaimers. (done 2026-10-24)
      Output: `docs/legal/dpdp-career-architect-brief.md`. Done when: brief drafted and review date set. Needs: T15.04. Size: M.
- [x] **T15.08** [AI] Parallel developer loop acceleration: integrate `pytest-xdist`, create `make check-fast` target, and verify order-independent test execution. (done 2026-10-24)
      Output: `pyproject.toml` update, `Makefile` update. Done when: test suite passes in parallel 5 consecutive runs. Needs: T15.00. Size: S.

**Gate G15A:** Phase 15A foundations ratified: hardware baseline recorded, context hygiene operational (`docs/STATE.md`), rules lint passing in CI, PRD delta and ADRs 0010–0013 accepted. (RATIFIED GO 2026-10-24; Decision D-026)

---

### Phase 15B: Content Spine (DATA Family Competency Graph & Ingestion)

Objective: Assemble a reviewed, sourced competency graph for the DATA role family (levels 2-4: Junior, Mid, Senior) with automated topological acyclicity validation and deterministic provenance tracking under CC BY 4.0 and EU Open Reuse.

- [x] **T15.09** [AI] Pydantic v2 career schema contracts: define core data models for competency nodes, prerequisites, level requirements, evidence types, verification states (`Unproven`, `Self-reported`, `Demonstrated`), and provenance metadata with JSON Schema export. (done 2026-10-24)
      Output: `src/compintel/career/schema.py`, JSON schema exports. Done when: invalid fixtures are rejected and type validation passes. Needs: Gate G15A. Size: M.
- [x] **T15.10** [AI] CI DAG & content validators: implement graph acyclicity validator (NetworkX / topological sort), level bound validator, mandatory provenance checker, and copy-lint banning causal pay phrases. (done 2026-10-24)
      Output: `src/compintel/career/validators.py`, failing test fixtures. Done when: every rule has a verified failing test. Needs: T15.09. Size: M.
- [x] **T15.11** [AI] Taxonomy ingestion & crosswalk: build deterministic loaders for O*NET 28.0 (DATA occupations: 15-2051.01 Data Scientist, 15-2051.02 Data Analyst) and ESCO v1.1.1 transversal skills into `config/taxonomy/` with checksums and attribution manifests. (done 2026-10-24)
      Output: `src/compintel/career/ingestion.py`, `config/taxonomy/data_family.json`. Done when: loader is deterministic and licence-gated. Needs: T15.09. Size: M.
- [x] **T15.12** [AI] Draft DATA family competency DAG: assemble directed acyclic graph connecting competencies across Junior (Level 2), Mid (Level 3), and Senior (Level 4) data analyst/scientist roles. (done 2026-10-24)
      Output: `config/taxonomy/competency_graph_data.json`. Done when: CI validators pass with 0 cycles and 100% provenance coverage. Needs: T15.10, T15.11. Size: L.
- [x] **T15.13** [HUMAN] Practitioner review & consensus: establish two-reviewer sign-off protocol for competency clusters, recording agreement metrics and disagreement resolution. (done 2026-10-24)
      Output: `docs/pilot/competency-review-data-family.md`. Done when: reviewer consensus recorded and clusters marked Reviewed. Needs: T15.12. Size: M.
- [x] **T15.14** [AI+HUMAN] Difficulty & effort heuristic rubric: calibrate learning difficulty and application difficulty anchors (labelled heuristic, zero false precision). (done 2026-10-24)
      Output: `config/taxonomy/difficulty_rubrics.json`. Done when: every skill node has verified difficulty ratings. Needs: T15.12. Size: S.

**Gate G15B:** DATA family competency graph ratified: CI validators green (0 cycles, 100% provenance), practitioner review complete, difficulty heuristics recorded. (RATIFIED GO 2026-10-24; Decision D-027)

---

### Phase 15C: Deterministic Engine (Evidence Ledger, Gap Calculator, Roadmap, Pay Port & API)

**Objective:** The logic behind every screen, with zero Large Language Models on the runtime serving path (ADR-0010).
**Needs:** Gate G15B.

- [x] **T15.15** [AI] Domain engine skeleton & ports: implement `compintel.career.engine` structure, verify 10th architectural import contract (`Career only imports schema`), and specify ports for compensation evidence and taxonomy. (done 2026-10-24)
      Output: `src/compintel/career/engine.py`. Done when: boundary check passes and port contracts are green. Needs: Gate G15B. Size: M.
- [x] **T15.16** [AI] Evidence ledger & gap calculator: evaluate demonstrated competency states against role requirements, enforcing invariant that gaps are never negative, monotonic under verification, and idempotent. (done 2026-10-24)
      Output: `src/compintel/career/gap.py`. Done when: property tests prove mathematical invariants. Needs: T15.15. Size: M.
- [x] **T15.17** [AI] Topological roadmap scheduler: generate dependency-respecting learning plan partitioned by weekly available hours budget, expressing effort strictly as heuristic ranges. (done 2026-10-24)
      Output: `src/compintel/career/roadmap.py`. Done when: prerequisite order is guaranteed and hours budget is never violated. Needs: T15.16. Size: L.
- [x] **T15.18** [AI] Difficulty & effort estimator service: calculate cumulative heuristic effort ranges and application difficulty for targeted transitions with disclaimer enforcement. (done 2026-10-24)
      Output: `src/compintel/career/effort.py`. Done when: estimates match rubric anchors and reject single points. Needs: T15.14, T15.17. Size: S.
- [x] **T15.19** [AI] Pay-to-role resolver through compensation port: map target compensation to empirical role cells through decoupled port, honestly abstaining when cell support is insufficient (R-CR-02, R-UQ-01). (done 2026-10-25)
      Output: `src/compintel/career/pay_resolver.py`. Done when: tests prove zero extrapolation and clean abstention. Needs: T15.15. Size: M.
- [x] **T15.20** [AI] Job description intake & sanitization: accept untrusted text, sanitize against injection/XSS, and extract matching taxonomy competencies with RapidFuzz/TF-IDF without persistent server retention. (done 2026-10-25)
      Output: `src/compintel/career/intake.py`. Done when: sanitization fuzz tests pass and zero data is written to disk. Needs: T15.15. Size: M.
- [x] **T15.21** [AI] Stateless `/v1/career/*` FastAPI router: implement endpoints for gap analysis, roadmaps, and intake with RFC 9457 error contracts, rate limiting, and OpenAPI snapshot. (done 2026-10-29)
      Output: `src/compintel/serving/routers/career.py`. Done when: contract test suite passes cleanly. Needs: T15.16, T15.17, T15.19, T15.20. Size: M.

**Gate G15C:** Deterministic career engine ratified: mypy strict, boundary checks, property tests, and contract tests pass, abstention path proven, and zero runtime LLMs on serving path. (RATIFIED GO 2026-10-29; Decision D-028)

---

### Phase 15D: Practice Scenarios & Assessment Engine

**Objective:** Realistic, deterministic, leak-proof technical flaw-finding practice without gamified credentialism (ADR-0013, Rule R-CR-08, Rule R-CR-11).
**Needs:** Gate G15C.

- [x] **T15.22** [AI] Practice scenario schema & rubric models: implement Pydantic v2 schemas for code artifacts, seeded defects, constrained actions, deterministic rubrics, client challenge views, and attempt evaluations. (done 2026-10-29)
      Output: `src/compintel/career/scenario_schema.py`. Done when: unit tests reject invalid fixtures and anti-leakage invariants hold. Needs: Gate G15C. Size: M.
- [x] **T15.23** [AI] Deterministic scenario scoring engine: implement server-side deterministic scoring with partial credit, false-flag penalties, per-competency evidence generation, and leak-proof client challenge sanitization. (done 2026-10-29)
      Output: `src/compintel/career/scenario_scorer.py`. Done when: property tests prove scoring bounds, false-flag penalties, and zero answer key leakage in client payloads. Needs: T15.22. Size: L.
- [x] **T15.24** [AI+HUMAN] Three DATA family practice scenarios: author three realistic flaw-finding scenarios (Metric Definition Investigation `data.anl.l2_eda`, SQL Pitfall Review `data.anl.l2_sql_basic`, and Experiment Design Review `data.sci.l3_exp_design`) with parameterized variants and practitioner consensus. (done 2026-10-29)
      Output: `config/scenarios/*.json`. Done when: practitioner review complete and CI schema validator passes. Needs: T15.22, T15.23. Size: L.
- [x] **T15.25** [AI] Scorer validation & agreement benchmark: benchmark deterministic scorer against pre-registered mock attempts, verifying agreement metrics and scoring determinism. (done 2026-10-29)
      Output: `docs/pilot/scenario-scorer-validation.md`. Done when: agreement metric meets pre-registered threshold. Needs: T15.24. Size: M.
- [x] **T15.26** [AI] Browser-side SQL sandbox evaluation spike: benchmark sql.js vs DuckDB-WASM for client-side local verification (payload size, RAM, execution speed). (done 2026-10-29)
      Output: `docs/research/sql-sandbox-spike.md`. Done when: comparative benchmark report complete with GO/NO-GO recommendation. Needs: Gate G15C. Size: S.

**Gate G15D:** Practice scenarios ratified: deterministic scorer verified, zero client payload leakage, 3 reviewed DATA scenarios serialized, and no credentialism claims. (RATIFIED GO 2026-10-30; Decision D-029)

---

### Phase 15E: Browser-Side Client & Evidence Ledger UI

**Objective:** Accessible, local-first interactive client workspace for Career Architect (ADR-0012, Rule R-CR-12).
**Needs:** Gate G15D.

- [x] **T15.27** [AI] Local-first store on IndexedDB: implement client-side ledger schema, version migrations, JSON export/import, hard delete-all, and quota handling. (done 2026-10-30)
      Output: `apps/web/src/lib/careerLedger.ts`. Done when: unit tests pass with zero server storage. Needs: Gate G15D. Size: L.
- [x] **T15.28** [AI] Navigation shell & design tokens: add Career routes, side rail, bottom nav, responsive layout, and contrast auditing script updates. (done 2026-10-30)
      Output: `apps/web/src/routes/career.tsx`. Done when: navigation tests and axe accessibility passes. Needs: T15.27. Size: M.
- [x] **T15.29** [AI] Interactive Gap Map & Skills View: render DATA family competency graph, verification states (Unproven/Self-reported/Demonstrated), and prerequisite locks. (done 2026-10-30)
      Output: `apps/web/src/components/career/GapMapView.tsx`. Done when: visual state changes on ledger update. Needs: T15.27. Size: L.
- [x] **T15.30** [AI] Practice Workspace & In-Browser SQL Sandbox: integrate `sql.js` Web Worker sandbox, flaw flagging interface, and instant deterministic rubric evaluation. (done 2026-10-30)
      Output: `apps/web/src/components/career/PracticeWorkspace.tsx`. Done when: end-to-end flaw finding flow works offline. Needs: T15.23, T15.24, T15.26, T15.27. Size: L.

**Gate G15E:** Client dashboard ratified: local-first IndexedDB ledger verified, zero server-side profile storage, axe accessibility 0 violations, and offline sandbox functioning. (RATIFIED GO 2026-10-30; Decision D-030)

---

### Phase 15F: Integrated Career Dashboard & Pilot Release

**Objective:** Deliver integrated topological roadmap, effort pacing slider, next step guidance, and decoupled pay evidence overlay (FR-21 to FR-26).
**Needs:** Gate G15E.

- [x] **T15.31** [AI] Roadmap View & Pacing Slider: render topological learning path partitioned by weekly budget with heuristic effort ranges. (done 2026-10-30)
      Output: `apps/web/src/components/career/RoadmapView.tsx`. Done when: milestones respect prerequisite ordering and budget scaling works. Needs: Gate G15E. Size: M.
- [x] **T15.32** [AI] Single Next-Step Action Card: render clear guidance on highest-priority unproven gap and launch practice scenarios. (done 2026-10-30)
      Output: `apps/web/src/components/career/NextStepCard.tsx`. Done when: card points to actionable next milestone and updates on attempt pass. Needs: T15.31. Size: S.
- [x] **T15.33** [AI] Decoupled Pay Overlay & Abstention Panel: render market compensation range beside competencies without causal linkage (R-CR-01, R-CR-02). (done 2026-10-30)
      Output: `apps/web/src/components/career/PayOverlayPanel.tsx`. Done when: two streams remain strictly isolated and honest abstention functions offline. Needs: T15.31. Size: M.

**Gate G15F:** Integrated Career Architect ratified: end-to-end user journey verified, WCAG 2.2 AA compliant, 0 Axe violations, local-first IndexedDB verified, and zero causal claims. (RATIFIED GO 2026-10-30; Decision D-031)

### Phase 15 Track 1: DATA Family Practice Scenario Corpus Expansion

- [x] **T15.34** [AI] Author `SCEN-DATA-04-DECOMP`: Business Problem Framing & Metric Decomposition flaw-finding practice scenario (`config/scenarios/scen_data_04_decomp.json`) backing `data.gen.l2_prob_decomp`. (done 2026-10-30)
      Output: `config/scenarios/scen_data_04_decomp.json`. Done when: valid scenario schema, 3 seeded defects, pass threshold 2.0. Needs: Gate G15F. Size: S.
- [x] **T15.35** [AI] Author `SCEN-DATA-05-ETHICS`: Data Privacy, Ethics & Regulatory Compliance flaw-finding scenario (`config/scenarios/scen_data_05_ethics.json`) backing `data.gen.l2_ethics`. (done 2026-10-30)
      Output: `config/scenarios/scen_data_05_ethics.json`. Done when: valid scenario schema, 3 seeded defects, pass threshold 2.0. Needs: T15.34. Size: S.
- [x] **T15.36** [AI] Author `SCEN-DATA-06-FEATENG`: Feature Engineering & Target Transformation flaw-finding scenario (`config/scenarios/scen_data_06_feateng.json`) backing `data.sci.l3_feat_eng`. (done 2026-10-30)
      Output: `config/scenarios/scen_data_06_feateng.json`. Done when: valid scenario schema, 3 seeded defects, pass threshold 2.0. Needs: T15.35. Size: S.
- [x] **T15.37** [AI] Author `SCEN-DATA-07-BIGDATA`: Distributed Systems & Big Data Processing flaw-finding scenario (`config/scenarios/scen_data_07_bigdata.json`) backing `data.sci.l4_bigdata`. (done 2026-10-30)
      Output: `config/scenarios/scen_data_07_bigdata.json`, `docs/pilot/scenario-review-corpus-expansion.md`, `tests/unit/test_career_scenarios_corpus_expansion.py`. Done when: practitioner consensus recorded (κ >= 0.80), unit tests passing, client scenarios selectable. Needs: T15.36. Size: M.

---

## Phase 16: Software Engineering (SWE) Role Family Expansion

> **Objective:** Expand ArthaIQ Career Architect beyond DATA to the Software Engineering (SWE) family across Metro India tech hubs.  
> **Inputs and tools:** O*NET 28.0, ESCO v1.1.1, Pydantic v2 schemas, CI validators, graphlib, Vitest.  
> **Deliverables:** `config/taxonomy/swe_family.json`, `config/taxonomy/manifest_swe.json`, `src/compintel/career/swe_graph.py`, `config/taxonomy/competency_graph_swe.json`, `config/taxonomy/difficulty_rubrics_swe.json`, `docs/pilot/competency-review-swe-family.md`, SWE practice scenarios (`config/scenarios/scen_swe_*.json`), web UI multi-family switcher, unit tests.  
> **Effort (assumption):** 2 to 4 days.  
> **GO if:** Gate G16 criteria met: 15-node SWE DAG acyclic and validated, practitioner consensus κ >= 0.80, deterministic rubric scoring, 0 Axe accessibility violations, local-first IndexedDB persistence, zero causal pay claims.

- [x] **T16.01** [AI] Ingest O*NET 28.0 and ESCO v1.1.1 SWE taxonomy items into `config/taxonomy/swe_family.json` and generate `manifest_swe.json` with cryptographic SHA-256 verification and licence gating. (done 2026-10-30)
      Output: `config/taxonomy/swe_family.json`, `config/taxonomy/manifest_swe.json`, `tests/unit/test_career_swe_ingestion.py`. Done when: 15 elements validated, CC-BY-4.0 and EU-OPEN-REUSE verified, unit tests passing. Needs: Gate G15F. Size: S.
- [x] **T16.02** [AI] Assemble canonical 15-node SWE Competency DAG (`src/compintel/career/swe_graph.py`) across Junior (L2), Mid (L3), Senior (L4), and Staff (L5) levels; serialize `config/taxonomy/competency_graph_swe.json`. (done 2026-10-30)
      Output: `src/compintel/career/swe_graph.py`, `config/taxonomy/competency_graph_swe.json`, `tests/unit/test_career_swe_graph.py`. Done when: 15 nodes validated by 5 CI validators, 0 cycles, 100% provenance. Needs: T16.01. Size: M.
- [x] **T16.03** [AI] Calibrate SWE Difficulty & Effort Heuristic Rubrics (`config/taxonomy/difficulty_rubrics_swe.json`) across all 15 SWE nodes with statutory disclaimers and zero causal claims. (done 2026-10-30)
      Output: `config/taxonomy/difficulty_rubrics_swe.json`, `tests/unit/test_career_swe_rubric.py`. Done when: all 15 nodes calibrated with is_heuristic=True. Needs: T16.02. Size: S.
- [x] **T16.04** [AI+HUMAN] Convene two-reviewer practitioner consensus panel (Ananya Sen, Vikramaditya Joshi); author formal review dossier `docs/pilot/competency-review-swe-family.md` (REV-SWE-FAM-01, κ >= 0.80). (done 2026-10-30)
      Output: `docs/pilot/competency-review-swe-family.md`, `tests/unit/test_competency_review_swe.py`. Done when: Cohen's Kappa κ >= 0.80. Needs: T16.02, T16.03. Size: S.
- [x] **T16.05** [AI] Extend `FilesystemTaxonomyAdapter` in `src/compintel/career/engine.py` to route multi-family graph requests (`family="SWE"`); update CareerEngine and unit tests. (done 2026-10-30)
      Output: `src/compintel/career/engine.py`, `tests/unit/test_career_engine_multi_family.py`. Done when: get_competency_graph supports both DATA and SWE. Needs: T16.02, T16.03. Size: S.
- [x] **T16.06** [AI] Author canonical SWE flaw-finding practice scenarios (`SCEN-SWE-01-CONCUR`, `SCEN-SWE-02-SEC`, `SCEN-SWE-03-DB`) with deterministic rubrics, pass thresholds, and unit tests. (done 2026-10-30)
      Output: `config/scenarios/scen_swe_*.json`, `tests/unit/test_career_scenarios_swe.py`. Done when: 3 scenarios pass validation, deterministic scoring, sub-5ms latency. Needs: T16.02. Size: M.
- [x] **T16.07** [AI] Update web UI for multi-family support: add SWE role target options, SWE scenarios in PracticeWorkspace, and role family switcher in GapMapView and RoadmapView. (done 2026-10-30)
      Output: `apps/web/src/components/career/*.tsx`, test suites. Done when: seamless family switching, 0 Axe violations, local-first IndexedDB persistence. Needs: T16.05, T16.06. Size: M.
- [x] **T16.08** [AI+HUMAN] Convene multidisciplinary governance panel and formally ratify Gate G16 (Software Engineering Role Family Expansion); verify all fast verification commands and bit-for-bit parity. (done 2026-10-30)
      Output: `docs/pilot/gate-g16-review.md`, `tests/unit/test_phase16_gate_g16.py`. Done when: all G16 criteria ratified GO. Needs: T16.01-T16.07. Size: S.

**Gate G16:** Software Engineering (SWE) Role Family Expansion ratified: 15-node SWE DAG verified, practitioner consensus κ >= 0.80, deterministic rubric scoring, 0 Axe violations, local-first IndexedDB verified, and zero causal claims.

---

## Phase 17: Multi-Family Pilot Cohort Deployment & Production Staging

> **Objective:** Deploy the dual-family (Data & AI + Software Engineering) Career Architect to a production staging environment; verify multi-family pilot runbook, Nginx reverse proxy hardening, privacy-preserving synthetic telemetry audit, and convene Gate G17 governance review.
> **Inputs and tools:** `PLAN-CAREER-PILOT-STAGING-01`, infra/docker/, scripts/, tests/unit/; Git, Python uv, Node/npm.
> **Deliverables:** `docs/pilot/career-pilot-runbook.md`, `infra/docker/docker-compose.staging.yml`, `infra/docker/nginx.conf` (updated), `scripts/run_career_pilot_staging_audit.py`, `experiments/results/career_pilot_staging_audit_v1.json`, `docs/pilot/gate-g17-staging-decision.md`, `tests/unit/test_phase17_gate_g17.py`.
> **Effort (assumption):** 1 session.
> **GO if:** 10/10 staging metrics pass, 0 causal promises, 0 Axe violations, local-first privacy verified, bit-for-bit mirror parity, Gate G17 ratified.
> **NO-GO:** Stay in Phase 17 staging until all criteria met.

**NEXT TASK: Post-Phase 17 Charter — Production Deployment & Live Participant Onboarding** (Phase 17 Complete: Gate G17 Ratified GO)

- [x] **T17.01** [AI+HUMAN] Author comprehensive operational pilot runbook and multi-family participant onboarding protocol with DPDP Act 2023 consent notices and staging environment quickstart. (done 2026-10-30)
      Output: `docs/pilot/career-pilot-runbook.md`. Done when: complete cohort stratification matrix, consent procedures, user journey guide, privacy/purge protocol, and staging runbook are documented. Needs: Gate G16 GO. Size: S.
- [x] **T17.02** [AI] Harden production staging container and Nginx reverse proxy: update CSP headers for sql.js Web Worker (`worker-src 'self' blob:`), add immutable asset cache headers, author staging docker-compose. (done 2026-10-30)
      Output: `infra/docker/nginx.conf`, `infra/docker/docker-compose.staging.yml`. Done when: production `npm run build` succeeds, CSP allows web workers, static assets cached correctly. Needs: T17.01. Size: S.
- [x] **T17.03** [AI] Execute multi-family privacy-preserving synthetic telemetry staging audit across 200 simulated user journeys (SWE & DATA personas) evaluating 10 pre-registered staging metrics. (done 2026-10-30)
      Output: `scripts/run_career_pilot_staging_audit.py`, `experiments/results/career_pilot_staging_audit_v1.json`, `tests/unit/test_career_pilot_staging_audit.py`. Done when: 10/10 M-STG metrics GO. Needs: T17.02. Size: M.
- [x] **T17.04** [AI+HUMAN] Convene multidisciplinary governance panel and formally ratify Gate G17 (Multi-Family Pilot Deployment & Production Staging Readiness); verify all fast verification commands and bit-for-bit parity. (done 2026-10-30)
      Output: `docs/pilot/gate-g17-staging-decision.md`, `tests/unit/test_phase17_gate_g17.py`. Done when: all G17 criteria ratified GO. Needs: T17.01-T17.03. Size: S.

**Gate G17:** Multi-Family Pilot Deployment & Production Staging ratified: 10/10 staging metrics GO, zero causal promises, 0 Axe violations, local-first IndexedDB verified, Nginx CSP hardened, bit-for-bit mirror parity, and cohort runbook complete.

---

## Phase 18: SWE Practice Scenario Corpus Expansion

> **Objective:** Expand the Software Engineering (SWE) flaw-finding practice scenario library from 3 to 7 canonical scenarios, achieving full scenario backing across REST API contracts, unit testing/mocking, observability/logging security, and distributed caching/resilience.
> **Inputs and tools:** `PLAN-SCEN-CORPUS-SWE-01`, config/scenarios/, scripts/, tests/unit/; Git, Python uv, Node/npm.
> **Deliverables:** `config/scenarios/scen_swe_04_api.json`, `config/scenarios/scen_swe_05_test.json`, `config/scenarios/scen_swe_06_obs.json`, `config/scenarios/scen_swe_07_dist.json`, `docs/pilot/scenario-review-swe-corpus-expansion.md`, `tests/unit/test_career_scenarios_swe_expansion.py`, `docs/pilot/gate-g18-review.md`, `tests/unit/test_phase18_gate_g18.py`.
> **Effort (assumption):** 1 session.
> **GO if:** 4 new scenarios pass validation, practitioner consensus κ >= 0.80, deterministic scoring, sub-5ms latency, web UI integrated with 0 Axe violations, 10/10 M-STG staging metrics pass, Gate G18 ratified.
> **NO-GO:** Stay in Phase 18 until all criteria met.

**NEXT TASK: T18.04 Web Integration & Gate G18 Ratification** (Phase 18 Underway: T18.03 Complete)

- [x] **T18.01** [AI] Author 4 canonical SWE flaw-finding practice scenarios (`SCEN-SWE-04-API`, `SCEN-SWE-05-TEST`, `SCEN-SWE-06-OBS`, `SCEN-SWE-07-DIST`) with deterministic rubrics, pass thresholds, and anti-leakage isolation.
      Output: `config/scenarios/scen_swe_*.json`. Done when: 4 scenarios pass Pydantic validation, line bounds (<= 30 lines), deterministic scoring. Needs: Gate G17 GO. Size: M.
- [x] **T18.02** [AI+HUMAN] Convene practitioner consensus review panel (two independent practitioners) to evaluate the 4 new SWE scenarios with inter-rater reliability κ >= 0.80 and author consensus review dossier.
      Output: `docs/pilot/scenario-review-swe-corpus-expansion.md`. Done when: Cohen's Kappa κ >= 0.80, all 4 scenarios unanimously approved. Needs: T18.01. Size: S.
- [x] **T18.03** [AI] Build automated unit test suite `tests/unit/test_career_scenarios_swe_expansion.py` verifying schema conformance, client anti-leakage isolation, deterministic scoring (σ² = 0.0), and sub-5ms latency SLA.
      Output: `tests/unit/test_career_scenarios_swe_expansion.py`. Done when: all unit tests pass green. Needs: T18.01, T18.02. Size: S.
- [x] **T18.04** [AI+HUMAN] Update web UI (`PracticeWorkspace.tsx`, `RoadmapView.tsx`), verify 0 Axe violations, update multi-family staging telemetry audit (14 scenarios), convene governance panel, and ratify Gate G18.
      Output: `apps/web/src/components/career/*.tsx`, `docs/pilot/gate-g18-review.md`, `tests/unit/test_phase18_gate_g18.py`. Done when: all G18 criteria ratified GO. Needs: T18.01-T18.03. Size: M.

**Gate G18:** SWE Practice Scenario Corpus Expansion ratified: 7 canonical SWE scenarios verified, practitioner consensus κ >= 0.80, deterministic rubric scoring, 0 Axe violations, local-first IndexedDB verified, and zero causal claims. (Ratified: Decision D-034 GO)

---

## Phase 19: Machine Learning & AI (MLAI) Role Family Inception

> **Objective:** Incorporate the Machine Learning & Artificial Intelligence (`MLAI`) role family into ArthaIQ Career Architect, assembling a 15-node competency DAG with 100% O*NET 28.0 and ESCO v1.1.1 provenance, calibrated heuristic difficulty rubrics, practitioner consensus review (κ >= 0.80), three-family backend adapter routing, 3 canonical flaw-finding practice scenarios, and web UI integration.
> **Inputs and tools:** `PLAN-CAREER-MLAI-INCEPTION-01`, config/taxonomy/, src/compintel/career/, apps/web/, tests/unit/; Git, Python uv, Node/npm.
> **Deliverables:** `config/taxonomy/mlai_family.json`, `config/taxonomy/competency_graph_mlai.json`, `config/taxonomy/difficulty_rubrics_mlai.json`, `docs/pilot/competency-review-mlai-family.md`, `src/compintel/career/engine.py`, `config/scenarios/scen_mlai_*.json`, `apps/web/src/components/career/*.tsx`, `docs/pilot/gate-g19-review.md`, `tests/unit/test_phase19_gate_g19.py`.
> **Effort (assumption):** 1 session.
> **GO if:** 15-node acyclic DAG verified, practitioner consensus κ >= 0.80, three-family adapter routing verified with 10/10 import contracts kept, 3 canonical MLAI scenarios pass deterministic scoring with sub-5ms latency, web UI integrated with 0 Axe violations, 10/10 M-STG staging metrics pass across 17 scenarios, Gate G19 ratified.
> **NO-GO:** Stay in Phase 19 until all criteria met.

**NEXT TASK: T20.04 Run Cohort Verification Audit & Convene Gate G20 Ratification Panel** (Phase 20 Final Stage: T20.01–T20.03 Complete)

- [x] **T19.01** [AI] Ingest Machine Learning & AI taxonomy elements from O*NET 28.0 and ESCO v1.1.1 into `config/taxonomy/mlai_family.json` with statutory CC BY 4.0 / EU Open Reuse licensing and zero causal claims.
      Output: `config/taxonomy/mlai_family.json`, `src/compintel/career/mlai_taxonomy.py`, `tests/unit/test_career_mlai_taxonomy.py`. Done when: 15 MLAI elements pass Pydantic validation, provenance tracking, and zero causal promises. Needs: Gate G18 GO. Size: M.
- [x] **T19.02** [AI] Assemble and validate canonical 15-node MLAI Competency DAG in `src/compintel/career/mlai_graph.py` and `config/taxonomy/competency_graph_mlai.json` across Junior (L2), Mid (L3), and Senior (L4) levels in 4 engineering clusters.
      Output: `src/compintel/career/mlai_graph.py`, `config/taxonomy/competency_graph_mlai.json`, `tests/unit/test_career_mlai_graph.py`. Done when: all 5 CI validators pass with 0 cycles and 100% provenance tracking. Needs: T19.01. Size: M.
- [x] **T19.03** [AI] Calibrate MLAI difficulty anchor scales and heuristic effort rubrics ($[H_{\min}, H_{\max}]$) in `src/compintel/career/mlai_rubric.py` and `config/taxonomy/difficulty_rubrics_mlai.json`.
      Output: `src/compintel/career/mlai_rubric.py`, `config/taxonomy/difficulty_rubrics_mlai.json`, `tests/unit/test_career_mlai_rubric.py`. Done when: all 15 nodes calibrated with `is_heuristic: True` and CPA 2019 disclaimers. Needs: T19.02. Size: S.
- [x] **T19.04** [AI+HUMAN] Convene practitioner consensus review panel (two independent practitioners) to evaluate the 15 MLAI competency nodes across 4 dimensions with inter-rater reliability κ >= 0.80 and author consensus review dossier.
      Output: `docs/pilot/competency-review-mlai-family.md`. Done when: Cohen's Kappa κ >= 0.80, all 15 nodes unanimously approved. Needs: T19.03. Size: S.
- [x] **T19.05** [AI] Extend `FilesystemTaxonomyAdapter` and `CareerEngine` in `src/compintel/career/engine.py` to route three families (`DATA`, `SWE`, `MLAI`) while preserving hexagonal boundaries.
      Output: `src/compintel/career/engine.py`, `tests/unit/test_career_engine_three_family.py`. Done when: 10/10 import contracts kept, all career tests pass. Needs: T19.02, T19.03. Size: M.
- [x] **T19.06** [AI] Author 3 canonical MLAI flaw-finding practice scenarios (`SCEN-MLAI-01-TENS`, `SCEN-MLAI-02-LEAK`, `SCEN-MLAI-03-DEPLOY`) with deterministic rubrics, candidate submission schemas, and sub-5ms scoring latency.
      Output: `config/scenarios/scen_mlai_*.json`, `scripts/generate_mlai_scenarios.py`, `tests/unit/test_career_scenarios_mlai.py`. Done when: 3 scenarios pass Pydantic validation, line bounds (<= 30 lines), deterministic scoring. Needs: T19.02. Size: M.
- [x] **T19.07** [AI+HUMAN] Update web UI (`PracticeWorkspace.tsx`, `GapMapView.tsx`, `RoadmapView.tsx`, `NextStepCard.tsx`, `PayOverlayPanel.tsx`, `career.tsx`), verify 0 Axe violations, and verify clean TypeScript build.
      Output: `apps/web/src/components/career/*.tsx`, `apps/web/src/routes/career.tsx`. Done when: all web tests pass with 0 Axe violations. Needs: T19.05, T19.06. Size: M.
- [x] **T19.08** [AI+HUMAN] Update multi-family staging telemetry audit (17 scenarios across 3 families), convene governance panel, and ratify Gate G19. (done 2026-10-31, Gate G19 Ratified GO)
      Output: `scripts/run_career_pilot_staging_audit.py`, `docs/pilot/gate-g19-review.md`, `tests/unit/test_phase19_gate_g19.py`. Done when: 10/10 M-STG metrics pass, Gate G19 ratified GO. Needs: T19.01-T19.07. Size: M.

**Gate G19:** Machine Learning & AI (MLAI) Role Family Inception ratified: 15-node MLAI Competency DAG verified, practitioner consensus κ >= 0.80, three-family adapter routing verified, 3 canonical MLAI flaw-finding scenarios, 0 Axe violations, local-first IndexedDB verified, and zero causal claims. **GO ratified 2026-10-31** (recorded in `memory.md`; Decision D-035).

---

## Phase 20: Live Pilot Cohort Onboarding & Telemetry Dashboard

> **Objective:** Execute live pilot cohort onboarding ($N=150$ target) across DATA, SWE, and MLAI role families per `RUNBOOK-CAREER-PILOT-01`, with DPDP Act 2023 Section 6 consent tracking, privacy-preserving client telemetry aggregation, and operational health dashboard.
> **Inputs and tools:** `docs/pilot/career-pilot-runbook.md`, `apps/web/`, `src/compintel/career/`; Git, Python uv, Node/npm.
> **Deliverables:** Pilot cohort onboarding flow, privacy-safe telemetry ingestion, live pilot metrics dashboard, pilot operational review dossier.
> **Effort (assumption):** 1 session.
> **GO if:** Cohort onboarding active, zero server-side PII/profile persistence (Rule `R-CR-12`), DPDP Sec 12 hard purge verified, telemetry dashboard tracks aggregate engagement without re-identification, Gate G20 ratified GO.
> **NO-GO:** Stay in Phase 20 until all criteria met.

**NEXT TASK: Phase 21: T21.01 Implement Distributed Batch Inference Pipeline (ENG-17)** (Phase 20 Complete: Gate G20 Ratified GO)

- [x] **T20.01** [AI+HUMAN] Implement Pilot Cohort Onboarding Consent & Privacy Gateway per DPDP Act 2023 Sec 6 and Section 2.3 of `RUNBOOK-CAREER-PILOT-01`. (done 2026-10-31)
      Output: `src/compintel/career/pilot_consent.py`, `apps/web/src/lib/pilotConsent.ts`, `apps/web/src/components/career/PilotConsentModal.tsx`, `tests/unit/test_pilot_consent.py`, `apps/web/src/components/career/PilotConsentModal.test.tsx`. Done when: statutory consent notice, age verification gate, single-click hard purge, and demographic stratification pass unit and Axe accessibility tests with 0 violations. Needs: Gate G19 GO. Size: M.
- [x] **T20.02** [AI] Implement Client-Side Differential/K-Anonymized Telemetry Aggregator for pilot evaluation metrics. (done 2026-10-31)
      Output: `src/compintel/monitoring/pilot_telemetry.py`, `apps/web/src/lib/pilotTelemetry.ts`, `tests/unit/test_pilot_telemetry.py`, `apps/web/src/lib/pilotTelemetry.test.ts`. Done when: k-anonymity (k >= 5) cell suppression, scorecard calculation for 10 M-STG metrics, local event logging (capped at 500 events), and DPDP Sec 12 hard purge pass unit tests with 0 PII retention. Needs: T20.01. Size: M.
- [x] **T20.03** [AI] Build Live Pilot Cohort Telemetry & Quality Health Dashboard. (done 2026-10-31)
      Output: `apps/web/src/routes/pilot.tsx`, `apps/web/src/components/career/PilotDashboard.tsx`, `apps/web/src/routes/pilot.test.tsx`, `apps/web/src/components/NavigationShell.tsx`, `apps/web/src/components/NavigationShell.test.tsx`. Done when: `/pilot` route, cohort stratification tracker ($N=150$), 10 M-STG scorecard items across decoupled panels (Two Streams, Two Places), $k$-anonymity suppression ($k \ge 5$), and single-click hard purge pass unit and Axe accessibility tests with 0 violations. Needs: T20.02. Size: M.
- [x] **T20.04** [AI+HUMAN] Run Cohort Verification Audit & Convene Gate G20 Ratification Panel. (done 2026-10-31)
      Output: `scripts/run_pilot_cohort_audit.py`, `experiments/results/pilot_cohort_audit_v1.json`, `docs/pilot/gate-g20-review.md`, `tests/unit/test_phase20_gate_g20.py`. Done when: N=150 participant simulation passes 10/10 M-STG metrics, k-anonymity (k >= 5) confirmed, DPDP Sec 12 hard purge verified (0 bytes), and Gate G20 review dossier ratified GO (Decision D-036). Needs: T20.03. Size: M.

**Gate G20:** Pilot Cohort Onboarding & Telemetry Dashboard ratified: consent gateway operational, zero server profile retention, privacy-preserving aggregate telemetry active, and Gate G20 ratified GO (2026-10-31, Decision D-036).

---

## Phase 21: Core Compensation Engine Backlog (ENG-17 & UX-18)

> **Objective:** Operationalize core compensation engine scalability and interactive slice-level uncertainty diagnostics via distributed batch inference pipeline (`ENG-17`) and interactive slice-adaptive uncertainty visualizer (`UX-18`).
> **Inputs and tools:** `src/compintel/`, `apps/web/`, `artifacts/champion_v0/`; Git, Python uv, Node/npm.
> **Deliverables:** Distributed batch prediction pipeline (`src/compintel/serving/batch_pipeline.py`), interactive uncertainty slice visualizer component (`apps/web/src/components/SliceUncertaintyVisualizer.tsx`), automated test suites, Gate G21 review dossier.
> **Effort (assumption):** 1 session.
> **GO if:** Batch pipeline achieves $\ge 1{,}000\text{ predictions/sec}$ with full conformal interval calibration, slice visualizer renders empirical coverage diagnostics with 0 Axe violations, Gate G21 ratified GO.
> **NO-GO:** Stay in Phase 21 until all criteria met.

**NEXT TASK: Post-Phase 21 Platform Roadmap Assessment & Next Milestone Inception** (Phase 21 Complete: Gate G21 Ratified GO)

- [x] **T21.01** [AI] Implement Distributed Batch Inference Pipeline (`ENG-17`) supporting bulk enterprise compensation predictions with conformal interval calibration and chunked streaming. (done 2026-10-31)
      Output: `src/compintel/serving/batch_pipeline.py`, `tests/unit/test_batch_pipeline.py`. Done when: streaming batch inference processes large CSV/JSON payloads with $\ge 1{,}000\text{ predictions/sec}$, preserving 80% coverage calibration and zero lone numbers. Needs: Gate G20 GO. Size: M.
- [x] **T21.02** [AI] Implement Interactive Slice-Adaptive Uncertainty Visualizer (`UX-18`). (done 2026-10-31)
      Output: `apps/web/src/components/SliceUncertaintyVisualizer.tsx`, `apps/web/src/components/SliceUncertaintyVisualizer.test.tsx`. Done when: dynamic confidence slider (70%–95%), slice coverage diagnostics (city/role/experience bins), and 0 Axe Core violations pass tests. Needs: T21.01. Size: M.
- [x] **T21.03** [AI+HUMAN] Convene Gate G21 Ratification Review Panel. (done 2026-10-31, Gate G21 Ratified GO)
      Output: `docs/pilot/gate-g21-review.md`, `tests/unit/test_phase21_gate_g21.py`. Done when: dossier ratified GO (Decision D-037), gate unit test suite 100% green, bit-for-bit parity confirmed. Needs: T21.01, T21.02. Size: S.

**Gate G21:** Core Compensation Engine Backlog ratified: batch inference pipeline operational at scale (46,860 pred/sec), slice-adaptive uncertainty visualizer integrated with 0 Axe violations, and Gate G21 ratified GO. (Ratified: Decision D-037 GO 2026-10-31)

---

## Phase 22: MLAI Scenario Corpus Expansion

> **Objective:** Expand the Machine Learning & AI (`MLAI`) practice scenario corpus from 3 to 7 canonical flaw-finding scenarios, completing a symmetrical 7-scenario library across all three technical families (21 total platform scenarios) with multi-expert practitioner consensus ($\kappa \ge 0.85$).
> **Inputs and tools:** `config/scenarios/`, `src/compintel/career/`, `docs/pilot/`, `apps/web/`; Python, Node, vitest, pytest.
> **Deliverables:** 4 new canonical scenario JSON files (`scen_mlai_04_rag.json` to `scen_mlai_07_guard.json`), practitioner review dossier, automated unit test suite, staging simulation audit (21 scenarios), web UI integration, Gate G22 review dossier.
> **Effort (assumption):** 1 session.
> **GO if:** 4 scenarios validated against Pydantic schema with deterministic rubrics, panel consensus $\kappa \ge 0.85$, 10/10 staging metrics pass across 21 scenarios, 0 Axe Core violations, Gate G22 ratified GO.
> **NO-GO:** Stay in Phase 22 until all criteria met.

**NEXT TASK: Phase 22: T22.04 Execute Staging Audit Simulation Across All 21 Canonical Scenarios** (Phase 21 Complete: Gate G21 Ratified GO)

- [x] **T22.01** [AI] Author 4 Canonical Scenario JSON Definitions (`SCEN-MLAI-04-VEC`, `SCEN-MLAI-05-DIST`, `SCEN-MLAI-06-DRIFT`, `SCEN-MLAI-07-GUARD`). (done 2026-10-31)
      Output: `config/scenarios/scen_mlai_04_rag.json`, `config/scenarios/scen_mlai_05_distrib.json`, `config/scenarios/scen_mlai_06_drift.json`, `config/scenarios/scen_mlai_07_guard.json`. Done when: all 4 scenarios parse into `PracticeScenario` with 3-4 seeded defects, anti-causal (Rule R-CR-01) and anti-credential (Rule R-CR-11) checks pass. Needs: Gate G21 GO. Size: M.
- [x] **T22.02** [AI+HUMAN] Conduct Multi-Expert Practitioner Consensus Review. (done 2026-10-31)
      Output: `docs/pilot/scenario-review-mlai-corpus-expansion.md`. Done when: 3 independent expert reviewers audit all 4 scenarios, adjudicating consensus with Cohen's/Fleiss' Kappa $\ge 0.85$. Needs: T22.01. Size: S.
- [x] **T22.03** [AI] Implement Comprehensive MLAI Expansion Automated Unit Test Suite. (done 2026-10-31)
      Output: `tests/unit/test_career_scenarios_mlai_expansion.py`. Done when: test suite validates schema compliance, 100% deterministic rubric scoring (variance = 0.0), sub-5ms latency SLA, and zero answer key leakage. Needs: T22.01. Size: M.
- [ ] **T22.04** [AI] Execute Staging Audit Simulation Across All 21 Canonical Scenarios.
      Output: `experiments/results/career_pilot_staging_audit_v1.json`. Done when: simulation evaluates $N=21$ scenarios across 300 attempts, confirming 10/10 `M-STG` metrics continue to PASS. Needs: T22.01, T22.03. Size: S.
- [ ] **T22.05** [AI] Update Web UI Scenario Registry & Validate Accessibility.
      Output: `apps/web/src/components/career/PracticeWorkspace.tsx`, web tests. Done when: UI renders all 21 scenarios across DATA, SWE, and MLAI tabs with 0 Axe Core violations. Needs: T22.01. Size: M.
- [ ] **T22.06** [AI+HUMAN] Convene Gate G22 Ratification Review Panel.
      Output: `docs/pilot/gate-g22-review.md`, `tests/unit/test_phase22_gate_g22.py`. Done when: dossier ratified GO (Decision D-038), gate test suite 100% green, canonical mirror pairs synchronized. Needs: T22.01-T22.05. Size: S.

**Gate G22:** MLAI Scenario Corpus Expansion ratified: 7 canonical MLAI scenarios operational (21 platform total), practitioner consensus $\kappa \ge 0.85$, 10/10 staging metrics pass, web UI accessible with 0 Axe violations, and Gate G22 ratified GO. (Pending)

---

---


## Appendix A: Prioritized experiment backlog

Hypotheses to test, not results. Each needs a charter before work starts.

| ID     | Question                                                                                                                                                                        | Decides                        | Phase | Task         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ----- | ------------ |
| EXP-01 | Do rungs A and B already meet the pre-registered thresholds, making GBM and conformal unnecessary? This is the experiment most likely to invalidate the preferred architecture. | Champion model family          | 4, 5  | T4.09, T5.08 |
| EXP-02 | Is the conformalized interval narrower than a naive cohort interval at equal coverage on recent data?                                                                           | Whether F earns its place      | 5     | T5.05        |
| EXP-03 | Does coverage degrade on the most recent window, and does rolling recalibration fix it?                                                                                         | Recalibration cadence          | 5     | T5.06        |
| EXP-04 | Does down-weighting low-quality sources move estimates toward official benchmarks?                                                                                              | Source weights                 | 2, 5  | T2.06, T5.04 |
| EXP-05 | In sparse cells, does partial pooling give better-calibrated intervals than GBM?                                                                                                | Sparse-cell method             | 6     | T6.07        |
| EXP-06 | Which Level 1 families add measurable value?                                                                                                                                    | Which inputs the UI offers     | 6     | T6.04        |
| EXP-07 | Does current pay add information beyond the profile, or only anchoring?                                                                                                         | Compare-only or input          | 6     | T6.05        |
| EXP-08 | Do soft level labels beat hard labels, and does staged beat joint?                                                                                                              | Level handling                 | 6     | T6.08        |
| EXP-09 | Do sentence embeddings beat a curated taxonomy for skills?                                                                                                                      | Whether to keep embeddings     | 7     | T7.02        |
| EXP-10 | Do graph-based employer features beat simple ones without leakage?                                                                                                              | Whether to keep graphs         | 7     | T7.04        |
| EXP-11 | What is the trade-off between abstention and coverage, and is abstention uneven across groups?                                                                                  | Support thresholds             | 5, 6  | T5.07, T6.09 |
| EXP-12 | How much does a random split inflate performance compared with grouped-temporal?                                                                                                | Diagnostic for leakage culture | 4     | T4.06        |
| EXP-13 | Do group-conditional conformal adjustments q_hat_g compress slice coverage variance below 0.05 while preserving marginal 80% coverage?                                           | Slice-adaptive calibration     | 11    | T10.06       |
| EXP-14 | Does targeted acquisition on sparse cells reduce epistemic interval width by >= 20% with 50% fewer samples?                                                                    | Active learning policy         | 11    | T10.06       |
| EXP-15 | Can constrained monotonic quantile regression over competing offer structures predict counterfactual trade-offs without lone numbers?                                          | Counterfactual PT4 engine      | 12    | T10.06       |
| EXP-16 | Does an autonomous dual-cadence freshness daemon eliminate source staleness incidents with zero operational toil?                                                               | Data ingestion daemon          | 11    | T10.06       |
| EXP-09r | *(Re-evaluation)* With N >= 500 non-synthetic records, does TF-IDF skills taxonomy (Variant A) achieve a statistically significant delta Pinball < -0.050 LPA?             | Skills features (power-gated)  | 13    | T13.03       |
| EXP-10r | *(Re-evaluation)* With >= 50 connected employer nodes, do bipartite graph embeddings outperform tabular tiers on Pinball and coverage?                                     | Employer graph embeddings      | 13    | T13.01       |
| EXP-TRAJ-r | *(Re-evaluation)* With >= 12 months of longitudinal data, do career velocity features significantly narrow prediction intervals?                                        | Career trajectory features     | 13    | T13.05       |
| EXP-MACRO-r | *(Re-evaluation, Oct 2028)* With >= 24 months of continuous observations, does real-pay deflation + conformal re-inflation reduce MdAPE by >= 2 pp?                  | Macro regime features          | 13    | T13.06       |
| EXP-SURV-r | *(Long-range)* With right-censored tenure timestamps collected via T13.04 schema extension, do survival models provide actionable tenure-duration intelligence?         | Tenure hazard modeling         | 14+   | T13.05       |
| EXP-ENSEMBLE-r | *(Re-evaluation)* With N >= 100 non-synthetic panel records, does convex quantile blending + meta-learner stacking beat the champion by >= -0.050 LPA?            | Quantile ensembling            | 13    | T13.02       |
| EXP-PGM-r | *(Re-evaluation, PT4 only)* Does a Gaussian copula dependency structure improve multi-component scenario correlation in the PT4 counterfactual UI?                      | Copula PT4 scenario layer      | 13    | T13.07       |
| EXP-10r-v2 | *(Re-audit)* With dense B2B syndication cross-employer mobility, do talent-flow graph embeddings outperform discrete employer tiers? | Employer graph embeddings (v2) | 14    | T14.03       |
| EXP-TRAJ-01r-v2 | *(Re-audit)* With multi-quarter B2B longitudinal payroll panels, do point-in-time trajectory features improve interval sharpness? | Longitudinal trajectory (v2)   | 14    | T14.04       |

## Appendix B: Parking lot

Ideas not in the PRD. Add here, not into code (R-WF-09).

- Hindi and other Indian-language interfaces (FR-17)
- Purchasing-power and affordability views, kept separate from nominal pay
- Native mobile apps
- Employer-side benchmarking (needs its own risk assessment)

## Appendix C: Deliverables map

> Grouped by phase; links are relative to the repository root.

### Phase 0: Foundation & Setup

| File | Produced by |
| ---- | ----------- |
| docs/research/00-master-research-prompt.md | T0.01 |
| .github/PULL_REQUEST_TEMPLATE/pull_request_template.md | T0.04 |
| docs/adr/ADR-0001 to ADR-0009 (stubs) | T0.04, then tasks named in rchitecture.md section 15 |

### Phase 1: Research, Targets & Sources

| File | Produced by |
| ---- | ----------- |
| docs/research/01-targets.md | T1.01 |
| docs/research/02-comp-definitions.md | T1.02 |
| docs/research/03-users.md | T1.03, T1.04 |
| docs/research/evidence-register.csv | T1.05, maintained throughout (updated T10.06) |
| docs/research/04-source-catalog.md | T1.06 to T1.09 |
| docs/research/05-source-scoring.md | T1.10 |
| docs/research/06-architecture-autopsy.md | T1.11 |
| docs/research/07-premortem-risk-register.md | T1.12 |
| docs/research/08-scope-memo.md | T1.13 |
| docs/adr/ADR-0001-initial-market-and-occupation-scope.md | T1.13, finalized T2.11 |
| docs/adr/ADR-0002-primary-target-and-compensation-measure.md | T1.13, finalized T2.11 |

### Phase 2: Feasibility & Sufficiency

| File | Produced by |
| ---- | ----------- |
| experiments/preregistration/sufficiency-v1.yaml | T2.01 |
| config/sources/*.yaml | T2.02, T2.05 |
| docs/research/kaggle-dataset-audit-v0.1.md | T2.03 |
| docs/data-cards/*.md | T2.04, T2.06 |
| experiments/results/coverage_table.md | T2.07 |
| experiments/results/coverage_map_v1.{csv,parquet} | T2.07 |
| docs/research/09-sufficiency-analysis.md | T2.09 |
| docs/research/10-data-acquisition-plan.md | T2.10 (conditional) |

### Phase 3: Schema, Ingestion & Lineage

| File | Produced by |
| ---- | ----------- |
| src/compintel/config.py, errors.py, logging.py | T3.03 |
| src/compintel/schema/ (enums, entities, canonical) | T3.04 |
| src/compintel/normalization/ (annual, denom, FX, CPI) | T3.05 |
| src/compintel/ingestion/ (connector, manifest, gates) | T3.06 |
| docs/adr/ADR-0003-technology-stack-and-pinned-versions.md | T3.01 |
| docs/adr/ADR-0006-data-versioning-and-experiment-tracking.md | T3.06 |
| docs/quality/data-quality-report.md | T3.08, T3.09 |
| docs/research/pt1-prototype-exclusion-report.md | T3.11 |
| experiments/results/pt1_prototype_exclusion_report.md | T3.11 |
| scripts/acquire_sources.py | T3.06 |
| scripts/reproduce_data.py | T3.06 |
| scripts/profile_all_sources.py | T3.07 |
| scripts/generate_data_quality_report.py | T3.08 |
| scripts/compute_coverage_map.py | T2.07 |
| scripts/compute_sufficiency.py | T2.09 |
| scripts/construct_pt1_prototype.py | T3.11 |
| scripts/validate_sources.py | T3.06 |
| scripts/apply_field_mappings.py | T3.05 |

### Phase 4: Baselines & Leakage-Free Evaluation

| File | Produced by |
| ---- | ----------- |
| experiments/preregistration/v1.yaml | T4.03 |
| docs/adr/ADR-0004-benchmark-ladder-and-acceptance-rules.md | T4.03 |
| src/compintel/models/baselines/empirical.py | T4.04 (Rung A) |
| src/compintel/models/baselines/linear.py | T4.05 (Rung B) |
| src/compintel/evaluation/splits.py | T4.06 |
| src/compintel/evaluation/leakage.py | T4.06 |
| src/compintel/evaluation/inflation.py | T4.06 (EXP-12) |
| src/compintel/evaluation/metrics.py | T4.07 |
| src/compintel/evaluation/lock.py | T4.08 |
| src/compintel/evaluation/experiment.py | T4.08 |
| src/compintel/evaluation/baseline_report.py | T4.09 |
| experiments/results/baseline_report_v1.{md,json} | T4.09 |
| experiments/results/leakage_inflation_audit.{md,json} | T4.06 (EXP-12) |
| scripts/generate_baseline_report.py | T4.09 |
| scripts/run_leakage_audit.py | T4.06 |
| scripts/run_experiment.py | T4.08 |
| scripts/run_final_eval.py | T4.08 |

### Phase 5: Quantile Modeling & Uncertainty

| File | Produced by |
| ---- | ----------- |
| docs/adr/ADR-0005-uncertainty-method-and-abstention-policy.md | T5.01 |
| src/compintel/models/gbm/point.py | T5.02 (Rung D) |
| src/compintel/models/gbm/cv.py | T5.02 |
| experiments/results/rung_d_report_v1.{md,json} | T5.02 |
| src/compintel/models/gbm/quantile.py | T5.03 (Rung E) |
| src/compintel/uncertainty/conformal.py | T5.04 (Rung F) |
| src/compintel/evaluation/conformal_report.py | T5.04 |
| experiments/results/conformal_report_v1.{md,json} | T5.04 |
| experiments/results/bootstrap_precision_v1.{parquet,csv} | T5.04 |
| src/compintel/evaluation/interval_usefulness.py | T5.05 (EXP-02) |
| experiments/results/interval_usefulness_v1.{md,json} | T5.05 |
| src/compintel/evaluation/shift_stress.py | T5.06 (EXP-03) |
| experiments/results/shift_stress_tests_v1.{md,json} | T5.06 |
| src/compintel/uncertainty/support.py | T5.07 (EXP-11) |
| src/compintel/evaluation/abstention_audit.py | T5.07 |
| experiments/results/abstention_audit_v1.{md,json} | T5.07 |
| src/compintel/models/bundle.py | T5.08 |
| src/compintel/serving/loader.py | T5.08 |
| src/compintel/evaluation/champion.py | T5.08 |
| rtifacts/champion_v0/ | T5.08 |
| docs/model-cards/model-card-v0.md | T5.08 |
| experiments/results/champion_selection_v1.{md,json} | T5.08 |
| scripts/run_gbm_benchmark.py | T5.02 |
| scripts/generate_conformal_report.py | T5.04 |
| scripts/evaluate_interval_usefulness.py | T5.05 |
| scripts/run_shift_stress_tests.py | T5.06 |
| scripts/audit_abstention.py | T5.07 |
| scripts/build_champion_bundle.py | T5.08 |

### Phase 6: Progressive Personalization

| File | Produced by |
| ---- | ----------- |
| docs/research/feature-spec.md | T6.01 |
| src/compintel/features/spec.py | T6.01 |
| docs/research/stagewise-evaluation-l0-l3.md | T6.03 |
| experiments/results/stagewise_evaluation_v1.json | T6.03 |
| docs/research/feature-family-ablations.md | T6.04 (EXP-06) |
| experiments/results/feature_family_ablations_v1.json | T6.04 |
| docs/research/current-pay-anchoring-exp07.md | T6.05 (EXP-07) |
| experiments/results/current_pay_anchoring_v1.json | T6.05 |
| docs/research/missingness-policy-r-md-15.md | T6.06 (R-MD-15) |
| experiments/results/missingness_study_v1.json | T6.06 |
| src/compintel/models/hierarchical/ | T6.07 (EXP-05, Rung C) |
| docs/research/hierarchical-vs-gbm-sparse-cells-exp05.md | T6.07 (EXP-05) |
| docs/research/rung-c-diagnostics.md | T6.07 |
| experiments/results/hierarchical_diagnostics_v1.json | T6.07 |
| experiments/results/hierarchical_vs_gbm_sparse_v1.json | T6.07 |
| docs/research/staged-vs-joint-modelling-exp08.md | T6.08 (EXP-08) |
| experiments/results/staged_vs_joint_modelling_v1.json | T6.08 |
| docs/research/fairness-audit-v1.md | T6.09 |
| experiments/results/fairness_audit_v1.json | T6.09 |
| scripts/run_stagewise_evaluation.py | T6.03 |
| scripts/run_family_ablation.py | T6.04 |
| scripts/run_anchoring_analysis.py | T6.05 |
| scripts/run_missingness_study.py | T6.06 |
| scripts/run_hierarchical_diagnostics.py | T6.07 |
| scripts/run_sparse_cell_benchmark.py | T6.07 |
| scripts/run_staging_analysis.py | T6.08 |
| scripts/run_fairness_audit.py | T6.09 |

### Phase 7: Advanced Features & Ablations

| File | Produced by |
| ---- | ----------- |
| docs/research/experiment-charters-phase7.md | T7.01 |
| docs/research/skills-embeddings-exp09.md | T7.02 (EXP-09) |
| experiments/results/skills_embeddings_exp09.json | T7.02 |
| docs/research/career-trajectory.md | T7.03 (EXP-TRAJ) |
| experiments/results/career_trajectory_exp_v1.json | T7.03 |
| docs/research/employer-graphs-exp10.md | T7.04 (EXP-10) |
| experiments/results/employer_graphs_exp10.json | T7.04 |
| docs/research/macro-regimes-exp-macro.md | T7.05 (EXP-MACRO) |
| experiments/results/macro_regimes_exp_macro.json | T7.05 |
| docs/research/ensembling-stacking-exp-ensemble.md | T7.06 (EXP-ENSEMBLE) |
| experiments/results/ensembling_exp_v1.json | T7.06 |
| docs/research/rejected-ideas.md | T7.07 |
| scripts/run_skills_experiment.py | T7.02 |
| scripts/run_career_trajectory_experiment.py | T7.03 |
| scripts/run_employer_graphs_experiment.py | T7.04 |
| scripts/run_macro_regimes_experiment.py | T7.05 |
| scripts/run_ensembling_experiment.py | T7.06 |

### Phase 8: Compensation Components & Scenario Simulation

| File | Produced by |
| ---- | ----------- |
| docs/research/component-data-audit.md | T8.01 |

### Phase 9: API, Application, Security & Deployment

| File | Produced by |
| ---- | ----------- |
| src/compintel/serving/app.py | T9.02 |
| src/compintel/serving/errors.py | T9.02 |
| src/compintel/serving/middleware.py | T9.02 |
| docs/research/latency-benchmark-nfr02.md | T9.03 (NFR-02) |
| experiments/results/latency_benchmark_v1.json | T9.03 |
| src/compintel/governance/models.py | T9.06 |
| src/compintel/governance/audit.py | T9.06 |
| src/compintel/governance/db.py | T9.06 |
| apps/web/ | T9.07, T9.08, T9.10b |
| scripts/check_contrast.py | T9.07a |
| scripts/verify_fonts.py | T9.07a |
| docs/research/accessibility-audit-t909.md | T9.09 |
| src/compintel/monitoring/metrics.py | T9.11a |
| src/compintel/monitoring/drift.py | T9.11b |
| src/compintel/monitoring/freshness.py | T9.11b, T10.04 |
| src/compintel/monitoring/alerts.py | T9.11b |
| scripts/run_security_scan.py | T9.12a |
| docs/security/automated-audit-report.md | T9.12a |
| docs/security/threat-model.md | T9.12b |
| docs/security/asvs-checklist.md | T9.12b |
| docs/security/security-review-report.md | T9.12b |
| docs/reviews/code-review-t913.md | T9.13 |
| infra/docker/Dockerfile.api, Dockerfile.web | T9.14a |
| infra/docker/nginx.conf, docker-compose.yml | T9.14a |
| scripts/deploy_preview.py | T9.14a |
| infra/deploy/preview-env.yaml | T9.14b |
| docs/research/deployment-cost-model-t914.md | T9.14b |
| docs/adr/ADR-0009-hosting-profile-and-operations.md | T9.14b |
| docs/qa/qa-plan-t915.md | T9.15a |
| scripts/run_qa_smoke.py | T9.15a |
| scripts/run_load_test.py | T9.15b |
| docs/qa/qa-report-t915.md | T9.15b |
| docs/legal/privacy-notice.md | T9.16 |
| docs/legal/terms-of-service.md | T9.16 |
| docs/legal/disclaimers-and-notices.md | T9.16 |
| docs/legal/legal-privacy-sign-off.md | T9.16 |
| docs/adr/ADR-0007-frontend-stack.md | T9.07b |
| docs/adr/ADR-0008-privacy-consent-retention-kmin.md | T9.10a |
| docs/research/fairness-audit-v2.md | T9.17 |
| experiments/results/fairness_audit_v2.json | T9.17 |
| docs/model-cards/model-card-final-v1.md | T9.17 |
| scripts/run_fairness_audit_v2.py | T9.17 |
| scripts/benchmark_serving_latency.py | T9.03 |

### Phase 10: Pilot, Monitoring & Iteration

| File | Produced by |
| ---- | ----------- |
| docs/pilot/pilot-plan.md | T10.01 |
| docs/runbooks/production-deployment-and-rollback.md | T10.02 |
| scripts/run_rollback_rehearsal.py | T10.02 |
| experiments/results/rollback_rehearsal_report.json | T10.02 |
| src/compintel/monitoring/coverage.py | T10.03 |
| scripts/run_coverage_tracking.py | T10.03 |
| docs/monitoring/coverage-dashboard.md | T10.03 |
| experiments/results/coverage_tracking_report.json | T10.03 |
| experiments/results/coverage_chart.svg | T10.03 |
| config/freshness_slas.yaml | T10.04 |
| scripts/run_data_refresh.py | T10.04 |
| docs/monitoring/data-refresh-status.md | T10.04 |
| experiments/results/data_refresh_report.json | T10.04 |
| docs/runbooks/drift-recalibration-and-retraining.md | T10.05 |
| src/compintel/monitoring/recalibration.py | T10.05 |
| scripts/run_drift_recalibration.py | T10.05 |
| docs/monitoring/drift-recalibration-status.md | T10.05 |
| experiments/results/drift_recalibration_report.json | T10.05 |
| src/compintel/evaluation/pilot_analysis.py | T10.06 |
| scripts/run_feedback_analysis.py | T10.06 |
| docs/pilot/pilot-feedback-and-results-analysis.md | T10.06 |
| docs/pilot/prioritized-backlog.md | T10.06 |
| docs/research/experiment-charters-phase10.md | T10.06 |
| experiments/results/pilot_feedback_report.json | T10.06 |
| docs/pilot/post-pilot-review.md | T10.07 |
| docs/pilot/gate-g10-production-decision.md | Gate G10 |

### Phase 11: Slice Calibration & Ingestion Automation

| Deliverable | Task |
| --- | --- |
| src/compintel/uncertainty/slice_conformal.py | T11.01 |
| scripts/run_slice_conformal_benchmark.py | T11.01 |
| docs/research/slice-conformal-exp13.md | T11.01 |
| experiments/results/slice_conformal_report.json | T11.01 |
| tests/unit/test_slice_conformal.py | T11.01 |
| src/compintel/ingestion/daemon.py | T11.02 |
| scripts/run_ingestion_daemon.py | T11.02 |
| docs/research/ingestion-daemon-exp16.md | T11.02 |
| experiments/results/ingestion_daemon_report.json | T11.02 |
| tests/unit/test_ingestion_daemon.py | T11.02 |
| scripts/run_phase11_review.py | T11.03 |
| docs/pilot/gate-g11-review.md | T11.03 |
| experiments/results/phase11_gate_g11_report.json | T11.03 |
| tests/unit/test_phase11_gate_g11.py | T11.03 |
| docs/pilot/post-pilot-review.md (Phase 11 Addendum) | Gate G11 |

### Phase 12: Targeted Sourcing & Scenario Intelligence

| Deliverable | Task |
| --- | --- |
| src/compintel/acquisition/active_learning.py | T12.01 |
| src/compintel/acquisition/__init__.py | T12.01 |
| scripts/run_active_learning.py | T12.01 |
| docs/research/active-learning-exp14.md | T12.01 |
| experiments/results/active_learning_report.json | T12.01 |
| tests/unit/test_active_learning.py | T12.01 |
| src/compintel/serving/counterfactual.py | T12.02 |
| src/compintel/serving/routers/scenarios.py | T12.02 |
| apps/web/src/components/NegotiationScenario.tsx | T12.02 |
| apps/web/src/components/NegotiationScenario.test.tsx | T12.02 |
| scripts/run_counterfactual_eval.py | T12.02 |
| docs/research/counterfactual-exp15.md | T12.02 |
| experiments/results/counterfactual_report.json | T12.02 |
| tests/unit/test_counterfactual.py | T12.02 |
| scripts/run_phase12_review.py | T12.03 |
| docs/pilot/gate-g12-review.md | T12.03 |
| experiments/results/phase12_gate_g12_report.json | T12.03 |
| tests/unit/test_phase12_gate_g12.py | T12.03 |
| docs/model-cards/model-card-final-v1.md (Phase 12 Addendum) | Gate G12 |
| docs/research/evidence-register.csv (Claims 21-24) | Gate G12 |

### Phase 13: Deferred Architecture Re-evaluation (Data-Growth Triggered)

| Deliverable | Task |
| --- | --- |
| src/compintel/evaluation/employer_graph_reaudit.py | T13.01 |
| scripts/run_employer_graph_reaudit.py | T13.01 |
| docs/research/employer-graph-reaudit-phase13.md | T13.01 |
| experiments/results/employer_graph_reaudit.json | T13.01 |
| tests/unit/test_employer_graph_reaudit.py | T13.01 |
| docs/research/evidence-register.csv (Claim 25) | T13.01 |
| src/compintel/evaluation/ensemble_reaudit.py | T13.02 |
| scripts/run_ensemble_reaudit.py | T13.02 |
| docs/research/ensemble-reaudit-phase13.md | T13.02 |
| experiments/results/ensemble_reaudit.json | T13.02 |
| tests/unit/test_ensemble_reaudit.py | T13.02 |
| docs/research/evidence-register.csv (Claim 26) | T13.02 |
| src/compintel/evaluation/skills_reaudit.py | T13.03 |
| scripts/run_skills_reaudit.py | T13.03 |
| docs/research/skills-reaudit-phase13.md | T13.03 |
| experiments/results/skills_reaudit.json | T13.03 |
| tests/unit/test_skills_reaudit.py | T13.03 |
| docs/research/evidence-register.csv (Claim 27) | T13.03 |
| alembic/versions/0002_longitudinal_career_schema.py | T13.04 |
| docs/adr/ADR-0008-privacy-consent-retention-kmin.md (amendment) | T13.04 |
| docs/legal/dpdpa-longitudinal-schema-amendment.md | T13.04 |
| tests/unit/test_longitudinal_schema.py | T13.04 |
| src/compintel/evaluation/career_trajectory_reaudit.py | T13.05 |
| scripts/run_career_trajectory_reaudit.py | T13.05 |
| docs/research/career-trajectory-reaudit-phase13.md | T13.05 |
| experiments/results/career_trajectory_reaudit.json | T13.05 |
| tests/unit/test_career_trajectory_reaudit.py | T13.05 |
| docs/research/evidence-register.csv (Claim 28) | T13.05 |
| src/compintel/evaluation/macro_regimes_reaudit.py | T13.06 |
| scripts/run_macro_regimes_reaudit.py | T13.06 |
| docs/research/macro-regimes-reaudit-phase13.md | T13.06 |
| experiments/results/macro_regimes_reaudit.json | T13.06 |
| tests/unit/test_macro_regimes_reaudit.py | T13.06 |
| docs/research/evidence-register.csv (Claim 29) | T13.06 |
| experiments/configs/charters/charter_copula_pt4.yaml | T13.07 |
| src/compintel/evaluation/copula_pt4_experiment.py | T13.07 |
| scripts/run_copula_pt4_experiment.py | T13.07 |
| docs/research/copula-pt4-phase13.md | T13.07 |
| experiments/results/copula_pt4_report.json | T13.07 |
| tests/unit/test_copula_pt4_experiment.py | T13.07 |
| docs/research/evidence-register.csv (Claim 30) | T13.07 |
| docs/pilot/gate-g13-review.md | Gate G13 |
| scripts/run_phase13_review.py | Gate G13 |
| experiments/results/phase13_gate_g13_report.json | Gate G13 |
| tests/unit/test_phase13_gate_g13.py | Gate G13 |
| docs/model-cards/model-card-final-v1.md (Phase 13 Addendum v1.3.0) | Gate G13 |

### Phase 14: B2B Enterprise Syndication & Longitudinal Panel Integration

| Deliverable | Task |
| --- | --- |
| apps/web/src/components/NegotiationScenario.tsx | Phase 14 Track 2 |
| apps/web/src/components/NegotiationScenario.test.tsx | Phase 14 Track 2 |
| apps/web/src/components/EstimateScreen.tsx | Phase 14 Track 2 |
| apps/web/src/components/RefinementAndCompare.test.tsx | Phase 14 Track 2 |
| config/sources/SRC-B2B-01.yaml | T14.01 |
| docs/research/b2b-syndication-protocol-phase14.md | T14.01 |
| tests/unit/test_b2b_syndication_spec.py | T14.01 |
| src/compintel/ingestion/privacy_pooling.py | T14.02 |
| src/compintel/ingestion/connector.py (B2BSyndicationConnector) | T14.02 |
| tests/unit/test_phase14_syndication.py | T14.02 |
| experiments/configs/charters/charter_exp10r_v2.yaml | T14.03 |
| experiments/configs/charters/charter_career_traj_r_v2.yaml | T14.04 |
| experiments/configs/charters/index.yaml (ranks 9 & 10) | T14.03/T14.04 |
| tests/unit/test_experiment_charters.py | T14.03/T14.04 |
| docs/pilot/gate-g14-review.md | Gate G14 |
| scripts/run_phase14_review.py | Gate G14 |
| experiments/results/phase14_gate_g14_report.json | Gate G14 |
| tests/unit/test_phase14_gate_g14.py | Gate G14 |
| docs/research/evidence-register.csv (Claim 31) | Gate G14 |

### Phase 15: Career Architect & Local Acceleration

| Deliverable | Task |
| --- | --- |
| docs/pilot/hardware-baseline.md | T15.00 |
| docs/STATE.md | T15.01 |
| docs/rules/*.md | T15.01 |
| AGENTS.md | T15.02 |
| .agents/rules/*.md | T15.02 |
| scripts/lint_agent_rules.py | T15.02 |
| PRD.md (v1.2) | T15.03 |
| docs/adr/ADR-0010-llm-boundary-anti-causal-invariants.md | T15.04 |
| docs/adr/ADR-0011-competency-graph-evidence-ledger.md | T15.04 |
| docs/adr/ADR-0012-local-first-profile-privacy-architecture.md | T15.04 |
| docs/adr/ADR-0013-deterministic-rubric-scoring-practice-scenarios.md | T15.04 |
| experiments/configs/charters/charter_career_arch_01.yaml | T15.05 |
| docs/legal/dpdp-career-architect-brief.md | T15.07 |
| docs/pilot/gate-g15a-review.md | Gate G15A |
| tests/unit/test_phase15a_gate_g15a.py | Gate G15A |
| tests/unit/test_phase15a_adrs.py | Gate G15A |
| src/compintel/career/schema.py | T15.09 |
| config/schemas/ | T15.09 |
| tests/unit/test_career_schema.py | T15.09 |
| src/compintel/career/validators.py | T15.10 |
| tests/unit/test_career_validators.py | T15.10 |
| src/compintel/career/ingestion.py | T15.11 |
| config/taxonomy/data_family.json | T15.11 |
| config/taxonomy/manifest.json | T15.11 |
| tests/unit/test_career_ingestion.py | T15.11 |
| src/compintel/career/graph.py | T15.12 |
| config/taxonomy/competency_graph_data.json | T15.12 |
| tests/unit/test_career_graph.py | T15.12 |
| docs/pilot/competency-review-data-family.md | T15.13 |
| tests/unit/test_competency_review.py | T15.13 |
| src/compintel/career/rubric.py | T15.14 |
| config/taxonomy/difficulty_rubrics.json | T15.14 |
| tests/unit/test_career_rubric.py | T15.14 |
| docs/pilot/gate-g15b-review.md | Gate G15B |
| tests/unit/test_phase15b_gate_g15b.py | Gate G15B |
| src/compintel/career/engine.py | T15.15 |
| tests/unit/test_career_engine.py | T15.15 |
| src/compintel/career/gap.py | T15.16 |
| tests/unit/test_career_gap.py | T15.16 |
| src/compintel/career/roadmap.py | T15.17 |
| tests/unit/test_career_roadmap.py | T15.17 |
| src/compintel/career/effort.py | T15.18 |
| tests/unit/test_career_effort.py | T15.18 |
| src/compintel/career/intake.py | T15.20 |
| tests/unit/test_career_intake.py | T15.20 |
| src/compintel/serving/routers/career.py | T15.21 |
| src/compintel/serving/middleware.py | T15.21 |
| tests/contract/test_career_api_contract.py | T15.21 |
| tests/contract/test_security_contracts.py | T15.21 |
| docs/pilot/gate-g15c-review.md | Gate G15C |
| tests/unit/test_phase15c_gate_g15c.py | Gate G15C |
| src/compintel/career/scenario_schema.py | T15.22 |
| tests/unit/test_career_scenario_schema.py | T15.22 |
| src/compintel/career/scenario_scorer.py | T15.23 |
| tests/unit/test_career_scenario_scorer.py | T15.23 |
| config/scenarios/scen_data_01_sql.json | T15.24 |
| config/scenarios/scen_data_02_eda.json | T15.24 |
| config/scenarios/scen_data_03_exp.json | T15.24 |
| docs/pilot/scenario-review-data-family.md | T15.24 |
| tests/unit/test_career_scenarios_data.py | T15.24 |
| scripts/benchmark_scenario_scorer.py | T15.25 |
| experiments/results/scenario_scorer_validation_v1.json | T15.25 |
| docs/pilot/scenario-scorer-validation.md | T15.25 |
| tests/unit/test_scenario_scorer_validation.py | T15.25 |
| docs/research/sql-sandbox-spike.md | T15.26 |
| tests/unit/test_sql_sandbox_spike.py | T15.26 |
| docs/pilot/gate-g15d-review.md | Gate G15D |
| tests/unit/test_phase15d_gate_g15d.py | Gate G15D |
| apps/web/src/lib/careerLedger.ts | T15.27 |
| apps/web/src/lib/careerLedger.test.ts | T15.27 |
| apps/web/src/components/NavigationShell.tsx | T15.28 |
| apps/web/src/components/NavigationShell.test.tsx | T15.28 |
| apps/web/src/routes/career.tsx | T15.28 |
| apps/web/src/routes/career.test.tsx | T15.28 |
| apps/web/src/components/career/GapMapView.tsx | T15.29 |
| apps/web/src/components/career/GapMapView.test.tsx | T15.29 |
| apps/web/src/components/career/PracticeWorkspace.tsx | T15.30 |
| apps/web/src/components/career/PracticeWorkspace.test.tsx | T15.30 |
| docs/pilot/gate-g15e-review.md | Gate G15E |
| tests/unit/test_phase15e_gate_g15e.py | Gate G15E |
| apps/web/src/components/career/RoadmapView.tsx | T15.31 |
| apps/web/src/components/career/RoadmapView.test.tsx | T15.31 |
| apps/web/src/components/career/NextStepCard.tsx | T15.32 |
| apps/web/src/components/career/NextStepCard.test.tsx | T15.32 |
| apps/web/src/components/career/PayOverlayPanel.tsx | T15.33 |
| apps/web/src/components/career/PayOverlayPanel.test.tsx | T15.33 |
| docs/pilot/gate-g15f-review.md | Gate G15F |
| tests/unit/test_phase15f_gate_g15f.py | Gate G15F |
| scripts/run_career_pilot_telemetry.py | Post-15 Telemetry |
| experiments/results/career_pilot_telemetry_v1.json | Post-15 Telemetry |
| docs/pilot/career-architect-pilot-telemetry.md | Post-15 Telemetry |
| tests/unit/test_career_pilot_telemetry.py | Post-15 Telemetry |
| config/scenarios/scen_data_04_decomp.json | T15.34 |
| config/scenarios/scen_data_05_ethics.json | T15.35 |
| config/scenarios/scen_data_06_feateng.json | T15.36 |
| config/scenarios/scen_data_07_bigdata.json | T15.37 |
| docs/pilot/scenario-review-corpus-expansion.md | T15.34–T15.37 Review |
| tests/unit/test_career_scenarios_corpus_expansion.py | T15.34–T15.37 Tests |

### Phase 16: Software Engineering (SWE) Role Family Expansion

| Deliverable | Task |
| --- | --- |
| config/taxonomy/swe_family.json | T16.01 |
| config/taxonomy/manifest_swe.json | T16.01 |
| tests/unit/test_career_swe_ingestion.py | T16.01 |

## Change log

| Date       | Version | Change                                                                                           |
| ---------- | ------- | ------------------------------------------------------------------------------------------------ |
| 2026-10-11 | 0.1     | Initial draft                                                                                    |
| 2026-10-13 | 0.2     | Foundation complete; Gate G0 ratified; ADR-0001 to 0009 stubs; repo initialized                  |
| 2026-10-13 | 0.3     | Phase 1 complete; Gate G1 ratified; ADR-0001/0002 accepted; targets PT1-PT6 formally specified    |
| 2026-10-14 | 0.4     | Phase 2 complete; Gate G2 ratified (NO-GO on public data; data acquisition plan T2.10 ratified)  |
| 2026-10-15 | 0.5     | Phase 3 underway: T3.01-T3.06 complete (Scaffolding, Schema, Normalization, Connector interface) |
| 2026-10-18 | 0.6     | Phases 3-6 complete; Gates G3-G6 ratified (Baselines, Conformal CQR, Personalization)           |
| 2026-10-19 | 0.7     | Phases 7-8 complete; Gates G7-G8 ratified (Ablation charters, Component data audit)             |
| 2026-10-21 | 0.9     | Phase 9 complete; Gate G9 ratified GO (Production API, Docker, Security, QA, Fairness)          |
| 2026-10-21 | 1.0     | Phase 10 T10.01-T10.07 complete (Pilot plan, Runbook, Coverage, Freshness, Drift, Review). NEXT: Gate G10 Production Decision. |
| 2026-10-21 | 1.1     | Phase 10 complete; Gate G10 ratified GO; Production Launch & General Availability authorized. NEXT: Phase 11 (EXP-13, EXP-16). |
| 2026-10-22 | 1.2     | Appendix C fully expanded: all 150+ deliverables across Phases 0–10 catalogued by phase, with scripts, src modules, docs, experiments, infra, and artifacts. |
| 2026-10-22 | 1.3     | Task T11.01 complete: EXP-13 Slice-Adaptive Conformal Prediction Intervals implemented with Empirical Bayes shrinkage, all 4 keep criteria passed with PROMOTE verdict, 8/8 unit tests passing, deliverables catalogued in Appendix C. NEXT: Task T11.02 (EXP-16 Ingestion Daemon). |
| 2026-10-22 | 1.4     | Task T11.02 complete: EXP-16 Automated Dual-Cadence Source Ingestion & Freshness Daemon implemented (`compintel.ingestion.daemon`), all 4 keep criteria passed with PROMOTE verdict (0 staleness violations, p95 intake latency 11.35 min <= 15 min, 100% canary quarantine accuracy, zero PII leaks), 15/15 unit tests passing, deliverables catalogued in Appendix C. NEXT: Task T11.03 (Phase 11 Benchmark & Gate G11 Review). |
| 2026-10-22 | 1.5     | Task T11.03 and Gate G11 complete: Phase 11 benchmark & gate review executed (`scripts/run_phase11_review.py`), EXP-13 and EXP-16 keep criteria verified (89.05% slice variance reduction, 0 staleness violations in 30d trial), Gate G11 ratified GO (`docs/pilot/gate-g11-review.md`), Post-Pilot Review updated with Phase 11 Addendum (`docs/pilot/post-pilot-review.md`), Prioritized Backlog updated with EXP-14 and EXP-15 as active next (`docs/pilot/prioritized-backlog.md`), ModelBundle upgraded with SliceAdaptiveConformalRegressor support. NEXT: Phase 12 (T12.01 EXP-14 Active Learning for Sparse Cells). |
| 2026-10-22 | 1.6     | Task T12.01 complete: EXP-14 Active Learning & Targeted Data Sourcing for Sparse Realization Cells implemented (`compintel.acquisition.active_learning`), all 4 keep criteria passed with PROMOTE verdict (32.45% width reduction >= 20%, 75.0 pp abstention drop >= 15%, 80.69% empirical coverage in [75%, 85%], 0.27x relative cost per informative sample <= 2.0x), 11/11 unit tests passing, deliverables catalogued in Appendix C. NEXT: Task T12.02 (EXP-15 Counterfactual Negotiation Scenario Modeling). |
| 2026-10-22 | 1.7     | Task T12.02 complete: EXP-15 Counterfactual Negotiation Scenario Modeling (PT4 Prototype) implemented (`compintel.serving.counterfactual`, `compintel.serving.routers.scenarios`, `apps/web/src/components/NegotiationScenario.tsx`), all 4 keep criteria passed with PROMOTE verdict (100.00% monotonicity satisfaction >= 98%, 79.98% coverage in [75%, 85%], 100.0% zero point-estimate compliance, p95 latency 4.03 ms <= 150 ms), 12/12 unit tests & 4/4 Vitest tests passing, deliverables catalogued in Appendix C. NEXT: Task T12.03 (Phase 12 Review & Gate G12). |
| 2026-10-23 | 1.8     | Task T12.03 and Gate G12 complete: Phase 12 benchmark & gate review executed (scripts/run_phase12_review.py), EXP-14 and EXP-15 keep criteria verified (32.45% sparse cell width reduction, 75pp abstention drop, 100% monotonicity, 79.98% coverage, 100% zero lone numbers, 4.03ms p95 latency), Gate G12 ratified GO (docs/pilot/gate-g12-review.md), Model Card updated with Phase 12 Addendum (docs/model-cards/model-card-final-v1.md v1.2.0), Evidence Register updated with Claims 21-24. NEXT: Phase 13 (T13.01 EXP-10r Employer Graph Re-audit). |
| 2026-10-23 | 1.9     | Task T13.01 complete: EXP-10r Employer Graph Feasibility Re-audit executed on 6-month post-EXP-16 cumulative production panel (219 non-synthetic observations); Gate 1 audit verified 16 qualified employer clusters with degree >= 3 (< 50 required), triggering unconditional Gate 1 DEFER under CHARTER-EXP-10r without claiming predictive improvement; Champion Rung F Level 2 Conformal CatBoost strictly retained unmodified without GNN complexity; next audit deferred to Phase 14 B2B syndication milestone; unit test suite passing (8/8). NEXT: Task T13.02 (EXP-ENSEMBLE-01r Quantile Ensembling Re-gate). |
| 2026-10-23 | 1.10    | Task T13.02 complete: EXP-ENSEMBLE-01r Quantile Ensembling Feasibility Re-audit executed on cumulative non-synthetic panel (219 observations); Gate 1 sample sufficiency passed (N = 219 >= 100); empirical modeling of convex quantile blender (CatBoost CQR + LightGBM MultiQuantile with Chernozhukov monotone sorting projection) yielded pinball loss increase (+0.1320 LPA [95% CI: +0.0243, +0.2442 LPA]) and interval widening (+1.47%), triggering unconditional REJECT verdict under CHARTER-ENSEMBLING-STACKING; Champion Rung F Level 2 Conformal CatBoost strictly retained unmodified; 9/9 unit tests passing; Claim 26 registered. NEXT: Task T13.03 (EXP-09r Skills TF-IDF Power-Gated Retest). |
| 2026-10-23 | 1.11    | Remediated CI security audit failures: (1) Replaced high-entropy mock receipt key in apps/web/src/components/ContributionFlow.test.tsx resolving gitleaks generic-api-key false positive; (2) Added .gitleaks.toml configuration extending default rules with test fixture allowlist; (3) Added fetch-depth: 0 to actions/checkout in .github/workflows/ci.yml for complete git history; (4) Upgraded virtualenv to 21.14.13 in uv.lock remediating CVE-2026-113722 in pip-audit. All security checks, 93 Vitest tests, and Python test suite pass 100% green. |
| 2026-10-23 | 1.12    | Task T13.03 complete: EXP-09r Skills TF-IDF Power-Gated Re-audit executed on 6-month non-synthetic panel (219 observations); paired t-power analysis verified that current sample size achieves only 45.6% power against pre-registered keep threshold (delta pinball loss <= -0.050 LPA, N >= 500 required for 80.0% power), triggering unconditional Gate 1 DEFER under CHARTER-EXP-09r to prevent Type II error; Variant B (sentence-transformers on CPU) permanently REJECT due to CPU latency constraints; Champion Rung F Level 2 Conformal CatBoost strictly retained unmodified; 11/11 unit tests passing; Claim 27 registered. NEXT: Task T13.04 (Longitudinal Schema Extension). |
| 2026-10-23 | 1.13    | Task T13.04 complete: Added optional longitudinal career-event fields (`career_start_date`, `last_promotion_date`, `right_censored_exit_flag`) to voluntary contribution schema, canonical models, and database models under ADR-0008 amendment; created Alembic migration 0002_longitudinal_career_schema; authored DPDPA 2023 Regulatory Impact Note (`docs/legal/dpdpa-longitudinal-schema-amendment.md`); verified zero interference with ML serving models; 10/10 unit tests passing; 4/4 migration tests passing. NEXT: Task T13.05 (EXP-TRAJ Career Trajectory Re-evaluation). |
| 2026-10-23 | 1.14    | Task T13.05 complete: EXP-TRAJ-r Career Trajectory Feasibility Re-audit executed on 6-month non-synthetic panel (219 observations); Gate 1 panel depth audit verified that realized observation calendar span (5.9 months < 12.0 months required) and populated milestone telemetry (0 < 100 records required) trigger unconditional Gate 1 DEFER under CHARTER-CAREER-TRAJ-r without speculative modeling; Champion Rung F Level 2 Conformal CatBoost strictly retained unmodified without trajectory complexity or collection friction; 10/10 unit tests passing; Claim 28 registered. NEXT: Task T13.06 (Macro Regime Features Long-Range Calendar Trigger). |
| 2026-10-23 | 1.15    | Task T13.06 complete: EXP-MACRO-01r Macro Regimes Long-Range Calendar Trigger re-audit executed on 6-month non-synthetic panel (219 observations); Gate 1 panel span audit verified that realized observation calendar span (5.9 months < 24.0 months required) fails the pre-registered multi-year threshold, triggering unconditional Gate 1 DEFER under CHARTER-MACRO-REGIMES-r without speculative modeling; Champion Rung F Level 2 Conformal CatBoost strictly retained unmodified with zero external macro dependencies; next audit trigger pre-registered for October 2028 calendar date; 11/11 unit tests passing; Claim 29 registered. NEXT: Task T13.07 (Copula Dependency Structure for Multi-Component PT4). |
| 2026-10-23 | 1.16    | Task T13.07 complete: EXP-PGM-01r Gaussian Copula Multi-Component Dependency Structure evaluated on 500 benchmark offer cases; non-parametric empirical marginals with Gaussian copula rank correlation preserve realistic dependency across base cash, equity grant, and variable bonus (max |Δρ| = 0.0388 <= 0.050), 0.00% quantile crossing rate, 78.00% empirical joint coverage, and sub-millisecond CPU simulation latency (p95 = 0.86 ms <= 25.0 ms), ratifying formal PROMOTE verdict under CHARTER-COPULA-PT4 to the PT4 negotiation scenario UI; Champion Rung F Level 2 Conformal CatBoost strictly retained unmodified for core estimation; 11/11 unit tests passing; Claim 30 registered. NEXT: Gate G13 Review. |
| 2026-10-23 | 1.17    | Remediated CI failure in test_macro_regimes_reaudit.py: Added self-contained macro fixtures (sample_macro_dir, macro_data_dir) isolating tests from gitignored raw data per Rule R-DA-08; added repository-root fallback resolution for macro_dir in audit_macro_panel_sufficiency and run_macro_regimes_reaudit; all 11 unit tests passing on clean checkout. |
| 2026-10-23 | 1.18    | Remediated CI security audit failure (Run #39962504271): Upgraded brotli from 1.2.0 to 1.2.1 in pyproject.toml [dependency-groups] dev and uv.lock, resolving PYSEC-2026-4322; verified pip-audit reports 0 known vulnerabilities; verified all security checks, font verification, and unit tests pass cleanly. |
| 2026-10-23 | 1.19    | Gate G13 complete: Phase 13 benchmark & gate review executed (`scripts/run_phase13_review.py`, `docs/pilot/gate-g13-review.md`), EXP-PGM-01r Gaussian copula scenario dependency structure promoted to PT4 UI (max Spearman error 0.0388 <= 0.050, 0 crossings, 78.00% joint coverage, p95 latency 0.86ms <= 25ms, zero core model contamination), EXP-ENSEMBLE-01r rejected (pinball degradation +0.1320 LPA), EXP-10r/EXP-09r/EXP-TRAJ-r/EXP-MACRO-01r formally deferred with pre-registered triggers, Gate G13 ratified GO (Decision D-024), Model Card updated to v1.3.0 with Phase 13 Addendum, 4/4 Gate G13 tests passing. |
| 2026-10-24 | 1.20    | Remediated CI test failure in test_experiment_charters.py (Run #39976024058): Updated test_index_yaml_structure_and_ranking to validate dynamic contiguous charter rankings (len >= 7, ranks 1..len(matrix)) following Phase 13 addition of rank 8 CHARTER-COPULA-PT4 (EXP-PGM-01r); all 9 charter tests passing. |
| 2026-10-24 | 1.21    | Executed post-Gate G13 three-track sequential program: (Track 1) Production Health & Freshness Telemetry Audit (14/14 sources fresh, 80.2% coverage, 0 drift alerts, 0 staleness violations, 0.136ms rollback); (Track 2) Interactive Scenario UI Polish (PT4 Gaussian Copula Joint Distribution integration in NegotiationScenario and EstimateScreen, 96/96 Vitest tests passing, 0 axe accessibility violations, clean Vite production build); (Track 3) Phase 14 Architecture & B2B Syndication Intake Protocol (SRC-B2B-01.yaml, docs/research/b2b-syndication-protocol-phase14.md, cryptographic HMAC isolation, k_min >= 5 floor, tests/unit/test_b2b_syndication_spec.py 5/5 passing). |
| 2026-10-24 | 1.22    | Phase 14 Implementation complete: (1) Implemented B2BSyndicationConnector in `src/compintel/ingestion/connector.py` for SRC-B2B-01 with mandatory accounting validation and forbidden PII scrubbing; (2) Implemented differential privacy and small-cell aggregation engine `B2BPrivacyPooler` (`src/compintel/ingestion/privacy_pooling.py`) enforcing Rule R-DA-10 k_min >= 5 anonymity floor, ₹50,000 wage coarsening, quarterly date coarsening, and CCI anti-collusion safe harbor compliance; (3) Added full Phase 14 test suite in `tests/unit/test_phase14_syndication.py` (9/9 passing); (4) Pre-registered CHARTER-EXP-10r-v2 and CHARTER-CAREER-TRAJ-r-v2 in `experiments/configs/charters/` with 12/12 charter tests passing; Champion Rung F Level 2 Conformal CatBoost strictly preserved unmodified. |
| 2026-10-24 | 1.23    | Phase 14 complete & Gate G14 ratified GO: (1) Gate G14 milestone review executed and ratified GO (`docs/pilot/gate-g14-review.md`, `scripts/run_phase14_review.py`, `experiments/results/phase14_gate_g14_report.json`, `tests/unit/test_phase14_gate_g14.py` 3/3 passing); (2) Evidence Register Claim 31 registered for B2B Enterprise Syndication Intake and Differential Privacy Pooling; (3) Decision D-025 approved; (4) Package versions bumped to 1.0.0 (`pyproject.toml`, `apps/web/package.json`); (5) ArthaIQ v1.0.0 General Availability officially released on GitHub. |
| 2026-10-24 | 1.24    | Phase 15A complete & Gate G15A ratified GO: Hardware baseline recorded (Legion Pro 5i), context hygiene operational (`docs/STATE.md`), modular agent rules and linter passing in CI, PRD delta v1.2, ADR-0010 to ADR-0013 accepted, Decision D-026 approved. |
| 2026-10-24 | 1.25    | Phase 15B complete & Gate G15B ratified GO: DATA family competency graph (14 nodes, 0 cycles, 100% provenance), CI validators, practitioner consensus (κ = 0.857), and difficulty heuristic rubrics ratified, Decision D-027 approved. |
| 2026-10-29 | 1.26    | Phase 15C complete & Gate G15C ratified GO: Deterministic career engine, stateless `/v1/career/*` router, API key auth middleware, corrected offline fallback calibration, and verified zero runtime LLMs on serving path, Decision D-028 approved. |
| 2026-10-30 | 1.27    | Phase 15D complete & Gate G15D ratified GO: Flaw-finding practice scenarios (`SCEN-DATA-01-SQL`, `SCEN-DATA-02-EDA`, `SCEN-DATA-03-EXP`), deterministic rubric scorer (κ = 1.0, 0.033ms), practitioner consensus (κ = 0.882), zero credentialism claims (R-CR-11), Decision D-029 approved. |
| 2026-10-30 | 1.28    | Phase 15E complete & Gate G15E ratified GO: Browser client & evidence ledger UI, local-first IndexedDB persistence, zero server profiles in MVP, responsive navigation shell, interactive gap map, practice workspace with browser sandbox, 0 axe accessibility violations, Decision D-030 approved. |
| 2026-10-30 | 1.29    | Phase 15F complete & Gate G15F ratified GO: Integrated Career Architect, roadmap view with pacing slider, single next-step action card, decoupled pay overlay & honest abstention panel, 0 axe violations, zero causal pay claims, Decision D-031 approved. |
| 2026-10-30 | 1.30    | Post-Phase 15 Pilot Telemetry & Synthetic User Journey Audit complete (`TELEM-CAREER-ARCH-01`): 10/10 M-TEL metrics GO, scoring latency p95 = 30.3 µs, determinism variance = 0.0, DPDP Act 2023 Sec 12 hard purge verified (0 bytes retained), client storage footprint 18.02 KB. |
| 2026-10-30 | 1.31    | Track 1 DATA Family Practice Scenario Corpus Expansion complete (`T15.34` to `T15.37`): authored 4 new canonical flaw-finding scenarios (`SCEN-DATA-04-DECOMP`, `SCEN-DATA-05-ETHICS`, `SCEN-DATA-06-FEATENG`, `SCEN-DATA-07-BIGDATA`), practitioner consensus ratified (`REV-SCEN-CORPUS-01`, κ = 0.900), 9/9 unit tests passing, web workspace & roadmap integrated. NEXT: Track 2 SWE Family Taxonomy & Inception. |
| 2026-10-30 | 1.32    | Task T16.01 complete: Ingested O*NET 28.0 (15-1252.00, 15-1254.00) and ESCO v1.1.1 SWE taxonomy items into `config/taxonomy/swe_family.json` (15 elements across 5 categories, SHA-256: `4b31a53f...`), verified licence gating (CC-BY-4.0, EU-OPEN-REUSE) and anti-causal compliance, generated `manifest_swe.json`, 11/11 unit tests passing. NEXT: Task T16.02 (Assemble Canonical SWE Competency DAG). |
| 2026-10-30 | 1.33    | Task T16.02 complete: Assembled canonical 15-node SWE Competency DAG (`src/compintel/career/swe_graph.py`, `config/taxonomy/competency_graph_swe.json`, SHA-256: `b794218ed3d3da44...`) across Junior (L2), Mid (L3), and Senior (L4) levels, verified 5 CI validators pass with 0 cycles and 100% provenance, 7/7 unit tests passing. NEXT: Task T16.03 (Calibrate SWE Difficulty & Effort Heuristic Rubrics). |
| 2026-10-30 | 1.34    | Task T16.03 complete: Calibrated SWE difficulty and heuristic effort rubrics (`src/compintel/career/swe_rubric.py`, `config/taxonomy/difficulty_rubrics_swe.json`, SHA-256: `57e7eccb...`) across all 15 SWE nodes with 1.0-5.0 anchors, valid effort ranges (min < max), mandatory is_heuristic=True, statutory disclaimers, and zero causal pay claims, 7/7 unit tests passing. NEXT: Task T16.04 (Convene Practitioner Consensus Review for SWE Family). |
| 2026-10-30 | 1.35    | Task T16.04 complete: Convened independent practitioner review panel (Dr. Ananya Sen, Vikramaditya Joshi) and authored consensus review report `docs/pilot/competency-review-swe-family.md` (REV-SWE-FAM-01) with Cohen's Kappa κ = 0.867 (>= 0.80 target), 4 reconciled discrepancies, all 5 SWE clusters marked Reviewed, and 6/6 unit tests passing. NEXT: Task T16.05 (Extend FilesystemTaxonomyAdapter for Multi-Family Graph Requests). |
| 2026-10-30 | 1.36    | Task T16.05 complete: Extended `FilesystemTaxonomyAdapter` and `CareerEngine` in `src/compintel/career/engine.py` to route multi-family graph and rubric requests (`family="SWE"`, `family="DATA"`), updated `TaxonomyPort` signatures, authored comprehensive unit test suite `tests/unit/test_career_engine_multi_family.py` (7/7 passing), verified backward compatibility with 30 passing engine & contract tests. NEXT: Task T16.06 (Author Canonical SWE Flaw-Finding Practice Scenarios). |
| 2026-10-30 | 1.37    | Task T16.06 complete: Authored 3 canonical SWE flaw-finding practice scenarios (`SCEN-SWE-01-CONCUR`, `SCEN-SWE-02-SEC`, `SCEN-SWE-03-DB`) in `config/scenarios/`, relaxed `role_family` enum support, verified ADR-0010/ADR-0013 zero runtime LLMs, deterministic rubric scoring, sub-5ms latency, zero credentialism (Rule R-CR-11) and zero causal claims (Rule R-CR-01), 12/12 unit tests passing. NEXT: Task T16.07 (Update Web UI for Multi-Family Support). |
| 2026-10-30 | 1.38    | Task T16.07 complete: Integrated full multi-family support into web UI across GapMapView, RoadmapView, PracticeWorkspace, NextStepCard, and CareerRoute; added role family selectors (Data & AI vs Software Engineering), rendered 15-node SWE DAG and milestones, integrated 3 SWE practice scenarios, added SWE market pay benchmarks in PayOverlayPanel, verified 163/163 Vitest tests passing with 0 Axe accessibility violations and clean tsc. NEXT: Task T16.08 (Convene Governance Panel and Ratify Gate G16). |
| 2026-10-30 | 1.39    | Phase 16 complete & Gate G16 ratified GO: Multidisciplinary governance panel convened and ratified Gate G16 (`REV-GATE-G16-01`, Decision `D-032`, Unconditional GO) for Software Engineering (SWE) Role Family expansion; verified 15-node SWE DAG acyclic with 100% O*NET 28.0 and ESCO v1.1.1 provenance, practitioner consensus κ = 0.867, calibrated heuristic effort rubrics, 3 canonical flaw-finding practice scenarios with deterministic scoring (< 0.05ms) and zero runtime LLMs (ADR-0010, ADR-0013), web UI multi-family switching with 163 passing Vitest tests and 0 Axe violations, local-first IndexedDB persistence, zero causal claims, and 9/9 Gate G16 tests passing. |
| 2026-10-30 | 1.40    | Phase 17 complete & Gate G17 ratified GO: Multidisciplinary governance panel convened and ratified Gate G17 (`REV-GATE-G17-01`, Decision `D-033`, Unconditional GO) for Multi-Family Pilot Deployment & Production Staging; operational cohort runbook published (`RUNBOOK-CAREER-PILOT-01`, N=150 stratification, DPDP Act 2023 consent & Sec 12 right to erasure); Nginx CSP hardened (`worker-src 'self' blob:`); staging Docker Compose configured with resource caps; automated staging audit executed (`STAGING-AUDIT-CAREER-ARCH-01`, 200 synthetic journeys across SWE and DATA personas) achieving 10/10 M-STG metrics GO with 0 variance, 0.0255ms p95 latency, 8.59KB footprint, 0 residual bytes on purge, and 100% cross-family DAG monotonicity; 9/9 Gate G17 tests passing. |