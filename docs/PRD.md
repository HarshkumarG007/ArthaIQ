# PRD: ArthaIQ Compensation Intelligence Platform

Project identity: **ArthaIQ** (Compensation Intelligence · India-first)  
*Ethical Compensation Intelligence for Tech Careers.*

| Field | Value |
|---|---|
| Status | v1.0 (Ratified at Gate G2; scope, measure, and acquisition plan locked) |
| Last updated | 2026-10-14 |
| Owner | _your name_ |
| Workflow position | Step 1, define what you want to build (tracker in `memory.md`) |
| Companion docs | `architecture.md`, `rules.md`, `design.md`, `task.md`, `memory.md`, `research/00-master-research-prompt.md` |

**Core principle: never skip directly from IDEA → AI → DEPLOY.** Research, user definition, PRD, stack, architecture, design, rules, task breakdown, setup, development, testing, security review, code review, preview deployment, QA, production, monitoring and iteration all sit between the idea and a deployed product. `task.md` maps each stage to a phase and a go/no-go gate.

**Tags used in this document**

| Tag | Meaning |
|---|---|
| `[H]` | Hypothesis. Research or user testing must confirm it. |
| `[U]` | External fact not yet checked against a primary source. |
| `[TBD: T2.09]` | Decision owed to the named task or gate. |

Nothing here is a measured result. No salary, accuracy or cost figure appears in this document, and none may be added without a source or a measurement (R-EV-04).

---

## 1. Product overview

**One line.** A personalized compensation intelligence and decision-support tool. For a given role, level and location it estimates a plausible range of pay from evidence of known quality, shows how reliable the estimate is, and says plainly when the evidence is too thin to estimate at all.

| It is | It is not |
|---|---|
| Decision support for people evaluating offers or benchmarking their own pay | An appraisal, an offer, a guarantee, or legal or tax advice |
| A range with a stated definition, evidence summary and limitations | A single "your salary is X" number |
| Evidence-weighted, and willing to abstain | A model that always returns something |
| A report of associations observed in data | A claim that a skill, employer or tactic will cause a raise |
| A tool for individuals | A tool for ranking candidates or setting an individual's pay at an employer |

**Product commitments.** Each is testable and traces to a rule in `rules.md`.

1. Evidence before algorithms (R-EV, R-DA).
2. Ranges, never a lone point estimate (R-UQ-01).
3. Abstain rather than guess (R-UQ-02).
4. The simplest model that meets pre-registered thresholds (R-MD-01).
5. Honest scope: a market or occupation is supported only when data supports it (R-EV-03).

---

## 2. Problem

All rows are `[H]` until user research (T1.03, T1.04) and data research (Phases 1 and 2) confirm them.

| ID | Problem as the user experiences it | Why a title average or a single number falls short | Product response |
|---|---|---|---|
| PB-1 | "Pay for my title" ignores my level, city, employer type and skills. | Averages by title pool very different jobs. | Personalized estimates built through progressive profiling (FR-01, FR-05) |
| PB-2 | One number sounds precise and is not. | Pay for comparable people spreads widely. | Ranges with a stated coverage intent (FR-02) |
| PB-3 | I cannot tell where the data came from or whom it represents. | Self-reported data carries selection and reporting bias. | Evidence summary and transparency page (FR-04, FR-09) |
| PB-4 | "Salary", "CTC", "fixed", "in-hand" and "total compensation" get mixed. | Comparing incomparable measures yields confident nonsense. | Explicit measure definition on every output (FR-02) |
| PB-5 | My current pay and a recruiter's number anchor me. | Current pay can reflect past underpayment and is not an unbiased market signal. | Independent benchmark and compare view (FR-06) |
| PB-6 | I do not know when to stop trusting the tool. | Many tools always answer. | Evidence grade and abstention (FR-03, FR-19) |
| PB-7 | "What if I change city, level or employer type?" has no evidence-based answer. | Data shows associations, not what a change would cause. | Scenario comparisons labelled as associations (FR-14, deferred) |

---

## 3. Target users

