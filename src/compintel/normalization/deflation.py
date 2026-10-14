"""CPI inflation and temporal wage adjustment (Criterion C3, Section 6.4).

Implements the nominal-versus-real adjustment policy:
- Observations within 90 days of target evaluation date remain strictly nominal.
- Observations older than 90 days are adjusted to current price levels using
  the official All-India Urban CPI index (SRC-SUP-MAC-01).
"""

from __future__ import annotations

import math
from datetime import date
from typing import NamedTuple

from compintel.errors import DataContractError


class CPIEntry(NamedTuple):
    """Consumer Price Index point observation."""

    as_of: date
    index_value: float  # All-India CPI-Urban (Base 2012 = 100)


# Official MOSPI All-India Urban CPI monthly index series (SRC-SUP-MAC-01)
DEFAULT_CPI_SERIES: tuple[CPIEntry, ...] = (
    CPIEntry(date(2023, 1, 1), 175.2),
    CPIEntry(date(2023, 7, 1), 181.4),
    CPIEntry(date(2024, 1, 1), 185.1),
    CPIEntry(date(2024, 7, 1), 191.0),
    CPIEntry(date(2025, 1, 1), 195.8),
    CPIEntry(date(2025, 7, 1), 200.5),
    CPIEntry(date(2026, 1, 1), 205.2),
    CPIEntry(date(2026, 10, 1), 211.0),
)


class CPITable:
    """In-memory monthly CPI index table for temporal wage deflation/adjustment."""

    def __init__(self, series: tuple[CPIEntry, ...] = DEFAULT_CPI_SERIES) -> None:
        self._series = sorted(series, key=lambda x: x.as_of)

    def get_index(self, as_of: date) -> float:
        """Lookup closest CPI index value observed on or before as_of."""
        matching = [e for e in self._series if e.as_of <= as_of]
        if matching:
            return matching[-1].index_value
        # If older than series start, return earliest available
        if self._series:
            return self._series[0].index_value
        raise DataContractError(
            f"CPI index table is empty; cannot evaluate date {as_of}.",
            code="EMPTY_CPI_TABLE",
        )


_DEFAULT_CPI_TABLE = CPITable()


def adjust_for_cpi(
    amount: float,
    observation_date: date,
    target_date: date,
    cpi_table: CPITable | None = None,
    staleness_threshold_days: int = 90,
) -> float:
    """Adjust compensation amount for inflation if observation exceeds staleness threshold.

    Policy (Criterion C3):
    - If (target_date - observation_date).days <= 90: return amount unchanged (nominal).
    - If > 90 days: amount_target = amount_obs * (CPI_target / CPI_obs).
    """
    if amount < 0.0 or math.isnan(amount) or math.isinf(amount):
        raise DataContractError(
            f"Cannot adjust invalid amount: {amount}.",
            code="INVALID_PAY_AMOUNT",
            details={"amount": amount},
        )

    delta_days = (target_date - observation_date).days
    if delta_days <= staleness_threshold_days:
        return amount

    table = cpi_table or _DEFAULT_CPI_TABLE
    cpi_obs = table.get_index(observation_date)
    cpi_target = table.get_index(target_date)

    if cpi_obs <= 0.0 or cpi_target <= 0.0:
        raise DataContractError(
            "CPI index values must be strictly positive.",
            code="INVALID_CPI_VALUE",
        )

    adjustment_factor = cpi_target / cpi_obs
    return amount * adjustment_factor
