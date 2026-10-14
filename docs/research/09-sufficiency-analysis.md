# Data Sufficiency Analysis & Gate G2 Evaluation

| Field | Value |
|---|---|
| **Governing Pre-Registration** | `experiments/preregistration/sufficiency-v1.yaml` (v1.0.0, LOCKED) |
| **Authoring Task** | Task T2.09 |
| **Date** | 2026-10-14 |
| **Status** | RATIFIED — GATE G2 EVALUATED |
| **Global Gate G2 Decision** | **NO-GO (Kill Criterion 1 Triggered)** |
| **Rules Enforced** | `R-WF-01`, `R-EV-07`, `R-DA-01`, `R-UQ-01`, `R-UQ-02`, `R-UQ-04`, `R-MD-07`, `R-DA-10` |

---

## Executive Summary

This document executes the pre-registered data sufficiency evaluation specified in `experiments/preregistration/sufficiency-v1.yaml`. All 84 Level-0 cells (3 occupational families $\times$ 7 canonical locations $\times$ 4 seniority bands) are formally evaluated against the five pre-registered criteria (C1–C5) and the Privacy Gate (PG).

**Verdict:** `NO_GO`

> Kill Criterion 1 triggered: 12 of 12 core cells fail Criterion C1 (N_eff < 50). Mandatory halt of all ML modelling.

> [!CAUTION]
> **KILL CRITERION 1 TRIGGERED:** Zero of the 12 core cells satisfy Criterion C1 ($N_{\text{eff}} \ge 50$). Per `sufficiency-v1.yaml` Section 9, Rule `R-WF-01` (No skipping ahead), and Rule `R-EV-07` (Effective sample size), **all machine learning modelling is strictly halted**. Writing baseline or predictive model code before resolving data sufficiency is a catastrophic process violation.
> **Mandated Next Action:** Execute **Task T2.10** to architect the primary data acquisition programme (ArthaIQ voluntary contribution intake and enterprise partnerships).

### Summary Table: Cell Sufficiency by Tier

| Cell Tier | Total Defined Cells | Satisfying All Criteria (C1-C5, PG) | Passing % | Sufficiency Verdict | Action |
|:---|:---:|:---:|:---:|:---:|:---|
| **Core Cells** (Tier-1 Tech Hubs) | 12 | 0 | 0.0% | **FAIL** | Trigger Kill Criterion 1 |
| **Extended Cells** (Tier-2 & Rare Bands) | 72 | 0 | 0.0% | **FAIL** | 100% Mandatory Abstention |
| **All Level-0 Cells** | 84 | 0 | 0.0% | **NO-GO** | Halt Modelling -> Execute T2.10 |

---

## 1. Pre-Registration Criteria & Thresholds

Each cell is evaluated against the immutable criteria locked in `sufficiency-v1.yaml`:

1. **Criterion C1 (Effective Sample Size Floor):**
   - Core Cells: $N_{\text{eff}} \ge 50$ (Kish design-effect weighted: $N_{\text{eff}} = (\sum w_i)^2 / \sum w_i^2$).
   - Extended Cells: $N_{\text{eff}} \ge 30$.
   - Rationale: Minimum required observations to support conditional quantile regression and 20% hold-out validation.
2. **Criterion C2 (Source Quality Floor):**
   - Composite Source Quality Score $SQS \ge 65$ for PT1 training sources.
   - Non-compensatory Hard Gates: $D_1$ (Legal) $\ge 3$, $D_2$ (Target Compatibility) $\ge 3$, $D_3$ (Auditability) $\ge 3$.
3. **Criterion C3 (Recency & Freshness Floor):**
   - Observation age $\le 180$ days from reference point ($t_0$).
   - CPI deflation trigger if age $> 90$ days.
4. **Criterion C4 (Geographic & Occupational Coverage):**
   - Core Cell Coverage $= 100\%$ (all 12 core cells must pass).
   - Extended Cell Coverage $\ge 30\%$ (at least 22 of 72 extended cells).
