# Research Report 10: Primary Data Acquisition Programme & Architecture

| Metadata | Value |
|---|---|
| **Document ID** | `docs/research/10-data-acquisition-plan.md` |
| **Task Reference** | Task T2.10 (Data Acquisition Plan for Primary Pipeline) |
| **Pre-Registration** | `experiments/preregistration/sufficiency-v1.yaml` (Section 9) |
| **Status** | Ratified Plan / Production Specification |
| **Trigger Event** | Gate G2 Evaluation: **NO-GO on Existing Public Data** (Kill Criterion 1 Triggered) |
| **Primary Source Entity** | `SRC-INT-VOL-01` (ArthaIQ Governed Voluntary Intake) & `SRC-INT-CORP-01` (Enterprise Syndication) |
| **Author** | Antigravity AI Assistant & Engineering Research Team |
| **Date** | 2026-10-14 |
| **Governing Rules** | `R-DA-01` (Zero Scraping), `R-DA-05` (Reconciliation), `R-DA-07` (Zero PII), `R-DA-08` (Gitignore), `R-DA-10` ($k_{\text{min}} \ge 5$), `R-MD-07` (Anti-Heuristic Unbundling) |

---

## Executive Summary

At Gate G2 (Task T2.09), ArthaIQ formally evaluated all approved public and secondary datasets against pre-registered sufficiency criteria (`sufficiency-v1.yaml`). The empirical outcome was unequivocal:
* **0 of 12 Core Cells** met Criterion C1 ($N_{\text{eff}} \ge 50.0$), yielding $N_{\text{eff}} = 0.0$ for strict unbundled guaranteed cash (`guaranteed_cash_annual`).
* **Kill Criterion 1 was Triggered**, mandating an immediate halt to all Phase 3 machine learning modelling (`R-WF-01`).
* **Root Cause:** Audited public datasets either violate third-party Terms of Service via unauthorised scraping (`R-DA-01`), represent aggregated macro/enterprise statistics (`SRC-IND-OFF-01`, `SRC-SUP-CORP-01`), or conflate basic salary, variable performance bonuses, and stock options into an opaque aggregate (`R-MD-07`).

Per the pre-registered protocol, Gate G2 NO-GO directs the project to **Task T2.10**: architecting the **smallest viable primary data acquisition programme**.

This document specifies the end-to-end design, privacy governance, statistical sampling framework, financial model, and operational roadmap for ArthaIQ's proprietary data acquisition pipeline. The programme combines:
1. **A B2C Governed Voluntary Contribution Platform (`SRC-INT-VOL-01`):** Capturing verified, component-level compensation line items via a "give-to-get" value exchange with client-side redacted payslip validation.
2. **A B2B Corporate & Recruitment Partner Data Pool (`SRC-INT-CORP-01`):** Establishing bilateral data-sharing consortiums with vetted employers and recruitment firms.

```
                              ┌────────────────────────────────────────┐
                              │  Gate G2: NO-GO on Public Sources      │
                              │  (0/12 Core Cells; Kill Criterion 1)   │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │      Task T2.10 Acquisition Plan       │
                              └──────────────────┬─────────────────────┘
                                                 │
                    ┌────────────────────────────┴───────────────────────────┐
                    ▼                                                        ▼
   ┌──────────────────────────────────┐                    ┌──────────────────────────────────┐
   │ B2C Governed Voluntary Intake    │                    │ B2B Partner Data Syndication     │
   │ (`SRC-INT-VOL-01`)               │                    │ (`SRC-INT-CORP-01`)              │
   │ - Give-to-Get Value Exchange     │                    │ - Mid-Market Tech & GCC Pooling  │
   │ - Client-Side Redacted Payslips  │                    │ - Standardized Data Sharing Agrmt│
   │ - Component-Level Unbundling     │                    │ - Anonymized Payroll Exports     │
   └────────────────┬─────────────────┘                    └────────────────┬─────────────────┘
                    │                                                        │
                    └────────────────────────────┬───────────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │ Privacy & Governance Core              │
                              │ - DPDPA 2023 Explicit Consent          │
                              │ - Zero Cleartext PII Storage (R-DA-07) │
                              │ - k-Anonymity (k >= 5) & Diff Privacy  │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │ Target: 780+ Core Verified Records     │
                              │ N_eff >= 50 across 12 Core Cells       │
                              │ Re-weighting vs PLFS / BSE Benchmarks  │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │ Gate G2 Re-Evaluation -> Unlock Ph. 3  │
                              └────────────────────────────────────────┘
```

