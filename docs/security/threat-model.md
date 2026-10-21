# CompIntel Threat Model (T9.12b)

**Status:** Ratified  
**Version:** 1.0.0  
**Date:** 2026-10-21  
**Framework:** STRIDE (Microsoft / OWASP)  
**Applicable Scope:** Public Serving API, Governance Intake & Erasure Service, Prometheus Telemetry, Web Client  
**Applicable Rules:** PRD Section 8 NFR-03/04/07, ADR-0008, Rules `R-CD-06`, `R-DA-07`, `R-DA-10`, `R-MD-13`, `R-ER-04`, `R-CD-08`.

---

## 1. System Architecture & Trust Boundaries

The CompIntel architecture processes two distinct classes of data:
1. **Public Query Profiles (Ephemeral / Stateless)**: User queries (`POST /v1/estimates`) seeking empirical compensation ranges (P10, P50, P90). Queries contain no names or direct identifiers and are processed purely in-memory.
2. **Voluntary Compensation Contributions (Stateful / Governed)**: Self-reported salary submissions (`POST /v1/contributions`) protected under DPDPA 2023, requiring unbundled consent, bounds quarantine, $k_{\min} \ge 5$ thresholding, and irrevocable statutory erasure (`POST /v1/contributions/delete`).

```
+-----------------------------------------------------------------------------------+
| TRUST BOUNDARY 0: Public Internet (Untrusted User Agent / Browser)                |
+-----------------------------------------------------------------------------------+
       |                                                    |
       | HTTPS (TLS 1.3)                                    | HTTPS (TLS 1.3)
       v                                                    v
+-------------------------------+              +------------------------------------+
| Web Client (apps/web)         |              | Reverse Proxy / API Gateway        |
| - Pure CSR SPA                |              | - Rate limiting (100 req/min)      |
| - Static Assets (No secrets)  |              | - TLS Termination, HSTS            |
+-------------------------------+              +------------------------------------+
                                                            |
+-----------------------------------------------------------v-----------------------+
| TRUST BOUNDARY 1: Application Serving Runtime (compintel.serving)                 |
| - SecurityHeadersMiddleware (CSP, HSTS, X-Content-Type-Options: nosniff)          |
| - RequestLoggingMiddleware (Correlation ID, PII-masked structlog)                 |
| - RFC 9457 Problem Details Exception Handlers (Zero stack trace leakage)          |
+-----------------------------------------------------------------------------------+
       |                                                    |
       v                                                    v
+-------------------------------+              +------------------------------------+
| Serving Router (/v1/estimates)|              | Governance Router                  |
| - Pure pure_estimate()        |              | - /v1/contributions                |
| - Compare-Only quarantine     |              | - /v1/contributions/delete         |
|   (R-MD-13: current pay       |              | - Unbundled consent enforcement    |
|    quarantined from features) |              | - HMAC-SHA256 deletion tokens      |
+-------------------------------+              +------------------------------------+
       |                                                    |
       v                                                    v
+-------------------------------+              +------------------------------------+
| Champion Model Bundle         |              | Governance Persistence Store       |
| - Local read-only disk        |              | - PostgreSQL / SQLite (asyncpg)    |
| - SHA-256 verified manifests  |              | - Pseudonymized contributor keys   |
| - Conformal quantile weights  |              | - Immutable append-only audit trail|
+-------------------------------+              +------------------------------------+
```

---

## 2. Threat Analysis (STRIDE Matrix)

### S — Spoofing Identity

| Threat ID | Threat Scenario | Component Affected | Severity | Existing Mitigation & Verification | Residual Risk |
|---|---|---|---|---|---|
| **STRIDE-S01** | Attacker forges an `X-Request-ID` header to correlate or inject malicious tracing logs. | `RequestLoggingMiddleware` | Low | Middleware validates UUID format; if malformed or missing, a cryptographically secure `uuid.uuid4()` is generated. Verified in `test_error_contracts.py`. | Negligible |
| **STRIDE-S02** | Attacker presents a forged deletion token to delete another contributor's data. | `POST /v1/contributions/delete` | High | Deletion tokens use HMAC-SHA256 with server-side secrets (`hmac.compare_digest` constant-time comparison). Contributor keys cannot be guessed. Verified in `test_contribution_lifecycle.py`. | Negligible |
| **STRIDE-S03** | Malicious third-party frames or spoofs the frontend client. | `apps/web` | Medium | `SecurityHeadersMiddleware` sets `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`, and `X-Content-Type-Options: nosniff`. | Negligible |

