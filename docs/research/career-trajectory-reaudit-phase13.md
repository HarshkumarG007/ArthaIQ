# Career Trajectory Feature Re-evaluation (Phase 13, EXP-TRAJ-r, CHARTER-CAREER-TRAJ-r)

> **Scope:** Longitudinal Panel Depth Audit and Empirical Data-Growth Re-evaluation of Dynamic Career Trajectory Features (Career Velocity, Promotion Acceleration, Tenure Stability) vs Static Baseline on Cumulative Non-Synthetic Production Panel.
> **Governing Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-02, R-MD-03, R-MD-04, R-MD-05, R-MD-09, R-MD-11, R-MD-15, R-UQ-01, R-UQ-05 · ADR-0008 Section 6 · Task T13.05.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `EXPTRAJR-20261023075026` |
| **Charter ID** | `CHARTER-CAREER-TRAJ-r` |
| **Experiment ID** | `EXP-TRAJ-r` |
| **Task ID** | `T13.05` |
| **Generated At** | `2026-10-23T07:50:26.841036+00:00` |
| **Git Commit** | `ced0d62c` |
| **Cumulative Production Panel** | `219 observations` (`219` verified non-synthetic) |
| **Realized Observation Calendar Span** | `5.9 calendar months` (`179 days`, `2026-10-22` to `2027-04-19`) |
| **Pre-Registered Span Requirement** | $\ge 12.0$ calendar months |
| **Span Sufficiency Status** | `DEFER` (Deficit: `6.1 calendar months`) |
| **Longitudinal Milestone Records** | `0 records` (Required: $\ge 100$ records, Deficit: `100 records`) |
| **Gate 1 Feasibility Audit** | **`INSUFFICIENT_SPAN_DEFER`** |
| **Overall Re-audit Verdict** | **`DEFER`** |
| **Production Champion Status** | **`RETAINED_UNMODIFIED (Rung F Level 2 Conformal CatBoost)`** |
| **Next Scheduled Trigger Date** | `2028-06-30 (Phase 14 B2B Syndication Milestone)` |
| **Next Audit Trigger Condition** | `Longitudinal panel >= 12.0 calendar months AND verified longitudinal records >= 100` |

---

## 1. Executive Summary & Governance Verdict

**Final Verdict:** **`DEFER`**

Gate 1 Longitudinal Feasibility DEFERRED: Cumulative non-synthetic production panel spans 5.9 calendar months (179 days, threshold: >= 12.0 months) with 0 verified records with populated longitudinal milestone dates (threshold: >= 100 records). In strict accordance with CHARTER-CAREER-TRAJ-r and Rule R-MD-09, empirical modeling is held in abeyance to prevent premature model training and survivor/recall bias on truncated career histories. Production Champion Rung F Level 2 Conformal CatBoost is strictly retained unmodified without career trajectory complexity or collection burden. Next audit pre-registered for Phase 14 B2B syndication intake (estimated mid-2028).

> [!IMPORTANT]
> **Governance Determination:** In strict adherence to **Rule `R-MD-09`** and **`CHARTER-CAREER-TRAJ-r`**, candidate feature re-evaluations must not proceed without meeting the pre-registered data feasibility criteria. The current production panel spans `5.9 calendar months` (required: $\ge 12.0$ calendar months), with `0 records` possessing verified milestone dates following the recent Task T13.04 schema deployment. Premature empirical training on truncated career spans creates severe recall bias and risks false modeling conclusions. Production Champion Rung F Level 2 Conformal CatBoost is strictly retained unmodified. Next audit trigger is pre-registered for the Phase 14 B2B syndication milestone (estimated mid-2028).

---

## 2. Gate 1: Longitudinal Panel Depth & Milestone Telemetry Audit

Under **Rule `R-MD-09`**, **Rule `R-MD-01`**, and **`CHARTER-CAREER-TRAJ`**, dynamic trajectory modeling requires genuine longitudinal depth. In the Indian tech market, compensation appraisals and promotion cycles occur on an annualized (12-month) or biennial (24-month) cadence. A panel spanning under 12 calendar months captures at most half of an appraisal cycle, rendering annualized velocity and promotion-acceleration metrics unidentifiable and statistically biased.

| Feasibility Dimension | Pre-Registered Standard | Empirical Value | Gate 1 Evaluation |
|:---|:---|:---|:---|
| **Observation Calendar Span** | $\ge 12.0$ calendar months | `5.9 calendar months` (`179 days`) | `DEFER (Deficit: 6.1 calendar months)` |
| **Populated Milestone Records** | $\ge 100$ records | `0 records` | `DEFER (Deficit: 100 records)` |
| **Synthetic Isolation Guard (`R-MD-11`)** | `100.0%` verified non-synthetic | `219 / 219` (`100.0%`) | `PASS (Zero Synthetic Data)` |
| **Privacy Floor & Consent (ADR-0008)** | Voluntary unbundled consent ($k_{\min} \ge 5$) | `100.0%` compliant with ADR-0008 Section 6 | `PASS (DPDPA 2023 Compliant)` |

