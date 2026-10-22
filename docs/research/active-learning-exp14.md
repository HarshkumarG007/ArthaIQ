# CHARTER-EXP-14: Active Learning & Targeted Data Sourcing for Sparse Realization Cells

> **Document Type:** Publication-Grade Empirical Research Memo  
> **Evaluation Timestamp:** 2026-10-22 23:15:00 UTC  
> **Empirical Verdict:** **PROMOTE**  
> **Governing Rule:** `Rule R-MD-09` (Pre-Registered Keep Criteria)  
> **Companion Docs:** `docs/research/experiment-charters-phase10.md`, `docs/pilot/prioritized-backlog.md`

---

## 1. Executive Summary & Verdict

Under pre-registered charter **CHARTER-EXP-14**, we evaluated an active learning acquisition policy designed to resolve epistemic uncertainty and high abstention rates in sparse compensation realization cells ($N < 15$).

**Official Verdict:** **🟢 PROMOTE**  
All four pre-registered keep criteria passed unconditionally:
1. **Interval Width Compression:** Target sparse cell interval width narrowed by **32.45%** (from 25.38 LPA to 17.15 LPA), exceeding the $\ge 20.0\%$ threshold.
2. **Cell Abstention Elimination:** Cell abstention rate dropped by **75.0 pp** (from 85.0% to 10.0%) with strictly zero quantile crossings ($0.0\%$).
3. **Conformal Coverage Invariant:** Realized empirical coverage on newly populated cells remained calibrated at **80.69%** within the statutory $[75.0\%, 85.0\%]$ conformal band.
4. **Information Sourcing Efficiency:** Relative cost per informative observation was **0.27x** baseline, comfortably beneath the $\le 2.0x$ constraint.

---

## 2. Quantitative Keep Criteria Scorecard

| Keep Criterion | Target Requirement | Measured Treatment Result | Baseline Uniform Result | Status |
|---|---|---|---|---|
| **1. Interval Width Reduction** | $\ge 20.0\%$ reduction | **32.45%** (17.15 LPA) | 1.8% (24.9 LPA) | **PASS** |
| **2. Cell Abstention Drop** | $\ge 15.0\%$ drop; 0 crossings | **75.0 pp** drop (0 crossings) | 0.0 pp drop | **PASS** |
| **3. Conformal Coverage** | $[75.0\%, 85.0\%]$ nominal 80% | **80.69%** | 80.1% | **PASS** |
| **4. Sourcing Cost Efficiency** | $\le 2.0x$ baseline cost/sample | **0.27x** relative | 1.0x baseline | **PASS** |

---

## 3. Policy Comparison: Active Learning vs Uniform Random

| Dimension | Baseline (Uniform Random) | Treatment (Active Learning $\mathcal{A}(c)$) | Delta / Improvement |
|---|---|---|---|
| **Sampling Policy** | Uniform random across 96 cells | Uncertainty-guided $\mathcal{A}(c)$ | Targeted priority |
| **Total Sample Budget** | 150 observations | 150 observations | Equal budget |
| **Informative Yield (Target Cells)** | 28 / 150 (18.7%) | **150 / 150 (100.0%)** | **+122 informative samples** |
| **Target Cells Final Mean Width** | 24.9 LPA | **17.15 LPA** | **32.45% narrower** |
| **Target Cells Final Abstention** | 65.0% | **10.0%** | **75.0 pp drop** |

---

## 4. Trajectory Progression (150 Targeted Samples)

| Milestone | Samples Acquired | Target Cells Mean Width (LPA) | Abstention Rate | Empirical Coverage | Cumulative Cost Units |
|:---:|:---:|:---:|:---:|:---:|:---:|
| Step 0 | 0 | 25.384999999999998 | 85.0% | 80.10% | 0.0 |
| Step 1 | 30 | 22.925 | 75.0% | 78.65% | 42.6 |
| Step 2 | 60 | 20.609 | 60.0% | 80.14% | 85.2 |
| Step 3 | 90 | 19.183 | 40.0% | 79.67% | 127.8 |
| Step 4 | 120 | 17.995 | 20.0% | 78.59% | 170.4 |
| Step 5 | 150 | 17.147 | 10.0% | 80.69% | 213.0 |

---

## 5. Top 10 Targeted Recruitment Campaign Directives

The active learning engine generated the following prioritized recruitment campaign directives:

| Priority | Cell Key | Role | Seniority | Location | Utility $\mathcal{A}(c)$ | Recommended Channel | Incentive Multiplier | Sample Quota |
|:---:|:---|:---|:---|:---|:---:|:---|:---:|:---:|
| **#1** | `SWE:PRINCIPAL:PUNE` | SWE | PRINCIPAL | PUNE | 22.200 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 12 |
| **#2** | `MLAI:PRINCIPAL:PUNE` | MLAI | PRINCIPAL | PUNE | 22.200 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 12 |
| **#3** | `DATA:PRINCIPAL:PUNE` | DATA | PRINCIPAL | PUNE | 21.062 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 13 |
| **#4** | `OTHER:PRINCIPAL:PUNE` | OTHER | PRINCIPAL | PUNE | 21.062 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 13 |
| **#5** | `MLAI:PRINCIPAL:HYDERABAD` | MLAI | PRINCIPAL | HYDERABAD | 17.146 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 10 |
| **#6** | `DATA:PRINCIPAL:HYDERABAD` | DATA | PRINCIPAL | HYDERABAD | 15.456 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 11 |
| **#7** | `MLAI:STAFF:PUNE` | MLAI | STAFF | PUNE | 14.087 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 11 |
| **#8** | `SWE:PRINCIPAL:HYDERABAD` | SWE | PRINCIPAL | HYDERABAD | 14.001 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 8 |
| **#9** | `MLAI:PRINCIPAL:NCR` | MLAI | PRINCIPAL | NCR | 14.001 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 8 |
| **#10** | `DATA:PRINCIPAL:NCR` | DATA | PRINCIPAL | NCR | 12.337 | `COMMUNITY_REFERRAL_BOUNTY` | 2.0x | 9 |

---

## 6. Architectural Safety, Ethical & Privacy Verification

1. **Zero Raw PII Retention (`Rule R-CD-06`):** All campaign directives and cell scores operate on coarse-grained tuples `(role_family, seniority, location)`. No individual user identifiers or raw compensation records are retained in acquisition queues.
2. **Abstention Integrity (`Rule R-MD-08`):** S1 abstention floor ($N < 10$) remained strictly enforced throughout the simulation. Profiles in cells with $N < 10$ continue to receive explicit HTTP 200 `status='abstained'` without lone numbers.
3. **Monotonic Quantile Non-Crossing (`Rule R-UQ-05`):** Quantile non-crossing was validated at every step ($0.0\%$ crossings observed across all evaluations).
4. **Anonymization Floor (`Rule R-DA-10`):** Employer cluster aggregation maintains $k_{\min} \ge 5$ across all intake routing.

---

## 7. Recommendation & Next Steps

- **Charter Status:** **RATIFIED / PROMOTE** to Production Intake Router.
- **Next Action:** Advance to **Task T12.02**: `EXP-15 Counterfactual Negotiation Scenario Modeling (PT4 Prototype)`.