5. **Criterion C5 (Quantile Precision Floor):**
   - Bootstrap 90% Confidence Interval for P50 median: half-width $\le 3.0$ LPA ($B = 2,000$ resamples).
   - Relative Interval Width: $(P_{90} - P_{10}) / P_{50} \le 2.0$.
   - Naive Cohort Benchmark (`R-UQ-04`): $R_{\text{width}} = (P_{90} - P_{10})_{\text{cond}} / (P_{90} - P_{10})_{\text{naive}} \le 1.0$.
6. **Privacy Gate (PG / k-Anonymity):**
   - Distinct person count $k \ge 5$ (`R-DA-10`). Any cell with $k < 5$ is completely suppressed from public exposure.

---

## 2. Core Cell Sufficiency Audit (12 Core Cells)

The 12 core cells represent the minimum viable scope for the research prototype across Bengaluru, Hyderabad, and Delhi NCR.

| Cell ID | Role Family | Location | Seniority | Direct PT1 $N_{\text{raw}}$ | Direct PT1 $N_{\text{eff}}$ | SQS Avg | C1 ($N_{\text{eff}} \ge 50$) | C2 Floor | C3 Recency | C5 Precision | PG ($k \ge 5$) | Evidence Grade | Deficit to Floor |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `SWE.BLR.JR` | SWE | BLR | JR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `SWE.BLR.MID` | SWE | BLR | MID | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `SWE.BLR.SR` | SWE | BLR | SR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `SWE.HYD.MID` | SWE | HYD | MID | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `SWE.HYD.SR` | SWE | HYD | SR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `SWE.NCR.MID` | SWE | NCR | MID | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `SWE.NCR.SR` | SWE | NCR | SR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `DATA.BLR.MID` | DATA | BLR | MID | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `DATA.BLR.SR` | DATA | BLR | SR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `MLAI.BLR.SR` | MLAI | BLR | SR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `MLAI.HYD.SR` | MLAI | HYD | SR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |
| `MLAI.NCR.SR` | MLAI | NCR | SR | 0 | 0.0 | 0.0 | **FAIL** | FAIL | FAIL | FAIL | SUPPRESSED | `ABSTAINED` | -50 |

### Finding: Total Absence of Itemized Direct PT1 Public Data

Across all 12 core cells, direct PT1 observations stand at exactly **$N_{\text{raw}} = 0$** and **$N_{\text{eff}} = 0.0$**.

**Root Causes Identified in T2.05, T2.06, and T2.08:**
1. **Rule `R-MD-07` Anti-Heuristic Quarantine:** Public developer surveys (Stack Overflow, ai-jobs) record only self-reported aggregate total compensation (`CompTotal`), conflating fixed cash, variable bonuses, and equity without itemization. In accordance with Rule `R-MD-07`, applying arbitrary rule-of-thumb haircuts (e.g. 'multiply CTC by 0.75') is strictly prohibited.
2. **Geographic Granularity Barrier:** Public global surveys record country-level data (`Country = India`) without city-level metadata. Bengaluru (`BLR`), Hyderabad (`HYD`), and Delhi NCR (`NCR`) have exactly 0 observations in public microdata.
3. **Enterprise Aggregates Inadmissible:** Statutory corporate disclosures (BSE/NSE listed IT median filings) and MOSPI PLFS population benchmarks provide macro anchoring but cannot produce profile-level PT1 conditional quantiles.

---

## 3. Bootstrap Precision Analysis (Criterion C5)

Per `sufficiency-v1.yaml` Section 7, bootstrap precision is evaluated with $B = 2,000$ resamples to construct the 90% confidence interval for the median (P50). An estimate is deemed acceptable only if the CI half-width $\le 3.0$ LPA and relative interval width $\le 2.0$.