> **Gate 1 Diagnostic:** Panel depth audit triggers **`INSUFFICIENT_SPAN_DEFER`**. The cumulative non-synthetic panel has accumulated `219 observations` over `5.9 calendar months` since daemon launch. Voluntary longitudinal telemetry (`career_start_date`, `last_promotion_date`, `right_censored_exit_flag`) deployed in Task T13.04 has accumulated `0 records` of mature multi-cycle history. Feasibility retest is formally deferred until both panel span and record depth thresholds are satisfied.

---

## 3. Candidate Trajectory Feature Specifications & Abeyance Status

The two candidate trajectory representations defined in **`CHARTER-CAREER-TRAJ`** remain held in abeyance pending longitudinal data maturity:

1. **Variant A (Career Velocity):**
   - **Formulation:** $\text{Velocity} = \frac{\text{Seniority Ordinal}}{\max(\text{YoE}, 1.0)}$.
   - **Mechanism:** Annualized rate of ladder climbing across standard engineering grades (JR to PRINCIPAL).
   - **Abeyance Rationale:** Without longitudinal start dates, YoE is self-reported and cannot distinguish fast-track early promotions from tenure stagnation.

2. **Variant B (Composite Trajectory Vector):**
   - **Formulation:** Vector bundle comprising career velocity, tenure stability (median employer duration), promotion acceleration vs peer cohort, and company tier mobility.
   - **Mechanism:** Captures acceleration ($\partial^2 \text{level} / \partial t^2$) and employer tier escalation (IT Services to Tier 1 Product).
   - **Abeyance Rationale:** Requires at least two verified career transition milestones separated by $\ge 12.0$ calendar months to calculate non-zero acceleration.

| Architecture Variant | Gate 1 Feasibility Status | Benchmark Status | Pre-Registered Verdict |
|:---|:---:|:---:|:---:|
| **Champion Baseline (Rung F Level 2)** | N/A (Production Champion) | Retained Unmodified | **`RETAINED`** |
| **Variant A: Career Velocity** | `INSUFFICIENT_SPAN_DEFER` | Gated (Under-spanned) | **`DEFER`** |
| **Variant B: Composite Trajectory Vector** | `INSUFFICIENT_SPAN_DEFER` | Gated (Under-spanned) | **`DEFER`** |

---

## 4. Production Champion Invariance & Operational Assessment

1. **Zero Serving Disruption:** Production Champion Rung F Level 2 Conformal CatBoost is retained strictly unmodified.
2. **Zero Feature Collection Friction:** The core B2C salary prediction tool (/v1/predict) continues to require only 4 lightweight inputs (role family, seniority, location, total YoE), eliminating user abandonment.
3. **Microsecond Latency Preservation:** Champion CatBoost inference executes in `< 1.0 ms` p95 CPU latency, well within the 10.0 ms serving budget and 200.0 ms overall application SLA.
4. **Zero Model Complexity Inflation:** Retains static tenure and quadratic Mincerian experience curve without multi-period feature tables or temporal join machinery.

---

## 5. Governance, Privacy & DPDPA 2023 Compliance

All longitudinal schema fields deployed in Task T13.04 operate under strict regulatory safeguards established in **ADR-0008 Section 6** and the **DPDPA 2023 Regulatory Impact Note** (`docs/legal/dpdpa-longitudinal-schema-amendment.md`):

- **Strict Optionality & Default Null:** `career_start_date`, `last_promotion_date`, and `right_censored_exit_flag` remain strictly optional across all contribution endpoints.
- **Unbundled Research Consent:** Explicit voluntary consent checkbox with purpose specification for longitudinal career trajectory modeling.
- **24-Month Retention Window:** Rolling 24-month retention schedule from submission timestamp; expired observations undergo automatic anonymization.
- **Automated Erasure Cascade:** Upon contributor receipt key revocation (`DELETE /v1/contributions/{key}`), longitudinal fields are purged within 100 milliseconds.

---

## 6. Pre-Registered Next Audit Triggers & Phase 14 Roadmap

Per **`CHARTER-CAREER-TRAJ-r`**, the next empirical re-audit of dynamic career trajectory features will be triggered when BOTH of the following conditions are met:

1. **Calendar Span Trigger:** Non-synthetic production observation panel spans $\ge 12.0$ calendar months (estimated Phase 14 / mid-2028).
2. **Milestone Volume Trigger:** Voluntary contributor panel accumulates $\ge 100$ verified records with populated `career_start_date` and `last_promotion_date` milestones.
3. **Milestone Date:** Target re-audit scheduled for `2028-06-30` or upon Phase 14 B2B syndication intake.

> [!NOTE]
> Until both trigger thresholds are verified by automated audit, any speculative trajectory feature integration remains rejected to protect production model stability and prevent statistical hallucination.
