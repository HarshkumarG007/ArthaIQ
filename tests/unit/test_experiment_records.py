"""Comprehensive unit and reproduction tests for Experiment Records and Tracking (Task T4.07).

Governed by:
- Rule R-MD-10: Seed everything. Every run records data snapshot id, config, library
  versions, timings, peak memory, and commit, and reproduces with one command.
- Rule R-MD-02: Isolated final test set; routine experiments evaluate strictly on dev.
- Rule R-MD-05: Standard evaluation metrics suite.
- Rule R-MD-08: Thin evidence abstentions properly handled.
- Rule R-MD-11: Synthetic data flagged and blocked from canonical experiment tracking.
- Rule R-TS-03: Minimum 90% unit test coverage on new modules.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import polars as pl
import pytest
import yaml

from compintel.errors import CompIntelError, CompIntelValidationError, DataContractError
from compintel.evaluation.experiment import (
    ExperimentConfig,
    ExperimentRunner,
    ExperimentRunRecord,
    get_environment_manifest,
    get_git_commit,
    reproduce_experiment,
)


@pytest.fixture
def sample_experiment_df() -> pl.DataFrame:
    """Deterministic, multi-contributor evaluation DataFrame."""
    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:03d}" for i in range(1, 11)],
            "person_cluster_id": [
                "PER-001",
                "PER-002",
                "PER-003",
                "PER-004",
                "PER-005",
                "PER-006",
                "PER-007",
                "PER-008",
                "PER-009",
                "PER-010",
            ],
            "employer_cluster_id": [
                "EMP-001",
                "EMP-001",
                "EMP-002",
                "EMP-002",
                "EMP-003",
                "EMP-003",
                "EMP-004",
                "EMP-004",
                "EMP-005",
                "EMP-005",
            ],
            "role_family": [
                "software_engineering",
                "software_engineering",
                "software_engineering",
                "software_engineering",
                "software_engineering",
                "data_science",
                "data_science",
                "data_science",
                "machine_learning",
                "machine_learning",
            ],
            "seniority": [
                "junior",
                "mid",
                "senior",
                "staff",
                "lead",
                "junior",
                "mid",
                "senior",
                "mid",
                "senior",
            ],
            "metro_location": [
                "bengaluru",
                "bengaluru",
                "hyderabad",
                "pune",
                "delhi_ncr",
                "bengaluru",
                "mumbai",
                "hyderabad",
                "bengaluru",
                "delhi_ncr",
            ],
            "location": [
                "bengaluru",
                "bengaluru",
                "hyderabad",
                "pune",
                "delhi_ncr",
                "bengaluru",
                "mumbai",
                "hyderabad",
                "bengaluru",
                "delhi_ncr",
            ],
            "years_experience": [1.5, 3.5, 7.0, 11.0, 14.0, 2.0, 4.5, 8.0, 5.0, 9.5],
            "guaranteed_cash_annual": [
                12.0,
                20.0,
                35.0,
                55.0,
                75.0,
                14.0,
                24.0,
                38.0,
                30.0,
                48.0,
            ],
            "as_of_date": [
                date(2024, 1, 15),
                date(2024, 2, 20),
                date(2024, 3, 25),
                date(2024, 4, 10),
                date(2024, 5, 18),
                date(2024, 6, 22),
                date(2024, 7, 14),
                date(2024, 8, 30),
                date(2024, 9, 15),
                date(2024, 10, 5),
            ],
            "is_synthetic": [False] * 10,
            "is_pt1_eligible": [True] * 10,
        }
    )


@pytest.fixture
def synthetic_experiment_df(sample_experiment_df: pl.DataFrame) -> pl.DataFrame:
    """Fixture DataFrame flagged as synthetic (Rule R-MD-11)."""
    return sample_experiment_df.with_columns(pl.lit(True).alias("is_synthetic"))


class TestExperimentConfig:
    """Tests for ExperimentConfig validation, defaults, and serialization."""

    def test_default_config_valid(self) -> None:
        """Default config should be completely valid."""
        cfg = ExperimentConfig()
        assert cfg.experiment_name == "baseline_rung_ab_dev"
        assert cfg.seed == 42
        assert cfg.evaluation_split == "select"
        assert cfg.train_ratio == 0.60
        assert "rung_a_empirical" in cfg.models
        assert "rung_b_linear" in cfg.models

    def test_rule_r_md_02_locked_test_rejection(self) -> None:
        """Routine experiments configured with evaluation_split='test' must be rejected."""
        with pytest.raises(CompIntelValidationError) as exc:
            ExperimentConfig(evaluation_split="test")  # type: ignore[arg-type]
        assert "FINAL_TEST_PARTITION_LOCKED" in str(exc.value.code)

    def test_invalid_split_ratios_rejected(self) -> None:
        """Split ratios that are <= 0 or do not sum to 1.0 must fail."""
        with pytest.raises(CompIntelValidationError) as exc1:
            ExperimentConfig(train_ratio=0.0)
        assert "INVALID_SPLIT_RATIOS" in str(exc1.value.code)

        with pytest.raises(CompIntelValidationError) as exc2:
            ExperimentConfig(
                train_ratio=0.50, select_ratio=0.20, calibrate_ratio=0.10, test_ratio=0.10
            )
        assert "INVALID_SPLIT_RATIOS_SUM" in str(exc2.value.code)

    def test_serialization_round_trip(self, tmp_path: Path) -> None:
        """Config serializes to and parses from YAML cleanly."""
        cfg = ExperimentConfig(
            experiment_name="custom_eval",
            seed=123,
            evaluation_split="calibrate",
            models=["rung_b_linear"],
            model_params={"rung_b_linear": {"alpha": 0.05}},
            allow_synthetic=True,
        )

        yaml_str = cfg.to_yaml()
        assert "custom_eval" in yaml_str
        assert "123" in yaml_str

        # Parse from string
        loaded = ExperimentConfig.from_yaml(yaml_str)
        assert loaded.experiment_name == "custom_eval"
        assert loaded.seed == 123
        assert loaded.evaluation_split == "calibrate"
        assert loaded.models == ["rung_b_linear"]
        assert loaded.model_params["rung_b_linear"]["alpha"] == 0.05
        assert loaded.allow_synthetic is True

        # Parse from file
        cfg_file = tmp_path / "test_config.yaml"
        cfg_file.write_text(yaml_str, encoding="utf-8")
        from_file = ExperimentConfig.from_yaml(cfg_file)
        assert from_file.experiment_name == "custom_eval"
        assert from_file.seed == 123

    def test_from_yaml_invalid_content(self, tmp_path: Path) -> None:
        """Non-dict YAML content must raise CompIntelValidationError."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(CompIntelValidationError) as exc:
            ExperimentConfig.from_yaml(bad_yaml)
        assert "INVALID_YAML_CONFIG" in str(exc.value.code)


