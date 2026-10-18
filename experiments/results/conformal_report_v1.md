# ArthaIQ Conformal Coverage & Calibration Report (Task T5.04)

> [!NOTE]
> **FORMAL CONFORMAL ASSUMPTIONS (Rule R-UQ-03)**: Coverage guarantees are
> strictly **marginal** ($P(Y \in C(X)) \ge 1 - \alpha$) over population,
> and hold **conditionally on exchangeability** between calibration and eval.
> ArthaIQ makes **no claim of individual-level conditional coverage**.

> [!IMPORTANT]
> **LOCKED TEST PARTITION (Rule R-MD-02)**: Routine evaluation is strictly
> isolated to dev pool partition (`select`). Test partition
> remains locked and untouched until Gate G5 acceptance.

## 1. Provenance and Partition Metadata

| Parameter | Value | Description |
|---|---|---|
| **Report ID** | `CONF-20261017231813` | Unique evaluation audit ID |
| **Data Snapshot ID** | `SNAP-1FF34A8E9633` | Cryptographic dataset digest |
| **Git Commit** | `2d3d5634` | Exact repository commit SHA |
| **Random Seed** | `42` | Deterministic seeded RNG (R-MD-10) |
| **Evaluation Split** | `select` | Dev partition (Rule R-MD-02) |
| **Total Analyzed** | `5` | Total canonical observations |
| **Training Records** | `3` | Base model training partition |
| **Calibration Records** | `1` | Conformal calibration partition |
| **Evaluation Records** | `1` | Holdout validation partition |

## 2. Global Conformal Performance Comparison

| Model Architecture | Method | Conformal $q$ | 80% Coverage (95% CI) | Mean Width (LPA) | Mean Pinball | Crossing Rate | Abstention |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **CatBoost CQR (Rung F)** | `cqr` | `18.0000` | `100.0%` | `36.27` | `1.7657` | `0.0%` | `0.0%` |
| **CatBoost Split Conformal (Rung F Baseline)** | `split_conformal` | `18.3783` | `100.0%` | `36.76` | `1.7620` | `0.0%` | `0.0%` |
| **CatBoost Quantile Base (Rung E Uncalibrated)** | `uncalibrated_quantile` | `None` | `0.0%` | `0.27` | `1.6757` | `0.0%` | `0.0%` |

## 3. Tail Error & Boundary Distribution

Under nominal 80% coverage $[P10, P90]$, theoretical tail underflow and overflow rates are exactly 10.0%.

| Model | Underflow Rate (< P10) | Overflow Rate (> P90) | Balance Ratio | Lower Tail Pay Coverage | Upper Tail Pay Coverage |
|---|:---:|:---:|:---:|:---:|:---:|
| **CatBoost CQR (Rung F)** | `0.0%` | `0.0%` | `1.00` | `100.0%` (N=1) | `100.0%` (N=1) |
| **CatBoost Split Conformal (Rung F Baseline)** | `0.0%` | `0.0%` | `1.00` | `100.0%` (N=1) | `100.0%` (N=1) |
| **CatBoost Quantile Base (Rung E Uncalibrated)** | `100.0%` | `0.0%` | `1.00` | `0.0%` (N=1) | `0.0%` (N=1) |

## 4. Temporal Drift & Recent Window Breakdown (Rule R-UQ-03)

Conformal coverage assumes exchangeability across time. We evaluate the most recent temporal quarter against earlier data to quantify temporal drift.

| Model | Recent Window Coverage | Older Cohort Coverage | Temporal Drift ($\Delta$) | Drift Status |
|---|:---:|:---:|:---:|:---:|
| **CatBoost CQR (Rung F)** | `N/A` | `N/A` | `N/A` | `INSUFFICIENT_TIMESTAMPS` |
| **CatBoost Split Conformal (Rung F Baseline)** | `N/A` | `N/A` | `N/A` | `INSUFFICIENT_TIMESTAMPS` |
| **CatBoost Quantile Base (Rung E Uncalibrated)** | `N/A` | `N/A` | `N/A` | `INSUFFICIENT_TIMESTAMPS` |

## 5. Subgroup Slice Analysis & Minimum Support Flags (Rule R-MD-08)

> [!IMPORTANT]
> **MINIMUM SUPPORT POLICY (Rule R-MD-08)**: Slices with $N < 10$
> are explicitly flagged as `[FLAGGED: LOW SUPPORT]` with cell counts.
> In adherence to the project charter, under-supported cohorts are **never hidden or omitted**.

### Slice: Experience Band

| Category | Support Status | Sample Size | 80% Coverage (95% CI) | Mean Width (LPA) | Underflow (< P10) | Overflow (> P90) | Abstention |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`6-10`** | **`FLAGGED (N < 10)`** | `1` | `100.0%` | `36.27` | `0.0%` | `0.0%` | `0.0%` |

### Slice: Role Family

| Category | Support Status | Sample Size | 80% Coverage (95% CI) | Mean Width (LPA) | Underflow (< P10) | Overflow (> P90) | Abstention |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`DATA`** | **`FLAGGED (N < 10)`** | `1` | `100.0%` | `36.27` | `0.0%` | `0.0%` | `0.0%` |

### Slice: Seniority

| Category | Support Status | Sample Size | 80% Coverage (95% CI) | Mean Width (LPA) | Underflow (< P10) | Overflow (> P90) | Abstention |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`SR`** | **`FLAGGED (N < 10)`** | `1` | `100.0%` | `36.27` | `0.0%` | `0.0%` | `0.0%` |

### Slice: Location

| Category | Support Status | Sample Size | 80% Coverage (95% CI) | Mean Width (LPA) | Underflow (< P10) | Overflow (> P90) | Abstention |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`PUNE`** | **`FLAGGED (N < 10)`** | `1` | `100.0%` | `36.27` | `0.0%` | `0.0%` | `0.0%` |

### Slice: Provenance Tier

| Category | Support Status | Sample Size | 80% Coverage (95% CI) | Mean Width (LPA) | Underflow (< P10) | Overflow (> P90) | Abstention |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`A`** | **`FLAGGED (N < 10)`** | `1` | `100.0%` | `36.27` | `0.0%` | `0.0%` | `0.0%` |

## 6. Champion Uncertainty Model Verdict

- **Designated Champion**: `CatBoost CQR (Rung F)`
- **Verdict Status**: `ACCEPTED_AS_RUNG_F_CHAMPION`
- **Reasoning**: CQR achieved empirical coverage of 100.0% (calibration error 20.0 pp vs target 80.0%), with adaptive interval width 36.27 LPA and zero crossing violations.

---
*Report automatically generated by `src/compintel/evaluation/conformal_report.py`*