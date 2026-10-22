"""Model bundle definition and serialization engine for ArthaIQ / CompIntel.

Provides the deployment bundle artifact packaging trained quantile models, conformal
calibrators, prediction support evaluators, feature schemas, training lineage, and
cryptographic SHA-256 manifests.

Adheres to:
- Rule R-MD-01: Grouped-temporal validation, champion promotion ladder.
- Rule R-MD-08: Thin-evidence abstention (N < 10) without lone point estimates.
- Rule R-MD-14: Model bundle with metadata, model card reference, and rollback capability.
- Rule R-UQ-01: Always output P10, P50, P90 with definitions and nominal coverage.
- Rule R-UQ-02: Abstention is a valid, designed result returning HTTP 200 payloads.
- Rule R-UQ-03: Marginal conformal coverage guarantees documented and exchangeability assumed.
- Rule R-UQ-07: Decoupled Evidence Framework (Source Quality Tier vs Prediction Support).
- Rule R-CD-01: Strict type annotations and runtime validations.
- Rule R-CD-03: Architectural dependency boundaries.
- Rule R-ER-04: Standardized abstention response payloads.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

import joblib
import polars as pl

from compintel.errors import ModelArtifactError
from compintel.logging import get_logger
from compintel.schema.enums import (
    CompensationMeasure,
    Currency,
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    RoleFamily,
    SeniorityLevel,
    TaxBasis,
)
from compintel.uncertainty.support import (
    CandidateProfile,
    CohortEvidenceContext,
    EvidenceGrade,
    SupportCheckResult,
    SupportEvaluator,
    SupportStatus,
)

if TYPE_CHECKING:
    from compintel.models.gbm.quantile import BaseGBMQuantileModel
    from compintel.uncertainty.conformal import CalibratedPrediction, ConformalQuantileRegressor
    from compintel.uncertainty.slice_conformal import SliceAdaptiveConformalRegressor

ProfileInput: TypeAlias = CandidateProfile
CohortEvidenceInput: TypeAlias = CohortEvidenceContext
SupportEvaluationResult: TypeAlias = SupportCheckResult

logger = get_logger(__name__)

CURRENT_BUNDLE_FORMAT_VERSION = "1.0.0"


# -----------------------------------------------------------------------------
# 1. Feature Schema Utilities
# -----------------------------------------------------------------------------


def compute_feature_schema_hash(feature_names: list[str]) -> str:
    """Compute deterministic SHA-256 digest of feature column schema."""
    canonical_repr = json.dumps(sorted(feature_names), sort_keys=True)
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 digest of a local file.

    For text-based artifacts (.md, .txt, .json, .yaml, .yml), line endings are normalized
    (\\r\\n -> \\n) before hashing to ensure identical cross-platform checksums.
    """
    hasher = hashlib.sha256()
    if file_path.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml"}:
        content = file_path.read_bytes().replace(b"\r\n", b"\n")
        hasher.update(content)
        return hasher.hexdigest()

    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


