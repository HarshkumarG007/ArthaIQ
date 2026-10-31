"""Package initialization for compintel.serving.

Exposes:
- Pure estimation function: estimate(profile, as_of) -> Estimate | Abstained
- Response types: Estimate, Abstained, EstimateResult
- Request types: ProfileRequest, EstimateRequest, ExperienceInput
- Serving runtime manager: ServingModelManager, get_default_serving_manager
"""

from compintel.serving.app import app, create_app
from compintel.serving.batch_pipeline import (
    BatchInferencePipeline,
    BatchInferenceResponse,
    BatchInferenceResultItem,
    BatchInferenceSummary,
)
from compintel.serving.core import (
    estimate,
    get_default_serving_manager,
    reset_default_serving_manager,
)
from compintel.serving.counterfactual import (
    CounterfactualConfig,
    CounterfactualQuery,
    CounterfactualScenarioEngine,
    CounterfactualScenarioResponse,
    DualOfferComparisonResponse,
    IndiaNewTaxRegimeEngine,
    OfferStructure,
    ScenarioFrontierPoint,
    ScenarioType,
    TaxAdjustedTakeHome,
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
    "BatchInferencePipeline",
    "BatchInferenceResponse",
    "BatchInferenceResultItem",
    "BatchInferenceSummary",
    "ComparisonInfo",
    "CounterfactualConfig",
    "CounterfactualQuery",
    "CounterfactualScenarioEngine",
    "CounterfactualScenarioResponse",
    "DualOfferComparisonResponse",
    "Estimate",
    "EstimateRequest",
    "EstimateResult",
    "EvidenceInfo",
    "ExperienceInput",
    "FallbackItem",
    "FeedbackSubmissionRequest",
    "FeedbackSubmissionResponse",
    "IndiaNewTaxRegimeEngine",
    "OfferStructure",
    "ProblemDetails",
    "ProfileRequest",
    "QuantileSpan",
    "ReliabilityInfo",
    "ScenarioFrontierPoint",
    "ScenarioType",
    "ServingModelManager",
    "SourceMixItem",
    "TaxAdjustedTakeHome",
    "app",
    "create_app",
    "estimate",
    "get_default_serving_manager",
    "reset_default_serving_manager",
]