| Persona | Situation `[H]` | Key question | What "useful" means | Priority |
|---|---|---|---|---|
| A. Offer evaluator | Holds or expects an offer for a role in a city | Is this offer inside a realistic range for someone like me? | A range with a stated definition and evidence, and a clear "cannot tell" when evidence is thin | Primary |
| B. Pay benchmarker | Employed, wondering whether current pay is typical | Where does my pay sit against comparable people? | A percentile band with uncertainty, using terms that match their payslip | Primary |
| C. Career explorer | Considering a change of role, level, city or employer type | How do ranges differ across these options, and how sure are we? | Side-by-side ranges labelled as associations | Secondary, after MVP |
| D. HR or compensation analyst | Benchmarks roles for an employer | Different needs: job matching, survey participation, pay-setting | Out of scope until a separate legal and ethical risk assessment exists | Deferred |

**Uses the product must not support**: ranking or screening candidates for employment; setting or negotiating an individual's pay on an employer's behalf; legal, tax or payroll advice; any formal appraisal.

**Open validation** (T1.03, T1.04): confirm the personas, the vocabulary users actually use for pay (CTC, fixed, in-hand), device and connectivity assumptions, and willingness to contribute data.

---

## 4. Ratified Product Scope and Gate G2 Decision

Scope formally ratified at Gate G2 (Task T2.11) following Phase 2 data profiling, prototype target construction, and data sufficiency analysis. The primary scope is locked to Indian technology roles with measure `guaranteed_cash_annual` in nominal INR LPA, supported by the Primary Data Acquisition Programme (T2.10).

| Dimension | Ratified Scope | Alternatives Considered | Decided / Ratified At |
|---|---|---|---|
| Market | India (`IND`); amounts in INR nominal (LPA) | US first (richer disclosures); global (rejected for MVP) | Ratified at Gate G2; ADR-0001 |
| Occupation family | Software engineering, data science and ML/AI roles | Broader white-collar set; single occupation | Ratified at Gate G2; ADR-0001 |
| Measure | `guaranteed_cash_annual`: fixed committed cash before tax, excluding variable, bonuses and equity | `base_annual`; `target_cash_annual`; total compensation | Ratified at Gate G2; ADR-0002 |
| Population | Salaried full-time employees; contract and hourly pay excluded | Include contract / freelance work | Ratified at Gate G2; ADR-0002 |
| Granularity | Occupation × city or region × experience band (84 Level-0 cells; 12 Core Cells) | Finer (employer) or coarser | Ratified at Gate G2; T2.01, T2.07, T2.09 |
| Profile levels | L0 required; L1 only for feature families that pass ablation | L2 and L3 deferred | G6 |
| Language | English only at prototype and launch | Hindi and regional languages | Ratified at T0.02 (Q-010); after PB |

**Gate G2 Decision Outcome & Operational Mandate (2026-10-14):**  
In strict compliance with the pre-registered decision rule, all approved public and secondary datasets were evaluated against sufficiency criteria (Task T2.09 / `experiments/preregistration/sufficiency-v1.yaml`).
- **Empirical Result:** All 12 core cells failed Criterion C1 (yielding $N_{\text{eff}} = 0.0$), triggering **Kill Criterion 1**. Phase 3 ML modelling on existing public datasets was immediately halted (`Rule R-WF-01`).
- **Operational Ratification:** Rather than abandoning the India tech market, relaxing sufficiency rules, or resorting to illegal scraping (`R-DA-01`) or invalid multipliers (`R-MD-07`), ArthaIQ formally adopted the **Smallest Viable Data Acquisition Programme** (Task T2.10 / `docs/research/10-data-acquisition-plan.md`).
- **Acquisition Protocol:** Ground truth itemized compensation records are acquired via B2C Governed Voluntary Intake (`SRC-INT-VOL-01`) with client-side WebAssembly redacted payslip verification and B2B Employer Syndication (`SRC-INT-CORP-01`) with standardized Data Sharing Agreements.
- **Sufficiency Gate for Phase 3 Baseline Models:** Phase 3 ML model training remains gated until the acquisition programme reaches the pre-registered floor of $N_{\text{eff}} \ge 50.0$ across the 12 core cells (target: 780 verified records).
- **Contingency Scope Boundary:** If after 90 days of acquisition, core cells outside Bengaluru fail to reach $N_{\text{eff}} \ge 50$, operational scope automatically narrows to **Bengaluru Software Engineering Professionals Only** ($H_{\text{narrowed}}$).

