"""Unit tests for feature specification and progressive personalization registry (Phase 6, T6.01).

Validates:
- All 22 candidate features have non-empty mandatory audit fields.
- Exact partition counts across levels L0 to L3 (4 L0, 7 L1, 6 L2, 5 L3).
- Lookup functions (get_feature, get_features_by_level, get_features_by_family, etc.).
- Strict Compare-Only invariant for current guaranteed cash (Rule R-MD-13, EXP-07).
- Absolute prohibition of protected demographic attributes (rules.md Sec 16 Rule 11).
- JSON serialization integrity.
"""

from __future__ import annotations

import json
import re

import pytest

from compintel.features import (
    FEATURE_REGISTRY,
    AblationDisposition,
    FeatureDataType,
    FeatureFamily,
    FeatureLevel,
    FeatureSpec,
    get_compare_only_features,
    get_feature,
    get_features_by_family,
    get_features_by_level,
    get_input_features,
)

EXPECTED_L0_IDS = {
    "feat_l0_role_family",
    "feat_l0_seniority",
    "feat_l0_location",
    "feat_l0_years_experience",
}

EXPECTED_L1_IDS = {
    "feat_l1_skills_primary",
    "feat_l1_skills_depth",
    "feat_l1_domain_specialization",
    "feat_l1_employer_tier",
    "feat_l1_work_arrangement",
    "feat_l1_career_velocity",
    "feat_l1_leadership_scope",
    "feat_l1_macro_market_regime",
}

EXPECTED_L2_IDS = {
    "feat_l2_target_employer_id",
    "feat_l2_target_level_code",
    "feat_l2_advertised_band_midpoint",
    "feat_l2_competing_offers_count",
    "feat_l2_notice_period_days",
    "feat_l2_search_urgency",
}

EXPECTED_L3_IDS = {
    "feat_l3_current_guaranteed_cash",
    "feat_l3_verified_payslip_level",
    "feat_l3_fixed_allowance_ratio",
    "feat_l3_project_scale_tier",
    "feat_l3_tenure_stability_index",
}

PROHIBITED_DEMOGRAPHIC_TERMS = {
    "gender",
    "sex",
    "caste",
    "tribe",
    "religion",
    "faith",
    "date_of_birth",
    "birthdate",
    "mother_tongue",
    "ethnicity",
    "marital",
    "dependents",
    "biometric",
}


@pytest.mark.unit
def test_feature_registry_integrity() -> None:
    """Verify registry contains exactly 22 uniquely identified features adhering to naming rules."""
    assert len(FEATURE_REGISTRY) == 23
    feature_ids = [feat.feature_id for feat in FEATURE_REGISTRY]
    assert len(set(feature_ids)) == 23

    pattern = re.compile(r"^feat_l[0-3]_[a-z0-9_]+$")
    for feat_id in feature_ids:
        assert pattern.match(feat_id) is not None, f"Feature ID '{feat_id}' does not match pattern."


@pytest.mark.unit
def test_mandatory_audit_fields_non_empty() -> None:
    """Verify all 23 candidate features have complete, non-empty mandatory audit fields."""
    for feat in FEATURE_REGISTRY:
        assert isinstance(feat, FeatureSpec)
        assert feat.feature_id.strip() != ""
        assert feat.display_name.strip() != ""
        assert isinstance(feat.level, FeatureLevel)
        assert isinstance(feat.family, FeatureFamily)
        assert isinstance(feat.data_type, FeatureDataType)
        assert len(feat.definition.strip()) >= 15
        assert len(feat.availability_timing.strip()) >= 10
        assert len(feat.data_source.strip()) >= 5
        assert len(feat.leakage_risk.strip()) >= 10
        assert len(feat.leakage_mitigations.strip()) >= 10
        assert len(feat.privacy_implications.strip()) >= 5
        assert len(feat.expected_utility.strip()) >= 10
        assert len(feat.ablation_plan.strip()) >= 10
        assert len(feat.ablation_threshold.strip()) >= 3
        assert isinstance(feat.disposition, AblationDisposition)
        assert isinstance(feat.is_input_feature, bool)


@pytest.mark.unit
def test_feature_partition_counts_by_level() -> None:
    """Verify exact feature counts and identifiers across levels L0 to L3."""
    l0_feats = get_features_by_level(FeatureLevel.L0_CORE)
    l1_feats = get_features_by_level(FeatureLevel.L1_ROLE_PROFILE)
    l2_feats = get_features_by_level(FeatureLevel.L2_TARGET_OPPORTUNITY)
    l3_feats = get_features_by_level(FeatureLevel.L3_ADDITIONAL_EVIDENCE)

    assert len(l0_feats) == 4
    assert len(l1_feats) == 8
    assert len(l2_feats) == 6
    assert len(l3_feats) == 5

    assert {f.feature_id for f in l0_feats} == EXPECTED_L0_IDS
    assert {f.feature_id for f in l1_feats} == EXPECTED_L1_IDS
    assert {f.feature_id for f in l2_feats} == EXPECTED_L2_IDS
    assert {f.feature_id for f in l3_feats} == EXPECTED_L3_IDS


