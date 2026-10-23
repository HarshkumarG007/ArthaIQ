# Gate G13 Milestone Review & Architecture Re-evaluation

| Field | Value |
|---|---|
| **Document Type** | Milestone Gate Review & Architecture Re-evaluation Decision |
| **Status** | **🟢 RATIFIED GO (Gaussian Copula Promoted to PT4 UI; 4 Charters Deferred with Pre-registered Triggers; Ensembling Rejected)** |
| **Review Date** | 2026-10-23 |
| **Gate Reference** | Gate G13 (`task.md` Phase 13, `PRD.md` Section 15) |
| **Prerequisites** | Tasks T13.01–T13.07 (`EXP-10r`, `EXP-ENSEMBLE-01r`, `EXP-09r`, `T13.04`, `EXP-TRAJ-r`, `EXP-MACRO-01r`, `EXP-PGM-01r`), Benchmark Review (`scripts/run_phase13_review.py`) |
| **Governing Rules** | `rules.md` (R-WF-01, R-WF-08, R-MD-01, R-MD-05, R-MD-08, R-MD-09, R-MD-11, R-UQ-01, R-UQ-05, R-CD-01, R-CD-03, R-CD-06) |
| **Companion Docs** | `docs/research/copula-pt4-phase13.md`, `docs/research/employer-graph-reaudit-phase13.md`, `docs/research/ensemble-reaudit-phase13.md`, `docs/research/skills-reaudit-phase13.md`, `docs/research/career-trajectory-reaudit-phase13.md`, `docs/research/macro-regimes-reaudit-phase13.md`, `docs/model-cards/model-card-final-v1.md`, `docs/research/evidence-register.csv` |

---

## 1. Executive Determination

On 2026-10-23, the multidisciplinary Governance Panel convened to conduct the formal, adversarial milestone review of **Gate G13: Deferred Architecture Re-evaluation & Scenario Copula Promotion** for the **ArthaIQ Compensation Intelligence Platform**.

### Formal Verdict
> **GATE G13 VERDICT: UNCONDITIONAL GO — ALL GATE REQUIREMENTS SATISFIED.**  
> In strict accordance with `task.md` Gate G13 requirements (*"all Phase 13 feasibility audits completed with documented verdicts; at least one PROMOTE verdict achieved OR all formally deferred with next trigger dates recorded"*), the review panel determines that:
>
> 1. **Gaussian Copula Scenario Dependency Structure (`EXP-PGM-01r`, T13.07):** Evaluated across 500 benchmark offer cases. Non-parametric empirical marginal probability integral transforms combined with Gaussian copula rank correlation achieved a maximum Spearman error $|\Delta \rho| = 0.0388 \le 0.050$ across base cash, equity grants, and variable performance bonuses. It demonstrated **0.00% quantile crossing rates** across 1,000 queries, maintained **78.00% empirical joint coverage** within the pre-registered $[75.0\%, 85.0\%]$ nominal window, operated at a sub-millisecond CPU simulation latency ($p_{95} = 0.86\text{ ms} \le 25.0\text{ ms}$ budget and $150.0\text{ ms}$ scenario SLA), and strictly adhered to Rule `R-UQ-01` (zero lone numbers). **Formal Verdict: PROMOTE to PT4 Interactive Negotiation Scenario UI Layer.** Champion Rung F Level 2 Conformal CatBoost is strictly preserved unmodified for core compensation estimation.
>
> 2. **Quantile Model Ensembling & Stacking (`EXP-ENSEMBLE-01r`, T13.02):** Evaluated on the 6-month non-synthetic production panel ($N = 219$). Convex quantile blending (CatBoost CQR + LightGBM MultiQuantile with Chernozhukov monotone sorting projection) resulted in a pinball loss increase of $+0.1320\text{ LPA}$ ($95\%$ bootstrap CI: $[+0.0243, +0.2442]\text{ LPA}$) and interval widening ($+1.47\%$, width ratio $1.0147 > 0.950$), failing pre-registered keep criteria. **Formal Verdict: REJECT.** Operational complexity of dual-model bundling is rejected; production Champion Rung F CatBoost remains unmodified.
>
> 3. **Disciplined Feasibility Deferrals with Calendar/Data Triggers:**
>    - **`EXP-10r` (Employer Graphs, T13.01):** Topological audit revealed 16 qualified employer clusters ($< 50$ required). Formal Gate 1 **DEFER** ratified. Scheduled trigger: Phase 14 B2B syndication intake or $\ge 500$ transition records.
>    - **`EXP-09r` (Skills TF-IDF, T13.03):** Statistical power analysis confirmed that the current $N = 219$ panel achieves only $45.6\%$ power against the pre-registered effect threshold ($\Delta \text{Pinball} \le -0.050\text{ LPA}$ requires $N \ge 500$). Formal Gate 1 **DEFER** ratified to avoid Type II error under Rule `R-MD-01`. Scheduled trigger: panel milestone $N \ge 500$. Variant B (sentence-transformers on CPU) remains permanently **REJECTED** due to CPU serving constraints.
>    - **`EXP-TRAJ-r` (Career Trajectories, T13.05):** Longitudinal span audit verified $5.9$ calendar months ($< 12.0$ months required) and $0$ populated milestone records ($< 100$ required). Formal Gate 1 **DEFER** ratified without speculative modeling. Scheduled trigger: longitudinal panel $\ge 12.0$ months and $\ge 100$ milestone records.
>    - **`EXP-MACRO-01r` (Macro Regimes, T13.06):** Realized observation calendar span ($5.9$ months $< 24.0$ months required) fails multi-year threshold. Formal Gate 1 **DEFER** ratified to prevent collinearity and spurious correlation. Scheduled trigger: October 2028 calendar date or panel span $\ge 24.0$ months.
>
> 4. **Longitudinal Schema Extension Delivered (`T13.04`):** Optional career milestone fields (`career_start_date`, `last_promotion_date`, `right_censored_exit_flag`) deployed via Alembic migration `0002_longitudinal_career_schema` with ADR-0008 amendment and DPDPA 2023 compliance sign-off.
>
> The panel unanimously ratifies **Gate G13 (GO)**, approving Decision `D-024`.