---

## 5. Prediction targets

These are different tasks. They must never be merged or served through one undifferentiated model. Full specifications are produced in T1.01.

| ID | Target | Variable | Observation unit | Horizon | Key assumptions and identification limits | Stage |
|---|---|---|---|---|---|---|
| PT1 | Market compensation for a role and candidate profile | Conditional distribution of the selected measure for comparable workers or openings | Worker-role-employer-period record, or a posting | Nowcast at the as-of date; staleness limit `[TBD: T2.04]` | Comparable-profile evidence is informative; it does not identify what this person would be offered. Depends on the mix of source types. | RP |
| PT2 | Compensation of comparable employees and openings | Descriptive cohort quantiles, with n and sources | Same as PT1 | As-of date | Descriptive only; minimum cohort size k_min applies (R-DA-10) | RP |
| PT3 | Plausible offers in a defined job search | Distribution of offers a candidate might receive | Offer | Search window: 90 to 180 calendar days (settled T1.01) | Needs offered-pay data including offers not accepted. Acceptance truncates the observed distribution. | Deferred |
| PT4 | Compensation under stated negotiation scenarios | Shift in the offer distribution given stated conditions | Offer plus context | Negotiation duration (7–30 days) | Needs negotiation metadata. Causal identification is weak. No hard-coded multipliers (R-MD-07). | Deferred, experimental |
| PT5 | Compensation after a transition or skill change | Distribution under changed profile inputs | Longitudinal worker record | Transition horizon: 12 to 24 months post-transition (settled T1.01) | Association, not cause. Extrapolation guard required. | Deferred, experimental |
| PT6 | Current pay against a benchmark | Percentile band of the user's figure within PT1 | User-reported figure | As-of date | Needs a matching definition. Valid only as far as PT1 is valid. | RP, PB |

**Empirical Target-Source Validity & Admissibility Matrix (Ratified at T2.05).**  
Governed by `docs/research/02-comp-definitions.md`, Rule `R-MD-07` (Strict anti-heuristic CTC unbundling), Rule `R-DA-01` (Licence gate), and Rule `R-MD-08` (Cross-market/currency isolation).  
Symbols: **✓ Approved Primary** (admitted to training/estimation) · **~ Auxiliary / Signal** (prior anchor, relative ratio, or macro covariate only; segregated from direct training) · **✗ Quarantined / Inadmissible** (blocked by accounting incompatibility, legal restriction, or empirical invalidity).

