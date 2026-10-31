"""ArthaIQ Career Architect Pilot Cohort Consent & Privacy Gateway Models (T20.01).

Governed by:
- India Digital Personal Data Protection Act, 2023 (DPDP Act):
  - Section 6: Notice and Informed Consent for pilot research participation
  - Section 9: Age verification gate (mandatory 18+ declaration)
  - Section 12: Right to operational erasure (single-click hard wipe)
- Consumer Protection Act, 2019 (CPA 2019):
  - Rule R-CR-01: Anti-causal compensation guarantees prohibition
  - Rule R-CR-11: Practice, not certification (rejects exam/credentials)
- Architecture Invariants:
  - Rule R-CR-12 / ADR-0012: Local-first persistence; zero server-side profiles
  - ADR-0010: Zero runtime LLMs on consent/audit path
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from compintel.career.schema import RoleFamily, validate_anti_causal_text

SeniorityBand = Literal["junior", "mid", "senior", "staff_plus"]
GeographicCluster = Literal["BLR", "DEL_NCR", "HYD", "PUN_MUM_CHE", "OTHER"]


class PilotStratification(BaseModel):
    """Demographic stratification for the N=150 pilot cohort."""

    role_family: RoleFamily = Field(
        ...,
        description="Target role family: DATA, SWE, or MLAI",
    )
    seniority_band: SeniorityBand = Field(
        ...,
        description="Target seniority band (junior, mid, senior, staff_plus)",
    )
    geographic_cluster: GeographicCluster = Field(
        ...,
        description="Primary employment cluster in India",
    )


class PilotConsentSubmission(BaseModel):
    """Statutory consent submission record under India DPDP Act 2023."""

    consent_id: str = Field(
        default_factory=lambda: f"CONSENT-{uuid.uuid4().hex[:12].upper()}",
        description="Unique anonymous client-side consent identifier",
    )
    consent_version: str = Field(
        default="2026-10-dpdp-v1",
        description="Version identifier of the statutory consent text",
    )
    consented_at: str = Field(
        ...,
        description="ISO 8601 timestamp when consent was granted",
    )
    age_confirmed_18_plus: bool = Field(
        ...,
        description="Confirmation of 18+ years of age (DPDP Act 2023 Sec 9)",
    )
    voluntary_research_acknowledged: bool = Field(
        ...,
        description="Acknowledgment of voluntary pilot participation (DPDP Act 2023 Sec 6)",
    )
    non_appraisal_acknowledged: bool = Field(
        ...,
        description="Acknowledgment of non-appraisal, no-guarantee status (CPA 2019 / R-CR-01)",
    )
    right_to_erasure_acknowledged: bool = Field(
        ...,
        description="Acknowledgment of single-click right to erasure (DPDP Act 2023 Sec 12)",
    )
    stratification: PilotStratification = Field(
        ...,
        description="Demographic stratification data",
    )
    notes: str = Field(
        default="",
        description="Optional participant reflection notes; checked against anti-causal rules",
    )

    @field_validator("age_confirmed_18_plus")
    @classmethod
    def validate_age_gate(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Pilot participation requires participant to be 18 years of age or older "
                "under DPDP Act 2023 Section 9."
            )
        return v

    @field_validator(
        "voluntary_research_acknowledged",
        "non_appraisal_acknowledged",
        "right_to_erasure_acknowledged",
    )
    @classmethod
    def validate_statutory_acknowledgments(cls, v: bool, info: object) -> bool:
        if not v:
            field_name = getattr(info, "field_name", "statutory field")
            raise ValueError(
                f"Statutory consent acknowledgment for '{field_name}' must be accepted "
                "to participate in the pilot cohort."
            )
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes_anti_causal(cls, v: str) -> str:
        if v.strip():
            validate_anti_causal_text(v, "consent_notes")
        return v
