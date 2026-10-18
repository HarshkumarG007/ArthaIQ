# Feature Specification for Progressive Personalization (Levels L0 to L3)

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/feature-spec.md` |
| **Task** | T6.01 |
| **Status** | Complete v1.0 |
| **Date** | 2026-10-18 |
| **Governs** | Phase 6 (T6.01–T6.10), Phase 7, `src/compintel/features/`, `compintel.models.hierarchical` |
| **Author** | ArthaIQ Machine Learning Research & Governance Core |
| **Normative References** | PRD Section 5 & FR-05, Architecture Section 4, Rules `R-MD-03`, `R-MD-06`, `R-MD-07`, `R-MD-09`, `R-MD-11`, `R-MD-13`, `R-MD-15`, `rules.md` Section 16 Rule 11 |

---

## 1. Executive Summary & Purpose

A fundamental pathology in compensation intelligence systems is **premature feature bloat**: incorporating hundreds of noisy, uncurated, or ethically hazardous inputs into estimation algorithms without establishing whether each personal disclosure provides genuine statistical value over a compact baseline profile.

ArthaIQ approaches compensation estimation as a disciplined, staged, evidence-gated inquiry. The core objective of **Phase 6 (Progressive Personalization & Hierarchical Modelling)** is:
$$\text{Determine which personal disclosures measurably improve the conditional wage estimate, and by how much.}$$

This document establishes the formal specification, taxonomy, availability constraints, ethical bounds, and pre-registered ablation thresholds for **23 candidate features** spanning **Levels L0 through L3** across **7 feature families**.

### The Phase 6 Governing Invariant
If progressive personalization fails to demonstrate a statistically significant and economically meaningful improvement under pre-registered ablation rules (EXP-06, EXP-07), **the production platform ships Level 0 baseline models only**. Falling back to Level 0 is not a failure; it is a valid, scientifically defensible, and ethically protective outcome.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   PROGRESSIVE PERSONALIZATION TAXONOMY & ACCESS GATES                  │
│                                                                                        │
│  [LEVEL 0: CORE BASELINE PROFILE — MANDATORY CONDITIONING]                             │
│  • Role Family • Canonical Seniority • Metro Location • Years of Experience           │
│  → Feeds Rungs A, B, D, E, F (Accepted Core Baseline, Zero Lookahead)                 │
│                                                                                        │
│  [LEVEL 1: ROLE-RELEVANT PROFILE — OPTIONAL, GATED BY EXP-06 ABLATION]                 │
│  • Primary Skills • Skill Depth • Domain Track • Employer Tier • Work Arrangement     │
│  • Career Velocity Index • Leadership & Scope Scale • Macro Market Regime              │
│  → Evaluated in Phase 6; retained only if Pinball Loss Δ ≤ -0.01 to -0.05 LPA          │
│                                                                                        │
│  [LEVEL 2: TARGET OPPORTUNITY & SEARCH CONTEXT — SEPARATED FROM PT1]                  │
│  • Target Employer ID (Rung C Shrinkage) • Employer Level Code                         │
│  • Advertised Band Midpoint [PT3] • Competing Offers [PT4] • Notice Period [PT3]       │
│  • Search Urgency [PT4]                                                                │
│  → Contextual scenario modeling; quarantined from core market baseline PT1            │
│                                                                                        │
│  [LEVEL 3: ADDITIONAL EVIDENCE & COMPENSATION BREAKDOWNS]                              │
│  • Current Guaranteed Cash [COMPARE-ONLY PT6 per R-MD-13 / EXP-07]                     │
│  • Verified Payslip Level • Fixed Allowance Ratio • Project Scale • Tenure Stability   │
│  → Verification weights & breakdown diagnostics; strict non-anchoring invariant       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Feature Governance Framework & Principles

Every feature specified in the ArthaIQ ecosystem must satisfy five non-negotiable governance principles:

### 2.1 The 10 Mandatory Audit Fields
Per `task.md` T6.01 acceptance criteria, each candidate feature must document:
1. **Feature ID:** Unique, immutable canonical identifier (`feat_l[0-3]_[name]`).
2. **Personalization Level:** `L0_CORE`, `L1_ROLE_PROFILE`, `L2_TARGET_OPPORTUNITY`, or `L3_ADDITIONAL_EVIDENCE`.
3. **Feature Family:** Categorical domain grouping across 7 recognized compensation axes.
4. **Definition & Representation Data Type:** Unambiguous mathematical/semantic meaning and machine representation (`CATEGORICAL`, `NUMERICAL_CONTINUOUS`, `NUMERICAL_DISCRETE`, `STRING`, `BOOLEAN`, `ARRAY_STRING`).
5. **Availability Timing & Zero Lookahead (`R-MD-03`):** Explicit declaration of when the feature is observed; strict verification that it exists at prediction query time with zero post-facto contamination.
6. **Data Source:** Originating catalog or intake stream (e.g. `SRC-INT-VOL-01`, statutory filings, curated taxonomies).
7. **Leakage Risk & Mitigations (`R-MD-06`):** Identification of potential target or future information leakage, with programmatic inner-fold isolation guards.
8. **Privacy, Autonomy & DPDPA 2023 Compliance:** Evaluation of identifiability, sensitivity, consent mechanisms, and re-identification risk under the Digital Personal Data Protection Act 2023.
9. **Expected Utility:** Theoretical and empirical mechanism by which the feature informs compensation distributions in the Indian tech ecosystem.
10. **Ablation Plan & Pre-Registered Thresholds (EXP-06, EXP-07):** Pre-specified quantitative criteria governing whether the feature is kept, deferred, or rejected.

### 2.2 Absolute Prohibition of Protected Demographic Attributes
In strict adherence to `rules.md` Section 16 Rule 11 and ethical compensation intelligence standards:
> **Prohibited Demographic Inputs:** The feature registry, training pipelines, and prediction APIs **SHALL NOT** collect, store, engineer, or ingest:
> - Gender or sex
> - Caste, tribe, or community status
> - Religion or faith
> - Exact Date of Birth / Biological Age (years of professional experience is the sole permissible tenure metric)
> - Mother tongue, linguistic identity, or ethnicity
> - Marital status, family status, or number of dependents
> - Biometric data, facial photographs, or physical likeness

### 2.3 Inner-Fold Feature Pipeline Fitting (`R-MD-06`)
All transformers, encoders, imputers, normalizers, and target encodings associated with features must be fitted strictly inside cross-validation training folds. Out-of-fold validation and test sets must remain entirely unseen during feature fitting to prevent optimistic bias.

### 2.4 Occam's Razor & CPU-First Feasibility (`R-MD-09`)
No deep neural embeddings, graph neural networks (GNNs), or vector databases may be introduced for feature processing without an approved experiment charter demonstrating clear statistical lift over classical sparse encodings on standard CPU hardware.

---

## 3. Taxonomy of Feature Levels (L0 to L3)

The four personalization levels mirror the progressive information disclosure of a user navigating the ArthaIQ platform:

| Level | Name | Purpose | Typical Cardinality | Required / Optional | Target Mapping |
|:---|:---|:---|:---|:---|:---|
| **L0** | Core Baseline Profile | Foundation market benchmark | 4 features | Mandatory | PT1, PT2, PT6 |
| **L1** | Role-Relevant Profile | Skill, domain, macro, and firm archetype depth | 8 features | Optional | PT1 (Conditional) |
| **L2** | Target Opportunity | Firm-specific and negotiation context | 6 features | Optional | PT3, PT4, Rung C |
| **L3** | Additional Evidence | Cryptographic verification & unbundling | 5 features | Optional | PT6, Weighting, Diagnostics |

---

## 4. Comprehensive Specification of All 23 Features

### 4.1 Level 0 — Core Baseline Profile (Mandatory Conditioning)

The Level 0 profile represents the mandatory minimal set of occupational and geographic attributes necessary to condition any valid compensation distribution. All Level 0 features are `ACCEPTED_CORE` invariants.

---

#### `feat_l0_role_family`
- **Feature ID:** `feat_l0_role_family`
- **Display Name:** Role Family
- **Level:** `L0_CORE`
- **Family:** `ROLE_RESPONSIBILITY`
- **Data Type:** `CATEGORICAL`
- **Definition:** Standardized primary technology occupation family mapped via deterministic keyword rules and O\*NET 29.0 taxonomy: `SWE` (Software Engineering), `DATA` (Data Engineering & Analytics), `MLAI` (Machine Learning & AI), or `OTHER`.
- **Availability Timing:** Available at query time from mandatory user input selection. Zero lookahead (`R-MD-03`).
- **Data Source:** User selection validated against `compintel.normalization.roles.RoleFamily` enum.
- **Leakage Risk & Mitigations:** Low. Role mapping rules are deterministic and fitted strictly on occupational ontology without target salary awareness.
- **Privacy & DPDPA 2023:** Coarse functional occupation; non-sensitive personal data under DPDPA 2023.
- **Expected Utility:** Primary macro-segmentation of the engineering wage structure (e.g. MLAI specialization exhibiting +15% to +35% premia over generalist application development at equivalent tenure).
- **Ablation Plan & Thresholds:** Core baseline anchor (Rungs A, B, D, E, F). Cannot be ablated (`ACCEPTED_CORE`).

---

#### `feat_l0_seniority`
- **Feature ID:** `feat_l0_seniority`
- **Display Name:** Seniority Level
- **Level:** `L0_CORE`
- **Family:** `ROLE_RESPONSIBILITY`
- **Data Type:** `CATEGORICAL`
- **Definition:** Canonical career seniority grade: `ENTRY` (0–2y), `MID` (2–5y), `SR` (5–8y), `LEAD` (8–12y), `STAFF` (10–15y), or `PRINCIPAL` (15y+), standardized via deterministic title heuristics and Radford/Mercer crosswalks.
- **Availability Timing:** Available at query time from mandatory user input selection. Zero lookahead (`R-MD-03`).
- **Data Source:** User selection or title normalization via `compintel.normalization.levels.SeniorityLevel`.
- **Leakage Risk & Mitigations:** Lookahead risk if historical profile contains post-promotion title. Mitigated by strict `effective_on` timestamp anchoring (`R-DA-03`).
- **Privacy & DPDPA 2023:** Standard professional rank; non-sensitive under DPDPA 2023.
- **Expected Utility:** The single largest explanatory driver of guaranteed base pay, accounting for >40% of variance across compensation distributions.
- **Ablation Plan & Thresholds:** Core baseline anchor. Cannot be ablated (`ACCEPTED_CORE`).

---

#### `feat_l0_location`
- **Feature ID:** `feat_l0_location`
- **Display Name:** Metro Location
- **Level:** `L0_CORE`
- **Family:** `LOCATION_WORK_ARRANGEMENT`
- **Data Type:** `CATEGORICAL`
- **Definition:** Primary Indian employment technology hub: `BENGALURU`, `HYDERABAD`, `NCR` (Delhi, Noida, Gurugram), `PUNE`, `MUMBAI`, `CHENNAI`, or `OTHER_IN`.
- **Availability Timing:** Available at query time from mandatory user input selection. Zero lookahead (`R-MD-03`).
- **Data Source:** User selection validated against `compintel.normalization.locations.MetroLocation`.
- **Leakage Risk & Mitigations:** Geographic contamination risk if international salaries are pooled. Mitigated by strict Indian market isolation policy (`R-MD-08`).
- **Privacy & DPDPA 2023:** Metro-level aggregation ensures residential re-identification is mathematically impossible.
- **Expected Utility:** Captures substantial local market premiums (e.g. Bengaluru and NCR commanding 15–25% premiums over Tier-2 Indian tech hubs).
- **Ablation Plan & Thresholds:** Core baseline anchor. Cannot be ablated (`ACCEPTED_CORE`).

---

#### `feat_l0_years_experience`
- **Feature ID:** `feat_l0_years_experience`
- **Display Name:** Years of Experience
- **Level:** `L0_CORE`
- **Family:** `EXPERIENCE_HISTORY`
- **Data Type:** `NUMERICAL_CONTINUOUS`
- **Definition:** Total cumulative verified relevant professional software/technology industry experience in years, bounded in $[0.0, 45.0]$.
- **Availability Timing:** Available at query time from mandatory user continuous input. Zero lookahead (`R-MD-03`).
- **Data Source:** User numerical input or verified chronological employment timeline from `SRC-INT-VOL-01`.
- **Leakage Risk & Mitigations:** Lookahead bias if experience is counted up to the date of survey submission rather than the contract effective date. Mitigated by indexing experience strictly as of `observation_effective_date`.
- **Privacy & DPDPA 2023:** Continuous tenure measure; does not reveal biological age or date of birth (`rules.md` Sec 16 Rule 11).
- **Expected Utility:** Foundational human-capital covariate capturing concave Mincerian wage returns to tenure.
- **Ablation Plan & Thresholds:** Core baseline anchor. Cannot be ablated (`ACCEPTED_CORE`).

---

### 4.2 Level 1 — Role-Relevant Profile (Optional, Gated by EXP-06 Ablation)

Level 1 features capture role-specific competencies, firm archetypes, and career dynamics. Inclusion in the production prediction model (PT1) is strictly contingent upon passing the EXP-06 pre-registered ablation thresholds.

---

#### `feat_l1_skills_primary`
- **Feature ID:** `feat_l1_skills_primary`
- **Display Name:** Primary Technical Skills
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `SKILLS_CAPABILITY`
- **Data Type:** `ARRAY_STRING`
- **Definition:** Curated set of verified core technical frameworks, languages, and distributed systems competencies (e.g. `Python`, `Distributed Systems`, `PyTorch`, `Golang`, `Kubernetes`, `Rust`) mapped to canonical ESCO/O\*NET identifiers.
- **Availability Timing:** Optional user multi-select query at prediction time.
- **Data Source:** Curated technical ontology crosswalked from `SRC-SUP-TAX-01` (O\*NET) & `SRC-SUP-TAX-02` (ESCO).
- **Leakage Risk & Mitigations:** Keyword inflation and out-of-vocabulary drift. Mitigated by minimum frequency clipping ($N \ge 50$ observations in training folds) and frozen vocabulary per model release.
- **Privacy & DPDPA 2023:** Non-sensitive professional skill indicators.
- **Expected Utility:** Isolates scarcity premiums for specialized systems and machine learning competencies (+15% to +30% over generic application development).
- **Ablation Plan & Thresholds:** EXP-06 Family A (Multi-hot binary encoding vs L0 baseline). Keep if $\Delta \mathcal{L}_{pinball} \le -0.03$ LPA on validation folds and marginal coverage remains within $[75\%, 85\%]$.

---

#### `feat_l1_skills_depth`
- **Feature ID:** `feat_l1_skills_depth`
- **Display Name:** Skill Specialization Depth Index
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `SKILLS_CAPABILITY`
- **Data Type:** `CATEGORICAL`
- **Definition:** Categorical index of technical depth: `COMMODITY` (widely available general-purpose stack), `INTERMEDIATE` (specialized frameworks with production track record), or `HIGH_DEPTH` (compilers, distributed consensus, low-level kernel/GPU optimization).
- **Availability Timing:** Optional self-selection guided by system scale questions.
- **Data Source:** ESCO competence depth mapping calibrated against user self-reported architecture responsibility.
- **Leakage Risk & Mitigations:** Subjective self-inflation bias on unverified intake. Mitigated by bounded ordinal categories and cross-validation against verified enterprise profiles.
- **Privacy & DPDPA 2023:** Non-sensitive self-reported proficiency.
- **Expected Utility:** Separates superficial keyword matching on resumes from genuine architectural mastery.
- **Ablation Plan & Thresholds:** EXP-06 Family A depth interaction term. Keep if $\Delta \mathcal{L}_{pinball} \le -0.02$ LPA with zero increase in quantile crossing rate.

---

#### `feat_l1_domain_specialization`
- **Feature ID:** `feat_l1_domain_specialization`
- **Display Name:** Domain Specialization
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `ROLE_RESPONSIBILITY`
- **Data Type:** `CATEGORICAL`
- **Definition:** Sub-domain track within role family: `BACKEND`, `FRONTEND`, `FULLSTACK`, `ML_INFRA`, `DATA_PLATFORM`, `CLOUD_DEVOPS_SRE`, `EMBEDDED_IOT`, `SECURITY`, or `MOBILE`.
- **Availability Timing:** Optional selection at query time.
- **Data Source:** User selection cross-referenced with Title Normalization rules.
- **Leakage Risk & Mitigations:** Overfitting to ultra-niche domains. Mitigated by pooling sparse categories ($N < 20$) into parent role family.
- **Privacy & DPDPA 2023:** Standard functional specialism.
- **Expected Utility:** Captures supply-demand imbalances between high-scarcity engineering tracks (e.g. ML Infra, Cloud Security) and high-supply tracks (Fullstack Web).
- **Ablation Plan & Thresholds:** EXP-06 Family B domain categorical dummy ablation. Keep if $\Delta \mathcal{L}_{pinball} \le -0.025$ LPA across grouped-temporal splits.

---

#### `feat_l1_employer_tier`
- **Feature ID:** `feat_l1_employer_tier`
- **Display Name:** Employer Tier / Archetype
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `EMPLOYER_BUSINESS`
- **Data Type:** `CATEGORICAL`
- **Definition:** Canonical employer archetype: `TIER_1_PRODUCT` (global Big Tech & FAANG), `GCC` (Global Capability Centers of Fortune 500 MNCs), `HIGH_GROWTH_STARTUP` (Series B+ venture-backed tech startups), `DOMESTIC_PRODUCT` (mature Indian product firms), or `IT_SERVICES` (system integrators and IT consulting firms).
- **Availability Timing:** Optional query input; user selects current or prospective firm archetype.
- **Data Source:** Canonical Employer Entity Mapping (T3.10b) cross-referenced with MCA / BSE statutory filings.
- **Leakage Risk & Mitigations:** Halo effect and subjective prestige bias. Mitigated by defining tiers strictly by objective business model, gross margin structure, and capital source rather than proprietary black-box reputational ranks (`R-MD-09`).
- **Privacy & DPDPA 2023:** Broad organizational archetype; provides zero employer-specific re-identification risk.
- **Expected Utility:** Explains the well-documented trimodal tech wage distribution in India (e.g. IT Services P50 ~ 10 LPA vs Tier-1 Product P50 ~ 35 LPA at identical 5y YoE).
- **Ablation Plan & Thresholds:** EXP-06 Family C archetype categorical ablation. Keep if $\Delta \mathcal{L}_{pinball} \le -0.05$ LPA and interval width ratio $R_{width} \le 0.90$.

---

#### `feat_l1_work_arrangement`
- **Feature ID:** `feat_l1_work_arrangement`
- **Display Name:** Work Mode Arrangement
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `LOCATION_WORK_ARRANGEMENT`
- **Data Type:** `CATEGORICAL`
- **Definition:** Contractual attendance requirement: `ON_SITE`, `HYBRID` (1–3 days office attendance), or `FULL_REMOTE`.
- **Availability Timing:** Optional user selection at query time.
- **Data Source:** User query input; validated against job posting metadata in `SRC-EXT-JOB-01`.
- **Leakage Risk & Mitigations:** Post-pandemic return-to-office policy drift. Mitigated by weighting observations by recency and auditing policy change dates.
- **Privacy & DPDPA 2023:** Standard employment policy descriptor.
- **Expected Utility:** Tests empirical post-2024 tech compensation hypotheses regarding remote discounts vs hybrid parity in Indian metros.
- **Ablation Plan & Thresholds:** EXP-06 Family D arrangement ablation on interval sharpness. Keep if $\Delta \mathcal{L}_{pinball} \le -0.01$ LPA; otherwise defer to Level 0 geo.

---

#### `feat_l1_career_velocity`
- **Feature ID:** `feat_l1_career_velocity`
- **Display Name:** Career Velocity Index
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `EXPERIENCE_HISTORY`
- **Data Type:** `NUMERICAL_CONTINUOUS`
- **Definition:** Normalized ratio of career level grade attained relative to cumulative tenure: $\text{Level\_Index} / (1 + \text{Years\_Experience})$.
- **Availability Timing:** Derived from chronological employment timeline during voluntary profile intake.
- **Data Source:** `SRC-INT-VOL-01` verified tenure history.
- **Leakage Risk & Mitigations:** Lookahead bias if promotion occurred subsequent to the observation date. Mitigated by computing metric strictly on historical epochs prior to `observation_effective_date`.
- **Privacy & DPDPA 2023:** Derived continuous ratio; individual dates and employers are not retained in serving models.
- **Expected Utility:** Differentiates high-trajectory fast-track individual contributors from tenure-accumulating counterparts.
- **Ablation Plan & Thresholds:** EXP-06 Family E continuous spline interaction with experience. Keep if $\Delta \mathcal{L}_{pinball} \le -0.015$ LPA.

---

#### `feat_l1_leadership_scope`
- **Feature ID:** `feat_l1_leadership_scope`
- **Display Name:** Team & Scope Scale
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `ROLE_RESPONSIBILITY`
- **Data Type:** `CATEGORICAL`
- **Definition:** Organizational leadership accountability: `IC_INDIVIDUAL` (individual contributor, 0 reports), `TECH_LEAD` (technical guidance of 1–5 engineers), `TEAM_LEAD_MGR` (direct people management of 5–15 engineers), or `ORG_LEAD` (management of 15+ engineers across multiple teams).
- **Availability Timing:** Optional selection at query time.
- **Data Source:** User query input cross-referenced with organizational title crosswalks.
- **Leakage Risk & Mitigations:** Inflated title reporting on resumes. Mitigated by anchoring categories to concrete headcounts rather than arbitrary executive titles.
- **Privacy & DPDPA 2023:** Standard organizational role scope.
- **Expected Utility:** Disentangles high-level Individual Contributor compensation from Engineering Management pay tracks.
- **Ablation Plan & Thresholds:** EXP-06 Family F leadership dummy ablation. Keep if $\Delta \mathcal{L}_{pinball} \le -0.02$ LPA.

---

#### `feat_l1_macro_market_regime`
- **Feature ID:** `feat_l1_macro_market_regime`
- **Display Name:** Macro Tech Market Regime
- **Level:** `L1_ROLE_PROFILE`
- **Family:** `MACRO_MARKET`
- **Data Type:** `CATEGORICAL`
- **Definition:** Macroeconomic tech labor market hiring regime indexed to observation effective quarter: `COOLING` (post-2022 normalization / hiring freezes), `STABLE` (steady replacement demand), or `EXPANSIONARY` (peak hiring boom e.g. 2021–2022).
- **Availability Timing:** Available at query time joined strictly via point-in-time release date. Zero lookahead (`R-MD-03`, T7.05).
- **Data Source:** RBI / NASSCOM / MCA quarterly tech labor and GDP indicators.
- **Leakage Risk & Mitigations:** Lookahead bias if joined on publication date rather than release date. Mitigated by release-time joining (`R-MD-03`).
- **Privacy & DPDPA 2023:** Macro-level economic indicator; zero personal data under DPDPA 2023.
- **Expected Utility:** Captures structural compensation shifts across macroeconomic tech hiring cycles.
- **Ablation Plan & Thresholds:** EXP-06 Family G macro-market regime ablation. Keep if $\Delta \mathcal{L}_{pinball} \le -0.01$ LPA across temporal splits; otherwise defer to T7.05.

---

### 4.3 Level 2 — Target Opportunity & Job Search Context (Opportunity-Specific)

Level 2 features capture firm-specific hiring parameters and transactional search dynamics. They are strictly quarantined from the core baseline market model (PT1) and utilized exclusively in hierarchical shrinkage models (Rung C) and forward-looking negotiation scenarios (PT3/PT4).

---

#### `feat_l2_target_employer_id`
- **Feature ID:** `feat_l2_target_employer_id`
- **Display Name:** Target Employer Identifier
- **Level:** `L2_TARGET_OPPORTUNITY`
- **Family:** `EMPLOYER_BUSINESS`
- **Data Type:** `STRING`
- **Definition:** Canonical employer cluster identifier (e.g. `EMP-0A1B2C3D`) resolved via deterministic exact and fuzzy matching (T3.10b).
- **Availability Timing:** Optional input during firm-specific benchmarking or offer evaluation.
- **Data Source:** Canonical Employer Entity Registry and MCA statutory filings.
- **Leakage Risk & Mitigations:** Severe de-anonymization and overfitting in small firms. Mitigated by strict $k_{min} \ge 5$ person cluster threshold (`R-DA-10`). Employers with $N < 5$ shrink completely to their parent `feat_l1_employer_tier` via hierarchical partial pooling.
- **Privacy & DPDPA 2023:** Employer corporate entity identifier; individual contributor records remain strictly masked.
- **Expected Utility:** Enables high-precision company-specific benchmarking for high-volume Indian technology employers.
- **Ablation Plan & Thresholds:** Hierarchical partial pooling evaluation (T6.02, Rung C). Keep if random-effects variance $\sigma_{emp}^2 > 0$ with $p < 0.01$ and empirical coverage is preserved.

---

#### `feat_l2_target_level_code`
- **Feature ID:** `feat_l2_target_level_code`
- **Display Name:** Employer-Specific Level Code
- **Level:** `L2_TARGET_OPPORTUNITY`
- **Family:** `ROLE_RESPONSIBILITY`
- **Data Type:** `STRING`
- **Definition:** Organization-specific internal career level code (e.g. `L5`, `SDE-3`, `64`, `MTS-3`) crosswalked to canonical seniority via `compintel.normalization.levels`.
- **Availability Timing:** Optional input during target opportunity evaluation.
- **Data Source:** Verified employer level taxonomy and user self-report.
- **Leakage Risk & Mitigations:** Level code misalignment across disparate corporate ladders. Mitigated by continuous soft-label mapping distributions across canonical seniority grades (T3.09).
- **Privacy & DPDPA 2023:** Corporate career band code; non-personal.
- **Expected Utility:** Removes leveling ambiguity during lateral job transitions between major technology enterprises.
- **Ablation Plan & Thresholds:** Ablation against generic seniority grade. Keep if MAE improves by $\ge 0.50$ LPA on mapped enterprise cohorts.

---

#### `feat_l2_advertised_band_midpoint`
- **Feature ID:** `feat_l2_advertised_band_midpoint`
- **Display Name:** Advertised Salary Band Midpoint
- **Level:** `L2_TARGET_OPPORTUNITY`
- **Family:** `TRANSACTIONAL_SEARCH`
- **Data Type:** `NUMERICAL_CONTINUOUS`
- **Definition:** Midpoint of recruiter-disclosed or job-posting advertised guaranteed cash range: $(\text{min\_annual} + \text{max\_annual}) / 2$ in nominal INR LPA.
- **Availability Timing:** Available only when user possesses a disclosed recruiter range for an active opening.
- **Data Source:** Job posting metadata in `SRC-EXT-JOB-01` or user negotiation input.
- **Leakage Risk & Mitigations:** Advertised ranges reflect recruiter budgets rather than closed transactions. Mitigated by strict quarantine: barred from PT1 market value; used exclusively in PT3 offer realization modeling.
- **Privacy & DPDPA 2023:** Commercial job requisition metadata; non-personal.
- **Expected Utility:** Anchors candidate expectations within a specific recruiter-negotiated salary band.
- **Ablation Plan & Thresholds:** Opportunity-conditioning ablation in Phase 8 (PT3/PT4). Prohibited from PT1 (`is_input_feature=False`, `DEFERRED_TO_PHASE_7`).

---

#### `feat_l2_competing_offers_count`
- **Feature ID:** `feat_l2_competing_offers_count`
- **Display Name:** Competing Offers Count
- **Level:** `L2_TARGET_OPPORTUNITY`
- **Family:** `TRANSACTIONAL_SEARCH`
- **Data Type:** `NUMERICAL_DISCRETE`
- **Definition:** Number of active, concurrent written job offers held by the candidate: $0, 1, 2, \text{or } 3+$.
- **Availability Timing:** Optional input during negotiation scenario simulation.
- **Data Source:** User self-disclosure in negotiation planning interface.
- **Leakage Risk & Mitigations:** Spurious correlation with unobserved candidate quality. Mitigated by explicit prohibition from baseline PT1 market value (`rules.md` Sec 16 Rule 12).
- **Privacy & DPDPA 2023:** Highly sensitive negotiation posture data; strictly client-side simulation.
- **Expected Utility:** Quantifies empirical negotiation leverage and bidding premiums during active multi-offer scenarios.
- **Ablation Plan & Thresholds:** Causal counterfactual analysis in Phase 8 (PT4). Excluded from PT1 (`is_input_feature=False`, `DEFERRED_TO_PHASE_7`).

---

#### `feat_l2_notice_period_days`
- **Feature ID:** `feat_l2_notice_period_days`
- **Display Name:** Notice Period Duration
- **Level:** `L2_TARGET_OPPORTUNITY`
- **Family:** `TRANSACTIONAL_SEARCH`
- **Data Type:** `NUMERICAL_DISCRETE`
- **Definition:** Contractual notice period required by current employer: $0$ (immediate joiner), $15$, $30$, $60$, or $90$ days.
- **Availability Timing:** Optional user query input.
- **Data Source:** Standard Indian tech employment contract disclosure.
- **Leakage Risk & Mitigations:** Notice buyout dynamics and candidate drop-off friction. Mitigated by modeling as transition friction rather than intrinsic worker value.
- **Privacy & DPDPA 2023:** Standard contractual term.
- **Expected Utility:** Explains the substantial "immediate joiner premium" (5–10% cash premium for $\le 30$-day notice) prevalent in the Indian hiring market.
- **Ablation Plan & Thresholds:** Offer acceptance probability ablation in PT3. Keep in PT3 if offer realization delta $> 5\%$; excluded from base PT1 (`is_input_feature=False`, `DEFERRED_TO_PHASE_7`).

---

#### `feat_l2_search_urgency`
- **Feature ID:** `feat_l2_search_urgency`
- **Display Name:** Job Search Urgency
- **Level:** `L2_TARGET_OPPORTUNITY`
- **Family:** `TRANSACTIONAL_SEARCH`
- **Data Type:** `CATEGORICAL`
- **Definition:** Job search posture: `CASUAL_EXPLORING` (employed, curious), `ACTIVE_SEARCH` (actively interviewing), or `IMMEDIATE_TRANSITION` (serving notice or currently unemployed).
- **Availability Timing:** Optional user query disclosure.
- **Data Source:** User self-disclosure during decision-support queries.
- **Leakage Risk & Mitigations:** Selection bias: distressed candidates accepting sub-market offers. Mitigated by strictly preventing this feature from depressing baseline market rate estimates in PT1.
- **Privacy & DPDPA 2023:** Personal job search disposition.
- **Expected Utility:** Bounds reservation wages in career decision-support modules.
- **Ablation Plan & Thresholds:** Decision-support simulation utility. Excluded from PT1 by policy (`is_input_feature=False`, `DEFERRED_TO_PHASE_7`).

---

### 4.4 Level 3 — Additional Evidence & Compensation Components

Level 3 features encompass itemized compensation unbundling, cryptographic verification proofs, and historical tenure stability metrics.

---

#### `feat_l3_current_guaranteed_cash`
- **Feature ID:** `feat_l3_current_guaranteed_cash`
- **Display Name:** Current Guaranteed Cash (Anchor Candidate)
- **Level:** `L3_ADDITIONAL_EVIDENCE`
- **Family:** `EXPERIENCE_HISTORY`
- **Data Type:** `NUMERICAL_CONTINUOUS`
- **Definition:** Candidate's current annualized guaranteed base cash in nominal INR LPA, strictly unbundled per ADR-0002.
- **Availability Timing:** Optional voluntary user disclosure.
- **Data Source:** User intake self-report or verified payslip via `SRC-INT-VOL-01`.
- **Leakage Risk & Mitigations:** **CRITICAL ETHICAL HAZARD:** Inclusion as a regressor directly reproduces historical wage discrimination, locks in past underpayment, and produces circular tautological models ($R^2 \approx 0.95$ where prediction simply mirrors $\text{past pay} \times 1.20$). **Mitigated by Compare-Only Architecture (`R-MD-13`):** Current pay is strictly barred from PT1 regression inputs (`is_input_feature=False`, `COMPARE_ONLY`). It is used exclusively in PT6 to evaluate personal market positioning.
- **Privacy & DPDPA 2023:** High-sensitivity personal financial data under DPDPA 2023. Handled with explicit consent and client-side processing.
- **Expected Utility:** Enables personal market percentile benchmarking (PT6) without contaminating objective market compensation estimates (PT1).
- **Ablation Plan & Thresholds:** EXP-07 Anchoring & Selection Analysis. Reject as input feature if current pay explains $>60\%$ of model weight or exacerbates wage disparity for historically underpaid cohorts. Default disposition: `COMPARE_ONLY`.

---

#### `feat_l3_verified_payslip_level`
- **Feature ID:** `feat_l3_verified_payslip_level`
- **Display Name:** Income Verification Proof Level
- **Level:** `L3_ADDITIONAL_EVIDENCE`
- **Family:** `EXPERIENCE_HISTORY`
- **Data Type:** `CATEGORICAL`
- **Definition:** Cryptographic proof level of contributor record: `SELF_REPORTED` (unverified web submission), `DOCUMENT_VERIFIED` (client-side WebAssembly redacted payslip verified), or `ENTERPRISE_CONFIRMED` (statutory corporate payroll disclosure).
- **Availability Timing:** Recorded automatically by voluntary intake ingestion pipeline.
- **Data Source:** `SRC-INT-VOL-01` WebAssembly verification token metadata.
- **Leakage Risk & Mitigations:** Verification bias: higher-paid workers may verify more frequently. Mitigated by treating proof level as a sample precision weight (SQSF tier, `R-UQ-07`) rather than a direct additive wage covariate.
- **Privacy & DPDPA 2023:** Client-side WebAssembly hashing ensures zero cleartext payslip images or personal identifiers touch ArthaIQ servers (`R-DA-07`).
- **Expected Utility:** Informs observation confidence and heteroskedastic error modeling in Rung C hierarchical partial pooling.
- **Ablation Plan & Thresholds:** Measurement variance weighting in T6.02 (Rung C). Keep if residual variance $\sigma_e^2$ is significantly reduced ($p < 0.01$).

---

#### `feat_l3_fixed_allowance_ratio`
- **Feature ID:** `feat_l3_fixed_allowance_ratio`
- **Display Name:** Fixed Allowance to Base Ratio
- **Level:** `L3_ADDITIONAL_EVIDENCE`
- **Family:** `EXPERIENCE_HISTORY`
- **Data Type:** `NUMERICAL_CONTINUOUS`
- **Definition:** Ratio of fixed monthly allowances (Special Allowance + HRA) to statutory Basic Pay: $(\text{hra\_annual} + \text{special\_allowance\_annual}) / \text{basic\_annual}$.
- **Availability Timing:** Available when contributor provides itemized payslip breakdown.
- **Data Source:** Itemized fields in `SRC-INT-VOL-01` intake.
- **Leakage Risk & Mitigations:** Tax structuring artifacts masquerading as productivity signals. Mitigated by unbundling per ADR-0002; total guaranteed cash remains the primary target.
- **Privacy & DPDPA 2023:** Itemized financial structure descriptor.
- **Expected Utility:** Detects aggressive tax structuring versus standardized corporate payroll policies across Indian employers.
- **Ablation Plan & Thresholds:** Component breakdown analysis in Phase 8. Keep if residual variance of guaranteed cash decreases by $\ge 2\%$.

---

#### `feat_l3_project_scale_tier`
- **Feature ID:** `feat_l3_project_scale_tier`
- **Display Name:** Technical Project Scale Tier
- **Level:** `L3_ADDITIONAL_EVIDENCE`
- **Family:** `SKILLS_CAPABILITY`
- **Data Type:** `CATEGORICAL`
- **Definition:** Production system throughput scale: `SCALE_MODEST` ($<10\text{k}$ DAU / single node), `SCALE_MEDIUM` ($10\text{k}$–$1\text{M}$ DAU / distributed cluster), or `HYPERSCALE` ($1\text{M}+$ DAU / $>10\text{k}$ QPS).
- **Availability Timing:** Optional self-reported engineering scale questionnaire.
- **Data Source:** Deep profiling questionnaire in `SRC-INT-VOL-01`.
- **Leakage Risk & Mitigations:** Subjective self-reporting claims. Mitigated by coarse 3-tier discretization and cross-verification against employer archetype.
- **Privacy & DPDPA 2023:** Technical architecture specification; non-personal.
- **Expected Utility:** Refines individual technical capability assessments within senior engineering cohorts (Staff / Principal).
- **Ablation Plan & Thresholds:** Staff/Principal cohort ablation. Keep if MAE improves by $\ge 1.0$ LPA on Staff/Principal slices.

---

#### `feat_l3_tenure_stability_index`
- **Feature ID:** `feat_l3_tenure_stability_index`
- **Display Name:** Employment Tenure Stability Index
- **Level:** `L3_ADDITIONAL_EVIDENCE`
- **Family:** `EXPERIENCE_HISTORY`
- **Data Type:** `NUMERICAL_CONTINUOUS`
- **Definition:** Median tenure duration across past completed employment epochs in years.
- **Availability Timing:** Derived from chronological employment history.
- **Data Source:** Verified employment timeline in `SRC-INT-VOL-01`.
- **Leakage Risk & Mitigations:** Penalizing career breaks or involuntary layoffs. Mitigated by computing symmetric tenure metrics and auditing career break indicators.
- **Privacy & DPDPA 2023:** Chronological career summary.
- **Expected Utility:** Evaluates empirical trade-offs between frequent job transitions ("job-hopping premium") and long-tenure stagnation in the Indian tech market.
- **Ablation Plan & Thresholds:** Linear regression interaction with total years of experience. Keep if interaction coefficient is statistically significant ($p < 0.05$) and stable across temporal folds.

---

## 5. Current Pay Anchoring Policy (`R-MD-13`, EXP-07)

### 5.1 The Anchoring Pathology
In naive machine learning pipelines for salary estimation, introducing a candidate's current salary ($y_{current}$) as a predictive feature ($X$) creates an illusion of high predictive power:
- The coefficient for current salary approaches $1.15$ to $1.25$ (the modal salary hike on job switches in India).
- $R^2$ artificially inflates from $0.65$ to $0.94$.
- The model ceases to estimate **market worth** and instead becomes a **tautological magnifier of past compensation**.

### 5.2 Ethical & Societal Hazards
1. **Compounding Historical Underpayment:** Candidates from historically underpaid backgrounds (graduates of Tier-3 engineering colleges, candidates switching from IT Services to Product, or demographic minorities) remain permanently trapped in depressed wage bands.
2. **Loss of Decision-Support Agency:** If ArthaIQ's market estimation tells an underpaid engineer earning 12 LPA that their market value is 14 LPA (because the model conditioned on their current 12 LPA), the platform actively harms the candidate's negotiation agency when the true market cohort median is 24 LPA.

### 5.3 The Compare-Only Architecture
To solve this structural hazard, ArthaIQ adopts the **Compare-Only Architecture** per Decision D-010 and Rule `R-MD-13`:

```
                       ┌──────────────────────────────────────────────┐
                       │   Candidate Features (L0, L1, L2, L3)        │
                       │   (EXCLUDING Current Guaranteed Cash)        │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │   PT1 Market Compensation Model              │
                       │   (Quantile GBM / Conformal Intervals)       │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                             PT1 Market Distribution [P10, P50, P90]
                                              │
      Candidate Current Pay                   │
      (feat_l3_current_guaranteed_cash)       │
                 │                            │
                 ▼                            ▼
      ┌───────────────────────────────────────────────────────────────┐
      │               PT6 Benchmark Positioning Engine                │
      │   • Evaluates Candidate Percentile Rank in Market             │
      │   • Computes Market Delta (Current Pay vs PT1 P50)            │
      │   • Flags Underpayment or Overpayment Disparities             │
      └───────────────────────────────────────────────────────────────┘
