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

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile & Niche Audience Skew
1. **AI/ML Specialist Skew:** The user base of ai-jobs.net consists almost entirely of data scientists, machine learning engineers, and data engineers. Traditional full-stack, mobile, DevOps, and enterprise IT services developers are absent.
2. **International Remote Contractor Over-Representation:** A significant proportion of Indian respondents work remotely for North American or Western European companies, earning dollar-pegged international contract compensation rather than domestic Indian market pay.
3. **Small Sample Size:** Domestic India resident sample is sparse ($N \approx 200$), clustered heavily in senior roles.

### 4.2 Reporting & Measurement Bias Profile
1. **FX Conversion Distortion:** `salary_in_usd` is converted from local currencies using spot exchange rates on the date of collection. Converting Indian INR to USD via spot rates ignores purchasing power parity and creates artificial wage volatility when exchange rates fluctuate.
2. **Unbundled Total Comp Aggregate:** Reports an undefined single `salary` number, conflating base cash with variable bonuses. Fails line-item unbundling under Rule `R-MD-07`.

### 4.3 Comparison with Official Population Benchmarks
* **Comparison with MOSPI PLFS Benchmark (`SRC-IND-OFF-01`):** Median salary for Indian data roles in this dataset is $\sim \$26,500$ USD (approx. **₹22.00 LPA** at collection FX), which is **+144% higher than the PLFS urban software developer median of ₹9.00 LPA**.
* **Comparison with US Population Benchmark (`SRC-USA-BLS-01`):** For US-based Data Scientists, the dataset median of $\sim \$150,000$ USD aligns reasonably with the BLS OEWS May 2023 national median of $108,020–$136,620 for `SOC 15-2051` (Data Scientists), showing modest upward selection toward startup/venture-backed tech.
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * Strictly blocked from Indian domestic `PT1` / `PT2` direct training sets (`R-DA-01`, `R-MD-08`).
  * Restricted to international relative spread analysis and global remote work benchmark exploratory modules.
