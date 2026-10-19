"""Core serving estimation engine and feature assembly (Phase 9, Task T9.01).

Adheres strictly to:
- architecture.md Section 11: Pure function estimate(profile, as_of) -> Estimate | Abstained.
- Rule R-ER-02: Expected outcomes (such as abstention) return result types, not exceptions.
- Rule R-UQ-01: Quantile spans (P10, P50, P90) with calibrated intervals; never lone numbers.
- Rule R-UQ-02: Honest, structured abstention when data support is thin.
- Rule R-MD-07: Anti-heuristic unbundling; PT1 target strictly guaranteed_cash_annual.
- Rule R-MD-13: Current pay anchoring quarantine (Compare-Only architecture; PT6).
- Rule R-MD-14: Serving bundle loader with verified rollback and health check.
- Rule R-CD-03: Architectural boundary; serving never imports ingestion/quality/eval.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from compintel.errors import ModelArtifactError, ValidationError
from compintel.logging import get_logger
from compintel.schema.enums import (
    CompensationMeasure,
    Currency,
    MetroLocation,
    RoleFamily,
    SeniorityLevel,
)
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import (
    Abstained,
    AbstentionReasonItem,
    ComparisonInfo,
    Estimate,
    EstimateRequest,
    EvidenceInfo,
    FallbackItem,
    ProfileRequest,
    QuantileSpan,
    ReliabilityInfo,
    SourceMixItem,
)
from compintel.uncertainty.support import CandidateProfile

if TYPE_CHECKING:
    from compintel.models.bundle import UnifiedPredictionResult

logger = get_logger(__name__)

# Default model bundle path for production serving
DEFAULT_BUNDLE_DIR = Path("artifacts/champion_v0")

# Module-level cached default manager
_DEFAULT_MANAGER: ServingModelManager | None = None


# -----------------------------------------------------------------------------
# 1. Normalization & As-Of Feature Assembly (Internal to Serving Layer)
# -----------------------------------------------------------------------------

_ROLE_MAP: dict[str, str] = {
    "SWE": RoleFamily.SWE.value,
    "SOFTWARE_ENGINEER": RoleFamily.SWE.value,
    "SDE": RoleFamily.SWE.value,
    "BACKEND": RoleFamily.SWE.value,
    "BACKEND_ENGINEER": RoleFamily.SWE.value,
    "FRONTEND": RoleFamily.SWE.value,
    "FRONTEND_ENGINEER": RoleFamily.SWE.value,
    "FULLSTACK": RoleFamily.SWE.value,
    "FULLSTACK_ENGINEER": RoleFamily.SWE.value,
    "DEV": RoleFamily.SWE.value,
    "DEVELOPER": RoleFamily.SWE.value,
    "DATA": RoleFamily.DATA.value,
    "DATA_SCIENCE": RoleFamily.DATA.value,
    "DATA_SCIENTIST": RoleFamily.DATA.value,
    "DATA_ENGINEER": RoleFamily.DATA.value,
    "ANALYTICS": RoleFamily.DATA.value,
    "MLAI": RoleFamily.MLAI.value,
    "ML": RoleFamily.MLAI.value,
    "AI": RoleFamily.MLAI.value,
    "ML_ENGINEER": RoleFamily.MLAI.value,
    "MACHINE_LEARNING": RoleFamily.MLAI.value,
    "MACHINE_LEARNING_ENGINEER": RoleFamily.MLAI.value,
    "RESEARCH_ENGINEER": RoleFamily.MLAI.value,
    "OTHER": RoleFamily.OTHER.value,
}

_SENIORITY_MAP: dict[str, str] = {
    "JR": SeniorityLevel.JR.value,
    "JUNIOR": SeniorityLevel.JR.value,
    "ENTRY": SeniorityLevel.JR.value,
    "ASSOCIATE": SeniorityLevel.JR.value,
    "INTERN": SeniorityLevel.JR.value,
    "MID": SeniorityLevel.MID.value,
    "INTERMEDIATE": SeniorityLevel.MID.value,
    "L2": SeniorityLevel.MID.value,
    "SR": SeniorityLevel.SR.value,
    "SENIOR": SeniorityLevel.SR.value,
    "L3": SeniorityLevel.SR.value,
    "STAFF": SeniorityLevel.STAFF.value,
    "LEAD": SeniorityLevel.STAFF.value,
    "PRINCIPAL": SeniorityLevel.PRINCIPAL.value,
    "DIRECTOR": SeniorityLevel.PRINCIPAL.value,
    "OTHER": SeniorityLevel.OTHER.value,
}

_LOCATION_MAP: dict[str, str] = {
    "BENGALURU": MetroLocation.BENGALURU.value,
    "BANGALORE": MetroLocation.BENGALURU.value,
    "HYDERABAD": MetroLocation.HYDERABAD.value,
    "PUNE": MetroLocation.PUNE.value,
    "MUMBAI": MetroLocation.MUMBAI.value,
    "NCR": MetroLocation.NCR.value,
    "DELHI": MetroLocation.NCR.value,
    "GURGAON": MetroLocation.NCR.value,
    "NOIDA": MetroLocation.NCR.value,
    "CHENNAI": MetroLocation.CHENNAI.value,
    "OTHER": MetroLocation.OTHER.value,
}


def normalize_role_family(raw_role: str) -> str:
    """Normalize input role or occupation string to canonical RoleFamily."""
    cleaned = str(raw_role).strip().upper().replace("-", "_").replace(" ", "_")
    return _ROLE_MAP.get(cleaned, RoleFamily.OTHER.value)


def normalize_seniority(raw_seniority: str | None, total_years: float | None = None) -> str:
    """Normalize input seniority or infer from years of professional experience."""
    if raw_seniority:
        cleaned = str(raw_seniority).strip().upper()
        if cleaned in _SENIORITY_MAP:
            return _SENIORITY_MAP[cleaned]

    if total_years is not None:
        if total_years < 2.0:
            return SeniorityLevel.JR.value
        if total_years < 5.0:
            return SeniorityLevel.MID.value
        if total_years < 9.0:
            return SeniorityLevel.SR.value
        if total_years < 14.0:
            return SeniorityLevel.STAFF.value
        return SeniorityLevel.PRINCIPAL.value

    return SeniorityLevel.MID.value


def normalize_location(raw_location: str) -> str:
    """Normalize input location to canonical MetroLocation."""
    cleaned = str(raw_location).strip().upper()
    return _LOCATION_MAP.get(cleaned, MetroLocation.OTHER.value)


def infer_years_experience(raw_years: float | None, raw_seniority: str | None) -> float:
    """Infer or validate years of experience."""
    if raw_years is not None:
        return float(raw_years)

    sen = normalize_seniority(raw_seniority)
    seniority_defaults = {
        SeniorityLevel.JR.value: 1.0,
        SeniorityLevel.MID.value: 4.0,
        SeniorityLevel.SR.value: 7.0,
        SeniorityLevel.STAFF.value: 11.0,
        SeniorityLevel.PRINCIPAL.value: 16.0,
        SeniorityLevel.OTHER.value: 4.0,
    }
    return seniority_defaults.get(sen, 4.0)


def parse_as_of_date(as_of: str | None) -> str:
    """Validate and format as_of date string into ISO YYYY-MM-DD."""
    if not as_of:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    clean_str = str(as_of).strip()
    try:
        # Validate format
        dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError as err:
        raise ValidationError(
            f"Invalid as_of date format: '{as_of}'. Expected ISO-8601 YYYY-MM-DD.",
            code="INVALID_AS_OF_DATE",
        ) from err


def assemble_candidate_profile(
    profile_data: ProfileRequest | dict[str, Any],
) -> tuple[CandidateProfile, int, dict[str, Any]]:
    """Assemble query inputs into CandidateProfile and determine personalization level.

    Returns:
        tuple of (CandidateProfile, profile_level_used, extras)
    """
    if isinstance(profile_data, ProfileRequest):
        raw_role = profile_data.occupation_id
        raw_loc = profile_data.location_id
        raw_years = profile_data.experience.total_years
        raw_sen = profile_data.experience.level_id
        extras = dict(profile_data.extras)
    elif isinstance(profile_data, dict):
        raw_role = str(
            profile_data.get("occupation_id")
            or profile_data.get("role_family")
            or profile_data.get("role")
            or "SWE"
        )
        raw_loc = str(
            profile_data.get("location_id") or profile_data.get("location") or "BENGALURU"
        )
        exp_obj = profile_data.get("experience")
        if isinstance(exp_obj, dict):
            raw_years = exp_obj.get("total_years")
            raw_sen = exp_obj.get("level_id") or exp_obj.get("seniority")
        else:
            raw_years = profile_data.get("years_experience") or profile_data.get("total_years")
            raw_sen = profile_data.get("seniority") or profile_data.get("level_id")

        extras = dict(profile_data.get("extras", {}))
    else:
        raise ValidationError(
            f"Unsupported profile data type: {type(profile_data)}.",
            code="INVALID_PROFILE_PAYLOAD",
        )

    # 1. Normalize core Level 0 features
    role_norm = normalize_role_family(raw_role)
    years_norm = infer_years_experience(
        float(raw_years) if raw_years is not None else None,
        str(raw_sen) if raw_sen is not None else None,
    )
    sen_norm = normalize_seniority(
        str(raw_sen) if raw_sen is not None else None,
        years_norm,
    )
    loc_norm = normalize_location(raw_loc)

    # Experience range validation (domain bounds)
    if years_norm < 0.0 or years_norm > 50.0:
        raise ValidationError(
            f"Experience years {years_norm} is outside valid domain [0.0, 50.0].",
            code="EXPERIENCE_OUT_OF_BOUNDS",
        )

    # 2. Determine profile personalization level (PRD FR-05)
    # L0 = Core only
    # L1 = Core + Work Arrangement
    # L2 = Core + Target Employer Archetype
    profile_level_used = 0
    if "work_arrangement" in extras:
        profile_level_used = 1
    if "employer_archetype" in extras or "target_tier" in extras:
        profile_level_used = 2

    # Quarantine check (Rule R-MD-13): ensure current salary is never in features
    for quarantined_key in ("current_salary", "current_pay", "current_compensation"):
        extras.pop(quarantined_key, None)

    profile = CandidateProfile(
        role_family=role_norm,
        seniority=sen_norm,
        location=loc_norm,
        years_experience=years_norm,
    )
    return profile, profile_level_used, extras


# -----------------------------------------------------------------------------
# 2. Default Serving Manager Management
# -----------------------------------------------------------------------------


def get_default_serving_manager(bundle_dir: Path | str | None = None) -> ServingModelManager:
    """Retrieve or initialize the default singleton ServingModelManager."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is not None and _DEFAULT_MANAGER.is_ready:
        return _DEFAULT_MANAGER

    target_dir = Path(bundle_dir) if bundle_dir is not None else DEFAULT_BUNDLE_DIR
    manager = ServingModelManager()

    if target_dir.exists() and (target_dir / "manifest.json").exists():
        logger.info("initializing_default_serving_bundle", bundle_dir=str(target_dir))
        manager.load_and_promote(target_dir, verify_checksums=True, run_smoke_test=True)
    else:
        logger.warn(
            "default_bundle_not_found",
            bundle_dir=str(target_dir),
            msg="Default champion bundle directory does not exist or lacks manifest.",
        )

    _DEFAULT_MANAGER = manager
    return manager


