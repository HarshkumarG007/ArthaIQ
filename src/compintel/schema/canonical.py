"""Canonical schema specification and contracts for CompIntel (Rules R-DA-03, R-DA-04, R-MD-07).

Defines the Pydantic CompensationObservation model and the Pandera Polars
DataFrameSchema governing all canonical observations admitted into the pipeline.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandera.polars as pa
import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from compintel.errors import DataContractError
from compintel.schema.enums import (
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    QuarantineReason,
    RoleFamily,
    SeniorityLevel,
    TaxBasis,
)

CURRENT_SCHEMA_VERSION = "1.0.0"


class CompensationObservation(BaseModel):
    """Canonical observation entity representing an individual compensation datapoint.

    Adheres strictly to:
    - Rule R-DA-03: Raw values preserved beside normalized ones.
    - Rule R-DA-04: Mandatory provenance metadata attached to every record.
    - Rule R-MD-07: Anti-heuristic unbundling (bundled CTC without itemization cannot have
      guaranteed_cash_annual populated).
    - Rule R-MD-11: Synthetic data flagged with is_synthetic = True.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )

    # 1. Identification & Metadata (Rule R-DA-04)
    observation_id: str = Field(
        ...,
        min_length=1,
        description="Deterministic unique observation identifier (UUID or SHA-256 hash).",
    )
    source_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of originating source matching config/sources/<id>.yaml.",
    )
    source_version: str = Field(
        ...,
        min_length=1,
        description="Source dataset version or ingestion snapshot timestamp.",
    )
    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Canonical schema semver string.",
    )
    license_id: str = Field(
        ...,
        min_length=1,
        description="Approved SPDX license identifier or consent reference (Rule R-DA-01).",
    )
    provenance_tier: ProvenanceTier = Field(
        ...,
        description="Source Quality Scoring Framework (SQSF) evidence tier.",
    )
    as_of_date: date = Field(
        ...,
        description="Effective date of the compensation event or survey observation.",
    )
    ingested_at: datetime = Field(
        ...,
        description="UTC timestamp when the record was ingested into the pipeline.",
    )
    is_synthetic: bool = Field(
        default=False,
        description="Flag indicating synthetic test fixture data (Rule R-MD-11).",
    )

    # 2. Profile & Occupational Categorization (ADR-0001)
    role_family: RoleFamily = Field(
        ...,
        description="Canonical technical role family (SWE, DATA, MLAI, OTHER).",
    )
    canonical_title: str = Field(
        ...,
        min_length=1,
        description="Standardized occupation title mapped from taxonomy (T3.08).",
    )
    raw_title: str = Field(
        ...,
        min_length=1,
        description="Original un-normalized job title from source (Rule R-DA-03).",
    )
    seniority: SeniorityLevel = Field(
        ...,
        description="Standardized seniority level (JR, MID, SR, STAFF, PRINCIPAL, OTHER).",
    )
    location: MetroLocation = Field(
        ...,
        description="Standardized metro tech hub location (ADR-0001).",
    )
    raw_location: str = Field(
        ...,
        min_length=1,
        description="Original un-normalized location string from source (Rule R-DA-03).",
    )
    years_experience: float | None = Field(
        default=None,
        ge=0.0,
        le=50.0,
        description="Total relevant professional experience in years.",
    )
    education_level: str | None = Field(
        default=None,
        description="Highest attained educational qualification if reported.",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of standardized technical skill tokens associated with observation.",
    )

    # 3. Canonical Target Measures in Nominal INR LPA (ADR-0002, T1.02)
    # Primary Target PT1 / PT2
    guaranteed_cash_annual: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Contractual guaranteed annual cash in nominal INR LPA "
            "(Basic + HRA + Special Allowance). Strict primary target for PT1."
        ),
    )
    # Unbundled itemized components (LPA)
    basic_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Annualized statutory basic pay in INR LPA.",
    )
    hra_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Annualized house rent allowance in INR LPA.",
    )
    special_allowance_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Annualized supplementary / special allowance in INR LPA.",
    )
    fixed_allowances_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Other contractual recurring fixed cash allowances in INR LPA.",
    )
    variable_cash_annual: float | None = Field(
        default=None,
        ge=0.0,
        description="Target annual performance incentive / bonus in INR LPA.",
    )
    signon_bonus_cash: float | None = Field(
        default=None,
        ge=0.0,
        description="One-time upfront joining bonus in INR LPA.",
    )
    equity_annual_val: float | None = Field(
        default=None,
        ge=0.0,
        description="Annualized equity / RSU grant value in INR LPA.",
    )
    total_comp_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Total direct compensation (Cash + Equity + Variable) in INR LPA.",
    )
    ctc_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Cost-to-Company aggregate headline compensation in INR LPA.",
    )
    take_home_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Net deposited take-home cash in INR LPA.",
    )
    advertised_min_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Advertised minimum salary from job posting in INR LPA (PT3).",
    )
    advertised_max_annual: float | None = Field(
        default=None,
        gt=0.0,
        description="Advertised maximum salary from job posting in INR LPA (PT3).",
    )

    # 4. Companion Raw Fields Preserved (Rule R-DA-03)
    raw_pay_amount: float = Field(
        ...,
        gt=0.0,
        description="Original numeric pay value before normalization (Rule R-DA-03).",
    )
    raw_currency: str = Field(
        ...,
        min_length=1,
        description="Original currency denomination string (Rule R-DA-03).",
    )
    raw_pay_period: PayPeriod = Field(
        ...,
        description="Original payment frequency (annual, monthly, hourly).",
    )
    raw_tax_basis: TaxBasis = Field(
        default=TaxBasis.GROSS_PRETAX,
        description="Original tax basis of reported figure.",
    )

    # 5. Quality, Quarantine, and Integrity Flags
    is_unbundled_aggregate: bool = Field(
        default=False,
        description="True if record is bundled CTC without itemized line items (Rule R-MD-07).",
    )
    quarantine_status: bool = Field(
        default=False,
        description="True if record is quarantined from model training (Rule R-DA-05).",
    )
    quarantine_reason: QuarantineReason | None = Field(
        default=None,
        description="Deterministic rejection reason code if quarantined.",
    )

    # 6. Longitudinal Career Progression (ADR-0008 Amendment, Task T13.04)
    career_start_date: date | None = Field(
        default=None,
        description="Optional date contributor began professional technology career.",
    )
    last_promotion_date: date | None = Field(
        default=None,
        description="Optional date of contributor's last level change or promotion.",
    )
    right_censored_exit_flag: bool | None = Field(
        default=None,
        description="Optional flag: True if record marks role exit, False/None if continuing.",
    )

    @field_validator("observation_id", "source_id", "canonical_title", "raw_title", "raw_location")
    @classmethod
    def validate_non_blank_strings(cls, v: str) -> str:
        """Reject empty or whitespace-only string identifiers."""
        if not v.strip():
            raise ValueError("String field cannot be empty or whitespace only.")
        return v.strip()

    @model_validator(mode="after")
    def validate_invariants(self) -> CompensationObservation:
        """Enforce architectural and quality invariants across fields."""
        # Rule R-MD-07: Anti-heuristic unbundling
        # If record is an unbundled aggregate CTC, it CANNOT populate guaranteed_cash_annual
        if self.is_unbundled_aggregate and self.guaranteed_cash_annual is not None:
            raise DataContractError(
                "Violation of Rule R-MD-07: Bundled aggregate CTC (is_unbundled_aggregate=True) "
                "cannot populate guaranteed_cash_annual without itemized verification.",
                code="R_MD_07_CTC_UNBUNDLING_VIOLATION",
                details={
                    "observation_id": self.observation_id,
                    "source_id": self.source_id,
                    "guaranteed_cash_annual": self.guaranteed_cash_annual,
                },
            )

        # Quarantine status consistency
        if self.quarantine_status and self.quarantine_reason is None:
            raise DataContractError(
                "Quarantined observation must have a deterministic quarantine_reason code.",
                code="MISSING_QUARANTINE_REASON",
                details={"observation_id": self.observation_id},
            )

        # Advertised range bounds (PT3)
        if (
            self.advertised_min_annual is not None
            and self.advertised_max_annual is not None
            and self.advertised_min_annual > self.advertised_max_annual
        ):
            raise DataContractError(
                f"advertised_min_annual ({self.advertised_min_annual}) cannot exceed "
                f"advertised_max_annual ({self.advertised_max_annual}).",
                code="INVALID_ADVERTISED_RANGE",
                details={"observation_id": self.observation_id},
            )

        # Longitudinal career event ordering (Task T13.04)
        if (
            self.career_start_date is not None
            and self.last_promotion_date is not None
            and self.last_promotion_date < self.career_start_date
        ):
            raise DataContractError(
                f"last_promotion_date ({self.last_promotion_date}) cannot precede "
                f"career_start_date ({self.career_start_date}).",
                code="INVALID_LONGITUDINAL_DATES",
                details={
                    "observation_id": self.observation_id,
                    "career_start_date": str(self.career_start_date),
                    "last_promotion_date": str(self.last_promotion_date),
                },
            )

        return self

    @classmethod
    def from_record(cls, data: dict[str, Any]) -> CompensationObservation:
        """Create CompensationObservation with automatic DataContractError wrapping."""
        try:
            return cls(**data)
        except Exception as exc:
            if isinstance(exc, DataContractError):
                raise
            raise DataContractError(
                f"Failed to instantiate canonical CompensationObservation: {exc}",
                code="SCHEMA_VALIDATION_ERROR",
                details={"raw_data": str(data)},
            ) from exc