class TestEnvironmentProfiler:
    """Tests for runtime environment profiling and library version tracking."""

    def test_environment_manifest_structure(self) -> None:
        """get_environment_manifest should capture platform and tracked libraries."""
        env = get_environment_manifest()
        assert "python_version" in env
        assert "platform" in env
        assert "library_versions" in env

        libs = env["library_versions"]
        assert "polars" in libs
        assert libs["polars"] != "not_installed"
        assert "numpy" in libs
        assert "scipy" in libs
        assert "scikit-learn" in libs
        assert libs["scikit-learn"] != "not_installed"
        assert "pandera" in libs
        assert "pydantic" in libs

    def test_git_commit_detection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_git_commit should prioritize environment variable and fallback cleanly."""
        monkeypatch.setenv("ARTHAIQ_COMMIT", "test_commit_sha_123456")
        assert get_git_commit() == "test_commit_sha_123456"

        monkeypatch.delenv("ARTHAIQ_COMMIT", raising=False)
        commit = get_git_commit()
        assert isinstance(commit, str)
        assert len(commit) > 0


class TestExperimentRunner:
    """Tests for ExperimentRunner execution, synthetic isolation, and bundling."""

    def test_empty_dataframe_rejected(self) -> None:
        """Empty input DataFrame must be rejected."""
        runner = ExperimentRunner(config=ExperimentConfig())
        with pytest.raises(CompIntelValidationError) as exc:
            runner.run(df=pl.DataFrame())
        assert "EMPTY_DATASET" in str(exc.value.code)

    def test_rule_r_md_11_synthetic_data_blocked(
        self, synthetic_experiment_df: pl.DataFrame
    ) -> None:
        """Synthetic data without allow_synthetic=True must raise DataContractError."""
        runner = ExperimentRunner(config=ExperimentConfig(allow_synthetic=False))
        with pytest.raises(DataContractError) as exc:
            runner.run(df=synthetic_experiment_df)
        assert "SYNTHETIC_DATA_BLOCKED" in str(exc.value.code)

    def test_unknown_model_rejected(self, sample_experiment_df: pl.DataFrame) -> None:
        """Unsupported model keys must raise CompIntelValidationError."""
        cfg = ExperimentConfig(models=["unsupported_model_xyz"])
        runner = ExperimentRunner(config=cfg)
        with pytest.raises(CompIntelValidationError) as exc:
            runner.run(df=sample_experiment_df)
        assert "UNKNOWN_MODEL_KEY" in str(exc.value.code)

    def test_run_and_bundle_persistence(
        self, sample_experiment_df: pl.DataFrame, tmp_path: Path
    ) -> None:
        """Full experiment run produces valid bundle with config, metrics, record, and markdown."""
        output_dir = tmp_path / "exp_bundle_001"
        cfg = ExperimentConfig(
            experiment_name="integration_test_run",
            seed=42,
            models=["rung_a_empirical", "rung_b_linear"],
            model_params={"rung_a_empirical": {"thin_evidence_threshold": 2}},
        )

        runner = ExperimentRunner(config=cfg)
        record = runner.run(df=sample_experiment_df, output_dir=output_dir)

        assert record.experiment_name == "integration_test_run"
        assert record.seed == 42
        assert record.timings["duration_seconds"] >= 0.0
        assert record.memory["peak_memory_mib"] >= 0.0
        assert "rung_a_empirical" in record.model_metrics
        assert "rung_b_linear" in record.model_metrics

        # Verify persisted files
        assert (output_dir / "config.yaml").exists()
        assert (output_dir / "metrics.json").exists()
        assert (output_dir / "run_record.json").exists()
        assert (output_dir / "summary.md").exists()

        # Verify config.yaml
        with open(output_dir / "config.yaml", encoding="utf-8") as f:
            saved_cfg = yaml.safe_load(f)
        assert saved_cfg["experiment_name"] == "integration_test_run"

        # Verify run_record.json load
        loaded_record = ExperimentRunRecord.load(output_dir)
        assert loaded_record.run_id == record.run_id
        assert loaded_record.seed == 42

        # Verify summary.md contents
        summary_md = (output_dir / "summary.md").read_text(encoding="utf-8")
        assert record.run_id in summary_md
        assert "Mean Absolute Error" in summary_md
        assert "uv run python scripts/run_experiment.py --reproduce" in summary_md


class TestExperimentReproducibility:
    """Tests for exact reproducibility and tamper detection (Rule R-MD-10)."""

    def test_exact_reproduction_success(
        self, sample_experiment_df: pl.DataFrame, tmp_path: Path
    ) -> None:
        """reproduce_experiment must verify identical metrics within strict tolerance."""
        output_dir = tmp_path / "reproducible_run"
        cfg = ExperimentConfig(
            experiment_name="repro_run",
            seed=100,
            models=["rung_a_empirical", "rung_b_linear"],
            model_params={"rung_a_empirical": {"thin_evidence_threshold": 2}},
        )

        runner = ExperimentRunner(config=cfg)
        record = runner.run(df=sample_experiment_df, output_dir=output_dir)

        # Reproduce from output directory
        result = reproduce_experiment(
            run_dir_or_record=output_dir,
            df=sample_experiment_df,
            tolerance=1e-9,
        )

        assert result.is_identical is True
        assert result.run_id == record.run_id
        assert result.metrics_compared > 0
        assert result.max_discrepancy <= 1e-9
        assert len(result.discrepancies) == 0

    def test_reproduction_tamper_detection(
        self, sample_experiment_df: pl.DataFrame, tmp_path: Path
    ) -> None:
        """Tampering with recorded metrics must trigger a reproduction discrepancy error."""
        output_dir = tmp_path / "tampered_run"
        cfg = ExperimentConfig(
            experiment_name="tamper_test",
            seed=100,
            models=["rung_b_linear"],
        )

        runner = ExperimentRunner(config=cfg)
        runner.run(df=sample_experiment_df, output_dir=output_dir)

        # Intentionally tamper with run_record.json
        record_file = output_dir / "run_record.json"
        with open(record_file, encoding="utf-8") as f:
            data = json.load(f)

        # Alter MAE
        m_data = data["model_metrics"]["rung_b_linear"]["metrics"]
        if m_data and "point" in m_data:
            m_data["point"]["mae"] = 9999.99

        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Re-run reproduction: must detect discrepancy
        with pytest.raises(CompIntelError) as exc:
            reproduce_experiment(
                run_dir_or_record=output_dir,
                df=sample_experiment_df,
                tolerance=1e-9,
            )
        assert "REPRODUCTION_DISCREPANCY" in str(exc.value.code)

    def test_missing_record_raises_error(self, tmp_path: Path) -> None:
        """Attempting to load or reproduce non-existent record raises RECORD_NOT_FOUND."""
        non_existent = tmp_path / "does_not_exist"
        with pytest.raises(CompIntelError) as exc:
            reproduce_experiment(run_dir_or_record=non_existent)
        assert "RECORD_NOT_FOUND" in str(exc.value.code)


class TestExperimentCLI:
    """Subprocess integration tests for scripts/run_experiment.py."""

    def test_cli_execution_from_config(self, tmp_path: Path) -> None:
        """CLI runs successfully and produces run record bundle."""
        canonical_file = Path("data/canonical/canonical_observations.parquet")
        if not canonical_file.exists():
            pytest.skip("Canonical dataset not found; skipping CLI test on clean checkout.")

        out_dir = tmp_path / "cli_run_out"
        cfg_file = tmp_path / "cli_test_cfg.yaml"
        cfg = ExperimentConfig(
            experiment_name="cli_test",
            seed=42,
            models=["rung_b_linear"],
        )
        cfg_file.write_text(cfg.to_yaml(), encoding="utf-8")

        cmd = [
            sys.executable,
            "scripts/run_experiment.py",
            "--config",
            str(cfg_file),
            "--output-dir",
            str(out_dir),
            "--quiet",
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert proc.returncode == 0, f"CLI failed: {proc.stderr}"
        assert (out_dir / "run_record.json").exists()
        assert (out_dir / "metrics.json").exists()

        # Now test CLI reproduction mode
        repro_cmd = [
            sys.executable,
            "scripts/run_experiment.py",
            "--reproduce",
            str(out_dir),
        ]
        repro_proc = subprocess.run(repro_cmd, capture_output=True, text=True, check=False)
        assert repro_proc.returncode == 0, f"Reproduction CLI failed: {repro_proc.stderr}"
        assert "EXPERIMENT REPRODUCTION VERIFICATION: SUCCESS" in repro_proc.stdout


class TestExperimentEdgeCases:
    """Branch and edge-case coverage tests for experiment tracking."""

    def test_calibrate_and_train_eval_splits(
        self, sample_experiment_df: pl.DataFrame, tmp_path: Path
    ) -> None:
        """ExperimentRunner supports calibrate and train eval splits cleanly."""
        for split_name in ["calibrate", "train"]:
            cfg = ExperimentConfig(
                experiment_name=f"split_test_{split_name}",
                seed=42,
                evaluation_split=split_name,  # type: ignore[arg-type]
                models=["rung_b_linear"],
            )
            runner = ExperimentRunner(config=cfg)
            record = runner.run(
                df=sample_experiment_df,
                output_dir=tmp_path / f"out_{split_name}",
            )
            assert record.data_summary["eval_split_name"] == split_name

    def test_load_canonical_data_not_found(self, tmp_path: Path) -> None:
        """Missing canonical data file must raise CANONICAL_DATA_NOT_FOUND."""
        bad_path = tmp_path / "non_existent_canonical.parquet"
        cfg = ExperimentConfig(canonical_data_path=str(bad_path))
        runner = ExperimentRunner(config=cfg)
        with pytest.raises(CompIntelError) as exc:
            runner.run()
        assert "CANONICAL_DATA_NOT_FOUND" in str(exc.value.code)

    def test_to_markdown_no_models_and_empty_metrics(self) -> None:
        """Markdown rendering handles empty model lists and thin-evidence abstentions."""
        rec_empty = ExperimentRunRecord(
            run_id="RUN-EMPTY",
            experiment_name="empty",
            seed=42,
            git_commit="abcdef",
            data_snapshot_id="SNAP-TEST",
            created_at_utc="2026-10-17T00:00:00Z",
            config={},
            timings={},
            memory={},
            environment={},
            data_summary={},
            model_metrics={},
            reproduction_command="cmd",
        )
        md_empty = rec_empty.to_markdown()
        assert "No models were evaluated in this run" in md_empty

        rec_abstained = ExperimentRunRecord(
            run_id="RUN-ABSTAINED",
            experiment_name="abstained",
            seed=42,
            git_commit="abcdef",
            data_snapshot_id="SNAP-TEST",
            created_at_utc="2026-10-17T00:00:00Z",
            config={},
            timings={},
            memory={},
            environment={},
            data_summary={},
            model_metrics={
                "rung_a_empirical": {
                    "model_name": "Rung A",
                    "abstention_rate": 100.0,
                    "evaluated_records": 1,
                    "metrics": None,
                }
            },
            reproduction_command="cmd",
        )
        md_abstained = rec_abstained.to_markdown()
        assert "Insufficient non-abstained records" in md_abstained

    def test_reproduction_model_missing_discrepancy(
        self, sample_experiment_df: pl.DataFrame, tmp_path: Path
    ) -> None:
        """Missing model in reproduced record triggers REPRODUCTION_DISCREPANCY."""
        out_dir = tmp_path / "model_missing_run"
        cfg = ExperimentConfig(
            experiment_name="missing_model",
            seed=42,
            models=["rung_b_linear"],
        )
        runner = ExperimentRunner(config=cfg)
        runner.run(df=sample_experiment_df, output_dir=out_dir)

        # Inject extra model into recorded bundle
        record_file = out_dir / "run_record.json"
        with open(record_file, encoding="utf-8") as f:
            data = json.load(f)

        data["model_metrics"]["ghost_model"] = {
            "model_name": "Ghost Model",
            "abstention_rate": 0.0,
            "metrics": None,
        }

        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        with pytest.raises(CompIntelError) as exc:
            reproduce_experiment(run_dir_or_record=out_dir, df=sample_experiment_df)
        assert "REPRODUCTION_DISCREPANCY" in str(exc.value.code)
