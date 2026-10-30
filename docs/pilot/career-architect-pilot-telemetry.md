# ArthaIQ Career Architect Pilot Telemetry & Synthetic User Journey Audit

| Field | Value |
|---|---|
| **Document Type** | Subsystem Telemetry & Synthetic User Journey Audit Dossier |
| **Document ID** | `TELEM-CAREER-ARCH-01` |
| **Status** | **🟢 AUDIT PASSED (10/10 M-TEL Quality Metrics GO, Sub-Millisecond Deterministic Latency, Zero Causal Claims, DPDP Section 12 Purge Verified)** |
| **Audit Date** | 2026-10-30 |
| **Target Subsystem** | ArthaIQ Career Architect Engine & Client Workspace (Phase 15, Tasks T15.01–T15.33, Gates G15A–G15F) |
| **Governing Rules** | `rules.md` (`R-CR-01`, `R-CR-02`, `R-CR-03`, `R-CR-04`, `R-CR-05`, `R-CR-08`, `R-CR-11`, `R-CR-12`, `R-CR-14`, `R-CR-15`, `R-UQ-01`, `ADR-0010`, `ADR-0011`, `ADR-0012`, `ADR-0013`) |
| **Telemetry Artifact** | `experiments/results/career_pilot_telemetry_v1.json` |

---

## 1. Executive Summary

This telemetry and audit dossier certifies the quantitative performance, operational reliability, ethical guardrails, and statutory privacy compliance of the **ArthaIQ Career Architect** subsystem across synthetic user journeys and simulated high-volume usage patterns.

Following the ratification of **Gate G15F** (Decision `D-031`), an exhaustive automated simulation suite was executed (`scripts/run_career_pilot_telemetry.py`) to benchmark the integrated subsystem against 10 strict performance and safety criteria (**M-TEL-01** through **M-TEL-10**). 

The audit evaluated:
1. **Four Persona Journeys (`P-DATA-01` to `P-DATA-04`):** Spanning Junior (L2), Mid (L3), Senior (L4), and Regional Explorer profiles across Metro tech hubs (Bangalore, Hyderabad, Pune) and non-metro cohorts requiring honest abstention.
2. **Fifty Deterministic Practice Submissions:** Profiling 15 Expert/Flawless, 15 Partial/Near-miss, 10 Guessing/Over-flagging, and 10 Minimal/Empty attempts across canonical scenarios (`SCEN-DATA-01-SQL`, `SCEN-DATA-02-EDA`, `SCEN-DATA-03-EXP`).
3. **Scoring Latency & Determinism Stress-Testing:** Measuring execution speed and verifying zero variance ($\sigma^2 = 0.0$) across 100 repetitive evaluations of identical attempts.
4. **Client-Side Storage & India DPDP Act 2023 Section 12 Hard Wipe:** Measuring JSON export size for 50 competency evidence records + 10 attempt records, verifying bitwise roundtrip parity, and validating complete atomic data erasure (0 bytes retained).
5. **Anti-Causal & Anti-Credentialism Verification:** Scanning all serialized states, outputs, and disclaimers to ensure zero affirmative pay promises (Rule `R-CR-01`, CPA 2019) and zero examination or certification claims (Rule `R-CR-11`).

**Final Verdict:** All 10 scorecard metrics met or exceeded target tolerances. The Career Architect platform operates deterministically, provides sub-millisecond scoring latencies, upholds local-first privacy, and adheres to ethical compensation principles.

---

## 2. Telemetry Audit Scorecard (10/10 Metrics GO)

