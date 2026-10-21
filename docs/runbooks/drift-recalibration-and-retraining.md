# ArthaIQ Drift Triggers, Conformal Recalibration & Retraining Runbook

> **Governance & Operational Standard:** PRD FR-13, NFR-07, US-08, ADR-0004, ADR-0009, Rule `R-MD-14`, Rule `R-UQ-03`.  
> **Target Release:** Public Beta Pilot (Phase 10, Task T10.05).  
> **Last Ratified:** October 2026.  
> **Classification:** Internal Engineering & Operational Runbook.

---

## 1. Executive Scope & Architectural Invariants

### 1.1 Drift Taxonomy in Compensation Intelligence
In production compensation intelligence systems, model performance and interval coverage degrade across three distinct statistical mechanisms:

1. **Covariate Shift ($P(X)$):**
   - The distribution of incoming profile queries shifts over time (e.g. surge in AI/ML engineering roles, geographic migration toward Hyderabad/Pune, or changes in years of experience mix).
   - Base conditional relationships may hold, but empirical interval width and localized density shift.
2. **Concept Drift ($P(Y \mid X)$):**
   - Market compensation dynamics change given the same profile (e.g. post-pandemic salary normalization, macro inflation, statutory wage floor adjustments).
   - Point estimates drift from realized offers and conformal coverage breaks if uncorrected.
3. **Prior Probability Shift ($P(Y)$):**
   - Overall wage levels expand or contract across the entire tech sector.

### 1.2 The Conformal Exchangeability Invariant (Rule `R-UQ-03`)
Split conformal prediction intervals (CQR; Romano et al., 2019) guarantee finite-sample marginal coverage:
$$\mathbb{P}\left(Y_{n+1} \in \hat{C}(X_{n+1})\right) \ge 1 - \alpha$$
under the foundational assumption of **exchangeability** between calibration data $(X_1, Y_1), \dots, (X_n, Y_n)$ and live queries $(X_{n+1}, Y_{n+1})$.

When distribution drift violates exchangeability:
- Empirical coverage drifts away from the nominal $80\%$ target.
- **Rule `R-UQ-03` Mandate:** Conformal guarantees must never be treated as static. When moderate drift occurs, the operational pipeline must execute **Automated Conformal Recalibration**—updating the nonconformity score distribution on recent realized observations to recompute $\hat{q}$ without the latency and cost of full retraining.

### 1.3 Champion-Challenger Lifecycle (Rule `R-MD-14`)
When distribution drift is severe ($\text{PSI} \ge 0.25$ or continuous $\text{KS } D \ge 0.12$), recalibration alone is insufficient. The system triggers the **Challenger Retraining & Shadow Evaluation Protocol**:
- The current **Champion** model continues serving $100\%$ of active user traffic.
- A candidate **Challenger** model is trained on expanded canonical realization data.
- The Challenger runs in **Shadow Mode** evaluating live realization batches.
- The Challenger must pass all 5 pre-registered acceptance gates before atomic promotion.
- In-memory rollback buffers in `ServingModelManager` are preserved to enable immediate hot rollback if live telemetry breaks.

---

## 2. Drift Monitoring Architecture & Telemetry

### 2.1 Statistical Testing Rubric

```
                           +-------------------------------+
                           | Realized Queries / Submissions|
                           +---------------+---------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
         [Categorical Features]                        [Continuous Features]
      (role_family, location, level)               (yoe_total, current_salary)
                    |                                             |
                    v                                             v
         Population Stability Index                   Two-Sample Kolmogorov-Smirnov
            (PSI, Quantile Bins)                       (KS Statistic D, p-value)
                    |                                             |
                    +----------------------+----------------------+
                                           |
                                           v
                          +--------------------------------+
                          | Evaluated Trigger Tier Matrix   |
                          +--------------------------------+
```

