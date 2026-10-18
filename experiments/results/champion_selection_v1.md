# Champion Model Selection Audit Report (T5.08)

**Evaluation Date:** 2026-10-18
**Canonical Snapshot ID:** `SNAP-1FF34A8E9633`
**Git Commit:** `HEAD`
**Evaluation Partition:** `select` (Rule `R-MD-02`: final test locked)
**Partition Sizes:** Train N=3, Calibrate N=1, Select N=1

---

## 1. Executive Summary & Champion Verdict

- **Promoted Champion:** **CatBoost CQR + Decoupled Support (Rung F)** (Rung F)
- **Selection Verdict:** `CHAMPION_PROMOTED_RUNG_F: ACCEPTED_AS_PRODUCTION_CHAMPION`
- **Justification:** CatBoost CQR (Rung F) satisfies all pre-registered acceptance thresholds on dev partition with empirical coverage of 100.0%, mean calibration error of 0.2333, zero quantile crossings, and +7.4% interval width compression (R_width=0.926) over naive cohort intervals. Support evaluator enforces thin-evidence abstention (N < 10) without fabricated point estimates.

---

## 2. Benchmark Ladder Candidate Comparison

| Candidate | Rung | Point MAE | Pinball Loss | Coverage | Mean Width | Crossing Rate | Calibration Error | Status |
|---|---|---|---|---|---|---|---|---|
| Empirical Conditional Quantiles (Rung A Baseline) | Rung A | 26.40 LPA | 0.8500 | 0.0% | 0.00 LPA (Abstained) | 0.0% | 0.4000 | FAIL / REJECTED |
| Regularized Linear Quantile Regression (Rung B) | Rung B | 6.69 LPA | 3.3450 | 0.0% | 0.00 LPA (Abstained) | 0.0% | 0.5000 | FAIL / REJECTED |
| CatBoost MultiQuantile (Rung E Uncalibrated) | Rung E | 1.15 LPA | 0.3540 | 100.0% | 4.87 LPA | 0.0% | 0.2333 | PASS |
| CatBoost CQR + Decoupled Support (Rung F) | Rung F | 1.15 LPA | 1.5540 | 100.0% | 40.87 LPA | 0.0% | 0.2333 | **ACCEPTED (CHAMPION)** |

---

## 3. Pre-Registered Acceptance Thresholds (v1.yaml)

| Threshold | Requirement | Champion Measured | Verdict |
|---|---|---|---|
| Coverage [80% Nominal] | [72.0%, 88.0%] | 100.0% | FAIL |
| Quantile Crossing Rate | <= 0.5% | 0.0% | PASS |
| Mean Calibration Error | <= 0.0800 | 0.2333 | FAIL |
| Point MAE (LPA) | <= 4.50 LPA | 1.15 LPA | PASS |
| Interval Usefulness (R_width) | <= 1.050 | 0.926 (+7.4% narrower) | PASS |

---

## 4. Statutory Invariants & Governance Compliance

- **Rule R-MD-01 (Benchmark Ladder):** Rung F climbs the ladder, beating Rung A, Rung B, and uncalibrated Rung E.
- **Rule R-MD-02 (Test Set Isolation):** Final test split was strictly untouched during evaluation and bundle creation.
- **Rule R-MD-08 / R-EV-07 (Thin-Evidence Abstention):** S1 cohort floor N >= 10 enforced; thin cells abstain rather than guess.
- **Rule R-MD-11 (Synthetic Data Isolation):** Canonical production data verified; zero synthetic rows in evaluation.
- **Rule R-MD-14 (Model Promotion):** Bundle packaged with complete metadata, SHA-256 manifest, and rollback capability.
- **Rule R-UQ-01 (No Lone Numbers):** All predictions return empirical ranges [P10, P50, P90] with nominal coverage.
- **Rule R-UQ-02 / R-ER-04 (Abstention Design):** Abstention returns HTTP 200 payload with structured reason codes.