@pytest.mark.unit
def test_all_level_0_are_accepted_core() -> None:
    """Verify all Level 0 features are marked as ACCEPTED_CORE invariants."""
    l0_feats = get_features_by_level(FeatureLevel.L0_CORE)
    for feat in l0_feats:
        assert feat.disposition == AblationDisposition.ACCEPTED_CORE
        assert feat.is_input_feature is True


@pytest.mark.unit
def test_feature_partition_by_family() -> None:
    """Verify filtering by FeatureFamily returns matching items and covers all families."""
    covered_families: set[FeatureFamily] = set()
    for family in FeatureFamily:
        feats = get_features_by_family(family)
        for f in feats:
            assert f.family == family
            covered_families.add(f.family)

    # All 7 families should have at least 1 feature
    assert len(covered_families) == len(FeatureFamily)


@pytest.mark.unit
def test_get_feature_lookup_success() -> None:
    """Verify get_feature returns correct spec for valid identifiers."""
    feat = get_feature("feat_l0_role_family")
    assert feat.feature_id == "feat_l0_role_family"
    assert feat.display_name == "Role Family"
    assert feat.level == FeatureLevel.L0_CORE
    assert feat.family == FeatureFamily.ROLE_RESPONSIBILITY


@pytest.mark.unit
def test_get_feature_lookup_not_found() -> None:
    """Verify get_feature raises KeyError with informative message for unknown IDs."""
    with pytest.raises(KeyError, match="Feature 'feat_unknown_xyz' is not registered"):
        get_feature("feat_unknown_xyz")


@pytest.mark.unit
def test_current_guaranteed_cash_compare_only_architecture() -> None:
    """Verify current pay is strictly Compare-Only and excluded from inputs (R-MD-13, EXP-07)."""
    current_pay = get_feature("feat_l3_current_guaranteed_cash")
    assert current_pay.is_input_feature is False
    assert current_pay.disposition == AblationDisposition.COMPARE_ONLY

    input_features = get_input_features()
    assert current_pay not in input_features
    assert "feat_l3_current_guaranteed_cash" not in {f.feature_id for f in input_features}

    compare_only_features = get_compare_only_features()
    assert current_pay in compare_only_features


@pytest.mark.unit
def test_input_and_compare_only_partition() -> None:
    """Verify partition between input features and non-input/compare-only features."""
    input_feats = get_input_features()
    compare_or_deferred = get_compare_only_features()

    assert all(f.is_input_feature for f in input_feats)
    assert all(
        not f.is_input_feature or f.disposition == AblationDisposition.COMPARE_ONLY
        for f in compare_or_deferred
    )

    # All L0 features must be input features
    l0_ids = {f.feature_id for f in get_features_by_level(FeatureLevel.L0_CORE)}
    assert l0_ids.issubset({f.feature_id for f in input_feats})


@pytest.mark.unit
def test_zero_protected_demographic_attributes() -> None:
    """Verify absolute absence of protected demographic attributes (rules.md Sec 16 Rule 11)."""
    for feat in FEATURE_REGISTRY:
        id_lower = feat.feature_id.lower()
        name_lower = feat.display_name.lower()
        def_lower = feat.definition.lower()

        for prohibited in PROHIBITED_DEMOGRAPHIC_TERMS:
            assert prohibited not in id_lower, (
                f"Prohibited term '{prohibited}' found in feature_id '{feat.feature_id}'"
            )
            assert prohibited not in name_lower, (
                f"Prohibited term '{prohibited}' found in display_name '{feat.display_name}'"
            )
            assert prohibited not in def_lower, (
                f"Prohibited term '{prohibited}' found in definition of '{feat.feature_id}'"
            )


@pytest.mark.unit
def test_feature_spec_to_dict_and_json_serializable() -> None:
    """Verify FeatureSpec.to_dict converts enums to string values and is JSON serializable."""
    for feat in FEATURE_REGISTRY:
        d = feat.to_dict()
        assert isinstance(d, dict)
        assert d["feature_id"] == feat.feature_id
        assert isinstance(d["level"], str)
        assert isinstance(d["family"], str)
        assert isinstance(d["data_type"], str)
        assert isinstance(d["disposition"], str)

        # Must serialize cleanly to JSON
        json_str = json.dumps(d)
        assert len(json_str) > 0
