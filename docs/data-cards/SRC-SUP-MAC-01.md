# Data Card: RBI DBIE Macro Series (CPI-Urban & USD/INR Exchange Rates)

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-SUP-MAC-01` |
| **Document ID** | `docs/data-cards/SRC-SUP-MAC-01.md` |
| **Short Name** | RBI DBIE Macro Series |
| **Long Name** | Reserve Bank of India Database on Indian Economy Macroeconomic Time Series |
| **Provider** | Reserve Bank of India (RBI) / Federal Reserve Economic Data (FRED) |
| **Primary URL** | https://dbie.rbi.gov.in/ |
| **Licence** | Open Government Data License - India (`OGDL-IN`) |
| **SQS / Tier** | **94.4** / `TIER_4_SUPPLEMENTARY` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Supplementary Macro Series (Temporal Deflation & FX Reference) |
| **Prohibited Routing** | Direct PT1 ground-truth training |

---

## 1. Provenance, Governance & Methodological Mandate

* **Authority:** Reserve Bank of India (RBI) and Ministry of Statistics and Programme Implementation (MOSPI).
* **Mandate in ArthaIQ:**
  Governed by Target Contract (`01-targets.md`) and Normalization Contract (`02-comp-definitions.md`):
  Any salary observation older than **90 days** from prediction timestamp $t_0$ must be adjusted for inflation using the monthly Consumer Price Index (CPI-Urban):
  $$\text{Adjusted Pay} = \text{Reported Pay} \times \frac{\text{CPI}(t_0)}{\text{CPI}(t_{\text{reported}})}$$
  Observations older than **180 days** that fail temporal continuity checks are quarantined under Rule `R-DA-05`.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-SUP-MAC-01/` with verified SHA-256 manifest:

### 2.1 File: `cpi_urban_monthly.csv`
* Rows: 819 monthly observations (1957-01-01 to 2025-03-01) | Columns: 2 | Duplicate rows: 0

| Column | Type | Null % | Value Range | Description |
|:---|:---:|:---:|:---|:---|
| `observation_date` | String | 0.0% | `1957-01-01` to `2025-03-01` | First day of reporting month (YYYY-MM-01) |
| `INDCPIALLMINMEI` | Float64 | 0.0% | 1.47 to 159.20 | Consumer Price Index: All Items for India (Base 2012=100) |

* Latest values: January 2025 = 157.77, February 2025 = 157.33, March 2025 = 157.55.

### 2.2 File: `inr_usd_fx_daily.csv`
* Rows: 14,024 daily trading observations (1973-01-02 to 2026-10-02) | Columns: 2 | Duplicate rows: 0

| Column | Type | Null % | Value Range | Description |
|:---|:---:|:---:|:---|:---|
| `observation_date` | String | 0.0% | `1973-01-02` to `2026-10-02` | Trading day date (YYYY-MM-DD) |
| `DEXINUS` | Float64 | 3.9% (Market holidays) | ₹7.19 to ₹96.82 | Nominal INR per 1 USD spot exchange rate |

---

## 3. Missingness & Deflation Policy

* **Holiday Forward-Fill:** Trading holiday nulls (3.9% in daily FX series) are resolved via deterministic forward-fill (`pl.col("DEXINUS").forward_fill()`).
* **Monthly Deflator Lookup:** The deflation engine in `src/compintel/normalization/` uses month-keyed exact joins (`YYYY-MM`) against `cpi_urban_monthly.csv`.

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias & Macro Sampling Structure
1. **Official Macro Time Series:** Maintained jointly by the Reserve Bank of India (DBIE) and the Ministry of Statistics and Programme Implementation (MOSPI). Spot exchange rates reflect official FED / RBI daily interbank fixing rates.
2. **Zero Individual Selection Bias:** As macroeconomic index aggregates, these series contain zero individual survey participant or volunteer self-selection bias.

### 4.2 Index Choice & Measurement Bias Mitigation
1. **Urban vs Rural Index Divergence:** National general CPI (CPI-Combined) is heavily weighted by rural food and agricultural commodities (approx. 45% food weight), which exhibit high seasonal volatility that does not reflect technology worker living costs.
2. **ArthaIQ Index Calibration:** ArthaIQ deliberately isolates the **CPI-Urban** series (`INDCPIALLMINMEI`), which accurately mirrors the urban rent, utilities, and consumer goods basket experienced by technology professionals residing in Tier-1 and Tier-2 Indian metropolitan centers.

### 4.3 FX Misuse Warning (Rule `R-MD-08`)
* **Prohibition on Nominal Currency Conversion:** Spot exchange rate series (`DEXINUS`) is maintained strictly for international comparison dashboards and macro inflation monitoring.
* **Invariant:** Spot FX rates must **NEVER** be used to convert USD salaries directly into nominal INR training observations (`R-MD-08`). Doing so distorts local market clearing wages.
