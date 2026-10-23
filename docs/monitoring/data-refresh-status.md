# ArthaIQ Data Freshness & Scheduled Refresh Status

> **Governance & Compliance:** PRD NFR-11, RSK-11, Rule R-DA-01, Task T10.04.
> **System Health:** **🟢 PASS / HEALTHY** | **Evaluated As-Of:** `2026-10-23 18:42:36 UTC`
> **Run ID:** `REFRESH-1DF06DB4`

## 1. Executive Summary

| Metric | Value | Threshold / SLA Rule | Status |
|:---|:---:|:---:|:---:|
| **Total Sources Audited** | `14` | All approved sources | ✅ Complete |
| **Fresh Sources** | `14` | Age < 75% SLA | ✅ Nominal |
| **Warning Sources** | `0` | 75% SLA ≤ Age < SLA | ✅ None |
| **Stale Sources** | `0` | Age ≥ SLA | ✅ None |
| **Operational Alerts Dispatched** | `0` | 0 Critical Alerts | ✅ Zero Alerts |

---

## 2. Source Freshness Audit Matrix

| Source ID | Source Name | Cadence | Max SLA (Days) | Observed Age (Days) | Status | Operational Action |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `SRC-IND-OFF-01` | MOSPI Periodic Labour Force Survey (PLFS) | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-IND-OFF-03` | EPFO Monthly Payroll Microdata | Monthly | `60d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-INT-VOL-01` | ArthaIQ Voluntary Intake Submissions | Daily | `30d` | `8.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-KAG-AIJ-01` | AI/ML Jobs Salary Survey 2023 | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-KAG-AIJ-02` | AI/ML Jobs Salary Survey 2024 | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-KAG-SO-01` | Stack Overflow Developer Survey 2023 | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-KAG-SO-02` | Stack Overflow Developer Survey 2024 | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-SUP-CORP-01` | BSE/NSE Corporate Remuneration Filings (MRE Section 197) | Quarterly | `180d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-SUP-MAC-01` | RBI DBIE Macro Indices (CPI & FX) | Monthly | `45d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-SUP-TAX-01` | Union Budget Income Tax Slabs | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-SUP-TAX-02` | State Professional Tax Slabs | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-USA-BLS-01` | US BLS Occupational Employment and Wage Statistics (OEWS) | Annual | `365d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-USA-DOL-01` | US DOL Foreign Labor Certification LCA Disclosures | Quarterly | `120d` | `10.0d` | 🟢 FRESH | Nominal monitoring |
| `SRC-USA-DOL-02` | US DOL Foreign Labor Certification PERM Disclosures | Quarterly | `120d` | `10.0d` | 🟢 FRESH | Nominal monitoring |

---

## 3. Dispatched Operational Alerts

*No active freshness alerts. All data sources are within designated SLAs.*

---

## 4. Scheduled Refresh Cadence & Staleness Recovery Protocol

1. **High-Frequency Ingestion (Daily / Rolling):**
   - `SRC-INT-VOL-01` (Voluntary user submissions) streams into staging. Overdue > 30 days triggers an automated CRITICAL alarm flagging pipeline stall.
2. **Macro Series Ingestion (Monthly):**
   - `SRC-SUP-MAC-01` (RBI DBIE CPI and USD/INR FX) runs monthly via `scripts/acquire_sources.py`. Overdue > 45 days freezes deflation.
3. **Statutory Benchmark Ingestion (Quarterly / Annual):**
   - Government microdata (`SRC-IND-OFF-01`, `SRC-USA-BLS-01`, `SRC-USA-DOL-01`) operates on 120d to 365d SLAs. Releases are ingested through license barriers.
4. **Zero-PII Metric Guarantee:**
   - Freshness telemetry is strictly partitioned by `source_id` without exposing user identifiers or compensation amounts (Rules R-CD-06, R-DA-07).