---

## 1. Regulatory, Privacy & Governance Architecture (DPDPA 2023)

Operating a primary salary intake platform in India requires uncompromising adherence to privacy law. Data acquisition under `SRC-INT-VOL-01` and `SRC-INT-CORP-01` is governed by the **Digital Personal Data Protection Act, 2023 (DPDPA 2023)** and international standards (GDPR).

### 1.1 Statutory Compliance Matrix

| DPDPA 2023 Requirement | Statutory Reference | ArthaIQ Implementation Mechanism | Verification Test |
|---|---|---|---|
| **Notice & Specification of Purpose** | Section 5(1) | Standalone, plain-language notice presented before data entry. Clearly specifies that compensation items will be used solely to train aggregate statistical compensation models. | `test_consent_notice_displayed` |
| **Unbundled, Affirmative Consent** | Section 6(1) | Pre-ticked checkboxes strictly prohibited. Consent for benchmark generation is isolated from marketing or account creation. Versioned via `consent_version = "v1.0-202610"`. | `test_consent_checkbox_unticked` |
| **Data Minimisation** | Section 6(7) | Cleartext PII (Employee Name, Email, Phone, PAN, Aadhaar, Bank Details, Street Address, Employer Name) is **never requested, accepted, or stored** (`Rule R-DA-07`). | `test_zero_pii_in_payload` |
| **Right to Withdraw Consent & Erasure** | Section 12(1)(c) | Users can trigger irrevocable erasure of their raw submission at any time via a self-serve cryptographic token. Cascades to primary storage within 72 hours. | `test_cascading_erasure_protocol` |
| **Data Fiduciary Accountability** | Section 8(4) | All processing logic, pseudonymisation salts, and audit trails logged in tamper-evident append-only tables (`R-SC-08`). | `test_tamper_evident_audit_log` |

### 1.2 Cryptographic Identity Separation & Zero-PII Protocol (`R-DA-07`)

To enforce architectural separation of identity and compensation data:
1. **Client-Side Redaction Engine:**
   * Payslip documents uploaded as PDF or image files are processed **entirely client-side** in the user's browser via a WebAssembly-compiled engine (e.g., PDF.js + client-side OCR).
   * Rectangles containing Name, Employee ID, PAN, Bank IFSC/Account, and Provident Fund UAN are blacked out before transmission.
   * Only the numerical component bounding boxes and extracted text tokens leave the user's browser. The original unredacted file never touches ArthaIQ servers.
2. **Cryptographic Pseudonymisation:**
   $$\text{contributor\_key} = \text{HMAC-SHA256}(\text{ServerSecretSalt}, \text{ClientSubmissionID})$$
   * `contributor_key` is a one-way pseudonymous identifier.
   * A separate submission token is given to the contributor for deletion requests without ArthaIQ ever retaining identity linkage.
3. **Database Role Isolation:**
   * The application database role (`app_ingest`) has `INSERT-ONLY` permissions on staged raw submissions and zero read permissions on analytical feature tables.
   * The training feature pipeline role (`pipeline_etl`) reads only sanitized, k-anonymized records.

### 1.3 Small-Cell Privacy & Re-Identification Defense (`R-DA-10`)

* **Enforced $k$-Anonymity Floor:**
  $$k_{\text{min}} = 5 \quad (\text{Count of distinct contributors per cell})$$
  No aggregate statistic (mean, median, IQR, percentiles) will ever be published, displayed, or evaluated if the underlying cell contains fewer than 5 distinct contributors (`Rule R-DA-10`).
