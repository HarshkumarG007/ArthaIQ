"""Property-based tests for compensation normalization (Rules R-DA-03, R-MD-07, R-MD-08).

Uses Hypothesis to verify round-trip invertibility, strict monotonicity,
and contract invariants across annualization, denomination, and currency.
"""

import math
from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from compintel.errors import DataContractError
from compintel.normalization import (
    adjust_for_cpi,
    annualize,
    convert_currency,
    deannualize,
    enforce_market_isolation,
    from_lpa,
    to_lpa,
)
from compintel.schema.enums import Currency, PayPeriod

# Strategies
valid_amounts = st.floats(min_value=0.0, max_value=1e10, allow_nan=False, allow_infinity=False)
valid_periods = st.sampled_from(
    [
        PayPeriod.ANNUAL,
        PayPeriod.MONTHLY,
        PayPeriod.BIWEEKLY,
        PayPeriod.HOURLY,
    ]
)


@pytest.mark.property
@given(amount=valid_amounts, period=valid_periods)
def test_annualization_round_trip(amount: float, period: PayPeriod) -> None:
    """Invariant: deannualize(annualize(x, p), p) == x within floating-point tolerance."""
    annualized = annualize(amount, period)
    recovered = deannualize(annualized, period)

    assert math.isclose(recovered, amount, rel_tol=1e-7, abs_tol=1e-7)


@pytest.mark.property
@given(
    a1=st.floats(min_value=0.0, max_value=1e9, allow_nan=False),
    a2=st.floats(min_value=0.0, max_value=1e9, allow_nan=False),
    period=valid_periods,
)
def test_annualization_monotonicity(a1: float, a2: float, period: PayPeriod) -> None:
    """Invariant: a1 <= a2 implies annualize(a1) <= annualize(a2)."""
    low, high = (a1, a2) if a1 <= a2 else (a2, a1)

    ann_low = annualize(low, period)
    ann_high = annualize(high, period)

    assert ann_low <= ann_high


@pytest.mark.property
@given(inr_amount=valid_amounts)
def test_denomination_round_trip(inr_amount: float) -> None:
    """Invariant: from_lpa(to_lpa(x)) == x."""
    lpa = to_lpa(inr_amount)
    recovered = from_lpa(lpa)

    assert math.isclose(recovered, inr_amount, rel_tol=1e-7, abs_tol=1e-7)


@pytest.mark.property
@given(
    a1=st.floats(min_value=0.0, max_value=1e10, allow_nan=False),
    a2=st.floats(min_value=0.0, max_value=1e10, allow_nan=False),
)
def test_denomination_monotonicity(a1: float, a2: float) -> None:
    """Invariant: a1 <= a2 implies to_lpa(a1) <= to_lpa(a2)."""
    low, high = (a1, a2) if a1 <= a2 else (a2, a1)
    assert to_lpa(low) <= to_lpa(high)


@pytest.mark.property
@given(
    amount=st.floats(min_value=1.0, max_value=1e8, allow_nan=False),
    obs_date=st.sampled_from(
        [
            date(2023, 1, 1),
            date(2024, 1, 1),
            date(2025, 1, 1),
            date(2026, 1, 1),
        ]
    ),
)
def test_currency_conversion_round_trip(amount: float, obs_date: date) -> None:
    """Invariant: USD -> INR -> USD recovers original amount."""
    inr_val = convert_currency(amount, Currency.USD, Currency.INR, obs_date)
    recovered_usd = convert_currency(inr_val, Currency.INR, Currency.USD, obs_date)

    assert math.isclose(recovered_usd, amount, rel_tol=1e-5)


@pytest.mark.property
@given(
    a1=st.floats(min_value=0.0, max_value=1e8, allow_nan=False),
    a2=st.floats(min_value=0.0, max_value=1e8, allow_nan=False),
)
def test_currency_conversion_monotonicity(a1: float, a2: float) -> None:
    """Invariant: a1 <= a2 implies convert(a1) <= convert(a2)."""
    low, high = (a1, a2) if a1 <= a2 else (a2, a1)
    d = date(2026, 1, 1)

    c_low = convert_currency(low, Currency.USD, Currency.INR, d)
    c_high = convert_currency(high, Currency.USD, Currency.INR, d)

    assert c_low <= c_high


@pytest.mark.unit
def test_unknown_period_raises_contract_error() -> None:
    """Rule R-MD-07: Unknown pay period cannot be heuristically annualized."""
    with pytest.raises(DataContractError) as exc_info:
        annualize(50000.0, PayPeriod.UNKNOWN)
    assert "UNKNOWN_PAY_PERIOD_QUARANTINE" in exc_info.value.code


@pytest.mark.unit
def test_cross_market_isolation_enforcement() -> None:
    """Rule R-MD-08: Foreign market cannot be directly pooled into Indian training set."""
    with pytest.raises(DataContractError) as exc_info:
        enforce_market_isolation("US", "IN")
    assert "R_MD_08_MARKET_ISOLATION_VIOLATION" in exc_info.value.code

    # Domestic Indian market passes
    enforce_market_isolation("IN", "IN")


@pytest.mark.unit
def test_cpi_adjustment_freshness_window() -> None:
    """Observations <= 90 days are strictly nominal; > 90 days are adjusted."""
    base_pay = 20.0  # LPA
    target_date = date(2026, 10, 1)

    # 45 days old: within window, remains unchanged
    recent_date = date(2026, 8, 17)
    assert adjust_for_cpi(base_pay, recent_date, target_date) == 20.0

    # 2 years old (2024-01-01): exceeds 90 days, gets inflated by CPI ratio (211.0 / 185.1)
    older_date = date(2024, 1, 1)
    adjusted = adjust_for_cpi(base_pay, older_date, target_date)
    expected = 20.0 * (211.0 / 185.1)
    assert math.isclose(adjusted, expected, rel_tol=1e-4)
    assert adjusted > base_pay
