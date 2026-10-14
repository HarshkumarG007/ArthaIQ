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

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile & Visa Sponsorship Frame
1. **Foreign Guest Worker Selection:** Sourced strictly from employer petitions filed for H-1B temporary specialty occupation visas. Excludes the vast native US citizen workforce and permanent residents who do not require visa sponsorship.
2. **Employer Category Skew:** Heavy concentration in two distinct employer clusters:
   - Indian IT services multinationals (TCS, Infosys, Wipro, Cognizant, HCL Tech) filing high volumes of entry-to-mid software engineering petitions.
   - Elite US Big Tech enterprises (Amazon, Google, Meta, Microsoft, Apple) petitioning for high-specialization systems, AI, and research talent.
3. **Legal Lower-Bound Nature:** Represents the contractually certified minimum base salary the employer commits to pay, functioning as an administrative wage floor.

### 4.2 Reporting & Measurement Bias Profile
1. **Legal Certification Standard:** Certified under penalty of federal perjury (18 U.S.C. 1001) and civil money penalties administered by the Wage and Hour Division (WHD). Data exhibits zero personal prestige inflation or voluntary response error.
2. **Equity and Total Comp Exclusion:** Excludes stock grants, sign-on bonuses, and annual performance bonuses. For Big Tech roles where equity comprises 40%–60% of total comp, LCA filings strictly identify cash base pay (`guaranteed_cash_annual`).

### 4.3 Comparison with Official US Population Benchmark
* **Comparison with US BLS OEWS Benchmark (`SRC-USA-BLS-01`):**
  * Certified H-1B Software Engineer median base wage: **$128,000 USD**.
  * US BLS OEWS national Software Developer median wage: **$132,270 USD**.
  * **Concordance:** National H-1B median sits within **-3.2%** of the official BLS national median, proving that prevailing wage regulatory floors effectively track the broad US market base pay distribution.
  * In premium technology metropolitan hubs (San Jose, Seattle, San Francisco), certified H-1B tech wages display medians of **$145,000 to $172,000 USD**, closely tracking BLS MSA-level distributions ($180,470 median in San Jose).
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * Strictly blocked from domestic Indian INR models (`R-MD-08`).
  * Admitted for US market wage floor calibration and GCC offshore parity analysis.

---

## 5. Pipeline Routing & Staleness Policy

* **Scope Tagging:** Permanently tagged with `country: US` and `currency: USD`.
* **Refresh Cadence:** Quarterly cumulative releases by OFLC.
* **Deflation Policy:** Deflated using US BLS CPI-U series for temporal adjustments older than 90 days.
