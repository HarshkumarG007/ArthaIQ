"""Contract tests for canonical Pandera DataFrameSchema (Rules R-DA-03, R-ER-02)."""

from datetime import UTC, date, datetime

import polars as pl
import pytest

from compintel.errors import DataContractError
from compintel.schema import (
    CURRENT_SCHEMA_VERSION,
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    RoleFamily,
    SeniorityLevel,
    validate_observations_df,
)


def _build_valid_polars_df() -> pl.DataFrame:
    now = datetime.now(UTC)
    return pl.DataFrame(
        {
            "observation_id": ["OBS-001", "OBS-002"],
            "source_id": ["SRC-INT-VOL-01", "SRC-INT-VOL-01"],
            "source_version": ["v1.0", "v1.0"],
            "schema_version": [CURRENT_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION],
            "license_id": ["PROPRIETARY-CONSENTED", "PROPRIETARY-CONSENTED"],
            "provenance_tier": [ProvenanceTier.TIER_A.value, ProvenanceTier.TIER_A.value],
            "as_of_date": [date(2026, 10, 1), date(2026, 10, 2)],
            "ingested_at": [now, now],
            "is_synthetic": [False, False],
            "role_family": [RoleFamily.SWE.value, RoleFamily.DATA.value],
            "canonical_title": ["Backend Engineer", "Data Scientist"],
            "raw_title": ["SWE II", "Data Scientist"],
            "seniority": [SeniorityLevel.MID.value, SeniorityLevel.SR.value],
            "location": [MetroLocation.BENGALURU.value, MetroLocation.HYDERABAD.value],
            "raw_location": ["Bengaluru", "Hyderabad"],
            "years_experience": [4.0, 7.5],
            "guaranteed_cash_annual": [22.0, 31.0],
            "raw_pay_amount": [2200000.0, 3100000.0],
            "raw_currency": ["INR", "INR"],
            "raw_pay_period": [PayPeriod.ANNUAL.value, PayPeriod.ANNUAL.value],
            "is_unbundled_aggregate": [False, False],
            "quarantine_status": [False, False],
        }
    )


@pytest.mark.contract
def test_valid_dataframe_passes_contract() -> None:
    """Verify that conforming Polars DataFrame passes contract schema."""
    df = _build_valid_polars_df()
    validated = validate_observations_df(df)

    assert validated.height == 2
    assert "guaranteed_cash_annual" in validated.columns


@pytest.mark.contract
def test_missing_column_raises_data_contract_error() -> None:
    """Dropping a mandatory column must raise DataContractError."""
    df = _build_valid_polars_df().drop("observation_id")

    with pytest.raises(DataContractError) as exc_info:
        validate_observations_df(df)

    assert exc_info.value.code == "DATAFRAME_CONTRACT_ERROR"


@pytest.mark.contract
def test_negative_pay_amount_raises_data_contract_error() -> None:
    """Negative raw_pay_amount must violate value bounds and raise DataContractError."""
    df = _build_valid_polars_df().with_columns(pl.Series("raw_pay_amount", [-50000.0, 3100000.0]))

    with pytest.raises(DataContractError) as exc_info:
        validate_observations_df(df)

    assert exc_info.value.code == "DATAFRAME_CONTRACT_ERROR"


@pytest.mark.contract
def test_null_mandatory_field_raises_data_contract_error() -> None:
    """Null in a non-nullable column must violate contract and raise DataContractError."""
    df = _build_valid_polars_df().with_columns(pl.Series("source_id", [None, "SRC-INT-VOL-01"]))

    with pytest.raises(DataContractError) as exc_info:
        validate_observations_df(df)

    assert exc_info.value.code == "DATAFRAME_CONTRACT_ERROR"
