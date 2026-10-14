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

---

## 3. Selection & Reporting Bias Assessment

### 3.1 Selection Bias Profile & Remote Tech Skew
1. **Remote Work Disproportion:** Over 65% of recorded roles feature remote or hybrid work settings, strongly over-representing developers capable of securing decentralized employment.
2. **Specialized AI Focus:** Captures cutting-edge roles (Prompt Engineer, LLM Engineer, MLOps Specialist) with minimal representation of legacy enterprise maintenance or IT infrastructure support.
3. **Sparse Domestic Indian Representation:** Low overall Indian sample volume ($N < 150$), rendering it vulnerable to high sampling variance.

### 3.2 Reporting & Measurement Bias Profile
1. **Unverified Compensation Aggregation:** Captured without payslip audit; conflates base cash with performance incentives and unvested equity grants.
2. **Currency Conversion via Spot FX:** Raw pay converted to USD at instantaneous collection rates, obscuring domestic purchasing power nuances.

### 3.3 Comparison with Official Population Benchmarks
* **Comparison with MOSPI PLFS Benchmark (`SRC-IND-OFF-01`):** Indian tech entries in the 2024 feed display median annualized pay equivalent to **₹24.50 LPA**, representing a **+172% divergence** over the national PLFS benchmark (₹9.00 LPA). This substantial premium reflects remote USD consulting rates and AI/ML specialization premiums.
* **Comparison with US Population Benchmark (`SRC-USA-BLS-01`):** US data roles display a median of $142,000, aligning closely with BLS May 2023 75th percentile benchmarks for computer and mathematical occupations.
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * Blocked from direct PT1/PT2 training per Rules `R-DA-01` and `R-MD-08`.
  * Admitted exclusively as an auxiliary signal for remote work adjustment ratios and feature ablation studies.
