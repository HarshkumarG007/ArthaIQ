# Employer Feature Modeling: Simple vs Graph-Based (EXP-10, CHARTER-EXP-10)

> **Scope:** Discrete Archetypes vs Smoothed Target Encoding vs Spectral Graph Embeddings.
> **Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-02, R-MD-03, R-MD-04, R-MD-05, R-MD-09, R-DA-10, R-UQ-01, R-UQ-05 · Task T7.04.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `EXP10-20261019052507` |
| **Charter ID** | `CHARTER-EXP-10` |
| **Experiment ID** | `EXP-10` |
| **Generated At** | `2026-10-19T05:25:07.253596+00:00` |
| **Git Commit** | `aa90169f` |
| **Evaluation Split** | `select` |
| **Evaluated Observations** | `45` |
| **Overall Verdict** | **`DEFER`** |

---

## 1. Executive Summary & Production Decision

Experiment EXP-10 evaluated 2 candidate employer feature representations against the Champion Rung F L2 baseline. Variant A (Smoothed Target Encoding) achieved Δ Pinball = +0.108 LPA (verdict: REJECT); Variant B (Talent-Flow Graph Embedding) achieved Δ Pinball = -0.053 LPA (verdict: DEFER). The mobility graph audit verified 8/50 qualified nodes. The formal production decision is DEFER. Baseline Champion Rung F with discrete organizational archetypes and k_min >= 5 cluster masking is retained without complex graph or target encoding overhead.

---

## 2. Upfront Graph Feasibility Gate (Gate 1 Audit)

- **Total Employer Nodes:** `9`
- **Qualified Nodes (Degree $\ge 3$):** `8` (Threshold: $\ge 50$)
- **Gate 1 Feasibility Status:** `DEFERRED (EXCESSIVELY_SPARSE)`
- **Audit Detail:** Qualified nodes with degree >= 3: 8/50 required. Total edges: 28 across 9 clusters.

> [!NOTE]
> Under Rule `R-MD-09` and `CHARTER-EXP-10`, when fewer than 50 employer nodes have degree >= 3,
> the preregistered outcome for graph talent mobility modeling is strictly `DEFER` without claiming
> predictive improvement.

---

## 3. Comparative Performance Matrix

| Candidate Variant | Feats | Pinball (LPA) | MAE (LPA) | MDAPE (%) | Coverage | Width (LPA) | p95 Latency (ms) | Bundle (MB) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Champion Baseline (Discrete Tier + Masked Cluster)** | 7 | `2.176` | `7.00` | `16.8%` | `75.6%` | `21.54` | `0.72` | `12.0` |
| **Variant A: Smoothed Target Encoding** | 8 | `2.284` | `7.14` | `18.0%` | `71.1%` | `21.20` | `0.76` | `12.2` |
| **Variant B: Talent-Flow Graph Embedding** | 9 | `2.123` | `7.36` | `16.4%` | `77.8%` | `21.13` | `0.81` | `12.5` |

---

## 4. Paired Statistical Differences vs Champion Baseline

Paired differences evaluated using 1,000 nonparametric bootstrap resamples (Rule R-MD-01, R-UQ-01):

| Candidate Variant | $\Delta$ Pinball (LPA) | 95% Bootstrap CI | Stat. Sig? | $\Delta$ MAE (LPA) | Width Ratio ($R_w$) | Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Variant A: Smoothed Target Encoding** | `+0.108` | `[-0.106, +0.318]` | NO | `+0.14` | `0.984` | **`REJECT`** |
| **Variant B: Talent-Flow Graph Embedding** | `-0.053` | `[-0.200, +0.067]` | NO | `+0.36` | `0.981` | **`DEFER`** |

---

## 5. Graph Density & Deferral Audit (Network Sparsity Diagnostics)

- **Total Employer Nodes:** `9`
- **Nodes with Degree $\ge 3$:** `8` (Threshold: $\ge 50$)
- **Sparsity Verdict:** `EXCESSIVELY_SPARSE`
- **Audit Note:** Qualified nodes with degree >= 3: 8/50 required. Total edges: 28 across 9 clusters.

---

## 6. Engineering Directives & Pre-Registered Criteria Audit

### Variant A: Smoothed Target Encoding
- **Verdict:** `REJECT`
- **Pinball Difference ($\Delta \mathcal{L}$):** `+0.108` LPA
- **95% Confidence Interval:** `[-0.106, +0.318]`
- **Interval Width Ratio ($R_w$):** `0.984`
- **p95 CPU Inference Latency:** `0.76 ms`
- **Decision Rationale:** Failed pre-registered keep threshold: Δ Pinball = +0.108 LPA (threshold: -0.050 LPA, 95% CI: [-0.106, +0.318]). Employer target encoding provides no statistically detectable predictive benefit over discrete organizational archetypes and Mincerian experience curves.

