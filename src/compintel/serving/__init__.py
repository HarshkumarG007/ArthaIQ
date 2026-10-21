"""Package initialization for compintel.serving.

Exposes:
- Pure estimation function: estimate(profile, as_of) -> Estimate | Abstained
- Response types: Estimate, Abstained, EstimateResult
- Request types: ProfileRequest, EstimateRequest, ExperienceInput
- Serving runtime manager: ServingModelManager, get_default_serving_manager
"""

from compintel.serving.app import app, create_app
from compintel.serving.core import (
    estimate,
    get_default_serving_manager,
    reset_default_serving_manager,
)
from compintel.serving.errors import ProblemDetails
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
    FeedbackSubmissionRequest,
    FeedbackSubmissionResponse,
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
    "FeedbackSubmissionRequest",
    "FeedbackSubmissionResponse",
    "ProblemDetails",
    "ProfileRequest",
    "QuantileSpan",
    "ReliabilityInfo",
    "ServingModelManager",
    "SourceMixItem",
    "app",
    "create_app",
    "estimate",
    "get_default_serving_manager",
    "reset_default_serving_manager",
]
