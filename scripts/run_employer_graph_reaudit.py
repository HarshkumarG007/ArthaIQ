#!/usr/bin/env python3
"""CLI runner for EXP-10r: Employer Graph Feasibility Re-audit (Phase 13, Task T13.01).

Conducts an empirical data-growth feasibility audit on the cumulative non-synthetic
production panel accumulated post-EXP-16 ingestion daemon activation (6 months operational
window), determining whether bipartite talent-flow mobility graphs have achieved
topological density sufficiency to justify graph-based compensation modeling.

Adheres strictly to:
- PRD Section 5 & FR-05: Personalization hierarchy and employer representation.
- CHARTER-EXP-10 & CHARTER-EXP-10r: Re-evaluation of talent-flow transition graphs.
- Rule R-MD-01 / R-MD-02: Dev partition evaluation only; test set strictly locked.
- Rule R-MD-03: Zero lookahead; employer mobility graph built as-of training cutoff.
- Rule R-MD-04: Target encoding and graph embeddings fitted inside training folds only.
- Rule R-MD-05: Comprehensive evaluation metrics with paired difference bootstrap CIs.
- Rule R-MD-09: Pre-registered experiment charter required; pure CPU compute; no post-hoc threshold shifts.
- Rule R-MD-11: Synthetic data isolation guards.
- Rule R-UQ-01: Nonparametric bootstrap confidence intervals on paired differences; zero lone numbers.
- Rule R-UQ-05: Monotonic quantile non-crossing guarantee (P10 <= P50 <= P90).
- Rule R-DA-10: k_min >= 5 anonymization floor on employer clusters and graph nodes.

Usage:
    uv run python scripts/run_employer_graph_reaudit.py
        [--canonical-path <path>]
        [--output-md <path>]
        [--output-json <path>]
        [--months-operational <float>]
        [--force-embeddings]
        [--allow-synthetic]
        [--seed <int>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from compintel.errors import CompIntelError
from compintel.evaluation.employer_graph_reaudit import (
    evaluate_and_save_employer_graph_reaudit,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Employer Graph Feasibility Re-audit (EXP-10r, Phase 13, Task T13.01)."
    )
    parser.add_argument(
        "--canonical-path",
        default="data/canonical/canonical_observations.parquet",
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/research/employer-graph-reaudit-phase13.md",
        help="Output path for publication-grade Markdown memo.",
    )
    parser.add_argument(
        "--output-json",
        default="experiments/results/employer_graph_reaudit.json",
        help="Output path for structured JSON audit report.",
    )
    parser.add_argument(
        "--months-operational",
        type=float,
        default=6.0,
        help="Months of post-EXP-16 daemon operations to audit (default: 6.0).",
    )
    parser.add_argument(
        "--force-embeddings",
        action="store_true",
        default=False,
        help="Force execution of graph embeddings even if Gate 1 feasibility indicates sparsity.",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Explicitly permit synthetic data execution (Rule R-MD-11).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute employer graph feasibility re-audit CLI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()

    print("================================================================================")
    print(" ArthaIQ -- Employer Graph Feasibility Re-audit (EXP-10r, Task T13.01)")
    print("================================================================================")
    print(
        f"Operational Window:  {args.months_operational:.1f} months post-EXP-16 daemon activation"
    )
    print(f"Canonical Path:      {args.canonical_path}")
    print(f"Force Embeddings:    {args.force_embeddings}")
    print(f"Allow Synthetic:     {args.allow_synthetic}")
    print(f"Random Seed:         {args.seed}")
    print(f"Markdown Output:     {args.output_md}")
    print(f"JSON Output:         {args.output_json}")
    print("================================================================================")

    try:
        report = evaluate_and_save_employer_graph_reaudit(
            canonical_path=args.canonical_path,
            output_md=args.output_md,
            output_json=args.output_json,
            months_operational=args.months_operational,
            force_embeddings=args.force_embeddings,
            allow_synthetic=args.allow_synthetic,
            seed=args.seed,
        )

        tm = report.topology_metrics
        print(f"\nAudit Report ID:     {report.report_id}")
        print(f"Charter ID:          {report.charter_id}")
        print(f"Task ID:             {report.task_id}")
        print(f"Generated At:        {report.generated_at}")
        print(f"Git Commit:          {report.git_commit[:8]}")
        print(f"Total Observations:  {report.n_total_observations:,}")
        print(f"Non-Synthetic:       {report.n_non_synthetic:,} (100% Rule R-MD-11 verified)")
        print(f"Observation Span:    {report.date_range_start} to {report.date_range_end}")

        print("\nMobility Network Topology Audit (Gate 1):")
        print("-" * 70)
        print(f"  Total Clusters:    {tm.total_employer_clusters}")
        print(f"  Eligible (k >= 5): {tm.eligible_nodes_kmin5}")
        print(
            f"  Qualified (>= 3):  {tm.qualified_nodes_degree_ge_3} / {tm.required_threshold} required "
            f"({tm.qualified_nodes_degree_ge_3 / tm.required_threshold * 100:.1f}%)"
        )
        print(f"  Transition Edges:  {tm.total_transition_edges}")
        print(f"  Network Density:   {tm.network_density:.4f}")
        print(f"  Components Count:  {tm.num_connected_components}")
        print(
            f"  Giant Component:   {tm.giant_component_size} nodes ({tm.giant_component_fraction:.1%})"
        )
        print(f"  Isolated Nodes:    {tm.isolated_nodes_count}")
        print(f"  Gate 1 Status:     {report.feasibility_status.value}")
        print("-" * 70)

        print("\nTop Employer Cluster Connectivity:")
        sorted_degrees = sorted(tm.node_degrees.items(), key=lambda kv: kv[1], reverse=True)
        for cluster_id, deg in sorted_degrees[:8]:
            print(
                f"  {cluster_id:<22} | Degree: {deg:<2} | Gate 1 Qualified: {'YES' if deg >= 3 else 'NO'}"
            )

        print("\nProduction Decision & Next Trigger:")
        print("-" * 70)
        print(f"  Re-audit Verdict:  {report.verdict.value}")
        print(f"  Champion Status:   {report.champion_status}")
        print(f"  Next Trigger Date: {report.next_scheduled_audit_date}")
        print(f"  Trigger Condition: {report.next_audit_trigger_condition}")
        print("-" * 70)

        print(f"\n[OK] Publication-grade memo: {args.output_md}")
        print(f"[OK] Structured JSON report:  {args.output_json}")
        return 0

    except CompIntelError as err:
        print(f"\n[ERROR] Employer graph re-audit failed: {err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
