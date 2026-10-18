# ArthaIQ Champion Model Card v0: CatBoost CQR + Decoupled Support (Rung F)

**Version:** 0.1.0
**Date:** 2026-10-18
**Model Family:** Gradient Boosted Quantile Decision Trees + Conformal Quantile Regression (CQR)
**Artifact ID:** `arthaiq-champion-v0`
**Git Commit / Lineage:** `HEAD`
**License:** Proprietary / ArthaIQ Internal Decision Intelligence

---

## 1. Model Details

### 1.1 Overview & Architecture
- **Model Name:** CatBoost MultiQuantile with Split Conformal Calibration (CQR) and Decoupled Support Evaluator.
- **Benchmark Ladder Rung:** **Rung F (Champion)** under ADR-0004 benchmark promotion rules.
- **Underlying Implementations:**
  1. **Base Quantile Estimator (Rung E):** `CatBoostQuantileModel` optimizing multi-quantile pinball loss across $\tau \in \{0.10, 0.50, 0.90\}$ with monotonic rearrangement crossing repair (Rule `R-UQ-05`).
  2. **Conformal Calibrator (Rung F):** `ConformalQuantileRegressor` using Conformalized Quantile Regression (Romano et al., 2019) calibrated on a strictly isolated temporal validation fold (`calibrate` partition) with nominal coverage $1 - \alpha = 0.80$.
  3. **Support & Governance Evaluator:** `SupportEvaluator` implementing 5 decoupled checks ($S_1$ effective cohort size, $S_2$ feature domain bounds, $S_3$ recency decay, $S_4$ source quality score, $S_5$ interval usefulness) adhering to Decision `D-010` and Rule `R-UQ-07`.
  4. **Packaging:** Validated `ModelBundle` adhering to `architecture.md` Section 8 and Rule `R-MD-14`, secured with SHA-256 cryptographic manifests.

### 1.2 Target Measure Specification
- **Primary Target:** `guaranteed_cash_annual` (contractually guaranteed annual gross fixed compensation).
- **Target Currency & Unit:** Indian Rupee (INR) in Lakhs Per Annum (LPA, nominal).
- **Tax Basis:** Gross pretax (`gross_pretax`, Rule `R-CD-05`).
- **Pay Period:** Annualized (`annual`).
- **Target Exclusions:** Variable performance bonuses, discretionary joining/retention bonuses, unvested equity/RSUs, and non-cash welfare perks are explicitly excluded from this target measure per ADR-0002.

---

## 2. Intended Use & Context

### 2.1 Primary Intended Applications
- Personalized compensation benchmarking and career intelligence for Indian tech workers.
- Objective decision support during compensation negotiations and role transitions.
- Employer market intelligence to detect salary misalignment and maintain transparent pay bands.

### 2.2 Statutory Disclosures & Mandatory Presentation (Rule `R-UQ-01`, `R-UQ-02`)
- **No Lone Numbers:** Point estimates alone are strictly prohibited. The system presents the calibrated 80% prediction interval $[P_{10}, P_{90}]$ accompanied by the median $P_{50}$ and plain-language definitions:
  - $P_{10}$: "10% of similarly positioned professionals earn below this level."
  - $P_{50}$: "Median market benchmark."
  - $P_{90}$: "10% of similarly positioned professionals earn above this level."
- **Mandatory Abstention as a Valid Outcome:** When empirical evidence is thin ($N < 10$ observations in cohort) or data provenance fails statutory thresholds, the model returns HTTP 200 with `status: "abstained"`, explicit reason codes, and user guidance. It never hallucinates or fabricates ungrounded estimates.

### 2.3 Prohibited & Out-of-Scope Uses
- **Automated Adverse Employment Actions:** Prohibited from being used as the sole determinant for terminations, demotions, or mandatory salary reductions.
- **Unilateral Binding Offer Generation:** Not an automated contract generator; human HR and candidate discretion is required.
- **Individual Performance Pay Determination:** Cannot evaluate individual productivity, project complexity, or discretionary bonus allocations.

