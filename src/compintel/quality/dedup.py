"""Deduplication and person entity clustering engine (Task T3.10a).

Adheres strictly to:
- Rule R-DA-03: Companion field and lineage preservation.
- Rule R-DA-04: Mandatory provenance and deterministic cluster IDs.
- Rule R-CD-03: Quality layer only imports schema; zero dependencies on higher layers.
- Rule R-MD-09: Deterministic algorithms, strictly free of LLMs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any

import polars as pl

DEFAULT_DEDUP_VERSION: str = "v0.1.0"


def compute_exact_record_signature(payload: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 fingerprint for exact record duplicate detection.

    Canonicalizes fields to ensure invariance under dict key order or numerical precision jitter.
    """
    signature_keys = [
        "source_id",
        "role_family",
        "canonical_title",
        "seniority",
        "location",
        "years_experience",
        "guaranteed_cash_annual",
        "basic_annual",
        "hra_annual",
        "special_allowance_annual",
        "as_of_date",
    ]

    canonical_payload: dict[str, Any] = {}
    for k in sorted(signature_keys):
        val = payload.get(k)
        if isinstance(val, float):
            # Round floats to 2 decimal places to avoid IEEE 754 precision artifacts
            canonical_payload[k] = round(val, 2)
        elif val is None:
            canonical_payload[k] = None
        else:
            canonical_payload[k] = str(val).strip()

    serialized = json.dumps(canonical_payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_person_signature(payload: dict[str, Any]) -> str:
    """Compute a person-level biometric/profile fingerprint to cluster repeat submissions.

    Matches identical demographic profiles with matching base pay or specific compensation line items.
    """
    # If the payload explicitly carries an anonymized contributor ID, use it directly
    anon_id = payload.get("anonymized_employee_id") or payload.get("contributor_id")
    if anon_id and str(anon_id).strip():
        token = f"anon:{str(anon_id).strip()}"
        return f"PER-{hashlib.sha256(token.encode('utf-8')).hexdigest()[:12].upper()}"

    person_keys = [
        "location",
        "role_family",
        "education_level",
        "years_experience",
        "basic_annual",
        "guaranteed_cash_annual",
    ]

    canonical_person: dict[str, Any] = {}
    for k in sorted(person_keys):
        val = payload.get(k)
        if isinstance(val, float):
            canonical_person[k] = round(val, 2)
        elif val is None:
            canonical_person[k] = None
        else:
            canonical_person[k] = str(val).strip()

    serialized = json.dumps(canonical_person, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12].upper()
    return f"PER-{digest}"


@dataclass(frozen=True)
class DeduplicationResult:
    """Standardized deduplication and person-clustering outcome for an observation."""

    observation_id: str
    record_signature: str
    is_exact_duplicate: bool
    exact_duplicate_of: str | None
    person_cluster_id: str
    person_cluster_size: int
    dedup_version: str = DEFAULT_DEDUP_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "observation_id": self.observation_id,
            "record_signature": self.record_signature,
            "is_exact_duplicate": self.is_exact_duplicate,
            "exact_duplicate_of": self.exact_duplicate_of,
            "person_cluster_id": self.person_cluster_id,
            "person_cluster_size": self.person_cluster_size,
            "dedup_version": self.dedup_version,
        }


class ExactDeduplicator:
    """Stateful streaming and batch deduplicator tracking seen record signatures."""

    def __init__(self, dedup_version: str = DEFAULT_DEDUP_VERSION) -> None:
        self.dedup_version = dedup_version
        self._seen_signatures: dict[str, str] = {}  # signature -> primary observation_id
        self._person_clusters: dict[str, list[str]] = {}  # person_cluster_id -> [observation_id]

    @property
    def total_seen(self) -> int:
        """Total distinct signatures recorded."""
        return len(self._seen_signatures)

    @property
    def total_clusters(self) -> int:
        """Total person clusters formed."""
        return len(self._person_clusters)

    def process_record(
        self,
        observation_id: str,
        payload: dict[str, Any],
    ) -> DeduplicationResult:
        """Process a single record, returning duplicate status and person cluster assignment."""
        obs_id = str(observation_id).strip()
        sig = compute_exact_record_signature(payload)
        person_id = compute_person_signature(payload)

        # Check exact duplicate
        if sig in self._seen_signatures:
            is_dup = True
            dup_of = self._seen_signatures[sig]
        else:
            is_dup = False
            dup_of = None
            self._seen_signatures[sig] = obs_id

        # Update person cluster
        if person_id not in self._person_clusters:
            self._person_clusters[person_id] = []
        self._person_clusters[person_id].append(obs_id)
        cluster_size = len(self._person_clusters[person_id])

        return DeduplicationResult(
            observation_id=obs_id,
            record_signature=sig,
            is_exact_duplicate=is_dup,
            exact_duplicate_of=dup_of,
            person_cluster_id=person_id,
            person_cluster_size=cluster_size,
            dedup_version=self.dedup_version,
        )


def deduplicate_records_df(
    df: pl.DataFrame,
    id_column: str = "observation_id",
    dedup_version: str = DEFAULT_DEDUP_VERSION,
) -> pl.DataFrame:
    """Batch process a Polars DataFrame, appending deduplication and person cluster columns.

    Appends:
    - record_signature: Deterministic SHA-256 fingerprint string
    - is_exact_duplicate: Boolean indicating an identical prior record exists
    - exact_duplicate_of: Observation ID of the original record (or null)
    - person_cluster_id: Clustered worker identity string
    - person_cluster_size: Total records belonging to this person cluster

    Args:
        df: Polars DataFrame of canonical or raw observations.
        id_column: Column name containing the unique observation identifier.
        dedup_version: Version identifier attached to output.

    Returns:
        New Polars DataFrame with appended deduplication columns.
    """
    if df.height == 0:
        return df.with_columns(
            pl.lit(None, dtype=pl.String).alias("record_signature"),
            pl.lit(None, dtype=pl.Boolean).alias("is_exact_duplicate"),
            pl.lit(None, dtype=pl.String).alias("exact_duplicate_of"),
            pl.lit(None, dtype=pl.String).alias("person_cluster_id"),
            pl.lit(None, dtype=pl.Int64).alias("person_cluster_size"),
            pl.lit(None, dtype=pl.String).alias("dedup_version"),
        )

    deduplicator = ExactDeduplicator(dedup_version=dedup_version)
    records = df.iter_rows(named=True)

    results: list[DeduplicationResult] = []
    for r in records:
        obs_id = str(r.get(id_column, f"ROW-{len(results)}"))
        res = deduplicator.process_record(observation_id=obs_id, payload=r)
        results.append(res)

    # Post-process to update all records in a cluster with the final cluster_size
    final_cluster_sizes = {
        cid: len(members) for cid, members in deduplicator._person_clusters.items()
    }

    signatures = [r.record_signature for r in results]
    is_dups = [r.is_exact_duplicate for r in results]
    dup_ofs = [r.exact_duplicate_of for r in results]
    person_ids = [r.person_cluster_id for r in results]
    sizes = [final_cluster_sizes[r.person_cluster_id] for r in results]
    versions = [r.dedup_version for r in results]

    return df.with_columns(
        pl.Series("record_signature", signatures, dtype=pl.String),
        pl.Series("is_exact_duplicate", is_dups, dtype=pl.Boolean),
        pl.Series("exact_duplicate_of", dup_ofs, dtype=pl.String),
        pl.Series("person_cluster_id", person_ids, dtype=pl.String),
        pl.Series("person_cluster_size", sizes, dtype=pl.Int64),
        pl.Series("dedup_version", versions, dtype=pl.String),
    )
