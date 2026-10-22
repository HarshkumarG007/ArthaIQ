# Research Memo: EXP-15 Counterfactual Negotiation & Offer Scenario Modeling

| Attribute | Value |
| --- | --- |
| **Charter ID** | `CHARTER-EXP-15` |
| **Experiment Name** | Counterfactual Negotiation & Offer Scenario Modeling (PT4 Prototype) |
| **Evaluation Date** | 2026-10-22 23:45:00 UTC |
| **Verdict** | **PROMOTE** |
| **Sample Size** | 500 Negotiation Transcripts |

## 1. Executive Summary

Per `CHARTER-EXP-15`, this experiment evaluates our constrained counterfactual optimization engine 
(**PT4 Prototype**) designed to answer user negotiation queries (e.g., *'What cash-equity trade-off maintains 
market competitiveness?'* or *'How does relocating or promotion alter my quantile bounds?'*) without ever 
emitting deceptive lone point estimates or violating monotonicity.

- **Monotonicity Satisfaction Rate:** **100.00%** (threshold: $\ge 98.0\%$) — **PASS**
- **Counterfactual Empirical Coverage:** **79.98%** (pre-registered band: $[75.0\%, 85.0\%]$) — **PASS**
- **Zero Point-Estimate Compliance:** **100.0%** (100% compliant ranges $[P_{10}, P_{50}, P_{90}]$) — **PASS**
- **Frontier Generation Latency (p95):** **4.03 ms** (SLA: $\le 150.0\text{ ms}$) — **PASS**

## 2. Pre-Registered Keep Criteria Scorecard

| Criterion | Pre-Registered Target | Measured Outcome | Verdict |
| --- | --- | --- | --- |
| **Criterion 1 (Monotonicity)** | $\ge 98.0\%$ satisfaction | **100.00%** | **PASS** |
| **Criterion 2 (Empirical Coverage)** | $[75.0\%, 85.0\%]$ nominal | **79.98%** | **PASS** |
| **Criterion 3 (Zero Point Estimates)** | $100.0\%$ range compliance | **100.0%** | **PASS** |
| **Criterion 4 (Generation Latency)** | $p_{95} \le 150.0\text{ ms}$ | **4.03 ms** | **PASS** |

## 3. Detailed Benchmark Findings

### 3.1 Structural Monotonicity Verification
Across 500 transcripts comprising 3,500 individual perturbation steps across Experience, Seniority, and Metro 
dimensions, the constrained engine achieved **100.0% non-crossing quantile preservation** ($P_{10} \le P_{50} \le P_{90}$) 
and **100.00% directional monotonicity**. Isotonic repair successfully corrected 
minor local empirical sampling noise, guaranteeing that candidates are never told higher experience or seniority 
yields lower pay.

### 3.2 Statutory Tax-Adjusted Take-Home In-Hand Bounds
Every counterfactual frontier point incorporates statutory personal income tax calculations under Section 115BAC 
(India New Tax Regime, FY2024-26), reporting realistic net in-hand take-home bounds along with effective tax rates. 
This transparency directly addresses pilot user feedback regarding gross CTC vs net monthly realization.

### 3.3 Zero Lone-Number Guarantee (Rule R-UQ-01 / R-MD-08)
Every single scenario output generates full 80% conformal bounds $[P_{10}, P_{50}, P_{90}]$ accompanied by 
trade-off uncertainty margins. The statutory notice is immutably attached to every response payload, preventing 
the tool from acting as an appraisal or guaranteed financial promise.

## 4. Architectural Readiness & Promotion Determination

Based on 100% satisfaction of pre-registered Keep Criteria, the Governance Determination is **PROMOTE**.
The counterfactual engine (`compintel.serving.counterfactual`) and the interactive UI component 
(`NegotiationScenario.tsx`) are cleared for production deployment under PT4 prototype flags.