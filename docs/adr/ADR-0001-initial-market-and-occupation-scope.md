# ADR-0001: Initial Market and Occupation Scope

| Field | Value |
|---|---|
| Status | **Final Accepted / Ratified at Gate G2** |
| Decided at | Phase 2 Gate G2 (2026-10-14; initially proposed at Gate G1 2026-10-13) |
| Relates to | PRD section 4, `memory.md` D-004, `docs/research/08-scope-memo.md`, `docs/research/09-sufficiency-analysis.md`, `docs/research/10-data-acquisition-plan.md` |

---

## Context

ArthaIQ requires a defensible initial market and occupational scope. The Master Research Prompt dictates identifying the most practically achievable and defensible initial market rather than assuming a single global model can support all markets from inception. Scope hypothesis $H_0$ was established at Gate G0 and subjected to empirical evaluation across Phase 1 research and Phase 2 data profiling, prototype construction, and data sufficiency testing (Tasks T2.01 to T2.10).

## Evaluated Options

| Option | Pros | Cons | Disposition |
|---|---|---|---|
| **Option 1 ($H_0$): India, Software Engineering / Data / ML/AI** | Acute information asymmetry; massive addressable population (5.4M+); dense urban tech hubs; PLFS macro anchor exists; Stack Overflow benchmark available. | CTC accounting unbundling is complex; upper tech tail censored in household surveys; requires governed voluntary intake (T2.10). | **ADOPTED AS PRIMARY SCOPE** |
| **Option 2: United States Tech Market First** | Well-documented public disclosures (BLS OEWS, DOL LCA/PERM); standardized base salary reporting. | Saturated competitive landscape (Levels.fyi, Blind, Carta); high RSU dominance; misses ArthaIQ's core unbundling value proposition. | **REJECTED AS PRIMARY** (Retained as cross-market benchmark) |
| **Option 3: Broad All-Occupations India Market** | Maximum theoretical population coverage. | Severe unobserved heterogeneity; non-standard leveling; informal cash pay; dilutes predictive accuracy. | **REJECTED** |

## Decision

1. **Market:** **India (`IND`)**, focused on domestic salaried technology employment across primary urban tech hubs (Bengaluru, Hyderabad, Pune, Delhi-NCR, Chennai, Mumbai). Nominal currency: **Indian Rupee (INR)**, expressed in **Lakhs Per Annum (LPA)**.
2. **Occupational Family:** **Software Engineering, Data Science, and Machine Learning / AI**, standardized under `NCO-2015` codes `2512` (Software Developers), `2511` (Systems Analysts), `2521` (Database Designers), and crosswalked to `SOC-2018 15-1252` and `O*NET 29.0`.
3. **Gate G2 Operational Ratification & Acquisition Mandate:**
   * At Gate G2 (Task T2.09), public sources yielded $N_{\text{eff}} = 0.0$ for unbundled guaranteed cash (`guaranteed_cash_annual`), triggering Kill Criterion 1 and halting Phase 3 modelling on existing public datasets (`R-WF-01`).
   * Rather than abandoning the India tech market or resorting to illegal scraping (`R-DA-01`) or invalid multipliers (`R-MD-07`), ArthaIQ ratifies the primary scope in conjunction with the **Primary Data Acquisition Programme (Task T2.10 / `docs/research/10-data-acquisition-plan.md`)**.
   * Ground truth observations are acquired via Governed Voluntary Intake (`SRC-INT-VOL-01`) and B2B Employer Syndication (`SRC-INT-CORP-01`) targeting $N_{\text{eff}} \ge 50$ across 12 core cells (780 core records).
4. **Pre-Registered Contingency Scope Boundary:** If after 90 days of acquisition, core cells outside Bengaluru fail to reach $N_{\text{eff}} \ge 50$, this ADR automatically triggers Scope Narrowing: restricting operations to **Bengaluru Software Engineering Professionals Only** ($H_{\text{narrowed}}$).

## Consequences

- All Phase 3 data contracts (`src/compintel/schema/`), taxonomy definitions, and ingestion pipelines are locked to Indian tech roles in INR LPA.
- Cross-market US data from BLS and DOL is permanently segregated into dedicated USD tables and never pooled with Indian domestic records via currency conversions (`R-MD-07`, `R-MD-08`).
- The primary evaluation benchmarks are calibrated against Indian technology career ladders (`L1` to `L5`).
- Phase 3 machine learning baseline training is gated until voluntary intake reaches the pre-registered sample size floor ($N_{\text{eff}} \ge 50$ for core cells).

## Evidence & Verification

| Claim | Source / Document | Status |
|---|---|---|
| MOSPI PLFS microdata covers Indian tech occupations (`NCO 2512`) | `docs/research/04-source-catalog.md` (`SRC-IND-OFF-01`) | **VERIFIED** ($N \approx 2,200$ urban tech cohort; Macro Anchor) |
| US BLS OEWS covers software and ML titles | `docs/research/04-source-catalog.md` (`SRC-USA-BLS-01`) | **VERIFIED** (SOC 15-1252; Approved US Benchmark) |
| Public Kaggle salary CSVs lack legal provenance for Indian tech training | `docs/research/kaggle-dataset-audit-v0.1.md` | **VERIFIED** (0 of 20 training-eligible; 10 rejected; ToS scrapes) |
| Scope trade-offs and stop rules formalization | `docs/research/08-scope-memo.md` | **VERIFIED** (Full trade-off analysis ratified) |
| Public data sufficiency failure (Kill Criterion 1) | `docs/research/09-sufficiency-analysis.md` | **VERIFIED** (0/12 core cells pass C1; NO-GO ratified) |
| Smallest viable data acquisition plan | `docs/research/10-data-acquisition-plan.md` | **VERIFIED** (₹18.5L budget, 780 core target, DPDPA 2023) |

## Change Log

| Date | Author | Change |
|---|---|---|
| 2026-10-13 | AI / Human | Stub created at T0.04 |
| 2026-10-13 | AI / Human | Updated to Ratified at Gate G1 following T1.13 Scope Memo synthesis |
| 2026-10-14 | AI / Human | Finalized and Accepted at Gate G2 (T2.11) following T2.09 Sufficiency Evaluation and T2.10 Acquisition Plan |
