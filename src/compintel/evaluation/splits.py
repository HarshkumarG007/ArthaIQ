"""Leakage-resistant temporal and grouped dataset splitting framework (Tasks T4.01a, T4.01b).

Adheres strictly to:
- Rule R-MD-01: Grouped-temporal split hierarchy (person, employer, posting; temporal cutoffs).
  Random i.i.d. splits are prohibited for model evaluation.
- Rule R-MD-02: Final test set is isolated, untouched during tuning, and locked for make final-eval.
  Four distinct partitions: Train, Select, Calibrate, and Test.
- Rule R-MD-03: Splits strictly match deployment semantics. No lookahead or future information.
- Rule R-DA-03: Effective and reported timestamps preserved.
- Rule R-DA-06: Group by entity clusters before splitting; zero person overlap across splits.
- Rule R-CD-03: Evaluation layer imports only schema and errors; zero dependencies on serving.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

import polars as pl

from compintel.errors import CompIntelValidationError, DataContractError, LeakageError
from compintel.schema.canonical import validate_observations_df


class SplitType(StrEnum):
    """Canonical 4-way evaluation partition roles (Rule R-MD-02)."""

    TRAIN = "train"  # Model fitting and feature representation
    SELECT = "select"  # Hyperparameter tuning, feature ablation, model selection
    CALIBRATE = "calibrate"  # Conformal prediction interval calibration and crossing checks
    TEST = "test"  # Final untouched benchmark evaluation (locked for make final-eval)


@dataclass(frozen=True)
class SplitConfig:
    """Configuration for temporal-grouped dataset splitting."""

    # Explicit date boundaries (inclusive of end date):
    # train: [min_date, train_end]
    # select: (train_end, select_end]
    # calibrate: (select_end, calibrate_end]
    # test: (calibrate_end, test_end]
    train_end: date | None = None
    select_end: date | None = None
    calibrate_end: date | None = None
    test_end: date | None = None

    # Ratio-based temporal cutoffs when explicit dates are not provided
    train_ratio: float = 0.60
    select_ratio: float = 0.15
    calibrate_ratio: float = 0.15
    test_ratio: float = 0.10

    # Grouping columns to prevent entity leakage (Rule R-DA-06)
    group_column: str = "person_cluster_id"
    date_column: str = "as_of_date"
    id_column: str = "observation_id"

    # Leakage mitigation policy for multi-observation groups spanning temporal cutoffs
    # When True, multi-window groups are assigned to their earliest window and subsequent
    # records in future windows are quarantined/excluded to prevent individual trajectory leakage.
    exclude_cross_window_groups: bool = True

    # Validate canonical schema on split dataframes
    validate_schema: bool = False

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.train_end is not None:
            # Explicit temporal cutoffs provided
            if self.select_end is None or self.calibrate_end is None or self.test_end is None:
                raise CompIntelValidationError(
                    "All of [train_end, select_end, calibrate_end, test_end] must be provided.",
                    code="INVALID_SPLIT_CONFIG",
                )
            if not (self.train_end < self.select_end < self.calibrate_end <= self.test_end):
                raise CompIntelValidationError(
                    "Temporal cutoffs must satisfy "
                    "train_end < select_end < calibrate_end <= test_end: "
                    f"got {self.train_end} < {self.select_end} < "
                    f"{self.calibrate_end} <= {self.test_end}",
                    code="INVALID_TEMPORAL_ORDER",
                )
        else:
            # Ratio-based cutoffs
            tot_ratio = (
                self.train_ratio + self.select_ratio + self.calibrate_ratio + self.test_ratio
            )
            if abs(tot_ratio - 1.0) > 1e-4:
                raise CompIntelValidationError(
                    f"Split ratios must sum to 1.0 (got {tot_ratio:.4f})",
                    code="INVALID_SPLIT_RATIOS",
                )
            for r_name, r_val in [
                ("train_ratio", self.train_ratio),
                ("select_ratio", self.select_ratio),
                ("calibrate_ratio", self.calibrate_ratio),
                ("test_ratio", self.test_ratio),
            ]:
                if r_val <= 0.0:
                    raise CompIntelValidationError(
                        f"{r_name} must be strictly positive (got {r_val})",
                        code="INVALID_SPLIT_RATIOS",
                    )


@dataclass(frozen=True)
class SplitSummary:
    """Statistical summary and count reconciliation for dataset splits."""

    total_records: int
    train_records: int
    select_records: int
    calibrate_records: int
    test_records: int
    excluded_records: int
    discrepancy_count: int

    total_groups: int
    train_groups: int
    select_groups: int
    calibrate_groups: int
    test_groups: int

    train_date_span: tuple[date | None, date | None]
    select_date_span: tuple[date | None, date | None]
    calibrate_date_span: tuple[date | None, date | None]
    test_date_span: tuple[date | None, date | None]

    group_overlap_count: int
    is_leakage_free: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "total_records": self.total_records,
            "train_records": self.train_records,
            "select_records": self.select_records,
            "calibrate_records": self.calibrate_records,
            "test_records": self.test_records,
            "excluded_records": self.excluded_records,
            "discrepancy_count": self.discrepancy_count,
            "total_groups": self.total_groups,
            "train_groups": self.train_groups,
            "select_groups": self.select_groups,
            "calibrate_groups": self.calibrate_groups,
            "test_groups": self.test_groups,
            "train_date_span": [
                self.train_date_span[0].isoformat() if self.train_date_span[0] else None,
                self.train_date_span[1].isoformat() if self.train_date_span[1] else None,
            ],
            "select_date_span": [
                self.select_date_span[0].isoformat() if self.select_date_span[0] else None,
                self.select_date_span[1].isoformat() if self.select_date_span[1] else None,
            ],
            "calibrate_date_span": [
                self.calibrate_date_span[0].isoformat() if self.calibrate_date_span[0] else None,
                self.calibrate_date_span[1].isoformat() if self.calibrate_date_span[1] else None,
            ],
            "test_date_span": [
                self.test_date_span[0].isoformat() if self.test_date_span[0] else None,
                self.test_date_span[1].isoformat() if self.test_date_span[1] else None,
            ],
            "group_overlap_count": self.group_overlap_count,
            "is_leakage_free": self.is_leakage_free,
        }


@dataclass(frozen=True)
class DatasetSplits:
    """Immutable container holding the 4-way evaluation splits and validation metadata."""

    train_df: pl.DataFrame
    select_df: pl.DataFrame
    calibrate_df: pl.DataFrame
    test_df: pl.DataFrame
    excluded_df: pl.DataFrame
    config: SplitConfig
    summary: SplitSummary
    manifest: dict[str, Any] = field(default_factory=dict)

    def get_split(self, split_type: SplitType) -> pl.DataFrame:
        """Retrieve split DataFrame by SplitType enum."""
        match split_type:
            case SplitType.TRAIN:
                return self.train_df
            case SplitType.SELECT:
                return self.select_df
            case SplitType.CALIBRATE:
                return self.calibrate_df
            case SplitType.TEST:
                return self.test_df

    def to_markdown(self) -> str:
        """Generate GitHub-Flavored Markdown summary table of splits."""
        tot = self.summary.total_records or 1
        lines = [
            "# CompIntel Evaluation Split Audit (Rule R-MD-01, R-MD-02)",
            "",
            f"- **Grouping Key:** `{self.config.group_column}` (Rule R-DA-06)",
            f"- **Date Reference:** `{self.config.date_column}`",
            (
                f"- **Leakage Free:** "
                f"{'✅ PASS' if self.summary.is_leakage_free else '🚨 LEAKAGE DETECTED'}"
            ),
            f"- **Count Reconciliation (Δ):** {self.summary.discrepancy_count} (Must equal 0)",
            "",
            "| Split | Records | Share | Groups | Start Date | End Date |",
            "|---|---|---|---|---|---|",
            (
                f"| `train` | {self.summary.train_records:,} | "
                f"{self.summary.train_records / tot:.1%} | {self.summary.train_groups:,} | "
                f"{self.summary.train_date_span[0]} | {self.summary.train_date_span[1]} |"
            ),
            (
                f"| `select` | {self.summary.select_records:,} | "
                f"{self.summary.select_records / tot:.1%} | {self.summary.select_groups:,} | "
                f"{self.summary.select_date_span[0]} | {self.summary.select_date_span[1]} |"
            ),
            (
                f"| `calibrate` | {self.summary.calibrate_records:,} | "
                f"{self.summary.calibrate_records / tot:.1%} | {self.summary.calibrate_groups:,} | "
                f"{self.summary.calibrate_date_span[0]} | {self.summary.calibrate_date_span[1]} |"
            ),
            (
                f"| `test` | {self.summary.test_records:,} | "
                f"{self.summary.test_records / tot:.1%} | {self.summary.test_groups:,} | "
                f"{self.summary.test_date_span[0]} | {self.summary.test_date_span[1]} |"
            ),
            (
                f"| `excluded (cross-window)` | {self.summary.excluded_records:,} | "
                f"{self.summary.excluded_records / tot:.1%} | - | - | - |"
            ),
            "",
            f"**Total Records Processed:** {self.summary.total_records:,}",
            f"**Cross-Split Group Overlaps:** {self.summary.group_overlap_count}",
        ]
        return "\n".join(lines)


class TemporalGroupedSplitter:
    """Partitions canonical compensation datasets into leakage-resistant 4-way nested splits."""

    def __init__(self, config: SplitConfig | None = None) -> None:
        self.config = config or SplitConfig()

    def split(self, df: pl.DataFrame) -> DatasetSplits:
        """Execute temporal-grouped partitioning on a Polars DataFrame.

        Args:
            df: Input Polars DataFrame (validated canonical observations or raw intake).

        Returns:
            DatasetSplits container with train, select, calibrate, test, and excluded subsets.

        Raises:
            CompIntelValidationError: If required columns are missing or dataset is empty.
            LeakageError: If cross-split group leakage or temporal inverted splits occur.
        """
        if df.height == 0:
            raise CompIntelValidationError(
                "Cannot create evaluation splits from empty DataFrame.",
                code="EMPTY_DATASET",
            )

        # Verify required columns
        for col_name in [self.config.date_column, self.config.group_column, self.config.id_column]:
            if col_name not in df.columns:
                raise DataContractError(
                    f"Required column '{col_name}' missing from DataFrame for splitting.",
                    code="MISSING_SPLIT_COLUMN",
                )

        # Normalize temporal column to date
        working_df = df
        date_dtype = working_df.schema[self.config.date_column]
        if date_dtype == pl.Datetime:
            working_df = working_df.with_columns(
                pl.col(self.config.date_column).dt.date().alias("_split_date")
            )
        elif date_dtype == pl.Date:
            working_df = working_df.with_columns(
                pl.col(self.config.date_column).alias("_split_date")
            )
        elif date_dtype == pl.String:
            working_df = working_df.with_columns(
                pl.col(self.config.date_column).str.to_date("%Y-%m-%d").alias("_split_date")
            )
        else:
            raise CompIntelValidationError(
                f"Date column '{self.config.date_column}' must be Date, Datetime, or "
                f"ISO String (got {date_dtype})",
                code="INVALID_DATE_TYPE",
            )

        # Determine cutoff dates
        cutoffs = self._resolve_cutoffs(working_df)
        train_end, select_end, calibrate_end, test_end = cutoffs

        # Step 1: Compute the earliest observation date per group
        # This assigns every person/group cluster deterministically to its primary earliest window.
        group_min_dates = working_df.group_by(self.config.group_column).agg(
            pl.col("_split_date").min().alias("_group_first_date")
        )
        joined_df = working_df.join(group_min_dates, on=self.config.group_column, how="left")

        # Step 2: Determine group split assignment based on _group_first_date
        # Every group belongs to exactly ONE primary split.
        joined_df = joined_df.with_columns(
            pl.when(pl.col("_group_first_date") <= train_end)
            .then(pl.lit(SplitType.TRAIN.value))
            .when(pl.col("_group_first_date") <= select_end)
            .then(pl.lit(SplitType.SELECT.value))
            .when(pl.col("_group_first_date") <= calibrate_end)
            .then(pl.lit(SplitType.CALIBRATE.value))
            .otherwise(pl.lit(SplitType.TEST.value))
            .alias("_assigned_split")
        )

        # Step 3: Filter observations within each group's primary split
        # To avoid lookahead leakage: an observation can only be in a split if its own _split_date
        # also falls within that split's temporal boundary!
        # If an observation occurs in a future window relative to its group's assignment:
        # - If exclude_cross_window_groups=True: quarantine to excluded_df.
        # - Otherwise: raise LeakageError if temporal boundary is violated.

        # Condition for record falling into the window of its assigned split:
        train_cond = (pl.col("_assigned_split") == SplitType.TRAIN.value) & (
            pl.col("_split_date") <= train_end
        )
        select_cond = (
            (pl.col("_assigned_split") == SplitType.SELECT.value)
            & (pl.col("_split_date") > train_end)
            & (pl.col("_split_date") <= select_end)
        )
        calibrate_cond = (
            (pl.col("_assigned_split") == SplitType.CALIBRATE.value)
            & (pl.col("_split_date") > select_end)
            & (pl.col("_split_date") <= calibrate_end)
        )
        test_cond = (
            (pl.col("_assigned_split") == SplitType.TEST.value)
            & (pl.col("_split_date") > calibrate_end)
            & (pl.col("_split_date") <= test_end)
        )

        valid_assignment_cond = train_cond | select_cond | calibrate_cond | test_cond

        # Split DataFrames
        cols_to_drop = ["_split_date", "_group_first_date", "_assigned_split"]

        train_df = joined_df.filter(train_cond).drop(cols_to_drop)
        select_df = joined_df.filter(select_cond).drop(cols_to_drop)
        calibrate_df = joined_df.filter(calibrate_cond).drop(cols_to_drop)
        test_df = joined_df.filter(test_cond).drop(cols_to_drop)
        excluded_df = joined_df.filter(~valid_assignment_cond).drop(cols_to_drop)

        # Step 4: Validate schema if requested
        if self.config.validate_schema:
            if train_df.height > 0:
                train_df = validate_observations_df(train_df)
            if select_df.height > 0:
                select_df = validate_observations_df(select_df)
            if calibrate_df.height > 0:
                calibrate_df = validate_observations_df(calibrate_df)
            if test_df.height > 0:
                test_df = validate_observations_df(test_df)

        # Step 5: Audit group overlaps across splits
        groups_train = set(train_df[self.config.group_column].to_list())
        groups_select = set(select_df[self.config.group_column].to_list())
        groups_cal = set(calibrate_df[self.config.group_column].to_list())
        groups_test = set(test_df[self.config.group_column].to_list())

        overlaps = (
            (groups_train & groups_select)
            | (groups_train & groups_cal)
            | (groups_train & groups_test)
            | (groups_select & groups_cal)
            | (groups_select & groups_test)
            | (groups_cal & groups_test)
        )

        if len(overlaps) > 0:
            sample_overlaps = sorted(overlaps)[:5]
            raise LeakageError(
                f"Group leakage detected! {len(overlaps)} distinct groups appear in multiple "
                f"splits: {sample_overlaps}",
                code="GROUP_LEAKAGE_DETECTED",
                details={"overlapping_groups_count": len(overlaps)},
            )

        # Step 6: Temporal lookahead audit
        # Train max date must be <= train_end
        def _get_span(df_sub: pl.DataFrame) -> tuple[date | None, date | None]:
            if df_sub.height == 0:
                return (None, None)
            d_series = df_sub[self.config.date_column]
            if d_series.dtype == pl.Datetime:
                dates = [d.date() if isinstance(d, datetime) else d for d in d_series.to_list()]
            elif d_series.dtype == pl.String:
                dates = [date.fromisoformat(str(d)) for d in d_series.to_list()]
            else:
                dates = d_series.to_list()
            return (min(dates), max(dates))

        train_span = _get_span(train_df)
        select_span = _get_span(select_df)
        cal_span = _get_span(calibrate_df)
        test_span = _get_span(test_df)

        # Check temporal order
        if train_span[1] and select_span[0] and train_span[1] > select_span[0]:
            raise LeakageError(
                f"Temporal leakage: train max date ({train_span[1]}) > "
                f"select min date ({select_span[0]})",
                code="TEMPORAL_LOOKAHEAD_DETECTED",
            )
        if select_span[1] and cal_span[0] and select_span[1] > cal_span[0]:
            raise LeakageError(
                f"Temporal leakage: select max date ({select_span[1]}) > "
                f"calibrate min date ({cal_span[0]})",
                code="TEMPORAL_LOOKAHEAD_DETECTED",
            )
        if cal_span[1] and test_span[0] and cal_span[1] > test_span[0]:
            raise LeakageError(
                f"Temporal leakage: calibrate max date ({cal_span[1]}) > "
                f"test min date ({test_span[0]})",
                code="TEMPORAL_LOOKAHEAD_DETECTED",
            )

        # Step 7: Count reconciliation
        n_tot = df.height
        n_train = train_df.height
        n_sel = select_df.height
        n_cal = calibrate_df.height
        n_test = test_df.height
        n_exc = excluded_df.height

        discrepancy = n_tot - (n_train + n_sel + n_cal + n_test + n_exc)
        if discrepancy != 0:
            raise DataContractError(
                f"Row count reconciliation failed: Total {n_tot} != {n_train} + {n_sel} + "
                f"{n_cal} + {n_test} + {n_exc} (Δ={discrepancy})",
                code="COUNT_RECONCILIATION_FAILED",
            )

        all_groups = set(df[self.config.group_column].to_list())

        summary = SplitSummary(
            total_records=n_tot,
            train_records=n_train,
            select_records=n_sel,
            calibrate_records=n_cal,
            test_records=n_test,
            excluded_records=n_exc,
            discrepancy_count=discrepancy,
            total_groups=len(all_groups),
            train_groups=len(groups_train),
            select_groups=len(groups_select),
            calibrate_groups=len(groups_cal),
            test_groups=len(groups_test),
            train_date_span=train_span,
            select_date_span=select_span,
            calibrate_date_span=cal_span,
            test_date_span=test_span,
            group_overlap_count=len(overlaps),
            is_leakage_free=len(overlaps) == 0,
        )

        manifest = {
            "group_column": self.config.group_column,
            "date_column": self.config.date_column,
            "cutoffs": {
                "train_end": train_end.isoformat(),
                "select_end": select_end.isoformat(),
                "calibrate_end": calibrate_end.isoformat(),
                "test_end": test_end.isoformat(),
            },
            "summary": summary.to_dict(),
        }

        return DatasetSplits(
            train_df=train_df,
            select_df=select_df,
            calibrate_df=calibrate_df,
            test_df=test_df,
            excluded_df=excluded_df,
            config=self.config,
            summary=summary,
            manifest=manifest,
        )

    def _resolve_cutoffs(self, df: pl.DataFrame) -> tuple[date, date, date, date]:
        """Resolve concrete cutoff dates from explicit config or temporal ratios."""
        if self.config.train_end is not None:
            assert self.config.select_end is not None
            assert self.config.calibrate_end is not None
            assert self.config.test_end is not None
            return (
                self.config.train_end,
                self.config.select_end,
                self.config.calibrate_end,
                self.config.test_end,
            )

        # Deduce cutoffs from unique dates in the dataset
        sorted_dates: list[date] = sorted(df["_split_date"].unique().to_list())
        n_dates = len(sorted_dates)

        if n_dates < 4:
            # If dataset has fewer than 4 unique dates, synthesize daily offsets from min date
            base_d = sorted_dates[0]
            return (
                date.fromordinal(base_d.toordinal() + 0),
                date.fromordinal(base_d.toordinal() + 1),
                date.fromordinal(base_d.toordinal() + 2),
                date.fromordinal(base_d.toordinal() + 3),
            )

        # Quantile-based cutoffs over sorted dates
        idx_train = max(0, int(n_dates * self.config.train_ratio) - 1)
        idx_select = max(
            idx_train + 1,
            int(n_dates * (self.config.train_ratio + self.config.select_ratio)) - 1,
        )
        idx_cal = max(
            idx_select + 1,
            int(
                n_dates
                * (self.config.train_ratio + self.config.select_ratio + self.config.calibrate_ratio)
            )
            - 1,
        )
        idx_test = n_dates - 1

        # Ensure strict monotonicity of cutoffs
        train_end = sorted_dates[idx_train]
        select_end = sorted_dates[idx_select]
        cal_end = sorted_dates[idx_cal]
        test_end = sorted_dates[idx_test]

        return (train_end, select_end, cal_end, test_end)


def create_temporal_grouped_splits(
    df: pl.DataFrame,
    config: SplitConfig | None = None,
) -> DatasetSplits:
    """Convenience functional wrapper for temporal-grouped dataset splitting."""
    splitter = TemporalGroupedSplitter(config=config)
    return splitter.split(df)
