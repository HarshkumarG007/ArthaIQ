"""Unit tests for temporal-grouped dataset splitting framework (Task T4.01a).

Verifies:
1. SplitConfig parameter validation (temporal monotonic ordering, ratio sums).
2. 4-way partition disjointness, row conservation, and zero person cluster overlap.
3. Explicit temporal cutoffs versus ratio-based resolution.
4. Handling of multi-observation groups spanning temporal cutoffs (cross-window isolation).
5. Error handling for empty DataFrames, missing columns, and invalid types.
"""

from datetime import date

import polars as pl
import pytest
from tests.fixtures.synthetic import generate_synthetic_observations_df

from compintel.errors import CompIntelValidationError, DataContractError
from compintel.evaluation.splits import (
    DatasetSplits,
    SplitConfig,
    SplitType,
    create_temporal_grouped_splits,
)


@pytest.mark.unit
def test_split_config_validation() -> None:
    """Verify SplitConfig validates temporal boundaries and ratio constraints."""
    # 1. Valid default ratio config
    cfg = SplitConfig()
    assert cfg.train_ratio == 0.60
    assert cfg.test_ratio == 0.10

    # 2. Ratios not summing to 1.0
    with pytest.raises(CompIntelValidationError) as exc:
        SplitConfig(train_ratio=0.50, select_ratio=0.20, calibrate_ratio=0.10, test_ratio=0.10)
    assert exc.value.code == "INVALID_SPLIT_RATIOS"

    # 3. Non-positive ratio
    with pytest.raises(CompIntelValidationError) as exc:
        SplitConfig(train_ratio=0.70, select_ratio=0.20, calibrate_ratio=0.10, test_ratio=0.0)
    assert exc.value.code == "INVALID_SPLIT_RATIOS"

    # 4. Incomplete explicit dates
    with pytest.raises(CompIntelValidationError) as exc:
        SplitConfig(train_end=date(2025, 6, 30), select_end=date(2025, 9, 30))
    assert exc.value.code == "INVALID_SPLIT_CONFIG"

    # 5. Non-monotonic temporal order
    with pytest.raises(CompIntelValidationError) as exc:
        SplitConfig(
            train_end=date(2025, 12, 31),
            select_end=date(2025, 6, 30),
            calibrate_end=date(2026, 3, 31),
            test_end=date(2026, 6, 30),
        )
    assert exc.value.code == "INVALID_TEMPORAL_ORDER"


@pytest.mark.unit
def test_temporal_grouped_splits_explicit_cutoffs() -> None:
    """Verify 4-way splitting with explicit calendar cutoff dates."""
    # Construct a controlled dataset with distinct dates and groups
    records = [
        # Train window: 2025-01-01 to 2025-06-30
        {
            "observation_id": "OBS-01",
            "person_cluster_id": "P1",
            "as_of_date": date(2025, 2, 1),
            "cash": 12.0,
        },
        {
            "observation_id": "OBS-02",
            "person_cluster_id": "P2",
            "as_of_date": date(2025, 4, 15),
            "cash": 18.0,
        },
        # Select window: 2025-07-01 to 2025-09-30
        {
            "observation_id": "OBS-03",
            "person_cluster_id": "P3",
            "as_of_date": date(2025, 7, 10),
            "cash": 22.0,
        },
        {
            "observation_id": "OBS-04",
            "person_cluster_id": "P4",
            "as_of_date": date(2025, 8, 20),
            "cash": 15.0,
        },
        # Calibrate window: 2025-10-01 to 2025-12-31
        {
            "observation_id": "OBS-05",
            "person_cluster_id": "P5",
            "as_of_date": date(2025, 10, 5),
            "cash": 30.0,
        },
        {
            "observation_id": "OBS-06",
            "person_cluster_id": "P6",
            "as_of_date": date(2025, 11, 15),
            "cash": 28.0,
        },
        # Test window: 2026-01-01 to 2026-03-31
        {
            "observation_id": "OBS-07",
            "person_cluster_id": "P7",
            "as_of_date": date(2026, 1, 15),
            "cash": 35.0,
        },
        {
            "observation_id": "OBS-08",
            "person_cluster_id": "P8",
            "as_of_date": date(2026, 2, 28),
            "cash": 40.0,
        },
    ]
    df = pl.DataFrame(records)

    cfg = SplitConfig(
        train_end=date(2025, 6, 30),
        select_end=date(2025, 9, 30),
        calibrate_end=date(2025, 12, 31),
        test_end=date(2026, 3, 31),
    )

    splits: DatasetSplits = create_temporal_grouped_splits(df, config=cfg)

    # Verify counts
    assert splits.train_df.height == 2
    assert splits.select_df.height == 2
    assert splits.calibrate_df.height == 2
    assert splits.test_df.height == 2
    assert splits.excluded_df.height == 0

    # Verify count reconciliation
    assert splits.summary.total_records == 8
    assert splits.summary.discrepancy_count == 0
    assert splits.summary.is_leakage_free is True

    # Verify accessor methods
    assert splits.get_split(SplitType.TRAIN).equals(splits.train_df)
    assert splits.get_split(SplitType.SELECT).equals(splits.select_df)
    assert splits.get_split(SplitType.CALIBRATE).equals(splits.calibrate_df)
    assert splits.get_split(SplitType.TEST).equals(splits.test_df)

    # Verify markdown export
    md = splits.to_markdown()
    assert "CompIntel Evaluation Split Audit" in md
    assert "✅ PASS" in md
    assert "person_cluster_id" in md