| Prediction Target | Canonical Measure | Approved Primary Sources | Auxiliary Benchmark / Signal Sources | Quarantined / Inadmissible Sources & Governing Constraints |
|---|---|---|---|---|
| **PT1: Market Guaranteed Cash** (Conditional profile distribution) | `guaranteed_cash_annual` (Basic + Fixed Allowances, pre-tax gross) | `SRC-INT-VOL-01` (ArthaIQ Governed Itemized Intake) | `SRC-IND-OFF-01` (MOSPI PLFS Tech Salaried Wage Floor Anchor $\mu_{\text{floor}}$) | **✗ Excluded:** `SRC-KAG-SO-01/02` (Total Comp aggregate); `SRC-KAG-FIX-03` (Unbundled CTC, `R-MD-07`); `SRC-USA-*` (US USD datasets isolated from INR models, `R-MD-08`); `SRC-KAG-FIX-01/02` (Scraped ToS risk, `R-DA-01`); `SRC-KAG-REJ-01..03` (Synthetic/scraped, `R-MD-11`). |
| **PT2: Comparable Cohort Range** (Descriptive quantiles with $k_{\text{min}} \ge 5$) | `guaranteed_cash_annual` | `SRC-INT-VOL-01` | `SRC-IND-OFF-01` (Official NSS tech cohort medians) | **✗ Excluded:** All unbundled CTC aggregates (`R-MD-07`); small cells below $k_{\text{min}} = 5$ (`R-DA-10`); all US USD datasets (`R-MD-08`). |
| **PT3: Plausible Offer Distribution** (Search window: 90–180 days) | `advertised_range_annual` (`advertised_min`, `advertised_max`) | *None in Indian production* (Naukri `SRC-KAG-FIX-01` restricted to test fixtures only under `R-DA-01`) | `SRC-USA-DOL-01` (US certified H-1B wage offer range benchmark); `SRC-IND-OFF-04` (NCS job vacancy research prototype signal) | **✗ Quarantined:** `SRC-KAG-FIX-01` (ToS violation risk, `R-DA-01`); Indian production PT3 is deferred until legally licensed job board API feeds are contracted (T2.10). |
| **PT4: Negotiation Scenarios** (Shift given context fields) | `guaranteed_cash_annual` + `signon_bonus_cash` | *None currently acquired* | *None* | **✗ Deferred:** Requires negotiation metadata, counter-offer history, and competing offer context. Arbitrary percentage multipliers (e.g. +15% for competing offer) are strictly prohibited (`R-MD-07`). |
| **PT5: Career Transition Scenarios** (12–24m post-transition) | `guaranteed_cash_annual` (Longitudinal panel) | *None currently acquired* | `SRC-USA-DOL-02` (PERM tenure-wage slope benchmark); `SRC-KAG-SO-01` (Cross-sectional experience curve prior) | **✗ Deferred:** Cross-sectional self-reports cannot identify causal transition effects without longitudinal panel records (`R-EV-02`). Extrapolation guard required. |
| **PT6: Current Pay Benchmark** (Percentile band of user figure) | `guaranteed_cash_annual` & `total_comp_annual` | `SRC-INT-VOL-01` | `SRC-KAG-SO-01/02` (Total Comp distribution); `SRC-USA-BLS-01` (US Total Comp distribution); `SRC-SUP-CORP-01` (BSE/NSE IT firm median MRE) | **✗ Quarantined:** `SRC-KAG-REJ-01` (Synthetic salaries, `R-MD-11`); unverified user claims without matching canonical definition. Current pay is compare-only, never a model feature (`R-MD-13`). |

---

## 6. Release stages

| Stage | Who uses it | Includes | Excludes | Exit gate |
|---|---|---|---|---|
| Research prototype (RP) | The maintainer and invited testers; no personal data stored | Pipeline, evaluation harness, champion model, calibrated intervals, abstention, local API or CLI | Web UI, accounts, contributions, scenario views | G6 |
| Public beta (PB) | Limited public | RP plus the web app per `design.md`, transparency page, compare view, contributions, data rights, monitoring, security and legal review | Scenario and equity modules unless they pass G8 | G9 |
| Production (PROD) | Public | PB plus SLOs, scheduled refresh, drift and recalibration procedures, rollback runbook | Anything that failed a gate | G10 |

---

## 7. Functional requirements

Priority: P0 must exist at its stage; P1 should; P2 is deferred. Stage: the first release where it exists (RP = API or CLI, PB = web app).

