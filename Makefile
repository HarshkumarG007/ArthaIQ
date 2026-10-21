# Makefile — CompIntel
# See docs/architecture.md section 14 for the CI/CD pipeline.
# Versions are pinned at T3.01. Many targets are stubs until their phase starts.

.PHONY: help check lint typecheck boundary-check test test-unit test-property test-contract \
        test-leakage test-integration test-synthetic coverage-map sufficiency reproduce-data quality-report \
        audit-leakage experiment reproduce-experiment baseline-report benchmark-gbm conformal-report \
        interval-usefulness shift-stress-tests audit-abstention champion-bundle hierarchical-diagnostics \
        benchmark-latency final-eval migrate-up migrate-down migrate-reset migrate-check test-migrations security-scan \
        preview-up preview-down preview-health qa-smoke load-test fairness-audit-v2 clean


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

# ---- Experiments & Reproducibility (Phase 4, T4.07, R-MD-10, ADR-0006) ----
# Usage: make experiment [CONFIG=<path>] [SEED=<int>] [ALLOW_SYNTHETIC=1]
experiment:
	uv run python scripts/run_experiment.py $(if $(CONFIG),--config $(CONFIG),) $(if $(SEED),--seed $(SEED),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# Usage: make reproduce-experiment RUN=<run_id_or_path> [TOLERANCE=1e-9]
reproduce-experiment:
	uv run python scripts/run_experiment.py --reproduce $(RUN) $(if $(TOLERANCE),--tolerance $(TOLERANCE),)

# ---- Baseline Evaluation Report (Phase 4, T4.08, Rule R-MD-05) -------------
# Usage: make baseline-report [SNAPSHOT=<id>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
baseline-report:
	uv run python scripts/generate_baseline_report.py $(if $(SNAPSHOT),--snapshot-id $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Rung D Benchmark & Baseline Comparison (Phase 5, T5.01b, Rule R-MD-05) -
# Usage: make benchmark-gbm [SNAPSHOT=<id>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
benchmark-gbm:
	uv run python scripts/run_gbm_benchmark.py $(if $(SNAPSHOT),--snapshot-id $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Conformal Coverage & Calibration Report (Phase 5, T5.04, Rules R-MD-05, R-UQ-03) -
# Usage: make conformal-report [SNAPSHOT=<id>] [SEED=<int>] [SPLIT=<select|calibrate>] [COVERAGE=<float>] [ALLOW_SYNTHETIC=1]
conformal-report:
	uv run python scripts/generate_conformal_report.py $(if $(SNAPSHOT),--snapshot-id $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(COVERAGE),--nominal-coverage $(COVERAGE),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Interval Usefulness Report (Phase 5, T5.05, Rules R-UQ-04, EXP-02) -----
# Usage: make interval-usefulness [SNAPSHOT=<id>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
interval-usefulness:
	uv run python scripts/evaluate_interval_usefulness.py $(if $(SNAPSHOT),--snapshot-id $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Shift Stress Tests Report (Phase 5, T5.06, Rules R-UQ-04, EXP-03) -------
# Usage: make shift-stress-tests [SNAPSHOT=<id>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
shift-stress-tests:
	uv run python scripts/run_shift_stress_tests.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Abstention & Coverage Audit (Phase 5, T5.07, Rules R-UQ-02, R-UQ-07, EXP-11) -
# Usage: make audit-abstention [SNAPSHOT=<id>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
audit-abstention:
	uv run python scripts/audit_abstention.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Model Bundle & Champion Promotion (Phase 5, T5.08, Rule R-MD-14) -------
# Usage: make champion-bundle [SNAPSHOT=<path>] [OUTPUT_DIR=<path>] [ALLOW_SYNTHETIC=1]
champion-bundle:
	uv run python scripts/build_champion_bundle.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(OUTPUT_DIR),--output-dir $(OUTPUT_DIR),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Hierarchical Diagnostics & Prior/Posterior Checks (Phase 6, T6.02b, Rules R-UQ-06, EXP-05) -
# Usage: make hierarchical-diagnostics [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
hierarchical-diagnostics:
	uv run python scripts/run_hierarchical_diagnostics.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Stage-Wise Progressive Personalization Evaluation (Phase 6, T6.03b, Rules R-MD-05, R-MD-15, R-UQ-01) -
# Usage: make stagewise-evaluation [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
stagewise-evaluation:
	uv run python scripts/run_stagewise_evaluation.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Feature-Family Ablation Study (Phase 6, T6.04, Rules R-MD-05, R-MD-09, EXP-06) -
# Usage: make family-ablation [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
family-ablation:
	uv run python scripts/run_family_ablation.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Current Pay Anchoring & Selection Analysis (Phase 6, T6.05, Rules R-MD-05, R-MD-13, EXP-07) -
# Usage: make anchoring-analysis [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
anchoring-analysis:
	uv run python scripts/run_anchoring_analysis.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Missingness Study & Indicator Justification (Phase 6, T6.06, Rule R-MD-15) ------------
# Usage: make missingness-study [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
missingness-study:
	uv run python scripts/run_missingness_study.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Sparse Cell Benchmark: Hierarchical vs Conformal GBM (Phase 6, T6.07, EXP-05) --------
# Usage: make sparse-cell-benchmark [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
sparse-cell-benchmark:
	uv run python scripts/run_sparse_cell_benchmark.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Staged vs Joint Modelling Analysis (Phase 6, T6.08, EXP-08) --------------------------
# Usage: make staging-analysis [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
staging-analysis:
	uv run python scripts/run_staging_analysis.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Fairness Audit v1: Errors, Coverage, Abstention & Availability (Phase 6, T6.09, EXP-09) -
# Usage: make fairness-audit [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
fairness-audit:
	uv run python scripts/run_fairness_audit.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Skills Feature Modeling Experiment: Taxonomy vs Sentence Embeddings (Phase 7, T7.02, EXP-09) -
# Usage: make skills-experiment [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
skills-experiment:
	uv run python scripts/run_skills_experiment.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Career Trajectory Modeling Experiment: Tenure & Velocity (Phase 7, T7.03, EXP-08) -
# Usage: make career-trajectory-experiment [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
career-trajectory-experiment:
	uv run python scripts/run_career_trajectory_experiment.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Employer Feature Modeling Experiment: Simple vs Graph Embeddings (Phase 7, T7.04, EXP-10) -
# Usage: make employer-graphs-experiment [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1]
employer-graphs-experiment:
	uv run python scripts/run_employer_graphs_experiment.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,)

# ---- Macro & Market-Regime Experiment (Phase 7, T7.05, EXP-MACRO) ------------------
# Usage: make macro-regimes-experiment [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1] [FORCE_MODELING=1]
macro-regimes-experiment:
	uv run python scripts/run_macro_regimes_experiment.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,) $(if $(FORCE_MODELING),--force-modeling,)

# ---- Quantile Model Ensembling & Stacking Experiment (Phase 7, T7.06, EXP-ENSEMBLE) ---
# Usage: make ensembling-experiment [SNAPSHOT=<path>] [SEED=<int>] [SPLIT=<select|calibrate>] [ALLOW_SYNTHETIC=1] [FORCE_MODELING=1]
ensembling-experiment:
	uv run python scripts/run_ensembling_experiment.py $(if $(SNAPSHOT),--canonical-path $(SNAPSHOT),) $(if $(SEED),--seed $(SEED),) $(if $(SPLIT),--split $(SPLIT),) $(if $(ALLOW_SYNTHETIC),--allow-synthetic,) $(if $(FORCE_MODELING),--force-modeling,)

# ---- Serving Latency Benchmark (Phase 9, T9.03, NFR-02) --------------------
# Usage: make benchmark-latency [ITERATIONS=<int>] [WARMUP=<int>] [PROFILE=<str>]
benchmark-latency:
	uv run python scripts/benchmark_serving_latency.py $(if $(ITERATIONS),--iterations $(ITERATIONS),) $(if $(WARMUP),--warmup $(WARMUP),) $(if $(PROFILE),--profile-name "$(PROFILE)",)

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

# ---- Database & Migrations (Phase 9, T9.06, ADR-0008) ----------------------
migrate-up:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-reset:
	uv run alembic downgrade base

migrate-check:
	uv run alembic upgrade head --sql

test-migrations:
	uv run pytest tests/integration/test_migrations.py -v

# ---- Frontend Foundation & Design Tokens (Phase 9, T9.07) ------------------
check-contrast:
	uv run python scripts/check_contrast.py

verify-fonts:
	uv run python scripts/verify_fonts.py

# ---- Security Verification (Phase 9, T9.12) --------------------------------
security-scan:
	uv run python scripts/run_security_scan.py

# ---- Docker (Phase 9+) -----------------------------------------------------
build-image:
	docker build -t compintel:dev -f infra/docker/Dockerfile .

compose-up:
	docker compose -f infra/docker/docker-compose.yml up -d

compose-down:
	docker compose -f infra/docker/docker-compose.yml down

preview-up:
	uv run python scripts/deploy_preview.py up --build --wait

preview-down:
	uv run python scripts/deploy_preview.py down

preview-health:
	uv run python scripts/deploy_preview.py health

qa-smoke:
	uv run python scripts/run_qa_smoke.py

load-test:
	uv run python scripts/run_load_test.py --dry-run

fairness-audit-v2:
	uv run python scripts/run_fairness_audit_v2.py --allow-synthetic

# ---- Clean -----------------------------------------------------------------
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
