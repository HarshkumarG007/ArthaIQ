"""Package initialization for compintel.serving.

Exposes:
- Pure estimation function: estimate(profile, as_of) -> Estimate | Abstained
- Response types: Estimate, Abstained, EstimateResult
- Request types: ProfileRequest, EstimateRequest, ExperienceInput
- Serving runtime manager: ServingModelManager, get_default_serving_manager
"""

from compintel.serving.core import (
    estimate,
    get_default_serving_manager,
    reset_default_serving_manager,
)
from compintel.serving.loader import ServingModelManager
from compintel.serving.types import (
    Abstained,
    AbstentionReasonItem,
    ComparisonInfo,
    Estimate,
    EstimateRequest,
    EstimateResult,
    EvidenceInfo,
    ExperienceInput,
    FallbackItem,
    ProfileRequest,
    QuantileSpan,
    ReliabilityInfo,
    SourceMixItem,
)

__all__ = [
    "Abstained",
    "AbstentionReasonItem",
    "ComparisonInfo",
    "Estimate",
    "EstimateRequest",
    "EstimateResult",
    "EvidenceInfo",
    "ExperienceInput",
    "FallbackItem",
    "ProfileRequest",
    "QuantileSpan",
    "ReliabilityInfo",
    "ServingModelManager",
    "SourceMixItem",
    "estimate",
    "get_default_serving_manager",
    "reset_default_serving_manager",
]
