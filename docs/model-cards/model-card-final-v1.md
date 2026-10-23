# ArthaIQ Production Champion Model Card (Final v1.0.0)

| Field | Value |
|---|---|
| Document Version | 1.3.0 (Phase 13 Promotion & Re-audit; supersedes 1.2.0 (Phase 12 Promotion)) |
| Release Date | 2026-10-23 |
| Model Identifier | `arthaiq-champion-v1.3.0` |
| Benchmark Ladder Rung | **Rung F (Champion)** under ADR-0004 |
| Target Measure | PT1: `guaranteed_cash_annual` (Nominal INR LPA, Gross Pretax) |
| Deployment Profile | Profile B (`t4g.medium` Graviton3, ADR-0009) |
| Governing Standards | Mitchell et al. (2019), PRD Section 8 NFR-09, PRD Section 13, DPDPA 2023 |

---

## 1. Model Details

### 1.1 Architecture & Pipeline Specification
The ArthaIQ Production Champion Model is a calibrated, uncertainty-aware compensation estimation engine composed of three decoupled, mathematically verified stages:
1. **Base Multi-Quantile Regressor (Rung E):** Gradient-boosted decision trees (`CatBoostQuantileModel`) predicting joint conditional quantiles $\hat{q}_{\tau}(X)$ simultaneously across $\tau \in \{0.10, 0.50, 0.90\}$ on log-transformed guaranteed compensation, with tree-native handling of categorical features and feature vocabulary isolation fitted strictly inside training folds (`R-MD-04`).
2. **Monotone Rearrangement Crossing Repair (Rule R-UQ-05):** Post-processing projection implementing Chernozhukov, Fernández-Val, and Galichon (2010) monotone sorting rearrangement, guaranteeing that the empirical quantile crossing rate is **strictly 0.0%** ($P_{10} \le P_{50} \le P_{90}$).
3. **Split Conformal Calibration Engine (Rung F):** Conformalized Quantile Regression (CQR; Romano et al., 2019) calibrated on a strictly isolated temporal validation partition (`calibrate` split) with nominal coverage $1 - \alpha = 0.80$, computing conformal non-conformity scores $E_i = \max(\hat{q}_{0.10}(X_i) - Y_i, Y_i - \hat{q}_{0.90}(X_i))$ and adjusting interval bounds by finite-sample quantile adjustment $\hat{Q}_{1-\alpha}(E)$.
4. **Decoupled Support & Governance Evaluator:** Decoupled evaluation engine implementing 5 independent support criteria ($S_1$ cohort count $N \ge 10$, $S_2$ feature domain bounds $[0, 40]$ YoE, $S_3$ recency decay $\le 365$ days, $S_4$ source quality score $\text{SQSF} \ge 65.0$, $S_5$ interval usefulness ratio $\le 1.05$) per ADR-0005 and Decision `D-010`.

### 1.2 Target Measure & Economic Invariants
- **Primary Target (PT1):** `guaranteed_cash_annual` (annualized contractually guaranteed gross cash salary).
- **Unit & Currency:** Indian Rupee (INR) in Lakhs Per Annum (LPA, nominal).
- **Tax Basis:** Gross pretax (`gross_pretax`, Rule `R-CD-05`).
- **Target Exclusions:** Discretionary performance bonuses, retention sign-ons, unvested equity/RSUs, and employer health/perk benefits are strictly unbundled and excluded per ADR-0002.
- **Statutory Non-Negativity Floor:** All output bounds are bounded below by $\ge 0.50$ LPA per Rule `R-UQ-05`.

---

## 2. Intended Use, Scope & Non-Reliance

### 2.1 Primary Intended Applications
- Individual salary benchmarking and market context for software engineers, data professionals, and AI/ML specialists in Indian tech hubs.
- Objective decision-support during employment offer negotiations and career transitions.
- Organizational compensation benchmarking to prevent wage stagnation and internal pay inequities.

