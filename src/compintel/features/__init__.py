"""Feature engineering, taxonomies, and progressive profiling specifications (Phase 6)."""

from compintel.features.spec import (
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

__all__ = [
    "FEATURE_REGISTRY",
    "AblationDisposition",
    "FeatureDataType",
    "FeatureFamily",
    "FeatureLevel",
    "FeatureSpec",
    "get_compare_only_features",
    "get_feature",
    "get_features_by_family",
    "get_features_by_level",
    "get_input_features",
]
