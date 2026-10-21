#!/usr/bin/env python3
"""Scheduled drift audit, conformal recalibration, and champion-challenger runner (Task T10.05).

Executes scheduled covariate and concept drift auditing across monitored feature distributions,
evaluates multi-tier triggers (Tier 0: STABLE, Tier 1: RECALIBRATE, Tier 2: RETRAIN_CHALLENGER),
dispatches structured operational alerts via AlertManager, updates Prometheus metrics,
and executes the documented mitigation action:
- Tier 1: Automated Conformal Recalibration (Rule R-UQ-03) restoring nominal 80% coverage.
- Tier 2: Challenger Shadow Evaluation (Rule R-MD-14) evaluating 5 promotion gates.

Supports fault injection via `--induce-drift <feature>` and `--drift-severity <moderate|severe>`
to verify that simulated drift triggers the documented operational actions.

Usage:
    # Run nominal drift audit (Tier 0: STABLE):
    uv run python scripts/run_drift_recalibration.py

    # Verify that moderate drift triggers automated conformal recalibration (Tier 1):
    uv run python scripts/run_drift_recalibration.py --induce-drift role_family --drift-severity moderate

    # Verify that severe drift triggers challenger shadow training & evaluation (Tier 2):
    uv run python scripts/run_drift_recalibration.py --induce-drift role_family --drift-severity severe
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ensure src/ is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from compintel.logging import configure_logging, get_logger
from compintel.monitoring.alerts import AlertManager
from compintel.monitoring.recalibration import (
    execute_drift_recalibration_job,
    render_drift_recalibration_markdown,
)

configure_logging()
logger = get_logger("scripts.run_drift_recalibration")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scheduled drift audit, conformal recalibration, and champion-challenger runner."
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Evaluation reference timestamp in ISO format (default: current UTC).",
    )
    parser.add_argument(
        "--induce-drift",
        type=str,
        default=None,
        choices=["role_family", "yoe_total"],
        help="Feature name to inject simulated drift into (verifies trigger actions).",
    )
    parser.add_argument(
        "--drift-severity",
        type=str,
        default="moderate",
        choices=["moderate", "severe"],
        help="Severity level of simulated drift: moderate (Tier 1) or severe (Tier 2).",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=150,
        help="Realization cohort sample size to evaluate (default: 150).",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=repo_root / "experiments" / "results" / "drift_recalibration_report.json",
        help="Path to save JSON audit report.",
    )
    parser.add_argument(
        "--dashboard-md",
        type=Path,
        default=repo_root / "docs" / "monitoring" / "drift-recalibration-status.md",
        help="Path to save markdown dashboard.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with non-zero exit code if drift level is RETRAIN_CHALLENGER (CRITICAL).",
    )
    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="Disable Prometheus gauge metric updates.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    if args.induce_drift:
        logger.warning(
            "drift_fault_injected",
            feature=args.induce_drift,
            severity=args.drift_severity,
        )

    alert_manager = AlertManager()

    logger.info("executing_drift_recalibration_audit", as_of=as_of.isoformat())
    result = execute_drift_recalibration_job(
        repo_root=repo_root,
        as_of=as_of,
        induce_drift_feature=args.induce_drift,
        drift_severity=args.drift_severity,
        alert_manager=alert_manager,
        update_metrics=not args.no_metrics,
        sample_size=args.sample_size,
    )

    # Persist JSON report
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    report_dict = result.model_dump(mode="json")
    with open(args.report_json, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, default=str)
    logger.info("saved_drift_json_report", path=str(args.report_json))

    # Persist Markdown dashboard
    args.dashboard_md.parent.mkdir(parents=True, exist_ok=True)
    markdown_content = render_drift_recalibration_markdown(result)
    with open(args.dashboard_md, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    logger.info("saved_drift_markdown_dashboard", path=str(args.dashboard_md))

    # Print summary output to terminal
    print("\n" + "=" * 78)
    print(f" ArthaIQ Drift & Recalibration Engine -- Tier: {result.overall_trigger_level}")
    print("=" * 78)
    print(f" Run ID:             {result.run_id}")
    print(f" Evaluated As-Of:    {result.evaluated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f" Operational Status: {result.overall_status}")
    print(f" Max PSI:            {result.max_psi:.4f}")
    print(f" Max KS Distance:    {result.max_ks:.4f}")
    print(f" Action Executed:    {result.action_executed}")
    print(f" Alerts Dispatched:  {len(result.alerts_triggered)}")

    if result.recalibration_result:
        recal = result.recalibration_result
        print("\nAutomated Conformal Recalibration (Tier 1 Mitigation):")
        print(f"  Prior q_hat:           {recal.prior_conformal_quantile:.3f} LPA")
        print(f"  Updated q_hat:         {recal.updated_conformal_quantile:.3f} LPA")
        print(f"  Delta Correction:      {recal.delta_correction:.3f} LPA")
        print(f"  Prior Coverage:        {recal.prior_empirical_coverage:.1%}")
        print(f"  Post Coverage:         {recal.post_recalibration_coverage:.1%}")
        print(f"  Status:                {recal.recalibration_status}")

    if result.challenger_result:
        chall = result.challenger_result
        print("\nChallenger Shadow Promotion Evaluation (Tier 2 Mitigation):")
        print(f"  Champion Version:      {chall.champion_version}")
        print(f"  Challenger Version:    {chall.challenger_version}")
        print(f"  Champion Pinball:      {chall.champion_mean_pinball:.4f}")
        print(f"  Challenger Pinball:    {chall.challenger_mean_pinball:.4f}")
        print(f"  Pinball Improvement:   {chall.pinball_improvement_pct:+.2f}%")
        print(f"  Empirical Coverage:    {chall.challenger_coverage:.1%}")
        print(f"  Quantile Crossing:     {chall.crossing_rate:.2%}")
        print(f"  Fairness Parity:       {'PASS' if chall.fairness_parity_passed else 'FAIL'}")
        print(f"  Recommendation:        {chall.promotion_recommendation}")
        print(f"  Justification:         {chall.justification}")

    if result.alerts_triggered:
        print("\nActive Alerts Dispatched:")
        for alert in result.alerts_triggered:
            print(
                f"  [{alert['severity']}] {alert['category']}: {alert['title']} "
                f"(Metric: {alert['metric_name']} = {alert['metric_value']:.4f}, Threshold: {alert['threshold']:.4f})"
            )

    print("=" * 78 + "\n")

    if args.fail_on_critical and result.overall_status == "CRITICAL":
        logger.error(
            "drift_audit_failed_due_to_critical_drift", trigger_level=result.overall_trigger_level
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
