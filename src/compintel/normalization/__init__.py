"""CompIntel Normalization Package (Rules R-DA-03, R-MD-07, R-MD-08)."""

from compintel.normalization.annualization import (
    annualize,
    deannualize,
    get_annualization_factor,
)
from compintel.normalization.currency import (
    FXRateTable,
    convert_currency,
    enforce_market_isolation,
)
from compintel.normalization.deflation import (
    CPITable,
    adjust_for_cpi,
)
from compintel.normalization.denomination import (
    from_lpa,
    to_lpa,
)

__all__ = [
    "CPITable",
    "FXRateTable",
    "adjust_for_cpi",
    "annualize",
    "convert_currency",
    "deannualize",
    "enforce_market_isolation",
    "from_lpa",
    "get_annualization_factor",
    "to_lpa",
]
