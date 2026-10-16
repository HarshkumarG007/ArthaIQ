"""Leakage detection and adversarial audit engine for dataset splits (Tasks T4.01a, T4.01b).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal validation without cross-partition entity leakage.
- Rule R-MD-03: As-of cutoff enforcement; zero lookahead or future information in historical splits.
- Rule R-MD-04: Seeded leak detection tests. Unit and integration tests with intentional
  leakage MUST fail deterministically.
- Rule R-DA-06: Deduplicate and resolve entity clusters before splits.
- Rule R-CD-03: Evaluation layer imports only schema and errors; zero dependencies on serving.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

import polars as pl

from compintel.errors import LeakageError
from compintel.evaluation.splits import DatasetSplits, SplitType


@dataclass(frozen=True)
class LeakageAuditReport:
    """Detailed audit report of group, duplicate, and temporal leakage across splits."""

    is_leakage_free: bool
    total_violations_count: int
    group_overlaps: dict[str, list[str]] = field(default_factory=dict)
    exact_duplicate_overlaps: dict[str, list[str]] = field(default_factory=dict)
    observation_id_overlaps: dict[str, list[str]] = field(default_factory=dict)
    temporal_violations: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert audit report to a structured dictionary."""
        return {
            "is_leakage_free": self.is_leakage_free,
            "total_violations_count": self.total_violations_count,
            "group_overlaps": self.group_overlaps,
            "exact_duplicate_overlaps": self.exact_duplicate_overlaps,
            "observation_id_overlaps": self.observation_id_overlaps,
            "temporal_violations": self.temporal_violations,
            "details": self.details,
        }

    def to_markdown(self) -> str:
        """Generate GitHub-Flavored Markdown summary of the leakage audit."""
        badge = "🟢 PASS (Zero Leakage Detected)" if self.is_leakage_free else "🚨 LEAKAGE DETECTED"
        dup_total = sum(len(v) for v in self.exact_duplicate_overlaps.values())
        grp_total = sum(len(v) for v in self.group_overlaps.values())
        lines = [
            "# CompIntel Evaluation Splits Leakage Audit (Rule R-MD-03, R-MD-04)",
            "",
            f"**Audit Status:** {badge}",
            f"- **Total Violations:** {self.total_violations_count}",
            f"- **Group Overlap Instances:** {grp_total}",
            f"- **Duplicate Overlaps:** {dup_total}",
            f"- **Temporal Lookaheads:** {len(self.temporal_violations)}",
            "",
            "## Pairwise Split Overlap Analysis",
            "",
            "| Split Pair | Observation ID Dups | Group Cluster Overlaps | Exact Dup Overlaps |",
            "|---|---|---|---|",
        ]

        # Standard split pairs
        split_pairs = [
            ("train", "select"),
            ("train", "calibrate"),
            ("train", "test"),
            ("select", "calibrate"),
            ("select", "test"),
            ("calibrate", "test"),
        ]

        for s1, s2 in split_pairs:
            pair_key = f"{s1}_vs_{s2}"
            id_cnt = len(self.observation_id_overlaps.get(pair_key, []))
            grp_cnt = len(self.group_overlaps.get(pair_key, []))
            dup_cnt = len(self.exact_duplicate_overlaps.get(pair_key, []))
            lines.append(f"| `{s1}` vs `{s2}` | {id_cnt} | {grp_cnt} | {dup_cnt} |")

        if self.temporal_violations:
            lines.extend(
                [
                    "",
                    "## Temporal Boundary Violations",
                    "",
                    "| Split | Observation ID | Record Date | Expected Cutoff | Violation Type |",
                    "|---|---|---|---|---|",
                ]
            )
            for tv in self.temporal_violations[:10]:
                lines.append(
                    f"| `{tv.get('split')}` | `{tv.get('observation_id')}` | "
                    f"{tv.get('record_date')} | {tv.get('expected_cutoff')} | "
                    f"{tv.get('violation_type')} |"
                )
            if len(self.temporal_violations) > 10:
                lines.append(
                    f"| ... and {len(self.temporal_violations) - 10} more violations | | | | |"
                )

        lines.append("")
        return "\n".join(lines)


def _extract_date_series(df: pl.DataFrame, date_col: str) -> list[date]:
    """Extract dates as standard python datetime.date objects from Polars DataFrame."""
    if df.height == 0 or date_col not in df.columns:
        return []
    series = df[date_col]
    if series.dtype == pl.Datetime:
        return [d.date() if isinstance(d, datetime) else d for d in series.to_list()]
    if series.dtype == pl.String:
        return [date.fromisoformat(str(d)) for d in series.to_list()]
    out: list[date] = []
    for item in series.to_list():
        if isinstance(item, datetime):
            out.append(item.date())
        elif isinstance(item, date):
            out.append(item)
        else:
            out.append(date.fromisoformat(str(item)))
    return out


