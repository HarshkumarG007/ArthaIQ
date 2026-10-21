# CompIntel Master Quality Assurance Plan (T9.15a)

| Metadata | Details |
|---|---|
| **Author** | CompIntel QA & Engineering Team |
| **Date** | 2026-10-21 |
| **Status** | **Approved** (T9.15a) |
| **Scope** | India Technology Compensation Intelligence Engine (Decision Support v1) |
| **Relates to** | PRD Sections 8 & 11, `rules.md`, `architecture.md` Section 14, `design.md` Section 11, Gate G9 Readiness |

---

## 1. Objectives & Executive Scope

This Master Quality Assurance Plan defines the testing methodology, automated validation suites, verification matrices, and quality gates for the **ArthaIQ Public Beta Release**.

The primary objective is to verify that all functional, statistical, security, architectural, and user experience thresholds pre-registered across PRD v1.0, ADR-0001 through ADR-0009, and the Project Constitution (`rules.md`) are strictly met with zero unmitigated critical defects.

---

## 2. Pre-Registered Product Thresholds Matrix

Every gate and release candidate must pass all pre-registered thresholds before public promotion (PRD Section 11 & Gate G9):

| Dimension | Metric / Requirement | Target / SLA | Rule / Contract Reference | Verification Method |
|---|---|---|---|---|
| **Serving Latency** | p95 HTTP response latency (Core & Refined profiles) | $\le 50\text{ ms}$ | PRD NFR-02, ADR-0009 | `scripts/benchmark_serving_latency.py` (measured 4.32ms) |
| **Model Accuracy** | Quantile loss improvement over Rung A (empirical) | $> 5.0\%$ test pinball reduction | PRD FR-03, Rule R-MD-05 | `make final-eval`, `experiments/results/` |
| **Uncertainty Calibration** | Nominal 80% coverage interval empirical coverage | $80.0\% \pm 2.0\%$ ($[78\%, 82\%]$) | Rule R-UQ-03, PRD NFR-01 | Conformal evaluation suite, `CoverageTracker` |
| **Interval Usefulness** | Median width ratio ($\text{IQR} / \text{median}$) | $\le 0.45$ across supported slices | Rule R-UQ-04, PRD FR-05 | `make interval-usefulness` |
| **Abstention Integrity** | Thin cohort ($N < 5$), out-of-support, extrapolation | Calibrated abstention, zero lone numbers | Rules R-UQ-01, R-UQ-02, R-DA-10 | `test_abstention.py`, `test_serving_contracts.py` |
| **Compare-Only Isolation** | Current salary never modifies quantiles or base model | Strict read-only anchoring isolation | Rule R-MD-13, EXP-07 | `test_feature_spec.py`, `PayCompare.test.tsx` |
| **Privacy Suppression** | Small-cell anonymization threshold ($k_{\min}$) | $k \ge 5$ distinct contributors | Rule R-DA-10, ADR-0008 | `test_contribution_lifecycle.py` |
| **Operational Erasure** | Irreversible statutory deletion of self-reported records | 100% cascade across operational DB | ADR-0008, DPDPA 2023 | `test_contribution_lifecycle.py` |
| **Code Coverage** | Test line coverage across core `compintel` modules | $\ge 90.0\%$ | Rule R-TS-03, `pyproject.toml` | `pytest --cov=src/compintel` (currently >94%) |
| **Static Types** | Strict type-checking with zero untyped code | 100% clean mypy (Python), zero `any` (TS) | Rule R-CD-01, R-CD-09 | `mypy src/compintel`, `tsc -b` |
| **Import Boundaries** | Clean layer hierarchy (serving never imports governance/ingestion) | 9 of 9 contracts kept (0 broken) | Rule R-CD-03 | `lint-imports` |
| **Security SAST & CVEs** | Dependency audit, secret scans, Bandit SAST | 0 Critical, 0 High vulnerabilities | Rule R-CD-08, OWASP ASVS | `scripts/run_security_scan.py` (0 vuln, 0 SAST) |
| **Accessibility** | Automated WCAG 2.2 AA contrast & axe compliance | 0 axe violations, contrast $\ge 4.5:1$ | Rules R-UI-01, R-UI-04 | `Accessibility.test.tsx`, `scripts/check_contrast.py` |
| **Web Vitals** | Frontend loading, interactivity, visual stability | LCP $< 2.5\text{s}$, CLS $< 0.1$, INP $< 200\text{ms}$ | PRD NFR-03 | Vite production build + headless audit |

---

## 3. The 8-Tier Quality Test Pyramid

The CompIntel verification suite is organized into 8 distinct automated tiers:

```
                  [ Tier 8: Load & Abuse Stress ]
                [ Tier 7: End-to-End Smoke Runner ]
              [ Tier 6: Multi-Component Integration ]
            [ Tier 5: Leakage & Temporal Split Audits ]
          [ Tier 4: Data & API RFC 9457 Contract Tests ]
        [ Tier 3: Property-Based Numeric Invariant Tests ]
      [ Tier 2: Fast Unit Tests (Backend & Frontend Vitest) ]
    [ Tier 1: Static Analysis, Types, Linters & Import Boundaries ]
```

### Tier 1: Static Analysis & Architectural Boundaries
- **Linter & Formatter:** Ruff 0.8+ (`ruff check src tests scripts`, `ruff format --check`).
- **Python Type Engine:** Mypy 1.13+ in `--strict` mode across all 104 source modules.
- **Frontend Type Engine:** TypeScript 5.6+ with `noImplicitAny: true`, `strict: true`.
- **Architectural Boundary Linter:** `import-linter` enforcing 9 strict layer boundary contracts (Rule `R-CD-03`).

