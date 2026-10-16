"""Adversarial leakage tests for evaluation dataset splits (Task T4.01b).

Adheres strictly to:
- Rule R-MD-01: Leakage-resistant grouped-temporal validation.
- Rule R-MD-03: As-of cutoff enforcement; zero future lookahead.
- Rule R-MD-04: Seeded leak detection tests. Unit and integration tests with intentional
  leakage MUST fail deterministically.
- Rule R-DA-06: Entity clusters (person, employer, posting) strictly isolated.
"""

from datetime import date

import polars as pl
import pytest
from tests.fixtures.synthetic import generate_synthetic_observations_df

from compintel.errors import LeakageError
from compintel.evaluation.leakage import (
    LeakageAuditReport,
    audit_split_leakage,
    seed_exact_duplicate_leak,
    seed_group_leak,
    seed_observation_id_leak,
    seed_temporal_lookahead_leak,
)
from compintel.evaluation.splits import (
    DatasetSplits,
    SplitConfig,
    SplitType,
    create_temporal_grouped_splits,
)


@pytest.fixture
def clean_splits() -> DatasetSplits:
    """Fixture providing clean, verified 4-way evaluation splits from synthetic canonical data."""
    synth_df = generate_synthetic_observations_df(n_records=80, seed=42)

    # Spread dates over 2025-2026 to guarantee distinct temporal windows
    base_ordinal = date(2025, 1, 1).toordinal()
    date_list = [date.fromordinal(base_ordinal + (i * 4)) for i in range(synth_df.height)]
    synth_df = synth_df.with_columns(pl.Series("as_of_date", date_list, dtype=pl.Date))

    cfg = SplitConfig(
        train_ratio=0.60,
        select_ratio=0.15,
        calibrate_ratio=0.15,
        test_ratio=0.10,
    )
    return create_temporal_grouped_splits(synth_df, config=cfg)


@pytest.mark.leakage
@pytest.mark.unit
def test_clean_splits_pass_leakage_audit(clean_splits: DatasetSplits) -> None:
    """Verify that correctly partitioned splits pass all leakage audit invariants."""
    report: LeakageAuditReport = audit_split_leakage(
        clean_splits,
        group_columns=["person_cluster_id"],
        check_exact_duplicates=True,
        check_temporal_order=True,
        raise_on_leak=True,
    )

    assert report.is_leakage_free is True
    assert report.total_violations_count == 0
    assert len(report.group_overlaps) == 0
    assert len(report.exact_duplicate_overlaps) == 0
    assert len(report.observation_id_overlaps) == 0
    assert len(report.temporal_violations) == 0

    # Markdown export check
    md = report.to_markdown()
    assert "PASS" in md
    assert "Total Violations:** 0" in md

    # Dictionary export check
    rep_dict = report.to_dict()
    assert rep_dict["is_leakage_free"] is True
    assert rep_dict["total_violations_count"] == 0


@pytest.mark.leakage
@pytest.mark.unit
def test_seeded_person_group_leak_fails_audit(clean_splits: DatasetSplits) -> None:
    """Rule R-MD-04: Seeded person cluster overlap across splits must trigger LeakageError."""
    # Seed group leak: inject person cluster from Train into Test
    leaked_splits = seed_group_leak(
        clean_splits,
        source_split=SplitType.TRAIN,
        target_split=SplitType.TEST,
        group_column="person_cluster_id",
    )

    # 1. Must raise LeakageError when raise_on_leak=True
    with pytest.raises(LeakageError) as exc_info:
        audit_split_leakage(
            leaked_splits,
            group_columns=["person_cluster_id"],
            raise_on_leak=True,
        )

    assert exc_info.value.code == "SPLIT_LEAKAGE_DETECTED"
    assert "Group overlaps" in exc_info.value.message

    # 2. Non-raising audit mode must report failure
    report = audit_split_leakage(
        leaked_splits,
        group_columns=["person_cluster_id"],
        raise_on_leak=False,
    )
    assert report.is_leakage_free is False
    assert report.total_violations_count >= 1
    assert any("person_cluster_id" in k for k in report.group_overlaps)

    # Markdown audit must contain warning
    md = report.to_markdown()
    assert "LEAKAGE DETECTED" in md