---

### T — Tampering with Data

| Threat ID | Threat Scenario | Component Affected | Severity | Existing Mitigation & Verification | Residual Risk |
|---|---|---|---|---|---|
| **STRIDE-T01** | Poisoning attacks on voluntary contribution intake (flooding with fake extreme salaries). | `POST /v1/contributions` | High | 1. Mandatory quarantine bounds ($[0.5, 500]$ LPA; YoE $[0, 45]$) under Rule `R-DA-05`.<br>2. 90-day quarantine isolation holding before canonical promotion.<br>3. Statistical outlier flagging and automatic quarantine quarantine rejection. | Low (governed pipeline) |
| **STRIDE-T02** | Modification or replacement of model weights in production runtime. | `compintel.serving.loader` | High | Model bundles are read-only artifacts verified by cryptographic SHA-256 manifests at load time. Runtime filesystem permissions enforce read-only execution. | Negligible |
| **STRIDE-T03** | Manipulating estimation query body to inject invalid numeric or categorical types. | `POST /v1/estimates` | Medium | Strict Pydantic models reject unapproved fields, out-of-range floats, non-INR currencies, and non-guaranteed cash measures with HTTP 422 RFC 9457 Problem Details. | Negligible |

---

### R — Repudiation

| Threat ID | Threat Scenario | Component Affected | Severity | Existing Mitigation & Verification | Residual Risk |
|---|---|---|---|---|---|
| **STRIDE-R01** | Contributor claims they never granted consent under DPDPA 2023. | `compintel.governance.service` | High | Consent is unbundled into distinct non-pre-ticked boolean flags (`terms`, `privacy`, `research`). Consent timestamps, policy version hashes, and request correlation IDs are committed to the tamper-evident audit log. | Negligible |
| **STRIDE-R02** | Contributor claims their deletion request was ignored or unfulfilled. | `compintel.governance.service` | Medium | Deletion generates an immutable audit receipt with timestamp, deleted record count, and zero personal data, while purging operational records irreversibly. Verified in `test_contribution_lifecycle.py`. | Negligible |

---

### I — Information Disclosure (Privacy & PII)

| Threat ID | Threat Scenario | Component Affected | Severity | Existing Mitigation & Verification | Residual Risk |
|---|---|---|---|---|---|
| **STRIDE-I01** | **Current Pay Anchoring Leakage**: Attacker uses current salary comparison to infer private model internal state. | `POST /v1/estimates` | High | **Rule `R-MD-13` (Compare-Only Quarantine)**: Current pay (`current_salary_inr`) is strictly excluded from feature matrix $X$ and ML estimators. It only enters downstream post-prediction positioning. Verified in `test_estimates_contract.py`. | Negligible |
| **STRIDE-I02** | **Membership Inference / Re-identification**: Querying very small employer/seniority slices to infer an individual's actual compensation. | `POST /v1/estimates`, `compintel.uncertainty.support` | High | 1. Anonymization floor: employer cluster nodes with $N < 5$ are collapsed to parent industry tiers (Rule `R-DA-10`).<br>2. Thin-evidence abstention: cells with $N < 10$ return calm abstention notices (`THIN_COHORT_EVIDENCE`) without disclosing numeric bounds. Verified in contract tests. | Negligible |
| **STRIDE-I03** | **Telemetry PII Leakage**: High-cardinality user inputs (e.g. raw role titles or exact salaries) leaking into Prometheus metric labels. | `compintel.monitoring.metrics`, `GET /metrics` | High | **Rule `R-DA-07`**: Metric labels are strictly restricted to low-cardinality whitelisted enums (`role_family`, `metro_location`, `reason_code`, `evidence_grade`). Exact salaries and raw text are never labelled. | Negligible |
| **STRIDE-I04** | **Exception Stack Trace Disclosure**: Internal server errors exposing filesystem paths or database connection strings. | `compintel.serving.errors` | High | **Rule `R-ER-04`**: Global RFC 9457 exception handler catches generic exceptions, logs full trace to masked internal logger, and returns sanitized generic message with correlation ID. Verified in `test_error_contracts.py`. | Negligible |