### Variant B: Talent-Flow Graph Embedding
- **Verdict:** `DEFER`
- **Pinball Difference ($\Delta \mathcal{L}$):** `-0.053` LPA
- **95% Confidence Interval:** `[-0.200, +0.067]`
- **Interval Width Ratio ($R_w$):** `0.981`
- **p95 CPU Inference Latency:** `0.81 ms`
- **Decision Rationale:** Gate 1 Graph Feasibility: Transition network is excessively sparse (8/50 nodes with degree >= 3) in current PT1 sample. Under Charter CHARTER-EXP-10 deferral criteria, graph talent mobility modeling is formally deferred without claiming predictive improvement until B2B employer syndication tranches provide dense cross-employer mobility graphs.

---

## 7. Historical Benchmark Provenance & Corrective Patch Audit

### 7.1 Defect Analysis in Initial Implementation (`aa90169`)
In the initial T7.04 implementation (commit `aa90169`), `EmployerTargetEncoder.transform()` was applied directly to `train_clusters` during training feature matrix creation. While evaluation sets (`calibrate`, `select`) were correctly transformed out-of-sample, this in-sample transformation on the training split allowed each observation $y_i$ to enter its own cluster and tier aggregate mean, introducing a row-level target leakage defect during gradient boosting tree training (Rule `R-MD-04`).

### 7.2 Corrective Patch & Mathematical Invariance Guarantee
Under the T7.04 corrective patch:
1. Implemented `EmployerTargetEncoder.transform_leave_one_out(clusters, tiers, y_log)`, which analytically excludes observation $i$ from total sum, tier sum, and cluster sum:
   $$n_{-i} = N - 1, \quad s_{-i} = S - y_i, \quad \text{prior}_{-i} = \frac{S_{\text{tier}} - y_i}{N_{\text{tier}} - 1}$$
   $$\text{Smoothed}_{-i} = \frac{s_{-i} + m \cdot \text{prior}_{-i}}{n_{-i} + m}$$
   Ensuring $\frac{\partial \text{encoded}_i}{\partial y_i} \equiv 0$ (verified by regression test `test_employer_target_encoder_zero_leakage_invariance_vs_in_sample`).
2. Promoted graph feasibility to **Gate 1**: the eligible training mobility graph is audited upfront. Because only 8 nodes meet degree $\ge 3$ ($< 50$ required), Variant B is unconditionally deferred under `CHARTER-EXP-10` without claiming predictive improvement.
3. Added regression tests covering exact leave-one-out math, singleton cluster/tier fallbacks, empty inputs, and $k_{\min} \ge 5$ boundary conditions.

### 7.3 Side-by-Side Benchmark Provenance Matrix

| Metric Dimension | Historical Pre-Correction Benchmark (In-Sample Target Encoding) | Corrected Post-Patch Benchmark (Zero-Leakage LOO Target Encoding) | Impact Assessment |
|:---|:---:|:---:|:---|
| **Baseline Champion Pinball** | `2.162` LPA | `2.176` LPA | Baseline stable within seed variance |
| **Variant A Pinball** | `2.267` LPA | `2.284` LPA | Loss degradation increases under zero leakage |
| **Variant A $\Delta$ Pinball (95% CI)** | `+0.104` LPA `[-0.103, +0.300]` | `+0.108` LPA `[-0.106, +0.318]` | **REJECT** verdict robustly confirmed |
| **Variant A Width Ratio ($R_w$)** | `1.118` | `0.984` | Interval utility fails keep threshold |
| **Variant B Pinball** | `2.201` LPA | `2.123` LPA | Graph embedding evaluated |
| **Variant B $\Delta$ Pinball (95% CI)** | `+0.039` LPA `[-0.132, +0.236]` | `-0.053` LPA `[-0.200, +0.067]` | CI includes zero; non-significant |
| **Qualified Graph Nodes ($\ge 3$)** | `8 / 50` | `8 / 50` | **Gate 1 Fails ($\ge 50$ required)** |
| **Variant B Verdict** | **DEFER** | **DEFER** | Unconditional Gate 1 deferral |
| **Production Champion Status** | **UNCHANGED** (Rung F L2) | **UNCHANGED** (Rung F L2) | Rung F L2 Champion strictly retained |

---

*Report generated by `compintel.evaluation.employer_graphs_experiment` on 2026-10-19T05:25:07.253596+00:00*