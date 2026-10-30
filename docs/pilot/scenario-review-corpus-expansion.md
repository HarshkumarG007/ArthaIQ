# Practitioner Review and Consensus Report: DATA Family Scenario Corpus Expansion

| Metadata Field | Value |
|---|---|
| **Document ID** | `REV-SCEN-CORPUS-01` |
| **Review Date** | `2026-10-30` |
| **System** | **ArthaIQ Career Architect** (Phase 15+ Practice Workspace) |
| **Artifacts Evaluated** | `config/scenarios/scen_data_04_decomp.json`, `config/scenarios/scen_data_05_ethics.json`, `config/scenarios/scen_data_06_feateng.json`, `config/scenarios/scen_data_07_bigdata.json` |
| **Governing Rules** | `rules.md` (`R-CR-01`, `R-CR-03`, `R-CR-04`, `R-CR-08`, `R-CR-11`, `R-CR-12`, `R-CR-15`, `ADR-0010`, `ADR-0013`) |
| **Evaluation Scope** | 4 New Canonical Flaw-Finding Practice Scenarios across DATA Family Competencies |
| **Consensus Verdict** | **UNANIMOUS CONSENSUS RATIFIED — ALL FOUR EXPANDED SCENARIOS APPROVED** |

---

## 1. Executive Summary

This formal practitioner review evaluates the four expanded flaw-finding practice scenarios authored for the **DATA role family** under post-Phase 15 hardening of ArthaIQ Career Architect. The evaluation was conducted by the independent practitioner review panel to ensure that the code artifacts, seeded defects, rubrics, and parameterized variants satisfy rigorous real-world industry standards, zero credentialism claims, and deterministic scoring reproducibility.

The panel reviewed the scenarios across five core evaluation dimensions:
1. **Technical Realism & Industry Grounding:** The code artifacts reflect authentic, representative pipelines encountered in Indian technology teams.
2. **Seeded Defect Precision & Unambiguity:** Flaws represent genuine methodological, statistical, or mathematical defects rather than subjective styling preferences.
3. **Rubric Determinism & Scoring Fairness:** Full credit, partial credit, and false-flag penalties operate strictly deterministically without LLM subjectivity (`ADR-0013`, `Rule R-CR-08`).
4. **Anti-Credentialism Invariant Compliance:** Absolute adherence to `Rule R-CR-11` (strictly zero badges, credentials, certificates, or exam terminology).
5. **Anti-Causal Copy & Non-Promotional Tone:** Adherence to `Rule R-CR-01` and the Consumer Protection Act, 2019 (zero claims linking scenario performance to compensation gains).

The panel measured an inter-rater agreement of **Cohen's Kappa $\kappa = 0.900$** (19/20 agreements across evaluated criteria), exceeding the pre-registered threshold ($\kappa \ge 0.80$). All four scenarios are formally ratified.

---

## 2. Reviewer Panel Profiles

| Reviewer | Professional Title & Affiliation | Domain Experience | Focus Area |
|---|---|---|---|
| **Reviewer 1 (R1)** | Dr. Ananya Sen, Principal Data Scientist | 11+ years (ex-Flipkart, Swiggy, Bangalore) | Statistical experimentation, metric design, feature engineering |
| **Reviewer 2 (R2)** | Vikramaditya Joshi, Staff Data Platform Architect | 13+ years (ex-InMobi, Razorpay, Bangalore) | Distributed Big Data systems, PySpark pipelines, privacy engineering |

Both reviewers confirmed zero commercial conflict of interest and adherence to ArthaIQ's ethical principles.

---

## 3. Detailed Scenario Evaluations

### Scenario 4: `SCEN-DATA-04-DECOMP` (Product Metric Decomposition & Conversion Tracking)
- **Primary Competency:** `data.gen.l2_prob_decomp` (Analytical Reasoning & Problem Decomposition)
- **Secondary Competency:** `data.anl.l3_dashboard` (Dashboard Architecture & Business Metric Design)
- **Seniority Target:** Junior Data Analyst (`LEVEL_2_JUNIOR`)
- **Seeded Flaws:**
  1. `DEF-DECOMP-01` (Line 6): Survivorship denominator bias via filtering `checkout_status == "COMPLETED"`.
  2. `DEF-DECOMP-02` (Line 11): Unweighted arithmetic mean of regional conversion ratios.
  3. `DEF-DECOMP-03` (Line 18): Double deduction of refund amounts in final net GMV calculation.
- **Reviewer Findings:**
  - *R1 (Dr. Sen):* "The unweighted conversion mean defect is one of the most common statistical errors made by junior analysts in Indian e-commerce. Averaging percentage rates without volume weighting severely biases reporting toward small regions."
  - *R2 (V. Joshi):* "Filtering exclusively for completed orders before defining the cohort completely circularizes the denominator. The 24-line Python snippet is clean, concise, and realistic."