| ID | Requirement | Pri | Stage | Verified by |
|---|---|---|---|---|
| FR-01 | The user describes a Level 0 profile: occupation and location from controlled taxonomies, and experience as years, level, or "not sure". | P0 | RP, PB | T3.08, T9.08 |
| FR-02 | The system returns P10, P50 and P90 for the selected measure with its definition, currency, pay period, tax basis, nominal basis and as-of date. It never returns a lone point estimate. | P0 | RP, PB | T5.08, T9.03 |
| FR-03 | When support criteria fail, the system abstains: status `abstained`, plain-language reason codes, and fallbacks where they exist. No model number is shown. | P0 | RP, PB | T5.07, T9.03 |
| FR-04 | Every estimate carries an evidence summary: cohort size, source-type mix, data recency, evidence grade, data snapshot id and model version. | P0 | RP, PB | T9.05 |
| FR-05 | Optional Level 1 inputs (skills, industry, employer type, work arrangement) are offered only for feature families that pass the ablation gate. Each addition shows the before and after range, including when the range widens or does not change. | P1 | RP, PB | T6.04, T9.08 |
| FR-06 | The user can enter their current pay to see where it sits in the PT1 distribution, as a percentile band with uncertainty. Wording never says "underpaid" or "overpaid". Current pay is not a model input unless T6.05 shows it adds value. | P1 | PB | T6.05, T9.08 |
| FR-07 | Explanations. MVP shows cohort statements ("based on N comparable records"). Model-attribution views appear in PB, labelled as model attribution and never as cause. | P1 | PB | T9.05 |
| FR-08 | Money display: INR with Indian digit grouping and a lakh-per-annum shorthand, and USD; nominal only; one shared formatter; no purchasing-power conversion. | P0 | PB | T9.07 |
| FR-09 | A transparency page lists data sources, licences, freshness, the model card and known limitations. | P1 | PB | T9.05 |
| FR-10 | Versioned REST API with an OpenAPI schema, request validation and RFC 9457 problem-detail errors. | P0 | RP, PB | T9.02, T9.03 |
| FR-11 | Voluntary data contribution with unbundled consent, schema validation, deduplication, quarantine and a verification level. | P1 | PB | T9.10 |
| FR-12 | Data rights: view, export and delete contributions; retention enforced by a scheduled job. | P1 | PB | T9.10 |
| FR-13 | Internal monitoring: realized coverage, drift, source freshness and abstention rates by slice. | P1 | PB | T9.11 |
| FR-14 | Scenario comparison (market, level, employer type) labelled as association, with an extrapolation guard. | P2 | Deferred | T8.06 |
| FR-15 | Offer-distribution and negotiation scenarios. | P2 | Deferred, blocked on offer data | T8.07 |
| FR-16 | Component breakdown (base, variable, equity, benefits) and first-year versus recurring totals. | P2 | Deferred | T8.01 to T8.05 |
| FR-17 | Hindi and other Indian-language interfaces. | P2 | Deferred | n/a |
| FR-18 | A decision-support statement is visible on every estimate view and present in every API estimate response. | P0 | RP, PB | T9.03, T9.08 |
| FR-19 | Decoupled evidence framework (D-010): Source Quality Tier (institutional, triangulated disclosures, verified self-reports) and Prediction Support (deduplicated cell density, representativeness, source independence, recency, target consistency) are assessed independently. Invariant: sample size alone cannot justify an estimate. Abstention triggers whenever support, coverage or reliability fail preregistered thresholds. Thresholds fixed at G5. | P0 | RP, PB | T5.07, T5.08 |
| FR-20 | Level 2 and Level 3 inputs (target employer and level, recruiter range, offers, verified pay) are admitted one family at a time, each only after an ablation shows value. | P2 | Deferred | T6.01, T6.03 |

**Evidence and support framework (D-010).** Evaluated across two independent dimensions: (1) Source Quality Tier (Grade A institutional filings/verified payroll; Grade B triangulated/normalized disclosures; Grade C verified self-reports; Grade D unverified supplementary signals) and (2) Prediction Support Level (Supported, Guarded, Abstained). Abstention is triggered if data is single-source dependent, heavily unrepresentative, stale, or below preregistered cell density thresholds. Thresholds `[TBD: T5.07, G5]`.

---

## 8. Non-functional requirements

