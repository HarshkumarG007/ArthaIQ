"""Unit tests for Model Bundle, Serving Manager, and Champion Selection (Task T5.08).

Adheres strictly to:
- Rule R-MD-01: Benchmark ladder promotion rules (ADR-0004).
- Rule R-MD-02: Isolation of final 'test' partition.
- Rule R-MD-08: Mandatory thin-evidence abstention (N < 10).
- Rule R-MD-11: Strict synthetic data isolation from production artifacts.
- Rule R-MD-14: Model promotion, model card, and rollback capabilities.
- Rule R-UQ-01: Uncertainty quantification (P10, P50, P90).
- Rule R-UQ-02: Abstention is a designed result returning HTTP 200 payload.
- Rule R-TS-01, R-TS-03: Line coverage >= 90.0%.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from compintel.errors import DataContractError, ModelArtifactError
from compintel.evaluation.champion import (
    ChampionSelectionEvaluator,
    ChampionSelectionReport,
    build_champion_bundle,
)
from compintel.models.bundle import (
    BundleMetadata,
    BundleSmokeTestResult,
    BundleValidationResult,
    CandidateProfile,
    CohortEvidenceContext,
    ModelBundle,
    UnifiedPredictionResult,
    compute_feature_schema_hash,
    load_model_bundle,
)
from compintel.models.gbm.config import GBMModelType, GBMQuantileConfig
from compintel.models.gbm.quantile import (
    FEATURE_COLS_CATEGORICAL,
    FEATURE_COLS_CONTINUOUS,
    CatBoostQuantileModel,
)
from compintel.serving.loader import ServingModelManager
from compintel.uncertainty.conformal import ConformalConfig, ConformalQuantileRegressor
from compintel.uncertainty.support import SupportEvaluator

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def sample_features() -> list[str]:
    """Sample feature names."""
    return ["role_family", "seniority", "location", "years_experience"]


@pytest.fixture
def sample_train_df() -> pl.DataFrame:
    """Fixture providing diverse training observations."""
    return pl.DataFrame(
        {
            "role_family": [
                "SWE",
                "DATA",
                "SWE",
                "MLAI",
                "SWE",
                "DATA",
                "SWE",
                "SWE",
                "DATA",
                "MLAI",
                "SWE",
                "DATA",
            ],
            "seniority": [
                "MID",
                "SR",
                "JR",
                "STAFF",
                "SR",
                "MID",
                "MID",
                "SR",
                "JR",
                "MID",
                "STAFF",
                "SR",
            ],
            "location": [
                "BENGALURU",
                "HYDERABAD",
                "BENGALURU",
                "PUNE",
                "BENGALURU",
                "MUMBAI",
                "BENGALURU",
                "HYDERABAD",
                "BENGALURU",
                "PUNE",
                "BENGALURU",
                "NCR",
            ],
            "years_experience": [
                4.0,
                8.5,
                1.5,
                12.0,
                7.5,
                5.0,
                3.5,
                9.0,
                1.0,
                4.5,
                13.0,
                8.0,
            ],
            "guaranteed_cash_annual": [
                18.0,
                32.0,
                10.5,
                55.0,
                35.0,
                22.0,
                16.0,
                38.0,
                9.5,
                26.0,
                58.0,
                31.0,
            ],
            "as_of_date": [
                "2023-01-15",
                "2023-02-10",
                "2023-03-05",
                "2023-04-12",
                "2023-05-18",
                "2023-06-20",
                "2023-07-15",
                "2023-08-10",
                "2023-09-05",
                "2023-10-12",
                "2023-11-18",
                "2023-12-20",
            ],
            "person_cluster_id": [f"PID_{i:04d}" for i in range(12)],
            "observation_id": [f"OBS_{i:04d}" for i in range(12)],
            "source_quality_score": [85.0] * 12,
            "provenance_tier": ["TIER_A"] * 12,
            "is_pt1_eligible": [True] * 12,
            "is_synthetic": [False] * 12,
        }
    )


@pytest.fixture
def sample_cal_df() -> pl.DataFrame:
    """Fixture providing calibration observations."""
    return pl.DataFrame(
        {
            "role_family": ["SWE", "DATA", "SWE", "MLAI", "DATA", "SWE"],
            "seniority": ["MID", "JR", "SR", "MID", "SR", "JR"],
            "location": ["BENGALURU", "BENGALURU", "HYDERABAD", "PUNE", "NCR", "BENGALURU"],
            "years_experience": [3.5, 2.0, 7.0, 5.5, 9.0, 1.2],
            "guaranteed_cash_annual": [17.5, 12.0, 30.0, 24.5, 36.0, 10.0],
            "as_of_date": [
                "2024-01-15",
                "2024-02-10",
                "2024-03-05",
                "2024-04-12",
                "2024-05-18",
                "2024-06-20",
            ],
            "person_cluster_id": [f"PID_CAL_{i:04d}" for i in range(6)],
            "observation_id": [f"OBS_CAL_{i:04d}" for i in range(6)],
            "source_quality_score": [85.0] * 6,
            "provenance_tier": ["TIER_A"] * 6,
            "is_pt1_eligible": [True] * 6,
            "is_synthetic": [False] * 6,
        }
    )


@pytest.fixture
def sample_select_df() -> pl.DataFrame:
    """Fixture providing select/tuning observations."""
    return pl.DataFrame(
        {
            "role_family": ["SWE", "DATA", "MLAI", "SWE"],
            "seniority": ["SR", "MID", "SR", "MID"],
            "location": ["BENGALURU", "MUMBAI", "PUNE", "HYDERABAD"],
            "years_experience": [8.0, 4.5, 7.0, 4.0],
            "guaranteed_cash_annual": [36.0, 21.0, 34.0, 19.0],
            "as_of_date": ["2024-07-15", "2024-08-10", "2024-09-05", "2024-10-12"],
            "person_cluster_id": [f"PID_SEL_{i:04d}" for i in range(4)],
            "observation_id": [f"OBS_SEL_{i:04d}" for i in range(4)],
            "source_quality_score": [85.0] * 4,
            "provenance_tier": ["TIER_A"] * 4,
            "is_pt1_eligible": [True] * 4,
            "is_synthetic": [False] * 4,
        }
    )


@pytest.fixture
def sample_cohort_table() -> pl.DataFrame:
    """Fixture providing aggregated cohort evidence table."""
    return pl.DataFrame(
        {
            "role_family": ["SWE", "DATA"],
            "seniority": ["SR", "MID"],
            "location": ["BENGALURU", "HYDERABAD"],
            "cohort_size": [25, 18],
            "category_seen_count": [15, 12],
            "median_observation_age_days": [45.0, 60.0],
            "source_quality_score": [85.0, 80.0],
            "provenance_tier": ["TIER_A", "TIER_A"],
            "interval_width_lpa": [3.80, 4.20],
        }
    )


@pytest.fixture
def fitted_bundle(
    sample_train_df: pl.DataFrame,
    sample_cal_df: pl.DataFrame,
    sample_cohort_table: pl.DataFrame,
) -> ModelBundle:
    """Fixture providing a complete, fitted, calibrated, and validated ModelBundle."""
    # 1. Base model
    quant_cfg = GBMQuantileConfig(
        model_type=GBMModelType.CATBOOST,
        random_seed=42,
        n_estimators=10,
    )
    base_model = CatBoostQuantileModel(quant_cfg)
    base_model.fit(sample_train_df)

    # 2. Calibrator
    conf_cfg = ConformalConfig(nominal_coverage=0.80)
    calibrator = ConformalQuantileRegressor(base_model=base_model, config=conf_cfg)
    calibrator.calibrate(sample_cal_df)

    # 3. Support evaluator
    support_evaluator = SupportEvaluator()

    # 4. Metadata
    features = FEATURE_COLS_CATEGORICAL + FEATURE_COLS_CONTINUOUS
    meta = BundleMetadata(
        bundle_name="test-champion-bundle",
        model_version="0.1.0",
        rung="Rung F (CatBoost CQR + Decoupled Support)",
        model_family="CatBoostQuantileModel",
        feature_names=features,
        feature_schema_hash=compute_feature_schema_hash(features),
        canonical_snapshot_id="SNAP-TEST-001",
        git_commit_hash="abc1234",
    )

    return ModelBundle(
        metadata=meta,
        base_model=base_model,
        calibrator=calibrator,
        support_evaluator=support_evaluator,
        cohort_evidence_table=sample_cohort_table,
        model_card_markdown="# Test Model Card\nValid content.",
    )


# ==============================================================================
# Unit Tests: Feature Schema & Bundle Metadata
# ==============================================================================


def test_feature_schema_hash_deterministic(sample_features: list[str]) -> None:
    """Test feature schema hash is deterministic and order-invariant."""
    h1 = compute_feature_schema_hash(sample_features)
    h2 = compute_feature_schema_hash(list(reversed(sample_features)))
    assert h1 == h2
    assert len(h1) == 64  # SHA-256


def test_bundle_metadata_roundtrip(sample_features: list[str]) -> None:
    """Test BundleMetadata serialization and deserialization."""
    meta = BundleMetadata(
        bundle_name="test-bundle",
        model_version="1.2.3",
        rung="Rung F",
        model_family="CatBoost",
        feature_names=sample_features,
        feature_schema_hash=compute_feature_schema_hash(sample_features),
    )
    d = meta.to_dict()
    restored = BundleMetadata.from_dict(d)
    assert restored.bundle_name == meta.bundle_name
    assert restored.model_version == meta.model_version
    assert restored.feature_schema_hash == meta.feature_schema_hash


# ==============================================================================
# Unit Tests: Unified Prediction Result & HTTP 200 Payloads
# ==============================================================================


def test_unified_prediction_result_supported() -> None:
    """Test supported UnifiedPredictionResult to HTTP 200 payload (Rule R-UQ-01)."""
    res = UnifiedPredictionResult(
        target_measure="guaranteed_cash_annual",
        p10=25.0,
        p50=32.0,
        p90=40.0,
        interval_width=15.0,
        nominal_coverage=0.80,
        status="supported",
        is_abstained=False,
        evidence_grade="GRADE_A",
        support_status="SUPPORTED",
        source_quality_tier="TIER_A",
        reasons=[],
        explanation="Robust empirical evidence.",
        guidance="Reliable market benchmark.",
        checks={"S1": {"passed": True}},
        model_version="0.1.0",
    )
    d = res.to_dict()
    assert d["p50"] == 32.0
    assert not d["is_abstained"]

    http_resp = res.to_http_response()
    assert http_resp["status"] == "supported"
    assert not http_resp["is_abstained"]
    assert http_resp["estimates"]["p10"] == 25.0
    assert http_resp["estimates"]["p50"] == 32.0
    assert http_resp["estimates"]["p90"] == 40.0


def test_unified_prediction_result_abstained() -> None:
    """Test abstained UnifiedPredictionResult to HTTP 200 payload (Rule R-UQ-02, R-ER-04)."""
    res = UnifiedPredictionResult(
        target_measure="guaranteed_cash_annual",
        p10=None,
        p50=None,
        p90=None,
        interval_width=None,
        status="abstained",
        is_abstained=True,
        evidence_grade="ABSTAINED",
        support_status="ABSTAINED",
        source_quality_tier="TIER_C",
        reasons=["THIN_COHORT_EVIDENCE"],
        explanation="Evidence is below statutory reliability threshold.",
        guidance="Consider broadening your profile filters.",
        checks={"S1": {"passed": False}},
        model_version="0.1.0",
    )
    d = res.to_dict()
    assert d["is_abstained"]
    assert d["p50"] is None

    http_resp = res.to_http_response()
    assert http_resp["status"] == "abstained"
    assert http_resp["is_abstained"]
    assert http_resp["estimates"] is None
    assert "THIN_COHORT_EVIDENCE" in http_resp["reasons"]


def test_validation_and_smoke_test_results_to_dict() -> None:
    """Test BundleValidationResult and BundleSmokeTestResult serialization."""
    val_res = BundleValidationResult(is_valid=True, errors=[], warnings=["Check memory."])
    val_dict = val_res.to_dict()
    assert val_dict["is_valid"]
    assert "Check memory." in val_dict["warnings"]

    smoke_res = BundleSmokeTestResult(passed=True, latency_ms=12.5, details={"ok": True})
    smoke_dict = smoke_res.to_dict()
    assert smoke_dict["passed"]
    assert smoke_dict["latency_ms"] == 12.5


# ==============================================================================
# Unit Tests: ModelBundle Save, Load, Validation, and Tamper Detection
# ==============================================================================


def test_model_bundle_save_and_load(fitted_bundle: ModelBundle, tmp_path: Path) -> None:
    """Test full saving and loading lifecycle with manifest verification."""
    bundle_dir = tmp_path / "champion_v0"
    saved_meta = fitted_bundle.save(bundle_dir)
    assert saved_meta.bundle_sha256 != ""
    assert len(saved_meta.files_manifest) >= 5

    # Verify manifest exists and is valid JSON
    manifest_path = bundle_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["format_version"] == "1.0.0"
    assert "base_model.joblib" in manifest["files"]
    assert "calibrator.joblib" in manifest["files"]
    assert "support_evaluator.joblib" in manifest["files"]

    # Load bundle back
    loaded_bundle = load_model_bundle(bundle_dir)
    assert loaded_bundle.model_version == "0.1.0"
    assert loaded_bundle.rung == "Rung F (CatBoost CQR + Decoupled Support)"
    assert loaded_bundle.model_card_markdown is not None

    # Run smoke test on loaded bundle
    smoke_res = loaded_bundle.smoke_test()
    assert smoke_res.passed


def test_model_bundle_tamper_detection(fitted_bundle: ModelBundle, tmp_path: Path) -> None:
    """Test that tampering with any bundle asset raises ModelArtifactError (Rule R-MD-14)."""
    bundle_dir = tmp_path / "champion_tamper"
    fitted_bundle.save(bundle_dir)

    # 1. Corrupt a weight file by appending bytes
    weights_path = bundle_dir / "base_model.joblib"
    with open(weights_path, "ab") as f:
        f.write(b"CORRUPTED_BYTES")

    with pytest.raises(ModelArtifactError) as exc_info:
        load_model_bundle(bundle_dir)
    assert exc_info.value.code in ("MANIFEST_HASH_MISMATCH", "BUNDLE_CHECKSUM_MISMATCH")

    # 2. Test missing file
    weights_path.unlink()
    with pytest.raises(ModelArtifactError) as exc_info:
        load_model_bundle(bundle_dir)
    assert exc_info.value.code == "BUNDLE_FILE_MISSING"

    # 3. Test missing manifest
    (bundle_dir / "manifest.json").unlink()
    with pytest.raises(ModelArtifactError) as exc_info:
        load_model_bundle(bundle_dir)
    assert exc_info.value.code in ("MANIFEST_MISSING", "BUNDLE_MANIFEST_MISSING")

    # 4. Test non-existent directory
    with pytest.raises(ModelArtifactError) as exc_info:
        load_model_bundle(tmp_path / "non_existent_bundle")
    assert exc_info.value.code == "BUNDLE_DIR_NOT_FOUND"


def test_model_bundle_validation_checks(fitted_bundle: ModelBundle) -> None:
    """Test bundle.validate() detects integrity and configuration flaws."""
    val_res = fitted_bundle.validate()
    assert val_res.is_valid

    # Corrupt feature schema hash
    corrupt_meta = fitted_bundle.metadata.to_dict()
    corrupt_meta["feature_schema_hash"] = "invalid_hash_0000000000"
    fitted_bundle.metadata = BundleMetadata.from_dict(corrupt_meta)

    val_res_bad = fitted_bundle.validate()
    assert not val_res_bad.is_valid
    assert any("schema hash mismatch" in err for err in val_res_bad.errors)


# ==============================================================================
# Unit Tests: Prediction Logic & Decoupled Support in Bundle
# ==============================================================================


def test_model_bundle_predict_profile_supported(fitted_bundle: ModelBundle) -> None:
    """Test predict_profile with supported evidence returns valid quantiles."""
    profile = CandidateProfile(
        role_family="SWE",
        seniority="SR",
        location="BENGALURU",
        years_experience=7.0,
    )
    evidence = CohortEvidenceContext(
        cohort_size=25,
        median_observation_age_days=30.0,
        category_seen_count=15,
        source_quality_score=85.0,
        provenance_tier="TIER_A",
        interval_width_lpa=3.80,
    )

    pred = fitted_bundle.predict_profile(profile, evidence)
    assert not pred.is_abstained
    assert pred.p10 is not None and pred.p50 is not None and pred.p90 is not None
    assert 0.0 <= pred.p10 <= pred.p50 <= pred.p90
    assert pred.evidence_grade in ("GRADE_A", "GRADE_B")
    assert pred.interval_width == round(pred.p90 - pred.p10, 2)


def test_model_bundle_predict_profile_thin_evidence_abstains(
    fitted_bundle: ModelBundle,
) -> None:
    """Test predict_profile with thin evidence (< 10) abstains per Rule R-MD-08."""
    profile = CandidateProfile(
        role_family="SWE",
        seniority="SR",
        location="BENGALURU",
        years_experience=7.0,
    )
    thin_evidence = CohortEvidenceContext(
        cohort_size=2,  # Thin evidence < 10
        median_observation_age_days=30.0,
        category_seen_count=1,
        source_quality_score=60.0,
        provenance_tier="TIER_C",
        interval_width_lpa=1.50,
    )

    pred = fitted_bundle.predict_profile(profile, thin_evidence)
    assert pred.is_abstained
    assert pred.status == "abstained"
    assert pred.p10 is None
    assert pred.p50 is None
    assert pred.p90 is None
    assert len(pred.reasons) > 0


def test_model_bundle_cohort_table_lookup(fitted_bundle: ModelBundle) -> None:
    """Test cohort evidence auto-lookup when not supplied in predict_profile."""
    # Profile present in cohort table
    known_profile = CandidateProfile(
        role_family="SWE",
        seniority="SR",
        location="BENGALURU",
        years_experience=7.0,
    )
    pred_known = fitted_bundle.predict_profile(known_profile)
    assert not pred_known.is_abstained

    # Profile missing from cohort table -> triggers thin-evidence fallback
    unknown_profile = CandidateProfile(
        role_family="UNKNOWN_ROLE",
        seniority="MID",
        location="RURAL",
        years_experience=5.0,
    )
    pred_unknown = fitted_bundle.predict_profile(unknown_profile)
    assert pred_unknown.is_abstained


# ==============================================================================
# Unit Tests: ServingModelManager Lifecycle & Tested Rollback (Rule R-MD-14)
# ==============================================================================


def test_serving_model_manager_promotion_and_rollback(
    fitted_bundle: ModelBundle,
    tmp_path: Path,
) -> None:
    """Test ServingModelManager atomic promotion, health checks, and rollback."""
    manager = ServingModelManager()
    assert not manager.is_ready
    assert manager.health_check()["status"] in ("uninitialized", "UNHEALTHY")

    # Predicting when uninitialized raises ModelArtifactError
    profile = CandidateProfile(
        role_family="SWE",
        seniority="SR",
        location="BENGALURU",
        years_experience=7.0,
    )
    with pytest.raises(ModelArtifactError):
        manager.predict_profile(profile)

    # Rollback when no prior bundle raises ModelArtifactError
    with pytest.raises(ModelArtifactError):
        manager.rollback()

    # 1. Save and promote bundle v1
    dir_v1 = tmp_path / "bundle_v1"
    fitted_bundle.metadata.model_version = "0.1.0"
    fitted_bundle.save(dir_v1)
    bundle_v1 = load_model_bundle(dir_v1)

    assert manager.previous_bundle is None
    manager.promote_bundle(bundle_v1)
    assert manager.is_ready
    assert manager.model_version == "0.1.0"
    assert "Rung F" in manager.rung
    assert manager.health_check()["status"] in ("healthy", "HEALTHY")

    # Prediction works through manager
    pred = manager.predict_profile(profile)
    assert not pred.is_abstained
    pred_alias = manager.predict(profile)
    assert not pred_alias.is_abstained

    # 2. Promote bundle v2
    dir_v2 = tmp_path / "bundle_v2"
    fitted_bundle.metadata.model_version = "0.2.0"
    fitted_bundle.save(dir_v2)
    bundle_v2 = load_model_bundle(dir_v2)

    manager.promote_bundle(bundle_v2)
    assert manager.model_version == "0.2.0"
    assert manager.previous_bundle is not None

    # 3. Test rollback capability (Rule R-MD-14)
    rolled_back = manager.rollback()
    assert rolled_back.model_version == "0.1.0"
    assert manager.model_version == "0.1.0"

    # Rollback again when history exhausted raises ModelArtifactError
    with pytest.raises(ModelArtifactError):
        manager.rollback()


def test_serving_model_manager_load_and_promote_and_error_cases(
    fitted_bundle: ModelBundle,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test ServingModelManager load_and_promote and error recovery branches."""
    manager = ServingModelManager()
    assert not manager.is_ready
    hc = manager.health_check()
    assert hc["status"] == "UNHEALTHY"
    assert not hc["is_ready"]

    bundle_dir = tmp_path / "load_promote_bundle"
    fitted_bundle.save(bundle_dir)

    # 1. load_and_promote successfully
    loaded = manager.load_and_promote(bundle_dir, verify_checksums=True, run_smoke_test=True)
    assert loaded.model_version == fitted_bundle.model_version
    assert manager.is_ready

    # 2. load_and_promote with failing smoke test raises ModelArtifactError
    def fake_failing_smoke_test(self: ModelBundle) -> BundleSmokeTestResult:
        return BundleSmokeTestResult(passed=False, latency_ms=10.0, details={"error": "mock_fail"})

    monkeypatch.setattr(ModelBundle, "smoke_test", fake_failing_smoke_test)
    with pytest.raises(ModelArtifactError, match="Candidate bundle failed startup smoke test"):
        manager.load_and_promote(bundle_dir, run_smoke_test=True)

    # 3. promote_bundle with failing smoke test raises ModelArtifactError
    with pytest.raises(ModelArtifactError, match="Candidate bundle failed startup smoke test"):
        manager.promote_bundle(fitted_bundle, run_smoke_test=True)

    monkeypatch.undo()

    # 4. promote_bundle with validation failure raises ModelArtifactError
    def fake_failing_validate(self: ModelBundle) -> BundleValidationResult:
        return BundleValidationResult(is_valid=False, errors=["mock structural failure"])

    monkeypatch.setattr(ModelBundle, "validate", fake_failing_validate)
    with pytest.raises(ModelArtifactError, match="failed structural validation"):
        manager.promote_bundle(fitted_bundle)