1. **Population Stability Index (PSI):**
   Evaluated across discrete categorical features (`role_family`, `seniority_level`, `metro_location`) and binned continuous distributions:
   $$\text{PSI} = \sum_{k=1}^K \left(P_{\text{target}}(k) - P_{\text{baseline}}(k)\right) \times \ln\left(\frac{P_{\text{target}}(k)}{P_{\text{baseline}}(k)}\right)$$
2. **Kolmogorov-Smirnov (KS) Two-Sample Test:**
   Evaluated across continuous numeric inputs (`yoe_total`, `yoe_current_role`):
   $$D = \sup_x \left|F_{\text{baseline}}(x) - F_{\text{target}}(x)\right|$$
3. **Zero-PII Metric Guarantee (Rules `R-CD-06`, `R-DA-07`):**
   Telemetry records feature names, binned frequencies, and computed divergence statistics. Zero individual candidate identifiers, employer names, or raw compensation amounts enter drift metrics or logs.

---

## 3. Multi-Tier Trigger Matrix & Documented Actions

| Trigger Tier | Statistical Condition | Urgency & Alert | Documented Operational Action | Verification Criterion |
|---|---|:---:|---|---|
| **Tier 0: STABLE** | $\text{PSI} < 0.10$ and $\text{KS } D < 0.05$ | `INFO`<br>🟢 Nominal | **Nominal Monitoring:** Collect realization telemetry; log weekly drift summaries; no intervention required. | System health remains `HEALTHY`. |
| **Tier 1: MODERATE DRIFT** | $0.10 \le \text{PSI} < 0.25$ or $0.05 \le \text{KS } D < 0.12$ | `WARNING`<br>🟡 Warning | **Automated Conformal Recalibration:**<br>1. Ingest recent 30-day realized calibration observations.<br>2. Compute nonconformity scores $E_i = \max(q_{10}(X_i) - Y_i, Y_i - q_{90}(X_i))$.<br>3. Recompute finite-sample quantile $\hat{q}_{\text{recal}} = \text{Quantile}_{1-\alpha}(E)$.<br>4. Hot-patch active model bundle calibration parameters.<br>5. Confirm post-recalibration coverage restores to $[78\%, 82\%]$. | Coverage restored in next realization evaluation cohort. |
| **Tier 2: SEVERE DRIFT** | $\text{PSI} \ge 0.25$ or $\text{KS } D \ge 0.12$ | `CRITICAL`<br>🔴 Alarm | **Challenger Shadow Training & Promotion Review:**<br>1. Dispatch `CRITICAL` drift alert via `AlertManager`.<br>2. Ingest latest canonical snapshot (`make reproduce-data`).<br>3. Train candidate Challenger CatBoost quantile model.<br>4. Run shadow batch evaluation alongside Champion.<br>5. Audit Challenger against 5 pre-registered promotion gates.<br>6. Atomically promote Challenger if all gates pass; preserve hot rollback buffer. | Challenger promoted or emergency fallback initiated. |

---

## 4. Execution Protocols

### Protocol A: Automated Conformal Recalibration (Tier 1 Action)

1. **Trigger Condition:** Drift runner reports $0.10 \le \text{PSI} < 0.25$ on any core feature.
2. **Execution Steps:**
   ```bash
   # Run automated drift audit and recalibration
   uv run python scripts/run_drift_recalibration.py --induce-drift role_family --drift-severity moderate
   ```
3. **Mathematical Recalibration Logic:**
   - Base CatBoost tree weights remain unchanged (zero retraining latency).
   - Residual nonconformity scores are evaluated over the recent realization set $\mathcal{D}_{\text{recal}}$:
     $$E_i = \max\left(P_{10,\text{base}}(X_i) - y_i, \, y_i - P_{90,\text{base}}(X_i)\right)$$
   - The finite-sample correction is recomputed for $\alpha = 0.20$:
     $$k = \left\lceil (n_{\text{recal}} + 1)(1 - \alpha) \right\rceil, \quad \hat{q} = E_{(k)}$$
   - Calibrated bounds update:
     $$\hat{C}_{\text{recal}}(X) = \left[\max\left(0.5, P_{10}(X) - \hat{q}\right), \, \max\left(P_{10}, P_{90}(X) + \hat{q}\right)\right]$$
