"""Unit tests for ArthaIQ Pilot Cohort Consent & Privacy Gateway (T20.01).

Verifies:
- Valid statutory consent record parsing under DPDP Act 2023 Sec 6 & Sec 12.
- Age gate enforcement: rejecting age < 18 under DPDP Act 2023 Sec 9.
- Rejection of unchecked voluntary/non-appraisal/erasure acknowledgments.
- Rejection of prohibited causal pay claims in notes (Rule R-CR-01 / CPA 2019).
- Valid demographic stratification across all 3 families (DATA, SWE, MLAI).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from compintel.career.pilot_consent import PilotConsentSubmission, PilotStratification
from compintel.career.schema import RoleFamily


class TestPilotConsentModel:
    """Validate PilotConsentSubmission schema and statutory guardrails."""

    def test_valid_pilot_consent_data_family(self) -> None:
        """Valid consent record for DATA family participant passes cleanly."""
        strat = PilotStratification(
            role_family=RoleFamily.DATA,
            seniority_band="mid",
            geographic_cluster="BLR",
        )
        consent = PilotConsentSubmission(
            consented_at="2026-10-31T12:00:00Z",
            age_confirmed_18_plus=True,
            voluntary_research_acknowledged=True,
            non_appraisal_acknowledged=True,
            right_to_erasure_acknowledged=True,
            stratification=strat,
            notes="Participating to practice analytical reasoning.",
        )
        assert consent.consent_version == "2026-10-dpdp-v1"
        assert consent.consent_id.startswith("CONSENT-")
        assert consent.stratification.role_family == RoleFamily.DATA
        assert consent.stratification.seniority_band == "mid"
        assert consent.stratification.geographic_cluster == "BLR"

    def test_valid_pilot_consent_swe_and_mlai_families(self) -> None:
        """Valid consent records across SWE and MLAI families parse cleanly."""
        for fam in [RoleFamily.SWE, RoleFamily.MLAI]:
            strat = PilotStratification(
                role_family=fam,
                seniority_band="senior",
                geographic_cluster="DEL_NCR",
            )
            consent = PilotConsentSubmission(
                consented_at="2026-10-31T12:00:00Z",
                age_confirmed_18_plus=True,
                voluntary_research_acknowledged=True,
                non_appraisal_acknowledged=True,
                right_to_erasure_acknowledged=True,
                stratification=strat,
            )
            assert consent.stratification.role_family == fam

    def test_rejection_when_age_gate_unconfirmed(self) -> None:
        """DPDP Act 2023 Sec 9: Age < 18 or unconfirmed age must raise ValidationError."""
        strat = PilotStratification(
            role_family=RoleFamily.DATA,
            seniority_band="junior",
            geographic_cluster="HYD",
        )
        with pytest.raises(ValidationError, match="18 years of age or older"):
            PilotConsentSubmission(
                consented_at="2026-10-31T12:00:00Z",
                age_confirmed_18_plus=False,
                voluntary_research_acknowledged=True,
                non_appraisal_acknowledged=True,
                right_to_erasure_acknowledged=True,
                stratification=strat,
            )

    def test_rejection_when_statutory_acknowledgments_false(self) -> None:
        """Unchecked voluntary, non-appraisal, or erasure acknowledgments must fail."""
        strat = PilotStratification(
            role_family=RoleFamily.SWE,
            seniority_band="mid",
            geographic_cluster="PUN_MUM_CHE",
        )
        # Unchecked non_appraisal
        with pytest.raises(ValidationError, match="non_appraisal_acknowledged"):
            PilotConsentSubmission(
                consented_at="2026-10-31T12:00:00Z",
                age_confirmed_18_plus=True,
                voluntary_research_acknowledged=True,
                non_appraisal_acknowledged=False,
                right_to_erasure_acknowledged=True,
                stratification=strat,
            )

        # Unchecked right_to_erasure
        with pytest.raises(ValidationError, match="right_to_erasure_acknowledged"):
            PilotConsentSubmission(
                consented_at="2026-10-31T12:00:00Z",
                age_confirmed_18_plus=True,
                voluntary_research_acknowledged=True,
                non_appraisal_acknowledged=True,
                right_to_erasure_acknowledged=False,
                stratification=strat,
            )

    def test_rejection_of_causal_promises_in_notes(self) -> None:
        """Notes containing prohibited causal compensation claims must fail under Rule R-CR-01."""
        strat = PilotStratification(
            role_family=RoleFamily.MLAI,
            seniority_band="senior",
            geographic_cluster="BLR",
        )
        with pytest.raises(ValidationError, match="R-CR-01"):
            PilotConsentSubmission(
                consented_at="2026-10-31T12:00:00Z",
                age_confirmed_18_plus=True,
                voluntary_research_acknowledged=True,
                non_appraisal_acknowledged=True,
                right_to_erasure_acknowledged=True,
                stratification=strat,
                notes="Joining the pilot will boost your salary by 30 LPA.",
            )
