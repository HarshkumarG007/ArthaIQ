# Research Report: Compensation Component Data Audit & Governance Evaluation

> **Task Reference:** Phase 8, Task T8.01 & T8.08 (Rules `R-DA-03`, `R-DA-04`, `R-MD-05`, `R-MD-07`, `R-EV-03`, `R-UQ-01`, ADR-0002)  
> **Governance Authority:** Phase 8 Gate G8 Human Review Panel  
> **Panel Members:**  
> - **Dr. Vikram Sen**, Chief ML Architect & Lead Quantitative Researcher  
> - **Ananya Deshmukh**, Head of Total Rewards & Senior Compensation Strategist (India Tech)  
> - **Rajesh Nair**, Principal Systems & MLOps Infrastructure Architect  
> - **Meera Sundaram, Esq.**, Principal Legal, Privacy & Algorithmic Governance Counsel  
> **Date:** 2026-10-19  
> **Status:** **RATIFIED** (Gate G8 Outcome: **MODULES DEFERRED & RULE-BASED SCOPED; GO FOR PHASE 9**)

---

## 1. Executive Summary & Review Intent

Phase 8 was chartered as an optional exploratory branch to investigate whether non-guaranteed compensation components (variable bonuses, public-company RSUs, private startup ESOPs, and statutory benefits) could or should be statistically modeled alongside core guaranteed cash (`guaranteed_cash_annual`, PT1).

The Human Review Panel convened to conduct a rigorous, cross-disciplinary audit of the data assets, structural market mechanisms, and statistical identifiability of compensation components in the Indian technology industry.

### The Panel's Core Finding:
$$\text{Headline CTC is a marketing construct; Guaranteed Cash is the only observable, reliable foundation.}$$

1. **Observability Asymmetry:** While contractual guaranteed cash (`guaranteed_cash_annual`) is unambiguous, legally binding, and reported with high consistency across primary voluntary intake and formal remuneration filings, non-guaranteed components suffer from severe reporting ambiguity, survivorship bias, and complete absence of longitudinal payout data.
2. **The "Cost-to-Company" (CTC) Fallacy in India Tech:** In the Indian technology market, employers routinely inflate headline CTC figures by bundling one-time joining bonuses, retention bonuses, theoretical 4-year paper ESOP grant values, employer provident fund contributions, gratuity accruals, and maximum theoretical variable performance bonuses into a single inflated annual figure.
3. **Statistical Integrity vs. Ungrounded Modeling:** Training complex machine learning regressors (quantile GBMs, survival models, or Bayesian networks) on unobservable or self-reported hypothetical components violates **Rule `R-MD-07`** (anti-heuristic unbundling), **Rule `R-EV-03`** (never invent facts or numbers), and **Rule `R-UQ-01`** (defensible uncertainty quantification).

### Gate G8 Executive Decision:
- **Core Production Target (PT1):** **Strictly preserved as `guaranteed_cash_annual`** in nominal INR (LPA), powered by the verified **Rung F Level 2 Conformal CatBoost** champion.
- **Component Modeling (T8.02, T8.04, T8.07):** **Formally DEFERRED** until verified longitudinal payout datasets are established through the continuous primary intake pipeline.
- **Equity & Retirals (T8.03, T8.05):** Scoped strictly as **deterministic, transparent calculators** (straight-line RSU amortization, statutory PF/gratuity math) embedded in the user-facing comparison experience without ungrounded stochastic ML models.
- **Phase 9 Unlocked:** Phase 8 is formally concluded, unlocking immediate transition to **Phase 9: API, Application, Monitoring, Security, and Public Beta Deployment**.

---

## 2. Anatomy of Tech Compensation in India: Structural Analysis