@pytest.mark.unit
def test_cross_window_multi_observation_quarantine() -> None:
    """Rule R-DA-06: Prevent contributor leakage for multi-window individuals."""
    records = [
        # Person P1 has an observation in Train AND another in Select
        {
            "observation_id": "OBS-01",
            "person_cluster_id": "P1",
            "as_of_date": date(2025, 1, 10),
            "cash": 10.0,
        },
        {
            "observation_id": "OBS-02",
            "person_cluster_id": "P1",
            "as_of_date": date(2025, 8, 15),
            "cash": 14.0,
        },
        # Person P2 strictly in Train
        {
            "observation_id": "OBS-03",
            "person_cluster_id": "P2",
            "as_of_date": date(2025, 3, 1),
            "cash": 12.0,
        },
        # Person P3 strictly in Select
        {
            "observation_id": "OBS-04",
            "person_cluster_id": "P3",
            "as_of_date": date(2025, 7, 20),
            "cash": 20.0,
        },
        # Person P4 strictly in Calibrate
        {
            "observation_id": "OBS-05",
            "person_cluster_id": "P4",
            "as_of_date": date(2025, 11, 10),
            "cash": 25.0,
        },
        # Person P5 strictly in Test
        {
            "observation_id": "OBS-06",
            "person_cluster_id": "P5",
            "as_of_date": date(2026, 1, 10),
            "cash": 30.0,
        },
    ]
    df = pl.DataFrame(records)

    cfg = SplitConfig(
        train_end=date(2025, 6, 30),
        select_end=date(2025, 9, 30),
        calibrate_end=date(2025, 12, 31),
        test_end=date(2026, 3, 31),
        exclude_cross_window_groups=True,
    )

    splits = create_temporal_grouped_splits(df, config=cfg)

    # P1's earlier record (2025-01-10) is in Train
    train_persons = splits.train_df["person_cluster_id"].to_list()
    assert "P1" in train_persons
    assert "P2" in train_persons

    # P1's later record (2025-08-15) must NOT be in Select!
    select_persons = splits.select_df["person_cluster_id"].to_list()
    assert "P1" not in select_persons
    assert "P3" in select_persons

    # P1's later record must be quarantined in excluded_df
    assert splits.excluded_df.height == 1
    assert splits.excluded_df["observation_id"][0] == "OBS-02"

    # Count reconciliation: 6 == 2 (train) + 1 (sel) + 1 (cal) + 1 (test) + 1 (exc)
    assert splits.summary.discrepancy_count == 0
    assert splits.summary.is_leakage_free is True
    assert splits.summary.group_overlap_count == 0


