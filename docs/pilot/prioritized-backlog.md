# ArthaIQ Post-Pilot Prioritized Engineering & Research Backlog

> **Document ID:** `docs/pilot/prioritized-backlog.md`  
> **Status:** RATIFIED & LINKED TO CHARTERS  
> **Author:** Antigravity AI & Human Engineering Reviewer  
> **Date:** 2026-10-21  
> **Governing Framework:** RICE Scoring (Reach, Impact, Confidence, Effort)  
> **Governing Rules:** `R-MD-09`, `R-UQ-01`, `R-DA-10`, `R-CD-06`  
> **Prerequisites:** Pilot Analysis (`T10.06`), Online Coverage Tracking (`T10.03`), Freshness SLA (`T10.04`), Drift Recalibration (`T10.05`)

---

## 1. Executive Summary

Following the formal completion of the ArthaIQ production pilot across 232 realization cohort observations (which passed all 11 pre-registered PRD Section 11 metrics with $80.17\%$ coverage and zero PII/safety incidents), this backlog prioritizes post-launch enhancements.

Each candidate initiative is evaluated using the standardized **RICE framework**:
$$\text{RICE Score} = \frac{\text{Reach} \times \text{Impact} \times \text{Confidence}}{\text{Effort}}$$
where:
- **Reach:** Normalized proportion of active user sessions or inference queries impacted per quarter ($0.1$ to $1.0$).
- **Impact:** Strategic value to accuracy, user trust, latency, or compliance ($3.0$ = Massive, $2.0$ = High, $1.0$ = Medium, $0.5$ = Low).
- **Confidence:** Empirical backing and feasibility certainty ($1.0$ = High/Empirical, $0.8$ = Medium/Observed, $0.5$ = Speculative).
- **Effort:** Estimated engineering and validation effort in person-months / person-quarters.

Per **Rule `R-MD-09`**, all top items must possess pre-registered **Experiment Charters** (`docs/research/experiment-charters-phase10.md`) specifying objective keep/reject thresholds before any implementation may proceed.

---

## 2. Master Prioritized Backlog Table

| Rank | Item ID | Title | Category | Reach | Impact | Conf. | Effort | RICE Score | Experiment Charter | Target Horizon | Status |
|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|:---:|:---:|
| **—** | `EXP-13` | Slice-Adaptive Conformal Prediction Intervals | Calibration & UQ | 0.80 | 2.5 | 0.90 | 0.25 (3 wks) | **72.0** | `CHARTER-EXP-13` | Phase 11 | **🟢 PROMOTED (Gate G11)** |
| **—** | `EXP-16` | Automated Dual-Cadence Ingestion & Freshness Daemon | Data Ops & MLOps | 0.95 | 2.0 | 0.75 | 0.20 (2.5 wks) | **71.3** | `CHARTER-EXP-16` | Phase 11 | **🟢 PROMOTED (Gate G11)** |
| **1** | `EXP-14` | Active Learning & Targeted Sourcing for Sparse Cells | Active Learning | 0.35 | 3.0 | 0.70 | 0.44 (5.5 wks) | **55.3** | `CHARTER-EXP-14` | Phase 12 (Immediate) | **Chartered / Next (T12.01)** |
| **2** | `EXP-15` | Counterfactual Negotiation Scenario Modeling (PT4) | Product / UQ | 0.65 | 2.5 | 0.70 | 0.65 (8 wks) | **35.2** | `CHARTER-EXP-15` | Phase 12 (Immediate) | **Chartered / Next (T12.02)** |
| **3** | `ENG-17` | Distributed High-Throughput Batch Inference Pipeline | Performance | 0.20 | 1.5 | 0.95 | 0.35 (4.5 wks) | **8.1** | *N/A (Standard Eng)* | Phase 13 | Backlog |
| **4** | `UX-18` | Interactive Visual Explanations for Slice Uncertainty | Front-End / UX | 0.50 | 1.0 | 0.85 | 0.50 (6 wks) | **8.5** | *N/A (UX Prototype)* | Phase 13 | Backlog |

---

## 3. Detailed Item Breakdowns

