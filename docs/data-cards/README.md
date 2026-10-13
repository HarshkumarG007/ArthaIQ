# ArthaIQ Data Cards Catalog & Profiling Register (Task T2.04)

| Field | Value |
|:---|:---|
| **Directory** | `docs/data-cards/` |
| **Task** | T2.04 — Profile Each Source & Author Data Cards |
| **Governing Documents** | `PRD.md` (NFR-12), `architecture.md` (§9), `rules.md` (R-DA-01 to R-DA-10), `experiments/preregistration/sufficiency-v1.yaml` |
| **Last Updated** | 2026-10-14 |
| **Status** | Complete (14 Data Cards Authored & Polars Profiling Verified) |

---

## 1. Executive Summary & Master Profiling Matrix

Under Task **T2.04**, every acquired dataset in `data/raw/` has been systematically profiled using Polars for row counts, column types, missingness percentages, duplicate rates, value bounds, and staleness limits. Each source is documented in a dedicated Data Card specifying its legal authority, schema, target compatibility, and bias profile:

| Data Card | Source Name | Role in Pipeline | SQS | Status | Profiled Files & Dimensions | Staleness Limit |
|:---|:---|:---|:---:|:---:|:---|:---:|
| [SRC-IND-OFF-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-IND-OFF-01.md) | MOSPI PLFS 2023–24 Microdata | Macro Wage Anchor / Prior Floor ($\mu_{\text{floor}}$) | 82.6 | Approved | Layout (9 cols) & Tech Anchors (4 rows, 13 cols) | 36 months |
| [SRC-IND-OFF-03.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-IND-OFF-03.md) | Labour Bureau QES IT/BPO | Auxiliary Macro Signal (Headcount & Contract %) | 59.2 | Approved | 3 quarterly rounds, 8 cols, 0% nulls | 24 months |
| [SRC-USA-BLS-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-USA-BLS-01.md) | US BLS OEWS May 2023 | US Cross-Market Benchmark & Relative Ratios | 78.2 | Approved | 7 MSA rows, 11 percentile cols, 0% nulls | 24 months |
| [SRC-USA-DOL-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-USA-DOL-01.md) | US DOL OFLC H-1B LCA FY24 | US Certified Base Wage Regulatory Signal | 74.4 | Approved | 8 certified tech petitions, 11 cols | 12 months |
| [SRC-USA-DOL-02.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-USA-DOL-02.md) | US DOL OFLC PERM FY24 | US Returns to Tenure & Minimum Degree Demanded | 74.4 | Approved | 5 certified petitions, 10 cols with $YOE$ | 12 months |
| [SRC-KAG-SO-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-KAG-SO-01.md) | Stack Overflow Survey 2024 | Non-linear Returns to $YOE$ & Tech Stack Priors | 72.2 | Approved | 300 India cohort rows, 114 survey cols | 180 days (Deflated) |
| [SRC-KAG-SO-02.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-KAG-SO-02.md) | Stack Overflow Survey 2023 | Temporal Drift Baseline & Historical Stability | 72.2 | Approved | 300 cohort rows, 84 survey cols | 180 days (Deflated) |
| [SRC-KAG-AIJ-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-KAG-AIJ-01.md) | ai-jobs.net DS Salaries 2023 | Global Purchasing-Power Parity Baselines | 60.2 | Approved | 10 sample rows, 11 cols, 0% nulls | 180 days (Deflated) |
| [SRC-KAG-AIJ-02.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-KAG-AIJ-02.md) | JobsInData 2024 / ai-jobs | Remote Work Premiums & Feature Exploration | 60.8 | Approved | 6 sample rows, 12 cols, 0% nulls | 180 days (Deflated) |
| [SRC-SUP-TAX-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-SUP-TAX-01.md) | O*NET 29.0 Content Model | Canonical Skill Resolution & SOC Crosswalks | 84.4 | Approved | Tech Skills (13 rows) & Occ Data (6 rows) | 36 months |
| [SRC-SUP-TAX-02.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-SUP-TAX-02.md) | ESCO Skills Taxonomy v1.1 | Skill Hierarchy Graph & Distance Regularization | 79.8 | Approved | 7 tech hierarchy nodes, 5 cols | 36 months |
| [SRC-SUP-MAC-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-SUP-MAC-01.md) | RBI DBIE Macro Series | Temporal Deflator (CPI-Urban) & Spot FX | 94.4 | Approved | CPI (819 mos) & FX (14,024 days) | Monthly rolling |
| [SRC-SUP-CORP-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-SUP-CORP-01.md) | BSE/NSE Listed IT Corporate Filings | IT Services Enterprise Median Priors (Sec 197) | 83.8 | Approved | 8 major listed firms, 8 audited cols | Annual FY |
| [SRC-INT-VOL-01.md](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/data-cards/SRC-INT-VOL-01.md) | ArthaIQ Governed Voluntary Intake | Primary Ground Truth Training Data (Phase 8 Design) | 96.0 | Approved (Design) | Itemized form & cryptographic salt hash | Rolling live |

---

## 2. Universal Data Quality & Staleness Policies

1. **Rule R-DA-01 (Licence Gate):** Zero unapproved or scraped datasets are admitted to any training pipeline.
2. **Rule R-DA-04 (Original Values Preserved):** All raw currencies, reporting periods, and nominal amounts are preserved alongside normalized attributes.
3. **Rule R-DA-05 (Zero Silent Dropping):** Any malformed, missing, or out-of-range observations are routed to the quarantine zone with an explicit reason code.
4. **CPI Deflation Trigger:** Any observation older than 90 days from prediction timestamp $t_0$ must be indexed via `SRC-SUP-MAC-01`. Observations exceeding 180 days without continuous representation are quarantined.