* **Differential Privacy ($\epsilon, \delta$):**
  For public API queries and aggregate table exports, Laplace noise calibrated to global sensitivity is injected:
  $$\tilde{M}_{\text{cell}} = M_{\text{cell}} + \text{Laplace}\left(0, \frac{\Delta S}{\epsilon}\right) \quad \text{with } \epsilon = 1.0$$

---

## 2. B2C Governed Voluntary Contribution Platform (`SRC-INT-VOL-01`)

### 2.1 The "Give-to-Get" Value Proposition

Voluntary compensation platforms historically suffer from either low participation or extreme prestige bias. ArthaIQ overcomes this via an asymmetric utility exchange:

> **The Contributor Value Proposition:**
> *"Contribute 2 minutes of verified salary data; receive an institutional-grade Compensation Intelligence Dossier worth ₹15,000 for free."*

Upon completing an itemized submission, the contributor immediately unlocks:
1. **Cohort Distribution Diagnostics:** Exact percentile position within their specific cell (e.g., "72nd percentile for Senior Backend SWE in Bengaluru").
2. **Target Measure Realization Audit:** Mathematical breakdown revealing their true `guaranteed_cash_annual` vs statutory overheads and phantom variable pay.
3. **Tax & Structure Efficiency Score:** Actionable feedback on optimal HRA, NPS, and allowances restructuring under the new and old Indian tax regimes.
4. **Offer Negotiation Benchmark Card:** Exportable PDF summary for use during appraisal or job offer negotiations.

### 2.2 Canonical Component-Level Intake Schema

To eliminate the measurement error and unbundling failures documented in `09-sufficiency-analysis.md` and enforce Rule `R-MD-07`, the intake schema requires itemized accounting:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ARTHAIQ SALARY INTAKE SCHEMA                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 1. OCCUPATION & LOCATION CONTEXT                                                │
│    - Role Family: [ SWE | DATA | MLAI | DEVOPS | PROD ]                        │
│    - Primary Title: Free text (e.g., "Senior Software Engineer")                │
│    - Seniority Band: [ JR (0-2y) | MID (3-7y) | SR (8-14y) | STAFF (15y+) ]     │
│    - Exact Experience: Float years (e.g., 5.5)                                  │
│    - Primary Metro: [ BLR | HYD | NCR | PUN | MUM | CHN | OTHER ]               │
│                                                                                 │
│ 2. FIXED GUARANTEED CASH (Monthly / Annualized) -> Primary Target PT1           │
│    - Basic Salary (Monthly INR): [ ₹ ________ ]                                 │
│    - House Rent Allowance (HRA) (Monthly INR): [ ₹ ________ ]                   │
│    - Special Allowance / Fixed Allowances (Monthly INR): [ ₹ ________ ]         │
│    ──> COMPUTED GUARANTEED CASH: 12 x (Basic + HRA + Special) LPA               │
│                                                                                 │
│ 3. STATUTORY EMPLOYER OVERHEADS (Isolated from PT1 per R-MD-07)                 │
│    - Employer EPF Contribution (12% of basic or statutory cap): [ ₹ ________ ] │
│    - Gratuity Provision (Annual accrual ~4.81% of basic): [ ₹ ________ ]       │
│                                                                                 │
│ 4. PERFORMANCE & VARIABLE CASH (Auxiliary Target PT2)                           │
│    - Target Annual Performance Bonus (INR): [ ₹ ________ ]                      │
│    - Actual Bonus Realized in Preceding 12 Months (INR): [ ₹ ________ ]         │
│                                                                                 │
│ 5. LONG-TERM INCENTIVES & EQUITY (Auxiliary Target PT6)                         │
│    - Grant Type: [ None | ESOPs | RSUs | Phantom Units ]                        │
│    - Annualized Vesting Nominal Value (INR): [ ₹ ________ ]                     │
│                                                                                 │
│ 6. HEADLINE CTC (For Verification & Reconciliation Cross-Check)                 │
│    - Total Cost to Company stated in Offer/Appraisal Letter: [ ₹ ________ ]     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Exact Accounting Reconciliation Equation (`R-DA-05`)

Every submission must balance the canonical accounting identity within a $\pm 2.0\%$ reconciliation margin:

