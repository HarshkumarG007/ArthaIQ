# Canonical Compensation Definitions & Measurement Mapping (T1.02)

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/02-comp-definitions.md` |
| **Task** | T1.02 — Define compensation terms and map them |
| **Status** | Complete v1.0 |
| **Date** | 2026-10-13 |
| **Governs** | Ingestion Normalization (`src/compintel/ingestion/`), Source Mapping (`config/sources.yaml`), Target Contracts (`01-targets.md`), Data Cards (`docs/data-cards/`) |
| **Core Invariant** | A compensation label alone does not establish what is measured. Different pay components must never be silently aggregated or guessed via hard-coded percentage multipliers (`R-MD-07`). Unreconciled figures must be quarantined or mapped to distinct targets. |

---

## 1. Executive Summary & Problem Formulation

In Indian and international labor markets, the term "salary" is notoriously overloaded. Employers, recruiters, and survey platforms use conflicting definitions that diverge by 30% to 150%:
* An Indian offer letter displaying a headline **Cost to Company (CTC)** of ₹26.0 Lakhs Per Annum (LPA) often provides only **₹18.0 LPA in guaranteed pre-tax cash**, with the remainder composed of contingent performance bonuses (₹3.0 LPA), employer statutory provident fund & gratuity provisions (₹1.0 LPA), and multi-year paper stock options (₹4.0 LPA).
* Job boards (such as Naukri or Indeed) advertise recruiter budget ranges that exclude equity and bonuses altogether.
* Crowdsourced portals frequently capture self-reported total compensation, take-home pay, or unverified headline CTCs.

If ArthaIQ combines these heterogeneous quantities into a single training target, the model will output confidently distorted distributions.

This document establishes the **formal accounting contract and canonical compensation vocabulary** for ArthaIQ. Every incoming data field must map to a single canonical `measure_id` or be explicitly marked `non-comparable` and quarantined.

---

## 2. Canonical Compensation Glossary

The table below defines each compensation concept, its contractual status, and its relationship to ArthaIQ's principal prediction target **PT1 (`guaranteed_cash_annual`)**:

| Compensation Term | Formal Accounting Definition | Contractual Status | PT1 Status | Canonical Measure ID |
|:---|:---|:---|:---|:---|
| **Base Salary (Basic Pay)** | The core contractual fixed pay component upon which statutory benefits (PF, gratuity) and certain allowances are calculated. In India, typically 30%–50% of fixed pay. | Guaranteed | Admitted (Component) | `basic_salary_annual` |
| **Fixed Allowances** | Contractually committed, non-contingent monthly cash allowances paid alongside Basic Pay (e.g., House Rent Allowance [HRA], Special Allowance, Conveyance Allowance). | Guaranteed | Admitted (Component) | `fixed_allowances_annual` |
| **Guaranteed Annual Cash** | The total annualized cash compensation that the employer is contractually obligated to pay for standard service, conditional only on continued employment and free of performance contingencies. Sum of Basic Pay + Fixed Allowances. | Guaranteed | **PRIMARY TARGET (PT1)** | `guaranteed_cash_annual` |
| **Variable Cash (Performance Bonus)** | Contingent cash compensation paid periodically based on individual, business unit, or company performance metrics. May have a target amount (e.g., 10% of base) and an actual realized payout. | Contingent / Conditional | **EXCLUDED** from PT1 | `variable_cash_annual` |
| **Joining / Sign-on Bonus** | One-time cash payment granted upon commencement of employment, often subject to a 12-to-24-month clawback agreement. | One-time / Contingent | **EXCLUDED** from PT1 recurring cash | `signon_bonus_cash` |
| **Cost to Company (CTC)** | The employer's total budgeted annual expense for employing an individual. Typically bundles: Basic + Fixed Allowances + Employer EPF (12%) + Gratuity (4.81%) + Target Bonus + Annualized Equity Grant Value. | Employer Budget Aggregate | **NON-COMPARABLE** (Requires line-item unbundling) | `ctc_annual` |
| **Take-Home (In-Hand) Pay** | Net cash deposited into the employee's bank account after deducting employee EPF contribution (12%), Professional Tax, and Tax Deducted at Source (TDS). | Realized Net Post-Tax | **NON-COMPARABLE** (Post-tax personal rate) | `take_home_annual` |
| **Total Compensation (TC)** | Realized gross annual economic value received by the worker, including guaranteed cash, realized bonuses, and vested liquid equity. | Realized Annual Total | Excluded from PT1; Admitted for PT6 benchmark | `total_comp_annual` |
| **Equity Compensation (RSUs / ESOPs)** | Ownership interest granted as restricted stock units (RSUs), stock options (ESOPs), or phantom equity. Subject to vesting schedules, strike prices, and liquidity constraints. | Non-cash / Volatile | **EXCLUDED** from PT1 | `equity_annualized_grant` / `equity_realized_vested` |
| **Employer Statutory Contributions** | Statutory payroll provisions borne by the employer: Employer Provident Fund (EPF), Employee State Insurance (ESI), and Gratuity provision under the Payment of Gratuity Act, 1972. | Statutory Overhead | **EXCLUDED** from PT1 | `employer_contributions_annual` |

---

## 3. Canonical Measure Mapping Matrix

Every incoming source column across our data catalog (Kaggle fixtures, PLFS microdata, voluntary contributions, job postings) must resolve to one row in this table:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               CANONICAL MEASURE HIERARCHY                              │
│                                                                                        │
│  [PT1] guaranteed_cash_annual ◄── basic_salary_annual + fixed_allowances_annual       │
│                                                                                        │
│  [PT3] advertised_range_annual ◄── advertised_min_annual, advertised_max_annual        │
│                                                                                        │
│  [PT6] total_comp_annual ◄── guaranteed_cash_annual + variable_cash + equity_realized  │
│                                                                                        │
│  [NON-COMPARABLE / ISOLATED]                                                           │
│  • ctc_annual (Requires line-item decomposition)                                       │
│  • take_home_annual (Conflates tax brackets and deductions)                            │
│  • binned_range_annual (Coarse survey brackets)                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

| Canonical Measure ID | Target Compatibility | Unit / Denomination | Ingestion Validation Rule | Typical Source Instances |
|:---|:---|:---|:---|:---|
| `guaranteed_cash_annual` | **PT1, PT2** | Nominal INR LPA | Value $> 0$, must exclude employer PF, gratuity, bonus, equity | Redacted Indian payslips, voluntary intake line items |
| `basic_salary_annual` | Component | Nominal INR LPA | Value $> 0$, must be $\le \text{guaranteed\_cash}$ | Payroll records, statutory declarations |
| `fixed_allowances_annual` | Component | Nominal INR LPA | Sum of non-basic cash allowances | HRA, Special Allowance, Transport Allowance |
| `ctc_annual` | **Non-Comparable** | Nominal INR LPA | Unbundled aggregate. **Never admit to PT1** without itemization | Indian offer letters, AmbitionBox scrapes |
| `advertised_min_annual` | **PT3** | Nominal INR LPA | Advertised hiring floor from job opening | Naukri postings, LinkedIn listings |
| `advertised_max_annual` | **PT3** | Nominal INR LPA | Advertised hiring ceiling from job opening | Naukri postings, LinkedIn listings |
| `take_home_annual` | **Non-Comparable** | Nominal INR LPA | Post-tax net earnings. **Never reverse-engineer to gross** | Employee forum claims, salary slips |
| `variable_cash_annual` | PT6 / Auxiliary | Nominal INR LPA | Performance bonus, commission, incentives | Employer bonus statements, Stack Overflow survey |
| `equity_annualized_grant` | PT6 / Auxiliary | Nominal INR LPA | Total grant value divided by vesting period (years) | US tech offer letters, Levels.fyi disclosures |
| `total_comp_annual` | **PT6 / Benchmark** | Nominal INR LPA | Full cash + realized equity aggregate | Stack Overflow `CompTotal`, Levels.fyi |
| `binned_range_annual` | Benchmark Only | Ordinal Bracket | Coarse survey bin (e.g., $10k–$15k) | Kaggle Annual ML/DS Survey |

---

## 4. Indian CTC Unbundling Accounting Contract

### 4.1 The Full CTC Equation
In the Indian private technology sector, an employer's stated Cost to Company (CTC) is computed as follows:

$$\text{CTC} = \underbrace{\text{Basic} + \text{HRA} + \text{Special Allowance} + \text{Other Fixed Cash}}_{\mathbf{guaranteed\_cash\_annual}\ (G)} + \underbrace{\text{Employer PF} + \text{Gratuity Provision}}_{\text{Employer Statutory Provisions}\ (S)} + \underbrace{\text{Performance Bonus}}_{\text{Variable Cash}\ (V)} + \underbrace{\text{Annualized Equity}}_{\text{Equity Grant}\ (E)}$$

Where:
1. **Basic Pay:** Base contractual rate.
2. **House Rent Allowance (HRA):** Typically 40%–50% of Basic Pay (tax-exempt under Sec 10(13A) subject to rent receipts).
3. **Special Allowance:** Fully taxable flexible balancing allowance; guaranteed monthly cash.
4. **Employer Provident Fund (EPF):** Under the Employees' Provident Funds and Miscellaneous Provisions Act, 1952, employer contributes 12% of Basic Pay (either capped at ₹1,800/month or uncapped 12% of full Basic). This is an employer cost, **not** take-home or cash in the employee's control.
5. **Gratuity Provision:** Under the Payment of Gratuity Act, 1972, employer accrues an accounting provision of approximately:
   $$\text{Gratuity Accrual} = \frac{15}{26} \times \frac{\text{Basic}}{12} \approx 4.81\% \text{ of Basic Pay}$$
   Payable only upon completion of 5 continuous years of service. It is an actuarial reserve, **never** guaranteed annual cash.
6. **Variable / Performance Pay:** Paid annually/quarterly based on company and individual multiplier.
7. **Joining Bonus:** Often clawed back if employee leaves before 12 or 24 months.

### 4.2 Mathematical Transformation Rule: The Admissibility Gate
$$\mathbf{guaranteed\_cash\_annual} = \text{Basic} + \text{HRA} + \text{Special Allowance} + \text{Conveyance} + \text{LTA/Medical Fixed}$$

$$\text{CTC} - \mathbf{guaranteed\_cash\_annual} = \text{Employer PF} + \text{Gratuity} + \text{Variable Bonus} + \text{Equity}$$

### 4.3 The Strict Anti-Heuristic Rule (`R-MD-07`)
> [!CRITICAL]
> **RULE R-MD-07 ENFORCEMENT:** If an external dataset reports only `CTC = ₹24 LPA` without line-item component breakdowns, **ArthaIQ is strictly prohibited from guessing or subtracting a standard percentage (e.g. subtracting 15% or multiplying by 0.85).** 
> 
> *Rationale:* The ratio of guaranteed cash to total CTC varies from 60% (early-stage startups with heavy ESOPs or product MNCs with heavy variable components) to 92% (IT services firms with minimal bonus and statutory PF caps). Applying a uniform multiplier induces synthetic heteroskedastic distortion and violates empirical integrity.
> 
> *Action:* Unreconciled CTC observations must be flagged as `measure_id: ctc_annual` and **quarantined from PT1 training sets**.

---

## 5. United States Compensation Mapping & Cross-Market Rules

While ArthaIQ's initial scope is India-first (`H0`), our schema must support cross-market comparability and international benchmarks without semantic leakage.

### 5.1 US Compensation Terminology
In the US technology ecosystem, compensation is structured under the **Total Target Cash (TTC)** and **Total Direct Compensation (TDC)** paradigms:
1. **Base Salary:** Fixed annual gross cash salary paid semi-monthly or bi-weekly. Direct analogue to `guaranteed_cash_annual`.
2. **Short-Term Incentive (STI / Annual Bonus):** Target bonus percentage (e.g., 15% of base) based on company performance. Equivalent to `variable_cash_annual`.
3. **Long-Term Incentive (LTI / RSUs):** Multi-year equity grant, typically vesting over 4 years with a 1-year cliff (25% year 1, monthly/quarterly thereafter).
4. **Sign-on Bonus:** Upfront cash incentive, often split over year 1 and year 2 with clawback.
5. **Benefits & 401(k) Match:** Employer contribution match (e.g., 50% match up to 6% of salary) and health/dental coverage. Equivalent to employer overhead.

### 5.2 Regulatory & Tax Forms
* **Form W-2 Box 1 (Wages, tips, other comp):** Gross cash taxable pay plus the value of equity that *vested* during that tax year, *minus* pre-tax 401(k) and health deductions. Conflates realized equity with cash; cannot be used as Base Salary.
* **Form W-2 Box 5 (Medicare wages):** Gross earnings subject to Medicare, capturing pre-tax retirement contributions.
* **Offer Letter Base Pay:** The contractual equivalent of `guaranteed_cash_annual`.

### 5.3 Cross-Market Comparability Policy
1. **No Direct Currency Conversion:** US compensation figures denominated in USD must **never** be multiplied by nominal exchange rates (e.g. ₹83 / USD) and pooled into Indian INR datasets. Doing so conflates local purchasing power and employer talent markets.
2. **Market Isolation:** US observations must remain strictly tagged with `country: US` and `currency: USD`, routing only to secondary global benchmarking models (such as `ai-jobs.net` exploratory baselines).

---

## 6. Period, Currency, and Tax Normalization Conventions

All data admitted into ArthaIQ pipelines must follow deterministic normalization contracts:

### 6.1 Pay Period Normalization
All compensation is standardized to an **annualized basis**:
* **Annual (`period: annual`):** $Y_{\text{annual}} = Y_{\text{raw}}$
* **Monthly (`period: monthly`):** $Y_{\text{annual}} = Y_{\text{raw}} \times 12.0$
* **Bi-Weekly (`period: biweekly`):** $Y_{\text{annual}} = Y_{\text{raw}} \times 26.0$
* **Hourly (`period: hourly`):** $Y_{\text{annual}} = Y_{\text{raw}} \times 2,080.0$ (standard 40 hours/week $\times$ 52 weeks, for full-time only).
* **Unknown Period (`period: unknown`):** **QUARANTINE**. Never guess pay frequency from magnitude.

### 6.2 Denomination & Unit Standard
For the Indian tech market, ArthaIQ standardizes all reporting and modeling to **INR Lakhs Per Annum (LPA)**:
$$1.0\ \text{LPA} = 100,000\ \text{INR}$$
$$\text{Value in LPA} = \frac{\text{Value in INR}}{100,000}$$

*Example:* ₹1,850,000 annual cash $\rightarrow$ `18.5 LPA`.

### 6.3 Tax Basis Convention
All salary targets in ArthaIQ represent **Gross Pre-Tax Compensation** before personal income tax (Old Regime or New Regime under the Indian Income Tax Act, 1961).
* **Take-home pay** (net cash deposited) depends on individual deductions (Section 80C, 80D, HRA exemptions, regime selection) and cannot be mapped to gross pay without unobserved personal tax parameters.
* Datasets reporting take-home pay without gross payroll slips must remain isolated as `take_home_annual` and excluded from PT1.

### 6.4 Temporal Convention: Nominal vs Real
* **Training & Output:** Denominated in **nominal INR** at observation timestamp $t_{\text{obs}}$.
* **Deflation Policy:** If an observation has an age $> 90$ days from prediction date $t_0$, the ingestion engine applies the urban CPI or technology sector wage adjustment index before model conditioning.

---

## 7. Prediction Target Compatibility Matrix (PT1 – PT6)

The table below governs data routing across ArthaIQ's six prediction targets:

| Target ID | Target Name | Primary Admissible Measure | Admissible Line Items | Disqualified Measures |
|:---|:---|:---|:---|:---|
| **PT1** | Market Comp for Profile | `guaranteed_cash_annual` | Basic + HRA + Special Allowance + Fixed Cash | CTC, Variable Bonus, Equity, Take-home, Advertised Range |
| **PT2** | Comparable Cohort Range | `guaranteed_cash_annual` | Basic + HRA + Special Allowance + Fixed Cash | CTC, Variable Bonus, Equity, Take-home |
| **PT3** | Plausible Offer Distribution | `advertised_range_annual` | `advertised_min_annual`, `advertised_max_annual` | Settled employee payroll cash (PT1) |
| **PT4** | Negotiation Counterfactual | `guaranteed_cash_annual` + `signon_bonus_cash` | Fixed cash + joining bonus scenario | Unbundled CTC |
| **PT5** | Career Transition Scenarios | `guaranteed_cash_annual` | Longitudinal fixed cash records | Cross-sectional unverified claims |
| **PT6** | Current Pay Benchmark | `guaranteed_cash_annual` & `total_comp_annual` | User's verified fixed cash or total cash | Synthetic data |

---

## 8. Executable Test Suite Specifications (T1.02-TEST-01 to 08)

To ensure this contract is programmatic and verifiable during Phase 3 pipeline implementation, the following unit and property tests are preregistered:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              T1.02 VERIFICATION TEST SUITE                             │
│                                                                                        │
│  T1.02-TEST-01: Contractual Guaranteed Cash      ──► PASS (Mapped to PT1)              │
│  T1.02-TEST-02: Bundled CTC Headline             ──► REJECT / QUARANTINE from PT1      │
│  T1.02-TEST-03: Known Monthly Salary             ──► PASS (Annualized * 12)            │
│  T1.02-TEST-04: Missing / Unknown Currency       ──► QUARANTINE (No guessing)          │
│  T1.02-TEST-05: Unreconciled Performance Bonus   ──► EXCLUDE from guaranteed cash      │
│  T1.02-TEST-06: Equity-Inclusive Total Comp      ──► ROUTE to PT6 / Benchmark only     │
│  T1.02-TEST-07: Conflicting Measure Labels       ──► QUARANTINE as ambiguous           │
│  T1.02-TEST-08: Net Take-Home Without Tax Slip   ──► PRESERVE isolated (No tax guess)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Test Case Definitions:

#### T1.02-TEST-01: Contractual Guaranteed Cash
* **Input Record:** `{"basic": 1200000, "hra": 600000, "special_allowance": 400000, "period": "annual", "currency": "INR"}`
* **Expected Result:** Status `APPROVED`. `measure_id: guaranteed_cash_annual`, value = `22.0 LPA`. Admitted to PT1.

#### T1.02-TEST-02: Bundled CTC Headline
* **Input Record:** `{"ctc_headline": 2600000, "period": "annual", "currency": "INR", "components": null}`
* **Expected Result:** Status `QUARANTINED_FOR_PT1`. `measure_id: ctc_annual`, value = `26.0 LPA`. Disqualified from PT1 training.

#### T1.02-TEST-03: Monthly Salary Annualization
* **Input Record:** `{"monthly_fixed_cash": 150000, "period": "monthly", "currency": "INR"}`
* **Expected Result:** Status `APPROVED`. `measure_id: guaranteed_cash_annual`, normalized value = `18.0 LPA` ($150,000 \times 12 / 100,000$).

#### T1.02-TEST-04: Unknown Currency Quarantine
* **Input Record:** `{"amount": 1200000, "currency": null, "period": "annual"}`
* **Expected Result:** Status `QUARANTINED`. Error code `ERR_MISSING_CURRENCY`. No conversion heuristic applied.

#### T1.02-TEST-05: Performance Bonus Isolation
* **Input Record:** `{"basic": 1000000, "fixed_allowances": 500000, "performance_bonus_target": 300000, "currency": "INR"}`
* **Expected Result:** Status `APPROVED`. `guaranteed_cash_annual = 15.0 LPA`. `variable_cash_annual = 3.0 LPA`. Only `15.0 LPA` routed to PT1.

#### T1.02-TEST-06: Equity-Inclusive Total Compensation Routing
* **Input Record:** `{"base_salary": 2500000, "stock_annualized": 1500000, "currency": "INR"}`
* **Expected Result:** `guaranteed_cash_annual = 25.0 LPA` (PT1 eligible); `total_comp_annual = 40.0 LPA` (PT6 eligible). Equity excluded from PT1.

#### T1.02-TEST-07: Conflicting Label Quarantine
* **Input Record:** `{"salary_raw": "₹15 Lakhs Take-Home CTC", "currency": "INR"}`
* **Expected Result:** Status `QUARANTINED`. Error code `ERR_AMBIGUOUS_MEASURE_LABEL`. Both Take-Home and CTC claimed simultaneously.

#### T1.02-TEST-08: Net Take-Home Without Tax Slip
* **Input Record:** `{"net_take_home": 110000, "period": "monthly", "currency": "INR", "tax_details": null}`
* **Expected Result:** Status `ISOLATED`. `measure_id: take_home_annual`, value = `13.2 LPA`. **Never** back-calculate gross salary using an assumed 20% or 30% tax bracket.

---

## 9. Unresolved Governance Decisions

The following policy choices require explicit human sign-off prior to Gate G1:

| Decision ID | Description | Default Proposal | Impact | Status |
|:---|:---|:---|:---|:---|
| **DEC-T1.02-01** | Should fixed annual transport/conveyance allowances subject to bill submission be included in `guaranteed_cash_annual`? | **Include**, as standard employment contracts treat unspent amounts as fully taxable cash rather than forfeiture. | Adds 2%–5% to fixed cash | Proposed |
| **DEC-T1.02-02** | Treatment of joining/sign-on bonuses in PT1 vs PT4. | **Exclude entirely from PT1**; model separately as an auxiliary one-time parameter in PT4 negotiation scenarios. | Prevents first-year cash spike from distorting recurring pay distributions | Proposed |
| **DEC-T1.02-03** | Treatment of unvested ESOP grants for early-stage startup profiles. | **Exclude from continuous regression models**; report purely as descriptive qualitative liquidity risk flags. | Protects model calibration from highly illiquid paper equity | Proposed |

---

*Authored for ArthaIQ under Phase 1, Task T1.02.*
