# Phase 10 Post-Pilot Experiment Charters & Ranking

> **Document ID:** `docs/research/experiment-charters-phase10.md`  
> **Status:** RATIFIED & PRE-REGISTERED  
> **Author:** Antigravity AI & Human Engineering Reviewer  
> **Date:** 2026-10-21  
> **Governing Rules:** `R-MD-01`, `R-MD-03`, `R-MD-05`, `R-MD-09`, `R-UQ-01`, `R-CD-01`, `R-DA-10`  
> **Prerequisites:** Pilot Analysis (`T10.06`), Online Coverage Tracking (`T10.03`), Freshness SLA (`T10.04`), Drift Recalibration (`T10.05`)

---

## 1. Executive Summary & Governance Mandate

Under **Rule `R-MD-09`**, complex architectural components, statistical adjustments, or advanced algorithms are strictly prohibited from ad-hoc implementation without a pre-registered **Experiment Charter** defining explicit keep, defer, and reject criteria before any code is written or merged into production.

Following the successful execution of the ArthaIQ production pilot across 232 realization cohort observations (passing 11 of 11 PRD Section 11 metrics with $80.17\%$ conformal coverage and median width ratio $0.34$), user feedback and slice diagnostics identified four high-priority technical initiatives.

This document formally establishes the pre-registered scientific charters for the top four backlog items prioritized via the RICE framework.

### Master Charter Ranking by Expected Value (EV) vs Implementation Cost

| Rank | Charter ID | Candidate Name | Category | RICE Score | Expected Value | Cost / Effort | Pre-Registered Keep Criterion |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---|
| **1** | `CHARTER-EXP-13` | Slice-Adaptive Conformal Prediction Intervals | Calibration & UQ | **72.0** | **HIGH** | Medium (3 wks) | Slice coverage $\in [76\%, 84\%]$ on $\ge 90\%$ of cells; width growth $\le +5\%$ |
| **2** | `CHARTER-EXP-16` | Automated Dual-Cadence Source Ingestion & Freshness Daemon | Data Ops & MLOps | **71.3** | **HIGH** | Medium (3 wks) | Zero freshness SLA violations; $100\%$ zero PII quarantine |
| **3** | `CHARTER-EXP-14` | Active Learning & Targeted Data Sourcing for Sparse Realization Cells | Active Learning | **55.3** | **MED-HIGH** | High (5 wks) | Uncertainty reduction $\ge 20\%$; abstention reduction $\ge 15\%$ |
| **4** | `CHARTER-EXP-15` | Counterfactual Negotiation & Offer Scenario Modeling (PT4) | Product / UQ | **35.2** | **HIGH** | Very High (8 wks) | Monotonicity $\ge 98\%$; coverage parity on scenario bounds |

---

## 2. CHARTER-EXP-13: Slice-Adaptive Conformal Prediction Intervals (Group-Conditional Calibration)

### 2.1 Problem Statement & Background
Production telemetry from Pilot Task T10.03 revealed that while aggregate empirical coverage across all 232 realized compensation offers is tightly calibrated at $80.17\%$ (nominal $80\%$, Wilson 95% CI: $[74.67\%, 84.77\%]$), localized slice coverage exhibits mild under-coverage in niche geographic regions (Tier-2/3 cities: $75.0\%$) and senior bands (Staff/Principal: $76.2\%$). While strictly within our $\pm 5\%$ tolerance band, cross-slice variance ($s^2_{\text{cov}} = 0.0018$) can be systematically minimized through group-conditional conformal calibration.

### 2.2 Hypothesis
Partitioning the calibration set into hierarchical groups (by role category and experience tier) and computing group-conditional non-conformity adjustments $\hat{q}_g$ (with shrinkage toward global $\hat{q}_{\text{global}}$ via empirical Bayes) will improve slice-level coverage parity without inflating median interval width beyond $5\%$.

### 2.3 Experimental Methodology
- **Baseline:** Global split-conformal quantile regression (`CatBoostConformalPredictor` with scalar $\hat{q}_{\text{global}} = 0.4998$ LPA).
- **Treatment:** Hierarchical Group-Conditional Conformal Calibration:
  $$\hat{q}_g = \alpha_g \hat{q}_{\text{sample}, g} + (1 - \alpha_g) \hat{q}_{\text{global}}$$
  where $\alpha_g = \frac{n_g}{n_g + m_0}$ is the empirical Bayes shrinkage weight with prior weight $m_0 = 30$.
- **Validation Dataset:** Out-of-time evaluation split ($N=1,250$) and 6 weekly realization cohorts ($N=232$).
- **Stratification:** 4 role tiers $\times$ 3 experience bands = 12 slices. Minimum slice threshold $n_g \ge 15$.