$$\text{Reported CTC} \equiv \mathbf{PT1\ (Guaranteed\ Cash)} + \text{Employer Statutory Overheads} + \text{Target Variable Bonus} + \text{Annual Equity Vest}$$

If an unbalance exceeds 2.0%, the client-side UI prompts the contributor to resolve the discrepancy (e.g., unstated insurance premiums, retention bonuses) before submission is accepted.

### 2.4 Multi-Tier Verification Hierarchy

To quantify credibility and compute Kish design effects accurately, submissions are classified into three explicit quality tiers:

| Tier | Name | Verification Proof | Source Weight ($w_i$) | Assigned SQS | Target Pipeline Routing |
|---|---|---|---|---|---|
| **Tier 1** | **Document-Verified** | Redacted Payslip (PDF/Image) or Form 16 Part B uploaded and matched to entered line items via automated OCR validator. | $1.00$ | **96.0** | Direct PT1–PT6 Training |
| **Tier 2** | **Work-Email Verified** | Verification link clicked from corporate tech domain (`@company.com`). Identity decoupled immediately upon verification. | $0.80$ | **82.0** | Direct PT1–PT6 Training |
| **Tier 3** | **Unverified Contributor** | Anonymous web entry without email or document proof. Subject to strict statistical outlier filters. | $0.35$ | **55.0** | Exploratory Benchmark Only |

---

## 3. B2B Corporate & Recruitment Partner Syndication (`SRC-INT-CORP-01`)

While B2C voluntary intake provides granular worker-side truth, B2B data syndication delivers high-volume cohort density across core tech hubs.

### 3.1 The Mid-Market Employer Incentive

India tech startups, mid-market SaaS companies (Series A–C), and Global Capability Centers (GCCs) face severe compensation benchmarking challenges:
* Tier-1 compensation consultants (Aon, Mercer) charge ₹15L–₹35L per annual report, delivering static, 6-month-stale PDF tables.
* Big tech scrapers (Levels.fyi, AmbitionBox) suffer from uncontrolled self-selection skew and zero measure unbundling.

**The ArthaIQ Data Pooling Model:**
* Employers contribute anonymized, standardized payroll dumps (Job Role, Seniority, Exact Basic, Fixed Allowances, Bonus, Equity).
* In return, contributing employers receive continuous, real-time access to cohort percentiles and market competitiveness indices for their active job families.

### 3.2 Data Sharing Agreement (DSA) & Legal Boundaries

1. **Reciprocal Anonymity:** Partner employee payroll records are scrubbed of all employee identifiers before transfer.
2. **Anti-Poaching Guarantee:** ArthaIQ contractually guarantees that no individual employer's compensation data will ever be identifiable by competitors, and data cannot be queried to target specific company employees.
3. **Audit Rights:** Standardized Data Sharing Agreements contain provisions allowing third-party compliance verification.

---

## 4. Sampling Model, Sample Size Targets & Bias Correction

### 4.1 Sample Size Calculation to Satisfy Pre-Registered Sufficiency

To satisfy Criterion C1 ($N_{\text{eff}} \ge 50.0$) across all 12 core cells and achieve stable bootstrap interval half-widths ($\le 3.0$ LPA per Criterion C5):

$$N_{\text{eff}} = \frac{\left(\sum_{i=1}^n w_i\right)^2}{\sum_{i=1}^n w_i^2} \ge 50.0$$

Assuming an empirical distribution of contributions across verification tiers (40% Tier 1 @ $w=1.0$, 40% Tier 2 @ $w=0.8$, 20% Tier 3 @ $w=0.35$):
$$\bar{w} = 0.4(1.0) + 0.4(0.8) + 0.2(0.35) = 0.40 + 0.32 + 0.07 = 0.79$$
$$\overline{w^2} = 0.4(1.0) + 0.4(0.64) + 0.2(0.1225) = 0.40 + 0.256 + 0.0245 = 0.6805$$
$$\text{Deff} = \frac{\overline{w^2}}{\bar{w}^2} = \frac{0.6805}{0.79^2} = \frac{0.6805}{0.6241} \approx 1.09$$

