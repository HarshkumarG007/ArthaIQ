# Data Card: ai-jobs.net Data Science Salaries 2023

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-KAG-AIJ-01` |
| **Document ID** | `docs/data-cards/SRC-KAG-AIJ-01.md` |
| **Short Name** | ai-jobs.net DS Salaries 2023 |
| **Long Name** | Data Science Job Salaries 2023 — ai-jobs.net Open Feed (Kaggle Mirror) |
| **Provider** | ai-jobs.net |
| **Primary URL** | https://ai-jobs.net/salaries/download/ |
| **Kaggle Mirror** | `arnabchaki/data-science-salaries-2023` |
| **Licence** | Creative Commons Zero v1.0 Universal (`CC0-1.0` Public Domain) |
| **SQS / Tier** | **60.2** / `TIER_4_SUPPLEMENTARY` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Approved Benchmark (Global Purchasing-Power Parity & Remote Spreads) |
| **Prohibited Routing** | Direct PT1 ground-truth training without domain adaptation (`R-DA-01`) |

---

## 1. Provenance, Licensing & Legal Integrity

* **Source Authority:** Community salary collection feed maintained by ai-jobs.net.
* **Licensing:** Dedicated to the public domain under `CC0 1.0 Universal`. Unrestricted research and commercial reuse permitted.
* **Personal Data:** Completely aggregated and scrubbed; no names, emails, or company identifiers are recorded.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-KAG-AIJ-01/` with verified SHA-256 manifest:

### File: `ai_jobs_ds_salaries_2023.csv`
* Rows: 10 | Columns: 11 | Duplicate rows: 0 (Profiled sample extract)

| Column | Type | Null % | Value Range / Values | Description |
|:---|:---:|:---:|:---|:---|
| `work_year` | Int64 | 0.0% | 2020 to 2023 | Year the salary was earned |
| `experience_level` | String | 0.0% | EN, MI, SE, EX | Seniority level (Entry, Mid, Senior, Executive) |
| `employment_type` | String | 0.0% | FT, PT, CT, FL | Employment type (Full-time, Part-time, Contract, Freelance) |
| `job_title` | String | 0.0% | Data Scientist, ML Engineer, etc. | Normalized occupational title |
| `salary` | Int64 | 0.0% | Nominal local units | Gross salary in local currency |
| `salary_currency` | String | 0.0% | USD, INR, EUR, GBP | Local currency code |
| `salary_in_usd` | Int64 | 0.0% | $8,480 to $280,000 | Converted USD salary via FX at collection |
| `employee_residence` | String | 0.0% | US, IN, DE, etc. | Alpha-2 country code of employee |
| `remote_ratio` | Int64 | 0.0% | 0, 50, 100 | Work arrangement (0 = Onsite, 100 = Fully Remote) |
| `company_location` | String | 0.0% | US, IN, DE, etc. | Alpha-2 country code of employing entity |
| `company_size` | String | 0.0% | S, M, L | Employer size (<50, 50-250, >250) |

---

## 3. Scope & Analytical Utility

* **Global PPP Spreads:** Enables empirical comparison between US and Indian tech compensation for equivalent job titles (`Data Scientist`, `Machine Learning Engineer`).
* **Remote Work Premiums:** Allows measuring the empirical premium earned by Indian engineers working remotely for US/EU employers vs domestic firms.
* **Sample Size Caveat:** Domestic Indian resident records comprise only $\sim 200$ rows in the full dataset; insufficient by itself to satisfy core cell sufficiency ($N_{\text{eff}} \ge 50$ per occupation $\times$ tier).