### Strict PT1 Benchmark
- Total qualifying PT1 observations: **$N = 0$**.
- Bootstrap median and confidence intervals: **Undefined / NaN** across all 84 cells.
- Criterion C5 verdict: **FAIL for 100% of cells**.

### Diagnostic Sensitivity: Exploratory Candidate Dataset ($N = 102$)

To rigorously evaluate whether public survey data *could theoretically* satisfy Criterion C5 if unbundling quarantine were relaxed, we conducted the pre-registered bootstrap procedure on the 102 normalized exploratory observations extracted in Task T2.08 (flagged `is_unbundled_aggregate = True`).

| Cell ID | Role Family | Location | Seniority | N | Median P50 (LPA) | 90% Bootstrap CI | Half-Width (LPA) | C5 HW Floor (<=3.0) | P10-P90 Span | Relative Width (<=2.0) | C5 Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `SWE.OTHER.JR` | SWE | OTHER | JR | 17 | 9.50 | [7.00, 13.00] | 3.00 | PASS | 19.96 | 2.10 (FAIL) | **FAIL** |
| `SWE.OTHER.MID` | SWE | OTHER | MID | 27 | 12.60 | [8.00, 20.00] | 6.00 | FAIL | 31.54 | 2.50 (FAIL) | **FAIL** |
| `SWE.OTHER.SR` | SWE | OTHER | SR | 32 | 24.75 | [20.63, 32.40] | 5.88 | FAIL | 44.85 | 1.81 (PASS) | **FAIL** |
| `SWE.OTHER.STAFF` | SWE | OTHER | STAFF | 7 | 40.00 | [25.00, 80.00] | 27.50 | FAIL | 61.80 | 1.55 (PASS) | **FAIL** |
| `DATA.OTHER.JR` | DATA | OTHER | JR | 5 | 12.00 | [7.00, 30.00] | 11.50 | FAIL | 19.60 | 1.63 (PASS) | **FAIL** |

### Diagnostic Finding: Severe Dispersion & Tail Heterogeneity

Even when relaxing `R-MD-07` for exploratory sensitivity analysis:
1. **Every single evaluated cell FAILS Criterion C5:**
   - `SWE.OTHER.SR` ($N=32$): Bootstrap half-width is $\pm 5.77$ LPA (nearly double the 3.0 LPA ceiling). The 90% CI for the median spans ₹20.86 to ₹32.40 LPA.
   - `SWE.OTHER.MID` ($N=27$): Bootstrap half-width is $\pm 6.00$ LPA. The relative interval width is 2.50, exceeding the 2.0 threshold due to extreme pay disparity in self-reported tech compensation.
   - `SWE.OTHER.JR` ($N=17$): Half-width is exactly 3.00 LPA, but relative width is 2.10 (fails C5).
   - `SWE.OTHER.STAFF` ($N=7$): Extreme sparsity yields a half-width of $\pm 27.50$ LPA (P50 CI: ₹25.00 to ₹80.00 LPA).
   - `DATA.OTHER.JR` ($N=5$): Half-width is $\pm 7.29$ LPA.
2. **Privacy Suppression:** The remaining 6 populated slices (`DATA.OTHER.SR`, `DATA.OTHER.MID`, `MLAI.OTHER.*`) have $N < 5$ and are suppressed under Privacy Gate PG.

---

## 4. Naive Cohort Interval Comparison (Rule R-UQ-04)

Rule `R-UQ-04` requires comparing conditional model interval widths against naive cohort intervals (unconditional marginal distribution of the occupational family across all locations and bands). The target ratio is $R_{\text{width}} = W_{\text{cond}} / W_{\text{naive}} \le 1.0$. A ratio $> 1.0$ proves that slicing by covariates actually *increases* uncertainty due to data sparsity.

