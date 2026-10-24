---
trigger: glob
description: Python typing, layer boundaries, code quality, testing pyramid, and error handling rules
globs: "**/*.py"
---

# Python Engineering Rules (R-CD, R-TS, R-ER)

Consult canonical specification in `docs/rules/10-python.md`.

## Key Invariants
1. **R-CD-01:** 100% strict type annotations; pass `mypy --strict src/compintel` cleanly.
2. **R-CD-02:** Strict `ruff check` and `ruff format --check` compliance.
3. **R-CD-03:** Strict one-way layer boundaries validated by `import-linter`.
4. **R-CD-04:** Enforce Pandera schema contracts on DataFrames and Pydantic v2 contracts on request/response payloads.
5. **R-CD-07:** Pure core serving without disk I/O, database queries, or network calls during inference.
6. **R-TS-01:** Maintain >= 90.0% test coverage across all domain modules.
7. **R-TS-04:** Ensure all tests are order-independent and safe for parallel execution with `pytest-xdist`.
8. **R-ER-01:** Standard RFC 9457 `application/problem+json` error responses.
9. **R-ER-03:** Zero silent exception swallowing; catch specific types and log structured JSON events.
