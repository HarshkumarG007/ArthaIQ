# ArthaIQ Automated Data Quality & Contract Audit Report

| Field | Value |
|---|---|
| **Snapshot ID** | `SNAP-69F20D876BCB` |
| **Schema Version** | `1.0.0` |
| **Git Commit** | `e70ddbdc02` |
| **Manifest Digest (SHA-256)** | `87301ae50e59983f...` |
| **Generated At (UTC)** | `2026-10-16T14:06:16.941332+00:00` |
| **Overall Contract Verdict** | **PASSED** |

---

## 1. Executive Summary & Volume Reconciliation (Rule R-DA-05)

Mathematical count reconciliation verifies that no observations are silently dropped:

| Metric | Count | Share | Status |
|---|---|---|---|
| Total Raw Evaluated | **665** | 100.0% | Audited |
| Admitted Canonical Observations | **5** | 0.75% | Ground Truth |
| Quarantined Records | **660** | 99.25% | Isolated |
| Reconciliation Delta ($\Delta$) | **0** | 0.0% | **PASS** (Rule R-DA-05) |

> [!NOTE]
> Zero silent drops is a non-negotiable architectural invariant (`R-DA-05`).
> $\Delta = \text{Total} - (\text{Valid} + \text{Quarantined}) = 665 - (5 + 660) = 0$.

---

## 2. Data Contract Verification Checklist

| Rule ID | Contract Specification | Status |
|---|---|---|
| `reconciliation_contract` | Zero silent drops count conservation (R-DA-05) | PASSED |
| `schema_contract` | Pandera strict canonical dataframe schema conformance | PASSED |
| `unbundling_contract` | Anti-heuristic unbundling compliance (R-MD-07) | PASSED |
| `pii_safety_contract` | Zero cleartext PII leakage in datasets (R-DA-07) | PASSED |
| `cluster_id_contract` | Mandatory cluster IDs populated for all records (R-DA-06) | PASSED |
| `sqsf_provenance_contract` | Source Quality Scores and tiers attached (T3.12) | PASSED |

---

## 3. Quarantine Reason Distribution

Observations isolated from primary model training under deterministic criteria:

| Quarantine Reason Code | Count | Percentage | Operational Policy |
|---|---|---|---|
| `missing_pay` | 192 | 29.1% | Governed Isolation |
| `non_fulltime` | 158 | 23.9% | Governed Isolation |
| `unbundled_aggregate` | 152 | 23.0% | Governed Isolation |
| `geo_out_of_scope` | 125 | 18.9% | Governed Isolation |
| `enterprise_aggregate` | 24 | 3.6% | Governed Isolation |
| `outlier` | 7 | 1.1% | Governed Isolation |
| `currency_mismatch` | 2 | 0.3% | Governed Isolation |

---

## 4. Canonical Target Distribution (Nominal INR LPA)

| Statistic | Guaranteed Cash (INR LPA) | Years Experience |
|---|---|---|
| Min | ₹8.40 LPA | 1.0 yrs |
| P10 | ₹8.40 LPA | — |
| P25 | ₹18.00 LPA | — |
| Median (P50) | **₹26.40 LPA** | **7.5 yrs** |
| Mean | ₹26.16 LPA | 6.3 yrs |
| P75 | ₹30.00 LPA | — |
| P90 | ₹48.00 LPA | — |
| Max | ₹48.00 LPA | 11.0 yrs |

---

## 5. Occupational & Seniority Profile

| Role Family | Records | Seniority Band | Records | Metro Location | Records |
|---|---|---|---|---|---|
| `DATA`: 1 | — | `JR`: 1 | — | `BENGALURU`: 3 | — |
| `MLAI`: 1 | — | `MID`: 1 | — | `HYDERABAD`: 1 | — |
| `SWE`: 3 | — | `SR`: 2 | — | `PUNE`: 1 | — |
| — | — | `STAFF`: 1 | — | — | — |

---

## 6. Entity Resolution & Quality Scoring (SQSF)

| Metric | Value | Reference Rule |
|---|---|---|
| Distinct Person Clusters | **5** | Rule R-DA-06 (Dedup before split) |
| Distinct Employer Clusters | **1** | Task T3.10b (Entity resolution) |
| Distinct Posting Clusters | **4** | Task T3.10b (Posting clusters) |
| Exact Duplicate Count | **0** | Task T3.10a (Exact dedup) |
| Mean Source Quality Score | **96.0 / 100** | Rule R-UQ-07 (Decoupled evidence) |
| PT1 Training Eligible Rows | **5** | Task T3.12 (SQSF Gate) |
