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

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile & Tech Peak Exuberance
1. **Macro Timing Bias:** Collected in May 2023, capturing compensation agreements finalized during the late-2022 to early-2023 post-pandemic hiring peak, prior to widespread tech layoffs and compensation moderation.
2. **Community Skew:** Same self-selection mechanism as the 2024 survey (`SRC-KAG-SO-01`): over-represents English-fluent, community-engaged, product-focused developers ($N_{\text{India}} \approx 5,200$).

### 4.2 Reporting & Measurement Bias Profile
1. **Self-Reported Total Pay:** Unbundled `CompTotal` reported with significant digit heaping at ₹10 LPA, ₹20 LPA, and ₹30 LPA intervals.
2. **Unrealized Paper Wealth:** Conflates paper ESOP valuations granted at 2021–2022 private startup peak valuations with guaranteed cash pay.

### 4.3 Comparison with Official Population Benchmarks
* **Comparison with MOSPI PLFS Benchmark (`SRC-IND-OFF-01`):** 2023 Indian developer median was **₹19.50 LPA**, representing a **+116.7% divergence** over the PLFS urban software developer median of ₹9.00 LPA.
* **Temporal Drift vs 2024 Survey (`SRC-KAG-SO-01`):** Median Indian nominal developer total comp declined from ₹19.50 LPA in 2023 to ₹18.00 LPA in 2024 (-7.7% nominal contraction), empirically documenting the tech market salary correction.
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * Blocked from direct PT1/PT2 training under Rule `R-DA-01` and `R-MD-07`.
  * Utilized strictly for multi-year temporal drift verification and stability auditing across feature curves.