---

## 2. Review Panel Membership & Signatures

| Role | Representative | Vote | Date |
|---|---|---|---|
| **Lead Quantitative ML Engineer** | Algorithmic Evaluation Lead | **GO** | 2026-10-23 |
| **India Compensation Economics Specialist** | Principal Labour Economist | **GO** | 2026-10-23 |
| **Product & UX Design Lead** | Head of Product & Accessibility | **GO** | 2026-10-23 |
| **Data Protection & Legal Governance Counsel** | Privacy & Statutory Compliance Officer | **GO** | 2026-10-23 |
| **Platform / SRE Operations Lead** | Infrastructure & Systems Architect | **GO** | 2026-10-23 |

---

## 3. Quantitative Scorecard: Phase 13 Feasibility Re-audits & Trigger Registry

Evaluated without post-hoc threshold drifting (`Rule R-MD-09`):

| Charter ID | Candidate Architecture | Target Threshold | Measured Result (N=219 Non-Synthetic) | Formal Verdict | Next Scheduled Audit Trigger |
|---|---|---|---|:---:|---|
| **EXP-10r** | Employer Bipartite Graph Embeddings | $\ge 50$ qualified clusters with degree $\ge 3$ | **16 qualified clusters** (density $\rho = 0.9917$) | **DEFER** | Phase 14 B2B syndication intake or $\ge 500$ transition records |
| **EXP-ENSEMBLE-01r** | Convex Quantile Stacking / Blending | $\Delta \text{Pinball} \le -0.050\text{ LPA}$; Width Ratio $\le 0.950$ | $\Delta \text{Pinball} = \mathbf{+0.1320\text{ LPA}}$; Width Ratio = $\mathbf{1.0147}$ | **REJECT** | None (operational complexity permanently rejected) |
| **EXP-09r** | Skills TF-IDF Power-Gated Retest | $N \ge 500$ for $80.0\%$ power ($\Delta \le -0.050\text{ LPA}$) | $N = 219$, **Achieved Power = $45.6\%$** (deficit: 281 records) | **DEFER** | Cumulative non-synthetic panel size $N \ge 500$ records |
| **EXP-TRAJ-r** | Career Trajectory Longitudinal Modeling | Span $\ge 12.0\text{ mo}$; Milestones $\ge 100$ | **Span: 5.9 months**; **Milestones: 0 records** | **DEFER** | Longitudinal panel $\ge 12.0\text{ mo}$ AND $\ge 100$ milestone records |
| **EXP-MACRO-01r** | Macro Regime Time-Series Conditioning | Observation span $\ge 24.0$ calendar months | **Span: 5.9 calendar months** (deficit: 18.1 months) | **DEFER** | October 2028 calendar date OR observation span $\ge 24.0\text{ mo}$ |

---

## 4. Quantitative Scorecard: EXP-PGM-01r Gaussian Copula Keep Criteria

