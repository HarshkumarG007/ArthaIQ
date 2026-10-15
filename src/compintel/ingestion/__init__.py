"""Ingestion package: manifest verification, licence gates, and source connectors.

Governs Rules R-DA-01, R-DA-02, and R-DA-03.
"""

from compintel.ingestion.connector import (
    CONNECTOR_REGISTRY,
    BaseConnector,
    CorporateDisclosuresConnector,
    ESCOTaxonomyConnector,
    ONetTaxonomyConnector,
    RBIMacroConnector,
    compute_record_hash,
    find_repo_root,
    get_connector,
)
from compintel.ingestion.manifest import (
    ChecksumMismatchError,
    LicenceGateError,
    compute_sha256,
    generate_source_manifest,
    verify_licence_gate,
    verify_manifest,
)

__all__ = [
    "CONNECTOR_REGISTRY",
    "BaseConnector",
    "ChecksumMismatchError",
    "CorporateDisclosuresConnector",
    "ESCOTaxonomyConnector",
    "LicenceGateError",
    "ONetTaxonomyConnector",
    "RBIMacroConnector",
    "compute_record_hash",
    "compute_sha256",
    "find_repo_root",
    "generate_source_manifest",
    "get_connector",
    "verify_licence_gate",
    "verify_manifest",
]