def audit_split_leakage(
    splits: DatasetSplits,
    group_columns: Sequence[str] = ("person_cluster_id",),
    check_exact_duplicates: bool = True,
    check_temporal_order: bool = True,
    raise_on_leak: bool = True,
) -> LeakageAuditReport:
    """Audit 4-way evaluation splits for entity, duplicate, and temporal lookahead leakage.

    Args:
        splits: The DatasetSplits container to audit.
        group_columns: Column names to audit for disjoint entity clustering (e.g., person,
            employer).
        check_exact_duplicates: Whether to verify exact duplicate clusters are mutually exclusive.
        check_temporal_order: Whether to verify strict temporal ordering and cutoffs.
        raise_on_leak: If True, raises LeakageError upon detecting any violation.

    Returns:
        LeakageAuditReport detailing all verified invariants and any detected leaks.

    Raises:
        LeakageError: If raise_on_leak is True and any leakage violation is detected.
    """
    id_col = splits.config.id_column
    date_col = splits.config.date_column

    split_dfs: dict[str, pl.DataFrame] = {
        "train": splits.train_df,
        "select": splits.select_df,
        "calibrate": splits.calibrate_df,
        "test": splits.test_df,
    }

    group_overlaps: dict[str, list[str]] = {}
    dup_overlaps: dict[str, list[str]] = {}
    id_overlaps: dict[str, list[str]] = {}
    temporal_violations: list[dict[str, Any]] = []

    split_keys = ["train", "select", "calibrate", "test"]

    # 1. Pairwise checks for overlap across splits
    for i in range(len(split_keys)):
        for j in range(i + 1, len(split_keys)):
            name1 = split_keys[i]
            name2 = split_keys[j]
            pair_key = f"{name1}_vs_{name2}"
            df1 = split_dfs[name1]
            df2 = split_dfs[name2]

            if df1.height == 0 or df2.height == 0:
                continue

            # Check 1a: Observation ID overlap
            if id_col in df1.columns and id_col in df2.columns:
                ids1 = set(df1[id_col].to_list())
                ids2 = set(df2[id_col].to_list())
                overlap_ids = sorted(ids1 & ids2)
                if overlap_ids:
                    id_overlaps[pair_key] = [str(x) for x in overlap_ids]

            # Check 1b: Group cluster overlaps (person, employer, etc.)
            for grp_col in group_columns:
                if grp_col in df1.columns and grp_col in df2.columns:
                    g1 = set(df1[grp_col].drop_nulls().to_list())
                    g2 = set(df2[grp_col].drop_nulls().to_list())
                    overlap_grps = sorted(g1 & g2)
                    if overlap_grps:
                        key_name = f"{pair_key}:{grp_col}"
                        group_overlaps[key_name] = [str(x) for x in overlap_grps]

            # Check 1c: Exact duplicate cluster overlap
            if (
                check_exact_duplicates
                and "exact_duplicate_cluster_id" in df1.columns
                and "exact_duplicate_cluster_id" in df2.columns
            ):
                dups1 = set(df1["exact_duplicate_cluster_id"].drop_nulls().to_list())
                dups2 = set(df2["exact_duplicate_cluster_id"].drop_nulls().to_list())
                overlap_dups = sorted(dups1 & dups2)
                if overlap_dups:
                    dup_overlaps[pair_key] = [str(x) for x in overlap_dups]

            # Check 1d: Pairwise temporal non-inversion
            if check_temporal_order and date_col in df1.columns and date_col in df2.columns:
                dates1 = _extract_date_series(df1, date_col)
                dates2 = _extract_date_series(df2, date_col)
                if dates1 and dates2:
                    max_d1 = max(dates1)
                    min_d2 = min(dates2)
                    if max_d1 > min_d2:
                        temporal_violations.append(
                            {
                                "split": name1,
                                "violates_split": name2,
                                "violation_type": "PAIRWISE_TEMPORAL_INVERSION",
                                "max_d1": max_d1.isoformat(),
                                "min_d2": min_d2.isoformat(),
                                "details": (
                                    f"{name1} max date ({max_d1}) > {name2} min date ({min_d2})"
                                ),
                            }
                        )

    # 2. Check explicit cutoff adherence if cutoffs are specified in manifest or config
    if check_temporal_order:
        cutoffs = splits.manifest.get("cutoffs", {})
        train_end_str = cutoffs.get("train_end")
        select_end_str = cutoffs.get("select_end")
        cal_end_str = cutoffs.get("calibrate_end")
        test_end_str = cutoffs.get("test_end")

        if train_end_str and select_end_str and cal_end_str and test_end_str:
            c_train = date.fromisoformat(train_end_str)
            c_select = date.fromisoformat(select_end_str)
            c_cal = date.fromisoformat(cal_end_str)
            c_test = date.fromisoformat(test_end_str)

            # Audit Train
            for row in splits.train_df.iter_rows(named=True):
                r_date = row.get(date_col)
                if isinstance(r_date, datetime):
                    r_date = r_date.date()
                elif isinstance(r_date, str):
                    r_date = date.fromisoformat(r_date)
                if r_date and r_date > c_train:
                    temporal_violations.append(
                        {
                            "split": "train",
                            "observation_id": str(row.get(id_col)),
                            "record_date": str(r_date),
                            "expected_cutoff": c_train.isoformat(),
                            "violation_type": "TRAIN_LOOKAHEAD_AFTER_CUTOFF",
                        }
                    )

            # Audit Select
            for row in splits.select_df.iter_rows(named=True):
                r_date = row.get(date_col)
                if isinstance(r_date, datetime):
                    r_date = r_date.date()
                elif isinstance(r_date, str):
                    r_date = date.fromisoformat(r_date)
                if r_date and (r_date <= c_train or r_date > c_select):
                    temporal_violations.append(
                        {
                            "split": "select",
                            "observation_id": str(row.get(id_col)),
                            "record_date": str(r_date),
                            "expected_cutoff": f"({c_train}, {c_select}]",
                            "violation_type": "SELECT_OUTSIDE_WINDOW",
                        }
                    )

            # Audit Calibrate
            for row in splits.calibrate_df.iter_rows(named=True):
                r_date = row.get(date_col)
                if isinstance(r_date, datetime):
                    r_date = r_date.date()
                elif isinstance(r_date, str):
                    r_date = date.fromisoformat(r_date)
                if r_date and (r_date <= c_select or r_date > c_cal):
                    temporal_violations.append(
                        {
                            "split": "calibrate",
                            "observation_id": str(row.get(id_col)),
                            "record_date": str(r_date),
                            "expected_cutoff": f"({c_select}, {c_cal}]",
                            "violation_type": "CALIBRATE_OUTSIDE_WINDOW",
                        }
                    )

            # Audit Test
            for row in splits.test_df.iter_rows(named=True):
                r_date = row.get(date_col)
                if isinstance(r_date, datetime):
                    r_date = r_date.date()
                elif isinstance(r_date, str):
                    r_date = date.fromisoformat(r_date)
                if r_date and (r_date <= c_cal or r_date > c_test):
                    temporal_violations.append(
                        {
                            "split": "test",
                            "observation_id": str(row.get(id_col)),
                            "record_date": str(r_date),
                            "expected_cutoff": f"({c_cal}, {c_test}]",
                            "violation_type": "TEST_OUTSIDE_WINDOW",
                        }
                    )

    tot_violations = (
        sum(len(v) for v in id_overlaps.values())
        + sum(len(v) for v in group_overlaps.values())
        + sum(len(v) for v in dup_overlaps.values())
        + len(temporal_violations)
    )

    is_clean = tot_violations == 0

    report = LeakageAuditReport(
        is_leakage_free=is_clean,
        total_violations_count=tot_violations,
        group_overlaps=group_overlaps,
        exact_duplicate_overlaps=dup_overlaps,
        observation_id_overlaps=id_overlaps,
        temporal_violations=temporal_violations,
        details={
            "group_columns_checked": list(group_columns),
            "check_exact_duplicates": check_exact_duplicates,
            "check_temporal_order": check_temporal_order,
        },
    )

    if not is_clean and raise_on_leak:
        raise LeakageError(
            f"Evaluation split leakage detected ({tot_violations} violations): "
            f"ID overlaps={len(id_overlaps)}, Group overlaps={len(group_overlaps)}, "
            f"Duplicate overlaps={len(dup_overlaps)}, "
            f"Temporal lookaheads={len(temporal_violations)}",
            code="SPLIT_LEAKAGE_DETECTED",
            details=report.to_dict(),
        )

    return report