### 2.2 Statutory Disclaimers & Decision-Support Mandate (PRD FR-18, Rule R-UI-05)
- **Non-Reliance Disclosure:** The model output represents a statistical estimate derived from aggregated historical and self-reported market data of varying density. **It does not constitute an employment offer, wage guarantee, or binding wage appraisal.**
- **No Lone Numbers (Rule R-UQ-01):** The model never outputs single point estimates in isolation. It outputs the calibrated 80% interval $[P_{10}, P_{90}]$ alongside median $P_{50}$ and plain-language probabilistic definitions.
- **Calibrated Abstention (Rule R-UQ-02):** When a candidate profile falls outside reliable support (e.g. $N < 10$, out-of-range YoE, extreme interval dispersion), the model explicitly abstains with HTTP 200 `status: "abstained"` rather than guessing.

### 2.3 Strictly Prohibited Applications (PRD Section 12)
- **Candidate Screening & Ranking:** The model MUST NOT be used to filter, rank, screen, or blacklist job candidates or current employees.
- **Automated Adverse Employment Actions:** The model MUST NOT be the sole basis for wage reductions, terminations, or mandatory demotions.
- **Demographic Pricing:** The model MUST NOT be used to infer, condition, or discount pay based on demographic protected attributes.

---

## 3. Data Lineage, Features & Invariants

### 3.1 Training Lineage & Splits
- **Ingestion Lineage:** Multi-source tech compensation intakes (2021–2026), verified via SHA-256 manifests (`R-DA-01`, `R-DA-02`).
- **Eligibility Filter:** Only `is_pt1_eligible == True` observations meeting SQSF Provenance Tiers A, B, and C. Unverified scrapings (Tier D) are permanently excluded.
- **Partitioning (Rules R-MD-01, R-MD-03):** Grouped-temporal dataset splitting preserving temporal ordering (`train` $\to$ `calibrate` $\to$ `select` $\to$ `test`), grouped by employer cluster and candidate ID to prevent identity leakage. The final test set remains strictly locked (`make final-eval`, `R-MD-02`).
- **Synthetic Isolation (Rule R-MD-11):** Production model bundle training strictly excludes synthetic fixtures (`is_synthetic == False`).

### 3.2 Specified Feature Matrix (PRD Section 5)
The production model utilizes a disciplined set of 23 candidate features across Levels L0 to L2:
- **Level 0 (Core Baseline):** `role_family` (SWE, DATA, MLAI), `years_experience` (continuous tenure), `seniority` (Junior, Mid, Senior, Staff, Principal), `location` (Bengaluru, Hyderabad, Pune, Mumbai, NCR, Chennai, Other).
- **Level 1 (Role Profile):** `skills_primary`, `skills_depth`, `domain_specialization`.
- **Level 2 (Target Opportunity):** `employer_tier` (Tier 1 Product, Tier 2 Product, IT Services).

### 3.3 Compare-Only Current Pay Quarantine (Rule R-MD-13, EXP-07)
Current compensation (`feat_l3_current_guaranteed_cash`) is permanently quarantined to `COMPARE_ONLY` architecture. In empirical experiment EXP-07, entering current pay into the predictive matrix yielded an anchoring weight $\alpha = 0.880$, causing the model to tautologically compound historical underpayment. Current pay is exclusively processed client-side for benchmark positioning and is **never ingested into model training or inference matrices**.

### 3.4 Zero-Indicator Missingness Invariant (Rule R-MD-15)
Explicit binary missingness indicators ($1_{\{x \text{ is missing}\}}$) are strictly prohibited. Missing optional profile fields reflect user privacy choices under DPDPA 2023 and are routed dynamically to lower-level nested baseline models ($M_0, M_1, M_2$).

---

## 4. Quantitative Performance & Benchmark Progression

Evaluation across the pre-registered benchmark ladder on development partitions (`select`):

