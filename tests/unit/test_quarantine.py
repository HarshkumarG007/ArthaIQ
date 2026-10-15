"""Unit tests for outlier and inconsistency policy, quarantine, and halt threshold (Task T3.11)."""

from __future__ import annotations

from pathlib import Path
import polars as pl
import pytest

from compintel.errors import PipelineHaltError
from compintel.quality.quarantine import (
    DEFAULT_HALT_THRESHOLD,
    DEFAULT_QUARANTINE_VERSION,
    InconsistencyPolicy,
    OutlierPolicy,
    QuarantineReconciliationReport,
    evaluate_record_quarantine,
    export_quarantine_artifacts,
    partition_and_quarantine_df,
)
from compintel.schema.enums import QuarantineReason, RoleFamily


@pytest.fixture
def clean_record() -> dict[str, object]:
    """A fully compliant canonical tech compensation record."""
    return {
        "observation_id": "OBS-CLEAN-01",
        "source_id": "SRC-INT-VOL-01",
        "role_family": RoleFamily.SWE.value,
        "canonical_title": "Software Engineer",
        "seniority": "MID",
        "location": "BENGALURU",
        "years_experience": 4.5,
        "guaranteed_cash_annual": 22.0,
        "basic_annual": 11.0,
        "hra_annual": 5.5,
        "special_allowance_annual": 5.5,
        "total_comp_annual": 25.0,
        "employment_type": "full-time",
        "raw_currency": "INR",
        "is_unbundled_aggregate": False,
        "is_exact_duplicate": False,
    }


@pytest.mark.unit
def test_evaluate_record_clean(clean_record: dict[str, object]) -> None:
    """Verify that a compliant record passes quarantine evaluation without exclusion."""
    is_q, reason, detail = evaluate_record_quarantine(clean_record)
    assert not is_q
    assert reason is None
    assert detail is None


@pytest.mark.unit
def test_evaluate_non_tech_role(clean_record: dict[str, object]) -> None:
    """Verify non-tech occupation is quarantined under Rule R-DA-01."""
    rec = dict(clean_record)
    rec["role_family"] = "OTHER"
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.NON_TECH_ROLE
    assert detail is not None and "occupational scope" in detail


@pytest.mark.unit
def test_evaluate_foreign_geography(clean_record: dict[str, object]) -> None:
    """Verify foreign locations are quarantined under Rule R-MD-08."""
    rec = dict(clean_record)
    rec["location"] = "San Francisco, USA"
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.GEO_OUT_OF_SCOPE
    assert detail is not None and "isolated under Rule R-MD-08" in detail


@pytest.mark.unit
def test_evaluate_enterprise_aggregate(clean_record: dict[str, object]) -> None:
    """Verify corporate census aggregates are quarantined from individual training data."""
    rec = dict(clean_record)
    rec["source_id"] = "SRC-SUP-CORP-01"
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.ENTERPRISE_AGGREGATE


@pytest.mark.unit
def test_evaluate_non_fulltime(clean_record: dict[str, object]) -> None:
    """Verify intern or contractor observations are quarantined when fulltime is enforced."""
    rec = dict(clean_record)
    rec["employment_type"] = "Summer Intern"
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.NON_FULLTIME


@pytest.mark.unit
def test_evaluate_unbundled_aggregate_ctc(clean_record: dict[str, object]) -> None:
    """Verify bundled aggregate CTC without itemization is quarantined under Rule R-MD-07."""
    rec = dict(clean_record)
    rec["is_unbundled_aggregate"] = True
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.UNBUNDLED_AGGREGATE
    assert detail is not None and "Rule R-MD-07" in detail


@pytest.mark.unit
def test_evaluate_missing_or_negative_pay(clean_record: dict[str, object]) -> None:
    """Verify missing, null, or zero pay values are quarantined under Rule R-DA-05."""
    for bad_pay in (None, 0.0, -5.0, "invalid"):
        rec = dict(clean_record)
        rec["guaranteed_cash_annual"] = bad_pay
        is_q, reason, _ = evaluate_record_quarantine(rec)
        assert is_q
        assert reason == QuarantineReason.MISSING_PAY