# ==============================================================================
# Adversarial Leak Seeding Utilities (Rule R-MD-04)
# ==============================================================================


def seed_group_leak(
    splits: DatasetSplits,
    group_id: str | None = None,
    source_split: SplitType = SplitType.TRAIN,
    target_split: SplitType = SplitType.TEST,
    group_column: str = "person_cluster_id",
) -> DatasetSplits:
    """Adversarially inject an entity cluster across split boundaries for testing."""
    src_df = splits.get_split(source_split)
    if src_df.height == 0:
        raise ValueError(f"Cannot seed leak from empty source split {source_split}")

    chosen_group = group_id or str(src_df[group_column][0])
    donor_row = src_df.filter(pl.col(group_column) == chosen_group)
    if donor_row.height == 0:
        raise ValueError(f"Group {chosen_group} not found in source split {source_split}")

    # Create leaked record with a distinct observation ID to isolate group leakage
    leaked_record = donor_row.head(1).clone()
    new_obs_id = f"LEAK-GRP-{leaked_record[splits.config.id_column][0]}"
    leaked_record = leaked_record.with_columns(pl.lit(new_obs_id).alias(splits.config.id_column))

    # Append leaked record into target split
    tgt_df = splits.get_split(target_split)
    modified_tgt = pl.concat([tgt_df, leaked_record], how="vertical_relaxed")

    return _replace_split(splits, target_split, modified_tgt)