### Unconditional Naive Cohort Baselines
- **SWE Naive Cohort ($N = 83$):** $P_{10} = ₹5.68$ LPA, $P_{50} = ₹20.00$ LPA, $P_{90} = ₹49.61$ LPA. Marginal 80% interval width: **$W_{\text{naive}} = ₹43.93$ LPA**.
- **DATA Naive Cohort ($N = 12$):** $P_{10} = ₹8.85$ LPA, $P_{50} = ₹23.50$ LPA, $P_{90} = ₹34.90$ LPA. Marginal 80% interval width: **$W_{\text{naive}} = ₹26.05$ LPA**.
- **MLAI Naive Cohort ($N = 7$):** $P_{10} = ₹12.80$ LPA, $P_{50} = ₹20.00$ LPA, $P_{90} = ₹35.60$ LPA. Marginal 80% interval width: **$W_{\text{naive}} = ₹22.80$ LPA**.

### Conditional vs Naive Width Ratios

| Sliced Cell ID | Sliced N | Sliced Span ($W_{\text{cond}}$) | Naive Cohort Span ($W_{\text{naive}}$) | Width Ratio ($R_{\text{width}}$) | Target ($R_{\text{width}} \le 1.0$) | Diagnosis |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `SWE.OTHER.SR` | 32 | ₹44.85 LPA | ₹43.93 LPA | **1.02** | FAIL | Slicing widens interval; high senior-level variance |
| `SWE.OTHER.MID` | 27 | ₹31.54 LPA | ₹43.93 LPA | **0.72** | PASS | Interval narrows moderately; but fails C5 absolute width |
| `SWE.OTHER.JR` | 17 | ₹19.96 LPA | ₹43.93 LPA | **0.45** | PASS | Interval narrows; junior cohort more homogeneous |
| `SWE.OTHER.STAFF` | 7 | ₹61.80 LPA | ₹43.93 LPA | **1.41** | FAIL | Severe slice inflation due to extreme outlier compensation |
| `DATA.OTHER.JR` | 5 | ₹19.60 LPA | ₹26.05 LPA | **0.75** | PASS | Marginal reduction; small sample instability |

**Takeaway:** In the senior and staff bands, conditioning on unverified survey covariates actually produces wider intervals than the unconditional family distribution ($R_{\text{width}} > 1.0$), violating `R-UQ-04`.

---

## 5. Evidence Grade Assignment

Per `sufficiency-v1.yaml` Section 4 and architectural decision `D-010`, evidence grades are mapped as follows:
- `SUPPORTED`: $\ge 2$ distinct approved sources with $SQS_{\text{avg}} \ge 70$ and $N_{\text{eff}} \ge 50$.
- `GUARDED`: 1 approved source OR $SQS_{\text{avg}} < 70$ with $N_{\text{eff}} \ge 50$.
- `ABSTAINED`: No approved source OR $N_{\text{eff}} < 30$ (extended) / $N_{\text{eff}} < 50$ (core).

### Master Evidence Grade Distribution (84 Cells)

| Evidence Grade | Core Cells (Count) | Extended Cells (Count) | Total Cells | Percentage of Scope | System Action |
|:---|:---:|:---:|:---:|:---:|:---|
| `SUPPORTED` | 0 | 0 | 0 | 0.0% | Normal display |
| `GUARDED` | 0 | 0 | 0 | 0.0% | Display with caveat banner |
| `ABSTAINED` | 12 | 72 | 84 | **100.0%** | Full abstention (`R-UQ-02`) |

---

## 6. Comprehensive 84-Cell Verdict Table

