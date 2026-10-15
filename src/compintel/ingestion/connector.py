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
    normalized_payload = {str(k): v for k, v in payload.items()}
    serialized = json.dumps(normalized_payload, sort_keys=True, default=str).encode("utf-8")
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

    def get_manifest_retrieved_at(self) -> datetime:
        """Read retrieved_at / generated_at_utc timestamp from manifest or fallback to now."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, encoding="utf-8") as f:
                    manifest_data = yaml.safe_load(f)
                if isinstance(manifest_data, dict) and "generated_at_utc" in manifest_data:
                    return datetime.fromisoformat(manifest_data["generated_at_utc"])
            except Exception:
                pass
        return datetime.now(UTC)

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
        retrieved_at = self.get_manifest_retrieved_at()

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


class RBIMacroConnector(BaseConnector):
    """Connector for Reserve Bank of India DBIE Macro Series (SRC-SUP-MAC-01).

    Streams CPI Urban monthly index and INR/USD daily exchange rates.
    """

    source_id: str = "SRC-SUP-MAC-01"
    cpi_file_name: str = "cpi_urban_monthly.csv"
    fx_file_name: str = "inr_usd_fx_daily.csv"

    def extract_raw_records(self) -> Iterator[RawRecord]:
        """Extract RawRecord stream from RBI DBIE macro series."""
        config = self.verify_licence()
        self.verify_manifest()

        licence_meta = config.get("licence", {})
        license_id = str(licence_meta.get("spdx_id", "OGDL-IN"))
        retrieved_at = self.get_manifest_retrieved_at()

        # 1. CPI Urban Monthly
        cpi_path = self.source_raw_dir / self.cpi_file_name
        if cpi_path.exists():
            with open(cpi_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_payload = {
                        "series_name": "cpi_urban_monthly",
                        "observation_date": row.get("observation_date", ""),
                        "cpi_index": row.get("INDCPIALLMINMEI", ""),
                    }
                    record_hash = compute_record_hash(raw_payload)
                    yield RawRecord(
                        source_id=self.source_id,
                        source_version="cpi_urban_monthly",
                        license_id=license_id,
                        retrieved_at=retrieved_at,
                        raw_payload=raw_payload,
                        record_hash=record_hash,
                    )

        # 2. INR/USD Daily FX
        fx_path = self.source_raw_dir / self.fx_file_name
        if fx_path.exists():
            with open(fx_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_payload = {
                        "series_name": "inr_usd_fx_daily",
                        "observation_date": row.get("observation_date", ""),
                        "inr_per_usd": row.get("DEXINUS", ""),
                    }
                    record_hash = compute_record_hash(raw_payload)
                    yield RawRecord(
                        source_id=self.source_id,
                        source_version="inr_usd_fx_daily",
                        license_id=license_id,
                        retrieved_at=retrieved_at,
                        raw_payload=raw_payload,
                        record_hash=record_hash,
                    )


class ONetTaxonomyConnector(BaseConnector):
    """Connector for O*NET 29.0 Content Model Database (SRC-SUP-TAX-01).

    Streams tech occupation descriptors and technology skills mapped to SOC codes.
    """

    source_id: str = "SRC-SUP-TAX-01"
    occupations_file_name: str = "occupation_data_tech.csv"
    skills_file_name: str = "technology_skills_tech_roles.csv"

    def extract_raw_records(self) -> Iterator[RawRecord]:
        """Extract RawRecord stream from O*NET taxonomy tables."""
        config = self.verify_licence()
        self.verify_manifest()

        ref_period = config.get("reference_period", {})
        source_version = str(ref_period.get("version", "29.0"))
        licence_meta = config.get("licence", {})
        license_id = str(licence_meta.get("spdx_id", "CC-BY-4.0"))
        retrieved_at = self.get_manifest_retrieved_at()

        # 1. Tech Occupations
        occ_path = self.source_raw_dir / self.occupations_file_name
        if occ_path.exists():
            with open(occ_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_payload = {
                        "table_name": "occupations",
                        "onetsoc_code": row.get("onetsoc_code", ""),
                        "title": row.get("title", ""),
                        "description": row.get("description", ""),
                    }
                    record_hash = compute_record_hash(raw_payload)
                    yield RawRecord(
                        source_id=self.source_id,
                        source_version=source_version,
                        license_id=license_id,
                        retrieved_at=retrieved_at,
                        raw_payload=raw_payload,
                        record_hash=record_hash,
                    )

        # 2. Technology Skills
        skills_path = self.source_raw_dir / self.skills_file_name
        if skills_path.exists():
            with open(skills_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_payload = {
                        "table_name": "technology_skills",
                        "onetsoc_code": row.get("onetsoc_code", ""),
                        "commodity_code": row.get("commodity_code", ""),
                        "commodity_title": row.get("commodity_title", ""),
                        "example_tool": row.get("example_tool", ""),
                        "hot_technology": row.get("hot_technology", ""),
                    }
                    record_hash = compute_record_hash(raw_payload)
                    yield RawRecord(
                        source_id=self.source_id,
                        source_version=source_version,
                        license_id=license_id,
                        retrieved_at=retrieved_at,
                        raw_payload=raw_payload,
                        record_hash=record_hash,
                    )


class ESCOTaxonomyConnector(BaseConnector):
    """Connector for European Skills, Competences and Occupations (SRC-SUP-TAX-02).

    Streams ESCO tech skill labels, types, and hierarchy groups.
    """

    source_id: str = "SRC-SUP-TAX-02"
    data_file_name: str = "esco_skills_tech_hierarchy.csv"

    def extract_raw_records(self) -> Iterator[RawRecord]:
        """Extract RawRecord stream from ESCO skill hierarchy."""
        config = self.verify_licence()
        self.verify_manifest()

        data_file = self.source_raw_dir / self.data_file_name
        if not data_file.exists():
            msg = f"Raw data file not found: {data_file}"
            raise FileNotFoundError(msg)

        ref_period = config.get("reference_period", {})
        source_version = str(ref_period.get("version", "1.1.1"))
        licence_meta = config.get("licence", {})
        license_id = str(licence_meta.get("spdx_id", "ODbL-1.0"))
        retrieved_at = self.get_manifest_retrieved_at()

        with open(data_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_payload = {
                    "concept_uri": row.get("concept_uri", ""),
                    "skill_label": row.get("skill_label", ""),
                    "skill_type": row.get("skill_type", ""),
                    "reuse_level": row.get("reuse_level", ""),
                    "parent_skill_group": row.get("parent_skill_group", ""),
                }
                record_hash = compute_record_hash(raw_payload)
                yield RawRecord(
                    source_id=self.source_id,
                    source_version=source_version,
                    license_id=license_id,
                    retrieved_at=retrieved_at,
                    raw_payload=raw_payload,
                    record_hash=record_hash,
                )


class MOSPIPLFSConnector(BaseConnector):
    """Connector for MOSPI Periodic Labour Force Survey Microdata (SRC-IND-OFF-01).

    Streams urban tech wage macro anchors and Schedule 10.4 layout specifications.
    Admitted strictly as macro wage anchor and population benchmark (Rule D-010, R-DA-01).
    """

    source_id: str = "SRC-IND-OFF-01"
    anchors_file_name: str = "plfs_urban_tech_macro_anchors.csv"
    layout_file_name: str = "plfs_2023_24_layout_sched_10_4.csv"

    def extract_raw_records(self) -> Iterator[RawRecord]:
        """Extract RawRecord stream from MOSPI PLFS tables."""
        config = self.verify_licence()
        self.verify_manifest()

        ref_id = config.get("dataset_reference_id", "DDI-IND-CSO-PLFS-2023-24")
        source_version = str(ref_id)
        licence_meta = config.get("licence", {})
        license_id = str(licence_meta.get("spdx_id", "OGL-India-1.0"))
        retrieved_at = self.get_manifest_retrieved_at()

        anchors_path = self.source_raw_dir / self.anchors_file_name
        layout_path = self.source_raw_dir / self.layout_file_name

        if not anchors_path.exists() and not layout_path.exists():
            msg = f"No raw data files found for {self.source_id} in {self.source_raw_dir}"
            raise FileNotFoundError(msg)

        # 1. Macro wage anchors
        if anchors_path.exists():
            with open(anchors_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    clean_row = {str(k) if k is not None else "_extra_": v for k, v in row.items()}
                    raw_payload = {
                        "table_name": "macro_anchors",
                        **clean_row,
                    }
                    record_hash = compute_record_hash(raw_payload)
                    yield RawRecord(
                        source_id=self.source_id,
                        source_version=source_version,
                        license_id=license_id,
                        retrieved_at=retrieved_at,
                        raw_payload=raw_payload,
                        record_hash=record_hash,
                    )

        # 2. Schedule 10.4 layout specification
        if layout_path.exists():
            with open(layout_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    clean_row = {str(k) if k is not None else "_extra_": v for k, v in row.items()}
                    raw_payload = {
                        "table_name": "layout_sched_10_4",
                        **clean_row,
                    }
                    record_hash = compute_record_hash(raw_payload)
                    yield RawRecord(
                        source_id=self.source_id,
                        source_version=source_version,
                        license_id=license_id,
                        retrieved_at=retrieved_at,
                        raw_payload=raw_payload,
                        record_hash=record_hash,
                    )


class LabourBureauQESConnector(BaseConnector):
    """Connector for Labour Bureau Quarterly Employment Survey (SRC-IND-OFF-03).

    Streams IT/BPO formal employment counts and workforce ratios.
    Admitted strictly as auxiliary macro signal (Rule R-DA-01).
    """

    source_id: str = "SRC-IND-OFF-03"
    data_file_name: str = "qes_it_bpo_formal_employment.csv"

    def extract_raw_records(self) -> Iterator[RawRecord]:
        """Extract RawRecord stream from Labour Bureau QES IT/BPO survey."""
        config = self.verify_licence()
        self.verify_manifest()

        data_file = self.source_raw_dir / self.data_file_name
        if not data_file.exists():
            msg = f"Raw data file not found: {data_file}"
            raise FileNotFoundError(msg)

        ref_period = config.get("reference_period", {})
        source_version = f"{ref_period.get('start', '2023')}_{ref_period.get('end', '2024')}"
        licence_meta = config.get("licence", {})
        license_id = str(licence_meta.get("spdx_id", "OGL-India-1.0"))
        retrieved_at = self.get_manifest_retrieved_at()

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
    "SRC-IND-OFF-01": MOSPIPLFSConnector,
    "SRC-IND-OFF-03": LabourBureauQESConnector,
    "SRC-SUP-CORP-01": CorporateDisclosuresConnector,
    "SRC-SUP-MAC-01": RBIMacroConnector,
    "SRC-SUP-TAX-01": ONetTaxonomyConnector,
    "SRC-SUP-TAX-02": ESCOTaxonomyConnector,
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