| Metric ID | Description | Target Specification | Observed Result | Status |
|---|---|---|:---:|:---:|
| **M-TEL-01** | Deterministic Scorer Variance | $\sigma^2 = 0.0$ over 100 repeats | **0.000000** | **PASS** |
| **M-TEL-02** | Scoring Latency ($p_{95}$) | $\le 5.00\text{ ms}$ | **0.0303 ms** ($30.30\ \mu\text{s}$) | **PASS** |
| **M-TEL-03** | Rubric Net Score Boundedness | 100% in $[0.0, \text{max\_possible\_score}]$ | **100.0%** (50/50 attempts) | **PASS** |
| **M-TEL-04** | Dynamic Next-Step Resolution | 100% first-unmet node with satisfied DAG prereqs | **100.0%** | **PASS** |
| **M-TEL-05** | Weekly Pacing Slider Calculation | $W = \lceil\sum H / \text{budget}\rceil$ exact ceiling match | **100.0%** | **PASS** |
| **M-TEL-06** | DPDP Act 2023 Sec 12 Hard Wipe | 0 bytes residual user data post-purge | **0 bytes** | **PASS** |
| **M-TEL-07** | Client Backup Roundtrip Fidelity | 100% bitwise parity on JSON export/import | **100.0%** parity | **PASS** |
| **M-TEL-08** | Client Storage Footprint (50 records) | $\le 100.0\text{ KB}$ | **18.02 KB** (18,453 bytes) | **PASS** |
| **M-TEL-09** | Honest Pay Abstention Trigger | 100% abstention on unsupported cells/tiers | **100.0%** | **PASS** |
| **M-TEL-10** | Anti-Causal Copy Invariant | 0 affirmative pay promises / exam terms | **0 violations** | **PASS** |

---

## 3. Synthetic Persona Journeys Analysis

Four distinct user personas were modeled and tracked from onboarding through DAG gap resolution and practice execution:

```
[Onboarding: Role / Level / Hub] ──> [DAG Traversal] ──> [Next-Step Card] ──> [Practice Workspace] ──> [Ledger Transition]
```

### Persona Profiles & Resolution Outcomes

#### 1. Persona `P-DATA-01`: Junior Data Analyst (`L2_junior`) — Bangalore
- **Weekly Study Commitment:** 10 hours/week.
- **Initial State:** Empty evidence ledger; all 5 junior competencies unproven.
- **Initial Dynamic Next-Step:** `data.gen.l2_prob_decomp` (Root DAG node with 0 prerequisite dependencies).
- **Projected Pacing Interval:** Heuristic $[100, 170]\text{ hours} \implies [10, 17]\text{ weeks}$.
- **Simulated Action:** User passes practice scenario `SCEN-DATA-01-SQL`.
- **Post-Practice State:** Unlocks `data.anl.l2_sql_basic`. Next-step dynamically advances to `data.anl.l2_sql_basic`.
- **Decoupled Pay Overlay:** Bangalore L2 Market Distribution ($P_{10}: ₹8.0\text{L}, P_{50}: ₹12.0\text{L}, P_{90}: ₹16.0\text{L}$). Honest abstention not triggered.

#### 2. Persona `P-DATA-02`: Mid-Level Data Analyst (`L3_mid`) — Hyderabad
- **Weekly Study Commitment:** 15 hours/week.
- **Initial State:** L2 foundational competencies attested; SQL demonstrated.
- **Initial Dynamic Next-Step:** `data.anl.l2_eda` (Prerequisites satisfied).
- **Projected Pacing Interval:** Heuristic $[245, 405]\text{ hours} \implies [17, 27]\text{ weeks}$.
- **Simulated Action:** User completes practice scenario `SCEN-DATA-02-EDA` with score $3.0 / 3.0$.
- **Post-Practice State:** `data.anl.l2_eda` transitioned to Demonstrated. Next-step dynamically advances to `data.anl.l2_hygiene`.
- **Decoupled Pay Overlay:** Hyderabad L3 Market Distribution ($P_{10}: ₹15.0\text{L}, P_{50}: ₹22.0\text{L}, P_{90}: ₹30.0\text{L}$).

