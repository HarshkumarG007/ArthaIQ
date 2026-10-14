"""Unit tests for normalization error handling and edge cases (Rule R-DA-03)."""

from datetime import date

import pytest

from compintel.errors import DataContractError
from compintel.normalization.annualization import (
    annualize,
    deannualize,
    get_annualization_factor,
)
from compintel.normalization.currency import (
    FXRateTable,
    convert_currency,
)
from compintel.normalization.deflation import (
    CPIEntry,
    CPITable,
    adjust_for_cpi,
)
from compintel.normalization.denomination import (
    from_lpa,
    to_lpa,
)
from compintel.schema.enums import Currency, PayPeriod


@pytest.mark.unit
def test_annualization_invalid_period() -> None:
    """Invalid period string raises DataContractError."""
    with pytest.raises(DataContractError) as exc_info:
        get_annualization_factor("decade")
    assert exc_info.value.code == "INVALID_PAY_PERIOD"


@pytest.mark.unit
def test_hourly_invalid_hours_basis() -> None:
    """Non-positive hours per week raises DataContractError."""
    with pytest.raises(DataContractError) as exc_info:
        get_annualization_factor(PayPeriod.HOURLY, hours_per_week=0.0)
    assert exc_info.value.code == "INVALID_HOURLY_BASIS"


@pytest.mark.unit
def test_annualize_negative_amount_raises_error() -> None:
    """Negative amount raises DataContractError."""
    with pytest.raises(DataContractError) as exc_info:
        annualize(-1000.0, PayPeriod.MONTHLY)
    assert exc_info.value.code == "INVALID_PAY_AMOUNT"

    with pytest.raises(DataContractError) as exc_info:
        deannualize(-12000.0, PayPeriod.MONTHLY)
    assert exc_info.value.code == "INVALID_PAY_AMOUNT"


@pytest.mark.unit
def test_denomination_negative_amount_raises_error() -> None:
    """Negative amount raises DataContractError."""
    with pytest.raises(DataContractError) as exc_info:
        to_lpa(-500000.0)
    assert exc_info.value.code == "INVALID_DENOMINATION_AMOUNT"

    with pytest.raises(DataContractError) as exc_info:
        from_lpa(-5.0)
    assert exc_info.value.code == "INVALID_DENOMINATION_AMOUNT"


@pytest.mark.unit
def test_currency_unsupported_pair_raises_error() -> None:
    """Unsupported currency pair raises FX_RATE_NOT_FOUND."""
    empty_table = FXRateTable(entries=())
    with pytest.raises(DataContractError) as exc_info:
        convert_currency(
            100.0, Currency.USD, Currency.EUR, date(2026, 1, 1), rate_table=empty_table
        )
    assert exc_info.value.code == "FX_RATE_NOT_FOUND"


@pytest.mark.unit
def test_currency_negative_amount_raises_error() -> None:
    """Negative amount raises DataContractError."""
    with pytest.raises(DataContractError) as exc_info:
        convert_currency(-50.0, Currency.USD, Currency.INR, date(2026, 1, 1))
    assert exc_info.value.code == "INVALID_PAY_AMOUNT"


@pytest.mark.unit
def test_currency_same_currency_returns_amount() -> None:
    """Converting from currency to itself returns original amount."""
    val = convert_currency(500.0, Currency.INR, Currency.INR, date(2026, 1, 1))
    assert val == 500.0


@pytest.mark.unit
def test_deflation_empty_table_raises_error() -> None:
    """Empty CPI table raises EMPTY_CPI_TABLE."""
    empty_cpi = CPITable(series=())
    with pytest.raises(DataContractError) as exc_info:
        adjust_for_cpi(20.0, date(2024, 1, 1), date(2026, 1, 1), cpi_table=empty_cpi)
    assert exc_info.value.code == "EMPTY_CPI_TABLE"


@pytest.mark.unit
def test_deflation_negative_amount_raises_error() -> None:
    """Negative amount raises DataContractError."""
    with pytest.raises(DataContractError) as exc_info:
        adjust_for_cpi(-20.0, date(2024, 1, 1), date(2026, 1, 1))
    assert exc_info.value.code == "INVALID_PAY_AMOUNT"


@pytest.mark.unit
def test_deflation_invalid_cpi_value_raises_error() -> None:
    """Zero or negative CPI in table raises INVALID_CPI_VALUE."""
    bad_cpi = CPITable(
        series=(
            CPIEntry(date(2024, 1, 1), 0.0),
            CPIEntry(date(2026, 1, 1), 100.0),
        )
    )
    with pytest.raises(DataContractError) as exc_info:
        adjust_for_cpi(20.0, date(2024, 1, 1), date(2026, 1, 1), cpi_table=bad_cpi)
    assert exc_info.value.code == "INVALID_CPI_VALUE"
