# Phase 7 Advanced Modeling Experiment Charters & Ranking (T7.01)

> **Document ID:** `docs/research/experiment-charters-phase7.md`  
> **Status:** RATIFIED & PRE-REGISTERED  
> **Author:** AI Assistant & Human Reviewer  
> **Date:** 2026-10-19  
> **Governing Rules:** `R-MD-01`, `R-MD-03`, `R-MD-05`, `R-MD-09`, `R-CD-01`, `R-DA-10`

---

## 1. Executive Summary

Under **Rule `R-MD-09`**, complex architectural components (including sentence embeddings, text models, employer graphs, graph neural networks, ensembling, survival models, and probabilistic graphical models) are strictly prohibited from ad-hoc implementation without a pre-registered **Experiment Charter** defining explicit keep, defer, and reject criteria before code is written.

Phase 7 systematically assesses whether any advanced feature family or modeling technique can beat the **Champion Model** established at Gate G6:
- **Champion Baseline:** Rung F Conformal CatBoost on Level 2 features with split conformal coverage calibration (`experiments/results/champion_v0/`).
- **Pre-Registered Minimum Effect Size:** $\Delta \text{Mean Pinball Loss} \le -0.050$ LPA with a 95% bootstrap confidence interval strictly excluding zero ($p < 0.05$).
- **Efficiency and Latency Gates:** Max inference latency $\le 50\text{ms}$ (to fit within NFR-02 $200\text{ms}$ overall SLA), bundle size $\le 100\text{MB}$, zero GPU dependency, and zero quantile crossings ($\text{crossing rate} \le 0.5\%$).

---

## 2. Master Charter Ranking by Expected Value (EV) vs Cost

All candidate proposals are formally evaluated and ranked across expected predictive utility and implementation/maintenance overhead:

| Rank | Charter ID | Candidate Name | Primary Task | Expected Value | Cost | Feasibility | Pre-Registered Keep Criterion |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---|
| **1** | `CHARTER-EXP-09` | Curated Taxonomy & TF-IDF vs Sentence Embeddings | **T7.02** | **MEDIUM** | **MED-HIGH** | Feasible | $\Delta \text{Pinball} \le -0.050$ LPA, latency $\le 50\text{ms}$, bundle $\le 80\text{MB}$ |
| **2** | `CHARTER-CAREER-TRAJ` | Career Trajectory Features vs Experience | **T7.03** | **MEDIUM** | **LOW-MED** | Feasible | $\Delta \text{Pinball} \le -0.050$ LPA, no lookahead leakage |
| **3** | `CHARTER-EXP-10` | Employer Simple vs Graph-Based Talent Flows | **T7.04** | **LOW-MED** | **HIGH** | Conditional | $\Delta \text{Pinball} \le -0.050$ LPA, $k_{\text{min}} \ge 5$ floor |
| **4** | `CHARTER-MACRO-REGIMES` | Macro & Market Regimes with Release Joins | **T7.05** | **HIGH** | **LOW** | Feasible | $\Delta \text{Pinball} \le -0.050$ LPA, publication-lag joins |
| **5** | `CHARTER-ENSEMBLE-01` | Model Ensembling & Quantile Stacking | **T7.06** | **LOW-MED** | **HIGH** | Feasible | Width ratio $\le 0.95$, $\Delta \text{Pinball} \le -0.050$ LPA |
| **6** | `CHARTER-SURVIVAL-01` | Survival Models for Compensation Stagnation | *Advanced* | **LOW** | **MEDIUM** | Conditional | C-index $\ge 0.70$, PRD interval compliance |
| **7** | `CHARTER-PGM-01` | Probabilistic Graphical Models & DAGs | *Advanced* | **LOW** | **HIGH** | Low | $\Delta \text{Pinball} \le -0.050$ LPA, latency $\le 200\text{ms}$ |

---

## 3. Individual Charter Summaries

### 3.1 CHARTER-EXP-09: Skills Curated Taxonomy vs Sentence-Transformer Embeddings (T7.02)
- **Hypothesis:** Dense semantic embeddings from compact sentence-transformers or TF-IDF on standardized skill strings capture nuanced skill synergy better than a discrete curated taxonomy.
- **Keep:** $\Delta \text{Mean Pinball} \le -0.050$ LPA with 95% CI upper bound $< 0.0$ and CPU inference latency $\le 50\text{ms}$.
- **Reject:** $\Delta > -0.050$ LPA, CI includes zero, or memory/bundle exceeds budget.

### 3.2 CHARTER-CAREER-TRAJ: Career Trajectory vs Tenure & Total Experience (T7.03)
- **Hypothesis:** Dynamic career velocity ($\text{seniority rank} / \text{YoE}$) and promotion frequency explain compensation variance beyond static Mincerian quadratic tenure curves.
- **Keep:** $\Delta \text{Mean Pinball} \le -0.050$ LPA with 95% CI upper bound $< 0.0$.
- **Reject:** $\Delta > -0.050$ LPA, or requires unverifiable employment history in voluntary intake.

### 3.3 CHARTER-EXP-10: Employer Simple vs Graph-Based Talent Flows (T7.04)
- **Hypothesis:** Spectral graph embeddings on historical talent mobility networks capture compensation prestige tiers better than discrete employer archetypes.
- **Keep:** $\Delta \text{Mean Pinball} \le -0.050$ LPA with 95% CI upper bound $< 0.0$ and 100% compliance with $k_{\text{min}} \ge 5$ node privacy.
- **Reject:** $\Delta > -0.050$ LPA, temporal graph leakage across split boundaries, or excessive node sparsity.

### 3.4 CHARTER-MACRO-REGIMES: Macroeconomic Regimes with As-Of Release Joins (T7.05)
- **Hypothesis:** Macro indices (MOSPI CPI Urban, RBI reference rates, tech sector GDP growth) joined strictly by release timestamp capture macro wage inflation and narrow prediction intervals.
- **Keep:** $\Delta \text{Mean Pinball} \le -0.050$ LPA with 95% CI upper bound $< 0.0$ and verifiable publication lags.
- **Reject:** $\Delta > -0.050$ LPA, or time-series collinearity on short observation spans.

### 3.5 CHARTER-ENSEMBLE-01: Quantile Model Ensembling & Stacking (T7.06)
- **Hypothesis:** Blending CatBoost CQR, LightGBM MultiQuantile, and Hierarchical Bayes with monotonic isotonic projection achieves lower pinball loss than any single model.
- **Keep:** $\Delta \text{Mean Pinball} \le -0.050$ LPA, interval width compression $\ge 5\%$ (width ratio $\le 0.95$), and 0.00% crossing rate.
- **Reject:** Width compression $< 5\%$, marginal gain insufficient to justify 3x serving maintenance overhead.

### 3.6 CHARTER-SURVIVAL-01: Survival Models for Progression & Stagnation
- **Hypothesis:** Accelerated Failure Time models on tenure-at-level capture promotion hazard.
- **Reject/Defer:** Cross-sectional salary data lacks right-censoring duration markers; cannot directly predict guaranteed cash intervals per PRD FR-01.

### 3.7 CHARTER-PGM-01: Probabilistic Graphical Models & Bayesian Networks
- **Hypothesis:** Structural DAGs encode conditional dependencies between role, location, and compensation components.
- **Reject/Defer:** Inferior regression precision on tabular data; reserved for scenario simulation (Phase 8).

---

## 4. Architectural Boundaries and Pre-Commit Enforcement

All charter configurations reside in `experiments/configs/charters/` and are validated by unit tests in `tests/unit/test_experiment_charters.py`. No advanced model code may be promoted to production without meeting its specific charter criteria.