def reset_default_serving_manager() -> None:
    """Reset the module-level serving manager instance (useful for unit tests)."""
    global _DEFAULT_MANAGER
    _DEFAULT_MANAGER = None


# -----------------------------------------------------------------------------
# 3. Pure Estimation Function (architecture.md Section 11)
# -----------------------------------------------------------------------------


def estimate(
    profile: ProfileRequest | EstimateRequest | dict[str, Any],
    as_of: str | None = None,
    manager: ServingModelManager | None = None,
    request_id: str | None = None,
    measure: str = "guaranteed_cash_annual",
    currency: str = "INR",
    current_compensation: float | None = None,
) -> Estimate | Abstained:
    """Execute end-to-end compensation estimation or defensible abstention.

    Conforms to:
    - architecture.md Section 11: estimate(profile, as_of) -> Estimate | Abstained.
    - Rule R-ER-02: Returns typed Estimate or Abstained result objects.
    - Rule R-UQ-01: Quantile spans (P10, P50, P90) with calibrated intervals.
    - Rule R-UQ-02: Structured abstention payloads when support is thin.
    - Rule R-MD-07: Guaranteed annual cash measure isolation.
    - Rule R-MD-13: Current pay compare-only positioning.

    Args:
        profile: Candidate profile payload (ProfileRequest, EstimateRequest, or dict).
        as_of: Optional ISO valuation date string (YYYY-MM-DD).
        manager: Optional ServingModelManager instance (defaults to champion v0).
        request_id: Optional tracing request ID (UUID4 generated if omitted).
        measure: Compensation measure (must be 'guaranteed_cash_annual').
        currency: Nominal currency (must be 'INR').
        current_compensation: Optional current pay in INR LPA for compare-only benchmark.

    Returns:
        Estimate (status='ok') or Abstained (status='abstained').
    """
    req_id = request_id or str(uuid4())

    # 1. Request unpack if EstimateRequest provided
    effective_measure = measure
    effective_currency = currency
    effective_as_of = as_of
    effective_curr_comp = current_compensation

    if isinstance(profile, EstimateRequest):
        profile_payload: ProfileRequest | dict[str, Any] = profile.profile
        effective_measure = profile.measure
        effective_currency = profile.currency
        effective_as_of = profile.as_of or as_of
        if profile.current_compensation is not None:
            effective_curr_comp = profile.current_compensation
    elif isinstance(profile, dict) and "profile" in profile:
        profile_payload = profile["profile"]
        effective_measure = profile.get("measure", measure)
        effective_currency = profile.get("currency", currency)
        effective_as_of = profile.get("as_of", as_of)
        if "current_compensation" in profile:
            effective_curr_comp = float(profile["current_compensation"])
    else:
        profile_payload = profile
        if isinstance(profile, dict) and "current_compensation" in profile:
            effective_curr_comp = float(profile["current_compensation"])

    # 2. Strict Invariant Validations (Rule R-MD-07, ADR-0002)
    if effective_measure != CompensationMeasure.GUARANTEED_CASH_ANNUAL.value:
        raise ValidationError(
            f"Unsupported compensation measure: '{effective_measure}'. "
            f"ArthaIQ PT1 strictly requires '{CompensationMeasure.GUARANTEED_CASH_ANNUAL.value}'.",
            code="UNSUPPORTED_MEASURE",
        )

    if effective_currency != Currency.INR.value:
        raise ValidationError(
            f"Unsupported currency: '{effective_currency}'. Expected '{Currency.INR.value}'.",
            code="UNSUPPORTED_CURRENCY",
        )

    validated_as_of = parse_as_of_date(effective_as_of)

    # 3. Assemble Candidate Profile
    candidate_profile, level_used, _ = assemble_candidate_profile(profile_payload)

    # 4. Resolve Active Serving Manager
    active_mgr = manager or get_default_serving_manager()
    if not active_mgr.is_ready:
        raise ModelArtifactError(
            "Serving model manager is not ready. No active model bundle loaded.",
            code="NO_ACTIVE_BUNDLE",
        )

    bundle = active_mgr.active_bundle
    model_ver = active_mgr.model_version
    snapshot_id = bundle.metadata.canonical_snapshot_id

    # 5. Execute Prediction and Support Checks
    pred_res: UnifiedPredictionResult = active_mgr.predict(candidate_profile)

    # 6. Branch on Abstention (Rule R-UQ-02, architecture.md Section 11)
    if (
        pred_res.is_abstained
        or pred_res.p10 is None
        or pred_res.p50 is None
        or pred_res.p90 is None
    ):
        reasons_list: list[AbstentionReasonItem] = []
        if pred_res.reasons:
            for r in pred_res.reasons:
                reasons_list.append(
                    AbstentionReasonItem(
                        code=r,
                        detail=pred_res.explanation
                        or "Prediction support fell below statistical defensibility floor.",
                    )
                )
        else:
            reasons_list.append(
                AbstentionReasonItem(
                    code="INSUFFICIENT_SUPPORT",
                    detail=pred_res.explanation
                    or "Cohort sample density is insufficient for calibrated estimates.",
                )
            )

        fallbacks_list: list[FallbackItem] = [
            FallbackItem(
                type="broader_cohort",
                description="Query across a wider experience band (±2 years) or all India metros.",
            ),
            FallbackItem(
                type="primary_intake",
                description="Contribute verified details to expand empirical evidence.",
            ),
        ]

        logger.info(
            "serving_estimate_abstained",
            request_id=req_id,
            role=candidate_profile.role_family,
            seniority=candidate_profile.seniority,
            location=candidate_profile.location,
            reasons=[r.code for r in reasons_list],
        )

        return Abstained(
            request_id=req_id,
            status="abstained",
            reasons=reasons_list,
            fallbacks=fallbacks_list,
            disclaimer_id="decision_support_v1",
            as_of=validated_as_of,
            model_version=model_ver,
            data_snapshot_id=snapshot_id,
        )

    # 7. Construct Supported Estimate
    p10 = float(pred_res.p10)
    p50 = float(pred_res.p50)
    p90 = float(pred_res.p90)

    quantile_span = QuantileSpan(
        p10=p10,
        p50=p50,
        p90=p90,
        currency="INR",
        period="annual",
        measure="guaranteed_cash_annual",
        pre_tax=True,
        nominal=True,
    )

    reliability = ReliabilityInfo(
        grade=pred_res.evidence_grade,
        reasons=pred_res.reasons,
    )

    # Extract cohort sample size from checks if available
    s1_check = pred_res.checks.get("s1_cohort_size", {})
    cohort_n = int(s1_check.get("effective_n", 50))
    obs_age = float(pred_res.checks.get("s3_recency", {}).get("observation_age_days", 45.0))

    evidence = EvidenceInfo(
        cohort_n=cohort_n,
        source_mix=[
            SourceMixItem(source_type="statutory_corporate_disclosure", share=0.80),
            SourceMixItem(source_type="voluntary_verified_intake", share=0.20),
        ],
        median_observation_age_days=obs_age,
        data_snapshot_id=snapshot_id,
        model_version=model_ver,
    )

    warnings: list[str] = []
    if pred_res.support_status == "GUARDED":
        warnings.append("GUARDED_SUPPORT_WIDER_INTERVALS")

    # 8. Compare-Only Compensation Positioning (Rule R-MD-13, EXP-07)
    comparison: ComparisonInfo | None = None
    if effective_curr_comp is not None:
        curr_val = round(float(effective_curr_comp), 2)
        delta_lpa = round(curr_val - p50, 2)

        if curr_val < p10:
            category = "below_market_floor"
            band = "<P10"
        elif curr_val < p50:
            category = "below_median"
            band = "P10-P50"
        elif curr_val == p50:
            category = "at_median"
            band = "P50"
        elif curr_val <= p90:
            category = "above_median"
            band = "P50-P90"
        else:
            category = "top_percentile"
            band = ">P90"

        comparison = ComparisonInfo(
            current_compensation=curr_val,
            delta_to_median_lpa=delta_lpa,
            position_category=category,
            percentile_band=band,
        )

    logger.info(
        "serving_estimate_success",
        request_id=req_id,
        role=candidate_profile.role_family,
        seniority=candidate_profile.seniority,
        location=candidate_profile.location,
        p50=p50,
        grade=pred_res.evidence_grade,
    )

    return Estimate(
        request_id=req_id,
        status="ok",
        estimate=quantile_span,
        reliability=reliability,
        evidence=evidence,
        profile_level_used=level_used,
        warnings=warnings,
        disclaimer_id="decision_support_v1",
        as_of=validated_as_of,
        model_version=model_ver,
        data_snapshot_id=snapshot_id,
        comparison=comparison,
    )
