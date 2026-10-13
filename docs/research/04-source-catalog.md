# Data Source Catalog: Official & Benchmark Labor Sources (T1.06)

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/04-source-catalog.md` |
| **Tasks** | T1.06 (Indian Official Sources), T1.08 (Kaggle Audit Integration) |
| **Status** | Active Catalog v0.1 |
| **Date** | 2026-10-13 |
| **Governs** | Source Quality Scoring (`05-source-scoring.md`), Source Ingestion Config (`config/sources.yaml`), Data Sufficiency (`experiments/preregistration/sufficiency-v1.yaml`) |
| **Methodological Invariant** | A scientifically valid national survey cannot be repurposed to estimate quantities it was never designed to measure. Official sources provide population-level anchors, not granular tech-sector ground truth. |

---

## 1. Executive Summary & Source Hierarchy

For **ArthaIQ's** core objective—estimating **annual guaranteed cash compensation (`guaranteed_cash_annual`)** for Indian technology professionals—identifying legitimate, legally accessible, and empirically sound data sources requires separating sources by their structural capabilities:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               ARTHAIQ DATA SOURCE TIERS                                │
│                                                                                        │
│  TIER 1: OFFICIAL POPULATION BENCHMARKS (T1.06)                                        │
│  • Periodic Labour Force Survey (PLFS) — MOSPI (Annual & Urban Microdata)              │
│  • Labour Bureau Occupational Wage Survey (OWS) & Wage Rate Index (WRI)                │
│  • National Career Service (NCS) Job Vacancies                                         │
│  Role: Macro wage anchors, statutory distribution floors, formal/informal baselines.   │
│                                                                                        │
│  TIER 2: GOVERNED VOLUNTARY DISCLOSURES (T2.10 / Phase 8 Design)                       │
│  • ArthaIQ Component-Level Voluntary Intake (Basic + HRA + Special Allowance)         │
│  • Redacted payslip verification, cryptographic deduplication, k-anonymity >= 5        │
│  Role: Granular ground truth for Product / GCC / IT Services compensation tiers.       │
│                                                                                        │
│  TIER 3: OPEN AUXILIARY BENCHMARKS & FIXTURES (T1.08 Audited)                          │
│  • Stack Overflow Annual Developer Survey (ODbL 1.0) — Experience & stack curvature    │
│  • ai-jobs.net Open Feeds (CC0) — International PPP spreads & remote premiums          │
│  • Naukri / Software Industry Scraped Fixtures — NLP parsing & regex unit tests        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Indian Official Labor-Market Sources (Task T1.06 Audit)

---

### Source Candidate 01: Periodic Labour Force Survey (PLFS) — Unit-Level Microdata

* **Provider & Primary URL:** Ministry of Statistics and Programme Implementation (MOSPI), Government of India.
  - [MOSPI National Data Archive (NADA) Catalog](https://microdata.gov.in/NADA/index.php/catalog/213)
  - Dataset Reference ID: `DDI-IND-CSO-PLFS-2023-24` (July 2023 – June 2024 Annual Release).
* **Retrieval / Verification Date:** 2026-10-13
* **Verification Status:** `VERIFIED`
* **Country & Scope:** India nationwide (Urban and Rural sectors across all 28 States and 8 Union Territories).
* **Occupational & Industrial Coverage:**
  - Standardized under **NCO-2015** (National Classification of Occupations) at 1, 2, 3, and 4-digit levels.
  - Key Tech Occupational Codes:
    - `NCO 2512`: Software Developers
    - `NCO 2511`: Systems Analysts
    - `NCO 2519`: Software and Applications Developers and Analysts Not Elsewhere Classified
    - `NCO 2521`: Database Designers and Administrators
    - `NCO 2522`: Systems Administrators
  - Standardized under **NIC-2008** (National Industrial Classification):
    - `NIC Division 62`: Computer programming, consultancy, and related activities
    - `NIC Division 63`: Information service activities (data processing, hosting, web portals)
* **Time Span & Update Cadence:**
  - Annual microdata releases covering July to June (latest: 2023–24).
  - Quarterly Bulletins for Urban Areas (tracking Current Weekly Status LFPR, WPR, UR).
* **Data Granularity & Schema Structure:**
  - Microdata unit records across hierarchical data files:
    - `hhrv` / `hhv1`: Household-level records (demographics, monthly per capita expenditure, social group).
    - `perrv` / `perv1`: Person-level records (age, education, general technical education, activity status, earnings).
  - Schedule: `Schedule 10.4`.
* **Available Compensation & Earnings Fields:**
  - `ern25` (Block 5.1/5.2 or Block 6, Item 9): Gross earnings received or receivable during the preceding calendar month for **Regular Wage / Salaried** employees (in nominal INR).
  - `ern_self` (Block 6, Item 10): Gross earnings during the last 30 days from self-employment.
  - `wage_act`: Daily earnings received for casual labor activities.
  - `subsample_mult`: Sub-sample multiplier (sampling weights) required to project sample records to national and state population totals.
* **Sample Size & Resolution:**
  - National Sample: ~101,000 households and ~415,000 persons surveyed annually.
  - Tech Occupational Subset: Nationwide, individuals reporting `NCO 2512` or `NIC 62` in urban sectors comprise approximately **1,800 to 2,400 sample observations**, distributed across ~30 states and multiple city tiers.
  - Geographic Resolution: State code, NSS Region, Sector (Rural/Urban), and Town Size Class (Class I cities: population $\ge 10$ lakhs, e.g., Bengaluru, Hyderabad, Pune, Mumbai, Delhi). Specific employer names are **strictly confidential and suppressed**.
* **Compensation Measure Alignment:**
  - Reports **gross monthly cash earnings** from primary salaried employment.
  - Annualized as: $\text{Annual Earnings} = ern25 \times 12$.
  - Captures pre-tax cash; **does not capture equity vesting (RSUs/ESOPs)** or detailed CTC line items.
* **Selection & Reporting Bias:**
  - Geographically and demographically representative of the Indian resident population.
  - **Severe Tech Upper-Tail Censoring:** High-earning tech employees in Tier-1 product firms earning ₹40–₹90 LPA are heavily underrepresented due to household survey sampling frames (gated communities, non-contact rates) and top-coding/under-reporting tendencies.
* **Licensing, Access & Cost:**
  - Open Government Data under the MOSPI Data Dissemination Policy. Available free of cost upon portal registration. Permitted for research, educational, and analytical modeling.
* **Integration Complexity:**
  - Moderate to High: Requires parsing fixed-width text files or CSVs using layout specifications (`Data_LayoutPLFS_2023-24.xlsx`) and applying survey multipliers (`multiplier / 100` or `1000`) for weighted quantile calculations.
* **Contribution to Prediction Targets:**
  - **PT1 (Market Compensation for Profile):** **MACRO ANCHOR / PRIOR FLOOR ONLY**. Informs the baseline empirical wage distribution for urban educated salaried professionals; establishes lower-bound priors ($P_{10}$); **CANNOT serve as direct training data for tech salary predictions**.
  - **PT2 (Comparable Cohort Range):** Informs general demographic returns to education (Technical Degree vs General Graduate).
  - **PT6 (Current Compensation Benchmark):** Enables macro population context (e.g. "Your guaranteed cash places you in the top 1.2% of urban salaried wage-earners in Karnataka").
  - **PT3, PT4, PT5:** Unsuitable.
* **Audit Classification:** 🏛️ **Population Benchmark / Macro Wage Anchor** (`APPROVED_AS_MACRO_ANCHOR`).

---

### Source Candidate 02: Labour Bureau Occupational Wage Survey (OWS)

* **Provider & Primary URL:** Labour Bureau, Ministry of Labour and Employment, Government of India.
  - [Labour Bureau Occupational Wage Survey Portal](https://www.labourbureau.gov.in/occupational-wage-survey)
* **Retrieval / Verification Date:** 2026-10-13
* **Verification Status:** `VERIFIED`
* **Country & Scope:** India; selected scheduled industries across Manufacturing, Mining, Plantations, and Service sectors.
* **Occupational & Industrial Coverage:**
  - Primary focus is on manual, operational, clerical, and lower supervisory occupations.
  - **Explicit Exclusion:** The survey explicitly excludes executive, managerial, and high-level technical/supervisory personnel from many industry schedules.
  - Does NOT publish dedicated occupation tables for Software Developers (`NCO 2512`) or modern cloud/AI engineers.
* **Time Span & Freshness:**
  - **Severe Staleness:** The Seventh Round of the Occupational Wage Survey was conducted with a reference date of **June 2016** (published 2018–2020). The Eighth Round remains under consideration / unpublished.
* **Available Fields:** Average daily wage rates, dearness allowances, minimum/maximum basic rates across scheduled factory occupations.
* **Compensation Measure Alignment:** Daily wage rates in factory/manual trades. Incompatible with annual technology CTC or fixed cash.
* **Selection & Reporting Bias:** Confined to scheduled non-managerial formal employment in traditional industries. Zero representation of post-2020 Indian software tech salary dynamics.
* **Licensing & Access:** Public domain government reports (PDF tables).
* **Contribution to Prediction Targets (PT1–PT6):**
  - **PT1–PT6:** **UNSUITABLE / DISQUALIFIED**. The observations are 8+ years old, omit technical engineering roles, and measure daily manual wages.
* **Audit Classification:** 🔴 **Unsuitable for Tech Compensation Modeling** (`DISQUALIFIED`).

---

### Source Candidate 03: Labour Bureau Quarterly Employment Survey (QES) / AQSE

* **Provider & Primary URL:** Labour Bureau, Ministry of Labour and Employment.
  - [All-India Quarterly Survey of Employment (AQSE)](https://www.labourbureau.gov.in/quarterly-employment-survey)
* **Retrieval / Verification Date:** 2026-10-13
* **Verification Status:** `VERIFIED`
* **Coverage:** Formal establishments employing 10 or more workers across 9 selected sectors, explicitly including **IT/BPO** (`NIC Division 62 & 63`).
* **Available Fields:** Total employment counts, male/female ratios, contract vs regular employee proportions. **Does not report individual wage microdata.**
* **Contribution to Prediction Targets:**
  - Serves as an auxiliary macroeconomic signal (`04-source-catalog.md`) tracking aggregate employment expansion and contraction in the IT/BPO sector.
* **Audit Classification:** 📊 **Supplementary Macro Signal** (`AUXILIARY_SIGNAL`).

---

### Source Candidate 04: National Career Service (NCS) Job Vacancy Portal

* **Provider & Primary URL:** Ministry of Labour and Employment, National Career Service.
  - [National Career Service Portal](https://www.ncs.gov.in/)
* **Retrieval / Verification Date:** 2026-10-13
* **Verification Status:** `VERIFIED`
* **Coverage:** Job vacancies advertised across public sector undertakings (PSUs), government contracts, and participating private employers in India.
* **Available Fields:** Job title, minimum qualification, posted wage / salary range (INR per month or annual), location, vacancy count.
* **Target Compatibility:** Measures **advertised hiring ranges** (PT3), not realized employee earnings.
* **Limitations:** Heavy concentration in government apprenticeships, clerical postings, IT support, and entry-level IT services; underrepresents competitive private tech product firms.
* **Contribution to Prediction Targets:**
  - Test fixture and benchmark for entry-level government/PSU IT vacancy salary ranges.
* **Audit Classification:** 🔵 **Supplementary Job Posting Signal** (`BENCHMARK_PT3_AUXILIARY`).

---

## 3. Kaggle Candidates Integrated Catalog (From Task T1.08)

The table below incorporates the 20 audited Kaggle datasets from `docs/research/kaggle-dataset-audit-v0.1.md`, completing our centralized source catalog:

| Catalog ID | Source Identifier / Dataset Slug | Provider / Upstream | Stated License | Real Legal Status | Record Count | India Tech Subset | Target Compatibility | Catalog Role |
|:---|:---|:---|:---|:---|:---:|:---:|:---|:---|
| `SRC-IND-OFF-01` | **MOSPI PLFS Microdata 2023–24** | MOSPI (Schedule 10.4) | Open Govt Data | Verified Open | 415,000 | ~2,200 | Gross Monthly Cash | 🏛️ **Macro Wage Anchor (Layer 1)** |
| `SRC-IND-OFF-02` | **Labour Bureau OWS 7th Round** | Ministry of Labour | Govt Public | Verified (Stale) | N/A | 0 | Daily Wage Rate | 🔴 **Disqualified (Stale/Manual)** |
| `SRC-IND-OFF-03` | **Labour Bureau QES IT/BPO** | Ministry of Labour | Govt Public | Verified | Establishments | Aggregate | Headcount Counts | 📊 **Macro Signal (Employment)** |
| `SRC-IND-OFF-04` | **NCS Job Vacancies** | Ministry of Labour | Public Portal | Verified | Vacancies | Entry/Govt | Advertised Range | 🔵 **Supplementary PT3 Signal** |
| `SRC-KAG-SO-01` | `stack-overflow-developer-survey-2024` | Stack Overflow Official | ODbL 1.0 | Verified Legitimate | 65,000+ | ~4,500 | Total Comp (`CompTotal`) | 🟡 **Approved Benchmark (Stack Curves)** |
| `SRC-KAG-SO-02` | `stack-overflow-developer-survey-2023` | Stack Overflow Official | ODbL 1.0 | Verified Legitimate | 89,184 | ~5,200 | Total Comp (`CompTotal`) | 🟡 **Approved Benchmark (Temporal Drift)** |
| `SRC-KAG-AIJ-01` | `data-science-salaries-2023` (ai-jobs) | ai-jobs.net | CC0 Public Domain | Verified Open | 3,755 | ~200 | Gross USD Cash | 🟡 **Approved Benchmark (Global PPP)** |
| `SRC-KAG-AIJ-02` | `jobs-in-data` (JobsInData 2024) | ai-jobs.net / JID | CC0 Public Domain | Verified Open | 14,000+ | ~600 | Gross USD Cash | 🟡 **Approved Benchmark (Feature Ablation)** |
| `SRC-KAG-FIX-01` | `jobs-on-naukricom` | Scraped Naukri Postings | CC0 (Claimed) | Scraped Mirror | 30,000 | 30,000 | Advertised Range | 🔵 **Test-Fixture Only (NLP/Taxonomy)** |
| `SRC-KAG-FIX-02` | `software-industry-salary-dataset-2022` | Scraped Glassdoor/Ambition | CC0 (Claimed) | Scraped Mirror | 22,770 | ~22,000 | Aggregated CTC | 🔵 **Test-Fixture Only (Regex Parsing)** |
| `SRC-KAG-FIX-03` | `india-job-market-and-salary-trends-2026` | Multi-portal Scrape | Unknown | Unverified Scrape | 5,000 | 5,000 | Advertised Min/Max | 🔵 **Test-Fixture Only (Range Parser)** |
| `SRC-KAG-REJ-01` | `jackogozaly/data-science-stem-salaries` | Scraped Levels.fyi | CC0 (Claimed) | Direct ToS Breach | 62,642 | ~1,800 | Base / Stock / Bonus | 🔴 **Rejected (Legal Risk / ToS)** |
| `SRC-KAG-REJ-02` | `whenamancodes/data-science-jobs-india` | Scraped AmbitionBox | Apache 2.0 (Claimed) | Direct ToS Breach | 1,600 | 1,600 | Advertised LPA | 🔴 **Rejected (Unauthorized Scrape)** |
| `SRC-KAG-REJ-03` | `data-science-salary-predictor` | Synthetic Generator | Public | Fabricated | 1,000 | 0 | Continuous Mock | 🔴 **Rejected (Rule R-MD-11)** |

---

## 4. Operational Ingestion Guidelines for Approved Sources

### 4.1 Ingestion Contract for `SRC-IND-OFF-01` (MOSPI PLFS Microdata)
1. **Extraction Pipeline:**
   - Filter `perrv` / `perv1` records where `activity_status_code` indicates regular salaried employment (`status IN (31, 71, 72)`).
   - Filter for `sector == 'URBAN'` and `general_education_level >= Graduate`.
   - Identify tech cohort via `nco_code_2015 LIKE '2512%'` (Software Developers) or `nic_code_2008 LIKE '62%'`.
2. **Weighting Policy:**
   - Every empirical quantile ($P_{10}, P_{50}, P_{90}$) and weighted mean must apply the official sampling weight:
     $$w_i = \frac{\text{subsample\_mult}_i}{100.0}$$
   - Never compute unweighted summary statistics on PLFS microdata.
3. **Target Isolation Rule:**
   - PLFS wage outputs are routed strictly to:
     - Prior distributions for Bayesian/regularized baselines ($\mu_{\text{floor}}, \sigma_{\text{floor}}$).
     - Macro population percentile anchors in PT6.
   - **Never concatenate PLFS records directly into the primary PT1 training dataset** without a distinct source indicator and domain-adaptation regularizer.

### 4.2 Ingestion Contract for `SRC-KAG-SO-01` (Stack Overflow Survey 2024)
1. **Filtering:**
   - Filter `Country == 'India'` AND `Currency == 'INR'` AND `CompFreq == 'Yearly'`.
   - Remove outliers: $\text{CompTotal} < ₹1.0\ \text{LPA}$ or $\text{CompTotal} > ₹200.0\ \text{LPA}$.
2. **Target Isolation Rule:**
   - Map `CompTotal` strictly to `measure_id: total_comp_annual`.
   - Use strictly to fit non-linear returns to experience:
     $$\log(\text{CompTotal}) = \alpha + \beta_1 \cdot \text{YOE} + \beta_2 \cdot \text{YOE}^2 + \sum_k \gamma_k \cdot \text{Skill}_k$$
   - Relative ratios $\beta_1, \beta_2, \gamma_k$ are exported as priors; raw intercept $\alpha$ is discarded.

---

## 5. Next Actions

1. Ingest catalog IDs into `config/sources.yaml` with explicit status tags (`macro_anchor`, `benchmark_only`, `test_fixture_only`, `rejected`).
2. Update `docs/research/evidence-register.csv` with the empirical findings on PLFS sampling density and Labour Bureau OWS staleness.
3. Advance to **Task T1.03** (User persona hypotheses, jobs to be done, and interview recruiting guide).

---

*Authored for ArthaIQ under Phase 1, Task T1.06.*
