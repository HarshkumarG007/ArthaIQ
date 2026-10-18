"""Unit tests for Skills Feature Modeling Experiment Engine and CLI (EXP-09, Task T7.02).

Adheres to:
- PRD Section 5 & FR-05: Personalization hierarchy and skills capability modeling.
- CHARTER-EXP-09: experiments/configs/charters/charter_exp09_skills_embeddings.yaml.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-04: Pipelines fitted inside training folds only.
- Rule R-MD-05: Standard evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Objective business model tiers and pre-registered experiment charters.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from scripts.run_skills_experiment import parse_args

from compintel.errors import DataContractError
from compintel.evaluation.skills_embeddings_experiment import (
    SkillsDecisionVerdict,
    SkillsEmbeddingVariant,
    SkillsExperimentReport,
    _compute_deterministic_sentence_embeddings,
    _compute_paired_bootstrap_ci,
    _extract_skill_corpus,
    evaluate_and_save_skills_experiment,
    run_skills_embeddings_experiment,
)


@pytest.fixture
def skills_synthetic_df() -> pl.DataFrame:
    """Fixture providing 60 synthetic observations across L0-L2 feature tiers."""
    n_rows = 60
    rng = np.random.default_rng(42)

    roles = ["SWE", "DATA", "MLAI"] * (n_rows // 3)
    seniorities = ["JR", "MID", "SR", "LEAD"] * (n_rows // 4)
    locations = ["BANGALORE", "HYDERABAD", "PUNE", "MUMBAI", "NCR"] * (n_rows // 5)
    yoe = [float(i % 15) + 1.0 for i in range(n_rows)]

    salaries = [
        12.0 + (y * 1.8) + (8.0 if s in ("SR", "LEAD") else 0.0) + (float(rng.uniform(-1.0, 1.0)))
        for y, s in zip(yoe, seniorities, strict=False)
    ]

    base_dates = [datetime.date(2025, 1, 1) + datetime.timedelta(days=i * 5) for i in range(n_rows)]

    return pl.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(n_rows)],
            "person_cluster_id": [f"PER-{i:04d}" for i in range(n_rows)],
            "as_of_date": base_dates,
            "effective_on": base_dates,
            "guaranteed_cash_annual": salaries,
            "role_family": roles,
            "canonical_title": ["Software Engineer", "Data Scientist", "ML Engineer"]
            * (n_rows // 3),
            "seniority": seniorities,
            "location": locations,
            "years_experience": yoe,
            "skills_primary": ["PYTHON", "GO", "JAVA"] * (n_rows // 3),
            "is_synthetic": [True] * n_rows,
        }
    )


def test_skills_embedding_variants_enum() -> None:
    """Test that all three candidate architectures exist with correct identifiers."""
    assert SkillsEmbeddingVariant.BASELINE_CHAMPION.value == "baseline_champion_l2"
    assert SkillsEmbeddingVariant.VARIANT_A_TAXONOMY_TFIDF.value == "variant_a_taxonomy_tfidf"
    assert (
        SkillsEmbeddingVariant.VARIANT_B_SENTENCE_EMBEDDINGS.value
        == "variant_b_sentence_embeddings_cpu"
    )
    assert len(SkillsEmbeddingVariant) == 3


def test_extract_skill_corpus() -> None:
    """Test skill text extraction across multiple schema representations."""
    # 1. From list-of-strings skills column
    df_list = pl.DataFrame({"skills": [["Python", "FastAPI"], ["PyTorch", "MLOps"], None]})
    corpus_list = _extract_skill_corpus(df_list)
    assert len(corpus_list) == 3
    assert corpus_list[0] == "python fastapi"
    assert corpus_list[1] == "pytorch mlops"
    assert "software" in corpus_list[2] or "general" in corpus_list[2]

    # 2. From string skills_primary column
    df_str = pl.DataFrame({"skills_primary": ["GOLANG", "JAVA"]})
    corpus_str = _extract_skill_corpus(df_str)
    assert corpus_str == ["golang", "java"]


def test_deterministic_sentence_embeddings() -> None:
    """Test deterministic CPU sentence embedding properties."""
    texts = ["python distributed systems", "machine learning pytorch", ""]
    embs = _compute_deterministic_sentence_embeddings(texts, dim=8, seed=42)

    assert embs.shape == (3, 8)
    # Unit norm for non-empty text
    norm_0 = float(np.linalg.norm(embs[0]))
    assert np.isclose(norm_0, 1.0, atol=1e-5)
    # Deterministic consistency
    embs_repeat = _compute_deterministic_sentence_embeddings(texts, dim=8, seed=42)
    np.testing.assert_allclose(embs, embs_repeat)


def test_compute_paired_bootstrap_ci() -> None:
    """Test paired bootstrap confidence intervals and statistical significance."""
    # Clearly negative deltas (significant reduction)
    deltas_sig = np.array([-0.10, -0.12, -0.09, -0.15, -0.11, -0.08, -0.14, -0.10])
    ci_l, ci_u, is_sig = _compute_paired_bootstrap_ci(deltas_sig, n_resamples=500, seed=42)
    assert is_sig is True
    assert ci_u < 0.0
    assert ci_l <= ci_u

    # Centered around zero (non-significant)
    deltas_null = np.array([-0.02, 0.03, -0.01, 0.02, -0.03, 0.01])
    ci_l2, ci_u2, is_sig2 = _compute_paired_bootstrap_ci(deltas_null, n_resamples=500, seed=42)
    assert is_sig2 is False
    assert ci_l2 < 0.0 < ci_u2


def test_run_skills_embeddings_experiment(skills_synthetic_df: pl.DataFrame) -> None:
    """Test complete experiment orchestration across training, calibration, and eval splits."""
    train_df = skills_synthetic_df.slice(0, 30)
    calib_df = skills_synthetic_df.slice(30, 15)
    eval_df = skills_synthetic_df.slice(45, 15)

    report = run_skills_embeddings_experiment(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        eval_split_name="select",
        n_resamples=100,
        seed=42,
    )

    assert isinstance(report, SkillsExperimentReport)
    assert report.charter_id == "CHARTER-EXP-09"
    assert report.experiment_id == "EXP-09"
    assert report.evaluation_split == "select"
    assert report.n_eval_observations == 15

    # Check baseline metrics
    b = report.baseline_metrics
    assert b.variant == SkillsEmbeddingVariant.BASELINE_CHAMPION
    assert b.mean_pinball_loss > 0.0
    assert 0.0 <= b.empirical_coverage <= 1.0
    assert b.crossing_rate == 0.0  # Conformal monotonic projection guarantees zero crossings

    # Check variant metrics
    assert len(report.deltas) == 2
    assert report.overall_verdict in (
        SkillsDecisionVerdict.KEEP,
        SkillsDecisionVerdict.DEFER,
        SkillsDecisionVerdict.REJECT,
    )

    # Check markdown rendering
    md = report.to_markdown()
    assert "# Skills Feature Modeling Experiment Report" in md
    assert "CHARTER-EXP-09" in md
    assert "Champion Baseline" in md

    # Check dictionary serialization
    d = report.to_dict()
    assert d["charter_id"] == "CHARTER-EXP-09"
    assert len(d["deltas"]) == 2


def test_test_partition_isolation_contract(skills_synthetic_df: pl.DataFrame) -> None:
    """Verify that running experiment on locked 'test' split raises DataContractError (R-MD-02)."""
    train_df = skills_synthetic_df.slice(0, 30)
    calib_df = skills_synthetic_df.slice(30, 15)
    eval_df = skills_synthetic_df.slice(45, 15)

    with pytest.raises(DataContractError) as exc_info:
        run_skills_embeddings_experiment(
            train_df=train_df,
            eval_df=eval_df,
            calibrate_df=calib_df,
            eval_split_name="test",
        )
    assert "EVALUATION_ISOLATION_VIOLATION" in str(exc_info.value)
    assert exc_info.value.details.get("rule_id") == "R-MD-02"


def test_synthetic_data_isolation_contract(
    tmp_path: Path, skills_synthetic_df: pl.DataFrame
) -> None:
    """Verify synthetic data in canonical dataset raises DataContractError (R-MD-11)."""
    file_path = tmp_path / "test_canonical.parquet"
    skills_synthetic_df.write_parquet(file_path)

    with pytest.raises(DataContractError) as exc_info:
        evaluate_and_save_skills_experiment(
            canonical_path=file_path,
            output_md=tmp_path / "out.md",
            output_json=tmp_path / "out.json",
            allow_synthetic=False,
        )
    assert "SYNTHETIC_DATA_BLOCKED" in str(exc_info.value.code)
    assert exc_info.value.details.get("rule_id") == "R-MD-11"


def test_skills_experiment_cli_args() -> None:
    """Test CLI argument parsing and default configurations."""
    test_args = [
        "scripts/run_skills_experiment.py",
        "--canonical-path",
        "custom/path.parquet",
        "--output-md",
        "custom/out.md",
        "--output-json",
        "custom/out.json",
        "--split",
        "calibrate",
        "--n-resamples",
        "500",
        "--seed",
        "123",
        "--allow-synthetic",
    ]
    with patch("sys.argv", test_args):
        args = parse_args()
        assert args.canonical_path == "custom/path.parquet"
        assert args.output_md == "custom/out.md"
        assert args.output_json == "custom/out.json"
        assert args.split == "calibrate"
        assert args.n_resamples == 500
        assert args.seed == 123
        assert args.allow_synthetic is True
