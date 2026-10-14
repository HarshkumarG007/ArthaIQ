# Data Card: MOSPI Periodic Labour Force Survey (PLFS) 2023–24 Microdata

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-IND-OFF-01` |
| **Document ID** | `docs/data-cards/SRC-IND-OFF-01.md` |
| **Short Name** | MOSPI PLFS 2023–24 |
| **Long Name** | Ministry of Statistics and Programme Implementation Periodic Labour Force Survey (July 2023 – June 2024) |
| **Provider** | MOSPI, National Data Archive (NADA), Government of India |
| **Primary URL** | https://microdata.gov.in/NADA/index.php/catalog/213 |
| **Licence** | Open Government Data License (India) (`OGL-India-1.0`) |
| **SQS / Tier** | **82.6** / `TIER_2_POPULATION_BENCHMARK` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Macro Wage Anchor / Prior Floor ($\mu_{\text{floor}}$); PT6 Population Percentile Context |
| **Prohibited Routing** | Direct PT1 / PT2 training data (Rule `D-010`, `R-DA-01`) |

---

## 1. Source Provenance & Legal Review

* **Collection Authority:** National Statistical Office (NSO), MOSPI, Government of India.
* **Legal Terms:** Disseminated under the National Data Sharing and Accessibility Policy (NDSAP). Free public research and analytical reuse permitted with attribution.
* **Personal Data & Privacy:** Anonymized unit records. Household locations resolved to NSS Regions and Town Size Classes (Class I cities $\ge 10$ lakhs). Specific employer names and individual resident identities are suppressed. Fully compliant with DPDPA 2023.
* **ToS Risk:** Zero. Direct official portal distribution.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-IND-OFF-01/` with verified SHA-256 manifest:

### 2.1 File: `plfs_2023_24_layout_sched_10_4.csv`
Defines the Schedule 10.4 unit record layout specification for person records (`perrv` / `perv1`):

| Variable Name | Block / Item | Type | Null % | Description |
|:---|:---|:---:|:---:|:---|
| `fsu_serial` | Block 1, Item 1 | String | 0.0% | First Stage Unit sampling frame serial number |
| `sector` | Block 4, Item 1 | Int64 | 0.0% | Sector code (`1` = Rural, `2` = Urban) |
| `general_education` | Block 5, Item 8 | Int64 | 0.0% | Educational level (`08` = Graduate, `10` = Postgraduate+) |
| `technical_education` | Block 5, Item 9 | Int64 | 0.0% | Technical training (`03` = Degree in Engg/Technology) |
| `activity_status` | Block 5.1, Item 3 | Int64 | 0.0% | Current Weekly Activity (`31` = Regular Salaried Employee) |
| `nic_2008_2digit` | Block 5.1, Item 5 | Int64 | 0.0% | Industry Division (`62` = Computer Programming/Consulting) |
| `nco_2015_4digit` | Block 5.1, Item 6 | Int64 | 0.0% | Occupation code (`2512` = Software Developers) |
| `ern25` | Block 5.1, Item 9 | Int64 | 0.0% | Gross monthly cash earnings from salaried work (INR) |
| `subsample_mult` | Block 6, Item 10 | Float64 | 0.0% | Sampling weight multiplier ($w_i = \text{mult} / 100.0$) |

### 2.2 File: `plfs_urban_tech_macro_anchors.csv`
Empirical weighted quantile earnings benchmarks for urban technology degree holders:

| NCO Code | Role Title | Weighted $N$ | Monthly $P_{10}$ | Monthly $P_{50}$ | Monthly $P_{90}$ | Annual Cash $P_{10}$ | Annual Cash $P_{50}$ | Annual Cash $P_{90}$ |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `2512` | Software Developers | 2,240 | ₹25,000 | ₹75,000 | ₹2,40,000 | ₹3.00 LPA | ₹9.00 LPA | ₹28.80 LPA |
| `2511` | Systems Analysts | 890 | ₹28,000 | ₹82,000 | ₹2,60,000 | ₹3.36 LPA | ₹9.84 LPA | ₹31.20 LPA |
| `2521` | Database Designers | 650 | ₹22,000 | ₹68,000 | ₹2,10,000 | ₹2.64 LPA | ₹8.16 LPA | ₹25.20 LPA |
| `2519` | App Developers NEC | 1,120 | ₹20,000 | ₹65,000 | ₹2,05,000 | ₹2.40 LPA | ₹7.80 LPA | ₹24.60 LPA |

---

## 3. Coverage, Sampling Frame & Observation Unit

