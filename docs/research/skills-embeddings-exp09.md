# Skills Feature Modeling Experiment Report (EXP-09, CHARTER-EXP-09)

> **Scope:** Curated Taxonomy & TF-IDF vs Sentence-Transformer Embeddings on CPU.
> **Standards:** PRD Sec 5, FR-05 · Rules R-MD-01, R-MD-02, R-MD-05, R-MD-09, R-UQ-01, R-UQ-05 · Task T7.02.

| Metadata Attribute | Value |
|:---|:---|
| **Report ID** | `EXP09-SKILLS-20261018230126` |
| **Charter ID** | `CHARTER-EXP-09` |
| **Experiment ID** | `EXP-09` |
| **Generated At** | `2026-10-18T23:01:26.570622+00:00` |
| **Git Commit** | `de7d21bb` |
| **Evaluation Split** | `select` |
| **Evaluated Observations** | `45` |
| **Overall Verdict** | **`REJECT`** |

## 1. Executive Summary

Experiment EXP-09 evaluated 2 advanced skills representations against the Champion Rung F L2 baseline. Variant A (Curated Taxonomy & TF-IDF) achieved Δ Pinball = -0.070 LPA; Variant B (Sentence Embeddings on CPU) achieved Δ Pinball = +0.193 LPA. Both variants failed the pre-registered minimum effect threshold of -0.050 LPA. Under Rule R-MD-09 and Charter EXP-09, the formal decision is REJECT. Champion Rung F tabular baseline remains the unified production architecture without embedding overhead.

## 2. Model Performance and Latency Matrix

| Candidate Architecture | Features | MAE (LPA) | Mean Pinball (LPA) | 80% Coverage | Mean Width (LPA) | Crossing Rate | p95 Latency (ms) | Bundle Size (MB) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Champion Baseline (Rung F L2)** | 3 | 7.31 | 2.123 | 84.4% | 23.52 | 0.00% | 0.68 | 12.0 |
| **Variant A: Curated Taxonomy & TF-IDF** | 11 | 6.86 | 2.053 | 73.3% | 19.16 | 0.00% | 0.91 | 18.5 |
| **Variant B: Sentence-Transformer Embeddings (CPU)** | 11 | 6.85 | 2.315 | 68.9% | 23.59 | 0.00% | 0.80 | 45.0 |

## 3. Pre-Registered Comparative Deltas vs Champion Baseline

| Variant | Δ Mean Pinball (LPA) | 95% Bootstrap CI | Significant? | Δ MAE (LPA) | Width Ratio | Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Variant A: Curated Taxonomy & TF-IDF** | -0.070 | [-0.302, +0.167] | NO | -0.45 | 0.815 | **`REJECT`** |
| **Variant B: Sentence Embeddings (CPU)** | +0.193 | [-0.171, +0.606] | NO | -0.46 | 1.003 | **`REJECT`** |

## 4. Decision Rationales and Analysis

### 4.1 Variant A: Curated Taxonomy & TF-IDF
- **Verdict:** `REJECT`
- **Analysis:** Failed pre-registered keep threshold: Δ Pinball = -0.070 LPA (threshold: -0.050 LPA, 95% CI: [-0.302, +0.167]). Adding text representations does not yield justifiable predictive gain over tabular L2 baseline (Rule R-MD-09, EXP-09).

### 4.2 Variant B: Sentence Embeddings (CPU)
- **Verdict:** `REJECT`
- **Analysis:** Failed pre-registered keep threshold: Δ Pinball = +0.193 LPA (threshold: -0.050 LPA, 95% CI: [-0.171, +0.606]). Adding text representations does not yield justifiable predictive gain over tabular L2 baseline (Rule R-MD-09, EXP-09).

## 5. Architectural Recommendations

- **Rule R-MD-09 Compliance:** Complex text and embedding pipelines are only justified if they achieve >= 0.050 LPA pinball reduction with 95% bootstrap CI excluding zero.
- **Serving Footprint:** Avoiding heavy transformer runtimes preserves microsecond-level inference latency and eliminates large unpinned wheel dependencies.
- **Recommendation:** Retain Champion Rung F on Level 2 features as the production serving bundle.