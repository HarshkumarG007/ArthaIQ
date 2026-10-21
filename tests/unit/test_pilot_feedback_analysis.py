"""Unit tests for pilot feedback analysis, scorecard, and backlog (Task T10.06).

Validates:
1. Auditing all 11 pre-registered PRD Section 11 metrics (M-01 to M-11).
2. Failure condition detection on boundary violations.
3. Semantic clustering of qualitative user feedback.
4. RICE score calculation and charter linking for top backlog items.
5. Idempotent evidence register updating.
6. Markdown dashboard rendering and JSON serialization.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from compintel.evaluation.pilot_analysis import (
    cluster_qualitative_feedback,
    evaluate_pilot_metrics,
    execute_pilot_feedback_analysis,
    generate_prioritized_backlog,
    render_pilot_analysis_markdown,
    update_evidence_register,
)


def test_evaluate_pilot_metrics_all_pass() -> None:
    """Verifies that nominal pilot outcomes pass all 11 PRD Section 11 metrics."""
    metrics = evaluate_pilot_metrics()
    assert len(metrics) == 11

    metric_ids = [m.metric_id for m in metrics]
    expected_ids = [f"M-{i:02d}" for i in range(1, 12)]
    assert metric_ids == expected_ids

    for m in metrics:
        assert m.status == "PASS", f"Metric {m.metric_id} ({m.name}) failed unexpectedly: {m}"
        assert m.target_sla != ""
        assert m.governing_rule != ""
        assert m.description != ""


@pytest.mark.parametrize(
    ("kwargs", "failed_metric_id"),
    [
        ({"comprehension_rate": 0.899}, "M-01"),
        ({"task_completion_rate": 0.949}, "M-02"),
        ({"abstention_integrity": 0.999}, "M-03"),
        ({"realized_coverage": 0.749}, "M-04"),
        ({"realized_coverage": 0.851}, "M-04"),
        ({"median_width_ratio": 0.451}, "M-05"),
        ({"contribution_opt_in_rate": 0.149}, "M-06"),
        ({"contribution_validity_rate": 0.899}, "M-07"),
        ({"serving_latency_p95_ms": 50.1}, "M-08"),
        ({"operational_error_rate": 0.0011}, "M-09"),
        ({"pii_exposure_incidents": 1}, "M-10"),
        ({"erasure_time_seconds": 2.1}, "M-11"),
    ],
)
def test_evaluate_pilot_metrics_threshold_failures(
    kwargs: dict[str, float | int], failed_metric_id: str
) -> None:
    """Verifies that metric evaluations detect boundary violations accurately."""
    metrics = evaluate_pilot_metrics(**kwargs)  # type: ignore[arg-type]
    failed = [m for m in metrics if m.status == "FAIL"]
    assert len(failed) >= 1
    assert any(m.metric_id == failed_metric_id for m in failed)


def test_cluster_qualitative_feedback() -> None:
    """Verifies semantic clustering of feedback into 4 structured themes."""
    clusters = cluster_qualitative_feedback()
    assert len(clusters) == 4

    total_pct = sum(c.percentage for c in clusters)
    assert abs(total_pct - 100.0) < 0.1

    theme_ids = [c.theme_id for c in clusters]
    assert theme_ids == ["THEME-01", "THEME-02", "THEME-03", "THEME-04"]

    for c in clusters:
        assert c.mention_count > 0
        assert c.sentiment in ("POSITIVE", "NEUTRAL", "CONSTRUCTIVE")
        assert len(c.representative_quote) > 10


def test_generate_prioritized_backlog_rice_ranking() -> None:
    """Verifies RICE scoring formula and that top items possess published charters."""
    backlog = generate_prioritized_backlog()
    assert len(backlog) >= 4

    # RICE score must be strictly monotonically non-increasing
    for i in range(len(backlog) - 1):
        assert backlog[i].rice_score >= backlog[i + 1].rice_score

    # Top items must have experiment charters per Rule R-MD-09
    for item in backlog:
        assert item.has_charter is True
        assert item.charter_id is not None
        assert item.charter_id.startswith("CHARTER-")
        # Verify RICE formula: (reach * impact * confidence) / effort
        expected_rice = (item.reach * item.impact * item.confidence) / item.effort
        assert abs(item.rice_score - expected_rice) < 0.2


def test_update_evidence_register_idempotent() -> None:
    """Verifies updating evidence register CSV adds new claims and is idempotent."""
    with TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "evidence-register.csv"
        # Create initial register with 2 mock claims
        headers = [
            "claim_or_decision",
            "supporting_source",
            "contradictory_evidence",
            "evidence_quality",
            "confidence_level",
            "practical_implication",
            "validation_experiment_required",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow(
                {
                    "claim_or_decision": "Initial baseline claim",
                    "supporting_source": "Source A",
                    "contradictory_evidence": "None",
                    "evidence_quality": "Tier A",
                    "confidence_level": "High",
                    "practical_implication": "Implication A",
                    "validation_experiment_required": "Exp A",
                }
            )

        # 1st update: should append all new Phase 10 claims
        additions_1 = update_evidence_register(csv_path)
        assert additions_1 == 5

        with csv_path.open("r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 6  # 1 initial + 5 added

        # 2nd update: should add 0 duplicate claims (idempotency)
        additions_2 = update_evidence_register(csv_path)
        assert additions_2 == 0

        with csv_path.open("r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 6


def test_execute_pilot_feedback_analysis_verdicts() -> None:
    """Verifies full execution orchestration and verdict transitions."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    as_of = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)

    # Nominal run -> GO
    result_go = execute_pilot_feedback_analysis(
        repo_root=repo_root,
        as_of=as_of,
        comprehension_rate=0.9419,
    )
    assert result_go.overall_verdict == "GO"
    assert "GO" in result_go.summary
    assert len(result_go.metrics_evaluations) == 11
    assert len(result_go.feedback_clusters) == 4
    assert len(result_go.prioritized_backlog) == 4

    # Dict serialization check
    d = result_go.to_dict()
    assert d["overall_verdict"] == "GO"
    assert d["total_feedback_submissions"] == 155
    assert len(d["metrics_evaluations"]) == 11

    # Failing run -> NO_GO
    result_nogo = execute_pilot_feedback_analysis(
        repo_root=repo_root,
        as_of=as_of,
        comprehension_rate=0.8200,  # Below 90% threshold
    )
    assert result_nogo.overall_verdict == "NO_GO"
    assert "NO_GO" in result_nogo.summary


def test_render_pilot_analysis_markdown() -> None:
    """Verifies that generated markdown contains all necessary governance sections."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    result = execute_pilot_feedback_analysis(repo_root=repo_root)

    md = render_pilot_analysis_markdown(result)
    assert "# ArthaIQ Public Beta Pilot Results & Prioritized Backlog Analysis" in md
    assert "## 1. Executive Summary & Production Readiness" in md
    assert "## 2. Pre-Registered Metrics Scorecard (PRD Section 11)" in md
    assert "## 3. Qualitative User Feedback & Sentiment Clustering" in md
    assert "## 4. Prioritized Post-Pilot Backlog (RICE Scored)" in md
    assert "## 5. Evidence Register Synchronization" in md
    assert "## 6. Gate G10 Production Recommendation" in md
    assert "CHARTER-EXP-13" in md
    assert "CHARTER-EXP-16" in md
    assert "CHARTER-EXP-14" in md
    assert "CHARTER-EXP-15" in md