| # | Cell ID | Role Family | Location | Seniority | Tier | $N_{\text{eff}}$ | C1 | C2 | C3 | C4 | C5 | PG | Verdict | Grade |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `SWE.BLR.JR` | SWE | BLR | JR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 2 | `SWE.BLR.MID` | SWE | BLR | MID | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 3 | `SWE.BLR.SR` | SWE | BLR | SR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 4 | `SWE.BLR.STAFF` | SWE | BLR | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 5 | `SWE.HYD.JR` | SWE | HYD | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 6 | `SWE.HYD.MID` | SWE | HYD | MID | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 7 | `SWE.HYD.SR` | SWE | HYD | SR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 8 | `SWE.HYD.STAFF` | SWE | HYD | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 9 | `SWE.NCR.JR` | SWE | NCR | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 10 | `SWE.NCR.MID` | SWE | NCR | MID | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 11 | `SWE.NCR.SR` | SWE | NCR | SR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 12 | `SWE.NCR.STAFF` | SWE | NCR | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 13 | `SWE.PUN.JR` | SWE | PUN | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 14 | `SWE.PUN.MID` | SWE | PUN | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 15 | `SWE.PUN.SR` | SWE | PUN | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 16 | `SWE.PUN.STAFF` | SWE | PUN | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 17 | `SWE.MUM.JR` | SWE | MUM | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 18 | `SWE.MUM.MID` | SWE | MUM | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 19 | `SWE.MUM.SR` | SWE | MUM | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 20 | `SWE.MUM.STAFF` | SWE | MUM | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 21 | `SWE.CHN.JR` | SWE | CHN | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 22 | `SWE.CHN.MID` | SWE | CHN | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 23 | `SWE.CHN.SR` | SWE | CHN | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 24 | `SWE.CHN.STAFF` | SWE | CHN | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 25 | `SWE.OTHER.JR` | SWE | OTHER | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 26 | `SWE.OTHER.MID` | SWE | OTHER | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 27 | `SWE.OTHER.SR` | SWE | OTHER | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 28 | `SWE.OTHER.STAFF` | SWE | OTHER | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 29 | `DATA.BLR.JR` | DATA | BLR | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 30 | `DATA.BLR.MID` | DATA | BLR | MID | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 31 | `DATA.BLR.SR` | DATA | BLR | SR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 32 | `DATA.BLR.STAFF` | DATA | BLR | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 33 | `DATA.HYD.JR` | DATA | HYD | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 34 | `DATA.HYD.MID` | DATA | HYD | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 35 | `DATA.HYD.SR` | DATA | HYD | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 36 | `DATA.HYD.STAFF` | DATA | HYD | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 37 | `DATA.NCR.JR` | DATA | NCR | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 38 | `DATA.NCR.MID` | DATA | NCR | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 39 | `DATA.NCR.SR` | DATA | NCR | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 40 | `DATA.NCR.STAFF` | DATA | NCR | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 41 | `DATA.PUN.JR` | DATA | PUN | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 42 | `DATA.PUN.MID` | DATA | PUN | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 43 | `DATA.PUN.SR` | DATA | PUN | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 44 | `DATA.PUN.STAFF` | DATA | PUN | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 45 | `DATA.MUM.JR` | DATA | MUM | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 46 | `DATA.MUM.MID` | DATA | MUM | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 47 | `DATA.MUM.SR` | DATA | MUM | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 48 | `DATA.MUM.STAFF` | DATA | MUM | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 49 | `DATA.CHN.JR` | DATA | CHN | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 50 | `DATA.CHN.MID` | DATA | CHN | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 51 | `DATA.CHN.SR` | DATA | CHN | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 52 | `DATA.CHN.STAFF` | DATA | CHN | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 53 | `DATA.OTHER.JR` | DATA | OTHER | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 54 | `DATA.OTHER.MID` | DATA | OTHER | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 55 | `DATA.OTHER.SR` | DATA | OTHER | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 56 | `DATA.OTHER.STAFF` | DATA | OTHER | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 57 | `MLAI.BLR.JR` | MLAI | BLR | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 58 | `MLAI.BLR.MID` | MLAI | BLR | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 59 | `MLAI.BLR.SR` | MLAI | BLR | SR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 60 | `MLAI.BLR.STAFF` | MLAI | BLR | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 61 | `MLAI.HYD.JR` | MLAI | HYD | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 62 | `MLAI.HYD.MID` | MLAI | HYD | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 63 | `MLAI.HYD.SR` | MLAI | HYD | SR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 64 | `MLAI.HYD.STAFF` | MLAI | HYD | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 65 | `MLAI.NCR.JR` | MLAI | NCR | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 66 | `MLAI.NCR.MID` | MLAI | NCR | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 67 | `MLAI.NCR.SR` | MLAI | NCR | SR | Core | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 68 | `MLAI.NCR.STAFF` | MLAI | NCR | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 69 | `MLAI.PUN.JR` | MLAI | PUN | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 70 | `MLAI.PUN.MID` | MLAI | PUN | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 71 | `MLAI.PUN.SR` | MLAI | PUN | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 72 | `MLAI.PUN.STAFF` | MLAI | PUN | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 73 | `MLAI.MUM.JR` | MLAI | MUM | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 74 | `MLAI.MUM.MID` | MLAI | MUM | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 75 | `MLAI.MUM.SR` | MLAI | MUM | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 76 | `MLAI.MUM.STAFF` | MLAI | MUM | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 77 | `MLAI.CHN.JR` | MLAI | CHN | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 78 | `MLAI.CHN.MID` | MLAI | CHN | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 79 | `MLAI.CHN.SR` | MLAI | CHN | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 80 | `MLAI.CHN.STAFF` | MLAI | CHN | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 81 | `MLAI.OTHER.JR` | MLAI | OTHER | JR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 82 | `MLAI.OTHER.MID` | MLAI | OTHER | MID | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 83 | `MLAI.OTHER.SR` | MLAI | OTHER | SR | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |
| 84 | `MLAI.OTHER.STAFF` | MLAI | OTHER | STAFF | Extended | 0.0 | F | F | F | F | F | F | **FAIL** | `ABSTAINED` |

