"""Unit tests for Phase 11 Benchmark & Gate G11 Ratification Review (Task T11.03).

Validates:
1. Phase 11 review report generation and pre-registered keep criteria audit.
2. Formal Gate G11 documentation in docs/pilot/gate-g11-review.md.
3. Post-Pilot Review Phase 11 Addendum in docs/pilot/post-pilot-review.md.
4. Backlog status updates in docs/pilot/prioritized-backlog.md.
5. ModelBundle architectural support for SliceAdaptiveConformalRegressor.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from scripts.run_phase11_review import run_phase11_review

from compintel.models.bundle import BundleMetadata, ModelBundle
from compintel.models.gbm.quantile import CatBoostQuantileModel
from compintel.schema.enums import MetroLocation, RoleFamily, SeniorityLevel
from compintel.uncertainty.conformal import CalibratedPrediction
from compintel.uncertainty.slice_conformal import (
    SliceAdaptiveConformalRegressor,
    SliceConformalConfig,
)
from compintel.uncertainty.support import (
    CandidateProfile,
    CohortEvidenceContext,
    SupportEvaluator,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_phase11_gate_g11_report_runner(tmp_path: Path) -> None:
    """Verify scripts/run_phase11_review.py executes cleanly and ratifies Gate G11 GO."""
    slice_path = REPO_ROOT / "experiments" / "results" / "slice_conformal_report.json"
    daemon_path = REPO_ROOT / "experiments" / "results" / "ingestion_daemon_report.json"
    out_path = tmp_path / "test_g11_report.json"

    assert slice_path.exists(), f"Missing EXP-13 report at {slice_path}"
    assert daemon_path.exists(), f"Missing EXP-16 report at {daemon_path}"

    report = run_phase11_review(
        slice_report_path=slice_path,
        daemon_report_path=daemon_path,
        output_json_path=out_path,
    )

    assert report["verdict"] == "GO"
    assert "UNCONDITIONAL GO" in report["recommendation"]

    # Check EXP-13 summary
    exp13 = report["charter_summaries"]["EXP-13"]
    assert exp13["verdict"] == "PROMOTE"
    assert exp13["all_criteria_passed"] is True
    assert exp13["slice_variance_reduction_pct"] >= 30.0
    assert exp13["slices_in_band_ratio"] == "12/12 (100.0%)"

    # Check EXP-16 summary
    exp16 = report["charter_summaries"]["EXP-16"]
    assert exp16["verdict"] == "PROMOTE"
    assert exp16["all_criteria_passed"] is True
    assert exp16["staleness_violations_30d"] == 0
    assert exp16["pii_leaks"] == 0

    # Check comparative slice table
    assert len(report["slice_comparative_table"]) == 12
    for slice_entry in report["slice_comparative_table"]:
        assert slice_entry["slice_adaptive_in_band"] is True


def test_gate_g11_review_doc_exists_and_complete() -> None:
    """Verify docs/pilot/gate-g11-review.md exists and contains all required governance sections."""
    doc_path = REPO_ROOT / "docs" / "pilot" / "gate-g11-review.md"
    assert doc_path.is_file(), f"Missing {doc_path}"
    content = doc_path.read_text(encoding="utf-8")

    required_sections = [
        "# Gate G11 Milestone Review & Champion Bundle Promotion",
        "## 1. Executive Determination",
        "## 2. Review Panel Membership & Signatures",
        "## 3. Quantitative Scorecard: EXP-13 Pre-Registered Keep Criteria",
        "## 4. Quantitative Scorecard: EXP-16 Pre-Registered Keep Criteria",
        "## 5. Adversarial Review Checklist (Rule R-MD-05, Section 15)",
        "## 6. Champion Bundle Promotion & Next Steps",
    ]
    for section in required_sections:
        assert section in content, f"Missing section '{section}' in gate-g11-review.md"

    # Verify unanimous GO panel
    assert content.count("**GO**") >= 5
    assert "GATE G11 VERDICT: UNCONDITIONAL GO" in content


def test_post_pilot_review_addendum_exists() -> None:
    """Verify docs/pilot/post-pilot-review.md has Section 8 Phase 11 Addendum."""
    doc_path = REPO_ROOT / "docs" / "pilot" / "post-pilot-review.md"
    assert doc_path.is_file(), f"Missing {doc_path}"
    content = doc_path.read_text(encoding="utf-8")

    assert (
        "## 8. Phase 11 Addendum: Slice Calibration & Ingestion Automation Review (Gate G11)"
        in content
    )
    assert "Gate Ratified:** **Gate G11 (GO)**" in content
    assert "89.05%" in content
    assert "DualCadenceIngestionDaemon" in content
    assert "SliceAdaptiveConformalRegressor" in content


def test_prioritized_backlog_updated_with_phase11_promotions() -> None:
    """Verify docs/pilot/prioritized-backlog.md records Phase 11 promotions and Phase 12 as next."""
    doc_path = REPO_ROOT / "docs" / "pilot" / "prioritized-backlog.md"
    assert doc_path.is_file(), f"Missing {doc_path}"
    content = doc_path.read_text(encoding="utf-8")

    # EXP-13 and EXP-16 marked PROMOTED
    assert "PROMOTED (Gate G11)" in content
    assert "EXP-14" in content
    assert "Chartered / Next (T12.01)" in content
    assert "EXP-15" in content
    assert "Chartered / Next (T12.02)" in content


def test_model_bundle_slice_adaptive_conformal_integration() -> None:
    """Verify ModelBundle natively accepts and serves SliceAdaptiveConformalRegressor."""
    # Create mock fitted base model
    mock_base_model = MagicMock(spec=CatBoostQuantileModel)
    mock_base_model.is_fitted = True

    # Create mock calibrated slice conformal regressor
    mock_calibrator = MagicMock(spec=SliceAdaptiveConformalRegressor)
    mock_calibrator.is_calibrated = True
    mock_calibrator.base_model = mock_base_model
    mock_calibrator.config = SliceConformalConfig(nominal_coverage=0.80)
    mock_calibrator.predict.return_value = [
        CalibratedPrediction(
            p10_calibrated=22.50,
            p50=27.00,
            p90_calibrated=33.50,
            p10_uncalibrated=21.00,
            p90_uncalibrated=35.00,
            conformal_correction=1.50,
            is_crossing_repaired=False,
            is_abstained=False,
            abstention_reason=None,
            nominal_coverage=0.80,
            method="slice_adaptive_cqr",
        )
    ]

    support_evaluator = SupportEvaluator()
    meta = BundleMetadata(
        bundle_name="arthaiq-champion-v1",
        model_version="0.2.0",
        rung="Rung F (Slice-Adaptive Conformal CatBoost)",
        model_family="CatBoostQuantileModel",
        target_variable="guaranteed_cash_annual",
        target_unit="nominal INR LPA",
        quantiles=[0.10, 0.50, 0.90],
        created_at_utc="2026-10-22T00:00:00Z",
        canonical_snapshot_id="SNAP-1FF34A8E9633",
        git_commit_hash="HEAD",
        preregistration_path="experiments/preregistration/v1.yaml",
        feature_names=["role_family", "seniority", "location", "years_experience"],
        feature_schema_hash="dummy_hash",
        sample_sizes={"train": 100, "calibrate": 50, "select": 50, "total": 200},
        metrics_summary={"coverage_80": 0.80, "verdict": "PROMOTE"},
        description="Phase 11 Champion Bundle with SliceAdaptiveConformalRegressor.",
    )

    bundle = ModelBundle(
        metadata=meta,
        base_model=mock_base_model,
        calibrator=mock_calibrator,
        support_evaluator=support_evaluator,
    )

    assert bundle.calibrator is mock_calibrator
    assert bundle.model_version == "0.2.0"

    # Query with valid profile and evidence
    profile = CandidateProfile(
        role_family=RoleFamily.SWE.value,
        seniority=SeniorityLevel.SR.value,
        location=MetroLocation.BENGALURU.value,
        years_experience=6.0,
    )
    evidence = CohortEvidenceContext(
        cohort_size=30,
        median_observation_age_days=25.0,
        category_seen_count=20,
        source_quality_score=90.0,
        provenance_tier="TIER_A",
        interval_width_lpa=0.60,
    )

    pred = bundle.predict_profile(profile, evidence)

    assert pred.is_abstained is False
    assert pred.p10 == 22.50
    assert pred.p50 == 27.00
    assert pred.p90 == 33.50
    assert pred.interval_width == 11.00
    assert pred.nominal_coverage == 0.80
    assert pred.status == "supported"