# ==============================================================================
# Unit Tests: Champion Selection Evaluator & Pre-registered Rules
# ==============================================================================


def test_champion_selection_evaluator_candidates(
    sample_train_df: pl.DataFrame,
    sample_cal_df: pl.DataFrame,
    sample_select_df: pl.DataFrame,
    tmp_path: Path,
) -> None:
    """Test ChampionSelectionEvaluator compares ladder and promotes Rung F."""
    evaluator = ChampionSelectionEvaluator(seed=42)
    report = evaluator.evaluate_candidates(
        train_df=sample_train_df,
        calibrate_df=sample_cal_df,
        select_df=sample_select_df,
        snapshot_id="SNAP-TEST-001",
        commit_hash="abc1234",
    )

    assert isinstance(report, ChampionSelectionReport)
    assert report.champion_candidate_id in ("rung_f_conformal", "rung_f_cqr_catboost")
    assert "Rung F" in report.champion_rung
    assert "ACCEPTED_AS_PRODUCTION_CHAMPION" in report.promotion_verdict

    # Check candidate ladder populated
    assert "rung_a_empirical" in report.candidates
    assert "rung_b_linear" in report.candidates
    assert "rung_e_catboost" in report.candidates
    assert "rung_f_conformal" in report.candidates or "rung_f_cqr_catboost" in report.candidates

    # Check Markdown and JSON formatting
    md = report.to_markdown()
    assert "# Champion Model Selection Audit Report" in md

    report_dict = report.to_dict()
    assert report_dict["champion_id"] in ("rung_f_conformal", "rung_f_cqr_catboost")

    # Test saving reports
    md_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    report.save_reports(md_path=md_path, json_path=json_path)
    assert md_path.exists()
    assert json_path.exists()


