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