* **Observation Unit:** Individual resident wage-earning employee aged 18–65.
* **Geographical Coverage:** Nationwide India across all 28 States and 8 Union Territories.
* **Sampling Frame:** Stratified multistage probability sample of census enumeration blocks (urban) and villages (rural).
* **Tech Sector Subsample:** Urban salaried workers reporting `NIC 62` or `NCO 2512` constitute $\sim 2,240$ observations across tier-1, tier-2, and tier-3 cities.
* **Target Compensation Alignment:** Measures **gross monthly cash earnings** (`ern25`). Clean cash measure; completely excludes equity grants (RSUs/ESOPs) and variable employer bonus pools.

---

## 4. Selection & Reporting Bias Assessment

### 4.1 Selection Bias Profile & Sampling Frame Limits
1. **Sampling Frame Authority:** Administered by the National Statistical Office (NSO) via stratified two-stage sampling (FSU: Urban Frame Survey blocks; SSU: households). Covers 100% of Indian states and UTs.
2. **Upper-Tail Truncation:** Household sampling frames systematically under-sample affluent high-earning households in secure gated communities and high-rise apartment complexes in Bengaluru, Hyderabad, Gurugram, and Pune. Tech professionals earning $> ₹40$ LPA (especially Tier-1 product engineers with substantial equity compensation) have disproportionately low inclusion probabilities.
3. **Employer Type Representation:** Strongly represents domestic IT services vendors, regional software consultancies, public sector units, and mid-sized agencies. Global Capability Centers (GCCs) and US tech multinationals (e.g., Google, Amazon, Microsoft) are under-represented.

### 4.2 Reporting & Measurement Bias Profile
1. **Cash Accounting Fidelity:** Measures contractual gross monthly cash wages (`ern25`). Completely excludes employer statutory overhead (EPF 12%, Gratuity 4.81%), annual performance bonus pools, and stock grants (RSUs/ESOPs).
2. **Tax Avoidance Under-Reporting:** Survey responses exhibit a documented downward reporting bias (5%–15%) due to respondent apprehension regarding tax scrutiny and privacy disclosures.
3. **Recall Errors:** Reported as monthly cash earnings for the preceding 30-day reference period; subject to minor recall variance rather than payroll ledger extraction.

### 4.3 Official Population Benchmark Anchoring
* **Benchmark Status:** Serves as ArthaIQ's **primary Indian official population benchmark** for urban technology employment.
* **Empirical Population Anchors (NCO 2512 Software Developers):**
  * Weighted Median ($P_{50}$): **₹9.00 LPA** (₹75,000/month).
  * 10th Percentile ($P_{10}$): **₹3.00 LPA** (₹25,000/month).
  * 90th Percentile ($P_{90}$): **₹28.80 LPA** (₹2,40,000/month).
* **Mitigation & Pipeline Routing Rule in ArthaIQ:**
  * Strictly segregated from direct `PT1` / `PT2` training sets (Rule `R-DA-01`, `D-010`).
  * Admitted exclusively as an empirical **lower-bound prior floor** ($\mu_{\text{floor}} = ₹3.00$ LPA) and national percentile reference (`PT6`), preventing models from predicting implausibly low salaries for qualified tech professionals while avoiding downward bias on top-tier compensation bands.

---

## 5. Freshness & Staleness Policy

* **Reference Period:** July 2023 to June 2024.
* **Release Cadence:** Annual microdata release.
* **Deflation Rule:** Observations deflated using monthly CPI-Urban (`SRC-SUP-MAC-01`) from reference midpoint (December 2023) to prediction timestamp $t_0$.
* **Staleness Limits:** Valid for macro anchor priors up to 36 months from survey reference date.

---

## 6. Sufficiency Audit against `sufficiency-v1.yaml`

| Pre-Registered Criterion | Threshold | Source Status | Audit Verdict |
|:---|:---|:---:|:---:|
| **C1** — Effective sample size | $N_{\text{eff}} \ge 50$ per core cell | National tech $N \approx 2,240$ | ✅ PASS (Macro cohort) |
| **C2** — Source quality floor | $\text{SQS} \ge 65$, Hard Gates $\ge 3$ | $\text{SQS} = 82.6$, Gates 5/3/5 | ✅ PASS |
| **C3** — Temporal recency | Window $\le 180$ days / Deflated | Reference 2023–24, deflated | ✅ PASS (With CPI deflator) |
| **C4** — Cell coverage | 100% core occupation families | SWE, Systems, DB covered | ✅ PASS |
| **PG** — Privacy Gate | $k \ge 5$, zero direct PII | Fully anonymized microdata | ✅ PASS |