To achieve $N_{\text{eff}} \ge 50.0$ with a design effect of $1.09$:
$$N_{\text{raw\_per\_cell}} \ge 50 \times 1.09 \approx 55 \implies \text{Target: } \mathbf{65\ \text{contributions per core cell}}$$

### 4.2 Comprehensive Target Sampling Matrix

| Cell Category | Cell Count | Target $N_{\text{raw}}$ per Cell | Target $N_{\text{eff}}$ per Cell | Total Category Sample Goal | Target C1 Status |
|---|---|---|---|---|---|
| **Core Cells (Level-0 Priority)** | 12 | 65 | $\ge 50.0$ | **780** | **PASS (12/12)** |
| **Extended High-Demand Cells** | 24 | 25 | $\ge 20.0$ | **600** | **PASS (C2: 36/84 $\ge 42.8\%$)** |
| **Long-Tail Extended Cells** | 48 | 10 | $\ge 8.0$ | **480** | Guarded Support |
| **TOTALS** | **84** | — | — | **1,860 verified records** | **Full Gate G2 GO** |

#### Target Allocation for 12 Core Cells

| Cell ID | Role Family | Metro | Seniority Band | Target Verified Records | Target $N_{\text{eff}}$ |
|---|---|---|---|---|---|
| `SWE.BLR.JR` | Software Engineering | Bengaluru | Junior (0–2y) | 65 | $\ge 50.0$ |
| `SWE.BLR.MID` | Software Engineering | Bengaluru | Mid-Level (3–7y) | 65 | $\ge 50.0$ |
| `SWE.BLR.SR` | Software Engineering | Bengaluru | Senior (8–14y) | 65 | $\ge 50.0$ |
| `SWE.HYD.MID` | Software Engineering | Hyderabad | Mid-Level (3–7y) | 65 | $\ge 50.0$ |
| `SWE.HYD.SR` | Software Engineering | Hyderabad | Senior (8–14y) | 65 | $\ge 50.0$ |
| `SWE.NCR.MID` | Software Engineering | Delhi-NCR | Mid-Level (3–7y) | 65 | $\ge 50.0$ |
| `SWE.NCR.SR` | Software Engineering | Delhi-NCR | Senior (8–14y) | 65 | $\ge 50.0$ |
| `DATA.BLR.MID` | Data Analysis / Eng | Bengaluru | Mid-Level (3–7y) | 65 | $\ge 50.0$ |
| `DATA.BLR.SR` | Data Analysis / Eng | Bengaluru | Senior (8–14y) | 65 | $\ge 50.0$ |
| `MLAI.BLR.SR` | Machine Learning / AI | Bengaluru | Senior (8–14y) | 65 | $\ge 50.0$ |
| `MLAI.HYD.SR` | Machine Learning / AI | Hyderabad | Senior (8–14y) | 65 | $\ge 50.0$ |
| `MLAI.NCR.SR` | Machine Learning / AI | Delhi-NCR | Senior (8–14y) | 65 | $\ge 50.0$ |
| **Sum Core** | — | — | — | **780** | **$\ge 600.0$** |

### 4.3 Post-Stratification & Selection Bias Re-Weighting

As documented in `05-source-scoring.md` and `SRC-INT-VOL-01.md`, voluntary intake over-represents high-earning engineers from venture-funded startups and Tier-1 product MNCs.

To correct this selection bias without distorting underlying pay distributions:
1. **Stratification Variables:** Employer Tier (Tier 1 Product MNC / GCC vs Tier 2 Domestic Product vs Tier 3 IT Services), Metro Location, and Seniority Band.
2. **Benchmark Marginal Calibration:**
   * IT Services proportion is calibrated to audited BSE/NSE IT corporate census counts (`SRC-SUP-CORP-01`), ensuring services engineers represent at least 55% of the effective weight in `SWE` cells.
   * Macro distribution tails are constrained by MOSPI PLFS Schedule 10.4 urban tech wage medians (`SRC-IND-OFF-01`).
