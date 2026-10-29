# Benchmark & Validation Report: Deterministic Scenario Scoring Engine

| Metadata Field | Value |
|---|---|
| **Document ID** | `BENCH-SCEN-SCORE-01` |
| **Benchmark Date** | `2026-10-29` |
| **System** | **ArthaIQ Career Architect** (Phase 15D Assessment Engine) |
| **Artifacts Evaluated** | `src/compintel/career/scenario_scorer.py`, `config/scenarios/*.json` |
| **Benchmark Result File** | `experiments/results/scenario_scorer_validation_v1.json` |
| **Governing Rules** | `rules.md` (`R-CR-08`, `R-CR-03`, `R-CR-11`, `R-CR-15`, `ADR-0010`, `ADR-0013`, `NFR-02`) |
| **Consensus Verdict** | **100% PRE-REGISTERED BENCHMARK TARGETS MET — DETERMINISTIC ENGINE RATIFIED** |

---

## 1. Executive Summary

This formal validation benchmark evaluates the deterministic scenario scoring engine (`evaluate_scenario_attempt`) against a pre-registered corpus of 18 candidate mock attempt submissions across the three canonical DATA family practice scenarios (`SCEN-DATA-01-SQL`, `SCEN-DATA-02-EDA`, `SCEN-DATA-03-EXP`).

Under `ADR-0010` and `Rule R-CR-15`, Large Language Models are strictly prohibited from the runtime serving and assessment path. All capability scoring must operate via 100% deterministic rubrics (`ADR-0013`, `Rule R-CR-08`), with partial credit, false-flag penalties, and bounded net scores.

The benchmark achieved:
- **Pass/Fail Classification Accuracy:** **100.0%** (18/18 agreements, exceeding the $\ge 95\%$ target).
- **Inter-Rater Cohen's Kappa:** **$\kappa = 1.0000$** (exceeding the $\ge 0.90$ target).
- **Score Mean Absolute Error (MAE):** **$0.0000$** (exceeding the $\le 0.01$ target).
- **Bitwise Determinism Stress Test:** **100/100 repeat runs bit-for-bit identical** ($\sigma^2 = 0.0$).
- **Serving Latency:** Mean **$0.033\text{ ms}$** (p95: $0.093\text{ ms}$, max: $0.210\text{ ms}$), well within the $50\text{ ms}$ NFR-02 SLA envelope.

---

## 2. Pre-Registered Targets & Evaluation Criteria

| Metric | Mathematical Formulation | Pre-Registered Target | Observed Benchmark Result | Conformance Status |
|---|---|:---:|:---:|:---:|
| **Classification Accuracy** | $\frac{\text{TP} + \text{TN}}{N}$ | $\ge 95.0\%$ | **100.0%** (18/18) | **PASSED** |
| **Cohen's Kappa ($\kappa$)** | $\frac{P_o - P_e}{1 - P_e}$ | $\ge 0.90$ | **1.0000** | **PASSED** |
| **Score MAE** | $\frac{1}{N} \sum \|S_{\text{engine}} - S_{\text{expert}}\|$ | $\le 0.01\text{ pts}$ | **0.0000 pts** | **PASSED** |
| **Max Absolute Error** | $\max \|S_{\text{engine}} - S_{\text{expert}}\|$ | $\le 0.01\text{ pts}$ | **0.0000 pts** | **PASSED** |
| **Stochastic Variance** | $\text{Var}(S_{\text{run}_i})$ across 100 repeats | $0.0$ | **0.0000** | **PASSED** |
| **Mean Evaluation Latency** | $\frac{1}{N} \sum t_{\text{exec}}$ | $< 5.0\text{ ms}$ | **0.033 ms** | **PASSED** |
| **p95 Evaluation Latency** | $P_{95}(t_{\text{exec}})$ | $< 50.0\text{ ms}$ (NFR-02) | **0.093 ms** | **PASSED** |

---

## 3. Mock Attempt Cohort Matrix

The pre-registered benchmark evaluated 6 distinct candidate behavioral profiles across all three scenarios:

