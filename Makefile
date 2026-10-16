# Makefile — CompIntel
# See docs/architecture.md section 14 for the CI/CD pipeline.
# Versions are pinned at T3.01. Many targets are stubs until their phase starts.

.PHONY: help check lint typecheck boundary-check test test-unit test-property test-contract \
        test-leakage test-integration test-synthetic coverage-map sufficiency reproduce-data quality-report \
        audit-leakage final-eval clean


# ---- Help ------------------------------------------------------------------
help:
	@echo "CompIntel development targets"
	@echo ""
	@echo "  make check            Full local check (lint + types + tests)"
	@echo "  make lint             ruff lint and format check"
	@echo "  make typecheck        mypy strict"
	@echo "  make test             All test suites"
	@echo "  make test-unit        Unit tests only"
	@echo "  make test-property    Hypothesis property tests"
	@echo "  make test-contract    Data and API contract tests"
	@echo "  make test-leakage     Leakage and split tests"
	@echo "  make test-integration Integration tests"
	@echo "  make test-synthetic   Synthetic fixture tests (R-MD-11)"
	@echo "  make reproduce-data   Rebuild canonical data from raw manifests (T3.13)"
	@echo "  make quality-report   Generate data quality audit report and JSON (T3.14)"
	@echo "  make final-eval       Run the pre-registered final evaluation (T4.03)"
	@echo "  make clean            Remove generated files"
	@echo ""
	@echo "Pinned versions: see pyproject.toml (finalized at T3.01)"

# ---- Full check (used in CI) -----------------------------------------------
check: lint typecheck boundary-check test-cov

# ---- Lint ------------------------------------------------------------------
lint:
	ruff check src/ tests/ scripts/
	ruff format --check src/ tests/ scripts/

lint-fix:
	ruff check --fix src/ tests/ scripts/
	ruff format src/ tests/ scripts/

# ---- Types -----------------------------------------------------------------
typecheck:
	mypy src/compintel

# ---- Architecture boundary check (R-CD-03) --------------------------------
boundary-check:
	lint-imports


# ---- Tests -----------------------------------------------------------------
test:
	pytest tests/ -m "not e2e and not slow"

test-unit:
	pytest tests/unit/ -m "unit"

test-property:
	pytest tests/property/ -m "property"

test-contract:
	pytest tests/contract/ -m "contract"

test-leakage:
	pytest tests/leakage/ -m "leakage"

test-integration:
	pytest tests/integration/ -m "integration"

test-synthetic:
	pytest tests/ -m "synthetic"

test-e2e:
	pytest tests/e2e/ -m "e2e"

test-cov:
	pytest tests/ -m "not e2e" --cov=src/compintel --cov-report=term-missing --cov-report=html

# ---- Sufficiency & Coverage (Phase 2, T2.07 & T2.09) -----------------------
coverage-map:
	python scripts/compute_coverage_map.py

sufficiency:
	python scripts/compute_sufficiency.py


# ---- Data pipeline (Phase 3+) ----------------------------------------------
# Usage: make reproduce-data SNAPSHOT=<snapshot_id>
reproduce-data:
	uv run python scripts/reproduce_data.py $(if $(SNAPSHOT),--snapshot $(SNAPSHOT),)

# Usage: make quality-report [VERIFY=1]
quality-report:
	uv run python scripts/generate_data_quality_report.py $(if $(VERIFY),--verify-thresholds,)

# ---- Leakage & Baseline Audits (Phase 4, T4.06, EXP-12) --------------------
# Usage: make audit-leakage [SNAPSHOT=<id>] [ALLOW_SYNTHETIC=1]
audit-leakage:
	uv run python scripts/run_leakage_audit.py $(if $(SNAPSHOT),--snapshot-id $(SNAPSHOT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Final evaluation (Phase 4+, R-MD-02) ----------------------------------
# IMPORTANT: This touches the final test set. Running it twice is a violation
# unless you declare the first run contaminated and refresh the test period.
# A lock file is written after the first run.
# Usage: make final-eval [DRY_RUN=1] [CONTAMINATION_REASON="..."] [OPERATOR="..."]
final-eval:
	uv run python scripts/run_final_eval.py $(if $(DRY_RUN),--dry-run,) $(if $(CONTAMINATION_REASON),--declare-contamination "$(CONTAMINATION_REASON)",) $(if $(OPERATOR),--operator "$(OPERATOR)",)

# ---- Pre-commit (install once) ---------------------------------------------
install-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg

# ---- Security --------------------------------------------------------------
audit:
	pip-audit
	bandit -r src/compintel/ -ll

# ---- Docker (Phase 9+) -----------------------------------------------------
build-image:
	docker build -t compintel:dev -f infra/docker/Dockerfile .

compose-up:
	docker compose -f infra/docker/docker-compose.yml up -d

compose-down:
	docker compose -f infra/docker/docker-compose.yml down

# ---- Clean -----------------------------------------------------------------
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
