# Scope Recommendation Memo & Strategic Trade-Off Analysis (T1.13)

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/08-scope-memo.md` |
| **Task** | T1.13 — Scope Recommendation Memo with Alternatives & Kill Criteria |
| **Status** | Ratified v1.0 |
| **Date** | 2026-10-13 |
| **Governs** | ADR-0001, ADR-0002, Gate G1 Review, Phase 2 Pre-Registration (`experiments/preregistration/sufficiency-v1.yaml`) |
| **Methodological Invariants** | `D-004` (India First Scope $H_0$); `D-010` (Decoupled Evidence Framework); `R-WF-01` (No skipping ahead); `R-DA-01` (Zero scraping); `R-MD-07` (No uniform unbundling heuristics). |

---

## 1. Executive Summary & Recommendation

Based on the cumulative evidence synthesized across Phase 1—including target formalization (`01-targets.md`), canonical compensation accounting (`02-comp-definitions.md`), user research protocol (`03-users.md`), official source audits (`04-source-catalog.md`), the 20-candidate Kaggle audit (`kaggle-dataset-audit-v0.1.md`), the 32-source quality scoring framework (`05-source-scoring.md`), the 13-component architecture autopsy (`06-architecture-autopsy.md`), and the 15-risk premortem (`07-premortem-risk-register.md`)—this memo delivers the definitive scope recommendation for ArthaIQ's initial production pipeline:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ARTHAIQ RECOMMENDED INITIAL SCOPE (H0)                          │
│                                                                                        │
│  1. TARGET GEOGRAPHY & MARKET:                                                         │
│     India (Domestic Resident Employment, Urban Tech Centers)                          │
│                                                                                        │
│  2. OCCUPATIONAL FAMILY:                                                               │
│     Software Engineering, Data Science, and Machine Learning / AI                      │
│     (Standardized crosswalks: NCO-2015 2512/2511; SOC-2018 15-1252/15-2051)            │
│                                                                                        │
│  3. CANONICAL TARGET MEASURE:                                                          │
│     guaranteed_cash_annual (Nominal INR Lakhs Per Annum / LPA)                         │
│     Contractually committed, fixed pre-tax cash compensation; strictly unbundled from   │
│     discretionary bonuses, statutory employer PF/gratuity, and equity.                 │
│                                                                                        │
│  4. PREDICTION TARGET PRIORITIZATION:                                                  │
│     Phase 1–6 Primary Focus: PT1 (Market Pay for Profile) & PT2 (Comparable Cohort)    │
│     Contextual Distribution Anchor: PT6 (Current Pay vs Macro Distribution)            │
│     Explicitly Deferred Targets: PT3 (Advertised Postings), PT4 & PT5 (Scenarios)      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Strategic Rationale for Recommended Scope

### 2.1 Why India First?
1. **Acute Information Asymmetry & Market Inefficiency:**
   Unlike the United States—where public regulatory wage disclosures (DOL H-1B LCA, PERM), state salary transparency laws (California, New York, Colorado, Washington), and established platforms (Levels.fyi, Blind) have partially commoditized tech salary transparency—the Indian technology ecosystem suffers from acute structural opacity. Employers leverage complex "Cost to Company" (CTC) accounting tricks to inflate headline offers while depressing guaranteed monthly cash flow (`02-comp-definitions.md`).
2. **Massive Addressable Base:**
   India houses over 5.4 million technology professionals (NASSCOM 2024), representing the world's largest digital talent exporter and fastest-growing domestic product and Global Capability Center (GCC) ecosystem. Over 70% of tech hiring occurs across 6 primary urban clusters (Bengaluru, Hyderabad, Pune, Delhi-NCR, Chennai, Mumbai), providing dense geographic concentration for modeling.
3. **Macro Anchor Availability:**
   The Ministry of Statistics and Programme Implementation (MOSPI) conducts the Periodic Labour Force Survey (PLFS), providing an audited, unit-level probability microdata anchor (`SRC-IND-OFF-01`, $N \approx 2,200$ tech professionals) that establishes population wage floors and urban graduate percentiles (`PT6`).

### 2.2 Why Software Engineering, Data Science & ML/AI?
1. **Taxonomic Cohesion:**
   Software and data roles exhibit well-defined, standardized skill ontologies (O*NET 29.0 `SOC 15-1252`, ESCO v1.1) and clear career ladders (`L1` to `L5`), unlike amorphous corporate roles (e.g. "Operations Manager" or "Business Executive").
2. **High Returns to Observable Covariates:**
   Tech compensation displays high, measurable elasticity with respect to observable technical skills, continuous years of experience ($YOE$), and employer tier (Product vs GCC vs IT Services).
3. **Data Availability in Open Benchmarks:**
   The Stack Overflow Annual Developer Survey (`SRC-KAG-13`, $N_{\text{India}} \approx 4,500$) provides verified, permissive ($ODbL\ 1.0$) data specifically covering this occupational cohort, enabling empirical modeling of non-linear experience curves and skill relative deltas.

### 2.3 Why `guaranteed_cash_annual` (Nominal INR LPA)?
1. **Legal & Financial Contract Reality:**
   Fixed cash (Basic + HRA + Special Allowance) is the only legally binding, contractually guaranteed financial commitment an employer makes to an employee. Variable bonuses are discretionary and subject to company EBITDA gates; equity is illiquid or subject to 4-year vesting cliffs; employer PF and gratuity are statutory overhead costs (`02-comp-definitions.md`).
2. **Direct Practical Decision Utility (JTBD):**
   When a software engineer evaluates a job offer or plans household expenses (rent, EMIs, savings), they require certainty regarding their guaranteed bank credits. Predicting bundled CTC creates "paper wealth" illusions that mislead users.
3. **Measurement Tractability:**
   Fixed cash avoids the intractable valuation problems of private startup stock options, down-round dilution, and fluctuating public equity stock prices.

---

## 3. Rigorous Evaluation of Competing Alternatives

To avoid confirmation bias, three competing scope alternatives were evaluated against five criteria: **Data Feasibility**, **Target Cleanliness**, **Legal Defensibility**, **Market Impact**, and **Execution Complexity**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        COMPETING SCOPE ALTERNATIVES TRADE-OFF                          │
│                                                                                        │
│  Criteria             │ Alternative A:     │ Alternative B:     │ Alternative C:       │
│                       │ US Tech First      │ All-India Occup.   │ India Total CTC      │
│  ─────────────────────┼────────────────────┼────────────────────┼────────────────────  │
│  Data Feasibility     │ HIGH (BLS, LCA)    │ MODERATE (PLFS)    │ HIGH (Scraped CSVs)  │
│  Target Cleanliness   │ HIGH (Base USD)    │ LOW (Heterogeneous)│ FATAL COLLAPSE (CTC) │
│  Legal Defensibility  │ HIGH (Public Data) │ HIGH (Open Govt)   │ ZERO (ToS Scrapes)   │
│  Market Differentiation│ ZERO (Levels.fyi) │ LOW (Diffuse)      │ NEGATIVE (Misleading)│
│  Execution Complexity │ MODERATE           │ SEVERE (High noise)│ HIGH (Heuristics)    │
│  ─────────────────────┼────────────────────┼────────────────────┼────────────────────  │
│  OVERALL DISPOSITION  │ REJECTED           │ REJECTED           │ REJECTED             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Alternative A: US Technology Market First
* **Description:** Launching ArthaIQ for US software engineers, using BLS OEWS (`SRC-USA-BLS-01`) and Department of Labor H-1B/PERM filings (`SRC-USA-DOL-01/02`).
* **Why It Was Rejected:**
  - **Zero Competitive Differentiation:** The US tech market is saturated with established compensation platforms (Levels.fyi, Team Blind, Comprehensive.io, Carta, Pave). An early-stage project cannot out-compete established US incumbents on employer coverage.
  - **Misalignment with Problem Statement:** US tech compensation is heavily dominated by public equity RSUs ($40\text{--}60\%$ of total comp at Senior levels), whereas ArthaIQ's core unbundling and macro anchor innovations address India's CTC opacity.
  - **Disposition:** Retained strictly as an auxiliary cross-market benchmark (`SRC-USA-*`), isolated from domestic training pools.

### Alternative B: Broad All-Occupations India Market
* **Description:** Predicting compensation for all salaried occupations in India (finance, manufacturing, retail, healthcare, administrative) using PLFS microdata nationwide.
* **Why It Was Rejected:**
  - **Severe Unobserved Heterogeneity:** Non-tech sectors in India lack standardized leveling, have high informal/cash salary components, and exhibit extreme regional fragmentation that cannot be resolved without enterprise-specific HR data.
  - **Diluted Value Proposition:** Attempting to serve all white-collar jobs guarantees mediocre accuracy for everyone and exceptional utility for none.
  - **Disposition:** Rejected. Focus remains exclusively on technology professionals.

### Alternative C: Predicting Total Cost to Company (CTC) First
* **Description:** Modeling headline CTC by ingesting public Kaggle job portal scrapes (Naukri, AmbitionBox, Glassdoor) and outputting single CTC numbers.
* **Why It Was Rejected:**
  - **Fatal Legal Liability:** Scraped job portal datasets violate platform Terms of Service, triggering copyright and IT Act liabilities (`R-DA-01`, Premortem `FM-01`).
  - **Accounting Hallucination:** CTC bundles discretionary bonuses, gratuity reserves, employer PF, and paper ESOPs into an arbitrary aggregate. Predicting CTC validates misleading employer recruiting tactics and violates rule `R-MD-07`.
  - **Disposition:** Categorically rejected. CTC is unbundled or quarantined.

---

## 4. Pre-Registered Kill Criteria & Stop Rules (Phase 2 Gates)

To ensure scientific honesty and prevent sunk-cost fallacy, ArthaIQ pre-registers explicit, falsifiable **Kill Criteria** that mandate halting the project or pivoting scope before entering Phase 3 modeling:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PRE-REGISTERED KILL CRITERIA & STOP RULES                       │
│                                                                                        │
│  🛑 KILL CRITERION 1: Data Sufficiency Failure at Gate G2                              │
│     Condition: If at the conclusion of Phase 2 (Task T2.09), approved sources cannot   │
│     satisfy the pre-registered cell sample floor (N_eff >= 50 for at least 6 core tech │
│     cells: SWE Junior, Mid, Senior; Data Mid, Senior; ML Senior in Tier-1 cities).     │
│     Mandatory Action: HALT ALL ML MODELING. Do NOT write baseline or GBM code.         │
│     Pivot immediately to the Governed Voluntary Intake Program (T2.10 / ADR-0008).     │
│                                                                                        │
│  🛑 KILL CRITERION 2: Legal / Terms of Service Breach at Task T2.02                    │
│     Condition: If a shortlisted candidate source is found to rely on unauthorized      │
│     automated scraping, private database misappropriation, or restrictive ToS.        │
│     Mandatory Action: IMMEDIATE DISQUALIFICATION AND QUARANTINE. Zero data from that   │
│     source enters data/raw/ or feature pipelines.                                      │
│                                                                                        │
│  🛑 KILL CRITERION 3: Conformal Calibration Collapse at Gate G5                        │
│     Condition: If out-of-sample conformal prediction coverage on the forward temporal   │
│     hold-out test set falls below 70.0% (target 80.0%) and adaptive recalibration      │
│     fails to restore coverage within 3 iterations.                                     │
│     Mandatory Action: HALT PUBLIC BETA RELEASE. The model must not be deployed to      │
│     users; re-enter Phase 4 to re-examine feature definitions and market drift.        │
│                                                                                        │
│  🛑 KILL CRITERION 4: Quantile Inversion Floor Breach                                  │
│     Condition: If uncalibrated tree models produce crossing quantiles (P10 > P50 or    │
│     P50 > P90) on more than 5.0% of out-of-sample evaluation queries.                  │
│     Mandatory Action: REJECT STANDALONE QUANTILE GBM. Enforce simultaneous multi-      │
│     quantile joint loss or fall back to Rung C (Empirical Bayes partial pooling).       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Next Steps for Gate G1 Ratification

With this Scope Recommendation Memo finalized:
1. Advance **ADR-0001** (`docs/adr/ADR-0001-initial-market-and-occupation-scope.md`) to **Accepted / Ratified at Gate G1**.
2. Advance **ADR-0002** (`docs/adr/ADR-0002-primary-target-and-compensation-measure.md`) to **Accepted / Ratified at Gate G1**.
3. Submit Phase 1 research documentation suite to the User for **Gate G1 Ratification Review**.

---

*Authored for ArthaIQ under Phase 1, Task T1.13. Formally establishes the recommended scope, trade-off rationale, competing alternatives, and pre-registered kill criteria.*