3. **Calibration Weight Formulation:**
   $$W_{ijk} = w_i \times \frac{P_{\text{population}}(j, k)}{P_{\text{sample}}(j, k)}$$
   where $P_{\text{population}}$ is derived from official macro statistics and corporate filings.

---

## 5. Financial Budget & Unit Economics

The programme is designed for maximum capital efficiency by leveraging digital product value ("Give-to-Get") rather than paying unsustainable cash bounties per record.

### 5.1 Three-Month Line-Item Budget

| Budget Category | Description & Deliverables | Cost (INR) | Cost (USD Approx) |
|---|---|---|---|
| **Legal Counsel & Privacy Retainer** | Retention of Indian qualified privacy counsel to draft DPDPA 2023 compliant Terms of Service, consent notice templates, and B2B Data Sharing Agreements (ADR-0008 ratification). | ₹3,50,000 | $4,200 |
| **Intake UI & Verification Microservice** | Development of WebAssembly client-side payslip redaction tool, parsing engine, and cryptographic HMAC pipeline (`SRC-INT-VOL-01`). | ₹2,50,000 | $3,000 |
| **Developer Community Distribution** | Sponsored technical deep-dives, developer newsletters, targeted engineering community partnerships (Bangalore Tech Meetups, PyData India, GopherCon India). | ₹5,50,000 | $6,600 |
| **B2B Employer Pilot Outreach** | Dedicated B2B enterprise acquisition lead to sign 6–10 mid-market startup / GCC data pooling partnerships (`SRC-INT-CORP-01`). | ₹3,00,000 | $3,600 |
| **Cloud Infrastructure & Security Audit** | AWS/GCP isolated hosting, KMS key management for HMAC salts, vulnerability assessment & penetration testing (VAPT). | ₹2,00,000 | $2,400 |
| **Operational Contingency (10%)** | Unforeseen legal or promotional requirements. | ₹2,00,000 | $2,400 |
| **TOTAL PROGRAMME BUDGET** | **Smallest Viable Data Acquisition Programme** | **₹18,50,000** | **$22,200** |

### 5.2 Unit Economics

* **Target Verified Acquisitions:** 1,860 total records (780 core records).
* **Blended Cost per Verified Record:**
  $$\text{Blended Cost} = \frac{₹18,50,000}{1,860} \approx \mathbf{₹995\ (\approx \$12.00\ \text{USD})\ \text{per verified record}}$$
* In contrast, commercial enterprise compensation surveys (e.g., Radford / Aon) cost upwards of ₹2,500 per data point while lacking transparent unbundling methodology.

---

## 6. Phased Implementation Schedule & Milestones

The data acquisition plan is executed across three sequential phases over 12 weeks:

```
Week  1   2   3   4   5   6   7   8   9  10  11  12
      ├───Phase A───┤
                    ├───Phase B───┤
                                  ├───Phase C───┤
```

### Phase A: Foundation, Legal Ratification & Closed Alpha (Weeks 1–4)
* **Milestone A.1 (Week 2):** Retain legal counsel; complete formal DPDPA 2023 compliance review; ratify ADR-0008.
* **Milestone A.2 (Week 3):** Deploy client-side redaction tool and intake schema at `https://arthaiq.internal/intake`.
* **Milestone A.3 (Week 4):** Conduct Closed Alpha with 100 trusted technology professionals across Bengaluru and Hyderabad. Verify OCR parser accuracy ($\ge 95\%$) and zero-discrepancy reconciliation (`R-DA-05`).

### Phase B: Public B2C Beta Launch & Developer Marketing (Weeks 5–8)
* **Milestone B.1 (Week 5):** Launch public Give-to-Get benchmark dossier generator.
* **Milestone B.2 (Week 6):** Initiate engineering community distribution campaigns.
* **Milestone B.3 (Week 8):** Reach 1,000 cumulative submissions, including $\ge 400$ verified records across the 12 core cells.

