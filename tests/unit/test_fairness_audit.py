"""Unit tests for Fairness Audit v1 Engine and CLI (T6.09, EXP-09).

Adheres to:
- PRD Section 16 & Rule 11: Demographic proxy prohibition.
- Rules R-FA-01, R-FA-02, R-FA-03, R-FA-04: Fairness evaluation & legal framing.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-05: Standard evaluation metrics with bootstrap confidence intervals.
- Rule R-MD-08: No causal language; statistical associations only.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-MD-12: Zero protected demographic inputs or proxies.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on all metrics.
- Rule R-UQ-02: Abstention is a valid designed outcome.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_fairness_audit import main as run_fairness_audit_main

from compintel.errors import DataContractError
from compintel.evaluation.fairness_audit import (
    FairnessAuditReport,
    FairnessVerdict,
    SliceDimension,
    _assign_experience_band,
    _assign_geo_tier,
    _compute_group_metrics,
    evaluate_and_save_fairness_audit,
    run_fairness_audit,
    scan_demographic_proxy_compliance,
)


@pytest.fixture
def synthetic_fairness_df() -> pl.DataFrame:
    """Fixture providing 80 synthetic observations with operational slice columns."""
    n_rows = 80
    rng = np.random.default_rng(42)

    roles = ["SOFTWARE"] * 30 + ["DATA"] * 30 + ["MLAI"] * 20
    seniorities = ["MID"] * 40 + ["SENIOR"] * 40
    locations = ["BANGALORE"] * 30 + ["MUMBAI"] * 25 + ["NCR"] * 15 + ["PUNE"] * 10
    employer_tiers = ["PRODUCT_TIER_1"] * 35 + ["PRODUCT_TIER_2"] * 25 + ["SERVICES"] * 20

    yoe = [float(i % 14) + 0.5 for i in range(n_rows)]
    skills = ["PYTHON,FASTAPI" if i % 2 == 0 else "GO,KUBERNETES" for i in range(n_rows)]
    depths = ["SPECIALIZED" if i % 2 == 0 else "GENERALIST" for i in range(n_rows)]
    domains = ["FINTECH" if i % 3 == 0 else "ECOMMERCE" for i in range(n_rows)]

    salaries = [
        14.0
        + (y * 1.5)
        + (10.0 if s == "SENIOR" else 0.0)
        + (4.0 if loc in ("BANGALORE", "MUMBAI") else 0.0)
        + float(rng.uniform(-1.0, 1.0))
        for y, s, loc in zip(yoe, seniorities, locations, strict=False)
    ]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 4) for i in range(n_rows)]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "person_cluster_id": [f"PER-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            "role_family": roles,
            "seniority_level": seniorities,
            "location": locations,
            "years_experience": yoe,
            "skills": skills,
            "depth_level": depths,
            "domain_specialization": domains,
            "employer_tier": employer_tiers,
            "is_synthetic": [True] * n_rows,
        }
    )


class TestDemographicProxyCompliance:
    """Test prohibited demographic proxy detection per rules.md Section 16 Rule 11."""

    def test_clean_dataframe_passes_scan(self, synthetic_fairness_df: pl.DataFrame) -> None:
        compliance = scan_demographic_proxy_compliance(synthetic_fairness_df)
        assert compliance.is_compliant
        assert len(compliance.prohibited_columns_found) == 0
        assert "UNVERIFIED" in compliance.legal_note

    @pytest.mark.parametrize(
        "prohibited_col",
        ["gender", "sex", "caste", "religion", "ethnicity", "race", "disability", "marital_status"],
    )
    def test_prohibited_demographic_column_detected(
        self, synthetic_fairness_df: pl.DataFrame, prohibited_col: str
    ) -> None:
        tainted_df = synthetic_fairness_df.with_columns(pl.lit("test").alias(prohibited_col))
        compliance = scan_demographic_proxy_compliance(tainted_df)
        assert not compliance.is_compliant
        assert prohibited_col in compliance.prohibited_columns_found

    def test_case_insensitive_demographic_detection(
        self, synthetic_fairness_df: pl.DataFrame
    ) -> None:
        tainted_df = synthetic_fairness_df.with_columns(pl.lit("M").alias("GENDER_CODE"))
        compliance = scan_demographic_proxy_compliance(tainted_df)
        assert not compliance.is_compliant
        assert "GENDER_CODE" in compliance.prohibited_columns_found


class TestSliceHelpers:
    """Test mapping helpers for operational slice dimensions."""

    def test_assign_experience_band(self) -> None:
        assert _assign_experience_band(1.5) == "Early_Career"
        assert _assign_experience_band(5.0) == "Mid_Career"
        assert _assign_experience_band(10.0) == "Senior"
        assert _assign_experience_band(15.0) == "Leadership"
        assert _assign_experience_band(None) == "Unknown"

    def test_assign_geo_tier(self) -> None:
        assert _assign_geo_tier("BANGALORE") == "Metro_South"
        assert _assign_geo_tier("MUMBAI") == "Metro_West"
        assert _assign_geo_tier("DELHI") == "Metro_North"
        assert _assign_geo_tier("INDORE") == "Non_Metro"
        assert _assign_geo_tier(None) == "Non_Metro"


class TestFairnessMetricComputation:
    """Test group-level fairness metrics calculation."""

    def test_compute_group_metrics_normal(self) -> None:
        y = np.array([20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0])
        p10 = y - 4.0
        p50 = y + 1.0
        p90 = y + 5.0
        metrics = _compute_group_metrics(
            y,
            p10,
            p50,
            p90,
            global_mae=2.0,
            global_coverage=0.80,
            global_abstention=0.0,
            dimension=SliceDimension.ROLE_FAMILY,
            slice_value="SOFTWARE",
            n_resamples=50,
            seed=42,
        )
        assert metrics.n_observations == 11
        assert not metrics.is_low_support
        assert metrics.point_mae == pytest.approx(1.0, abs=1e-3)
        assert metrics.empirical_coverage == pytest.approx(1.0, abs=1e-3)
        assert metrics.mae_ratio_to_global == pytest.approx(0.5, abs=1e-3)
        assert (
            metrics.pinball_loss_ci_lower
            <= metrics.mean_pinball_loss
            <= metrics.pinball_loss_ci_upper
        )

    def test_compute_group_metrics_empty(self) -> None:
        empty = np.array([], dtype=np.float64)
        metrics = _compute_group_metrics(
            empty,
            empty,
            empty,
            empty,
            global_mae=2.0,
            global_coverage=0.80,
            global_abstention=0.0,
            dimension=SliceDimension.GEOGRAPHIC,
            slice_value="EMPTY",
        )
        assert metrics.n_observations == 0
        assert metrics.is_low_support
        assert np.isnan(metrics.mean_pinball_loss)


class TestFairnessAuditEngine:
    """Test end-to-end fairness audit execution."""

    def test_test_partition_is_strictly_locked(self, synthetic_fairness_df: pl.DataFrame) -> None:
        train_df = synthetic_fairness_df[:40]
        eval_df = synthetic_fairness_df[40:]
        with pytest.raises(DataContractError, match="EVALUATION_ISOLATION_VIOLATION"):
            run_fairness_audit(
                train_df=train_df,
                eval_df=eval_df,
                calibrate_df=eval_df,
                eval_split_name="test",
            )

    def test_demographic_proxy_in_eval_blocks_execution(
        self, synthetic_fairness_df: pl.DataFrame
    ) -> None:
        train_df = synthetic_fairness_df[:40]
        eval_df = synthetic_fairness_df[40:].with_columns(pl.lit("X").alias("gender_code"))
        with pytest.raises(DataContractError, match="DEMOGRAPHIC_PROXY_VIOLATION"):
            run_fairness_audit(
                train_df=train_df,
                eval_df=eval_df,
                calibrate_df=eval_df,
                eval_split_name="select",
            )

    def test_run_fairness_audit_success(self, synthetic_fairness_df: pl.DataFrame) -> None:
        train_df = synthetic_fairness_df[:40]
        eval_df = synthetic_fairness_df[40:]
        report = run_fairness_audit(
            train_df=train_df,
            eval_df=eval_df,
            calibrate_df=eval_df,
            eval_split_name="select",
            n_resamples=50,
            seed=42,
        )
        assert isinstance(report, FairnessAuditReport)
        assert report.n_total_observations == 40
        assert report.global_mae > 0.0
        assert report.global_pinball_loss > 0.0
        assert 0.0 <= report.global_empirical_coverage <= 1.0
        assert len(report.slice_audits) == 4
        assert report.proxy_compliance.is_compliant
        assert report.overall_verdict in (
            FairnessVerdict.PASS_ALL,
            FairnessVerdict.WARN_GAPS,
            FairnessVerdict.FAIL_PARITY,
            FairnessVerdict.INSUFFICIENT_DATA,
        )
        md = report.to_markdown()
        assert "# Fairness Audit v1" in md
        assert "UNVERIFIED" in md
        assert "Demographic Proxy Compliance" in md


class TestEvaluateAndSaveFairnessAudit:
    """Test saving reports and CLI runner integration."""

    def test_evaluate_and_save_synthetic(
        self, tmp_path: Path, synthetic_fairness_df: pl.DataFrame
    ) -> None:
        parquet_path = tmp_path / "canonical.parquet"
        synthetic_fairness_df.write_parquet(parquet_path)

        md_path = tmp_path / "fairness_audit.md"
        json_path = tmp_path / "fairness_audit.json"

        report = evaluate_and_save_fairness_audit(
            canonical_path=parquet_path,
            output_md=md_path,
            output_json=json_path,
            eval_split_name="select",
            n_resamples=50,
            seed=42,
            allow_synthetic=True,
        )

        assert md_path.exists()
        assert json_path.exists()
        assert report.n_total_observations > 0

    def test_cli_runner(self, tmp_path: Path, synthetic_fairness_df: pl.DataFrame) -> None:
        parquet_path = tmp_path / "canonical.parquet"
        synthetic_fairness_df.write_parquet(parquet_path)

        md_path = tmp_path / "cli_audit.md"
        json_path = tmp_path / "cli_audit.json"

        test_args = [
            "run_fairness_audit.py",
            "--canonical-path",
            str(parquet_path),
            "--output-md",
            str(md_path),
            "--output-json",
            str(json_path),
            "--split",
            "select",
            "--n-resamples",
            "50",
            "--seed",
            "42",
            "--allow-synthetic",
        ]

        with patch("sys.argv", test_args):
            exit_code = run_fairness_audit_main()
            assert exit_code == 0
            assert md_path.exists()
            assert json_path.exists()
