"""Supporting data entities and pipeline boundary records (Rules R-DA-02, R-DA-05).

Defines RawRecord, QuarantineRecord, SourceManifest, and CoverageCell entities
used throughout ingestion, quality reconciliation, and validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from compintel.schema.enums import (
    MetroLocation,
    ProvenanceTier,
    QuarantineReason,
    RoleFamily,
    SeniorityLevel,
)


class RawRecord(BaseModel):
    """Raw record captured at connector boundary before normalization (Rule R-DA-02)."""

    source_id: str = Field(description="Unique source identifier (e.g. SRC-INT-VOL-01)")
    source_version: str = Field(description="Source data version or retrieval timestamp")
    license_id: str = Field(description="SPDX license ID or proprietary consent reference")
    retrieved_at: datetime = Field(description="UTC timestamp of raw ingestion")
    raw_payload: dict[str, Any] = Field(description="Original un-normalized key-value payload")
    record_hash: str = Field(description="SHA-256 hash of raw payload bytes")


class QuarantineRecord(BaseModel):
    """Quarantine entry preserving non-qualifying records with reason codes (Rule R-DA-05)."""

    quarantine_id: str = Field(description="Unique deterministic quarantine identifier")
    source_id: str = Field(description="Originating source identifier")
    quarantine_reason: QuarantineReason = Field(description="Deterministic exclusion reason code")
    exclusion_details: str = Field(description="Human-readable explanation of rejection")
    raw_payload: dict[str, Any] = Field(description="Snapshot of original raw record")
    quarantined_at: datetime = Field(description="Timestamp when quarantine was applied")


class SourceManifest(BaseModel):
    """Integrity manifest accompanying raw source datasets (Rule R-DA-02)."""

    source_id: str = Field(description="Source identifier matching config/sources/<id>.yaml")
    source_name: str = Field(description="Human-readable name of the dataset")
    version: str = Field(description="Version string or snapshot date")
    license_spdx: str = Field(description="Approved license identifier")
    provenance_tier: ProvenanceTier = Field(description="SQSF evidence tier")
    retrieved_at: datetime = Field(description="Retrieval timestamp")
    sha256_checksum: str = Field(description="SHA-256 hash of raw data file")
    row_count: int = Field(ge=0, description="Total observations in the raw file")
    file_format: str = Field(description="Format (csv, parquet, json, zip)")


class CoverageCell(BaseModel):
    """Cell identifier in the 84-cell evaluation space (ADR-0001, T2.01)."""

    role_family: RoleFamily
    location: MetroLocation
    seniority: SeniorityLevel

    @property
    def cell_id(self) -> str:
        """Standard formatted string identifier: ROLE.LOCATION.SENIORITY."""
        return f"{self.role_family.value}.{self.location.value}.{self.seniority.value}"

    @property
    def is_core_cell(self) -> bool:
        """Check if cell belongs to the 12 core cells (Bengaluru/Hyderabad x JR/MID/SR/STAFF)."""
        return (
            self.role_family == RoleFamily.SWE
            and self.location in (MetroLocation.BENGALURU, MetroLocation.HYDERABAD)
            and self.seniority
            in (
                SeniorityLevel.JR,
                SeniorityLevel.MID,
                SeniorityLevel.SR,
                SeniorityLevel.STAFF,
            )
        )
