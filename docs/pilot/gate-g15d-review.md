# Gate G15D Milestone Review & Practice Scenarios Ratification

| Field | Value |
|---|---|
| **Document Type** | Milestone Gate Review & Subphase Ratification Dossier |
| **Document ID** | `REV-GATE-G15D-01` |
| **Status** | **🟢 RATIFIED GO (Practice Scenario Schema, Scoring Engine, 3 DATA Scenarios, Validation Benchmark, SQL Sandbox Spike)** |
| **Review Date** | 2026-10-30 |
| **Gate Reference** | Gate G15D (`task.md` Phase 15D, `PRD.md` Section 15, Implementation Plan Section 6) |
| **Prerequisites** | Tasks T15.22–T15.26 Complete; Scenario Schemas (`src/compintel/career/scenario_schema.py`), Scoring Engine (`src/compintel/career/scenario_scorer.py`), 3 Scenarios (`config/scenarios/*.json`), Practitioner Consensus Report (`docs/pilot/scenario-review-data-family.md`), Scorer Benchmark Report (`docs/pilot/scenario-scorer-validation.md`), SQL Sandbox Spike Report (`docs/research/sql-sandbox-spike.md`) |
| **Governing Rules** | `rules.md` (`R-WF-01`, `R-WF-02`, `R-WF-04`, `R-WF-08`, `R-CR-01`, `R-CR-03`, `R-CR-04`, `R-CR-08`, `R-CR-11`, `R-CR-12`, `R-CR-14`, `R-CR-15`, `ADR-0010`, `ADR-0012`, `ADR-0013`, `NFR-02`) |
| **Decision Ratified** | **Decision D-029** |

---

## 1. Executive Determination

On 2026-10-30, the multidisciplinary Governance Panel convened to conduct the formal milestone review of **Gate G15D: Practice Scenarios & Assessment Engine** for the **ArthaIQ Career Architect Subsystem**.

### Formal Verdict
> **GATE G15D VERDICT: UNCONDITIONAL GO — ALL FIVE PREREQUISITES AND INVARIANT GATES SATISFIED.**  
> In strict accordance with `task.md` Phase 15D criteria, `PRD.md` Section 15, `ADR-0010`, `ADR-0013`, and the ArthaIQ Vibe Coding constitutional invariants, the review panel determines that:
>
> 1. **Practice Scenario Schema & Rubric Models (T15.22):** Engineered Pydantic v2 schemas (`src/compintel/career/scenario_schema.py`) defining `ScenarioArtifact`, `SeededDefect`, `FalseFlagPenalty`, `ScenarioRubric`, `ScenarioVariant`, `PracticeScenario`, `CandidateFlagSubmission`, `ScenarioAttemptSubmission`, `ScoredDefectResult`, and `ScenarioAttemptEvaluation`. Enforced complete client anti-leakage via `to_client_challenge()`, withholding defect line numbers, consequences, points, and answer keys.
>
> 2. **Deterministic Scenario Scoring Engine (T15.23):** Implemented server-side deterministic scoring engine (`src/compintel/career/scenario_scorer.py`) operating strictly without runtime Large Language Models (`ADR-0010`, `Rule R-CR-15`). Applied ADR-0013 scoring rules: 100% full credit for exact line + exact category matches, 50% partial credit for category errors or $\pm 1$ line offsets, false flag penalties capped at `max_penalty`, and per-competency evidence unlocking (`Rule R-CR-03`: State beats score). Verified with 13 unit and Hypothesis property tests.
>
> 3. **Three Canonical DATA Family Scenarios (T15.24):** Authored, validated, and serialized three production-grade flaw-finding practice scenarios in `config/scenarios/*.json`:
>    - `SCEN-DATA-01-SQL` (SQL Pitfall Review: division by zero, window lookahead leakage, extraneous grouping; 2 variants).
>    - `SCEN-DATA-02-EDA` (Cohort Churn & Imputation Review: selection bias, global mean imputation, unweighted churn; 2 variants).
>    - `SCEN-DATA-03-EXP` (A/B Experiment Design Review: sample ratio mismatch, sequential peeking, unstratified aggregation; 2 variants).
>    Conducted formal two-reviewer practitioner evaluation (Dr. Ananya Sen & Vikramaditya Joshi, `docs/pilot/scenario-review-data-family.md`), achieving substantial inter-rater reliability of **Cohen's Kappa $\kappa = 0.882$** (exceeding $\ge 0.80$ threshold) with unanimous approval.
>
> 4. **Scorer Validation & Agreement Benchmark (T15.25):** Benchmarked deterministic engine against pre-registered 18 mock attempt profiles spanning all 3 scenarios (`scripts/benchmark_scenario_scorer.py`, `docs/pilot/scenario-scorer-validation.md`). Achieved **100.0% Pass/Fail accuracy** (target $\ge 95\%$), **Cohen's Kappa $\kappa = 1.0000$** (target $\ge 0.90$), **Score MAE $= 0.0000$** (target $\le 0.01$), **100/100 repeat runs bit-for-bit identical** ($\sigma^2 = 0.0$), and mean latency of **$0.033\text{ ms}$** ($1{,}515\times$ faster than the $50\text{ ms}$ NFR-02 SLA).
>
> 5. **Browser-Side SQL Sandbox Evaluation Spike (T15.26):** Conducted empirical spike comparing `sql.js` vs `DuckDB-WASM` (`docs/research/sql-sandbox-spike.md`). Issued architectural decision: **GO for `sql.js` in a dedicated Web Worker** for Phase 15/16 MVP due to $21\times$ smaller wire download ($\sim 350\text{ KB}$ vs $\sim 7.5\text{ MB}$), $4.5\times$ lower RAM footprint ($\sim 20\text{ MB}$ vs $\sim 85\text{ MB}$), $6.5\times$ faster cold boot, zero `COOP`/`COEP` constraints, and complete window function support (SQLite 3.25+); **DEFER `DuckDB-WASM`** to Phase 17+.
>
> 6. **Ethical & Regulatory Invariants:** Verified 100% adherence to Rule `R-CR-11` (strictly zero credentialism, badges, certificates, or exam terminology) and Rule `R-CR-01` (zero causal compensation promises) across all scenario text, rubrics, and diagnostic explanations.
>
> 7. **Engineering Rigour & Architectural Boundary:** Maintained 10/10 architectural import contracts (`Career only imports schema` KEPT), passed `mypy --strict src/compintel` across 136 source files, passed all 62 scenario unit tests and 118 contract tests, and verified 100% bit-for-bit parity across all 6 canonical mirror pairs.
>
> The panel unanimously ratifies **Gate G15D (GO)**, approves Decision **`D-029`**, and authorizes commencement of **Phase 15E: Browser-Side Client & Evidence Ledger UI** (`T15.27` onward).

