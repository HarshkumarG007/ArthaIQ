# Research Report: Quantile Model Ensembling & Stacking Experiment (T7.06)

| Metadata | Value |
| :--- | :--- |
| **Report ID** | `EXP-ENSEMBLE-20261019-083346` |
| **Charter ID** | `CHARTER-ENSEMBLING-STACKING` |
| **Experiment ID** | `EXP-ENSEMBLE-01` |
| **Task Reference** | Task T7.06 (Phase 7 Advanced Modeling) |
| **Evaluation Split** | `select` (Rule `R-MD-02`: Locked) |
| **Git Commit** | `eaa391e5` |
| **Generated At** | `2026-10-19T08:33:46.834315+00:00` |
| **Overall Verdict** | **`DEFER`** |
| **Modeling Executed** | `False` |
| **Production Champion Retained** | `True` |

---

## 1. Executive Summary & Governance Verdict

**Verdict:** `DEFER`

Gate 1 Feasibility DEFERRAL: The non-synthetic observation panel contains 3 records (1 in train), failing the pre-registered sufficiency threshold of >= 100. Cross-validated meta-learner stacking and multi-model ensembling on an underpowered panel is mathematically unidentifiable and prone to extreme variance inflation. Under Charter CHARTER-ENSEMBLING-STACKING deferral criteria, ensembling is formally DEFERRED. The production champion (Rung F L2 Conformal CatBoost) remains strictly unchanged.

> **Governance Decision:** DEFER: Insufficient non-synthetic observations to train or evaluate an ensemble model. Champion Rung F L2 Conformal CatBoost is retained without ensembling overhead.

---

## 2. Gate 1 Feasibility & Sample Sufficiency Audit

Under **Rule `R-MD-09`** and **`CHARTER-ENSEMBLING-STACKING`**, multi-model stacking and
meta-regression require a minimum sample size to avoid severe variance inflation and
collinear over-fitting on small batches.

| Audit Field | Audit Result | Requirement / Governance Standard |
| :--- | :--- | :--- |
| **Feasibility Status** | **`INSUFFICIENT_SAMPLE_SIZE`** | `FEASIBLE` required to proceed |
| **Total Records** | `3` records | $\ge 100$ records |
| **Training Records** | `1` records | Sufficient for cross-validation |
| **Is Synthetic Data** | `False` | Rule `R-MD-11` isolation guard |

**Audit Diagnostic:** Observation panel contains 3 records (1 train), failing the required sufficiency threshold of >= 100 records. Cross-validated meta-learner stacking or multi-model blending on an underpowered panel is statistically unidentifiable and prone to extreme variance inflation. Under CHARTER-ENSEMBLING-STACKING deferral criteria, ensembling is formally deferred.

---

## 3. Algorithmic Utility: Convex Quantile Blender

The mathematical blending utility combines quantile predictions from multiple base learners:
$$
\hat{q}_{p, \mathrm{blend}}(x) = \sum_{m=1}^{M} w_m \hat{q}_{p, m}(x), \quad \sum_{m=1}^{M} w_m = 1.0, \quad w_m \ge 0
$$

To strictly satisfy **Rule `R-UQ-05`**, the raw convex blend is projected via the **Chernozhukov et al. (2010)** monotone rearrangement operator, guaranteeing $\text{P10} \le \text{P50} \le \text{P90}$ with zero quantile crossings:
$$
\mathbf{\hat{q}}_{\mathrm{clean}}(x) = \mathrm{Sort}\left(\mathbf{\hat{q}}_{\mathrm{raw}}(x)\right)
$$

---

## 4. Evidentiary Conclusion & Production Recommendation

1. **Champion Preservation:** The existing Rung F L2 Conformal CatBoost champion is strictly preserved as the single production model.
2. **No Unwarranted Complexity:** Adding multi-model serving overhead (doubling bundle size and inference latency) is rejected when the underlying dataset cannot identify an ensemble gain.
3. **Next Step:** Advance to **Task T7.07** to consolidate all Phase 7 candidate outcomes in `docs/research/rejected-ideas.md` and ratify Gate G7.
