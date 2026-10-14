"""CompIntel Canonical Schema Package (Rules R-DA-03, R-DA-04, R-MD-07)."""

from compintel.schema.canonical import (
    CURRENT_SCHEMA_VERSION,
    CompensationObservation,
    canonical_dataframe_schema,
    validate_observations_df,
)
from compintel.schema.entities import (
    CoverageCell,
    QuarantineRecord,
    RawRecord,
    SourceManifest,
)
from compintel.schema.enums import (
    CompensationMeasure,
    Currency,
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    QuarantineReason,
    RoleFamily,
    SeniorityLevel,
    TaxBasis,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "CompensationMeasure",
    "CompensationObservation",
    "CoverageCell",
    "Currency",
    "MetroLocation",
    "PayPeriod",
    "ProvenanceTier",
    "QuarantineReason",
    "QuarantineRecord",
    "RawRecord",
    "RoleFamily",
    "SeniorityLevel",
    "SourceManifest",
    "TaxBasis",
    "canonical_dataframe_schema",
    "validate_observations_df",
]
