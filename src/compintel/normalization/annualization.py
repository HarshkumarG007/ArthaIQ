"""Pay period annualization and frequency normalization (T1.02, T3.05).

Converts compensation figures across pay frequencies (annual, monthly, biweekly, hourly)
to an annualized baseline and provides exact de-annualization.
"""

from __future__ import annotations

import math

from compintel.errors import DataContractError
from compintel.schema.enums import PayPeriod

# Standard full-time hours convention (40 hours/week * 52 weeks = 2,080 hours)
DEFAULT_HOURS_PER_WEEK: float = 40.0
WEEKS_PER_YEAR: float = 52.0
MONTHS_PER_YEAR: float = 12.0
BIWEEKS_PER_YEAR: float = 26.0


def _parse_period(period: PayPeriod | str) -> PayPeriod:
    """Validate and coerce input to PayPeriod enum."""
    if isinstance(period, PayPeriod):
        return period
    try:
        return PayPeriod(period.lower().strip())
    except (ValueError, AttributeError) as exc:
        raise DataContractError(
            f"Invalid pay period: '{period}'. Must be one of {[p.value for p in PayPeriod]}.",
            code="INVALID_PAY_PERIOD",
            details={"input_period": str(period)},
        ) from exc


def get_annualization_factor(
    period: PayPeriod | str, hours_per_week: float = DEFAULT_HOURS_PER_WEEK
) -> float:
    """Return multiplier to convert a single period payment to an annual payment."""
    p = _parse_period(period)

    if p == PayPeriod.ANNUAL:
        return 1.0
    if p == PayPeriod.MONTHLY:
        return MONTHS_PER_YEAR
    if p == PayPeriod.BIWEEKLY:
        return BIWEEKS_PER_YEAR
    if p == PayPeriod.HOURLY:
        if hours_per_week <= 0.0 or math.isnan(hours_per_week):
            raise DataContractError(
                f"Hourly annualization requires positive hours_per_week, got {hours_per_week}.",
                code="INVALID_HOURLY_BASIS",
            )
        return hours_per_week * WEEKS_PER_YEAR
    if p == PayPeriod.UNKNOWN:
        raise DataContractError(
            "Cannot annualize unknown pay period. Rule R-MD-07 forbids guessing frequency.",
            code="UNKNOWN_PAY_PERIOD_QUARANTINE",
        )

    raise DataContractError(f"Unhandled pay period: {p}", code="UNHANDLED_PAY_PERIOD")


def annualize(
    amount: float,
    period: PayPeriod | str,
    hours_per_week: float = DEFAULT_HOURS_PER_WEEK,
) -> float:
    """Annualize payment amount according to frequency.

    Args:
        amount: Raw payment value (must be non-negative and finite).
        period: Pay frequency (annual, monthly, biweekly, hourly).
        hours_per_week: Hours basis for hourly workers (default 40.0).

    Returns:
        Annualized compensation amount.
    """
    if amount < 0.0 or math.isnan(amount) or math.isinf(amount):
        raise DataContractError(
            f"Cannot annualize invalid amount: {amount}. Amount must be finite and non-negative.",
            code="INVALID_PAY_AMOUNT",
            details={"amount": amount},
        )

    factor = get_annualization_factor(period, hours_per_week=hours_per_week)
    return amount * factor


def deannualize(
    annual_amount: float,
    target_period: PayPeriod | str,
    hours_per_week: float = DEFAULT_HOURS_PER_WEEK,
) -> float:
    """Convert an annualized amount back to a specified pay frequency.

    Guarantees round-trip equality: deannualize(annualize(x, p), p) == x.
    """
    if annual_amount < 0.0 or math.isnan(annual_amount) or math.isinf(annual_amount):
        raise DataContractError(
            f"Cannot de-annualize invalid amount: {annual_amount}.",
            code="INVALID_PAY_AMOUNT",
            details={"annual_amount": annual_amount},
        )

    factor = get_annualization_factor(target_period, hours_per_week=hours_per_week)
    return annual_amount / factor