Evaluated against `CHARTER-COPULA-PT4` across 500 standardized benchmark offer transcripts:

| Keep Criterion | Target Threshold | Measured Empirical Result | Status |
|---|---|---|---|
| **Criterion 1: Rank Correlation Fidelity** | Max Spearman error $|\Delta \rho| \le 0.050$ | **Max $|\Delta \rho| = 0.0388$** (Mean $|\Delta \rho| = 0.0240$) | **PASS** |
| **Criterion 2: Quantile Monotonicity** | Crossing rate $= 0.00\%$ ($P_{10} \le P_{50} \le P_{90}$) | **0.00% crossings** across 1,000 simulated draws | **PASS** |
| **Criterion 3: Empirical Joint Coverage** | Empirical coverage within $[75.0\%, 85.0\%]$ | **78.00% joint coverage** (target 80.0%) | **PASS** |
| **Criterion 4: Simulation Latency SLA** | $p_{95} \le 25.0\text{ ms}$ (budget) / $150.0\text{ ms}$ (SLA) | $p_{50} = 0.34\text{ ms}$, **$p_{95} = 0.86\text{ ms}$**, $p_{99} = 1.44\text{ ms}$ | **PASS** |
| **Criterion 5: Zero Lone Point Estimates** | 100.0% compliant intervals (Rule `R-UQ-01`) | **100.0% compliant** calibrated spans emitted | **PASS** |
| **Criterion 6: Core Model Fence** | Zero contamination of Champion Rung F CatBoost | **100.0% unpolluted**; core estimation unmodified | **PASS** |

### Verified Pairwise Component Correlations
- `guaranteed_cash` $\leftrightarrow$ `equity_annualized`: Empirical Spearman $\rho = 0.9567$, Copula $\rho = 0.9179$ ($|\Delta \rho| = 0.0388 \le 0.050$ vs independent error $0.9729$).
- `guaranteed_cash` $\leftrightarrow$ `variable_bonus`: Empirical Spearman $\rho = 0.8608$, Copula $\rho = 0.8412$ ($|\Delta \rho| = 0.0196 \le 0.050$ vs independent error $0.8761$).
- `equity_annualized` $\leftrightarrow$ `variable_bonus`: Empirical Spearman $\rho = 0.8640$, Copula $\rho = 0.8504$ ($|\Delta \rho| = 0.0136 \le 0.050$ vs independent error $0.8723$).

---

## 5. Adversarial Review Checklist (Rule R-MD-05, Section 15)

Answers to mandatory governance review questions for Gate G13:

1. **Which target is this: market pay, accepted pay, or an offer? Are they separated?**  
   *Response:* Core target remains strictly PT1 (`guaranteed_cash_annual` nominal INR LPA). Multi-component pay simulation (equity grants, performance bonuses) is strictly partitioned to the PT4 interactive negotiation scenario UI layer (`compintel.serving.counterfactual`). Core baseline predictions are never conditioned on non-guaranteed pay.

2. **Does the data represent the intended population?**  
   *Response:* Yes. Evaluated on 500 benchmark offer profiles representing tech compensation in Indian metro hubs. Furthermore, feasibility audits explicitly verified that small samples ($N = 219$) must NOT be forced into high-dimensional representations (skills embeddings, macro time-series, graph walks), enforcing pre-registered `DEFER` decisions rather than misrepresenting small samples.

3. **Could the improvement come from leakage, duplicates, source artifacts or selection bias?**  
   *Response:* No. Copula evaluation employed out-of-sample empirical Probability Integral Transforms (PIT) with rank-correlation matrices estimated with strict partition isolation. For all other charters, zero performance improvement was claimed and zero models were promoted.

4. **Does personalization beat the baseline by a pre-registered margin?**  
   *Response:* For core compensation, Champion Rung F Level 2 Conformal CatBoost was audited against convex ensembling (`EXP-ENSEMBLE-01r`); ensembling degraded performance by $+0.1320\text{ LPA}$ and was rejected. For PT4 scenario simulation, the Gaussian copula beat independent marginals by reducing rank correlation error from $|\Delta \rho| > 0.60$ to $|\Delta \rho| \le 0.0388$, preserving realistic total package trade-offs.

5. **Are intervals calibrated on recent, representative data, and are they useful or merely wide?**  
   *Response:* Yes. Gaussian copula joint simulation achieved 78.00% empirical joint coverage in the pre-registered $[75.0\%, 85.0\%]$ nominal window. Quantile ensembling widened intervals by $+1.47\%$ without coverage gains and was decisively rejected.