| Ladder Rung | Model Architecture | MAE (LPA) | Pinball Loss (LPA) | Empirical 80% Coverage | Quantile Crossings | Interval Width Ratio |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Rung A** | Empirical Cell Median Backoff | 3.84 | 2.115 | 68.4% | N/A | 1.000 (Ref) |
| **Rung B** | Regularized Log-Linear (Ridge) | 2.45 | 1.420 | 72.1% | N/A | 0.985 |
| **Rung C** | Hierarchical Empirical Bayes Partial Pooling | 1.82 | 1.045 | 76.5% | 0.00% | 0.952 |
| **Rung D** | LightGBM Log-Pay Point Regressor | 1.48 | 0.935 | N/A | N/A | N/A |
| **Rung E** | CatBoost MultiQuantile Regressor | 1.22 | 0.845 | 77.2% | 0.00% | 0.940 |
| **Rung F** | **CatBoost CQR Champion (v1.0.0)** | **1.15** | **0.812** | **80.59%** | **0.00%** | **0.926** |

### Key Performance Findings:
- **Coverage Calibration:** Conformal prediction achieves 80.59% empirical coverage against the nominal 80.0% target ($| \Delta | = 0.0059 \le 0.020$).
- **Sharpness Gain (EXP-02):** Conformal intervals compress interval width by **+7.4%** over naive empirical cohorts ($R_{\text{width}} = 0.926$, 95% bootstrap CI: $[0.926, 0.926]$).
- **Serving Latency (PRD NFR-02):** Profile B runtime latency achieves p95 of **4.32 ms** ($>11\times$ faster than the $50.0\text{ ms}$ SLA).

---

## 5. Subgroup Fairness & Disparity Audit (Fairness Audit v2)

Audited across 4 lawful operational dimensions in `docs/research/fairness-audit-v2.md`:

| Operational Dimension | Slices Evaluated | Max MAE Ratio | Max Coverage Gap | Low-Support Slices ($N < 10$) | Parity Status |
|---|:---:|:---:|:---:|:---:|:---:|
| **Geographic Metro Hubs** | 6 | 1.18x | 0.11 | 0 | **PASS** |
| **Experience Bands** | 5 | 1.01x | 0.04 | 0 | **PASS** |
| **Role Families** | 3 | 1.00x | 0.01 | 0 | **PASS** |
| **Employer Tiers** | 3 | 1.12x | 0.03 | 0 | **PASS** |

### 5.1 Demographic Proxy Scan (rules.md Section 16 Rule 11)
- **Scanned Columns:** 52 features/columns across all schemas.
- **Prohibited Demographics Found:** **0** (Zero protected demographic attributes).
- **Status:** **COMPLIANT**.

### 5.2 Small-Cell Anonymization ($k_{\min} \ge 5$)
All displayed aggregates, evidence cards, and percentiles enforce the $k_{\min} \ge 5$ person-count floor (Rule `R-DA-10`, ADR-0008). Slices with $< 5$ distinct natural persons are automatically suppressed with `status: "abstained"`.

---

## 6. Environmental & Computational Efficiency

- **Hardware Efficiency (Rule R-MD-09):** The entire training and conformal calibration pipeline executes on standard developer CPU hardware with **zero GPU dependency**.
- **Inference Footprint:** Peak memory usage is **125.5 MB** Python heap, running stably within a 2 vCPU Graviton3 VM (`t4g.medium`).
- **Container Cold Start:** Cold start from disk to live healthcheck is **9.6 seconds**.
- **Serving Capacity:** Delivers **~230 requests/second** sustained throughput, providing $>90\times$ headroom over peak public beta traffic.

---

## 7. Model Governance, Lineage & Rollback Operations

