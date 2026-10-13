# Data Card: US Bureau of Labor Statistics OEWS May 2023

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-USA-BLS-01` |
| **Document ID** | `docs/data-cards/SRC-USA-BLS-01.md` |
| **Short Name** | BLS OEWS Tech Estimates |
| **Long Name** | US BLS Occupational Employment and Wage Statistics (OEWS) May 2023 |
| **Provider** | U.S. Bureau of Labor Statistics, U.S. Department of Labor |
| **Primary URL** | https://www.bls.gov/oes/ |
| **Licence** | US Federal Government Work — Public Domain (`CC0-1.0` / 17 USC 105) |
| **SQS / Tier** | **78.2** / `TIER_2_POPULATION_BENCHMARK` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | US Cross-Market Benchmark & Structural Wage Ratio Analysis |
| **Prohibited Routing** | PT1/PT2 Direct Training; Nominal Currency Pooling with India records (`R-MD-07`) |

---

## 1. Provenance, Authority & Legal Terms

* **Collection Agency:** U.S. Bureau of Labor Statistics (BLS).
* **Sampling Frame:** Semiannual establishment survey covering approximately 1.1 million nonfarm business establishments across six survey panels over 3 years.
* **Licensing:** US Federal government public domain. Commercial and research reuse fully permitted without restriction.
* **Privacy:** Confidentiality protected under the Confidential Information Protection and Statistical Efficiency Act (CIPSEA). Cell counts and percentiles are statistically suppressed where employer identification could occur.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-USA-BLS-01/` with verified SHA-256 manifest:

### File: `bls_oews_tech_estimates_may2023.csv`
* Rows: 7 | Columns: 11 | Duplicate rows: 0

| Column | Type | Null % | Value Range | Description |
|:---|:---:|:---:|:---|:---|
| `area_code` | Int64 | 0.0% | 0 to 42660 | FIPS / MSA area code (0 = National US) |
| `area_name` | String | 0.0% | National to Seattle MSA | Geographic area description |
| `soc_code` | String | 0.0% | 15-1251 to 15-2051 | 2018 Standard Occupational Classification |
| `occupation_title` | String | 0.0% | Software Devs to QA Analysts | Standard occupational title |
| `total_employment` | Int64 | 0.0% | 68,220 to 1,656,880 | Estimated employment headcount |
| `annual_mean_usd` | Int64 | 0.0% | $102,790 to $187,890 | Annual mean straight-time cash salary |
| `annual_p10_usd` | Int64 | 0.0% | $56,370 to $108,500 | 10th percentile annual cash salary |
| `annual_p25_usd` | Int64 | 0.0% | $74,210 to $145,200 | 25th percentile annual cash salary |
| `annual_median_p50_usd` | Int64 | 0.0% | $99,770 to $180,550 | 50th percentile (Median) annual salary |
| `annual_p75_usd` | Int64 | 0.0% | $129,200 to $228,400 | 75th percentile annual cash salary |
| `annual_p90_usd` | Int64 | 0.0% | $164,890 to $275,000 | 90th percentile annual cash salary |

---

## 3. Operational Ingestion & Cross-Market Isolation

* **Strict Prohibition on Currency Pooling (`R-MD-07`):**
  US dollar salary figures are **never converted to INR via nominal foreign exchange rates** to augment Indian training datasets. Doing so conflates local purchasing power and compensation structures.
* **Permitted Analytical Role:**
  1. US Market Benchmark ($P_{10}, P_{50}, P_{90}$) for foreign expat and GCC comparison modules.
  2. Relative Structural Ratios: Evaluating the ratio of Senior-to-Junior roles or Data Science-to-Software Engineering wage spreads across global tech labor markets.

---

## 4. Freshness & Staleness Policy

* **Reference Month:** May 2023 (released November 2023).
* **Cadence:** Annual publication cycle.
* **Staleness Limits:** Valid for structural ratio benchmarking up to 24 months from reference date.