@pytest.mark.unit
def test_temporal_grouped_splits_ratio_based_on_synthetic_fixture() -> None:
    """Verify ratio-based splitting on synthetic canonical observations."""
    synth_df = generate_synthetic_observations_df(n_records=80, seed=42)

    # Inject diverse dates into the synthetic dataset to test ratio splitting
    base_ordinal = date(2025, 1, 1).toordinal()
    date_list = [date.fromordinal(base_ordinal + (i * 4)) for i in range(synth_df.height)]
    synth_df = synth_df.with_columns(pl.Series("as_of_date", date_list, dtype=pl.Date))

    cfg = SplitConfig(
        train_ratio=0.60,
        select_ratio=0.15,
        calibrate_ratio=0.15,
        test_ratio=0.10,
    )

    splits = create_temporal_grouped_splits(synth_df, config=cfg)

    # Assert partitions are non-empty
    assert splits.train_df.height > 0
    assert splits.select_df.height > 0
    assert splits.calibrate_df.height > 0
    assert splits.test_df.height > 0

    # Total row reconciliation
    tot_reconciled = (
        splits.train_df.height
        + splits.select_df.height
        + splits.calibrate_df.height
        + splits.test_df.height
        + splits.excluded_df.height
    )
    assert tot_reconciled == synth_df.height
    assert splits.summary.discrepancy_count == 0

    # Verify zero group overlap between all pairs of splits
    train_groups = set(splits.train_df["person_cluster_id"].to_list())
    select_groups = set(splits.select_df["person_cluster_id"].to_list())
    cal_groups = set(splits.calibrate_df["person_cluster_id"].to_list())
    test_groups = set(splits.test_df["person_cluster_id"].to_list())

    assert train_groups.isdisjoint(select_groups)
    assert train_groups.isdisjoint(cal_groups)
    assert train_groups.isdisjoint(test_groups)
    assert select_groups.isdisjoint(cal_groups)
    assert select_groups.isdisjoint(test_groups)
    assert cal_groups.isdisjoint(test_groups)


@pytest.mark.unit
def test_splits_error_handling() -> None:
    """Verify input validation and error states."""
    # 1. Empty DataFrame
    empty_df = pl.DataFrame({"as_of_date": [], "person_cluster_id": [], "observation_id": []})
    with pytest.raises(CompIntelValidationError) as exc:
        create_temporal_grouped_splits(empty_df)
    assert exc.value.code == "EMPTY_DATASET"

    # 2. Missing required columns
    bad_df = pl.DataFrame({"cash": [10.0, 20.0]})
    with pytest.raises(DataContractError) as exc:
        create_temporal_grouped_splits(bad_df)
    assert exc.value.code == "MISSING_SPLIT_COLUMN"

    # 3. Invalid date dtype
    int_date_df = pl.DataFrame(
        {
            "as_of_date": [20250101, 20250102],
            "person_cluster_id": ["P1", "P2"],
            "observation_id": ["O1", "O2"],
        }
    )
    with pytest.raises(CompIntelValidationError) as exc:
        create_temporal_grouped_splits(int_date_df)
    assert exc.value.code == "INVALID_DATE_TYPE"


@pytest.mark.unit
def test_splits_with_string_and_datetime_and_schema_validation() -> None:
    """Verify split framework handles Datetime and String date formats and schema validation."""
    synth_df = generate_synthetic_observations_df(n_records=40, seed=123)

    # Convert date to Datetime
    dt_df = synth_df.with_columns(pl.col("as_of_date").cast(pl.Datetime).alias("as_of_date"))
    cfg = SplitConfig(validate_schema=True)
    splits = create_temporal_grouped_splits(dt_df, config=cfg)
    assert splits.summary.is_leakage_free is True
    assert splits.train_df.height > 0

    # Convert date to ISO String
    str_df = synth_df.with_columns(pl.col("as_of_date").cast(pl.String).alias("as_of_date"))
    cfg_str = SplitConfig(validate_schema=False)
    splits_str = create_temporal_grouped_splits(str_df, config=cfg_str)
    assert splits_str.summary.is_leakage_free is True
    assert splits_str.train_df.height > 0


@pytest.mark.unit
def test_splits_with_fewer_than_four_unique_dates() -> None:
    """Verify splitter handles datasets with <= 3 unique dates via daily offsets."""
    records = [
        {"observation_id": f"O{i}", "person_cluster_id": f"P{i}", "as_of_date": date(2025, 1, 1)}
        for i in range(10)
    ]
    df = pl.DataFrame(records)
    splits = create_temporal_grouped_splits(df)
    assert splits.summary.is_leakage_free is True
    assert splits.summary.total_records == 10
    assert splits.summary.discrepancy_count == 0
