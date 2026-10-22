# EXP-13 Research Report: Slice-Adaptive Conformal Prediction Intervals

| Field | Value |
|---|---|
| **Charter ID** | `CHARTER-EXP-13` |
| **Date** | 2026-10-22 13:26:30 UTC |
| **Status / Verdict** | ✅ **RATIFIED / PROMOTE** |
| **Governing Rules** | `PRD Section 11 Metric M-04`, `Rule R-UQ-01`, `Rule R-UQ-03`, `Rule R-MD-09` |

---

## 1. Executive Summary

This experiment evaluates **Hierarchical Group-Conditional Conformal Calibration with Empirical Bayes Shrinkage** (`CHARTER-EXP-13`) compared to the global split-conformal CQR baseline.

### Key Empirical Findings:
- **Slice Coverage Parity:** Cross-slice coverage variance decreased by **89.05%** (from `0.002766` to `0.000303`).
- **Aggregate Coverage:** Baseline = `79.1%`, Treatment = `79.4%` (target nominal 80.0%, pre-registered band `[78%, 82%]`).
- **Width Growth Penalty:** Interval width ratio shifted by **+0.95%** (well below the pre-registered `+5.0%` ceiling).
- **Serving Latency Overhead:** Overhead is **+1.9 µs/request** (sub-millisecond, easily satisfying `< 1.0 ms` constraint).

---

## 2. Pre-Registered Keep Criteria Verification

| Criterion | Pre-Registered Threshold | Baseline (Global CQR) | Treatment (Slice-Adaptive) | Status |
|---|---|---|---|---|
| **Criterion 1: Slice Coverage** | All cells ($N \ge 20$) in `[76.0%, 84.0%]` | 7/12 | 12/12 (100.0%) | PASS |
| **Criterion 2: Aggregate Coverage** | Aggregate coverage in `[78.0%, 82.0%]` | `79.08%` | `79.37%` | PASS |
| **Criterion 3: Width Ratio Growth** | Growth $\le +5.0\%$ (ratio $\le 0.360$) | `0.1579` | `0.1594` (+0.95%) | PASS |
| **Criterion 4: Latency Overhead** | Overhead $\le 1.0\text{ ms}$ (p95 $\le 5.5\text{ ms}$) | `17.3 µs` | `19.25 µs` (+1.9 µs) | PASS |

---

## 3. Slice-by-Slice Calibration Breakdown

| Slice Key (Role : Seniority) | Samples ($N$) | Baseline Coverage | Treatment Coverage | Baseline Width Ratio | Treatment Width Ratio | Delta Coverage |
|---|---|---|---|---|---|---|
| `DATA:JUNIOR` | 489 | 80.8% | **82.0%** | 0.218 | 0.223 | +1.2% |
| `DATA:MID` | 543 | 71.8% | **78.6%** | 0.129 | 0.147 | +6.8% |
| `DATA:SENIOR` | 489 | 83.6% | **80.8%** | 0.178 | 0.164 | -2.9% |
| `MANAGEMENT:JUNIOR` | 490 | 72.9% | **78.4%** | 0.140 | 0.151 | +5.5% |
| `MANAGEMENT:MID` | 488 | 80.1% | **78.5%** | 0.149 | 0.141 | -1.6% |
| `MANAGEMENT:SENIOR` | 495 | 87.1% | **79.0%** | 0.262 | 0.226 | -8.1% |
| `MLAI:JUNIOR` | 491 | 76.8% | **78.0%** | 0.151 | 0.156 | +1.2% |
| `MLAI:MID` | 476 | 72.9% | **78.6%** | 0.131 | 0.147 | +5.7% |
| `MLAI:SENIOR` | 483 | 89.2% | **82.2%** | 0.245 | 0.212 | -7.0% |
| `SOFTWARE:JUNIOR` | 498 | 79.7% | **81.9%** | 0.269 | 0.280 | +2.2% |
| `SOFTWARE:MID` | 539 | 77.4% | **77.0%** | 0.148 | 0.146 | -0.4% |
| `SOFTWARE:SENIOR` | 519 | 77.6% | **77.8%** | 0.145 | 0.147 | +0.2% |

---

## 4. Scientific Verdict & Governance Recommendation

**Verdict:** `PROMOTE`

- **Keep Criteria Passed:** 4 of 4 criteria satisfied.
- **Empirical Bayes Shrinkage:** Successfully balances local coverage accuracy for high-support cohorts while gracefully regularizing small slices toward the global quantile without destabilizing interval boundaries.
- **Recommendation:** Ratify EXP-13 promotion and integrate `SliceAdaptiveConformalRegressor` into the Phase 11 serving pipeline.

```json
{
  "charter_id": "CHARTER-EXP-13",
  "experiment_name": "Slice-Adaptive Conformal Prediction Intervals",
  "timestamp": "2026-10-22 13:26:30 UTC",
  "verdict": "PROMOTE",
  "keep_criteria": {
    "criterion_1_slice_coverage": {
      "passed": true,
      "threshold": ">= 75% slices in [76.0%, 84.0%], variance reduction >= 30%, zero slices in reject zone (<74% or >86%)",
      "treatment_pass_rate": "12/12 (100.0%)",
      "baseline_pass_rate": "7/12"
    },
    "criterion_2_aggregate_coverage": {
      "passed": true,
      "threshold": "[78.0%, 84.0%]",
      "value": 0.7937
    },
    "criterion_3_width_growth": {
      "passed": true,
      "threshold": "<= +5.0% growth and ratio <= 0.380",
      "growth_percent": 0.95,
      "final_ratio": 0.1594
    },
    "criterion_4_latency_overhead": {
      "passed": true,
      "threshold": "<= 1000 \u00b5s",
      "overhead_us": 1.95
    }
  },
  "comparison": {
    "variance_reduction_percent": 89.05,
    "width_growth_percent": 0.95,
    "latency_overhead_us": 1.95
  }
}
```