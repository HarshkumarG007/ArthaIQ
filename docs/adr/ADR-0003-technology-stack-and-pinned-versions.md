# ADR-0003: Technology Stack and Pinned Versions

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | T3.01 |
| Relates to | `architecture.md` section 6, `rules.md` library policy |

---

## Context

The full candidate stack is listed in `architecture.md` section 6. Versions are deliberately **not pinned** in this stub — pinning happens at T3.01, when current versions and compatibility are verified against a real machine (Q-003). Every `[U]` in the stack table must be resolved at T3.01 before the lockfile is created.

Banned technologies (GPU, distributed compute, vector databases, GNN libraries, Kubernetes) require an ADR and an experiment charter to become un-banned.

## Proposed stack (to be verified and pinned at T3.01)

| Layer | Choice | Why |
|---|---|---|
| Language | Python (newest stable minor supported by all pinned dependencies) | ML ecosystem |
| Packaging | `uv` with a lockfile, or pip-tools | Reproducible installs |
| Dataframes | Polars primary; pandas only at library boundaries | Speed and memory on a laptop |
| Analytics SQL | DuckDB over Parquet | Zero-server analytics |
| File format | Parquet via pyarrow | Typed, columnar |
| App database | PostgreSQL, SQLAlchemy 2, Alembic | Consent, contributions, audit log |
| Validation | Pydantic v2 at boundaries; pandera for dataframes | Contracts in code |
| Data versioning | Content-hashed manifests; DVC if remote storage needed | Lineage with little machinery |
| Classical ML | scikit-learn, statsmodels | Baselines B and E |
| Gradient boosting | LightGBM and CatBoost (competing) | Quantile objectives `[U: confirm in current docs]` |
| Hierarchical models | Empirical Bayes first; PyMC, Stan or NumPyro if justified | Partial pooling |
| Conformal | In-house split conformal and CQR, or MAPIE `[U: confirm maintenance]` | Calibrated intervals |
| Explainability | SHAP for tree models | Deferred to Phase 7 |
| Text features | rapidfuzz, TF-IDF; sentence-transformers CPU as experimental | Title and skill matching |
| Hyperparameter search | Budgeted random search; Optuna only if justified | Bounded effort |
| Experiment records | File-based run records; MLflow if collaboration needs it | Least machinery |
| Serving | FastAPI, Pydantic v2, Uvicorn | Typed contracts, OpenAPI |
| Frontend | TypeScript, React, Vite, Tailwind CSS, shadcn/ui primitives | Mainstream, AI-assistant friendly |
| Charts | Custom SVG for the Span; small chart library only if needed | Key visual is bespoke |
| Client data and forms | TanStack Query, React Hook Form, Zod | Typed forms and caching |
| Auth | Managed OIDC provider or invite tokens | Deferred to Phase 9 |
| Logging and metrics | structlog; OpenTelemetry `[TBD: backend]` | Structured, PII-free |
| Python quality | ruff, mypy, pytest, hypothesis, pytest-cov, import-linter, pre-commit, nbstripout | Enforce rules.md |
| Frontend quality | ESLint jsx-a11y, Prettier, Vitest, Testing Library, Playwright, axe-core | Accessibility |
| Security tooling | gitleaks, pip-audit, npm audit, Dependabot/Renovate, bandit | Supply-chain hygiene |
| CI/CD | GitHub Actions or equivalent | Gate merges |
| Containers | Docker and Compose | Same runtime everywhere |

## Items to verify at T3.01

- [ ] Python: confirm newest stable minor that all deps support
- [ ] LightGBM and CatBoost: confirm quantile objective API in current versions
- [ ] MAPIE: confirm maintenance status and API stability
- [ ] Polars: confirm version compatible with DuckDB integration
- [ ] Pydantic v2: confirm SQLAlchemy 2 integration
- [ ] Frontend package versions: React, Vite, shadcn/ui, TanStack Query
- [ ] Machine benchmark (Q-003): CPU cores, RAM, storage speed
- [ ] Licence compatibility: all packages checked

## Decision

**Pending.** Finalized at T3.01.

## Consequences

- The lockfile (`uv.lock` or `requirements*.txt`) is committed at T3.02.
- Any version change after T3.01 is a PR with a justification and re-verification.
- Banned items remain banned unless a new ADR approves them.

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
