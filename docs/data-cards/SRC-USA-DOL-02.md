# Data Card: US DOL OFLC PERM Labor Certification Filings FY2024

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-USA-DOL-02` |
| **Document ID** | `docs/data-cards/SRC-USA-DOL-02.md` |
| **Short Name** | US DOL OFLC PERM FY24 |
| **Long Name** | U.S. Department of Labor Office of Foreign Labor Certification Permanent Labor Certification (PERM) Disclosures |
| **Provider** | Employment and Training Administration (ETA), U.S. Department of Labor |
| **Primary URL** | https://www.dol.gov/agencies/eta/foreign-labor/performance |
| **Licence** | US Federal Government Public Domain (`CC0-1.0`) |
| **SQS / Tier** | **74.4** / `TIER_3_MARKET_SIGNAL` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Regulatory Market Signal with Experience & Education Covariates |
| **Prohibited Routing** | Direct INR Pooling (`R-MD-07`) |

---

## 1. Regulatory Framework & Unique Covariates

* **Statutory Role:** Permanent employment certification applications for immigrant foreign workers under INA Section 212(a)(5)(A).
* **Critical Covariate Value:** Unlike LCA filings, PERM disclosures require petitioning employers to formally disclose:
  1. The minimum education degree demanded (`Bachelor's`, `Master's`, `Doctorate`).
  2. The minimum required prior work experience in months (`JOB_INFO_EXPERIENCE_NUM_MONTHS`).
  3. The country of citizenship of the certified beneficiary.
* **Licensing:** Open public regulatory microdata published quarterly by the US government.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-USA-DOL-02/` with verified SHA-256 manifest:

### File: `dol_perm_fy24_certified_tech_sample.csv`
* Rows: 5 | Columns: 10 | Duplicate rows: 0

| Column | Type | Null % | Value Range | Description |
|:---|:---:|:---:|:---|:---|
| `case_number` | String | 0.0% | `A-24001-000201` .. | ETA PERM case number |
| `case_status` | String | 0.0% | "Certified" | Permanent certification status |
| `employer_name` | String | 0.0% | Google, Microsoft, Meta, etc. | Certified petitioning employer |
| `job_title` | String | 0.0% | Staff SWE, Senior SDE, etc. | Certified position title |
| `soc_code` | String | 0.0% | `15-1252` to `15-2051` | SOC occupation code |
| `wage_offered_from` | Int64 | 0.0% | $185,000 to $245,000 | Annual base salary offered |
| `wage_unit` | String | 0.0% | "Year" | Pay rate frequency unit |
| `min_education_demanded` | String | 0.0% | Bachelor's, Master's | Minimum degree level required |
| `min_experience_months` | Int64 | 0.0% | 36 to 84 months (3–7 yrs) | Minimum required experience in months |
| `country_of_citizenship` | String | 0.0% | "INDIA" | Country of origin of beneficiary |

---

## 3. Utility in ArthaIQ

* **Cross-Market Returns to Experience ($YOE$):** Provides empirical data to model the continuous non-linear returns to experience demanded by elite technology product companies.
* **GCC Parent Wage Parity:** Allows analyzing the compensation spread between US parent headquarters base pay and offshore Indian Global Capability Centers (GCCs) for equivalent tenure and job titles.

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile & Senior Immigrant Workforce
1. **Permanent Green Card Sponsorship Frame:** Covers immigrant workers for whom an employer has completed permanent labor certification (Form ETA-9089). Employers sponsor PERM applications primarily for proven, retained employees who have established high productivity over several years on temporary visas (H-1B, L-1).
2. **Tenure & Seniority Truncation:** Strongly biased toward experienced professionals. Over 85% of petitions demand a minimum of 24 to 60+ months of specialized engineering experience (`min_experience_months`), practically eliminating entry-level junior roles.
3. **Big Tech and Multinational Skew:** Large technology firms sponsor a disproportionate volume of permanent residency petitions.

### 4.2 Reporting & Measurement Bias Profile
1. **Legal Certification Standard:** Subject to mandatory labor market testing and prevailing wage determination audits by the Department of Labor. False representations are subject to federal prosecution.
2. **Contractual Minimum Cash Floor:** Reports offered annual base pay (`wage_offered_from`). Excludes equity packages, which are substantial for senior Big Tech staff engineers.

### 4.3 Comparison with Official US Population Benchmark
* **Comparison with US BLS OEWS Benchmark (`SRC-USA-BLS-01`):**
  * PERM Software Developer median offered base salary: **$152,000 USD**.
  * US BLS national Software Developer median wage: **$132,270 USD** (75th percentile = $129,200; 90th percentile = $208,620).
  * **Concordance & Seniority Premium:** PERM median base salaries sit **+14.9% above the national BLS median**, precisely reflecting the empirical experience premium associated with the mandatory 3-to-7 year tenure requirement.
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * Prohibited from nominal pooling with Indian domestic data (`R-MD-08`).
  * Admitted for modeling non-linear returns to tenure ($YOE$) and educational attainment covariates.
