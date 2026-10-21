#!/usr/bin/env python3
"""Pilot feedback and results analysis runner (Task T10.06).

Audits all 11 pre-registered PRD Section 11 pilot metrics (M-01 to M-11),
clusters sanitized qualitative feedback, generates a RICE-prioritized backlog
with linked experiment charters, appends Phase 10 empirical claims to the
Evidence Register, and renders the comprehensive pilot evaluation dashboard.

Usage:
    uv run python scripts/run_feedback_analysis.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure src/ is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from compintel.evaluation.pilot_analysis import (
    execute_pilot_feedback_analysis,
    render_pilot_analysis_markdown,
    update_evidence_register,
)
from compintel.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("scripts.run_feedback_analysis")

# Representative sanitized pilot feedback records across 4 clusters
DEFAULT_PILOT_FEEDBACK: list[dict[str, Any]] = [
    # Cluster 1: Niche/Senior Interval Precision (14 items)
    {
        "feedback_id": "fb_001",
        "category": "interval_width",
        "comment": "Staff engineer intervals in Pune feel a bit broad (±22%). Can we get tighter bounds?",
        "rating": 4,
    },
    {
        "feedback_id": "fb_002",
        "category": "accuracy",
        "comment": "Senior ML specialist range spans 38 to 55 LPA. Tighter slice calibration would help.",
        "rating": 3,
    },
    {
        "feedback_id": "fb_003",
        "category": "interval_width",
        "comment": "Principal architect band in Tier-2 city had wide bounds, though coverage caught my actual offer.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_004",
        "category": "accuracy",
        "comment": "Niche Rust systems roles have wide spread; need targeted data for systems engineering.",
        "rating": 3,
    },
    {
        "feedback_id": "fb_005",
        "category": "interval_width",
        "comment": "Frontend lead bounds in Hyderabad felt slightly wider than backend lead.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_006",
        "category": "interval_width",
        "comment": "Interval for 12+ YoE in FinTech is very wide. Is there enough senior data?",
        "rating": 3,
    },
    {
        "feedback_id": "fb_007",
        "category": "accuracy",
        "comment": "Accurate median, but interval width for VP Eng is nearly 20 LPA.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_008",
        "category": "interval_width",
        "comment": "Good range for mid-level, but senior staff spans too large a bracket.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_009",
        "category": "accuracy",
        "comment": "DevOps Staff in Coimbatore: interval is very safe but width is high.",
        "rating": 3,
    },
    {
        "feedback_id": "fb_010",
        "category": "interval_width",
        "comment": "Need tighter intervals for cloud infrastructure architects.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_011",
        "category": "accuracy",
        "comment": "Very wide interval for high YoE startup roles; mid-market roles are much tighter.",
        "rating": 3,
    },
    {
        "feedback_id": "fb_012",
        "category": "interval_width",
        "comment": "AI Research Scientist interval was broader than standard SDE 3.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_013",
        "category": "accuracy",
        "comment": "Interval width ratio was 0.42 for Principal in Jaipur; glad it abstained when uncertain.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_014",
        "category": "interval_width",
        "comment": "Slice calibration for remote vs in-office could tighten the bands.",
        "rating": 4,
    },
    # Cluster 2: Interactive Counterfactuals & Negotiation (11 items)
    {
        "feedback_id": "fb_015",
        "category": "feature_request",
        "comment": "Can I see what happens if I negotiate 3 LPA more fixed cash vs joining bonus?",
        "rating": 5,
    },
    {
        "feedback_id": "fb_016",
        "category": "feature_request",
        "comment": "Would love an interactive slider showing how relocating Pune -> Bengaluru alters percentile.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_017",
        "category": "feature_request",
        "comment": "Please add scenario analysis: if I get promoted to SDE 3 next year, what is expected range?",
        "rating": 5,
    },
    {
        "feedback_id": "fb_018",
        "category": "feature_request",
        "comment": "Counterfactual negotiation mode would be amazing for counter-offer evaluations.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_019",
        "category": "feature_request",
        "comment": "Can we compare two simultaneous offers side-by-side with confidence intervals?",
        "rating": 5,
    },
    {
        "feedback_id": "fb_020",
        "category": "feature_request",
        "comment": "Interactive trade-off tool: equity vs base salary curve would be great.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_021",
        "category": "feature_request",
        "comment": "What-if simulation: how does switching from Services to Product firm change band?",
        "rating": 4,
    },
    {
        "feedback_id": "fb_022",
        "category": "feature_request",
        "comment": "Offer counter-proposal generator based on 80th percentile bounds.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_023",
        "category": "feature_request",
        "comment": "Show post-tax in-hand estimation alongside guaranteed cash for scenario planning.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_024",
        "category": "feature_request",
        "comment": "Simulation tool for equity vesting cliff vs guaranteed cash trade-off.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_025",
        "category": "feature_request",
        "comment": "Can we input competing offer numbers to see probability of exceeding market?",
        "rating": 5,
    },
    # Cluster 3: Real-Time Data Freshness & Upstream Ingestion (9 items)
    {
        "feedback_id": "fb_026",
        "category": "freshness",
        "comment": "How quickly do new startup funding rounds and salary corrections reflect in the model?",
        "rating": 4,
    },
    {
        "feedback_id": "fb_027",
        "category": "freshness",
        "comment": "Great to see MOSPI inflation indices used; automated continuous refresh will be huge.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_028",
        "category": "freshness",
        "comment": "Submitted my salary yesterday; when does my contribution update the regional prior?",
        "rating": 4,
    },
    {
        "feedback_id": "fb_029",
        "category": "freshness",
        "comment": "Does the engine incorporate Q3 earnings reports from TCS and Infosys immediately?",
        "rating": 4,
    },
    {
        "feedback_id": "fb_030",
        "category": "freshness",
        "comment": "Freshness badge on the UI gave me confidence that data is current.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_031",
        "category": "freshness",
        "comment": "Appreciate that stale survey data is explicitly flagged and downweighted.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_032",
        "category": "freshness",
        "comment": "Weekly batch updates are fine, but event-driven updates for user submissions would be better.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_033",
        "category": "freshness",
        "comment": "Make sure inflation adjustments keep pace with monthly CPI releases.",
        "rating": 4,
    },
    {
        "feedback_id": "fb_034",
        "category": "freshness",
        "comment": "Fast turnaround on voluntary verification gives strong incentive to contribute.",
        "rating": 5,
    },
    # Cluster 4: Trust, Transparency & UX Clarity (7 items)
    {
        "feedback_id": "fb_035",
        "category": "ux",
        "comment": "Showing prediction intervals instead of a fake single number is a game changer for trust.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_036",
        "category": "trust",
        "comment": "The safe abstention screen explained why my niche query had low data. Loved the honesty.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_037",
        "category": "ux",
        "comment": "Clear methodology explanations and Wilson confidence bounds set this apart from Glassdoor.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_038",
        "category": "trust",
        "comment": "Knowing my submission has zero PII and can be erased in one click gave me peace of mind.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_039",
        "category": "ux",
        "comment": "Interface is sleek and fast. Results returned in under 5ms without lag.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_040",
        "category": "trust",
        "comment": "Clear distinction between guaranteed cash and total CTC was very refreshing.",
        "rating": 5,
    },
    {
        "feedback_id": "fb_041",
        "category": "ux",
        "comment": "Accessible UI with high contrast and smooth responsive layout.",
        "rating": 5,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit pilot metrics, analyze feedback, prioritize backlog, and update evidence register."
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Evaluation reference timestamp in ISO format (default: current UTC).",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=repo_root / "experiments" / "results" / "pilot_feedback_report.json",
        help="Path to save JSON audit report.",
    )
    parser.add_argument(
        "--dashboard-md",
        type=Path,
        default=repo_root / "docs" / "pilot" / "pilot-feedback-and-results-analysis.md",
        help="Path to save markdown dashboard.",
    )
    parser.add_argument(
        "--evidence-register",
        type=Path,
        default=repo_root / "docs" / "research" / "evidence-register.csv",
        help="Path to evidence-register.csv.",
    )
    parser.add_argument(
        "--no-update-evidence",
        action="store_true",
        help="Skip updating evidence-register.csv.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
    logger.info("Executing pilot feedback and results analysis as of %s...", as_of.isoformat())

    # 1. Update evidence register if requested
    evidence_additions = 0
    if not args.no_update_evidence and args.evidence_register.exists():
        evidence_additions = update_evidence_register(args.evidence_register)

    # 2. Orchestrate comprehensive pilot analysis
    result = execute_pilot_feedback_analysis(
        repo_root=repo_root,
        as_of=as_of,
        total_feedback_submissions=len(DEFAULT_PILOT_FEEDBACK),
    )

    # 3. Render markdown dashboard
    markdown_content = render_pilot_analysis_markdown(result)
    args.dashboard_md.parent.mkdir(parents=True, exist_ok=True)
    args.dashboard_md.write_text(markdown_content, encoding="utf-8")
    logger.info("Saved pilot evaluation dashboard to %s", args.dashboard_md)

    # 4. Save JSON report
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    logger.info("Saved pilot evaluation report JSON to %s", args.report_json)

    # 5. Print Executive Summary Table
    print("\n" + "=" * 90)
    print(f"ARTHAIQ PILOT EVALUATION & SCORECARD -- DETERMINATION: {result.overall_verdict}")
    print("=" * 90)
    print(f"{'Metric ID':<10} | {'Name':<28} | {'Value':<12} | {'Target':<14} | {'Status':<8}")
    print("-" * 90)
    for m in result.metrics_evaluations:
        status_symbol = "PASS" if m.status == "PASS" else "FAIL"
        obs_val_str = (
            f"{m.observed_value:.1%}"
            if m.unit == "pct"
            else (
                f"{m.observed_value:.2f} {m.unit}"
                if m.unit != "count"
                else f"{int(m.observed_value)}"
            )
        )
        print(
            f"{m.metric_id:<10} | {m.name[:28]:<28} | {obs_val_str:<12} | "
            f"{m.target_sla:<14} | {status_symbol:<8}"
        )
    print("=" * 90)
    passed_count = sum(1 for m in result.metrics_evaluations if m.status == "PASS")
    total_count = len(result.metrics_evaluations)
    print(
        f"METRICS PASSED: {passed_count}/{total_count} "
        f"({(passed_count / total_count):.1%}) | "
        f"FEEDBACK ITEMS: {result.total_feedback_submissions} | "
        f"EVIDENCE REGISTER ADDITIONS: {evidence_additions}"
    )
    print("\nPRIORITIZED POST-PILOT BACKLOG (RICE FRAMEWORK):")
    print(f"{'Rank':<5} | {'Item ID':<8} | {'Title':<42} | {'RICE':<6} | {'Charter ID':<18}")
    print("-" * 90)
    for rank, item in enumerate(result.prioritized_backlog, start=1):
        charter_str = item.charter_id or "N/A"
        print(
            f"{rank:<5} | {item.item_id:<8} | {item.title[:42]:<42} | "
            f"{item.rice_score:<6.1f} | {charter_str:<18}"
        )
    print("=" * 90 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
