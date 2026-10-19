"""Comprehensive unit test suite for serving core estimation engine (Phase 9, Task T9.01).

Tests:
- Normalization and feature assembly helpers (role, seniority, location, years).
- Pure estimate() function with ProfileRequest, EstimateRequest, and dict inputs.
- Structured abstention path under thin cohort evidence (Rules R-UQ-02, R-MD-08).
- Supported estimation path with calibrated P10, P50, P90 (Rules R-UQ-01, R-MD-07).
- Compare-only compensation positioning quarantine (Rule R-MD-13, architecture.md Section 11).
- Invariant validation errors (unsupported measure, currency, invalid dates).
- ServingModelManager lifecycle (promotion, rollback, health check).
- Response serialization and Pydantic schema validation.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from compintel.errors import ModelArtifactError, ValidationError
from compintel.models.bundle import UnifiedPredictionResult
from compintel.schema.enums import (
    CompensationMeasure,
    Currency,
    MetroLocation,
    RoleFamily,
    SeniorityLevel,
)
from compintel.serving.core import (
    assemble_candidate_profile,
    estimate,
    get_default_serving_manager,
    infer_years_experience,
    normalize_location,
    normalize_role_family,
    normalize_seniority,
    parse_as_of_date,
    reset_default_serving_manager,
)
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import (
    Abstained,
    ComparisonInfo,
    Estimate,
    EstimateRequest,
    ExperienceInput,
    ProfileRequest,
    QuantileSpan,
)
from compintel.uncertainty.support import CandidateProfile

# -----------------------------------------------------------------------------
# 1. Normalization & Feature Assembly Tests
# -----------------------------------------------------------------------------


class TestServingNormalization:
    """Test normalization and inference routines in the serving core."""

    def test_normalize_role_family_canonical_and_synonyms(self) -> None:
        assert normalize_role_family("SWE") == RoleFamily.SWE.value
        assert normalize_role_family("software engineer") == RoleFamily.SWE.value
        assert normalize_role_family("BACKEND_ENGINEER") == RoleFamily.SWE.value
        assert normalize_role_family("frontend") == RoleFamily.SWE.value
        assert normalize_role_family("data_scientist") == RoleFamily.DATA.value
        assert normalize_role_family("DATA_ENGINEER") == RoleFamily.DATA.value
        assert normalize_role_family("ml-engineer") == RoleFamily.MLAI.value
        assert normalize_role_family("machine_learning") == RoleFamily.MLAI.value
        assert normalize_role_family("UNKNOWN_ROLE") == RoleFamily.OTHER.value

    def test_normalize_seniority_explicit_and_synonyms(self) -> None:
        assert normalize_seniority("JR") == SeniorityLevel.JR.value
        assert normalize_seniority("junior") == SeniorityLevel.JR.value
        assert normalize_seniority("associate") == SeniorityLevel.JR.value
        assert normalize_seniority("mid") == SeniorityLevel.MID.value
        assert normalize_seniority("L2") == SeniorityLevel.MID.value
        assert normalize_seniority("sr") == SeniorityLevel.SR.value
        assert normalize_seniority("senior") == SeniorityLevel.SR.value
        assert normalize_seniority("staff") == SeniorityLevel.STAFF.value
        assert normalize_seniority("lead") == SeniorityLevel.STAFF.value
        assert normalize_seniority("principal") == SeniorityLevel.PRINCIPAL.value
        assert normalize_seniority("director") == SeniorityLevel.PRINCIPAL.value

    def test_normalize_seniority_inferred_from_years(self) -> None:
        assert normalize_seniority(None, total_years=1.0) == SeniorityLevel.JR.value
        assert normalize_seniority(None, total_years=3.5) == SeniorityLevel.MID.value
        assert normalize_seniority(None, total_years=7.0) == SeniorityLevel.SR.value
        assert normalize_seniority(None, total_years=11.5) == SeniorityLevel.STAFF.value
        assert normalize_seniority(None, total_years=16.0) == SeniorityLevel.PRINCIPAL.value

    def test_normalize_location_metros_and_synonyms(self) -> None:
        assert normalize_location("BENGALURU") == MetroLocation.BENGALURU.value
        assert normalize_location("bangalore") == MetroLocation.BENGALURU.value
        assert normalize_location("hyderabad") == MetroLocation.HYDERABAD.value
        assert normalize_location("pune") == MetroLocation.PUNE.value
        assert normalize_location("mumbai") == MetroLocation.MUMBAI.value
        assert normalize_location("delhi") == MetroLocation.NCR.value
        assert normalize_location("ncr") == MetroLocation.NCR.value
        assert normalize_location("gurgaon") == MetroLocation.NCR.value
        assert normalize_location("chennai") == MetroLocation.CHENNAI.value
        assert normalize_location("KOLKATA") == MetroLocation.OTHER.value

    def test_infer_years_experience(self) -> None:
        assert infer_years_experience(5.5, None) == 5.5
        assert infer_years_experience(None, "JR") == 1.0
        assert infer_years_experience(None, "MID") == 4.0
        assert infer_years_experience(None, "SR") == 7.0
        assert infer_years_experience(None, "STAFF") == 11.0
        assert infer_years_experience(None, "PRINCIPAL") == 16.0
        assert infer_years_experience(None, None) == 4.0

    def test_parse_as_of_date(self) -> None:
        parsed = parse_as_of_date("2026-03-31")
        assert parsed == "2026-03-31"

        iso_parsed = parse_as_of_date("2026-03-31T12:00:00Z")
        assert iso_parsed == "2026-03-31"

        default_parsed = parse_as_of_date(None)
        assert len(default_parsed) == 10
        assert default_parsed.count("-") == 2

        with pytest.raises(ValidationError) as exc:
            parse_as_of_date("not-a-date")
        assert exc.value.code == "INVALID_AS_OF_DATE"


class TestCandidateProfileAssembly:
    """Test conversion of heterogeneous input formats into CandidateProfile."""

    def test_assemble_from_pydantic_profile_request(self) -> None:
        req = ProfileRequest(
            occupation_id="SWE",
            location_id="BENGALURU",
            experience=ExperienceInput(total_years=6.0, level_id="SR"),
        )
        profile, level_used, extras = assemble_candidate_profile(req)
        assert isinstance(profile, CandidateProfile)
        assert profile.role_family == RoleFamily.SWE.value
        assert profile.seniority == SeniorityLevel.SR.value
        assert profile.location == MetroLocation.BENGALURU.value
        assert profile.years_experience == 6.0
        assert level_used == 0
        assert extras == {}

    def test_assemble_from_dict_flat(self) -> None:
        payload = {
            "role_family": "DATA_SCIENTIST",
            "seniority": "MID",
            "location": "HYDERABAD",
            "years_experience": 4.0,
        }
        profile, level_used, _ = assemble_candidate_profile(payload)
        assert profile.role_family == RoleFamily.DATA.value
        assert profile.seniority == SeniorityLevel.MID.value
        assert profile.location == MetroLocation.HYDERABAD.value
        assert profile.years_experience == 4.0
        assert level_used == 0

    def test_assemble_with_extras_sets_level_1_and_2(self) -> None:
        # L1: Core + Work Arrangement
        req_l1 = ProfileRequest(
            occupation_id="SWE",
            location_id="PUNE",
            experience=ExperienceInput(total_years=8.0),
            extras={"work_arrangement": "hybrid"},
        )
        profile_l1, level_used_l1, extras_l1 = assemble_candidate_profile(req_l1)
        assert profile_l1.years_experience == 8.0
        assert level_used_l1 == 1
        assert extras_l1.get("work_arrangement") == "hybrid"

        # L2: Core + Employer Archetype / Target Tier
        req_l2 = ProfileRequest(
            occupation_id="SWE",
            location_id="PUNE",
            experience=ExperienceInput(total_years=8.0),
            extras={"target_tier": "tier_1", "work_arrangement": "hybrid"},
        )
        _, level_used_l2, extras_l2 = assemble_candidate_profile(req_l2)
        assert level_used_l2 == 2
        assert extras_l2.get("target_tier") == "tier_1"

    def test_assemble_invalid_payload_type(self) -> None:
        with pytest.raises(ValidationError) as exc:
            assemble_candidate_profile(["invalid", "payload"])  # type: ignore[arg-type]
        assert exc.value.code == "INVALID_PROFILE_PAYLOAD"

    def test_assemble_negative_experience_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            assemble_candidate_profile(
                {"role": "SWE", "location": "PUNE", "years_experience": -2.0}
            )
        assert exc.value.code == "EXPERIENCE_OUT_OF_BOUNDS"

    def test_assemble_unrealistic_experience_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            assemble_candidate_profile(
                {"role": "SWE", "location": "PUNE", "years_experience": 55.0}
            )
        assert exc.value.code == "EXPERIENCE_OUT_OF_BOUNDS"


# -----------------------------------------------------------------------------
# 2. ServingModelManager Lifecycle Tests
# -----------------------------------------------------------------------------


class TestServingModelManagerLifecycle:
    """Test ServingModelManager initialization, promotion, rollback, and health checks."""

    def test_manager_starts_unready(self) -> None:
        manager = ServingModelManager()
        assert not manager.is_ready
        assert manager.previous_bundle is None
        health = manager.health_check()
        assert health["status"] == "UNHEALTHY"
        assert not health["is_ready"]

        with pytest.raises(ModelArtifactError) as exc:
            _ = manager.active_bundle
        assert exc.value.code == "NO_ACTIVE_BUNDLE"

    def test_manager_load_and_promote_champion(self) -> None:
        manager = ServingModelManager()
        manager.load_and_promote(
            "artifacts/champion_v0", verify_checksums=True, run_smoke_test=True
        )
        assert manager.is_ready
        assert manager.model_version == "0.1.0"
        assert "Rung F" in manager.rung

        health = manager.health_check()
        assert health["status"] == "HEALTHY"
        assert health["is_ready"] is True
        assert health["model_version"] == "0.1.0"
        assert health["has_rollback"] is False

    def test_manager_rollback_raises_when_no_prior_bundle(self) -> None:
        manager = ServingModelManager()
        manager.load_and_promote("artifacts/champion_v0")
        with pytest.raises(ModelArtifactError) as exc:
            manager.rollback()
        assert exc.value.code == "ROLLBACK_UNAVAILABLE"

    def test_manager_rollback_restores_previous(self) -> None:
        manager = ServingModelManager()
        b1 = manager.load_and_promote("artifacts/champion_v0")
        _ = manager.load_and_promote("artifacts/champion_v0")
        assert manager.previous_bundle is not None
        assert manager.health_check()["has_rollback"] is True

        restored = manager.rollback()
        assert restored is b1
        assert manager.previous_bundle is None


# -----------------------------------------------------------------------------
# 3. Pure estimate() Function Tests (Rules R-UQ-01, R-UQ-02, R-MD-13)
# -----------------------------------------------------------------------------


class TestServingEstimatePureFunction:
    """Test pure estimate() function under both abstained and supported execution paths."""

    def setup_method(self) -> None:
        """Reset default manager before each test."""
        reset_default_serving_manager()

    def test_estimate_abstained_with_champion_v0_thin_evidence(self) -> None:
        """Rule R-MD-08 & R-UQ-02: champion_v0 has thin sample count (N=1), must abstain."""
        req = ProfileRequest(
            occupation_id="SWE",
            location_id="BENGALURU",
            experience=ExperienceInput(total_years=6.0, level_id="SR"),
        )
        res = estimate(req)
        assert isinstance(res, Abstained)
        assert res.status == "abstained"
        assert len(res.reasons) > 0
        assert len(res.fallbacks) > 0
        assert res.disclaimer_id == "decision_support_v1"
        assert res.model_version == "0.1.0"
        assert len(res.data_snapshot_id) > 0

        # Validate UUID
        uuid_obj = UUID(res.request_id)
        assert str(uuid_obj) == res.request_id

        # Validate fallbacks contain actionable recommendations
        fallback_types = [fb.type for fb in res.fallbacks]
        assert "broader_cohort" in fallback_types

    def test_estimate_abstained_from_raw_dict(self) -> None:
        raw_dict = {
            "role_family": "DATA_SCIENTIST",
            "seniority": "MID",
            "location": "HYDERABAD",
            "years_experience": 4.0,
        }
        res = estimate(raw_dict, as_of="2026-03-31")
        assert isinstance(res, Abstained)
        assert res.status == "abstained"
        assert res.as_of == "2026-03-31"

    def test_estimate_supported_prediction_with_mocked_manager(self) -> None:
        """Rule R-UQ-01: When cohort support is sufficient, returns full QuantileSpan."""
        mock_manager = MagicMock(spec=ServingModelManager)
        mock_manager.is_ready = True
        mock_manager.model_version = "0.1.0"
        mock_manager.active_bundle.metadata.canonical_snapshot_id = "test-snap-001"

        mock_pred = UnifiedPredictionResult(
            target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
            currency=Currency.INR.value,
            nominal_basis="LPA",
            p10=22.50,
            p50=35.00,
            p90=52.00,
            interval_width=29.50,
            nominal_coverage=0.80,
            status="supported",
            is_abstained=False,
            evidence_grade="GRADE_A",
            support_status="SUPPORTED",
            source_quality_tier="TIER_A",
            reasons=[],
            explanation="Statistically defensible cohort support.",
            guidance=None,
            checks={
                "s1_cohort_size": {"effective_n": 85},
                "s3_recency": {"observation_age_days": 42.0},
            },
            model_version="0.1.0",
        )
        mock_manager.predict.return_value = mock_pred

        req = ProfileRequest(
            occupation_id="SWE",
            location_id="BENGALURU",
            experience=ExperienceInput(total_years=6.0, level_id="SR"),
        )

        res = estimate(req, as_of="2026-04-01", manager=mock_manager)
        assert isinstance(res, Estimate)
        assert res.status == "ok"
        assert res.as_of == "2026-04-01"
        assert res.profile_level_used == 0
        assert res.disclaimer_id == "decision_support_v1"

        # Verify QuantileSpan
        assert isinstance(res.estimate, QuantileSpan)
        assert res.estimate.p10 == 22.50
        assert res.estimate.p50 == 35.00
        assert res.estimate.p90 == 52.00
        assert res.estimate.p10 <= res.estimate.p50 <= res.estimate.p90
        assert res.estimate.currency == "INR"
        assert res.estimate.measure == "guaranteed_cash_annual"
        assert res.estimate.pre_tax is True
        assert res.estimate.nominal is True

        # Verify Reliability & Evidence
        assert res.reliability.grade == "GRADE_A"
        assert res.evidence.cohort_n == 85
        assert res.evidence.median_observation_age_days == 42.0
        assert res.evidence.data_snapshot_id == "test-snap-001"
        assert len(res.evidence.source_mix) == 2

    def test_estimate_compare_only_quarantine_bands(self) -> None:
        """Rule R-MD-13 & PT6: Current compensation is strictly quarantined to compare-only."""
        mock_manager = MagicMock(spec=ServingModelManager)
        mock_manager.is_ready = True
        mock_manager.model_version = "0.1.0"
        mock_manager.active_bundle.metadata.canonical_snapshot_id = "test-snap-001"

        mock_pred = UnifiedPredictionResult(
            target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
            currency=Currency.INR.value,
            nominal_basis="LPA",
            p10=20.0,
            p50=30.0,
            p90=45.0,
            interval_width=25.0,
            nominal_coverage=0.80,
            status="supported",
            is_abstained=False,
            evidence_grade="GRADE_A",
            support_status="SUPPORTED",
            source_quality_tier="TIER_A",
            reasons=[],
            explanation="",
            guidance=None,
            checks={},
            model_version="0.1.0",
        )
        mock_manager.predict.return_value = mock_pred

        test_cases: list[tuple[float, str, str, float]] = [
            (15.0, "below_market_floor", "<P10", -15.0),
            (25.0, "below_median", "P10-P50", -5.0),
            (30.0, "at_median", "P50", 0.0),
            (38.0, "above_median", "P50-P90", 8.0),
            (55.0, "top_percentile", ">P90", 25.0),
        ]

        for curr_comp, expected_cat, expected_band, expected_delta in test_cases:
            full_req = EstimateRequest(
                profile=ProfileRequest(
                    occupation_id="SWE",
                    location_id="BENGALURU",
                    experience=ExperienceInput(total_years=5.0),
                ),
                current_compensation=curr_comp,
            )
            res = estimate(full_req, manager=mock_manager)
            assert isinstance(res, Estimate)
            assert res.comparison is not None
            assert isinstance(res.comparison, ComparisonInfo)
            assert res.comparison.current_compensation == curr_comp
            assert res.comparison.delta_to_median_lpa == expected_delta
            assert res.comparison.position_category == expected_cat
            assert res.comparison.percentile_band == expected_band

            # Invariant: Verify current_compensation was NOT passed into CandidateProfile
            passed_profile = mock_manager.predict.call_args[0][0]
            assert not hasattr(passed_profile, "current_compensation")

    def test_estimate_unsupported_measure_rejected(self) -> None:
        """Rule R-MD-07: Unbundled compensation; PT1 strictly requires guaranteed_cash_annual."""
        with pytest.raises(ValidationError) as exc:
            estimate(
                {"role": "SWE", "location": "PUNE", "years_experience": 5.0},
                measure="total_cost_to_company",
            )
        assert exc.value.code == "UNSUPPORTED_MEASURE"

    def test_estimate_unsupported_currency_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            estimate(
                {"role": "SWE", "location": "PUNE", "years_experience": 5.0},
                currency="USD",
            )
        assert exc.value.code == "UNSUPPORTED_CURRENCY"

    def test_estimate_manager_unready_raises_artifact_error(self) -> None:
        unready_manager = ServingModelManager()
        with pytest.raises(ModelArtifactError) as exc:
            estimate(
                {"role": "SWE", "location": "PUNE", "years_experience": 5.0},
                manager=unready_manager,
            )
        assert exc.value.code == "NO_ACTIVE_BUNDLE"


# -----------------------------------------------------------------------------
# 4. Serialization & Pydantic Schema Validation Tests
# -----------------------------------------------------------------------------


class TestServingSchemaSerialization:
    """Test serialization/deserialization to dict and JSON."""

    def test_estimate_model_dump_and_json(self) -> None:
        est = Estimate(
            request_id="12345678-1234-5678-1234-567812345678",
            status="ok",
            estimate=QuantileSpan(p10=18.0, p50=28.0, p90=42.0),
            reliability={"grade": "GRADE_A", "reasons": []},  # type: ignore[arg-type]
            evidence={  # type: ignore[arg-type]
                "cohort_n": 40,
                "source_mix": [{"source_type": "statutory", "share": 1.0}],
                "median_observation_age_days": 35.0,
                "data_snapshot_id": "snap-1",
                "model_version": "0.1.0",
            },
            profile_level_used=0,
            warnings=[],
            disclaimer_id="decision_support_v1",
            as_of="2026-03-31",
            model_version="0.1.0",
            data_snapshot_id="snap-1",
        )

        d = est.to_dict()
        assert d["status"] == "ok"
        assert d["estimate"]["p50"] == 28.0
        assert d["disclaimer_id"] == "decision_support_v1"

        json_str = est.model_dump_json()
        assert '"status":"ok"' in json_str or '"status": "ok"' in json_str

    def test_abstained_model_dump_and_json(self) -> None:
        abs_res = Abstained(
            request_id="12345678-1234-5678-1234-567812345678",
            status="abstained",
            reasons=[{"code": "THIN_COHORT_EVIDENCE", "detail": "N < 10"}],  # type: ignore[arg-type]
            fallbacks=[{"type": "broader_cohort", "description": "Expand search"}],  # type: ignore[arg-type]
            disclaimer_id="decision_support_v1",
            as_of="2026-03-31",
            model_version="0.1.0",
            data_snapshot_id="snap-1",
        )

        d = abs_res.to_dict()
        assert d["status"] == "abstained"
        assert len(d["reasons"]) == 1
        assert d["reasons"][0]["code"] == "THIN_COHORT_EVIDENCE"

    def test_manager_promote_bundle_and_predict_alias(self) -> None:
        """Test promote_bundle with an in-memory ModelBundle and predict_profile alias."""
        from compintel.models.bundle import load_model_bundle

        bundle = load_model_bundle("artifacts/champion_v0")
        mgr = ServingModelManager()
        promoted = mgr.promote_bundle(bundle, run_smoke_test=True)
        assert promoted.model_version == "0.1.0"
        assert mgr.is_ready

        profile = CandidateProfile(
            role_family="SWE", seniority="SR", location="BENGALURU", years_experience=6.0
        )
        res = mgr.predict_profile(profile)
        assert res.is_abstained is True

    def test_default_serving_manager_lazy_init_and_reset(self) -> None:
        """Test get_default_serving_manager lazy loading and reset."""
        reset_default_serving_manager()
        mgr = get_default_serving_manager()
        assert mgr.is_ready
        assert mgr.model_version == "0.1.0"

        # Calling again returns cached singleton
        mgr2 = get_default_serving_manager()
        assert mgr2 is mgr

        reset_default_serving_manager()

    def test_assemble_candidate_profile_with_alternative_dict_keys(self) -> None:
        """Test candidate profile assembly using total_years and level_id in dict."""
        payload = {
            "role": "SWE",
            "location": "BENGALURU",
            "experience": {
                "total_years": 7.5,
                "level_id": "SR",
            },
        }
        profile, level, _ = assemble_candidate_profile(payload)
        assert profile.years_experience == 7.5
        assert profile.seniority == SeniorityLevel.SR.value
        assert level == 0

        flat_payload = {
            "occupation_id": "DATA",
            "location_id": "MUMBAI",
            "total_years": 3.0,
            "level_id": "MID",
        }
        flat_prof, _, _ = assemble_candidate_profile(flat_payload)
        assert flat_prof.years_experience == 3.0
        assert flat_prof.seniority == SeniorityLevel.MID.value

    def test_estimate_guarded_support_warning(self) -> None:
        """Test guarded support attaches GUARDED_SUPPORT_WIDER_INTERVALS warning."""
        mock_mgr = MagicMock(spec=ServingModelManager)
        mock_mgr.is_ready = True
        mock_mgr.model_version = "0.1.0"
        mock_mgr.active_bundle.metadata.canonical_snapshot_id = "test-snap-002"

        mock_pred = UnifiedPredictionResult(
            target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
            currency=Currency.INR.value,
            nominal_basis="LPA",
            p10=18.0,
            p50=28.0,
            p90=46.0,
            interval_width=28.0,
            nominal_coverage=0.80,
            status="guarded",
            is_abstained=False,
            evidence_grade="GRADE_B",
            support_status="GUARDED",
            source_quality_tier="TIER_B",
            reasons=["MODERATE_RECENCY_DECAY"],
            explanation="Guarded support due to observation age.",
            guidance=None,
            checks={},
            model_version="0.1.0",
        )
        mock_mgr.predict.return_value = mock_pred

        res = estimate(
            {"role": "SWE", "location": "PUNE", "years_experience": 5.0},
            manager=mock_mgr,
        )
        assert isinstance(res, Estimate)
        assert "GUARDED_SUPPORT_WIDER_INTERVALS" in res.warnings
        assert res.reliability.grade == "GRADE_B"

    def test_estimate_with_estimate_request_full_object(self) -> None:
        """Test estimate() with top-level EstimateRequest object and explicit as_of."""
        mock_mgr = MagicMock(spec=ServingModelManager)
        mock_mgr.is_ready = True
        mock_mgr.model_version = "0.1.0"
        mock_mgr.active_bundle.metadata.canonical_snapshot_id = "test-snap-003"

        mock_pred = UnifiedPredictionResult(
            target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
            currency=Currency.INR.value,
            nominal_basis="LPA",
            p10=25.0,
            p50=38.0,
            p90=58.0,
            interval_width=33.0,
            nominal_coverage=0.80,
            status="supported",
            is_abstained=False,
            evidence_grade="GRADE_A",
            support_status="SUPPORTED",
            source_quality_tier="TIER_A",
            reasons=[],
            explanation="",
            guidance=None,
            checks={},
            model_version="0.1.0",
        )
        mock_mgr.predict.return_value = mock_pred

        req = EstimateRequest(
            profile=ProfileRequest(
                occupation_id="SWE",
                location_id="BENGALURU",
                experience=ExperienceInput(total_years=8.0),
            ),
            measure="guaranteed_cash_annual",
            currency="INR",
            as_of="2026-06-30",
        )

        res = estimate(req, manager=mock_mgr)
        assert isinstance(res, Estimate)
        assert res.as_of == "2026-06-30"
        assert res.estimate.p50 == 38.0

    def test_estimate_with_wrapped_dict_and_flat_dict_with_current_comp(self) -> None:
        """Test estimate() with wrapped dict payload and flat dict with current_compensation."""
        mock_mgr = MagicMock(spec=ServingModelManager)
        mock_mgr.is_ready = True
        mock_mgr.model_version = "0.1.0"
        mock_mgr.active_bundle.metadata.canonical_snapshot_id = "test-snap-004"

        mock_pred = UnifiedPredictionResult(
            target_measure=CompensationMeasure.GUARANTEED_CASH_ANNUAL.value,
            currency=Currency.INR.value,
            nominal_basis="LPA",
            p10=20.0,
            p50=30.0,
            p90=45.0,
            interval_width=25.0,
            nominal_coverage=0.80,
            status="supported",
            is_abstained=False,
            evidence_grade="GRADE_A",
            support_status="SUPPORTED",
            source_quality_tier="TIER_A",
            reasons=[],
            explanation="",
            guidance=None,
            checks={},
            model_version="0.1.0",
        )
        mock_mgr.predict.return_value = mock_pred

        # 1. Wrapped dict: {"profile": {...}, "current_compensation": 32.0}
        wrapped = {
            "profile": {
                "occupation_id": "SWE",
                "location_id": "BENGALURU",
                "experience": {"total_years": 5.0},
            },
            "current_compensation": 32.0,
            "measure": "guaranteed_cash_annual",
            "currency": "INR",
            "as_of": "2026-05-01",
        }
        res1 = estimate(wrapped, manager=mock_mgr)
        assert isinstance(res1, Estimate)
        assert res1.as_of == "2026-05-01"
        assert res1.comparison is not None
        assert res1.comparison.current_compensation == 32.0

        # 2. Flat dict with current_compensation: {"role": "SWE", "location": "PUNE", ...}
        flat = {
            "role": "SWE",
            "location": "PUNE",
            "years_experience": 5.0,
            "current_compensation": 28.0,
        }
        res2 = estimate(flat, manager=mock_mgr)
        assert isinstance(res2, Estimate)
        assert res2.comparison is not None
        assert res2.comparison.current_compensation == 28.0