- **Model Packaging (Rule R-MD-14):** Packaged as a self-contained deployable `ModelBundle` in `artifacts/champion_v0/`:
  - `base_model.joblib`: Trained CatBoost multi-quantile estimator.
  - `calibrator.joblib`: Fitted conformal quantile calibrator.
  - `support_evaluator.joblib`: Serialized decoupled support evaluator.
  - `cohort_evidence.parquet`: Canonical cohort support table.
  - `manifest.json`: Cryptographic SHA-256 integrity manifest.
- **Runtime Serving & Health Probes:** Served via `ServingModelManager` (`src/compintel/serving/loader.py`) with startup sanity checks, `/livez`, `/readyz`, and `/healthz` probes.
- **Rollback Procedure:** Tested zero-downtime rollback to previous bundle or static baseline in $< 100\text{ ms}$ upon alert trigger (`compintel.monitoring.alerts`).

---

---

## 8. Phase 12 Addendum: Active Learning & Counterfactual Scenario Intelligence (EXP-14 & EXP-15)

In Phase 12, two major architectural enhancements were developed, benchmarked, and ratified for production deployment under Gate G12 (`docs/pilot/gate-g12-review.md`):

### 8.1 Active Learning Acquisition Engine (`compintel.acquisition.active_learning`, EXP-14)
To eliminate severe uncertainty on thin realization cells without naive random sampling, an uncertainty-guided acquisition utility engine was deployed:
- **Acquisition Utility Metric:** $A(c) = \text{IntervalWidth}(c) \cdot \frac{1}{\sqrt{N_c + 1}} \cdot \text{SearchDemand}(c)$ balancing epistemic uncertainty, empirical density, and user search demand.
- **Epistemic Scorer:** $U(x) = \text{Var}_{\text{posterior}}(\hat{y} \mid x) \cdot (1 - \text{PSM}(x))$.
- **Targeted Recruitment Routing:** Automatically translates high-utility cells into operational directives across 4 acquisition channels (`COMMUNITY_REFERRAL_BOUNTY`, `GIVE_TO_GET_IN_APP`, `B2B_SYNDICATION_PARTNER`, `ALUMNI_NETWORK_SURVEY`) with incentive multipliers and sample quotas.
- **Empirical Audit:** Compressed average interval width on target sparse cells by **32.45%** (from 25.38 LPA to 17.15 LPA, exceeding the $\ge 20\%$ threshold), dropped cell abstention by **75.0 percentage points** (from 85.0% to 10.0%), maintained nominal conformal coverage at **80.69%** (inside $[75.0\%, 85.0\%]$), and delivered a **0.27x relative cost ratio** compared to uniform random acquisition.

### 8.2 Counterfactual Negotiation Scenario Engine (`compintel.serving.counterfactual`, EXP-15)
To support candidate decision-making without emitting uncalibrated point estimates, an interactive counterfactual scenario inversion engine (**PT4 Prototype**) was integrated into the serving layer:
- **Constrained Monotonic Projection (PAVA):** Enforces $\partial \hat{y} / \partial \text{YoE} \ge 0$ via isotonic regression rearrangement, preventing anomalous decreases in predicted earnings as experience increases.
- **Seniority Step-Ups & Relocation Frontiers:** Guarantees non-crossing quantiles across seniority tiers ($P_{10}(\text{JR}) \le P_{10}(\text{MID}) \le \dots$) and computes empirical cost-of-living differentials across metro tech hubs.
- **India New Tax Regime Engine (Section 115BAC):** Computes net in-hand annual take-home compensation incorporating the ₹75,000 standard deduction, Section 87A rebate, and marginal tax relief, returning calibrated net spans $[P_{10}, P_{50}, P_{90}]$.
- **Dual Offer Trade-Off Analysis:** Analyzes cash versus equity trade-offs with risk-adjusted certainty narratives.
- **Invariants Enforced:** Zero lone point estimates (100.0% compliant ranges under Rule `R-UQ-01`), strict serving boundary isolation under Rule `R-CD-03`, and serving latency $p_{95} = 4.03\text{ ms}$ (well within the $150.0\text{ ms}$ SLA).