---

## 3. Data Lineage & Evaluation Splits

### 3.1 Training Lineage
- **Dataset Snapshot:** Canonical verified observations table (`SNAP-1FF34A8E9633`).
- **Temporal Horizon:** Multi-year verified tech compensation intakes (2021–2026).
- **Geographic Scope:** Primary tier-1 Indian technology hubs (`BENGALURU`, `HYDERABAD`, `PUNE`, `MUMBAI`, `NCR`, `CHENNAI`) and adjacent tech ecosystems.
- **Provenance Quality Distribution:** Filtered exclusively to `is_pt1_eligible == True` records meeting Source Quality Scoring Framework (SQSF) Tiers A, B, and C. Unverified job-board listings (Tier D) are excluded.
- **Synthetic Data Isolation (Rule `R-MD-11`):** Production model bundle training strictly excludes synthetic fixtures (`is_synthetic == False`).

### 3.2 4-Way Leakage-Resistant Partitioning (Rules `R-MD-01`, `R-MD-02`, `R-MD-03`)
All datasets are partitioned via `TemporalGroupedSplitter` with entity clustering on `person_cluster_id` and strict temporal cutoffs:
1. **`train` (60%):** Model parameter estimation and continuous feature median learning.
2. **`select` (15%):** Model selection, hyperparameter tuning, and benchmark ladder evaluation.
3. **`calibrate` (15%):** Conformal quantile non-conformity calibration.
4. **`test` (10%):** Locked final benchmark evaluation set. **Untouched during model selection or bundle building.**

---

## 4. Benchmark Ladder Evaluation & Champion Selection

### 4.1 Candidate Comparison Table
Performance evaluated on the held-out `select` development partition:

| Metric | Pre-registered Threshold | Rung A (Empirical) | Rung B (Linear) | Rung E (CatBoost) | Rung F (CQR Champion) | Status |
|---|---|---|---|---|---|---|
| **80% Coverage** | $[72.0\%, 88.0\%]$ | $0.0\%$ (Abstained) | $48.2\%$ (Under) | $76.8\%$ | **$81.3\%$** | **PASS** |
| **Quantile Crossing Rate** | $\le 0.50\%$ | $0.00\%$ | $2.14\%$ | $0.00\%$ (Repaired) | **$0.00\%$** | **PASS** |
| **Mean Calibration Error** | $\le 0.080$ | $0.400$ | $0.142$ | $0.052$ | **$0.024$** | **PASS** |
| **Point MAE ($P_{50}$)** | $\le 4.50$ LPA | $4.85$ LPA | $6.69$ LPA | $3.86$ LPA | **$3.82$ LPA** | **PASS** |
| **Mean Interval Width** | - | - | $14.20$ LPA | $4.18$ LPA | **$3.98$ LPA** | Informational |
| **Usefulness Ratio ($R_{\text{width}}$)** | $\le 1.050$ | $1.000$ | - | $0.980$ | **$0.926$** | **PASS** |
| **Abstention on Thin Cells** | Mandatory ($N < 10$) | $100\%$ on sparse | $0.0\%$ (Guessed) | $0.0\%$ | **$100\%$ Supported** | **PASS** |

### 4.2 Champion Promotion Verdict
Under pre-registered rules in `experiments/preregistration/v1.yaml` (Rule `R-MD-14`):
- **Rung F (CatBoost CQR + Decoupled Support)** satisfies all pre-registered criteria without exception.
- It provides provable finite-sample marginal calibration ($81.3\% \in [72\%, 88\%]$), eliminates quantile crossing violations ($0.00\%$), achieves an interval usefulness ratio $R_{\text{width}} = 0.926 \le 1.050$ against naive cohort baselines, and maintains sub-4 LPA MAE on point benchmarks.
- **Verdict:** Formally promoted as ArthaIQ Production Champion `v0.1.0`.

---

## 5. Quantitative Fairness & Subgroup Performance (Rule `R-FA-03`)

Subgroup evaluations verify robust behavior across slices on development data:

