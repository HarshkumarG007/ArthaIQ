# Fairness Audit v1: Prediction Parity by Operational Group (T6.09)

> **Legal Note (R-FA-04):** Legal status of regulations cited here is `UNVERIFIED` until confirmed by qualified counsel. This audit is provided as decision-support only and does not constitute a legal compliance determination.

> **Scope:** ArthaIQ PT1 market compensation estimates (P10/P50/P90) are evaluated for prediction parity across lawful operational slices: geographic tier, experience band, role family, and employer tier. Protected attributes (gender, caste, religion, age, disability) are strictly excluded from all model inputs and audit dimensions per Rule R-MD-12 and rules.md Section 16 Rule 11.

| Metadata | Value |
|:---|:---|
| **Report ID** | `FAIRNESS-V1-20261018213640` |
| **Generated At** | `2026-10-18T21:36:39.994964+00:00` |
| **Git Commit** | `de1f1777` |
| **Evaluation Split** | `select` |
| **Total Observations Evaluated** | `1` |
| **Overall Verdict** | **`INSUFFICIENT_DATA`** |

## 1. Executive Summary

The fairness audit v1 evaluated 1 observations across 4 operational slice dimensions: Geographic Tier, Experience Band, Role Family, and Employer Tier. Global baseline: Pinball = 1.783 LPA, MAE = 3.47 LPA, 80% Coverage = 100.0%, Abstention = 0.0%. All protected demographic attributes (gender, caste, religion, age, disability) confirmed absent from model inputs and audit dimensions. Overall parity verdict: **INSUFFICIENT_DATA**. 0 dimension(s) failed parity; 3 dimension(s) contain low-support slices (N < 10). See Section 7 for identified gaps and mitigations.

---

## 2. Global Baseline Metrics

| Metric | Value |
|:---|:---:|
| **Global Mean Pinball Loss** | `1.783` LPA |
| **Global Point MAE** | `3.47` LPA |
| **Global 80% Empirical Coverage** | `100.0%` |
| **Global Abstention Rate** | `0.0%` |

---

## 3. Demographic Proxy Compliance (rules.md Section 16 Rule 11)

- **Columns Scanned:** `52`
- **Prohibited Columns Found:** `0`
- **Compliance Status:** **`COMPLIANT`**

> LEGAL NOTE (R-FA-04, status=UNVERIFIED): All column names were scanned against the prohibited demographic proxy list per rules.md Section 16 Rule 11 and Rule R-MD-12. Protected attributes (gender, caste, religion, age, disability, nationality, etc.) are strictly excluded from model inputs and evaluation dimensions. This scan is automated; final legal review by qualified counsel is required before beta.

---

## 4. Per-Slice Parity Results

### 4.1. GEOGRAPHIC Parity ❌

| Parity Metric | Value | Threshold | Status |
|:---|:---:|:---:|:---:|
| **Max MAE Ratio (slice/global)** | `nan` | `<= 1.30` | `FAIL` |
| **Max Coverage Gap (|slice - global|)** | `nan` | `<= 0.15` | `FAIL` |
| **Max Abstention Gap (|slice - global|)** | `nan` | `<= 0.25` | `FAIL` |
| **Slices Evaluated** | `1` | — | — |
| **Slices Low Support (N < 10)** | `1` | — | — |

### 4.2. EXPERIENCE_BAND Parity ❌

| Parity Metric | Value | Threshold | Status |
|:---|:---:|:---:|:---:|
| **Max MAE Ratio (slice/global)** | `nan` | `<= 1.30` | `FAIL` |
| **Max Coverage Gap (|slice - global|)** | `nan` | `<= 0.15` | `FAIL` |
| **Max Abstention Gap (|slice - global|)** | `nan` | `<= 0.25` | `FAIL` |
| **Slices Evaluated** | `1` | — | — |
| **Slices Low Support (N < 10)** | `1` | — | — |

### 4.3. ROLE_FAMILY Parity ❌