---

## 9. Phase 13 Addendum: Multi-Component Copula Scenario Structure & Re-audit Ratification (EXP-PGM-01r)

In Phase 13, the platform evaluated accumulating 6-month non-synthetic production data across 6 research charters under Gate G13 (`docs/pilot/gate-g13-review.md`):

### 9.1 Gaussian Copula Scenario Dependency Layer (`src/compintel/evaluation/copula_pt4_experiment.py`, EXP-PGM-01r)
To prevent unrealistic multi-component compensation permutations in the PT4 negotiation scenario UI, a Gaussian copula rank-correlation layer with non-parametric empirical marginal probability integral transforms (PIT) was promoted:
- **Multi-Component Trade-off Dependency:** Preserves empirical correlation structure between base cash (`guaranteed_cash_annual`), equity grants (`equity_annualized`), and performance bonuses (`variable_performance_annual`).
- **Rank-Correlation Preservation:** Achieved maximum Spearman rank correlation error $|\Delta \rho| = 0.0388 \le 0.050$ across all component pairs (vs $|\Delta \rho| > 0.60$ under independent marginal assumptions).
- **Monotonic Non-Crossing Quantiles:** Enforces Chernozhukov sorting projection with $0.00\%$ crossing rate across simulated draws ($P_{10} \le P_{50} \le P_{90}$).
- **Joint Calibration & Efficiency:** Maintained $78.00\%$ empirical joint coverage in the $[75.0\%, 85.0\%]$ nominal window at $p_{95} = 0.86\text{ ms}$ CPU simulation latency.
- **Architectural Boundary Guard (Rules R-MD-08 & R-CD-03):** The copula layer is strictly integrated into the PT4 interactive negotiation scenario UI layer (`compintel.serving.counterfactual`). Core compensation point and interval predictions remain 100% governed by Champion Rung F Level 2 Conformal CatBoost without model contamination or lone numbers.

### 9.2 Architecture Re-audit & Re-gate Verdicts
- **Quantile Model Ensembling (`EXP-ENSEMBLE-01r`):** Convex quantile stacking degraded pinball loss by $+0.1320\text{ LPA}$ and widened interval widths by $+1.47\%$. Permanently **REJECTED**; Champion CatBoost retained unmodified.
- **Disciplined Feasibility Deferrals:** `EXP-10r` (Employer Graphs, 16 clusters $< 50$), `EXP-09r` (Skills TF-IDF, $45.6\%$ power $< 80.0\%$), `EXP-TRAJ-r` (Career Trajectories, $5.9$ mo $< 12.0$ mo span), and `EXP-MACRO-01r` (Macro Regimes, $5.9$ mo $< 24.0$ mo span) were formally **DEFERRED** with pre-registered triggers, preventing speculative model drift.

---

## 10. Model Card Sign-Off

| Reviewer Role | Signatory | Determination | Date | Status |
|---|---|---|---|---|
| **Lead ML Engineer** | Algorithmic Evaluation Lead | Quantitative benchmarks & calibration verified | 2026-10-23 | **RATIFIED (GO)** |
| **Lead Systems Architect** | Infrastructure & Serving Lead | Latency SLA & container packaging verified | 2026-10-23 | **RATIFIED (GO)** |
| **Data Governance Officer** | Privacy & Statutory Compliance Officer | DPDPA, $k_{\min} \ge 5$, zero demographic proxies verified | 2026-10-23 | **RATIFIED (GO)** |
| **Compensation Economics Lead** | Principal Labour Economist | Economic monotonicity & Section 115BAC tax verified | 2026-10-23 | **RATIFIED (GO)** |
| **Product & UX Design Lead** | Head of Product & Accessibility | Zero lone numbers & scenario comprehension verified | 2026-10-23 | **RATIFIED (GO)** |

