# Copula Dependency Structure for Multi-Component PT4 (Phase 13, CHARTER-COPULA-PT4)

> **Scope:** Empirical Re-evaluation of Gaussian Copula Joint Dependency Structure (Non-Parametric Empirical Marginals, Zero Discretization) as a PT4 Scenario Correlation Layer on Top of EXP-15 Counterfactual Engine.
> **Governing Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-05, R-MD-08, R-MD-09, R-UQ-01, R-UQ-05, R-CD-01 · Task T13.07.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `RPT-COPULA-PT4-20261023-001` |
| **Charter ID** | `CHARTER-COPULA-PT4` |
| **Experiment ID** | `EXP-PGM-01r` |
| **Task ID** | `T13.07` |
| **Generated At** | `2026-10-23 09:57:46 UTC` |
| **Git Commit** | `c17f2d5c` |
| **Dataset Observations** | `500` (219 non-synthetic) |
| **Evaluated Components** | `guaranteed_cash_annual, equity_annualized, variable_performance_annual` |
| **Pre-Registered Verdict** | **`PROMOTE`** |
| **Core Model Integrity** | **Champion CatBoost Preserved Unmodified** |

---

## 1. Executive Summary & Production Decision

Evaluation of Gaussian copula joint dependency structure (EXP-PGM-01r, Task T13.07) confirms outstanding empirical performance across all 6 pre-registered keep criteria:
- Rank Correlation Preservation: Max Spearman error |Δρ| = 0.0388 (<= 0.050 threshold) across components, compared to severe distortion under independent marginals (|Δρ| up to 0.65).
- Monotonic Non-Crossing Quantiles: 0.00% crossing rate across 1,000 queries (100% satisfaction of P10 <= P50 <= P90 under Rule R-UQ-05).
- Microsecond Inference Latency: p95 latency = 0.86 ms (well within 25.0 ms budget and 150 ms scenario SLA).
- Empirical Holdout Joint Coverage: 78.00% in pre-registered [75%, 85%] target window.
- Final Verdict: Formal PROMOTE to the PT4 interactive negotiation scenario UI layer. Champion Conformal CatBoost is strictly preserved unmodified for core estimation.

---

## 2. Pre-Registered Keep Criteria Audit

Under Rule `R-MD-09` and `CHARTER-COPULA-PT4`, the Gaussian copula scenario layer must satisfy all pre-registered empirical criteria to earn a `PROMOTE` verdict:

| Criterion Dimension | Target Threshold | Observed Value | Status |
|:---|:---:|:---:|:---:|
| **Primary: Rank Correlation Fidelity (Max $|\Delta \rho|$)** | $\le 0.050$ | `0.0388` | **PASS** |
| **Secondary: Zero Point-Estimate Compliance** | `100.0%` calibrated spans | `100.0%` | **PASS** |
| **Secondary: Quantile Crossing Rate** | $\le 0.000$ | `0.0000` | **PASS** |
| **Secondary: Scenario Generation Latency ($p95$)** | $\le 25.0\text{ ms}$ | `0.86\text{ ms}` | **PASS** |
| **Secondary: Empirical Joint Coverage** | $[0.75, 0.85]$ | `78.00%` | **PASS** |
| **Secondary: Core Model Non-Contamination** | `100.0%` isolated | `ISOLATED` | **PASS** |

---

## 3. Multivariate Dependency Analysis: Empirical vs Copula vs Independent

Table below contrasts empirical pairwise rank correlations (Spearman $\rho$ and Kendall $\tau$) against simulated samples from the Gaussian Copula model and the naive independent marginals baseline:

| Component Pair | Empirical Spearman $\rho$ | Copula Spearman $\rho$ | Copula $|\Delta \rho|$ | Independent $\rho$ | Empirical Kendall $\tau$ | Copula Kendall $\tau$ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **guaranteed_cash_annual** $\times$ **equity_annualized** | `+0.957` | `+0.918` | `0.0388` | `-0.016` | `+0.816` | `+0.754` |
| **guaranteed_cash_annual** $\times$ **variable_performance_annual** | `+0.861` | `+0.841` | `0.0196` | `-0.015` | `+0.689` | `+0.651` |
| **equity_annualized** $\times$ **variable_performance_annual** | `+0.864` | `+0.850` | `0.0136` | `-0.008` | `+0.689` | `+0.662` |

---

## 4. Latency and Monotonicity Performance Profile

- **Median Simulation Latency ($p50$):** `0.34 ms`
- **95th Percentile Latency ($p95$):** `0.86 ms` (SLA Budget: `25.0 ms`)
- **99th Percentile Latency ($p99$):** `1.44 ms`
- **Quantile Crossing Rate:** `0.00%` (Guarantees $P_{10} \le P_{50} \le P_{90}$ across all sampled trade-off bounds)
- **Empirical Joint Coverage:** `78.00%` (Target: 80.0% nominal interval coverage)

---

## 5. Scope Boundary & Architectural Governance

Strict Architectural Fence (Rules R-MD-08 & R-MD-09):
1. Interactive Scenario UI Only: The Gaussian copula layer is strictly integrated into the PT4 negotiation engine (compintel.serving.counterfactual) for generating conditional trade-off bounds [P10, P50, P90] in the web UI.
2. Zero Core Interference: Core compensation point estimation and single-point baseline inferences remain 100% governed by the Champion Rung F Level 2 Conformal CatBoost model. The copula model never overrides or influences core point predictions.
3. Zero Lone Numbers: Every scenario query outputs explicit 80% conformal bounds with monotonic non-crossing guarantees.

---

## 6. Actionable Integration Directive

1. **PT4 Scenario Integration:** Promote `GaussianCopulaJointModel` as an multi-component dependency engine in `compintel.serving.counterfactual` for candidate offer trade-off simulations.
2. **Zero Core Disturbance:** Maintain Champion Conformal CatBoost strictly unmodified for core compensation point and interval predictions.
3. **Claim Registration:** Register Claim 30 in `evidence-register.csv` authorizing Gate G13 advancement.