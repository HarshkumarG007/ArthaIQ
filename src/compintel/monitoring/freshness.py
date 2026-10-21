"""Source data freshness and staleness monitoring (PRD NFR-11, US-08).

Monitors the age of the newest observation from each approved data source against
statutory freshness SLAs (e.g. 365 days max observation age).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FreshnessStatus = Literal["FRESH", "WARNING", "STALE"]

DEFAULT_SOURCE_SLA_DAYS: float = 365.0
WARNING_SLA_RATIO: float = 0.75


class FreshnessReport(BaseModel):
    """Evaluation result for freshness of an individual data source."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    source_id: str = Field(..., description="Approved data source identifier.")
    latest_observation_date: datetime = Field(..., description="Most recent record timestamp.")
    as_of_date: datetime = Field(..., description="Evaluation baseline timestamp.")
    age_days: float = Field(..., description="Calculated age of the newest record in days.")
    sla_days: float = Field(..., description="Maximum allowed freshness SLA in days.")
    status: FreshnessStatus = Field(..., description="Freshness evaluation status.")
    description: str = Field(..., description="Human-readable explanation of freshness status.")


def evaluate_freshness(
    source_id: str,
    latest_date: datetime,
    sla_days: float = DEFAULT_SOURCE_SLA_DAYS,
    as_of: datetime | None = None,
) -> FreshnessReport:
    """Evaluate observation staleness against source SLAs.

    Args:
        source_id: Data source identifier.
        latest_date: Timestamp of newest observation in dataset.
        sla_days: Allowed age in days before source is marked stale (default: 365).
        as_of: Evaluation reference timestamp (defaults to current UTC).

    Returns:
        FreshnessReport: Structured report with staleness assessment.
    """
    if as_of is None:
        as_of = datetime.now(UTC)

    # Ensure timezone awareness
    if latest_date.tzinfo is None:
        latest_date = latest_date.replace(tzinfo=UTC)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    age_seconds = max(0.0, (as_of - latest_date).total_seconds())
    age_days = round(age_seconds / 86400.0, 1)

    warning_threshold = sla_days * WARNING_SLA_RATIO

    if age_days >= sla_days:
        status: FreshnessStatus = "STALE"
        desc = (
            f"Source {source_id} is stale: newest record is {age_days} days old, "
            f"exceeding the SLA of {sla_days} days."
        )
    elif age_days >= warning_threshold:
        status = "WARNING"
        desc = (
            f"Source {source_id} approaching staleness: newest record is {age_days} days old "
            f"(warning threshold: {warning_threshold:.1f} days)."
        )
    else:
        status = "FRESH"
        desc = f"Source {source_id} is fresh: age {age_days} days is within {sla_days} days SLA."

    return FreshnessReport(
        source_id=source_id,
        latest_observation_date=latest_date,
        as_of_date=as_of,
        age_days=age_days,
        sla_days=sla_days,
        status=status,
        description=desc,
    )
