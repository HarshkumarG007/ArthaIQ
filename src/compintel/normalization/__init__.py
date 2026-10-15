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
from compintel.normalization.levels import (
    DEFAULT_LEVEL_MAPPING_VERSION,
    LevelAmbiguityAudit,
    LevelMappingResult,
    map_level,
    normalize_levels_df,
)
from compintel.normalization.titles import (
    DEFAULT_TAXONOMY_VERSION,
    TitleMappingResult,
    normalize_title,
    normalize_titles_df,
    sanitize_title,
)

__all__ = [
    "CPITable",
    "DEFAULT_LEVEL_MAPPING_VERSION",
    "DEFAULT_TAXONOMY_VERSION",
    "FXRateTable",
    "LevelAmbiguityAudit",
    "LevelMappingResult",
    "TitleMappingResult",
    "adjust_for_cpi",
    "annualize",
    "convert_currency",
    "deannualize",
    "enforce_market_isolation",
    "from_lpa",
    "get_annualization_factor",
    "map_level",
    "normalize_levels_df",
    "normalize_title",
    "normalize_titles_df",
    "sanitize_title",
    "to_lpa",
]
