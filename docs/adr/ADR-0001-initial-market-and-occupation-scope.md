# ADR-0001: Initial Market and Occupation Scope

| Field | Value |
|---|---|
| Status | **Accepted / Ratified at Gate G1** (Operational validation at Gate G2) |
| Decided at | Phase 1 Gate G1 (2026-10-13) |
| Relates to | PRD section 4 (H0), `memory.md` D-004, `docs/research/08-scope-memo.md` |

---

## Context

ArthaIQ requires a defensible initial market and occupational scope. The Master Research Prompt dictates identifying the most practically achievable and defensible initial market rather than assuming a single global model can support all markets from inception. Scope hypothesis $H_0$ was established at Gate G0 and subjected to rigorous empirical evaluation across Phase 1 research (Tasks T1.06, T1.07, T1.08, T1.09, T1.10, T1.12, and T1.13).

## Evaluated Options

| Option | Pros | Cons | Disposition |
|---|---|---|---|
| **Option 1 ($H_0$): India, Software Engineering / Data / ML/AI** | Acute information asymmetry; massive addressable population (5.4M+); dense urban tech hubs; PLFS macro anchor exists; Stack Overflow benchmark available. | CTC accounting unbundling is complex; upper tech tail censored in household surveys; requires governed voluntary intake (T2.10). | **ADOPTED AS PRIMARY SCOPE** |
| **Option 2: United States Tech Market First** | Well-documented public disclosures (BLS OEWS, DOL LCA/PERM); standardized base salary reporting. | Saturated competitive landscape (Levels.fyi, Blind, Carta); high RSU dominance; misses ArthaIQ's core unbundling value proposition. | **REJECTED AS PRIMARY** (Retained as cross-market benchmark) |
| **Option 3: Broad All-Occupations India Market** | Maximum theoretical population coverage. | Severe unobserved heterogeneity; non-standard leveling; informal cash pay; dilutes predictive accuracy. | **REJECTED** |

## Decision

1. **Market:** **India (`IND`)**, focused on domestic salaried technology employment across primary urban tech hubs (Bengaluru, Hyderabad, Pune, Delhi-NCR, Chennai, Mumbai). Nominal currency: **Indian Rupee (INR)**, expressed in **Lakhs Per Annum (LPA)**.
2. **Occupational Family:** **Software Engineering, Data Science, and Machine Learning / AI**, standardized under `NCO-2015` codes `2512` (Software Developers), `2511` (Systems Analysts), `2521` (Database Designers), and crosswalked to `SOC-2018 15-1252` and `O*NET 29.0`.
3. **Conditionality:** This scope is ratified for Phase 2 data acquisition and profiling. It remains subject to the **Gate G2 Data Sufficiency Verification** (`experiments/preregistration/sufficiency-v1.yaml`). If approved sources fail to meet cell sufficiency thresholds ($N_{\text{eff}} \ge 50$ for core tech cells), modeling is halted immediately and the scope is reviewed.

## Consequences

- All Phase 2 data ingestion configs (`config/sources/*.yaml`), taxonomy files (`config/taxonomy/`), and schema contracts are locked to this scope.
- Cross-market US data from BLS and DOL is permanently segregated into dedicated USD tables and never pooled with Indian domestic records via currency conversions (`R-MD-07`).
- The primary evaluation benchmarks are calibrated against Indian technology career ladders (`L1` to `L5`).

## Evidence & Verification

| Claim | Source / Document | Status |
|---|---|---|
| MOSPI PLFS microdata covers Indian tech occupations (`NCO 2512`) | `docs/research/04-source-catalog.md` (`SRC-IND-OFF-01`) | **VERIFIED** ($N \approx 2,200$ urban tech cohort; Macro Anchor) |
| US BLS OEWS covers software and ML titles | `docs/research/04-source-catalog.md` (`SRC-USA-BLS-01`) | **VERIFIED** (SOC 15-1252; Approved US Benchmark) |
| Public Kaggle salary CSVs lack legal provenance for Indian tech training | `docs/research/kaggle-dataset-audit-v0.1.md` | **VERIFIED** (0 of 20 training-eligible; 10 rejected; ToS scrapes) |
| Scope trade-offs and stop rules formalization | `docs/research/08-scope-memo.md` | **VERIFIED** (Full trade-off analysis ratified) |

## Change Log

| Date | Author | Change |
|---|---|---|
| 2026-10-13 | AI / Human | Stub created at T0.04 |
| 2026-10-13 | AI / Human | Updated to Ratified at Gate G1 following T1.13 Scope Memo synthesis |