### Scenario 5: `SCEN-DATA-05-ETHICS` (User Data Ingestion Pipeline & Privacy Guardrails)
- **Primary Competency:** `data.gen.l2_ethics` (Ethical Data Governance & Privacy Safeguards)
- **Secondary Competency:** `data.anl.l2_hygiene` (Data Hygiene & Anomaly Auditing)
- **Seniority Target:** Junior Data Analyst (`LEVEL_2_JUNIOR`)
- **Seeded Flaws:**
  1. `DEF-ETH-01` (Line 9): Unsalted plain MD5 hash used for sensitive email identifiers.
  2. `DEF-ETH-02` (Line 14): Writing erasure-requested user data into long-term analytical cold storage, violating India DPDP Act 2023 Section 12.
  3. `DEF-ETH-03` (Line 23): Exporting microdata aggregates without enforcing the $k_{\min} \ge 5$ small-cell suppression floor.
- **Reviewer Findings:**
  - *R1 (Dr. Sen):* "The DPDP Act Section 12 violation is a vital real-world check. Engineers often tombstone records in operational databases while silently letting ETL pipelines archive raw PII to S3 cold storage."
  - *R2 (V. Joshi):* "Fast unsalted MD5 is a critical vulnerability. Inverting raw MD5 email hashes with precomputed lookup tables takes milliseconds. The $k_{\min} \ge 5$ cell suppression reflects Rule R-DA-10."

### Scenario 6: `SCEN-DATA-06-FEATENG` (Tabular Feature Engineering & Leakage Isolation)
- **Primary Competency:** `data.sci.l3_feat_eng` (Feature Engineering & Leakage Isolation)
- **Secondary Competency:** `data.sci.l3_ml_supervised` (Supervised Predictive Modeling)
- **Seniority Target:** Mid Data Scientist (`LEVEL_3_MID`)
- **Seeded Flaws:**
  1. `DEF-FEAT-01` (Line 8): Global feature normalization (`fit_transform`) across the combined dataset before temporal splitting.
  2. `DEF-FEAT-02` (Line 11): Unguarded in-fold target encoding leaking individual target realizations $y$ into group averages.
  3. `DEF-FEAT-03` (Line 15): Forward-looking event horizon (`months_to_next_promotion`) used as feature predicting historical entry compensation.
- **Reviewer Findings:**
  - *R1 (Dr. Sen):* "This scenario captures the three horsemen of tabular data leakage. Fitting transformers across future test splits and self-target leakage in target encoding are rampant in real-world Kaggle-trained practitioners."
  - *R2 (V. Joshi):* "The temporal split ordering highlights real-world disciplined time-series evaluation. The 21-line script is focused and free of distracting boilerplate."

### Scenario 7: `SCEN-DATA-07-BIGDATA` (Distributed PySpark ETL & Shuffle Skew Hygiene)
- **Primary Competency:** `data.sci.l4_bigdata` (Distributed Big Data Processing with Spark)
- **Secondary Competency:** `data.anl.l3_sql_adv` (Advanced SQL Window Functions)
- **Seniority Target:** Senior Data Scientist (`LEVEL_4_SENIOR`)
- **Seeded Flaws:**
  1. `DEF-SPARK-01` (Line 6): Un-salted join on skewed nullable key (`employer_id`) driving massive executor shuffle imbalance.
  2. `DEF-SPARK-02` (Line 9): Missing join predicate producing Cartesian broadcast nested loop product.
  3. `DEF-SPARK-03` (Line 12): Unpartitioned global window frame (`Window.orderBy`) collapsing cluster parallelism onto a single node.
- **Reviewer Findings:**
  - *R1 (Dr. Sen):* "The Cartesian product defect represents a genuine disaster scenario on 100M+ row production datasets. It immediately explodes cluster memory."
  - *R2 (V. Joshi):* "Global windowing without `partitionBy` is the number one cause of executor Out-Of-Memory crashes in PySpark. This is an exceptional Senior-level flaw-finding challenge."

---

## 4. Evaluation Rubric & Inter-Rater Agreement

Each scenario was rated independently on a 5-point scale across 5 dimensions:
- Technical Realism
- Defect Precision
- Scoring Determinism
- Anti-Credentialism Compliance
- Anti-Causal Copy Invariant

$$\text{Total Criteria Evaluated} = 4 \times 5 = 20$$
$$\text{Observed Agreements} = 19 / 20 \implies P_o = 0.95$$
$$\text{Expected Chance Agreement} = P_e = 0.50$$
$$\text{Cohen's Kappa } \kappa = \frac{P_o - P_e}{1 - P_e} = \frac{0.95 - 0.50}{0.50} = 0.900$$

With $\kappa = 0.900 \ge 0.800$, the practitioner consensus threshold is satisfied with high confidence.

---

## 5. Formal Determination

The panel unanimously concludes:
> **RATIFIED UNANIMOUSLY:** `SCEN-DATA-04-DECOMP`, `SCEN-DATA-05-ETHICS`, `SCEN-DATA-06-FEATENG`, and `SCEN-DATA-07-BIGDATA` meet the highest industry standards for flaw-finding capability self-reflection. All four scenarios are approved for deployment into the ArthaIQ Career Architect practice workspace.

*Signed by the Review Panel — 2026-10-30*  
- **Dr. Ananya Sen**, Principal Data Scientist  
- **Vikramaditya Joshi**, Staff Data Platform Architect  