6. **Are any explanations being read as causes?**  
   *Response:* No. Copula simulations describe joint empirical probability distributions across multi-component offers. All UI components provide descriptive disclaimers clarifying that component distributions reflect conditional market associations, not contractual employer commitments or causal negotiation levers.

7. **Could employer prestige, education or past pay introduce unjustified bias?**  
   *Response:* Mitigated. Employer graphs were deferred because sparse clusters ($< 50$) would risk prestige bias and privacy disclosure. Current pay remains permanently quarantined to Compare-Only downstream positioning (`R-MD-13`). Zero demographic columns exist in the pipeline.

8. **Is a simpler model equally good?**  
   *Response:* Decisively proven across all 6 charters. Complex graph embeddings, sentence transformers, multi-lag macro joins, and model stacking all added operational, memory, or statistical fragility without beating the simpler production Champion (Rung F Level 2 Conformal CatBoost). The simpler model was rigorously protected.

9. **Is every feature available at prediction time?**  
   *Response:* Yes. Scenario simulations require only candidate inputs. All macro features were deferred specifically because releases and time lags introduce lookahead leakage risks.

10. **Does the system recognize profiles outside its reliable range?**  
    *Response:* Yes. Decoupled support checks ($S_1$ to $S_5$) enforce explicit abstention. The Gaussian copula layer falls back safely when component margins lack empirical support. Zero lone numbers were emitted across 1,000 evaluation queries.

11. **Can the whole pipeline be reproduced, audited and run within budget?**  
    *Response:* Yes. Complete test suite and experiment suite run on pure CPU with zero GPU dependencies (`R-CD-01`). Copula inference adds only $0.86\text{ ms}$ $p_{95}$ latency ($< 25.0\text{ ms}$ budget).

12. **Which single experiment would most likely invalidate the current design?**  
    *Response:* Severe non-linear tail dependency in compensation components (e.g., extreme asymmetric equity crashes). The copula layer uses rank correlation; if extreme tail dependence emerges, Student-t copulas can be evaluated at the next scheduled review.

13. **What evidence would make us drop this feature?**  
    *Response:* If copula simulation exceeded the 25.0 ms latency budget, produced quantile crossings, or distorted joint coverage outside $[75\%, 85\%]$, it would be rejected.

14. **What is the strongest alternative explanation for each claimed gain?**  
    *Response:* That marginal distributions alone explain multi-component variation. Decisively disproven: independent marginal simulation produced massive correlation errors ($|\Delta \rho| > 0.60$ to $0.97$), demonstrating that the Gaussian copula rank correlation is necessary to prevent unrealistic package permutations (e.g., top-decile base cash paired with bottom-decile equity).

---

## 6. Architecture Promotions & Decisions Ratified

### Decision D-024: Gaussian Copula Promotion & Phase 13 Architecture Ratification
- **Promoted Component:**
  - `src/compintel/evaluation/copula_pt4_experiment.py` (Gaussian copula multi-component dependency structure engine).
  - Promoted to integration with `compintel.serving.counterfactual` for PT4 interactive negotiation scenario UI.
- **Retained Unmodified Invariant:**
  - Production Champion Rung F Level 2 Conformal CatBoost strictly retained as the sole, authoritative engine for core point and interval compensation estimation.
- **Architectural Boundary Adherence (`Rule R-CD-03`):**
  - Scenario simulation logic remains strictly isolated within serving routers; zero core estimation models import scenario simulation code.
- **Formal Rejection:**
  - Multi-model quantile stacking and ensembling (`EXP-ENSEMBLE-01r`) is permanently rejected for the core serving engine.

---

## 7. Completion of Phase 13 & Future Roadmap

With Gate G13 unanimously ratified **GO**, Phase 13 is formally concluded:
1. **Phase 13 Closed:** All tasks T13.01 through T13.07 completed, audited, and committed.
2. **Production Stack Hardened:** GA baseline retains microsecond CPU latency, calibrated 80% conformal intervals, active learning targeted sourcing, and multi-component copula scenario intelligence.
3. **Standing Re-Audit Triggers Registered:**
   - `EXP-10r`: Phase 14 B2B syndication intake ($\ge 500$ transitions, $\ge 50$ qualified nodes).
   - `EXP-09r`: Panel milestone $N \ge 500$ verified records.
   - `EXP-TRAJ-r`: Realized panel span $\ge 12.0$ months and $\ge 100$ populated milestones.
   - `EXP-MACRO-01r`: October 2028 calendar date or panel span $\ge 24.0$ months.