### 3.1 EXP-13: Slice-Adaptive Conformal Prediction Intervals (Completed & Promoted — Gate G11)
- **Charter Reference:** [`docs/research/experiment-charters-phase10.md#2-charter-exp-13-slice-adaptive-conformal-prediction-intervals-group-conditional-calibration`](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/research/experiment-charters-phase10.md#2-charter-exp-13-slice-adaptive-conformal-prediction-intervals-group-conditional-calibration)
- **Outcome:** **🟢 PROMOTE / RATIFIED AT GATE G11.** Implemented `SliceAdaptiveConformalRegressor` with Empirical Bayes shrinkage (`compintel.uncertainty.slice_conformal`). Verified 89.05% slice variance reduction, 12/12 slices in $[76\%, 84\%]$, +0.95% median width growth, and +1.95 µs/sample latency overhead (`docs/research/slice-conformal-exp13.md`, `experiments/results/slice_conformal_report.json`). Promoted to production champion bundle.

### 3.2 EXP-16: Automated Dual-Cadence Ingestion & Freshness Daemon (Completed & Promoted — Gate G11)
- **Charter Reference:** [`docs/research/experiment-charters-phase10.md#3-charter-exp-16-automated-dual-cadence-source-ingestion--freshness-daemon`](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/research/experiment-charters-phase10.md#3-charter-exp-16-automated-dual-cadence-source-ingestion--freshness-daemon)
- **Outcome:** **🟢 PROMOTE / RATIFIED AT GATE G11.** Implemented `DualCadenceIngestionDaemon` and `AutomatedCanary` (`compintel.ingestion.daemon`). Verified 0 staleness violations across 14 statutory sources over continuous 30-day trial, p95 intake latency 11.35 min <= 15 min, 100% canary quarantine accuracy with 0.00% false accepts, and zero PII retained (`docs/research/ingestion-daemon-exp16.md`, `experiments/results/ingestion_daemon_report.json`). Promoted to production operational architecture.

### 3.3 EXP-14: Active Learning & Targeted Sourcing for Sparse Cells (Rank 1 Active — RICE: 55.3)
- **Charter Reference:** [`docs/research/experiment-charters-phase10.md#4-charter-exp-14-active-learning--targeted-data-sourcing-for-sparse-realization-cells`](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/research/experiment-charters-phase10.md#4-charter-exp-14-active-learning--targeted-data-sourcing-for-sparse-realization-cells)
- **Problem:** 18 out of 96 market cells currently have $N < 15$ realized observations, leading to elevated epistemic uncertainty, wider prediction intervals ($0.41$ median ratio), and higher abstention trigger rates.
- **Proposed Solution:** An active learning utility model prioritizing acquisition based on posterior variance, user query volume, and cell sparsity. Routes recruitment bounties and syndication partnerships directly to under-represented cells.
- **Value Proposition:** Narrows prediction intervals in high-demand, high-uncertainty roles (e.g. Staff Engineers, specialized AI/ML roles) with $50\%$ fewer total required samples than uniform sampling.
- **Pre-Registered Gate:** Average interval width on target sparse cells narrows by $\ge 20\%$; cell abstention drops by $\ge 15\%$; nominal coverage maintained in $[75\%, 85\%]$. Target: **Phase 12 (Task T12.01)**.

### 3.4 EXP-15: Counterfactual Negotiation & Offer Scenario Modeling (PT4) (Rank 2 Active — RICE: 35.2)
- **Charter Reference:** [`docs/research/experiment-charters-phase10.md#5-charter-exp-15-counterfactual-negotiation--offer-scenario-modeling-pt4-prototype`](file:///c:/Users/Lenovo/Downloads/Salary%20Prediction/docs/research/experiment-charters-phase10.md#5-charter-exp-15-counterfactual-negotiation--offer-scenario-modeling-pt4-prototype)
- **Problem:** Over $26\%$ of pilot user feedback expressed a strong desire for interactive counterfactual queries (*"What if I relocate?"*, *"What if I negotiate 4 LPA more cash?"*), which currently trigger safe abstentions under Rule `R-MD-08`.
- **Proposed Solution:** Develop a constrained counterfactual optimization engine (Target Branch PT4) that computes monotonic compensation frontiers with explicit conformal bounds.
- **Value Proposition:** Transforms ArthaIQ from a passive compensation lookup engine into an interactive decision-support tool while maintaining mathematical honesty and zero lone numbers.
- **Pre-Registered Gate:** Monotonicity satisfaction $\ge 98\%$; counterfactual interval coverage $[75\%, 85\%]$; zero point-estimate advice. Target: **Phase 12 (Task T12.02)**.

---

## 4. Traceability Matrix: Feedback Clusters to Backlog Items

Every backlog item directly originates from and addresses empirical evidence gathered during the Phase 10 pilot:

| Feedback Cluster | Volume (%) | Primary Sentiment | Addressed By | Backlog Priority |
|:---|:---:|:---:|:---|:---:|
| **Niche/Senior Interval Precision** | 34.1% | Mixed ($42\%$ positive) | `EXP-13` (Promoted) & `EXP-14` (Active Learning) | **P0 (Phase 12 T12.01)** |
| **Interactive Counterfactuals** | 26.8% | Neutral ($78\%$ feature req) | `EXP-15` (Counterfactual Modeling PT4) | **P0 (Phase 12 T12.02)** |
| **Real-Time Data Freshness** | 22.0% | Positive ($65\%$ positive) | `EXP-16` (Promoted Daemon) | **DONE (Gate G11)** |
| **Trust, Transparency & UX** | 17.1% | Strongly Positive ($88\%$ pos) | `UX-18` (Interactive Visual Explanations) | **P2 (Design Polish)** |

---

## 5. Implementation Roadmap & Resource Allocation

```mermaid
gantt
    title ArthaIQ Post-Pilot Engineering & Research Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 11 (Completed & Promoted)
    EXP-13 Slice-Adaptive Conformal     :done, exp13, 2026-10-22, 2026-10-22
    EXP-16 Freshness Ingestion Daemon   :done, exp16, 2026-10-22, 2026-10-22
    Gate G11 Champion Promotion         :milestone, g11, 2026-10-22, 0d
    section Phase 12 (Targeted Sourcing & Scenarios)
    EXP-14 Active Learning Sparse Cells :active, exp14, 2026-10-23, 21d
    EXP-15 Counterfactual PT4 Engine    :active, exp15, 2026-10-25, 28d
    section Phase 13 (Advanced Architecture)
    ENG-17 Distributed Batch Inference  :eng17, 2026-11-20, 28d
    UX-18 Visual Slice Explanations     :ux18, 2026-12-01, 28d
```

All implementations remain bound by the **Production Readiness Review** and must achieve Gate clearance before merging into main.