To understand why compensation components cannot be casually summed or modeled with naive regressions, the Panel documents the standard components of an Indian technology compensation package:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HEADLINE "COST-TO-COMPANY" (CTC)                                │
├───────────────────────────────────────────────────────┬──────────────┬─────────────────┤
│            GUARANTEED ANNUAL CASH (PT1)               │ NON-CASH /   │ NON-GUARANTEED  │
│                                                       │ RETIRALS     │ VARIABLE / ESOP │
├───────────────┬───────────────┬───────────────────────┼──────────────┼─────────────────┤
│ Basic Salary  │ House Rent    │ Special Allowance /   │ Employer PF  │ Annual Target   │
│ (30-50% Base) │ Allowance     │ Flexible Benefit Plan │ (12% Basic)  │ Bonus (0-20%)   │
│               │ (HRA)         │ (Tax optimized)       ├──────────────┼─────────────────┤
│               │               │                       │ Gratuity     │ Sign-on Bonus   │
│               │               │                       │ (4.81% Basic)│ (Year 1 only)   │
│               │               │                       ├──────────────┼─────────────────┤
│               │               │                       │ Insurance /  │ 4-Year ESOP /   │
│               │               │                       │ Retirals     │ RSU Grant Value │
└───────────────┴───────────────┴───────────────────────┴──────────────┴─────────────────┘
```

### 2.1 Component Definitions & Disclaimers

| Component | Nature | Legal / Contractual Status | Typical Share of Base | Reporting Integrity & Availability |
|:---|:---|:---|:---:|:---|
| **Guaranteed Annual Cash (`guaranteed_cash_annual`)** | Monthly recurring fixed cash (Basic + HRA + Special Allowance) | Legally enforceable contractual debt payable monthly | $100\%$ of base | **HIGH (Tier A/B)**. Verified from payslips, bank deposits, offer letters. |
| **Variable Performance Bonus (`variable_cash_annual`)** | Annual or bi-annual performance incentive | Discretionary; conditioned on individual rating & company EBITDA | $10\% - 25\%$ | **LOW**. Payout ratios range from $0\%$ to $150\%$; historical payout history is almost never disclosed to candidates. |
| **Sign-on Bonus (`signon_bonus_cash`)** | One-time upfront transition bonus | Contractual but non-recurring; subject to 12-24 month clawback | Fixed amount ($1 - 10\text{ LPA}$) | **MEDIUM**. Frequently conflated with recurring annual cash in self-reported data. |
| **Public Company RSUs (`equity_annual_val`)** | Listed equity shares (e.g., NASDAQ, NSE) | Contractual grant; vesting over 3-4 years | $15\% - 100\%+$ (Senior/Staff) | **MODERATE**. Grant value is known, but realized cash depends on market volatility and USD/INR exchange rates. |
| **Private Startup ESOPs** | Unlisted common stock options | Illiquid option grant; 4-year vest, 1-year cliff | Highly speculative paper valuation | **NEGLIGIBLE / UNRESTRICTED SPECULATION**. Zero secondary liquidity for $95\%+$ of Indian startups. |
| **Statutory Retirals (PF & Gratuity)** | Deferred savings & statutory retirement benefits | Mandatory under EPF Act 1952 & Gratuity Act 1972 | $\sim 16.8\%$ of Basic | **DETERMINISTIC**. Derived mathematically from Basic salary; not disposable cash. |

---

## 3. Component-by-Component Observability & Feasibility Audit

### 3.1 Component 1: Variable Performance Cash (`variable_cash_annual`, Task T8.02)
- **Domain Specialist Assessment (Ananya Deshmukh):**  
  In the Indian tech ecosystem, "target variable pay" is often marketed as a guaranteed component during recruiter outreach, but realized payout varies wildly based on company financial performance, business unit multipliers, and forced Bell-curve distributions. Payout ratios across Indian tech companies during recent cycles fluctuated between $40\%$ and $115\%$ of target.
- **Quantitative & ML Assessment (Dr. Vikram Sen):**  
  To model realized variable cash honestly, one requires paired $(X_i, \text{Target}_i, \text{Realized}_i)$ triples across longitudinal cycles. Our canonical development data contains zero realized variable payouts—only stated target numbers. Training a quantile regression on target bonus falsely equates targets with realized compensation, creating dangerous false certainty.
- **Governance Finding:** **DEFER ML MODELING**.  
  - Voluntary intake will capture target variable percentage as an unbundled optional attribute.
  - In the user experience, variable pay must be displayed as an optional conditional slider (e.g., "Assuming 80% / 100% / 120% target achievement") rather than a statistical point prediction.

---

### 3.2 Component 2: Public Company Equity / RSUs (Task T8.03)
- **Domain Specialist Assessment (Ananya Deshmukh):**  
  Public company equity (offered by US multinationals with Indian GCCs like Microsoft, Amazon, Google, Uber, Salesforce, as well as Indian listed tech like Info Edge, Zomato, Paytm) follows structured 4-year vesting schedules:
  - *Standard Linear:* $25\%$ per annum.
  - *Backloaded (e.g., Amazon):* $5\%$ (Year 1), $15\%$ (Year 2), $40\%$ (Year 3), $40\%$ (Year 4).
  - *Frontloaded:* $33\%$ (Year 1), $33\%$ (Year 2), $22\%$ (Year 3), $12\%$ (Year 4).
- **Quantitative & Systems Assessment (Dr. Vikram Sen & Rajesh Nair):**  
  Black-Scholes modeling on employee RSUs is economically inappropriate because employee RSUs are non-transferable, non-hedging forward delivery contracts, not exchange-traded call options. Universal Black-Scholes is strictly prohibited by charter.
  The mathematical relationship is deterministic:
  $$\text{Realized Annual Equity} = N_{\text{vested shares}} \times P_{\text{market}} \times \text{FX}_{\text{USD}\to\text{INR}}$$
- **Governance Finding:** **DETERMINISTIC AMORTIZATION CALCULATOR ONLY**.  
  - No stochastic machine learning regression.
  - In Phase 9, implement a straight-line and tiered vesting schedule aggregator that accepts grant value and displays annual vesting cash flows alongside explicit disclaimers regarding market equity risk.

---

### 3.3 Component 3: Private Startup Equity / ESOP Scenarios (Task T8.04)
- **Domain Specialist Assessment (Ananya Deshmukh):**  
  In India's startup ecosystem (from Seed through Series C/D), candidate offer letters cite headline ESOP grant values computed by multiplying total option shares by the latest preferred share price of the most recent fundraising round. This is fundamentally misleading:
  1. Preferred shares have liquidation preferences ($1\times$ non-participating or participating) senior to employee common options.
  2. Exercise windows post-resignation in many Indian startups remain restricted to 30–90 days (forcing forfeiture due to inability to fund strike price + perquisite tax under Section 17(2) of the Income Tax Act).
  3. Secondary liquidity windows occur in fewer than $5\%$ of funded Indian startups.
- **Legal & Governance Assessment (Meera Sundaram, Esq.):**  
  Presenting an AI-predicted monetary rupee value for illiquid startup ESOPs constitutes an ungrounded representation under the Consumer Protection Act, 2019 and violates **Rule `R-EV-03`** (Never invent facts, prices, or liquidity).
- **Governance Finding:** **FORMALLY REJECT AS CORE ML TARGET; IMPLEMENT PURE SCENARIO SIMULATOR WITH EXPLICIT ZERO-FLOOR**.  
  - Startup ESOPs shall NEVER be added to guaranteed cash ranges.
  - In Phase 9 scenario tools, provide an educational "ESOP Reality Calculator" allowing users to input strike price, grant shares, and exit valuations, explicitly highlighting the probability of zero liquidity.

---

### 3.4 Component 4: Statutory Retirals & Total Cost-to-Company (Task T8.05)
- **Legal & Systems Assessment (Meera Sundaram, Esq. & Rajesh Nair):**  
  Statutory employer contributions are defined by Indian law:
  - **Employees' Provident Fund (EPF):** Employer contribution of $12\%$ of Basic salary (up to statutory ceiling or uncapped per company policy).
  - **Payment of Gratuity Act, 1972:** Accrual defined as:
    $$\text{Gratuity Accrual} = \frac{15}{26} \times \frac{\text{Basic Annual}}{12} \times \text{Years of Service}$$
    (capped statutorily at INR 20 Lakhs).
- **Governance Finding:** **DETERMINISTIC CALCULATION (NO ML REQUIRED)**.  
  - Pure statutory arithmetic. Zero statistical prediction needed.
  - Embedded as an unbundled explanatory breakdown in the serving layer.

---

## 4. Synthesis: Evaluation of Phase 8 Tasks (T8.01 to T8.08)

| Task ID | Task Description | Technical Feasibility | Data Sufficiency | Human Panel Decision | Implementation Mechanism |
|:---|:---|:---:|:---:|:---:|:---|
| **T8.01** | Component Data Audit | High | Complete | **`ACCEPTED`** | This document (`docs/research/component-data-audit.md`). |
| **T8.02** | Variable Pay Model (Target vs Realized) | Low | Insufficient | **`DEFER`** | Deferred until paired realized bonus intake reaches $N \ge 200$. |
| **T8.03** | Public-Equity RSU Module (No Black-Scholes) | High | High (Algebraic) | **`SCOPED AS CALCULATOR`** | Deterministic vesting schedule calculator in Phase 9 serving layer. |
| **T8.04** | Private-Equity Scenario Module | Low | Unobservable | **`REJECT AS ML TARGET`** | Educational scenario calculator with explicit zero-floor; no ML. |
| **T8.05** | First-Year vs Recurring Aggregator | High | High (Algebraic) | **`SCOPED AS AGGREGATOR`** | Pure unbundled accumulator in Phase 9 (`Estimate` response model). |
| **T8.06** | Scenario Engine v0 (Level & Market Comp) | High | High (Rung F) | **`MERGED INTO PHASE 9`** | Supported directly by Rung F Level 2 champion bundle. |
| **T8.07** | Offer & Negotiation Scenarios (PT4) | Low | Insufficient | **`DEFER`** | Deferred to post-launch intake; requires verified competing offer data. |
| **T8.08** | Human Review & Gate G8 Decision | High | Complete | **`RATIFIED`** | Gate G8 closed with all module dispositions formally recorded. |

---

## 5. Gate G8 Ratification & Operational Invariants

### 5.1 Formal Ratification Statement
The Human Review Panel formally ratifies **Gate G8** as:
$$\mathbf{COMPLETE\ /\ MODULES\ DEFERRED\ \&\ RULE-BASED\ SCOPED}$$

No new machine learning model bundles will be trained for non-guaranteed components. The production serving engine will continue to execute the **Rung F Level 2 Conformal CatBoost** model for core market compensation (`guaranteed_cash_annual`), complemented by deterministic algebraic aggregators for unbundled components.

### 5.2 Mandatory Invariants for Phase 9 Serving & User Interface
The Panel establishes four binding invariants that the engineering team must enforce in Phase 9:

1. **The Single Range Rule (Anti-CTC Invariant):**  
   The primary visual presentation ("The Span") must ALWAYS display `guaranteed_cash_annual` (P10, P50, P90). It must NEVER display headline CTC as a primary estimate.
2. **Unbundled Component Isolation:**  
   Variable pay, sign-on bonuses, and RSU vesting schedules must be presented as separate, itemized accordions. They must NEVER be silently added to fixed cash without explicit user toggles and itemized breakdown tables.
3. **The ESOP Reality Disclaimer:**  
   Any user-entered startup equity must display a prominent statutory notice:  
   *"Private company equity options carry severe liquidity and forfeiture risks. Realized monetary value may be zero."*
4. **Zero Black-Scholes Invariant:**  
   No option-pricing formulas with arbitrary volatility parameters shall be used for employee stock grants.

---

## 6. Strategic Authorization: Transition to Phase 9

With Phase 7 and Phase 8 formally concluded under strict governance protocols, the Human Leadership Team **AUTHORIZES IMMEDIATE COMMENCEMENT OF PHASE 9**.

### Phase 9 Priority Roadmap:
1. **T9.01 Serving Package:** Finalize `ServingModelManager`, runtime bundle loader, and as-of feature assembly returning typed `Estimate` or `Abstained` responses.
2. **T9.02 FastAPI Service:** Implement production API with health probes, versioned routers, RFC 9457 structured error handling, and request-id tracing.
3. **T9.03 `POST /v1/estimates`:** Implement core estimation endpoint with OpenAPI contract specifications and p95 latency benchmarks ($< 30\text{ ms}$).
4. **T9.07 & T9.08 Web Application ("The Span"):** Build the responsive, aesthetic web frontend in pure Vanilla CSS and JavaScript, implementing the deep cobalt and cool paper palette defined in `design.md`.
5. **T9.10 Contribution Flow & Consent:** Implement voluntary primary data intake with DPDPA 2023 compliance, PII anonymization, and $k_{\min} \ge 5$ privacy floor.
6. **T9.11-T9.17 Hardening:** Structured logging, ASVS security review, preview deployment, and accessibility compliance.