```

- In `src/compintel/features/spec.py`, `feat_l3_current_guaranteed_cash` is explicitly declared with:
  ```python
  is_input_feature = False
  disposition = AblationDisposition.COMPARE_ONLY
  ```
- Current pay **NEVER** enters the training matrix of the PT1 market estimation regressor.
- Under pre-registered hypothesis **EXP-07**, current pay will be evaluated in Phase 6. Unless it passes rigorous fairness parity tests, its permanent status remains strictly `COMPARE_ONLY`.

---

## 6. Missingness Policy & Sparsity Invariant (`R-MD-15`)

### 6.1 Progressive Disclosure & Incomplete Profiles
Because ArthaIQ respects user privacy, users are never compelled to disclose optional Level 1, Level 2, or Level 3 information. Consequently, query profiles exhibit structured sparsity.

### 6.2 The Three Invariants of Missingness (`R-MD-15`)
1. **Prohibition of Naive Default Imputation:** Optional continuous or categorical features (e.g. `feat_l1_skills_primary`, `feat_l1_employer_tier`) **SHALL NOT** be filled with naive global medians, modes, or zero values. A candidate who omits their employer tier is fundamentally distinct from a candidate working at an average firm.
2. **Masked-Missingness & Hierarchical Shrinkage:** 
   - Tree-based regressors (LightGBM, CatBoost) treat missing values natively through separate missing branches or NaN-aware splits.
   - Hierarchical models (Rung C, T6.02) shrink missing lower-level nodes back to their fully observed Level 0 parent distributions.
3. **Missingness is Never a Negative Attribute:** Missing inputs must never be interpreted by the platform, UI, or modeling artifacts as an indicator of candidate unfitness, lack of skill, or low employability.

---

## 7. Privacy, Data Protection & DPDPA 2023 Compliance Matrix

In accordance with India's Digital Personal Data Protection Act 2023 (DPDPA 2023) and global privacy standards:

| Level | Feature ID | Identifiability Risk | DPDPA 2023 Classification | Mitigation & Engineering Controls |
|:---|:---|:---|:---|:---|
| **L0** | `feat_l0_role_family` | Zero | General Occupational Data | Coarse categorization (4 families). |
| **L0** | `feat_l0_seniority` | Zero | General Career Rank | Coarse career bands (6 levels). |
| **L0** | `feat_l0_location` | Low | Geographic Region | Coarse metro aggregation; no pincodes or coordinates. |
| **L0** | `feat_l0_years_experience` | Low | Professional Tenure | Continuous bounded value; no DOB collected. |
| **L1** | `feat_l1_skills_primary` | Low | Professional Competency | Minimum frequency threshold ($N \ge 50$). |
| **L1** | `feat_l1_skills_depth` | Zero | Self-Reported Rating | Bounded 3-tier ordinal index. |
| **L1** | `feat_l1_domain_specialization`| Low | Professional Sub-track | Rare domain pooling ($N < 20$). |
| **L1** | `feat_l1_employer_tier` | Low | Corporate Archetype | Coarse 5-tier business model classification. |
| **L1** | `feat_l1_work_arrangement` | Zero | Workplace Policy | 3-tier operational categorization. |
| **L1** | `feat_l1_career_velocity` | Low | Derived Velocity Ratio | Continuous ratio; exact dates not stored. |
| **L1** | `feat_l1_leadership_scope` | Zero | Functional Scope | 4-tier head-count band. |
| **L1** | `feat_l1_macro_market_regime` | Zero | Macroeconomic Indicator | Point-in-time release join; zero personal data. |
| **L2** | `feat_l2_target_employer_id` | Medium | Corporate Identifier | $k$-anonymity cluster floor ($k \ge 5$, `R-DA-10`). |
| **L2** | `feat_l2_target_level_code` | Low | Corporate Ladder Code | Soft-label mapping; unlinked from identity. |
| **L2** | `feat_l2_advertised_band_midpoint`| Zero | Commercial Requisition | Bounded market cash range. |
| **L2** | `feat_l2_competing_offers_count` | Medium | Negotiation Posture | Client-side simulation only; not persisted. |
| **L2** | `feat_l2_notice_period_days` | Zero | Contractual Term | Discrete standard durations. |
| **L2** | `feat_l2_search_urgency` | Low | Intent State | Ephemeral query state; not logged to profile. |
| **L3** | `feat_l3_current_guaranteed_cash`| High | Financial Data | Compare-Only; encrypted at rest; client-side opt-in. |
| **L3** | `feat_l3_verified_payslip_level`| High | Verification Proof | Client-side WebAssembly redaction (`R-DA-07`). Zero cleartext images. |
| **L3** | `feat_l3_fixed_allowance_ratio` | Medium | Financial Structure | Component unbundling per ADR-0002. |
| **L3** | `feat_l3_project_scale_tier` | Zero | System Capability | Coarse 3-tier architecture scale. |
| **L3** | `feat_l3_tenure_stability_index`| Low | Tenure Chronology | Continuous summary; individual epochs discarded. |

---

## 8. Pre-Registered Ablation Protocol (EXP-06 & EXP-07)

### 8.1 Experimental Design
All feature evaluations in Phase 6 follow a nested, grouped-temporal validation framework. Models are trained on historical observation epochs and tested on strictly subsequent time windows.

### 8.2 Evaluation Metrics
1. **Change in Pinball Loss ($\Delta \mathcal{L}_{pinball}$):**
   $$\mathcal{L}_{pinball}(y, \hat{q}_\tau) = \max\left( \tau (y - \hat{q}_\tau),\, (\tau - 1)(y - \hat{q}_\tau) \right)$$
   Evaluated at $\tau \in \{0.10, 0.50, 0.90\}$.
2. **Empirical Coverage Retention ($C_{90}$):** Calibrated $80\%$ conformal interval must maintain marginal coverage within $[75\%, 85\%]$.
3. **Relative Interval Width ($R_{width}$):**
   $$R_{width} = \frac{\text{Median Width}(X_{L0} \cup X_{L1})}{\text{Median Width}(X_{L0})}$$
   Personalization must sharpen (narrow) prediction intervals without violating coverage.

### 8.3 Pre-Registered Decision Thresholds

| Feature Family | Candidate Features | Minimum Effect Threshold | Coverage Constraint | Decision Action |
|:---|:---|:---|:---|:---|
| **L0 Core Baseline** | Role, Seniority, Location, YoE | Baseline Anchor | $C_{90} \in [75\%, 85\%]$ | **ACCEPTED_CORE** |
| **EXP-06 Family A: Skills** | Primary Skills, Depth | $\Delta \mathcal{L}_{pinball} \le -0.03\text{ LPA}$ | No coverage drop | Keep if met; else Reject |
| **EXP-06 Family B: Domain** | Domain Specialization | $\Delta \mathcal{L}_{pinball} \le -0.025\text{ LPA}$ | No coverage drop | Keep if met; else Reject |
| **EXP-06 Family C: Employer Tier** | Employer Archetype Tier | $\Delta \mathcal{L}_{pinball} \le -0.05\text{ LPA},\, R_{width} \le 0.90$ | No coverage drop | Keep if met; else Reject |
| **EXP-06 Family D: Work Arrangement** | Hybrid, Remote, On-Site | $\Delta \mathcal{L}_{pinball} \le -0.01\text{ LPA}$ | No coverage drop | Keep if met; else Defer to L0 |
| **EXP-06 Family E: Career Velocity** | Velocity Ratio, Tenure | $\Delta \mathcal{L}_{pinball} \le -0.015\text{ LPA}$ | No coverage drop | Keep if met; else Reject |
| **EXP-06 Family F: Leadership Scope** | Scope Scale | $\Delta \mathcal{L}_{pinball} \le -0.02\text{ LPA}$ | No coverage drop | Keep if met; else Reject |
| **EXP-06 Family G: Macro Market** | Macro Market Regime | $\Delta \mathcal{L}_{pinball} \le -0.01\text{ LPA}$ | No coverage drop | Keep if met; else Defer to T7.05 |
| **EXP-07 Current Pay Anchoring** | Current Guaranteed Cash | $\text{Model Weight} < 60\% \text{ and } \Delta \text{Disparity} \le 5\%$ | Strict Parity | **COMPARE_ONLY** (Default) |

---

## 9. Architectural Traceability & Implementation Verification

The formal specifications detailed in this document are codified directly in ArthaIQ source code:
- **Registry & Spec Dataclass:** [`src/compintel/features/spec.py`](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/src/compintel/features/spec.py)
- **Module Interface & Lookups:** [`src/compintel/features/__init__.py`](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/src/compintel/features/__init__.py)
- **Architectural Boundary Conformance:** Verified via `uv run lint-imports` (`import-linter` contract: `Features only imports schema and normalization`).
- **Test Suite Verification:** [`tests/unit/test_feature_spec.py`](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/tests/unit/test_feature_spec.py) verifying registry invariants, coverage $\ge 90.0\%$, non-empty audit fields, and compare-only anchoring enforcement.
