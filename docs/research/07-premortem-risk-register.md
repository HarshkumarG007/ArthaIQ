# Premortem Analysis & Full Risk Register (T1.12)

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/07-premortem-risk-register.md` |
| **Task** | T1.12 — Premortem and Full Risk Register |
| **Status** | Ratified v1.0 |
| **Date** | 2026-10-13 |
| **Governs** | Phase 2–9 Implementation Tasks, Gate G1–G6 Readiness, Security & Compliance Reviews (`T9.12`) |
| **Methodological Invariants** | `R-WF-01` (No skipping ahead); `R-DA-01` (Zero scraping liability); `R-MD-07` (No hard-coded multipliers); `R-UQ-01` (Honest uncertainty quantification & abstention); `R-EV-03` (Never invent facts). |

---

## 1. Executive Summary & Premortem Mandate

A **Premortem** is an adversarial forecasting exercise: we assume that the project has launched, suffered an catastrophic failure, and been completely shut down or discredited. By analyzing the most plausible failure paths *before* building model code, we can design definitive engineering safeguards and pre-register explicit mitigation tasks.

### The Premortem Scenario (Simulated Retrospective: October 2027)

> *"Twelve months after launch, ArthaIQ has been permanently shut down. Its public API is offline, its GitHub repository is frozen, and its founders face legal inquiries and reputational ruin. A junior engineer in Pune relied on ArthaIQ's narrow salary prediction to reject an 8.5 LPA fixed offer, expecting an offer of 18 LPA; after 7 months of unemployment, they discovered ArthaIQ's model had collapsed on an unweighted scraped Kaggle dataset that conflated headline CTC with fixed pay. Simultaneously, a Bengaluru fintech received a cease-and-desist from a listed recruitment portal whose proprietary database was traced into ArthaIQ's feature pipeline, while India's Data Protection Board levied statutory penalties under DPDPA 2023 for disclosing small-startup compensation bands with $k=1$ employee anonymity violations."*

This failure did not occur through bad luck. It was the predictable consequence of seven fatal systemic errors:
1. **The Legal Poison Pill:** Ingesting unauthorized scraped datasets masquerading as "open data."
2. **The Target Conflation Disaster:** Failing to unbundle headline CTC from contractual fixed cash.
3. **The False Precision Trap:** Predicting narrow intervals in sparse cells instead of honestly abstaining.
4. **The Temporal Calibration Collapse:** Silent distribution drift during tech market downturns.
5. **The Causal Advice Backfire:** Users mistaking descriptive attributions for guaranteed career advice.
6. **The De-Anonymization Breach:** Violating $k$-anonymity on boutique startups.
7. **The Infrastructure Bloat Exhaustion:** Overengineering latency and compute costs before product-market fit.

---

## 2. Seven Catastrophic Failure Modes & Built-in Safeguards

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          SEVEN FATAL PREMORTEM FAILURE MODES                           │
│                                                                                        │
│  [FM-01] Legal & Copyright Expropriation (Scraped Data Poison Pill)                    │
│  [FM-02] Compensation Accounting Conflation (CTC vs Fixed Cash Hallucination)         │
│  [FM-03] Overconfident Sparse-Cell Extrapolation (Zero Data Support Failure)           │
│  [FM-04] Macro Drift & Calibration Collapse (Out-of-Exchangeability Ruin)              │
│  [FM-05] Causal Advice Misinterpretation (Feature Attribution Backfire)                │
│  [FM-06] Re-Identification & Statutory Privacy Breach (DPDPA 2023 Penalty)             │
│  [FM-07] Operational Complexity & Latency Asphyxiation (Overengineered Stack)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Failure Mode 01: Legal & Copyright Expropriation (Scraped Data Poison Pill)
* **What Happened:** An engineer ingested Kaggle candidate CSVs containing scraped job portal records (Naukri, AmbitionBox, Glassdoor, Levels.fyi) because "they were already public on Kaggle." Portal legal teams filed copyright infringement, database theft, and Computer Fraud/IT Act Section 43/66 notices.
* **Why It Succeeded in Crashing the Project:** The team treated Kaggle's claimed `CC0` license at face value without tracing upstream provenance.
* **Hard Architectural Safeguard:**
  - Automated CI license barrier (`Task T2.02` & `T9.12`): `config/sources/*.yaml` schema forbids ingestion of any source whose `licensing.terms_verified` is false or whose provenance indicates automated scraping of gated portals (`R-DA-01`).
  - Pre-commit hook hashes and blocks unauthorized CSV files in `data/raw/`.

---

### Failure Mode 02: Compensation Accounting Conflation (The CTC Bait-and-Switch)
* **What Happened:** The model was trained on datasets measuring headline CTC, while the user entered fixed salary. A user received an offer stating "₹22 LPA CTC," input their current ₹16 LPA fixed, and the system claimed they were getting a ₹6 LPA raise. When their monthly bank credit arrived, ₹7 LPA of the new offer was unvested 4-year ESOPs and ₹3 LPA was employer PF/gratuity; their take-home pay actually dropped by 15%.
* **Why It Succeeded in Crashing the Project:** The team used uniform heuristics (e.g. `fixed = 0.82 * CTC`) to force-fit mixed datasets, violating `R-MD-07`.
* **Hard Architectural Safeguard:**
  - Mandatory line-item unbundling equation (`02-comp-definitions.md`).
  - Strict quarantine rule: Any dataset or contribution lacking itemized line items (`basic`, `hra`, `special_allowance`, `variable_pay`, `equity`) is permanently quarantined from PT1 training tables. Zero hard-coded multipliers permitted (`R-MD-07`).

---

### Failure Mode 03: Overconfident Sparse-Cell Extrapolation (Zero Data Support Failure)
* **What Happened:** A user requested a prediction for an ML Compiler Engineer in Kochi with 11 YOE at an early-stage startup. The training set contained zero observations in Kochi and zero ML compiler engineers. Instead of declining, the Gradient Boosted Tree happily extrapolated across tree leaves, outputting a tight interval of [₹38 LPA, ₹44 LPA]. True local clearing rate was ₹18 LPA. The user rejected a fair local offer and blamed ArthaIQ.
* **Why It Succeeded in Crashing the Project:** The system conflated point-estimate generation with statistical support. It lacked an honest abstention contract.
* **Hard Architectural Safeguard:**
  - Decoupled Evidence Framework (`D-010`): Before generating a prediction, the query must pass the **Local Prediction Support Metric (PSM)**:
    $$U(x) = \sum_{i \in \mathcal{D}} K\left(\frac{d(x_i, x)}{h}\right) \ge N_{\text{min}}$$
  - If $U(x) < \text{threshold}$, the API returns `status: "abstained"` with machine-readable reason code `REASON_SPARSE_CELL` (`R-UQ-01`, `R-UQ-06`).

---

### Failure Mode 04: Macro Drift & Calibration Collapse (Out-of-Exchangeability Ruin)
* **What Happened:** Conformal prediction intervals were calibrated on 2021–2022 tech hiring data. When market clearing rates adjusted downward during the 2023–2024 global funding correction, test coverage dropped from the promised 80% to 38%. Users consistently found realized offers falling below the lower bound $P_{10}$.
* **Why It Succeeded in Crashing the Project:** The team assumed static exchangeability between past observations and future economic periods.
* **Hard Architectural Safeguard:**
  - Forward Temporal Calibration (`Task T4.08` & `T5.05`): Calibration sets $\mathcal{D}_{\text{cal}}$ must be strictly held out temporally ($t_{\text{cal}} > t_{\text{train}}$).
  - Mandatory CPI-Urban indexation (`SRC-SUP-MAC-01`) deflating historical nominal rupees to prediction timestamp $t_0$.
  - Continuous drift monitoring (`Task T9.11`) triggering automated coverage re-verification on rolling 90-day batches.

---

### Failure Mode 05: Causal Advice Misinterpretation (Feature Attribution Backfire)
* **What Happened:** ArthaIQ displayed SHAP feature bars indicating: `+₹6.5 LPA for Apache Spark skill`. An unemployed candidate spent 4 months and ₹80,000 on Spark certification, but was rejected by 30 companies because local startups were hiring Go/React generalists. The candidate publicly sued ArthaIQ for false advertising and deceptive career claims.
* **Why It Succeeded in Crashing the Project:** The UI presented observational feature correlations as actionable, counterfactual causal recommendations.
* **Hard Architectural Safeguard:**
  - Strict Causal Boundary Invariant (`R-MD-10`, `01-targets.md`): The UI and API must explicitly forbid language implying causation (e.g. "Learning X will increase your pay by Y").
  - Attribution statements are strictly descriptive: *"In our historical dataset, profiles containing Apache Spark reported higher median compensation; this reflects unobserved seniority and company tier differences, not a guaranteed return to the skill alone."*

---

### Failure Mode 06: Re-Identification & Statutory Privacy Breach (DPDPA 2023 Penalty)
* **What Happened:** An employee at a 12-person Bengaluru AI boutique contributed their salary. ArthaIQ published an estimate for `AI Startup, Seed Stage, Koramangala, 3 YOE`. The founder checked ArthaIQ, recognized the exact profile of their sole data scientist, and fired them. The Data Protection Board of India levied an administrative penalty under Section 33 of the Digital Personal Data Protection Act, 2023.
* **Why It Succeeded in Crashing the Project:** The system failed to enforce $k$-anonymity across small employers.
* **Hard Architectural Safeguard:**
  - Mandatory $k$-Anonymity Floor ($k \ge 5$) (`R-DA-10`): No prediction, benchmark, or corporate median is ever displayed or queried if the underlying cell contains fewer than 5 unique verified individuals.
  - Employer names are permanently salt-hashed; boutique startups ($<50$ employees) are automatically anonymized into aggregate company tiers (`Early-Stage Startup`, `Series A-B`, `Bootstrapped`).

---

### Failure Mode 07: Operational Complexity & Latency Asphyxiation (Overengineered Stack)
* **What Happened:** The engineering team deployed a vector database, PyTorch sentence transformers on GPU clusters, and an un-indexed PostgreSQL instance. Cold boots took 45 seconds; API latency was 2,400 ms; cloud hosting cost $3,800/month. The project burned through its budget before achieving data sufficiency.
* **Why It Succeeded in Crashing the Project:** The team chased resume-driven architectural fads instead of building the simplest credible system.
* **Hard Architectural Safeguard:**
  - The Banned Technology Rule (`R-MD-09`): Distributed compute, GPUs, Graph Neural Networks, and Vector Databases are banned by default.
  - Architecture Profile A: Entire system runs in-process on CPU using Polars, DuckDB, Parquet, and LightGBM with query latency $<20$ ms and zero cloud database hosting costs during prototyping.

---

## 3. Comprehensive Risk Register (15 Systemic Risks)

The risk register below formalizes all identified technical, legal, statistical, product, and operational risks. Each risk is evaluated by:
* **Severity (S):** $1 = \text{Negligible}$ to $5 = \text{Catastrophic Project Death}$.
* **Likelihood (L):** $1 = \text{Rare}$ to $5 = \text{Almost Certain without Controls}$.
* **Risk Priority Number (RPN):** $\text{RPN} = S \times L$ (Scale: $1\text{--}25$). Risks with $\text{RPN} \ge 15$ are **Critical Blockers**.

| Risk ID | Risk Category | Risk Summary & Trigger Condition | S | L | RPN | Root Cause | Mandatory Safeguard & Pre-Registered Mitigation Task | Governed Rule / Task |
|:---:|:---|:---|:---:|:---:|:---:|:---|:---|:---|
| **RSK-01** | Legal / IP | Ingestion of scraped job portal data triggering ToS breach and copyright lawsuits. | **5** | **4** | **20** | Relying on unverified Kaggle upload tags without upstream provenance tracing. | **Task T2.02:** Full license register; CI blocks any source not flagged `approved`. Reject all scraped datasets. | `R-DA-01`, `R-DA-02` |
| **RSK-02** | Target Integrity | Training models on bundled CTC or advertised postings, polluting PT1 guaranteed cash. | **5** | **4** | **20** | Conflating advertised range / CTC with realized fixed cash; applying uniform percentage multipliers. | **Task T2.05 & T3.02:** Quarantine all observations without itemized basic/hra/allowances. Strictly forbid hard-coded multipliers. | `R-MD-07`, `02-comp-definitions.md` |
| **RSK-03** | Statistical / UQ | Reporting narrow, confident intervals for rare or unobserved profiles ($N_{\text{cell}} = 0$). | **5** | **4** | **20** | Global tree models extrapolating blindly into empty covariate space without support checks. | **Task T4.04 & T5.03:** Decoupled Evidence Support Metric $U(x)$. Abstain with reason code `REASON_SPARSE_CELL` when support $< N_{\text{min}}$. | `D-010`, `R-UQ-01`, `R-UQ-06` |
| **RSK-04** | Privacy / Legal | De-anonymization of individual employees at small tech startups violating DPDPA 2023. | **5** | **3** | **15** | Granular filtering on boutique company names with sparse worker populations ($k < 5$). | **Task T2.09 & T9.12:** Enforce $k$-anonymity ($k \ge 5$). Salt-hash employer identities; bucket firms $<50$ into generic tier. | `R-DA-10`, `ADR-0008` |
| **RSK-05** | Calibration | Distribution drift during economic shifts causing conformal interval undercoverage. | **4** | **4** | **16** | Violation of exchangeability between historical training vintage and current market clearing. | **Task T4.08 & T5.05:** Strictly forward-temporal calibration splits; CPI-Urban deflation; rolling 90-day coverage monitoring. | `R-MD-02`, `R-UQ-02` |
| **RSK-06** | Product / Trust | Users interpreting feature attributions (SHAP) as guaranteed causal recipes for raises. | **4** | **4** | **16** | Presenting observational correlational coefficients without prominent non-causal disclaimers. | **Task T5.06 & T7.03:** Enforce descriptive non-causal UI framing (`design.md`); disclaimers on all skill comparisons. | `R-MD-10`, `01-targets.md` |
| **RSK-07** | Data Leakage | Future information or employer-clustered leakage artificially inflating test accuracy. | **4** | **3** | **12** | Random $K$-fold cross-validation mixing identical workers, employers, or future dates into train set. | **Task T4.01 & T5.01:** Grouped-employer and strictly forward-temporal cross-validation splits. Audit with `test_leakage.py`. | `R-DA-03`, `R-MD-02` |
| **RSK-08** | Operational | Overengineering with GPUs, GNNs, and Vector DBs exhausting latency and financial budgets. | **3** | **4** | **12** | Chasing ML research trends instead of building the simplest credible tabular system. | **Task T1.11 & T3.01:** Banned technology rule (`R-MD-09`). Enforce Profile A (Polars, DuckDB, LightGBM CPU, latency $<50$ms). | `R-MD-09`, `architecture.md` |
| **RSK-09** | Measurement | Currency and period normalizer errors (e.g. treating monthly salary as annual or USD as INR). | **4** | **3** | **12** | Inconsistent schema ingestion scripts failing on Indian number conventions (Lakhs vs Millions). | **Task T3.02:** Exhaustive unit test suite (`tests/fixtures/`) on regex normalizers and currency converters. | `T1.02-TEST-01..08` |
| **RSK-10** | Selection Bias | Self-selected crowdsourced voluntary contributions overrepresenting high-earning Tier-1 tech. | **4** | **3** | **12** | Prestige bias; employees earning ₹35+ LPA submit data, while ₹6 LPA IT services staff do not. | **Task T4.06 & T6.03:** Post-stratification weighting against MOSPI PLFS (`SRC-IND-OFF-01`) and listed IT medians (`SRC-SUP-CORP-01`). | `D-010`, `04-source-catalog.md` |
| **RSK-11** | Model Risk | Quantile crossing ($\hat{q}_{0.10} > \hat{q}_{0.50}$ or $\hat{q}_{0.50} > \hat{q}_{0.90}$) in uncalibrated tree models. | **3** | **4** | **12** | Independent quantile gradient boosting objectives violating monotonicity constraints. | **Task T4.07 & T5.02:** Post-processing isotonic rearrangement (Chernozhukov et al.) and simultaneous quantile penalties. | `architecture.md` Sec 4 |
| **RSK-12** | Equity Risk | Valuing unvested private startup equity as guaranteed cash, misleading job changers. | **4** | **3** | **12** | Attempting Black-Scholes valuation on illiquid, unverified startup stock option grants. | **Task T1.02 & Phase 8:** Strictly isolate equity from `guaranteed_cash_annual`. Display equity descriptively only. | `R-MD-07`, `02-comp-definitions.md` |
| **RSK-13** | Governance | Secret or credential leakage in git repository (database passwords, API keys). | **5** | **2** | **10** | Committing `.env` or configuration files with embedded service credentials. | **Task T0.01 & T9.12:** Automated `gitleaks` pre-commit hooks; `.gitignore` validation; zero credentials in git. | `R-CD-02`, `.pre-commit-config.yaml` |
| **RSK-14** | Architecture | Uncontrolled circular imports and architecture spaghetti between serving and ML modules. | **3** | **3** | **9** | Monolithic Python scripts blurring module boundaries and breaking dependency flow. | **Task T0.07 & T9.13:** Enforce strict package import direction (`import-linter`) via `contracts.ini` in CI. | `R-CD-03`, `pyproject.toml` |
| **RSK-15** | UX / Product | Users perceiving the output as a rigid guarantee or corporate salary appraisal. | **4** | **2** | **8** | Lack of prominent UI boundaries and statistical confidence framing. | **Task T0.05 & T9.01:** Editorial design system (`design.md`); signature "Span" visualization; clear non-guarantee copy. | `design.md`, `PRD.md` FR-16 |

---

## 4. Operational Risk Mitigation Mapping to Implementation Tasks

Every risk in the register is tied to an explicit, accountable engineering task in `task.md`. This guarantees that no risk remains a passive theoretical observation:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              RISK-TO-TASK TRACEABILITY MAP                             │
│                                                                                        │
│  [RSK-01, RSK-04] Legal & Privacy  ──► Task T2.02 (License Register) & T9.12 (Audits) │
│  [RSK-02, RSK-12] Target & CTC     ──► Task T2.05 (Quarantine) & T3.02 (Normalization) │
│  [RSK-03, RSK-10] UQ & Bias        ──► Task T4.04 (Support Metric) & T4.06 (Weights)  │
│  [RSK-05, RSK-11] Drift & Crossing ──► Task T4.08 (Conformal) & T5.02 (Isotonic Sort)  │
│  [RSK-06, RSK-15] UX & Causality   ──► Task T5.06 (Attribution) & T9.01 (UI Copy)      │
│  [RSK-07, RSK-14] Leakage & Lint   ──► Task T4.01 (Splits) & T0.07 (import-linter)     │
│  [RSK-08, RSK-09] Stack & Parsing  ──► Task T3.01 (DuckDB Engine) & T3.02 (Fixtures)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Pre-Registration of Phase 2 Hard Stop Gates

1. **Gate G1 Check (Closing Phase 1):**
   - If RSK-01, RSK-02, or RSK-03 mitigation tasks are missing from `task.md`, Gate G1 CANNOT be ratified.
2. **Gate G2 Check (Data Sufficiency Verification):**
   - If unbundled, legally cleared data fails to satisfy pre-registered cell sample thresholds in `experiments/preregistration/sufficiency-v1.yaml`, modelling is HALTED immediately. The team must NOT proceed to Phase 3 ML engineering without data sufficiency.

---

*Authored for ArthaIQ under Phase 1, Task T1.12. Fully satisfies the Premortem mandate and formalizes the 15-risk register with operational task mitigations.*
