# Quantile Ensembling Feasibility Re-audit (Phase 13, EXP-ENSEMBLE-01r, CHARTER-ENSEMBLING-STACKING)

> **Scope:** Empirical Data-Growth Re-evaluation of Convex Quantile Blending and Stacking Feasibility on Cumulative Non-Synthetic Production Panel.
> **Governing Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-02, R-MD-04, R-MD-05, R-MD-09, R-MD-11, R-UQ-01, R-UQ-05 · Task T13.02.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `EXP-ENSEMBLE-R-20261023-024139` |
| **Charter ID** | `CHARTER-ENSEMBLING-STACKING` |
| **Task ID** | `T13.02` |
| **Generated At** | `2026-10-23T02:41:39.627199+00:00` |
| **Git Commit** | `2c6668d8` |
| **Operational Window** | `6.0 months` post-EXP-16 |
| **Observation Panel** | `219` records (`219` verified non-synthetic) |
| **Evaluation Partitions** | Train: `131`, Calibrate: `43`, Eval (`select`): `45` |
| **Gate 1 Feasibility** | **`FEASIBLE`** |
| **Modeling Executed** | `True` |
| **Pre-Registered Verdict** | **`REJECT`** |
| **Champion Status** | **`RETAINED_UNMODIFIED`** |

---

## 1. Executive Summary & Governance Verdict

**Final Verdict:** `REJECT`

Empirical Re-audit REJECT: Gate 1 passed with 219 records (>= 100 required). Empirical modeling on 45 eval rows demonstrated pinball loss delta of +0.1320 LPA (95% CI: [+0.0243, +0.2442] LPA) and interval width ratio of 1.0147, failing the pre-registered keep criteria (delta pinball <= -0.050 LPA, width ratio <= 0.950). The ensemble degraded predictive sharpness and widened intervals. Added operational complexity of multi-model serving is formally REJECTED. Production Champion Rung F Level 2 Conformal CatBoost is retained unmodified.

> **Governance Decision:** REJECT: Ensembling failed pre-registered performance gates (delta pinball <= -0.050 LPA). Champion Rung F Level 2 Conformal CatBoost strictly retained without ensembling complexity.

---

## 2. Gate 1: Non-Synthetic Panel Sufficiency Audit

Under **Rule `R-MD-09`** and **`CHARTER-ENSEMBLING-STACKING`**, convex quantile blending and cross-validated meta-regression require a minimum observation panel of $N \ge 100$ verified non-synthetic observations to estimate weights and evaluate out-of-fold generalization without catastrophic overfitting.

| Audit Metric | Empirical Value | Pre-Registered Standard | Gate Status |
|:---|:---|:---|:---|
| **Total Panel Observations ($N$)** | `219` records | $N \ge 100$ | PASS |
| **Verified Non-Synthetic Records** | `219` (100.0%) | 100.0% verified non-synthetic (`R-MD-11`) | PASS |
| **Training Partition ($N_{\text{train}}$)** | `131` records | $\ge 60$ records for stable fold fitting | PASS |
| **Calibration Partition ($N_{\text{calib}}$)** | `43` records | $\ge 20$ records for conformal calibration | PASS |
| **Evaluation Split** | `select` (`45` records) | `select` partition; locked test isolated (`R-MD-02`) | PASS |

> **Gate 1 Diagnostic:** Gate 1 feasibility passed: panel has 219 records (131 train), meeting threshold of >= 100.

---

## 3. Comparative Modeling & Algorithmic Performance Matrix

Variant A evaluates a convex blend ($w_{\text{CB}} = 0.50, $w_{\text{LGB}} = 0.50$) of Rung F Conformal CatBoost and Rung E LightGBM MultiQuantile regressors, projected through the **Chernozhukov et al. (2010)** monotone rearrangement operator to guarantee $P_{10} \le P_{50} \le P_{90}$ with strictly zero quantile crossings (Rule `R-UQ-05`).

| Evaluation Metric | Champion Baseline (Rung F CatBoost) | Variant A (Convex Blend) | Paired Difference / Ratio | Keep Criterion | Status |
|:---|:---|:---|:---|:---|:---|
| **Mean Pinball Loss** | `3.4810 LPA` | `3.6131 LPA` | `+0.1320 LPA` (95% CI: `[+0.0243, +0.2442]`) | $\Delta \le -0.050\text{ LPA}$, CI upper $< 0$ | FAIL |
| **Mean Absolute Error (MAE)** | `12.2992 LPA` | `12.8420 LPA` | `+0.5429 LPA` | Informational | PASS |
| **Median Absolute Error (MdAE)** | `10.7635 LPA` | `11.0705 LPA` | `+0.3070 LPA` | Informational | PASS |
| **Empirical Coverage ($P_10-P_90$)** | `75.56%` | `73.33%` | `-2.22 pp` | Nominal $[72.0\%, 88.0\%]$ | PASS |
| **Mean Interval Width** | `36.12 LPA` | `36.65 LPA` | Width Ratio: `1.0147` | $\text{Ratio} \le 0.950$ ($\ge 5\%$ narrowing) | FAIL |
| **Quantile Crossing Rate** | `0.00%` | `0.00%` | `0.00%` (Monotone sort guaranteed) | $\le 0.50\%$ (`R-UQ-05`) | PASS |
| **Inference Latency (p95)** | `3.648 ms` | `5.472 ms` | `1.50x` overhead | $\le 1.50\times$ latency multiplier | PASS |
| **Statistically Significant Gain?** | N/A | N/A | `YES` (CI excludes 0) | Required | FAIL |

---

## 4. Pre-Registered Keep / Reject Decision Analysis

Under **`CHARTER-ENSEMBLING-STACKING`**, ensembling must satisfy strict economic and predictive utility thresholds to justify the operational overhead of training, validating, packaging, and monitoring multiple model families simultaneously in production.

1. **Pinball Loss Criterion (FAIL):** The convex quantile blend achieved a mean pinball loss delta of `+0.1320 LPA` with 95% bootstrap confidence interval `[+0.0243, +0.2442] LPA`. This fails the pre-registered requirement of $\Delta \le -0.050	ext{ LPA}$. Furthermore, the entire confidence interval lies in the positive zone, indicating that blending empirically *degraded* quantile sharpness compared to the single Champion CatBoost.

2. **Interval Width Criterion (FAIL):** The prediction interval width ratio was `1.0147` (an interval expansion of `+1.47%`), failing the pre-registered requirement to achieve at least 5% interval narrowing (width ratio $\le 0.950$).

3. **Operational Overhead vs Gain (REJECT):** Serving an ensemble requires bundling both CatBoost and LightGBM weights, maintaining dual preprocessing pipelines, and synchronizing cross-model versioning. In the absence of positive predictive gain, this added complexity is formally rejected under Rule `R-MD-09`.

---

## 5. Architectural Invariants & Conclusion

1. **Production Champion Preserved:** The production champion **Rung F Level 2 Conformal CatBoost** remains strictly retained without ensembling overhead. Serving continues on pure CPU tabular inference at $< 1.0	ext{ ms}$ latency.
2. **Rule `R-UQ-05` Verification:** The Chernozhukov rearrangement operator demonstrated 100% mathematical non-crossing compliance ($0.00\%$ crossings across all observations).
3. **Rule `R-MD-11` Verification:** 100% of panel observations were verified non-synthetic with zero synthetic fixture leakage.
4. **Next Roadmap Action:** Advance to **Task T13.03** (EXP-09r Skills TF-IDF Power-Gated Retest) under Phase 13.