#### 3. Persona `P-DATA-03`: Senior Data Scientist (`L4_senior`) — Pune
- **Weekly Study Commitment:** 20 hours/week.
- **Initial State:** Level 2 and Level 3 foundations verified; targeting senior architecture milestones.
- **Initial Dynamic Next-Step:** `data.sci.l3_feat_eng` (Target level gap).
- **Projected Pacing Interval:** Heuristic $[390, 650]\text{ hours} \implies [20, 33]\text{ weeks}$.
- **Simulated Action:** User attempts advanced scenario `SCEN-DATA-03-EXP` with expert precision.
- **Post-Practice State:** Unlocks `data.sci.l3_exp_design` and `data.sci.l4_causal`. Next step advances to `data.sci.l4_bigdata`.
- **Decoupled Pay Overlay:** Pune L4 Market Distribution ($P_{10}: ₹26.5\text{L}, P_{50}: ₹38.0\text{L}, P_{90}: ₹52.0\text{L}$).

#### 4. Persona `P-DATA-04`: Career Explorer — Non-Metro Regional Hub (`other`)
- **Weekly Study Commitment:** 5 hours/week.
- **Initial State:** Non-metro Indian location; exploring data roles with limited weekly time budget.
- **Initial Dynamic Next-Step:** `data.gen.l2_prob_decomp`.
- **Projected Pacing Interval:** Heuristic $[100, 170]\text{ hours} \implies [20, 34]\text{ weeks}$.
- **Decoupled Pay Overlay:** **Honest Abstention Triggered (Rule `R-CR-14`).**
  - Rather than fabricating compensation figures or imputing unrepresentative national averages, the system cleanly abstains with the notice:
    > *"Decoupled market compensation estimates are currently calibrated exclusively for Tier-1 Indian tech hubs (Bangalore, Hyderabad, Pune, Mumbai, NCR). ArthaIQ honest abstention policy prevents ungrounded extrapolation."*
  - Full local learning roadmap, DAG sequencing, and flaw-finding practice remain 100% functional offline without degradation.

---

## 4. Deterministic Rubric Benchmarking & Latency Profiling

The deterministic scoring algorithm (`evaluate_scenario_attempt` in `compintel.career.scenario_scorer`) was profiled across 50 heterogeneous attempt submissions:

### Attempt Submission Matrix Summary

| Submission Profile | Attempts | Description & Injected Defects | Scoring Behavior | Pass Rate |
|---|:---:|---|---|:---:|
| **Expert / Perfect** | 15 | Exact target lines and matching defect categories flagged | $1.0\text{ pt}$ awarded per defect; 0 penalties. Total score $= 3.0 / 3.0$. | 100% |
| **Partial / Near-Miss** | 15 | Line offsets ($\pm 1$ line) and category misidentifications | Partial credit awarded ($0.5\text{ pt}$ per near-miss); 0 penalties. Net score: $1.0 - 1.5$. | 0% (Below pass threshold 2.0) |
| **Guessing / Over-flagging** | 10 | 4 completely spurious lines submitted across the artifact | Penalty deduction ($0.5\text{ pt} \times 4 = 2.0\text{ pt}$). Net score bounded at $0.0$. | 0% |
| **Minimal / Empty** | 10 | Empty submission or 1 invalid line flagged | Zero credits awarded; net score $0.0$. | 0% |

### Latency Distribution

Execution timing was recorded using high-resolution monotonic hardware timers (`time.perf_counter_ns`):

- **Mean Execution Time:** $20.92\ \mu\text{s}$ ($0.0209\text{ ms}$)
- **Median ($p_{50}$):** $17.20\ \mu\text{s}$ ($0.0172\text{ ms}$)
- **95th Percentile ($p_{95}$):** $30.30\ \mu\text{s}$ ($0.0303\text{ ms}$)
- **99th Percentile ($p_{99}$):** $88.50\ \mu\text{s}$ ($0.0885\text{ ms}$)
- **Target Threshold:** $\le 5.00\text{ ms}$ (Achieved **$165\times$ faster** than statutory ceiling).

### Mathematical Determinism Stress Test