### Tier 2: Unit Testing (Backend & Frontend)
- **Backend Unit Tests:** Over 760 fast pytest unit tests (`tests/unit/`) executing in $< 5\text{ seconds}$ without external network or persistent storage dependencies.
- **Frontend Component Tests:** 89 Vitest unit tests (`apps/web/src/components/`) validating form state machines, formatting routines, RangeSpan dimension line math, and modal dialogues.

### Tier 3: Property-Based Testing
- **Hypothesis Invariant Tests:** `tests/property/` testing monotonic crossing repair ($P_{10} \le P_{50} \le P_{90}$), date parsing boundaries, and currency annualization across arbitrary inputs.

### Tier 4: Contract Testing
- **API Error Contracts:** Validates RFC 9457 `ProblemDetails` schema for 400, 404, 422, and 500 error responses (`tests/contract/test_error_contracts.py`).
- **Data Schemas:** Pandera dataframe schema validation against canonical observations (`tests/contract/test_data_contracts.py`).
- **OpenAPI Schema Diff:** Automated drift detection asserting committed `docs/api/openapi.json` matches current FastAPI route definitions (`tests/contract/test_openapi_drift.py`).
- **Prometheus Telemetry Contract:** Validates `/metrics` OpenMetrics format and label sanitization (`tests/contract/test_metrics_contract.py`).

### Tier 5: Leakage & Temporal Split Audits
- **Adversarial Temporal Check:** Proves no future observations leak into training or calibration splits (`tests/leakage/test_temporal_leakage.py`).
- **Group Overlap Check:** Proves no entity clusters or duplicate records straddle evaluation splits (`tests/leakage/test_group_leakage.py`).

### Tier 6: Integration Testing & Migrations
- **Database Migrations:** Tests Alembic migration cycle: `downgrade base` $\to$ `upgrade head` $\to$ `downgrade -1` $\to$ `upgrade head` (`tests/integration/test_migrations.py`).
- **Contribution Lifecycle:** End-to-end voluntary salary intake, bounds quarantine, $k_{\min}$ enforcement, HMAC token generation, and operational erasure cascade (`tests/integration/test_contribution_lifecycle.py`).
- **Monitoring & Alerting:** Fault injection test verifying PSI drift alerts, staleness alarms, and coverage drop alerts (`tests/integration/test_monitoring_fault_injection.py`).

### Tier 7: Automated End-to-End Smoke Verification
- Automated CLI runner `scripts/run_qa_smoke.py` executing all static, test, build, and container configuration checks in a single orchestrated command.

### Tier 8: Non-Functional & Stress Testing (T9.15b)
- **Concurrent Load Test:** Verifies p95 latency under 50 concurrent requests.
- **Abuse & Rate Limiting:** Verifies HTTP 429 Too Many Requests under burst query conditions.
- **Core Web Vitals & Responsiveness:** Evaluates responsive rendering across 320px, 768px, and 1280px viewports with zero layout shift (CLS $< 0.1$).

---

## 4. Test Environments & Tooling

| Environment | Purpose | Infrastructure | URL / Host |
|---|---|---|---|
| **Local Development** | Rapid developer feedback, TDD, linting | Profile A (workstation CPU, in-memory SQLite / mock DB) | `http://localhost:8000` |
| **CI Runner** | PR validation, gating, regression tests | GitHub Actions Ubuntu 24.04 (clean virtualenv) | Ephemeral headless |
| **Preview Container Stack** | Staging, load testing, smoke testing | Profile B Docker Compose (Nginx + FastAPI + Postgres 16) | `http://localhost:8080` |

---

## 5. Defect Classification & Triage Rubric

Defects identified during QA execution are categorized using the following severity rubric:

| Severity | Definition | SLA / Action |
|---|---|---|
| **P0 (Blocker)** | Privacy violation, statutory non-compliance (DPDPA 2023), arbitrary lone number displayed without evidence, p95 latency $> 500\text{ms}$, or serving crash. | Immediate halt. Must be fixed before any further task or gate promotion. |
| **P1 (Critical)** | Core estimate inaccurate, unhandled 500 internal server error, failure in operational erasure cascade, WCAG AA contrast failure, or open High/Critical CVE. | Blocks Gate G9. Must be resolved before Public Beta release. |
| **P2 (Major)** | Edge-case validation glitch, suboptimal mobile rendering at extreme zoom, non-blocking telemetry delay, or secondary error message typo. | Triaged and fixed in Phase 9 refinement backlog or pilot cycle. |
| **P3 (Minor)** | Code style cleanup, documentation clarification, non-critical dependency upgrade, or diagnostic logging enhancement. | Deferred to Phase 10 maintenance cycle. |

---

## 6. Exit Criteria for Public Beta Readiness (Gate G9)

1. **100% Automated Test Pass Rate:** All 760+ backend Python tests, 89 frontend Vitest tests, and integration test suites pass with zero failures.
2. **Zero Open P0 or P1 Defects:** All blocker and critical issues triaged and resolved.
3. **Pre-Registered Threshold Compliance:**
   - Latency: p95 $\le 50\text{ ms}$ (measured $4.32\text{ ms}$).
   - Coverage: Conformal coverage in $[78\%, 82\%]$.
   - Security: Zero Critical or High CVEs in locked dependencies; Bandit SAST clean.
   - Privacy: $k_{\min} \ge 5$ enforced; operational erasure cascade verified.
   - Code Coverage: $\ge 90.0\%$ core test coverage.
4. **Clean Builds & Containerization:** Multi-stage Docker containers build and start healthy under Docker Compose.
5. **Signed Documentation:** ADR-0001 through ADR-0009 ratified to **Accepted**.