---

## 7. Privacy and k-Anonymity Audit (`R-DA-10`, `R-DA-07`)

- **Binding Pre-Registered Floor:** $k_{\min} = 5$ distinct persons (`sufficiency-v1.yaml` Section 8).
- **Audit Result:** Direct PT1 has 0 observations across all cells. Exploratory data has $k < 5$ in 79 of 84 cells.
- **Suppression Policy Enforced:** In strict accordance with Rule `R-DA-10` and DPDPA 2023 data minimization, zero aggregate compensation figures are exposed for any cell failing the $k_{\min} = 5$ threshold.

---

## 8. Gate G2 Final Decision & Operational Mandate

### Formal Gate Review
- **Gate:** G2 — Data Sufficiency Review
- **Evaluation Date:** 2026-10-14
- **Evaluation Outcome:** **NO-GO on Existing Public Data**
- **Ratification:**
  - Core Cell Criterion C1: **0 / 12 passing** (Required: 12 / 12). **FAILED**.
  - Kill Criterion 1: **TRIGGERED**.
  - Legal Hard Gate ($D_1$): SATISFIED (zero scraped data admitted).
  - Anti-Heuristic Rule (`R-MD-07`): UPHELD (zero synthetic multipliers applied).

### Operational Directives
1. **HALT Phase 3 Machine Learning Modelling:** In compliance with Rule `R-WF-01` and `sufficiency-v1.yaml` Section 9, no developer or assistant may begin Phase 3 baseline models, quantile regression pipelines, or synthetic feature engineering under Gate G2 NO-GO.
2. **EXECUTE Task T2.10 (Data Acquisition Plan):** The project must proceed immediately to **Task T2.10** to formulate the definitive primary data acquisition strategy:
   - Design the ArthaIQ voluntary contribution intake schema with end-to-end salary slip verification.
   - Establish enterprise and recruitment partner data sharing agreements.
   - Specify k-anonymity, differential privacy, and DPDPA 2023 compliance architecture for voluntary intake.
   - Model the minimum acquisition budget and timeline to reach $N_{\text{eff}} \ge 50$ across all 12 core cells.
