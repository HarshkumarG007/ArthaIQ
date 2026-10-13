# Specification of Prediction Targets (PT1 – PT6)

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/01-targets.md` |
| **Task** | T1.01 |
| **Status** | Complete v1.0 |
| **Date** | 2026-10-13 |
| **Governs** | `PRD.md` Section 5, `architecture.md` Section 4, Source Audits (T1.06, T1.08, T1.10) |
| **Core Invariant** | Targets are distinct mathematical estimation tasks; they MUST NEVER be conflated into a single model. |

---

## 1. Executive Summary & Foundational Constraints

In compensation intelligence, the single most common failure mode is **target contamination**: treating advertised job budgets, self-reported total CTC, verified payroll cash, and hypothetical counterfactual offers as if they were interchangeable observations of the same variable.

ArthaIQ maintains strict mathematical, semantic, and operational separation across six distinct prediction targets:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                PREDICTION TARGET TAXONOMY                              │
│                                                                                        │
│  [INITIAL RELEASE: MVP]                                                                │
│  • PT1: Market Compensation for Profile (Conditional Quantile Distribution)            │
│  • PT2: Comparable Cohort Distribution (Empirical Descriptive Quantiles)               │
│  • PT6: Current Compensation Benchmark (Percentile Positioning & Delta)                │
│                                                                                        │
│  [FUTURE EXPANSION: DEFERRED]                                                          │
│  • PT3: Plausible Offer Distribution in Defined Job Search (Truncated Offer Process)   │
│  • PT4: Compensation Under Stated Negotiation Scenarios (Counterfactual Shift)         │
│  • PT5: Compensation Post-Transition or Skill Addition (Longitudinal Horizon)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Universal Mathematical Conventions
1. **Target Measure:** All targets in the initial scope are standardized to `guaranteed_cash_annual` (fixed committed pre-tax cash, excluding variable, discretionary bonuses, gratuity accrual, employer PF contributions, and equity), denominated in **nominal INR Lakhs Per Annum (LPA)**.
2. **Quantile Specification:** Continuous predictions output conditional quantiles:
   $$\mathbf{Q}(Y | X) = \left[ Q_{0.10}(Y | X),\, Q_{0.50}(Y | X),\, Q_{0.90}(Y | X) \right]$$
   alongside a calibrated $(1 - \alpha)$ conformal prediction interval $[L(X), U(X)]$.
3. **Honest Abstention:** If effective sample density, source reliability, or covariate support fall below pre-registered thresholds, no estimate is generated.

---

## 2. Detailed Target Specifications

---

### Target PT1: Market Compensation for a Candidate Profile

*What is the plausible distribution of annual guaranteed cash for a specific tech profile in the Indian market as of today?*

| Dimension | Specification |
|:---|:---|
| **Mathematical Variable ($Y$)** | $Y \in \mathbb{R}^+$: `guaranteed_cash_annual` (INR LPA, nominal). Continuous variable representing annualized guaranteed fixed cash pay before personal income taxes. |
| **Observation Unit** | A single verified employment-compensation observation: a full-time tech worker in India, employed in a specific role and location, with an active compensation rate at timestamp $t$. |
| **Observation Horizon & Recency** | Nowcast at prediction date $t_0$. Observations admissible if observation date $t_{\text{obs}} \in [t_0 - 180\text{d}, t_0]$. If $t_{\text{obs}} > 90\text{d}$, observations are normalized via the sector wage index or urban CPI deflator. |
| **Conditioning Covariates ($X$)** | **Level 0 (Core / Mandatory):**<br>• Standardized Role Family (e.g. Backend Engineer, Data Scientist, ML Engineer)<br>• Normalized Total Relevant Experience (Years, continuous or 1-year bins)<br>• Canonical Location (Bengaluru, Hyderabad, NCR, Pune, Mumbai, Chennai, Other/Remote)<br>**Level 1 (Extended):**<br>• Primary Technical Competencies / Stack<br>• Employer Tier (Tier-1 Tech / Product, Global Capability Center [GCC], Mid-market Product, IT Services / System Integrator)<br>**Levels 2 & 3 (Deferred):** Specific target company, specialized internal job level. Admitted only post-ablation verification. |
| **Statistical Objective** | Minimize pinball loss across $\tau \in \{0.10, 0.50, 0.90\}$ subject to non-crossing constraints: $Q_{0.10}(Y|X) \le Q_{0.50}(Y|X) \le Q_{0.90}(Y|X)$. |
| **Underlying Assumptions** | 1. **Stationarity:** The underlying market wage structure does not undergo unmeasured structural breaks within the 180-day ingestion window.<br>2. **Taxonomy Consistency:** Distinct employer titles can be reliably mapped into canonical roles without destroying the core compensation signal. |
| **Identification Limits & Causal Caveats** | • **Association, not causation:** $Q_\tau(Y | X)$ reflects market equilibrium pricing for individuals with characteristics $X$, not a causal guarantee that giving an individual skill $X_j$ will increase their pay by $\Delta Y$.<br>• **Unobserved Quality:** Does not observe interview performance, problem-solving fluency, communication, or historical pedigree.<br>• **Conformal Scope:** Conformal prediction intervals guarantee marginal coverage over the population, not conditional coverage for every narrow micro-stratum. |
| **Release Stage** | **Research Prototype (RP) & Public Beta (PB)** |

---

### Target PT2: Comparable Cohort Distribution

*What do actual observed peers with similar profiles earn, based on raw, auditable records?*

| Dimension | Specification |
|:---|:---|
| **Mathematical Variable ($Y$)** | Empirical sample quantiles $(\hat{Q}_{10}, \hat{Q}_{50}, \hat{Q}_{90})$ and interquartile range of observed `guaranteed_cash_annual` (INR LPA). |
| **Observation Unit** | An aggregated cohort cell $C = \{y_i\}_{i=1}^N$ of $N$ deduplicated records matching a discretized profile query: $(\text{Role}, \text{Location}, \text{Experience Band}, \text{Employer Tier})$. |
| **Horizon & Recency** | Historical slice as of $t_0$. Max staleness 365 days, with median record age reported in metadata. |
| **Conditioning Covariates ($X$)** | Discrete taxonomy tuples: $\text{Role} \times \text{City Tier} \times \text{Exp Band} \times \text{Employer Segment}$. |
| **Statistical Objective** | Exact weighted empirical distribution function: $\hat{F}_N(y) = \frac{1}{\sum w_i} \sum_{i=1}^N w_i \mathbb{I}(y_i \le y)$, with sample size $N$ and source count $K$ explicitly exposed. |
| **Underlying Assumptions** | Records in cell $C$ are drawn from independent observations (no duplicate submissions, no single-firm clustering). |
| **Identification Limits & Safeguards** | • **Strict $k$-Anonymity Floor:** If $N < 5$, cell is completely withheld to preserve privacy.<br>• **Reliability Threshold:** If $N < 10$, descriptive quantiles are withheld from primary display (Abstention Triggered).<br>• **Selection Bias:** Cohort reflects whoever submitted or was recorded in the dataset; not necessarily a random sample of the national tech workforce. |
| **Release Stage** | **Research Prototype (RP) & Public Beta (PB)** |

---

### Target PT3: Plausible Offer Distribution in a Defined Job Search

*What distribution of offers is an active candidate likely to receive if they run a focused job search?*

| Dimension | Specification |
|:---|:---|
| **Mathematical Variable ($Y$)** | $Y_{\text{offer}} \in \mathbb{R}^+$: Initial and final written compensation offers extended to candidate $i$ during search period $W$. |
| **Observation Unit** | A discrete employment offer instance $(i, j, t)$ extended by employer $j$ to candidate $i$ at date $t$. |
| **Settled Search Window ($W$)** *(PRD [TBD: T1.01] Resolved)* | **90 to 180 Calendar Days.**<br>*Rationale:* In the Indian technology sector, typical contractual notice periods range from 30 to 90 days. A realistic search campaign involves 4–8 weeks of sourcing/interviews followed by 4–12 weeks of notice buyout or serve-out negotiation. Searches $<90\text{d}$ understate multiple offer arrival; searches $>180\text{d}$ suffer from market drift and fatigue bias. |
| **Conditioning Covariates ($X$)** | Profile covariates $X$ plus search intensity parameters: search duration, number of active applications, target employer tier, and location flexibility. |
| **Statistical Objective** | Offer generation arrival process modeled as a compound Poisson or order-statistic distribution: $Y_{\max} = \max(Y_1, Y_2, \dots, Y_M)$, where $M \sim \text{Poisson}(\lambda \cdot W)$. |
| **Underlying Assumptions** | Candidate actively participates in interviews; market hiring budgets remain active during window $W$. |
| **Identification Limits & Truncation** | • **Severe Right-Censoring & Acceptance Truncation:** Public data only captures *accepted* offers or *advertised* ranges. Rejected offers (which may be low, or extraordinarily high but declined for culture/stability) are missing not at random (MNAR).<br>• **Offer Elasticity:** Candidate leverage changes dramatically once offer 1 is received, altering offers 2 and 3. |
| **Release Stage** | **Deferred** (Requires dedicated offer-tracking ingestion pipeline with rejection status). |

---

### Target PT4: Compensation Under Stated Negotiation Scenarios

*How does an offer distribution shift if specific negotiation leverage or counterfactual conditions are introduced?*

| Dimension | Specification |
|:---|:---|
| **Mathematical Variable ($Y$)** | Counterfactual shift $\Delta Y = Y_{\text{final}} - Y_{\text{initial}}$ (INR LPA) and revised distribution $Q_\tau(Y_{\text{final}} | X, Z)$. |
| **Observation Unit** | A paired negotiation episode: $(Y_{\text{initial}}, Y_{\text{final}}, Z, X)$ where $Z$ represents negotiation context variables. |
| **Horizon** | Negotiation window: **7 to 30 Calendar Days** between initial verbal/written offer and final contract execution. |
| **Conditioning Covariates ($Z$)** | Context levers: presence of competing written offer ($\text{INR}$ value), current CTC anchoring, competing offer company tier, candidate willingness to walk away, skill uniqueness. |
| **Statistical Objective** | Estimating conditional uplift $\mathbb{E}[\Delta Y | X, Z]$ or shift function without parametric assumptions. |
| **Underlying Assumptions** | Negotiation dynamics depend on observable leverage $Z$ and employer budget elasticity. |
| **Identification Limits & Causal Caveats** | • **Zero Hard-Coded Multipliers (R-MD-07):** The system MUST NOT multiply baseline by an arbitrary constant (e.g. "+15% for competing offer").<br>• **Confounding & Ability Bias:** Candidates who negotiate hard often possess unobserved qualities (superior communication, high confidence, lower risk aversion) that cannot be causally transferred to another user.<br>• Must be explicitly presented as an observational association, never a promised outcome. |
| **Release Stage** | **Deferred / Experimental** (Blocked on verified negotiation telemetry). |

---

### Target PT5: Compensation Post-Transition or Skill Addition

*What is the expected compensation trajectory after switching role families or acquiring a high-demand skill stack?*

| Dimension | Specification |
|:---|:---|
| **Mathematical Variable ($Y$)** | Post-transition guaranteed cash $Y_{t + H}$ (INR LPA) and longitudinal delta $\Delta Y_H = Y_{t + H} - Y_t$. |
| **Observation Unit** | Longitudinal career transition record of individual $i$ who transitioned from role/stack $R_{\text{origin}}$ to $R_{\text{target}}$ at transition event $t_{\text{trans}}$. |
| **Settled Transition Horizon ($H$)** *(PRD [TBD: T1.01] Resolved)* | **12 to 24 Months Post-Transition.**<br>*Rationale:* A transition (e.g. Backend Engineer $\rightarrow$ Machine Learning Engineer, or QA Engineer $\rightarrow$ SDE) requires 3–6 months of onboarding, 6–12 months of demonstrated impact, and a subsequent annual appraisal or lateral market jump to reflect true market compensation in the new role. Evaluating at $<12\text{m}$ captures probationary/entry-discount compensation; evaluating at $>24\text{m}$ conflates standard career tenure with the transition event. |
| **Conditioning Covariates ($X$)** | Baseline profile $X_t$, target role $R_{\text{target}}$, acquired skill stack, pedigree/certification tier, and transition mechanism (internal transfer vs. external lateral hire). |
| **Statistical Objective** | Longitudinal treatment effect or trajectory quantile regression: $Q_\tau(Y_{t + H} | X_t, R_{\text{target}}, H)$. |
| **Underlying Assumptions** | Worker successfully passes transition hurdles and operates at the target role baseline. |
| **Identification Limits & Survivorship Bias** | • **Severe Survivorship Bias:** Observational data only shows those who *succeeded* in making the transition. Workers who attempted to transition but failed or returned to their original domain are missing.<br>• **Extrapolation Guard:** The system must actively prevent suggesting unrealistic transitions (e.g. manual tester with 10 YOE moving directly to Senior Research Scientist). |
| **Release Stage** | **Deferred / Experimental** (Requires multi-year panel/longitudinal dataset). |

---

### Target PT6: Current Compensation Benchmark against Market

*Where does an individual's current compensation sit relative to the empirical market distribution for their peer group?*

| Dimension | Specification |
|:---|:---|
| **Mathematical Variable ($Y$)** | Percentile positioning $P(Y \le y_{\text{user}} | X) \in [0, 100]$ and absolute delta $\Delta_{\text{median}} = y_{\text{user}} - Q_{0.50}(Y | X)$ in INR LPA. |
| **Observation Unit** | User-submitted verified compensation figure $y_{\text{user}}$ evaluated against the conditional PT1 model distribution and PT2 empirical cohort. |
| **Horizon** | As-of prediction date $t_0$. |
| **Conditioning Covariates ($X$)** | Matching PT1 covariates $X$. |
| **Statistical Objective** | Evaluate the cumulative distribution function $\hat{F}(y_{\text{user}} | X)$ using calibrated quantile interpolation. |
| **Underlying Assumptions** | User accurately inputs true annual guaranteed fixed cash (excluding bonuses, PF, gratuity, and equity) matching canonical definition. |
| **Identification Limits & UI Ethics** | • **Normative Language Invariant (FR-06):** The system MUST NEVER state that a user is "underpaid", "overpaid", "cheated", or "worth more".<br>• Must display as neutral statistical positioning: *"Your guaranteed cash sits within the 35th–45th percentile band for comparable profiles in our verified evidence pool."*<br>• Validity of PT6 is strictly bounded by the statistical validity of PT1. |
| **Release Stage** | **Research Prototype (RP) & Public Beta (PB)** |

---

## 3. Data Compatibility & Audit Matrix

This matrix provides the **binding evaluation rubric** for assessing candidate data sources (such as Kaggle datasets in T1.08, official Indian statistics in T1.06, and survey datasets in T1.05):

| Audit Requirement | PT1 (Market Profile) | PT2 (Cohort) | PT3 (Offers) | PT4 (Negotiation) | PT5 (Transition) | PT6 (Benchmark) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Guaranteed Cash Measure** | **Mandatory** | **Mandatory** | Desired | Desired | **Mandatory** | **Mandatory** |
| **Advertised Range Acceptable?** | No (proxy only) | No | **Primary** | No | No | No |
| **Total CTC Acceptable?** | Only if unbundlable | Only if unbundlable | Only if unbundlable | Only if unbundlable | Only if unbundlable | Only if unbundlable |
| **Observation Timestamp** | **Mandatory** ($<180\text{d}$) | **Mandatory** ($<365\text{d}$) | Mandatory | Mandatory | **Mandatory** (Longitudinal) | **Mandatory** |
| **Location (India City/Tier)** | **Mandatory** | **Mandatory** | Mandatory | Mandatory | Mandatory | **Mandatory** |
| **Experience / YOE** | **Mandatory** | **Mandatory** | Mandatory | Mandatory | **Mandatory** | **Mandatory** |
| **Employer Tier / Context** | Desired | Desired | **Mandatory** | **Mandatory** | Desired | Desired |
| **Offer Acceptance Status** | N/A | N/A | **Mandatory** | **Mandatory** | N/A | N/A |
| **Longitudinal Worker ID** | N/A | N/A | N/A | Desired | **Mandatory** | N/A |
| **Minimum Cell Count ($N$)** | $N \ge 30$ per slice | $N \ge 10$ ($k \ge 5$) | $N \ge 50$ | $N \ge 30$ episodes | $N \ge 50$ transitions | Inherits PT1 |

---

## 4. Immediate Research Directives (T1.08 & T1.06 Coordination)

With PT1 through PT6 formally specified, the candidate dataset audits proceed under explicit target filters:

1. **Kaggle Audit (T1.08):**
   - Every candidate dataset must be classified against:
     - **Eligible for PT1 training:** Contains Indian tech compensation, clear observation date, YOE, role, and isolatable fixed cash.
     - **Benchmark / Feature discovery only:** Contains developer profiles (e.g. Stack Overflow / global tech surveys) useful for skill-to-role mappings or experience distributions, but target is total compensation or non-Indian.
     - **Test-fixture only:** Small or synthetic datasets ($N < 500$ or single-city) useful for testing parsing and pipeline plumbing.
     - **Rejected:** Unverifiable scrape of consumer portals, ambiguous measure, or missing key covariates.
2. **Indian Official Sources (T1.06):**
   - Evaluate PLFS and Labour Bureau microdata as **Layer 1 Macro Benchmarks**: assess whether National Classification of Occupations (NCO-2015) codes 2512 (Software Developers), 2511 (Systems Analysts), and 2521 (Database Designers) contain sufficient wage observations in urban centers (Bengaluru, Pune, Hyderabad, NCR) to serve as a macro anchor.

---

*Authored for ArthaIQ under Phase 1, Task T1.01.*
