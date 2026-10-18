"""Serving bundle loader and runtime model manager for CompIntel (Phase 5, T5.08).

Implements the serving-layer bundle loader with startup validation, health checks,
canary readiness, and rollback capabilities adhering to architecture.md Section 8
and Rule R-MD-14.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from compintel.errors import ModelArtifactError
from compintel.logging import get_logger
from compintel.models.bundle import ModelBundle, UnifiedPredictionResult, load_model_bundle

if TYPE_CHECKING:
    from pathlib import Path

    from compintel.models.bundle import CohortEvidenceInput, ProfileInput

logger = get_logger(__name__)


class ServingModelManager:
    """Manages the active in-memory model bundle for the serving layer.

    Supports:
    - Atomic promotion of champion model bundles.
    - Startup validation and smoke testing.
    - Rollback to previous model bundle (Rule R-MD-14).
    - Health checks and metadata introspection.
    """

    def __init__(self, initial_bundle: ModelBundle | None = None) -> None:
        """Initialize serving model manager."""
        self._active_bundle: ModelBundle | None = initial_bundle
        self._previous_bundle: ModelBundle | None = None

    @property
    def is_ready(self) -> bool:
        """Return True if an active, validated bundle is loaded and ready for serving."""
        return self._active_bundle is not None

    @property
    def active_bundle(self) -> ModelBundle:
        """Return the current active model bundle."""
        if self._active_bundle is None:
            msg = "No active model bundle is loaded in serving manager."
            raise ModelArtifactError(msg, code="NO_ACTIVE_BUNDLE")
        return self._active_bundle

    @property
    def previous_bundle(self) -> ModelBundle | None:
        """Return the previously active bundle if available for rollback."""
        return self._previous_bundle

    @property
    def model_version(self) -> str:
        """Return the active model version."""
        return self.active_bundle.model_version

    @property
    def rung(self) -> str:
        """Return the active model rung."""
        return self.active_bundle.rung

    def load_and_promote(
        self,
        bundle_dir: Path | str,
        verify_checksums: bool = True,
        run_smoke_test: bool = True,
    ) -> ModelBundle:
        """Load a candidate model bundle, validate, smoke-test, and promote to active.

        Preserves the previous active bundle to guarantee tested rollback capability (R-MD-14).
        """
        logger.info("loading_candidate_bundle", bundle_dir=str(bundle_dir))
        candidate = load_model_bundle(bundle_dir, verify_checksums=verify_checksums)

        if run_smoke_test:
            smoke_res = candidate.smoke_test()
            if not smoke_res.passed:
                msg = f"Candidate bundle failed startup smoke test: {smoke_res.details}"
                raise ModelArtifactError(msg, code="SMOKE_TEST_FAILED")
            logger.info("bundle_smoke_test_passed", latency_ms=smoke_res.latency_ms)

        # Atomic promotion with rollback buffer
        self._previous_bundle = self._active_bundle
        self._active_bundle = candidate

        logger.info(
            "model_promoted_to_active",
            model_version=candidate.model_version,
            rung=candidate.rung,
        )
        return candidate

    def promote_bundle(
        self,
        bundle: ModelBundle,
        run_smoke_test: bool = True,
    ) -> ModelBundle:
        """Promote an in-memory ModelBundle directly to active with validation and smoke test."""
        val = bundle.validate()
        if not val.is_valid:
            msg = f"Candidate bundle failed structural validation: {val.errors}"
            raise ModelArtifactError(msg, code="BUNDLE_VALIDATION_FAILED")

        if run_smoke_test:
            smoke_res = bundle.smoke_test()
            if not smoke_res.passed:
                msg = f"Candidate bundle failed startup smoke test: {smoke_res.details}"
                raise ModelArtifactError(msg, code="SMOKE_TEST_FAILED")

        self._previous_bundle = self._active_bundle
        self._active_bundle = bundle
        return bundle

    def rollback(self) -> ModelBundle:
        """Roll back active bundle to the previous model version (Rule R-MD-14)."""
        if self._previous_bundle is None:
            msg = "Cannot roll back: no previous model bundle is available."
            raise ModelArtifactError(msg, code="ROLLBACK_UNAVAILABLE")

        rolled_back = self._previous_bundle
        self._previous_bundle = None
        self._active_bundle = rolled_back

        logger.warn(
            "model_rolled_back",
            active_version=self._active_bundle.model_version,
        )
        return self._active_bundle

    def predict(
        self,
        profile: ProfileInput,
        cohort_evidence: CohortEvidenceInput | None = None,
    ) -> UnifiedPredictionResult:
        """Serve prediction using the active model bundle."""
        return self.active_bundle.predict_profile(profile, cohort_evidence)

    def predict_profile(
        self,
        profile: ProfileInput,
        cohort_evidence: CohortEvidenceInput | None = None,
    ) -> UnifiedPredictionResult:
        """Serve prediction using the active model bundle (alias for predict)."""
        return self.predict(profile, cohort_evidence)

    def health_check(self) -> dict[str, Any]:
        """Produce serving health check status and model metadata."""
        if self._active_bundle is None:
            return {
                "status": "UNHEALTHY",
                "is_ready": False,
                "message": "No model bundle loaded.",
            }

        return {
            "status": "HEALTHY",
            "is_ready": True,
            "bundle_name": self._active_bundle.metadata.bundle_name,
            "model_version": self._active_bundle.model_version,
            "rung": self._active_bundle.rung,
            "target": self._active_bundle.metadata.target_variable,
            "created_at_utc": self._active_bundle.metadata.created_at_utc,
            "commit_hash": self._active_bundle.metadata.git_commit_hash,
            "has_rollback": self._previous_bundle is not None,
        }
