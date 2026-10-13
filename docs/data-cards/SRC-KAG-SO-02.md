# Data Card: Stack Overflow Annual Developer Survey 2023

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-KAG-SO-02` |
| **Document ID** | `docs/data-cards/SRC-KAG-SO-02.md` |
| **Short Name** | Stack Overflow Survey 2023 |
| **Long Name** | Stack Overflow Annual Developer Survey 2023 (Official Public Release) |
| **Provider** | Stack Exchange Inc. / Stack Overflow |
| **Primary URL** | https://survey.stackoverflow.co/2023/ |
| **Repository URL** | https://github.com/StackExchange/Survey |
| **Licence** | Open Data Commons Open Database License (`ODbL-1.0`) |
| **SQS / Tier** | **72.2** / `TIER_3_MARKET_SIGNAL` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Approved Benchmark (Temporal Drift Analysis & Historical Stability Baselines) |
| **Prohibited Routing** | Direct PT1 ground-truth training (`R-EV-05`) |

---

## 1. Overview & Comparative Role

* **Role in Pipeline:** Pairs with `SRC-KAG-SO-01` (2024 Survey) to provide a multi-year longitudinal baseline.
* **Temporal Drift Tracking:** Enables evaluating year-over-year compensation shifts for specific technology skills (e.g. Generative AI, Rust, Go, Python) across comparable Indian experience cohorts before and after the 2023 tech market cooling.
* **Licensing:** ODbL 1.0. Verified legitimate open distribution.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-KAG-SO-02/` with verified SHA-256 manifest:

### File: `so_survey_2023_raw_sample.csv`
* Rows: 300 (representative cohort slice) | Columns: 84 | Duplicate rows: 0

Key Profiled Fields:
* `ResponseId`: Unique participant ID (1 to 89,184 in full release).
* `CompTotal`: Total annual compensation reported in local currency.
* `Country`: Country of residence (India $N \approx 5,200$ in full release).
* `YearsCodePro`: Years of professional coding experience.
* `LanguageHaveWorkedWith`: Tech stack programming languages.

---

## 3. Freshness & Staleness Policy

* **Survey Reference Window:** May 2023.
* **Staleness Classification:** Observations are $>12$ months old relative to 2024 and $>24$ months relative to current date.
* **Mandatory Deflation:** Under target contracts (`01-targets.md`), all 2023 financial figures must be indexed to prediction time $t_0$ using the monthly RBI CPI-Urban series (`SRC-SUP-MAC-01`).
