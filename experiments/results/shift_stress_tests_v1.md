# ArthaIQ -- Shift Stress Testing & Hypothesis EXP-03 Report

| Metadata Attribute | Value |
| :--- | :--- |
| **Report ID** | `SSR-2026-10-18-select` |
| **Generated At** | `2026-10-18T04:30:27.351728+00:00` |
| **Dataset Snapshot** | `SNAP-1FF34A8E9633` |
| **Evaluation Split** | `select` (strictly dev; test locked) |
| **Evaluated Model** | `catboost_cqr` (CatBoost CQR Rung F) |
| **Nominal Target Coverage** | `80.0%` |
| **EXP-03 Verdict** | **`DRIFT_NEGLIGIBLE`** |
| **Recalibration Cadence** | `PERIODIC_STATIC (Quarterly recalibration sufficient)` |

---

## 1. Executive Summary

Evaluated CatBoost CQR on partition 'select' (N=1). Temporal shift analysis yields EXP-03 verdict **DRIFT_NEGLIGIBLE** (coverage drift: +0.0 pp, recalibration gain: +0.0 pp). Recommended recalibration cadence: `PERIODIC_STATIC (Quarterly recalibration sufficient)`. Geographic disparity between primary tech hubs and regional markets is -100.0 pp in coverage and 0.000 in interval width ratio. Identified 1 thin-support slices (N < 10) marked for automated abstention in task T5.07.

---

## 2. Temporal Shift & Rolling Recalibration (Hypothesis EXP-03)

> **Pre-Registered Hypothesis EXP-03:** *Does coverage degrade on the most recent window, and does rolling recalibration fix it? Decides: Recalibration cadence.*

| Metric | Historical Window | Recent Window (Static) | Recent Window (Recalibrated) | Drift / Gain | 95% Bootstrap CI |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Observation Count (N)** | 1 | 1 | 1 | - | - |
| **Empirical Coverage** | 100.00% | 100.00% | 100.00% | Static Drift: +0.00 pp<br>Recal Gain: +0.00 pp | Drift: [+0.00 pp, +0.00 pp]<br>Gain: [+0.00 pp, +0.00 pp] |
| **Mean Interval Width** | 36.27 LPA | 36.27 LPA | 36.27 LPA | Delta: +0.00 LPA | - |

**EXP-03 Formal Interpretation:** Coverage remained stable across historical (100.0%) and recent (100.0%) windows with negligible drift (+0.0 pp). Static calibration remains reliable.

---

## 3. Geographic Shift Stress Test

Evaluates performance and coverage stability across Tier-1 Primary Tech Hubs (Bangalore, Hyderabad, Pune, Delhi NCR, Mumbai) versus Regional and Emerging Hubs.

### Geographic Aggregate Comparison

| Market Tier | N | Coverage | Mean Width | Disparity vs Primary |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Tech Hubs (Tier 1)** | 1 | 100.00% | 36.27 LPA | Baseline |
| **Regional & Emerging Hubs** | 0 | 0.00% | 0.00 LPA | Coverage: -100.00 pp, Width Ratio: 0.000 |

### Geographic Slices (Flagging Rules R-MD-08 & R-EV-07)

| Location | Tier | Support Status | N | Coverage | Mean Width | Median Width | MAE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PUNE** | TIER_1_PRIMARY | **FLAGGED (N < 10)** | 1 | 100.0% | 36.27 LPA | 36.27 LPA | 3.34 LPA |

---

## 4. Rare Cells & Thin-Support Slices Stress Test

Evaluates stability on sparse cells (sparse role x seniority intersections and veteran experience tails where N < 10).

### Rare Cell Aggregate Comparison

| Support Stratum | Slices | Coverage | Mean Width | Gap vs Common |
| :--- | :--- | :--- | :--- | :--- |
| **Common Cells (N >= 10)** | 0 | 0.00% | 0.00 LPA | Baseline |
| **Rare Cells (N < 10)** | 1 | 100.00% | 36.27 LPA | Coverage: +100.00 pp, Width Ratio: 1.000 |

### Rare Slices Breakdown (Rules R-MD-08 & R-EV-07)

| Dimension | Cell Key | Support Status | N | Coverage | Mean Width | MAE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| role_seniority | **DATA_SR** | **FLAGGED (N < 10)** | 1 | 100.0% | 36.27 LPA | 3.34 LPA |

---

## 5. Architectural & Governance Safeguards

- **Rule R-UQ-03 Compliance:** Conformal guarantees assume exchangeability. Temporal drift violates exchangeability, necessitating rolling recalibration cadence monitoring.
- **Rule R-MD-02 Compliance:** Evaluation performed exclusively on dev partitions (select/calibrate). Final test set remains isolated and untouched.
- **Rule R-MD-08 / R-EV-07 Compliance:** Every slice with $N < 10$ is prominently flagged with `**FLAGGED (N < 10)**`, preventing deceptive support claims.
- **Upcoming Task T5.07 Input:** Slices identified with severe degradation or $N < 10$ are cataloged for automated thin-evidence abstention.
