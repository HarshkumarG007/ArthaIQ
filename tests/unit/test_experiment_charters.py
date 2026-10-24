"""Unit tests for Phase 7 advanced modeling experiment charters (T7.01).

Validates that all charters conform to Rule R-MD-09, contain mandatory keep and
reject criteria, cite governing rules, and rank candidates by expected value and cost.
"""

from pathlib import Path

import pytest
import yaml

CHARTERS_DIR = Path("experiments/configs/charters")
INDEX_PATH = CHARTERS_DIR / "index.yaml"

MANDATORY_CHARTER_KEYS = {
    "charter_id",
    "experiment_id",
    "title",
    "task_id",
    "governing_rules",
    "priority_rank",
    "expected_value",
    "computational_cost",
    "candidate_summary",
    "evaluation_protocol",
    "keep_criteria",
    "reject_criteria",
}


def test_charters_directory_and_index_exist() -> None:
    """Verify charters directory and master index exist."""
    assert CHARTERS_DIR.is_dir(), f"Charters directory missing: {CHARTERS_DIR}"
    assert INDEX_PATH.is_file(), f"Index file missing: {INDEX_PATH}"


def test_index_yaml_structure_and_ranking() -> None:
    """Verify index.yaml parses and contains properly ranked candidates."""
    with open(INDEX_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "ranking_matrix" in data
    matrix = data["ranking_matrix"]
    assert len(matrix) >= 7, f"Expected at least 7 ranked charters, got {len(matrix)}"

    ranks = [item["rank"] for item in matrix]
    assert ranks == list(range(1, len(matrix) + 1)), (
        f"Ranks must be contiguous 1..{len(matrix)}: {ranks}"
    )

    for item in matrix:
        assert "charter_id" in item
        assert "experiment_id" in item
        assert "charter_file" in item
        assert "expected_value" in item
        assert "cost" in item
        charter_file = Path(item["charter_file"])
        assert charter_file.is_file(), f"Referenced charter file not found: {charter_file}"


@pytest.mark.parametrize(
    "filename",
    [
        "charter_exp09_skills_embeddings.yaml",
        "charter_career_trajectory.yaml",
        "charter_exp10_employer_graphs.yaml",
        "charter_macro_regimes.yaml",
        "charter_ensembling_stacking.yaml",
        "charter_survival_models.yaml",
        "charter_probabilistic_networks.yaml",
        "charter_exp10r_v2.yaml",
        "charter_career_traj_r_v2.yaml",
    ],
)
def test_individual_charter_conformance(filename: str) -> None:
    """Verify each charter YAML parses and contains all mandatory sections."""
    filepath = CHARTERS_DIR / filename
    assert filepath.is_file(), f"Charter missing: {filepath}"

    with open(filepath, encoding="utf-8") as f:
        charter = yaml.safe_load(f)

    # Check mandatory top-level keys
    missing_keys = MANDATORY_CHARTER_KEYS - set(charter.keys())
    assert not missing_keys, f"{filename} missing mandatory keys: {missing_keys}"

    # Verify R-MD-09 is cited in governing rules
    assert "R-MD-09" in charter["governing_rules"], (
        f"{filename} must cite Rule R-MD-09 in governing_rules"
    )

    # Verify candidate summary
    summary = charter["candidate_summary"]
    assert "hypothesis" in summary
    assert "baseline_champion" in summary
    assert "proposed_variants" in summary
    assert len(summary["proposed_variants"]) >= 1

    # Verify keep criteria
    keep = charter["keep_criteria"]
    assert "primary_metric_threshold" in keep
    prim = keep["primary_metric_threshold"]
    assert prim["metric"] == "delta_mean_pinball_loss"
    assert prim["min_effect_size_lpa"] <= -0.050, (
        f"Keep criterion in {filename} must require >= 0.05 LPA improvement"
    )

    # Verify reject criteria
    reject = charter["reject_criteria"]
    assert isinstance(reject, list)
    assert len(reject) >= 3, f"{filename} must have at least 3 reject criteria"


def test_copula_charter_conformance() -> None:
    """Verify charter_copula_pt4.yaml conforms to governance requirements."""
    filepath = CHARTERS_DIR / "charter_copula_pt4.yaml"
    assert filepath.is_file(), f"Charter missing: {filepath}"

    with open(filepath, encoding="utf-8") as f:
        charter = yaml.safe_load(f)

    assert charter["charter_id"] == "CHARTER-COPULA-PT4"
    assert "R-MD-09" in charter["governing_rules"]
    assert "candidate_summary" in charter
    assert "keep_criteria" in charter
    assert len(charter["reject_criteria"]) >= 3


def test_career_architect_charter_conformance() -> None:
    """Verify charter_career_arch_01.yaml conforms to governance requirements."""
    filepath = CHARTERS_DIR / "charter_career_arch_01.yaml"
    assert filepath.is_file(), f"Charter missing: {filepath}"

    with open(filepath, encoding="utf-8") as f:
        charter = yaml.safe_load(f)

    assert charter["charter_id"] == "CHARTER-CAREER-ARCH-01"
    assert charter["experiment_id"] == "EXP-CAREER-01"
    assert "R-MD-09" in charter["governing_rules"]
    assert "R-CR-01" in charter["governing_rules"]
    assert "R-CR-12" in charter["governing_rules"]
    assert "R-SC-07" in charter["governing_rules"]
    assert charter["priority_rank"] == 11
    assert "candidate_summary" in charter
    assert "keep_criteria" in charter
    assert len(charter["reject_criteria"]) >= 5