@pytest.mark.unit
def test_evaluate_missing_or_negative_experience(clean_record: dict[str, object]) -> None:
    """Verify negative experience is quarantined under Rule R-DA-05."""
    rec = dict(clean_record)
    rec["years_experience"] = -1.0
    is_q, reason, _ = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.MISSING_EXPERIENCE


@pytest.mark.unit
def test_evaluate_pay_outliers(clean_record: dict[str, object]) -> None:
    """Verify extreme pay values below floor or above ceiling trigger OUTLIER quarantine."""
    # Below floor (e.g. 0.1 LPA = 10,000 INR/year)
    rec_low = dict(clean_record)
    rec_low["guaranteed_cash_annual"] = 0.10
    is_q, reason, detail = evaluate_record_quarantine(rec_low)
    assert is_q
    assert reason == QuarantineReason.OUTLIER
    assert detail is not None and "below entry floor" in detail

    # Above ceiling (e.g. 400 LPA base pay)
    rec_high = dict(clean_record)
    rec_high["guaranteed_cash_annual"] = 400.0
    is_q, reason, detail = evaluate_record_quarantine(rec_high)
    assert is_q
    assert reason == QuarantineReason.OUTLIER
    assert detail is not None and "exceeds base ceiling" in detail


@pytest.mark.unit
def test_evaluate_experience_outlier(clean_record: dict[str, object]) -> None:
    """Verify unrealistic experience values trigger OUTLIER quarantine."""
    rec = dict(clean_record)
    rec["years_experience"] = 52.0
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.OUTLIER
    assert detail is not None and "maximum career ceiling" in detail


@pytest.mark.unit
def test_evaluate_itemized_sum_inconsistency(clean_record: dict[str, object]) -> None:
    """Verify arithmetic mismatch between itemized lines and base pay triggers SCHEMA_VIOLATION."""
    rec = dict(clean_record)
    rec["guaranteed_cash_annual"] = 20.0
    rec["basic_annual"] = 5.0
    rec["hra_annual"] = 2.0
    rec["special_allowance_annual"] = 2.0  # Sum is 9.0 != 20.0 (11 LPA deviation)
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.SCHEMA_VIOLATION
    assert detail is not None and "deviates by" in detail


@pytest.mark.unit
def test_evaluate_total_comp_inconsistency(clean_record: dict[str, object]) -> None:
    """Verify total compensation less than guaranteed cash triggers SCHEMA_VIOLATION."""
    rec = dict(clean_record)
    rec["guaranteed_cash_annual"] = 25.0
    rec["total_comp_annual"] = 20.0
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.SCHEMA_VIOLATION


@pytest.mark.unit
def test_evaluate_duplicate(clean_record: dict[str, object]) -> None:
    """Verify records flagged as duplicates are quarantined with DUPLICATE reason."""
    rec = dict(clean_record)
    rec["is_exact_duplicate"] = True
    rec["exact_duplicate_of"] = "OBS-PRIMARY-01"
    is_q, reason, detail = evaluate_record_quarantine(rec)
    assert is_q
    assert reason == QuarantineReason.DUPLICATE
    assert detail is not None and "OBS-PRIMARY-01" in detail


@pytest.mark.unit
def test_partition_and_quarantine_df_empty() -> None:
    """Verify empty DataFrame handles cleanly with zero counts and exact reconciliation."""
    df = pl.DataFrame({"observation_id": pl.Series([], dtype=pl.String)})
    res = partition_and_quarantine_df(df)

    assert res.valid_df.height == 0
    assert res.quarantined_df.height == 0
    assert len(res.quarantine_records) == 0
    assert res.report.total_input_records == 0
    assert res.report.is_reconciled
    assert res.report.discrepancy_count == 0