---

### D — Denial of Service (DoS)

| Threat ID | Threat Scenario | Component Affected | Severity | Existing Mitigation & Verification | Residual Risk |
|---|---|---|---|---|---|
| **STRIDE-D01** | **Prometheus Metric Cardinality Explosion**: Sending random URLs or query strings to exhaust memory via dynamically generated metric labels. | `RequestLoggingMiddleware` | High | Path normalization: all incoming paths are mapped to static `_KNOWN_PATHS` or collapsed to `/unknown` / `/v1/taxonomy/{param}`. Path cardinality is bounded to $< 30$ distinct labels. | Negligible |
| **STRIDE-D02** | Heavy compute requests via complex profile queries or batch estimations. | `POST /v1/estimates` | Medium | Pure model inference is optimized to $\le 15\text{ms}$ on CPU (CatBoost tree evaluation without deep transformers per EXP-09). Production deployment fronted by gateway rate limiting (100 req/min). | Negligible |
| **STRIDE-D03** | Algorithmic complexity attack on string fuzzy matching in taxonomy lookups. | `POST /v1/taxonomy/occupations` | Low | Search queries bounded in length ($\le 100$ characters) with `rapidfuzz` score thresholds and capped result count ($\le 20$). | Negligible |

---

### E — Elevation of Privilege

| Threat ID | Threat Scenario | Component Affected | Severity | Existing Mitigation & Verification | Residual Risk |
|---|---|---|---|---|---|
| **STRIDE-E01** | Unauthorized administrative execution or database schema alteration via API endpoints. | FastAPI serving app | Critical | The API exposes zero administrative endpoints, zero eval execution routes, and zero dynamic SQL execution (`SQLAlchemy` parameterized queries only). | Negligible |
| **STRIDE-E02** | Contributor uses deletion token to delete records belonging to other users. | `POST /v1/contributions/delete` | High | Deletion queries strictly match `WHERE contributor_key = :resolved_key`. Tokens are mathematically tied to the specific record hash. Verified in `test_contribution_lifecycle.py`. | Negligible |

---

## 3. Privacy Attacks & Defences Deep-Dive

### 3.1 Model Inversion & Reconstruction Attacks
- **Threat**: An adversary issues thousands of synthetic queries across a grid of YoE and locations to invert the model weights or reconstruct individual training records.
- **Defences**:
  1. The model predicts population quantiles (P10, P50, P90) calibrated via split-conformal prediction, not individual point targets.
  2. Rung F Conformal CatBoost uses regularization (`l2_leaf_reg=5.0`, `depth=6`), preventing leaf-level memorization.
  3. Continuous outputs have intrinsic interval width; exact point salaries are never reported.
  4. Query profiles in sparse regions trigger thin-evidence abstention rather than overfitted extrapolation.

### 3.2 Linkage Attacks on Voluntary Intake
- **Threat**: An adversary combines voluntary contribution records with an external corporate directory.
- **Defences**:
  1. No personal identifiers (name, email, employee ID, exact date of birth) are requested or stored.
  2. Employer names are clustered into anonymized tiers ($k_{\min} \ge 5$).
  3. Contributor key is derived via one-way HMAC-SHA256 and salt, preventing reverse lookup.
  4. Operational deletion permanently purges all submission fields upon presentation of the deletion token.

---

## 4. Threat Model Ratification

- **High / Critical Unmitigated Risks:** **0**
- **Architecture Invariants Enforced:**
  - `R-MD-13`: Current pay compare-only quarantine
  - `R-DA-07`: Zero PII in metrics or log labels
  - `R-DA-10`: $k_{\min} \ge 5$ anonymization floor
  - `R-ER-04`: RFC 9457 error detail sanitization
  - ADR-0008: DPDPA 2023 unbundled consent and operational erasure cascade
