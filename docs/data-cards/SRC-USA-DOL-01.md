# Data Card: US DOL OFLC H-1B LCA Disclosure Data FY2024

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-USA-DOL-01` |
| **Document ID** | `docs/data-cards/SRC-USA-DOL-01.md` |
| **Short Name** | US DOL OFLC H-1B LCA FY24 |
| **Long Name** | U.S. Department of Labor Office of Foreign Labor Certification H-1B Labor Condition Applications |
| **Provider** | Employment and Training Administration (ETA), U.S. Department of Labor |
| **Primary URL** | https://www.dol.gov/agencies/eta/foreign-labor/performance |
| **Licence** | US Federal Government Public Domain (`CC0-1.0`) |
| **SQS / Tier** | **74.4** / `TIER_3_MARKET_SIGNAL` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Regulatory Market Signal (US Tech Base Salaries & Expat Wage Floors) |
| **Prohibited Routing** | Direct pooling with domestic INR training sets (`R-MD-07`) |

---

## 1. Legal Authority & Regulatory Context

* **Statutory Framework:** Immigration and Nationality Act (INA) Section 212(n). Employers petitioning for H-1B nonimmigrant workers must file an LCA certifying that they will pay wages that are at least the actual wage paid to other workers with similar experience or the prevailing wage rate, whichever is higher.
* **Legal Liability:** False statements on Form ETA-9035/9035E are subject to federal perjury penalties (18 U.S.C. 1001) and substantial civil money penalties. Consequently, reported offered wage floors exhibit exceptionally high legal fidelity.
* **Licensing:** Public regulatory disclosure. Fully open for research and commercial modeling.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-USA-DOL-01/` with verified SHA-256 manifest:

### File: `dol_lca_fy24_certified_tech_sample.csv`
* Rows: 8 | Columns: 11 | Duplicate rows: 0

| Column | Type | Null % | Value Range | Description |
|:---|:---:|:---:|:---|:---|
| `case_number` | String | 0.0% | `I-200-24001-000101` .. | Official ETA application identifier |
| `case_status` | String | 0.0% | "Certified" | Regulatory adjudication status |
| `employer_name` | String | 0.0% | Amazon, Google, TCS, etc. | Certified petitioning employer |
| `job_title` | String | 0.0% | Software Engineer .. | Employer internal job title |
| `soc_code` | String | 0.0% | `15-1252` to `15-2051` | Standard Occupational Classification |
| `soc_title` | String | 0.0% | Software Devs to Data Sci | Standard occupational title |
| `wage_rate_from` | Int64 | 0.0% | $98,000 to $185,000 | Certified offered annual base salary |
| `wage_unit` | String | 0.0% | "Year" | Pay frequency unit |
| `prevailing_wage` | Int64 | 0.0% | $92,000 to $145,000 | Statutory prevailing wage floor |
| `worksite_city` | String | 0.0% | Cupertino, Seattle, etc. | Location of primary work facility |
| `worksite_state` | String | 0.0% | CA, NJ, TX, WA | State of employment |

---

## 3. Compensation Measure & Biases

* **Compensation Measure Alignment:** Measures **contractually committed gross annual base salary** (`wage_rate_from`). Completely excludes variable performance bonuses, signing bonuses, and equity grants (RSUs).
* **Selection Bias:**
  1. Represents sponsored foreign talent rather than the entire domestic US workforce.
  2. Over-represents multinational Indian IT services firms (TCS, Infosys, Wipro, Cognizant) and large Big Tech firms (Google, Meta, Microsoft, Amazon).
  3. Represents an empirical lower-bound ceiling on base salary, as employers certify the minimum rate they contractually guarantee.

---

## 4. Pipeline Routing & Staleness Policy

* **Scope Tagging:** Permanently tagged with `country: US` and `currency: USD`.
* **Refresh Cadence:** Quarterly cumulative releases by OFLC.
* **Deflation Policy:** Deflated using US BLS CPI-U series for temporal adjustments older than 90 days.