@pytest.mark.unit
def test_partition_and_quarantine_df_reconciliation(clean_record: dict[str, object]) -> None:
    """Verify mathematical reconciliation: Total == Valid + Quarantined (Rule R-DA-05)."""
    r1 = dict(clean_record)
    r1["observation_id"] = "REC-1"

    r2 = dict(clean_record)
    r2["observation_id"] = "REC-2"
    r2["guaranteed_cash_annual"] = 0.05  # Outlier low

    r3 = dict(clean_record)
    r3["observation_id"] = "REC-3"
    r3["role_family"] = "OTHER"  # Non-tech role

    r4 = dict(clean_record)
    r4["observation_id"] = "REC-4"

    df = pl.DataFrame([r1, r2, r3, r4])

    res = partition_and_quarantine_df(
        df,
        halt_threshold=0.60,
        halt_on_exceed=True,
    )

    assert res.valid_df.height == 2
    assert res.quarantined_df.height == 2
    assert len(res.quarantine_records) == 2

    # Zero silent drops (Rule R-DA-05)
    assert res.report.total_input_records == 4
    assert res.report.valid_accepted_records == 2
    assert res.report.quarantined_records == 2
    assert res.report.is_reconciled
    assert res.report.discrepancy_count == 0
    assert res.report.quarantine_rate == 0.50
    assert not res.report.halt_triggered

    # Quarantined columns check
    assert "quarantine_id" in res.quarantined_df.columns
    assert "quarantine_reason" in res.quarantined_df.columns
    assert "exclusion_details" in res.quarantined_df.columns
    assert "quarantined_at" in res.quarantined_df.columns


@pytest.mark.unit
def test_partition_and_quarantine_halt_threshold(clean_record: dict[str, object]) -> None:
    """Verify PipelineHaltError is raised when quarantine rate exceeds threshold (Rule R-ER-06)."""
    # 3 out of 4 records invalid -> 75% quarantine rate > 25% threshold
    records = [
        dict(clean_record, observation_id="R1"),
        dict(clean_record, observation_id="R2", guaranteed_cash_annual=None),
        dict(clean_record, observation_id="R3", role_family="OTHER"),
        dict(clean_record, observation_id="R4", location="New York, USA"),
    ]
    df = pl.DataFrame(records)

    with pytest.raises(PipelineHaltError) as exc_info:
        partition_and_quarantine_df(
            df,
            halt_threshold=0.25,
            halt_on_exceed=True,
        )

    err = exc_info.value
    assert err.code == "QUARANTINE_RATE_EXCEEDED"
    assert "exceeded configured halt threshold" in err.message
    assert err.details["quarantine_rate"] == 0.75
    assert err.details["halt_threshold"] == 0.25

    # If halt_on_exceed is False, it should complete with halt_triggered = True
    res = partition_and_quarantine_df(
        df,
        halt_threshold=0.25,
        halt_on_exceed=False,
    )
    assert res.report.halt_triggered
    assert res.report.quarantine_rate == 0.75


@pytest.mark.unit
def test_quarantine_report_formatting_and_export(tmp_path: Path, clean_record: dict[str, object]) -> None:
    """Verify report serialization and artifact export (parquet table + markdown report)."""
    records = [
        dict(clean_record, observation_id="R1"),
        dict(clean_record, observation_id="R2", role_family="OTHER"),
        dict(clean_record, observation_id="R3", guaranteed_cash_annual=0.1),
    ]
    df = pl.DataFrame(records)
    res = partition_and_quarantine_df(df, halt_threshold=0.80)

    # Dictionary conversion
    d = res.report.to_dict()
    assert d["total_input_records"] == 3
    assert d["quarantined_records"] == 2
    assert d["is_reconciled"] is True

    # Polars DataFrame conversion
    report_df = res.report.to_dataframe()
    assert report_df.height == 2
    assert "quarantine_reason" in report_df.columns
    assert "count" in report_df.columns

    # Markdown formatting
    md = res.report.to_markdown()
    assert "# CompIntel Data Quality: Quarantine & Count Reconciliation Report" in md
    assert "RECONCILED (Zero Silent Drops)" in md
    assert "non_tech_role" in md
    assert "outlier" in md

    # Artifact export
    parquet_path, md_path = export_quarantine_artifacts(res, output_dir=tmp_path)
    assert parquet_path.exists()
    assert md_path.exists()
    assert parquet_path.stat().st_size > 0
    assert md_path.stat().st_size > 0