### 2.4 Pre-Registered Criteria
- **Keep Criteria:**
  1. Empirical coverage for all evaluated slices with $n_g \ge 20$ falls strictly within $[76.0\%, 84.0\%]$.
  2. Overall aggregate coverage remains within $[78.0\%, 82.0\%]$.
  3. Aggregate median interval width ratio ($\frac{q_{0.90} - q_{0.10}}{q_{0.50}}$) increases by no more than $+5.0\%$ relative to global baseline (max width ratio $\le 0.360$).
  4. Serving latency overhead is $\le 1.0\text{ ms}$ (p95 $\le 5.5\text{ ms}$).
- **Defer Criteria:**
  - Slice coverage variance decreases by $< 30\%$ or requires slice sample size $n_g > 50$ to avoid erratic boundaries.
- **Reject Criteria:**
  - Any evaluated slice suffers coverage $< 74.0\%$ or $> 86.0\%$.
  - Median interval width ratio exceeds $0.380$ (compromising PRD Section 11 M-05).
  - Introduction of quantile crossing errors ($> 0.1\%$).

---

## 3. CHARTER-EXP-16: Automated Dual-Cadence Source Ingestion & Freshness Daemon

### 3.1 Problem Statement & Background
Under Task T10.04, ArthaIQ defined strict Freshness SLAs (`config/freshness_slas.yaml`) across external statutory indices (PLFS: 365d, CPI: 35d, MRE: 90d, SO Survey: 365d) and primary voluntary intake (Continuous: max 7d delay). While `scripts/run_data_refresh.py` successfully audits data staleness, upstream ingestion currently relies on scheduled batch cron execution. When upstream providers publish out-of-schedule revisions (e.g. MOSPI CPI release anomalies), pipeline latency can cause temporary staleness alerts.

### 3.2 Hypothesis
An event-driven dual-cadence freshness daemon—combining webhook-triggered ingestion for high-frequency primary contributions and automated polling with schema-diff validation for official macro sources—will eliminate staleness incidents while enforcing zero-leakage temporal isolation and strict DPDPA compliance.

### 3.3 Experimental Methodology
- **Baseline:** Weekly manual/cron batch refresh runner (`scripts/run_data_refresh.py`).
- **Treatment:** `compintel.ingestion.daemon` background service:
  - Fast-path: Event-driven quarantine queue processing contributions within 15 minutes of user submission.
  - Slow-path: Automated MOSPI / BSE statutory publication scrapers with checksum validation and release-calendar joins.
  - Automated canary verification: Every ingested batch automatically runs schema validation (`Rule R-DA-03`), statutory unbundling integrity (`Rule R-MD-07`), and privacy erasure audit (`Rule R-CD-06`).
- **Metrics Tracked:** Ingestion-to-serving latency, freshness SLA headroom, schema rejection accuracy, pipeline CPU/memory utilization.

### 3.4 Pre-Registered Criteria
- **Keep Criteria:**
  1. $100\%$ zero staleness violations across all 6 data sources over a continuous 30-day monitoring window.
  2. Contribution ingestion-to-shadow-eval latency $\le 60\text{ minutes}$ (down from 7 days).
  3. $0.00\%$ false accepts of non-compliant schemas (synthetic injection test: 100/100 anomalous batches quarantined).
  4. Zero PII leakage across raw ingestion buffers, intermediate checkpoints, and logging telemetry.
- **Defer Criteria:**
  - Provider rate limits or CAPTCHA barriers require manual intervention on more than 2 sources.
- **Reject Criteria:**
  - Ingestion daemon process memory leaks exceeding $500\text{MB}$ resident set size.
  - Any automated schema migration that introduces unbundled CTC leakage into PT1.

---

## 4. CHARTER-EXP-14: Active Learning & Targeted Data Sourcing for Sparse Realization Cells

### 4.1 Problem Statement & Background
Pilot evaluation and sparse-cell benchmarking (T4.08 / T10.03) identified that 18 out of 96 fine-grained market cells (e.g., Staff/Principal Mobile Engineers in Tier-2 locations, or Compilers/Systems Specialists in Chennai) possess low observation counts ($N < 15$). In these cells, the epistemic uncertainty remains elevated, resulting in wider prediction intervals (median width ratio $0.41$) and higher abstention trigger rates under Rule `R-UQ-03`.

### 4.2 Hypothesis
An active learning sampling policy that computes epistemic uncertainty scores $\mathcal{U}(x) = \text{Var}_{\text{posterior}}(\hat{y} \mid x) \cdot (1 - \text{PSM}(x))$ to dynamically boost user referral rewards and targeted B2B syndication incentives for high-uncertainty cells will achieve a $25\%$ reduction in average interval width on sparse cells with $50\%$ fewer total acquired samples compared to uniform random sourcing.

