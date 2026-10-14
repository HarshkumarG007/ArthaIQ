# PT1 Prototype Target Construction & Exclusion Accounting Report

| Audit Field | Value | Policy Rule |
|:---|:---:|:---|
| **Total Observations Evaluated** | **648** | Exhaustive raw inventory |
| **Strict PT1 Observations Retained** | **0** | Itemized guaranteed cash (`R-MD-07`) |
| **Exploratory Candidate Observations** | **102** | Normalized for diagnostics (T2.09) |
| **Total Excluded / Quarantined** | **648** | Reason-coded quarantine (`R-DA-05`) |
| **Reconciliation Equation** | `648 == 0 + 648` | VERIFIED (0 discrepancy) |

---

## 1. Master Exclusion Breakdown by Reason Code

| Reason Code | Count | % of Evaluated | Primary Trigger & Policy Justification |
|:---|:---:|:---:|:---|
| `EXC_MISSING_COMPENSATION` | 168 | 25.9% | Compensation field is null, 'NA', empty string, or zero. |
| `EXC_NON_FULLTIME` | 158 | 24.4% | Non-full-time employment status (Student, Freelance/Contractor, Part-time, Unemployed). |
| `EXC_GEO_OUT_OF_SCOPE` | 125 | 19.3% | Geographic location outside India (US BLS, US DOL H-1B/PERM, global survey rows). Isolated under Rule `R-MD-08`. |
| `EXC_UNBUNDLED_CTC_OR_AGGREGATE` | 102 | 15.7% | **Rule R-MD-07 Anti-Heuristic Violation:** Self-reported total comp (`CompTotal`) or aggregate CTC conflating variable bonuses, EPF overhead, and equity grants without itemization. |
| `EXC_EXACT_OR_NEAR_DUPLICATE` | 40 | 6.2% | Identical profile tuple (`family`, `seniority_band`, `salary_lpa`) within same survey cluster (`R-DA-06`). |
| `EXC_NON_TECH_OCCUPATION` | 33 | 5.1% | Occupation role outside canonical tech taxonomy (Sales, Marketing, HR, Educator, Academic). |
| `EXC_ENTERPRISE_AGGREGATE` | 12 | 1.9% | Observation is an enterprise-wide census median (BSE/NSE listed IT filings) or macro quantile summary (PLFS macro anchors), not an individual profile tuple. |
| `EXC_COMPENSATION_OUTLIER` | 7 | 1.1% | Annualized salary outside plausible tech compensation bounds (< 1.5 LPA or > 500 LPA). |
| `EXC_CURRENCY_MISMATCH` | 2 | 0.3% | Stated currency is not INR without verified domestic payroll contract. |
| `EXC_MISSING_EXPERIENCE` | 1 | 0.2% | Professional years of experience unobserved or unmappable. |

---

## 2. Per-Source Exclusion Breakdown

| Source ID | Total Rows | Retained Strict | Retained Exploratory | Primary Exclusion Reasons |
|:---|:---:|:---:|:---:|:---|
| `SRC-IND-OFF-01` | 4 | 0 | 0 | `EXC_ENTERPRISE_AGGREGATE` (4) |
| `SRC-KAG-AIJ-01` | 10 | 0 | 7 | `EXC_UNBUNDLED_CTC_OR_AGGREGATE` (7), `EXC_GEO_OUT_OF_SCOPE` (3) |
| `SRC-KAG-AIJ-02` | 6 | 0 | 4 | `EXC_UNBUNDLED_CTC_OR_AGGREGATE` (4), `EXC_GEO_OUT_OF_SCOPE` (2) |
| `SRC-KAG-SO-01` | 300 | 0 | 55 | `EXC_MISSING_COMPENSATION` (87), `EXC_NON_FULLTIME` (74), `EXC_UNBUNDLED_CTC_OR_AGGREGATE` (55) |
| `SRC-KAG-SO-02` | 300 | 0 | 36 | `EXC_NON_FULLTIME` (84), `EXC_MISSING_COMPENSATION` (81), `EXC_GEO_OUT_OF_SCOPE` (51) |
| `SRC-SUP-CORP-01` | 8 | 0 | 0 | `EXC_ENTERPRISE_AGGREGATE` (8) |
| `SRC-USA-BLS-01` | 7 | 0 | 0 | `EXC_GEO_OUT_OF_SCOPE` (7) |
| `SRC-USA-DOL-01` | 8 | 0 | 0 | `EXC_GEO_OUT_OF_SCOPE` (8) |
| `SRC-USA-DOL-02` | 5 | 0 | 0 | `EXC_GEO_OUT_OF_SCOPE` (5) |

---

## 3. Exploratory Candidate Target Distribution Summary

The **102 deduplicated exploratory observations** (from SO 2024, SO 2023, and ai-jobs) provide empirical shape diagnostics for Task T2.09 (Sufficiency Analysis & Bootstrap Intervals):

- **Sample Size:** $N = 102$ valid exploratory observations.
- **Measure:** Normalized annual total compensation in INR Lakhs Per Annum (LPA).
- **Quarantine Flag:** `is_unbundled_aggregate = True`, `quarantined_from_production = True`.
- **Distributional Quantiles (Empirical):**
  - **P10:** ₹6.00 LPA
  - **P25:** ₹9.50 LPA
  - **P50 (Median):** ₹20.00 LPA
  - **P75:** ₹32.00 LPA
  - **P90:** ₹45.00 LPA
  - **Mean ± SD:** ₹23.39 ± ₹17.95 LPA

---

## 4. Architectural Feasibility Conclusion

> [!IMPORTANT]
> **Zero Strict Training Observations Confirmed:**
> Out of 648 evaluated candidate observations, exactly **0 records** satisfy the strict unbundled `guaranteed_cash_annual` criteria required for production PT1 > Public datasets either fail geographic scope, represent enterprise-level aggregates, or self-report unbundled total compensation conflating variable cash and equity (`R-MD-07`).
> This empirically proves the necessity of **Task T2.10** (ArthaIQ Governed Voluntary Intake & Corporate Partnerships) to acquire itemized compensation ground truth.