# ---------------------------------------------------------------------------
# Pandera DataFrameSchema for Bulk Polars Validation
# ---------------------------------------------------------------------------

canonical_dataframe_schema = pa.DataFrameSchema(
    columns={
        "observation_id": pa.Column(pl.String, nullable=False),
        "source_id": pa.Column(pl.String, nullable=False),
        "source_version": pa.Column(pl.String, nullable=False),
        "schema_version": pa.Column(pl.String, nullable=False),
        "license_id": pa.Column(pl.String, nullable=False),
        "provenance_tier": pa.Column(pl.String, nullable=False),
        "as_of_date": pa.Column(pl.Date, nullable=False),
        "ingested_at": pa.Column(pl.Datetime, nullable=False),
        "is_synthetic": pa.Column(pl.Boolean, nullable=False),
        "role_family": pa.Column(pl.String, nullable=False),
        "canonical_title": pa.Column(pl.String, nullable=False),
        "raw_title": pa.Column(pl.String, nullable=False),
        "seniority": pa.Column(pl.String, nullable=False),
        "location": pa.Column(pl.String, nullable=False),
        "raw_location": pa.Column(pl.String, nullable=False),
        "years_experience": pa.Column(pl.Float64, pa.Check.ge(0.0), nullable=True),
        "guaranteed_cash_annual": pa.Column(pl.Float64, pa.Check.gt(0.0), nullable=True),
        "raw_pay_amount": pa.Column(pl.Float64, pa.Check.gt(0.0), nullable=False),
        "raw_currency": pa.Column(pl.String, nullable=False),
        "raw_pay_period": pa.Column(pl.String, nullable=False),
        "is_unbundled_aggregate": pa.Column(pl.Boolean, nullable=False),
        "quarantine_status": pa.Column(pl.Boolean, nullable=False),
        "career_start_date": pa.Column(pl.Date, nullable=True, required=False),
        "last_promotion_date": pa.Column(pl.Date, nullable=True, required=False),
        "right_censored_exit_flag": pa.Column(pl.Boolean, nullable=True, required=False),
    },
    strict=False,
    coerce=True,
)


def validate_observations_df(df: pl.DataFrame) -> pl.DataFrame:
    """Validate a Polars DataFrame against the canonical schema contract.

    Raises DataContractError if schema check fails.
    """
    try:
        validated_df: pl.DataFrame = canonical_dataframe_schema.validate(df)
        return validated_df
    except Exception as exc:
        raise DataContractError(
            f"Polars DataFrame failed canonical schema validation: {exc}",
            code="DATAFRAME_CONTRACT_ERROR",
            details={"error_type": exc.__class__.__name__},
        ) from exc
