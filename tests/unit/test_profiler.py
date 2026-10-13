"""Unit tests for compintel.quality.profiler."""

from pathlib import Path

import pytest

from compintel.quality.profiler import profile_csv, profile_source_directory


@pytest.mark.unit
def test_profile_csv_basic(tmp_path: Path) -> None:
    """Verify that profile_csv accurately computes dimensions, nulls, and unique counts."""
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(
        "id,salary,city\n"
        "1,100000,BLR\n"
        "2,120000,HYD\n"
        "3,,BLR\n"
        "4,150000,\n"
        "1,100000,BLR\n",  # Duplicate row
        encoding="utf-8",
    )

    profile = profile_csv(csv_file, "TEST-SRC-01")
    assert profile.row_count == 5
    assert profile.column_count == 3
    assert profile.duplicate_rows == 1

    cols = {c.name: c for c in profile.columns}
    assert cols["id"].null_count == 0
    assert cols["salary"].null_count == 1
    assert cols["salary"].null_pct == 20.0
    assert cols["city"].null_count == 1
    assert cols["city"].unique_count == 3  # "BLR", "HYD", null


@pytest.mark.unit
def test_profile_source_directory_on_acquired_raw() -> None:
    """Verify that profile_source_directory successfully profiles an acquired raw source."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    raw_dir = repo_root / "data" / "raw"

    profiles = profile_source_directory("SRC-SUP-CORP-01", raw_dir)
    assert len(profiles) == 1
    p = profiles[0]
    assert p.file_name == "listed_it_mre_fy24.csv"
    assert p.row_count >= 8
    assert p.column_count == 8
    assert p.duplicate_rows == 0
