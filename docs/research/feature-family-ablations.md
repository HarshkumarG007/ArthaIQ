# Feature-Family Ablation Study Report (EXP-06)

> **Scope:** Systematic ablation of candidate feature families at Level 1.
> **Standards:** PRD Sec 5 · Rules R-MD-01, R-MD-02, R-MD-05, R-MD-09, R-MD-11, R-MD-13, R-MD-15 · Hypothesis EXP-06.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `EXP06-ABLATION-20261018162804` |
| **Generated At** | `2026-10-18T16:28:04.790806+00:00` |
| **Git Commit** | `4fcfd496` |
| **Evaluation Split** | `select` |
| **Evaluated Observations** | `45` |

## 1. Executive Summary

Ablation study EXP-06 evaluated 7 candidate feature families at Level 1 against the L0 Core Baseline. Results: 0 family kept, 2 deferred, and 5 rejected under pre-registered thresholds in v1.yaml. Core representations remain parsimonious while capturing high-signal personalization dimensions.

---

## 2. Baseline Model Performance Reference

| Configuration | Features | Point MAE | MdAPE | Pinball | 80% Cov | Width (LPA) | Crossing |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **L0 Core Baseline** | 4 | `7.18` | `17.7%` | `2.024` | `75.6%` | `20.23` | `0.00%` |
| **L1 Full Profile** | 8 | `22.74` | `57.1%` | `6.677` | `80.0%` | `72.71` | `0.00%` |

---

## 3. Pre-Registered Feature-Family Ablation Table (EXP-06)

We evaluate paired differences $\Delta = \text{Metric}_{\text{Augmented}} - \text{Metric}_{\text{Baseline}}$ with 95% nonparametric bootstrap confidence intervals (1,000 resamples). A negative $\Delta$ indicates an accuracy or sharpness improvement.

| Family | Evaluated Features | Keep Threshold | Forward Δ Pinball (95% CI) | Width Ratio | Backward Δ Pinball ($L_1 \setminus F$) | Verdict |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Skills & Depth (Family A)** | `feat_l1_skills_primary`<br>`feat_l1_skills_depth` | $\Delta \le -0.030$ | `+0.051` [-0.072, +0.189] | `0.964` | `+0.380` | **`REJECT`** |
| **Domain Specialization (Family B)** | `feat_l1_domain_specialization` | $\Delta \le -0.025$ | `+0.000` [+0.000, +0.000] | `1.000` | `+0.000` | **`REJECT`** |
| **Employer Archetype Tier (Family C)** | `feat_l1_employer_tier` | $\Delta \le -0.050$, $R \le 0.90$ | `+0.000` [+0.000, +0.000] | `1.000` | `+0.000` | **`REJECT`** |
| **Work Arrangement / Geo Mode (Family D)** | `feat_l1_work_arrangement` | $\Delta \le -0.010$ | `+0.000` [+0.000, +0.000] | `1.000` | `+0.000` | **`DEFER`** |
| **Career Velocity (Family E)** | `feat_l1_career_velocity` | $\Delta \le -0.015$ | `+0.000` [+0.000, +0.000] | `1.000` | `+0.000` | **`REJECT`** |
| **Leadership Scope (Family F)** | `feat_l1_leadership_scope` | $\Delta \le -0.020$ | `+0.000` [+0.000, +0.000] | `1.000` | `+0.000` | **`REJECT`** |
| **Macro Market Regime (Family G)** | `feat_l1_macro_market_regime` | $\Delta \le -0.010$ | `+0.000` [+0.000, +0.000] | `1.000` | `+0.000` | **`DEFER`** |

---

## 4. Detailed Family Analyses & Engineering Directives

### Skills & Depth (Family A)
- **Verdict:** `REJECT`
- **Features Included:** `feat_l1_skills_primary`, `feat_l1_skills_depth`
- **Keep Criteria:** $\Delta \mathcal{L}_{pinball} \le -0.030\text{ LPA}$
- **Forward Addition ($L_0 + F$):** $\Delta \text{Mean Pinball} = +0.051$ LPA (95% CI: `[-0.072, +0.189]`), Width Ratio: `0.964`, $\Delta \text{Coverage} = +2.2\%$
- **Backward Drop ($L_1 \setminus F$):** $\Delta \text{Mean Pinball} = +0.380$ LPA (Damage when removed from full profile)
- **Decision Rationale:** Failed minimum effect threshold (Δ Pinball = +0.051 vs threshold -0.030 LPA). Rejected per Rule EXP-06.