| ID | Area | Requirement | Target | Verified by |
|---|---|---|---|---|
| NFR-01 | Reproducibility | Any reported metric reproduces from a commit hash, data snapshot id and seed with one documented command | Every reported metric | T3.13, T4.07 |
| NFR-02 | Latency | p95 estimate latency on the chosen deployment profile | `[TBD: T9.03 after benchmark]` | T9.03 |
| NFR-03 | Cost | Monthly infrastructure and data cost per deployment profile | `[TBD: ADR-0009]` | T9.14 |
| NFR-04 | Privacy | Data minimization, purpose limitation, consent, retention and deletion; k_min on any displayed aggregate | Per ADR-0008 | T9.10, T9.16 |
| NFR-05 | Security | OWASP ASVS-aligned baseline `[U: confirm current version]`, dependency audit and secret scanning in CI | No critical finding open at G9 | T9.12 |
| NFR-06 | Accessibility | WCAG 2.2 AA `[U: confirm no newer Recommendation]` | Automated and manual pass | T9.09 |
| NFR-07 | Observability | Structured logs with request ids; metrics for status, abstention and latency; no personal data in logs | Live in preview | T9.11 |
| NFR-08 | Maintainability | Typed, linted and tested code; CI blocks merge on failure | All merges | T3.02 |
| NFR-09 | Fairness reporting | Error, coverage, abstention and data availability by group where lawful and statistically supportable | Before G9 and each promotion | T6.09, T9.17 |
| NFR-10 | Licensing | No source is used before it is `approved` in the licence register | 100% | T2.02, T3.06 |
| NFR-11 | Freshness | Each source has a refresh cadence and a staleness alarm | `[TBD: T2.04]` | T10.04 |
| NFR-12 | Documentation | A model card per promoted model and a data card per source | 100% | T2.04, T5.08 |
| NFR-13 | Availability | PB best effort; PROD objective | `[TBD: ADR-0009]` | T10.02 |

---

## 9. User stories and acceptance criteria

| ID | Story | Acceptance (Given / When / Then) |
|---|---|---|
| US-01 | As an offer evaluator, I enter role, city and experience and see a range, so I can judge whether an offer is plausible. | Given a supported profile, when I submit, then I see P10 to P90 with P50, the measure definition and as-of date, an evidence summary and the disclaimer. No number appears without its range. |
| US-02 | As any user, I can see how far to trust an estimate. | Given an estimate, then I see an evidence grade, cohort size, source mix and recency, and "How this was calculated" opens the model card. |
| US-03 | As a user with an unusual or thinly covered profile, I am told plainly that there is no reliable estimate. | Given an unsupported profile, then I see an abstention notice with reasons and next options, and no model number. |
| US-04 | As a user, I add optional details and see what changed. | Given an estimate, when I add a Level 1 detail that passed ablation, then I see the before and after ranges, including when the range widens or stays the same. |
| US-05 | As a benchmarker, I compare my current pay with the estimate. | Given an estimate and my figure, then I see where it sits with its uncertainty, in neutral wording. |
| US-06 | As a contributor, I add my own pay record. | Given explicit consent, when I submit, then the record is validated, deduplicated and held in quarantine until checks pass. |
| US-07 | As a contributor, I can delete my data. | Given a contribution, when I request deletion, then it is removed from operational stores within the retention window `[TBD: ADR-0008]`, and aggregates recompute at the next refresh. |
| US-08 | As the maintainer, I see when the model is going stale. | Given live traffic and new observations, then monitoring shows realized coverage, drift, freshness and abstention by slice, and alerts at thresholds fixed at G5. |

---

## 10. Core flows

1. **Estimate (Level 0).** Profile form with three required fields → submit → if supported, estimate with evidence; if not, abstention notice → refine, compare, or open the calculation notes.
2. **Refine.** From an estimate, add optional details → recompute → show the before and after range.
3. **Compare.** From an estimate, enter current pay and pick the matching definition → percentile band with uncertainty.
4. **Contribute (PB).** Sign in → consent step → pay details → validation → confirmation → manage or delete later.

Layouts and states for these flows are specified in `design.md`.

---

## 11. Success metrics and pre-registration

Thresholds are written into `experiments/preregistration/` **before** the final test run (T4.03). Changing one afterwards is logged as a deviation. A candidate is promoted over a simpler model only if the improvement has a bootstrap 95% confidence interval that excludes zero and exceeds a minimum effect size fixed in advance.

