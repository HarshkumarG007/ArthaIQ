"""Data profiling utility using Polars for source dataset analysis.

Governs Task T2.04: Profiling schemas, coverage, missingness, and duplicates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ColumnProfile:
    """Statistical and missingness profile for an individual column."""

    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    min_val: Any = None
    max_val: Any = None


@dataclass(frozen=True)
class DatasetProfile:
    """Complete profile of a raw tabular dataset."""

    source_id: str
    file_name: str
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: list[ColumnProfile]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_csv(file_path: Path, source_id: str) -> DatasetProfile:
    """Profile a CSV file using Polars, returning structured statistics."""
    df = pl.read_csv(file_path, ignore_errors=True, infer_schema_length=10000)

    row_count = df.height
    col_count = df.width
    duplicate_rows = row_count - df.unique().height if row_count > 0 else 0

    col_profiles: list[ColumnProfile] = []
    for col_name in df.columns:
        s = df[col_name]
        null_c = s.null_count()
        null_p = round((null_c / row_count) * 100, 2) if row_count > 0 else 0.0
        uniq_c = s.n_unique()

        min_v = None
        max_v = None
        if s.dtype.is_numeric() and s.drop_nulls().len() > 0:
            min_v = s.min()
            max_v = s.max()
        elif s.dtype == pl.String and s.drop_nulls().len() > 0:
            min_v = s.drop_nulls().min()
            max_v = s.drop_nulls().max()

        col_profiles.append(
            ColumnProfile(
                name=col_name,
                dtype=str(s.dtype),
                null_count=null_c,
                null_pct=null_p,
                unique_count=uniq_c,
                min_val=min_v,
                max_val=max_v,
            )
        )

    return DatasetProfile(
        source_id=source_id,
        file_name=file_path.name,
        row_count=row_count,
        column_count=col_count,
        duplicate_rows=duplicate_rows,
        columns=col_profiles,
    )


def profile_source_directory(source_id: str, raw_dir: Path) -> list[DatasetProfile]:
    """Profile all CSV files in data/raw/<source_id>/."""
    source_dir = raw_dir / source_id
    if not source_dir.exists():
        msg = f"Source directory not found: {source_dir}"
        raise FileNotFoundError(msg)

    profiles: list[DatasetProfile] = []
    for csv_file in sorted(source_dir.glob("*.csv")):
        profiles.append(profile_csv(csv_file, source_id))
    return profiles
