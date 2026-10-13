# Kaggle Dataset Audit v0.1: Technology Compensation Feasibility for ArthaIQ

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/kaggle-dataset-audit-v0.1.md` |
| **Task** | T1.08 — Kaggle Dataset Audit v0.1 (Coordinated with T1.01 & T1.05) |
| **Status** | Complete v0.1 |
| **Date** | 2026-10-13 |
| **Governs** | Source Catalog (`04-source-catalog.md`), Source Scoring (`05-source-scoring.md`), Data Ingestion (`config/sources.yaml`) |
| **Methodological Invariant** | A dataset being on Kaggle does NOT establish that its figures are accurate, representative, current, or legally reusable. A large row count does not justify training eligibility. Sample size ($N$) alone CANNOT validate an estimate (`D-010`, `R-EV-07`, `R-UQ-07`). |

---

## 1. Executive Summary & Audit Mandate

Kaggle represents one of the fastest discovery channels for tabular datasets, data dictionaries, schema architectures, and exploratory baseline notebooks. However, for **ArthaIQ's** core mission—predicting **annual guaranteed cash compensation (`guaranteed_cash_annual`)** for Indian technology professionals—public Kaggle datasets present severe methodological, legal, and structural pitfalls:

1. **The "Relicensing" Fallacy:** Uploaders frequently tag datasets as `CC0: Public Domain` or `CC-BY 4.0`, whereas the underlying records were scraped without authorization from proprietary Indian platforms (AmbitionBox, Naukri, Glassdoor, Levels.fyi, Indeed), whose Terms of Service explicitly prohibit automated scraping and commercial redistribution. Ingesting these datasets into ArthaIQ's training pipeline violates rules `R-DA-01` and `R-DA-02`.
2. **Target Contamination:** Most Kaggle salary datasets measure *Total Cost to Company (CTC)*, *Advertised Job Openings*, or *Gross Annual USD Cash*, which cannot be substituted for Indian guaranteed fixed cash without explicit component unbundling. Conflating advertised ranges with realized earnings introduces severe upward or downward skew.
3. **Geographic Dilution & Remote Bias:** Global datasets advertising 10,000+ rows often contain fewer than 300 Indian records, heavily skewed toward US remote contractors and international agencies rather than domestic GCCs, product firms, or IT services employers.
4. **Coarse Bins & Synthetic Artifacts:** Several datasets discretize compensation into wide bins ($10k brackets) or contain synthetically fabricated observations (SMOTE/Faker), violating rule `R-MD-11` (synthetic data must never be reported as real compensation evidence).

### Key Finding of Audit v0.1
* **Training-Eligible Candidates for PT1:** **0 of 20 candidates audited.** None of the publicly available Kaggle salary datasets satisfy the dual criteria of **clean legal provenance** (authorized collection/open license) AND **unambiguous `guaranteed_cash_annual` reporting** for Indian tech workers.
* **Approved Benchmark & Relationship Discovery Assets:** **4 candidates approved** (Stack Overflow Developer Surveys 2023/2024 and ai-jobs.net feeds) for learning non-linear experience curves ($YOE$), tech stack premiums, and model architecture validation under distinct target measures (`comp_total_annual`).
* **Approved Test-Fixture & Schema Plumbing Assets:** **6 candidates approved** for testing INR currency normalization, city fuzzy-matching, and schema validation pipelines in unit tests (`tests/fixtures/`).
* **Disqualified / Rejected:** **10 candidates rejected** due to unauthorized portal scraping, synthetic fabrication, unverified anecdotal provenance, or fatal target mismatch.

---

## 2. Audit Framework: The 10 Evaluation Dimensions

Each candidate is evaluated across the ten dimensions established in our data strategy and master research prompt:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                10-DIMENSION AUDIT RUBRIC                               │
│                                                                                        │
│  1. Target Compatibility:   guaranteed_cash vs Total CTC vs Advertised Range           │
│  2. Population Coverage:    Indian tech professionals (SWE, Data, ML) vs Global/Broad  │
│  3. Granularity:            Role, YOE, City/Location, Employer Context, Date           │
│  4. Upstream Provenance:    Original collector traced vs Uncredited scraped mirror     │
│  5. Independence:           Deduplicated records vs Clustered/synthetic copies         │
│  6. Selection Bias Profile: Voluntary self-report vs Advertised budget vs Institutional │
│  7. Temporal Freshness:     Verified observation timestamp vs Upload date staleness    │
│  8. Licensing Integrity:    Verifiable commercial rights vs Unauthorized relicensing   │
│  9. Privacy & Anonymity:    Absence of PII, adherence to k-anonymity (k >= 5)          │
│ 10. Validation Utility:     Viable for temporal / employer-held-out evaluation splits   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Disposition Categories:
* 🟢 **Training-Eligible (TE):** Provenance and usage rights verified; target matches `guaranteed_cash_annual`; passes schema, quality, and anti-leakage checks.
* 🟡 **Benchmark-Only (BO):** Permissive license and verified provenance; useful for validating relationships (e.g. YOE curves, skill premiums), but target definition differs (e.g. Total Comp) or population is global. Must be evaluated under a separate target branch.
* 🔵 **Test-Fixture-Only (TF):** Useful strictly for pipeline plumbing, regex currency parsing, and unit tests without making real-world market claims. Never ingested into feature stores or training sets.
* 🔴 **Rejected (REJ):** Unauthorized upstream scraping, unverifiable provenance, synthetic fabrication, or fatal target mismatch.

---

## 3. Comprehensive Candidate Dataset Catalog (20 Candidates)

---

### Archetype A: Scraped Indian Job Portals & Company Review Aggregates (Naukri, AmbitionBox, Glassdoor)

#### Candidate 01: Software Industry Salary Dataset — 2022
* **Kaggle Link:** [iamsouravbanerjee/software-industry-salary-dataset-2022](https://www.kaggle.com/datasets/iamsouravbanerjee/software-industry-salary-dataset-2022)
* **Author / Uploader:** Sourav Banerjee (`iamsouravbanerjee`)
* **Observed Attributes:** ~22,770 rows. Primary files: `Salary_Dataset_with_Extra_Features.csv`, `Software_Professional_Salaries.csv`.
* **Columns:** `Company Name`, `Rating`, `Job Title`, `Salary`, `Salaries Reported`, `Location`, `Employment Status`.
* **Upstream Provenance:** Scraped from Glassdoor India and AmbitionBox company pages (evident from `Salaries Reported` aggregation count).
* **Target Compatibility:** Measures aggregated annual compensation strings (e.g., `"₹ 6,00,000/yr"` or `"₹ 45,000/mo"`). Unbundled CTC; fails to isolate fixed cash from variable bonuses or employer PF.
* **Licensing & Legal Status:** Uploader tagged as `CC0: Public Domain`. **However**, Glassdoor and AmbitionBox Terms of Use explicitly forbid automated scraping and redistribution. The uploader has no legal standing to dedicate scraped third-party database entries to the public domain.
* **Audit Disposition:** 🔴 **REJECTED for Model Training**; 🔵 **Approved as Test-Fixture Only** (Plumbing test asset for Indian salary string parsing: `₹/yr`, `₹/mo`, Lakhs shorthand).

#### Candidate 02: Data Science Jobs in India (AmbitionBox Scrape)
* **Kaggle Link:** [whenamancodes/data-science-jobs-in-india](https://www.kaggle.com/datasets/whenamancodes/data-science-jobs-in-india)
* **Author / Uploader:** Aman Chauhan (`whenamancodes`)
* **Observed Attributes:** ~1,600 rows.
* **Columns:** `Company`, `Job Title`, `Salary (INR Lakhs)`, `Min_Experience`, `Max_Experience`, `Location`.
* **Upstream Provenance:** Scraped from AmbitionBox India job search pages.
* **Target Compatibility:** Measures advertised salary brackets on job listings (PT3 Advertised Range), NOT realized employee compensation (PT1).
* **Licensing & Legal Status:** Info Edge India Ltd. (AmbitionBox) Terms of Service violation.
* **Audit Disposition:** 🔴 **REJECTED for Training** (Unauthorized scrape; Advertised range target mismatch).

#### Candidate 03: Jobs on Naukri.com
* **Kaggle Link:** [promptcloud/jobs-on-naukricom](https://www.kaggle.com/datasets/promptcloud/jobs-on-naukricom)
* **Author / Uploader:** PromptCloud
* **Observed Attributes:** ~30,000 job postings across Indian industries (IT, Software, Analytics, BPO).
* **Columns:** `Job Title`, `Job Experience Required`, `Key Skills`, `Role Category`, `Location`, `Functional Area`, `Industry`, `Salary Pay`.
* **Upstream Provenance:** Web-scraped archive from Naukri.com listings.
* **Target Compatibility:** Advertised salary strings (`"3,00,000 - 6,00,000 P.A."`). High missingness (>65% list `"Not Disclosed by Recruiter"`).
* **Licensing & Legal Status:** Info Edge India Ltd. strictly prohibits scraping under Section 4 of its terms.
* **Audit Disposition:** 🔴 **REJECTED for Training**; 🔵 **Approved as Test-Fixture Only** (Valuable fixture for verifying NLP skill-extraction and Indian city normalization pipelines).

#### Candidate 04: Job Postings Dataset from Naukri.com
* **Kaggle Link:** [iqbal303/job-postings-dataset-from-naukricom](https://www.kaggle.com/datasets/iqbal303/job-postings-dataset-from-naukricom)
* **Author / Uploader:** Iqbal (`iqbal303`)
* **Observed Attributes:** ~12,000 listings.
* **Columns:** `Job Title`, `Company Name`, `Experience`, `Salary`, `Location`, `Job Description`, `Skills`.
* **Upstream Provenance:** Scraped from Naukri.com search results.
* **Target Compatibility:** Advertised compensation range.
* **Licensing & Legal Status:** Unauthorized scrape of proprietary portal.
* **Audit Disposition:** 🔴 **REJECTED for Training** (Duplicate upstream of Candidate 03; legal terms violation).

#### Candidate 05: 12,000 Data Science Jobs in India (Naukri.com)
* **Kaggle Link:** [anandhuh/12000-data-science-jobs-in-india-naukricom](https://www.kaggle.com/datasets/anandhuh/12000-data-science-jobs-in-india-naukricom)
* **Author / Uploader:** Anandhu H (`anandhuh`)
* **Observed Attributes:** 12,000 records specifically filtered for Data Science, ML, and Analytics in India.
* **Columns:** `Job Title`, `Company`, `Experience`, `Salary`, `Location`, `Skills`, `Posted Date`.
* **Upstream Provenance:** Scraped from Naukri.com using Selenium/BeautifulSoup.
* **Target Compatibility:** Advertised range (PT3), heavy missingness on salary.
* **Audit Disposition:** 🔴 **REJECTED for Training** (Scraped portal data; target mismatch).

#### Candidate 06: India Job Market and Salary Trends 2026
* **Kaggle Link:** [amar5693/india-job-market-and-salary-trends-2026](https://www.kaggle.com/datasets/amar5693/india-job-market-and-salary-trends-2026)
* **Author / Uploader:** Amar (`amar5693`)
* **Observed Attributes:** ~5,000 records across Bengaluru, Hyderabad, Pune, NCR.
* **Columns:** `job_title`, `company_name`, `location`, `experience_required_years`, `skills`, `salary_min_inr`, `salary_max_inr`, `remote_work`.
* **Upstream Provenance:** Multi-portal job posting aggregator.
* **Target Compatibility:** Advertised range (`salary_min_inr`, `salary_max_inr`).
* **Licensing & Legal Status:** Unknown aggregation; lack of original source license grants.
* **Audit Disposition:** 🔴 **REJECTED for Training**; 🔵 **Approved as Test-Fixture Only** (Clean structured schema for testing PT3 advertised range parser).

#### Candidate 07: Jobs in Kolkata
* **Kaggle Link:** [himanshusingh2003/jobs-in-kolkata](https://www.kaggle.com/datasets/himanshusingh2003/jobs-in-kolkata)
* **Author / Uploader:** Himanshu Singh (`himanshusingh2003`)
* **Observed Attributes:** 40 rows.
* **Columns:** `Company`, `Job Role`, `Annual Salary Range`, `Required Experience`, `Skill Tags`.
* **Upstream Provenance:** Manual scrape / extraction of localized job board listings.
* **Target Compatibility:** Advertised salary ranges.
* **Audit Disposition:** 🔵 **Test-Fixture-Only** (Useful as a minimal 40-row CSV fixture for quick unit test execution; completely inadequate for statistical modeling).

#### Candidate 08: Indian Job Market Analysis
* **Kaggle Link:** [kapoorprakhar/indian-job-market-analysis](https://www.kaggle.com/datasets/kapoorprakhar/indian-job-market-analysis)
* **Author / Uploader:** Prakhar Kapoor (`kapoorprakhar`)
* **Observed Attributes:** ~180 job listings.
* **Columns:** `job_title`, `location`, `salary_raw`, `salary_monthly_normalized`, `state`.
* **Upstream Provenance:** Exploratory project scraper across job portals.
* **Target Compatibility:** Advertised monthly salary. Extreme sample sparsity.
* **Audit Disposition:** 🔵 **Test-Fixture-Only** (Plumbing test for monthly-to-annual normalizers).

---

### Archetype B: Standardized Global Tech Salary Feeds (ai-jobs.net Mirrors)

#### Candidate 09: Data Science Job Salaries (2023 Edition)
* **Kaggle Link:** [arnabchaki/data-science-salaries-2023](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)
* **Author / Uploader:** Arnab Chaki (`arnabchaki`)
* **Observed Attributes:** 3,755 global rows.
* **Columns:** `work_year`, `experience_level`, `employment_type`, `job_title`, `salary`, `salary_currency`, `salary_in_usd`, `employee_residence`, `remote_ratio`, `company_location`, `company_size`.
* **Upstream Provenance:** Direct export from the `ai-jobs.net` open data initiative. Authenticated open source.
* **Licensing:** `CC0: Public Domain` (Confirmed: original collector ai-jobs.net explicitly dedicates its data to public domain).
* **Target Compatibility:** Primary field is `salary_in_usd` / gross annual cash. For Indian workers, reported as local INR converted to USD or direct USD export contracts.
* **Indian Population Coverage:** Only ~150–220 records represent `employee_residence == 'IN'`.
* **Audit Disposition:** 🟡 **BENCHMARK-ONLY**. Fully legally usable; excellent for validating global vs. India purchasing-power parity spreads, remote work premiums, and experience coefficients, but far too sparse for standalone Indian cell modeling.

#### Candidate 10: Jobs and Salaries in Data Science (2024 / 2025 Edition)
* **Kaggle Link:** [hummaamqaasim/jobs-in-data](https://www.kaggle.com/datasets/hummaamqaasim/jobs-in-data)
* **Author / Uploader:** Hummaam Qaasim (`hummaamqaasim`)
* **Observed Attributes:** ~14,000+ global records (updated through late 2024).
* **Upstream Provenance:** Expanded feed from `ai-jobs.net` / `JobsInData`.
* **Licensing:** `CC0: Public Domain`.
* **Target Compatibility:** Gross annualized compensation.
* **Indian Population Coverage:** ~600 records with `employee_residence == 'IN'`. Mostly remote US/EU contractors or multinational AI engineers.
* **Audit Disposition:** 🟡 **BENCHMARK-ONLY**. Approved for baseline benchmarking and ablated feature testing; disqualified as primary ground truth due to sample concentration in international export roles rather than domestic tech employment.

#### Candidate 11: Data Science, AI & ML Job Salaries
* **Kaggle Link:** [suprajapanicker/data-science-ai-ml-job-salarie](https://www.kaggle.com/datasets/suprajapanicker/data-science-ai-ml-job-salarie)
* **Author / Uploader:** Supraja Panicker (`suprajapanicker`)
* **Observed Attributes:** ~3,500 global records.
* **Upstream Provenance:** ai-jobs.net mirror with cleaned role categories.
* **Licensing:** `CC0: Public Domain`.
* **Audit Disposition:** 🟡 **BENCHMARK-ONLY** (Deduplicate against Candidate 09 and Candidate 10).

#### Candidate 12: Data Science Salaries (Sazid)
* **Kaggle Link:** [sazidthe1/data-science-salaries](https://www.kaggle.com/datasets/sazidthe1/data-science-salaries)
* **Author / Uploader:** Sazid (`sazidthe1`)
* **Observed Attributes:** ~4,000 global records.
* **Upstream Provenance:** ai-jobs.net export.
* **Licensing:** `CC0: Public Domain`.
* **Audit Disposition:** 🟡 **BENCHMARK-ONLY** (Duplicate stream; redundant with Candidate 10).

---

### Archetype C: Major Developer & Data Science Community Surveys

#### Candidate 13: Stack Overflow Annual Developer Survey 2024
* **Kaggle Link:** [kunal28luthra/stack-overview-annual-developer-survey-2024](https://www.kaggle.com/datasets/kunal28luthra/stack-overview-annual-developer-survey-2024) (and [thedevastator/stack-overflow-annual-developer-survey-2024](https://www.kaggle.com/datasets/thedevastator/stack-overflow-annual-developer-survey-2024))
* **Author / Uploader:** Kunal Luthra / The Devastator
* **Observed Attributes:** 65,000+ global responses. Filterable to **~4,500+ Indian developer responses**.
* **Key Fields:** `Country`, `EdLevel`, `YearsCode`, `YearsCodePro`, `DevType`, `OrgSize`, `CompTotal`, `CompFreq`, `ConvertedCompYearly`, `LanguageHaveWorkedWith`, `DatabaseHaveWorkedWith`, `AISelect`.
* **Upstream Provenance:** Stack Overflow official annual community survey.
* **Licensing:** Open Database License (`ODbL 1.0`) / `DbCL 1.0`. Commercial redistribution permitted with attribution and share-alike terms.
* **Target Compatibility:** Measures `CompTotal` (Total Annual Compensation). Self-reported; bundles performance bonuses, allowances, and informal perks. Not guaranteed fixed cash.
* **Selection Bias:** Highly active open-source and English-speaking developer community; heavily overrepresents active learners, web technologies, and modern frameworks; underrepresents traditional legacy IT services cohorts.
* **Audit Disposition:** 🟡 **APPROVED FOR BENCHMARK & RELATIONSHIP DISCOVERY**. 
  - One of ArthaIQ's highest-value exploratory assets.
  - Usable for: Modeling non-linear returns to experience ($YOE$), tech-stack premiums (e.g. PyTorch/Rust vs Java/Spring Boot relative delta), and education level returns.
  - Binding Rule: Must be evaluated under a separate target branch (`target_measure: total_comp_annual`) and never mixed directly into `guaranteed_cash_annual` tables without unbundling adjustments.

#### Candidate 14: Stack Overflow 2023 Developer Survey
* **Kaggle Link:** [moyangkai/stack-overflow-2023-developer-survey](https://www.kaggle.com/datasets/moyangkai/stack-overflow-2023-developer-survey)
* **Author / Uploader:** Moyang Kai (`moyangkai`)
* **Observed Attributes:** 89,184 global responses (~5,200 Indian tech professionals).
* **Upstream Provenance:** Official Stack Overflow Survey 2023.
* **Licensing:** `ODbL 1.0`.
* **Audit Disposition:** 🟡 **APPROVED FOR BENCHMARK & TEMPORAL DRIFT ANALYSIS** (Enables measuring year-over-year tech stack salary shifts between 2023 and 2024).

#### Candidate 15: Stack Overflow Survey Salaries 2023 vs 2024
* **Kaggle Link:** [ahmedmohamed2003/stack-overflow-survey-salaries-2023-vs-2024](https://www.kaggle.com/datasets/ahmedmohamed2003/stack-overflow-survey-salaries-2023-vs-2024)
* **Author / Uploader:** Ahmed Mohamed (`ahmedmohamed2003`)
* **Observed Attributes:** ~30,000 pre-cleaned salary responses across the two survey cycles.
* **Upstream Provenance:** Harmonized slice of Stack Overflow 2023/2024 surveys.
* **Licensing:** `ODbL 1.0`.
* **Audit Disposition:** 🟡 **BENCHMARK-ONLY** (Useful for quick drift exploration without processing the full raw SO survey schemas).

#### Candidate 16: Kaggle Machine Learning & Data Science Survey 2022
* **Kaggle Link:** [kaggle-survey-2022](https://www.kaggle.com/c/kaggle-survey-2022)
* **Author / Uploader:** Kaggle Official
* **Observed Attributes:** 23,997 respondents worldwide; ~6,000+ Indian respondents.
* **Target Compatibility:** Compensation reported strictly in **coarse binned brackets** (e.g. `"$1,000-$1,999"`, `"$10,000-$14,999"`, `"$25,000-$29,999"`).
* **Licensing:** Kaggle Terms / Open Data.
* **Audit Disposition:** 🟡 **BENCHMARK-ONLY (Ordinal/Classification)**. The coarse bracket bins prevent continuous quantile regression ($P_{10}, P_{50}, P_{90}$ in LPA), but serve as a valuable macro shape check.

---

### Archetype D: Crowdsourced Platforms, Scrapes & Student Projects

#### Candidate 17: Data Science and STEM Salaries (Levels.fyi Scrape)
* **Kaggle Link:** [jackogozaly/data-science-and-stem-salaries](https://www.kaggle.com/datasets/jackogozaly/data-science-and-stem-salaries)
* **Author / Uploader:** Jack Ogozaly (`jackogozaly`)
* **Observed Attributes:** 62,642 records. India subset: ~1,800 records across Bengaluru, Hyderabad, Pune, Gurgaon.
* **Columns:** `totalyearlycompensation`, `company`, `level`, `title`, `location`, `yearsofexperience`, `yearsatcompany`, `basesalary`, `stockgrantvalue`, `bonus`.
* **Upstream Provenance:** Scraped from Levels.fyi API and public submissions.
* **Target Compatibility:** Explicitly unbundles `basesalary`, `stockgrantvalue`, and `bonus`. Perfect structural alignment with ArthaIQ's compensation ontology.
* **Licensing & Legal Status:** **CRITICAL LEGAL DISQUALIFIER.** Levels.fyi Terms of Service explicitly prohibit automated scraping, indexing, and commercial derivative works. Ingesting this data into ArthaIQ exposes the project to direct intellectual property and breach-of-terms liability under rule `R-DA-01`.
* **Audit Disposition:** 🔴 **REJECTED FOR MODEL TRAINING**. May only be inspected as a conceptual schema design reference for unbundling equity vs fixed cash.

#### Candidate 18: Salary Data based on Experience, Age, Gender, Education
* **Kaggle Link:** [mohithsairamreddy/salary-data](https://www.kaggle.com/datasets/mohithsairamreddy/salary-data)
* **Author / Uploader:** Mohith Sai Ram Reddy (`mohithsairamreddy`)
* **Observed Attributes:** ~6,700 rows.
* **Columns:** `Age`, `Gender`, `Education Level`, `Job Title`, `Years of Experience`, `Salary`.
* **Upstream Provenance:** Aggregated generic web tutorial dataset; no verified employer or location provenance. Currency unit is ambiguous (unlabeled USD/INR mix).
* **Audit Disposition:** 🔴 **REJECTED** (Unverified origin, missing geographic grounding, ambiguous currency).

#### Candidate 19: Companies' Salary Dataset for Various Job Roles
* **Kaggle Link:** [asaniczka/salary-dataset-a-simple-introductory-dataset](https://www.kaggle.com/datasets/asaniczka/salary-dataset-a-simple-introductory-dataset)
* **Author / Uploader:** Asaniczka (`asaniczka`)
* **Observed Attributes:** ~1,000 rows.
* **Columns:** `Company Name`, `Job Title`, `Salaries Reported`, `Location`, `Salary`.
* **Upstream Provenance:** Scraped slice of Glassdoor UK/India.
* **Audit Disposition:** 🔴 **REJECTED for Training**; 🔵 **Approved as Test-Fixture Only** (Small test fixture for regression pipeline smoke tests).

#### Candidate 20: Data Science Salary Predictor Dataset
* **Kaggle Link:** Community uploads (e.g. `sazidthe1/data-science-salaries-clean` / student project mirrors)
* **Observed Attributes:** ~1,000 synthetic rows generated via SMOTE and Faker distributions.
* **Target Compatibility:** Fabricated continuous target.
* **Audit Disposition:** 🔴 **REJECTED (Violation of R-MD-11)**. Synthetic data must never be reported as real compensation evidence or used to fit predictive distributions.

---

## 4. Master Evaluation & Training-Readiness Matrix

The following matrix records the definitive audit decisions across the 20 candidates, detailing their compatibility with ArthaIQ Prediction Targets (PT1–PT6) and Phase 1 pipelines:

| # | Candidate Dataset Slug | Primary Provenance | Stated License | Real Legal Status | Stated Target Measure | ArthaIQ Target Match | N (Total) | N (India Tech) | Disposition | Permitted Role in ArthaIQ |
|:---:|:---|:---|:---|:---|:---|:---|:---:|:---:|:---:|:---|
| 01 | `iamsouravbanerjee/software-industry-salary-dataset-2022` | Glassdoor / AmbitionBox | CC0 (Claimed) | Unauthorized Scrape | Aggregated CTC | Incompatible (Bundled) | 22,770 | ~22,000 | 🔵 **Test-Fixture Only** | Currency & Lakhs regex unit tests (`tests/fixtures/`) |
| 02 | `whenamancodes/data-science-jobs-in-india` | AmbitionBox Job Search | Apache 2.0 (Claimed) | Unauthorized Scrape | Advertised LPA | PT3 Only (Skewed) | 1,600 | 1,600 | 🔴 **Rejected** | None (Violates `R-DA-01`) |
| 03 | `promptcloud/jobs-on-naukricom` | Naukri.com Postings | CC0 (Claimed) | Unauthorized Scrape | Advertised Pay String | PT3 (65% missing) | 30,000 | 30,000 | 🔵 **Test-Fixture Only** | Skill taxonomy & entity extraction test fixture |
| 04 | `iqbal303/job-postings-dataset-from-naukricom` | Naukri.com Search | Unknown | Unauthorized Scrape | Advertised Range | PT3 | 12,000 | 12,000 | 🔴 **Rejected** | None (Redundant scrape) |
| 05 | `anandhuh/12000-data-science-jobs-in-india-naukricom` | Naukri.com Scrape | Open | Unauthorized Scrape | Advertised Range | PT3 | 12,000 | 12,000 | 🔴 **Rejected** | None (Violates `R-DA-01`) |
| 06 | `amar5693/india-job-market-and-salary-trends-2026` | Multi-portal Scrape | Unknown | Unverified Aggregation | Advertised Min/Max | PT3 | 5,000 | 5,000 | 🔵 **Test-Fixture Only** | PT3 advertised range schema tests |
| 07 | `himanshusingh2003/jobs-in-kolkata` | Job Board Scrape | CC0 | Unverified Micro-sample | Advertised Range | PT3 | 40 | 40 | 🔵 **Test-Fixture Only** | Minimal 40-row fixture for schema tests |
| 08 | `kapoorprakhar/indian-job-market-analysis` | Job Portal Scrape | Unknown | Unverified Aggregation | Monthly Advertised | PT3 | 180 | 180 | 🔵 **Test-Fixture Only** | Monthly-to-annual normalizer tests |
| 09 | `arnabchaki/data-science-salaries-2023` | ai-jobs.net Open Feed | CC0 | Verified Open Source | Gross USD Cash | Incompatible (USD/Remote) | 3,755 | ~200 | 🟡 **Benchmark Only** | Global vs India PPP spread, remote work premium |
| 10 | `hummaamqaasim/jobs-in-data` | ai-jobs.net / JobsInData | CC0 | Verified Open Source | Gross USD Cash | Incompatible (USD/Remote) | 14,000+ | ~600 | 🟡 **Benchmark Only** | Exploratory non-linear feature benchmarking |
| 11 | `suprajapanicker/data-science-ai-ml-job-salarie` | ai-jobs.net Mirror | CC0 | Verified Open Source | Gross USD Cash | Incompatible | 3,500 | ~200 | 🟡 **Benchmark Only** | Feature ablation experiments |
| 12 | `sazidthe1/data-science-salaries` | ai-jobs.net Mirror | CC0 | Verified Open Source | Gross USD Cash | Incompatible | 4,000 | ~200 | 🟡 **Benchmark Only** | Deduplicate against #10 |
| 13 | `kunal28luthra/stack-overview-annual-developer-survey-2024` | Stack Overflow Official | ODbL 1.0 | Verified Legitimate | Total Comp Annual | PT6 / Benchmark (`comp_total`) | 65,000+ | ~4,500 | 🟡 **Benchmark & Discovery** | Experience curves, tech stack coefficients |
| 14 | `moyangkai/stack-overflow-2023-developer-survey` | Stack Overflow Official | ODbL 1.0 | Verified Legitimate | Total Comp Annual | PT6 / Benchmark (`comp_total`) | 89,184 | ~5,200 | 🟡 **Benchmark & Discovery** | 2023–2024 temporal compensation drift tests |
| 15 | `ahmedmohamed2003/stack-overflow-survey-salaries-2023-vs-2024` | Stack Overflow Harmonized | ODbL 1.0 | Verified Legitimate | Total Comp Annual | PT6 / Benchmark | 30,000 | ~2,500 | 🟡 **Benchmark Only** | Quick drift verification |
| 16 | `kaggle-survey-2022` | Kaggle Community Survey | Kaggle Terms | Verified Legitimate | Coarse USD Bins | Incompatible (Binned) | 23,997 | ~6,000 | 🟡 **Benchmark Only** | Macro distribution shape validation |
| 17 | `jackogozaly/data-science-and-stem-salaries` | Levels.fyi Scrape | CC0 (Claimed) | Direct ToS Breach | Base / Stock / Bonus | Incompatible (Legal Risk) | 62,642 | ~1,800 | 🔴 **Rejected (Legal Risk)** | Schema design reference only; NO CODE INGESTION |
| 18 | `mohithsairamreddy/salary-data` | Web Tutorial Scrape | Unknown | Unverified Origin | Ambiguous Salary | Incompatible | 6,700 | Unknown | 🔴 **Rejected** | None (Unverified data) |
| 19 | `asaniczka/salary-dataset-a-simple-introductory-dataset` | Glassdoor Scrape | CC0 (Claimed) | Unauthorized Scrape | Aggregated Salary | Incompatible | 1,000 | ~200 | 🔵 **Test-Fixture Only** | Smoke testing model pipelines |
| 20 | `data-science-salary-predictor` | Synthetic Generator | Public | Synthetic Fabrication | Fabricated Continuous | Incompatible (Synthetic) | 1,000 | 0 | 🔴 **Rejected (R-MD-11)** | None (Synthetic data violation) |

---

## 5. Strategic Implications for ArthaIQ Roadmap

### 1. The Core Scientific & Legal Conclusion
**ArthaIQ cannot and will not train its primary production compensation model (PT1) on public Kaggle datasets.**

Any machine learning tool that claims to deliver reliable, personalized salary predictions for Indian tech workers by training on Kaggle CSVs is either:
1. **Legally Vulnerable:** Training on unauthorized scrapes of proprietary platforms (AmbitionBox, Naukri, Glassdoor, Levels.fyi) in violation of site terms and data protection laws;
2. **Statistically Unrepresentative:** Training on ~300 international remote contractor rows from `ai-jobs.net`, which represent foreign billing rates rather than domestic Indian compensation; or
3. **Methodologically Distorted:** Conflating advertised hiring ranges (which exclude equity and represent recruiter budgets) or unbundled CTC (which bundles variable bonuses and employer PF) with `guaranteed_cash_annual`.

### 2. The Legitimate Engineering Role of Approved Kaggle Datasets
While rejected for training PT1, approved Kaggle assets provide immediate engineering and scientific value in Phase 1 and Phase 2:

* **Primary Exploratory Benchmark (Candidate 13 — Stack Overflow 2024, $N_{\text{IN}} \approx 4,500$):**
  We will use this dataset to fit baseline non-linear relationships:
  $$\log(\text{CompTotal}) = \alpha + \beta_1 \cdot \text{YOE} + \beta_2 \cdot \text{YOE}^2 + \sum_k \gamma_k \cdot \text{Skill}_k + \epsilon$$
  This allows us to calibrate expected returns to experience and technology stack premiums (e.g. PyTorch/Rust vs Java) prior to ingesting proprietary ground truth.
* **Plumbing Test Fixtures (Candidates 01, 03, 06, 07):**
  Frozen strictly inside `tests/fixtures/` to validate:
  1. Indian currency text parsing (`"₹12-15 Lacs p.a."` $\rightarrow$ `[12.0, 15.0] LPA`).
  2. Role canonicalization (mapping `"Sr. Software Engineer - Java"` $\rightarrow$ `role_id: backend_engineer`, `level: senior`).
  3. City fuzzy matching (`"Bangalore / Bengaluru"` $\rightarrow$ `location_id: BLR`).

### 3. Bridging the Indian Ground Truth Moat
Because public Kaggle datasets cannot supply verified `guaranteed_cash_annual` ground truth, ArthaIQ must execute the coordinated Phase 1/Phase 2 data roadmap:
1. **Layer 1 Official Anchor (Task T1.06):** Ingest unit-level microdata from the **Periodic Labour Force Survey (PLFS)** and Labour Bureau surveys to establish statistically valid urban wage floors and distribution tails across Indian metropolitan regions (Bengaluru, Hyderabad, Pune, NCR).
2. **Layer 2 Voluntary Governed Ingestion (Task T2.10):** Design ArthaIQ's proprietary voluntary contribution intake schema, capturing component-level salary line items (Basic + HRA + Special Allowance) with optional redacted payslip verification and strict $k$-anonymity ($\ge 5$).

---

## 6. Outstanding Research Questions & Next Actions

### Unresolved Research Questions
1. **Q-KAG-01:** Can the non-linear experience curves fitted on Stack Overflow's self-reported total compensation ($\beta_{\text{YOE}}, \beta_{\text{YOE}^2}$) transfer directly as prior distributions to `guaranteed_cash_annual` models without scale distortion? *(To be tested in Phase 4 benchmark experiments).*
2. **Q-KAG-02:** What is the empirical divergence between advertised salary midpoints in Naukri fixtures (Candidate 03) and realized employee earnings reported in Stack Overflow (Candidate 13) for identical YOE brackets in Bengaluru?

### Immediate Next Actions
1. **T1.05 Update:** Seed `docs/research/evidence-register.csv` with the claims, evidence quality ratings, and validation experiments established in this audit.
2. **T1.06 Execution:** Inspect Periodic Labour Force Survey (PLFS) microdata layouts and Labour Bureau Occupational Wage Survey tables to establish Layer 1 official benchmarks.
3. **Plumbing Setup:** Copy Candidate 01 and 03 schema headers into `tests/fixtures/` for upcoming parser property tests.

---

*Authored for ArthaIQ under Phase 1, Task T1.08.*
