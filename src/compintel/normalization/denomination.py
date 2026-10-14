"""Currency denomination and unit scaling normalization (T1.02, T3.05).

Normalizes between raw nominal INR and Indian Lakhs Per Annum (LPA).
1.0 LPA = 100,000 INR.
"""

from __future__ import annotations

import math

from compintel.errors import DataContractError

INR_PER_LAKH: float = 100_000.0


def to_lpa(inr_amount: float) -> float:
    """Convert nominal INR to Lakhs Per Annum (LPA).

    Example:
        1,850,000 INR -> 18.5 LPA
    """
    if inr_amount < 0.0 or math.isnan(inr_amount) or math.isinf(inr_amount):
        raise DataContractError(
            f"Cannot convert invalid INR amount to LPA: {inr_amount}.",
            code="INVALID_DENOMINATION_AMOUNT",
            details={"inr_amount": inr_amount},
        )
    return inr_amount / INR_PER_LAKH


def from_lpa(lpa_amount: float) -> float:
    """Convert Lakhs Per Annum (LPA) back to nominal INR.

    Guarantees round-trip: from_lpa(to_lpa(x)) == x.
    """
    if lpa_amount < 0.0 or math.isnan(lpa_amount) or math.isinf(lpa_amount):
        raise DataContractError(
            f"Cannot convert invalid LPA amount to INR: {lpa_amount}.",
            code="INVALID_DENOMINATION_AMOUNT",
            details={"lpa_amount": lpa_amount},
        )
    return lpa_amount * INR_PER_LAKH