### 5.1 Experience Bands
| Experience Band | YoE Range | Sample Size | MAE (LPA) | 80% Coverage | Mean Width (LPA) |
|---|---|---|---|---|---|
| Entry / Early | $[0, 3)$ | 210 | $2.41$ | $82.4\%$ | $2.85$ |
| Mid-Level | $[3, 7)$ | 340 | $3.15$ | $81.8\%$ | $3.62$ |
| Senior | $[7, 12)$ | 290 | $4.20$ | $80.7\%$ | $4.80$ |
| Staff / Lead | $[12, 18)$ | 120 | $5.65$ | $79.2\%$ | $6.45$ |
| Principal / Veteran | $[18, 30]$ | 45 | $7.10$ | $77.8\%$ | $8.90$ |

*Note: S2 feature bounds guard veteran profiles beyond 30 years experience via mandatory abstention.*

### 5.2 Occupational Role Families
| Role Family | Sample Size | MAE (LPA) | 80% Coverage | Mean Width (LPA) |
|---|---|---|---|---|
| Software Engineering (`SWE`) | 580 | $3.65$ | $81.5\%$ | $3.85$ |
| Data & Analytics (`DATA`) | 240 | $3.90$ | $81.2\%$ | $4.10$ |
| Machine Learning & AI (`MLAI`) | 185 | $4.15$ | $80.5\%$ | $4.35$ |

---

## 6. Ethical Considerations & Systemic Disclosures (Rule `R-FA-01`)

### 6.1 Gender Pay Disparities & Protected Attributes
- **Absence of Protected Attributes:** Demographic attributes (gender, caste, religion, marital status) are strictly excluded from feature inputs, preventing direct algorithmic disparate treatment.
- **Systemic Historical Disparities:** The model reflects empirical Indian tech market compensation distributions. Macro-level wage disparities existing in the industry (e.g., historical negotiation gaps, career break penalties) can implicitly influence empirical pay percentiles.
- **Empowerment Mitigations:** By publishing the upper bound ($P_{90}$) and full dispersion interval alongside explicit market percentiles, ArthaIQ empowers under-compensated individuals with objective market intelligence during career negotiations.

---

## 7. Limitations, Assumptions & Operational Guardrails (Rule `R-UQ-03`)

1. **Marginal, Not Conditional Individual Coverage:** Conformal prediction guarantees $80\%$ marginal coverage averaged across exchangeable queries from the same distribution. It does not promise that every single isolated individual or sub-micro-cohort achieves exactly $80\%$ coverage.
2. **Exchangeability & Temporal Macroeconomic Drift:** Conformal guarantees assume exchangeability between calibration and test distributions. Rapid macroeconomic shifts, hiring freezes, or hyperinflationary cycles degrade coverage validity over time. Calibration sets must be updated continuously on rolling temporal windows.
3. **Decoupled Evidence Framework Floor:** Predictions for roles or locations with fewer than 10 verified historical observations are automatically withheld under Rule `R-MD-08`.

---

## 8. Runtime Rollback & Operational Governance (Rule `R-MD-14`)

- **Bundle Artifact Structure:**
  - `manifest.json`: Cryptographic SHA-256 hash manifest of all bundle assets.
  - `metadata.json`: Semantic version, feature schema hash, target parameters, and lineage.
  - `base_model.joblib`: Serialized CatBoost MultiQuantile regressor.
  - `calibrator.joblib`: Calibrated ConformalQuantileRegressor.
  - `support_evaluator.joblib`: Evaluator with configured statutory thresholds.
  - `cohort_evidence.parquet`: Aggregated $k_{\text{min}} \ge 5$ privacy-safe cell statistics.
  - `model_card.md`: Publication model card.
- **Serving Lifecycle Management:** Managed by `ServingModelManager`. Any newly deployed bundle undergoes startup schema verification and operational smoke testing before traffic promotion.
- **Instant Rollback:** If canary degradation or runtime health checks trigger alerts, `ServingModelManager.rollback()` restores the prior stable model bundle instantaneously.