| Layer | Metric | Threshold |
|---|---|---|
| Model | Pinball loss at q = 0.1, 0.5, 0.9, against Baselines A and B | `[TBD: T4.03]` |
| Model | MAE, median absolute error, median relative error | `[TBD: T4.03]` |
| Model | Coverage of the P10 to P90 interval on grouped-temporal test data, with CI, by slice and on the most recent window | Acceptable band `[TBD: T4.03]` |
| Model | Mean and median interval width, against a naive cohort interval at equal coverage | `[TBD: T5.05]` |
| Model | Quantile crossing after post-processing; raw rate also reported | 0 after post-processing |
| Model | Calibration error by quantile level and slice | `[TBD: T5.04]` |
| Model | Abstention rate overall and by slice; coverage among answered requests | `[TBD: T5.07]` |
| Data | Share of requests inside supported cells; source freshness; effective sample size per cell | `[TBD: T2.01, T2.09]` |
| Product | Comprehension: users can state that a range is not a guarantee | `[TBD: T9.15]` |
| Product | Task completion: an estimate or a clean abstention is delivered | `[TBD: T9.15]` |
| Product | Contribution opt-in rate and record validity rate | `[TBD: T10.01]` |
| Operations | p95 latency, error rate, freshness SLO, realized coverage drift | `[TBD: T9.03, T10.05]` |

Engagement maximization is not a success metric. Retention, streaks and urgency messaging are excluded by design (R-UI-05).

---

## 12. Out of scope and rejected

| Item | Decision | Reason | Revisit when |
|---|---|---|---|
| Ranking or screening candidates for employers | Never | Ethical and legal risk | Not planned |
| Hard-coded negotiation, notice-period, employer-prestige or skill multipliers | Rejected | No credible evidence; effects vary by market and role | Data supports a measured, caveated effect |
| Skill or certification "ROI" claims | Rejected | Association is not cause | Credible causal evidence exists |
| Black–Scholes as a universal private-equity value | Rejected | Option value, grant value and realized proceeds differ | Phase 8 scenario design |
| Scraping that violates terms, robots rules or law | Never | Legal and ethical risk | Licence granted |
| Global multi-country coverage in the MVP | Rejected | Representative data is unlikely to exist everywhere | After one market is validated |
| Graph neural networks, LLM feature extraction, vector databases, distributed compute | Deferred | Complexity without evidence | An experiment charter shows a measured gain (R-MD-09) |
| Protected attributes as model inputs | Not used | Discrimination and proxy risk | ADR with legal review (R-MD-12) |
| In-hand salary and tax computation | Out of scope | Jurisdiction-specific and changes often | Separate project |
| Purchasing-power or affordability outputs | Deferred | Must stay distinct from nominal pay | Phase 8 or later |
| Native mobile apps | Deferred | Responsive web comes first | After PB |

---

## 13. Data, legal and ethics summary

- **Licence gate.** No source is ingested until the licence register marks it `approved`: terms read, commercial use, redistribution and personal-data status recorded (R-DA-01).
- **Privacy.** India's Digital Personal Data Protection Act, 2023 and its rules `[U: confirm in-force status and obligations with qualified counsel; T2.02, T9.16]`. If the US enters scope, relevant state privacy laws `[U]`.
- **Minimization.** Collect only fields justified in `docs/research/feature-spec.md`. Contributor identity is stored apart from pay records (ADR-0008).
- **Small cells.** No aggregate is shown or exported for fewer than $k_{\text{min}} = 5$ distinct persons (`Rule R-DA-10`, ADR-0008). Count persons, not rows.
- **Fairness.** Audit errors, coverage, abstention and data availability by group where lawful and statistically supportable. Employer prestige, institution and location granularity get proxy-bias review.
- **Not legal advice.** The AI assistant does not reach legal conclusions; it flags items for qualified counsel (R-FA-04).

---

## 14. Risks (summary)

The full register is created in T1.12. Ratings are `[H]`.