### Phase C: B2B Syndication, Post-Stratification & Gate G2 Re-Audit (Weeks 9–12)
* **Milestone C.1 (Week 10):** Ingest first batch of B2B partner data pooling exports (`SRC-INT-CORP-01`) from at least 5 partner companies.
* **Milestone C.2 (Week 11):** Run automated post-stratification re-weighting pipeline against PLFS and BSE/NSE anchors.
* **Milestone C.3 (Week 12):** Execute pre-registered sufficiency audit (`make sufficiency`). If 12/12 core cells meet C1 ($N_{\text{eff}} \ge 50.0$), formally ratify **Gate G2 GO** and unfreeze Phase 3 Machine Learning development.

---

## 7. Contingency Plans, Scope Narrowing & Exit Criteria

In strict accordance with Rule `R-WF-08` and `sufficiency-v1.yaml` Kill Criteria, clear failure boundaries are pre-registered:

```
                             [ Week 8 Progress Check ]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │                                           │
          Core Records >= 400                         Core Records < 400
                   │                                           │
                   ▼                                           ▼
          [ Proceed to Phase C ]                      [ Trigger Mitigation ]
                   │                                  - Intensify B2B GCC outreach
                   │                                  - Add referral dossier unlocks
                   │                                           │
                   │                             [ Week 12 Final Evaluation ]
                   │                                           │
                   │                        ┌──────────────────┴──────────────────┐
                   │                        │                                     │
                   │             >= 4 Core Cells Pass C1               < 4 Core Cells Pass C1
                   │                        │                                     │
                   ▼                        ▼                                     ▼
          [ Gate G2 Full GO ]   [ Contingency Narrowing ]             [ Hard Project Sunset ]
          - Unlock Phase 3 ML   - Re-scope to Bengaluru SWE only      - Terminate ML modelling
          - All 12 Core Cells   - Update ADR-0001; Amend PRD          - Publish Open Data Report
```

### 7.1 Scope Narrowing Trigger (Contingency Option 1)
* **Trigger Condition:** At Week 12, overall core cell acquisition reaches $\ge 4$ core cells passing C1, but fails all 12 (e.g., Bengaluru SWE cells reach $N_{\text{eff}} \ge 50$, but MLAI in NCR or Hyderabad fails).
* **Pre-Registered Action:** Amend ADR-0001 and PRD v1.0 to narrow operational scope to:
  $$\mathbf{H_{\text{narrowed}}:\ \text{Software Engineering Professionals in Bengaluru Metro Only}}$$
  Phase 3 modelling proceeds exclusively on verified Bengaluru SWE cells.

### 7.2 Hard Project Sunset Trigger (Kill Criterion 1 Follow-Through)
* **Trigger Condition:** At Week 12, despite expenditure of the ₹18.5L budget, fewer than 4 core cells achieve $N_{\text{eff}} \ge 50.0$.
* **Pre-Registered Action:**
  1. The project does **NOT** relax sufficiency criteria, apply synthetic multipliers, or use scraped datasets (`R-MD-07`, `R-DA-01`, `R-WF-01`).
  2. The commercial machine learning prediction initiative is formally paused.
  3. All acquired, verified data is compiled into an open, aggregate compensation whitepaper ("The State of Indian Software Engineering Compensation: A Verified Component-Level Audit").
  4. This guarantees that ArthaIQ never ships unscientific or deceptive salary models to Indian engineers.

---

## 8. Summary of Pre-Registered Artifacts & Invariants

| Invariant / Artifact | Contractual Status |
|---|---|
| **Intake Schema** | Itemized unbundling mandated (`guaranteed_cash_annual` isolated from bonuses, statutory EPF/gratuity, and equity). |
| **Privacy Compliance** | DPDPA 2023 notice, unbundled consent, zero cleartext PII, $k_{\text{min}} = 5$ small-cell suppression. |
| **Verification Gate** | Document-verified ($w=1.0$) and work-email-verified ($w=0.8$) records required to meet $N_{\text{eff}} \ge 50.0$. |
| **Post-Stratification** | Weights calibrated against MOSPI PLFS (`SRC-IND-OFF-01`) and corporate median disclosures (`SRC-SUP-CORP-01`). |
| **Next Task** | **Task T2.11** (Finalize ADR-0001, ADR-0002; Update PRD to v1.0 reflecting Gate G2 decisions). |
