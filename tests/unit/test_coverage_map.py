"""Unit tests for cell coverage map and effective sample size calculation (Task T2.07).

Governed by experiments/preregistration/sufficiency-v1.yaml.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from compintel.quality.coverage import (
    compute_coverage_map,
    compute_kish_effective_sample,
    export_coverage_artifacts,
    get_canonical_cells,
    map_location_to_canonical,
    map_role_to_family,
    map_yoe_to_band,
)


@pytest.mark.unit
def test_get_canonical_cells() -> None:
    """Verify that canonical cells match pre-registered 84 Level-0 specification."""
    cells = get_canonical_cells()
    assert len(cells) == 84, f"Expected 84 cells, got {len(cells)}"

    core_cells = [c for c in cells if c.is_core]
    assert len(core_cells) == 12, f"Expected 12 core cells, got {len(core_cells)}"

    expected_core_ids = {
        "SWE.BLR.JR",
        "SWE.BLR.MID",
        "SWE.BLR.SR",
        "SWE.HYD.MID",
        "SWE.HYD.SR",
        "SWE.NCR.MID",
        "SWE.NCR.SR",
        "DATA.BLR.MID",
        "DATA.BLR.SR",
        "MLAI.BLR.SR",
        "MLAI.HYD.SR",
        "MLAI.NCR.SR",
    }
    actual_core_ids = {c.cell_id for c in core_cells}
    assert actual_core_ids == expected_core_ids

    extended_cells = [c for c in cells if not c.is_core]
    assert len(extended_cells) == 72, f"Expected 72 extended cells, got {len(extended_cells)}"


@pytest.mark.unit
def test_compute_kish_effective_sample() -> None:
    """Verify Kish design effect effective sample size calculations."""
    assert compute_kish_effective_sample([]) == 0.0
    assert compute_kish_effective_sample([0.0, 0.0]) == 0.0

    # Uniform weights -> N_eff equals N
    uniform_weights = [1.0] * 10
    assert pytest.approx(compute_kish_effective_sample(uniform_weights)) == 10.0

    scaled_uniform = [0.8] * 25
    assert pytest.approx(compute_kish_effective_sample(scaled_uniform)) == 25.0

    # Unequal weights reduce N_eff
    # 1 observation with weight 10, 9 observations with weight 1
    # sum(w) = 19, sum(w^2) = 100 + 9 = 109 -> N_eff = 361 / 109 = 3.31 < 10
    unequal_weights = [10.0] + [1.0] * 9
    expected_neff = (19.0**2) / 109.0
    assert pytest.approx(compute_kish_effective_sample(unequal_weights)) == expected_neff


@pytest.mark.unit
def test_mapping_helpers() -> None:
    """Verify role, location, and seniority mapping logic."""
    # Role mapping
    assert map_role_to_family("Senior Full-Stack Developer") == "SWE"
    assert map_role_to_family("Lead Software Engineer") == "SWE"
    assert map_role_to_family("Data Analyst") == "DATA"
    assert map_role_to_family("Database Administrator") == "DATA"
    assert map_role_to_family("Machine Learning Engineer") == "MLAI"
    assert map_role_to_family("Data Scientist") == "MLAI"
    assert map_role_to_family("Unknown Occupation") is None

    # Location mapping
    assert map_location_to_canonical("Bengaluru, Karnataka") == "BLR"
    assert map_location_to_canonical("Bangalore") == "BLR"
    assert map_location_to_canonical("Hyderabad, Telangana") == "HYD"
    assert map_location_to_canonical("Gurgaon, NCR") == "NCR"
    assert map_location_to_canonical("New Delhi") == "NCR"
    assert map_location_to_canonical("Pune") == "PUN"
    assert map_location_to_canonical("Mumbai") == "MUM"
    assert map_location_to_canonical("Chennai") == "CHN"
    assert map_location_to_canonical("Jaipur") == "OTHER"
    assert map_location_to_canonical(None) == "OTHER"

    # YOE mapping
    assert map_yoe_to_band(0.0) == "JR"
    assert map_yoe_to_band(1.5) == "JR"
    assert map_yoe_to_band(2.0) == "JR"
    assert map_yoe_to_band(3.0) == "MID"
    assert map_yoe_to_band(6.0) == "MID"
    assert map_yoe_to_band(8.0) == "SR"
    assert map_yoe_to_band(12.0) == "SR"
    assert map_yoe_to_band(15.0) == "STAFF"
    assert map_yoe_to_band(None) is None
    assert map_yoe_to_band(-1.0) is None


@pytest.mark.unit
def test_compute_coverage_map_schema_and_counts() -> None:
    """Verify compute_coverage_map produces exactly 84 rows with expected schema."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    df = compute_coverage_map(repo_root=repo_root)

    assert df.height == 84
    expected_cols = {
        "family",
        "location",
        "band",
        "cell_id",
        "is_core",
        "n_raw",
        "n_eff",
        "source_count",
        "sqs_avg",
        "median_age_days",
        "c1_pass",
        "c2_pass",
        "c3_pass",
        "c4_pass",
        "pg_pass",
        "overall_pass",
        "evidence_grade",
        "n_distinct_persons",
        "diagnostic_n_exploratory",
    }
    assert expected_cols.issubset(set(df.columns))

    core_df = df.filter(pl.col("is_core"))
    assert core_df.height == 12

    # Under current raw acquisition, all core cells fail C1 (Kill Criterion 1)
    assert core_df.filter(pl.col("c1_pass")).height == 0
    assert core_df.filter(pl.col("evidence_grade") == "ABSTAINED").height == 12


@pytest.mark.unit
def test_export_coverage_artifacts(tmp_path: Path) -> None:
    """Verify export_coverage_artifacts writes valid files to disk."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    df = compute_coverage_map(repo_root=repo_root)

    artifacts = export_coverage_artifacts(df, output_dir=tmp_path)
    assert artifacts["parquet"].exists()
    assert artifacts["csv"].exists()
    assert artifacts["markdown"].exists()
    assert artifacts["svg"].exists()

    # Verify parquet is readable
    read_df = pl.read_parquet(artifacts["parquet"])
    assert read_df.height == 84

    # Verify markdown contents
    md_text = artifacts["markdown"].read_text(encoding="utf-8")
    assert "Kill Criterion 1" in md_text
    assert "Core Cells" in md_text

    # Verify SVG contents
    svg_text = artifacts["svg"].read_text(encoding="utf-8")
    assert "<svg" in svg_text
    assert "</svg>" in svg_text
    assert "84-Cell Coverage Map" in svg_text


@pytest.mark.unit
def test_persisted_results_in_experiments_folder() -> None:
    """Verify that experiments/results/ contains valid persisted coverage map artifacts."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_dir = repo_root / "experiments" / "results"

    parquet_file = results_dir / "coverage_map_v1.parquet"
    csv_file = results_dir / "coverage_map_v1.csv"
    table_file = results_dir / "coverage_table.md"
    chart_file = results_dir / "coverage_chart.svg"
    if not parquet_file.exists():
        df_gen = compute_coverage_map(repo_root=repo_root)
        export_coverage_artifacts(df_gen, output_dir=results_dir)

    assert parquet_file.exists(), "Missing coverage_map_v1.parquet in experiments/results/"
    assert csv_file.exists(), "Missing coverage_map_v1.csv in experiments/results/"
    assert table_file.exists(), "Missing coverage_table.md in experiments/results/"
    assert chart_file.exists(), "Missing coverage_chart.svg in experiments/results/"

    df = pl.read_parquet(parquet_file)
    assert df.height == 84
