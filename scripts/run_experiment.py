"""Command-line runner for CompIntel experiment execution and reproduction (Task T4.07).

Governed by:
- Rule R-MD-10: Seed everything. Every run records data snapshot id, config, library
  versions, timings, peak memory, and commit, and reproduces with one command.
- Rule R-MD-02: Isolated final test set; routine experiments evaluate strictly on dev.
- Rule R-MD-05: Standard comprehensive metrics suite.
- Rule R-MD-08: Thin evidence abstentions properly handled.
- Rule R-MD-11: Synthetic data flagged and blocked from canonical experiment records.
- ADR-0006: File-based run records persisted to experiments/results/<run_id>/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from compintel.errors import CompIntelError
from compintel.evaluation.experiment import (
    ExperimentConfig,
    ExperimentRunner,
    reproduce_experiment,
)
from compintel.logging import configure_logging, get_logger

logger = get_logger("scripts.run_experiment")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run or reproduce CompIntel model experiments (Rule R-MD-10, Task T4.07)."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("experiments/configs/baseline_rung_ab.yaml"),
        help="Path to YAML experiment configuration.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override experiment random seed.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Custom destination directory for run record bundle.",
    )
    parser.add_argument(
        "--canonical-path",
        type=Path,
        default=None,
        help="Path to canonical observations parquet file.",
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        default=False,
        help="Permit execution on synthetic fixture data (Rule R-MD-11).",
    )
    parser.add_argument(
        "--reproduce",
        type=Path,
        default=None,
        help="Path to past experiment run directory or run_record.json to reproduce and verify.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-9,
        help="Discrepancy tolerance for metric equality during reproduction.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress printing report markdown to stdout.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    configure_logging()
    args = parse_args()

    # Mode 1: Reproduce a past experiment run
    if args.reproduce is not None:
        logger.info(
            "Reproducing experiment run",
            target=str(args.reproduce),
            tolerance=args.tolerance,
        )
        try:
            result = reproduce_experiment(
                run_dir_or_record=args.reproduce,
                canonical_data_path=args.canonical_path,
                tolerance=args.tolerance,
            )
            print("=" * 80)
            print("EXPERIMENT REPRODUCTION VERIFICATION: SUCCESS")
            print("=" * 80)
            print(f"Run ID:            {result.run_id}")
            print(f"Metrics Verified:  {result.metrics_compared}")
            print(
                f"Max Discrepancy:   {result.max_discrepancy:.2e} (tolerance: {args.tolerance:.2e})"
            )
            print(f"Identical Metrics: {result.is_identical}")
            print("Rule R-MD-10 Verification: 100% REPRODUCIBLE")
            print("=" * 80)
            return 0
        except CompIntelError as e:
            logger.error("Reproduction failed", error=str(e), code=e.code)
            print(f"ERROR: Reproduction failed [{e.code}]: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            logger.error("Unexpected error during reproduction", error=str(e))
            print(f"FATAL: {e}", file=sys.stderr)
            return 2

    # Mode 2: Execute a new experiment run from config
    config_path = args.config
    if not config_path.exists():
        logger.error("Configuration file not found", path=str(config_path))
        print(f"ERROR: Config file not found at {config_path}", file=sys.stderr)
        return 1

    try:
        config = ExperimentConfig.from_yaml(config_path)
    except Exception as e:
        logger.error("Failed to parse experiment configuration", error=str(e))
        print(f"ERROR: Invalid configuration: {e}", file=sys.stderr)
        return 1

    # Apply CLI overrides
    if args.seed is not None:
        config.seed = args.seed
    if args.allow_synthetic:
        config.allow_synthetic = True
    if args.canonical_path is not None:
        config.canonical_data_path = str(args.canonical_path)

    # Resolve input data path
    data_path = (
        Path(config.canonical_data_path)
        if config.canonical_data_path
        else Path("data/canonical/canonical_observations.parquet")
    )

    if not data_path.exists():
        logger.error("Canonical data not found", path=str(data_path))
        print(
            f"ERROR: Canonical data not found at {data_path}. Run 'make reproduce-data' first.",
            file=sys.stderr,
        )
        return 1

    try:
        df = pl.read_parquet(data_path)
        runner = ExperimentRunner(config=config)
        record = runner.run(df=df, output_dir=args.output_dir)

        if not args.quiet:
            print("\n" + "=" * 80)
            print(record.to_markdown())
            print("=" * 80 + "\n")

        return 0

    except CompIntelError as e:
        logger.error("Experiment failed", error=str(e), code=e.code)
        print(f"ERROR [{e.code}]: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error("Unexpected error during experiment", error=str(e))
        print(f"FATAL: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
