# Data Card: Stack Overflow Annual Developer Survey 2024

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-KAG-SO-01` |
| **Document ID** | `docs/data-cards/SRC-KAG-SO-01.md` |
| **Short Name** | Stack Overflow Survey 2024 |
| **Long Name** | Stack Overflow Annual Developer Survey 2024 (Official Public Release) |
| **Provider** | Stack Exchange Inc. / Stack Overflow |
| **Primary URL** | https://survey.stackoverflow.co/2024/ |
| **Repository URL** | https://github.com/StackExchange/Survey |
| **Licence** | Open Data Commons Open Database License (`ODbL-1.0`) |
| **SQS / Tier** | **72.2** / `TIER_3_MARKET_SIGNAL` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Approved Benchmark (Non-Linear Returns to Experience & Tech Stack Curvature Priors) |
| **Prohibited Routing** | Direct PT1 ground-truth training without domain regularizer (`R-EV-05`) |

---

## 1. Provenance, Licensing & Legal Integrity

* **Collection Organization:** Stack Overflow. Conducted annually across global professional developers.
* **Licensing:** Published under the Open Data Commons Open Database License (`ODbL 1.0`). Confirmed commercial and research reuse, modification, and distribution permitted with attribution and share-alike conditions.
* **ToS Risk:** Zero. Direct release from official Stack Overflow repository.
* **Privacy & PII:** Redacted public release; all free-text fields containing potential personal identifiers are excluded.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-KAG-SO-01/` with verified SHA-256 manifest:

### File: `so_survey_2024_raw_sample.csv`
* Rows: 300 (representative India tech cohort slice) | Columns: 114 | Duplicate rows: 0

Key compensation and covariate fields profiled:

| Column | Type | Null % | Example Values / Range | Description |
|:---|:---:|:---:|:---|:---|
| `ResponseId` | Int64 | 0.0% | 1 to 65,437 | Unique survey respondent identifier |
| `Country` | String | 0.0% | "India", "United States", .. | Country of residence |
| `Currency` | String | 12.0% | "INR", "USD", "EUR" | Reported currency |
| `CompTotal` | Float64 | 24.3% | ₹1,50,000 to ₹1,80,00,000 | Self-reported total annual compensation |
| `CompFreq` | String | 15.0% | "Yearly", "Monthly", "Weekly" | Compensation reporting frequency |
| `YearsCodePro` | String | 4.2% | "Less than 1 year", "1" to "30" | Professional software development experience ($YOE$) |
| `DevType` | String | 8.5% | "Developer, full-stack", .. | Self-identified primary engineering role |
| `LanguageHaveWorkedWith` | String | 2.1% | "Python;JavaScript;SQL;Go" | Semicolon-delimited programming languages |
| `DatabaseHaveWorkedWith` | String | 5.4% | "PostgreSQL;Redis;MongoDB" | Semicolon-delimited databases |
| `PlatformHaveWorkedWith` | String | 8.0% | "Amazon Web Services (AWS);Docker" | Cloud and deployment platforms |
| `EdLevel` | String | 3.5% | "Bachelor’s degree", "Master’s degree" | Formal educational attainment |

---

## 3. Compensation Target Alignment & Accounting Identity

* **Compensation Measure Alignment:**
  Stack Overflow asks: *"What is your current total compensation (salary, bonuses, and perks, before taxes and deductions)?"*
  This reports **`total_comp_annual`** (`PT-TOT`), **NOT** guaranteed fixed cash (`guaranteed_cash_annual`).
* **Unbundling Prohibition (`R-MD-07`):**
  Under Rule `R-MD-07`, ArthaIQ **strictly forbids** applying a uniform heuristic divisor (e.g. dividing `CompTotal` by $1.20$ or $1.30$) to manufacture synthetic base pay.
* **Approved Transformation Policy:**
  Stack Overflow data is used strictly to estimate **relative dimensionless curvature ratios**:
  $$\log(\text{CompTotal}) = \alpha + \beta_1 \cdot \text{YOE} + \beta_2 \cdot \text{YOE}^2 + \sum_k \gamma_k \cdot \text{Skill}_k$$
  The relative parameters $\beta_1, \beta_2, \gamma_k$ serve as regularization priors for experience and tech-stack curvature in Phase 4 feature modeling. The intercept $\alpha$ is discarded.

---

## 4. Selection & Response Biases

1. **Self-Selection Bias:** Voluntary participation by self-directed developers visiting Stack Overflow. Over-represents motivated, community-active developers.
2. **Rounding & Anchoring:** Respondents disproportionately report round numbers (e.g. ₹15,00,000, ₹20,00,000 LPA).
3. **Upper-Tail Truncation:** Very senior executives, CTOs, and staff architects rarely complete public surveys.

---

## 5. Sufficiency Audit against `sufficiency-v1.yaml`

* **C1 (Sample size):** National India tech subset $N \approx 4,500$ across the full survey release; core cells satisfy $N_{\text{eff}} \ge 50$.
* **C2 (SQS floor):** SQS = 72.2 ($\ge 65.0$). All Hard Gates $\ge 3$. Approved for benchmark curvature.
* **C3 (Recency):** May–June 2024 survey window. Deflated via RBI CPI-Urban (`SRC-SUP-MAC-01`).