### 4.3 Experimental Methodology
- **Baseline Policy:** Uniform random sourcing across tech job titles via standard give-to-get intake.
- **Treatment Policy (Active Learning Acquisition):**
  1. Every 24 hours, score all unobserved or low-support cells in the market taxonomy.
  2. Select top 20 cells by uncertainty utility:
     $$\mathcal{A}(c) = \text{IntervalWidth}(c) \times \frac{1}{\sqrt{N_c + 1}} \times \text{SearchDemand}(c)$$
  3. Dynamically route targeted survey prompts and B2B syndication requests to recruit candidates matching cell $c$.
- **Simulation & Shadow Evaluation:** 1,000 synthetic offer realizations simulated under empirical covariance structures.

### 4.4 Pre-Registered Criteria
- **Keep Criteria:**
  1. Average interval width on target sparse cells narrows by $\ge 20.0\%$ after acquiring 150 targeted observations.
  2. Cell abstention rate on targeted roles drops by $\ge 15.0\%$ without increasing quantile crossing rate.
  3. Empirical coverage on newly populated cells remains within $[75.0\%, 85.0\%]$.
  4. Cost per informative observation is $\le 2.0\times$ baseline uniform cost.
- **Defer Criteria:**
  - Acquisition volume in niche categories fails to reach $N=10$ per cell within 60 days due to labor market scarcity.
- **Reject Criteria:**
  - Targeted acquisition introduces selection bias that degrades out-of-sample coverage below $72.0\%$.
  - Incentivized reporting inflates invalid contribution rate (M-07) above $10.0\%$.

---

## 5. CHARTER-EXP-15: Counterfactual Negotiation & Offer Scenario Modeling (PT4 Prototype)

### 5.1 Problem Statement & Background
User qualitative feedback from Pilot Task T10.01 revealed that $26.8\%$ of active users requested interactive scenario modeling—specifically asking questions such as: *"If I negotiate an additional 3 LPA in guaranteed cash, what equity or bonus trade-off maintains market competitiveness?"* or *"How would relocating from Pune to Bengaluru alter my percentile position?"* Currently, ArthaIQ is strictly calibrated for factual prediction (PT1) and abstains from speculative scenario generation to prevent hallucinated advice.

### 5.2 Hypothesis
A constrained counterfactual optimization engine—leveraging the monotonic properties of our conformalized gradient boosted quantile surfaces combined with statutory tax brackets—can provide reliable counterfactual trade-off bounds while strictly maintaining nominal coverage and preventing deceptive lone-number recommendations.

### 5.3 Experimental Methodology
- **Baseline:** Fixed point-in-time percentile lookup (no counterfactual simulation; user must manually execute separate queries).
- **Treatment:** Counterfactual Quantile Inversion Engine:
  $$\hat{\delta}_{\text{cash}} = \arg\min_{\delta} \|\mathcal{Q}_{\tau}(x + \Delta x) - (y_{\text{target}} + \delta)\|$$
  subject to structural monotonicity constraints ($\frac{\partial y}{\partial \text{YoE}} \ge 0$, $\text{Tier-1} \ge \text{Tier-2}$) and conformal uncertainty bounds.
- **Evaluation Benchmark:** 500 pre-defined historical negotiation transcripts with dual offer pairs.
- **Safety Audits:** Automated adversarial probe checking for negative compensation returns, illogical seniority reversals, or misleading precision.

### 5.4 Pre-Registered Criteria
- **Keep Criteria:**
  1. Monotonicity constraint satisfaction $\ge 98.0\%$ across all simulated perturbation trajectories.
  2. Counterfactual interval coverage on verified subsequent job hops falls within $[75.0\%, 85.0\%]$.
  3. Zero point-estimate advice (every scenario outputs an 80% conformal bound with explicit tradeoff uncertainty).
  4. Response time for full scenario frontier generation $\le 150\text{ ms}$ (within NFR-02 SLA).
- **Defer Criteria:**
  - Counterfactual bounds expand wider than $0.50$ median width ratio, rendering advice insufficiently actionable.
- **Reject Criteria:**
  - Hallucination or reversal rate $> 2.0\%$ (e.g. suggesting lower pay for higher seniority).
  - Any violation of Rule `R-MD-08` (providing lone numbers or financial advisory claims).

---

## 6. Architectural Safety, Ethical & Privacy Boundaries

All experiments governed by these charters must strictly uphold the following invariants:
1. **Zero PII Principle (`Rule R-CD-06`):** No feature, embedding, or active learning query may ingest, store, or transmit direct personal identifiers (names, emails, phone numbers, exact company IDs where cell count $< 5$).
2. **Deterministic Reproducibility (`Rule R-MD-05`):** All experiments must include immutable random seeds, frozen data snapshot hashes, and configuration YAML files in `experiments/configs/charters/`.
3. **Continuous Conformal Monitoring (`Rule R-UQ-01`):** No algorithmic change may be promoted to production if it breaks the nominal 80% coverage guarantee or introduces quantile crossings.
4. **Independent Evidence Review:** All empirical results will be submitted to the Evidence Register (`docs/research/evidence-register.csv`) with supporting run artifacts before production deployment.