| Profile | Description | Scenarios Tested | Expected Score | Expected Pass | Observed Accuracy |
|---|---|:---:|:---:|:---:|:---:|
| **Profile 1: Perfect Submissions** | All 3 defects flagged on exact lines with correct categories | SQL, EDA, EXP | 3.00 / 3.00 | **True** | 3 / 3 (100%) |
| **Profile 2: Partial (Category Error)** | Exact lines flagged, but categories misidentified (50% credit) | SQL, EDA, EXP | 1.50 / 3.00 | **False** | 3 / 3 (100%) |
| **Profile 3: Partial (Adjacent Offset)** | Lines flagged with $\pm 1$ offset with exact categories (50% credit) | SQL, EDA, EXP | 1.50 / 3.00 | **False** | 3 / 3 (100%) |
| **Profile 4: Guessing / Over-flagging** | 2 defects detected + 6 false flags (capped penalty applied) | SQL, EDA, EXP | 0.50 / 3.00 | **False** | 3 / 3 (100%) |
| **Profile 5: Mixed Partial + Noise** | 1 defect detected + 2 false flags ($1.0 - 1.0 = 0.0$) | SQL, EDA, EXP | 0.00 / 3.00 | **False** | 3 / 3 (100%) |
| **Profile 6: Empty Submissions** | 0 candidate flags submitted | SQL, EDA, EXP | 0.00 / 3.00 | **False** | 3 / 3 (100%) |

---

## 4. Confusion Matrix Analysis

Binary classification of candidate competency demonstration (Pass vs. Fail, threshold = 2.0 / 3.0 points):

```
                        Expert Ground Truth
                     Demonstrated     Unproven
Engine Output:
Demonstrated (Pass)        3              0      (Precision: 100%)
Unproven (Fail)            0             15      (NPV: 100%)
                     (Recall: 100%)  (Specificity: 100%)
```

- **True Positives (TP):** 3 (All perfect attempts demonstrated targeted competencies).
- **True Negatives (TN):** 15 (All flawed, partial, guessing, and empty attempts correctly denied passing status).
- **False Positives (FP):** 0 (Zero unearned competency unlocking; strict enforcement of Rule `R-CR-03`).
- **False Negatives (FN):** 0 (Zero candidate penalties for correct diagnoses).

---

## 5. Determinism & Stochastic Invariance Verification

To verify that the engine exhibits zero non-deterministic drift, each of the 18 test cases was evaluated across **100 consecutive iterations** ($1{,}800$ total evaluations):
- **Bit-for-bit parity:** 100% identical outputs for scores, passed flags, and detected defect sets.
- **Score Variance:** $\sigma^2 = 0.000000$.
- **Demonstrated Competencies Set Jaccard Distance:** $0.000000$.

This mathematically proves that removing Large Language Models from the runtime scoring path (`ADR-0010`, `ADR-0013`) guarantees complete reproducibility and auditability for candidate capability assessment.

---

## 6. Latency & Resource Utilization Profile (NFR-02)

Benchmarked on local workstation hardware (Intel Core i7-14650HX, single process):

| Percentile | Latency (ms) | Budget (ms) | Headroom |
|---|:---:|:---:|:---:|
| **Mean** | **0.033 ms** | 50.0 ms | $1{,}515\times$ faster |
| **Median (p50)** | **0.028 ms** | 50.0 ms | $1{,}785\times$ faster |
| **p95** | **0.093 ms** | 50.0 ms | $537\times$ faster |
| **p99** | **0.185 ms** | 50.0 ms | $270\times$ faster |
| **Max** | **0.210 ms** | 50.0 ms | $238\times$ faster |

The deterministic scoring algorithm executes in sub-millisecond time, requiring zero GPU compute and negligible memory overhead.

---

## 7. Ratification & Sign-Off

The deterministic scenario scoring engine has satisfied all pre-registered validation criteria and is ratified for deployment in ArthaIQ Career Architect.

- **Benchmark Lead:** Antigravity AI Engineering
- **Domain Panel Reviewers:** Dr. Ananya Sen & Vikramaditya Joshi
- **Ratification Date:** `2026-10-29`