| ID | Risk | L | I | Mitigation | Task |
|---|---|---|---|---|---|
| RSK-01 | No representative, licensed, record-level data for the target market and occupations | High | Critical | Sufficiency criteria fixed first; no-go gate; data acquisition programme | T2.01, T2.09, T2.10 |
| RSK-02 | Selection bias in self-reported data produces biased, overconfident estimates | High | High | Source scoring; checks against official benchmarks; abstention | T1.10, T2.06 |
| RSK-03 | Leakage or duplicates inflate performance | Med | Critical | Grouped-temporal splits, dedup, leakage tests, pre-registration | T3.10, T4.01, T4.06 |
| RSK-04 | Intervals miscalibrated under drift | High | High | Temporal calibration, recent-window tests, monitoring, recalibration | T5.03, T5.06, T10.05 |
| RSK-05 | Measure mismatch (CTC vs fixed vs total; offered vs reported) | High | High | Canonical schema with `comp_type` and `measure`; per-source mapping | T1.02, T2.05 |
| RSK-06 | Licensing, terms or privacy violation | Med | Critical | Licence register gate; counsel review; consent design | T2.02, T9.16 |
| RSK-07 | Over-engineering consumes the project | High | Med | Benchmark ladder; experiment charters; kill criteria | T7.01 |
| RSK-08 | Users read ranges as guarantees or explanations as causes | Med | High | Design rules, copy rules, comprehension testing | T9.15 |
| RSK-09 | Proxy bias via employer prestige, institution or location | Med | High | Feature review; fairness audits | T6.09, T9.17 |
| RSK-10 | Only a few cells are supported, so utility is low | High | High | Narrow scope; show coverage honestly; contribution programme | T2.07, T2.10 |
| RSK-11 | Data refresh and maintenance burden | Med | Med | Few sources; automation; freshness alarms | T10.04 |
| RSK-12 | Re-identification through small cells or contributions | Low | Critical | k_min; aggregation; access control | T9.10 |
| RSK-13 | AI-assistant drift: invented data, scope creep, silent changes | Med | High | `rules.md`, small tasks, definition of done, tests | every task |

---

## 15. Gates

One go/no-go decision closes each phase of `task.md`. Details and failure paths live there.

| Gate | Decision | Critical |
|---|---|---|
| G0 | Charter and docs ratified; blocking questions answered | |
| G1 | Targets, definitions and candidate sources agreed | |
| G2 | Data sufficiency and scope decision | Yes |
| G3 | Pipeline reproducible; contracts enforced | |
| G4 | Evaluation protocol locked; baselines reviewed | Yes |
| G5 | Calibrated intervals and abstention accepted | Yes |
| G6 | Personalization value decided; research prototype complete | Yes |
| G7 | Advanced modules kept or rejected | |
| G8 | Component and scenario modules kept or deferred | |
| G9 | Public-beta readiness | Yes |
| G10 | Production decision | Yes |

Phases 7 and 8 are optional branches. Phase 9 needs G6, not G8.

---

## 16. Glossary

| Term | Meaning |
|---|---|
| CTC | Cost to company. An Indian pay convention that can bundle fixed pay, variable pay and employer contributions; its definition varies by employer. |
| LPA | Lakh per annum. 1 lakh = 100,000. |
| Fixed pay, variable pay | Pay committed regardless of performance, versus pay that depends on performance or targets. |
| P10, P50, P90 | The 10th, 50th and 90th percentiles of the predicted distribution. P10 to P90 is an 80% interval by construction; real coverage must be measured. |
| Pinball loss | The standard loss for evaluating quantile predictions. |
| Conformal prediction | A method for calibrating intervals. Guarantees are marginal and assume exchangeability; drift can break them. |
| Partial pooling | Estimating small groups by borrowing strength from related groups. |
| Support | How much comparable, recent, good-quality evidence exists for a request. |
| Abstention | Declining to give an estimate because support is insufficient. |
| PLFS | Periodic Labour Force Survey (India) `[U]`. |
| OEWS, LCA | US BLS Occupational Employment and Wage Statistics, and Labor Condition Application disclosures `[U]`. |

---

## 17. Change log

| Date | Version | Change |
|---|---|---|
| 2026-10-11 | 0.1 | Initial draft generated from the master research prompt and the Vibe Coding Workflow |
| 2026-10-13 | 0.2 | Ratified at T0.03 following T0.02 decisions; updated validity matrix at T2.05 |
| 2026-10-14 | 1.0 | Ratified v1.0 at Gate G2 (Task T2.11). Replaced H0 with finalized India Tech scope (ADR-0001) and guaranteed_cash_annual measure (ADR-0002). Incorporated Gate G2 evaluation findings and the Primary Data Acquisition Programme (T2.10). Fixed k_min = 5 (ADR-0008, R-DA-10). |