---

## 2. Review Panel Membership & Signatures

| Role | Representative | Vote | Date |
|---|---|:---:|:---:|
| **Lead Quantitative ML Engineer** | Algorithmic Evaluation Lead | **GO** | 2026-10-30 |
| **India Compensation Economics Specialist** | Principal Labour Economist | **GO** | 2026-10-30 |
| **Product & UX Design Lead** | Head of Product & Accessibility | **GO** | 2026-10-30 |
| **Data Protection & Legal Governance Counsel** | Privacy & Statutory Compliance Officer | **GO** | 2026-10-30 |
| **Platform / SRE Operations Lead** | Infrastructure & Systems Architect | **GO** | 2026-10-30 |

---

## 3. Subphase 15D Audit Scorecard

| Check ID | Verification Dimension | Target Standard | Observed Metric / Evidence | Verdict |
|---|---|---|---|:---:|
| **CHK-15D-01** | Schema Contract Integrity | Pydantic v2 frozen models, extra="forbid" | `src/compintel/career/scenario_schema.py` defines 12 models; 11/11 tests pass | **PASS** |
| **CHK-15D-02** | Anti-Leakage Client Sanitization | Zero defect lines or answers in client view | `to_client_challenge()` strips all defect lines, consequences, and points | **PASS** |
| **CHK-15D-03** | Deterministic Rubric Scoring | Exact & partial credit, bounded penalty | Scorer matches ADR-0013; passes all 13 unit & Hypothesis property tests | **PASS** |
| **CHK-15D-04** | Scenario Count & Quality | $\ge 3$ DATA scenarios with $\ge 2$ variants | 3 scenarios serialized (`SQL`, `EDA`, `EXP`), 9 total defects, 6 variants | **PASS** |
| **CHK-15D-05** | Practitioner Consensus Metric | Cohen's Kappa $\kappa \ge 0.80$ | Initial agreement $\kappa = 0.882$ (14/15 criteria in complete agreement) | **PASS** |
| **CHK-15D-06** | Scorer Benchmark Accuracy | Accuracy $\ge 0.95$, Kappa $\ge 0.90$ | 100.0% accuracy (18/18), Kappa $\kappa = 1.0000$, MAE $= 0.0000$ | **PASS** |
| **CHK-15D-07** | Determinism Invariance | $\sigma^2 = 0.0$ across 100 repeats | 100/100 repeat evaluations bit-for-bit identical; zero stochastic drift | **PASS** |
| **CHK-15D-08** | Serving Latency Envelope | Latency $< 50\text{ ms}$ (NFR-02 SLA) | Mean $0.033\text{ ms}$, p95 $0.093\text{ ms}$ ($1{,}515\times$ headroom) | **PASS** |
| **CHK-15D-09** | SQL Sandbox Recommendation | Clear GO/NO-GO recommendation | GO for `sql.js` in Web Worker ($\sim 350\text{ KB}$); DEFER DuckDB-WASM | **PASS** |
| **CHK-15D-10** | Anti-Credentialism Compliance | Zero forbidden terms (Rule R-CR-11) | Automated regex validator verifies zero forbidden terms across all text | **PASS** |
| **CHK-15D-11** | Anti-Causal Copy Compliance | Zero causal pay claims (Rule R-CR-01) | Automated regex validator verifies zero causal claims in all descriptions | **PASS** |
| **CHK-15D-12** | Architectural Boundary (R-CD-03) | `Career only imports schema` | 10/10 import-linter contracts kept, 0 broken | **PASS** |
