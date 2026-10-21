#!/usr/bin/env python3
"""Scheduled data refresh job and source freshness SLA audit engine (Task T10.04).

Executes scheduled source freshness auditing against pre-registered SLAs (PRD NFR-11,
RSK-11, Rule R-DA-01). Detects approaching staleness (WARNING) and overdue feeds (CRITICAL),
dispatches structured operational alerts via AlertManager, updates Prometheus metrics,
and produces persistent markdown and JSON audit artifacts.

Supports fault injection via `--induce-staleness <source_id>` to verify that stale
sources trigger CRITICAL alerts immediately.

Usage:
    # Run nominal data refresh audit:
    uv run python scripts/run_data_refresh.py

    # Verify that a stale source raises an alert (Done when criterion):
    uv run python scripts/run_data_refresh.py --induce-staleness SRC-INT-VOL-01 --stale-days 45

    # Exit with code 1 if stale (for CI assertion):
    uv run python scripts/run_data_refresh.py --fail-on-stale
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
from compintel.monitoring.freshness import (
    execute_data_refresh_job,
    load_source_freshness_slas,
    render_data_refresh_markdown,
)

configure_logging()
logger = get_logger("scripts.run_data_refresh")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scheduled data refresh and source freshness SLA audit engine."
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Evaluation reference timestamp in ISO format (default: current UTC).",
    )
    parser.add_argument(
        "--induce-staleness",
        type=str,
        default=None,
        help="Source ID to inject simulated staleness for (verifies alert generation).",
    )
    parser.add_argument(
        "--stale-days",
        type=float,
        default=400.0,
        help="Simulated age in days when using --induce-staleness (default: 400.0).",
    )
    parser.add_argument(
        "--config-slas",
        type=Path,
        default=repo_root / "config" / "freshness_slas.yaml",
        help="Path to freshness SLAs configuration YAML.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=repo_root / "experiments" / "results" / "data_refresh_report.json",
        help="Path to save JSON audit report.",
    )
    parser.add_argument(
        "--dashboard-md",
        type=Path,
        default=repo_root / "docs" / "monitoring" / "data-refresh-status.md",
        help="Path to save markdown dashboard.",
    )
    parser.add_argument(
        "--fail-on-stale",
        action="store_true",
        help="Exit with non-zero exit code if any source is STALE.",
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

    induce_dict: dict[str, float] | None = None
    if args.induce_staleness:
        induce_dict = {args.induce_staleness: args.stale_days}
        logger.warning(
            "staleness_fault_injected",
            source_id=args.induce_staleness,
            stale_days=args.stale_days,
        )

    alert_manager = AlertManager()

    logger.info("executing_data_refresh_audit", as_of=as_of.isoformat())
    result = execute_data_refresh_job(
        repo_root=repo_root,
        as_of=as_of,
        induce_staleness=induce_dict,
        alert_manager=alert_manager,
        update_metrics=not args.no_metrics,
        slas_config_path=args.config_slas,
    )

    # Persist JSON report
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    report_dict = result.model_dump(mode="json")
    with open(args.report_json, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, default=str)
    logger.info("saved_refresh_json_report", path=str(args.report_json))

    # Persist Markdown dashboard
    args.dashboard_md.parent.mkdir(parents=True, exist_ok=True)
    slas = load_source_freshness_slas(args.config_slas)
    markdown_content = render_data_refresh_markdown(result, slas=slas)
    with open(args.dashboard_md, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    logger.info("saved_refresh_markdown_dashboard", path=str(args.dashboard_md))

    # Print summary output to terminal
    print("\n" + "=" * 78)
    print(f" ArthaIQ Scheduled Data Refresh Job -- Verdict: {result.overall_status}")
    print("=" * 78)
    print(f" Run ID:            {result.run_id}")
    print(f" Evaluated As-Of:   {result.evaluated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f" Total Sources:     {result.total_sources_evaluated}")
    print(f" Fresh (< 75% SLA): {result.fresh_count}")
    print(f" Warning (75-100%): {result.warning_count}")
    print(f" Stale (>= SLA):    {result.stale_count}")
    print(f" Alerts Dispatched: {len(result.alerts_triggered)}")

    if result.alerts_triggered:
        print("\nActive Alerts:")
        for alert in result.alerts_triggered:
            print(
                f"  [{alert['severity']}] {alert['category']}: {alert['title']} "
                f"(Metric: {alert['metric_name']} = {alert['metric_value']:.1f}d, SLA: {alert['threshold']:.1f}d)"
            )

    print("=" * 78 + "\n")

    if args.fail_on_stale and result.stale_count > 0:
        logger.error("data_refresh_failed_due_to_stale_source", count=result.stale_count)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
