"""Connector interface and concrete source connectors for raw data ingestion.

Governs Rule R-DA-01 (Licence gate), R-DA-02 (Immutable raw zone with manifests),
and R-DA-03 (Raw companion preservation).
"""

from __future__ import annotations

import csv
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl
import yaml

from compintel.ingestion.manifest import (
    verify_licence_gate,
    verify_manifest,
)
from compintel.schema.entities import RawRecord

if TYPE_CHECKING:
    from collections.abc import Iterator


def find_repo_root(start_path: Path | None = None) -> Path:
    """Find repository root by looking for pyproject.toml."""
    curr = (start_path or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return curr


def compute_record_hash(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of a raw record payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


class BaseConnector(ABC):
    """Abstract base class for all data ingestion connectors (Rules R-DA-01, R-DA-02).

    Enforces that every connector:
    1. Verifies its licence against config/sources/<id>.yaml before reading data.
    2. Validates raw file checksums against manifest.yaml to ensure immutability.
    3. Emits immutable RawRecord entities with deterministic SHA-256 payloads.
    """

    source_id: str

    def __init__(
        self,
        raw_dir: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve() if repo_root else find_repo_root()
        self.raw_dir = raw_dir.resolve() if raw_dir else self.repo_root / "data" / "raw"

    @property
    def source_raw_dir(self) -> Path:
        """Directory path containing raw data files for this source."""
        return self.raw_dir / self.source_id

    @property
    def manifest_path(self) -> Path:
        """Path to manifest.yaml for this source."""
        return self.source_raw_dir / "manifest.yaml"

    def verify_licence(self) -> dict[str, Any]:
        """Verify licence status for this connector's source.

        Raises LicenceViolationError (LicenceGateError) if blocked or unapproved.
        """
        return verify_licence_gate(self.source_id, self.repo_root)

    def verify_manifest(self) -> bool:
        """Verify SHA-256 checksums and immutability for this connector's raw files.

        Raises FileNotFoundError if manifest is missing.
        Raises ChecksumMismatchError if any raw file was tampered with.
        """
        if not self.manifest_path.exists():
            msg = f"Manifest not found for source {self.source_id} at {self.manifest_path}"
            raise FileNotFoundError(msg)
        return verify_manifest(self.manifest_path)

    @abstractmethod
    def extract_raw_records(self) -> Iterator[RawRecord]:
        """Extract and stream immutable RawRecord instances from the raw source."""

    def to_raw_dataframe(self) -> pl.DataFrame:
        """Collect all extracted RawRecord entities into a Polars DataFrame."""
        records = list(self.extract_raw_records())
        if not records:
            return pl.DataFrame(
                schema={
                    "source_id": pl.String,
                    "source_version": pl.String,
                    "license_id": pl.String,
                    "retrieved_at": pl.Datetime("us", "UTC"),
                    "record_hash": pl.String,
                    "raw_payload": pl.String,
                }
            )

        data = [
            {
                "source_id": r.source_id,
                "source_version": r.source_version,
                "license_id": r.license_id,
                "retrieved_at": r.retrieved_at,
                "record_hash": r.record_hash,
                "raw_payload": json.dumps(r.raw_payload, sort_keys=True),
            }
            for r in records
        ]
        return pl.DataFrame(data)


class CorporateDisclosuresConnector(BaseConnector):
    """Connector for BSE / NSE Listed IT Firm Statutory Annual Filings (SRC-SUP-CORP-01).

    Measures Median Remuneration of Employees (MRE) under Section 197(12) of Companies Act 2013.
    """

    source_id: str = "SRC-SUP-CORP-01"
    data_file_name: str = "listed_it_mre_fy24.csv"

    def extract_raw_records(self) -> Iterator[RawRecord]:
        """Extract RawRecord stream from corporate remuneration filings."""
        # Step 1: Licence Gate (Rule R-DA-01)
        config = self.verify_licence()

        # Step 2: Manifest & Checksum Verification (Rule R-DA-02)
        self.verify_manifest()

        data_file = self.source_raw_dir / self.data_file_name
        if not data_file.exists():
            msg = f"Raw data file not found: {data_file}"
            raise FileNotFoundError(msg)

        # Retrieve metadata
        ref_period = config.get("reference_period", {})
        source_version = str(ref_period.get("fiscal_year", "FY2023-24"))
        licence_meta = config.get("licence", {})
        license_id = str(licence_meta.get("spdx_id", "STATUTORY-PUBLIC-DISCLOSURE"))

        # Ingestion timestamp from manifest if available
        retrieved_at = datetime.now(UTC)
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, encoding="utf-8") as f:
                    manifest_data = yaml.safe_load(f)
                if isinstance(manifest_data, dict) and "generated_at_utc" in manifest_data:
                    retrieved_at = datetime.fromisoformat(manifest_data["generated_at_utc"])
            except Exception:
                pass

        # Step 3: Stream and parse CSV records preserving all raw companion columns (Rule R-DA-03)
        with open(data_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_payload = dict(row)
                record_hash = compute_record_hash(raw_payload)
                yield RawRecord(
                    source_id=self.source_id,
                    source_version=source_version,
                    license_id=license_id,
                    retrieved_at=retrieved_at,
                    raw_payload=raw_payload,
                    record_hash=record_hash,
                )


# Master registry mapping approved source IDs to connector implementations
CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "SRC-SUP-CORP-01": CorporateDisclosuresConnector,
}


def get_connector(
    source_id: str,
    raw_dir: Path | None = None,
    repo_root: Path | None = None,
) -> BaseConnector:
    """Factory retrieving an instantiated connector for an approved source ID.

    Raises LicenceViolationError if the source is unapproved.
    Raises ValueError if no connector is registered for the approved source.
    """
    root = repo_root.resolve() if repo_root else find_repo_root()
    # Always enforce licence gate check
    verify_licence_gate(source_id, root)

    connector_cls = CONNECTOR_REGISTRY.get(source_id)
    if connector_cls is None:
        msg = f"No connector implementation registered for source '{source_id}'."
        raise ValueError(msg)

    return connector_cls(raw_dir=raw_dir, repo_root=root)