@pytest.mark.leakage
@pytest.mark.unit
def test_seeded_employer_group_leak_fails_when_audited(clean_splits: DatasetSplits) -> None:
    """Rule R-MD-04: Seeded employer cluster overlap must fail when employer grouping checked."""
    leaked_splits = seed_group_leak(
        clean_splits,
        source_split=SplitType.TRAIN,
        target_split=SplitType.TEST,
        group_column="employer_cluster_id",
    )

    with pytest.raises(LeakageError) as exc_info:
        audit_split_leakage(
            leaked_splits,
            group_columns=["person_cluster_id", "employer_cluster_id"],
            raise_on_leak=True,
        )

    assert "Group overlaps" in exc_info.value.message
    assert any("employer_cluster_id" in k for k in exc_info.value.details["group_overlaps"])


@pytest.mark.leakage
@pytest.mark.unit
def test_seeded_exact_duplicate_leak_fails_audit(clean_splits: DatasetSplits) -> None:
    """Rule R-MD-04: Exact duplicate cluster leaking from Train into Test must fail audit."""
    leaked_splits = seed_exact_duplicate_leak(
        clean_splits,
        source_split=SplitType.TRAIN,
        target_split=SplitType.TEST,
    )

    with pytest.raises(LeakageError) as exc_info:
        audit_split_leakage(
            leaked_splits,
            check_exact_duplicates=True,
            raise_on_leak=True,
        )

    assert "Duplicate overlaps" in exc_info.value.message
    assert "train_vs_test" in exc_info.value.details["exact_duplicate_overlaps"]


@pytest.mark.leakage
@pytest.mark.unit
def test_seeded_observation_id_leak_fails_audit(clean_splits: DatasetSplits) -> None:
    """Rule R-MD-04: Exact observation ID leaking across splits must fail audit."""
    leaked_splits = seed_observation_id_leak(
        clean_splits,
        source_split=SplitType.TRAIN,
        target_split=SplitType.TEST,
    )

    with pytest.raises(LeakageError) as exc_info:
        audit_split_leakage(
            leaked_splits,
            raise_on_leak=True,
        )

    assert "ID overlaps" in exc_info.value.message
    assert "train_vs_test" in exc_info.value.details["observation_id_overlaps"]


@pytest.mark.leakage
@pytest.mark.unit
def test_seeded_temporal_lookahead_leak_fails_audit(clean_splits: DatasetSplits) -> None:
    """Rule R-MD-03, R-MD-04: Future observation injected into Train must trigger LeakageError."""
    # Inject a 2099 date into Train
    future_date = date(2099, 12, 31)
    leaked_splits = seed_temporal_lookahead_leak(
        clean_splits,
        target_split=SplitType.TRAIN,
        lookahead_date=future_date,
    )

    with pytest.raises(LeakageError) as exc_info:
        audit_split_leakage(
            leaked_splits,
            check_temporal_order=True,
            raise_on_leak=True,
        )

    assert "Temporal lookaheads" in exc_info.value.message
    assert len(exc_info.value.details["temporal_violations"]) >= 1

    report = audit_split_leakage(
        leaked_splits,
        check_temporal_order=True,
        raise_on_leak=False,
    )
    assert report.is_leakage_free is False
    assert len(report.temporal_violations) >= 1
    assert any("2099" in str(v) for v in report.temporal_violations)


@pytest.mark.leakage
@pytest.mark.unit
def test_seeding_utilities_error_handling(clean_splits: DatasetSplits) -> None:
    """Verify input validation and error raising on invalid seeding requests."""
    empty_df = clean_splits.train_df.filter(pl.col("observation_id") == "NONEXISTENT")
    empty_splits = DatasetSplits(
        train_df=empty_df,
        select_df=clean_splits.select_df,
        calibrate_df=clean_splits.calibrate_df,
        test_df=clean_splits.test_df,
        excluded_df=clean_splits.excluded_df,
        config=clean_splits.config,
        summary=clean_splits.summary,
        manifest=clean_splits.manifest,
    )

    with pytest.raises(ValueError, match="Cannot seed leak from empty source"):
        seed_group_leak(empty_splits, source_split=SplitType.TRAIN)

    with pytest.raises(ValueError, match="Target split train is empty"):
        seed_temporal_lookahead_leak(empty_splits, target_split=SplitType.TRAIN)

    with pytest.raises(ValueError, match="Source split train is empty"):
        seed_exact_duplicate_leak(empty_splits, source_split=SplitType.TRAIN)

    with pytest.raises(ValueError, match="Source split train is empty"):
        seed_observation_id_leak(empty_splits, source_split=SplitType.TRAIN)

    with pytest.raises(ValueError, match="Group NONEXISTENT_GROUP not found"):
        seed_group_leak(clean_splits, group_id="NONEXISTENT_GROUP")
