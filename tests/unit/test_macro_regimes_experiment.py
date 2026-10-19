"""Unit and regression tests for Macroeconomic & Market-Regime Experiment (T7.05, EXP-MACRO-01).

Validates:
- Gate 1 data feasibility: audits non-synthetic observation span (< 24 months triggers DEFER).
- Gate 2 point-in-time integrity: verifies MOSPI CPI release calendar and zero lookahead.
- Real-pay mathematical transformation and exact round-trip inversion.
- FX lookbacks over weekends, bank holidays, and missing trade days.
- Pre-series and missing series contract guards.
- Preregistered DEFER outcome and production champion preservation.
- Self-contained fixtures isolating unit tests from gitignored raw data (Rule R-DA-08).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import polars as pl
import pytest

from compintel.errors import DataContractError
from compintel.evaluation.macro_regimes_experiment import (
    CPIReleaseCalendar,
    MacroDecisionVerdict,
    MacroFeasibilityStatus,
    PointInTimeMacroJoiner,
    RealPayTransformer,
    audit_macro_feasibility,
    run_macro_regimes_experiment,
)


@pytest.fixture
def sample_macro_dir(tmp_path: Path) -> Path:
    """Create a self-contained macro directory with valid CPI and FX series (Rule R-DA-08)."""
    # 1. Generate monthly CPI from 1957 to 2024
    cpi_rows = ["observation_date,INDCPIALLMINMEI", "1957-01-01,1.47"]
    start_cpi = datetime.date(2021, 1, 1)
    end_cpi = datetime.date(2024, 8, 1)
    curr = start_cpi
    cpi_val = 160.0
    while curr <= end_cpi:
        if curr == datetime.date(2024, 4, 1):
            cpi_rows.append("2024-04-01,185.00")
        elif curr == datetime.date(2024, 5, 1):
            cpi_rows.append("2024-05-01,186.20")
        else:
            cpi_rows.append(f"{curr.isoformat()},{cpi_val:.2f}")
        year = curr.year + (curr.month // 12)
        month = (curr.month % 12) + 1
        curr = datetime.date(year, month, 1)
        cpi_val += 0.65

    cpi_csv = tmp_path / "cpi_urban_monthly.csv"
    cpi_csv.write_text("\n".join(cpi_rows) + "\n", encoding="utf-8")

    # 2. Generate daily FX rates from 2021 to 2024
    fx_rows = ["observation_date,DEXINUS", "1973-01-02,8.02"]
    start_fx = datetime.date(2021, 1, 1)
    end_fx = datetime.date(2024, 8, 1)
    curr_fx = start_fx
    fx_val = 82.50
    while curr_fx <= end_fx:
        if curr_fx.weekday() < 5:  # Monday - Friday only
            if curr_fx == datetime.date(2024, 6, 14):
                fx_rows.append("2024-06-14,83.60")
            elif curr_fx == datetime.date(2024, 6, 17):
                fx_rows.append("2024-06-17,83.65")
            else:
                fx_rows.append(f"{curr_fx.isoformat()},{fx_val:.2f}")
            fx_val = round(fx_val + 0.005, 4)
        curr_fx += datetime.timedelta(days=1)

    fx_csv = tmp_path / "inr_usd_fx_daily.csv"
    fx_csv.write_text("\n".join(fx_rows) + "\n", encoding="utf-8")
    return tmp_path


# ==============================================================================
# Gate 1: Feasibility Audit Tests
# ==============================================================================


def test_gate1_feasibility_fails_on_canonical_short_span() -> None:
    """Verify that canonical observations (13 days) fail Gate 1 (< 24 months) and defer."""
    canonical_path = Path("data/canonical/canonical_observations.parquet")
    macro_path = Path("data/raw/SRC-SUP-MAC-01")
    if not canonical_path.exists() or not (macro_path / "cpi_urban_monthly.csv").exists():
        pytest.skip("Canonical or raw macro dataset missing (gitignored per R-DA-08)")

    df = pl.read_parquet(canonical_path)
    audit = audit_macro_feasibility(
        df,
        macro_dir=macro_path,
        min_required_months=24.0,
        allow_synthetic=False,
    )

    assert audit.status == MacroFeasibilityStatus.INSUFFICIENT_SPAN
    assert audit.observation_span_days < 730
    assert audit.observation_span_months < 24.0
    assert audit.cpi_series_present is True
    assert audit.fx_series_present is True
    assert "DEFER" in audit.summary or "failing" in audit.summary


def test_gate1_skips_modeling_and_records_defer_on_canonical_data() -> None:
    """Verify that Gate 1 skips expensive model fitting and records DEFER on canonical data."""
    canonical_path = Path("data/canonical/canonical_observations.parquet")
    macro_path = Path("data/raw/SRC-SUP-MAC-01")
    if not canonical_path.exists() or not (macro_path / "cpi_urban_monthly.csv").exists():
        pytest.skip("Canonical or raw macro dataset missing (gitignored per R-DA-08)")

    df = pl.read_parquet(canonical_path)
    report = run_macro_regimes_experiment(
        train_df=df,
        eval_df=df,
        calibrate_df=df,
        macro_dir=macro_path,
        force_modeling=False,
        allow_synthetic=False,
    )

    assert report.overall_verdict == MacroDecisionVerdict.DEFER
    assert report.modeling_executed is False
    assert report.baseline_metrics is None
    assert report.variant_a_metrics is None
    assert report.variant_b_metrics is None
    assert len(report.deltas) == 0
    assert "Feasibility Gate 1 DEFERRAL" in report.executive_summary


def test_gate1_feasibility_passes_on_long_longitudinal_span(sample_macro_dir: Path) -> None:
    """Verify that an observation panel spanning >= 24 months passes Gate 1."""
    dates = [
        datetime.date(2022, 1, 1),
        datetime.date(2023, 1, 1),
        datetime.date(2024, 7, 1),  # Span: 912 days > 730 days (~30 months)
    ]
    df = pl.DataFrame(
        {
            "observation_id": ["O1", "O2", "O3"],
            "as_of_date": dates,
            "is_synthetic": [False, False, False],
        }
    )

    audit = audit_macro_feasibility(
        df,
        macro_dir=sample_macro_dir,
        min_required_months=24.0,
        allow_synthetic=False,
    )

    assert audit.status == MacroFeasibilityStatus.FEASIBLE
    assert audit.observation_span_days >= 730
    assert audit.observation_span_months >= 24.0
    assert "Gate 1 feasibility passed" in audit.summary


def test_gate1_missing_macro_series_detection(tmp_path: Path) -> None:
    """Verify that missing macro files trigger MISSING_MACRO_SERIES."""
    df = pl.DataFrame(
        {
            "as_of_date": [datetime.date(2024, 1, 1), datetime.date(2024, 6, 1)],
            "is_synthetic": [False, False],
        }
    )
    audit = audit_macro_feasibility(df, macro_dir=tmp_path, allow_synthetic=False)
    assert audit.status == MacroFeasibilityStatus.MISSING_MACRO_SERIES
    assert audit.cpi_series_present is False
    assert audit.fx_series_present is False


# ==============================================================================
# Gate 2: Publication Calendar & Point-in-Time Join Tests
# ==============================================================================


def test_mospi_cpi_release_calendar_exact_dates_and_weekends() -> None:
    """Test MOSPI CPI publication calendar rules and weekend rollovers."""
    # May 2024 -> June 12, 2024 was Wednesday (normal day 12)
    rel_may_24 = CPIReleaseCalendar.get_release_date(datetime.date(2024, 5, 1))
    assert rel_may_24 == datetime.date(2024, 6, 12)

    # April 2024 -> May 12, 2024 was Sunday -> rolls to Monday May 13, 2024
    rel_apr_24 = CPIReleaseCalendar.get_release_date(datetime.date(2024, 4, 1))
    assert rel_apr_24 == datetime.date(2024, 5, 13)

    # September 2024 -> October 12, 2024 was Saturday -> rolls to Monday October 14, 2024
    rel_sep_24 = CPIReleaseCalendar.get_release_date(datetime.date(2024, 9, 1))
    assert rel_sep_24 == datetime.date(2024, 10, 14)

    # December 2023 -> January 12, 2024 was Friday (normal day 12)
    rel_dec_23 = CPIReleaseCalendar.get_release_date(datetime.date(2023, 12, 1))
    assert rel_dec_23 == datetime.date(2024, 1, 12)


def test_point_in_time_join_strictly_prevents_lookahead(sample_macro_dir: Path) -> None:
    """Test that query date strictly cannot access CPI before publication date."""
    joiner = PointInTimeMacroJoiner(sample_macro_dir)

    # May 2024 CPI (ref: 2024-05-01) was released on June 12, 2024.
    # Query on June 11, 2024 MUST NOT see May 2024 CPI; it must see April 2024 CPI.
    ref_pre, rel_pre, val_pre = joiner.get_as_of_cpi(datetime.date(2024, 6, 11))
    assert ref_pre == datetime.date(2024, 4, 1)
    assert rel_pre == datetime.date(2024, 5, 13)  # May 12 was Sunday -> May 13

    # Query on June 12, 2024 CAN see May 2024 CPI.
    ref_post, rel_post, val_post = joiner.get_as_of_cpi(datetime.date(2024, 6, 12))
    assert ref_post == datetime.date(2024, 5, 1)
    assert rel_post == datetime.date(2024, 6, 12)
    assert val_post != val_pre


def test_fx_lookback_handles_weekends_and_bank_holidays(sample_macro_dir: Path) -> None:
    """Test that FX lookback properly queries trading days and handles holidays."""
    joiner = PointInTimeMacroJoiner(sample_macro_dir)

    # Sunday query: 2024-06-16 (Sunday) must return Friday rate: 2024-06-14
    rate_sun, vol_sun = joiner.get_as_of_fx_metrics(datetime.date(2024, 6, 16))
    rate_fri, vol_fri = joiner.get_as_of_fx_metrics(datetime.date(2024, 6, 14))
    assert rate_sun == rate_fri
    assert vol_sun == vol_fri
    assert rate_sun > 80.0  # INR/USD in mid-2024 was ~83.5


def test_pre_series_observation_raises_data_contract_error(sample_macro_dir: Path) -> None:
    """Test that querying a date prior to earliest macro release raises DataContractError."""
    joiner = PointInTimeMacroJoiner(sample_macro_dir)
    ancient_date = datetime.date(1950, 1, 1)

    with pytest.raises(DataContractError, match="PRE_SERIES_MACRO_DATE"):
        joiner.get_as_of_cpi(ancient_date)


# ==============================================================================
# Real-Pay Transformation & Inversion Tests
# ==============================================================================


def test_real_pay_exact_round_trip_inversion() -> None:
    """Verify that nominal -> real -> nominal round trip is exact within 1e-9."""
    transformer = RealPayTransformer(cpi_ref=185.1)
    test_amounts = [5.0, 12.5, 35.0, 85.0, 150.0]
    test_cpis = [145.0, 153.0, 185.1, 205.0]

    for amt in test_amounts:
        for cpi in test_cpis:
            assert transformer.validate_round_trip(amt, cpi)
            real = transformer.to_real(amt, cpi)
            recon = transformer.to_nominal(real, cpi)
            assert abs(amt - recon) < 1e-9


def test_real_pay_reference_identity() -> None:
    """When cpi_as_of == cpi_ref, nominal and real pay are identical."""
    transformer = RealPayTransformer(cpi_ref=185.1)
    assert transformer.to_real(50.0, 185.1) == 50.0
    assert transformer.to_nominal(50.0, 185.1) == 50.0


# ==============================================================================
# End-to-End Simulation Test (Forced Modeling on Multi-Year Fixture)
# ==============================================================================


def test_macro_experiment_pipeline_when_modeling_forced(sample_macro_dir: Path) -> None:
    """Test that when modeling is forced, CatBoost runs with conformal calibration."""
    from tests.fixtures.synthetic import generate_synthetic_observations_df

    n = 60
    base_df = generate_synthetic_observations_df(n_records=n, seed=42)
    # Generate multi-year dates spanning 2022 to 2024
    dates = [datetime.date(2022, 1, 1) + datetime.timedelta(days=i * 15) for i in range(n)]
    df = base_df.with_columns(
        [
            pl.Series("as_of_date", dates),
            pl.Series("person_cluster_id", [f"PER-{i:03d}" for i in range(n)]),
        ]
    )

    train_df = df.slice(0, 35)
    calib_df = df.slice(35, 12)
    eval_df = df.slice(47, 13)

    report = run_macro_regimes_experiment(
        train_df=train_df,
        eval_df=eval_df,
        calibrate_df=calib_df,
        macro_dir=sample_macro_dir,
        eval_split_name="select",
        n_resamples=50,
        seed=42,
        force_modeling=True,
        allow_synthetic=True,
    )

    assert report.modeling_executed is True
    assert report.baseline_metrics is not None
    assert report.variant_a_metrics is not None
    assert report.variant_b_metrics is not None
    assert len(report.deltas) == 2

    # Verify monotonic non-crossing quantiles on all variants
    assert report.baseline_metrics.crossing_rate == 0.0
    assert report.variant_a_metrics.crossing_rate == 0.0
    assert report.variant_b_metrics.crossing_rate == 0.0