def seed_temporal_lookahead_leak(
    splits: DatasetSplits,
    target_split: SplitType = SplitType.TRAIN,
    lookahead_date: date | None = None,
) -> DatasetSplits:
    """Adversarially inject a future record into an earlier split window."""
    tgt_df = splits.get_split(target_split)
    if tgt_df.height == 0:
        raise ValueError(f"Target split {target_split} is empty")

    donor_row = tgt_df.head(1).clone()
    future_d = lookahead_date or date(2099, 1, 1)

    date_col = splits.config.date_column
    id_col = splits.config.id_column

    leaked_record = donor_row.with_columns(
        pl.lit(f"LEAK-TIME-{donor_row[id_col][0]}").alias(id_col),
        pl.lit(future_d).alias(date_col),
    )

    modified_tgt = pl.concat([tgt_df, leaked_record], how="vertical_relaxed")
    return _replace_split(splits, target_split, modified_tgt)


def seed_exact_duplicate_leak(
    splits: DatasetSplits,
    source_split: SplitType = SplitType.TRAIN,
    target_split: SplitType = SplitType.TEST,
) -> DatasetSplits:
    """Adversarially clone a record with exact duplicate cluster ID into another split."""
    src_df = splits.get_split(source_split)
    if src_df.height == 0:
        raise ValueError(f"Source split {source_split} is empty")

    donor = src_df.head(1).clone()
    id_col = splits.config.id_column
    cloned_record = donor.with_columns(pl.lit(f"LEAK-DUP-{donor[id_col][0]}").alias(id_col))

    tgt_df = splits.get_split(target_split)
    modified_tgt = pl.concat([tgt_df, cloned_record], how="vertical_relaxed")
    return _replace_split(splits, target_split, modified_tgt)


def seed_observation_id_leak(
    splits: DatasetSplits,
    source_split: SplitType = SplitType.TRAIN,
    target_split: SplitType = SplitType.TEST,
) -> DatasetSplits:
    """Adversarially inject an identical observation ID into another split."""
    src_df = splits.get_split(source_split)
    if src_df.height == 0:
        raise ValueError(f"Source split {source_split} is empty")

    donor = src_df.head(1).clone()
    tgt_df = splits.get_split(target_split)
    modified_tgt = pl.concat([tgt_df, donor], how="vertical_relaxed")
    return _replace_split(splits, target_split, modified_tgt)


def _replace_split(
    splits: DatasetSplits,
    target_split: SplitType,
    new_df: pl.DataFrame,
) -> DatasetSplits:
    """Internal helper constructing a new DatasetSplits with one partition modified."""
    train_df = new_df if target_split == SplitType.TRAIN else splits.train_df
    select_df = new_df if target_split == SplitType.SELECT else splits.select_df
    calibrate_df = new_df if target_split == SplitType.CALIBRATE else splits.calibrate_df
    test_df = new_df if target_split == SplitType.TEST else splits.test_df

    return DatasetSplits(
        train_df=train_df,
        select_df=select_df,
        calibrate_df=calibrate_df,
        test_df=test_df,
        excluded_df=splits.excluded_df,
        config=splits.config,
        summary=splits.summary,
        manifest=splits.manifest,
    )