4. **Post-Recalibration Verification:**
   - Empirical coverage must satisfy $75.0\% \le \text{Coverage} \le 85.0\%$.
   - Crossing rate must remain $\le 0.5\%$.
   - Conformal correction delta $|\Delta \hat{q}|$ must be logged to Prometheus.

---

### Protocol B: Challenger Shadow Training & Promotion (Tier 2 Action)

1. **Trigger Condition:** Drift runner reports $\text{PSI} \ge 0.25$ or $\text{KS } D \ge 0.12$.
2. **Execution Steps:**
   ```bash
   # Trigger severe drift evaluation and shadow challenger assessment
   uv run python scripts/run_drift_recalibration.py --induce-drift role_family --drift-severity severe
   ```
3. **Challenger Acceptance Gates (Must Pass 5 of 5):**
   - **Gate 1 (Pinball Loss Improvement):** $\Delta \mathcal{L}_{\text{pinball}} = \mathcal{L}_{\text{challenger}} - \mathcal{L}_{\text{champion}} \le 0.0$ (no accuracy regression).
   - **Gate 2 (Empirical Coverage Stability):** Realized coverage on holdout cohort strictly within $[75.0\%, 85.0\%]$.
   - **Gate 3 (Crossing Invariant, Rule `R-UQ-05`):** Monotone quantile crossing violations $\le 0.5\%$.
   - **Gate 4 (Interval Usefulness, Rule `R-UQ-04`):** Normalized median width ratio $\le 0.45$.
   - **Gate 5 (Fairness Parity, Rule `R-FA-01`):** Passes Fairness Audit v2 (disparity ratio $\le 1.30$, coverage gap $\le 0.15$, zero demographic proxies).
4. **Atomic Promotion Mechanism:**
   - `ServingModelManager.load_and_promote(challenger_path)` loads new bundle.
   - Executes startup verification smoke test.
   - Pushes former Champion into `_previous_bundle` slot (guaranteeing sub-millisecond rollback).
   - Atomic pointer swap: zero downtime, zero in-flight dropped requests.

---

### Protocol C: Emergency Rollback & Fallback

If post-promotion monitoring detects anomalies in the promoted Challenger:
1. Trigger hot rollback via serving API or CLI:
   ```bash
   uv run python scripts/run_rollback_rehearsal.py
   ```
2. `ServingModelManager.rollback()` reverts to the verified previous Champion bundle within $< 1.0\text{ ms}$ (SLA: $\le 30\text{ seconds}$).
3. Telemetry publishes `model_rollback_executed` event; maintainers are notified.

---

## 5. Prometheus Telemetry & Telemetry Registry

The drift and recalibration engine emits standard OpenMetrics telemetry:

| Metric Name | Type | Labels | Description |
|---|:---:|---|---|
| `arthaiq_feature_drift_psi` | Gauge | `feature_name`, `method` | Population Stability Index divergence value. |
| `arthaiq_feature_drift_ks` | Gauge | `feature_name` | Kolmogorov-Smirnov test statistic. |
| `arthaiq_drift_trigger_tier` | Gauge | None | Active trigger tier ($0=\text{STABLE}, 1=\text{RECALIBRATE}, 2=\text{RETRAIN}$). |
| `arthaiq_conformal_quantile_value` | Gauge | `method` | Active conformal correction factor $\hat{q}$. |
| `arthaiq_challenger_pinball_loss` | Gauge | `model_version` | Shadow Challenger mean pinball loss. |
| `arthaiq_drift_alerts_total` | Counter | `severity`, `feature` | Total operational drift alerts dispatched. |