### Domain Specialization (Family B)
- **Verdict:** `REJECT`
- **Features Included:** `feat_l1_domain_specialization`
- **Keep Criteria:** $\Delta \mathcal{L}_{pinball} \le -0.025\text{ LPA}$
- **Forward Addition ($L_0 + F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (95% CI: `[+0.000, +0.000]`), Width Ratio: `1.000`, $\Delta \text{Coverage} = +0.0\%$
- **Backward Drop ($L_1 \setminus F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (Damage when removed from full profile)
- **Decision Rationale:** Failed minimum effect threshold (Δ Pinball = +0.000 vs threshold -0.025 LPA). Rejected per Rule EXP-06.

### Employer Archetype Tier (Family C)
- **Verdict:** `REJECT`
- **Features Included:** `feat_l1_employer_tier`
- **Keep Criteria:** $\Delta \mathcal{L}_{pinball} \le -0.050\text{ LPA}$
- **Forward Addition ($L_0 + F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (95% CI: `[+0.000, +0.000]`), Width Ratio: `1.000`, $\Delta \text{Coverage} = +0.0\%$
- **Backward Drop ($L_1 \setminus F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (Damage when removed from full profile)
- **Decision Rationale:** Failed minimum effect threshold (Δ Pinball = +0.000 vs threshold -0.050 LPA). Rejected per Rule EXP-06.

### Work Arrangement / Geo Mode (Family D)
- **Verdict:** `DEFER`
- **Features Included:** `feat_l1_work_arrangement`
- **Keep Criteria:** $\Delta \mathcal{L}_{pinball} \le -0.010\text{ LPA}$
- **Forward Addition ($L_0 + F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (95% CI: `[+0.000, +0.000]`), Width Ratio: `1.000`, $\Delta \text{Coverage} = +0.0\%$
- **Backward Drop ($L_1 \setminus F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (Damage when removed from full profile)
- **Decision Rationale:** Marginal or deferred effect (Δ Pinball = +0.000 vs threshold -0.010 LPA). Deferred per pre-registered policy without polluting Core models.

### Career Velocity (Family E)
- **Verdict:** `REJECT`
- **Features Included:** `feat_l1_career_velocity`
- **Keep Criteria:** $\Delta \mathcal{L}_{pinball} \le -0.015\text{ LPA}$
- **Forward Addition ($L_0 + F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (95% CI: `[+0.000, +0.000]`), Width Ratio: `1.000`, $\Delta \text{Coverage} = +0.0\%$
- **Backward Drop ($L_1 \setminus F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (Damage when removed from full profile)
- **Decision Rationale:** Failed minimum effect threshold (Δ Pinball = +0.000 vs threshold -0.015 LPA). Rejected per Rule EXP-06.

### Leadership Scope (Family F)
- **Verdict:** `REJECT`
- **Features Included:** `feat_l1_leadership_scope`
- **Keep Criteria:** $\Delta \mathcal{L}_{pinball} \le -0.020\text{ LPA}$
- **Forward Addition ($L_0 + F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (95% CI: `[+0.000, +0.000]`), Width Ratio: `1.000`, $\Delta \text{Coverage} = +0.0\%$
- **Backward Drop ($L_1 \setminus F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (Damage when removed from full profile)
- **Decision Rationale:** Failed minimum effect threshold (Δ Pinball = +0.000 vs threshold -0.020 LPA). Rejected per Rule EXP-06.

### Macro Market Regime (Family G)
- **Verdict:** `DEFER`
- **Features Included:** `feat_l1_macro_market_regime`
- **Keep Criteria:** $\Delta \mathcal{L}_{pinball} \le -0.010\text{ LPA}$
- **Forward Addition ($L_0 + F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (95% CI: `[+0.000, +0.000]`), Width Ratio: `1.000`, $\Delta \text{Coverage} = +0.0\%$
- **Backward Drop ($L_1 \setminus F$):** $\Delta \text{Mean Pinball} = +0.000$ LPA (Damage when removed from full profile)
- **Decision Rationale:** Marginal or deferred effect (Δ Pinball = +0.000 vs threshold -0.010 LPA). Deferred per pre-registered policy without polluting Core models.

---

*Report generated by `compintel.evaluation.family_ablation` on 2026-10-18T16:28:04.790806+00:00*