# Skills TF-IDF Power-Gated Retest (Phase 13, EXP-09r, CHARTER-EXP-09r)

> **Scope:** Statistical Power Analysis and Empirical Data-Growth Re-evaluation of Skills Feature Modeling (TF-IDF vs Baseline) on Cumulative Non-Synthetic Production Panel.
> **Governing Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-02, R-MD-04, R-MD-05, R-MD-09, R-MD-11, R-UQ-01, R-UQ-05 · Task T13.03.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `EXP09R-SKILLS-20261023041519` |
| **Charter ID** | `CHARTER-EXP-09r` |
| **Task ID** | `T13.03` |
| **Generated At** | `2026-10-23T04:15:19.321666+00:00` |
| **Git Commit** | `23a6f62a` |
| **Operational Window** | `6.0 months` post-EXP-16 |
| **Observation Panel** | `219` records (`219` verified non-synthetic) |
| **Evaluation Partitions** | Train: `0`, Calibrate: `0`, Eval (`select`): `0` |
| **Gate 1 Power Feasibility** | **`UNDERPOWERED_DEFER`** |
| **Gate 1 Passed** | `False` |
| **Modeling Executed** | `False` |
| **Variant A Verdict** | **`DEFER`** |
| **Variant B Verdict** | **`REJECT`** |
| **Overall Re-audit Verdict** | **`DEFER`** |
| **Champion Status** | **`RETAINED_UNMODIFIED`** |

---

## 1. Executive Summary & Governance Verdict

**Final Verdict:** `DEFER`

Statistical power analysis for EXP-09r confirms that the current 6-month non-synthetic production panel (N = 219 observations) is underpowered to test pre-registered effect threshold (delta pinball loss <= -0.05 LPA) with 80.0% power (achieved power: 45.6%, deficit: 281 records, 54.4% Type II error risk). In accordance with Rule R-MD-01, empirical re-training is formally DEFERRED until panel achieves N >= 500 records. Variant B (sentence-transformers on CPU) remains REJECTED due to CPU serving latency constraints. Champion Rung F Level 2 Conformal CatBoost is strictly retained unmodified.

> **Governance Decision:** Ratify formal Gate 1 DEFER for Variant A under CHARTER-EXP-09r. Maintain Champion Rung F CatBoost without skills text overhead. Schedule next power audit for panel milestone N >= 500.

---

## 2. Gate 1: Non-Synthetic Panel Statistical Power & Sufficiency Audit

Under **Rule `R-MD-01`**, **Rule `R-MD-09`**, and **`CHARTER-EXP-09`**, candidate architecture re-evaluations must not be conducted on underpowered panels. Evaluating complex feature extraction pipelines without adequate sample size inflates Type II error rates (failing to detect genuine improvements) and produces excessively wide confidence intervals that span zero spuriously.

The minimum detectable effect size pre-registered in `CHARTER-EXP-09` is $\delta = -0.0500\text{ LPA}$ mean pinball loss reduction. With paired difference variance $\sigma_d = 0.4000\text{ LPA}$, significance level $\alpha = 0.05$ (two-sided, $z_{1-\alpha/2} = 1.960$), and target power $1 - \beta = 0.80$ ($80.0\%$, $z_{1-\beta} = 0.842$), the sample size requirement is governed by the paired t-power formula:

$$N_{\text{req}} = \frac{(z_{1-\alpha/2} + z_{1-\beta})^2 \cdot \sigma_d^2}{\delta^2} = \frac{(1.960 + 0.842)^2 \cdot (0.4000)^2}{(0.0500)^2} \approx 500 \text{ observations}$$

| Statistical Power Parameter | Pre-Registered Standard | Empirical Value | Audit Evaluation |
|:---|:---|:---|:---|
| **Minimum Detectable Effect Size ($\delta$)** | `-0.0500 LPA` | `-0.0500 LPA` | Pre-registered keep threshold |
| **Paired Difference Std Dev ($\sigma_d$)** | `0.4000 LPA` | `0.4000 LPA` | Calibrated from Phase 7 empirical variance |
| **Significance Level ($\alpha$)** | `0.05` (95% CI) | `0.05` (two-sided) | Rule `R-MD-01` bootstrap CI standard |
| **Target Statistical Power ($1 - \beta$)** | $\ge 80.0\%$ | `80.0%` | Standard power threshold |
| **Required Sample Size ($N_{\text{req}}$)** | $N \ge 500$ records | `500` records | Statistically powered threshold |
| **Current Panel Size ($N$)** | $N \ge 500$ records | `219` records | DEFER |
| **Verified Non-Synthetic Records** | 100.0% verified non-synthetic | `219 / 219` (100.0%) | PASS (`R-MD-11`) |
| **Achieved Statistical Power** | $\ge 80.0\%$ | `45.6%` | UNDERPOWERED |
| **Sample Size Deficit** | `0` records | `281` records | 56.2% deficit |

