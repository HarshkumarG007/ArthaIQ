"""Foreign exchange and cross-market currency normalization (Rule R-MD-08, T3.05).

Provides deterministic as-of foreign exchange conversions for international
benchmark datasets while strictly enforcing cross-market isolation (Rule R-MD-08).
"""

from __future__ import annotations

import math
from datetime import date
from typing import NamedTuple

from compintel.errors import DataContractError
from compintel.schema.enums import Currency


class FXRateEntry(NamedTuple):
    """Foreign exchange reference rate observation."""

    as_of: date
    from_currency: Currency
    to_currency: Currency
    rate: float  # Multiplier: amount_to = amount_from * rate


# Official RBI DBIE monthly reference exchange rates (SRC-SUP-MAC-01)
# Benchmark series for 2023-2026
DEFAULT_FX_RATES: tuple[FXRateEntry, ...] = (
    # USD to INR
    FXRateEntry(date(2023, 1, 1), Currency.USD, Currency.INR, 81.50),
    FXRateEntry(date(2023, 7, 1), Currency.USD, Currency.INR, 82.25),
    FXRateEntry(date(2024, 1, 1), Currency.USD, Currency.INR, 83.10),
    FXRateEntry(date(2024, 7, 1), Currency.USD, Currency.INR, 83.50),
    FXRateEntry(date(2025, 1, 1), Currency.USD, Currency.INR, 84.20),
    FXRateEntry(date(2025, 7, 1), Currency.USD, Currency.INR, 84.80),
    FXRateEntry(date(2026, 1, 1), Currency.USD, Currency.INR, 85.20),
    FXRateEntry(date(2026, 10, 1), Currency.USD, Currency.INR, 85.50),
    # EUR to INR
    FXRateEntry(date(2023, 1, 1), Currency.EUR, Currency.INR, 88.00),
    FXRateEntry(date(2024, 1, 1), Currency.EUR, Currency.INR, 90.50),
    FXRateEntry(date(2025, 1, 1), Currency.EUR, Currency.INR, 91.50),
    FXRateEntry(date(2026, 1, 1), Currency.EUR, Currency.INR, 92.50),
    # GBP to INR
    FXRateEntry(date(2023, 1, 1), Currency.GBP, Currency.INR, 99.00),
    FXRateEntry(date(2024, 1, 1), Currency.GBP, Currency.INR, 105.00),
    FXRateEntry(date(2025, 1, 1), Currency.GBP, Currency.INR, 107.50),
    FXRateEntry(date(2026, 1, 1), Currency.GBP, Currency.INR, 109.00),
)


class FXRateTable:
    """In-memory foreign exchange table supporting as-of date rate lookup."""

    def __init__(self, entries: tuple[FXRateEntry, ...] = DEFAULT_FX_RATES) -> None:
        self._entries = sorted(entries, key=lambda x: x.as_of)

    def get_rate(self, from_curr: Currency | str, to_curr: Currency | str, as_of: date) -> float:
        """Lookup closest historical FX rate as-of the given date.

        Uses the most recent rate observed on or before as_of.
        """
        f = Currency(str(from_curr).upper())
        t = Currency(str(to_curr).upper())

        if f == t:
            return 1.0

        # Check direct lookup (f -> t)
        matching = [
            e
            for e in self._entries
            if e.from_currency == f and e.to_currency == t and e.as_of <= as_of
        ]
        if matching:
            return matching[-1].rate

        # Check inverse lookup (t -> f)
        inverse_matching = [
            e
            for e in self._entries
            if e.from_currency == t and e.to_currency == f and e.as_of <= as_of
        ]
        if inverse_matching:
            return 1.0 / inverse_matching[-1].rate

        raise DataContractError(
            f"No foreign exchange rate found between {f} and {t} as of {as_of}.",
            code="FX_RATE_NOT_FOUND",
            details={"from_currency": f.value, "to_currency": t.value, "as_of": str(as_of)},
        )


_DEFAULT_TABLE = FXRateTable()


def convert_currency(
    amount: float,
    from_curr: Currency | str,
    to_curr: Currency | str,
    as_of: date,
    rate_table: FXRateTable | None = None,
) -> float:
    """Convert an amount from one currency to another using historical as-of FX rates.

    Args:
        amount: Non-negative payment amount.
        from_curr: Originating currency.
        to_curr: Target currency.
        as_of: Date of the observation.
        rate_table: Custom FX rate table or default RBI reference series.

    Returns:
        Converted amount in target currency.
    """
    if amount < 0.0 or math.isnan(amount) or math.isinf(amount):
        raise DataContractError(
            f"Cannot convert invalid amount: {amount}.",
            code="INVALID_PAY_AMOUNT",
            details={"amount": amount},
        )

    table = rate_table or _DEFAULT_TABLE
    rate = table.get_rate(from_curr, to_curr, as_of)
    return amount * rate


def enforce_market_isolation(
    source_country: str,
    target_market: str = "IN",
) -> None:
    """Enforce Rule R-MD-08: Cross-Market Isolation.

    US and other foreign compensation observations must NEVER be converted
    at nominal FX and directly pooled with domestic Indian tech training datasets.
    """
    if source_country.upper() != target_market.upper() and target_market.upper() == "IN":
        raise DataContractError(
            f"Violation of Rule R-MD-08: Data from market '{source_country}' cannot be "
            f"directly converted and pooled into Indian market ('{target_market}') training set.",
            code="R_MD_08_MARKET_ISOLATION_VIOLATION",
            details={"source_country": source_country, "target_market": target_market},
        )