To satisfy **ADR-0010**, **ADR-0013**, and Rule `R-CR-08`, an attempt submission combining exact hits, partial categories, and spurious flags was scored repeatedly 100 times in an isolated execution loop:
$$\text{Score Variance } \sigma^2 = \frac{1}{N-1} \sum_{i=1}^{100} (S_i - \bar{S})^2 = 0.000000$$
Scoring determinism is absolute. Zero non-deterministic LLM hallucinations or temperature variance exists on the scoring path.

---

## 5. Local-First Storage Footprint & India DPDP Act 2023 Compliance

Under **Rule `R-CR-12`** and **ADR-0012**, all user career profiles, diagnostic logs, and evidence ledgers reside exclusively in the client's local storage (IndexedDB) by default. Zero centralized user databases exist on the server.

### Storage Efficiency & Portability Benchmark
A full career state consisting of the user profile, 50 evidence records (covering demonstrated, self-reported, and unproven competencies), and 10 detailed scenario attempt results was serialized into the portable backup schema:

- **Total Payload Size:** $18,453\text{ bytes}$ ($18.02\text{ KB}$)
- **Headroom vs 100 KB Threshold:** $81.98\text{ KB}$ ($82\%$ safety margin)
- **JSON Roundtrip Fidelity:** $100\%$ exact bitwise reconstruction ($\text{Original} \equiv \text{Deserialized}$).

### India DPDP Act 2023 Section 12 Hard Wipe Verification
Under Section 12 of the India Digital Personal Data Protection Act 2023, data principals hold the fundamental right to full and instantaneous data erasure:

1. **Trigger:** User activates single-click "Hard Purge Career Ledger & Profile" in `CareerProfileCard.tsx` or `CareerLayout.tsx`.
2. **Execution:** Atomic purge of all 3 IndexedDB object stores (`career_profile`, `evidence_records`, `scenario_attempts`).
3. **Audit Measurement:** Post-purge data footprint $= 0\text{ bytes}$ retained. Zero server callbacks, zero retained shadows, and zero orphaned tokens.

---

## 6. Regulatory & Ethical Compliance Invariants

### 1. Zero Causal Compensation Promises (Rule `R-CR-01`, India CPA 2019)
- All roadmap duration estimates are phrased strictly as empirical pacing heuristics (`is_heuristic: true`). Solitary point estimates are prohibited.
- Market compensation panels display empirical statistical distributions ($P_{10}, P_{50}, P_{90}$) alongside role expectations.
- Outputs never state or imply that demonstrating a competency will increase salary by ₹X.
- Zero matches found for forbidden causal strings (`guarantee salary`, `will earn`, `boost your pay`).

### 2. Two Streams, Two Places (Rule `R-CR-02`)
- Competency progression and market compensation are completely decoupled in the data schema, API contracts, and user interface.
- Zero composite "career readiness scores" or "market value indices" are computed.

### 3. Practice, Not Certification (Rule `R-CR-11`)
- Scenarios are designated strictly as technical flaw-finding practice workspaces for capability self-reflection.
- The platform strictly rejects terms such as "certified", "exam", "grade", "accreditation", or "official assessment".

---

## 7. Operational Conclusions & Recommendations

The **ArthaIQ Career Architect** subsystem has successfully passed all synthetic telemetry and user journey verification milestones. The system is robust, sub-millisecond fast, mathematically deterministic, privacy-preserving, and legally compliant with Indian labor economics and statutory protections.

### Recommended Next Platform Initiatives:
1. **Pilot Cohort Onboarding:** Deploy Career Architect into closed pilot testing with initial cohorts of Indian tech practitioners across Bangalore and Hyderabad.
2. **Corpus Expansion:** Author additional scenario challenges for the remaining 11 competencies in the DATA family.
3. **Advanced Telemetry:** Continue logging client-side performance metrics and local export fidelity during live user interactions.

---

*Certified by the ArthaIQ Algorithmic Governance Panel — 2026-10-30*
