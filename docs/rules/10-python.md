# Python Architecture, Code Quality & Testing Rules (10-python)

| Field | Value |
|---|---|
| Topic | Python Engineering Standards, Layer Boundaries, Testing, and Error Handling |
| Governing Rule Families | `R-CD`, `R-TS`, `R-ER` |
| Audience | AI Assistant, Backend Engineers, Data Scientists |

---

## 1. Code Quality & Architecture Rules (R-CD)

| ID | Rule | Description |
|---|---|---|
| **R-CD-01** | **Strict Type Annotations** | 100% of functions, methods, and module-level variables must carry strict type annotations. Pass `mypy --strict` with zero warnings. |
| **R-CD-02** | **Ruff Enforcement** | Code must strictly pass `ruff check` and `ruff format --check`. Zero unformatted files permitted. |
| **R-CD-03** | **One-Way Layer Boundaries** | Strict architectural hierarchy enforced by `import-linter`. Schema $\to$ Governance $\to$ Ingestion/Quality $\to$ Normalization $\to$ Features $\to$ Models/Uncertainty $\to$ Serving. Lower layers never import higher layers. |
| **R-CD-04** | **Pydantic & Pandera Contracts** | All data frames verified by Pandera schemas; all request/response objects verified by Pydantic v2 schemas. |
| **R-CD-05** | **Zero Dead Code** | Remove unused imports, dead functions, and obsolete mocks. |
| **R-CD-06** | **Dependency Justification** | Any new dependency added to `pyproject.toml` requires explicit justification, version pinning in `uv.lock`, and security vulnerability scan with `pip-audit`. |
| **R-CD-07** | **Pure Core Serving** | Serving core estimation must be pure deterministic Python without disk I/O, database queries, or external network requests during inference. |
| **R-CD-08** | **Idempotent Pipelines** | Data pipelines and transformations must produce bit-for-bit identical outputs given identical inputs and random seeds. |
| **R-CD-09** | **Domain Driven Packages** | Keep domain logic isolated in `src/compintel/` and decoupled from framework adapters. |

---

## 2. Testing & Verification Rules (R-TS)

| ID | Rule | Description |
|---|---|---|
| **R-TS-01** | **Coverage Minimum** | Maintain >= 90.0% line and branch test coverage across all Python modules. Total repo coverage must never drop below 90%. |
| **R-TS-02** | **Test Pyramid Adherence** | Test suites must span Unit tests, Property-based tests (`hypothesis`), Contract tests, and Integration tests. |
| **R-TS-03** | **Synthetic Data Flagging** | Test fixtures using synthetic data must set `is_synthetic = True` and never be mixed into production metrics or model evaluation. |
| **R-TS-04** | **Order Independence** | All tests must be completely order-independent and free of shared mutable state to support parallel execution with `pytest-xdist`. |

---

## 3. Error Handling & Observability Rules (R-ER)

| ID | Rule | Description |
|---|---|---|
| **R-ER-01** | **RFC 9457 Problem Details** | All HTTP API errors return standard RFC 9457 `application/problem+json` schemas with `type`, `title`, `status`, `detail`, and `instance`. |
| **R-ER-02** | **Structured Logging** | Logs emitted as JSON with timestamp, level, correlation `request_id`, and event name. Zero raw print statements in production code. |
| **R-ER-03** | **Zero Silent Failures** | Catch specific exception types. Never write bare `except:` or `except Exception: pass`. Re-raise or quarantine with reason codes. |
| **R-ER-04** | **Data Quarantine Transparency** | Outliers and invalid records are placed in quarantine with unambiguous reason codes and logged in reconciliation metrics. |
