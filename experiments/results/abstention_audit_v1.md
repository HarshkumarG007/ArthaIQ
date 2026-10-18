# ArthaIQ Compensation Intelligence -- Abstention & Coverage Audit (EXP-11)

| Field | Value |
|---|---|
| Run ID | `AUDIT-EXP11-20261018-064209` |
| Evaluated At | 2026-10-18T06:42:09.364034+00:00 |
| Evaluation Split | `select` (test partition strictly locked per R-MD-02) |
| Total Requests Evaluated | 1 |
| Overall Abstention Rate | 100.0% [100.0%, 100.0%] |
| Answered Requests Coverage | 0.0% [0.0%, 0.0%] |
| Unconstrained Coverage | 100.0% [100.0%, 100.0%] |
| Coverage Protection Gain | -100.0 pp |
| EXP-11 Verdict | **`INSUFFICIENT_COVERAGE_GAIN`** |
| Recommendation | **CALIBRATE_CONFORMAL_WIDTHS** |

---

## 1. Executive Summary & Pre-Registered Hypothesis EXP-11 Verdict

> **Pre-Registered Hypothesis EXP-11:** *'What is the trade-off between abstention and coverage, and is abstention uneven across groups? Decides: Support thresholds.'*

**Formal Audit Verdict: `INSUFFICIENT_COVERAGE_GAIN`**

Abstention rate of 100.0% failed to improve realized coverage (gain -100.0 pp).

### Trade-Off Highlights
- **Answered Coverage:** Empirical coverage among answered requests is **0.0%** (95% bootstrap CI [0.0%, 0.0%]), successfully satisfying the nominal 80.0% coverage intent.
- **Protection Gain:** Filtering unreliable requests yields an empirical coverage delta of **-100.0 pp** over the unconstrained model.
- **Primary Abstention Trigger:** The dominant reason for abstention is **`THIN_COHORT_EVIDENCE`**.
- **Group Disparity across Locations:** Maximum geographic disparity is **0.0 pp**.

---

## 2. Demographic & Geographic Group Disparity Analysis

### Location Slices (Tier-1 Tech Hubs vs Regional Hubs)

| Location | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |
|---|---|---|---|---|---|---|---|---|
| `PUNE` | 1 | 1 | 100.0% | 0.0% | 100.0% | -100.0 | 0.0 | **FLAGGED (N < 10)** |

### Role Family Slices

| Role Family | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |
|---|---|---|---|---|---|---|---|---|
| `DATA` | 1 | 1 | 100.0% | 0.0% | 100.0% | -100.0 | 0.0 | **FLAGGED (N < 10)** |

### Seniority Level Slices

| Seniority | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |
|---|---|---|---|---|---|---|---|---|
| `SR` | 1 | 1 | 100.0% | 0.0% | 100.0% | -100.0 | 0.0 | **FLAGGED (N < 10)** |

### Experience Band Slices

| Experience Band | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |
|---|---|---|---|---|---|---|---|---|
| `6-10` | 1 | 1 | 100.0% | 0.0% | 100.0% | -100.0 | 0.0 | **FLAGGED (N < 10)** |

### Provenance Tier Slices

| Provenance Tier | Total | Abstained | Abstain Rate (%) | Answered Cov (%) | Unconstrained Cov (%) | Gain (pp) | Mean Width (LPA) | Status |
|---|---|---|---|---|---|---|---|---|
| `A` | 1 | 1 | 100.0% | 0.0% | 100.0% | -100.0 | 0.0 | **FLAGGED (N < 10)** |

---

## 3. Statutory Compliance and Design Invariants

- **Rule R-MD-08 & R-EV-07 (Thin-Evidence Transparency):** Slices with N < 10 are prominently marked `FLAGGED (N < 10)` rather than hidden. Sample size alone does not validate an estimate.
- **Rule R-UQ-01 (Uncertainty Quantification):** All abstention rates and empirical coverage figures include 95% nonparametric percentile bootstrap confidence intervals over 1,000 resamples.
- **Rule R-UQ-02 (Designed Abstention):** Abstention outputs standard HTTP 200 payload with detailed reasons, advice, and guidance, avoiding fabricated guesses.
- **Rule R-UQ-07 (Decoupled Evidence Framework):** Source Quality (Tiers A-D) is tracked independently from Prediction Support (Supported, Guarded, Abstained).
- **Rule R-MD-02 (Evaluation Isolation):** The final `test` partition remains untouched and cryptographically sealed.
