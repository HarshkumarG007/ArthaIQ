# Data Card: Labour Bureau Quarterly Employment Survey (QES) IT/BPO

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-IND-OFF-03` |
| **Document ID** | `docs/data-cards/SRC-IND-OFF-03.md` |
| **Short Name** | Labour Bureau QES IT/BPO |
| **Long Name** | Labour Bureau All-India Quarterly Survey of Employment (AQSE) IT/BPO Sector |
| **Provider** | Labour Bureau, Ministry of Labour and Employment, Government of India |
| **Primary URL** | https://www.labourbureau.gov.in/quarterly-employment-survey |
| **Licence** | Government Public Open Data (`OGDL-IN`) |
| **SQS / Tier** | **59.2** / `TIER_6_MACRO_CONTEXT_ONLY` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Auxiliary Macro Signal (IT/BPO Formal Employment & Contract Ratios) |
| **Prohibited Routing** | Wage prediction models (Contains zero individual wage microdata) |

---

## 1. Source Provenance & Legal Review

* **Collection Authority:** Labour Bureau, Ministry of Labour and Employment, Government of India.
* **Scope:** Formal establishments employing 10 or more workers across 9 non-farm sectors, specifically including **IT/BPO** (`NIC Division 62 & 63`).
* **Terms & Rights:** Official government statistical release. Free reuse with attribution.
* **Personal Data:** Zero personal or establishment identifiable data; published as aggregate statistical tabulations.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-IND-OFF-03/` with verified SHA-256 manifest:

### File: `qes_it_bpo_formal_employment.csv`
* Rows: 3 | Columns: 8 | Duplicate rows: 0

| Column | Type | Null % | Value Range | Description |
|:---|:---:|:---:|:---|:---|
| `round_number` | String | 0.0% | Round 7 to Round 9 | Survey round identifier |
| `reference_quarter` | String | 0.0% | Q2 FY22-23 to Q4 FY22-23 | Reference fiscal quarter |
| `sector_name` | String | 0.0% | "IT / BPO" | Target industrial sector |
| `nic_codes` | String | 0.0% | "62, 63" | NIC-2008 coverage codes |
| `estimated_employment` | Int64 | 0.0% | 3,310,000 to 3,450,000 | Estimated total formal workforce |
| `regular_workers_pct` | Float64 | 0.0% | 88.4% to 89.5% | Percentage of regular employees |
| `contract_workers_pct` | Float64 | 0.0% | 10.5% to 11.6% | Percentage of contract/gig workers |
| `female_workers_pct` | Float64 | 0.0% | 34.5% to 35.2% | Female workforce participation rate |

---

## 3. Utility & Identification Limits in ArthaIQ

* **Macro Headcount Context:** Establishes aggregate population bounds for the formal Indian IT/BPO sector (~3.45 million formal employees in establishments of 10+ workers).
* **Workforce Stability Benchmark:** Demonstrates that ~88.5% of formal tech sector workers are on regular payrolls, supporting the validity of annual guaranteed cash compensation (`guaranteed_cash_annual`) as the primary compensation target.
* **Strict Ingestion Limitation:** Fails Hard Gate 2 for direct compensation modeling because it reports headcount metrics exclusively, with zero wage observations. Restricted strictly to macro context reporting.

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile & Scope Boundaries
1. **Establishment Cutoff Bias:** Covers exclusively registered non-farm establishments employing **10 or more workers**. Systematically excludes early-stage technology startups (1–9 employees), independent freelance software engineers, and boutique consultancies.
2. **Sub-Sector Conflation:** Combines high-margin software development and IT architecture (`NIC 62`) with high-volume business process outsourcing (BPO/ITeS, `NIC 63`). BPO call center operations inflate headcount volume while depressing average skill profiles relative to pure software engineering.

### 4.2 Reporting & Measurement Bias Profile
1. **Administrative Census Reporting:** Data is compiled from mandatory establishment returns submitted to the Ministry of Labour and Employment. Exhibits high administrative accuracy for headcounts with zero individual recall error.
2. **Wage Dimension Absence:** Completely lacks wage, compensation, or payroll expenditure variables; cannot observe compensation distributions or wage variance.

### 4.3 Comparison with Official Population Benchmarks
* **Comparison with MOSPI PLFS (`SRC-IND-OFF-01`):** QES estimated IT/BPO workforce of 3.45 million formal workers strongly corroborates PLFS urban tech employment estimates (~3.1–3.6 million workers in `NIC 62/63`).
* **Contract Ratio Concordance:** QES regular employee share of 88.5% closely matches PLFS regular salaried worker proportion of 86.2% for urban IT professionals, proving that informal or contract gig labor is a minor fraction of the core formal Indian technology sector.
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * Assigned strictly as a macro sector-growth feature covariate (`macro_covariates`).
  * Never routed to any wage-quantile prediction model.