# ==============================================================================
# Unit Tests: End-to-End Champion Bundle Builder Pipeline & CLI
# ==============================================================================


def test_build_champion_bundle_synthetic_guard(
    sample_train_df: pl.DataFrame,
    tmp_path: Path,
) -> None:
    """Test synthetic data guard raises DataContractError unless allow_synthetic=True."""
    synth_df = sample_train_df.with_columns(pl.lit(True).alias("is_synthetic"))
    synth_path = tmp_path / "synthetic_data.parquet"
    synth_df.write_parquet(synth_path)

    # Building bundle with synthetic data and allow_synthetic=False -> Blocks (R-MD-11)
    with pytest.raises(DataContractError) as exc_info:
        build_champion_bundle(
            canonical_path=str(synth_path),
            output_dir=str(tmp_path / "out"),
            allow_synthetic=False,
        )
    assert exc_info.value.code == "SYNTHETIC_DATA_BLOCKED"


def test_build_champion_bundle_end_to_end(
    sample_train_df: pl.DataFrame,
    sample_cal_df: pl.DataFrame,
    sample_select_df: pl.DataFrame,
    tmp_path: Path,
) -> None:
    """Test full build_champion_bundle high-level function."""
    full_df = pl.concat([sample_train_df, sample_cal_df, sample_select_df])
    data_path = tmp_path / "canonical.parquet"
    full_df.write_parquet(data_path)

    card_path = tmp_path / "model_card.md"
    card_path.write_text("# Test Model Card", encoding="utf-8")

    out_bundle_dir = tmp_path / "champion_v0"
    report_md = tmp_path / "report.md"
    report_json = tmp_path / "report.json"

    report, bundle = build_champion_bundle(
        canonical_path=str(data_path),
        output_dir=str(out_bundle_dir),
        model_card_path=str(card_path),
        report_md_path=str(report_md),
        report_json_path=str(report_json),
        seed=42,
        allow_synthetic=True,
    )

    assert report.champion_candidate_id in ("rung_f_conformal", "rung_f_cqr_catboost")
    assert report.champion_metrics["coverage_80"] > 0
    assert out_bundle_dir.exists()
    assert (out_bundle_dir / "manifest.json").exists()
    assert (out_bundle_dir / "base_model.joblib").exists()
    assert (out_bundle_dir / "cohort_evidence.parquet").exists()
    assert report_md.exists()
    assert report_json.exists()

    # Missing file raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        build_champion_bundle(canonical_path=tmp_path / "non_existent.parquet")
