"""Canonical compensation enums and taxonomy constants (Rule R-CD-05).

Defines standard categories, currencies, roles, seniority, and quarantine
reason codes used across canonical schema, ingestion, and models.
"""

from __future__ import annotations

from enum import StrEnum


class RoleFamily(StrEnum):
    """Core occupational role families in scope (ADR-0001)."""

    SWE = "SWE"  # Software Engineering
    DATA = "DATA"  # Data Science, Analytics & Engineering
    MLAI = "MLAI"  # Machine Learning & AI Engineering
    OTHER = "OTHER"  # Out-of-scope or adjacent technical roles


class SeniorityLevel(StrEnum):
    """Standardized seniority tiers mapped from industry titles (T1.02, T3.09)."""

    JR = "JR"  # Entry / Junior (0-2 years typical)
    MID = "MID"  # Mid-level IC (3-5 years typical)
    SR = "SR"  # Senior IC (6-9 years typical)
    STAFF = "STAFF"  # Staff / Principal IC (10+ years typical)
    PRINCIPAL = "PRINCIPAL"  # Principal / Distinguished / Fellow (15+ years)
    OTHER = "OTHER"  # Unmapped or ambiguous seniority


class MetroLocation(StrEnum):
    """Geographic tier-1 Indian tech hubs and other locations (ADR-0001)."""

    BENGALURU = "BENGALURU"
    HYDERABAD = "HYDERABAD"
    PUNE = "PUNE"
    MUMBAI = "MUMBAI"
    NCR = "NCR"  # Delhi, Gurgaon, Noida
    CHENNAI = "CHENNAI"
    OTHER = "OTHER"  # Non-metro or global locations


class CompensationMeasure(StrEnum):
    """Admissible compensation line items and measures (ADR-0002, T1.02)."""

    GUARANTEED_CASH_ANNUAL = "guaranteed_cash_annual"  # Primary PT1/PT2 target (INR LPA)
    BASIC_ANNUAL = "basic_annual"  # Statutory basic pay
    HRA_ANNUAL = "hra_annual"  # House rent allowance
    SPECIAL_ALLOWANCE_ANNUAL = "special_allowance_annual"  # Special / supplementary allowance
    FIXED_ALLOWANCES_ANNUAL = "fixed_allowances_annual"  # Other contractual fixed cash
    VARIABLE_CASH_ANNUAL = "variable_cash_annual"  # Target performance bonus / STI
    SIGNON_BONUS_CASH = "signon_bonus_cash"  # One-time joining incentive
    EQUITY_ANNUAL_VAL = "equity_annual_val"  # Annualized stock/RSU value
    TOTAL_COMP_ANNUAL = "total_comp_annual"  # Comprehensive CTC/TDC sum
    CTC_ANNUAL = "ctc_annual"  # Bundled Cost-to-Company (quarantined from PT1)
    TAKE_HOME_ANNUAL = "take_home_annual"  # Post-tax deposited cash (quarantined)
    ADVERTISED_RANGE_ANNUAL = "advertised_range_annual"  # Job board pay span (PT3)


class PayPeriod(StrEnum):
    """Payment frequencies admissible before annualization normalization."""

    ANNUAL = "annual"
    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    HOURLY = "hourly"
    UNKNOWN = "unknown"


class Currency(StrEnum):
    """Supported currency codes."""

    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    SGD = "SGD"
    CAD = "CAD"
    OTHER = "OTHER"


class TaxBasis(StrEnum):
    """Tax basis of the compensation observation."""

    GROSS_PRETAX = "gross_pretax"  # Default canonical standard
    NET_POSTTAX = "net_posttax"  # Take-home pay


class ProvenanceTier(StrEnum):
    """Source Quality Scoring Framework (SQSF) evidence tier (T1.10)."""

    TIER_A = "A"  # Official population benchmarks & verified payslips (SQS >= 80)
    TIER_B = "B"  # Statutory corporate disclosures & employer syndication (65 <= SQS < 80)
    TIER_C = "C"  # Open public developer surveys (50 <= SQS < 65)
    TIER_D = "D"  # Unverified job board ranges (SQS < 50)


class QuarantineReason(StrEnum):
    """Deterministic reason codes for observation quarantine (Rule R-DA-05)."""

    MISSING_PAY = "missing_pay"
    MISSING_EXPERIENCE = "missing_experience"
    CURRENCY_MISMATCH = "currency_mismatch"
    NON_FULLTIME = "non_fulltime"
    GEO_OUT_OF_SCOPE = "geo_out_of_scope"
    NON_TECH_ROLE = "non_tech_role"
    UNBUNDLED_AGGREGATE = "unbundled_aggregate"  # Rule R-MD-07
    ENTERPRISE_AGGREGATE = "enterprise_aggregate"
    OUTLIER = "outlier"
    DUPLICATE = "duplicate"
    SCHEMA_VIOLATION = "schema_violation"
    UNAPPROVED_SOURCE = "unapproved_source"
    AMBIGUOUS_LABEL = "ambiguous_label"