# -----------------------------------------------------------------------------
# 2. Prediction Result Types (PRD FR-02, FR-19, Rules R-UQ-01, R-UQ-02)
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class UnifiedPredictionResult:
    """Unified compensation intelligence prediction result for serving.

    Never returns a lone point estimate (Rule R-UQ-01). When support checks
    fail, returns status='abstained' with structured reasons (Rule R-UQ-02).
    """

    # Primary identification
    target_measure: str = CompensationMeasure.GUARANTEED_CASH_ANNUAL.value
    currency: str = Currency.INR.value
    pay_period: str = PayPeriod.ANNUAL.value
    tax_basis: str = TaxBasis.GROSS_PRETAX.value
    nominal_basis: str = "nominal INR LPA"
    as_of_date: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d"))

    # Core Quantiles (None when abstained)
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    interval_width: float | None = None
    nominal_coverage: float = 0.80

    # Decoupled Evidence Framework (Decision D-010, Rule R-UQ-07)
    status: str = "supported"  # 'supported', 'guarded', 'abstained'
    is_abstained: bool = False
    evidence_grade: str = EvidenceGrade.GRADE_B.value
    support_status: str = SupportStatus.SUPPORTED.value
    source_quality_tier: str = ProvenanceTier.TIER_B.value

    # Abstention & Guidance
    reasons: list[str] = field(default_factory=list)
    explanation: str = ""
    guidance: str = ""

    # Check Audit
    checks: dict[str, Any] = field(default_factory=dict)
    model_version: str = "0.1.0"

    def to_http_response(self) -> dict[str, Any]:
        """Format as standard HTTP 200 payload adhering to Rule R-UQ-02 / R-ER-04."""
        if self.is_abstained:
            return {
                "status": "abstained",
                "is_abstained": True,
                "target_measure": self.target_measure,
                "currency": self.currency,
                "nominal_basis": self.nominal_basis,
                "as_of_date": self.as_of_date,
                "evidence_grade": EvidenceGrade.ABSTAINED.value,
                "support_status": SupportStatus.ABSTAINED.value,
                "source_quality_tier": self.source_quality_tier,
                "reasons": self.reasons,
                "explanation": self.explanation,
                "guidance": self.guidance,
                "estimates": None,
                "checks": self.checks,
                "model_version": self.model_version,
            }

        return {
            "status": self.status,
            "is_abstained": False,
            "target_measure": self.target_measure,
            "currency": self.currency,
            "nominal_basis": self.nominal_basis,
            "as_of_date": self.as_of_date,
            "evidence_grade": self.evidence_grade,
            "support_status": self.support_status,
            "source_quality_tier": self.source_quality_tier,
            "reasons": [],
            "explanation": self.explanation,
            "guidance": self.guidance,
            "estimates": {
                "p10": self.p10,
                "p50": self.p50,
                "p90": self.p90,
                "interval_width": self.interval_width,
                "nominal_coverage": self.nominal_coverage,
            },
            "checks": self.checks,
            "model_version": self.model_version,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert prediction result to standard dictionary."""
        return asdict(self)


# -----------------------------------------------------------------------------
# 3. Bundle Metadata & Validation Results
# -----------------------------------------------------------------------------


@dataclass
class BundleMetadata:
    """Comprehensive provenance, configuration, and metric metadata for model bundles."""

    bundle_name: str
    model_version: str
    rung: str
    model_family: str
    target_variable: str = CompensationMeasure.GUARANTEED_CASH_ANNUAL.value
    target_unit: str = "nominal INR LPA"
    quantiles: list[float] = field(default_factory=lambda: [0.10, 0.50, 0.90])
    created_at_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    canonical_snapshot_id: str = "SNAP-1FF34A8E9633"
    git_commit_hash: str = "HEAD"
    preregistration_path: str = "experiments/preregistration/v1.yaml"
    feature_names: list[str] = field(default_factory=list)
    feature_schema_hash: str = ""
    sample_sizes: dict[str, int] = field(default_factory=dict)
    metrics_summary: dict[str, Any] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)
    bundle_format_version: str = CURRENT_BUNDLE_FORMAT_VERSION
    description: str = ""

    @property
    def files_manifest(self) -> dict[str, str]:
        """Return files manifest."""
        return self.files

    @property
    def bundle_sha256(self) -> str:
        """Compute aggregate bundle SHA-256 from file hashes."""
        sorted_hashes = "".join(f"{k}:{v}" for k, v in sorted(self.files.items()))
        return hashlib.sha256(sorted_hashes.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Convert bundle metadata to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BundleMetadata:
        """Create bundle metadata from dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class BundleValidationResult:
    """Outcome of model bundle structural and cryptographic validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class BundleSmokeTestResult:
    """Outcome of model bundle operational smoke testing at startup."""

    passed: bool
    latency_ms: float
    in_support_passed: bool = True
    abstention_passed: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert smoke test result to dictionary."""
        return asdict(self)


# -----------------------------------------------------------------------------
# 4. Model Bundle Core Class (Rules R-MD-14, R-UQ-01, R-UQ-02)
# -----------------------------------------------------------------------------


class ModelBundle:
    """Self-contained deployable model artifact for compensation prediction.

    Encompasses:
    1. Fitted base quantile regression model (Rung E CatBoost/LightGBM).
    2. Calibrated conformal uncertainty regressor (Rung F CQR).
    3. Prediction support & decoupled evidence evaluator (SupportEvaluator).
    4. Aggregated cohort evidence summary for fast S1-S5 support evaluation.
    5. Training lineage, git commit, and cryptographic checksum manifest.
    """

    def __init__(
        self,
        metadata: BundleMetadata,
        base_model: BaseGBMQuantileModel,
        calibrator: ConformalQuantileRegressor | SliceAdaptiveConformalRegressor,
        support_evaluator: SupportEvaluator,
        cohort_evidence_table: pl.DataFrame | None = None,
        model_card_markdown: str | None = None,
    ) -> None:
        """Initialize model bundle with all constituent components."""
        self.metadata = metadata
        self.base_model = base_model
        self.calibrator = calibrator
        self.support_evaluator = support_evaluator
        self.cohort_evidence_table = cohort_evidence_table
        self.model_card_markdown = model_card_markdown

    @property
    def model_version(self) -> str:
        """Return the semantic model version."""
        return self.metadata.model_version

    @property
    def rung(self) -> str:
        """Return the benchmark ladder rung identifier."""
        return self.metadata.rung

    def predict_profile(
        self,
        profile: ProfileInput,
        cohort_evidence: CohortEvidenceInput | None = None,
    ) -> UnifiedPredictionResult:
        """Execute end-to-end prediction with support evaluation and conformal bounds.

        Workflow:
        1. Evaluate prediction support via SupportEvaluator (S1-S5 checks).
        2. If support fails (abstention triggered): return structured abstention result.
        3. If support passes: run ConformalQuantileRegressor to obtain calibrated P10, P50, P90.
        4. Package and return UnifiedPredictionResult with evidence grades.
        """
        # Resolve cohort evidence from internal table if not supplied
        effective_evidence = cohort_evidence or self._lookup_cohort_evidence(profile)

        # 1. Run Support & Abstention Checks
        support_res: SupportEvaluationResult = self.support_evaluator.evaluate_support(
            profile=profile,
            evidence=effective_evidence,
        )

        if support_res.is_abstained:
            return UnifiedPredictionResult(
                target_measure=self.metadata.target_variable,
                currency=Currency.INR.value,
                nominal_basis=self.metadata.target_unit,
                status="abstained",
                is_abstained=True,
                evidence_grade=EvidenceGrade.ABSTAINED.value,
                support_status=SupportStatus.ABSTAINED.value,
                source_quality_tier=support_res.source_quality_tier.value,
                reasons=[r.value for r in support_res.reasons],
                explanation=support_res.explanation,
                guidance=support_res.guidance,
                checks={k: v.to_dict() for k, v in support_res.checks.items()},
                model_version=self.model_version,
            )

        # 2. Build feature DataFrame for conformal prediction
        profile_df = pl.DataFrame(
            {
                "role_family": [profile.role_family],
                "seniority": [profile.seniority],
                "location": [profile.location],
                "years_experience": [float(profile.years_experience)],
            }
        )

        # 3. Predict via ConformalQuantileRegressor
        cal_preds: list[CalibratedPrediction] = self.calibrator.predict(profile_df)
        pred: CalibratedPrediction = cal_preds[0]

        if (
            pred.is_abstained
            or pred.p10_calibrated is None
            or pred.p50 is None
            or pred.p90_calibrated is None
        ):
            return UnifiedPredictionResult(
                target_measure=self.metadata.target_variable,
                currency=Currency.INR.value,
                nominal_basis=self.metadata.target_unit,
                status="abstained",
                is_abstained=True,
                evidence_grade=support_res.evidence_grade.value,
                support_status=support_res.support_status.value,
                source_quality_tier=support_res.source_quality_tier.value,
                reasons=[r.value for r in support_res.reasons] or ["MODEL_ABSTENTION"],
                explanation=support_res.explanation,
                guidance=support_res.guidance,
                checks={k: v.to_dict() for k, v in support_res.checks.items()},
                model_version=self.model_version,
            )

        # Non-negative clamping (pay cannot be negative in nominal INR LPA)
        p10 = max(0.0, round(float(pred.p10_calibrated), 2))
        p50 = max(p10, round(float(pred.p50), 2))
        p90 = max(p50, round(float(pred.p90_calibrated), 2))
        interval_width = round(p90 - p10, 2)

        return UnifiedPredictionResult(
            target_measure=self.metadata.target_variable,
            currency=Currency.INR.value,
            nominal_basis=self.metadata.target_unit,
            p10=p10,
            p50=p50,
            p90=p90,
            interval_width=interval_width,
            nominal_coverage=self.calibrator.config.nominal_coverage,
            status=(
                "supported" if support_res.support_status == SupportStatus.SUPPORTED else "guarded"
            ),
            is_abstained=False,
            evidence_grade=support_res.evidence_grade.value,
            support_status=support_res.support_status.value,
            source_quality_tier=support_res.source_quality_tier.value,
            reasons=[],
            explanation=support_res.explanation,
            guidance=support_res.guidance,
            checks={k: v.to_dict() for k, v in support_res.checks.items()},
            model_version=self.model_version,
        )

    def _lookup_cohort_evidence(self, profile: ProfileInput) -> CohortEvidenceInput:
        """Look up aggregated cohort statistics from internal evidence table."""
        if self.cohort_evidence_table is None or self.cohort_evidence_table.is_empty():
            return CohortEvidenceInput(
                cohort_size=1,
                category_seen_count=1,
                median_observation_age_days=30.0,
                source_quality_score=75.0,
                provenance_tier="TIER_A",
                interval_width_lpa=0.85,
            )

        # Match on role_family, seniority, location
        filtered = self.cohort_evidence_table.filter(
            (pl.col("role_family") == profile.role_family)
            & (pl.col("seniority") == profile.seniority)
            & (pl.col("location") == profile.location)
        )

        if filtered.is_empty():
            # Return sparse/thin evidence triggering caution or abstention
            return CohortEvidenceInput(
                cohort_size=1,
                category_seen_count=1,
                median_observation_age_days=60.0,
                source_quality_score=70.0,
                provenance_tier="TIER_B",
                interval_width_lpa=1.10,
            )

        row = filtered.row(0, named=True)
        return CohortEvidenceInput(
            cohort_size=int(row.get("cohort_size", row.get("cohort_observation_count", 1))),
            category_seen_count=int(row.get("category_seen_count", 5)),
            median_observation_age_days=float(
                row.get(
                    "median_observation_age_days",
                    row.get("days_since_latest_observation", 30.0),
                )
            ),
            source_quality_score=float(row.get("source_quality_score", 75.0)),
            provenance_tier=str(row.get("provenance_tier", "TIER_A")),
            interval_width_lpa=(
                float(row["interval_width_lpa"])
                if row.get("interval_width_lpa") is not None
                else None
            ),
        )

    def validate(self) -> BundleValidationResult:
        """Validate internal integrity, component contracts, and schema consistency."""
        errors: list[str] = []
        warnings: list[str] = []

        # Check base model fitting
        if not getattr(self.base_model, "is_fitted", False):
            errors.append("Base model is not fitted.")

        # Check calibrator fitting
        if not getattr(self.calibrator, "is_calibrated", False):
            errors.append("Conformal calibrator is not calibrated.")

        # Check calibrator base model alignment
        if getattr(self.calibrator, "base_model", None) is not self.base_model:
            warnings.append("Calibrator reference does not point to identical base model instance.")

        # Check feature schema hash
        current_hash = compute_feature_schema_hash(self.metadata.feature_names)
        if current_hash != self.metadata.feature_schema_hash:
            errors.append(
                f"Feature schema hash mismatch: expected {self.metadata.feature_schema_hash}, "
                f"computed {current_hash}."
            )

        # Check thresholds
        floor = self.support_evaluator.config.support_checks.s1_cohort_size.abstention_floor
        if floor < 10:
            errors.append(
                f"S1 cohort abstention floor {floor} is below statutory minimum 10 (Rule R-MD-08)."
            )

        return BundleValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def smoke_test(self) -> BundleSmokeTestResult:
        """Execute operational startup smoke test on supported and abstained profiles."""
        details: dict[str, Any] = {}
        start_time = time.perf_counter()

        # Test Case 1: In-Support Standard Profile
        valid_profile = ProfileInput(
            role_family=RoleFamily.SWE.value,
            seniority=SeniorityLevel.SR.value,
            location=MetroLocation.BENGALURU.value,
            years_experience=5.0,
        )
        supported_evidence = CohortEvidenceInput(
            cohort_size=25,
            median_observation_age_days=45.0,
            category_seen_count=15,
            source_quality_score=85.0,
            provenance_tier=ProvenanceTier.TIER_A.value,
            interval_width_lpa=0.75,
        )

        res_valid = self.predict_profile(valid_profile, supported_evidence)
        in_support_passed = (
            not res_valid.is_abstained
            and res_valid.p10 is not None
            and res_valid.p50 is not None
            and res_valid.p90 is not None
            and (0.0 <= res_valid.p10 <= res_valid.p50 <= res_valid.p90)
            and res_valid.evidence_grade
            in (EvidenceGrade.GRADE_A.value, EvidenceGrade.GRADE_B.value)
        )
        details["in_support_test"] = {
            "passed": in_support_passed,
            "result": res_valid.to_dict(),
        }

        # Test Case 2: Thin Evidence Profile (N=1 cohort)
        thin_evidence = CohortEvidenceInput(
            cohort_size=1,
            median_observation_age_days=30.0,
            category_seen_count=1,
            source_quality_score=60.0,
            provenance_tier=ProvenanceTier.TIER_C.value,
            interval_width_lpa=1.50,
        )
        res_thin = self.predict_profile(valid_profile, thin_evidence)
        abstention_passed = (
            res_thin.is_abstained
            and res_thin.status == "abstained"
            and res_thin.p10 is None
            and res_thin.p50 is None
            and res_thin.p90 is None
            and len(res_thin.reasons) > 0
        )
        details["abstention_test"] = {
            "passed": abstention_passed,
            "result": res_thin.to_dict(),
        }

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        passed = in_support_passed and abstention_passed

        return BundleSmokeTestResult(
            passed=passed,
            latency_ms=round(latency_ms, 2),
            in_support_passed=in_support_passed,
            abstention_passed=abstention_passed,
            details=details,
        )

    def save(self, target_dir: Path | str) -> BundleMetadata:
        """Serialize and save complete model bundle with cryptographic manifest."""
        out_dir = Path(target_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        files_manifest: dict[str, str] = {}

        # 1. Save Base Quantile Model
        base_model_path = out_dir / "base_model.joblib"
        joblib.dump(self.base_model, base_model_path)
        files_manifest["base_model.joblib"] = compute_file_sha256(base_model_path)

        # 2. Save Conformal Calibrator
        calibrator_path = out_dir / "calibrator.joblib"
        joblib.dump(self.calibrator, calibrator_path)
        files_manifest["calibrator.joblib"] = compute_file_sha256(calibrator_path)

        # 3. Save Support Evaluator
        support_path = out_dir / "support_evaluator.joblib"
        joblib.dump(self.support_evaluator, support_path)
        files_manifest["support_evaluator.joblib"] = compute_file_sha256(support_path)

        # 4. Save Cohort Evidence Table (if available)
        if self.cohort_evidence_table is not None:
            evidence_path = out_dir / "cohort_evidence.parquet"
            self.cohort_evidence_table.write_parquet(evidence_path)
            files_manifest["cohort_evidence.parquet"] = compute_file_sha256(evidence_path)

        # 5. Save Model Card (if available)
        if self.model_card_markdown:
            card_path = out_dir / "model_card.md"
            card_path.write_text(self.model_card_markdown, encoding="utf-8")
            files_manifest["model_card.md"] = compute_file_sha256(card_path)

        # 6. Save Metadata & Manifest
        self.metadata.files = files_manifest
        meta_path = out_dir / "metadata.json"
        meta_dict = self.metadata.to_dict()
        meta_path.write_text(json.dumps(meta_dict, indent=2), encoding="utf-8")

        manifest_path = out_dir / "manifest.json"
        manifest_payload = {
            "bundle_name": self.metadata.bundle_name,
            "model_version": self.metadata.model_version,
            "format_version": CURRENT_BUNDLE_FORMAT_VERSION,
            "bundle_format_version": CURRENT_BUNDLE_FORMAT_VERSION,
            "created_at_utc": self.metadata.created_at_utc,
            "files": files_manifest,
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        logger.info(
            "model_bundle_saved",
            bundle_name=self.metadata.bundle_name,
            model_version=self.metadata.model_version,
            target_dir=str(out_dir),
            file_count=len(files_manifest) + 2,
        )
        return self.metadata

    @classmethod
    def load(cls, source_dir: Path | str, verify_checksums: bool = True) -> ModelBundle:
        """Load model bundle from directory with cryptographic checksum verification."""
        bundle_dir = Path(source_dir)
        if not bundle_dir.exists() or not bundle_dir.is_dir():
            msg = f"Model bundle directory not found: {bundle_dir}"
            raise ModelArtifactError(msg, code="BUNDLE_DIR_NOT_FOUND")

        manifest_path = bundle_dir / "manifest.json"
        metadata_path = bundle_dir / "metadata.json"

        if not manifest_path.exists():
            msg = f"Bundle manifest.json missing from {bundle_dir}."
            raise ModelArtifactError(msg, code="BUNDLE_MANIFEST_MISSING")

        if not metadata_path.exists():
            msg = f"Bundle metadata.json missing from {bundle_dir}."
            raise ModelArtifactError(msg, code="BUNDLE_METADATA_MISSING")

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        metadata_data = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata = BundleMetadata.from_dict(metadata_data)

        # Verify cryptographic checksums for all component files
        if verify_checksums:
            expected_files: dict[str, str] = manifest_data.get("files", {})
            for rel_path, expected_sha in expected_files.items():
                file_path = bundle_dir / rel_path
                if not file_path.exists():
                    msg = f"Model bundle file missing: {rel_path} in {bundle_dir}"
                    raise ModelArtifactError(msg, code="BUNDLE_FILE_MISSING")

                actual_sha = compute_file_sha256(file_path)
                if actual_sha != expected_sha:
                    msg = (
                        f"Cryptographic checksum verification failed for {rel_path}: "
                        f"expected {expected_sha}, got {actual_sha}."
                    )
                    raise ModelArtifactError(msg, code="BUNDLE_CHECKSUM_MISMATCH")

        # Load constituents
        base_model_path = bundle_dir / "base_model.joblib"
        calibrator_path = bundle_dir / "calibrator.joblib"
        support_path = bundle_dir / "support_evaluator.joblib"

        base_model: BaseGBMQuantileModel = joblib.load(base_model_path)
        calibrator: ConformalQuantileRegressor = joblib.load(calibrator_path)
        support_evaluator: SupportEvaluator = joblib.load(support_path)

        evidence_table: pl.DataFrame | None = None
        evidence_path = bundle_dir / "cohort_evidence.parquet"
        if evidence_path.exists():
            evidence_table = pl.read_parquet(evidence_path)

        model_card_md: str | None = None
        card_path = bundle_dir / "model_card.md"
        if card_path.exists():
            model_card_md = card_path.read_text(encoding="utf-8")

        bundle = cls(
            metadata=metadata,
            base_model=base_model,
            calibrator=calibrator,
            support_evaluator=support_evaluator,
            cohort_evidence_table=evidence_table,
            model_card_markdown=model_card_md,
        )

        validation = bundle.validate()
        if not validation.is_valid:
            msg = f"Loaded model bundle failed structural validation: {validation.errors}"
            raise ModelArtifactError(msg, code="BUNDLE_VALIDATION_FAILED")

        return bundle


# -----------------------------------------------------------------------------
# 5. Helper Factory Functions
# -----------------------------------------------------------------------------


def save_model_bundle(bundle: ModelBundle, target_dir: Path | str) -> BundleMetadata:
    """Save model bundle to target directory."""
    return bundle.save(target_dir)


def load_model_bundle(source_dir: Path | str, verify_checksums: bool = True) -> ModelBundle:
    """Load model bundle from directory."""
    return ModelBundle.load(source_dir, verify_checksums=verify_checksums)


def validate_model_bundle(bundle: ModelBundle | Path | str) -> BundleValidationResult:
    """Validate model bundle contracts and configuration."""
    if isinstance(bundle, str | Path):
        bundle = load_model_bundle(bundle, verify_checksums=False)
    return bundle.validate()