| Parity Metric | Value | Threshold | Status |
|:---|:---:|:---:|:---:|
| **Max MAE Ratio (slice/global)** | `nan` | `<= 1.30` | `FAIL` |
| **Max Coverage Gap (|slice - global|)** | `nan` | `<= 0.15` | `FAIL` |
| **Max Abstention Gap (|slice - global|)** | `nan` | `<= 0.25` | `FAIL` |
| **Slices Evaluated** | `1` | — | — |
| **Slices Low Support (N < 10)** | `1` | — | — |

### 4.4. EMPLOYER_TIER Parity ❌

| Parity Metric | Value | Threshold | Status |
|:---|:---:|:---:|:---:|
| **Max MAE Ratio (slice/global)** | `nan` | `<= 1.30` | `FAIL` |
| **Max Coverage Gap (|slice - global|)** | `nan` | `<= 0.15` | `FAIL` |
| **Max Abstention Gap (|slice - global|)** | `nan` | `<= 0.25` | `FAIL` |
| **Slices Evaluated** | `0` | — | — |
| **Slices Low Support (N < 10)** | `0` | — | — |

---

## 5. Per-Group Detailed Metrics

| Dimension | Slice | N | MAE Ratio | Coverage | Coverage Gap | Abstention | Pinball | Low Support |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| GEOGRAPHIC | `Metro_West` | `1` | `1.000` | `100.0%` | `0.000` | `0.0%` | `1.783` | ⚠️ |
| EXPERIENCE_BAND | `Senior` | `1` | `1.000` | `100.0%` | `0.000` | `0.0%` | `1.783` | ⚠️ |
| ROLE_FAMILY | `DATA` | `1` | `1.000` | `100.0%` | `0.000` | `0.0%` | `1.783` | ⚠️ |

---

## 6. Data Availability by Operational Group

| Dimension | Slice | N Observations | Status | Note |
|:---|:---|:---:|:---:|:---|
| GEOGRAPHIC | `Metro_West` | `1` | ❌ `ABSENT` | Insufficient data (N=1); abstention expected for this tier. |
| EXPERIENCE_BAND | `Senior` | `1` | ❌ `ABSENT` | Marginal data (N=1) for experience band 'Senior'. |
| ROLE_FAMILY | `DATA` | `1` | ❌ `ABSENT` | Marginal data (N=1). |

---

## 7. Identified Gaps and Mitigations

1. All slices in GEOGRAPHIC have insufficient data (N < 5).
2. All slices in EXPERIENCE_BAND have insufficient data (N < 5).
3. All slices in ROLE_FAMILY have insufficient data (N < 5).
4. No observations found for this slice dimension.

---

## 8. Legal & Ethical Compliance Notes

> [!IMPORTANT]
> LEGAL DISCLAIMER (R-FA-04, status=UNVERIFIED): This fairness audit evaluates statistical prediction parity and data availability across operational groups. It does NOT constitute a legal compliance determination under DPDPA 2023, the Equal Remuneration Act 1976, or any other applicable Indian employment law. All parity gaps are statistical observations, not causal discrimination claims (Rule R-MD-08). Legal review by qualified counsel is required before beta launch.

1. **Rule R-MD-12 / Section 16 Rule 11:** Protected attributes (gender, caste, religion, age, disability) are excluded from all model inputs and audit dimensions.
2. **Rule R-FA-01:** This system is decision support. It does not rank candidates, recommend discriminatory pay, or present itself as an appraisal, offer, or guarantee.
3. **Rule R-FA-04:** Legal status of DPDPA 2023 and employment discrimination law in India is `UNVERIFIED` — qualified counsel must confirm before beta.
4. **Rule R-MD-08:** All parity gaps are associations and statistical observations. No causal discrimination claim is made.
5. **Rule R-MD-02:** Final test set was not used in this audit. Evaluation was performed exclusively on the development (`select`) partition.

---

*Report generated by `compintel.evaluation.fairness_audit` on 2026-10-18T21:36:39.994964+00:00*