#!/usr/bin/env python3
"""Run profiler across all acquired datasets in data/raw/ and print summary metrics."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from compintel.quality.profiler import profile_source_directory  # noqa: E402


def profile_all() -> None:
    raw_dir = repo_root / "data" / "raw"
    sources = sorted([d.name for d in raw_dir.iterdir() if d.is_dir()])

    print("=" * 80)
    print("ARTHAIQ RAW DATASETS PROFILING SUMMARY (T2.04)")
    print("=" * 80)

    for sid in sources:
        try:
            profiles = profile_source_directory(sid, raw_dir)
            print(f"\n[{sid}] ({len(profiles)} file(s)):")
            for p in profiles:
                print(f"  File: {p.file_name}")
                print(
                    f"    Rows: {p.row_count:,} | Cols: {p.column_count} | Duplicates: {p.duplicate_rows:,}"
                )
                print("    Columns & Missingness:")
                for col in p.columns:
                    range_info = ""
                    if col.min_val is not None and col.max_val is not None:
                        range_info = f" | range: [{col.min_val} .. {col.max_val}]"
                    print(
                        f"      - {col.name:<28} : {col.dtype:<8} | nulls: {col.null_count:>4} ({col.null_pct:>5.1f}%) | uniq: {col.unique_count:>5}{range_info}"
                    )
        except Exception as e:
            print(f"\n[{sid}] ERROR: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    profile_all()