> **Gate 1 Diagnostic:** Gate 1 feasibility deferred: non-synthetic panel size N = 219 is underpowered relative to required threshold (N >= 500), achieving only 45.6% statistical power (deficit: 281 observations, 54.4% Type II error risk). Retest deferred under Rule R-MD-01.

### Empirical Statistical Power Trajectory Curve

| Panel Size ($N$) | Statistical Power ($1 - \beta$) | Feasibility Qualification Status |
|:---|:---:|:---|
| `50` observations | `14.1%` | Severely Underpowered |
| `100` observations | `23.9%` | Severely Underpowered |
| `150` observations | `33.4%` | Underpowered (DEFER Trigger) |
| `200` observations | `42.4%` | Underpowered (DEFER Trigger) |
| `219` observations **(Current Live Panel)** | `45.6%` | Underpowered (DEFER Trigger) |
| `300` observations | `58.1%` | Underpowered (DEFER Trigger) |
| `400` observations | `70.5%` | Approaching Sufficiency |
| `500` observations | `79.8%` | Approaching Sufficiency |
| `750` observations | `92.8%` | Powered for Pre-Registered Testing |
| `1000` observations | `97.7%` | High Power |

---

## 3. Comparative Modeling & Algorithmic Performance Matrix

> **Modeling Status:** Full model re-training was deliberately bypassed under pre-registered Gate 1 power gating. Running empirical model comparisons on $N = 219$ records achieves only 45.6% statistical power, yielding an unacceptable $54.4\%$ risk of Type II error. To prevent publication of false negative conclusions and to respect Rule `R-MD-01`, re-training is deferred until panel achieves $N \ge 500$ records.

| Architecture Variant | Gate 1 Power Status | Modeling Execution | Pre-Registered Verdict |
|:---|:---:|:---:|:---:|
| **Champion Baseline (Rung F Level 2)** | N/A (Production Champion) | Retained Unmodified | **`RETAINED`** |
| **Variant A: Curated Taxonomy & TF-IDF** | `UNDERPOWERED_DEFER` (45.6% power) | Gated (Underpowered) | **`DEFER`** |
| **Variant B: Sentence-Transformer Embeddings (CPU)** | Architecturally Disqualified | Skipped | **`REJECT`** |

---

## 4. Variant B: Sentence-Transformer Embeddings (CPU) Architecture Rejection

Per **`CHARTER-EXP-09`** and **Phase 13 pre-registration**, Variant B (dense sentence-transformer embeddings running on CPU) remains **`REJECT`** without requiring data-growth re-evaluation. The permanent technical grounds for this rejection are:

1. **Serving Latency SLA Violation:** Evaluating dense sentence encoders (e.g., all-MiniLM-L6-v2) on CPU environments incurs `> 50.0 ms` p95 latency, consuming over 25% of the total 200 ms end-to-end request budget.
2. **Pure CPU Production Constraint (Rule `R-CD-01`):** Production serving is strictly constrained to lightweight CPU containers. Introducing GPU clusters or heavy PyTorch/ONNX runtime dependencies solely for skills text embeddings violates cost-efficiency and operational simplicity.
3. **Zero Predictive Margin:** Phase 7 empirical evaluation demonstrated that Variant B produced worse pinball loss (+0.1930 LPA) than tabular baselines, as salary bands in Indian tech are primarily driven by tier, role family, and seniority rather than micro-variations in skill token phrasing.

---

## 5. Architectural Implications & Next Scheduled Audit Triggers

1. **Production Champion Invariance:** Rung F Level 2 Conformal CatBoost is strictly retained as the production champion without modifications or text overhead.
2. **Operational Simplicity Preservation:** Tabular CatBoost CPU inference operates at `< 1.0 ms` p95 latency with a compact `< 15.0 MB` bundle size.
3. **Pre-Registered Next Audit Trigger:**
   - **Target Panel Size:** `$N \ge 500$` verified non-synthetic observations.
   - **Scheduled Audit Date:** `2027-04-21` (6 months).
   - **Trigger Milestone:** `Non-synthetic cumulative panel size N >= 500 verified records`.
   - **Audit Action:** Rerun Gate 1 power analysis; if $N \ge 500$, execute full paired bootstrap model training.

---

*Report generated by `compintel.evaluation.skills_reaudit` on 2026-10-23T04:15:19.321666+00:00*