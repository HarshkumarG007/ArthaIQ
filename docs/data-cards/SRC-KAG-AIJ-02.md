# Data Card: JobsInData 2024 / ai-jobs Open Feed

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-KAG-AIJ-02` |
| **Document ID** | `docs/data-cards/SRC-KAG-AIJ-02.md` |
| **Short Name** | JobsInData 2024 Feed |
| **Long Name** | Jobs in Data / ai-jobs.net Global Tech Salaries 2024 Open Feed |
| **Provider** | JobsInData / ai-jobs.net |
| **Primary URL** | https://jobsindata.com/salaries/ |
| **Kaggle Mirror** | `hummaamqaasim/jobs-in-data` |
| **Licence** | Creative Commons Zero v1.0 Universal (`CC0-1.0` Public Domain) |
| **SQS / Tier** | **60.8** / `TIER_4_SUPPLEMENTARY` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Approved Benchmark (Feature Curve Exploration & Remote Spreads) |
| **Prohibited Routing** | Direct PT1 ground-truth training without domain regularizer |

---

## 1. Provenance & Schema Profiling

Acquired under `data/raw/SRC-KAG-AIJ-02/` with verified SHA-256 manifest:

### File: `jobs_in_data_2024.csv`
* Rows: 6 | Columns: 12 | Duplicate rows: 0 (Profiled sample extract)

| Column | Type | Null % | Example Values | Description |
|:---|:---:|:---:|:---|:---|
| `work_year` | Int64 | 0.0% | 2024 | Calendar year of observation |
| `job_title` | String | 0.0% | "Machine Learning Engineer" | Granular tech role |
| `job_category` | String | 0.0% | "Machine Learning and AI" | High-level role family |
| `salary_currency` | String | 0.0% | USD, INR | Currency of payment |
| `salary` | Int64 | 0.0% | Nominal amount | Contracted salary in local currency |
| `salary_in_usd` | Int64 | 0.0% | $10,200 to $190,000 | USD equivalent at collection |
| `employee_residence` | String | 0.0% | US, IN | Employee residence country |
| `experience_level` | String | 0.0% | Entry, Mid, Senior | Experience level tier |
| `employment_type` | String | 0.0% | Full-time | Employment contract type |
| `work_setting` | String | 0.0% | In-person, Hybrid, Remote | Work arrangement |
| `company_location` | String | 0.0% | US, IN | Employer country |
| `company_size` | String | 0.0% | M, L | Enterprise size category |

---

## 2. Freshness & Utility in ArthaIQ

* **Temporal Freshness:** 2024 collection window, reflecting current post-pandemic salary moderation.
* **Analytical Application:** Used to validate feature interactions between `experience_level`, `work_setting` (Remote vs Hybrid vs In-person), and international employer location spreads.
