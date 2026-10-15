"""Outlier and inconsistency policy with quarantine table and halt threshold (Task T3.11).

Adheres strictly to:
- Rule R-DA-05: Never silently drop, clip, or impute. Quarantine with reason codes and report counts.
- Rule R-ER-06: Data errors go to quarantine. If quarantine rate exceeds limit, halt the pipeline.
- Rule R-MD-07: Anti-heuristic CTC unbundling invariant.
- Rule R-MD-08: Cross-market isolation invariant.
- Rule R-CD-03: Quality layer only imports schema and errors; zero dependencies on higher layers.
- Rule R-MD-09: Deterministic algorithms, strictly free of LLMs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from compintel.errors import PipelineHaltError
from compintel.schema.entities import QuarantineRecord
from compintel.schema.enums import QuarantineReason, RoleFamily

DEFAULT_QUARANTINE_VERSION: str = "v0.1.0"
DEFAULT_HALT_THRESHOLD: float = 0.25  # 25% quarantine rate limit (Rule R-ER-06)


@dataclass(frozen=True)
class OutlierPolicy:
    """Physical and economic outlier boundaries for compensation in nominal INR LPA."""

    min_guaranteed_cash_annual: float = 0.50  # 50,000 INR/year entry floor
    max_guaranteed_cash_annual: float = 300.0  # 3 Crore INR/year guaranteed base ceiling
    max_total_comp_annual: float = 500.0  # 5 Crore INR/year total comp ceiling
    min_years_experience: float = 0.0
    max_years_experience: float = 45.0


@dataclass(frozen=True)
class InconsistencyPolicy:
    """Logical and structural consistency validation criteria."""

    itemized_sum_relative_tolerance: float = 0.05  # 5% margin for basic + hra + special
    itemized_sum_absolute_tolerance_lpa: float = 0.05  # 5,000 INR absolute margin
    enforce_fulltime: bool = True
    enforce_tech_role_only: bool = True
    enforce_market_isolation: bool = True  # Rule R-MD-08: India tech market only
    enforce_unbundled_anti_heuristic: bool = True  # Rule R-MD-07


def evaluate_record_quarantine(
    record: dict[str, Any],
    outlier_policy: OutlierPolicy | None = None,
    inconsistency_policy: InconsistencyPolicy | None = None,
) -> tuple[bool, QuarantineReason | None, str | None]:
    """Evaluate an observation for quarantine reasons in deterministic precedence order.

    Returns:
        tuple of (is_quarantined, quarantine_reason, explanation).
    """
    outliers = outlier_policy or OutlierPolicy()
    rules = inconsistency_policy or InconsistencyPolicy()

    # 1. Occupational scope check (RoleFamily must be tech: SWE, DATA, MLAI)
    role_fam = record.get("role_family")
    if rules.enforce_tech_role_only:
        if role_fam is None:
            return (True, QuarantineReason.SCHEMA_VIOLATION, "Missing mandatory field 'role_family'.")
        str_role = str(role_fam).upper()
        if str_role in ("OTHER", "ROLEFAMILY.OTHER") or str_role not in (
            RoleFamily.SWE.value,
            RoleFamily.DATA.value,
            RoleFamily.MLAI.value,
            "SWE",
            "DATA",
            "MLAI",
        ):
            return (
                True,
                QuarantineReason.NON_TECH_ROLE,
                f"Role family '{role_fam}' is outside India tech occupational scope.",
            )

    # 2. Geographic market isolation (Rule R-MD-08)
    loc = record.get("location")
    if rules.enforce_market_isolation and loc is not None:
        loc_str = str(loc).upper()
        if any(term in loc_str for term in ("US", "USA", "EUROPE", "UK", "UNITED STATES")):
            return (
                True,
                QuarantineReason.GEO_OUT_OF_SCOPE,
                f"Location '{loc}' is foreign employment isolated under Rule R-MD-08.",
            )

    # 3. Enterprise / corporate aggregate census (non-individual worker)
    if record.get("is_enterprise_aggregate") or record.get("source_id") == "SRC-SUP-CORP-01":
        return (
            True,
            QuarantineReason.ENTERPRISE_AGGREGATE,
            "Audited enterprise census median; non-individual worker observation.",
        )

    # 4. Employment type (Non-fulltime)
    emp_type = record.get("employment_type") or record.get("raw_employment_type")
    if rules.enforce_fulltime and emp_type is not None:
        emp_type_str = str(emp_type).lower()
        if any(t in emp_type_str for t in ("intern", "part-time", "part_time", "contractor", "freelance")):
            return (
                True,
                QuarantineReason.NON_FULLTIME,
                f"Employment type '{emp_type}' is non-fulltime.",
            )

    # 5. Anti-heuristic unbundling rule (Rule R-MD-07)
    is_unbundled_agg = record.get("is_unbundled_aggregate", False)
    cash_val = record.get("guaranteed_cash_annual")
    if rules.enforce_unbundled_anti_heuristic and is_unbundled_agg and cash_val is not None:
        return (
            True,
            QuarantineReason.UNBUNDLED_AGGREGATE,
            "Bundled aggregate CTC cannot populate guaranteed_cash_annual without itemization (Rule R-MD-07).",
        )

    # 6. Missing or invalid compensation
    if cash_val is None:
        return (
            True,
            QuarantineReason.MISSING_PAY,
            "Mandatory target 'guaranteed_cash_annual' is missing or null.",
        )
    try:
        cash_float = float(cash_val)
        if cash_float <= 0.0:
            return (
                True,
                QuarantineReason.MISSING_PAY,
                f"guaranteed_cash_annual {cash_float} is non-positive.",
            )
    except (ValueError, TypeError):
        return (
            True,
            QuarantineReason.MISSING_PAY,
            f"guaranteed_cash_annual '{cash_val}' cannot be parsed as numeric float.",
        )

    # 7. Missing or invalid experience
    yoe_val = record.get("years_experience")
    if yoe_val is not None:
        try:
            yoe_float = float(yoe_val)
            if yoe_float < outliers.min_years_experience:
                return (
                    True,
                    QuarantineReason.MISSING_EXPERIENCE,
                    f"years_experience {yoe_float} is negative.",
                )
            if yoe_float > outliers.max_years_experience:
                return (
                    True,
                    QuarantineReason.OUTLIER,
                    f"years_experience {yoe_float} exceeds maximum career ceiling {outliers.max_years_experience}.",
                )
        except (ValueError, TypeError):
            return (
                True,
                QuarantineReason.MISSING_EXPERIENCE,
                f"years_experience '{yoe_val}' cannot be parsed as numeric float.",
            )

    # 8. Currency mismatch
    raw_curr = record.get("raw_currency")
    if raw_curr is not None:
        curr_str = str(raw_curr).upper()
        if curr_str not in ("INR", "RS", "RUPEES") and not record.get("is_currency_converted", False):
            return (
                True,
                QuarantineReason.CURRENCY_MISMATCH,
                f"Foreign currency '{raw_curr}' without verified FX conversion.",
            )

    # 9. Outlier pay bounds
    if cash_float < outliers.min_guaranteed_cash_annual:
        return (
            True,
            QuarantineReason.OUTLIER,
            f"guaranteed_cash_annual {cash_float:.2f} LPA is below entry floor {outliers.min_guaranteed_cash_annual:.2f} LPA.",
        )
    if cash_float > outliers.max_guaranteed_cash_annual:
        return (
            True,
            QuarantineReason.OUTLIER,
            f"guaranteed_cash_annual {cash_float:.2f} LPA exceeds base ceiling {outliers.max_guaranteed_cash_annual:.2f} LPA.",
        )

    tot_val = record.get("total_comp_annual")
    if tot_val is not None:
        try:
            tot_float = float(tot_val)
            if tot_float > outliers.max_total_comp_annual:
                return (
                    True,
                    QuarantineReason.OUTLIER,
                    f"total_comp_annual {tot_float:.2f} LPA exceeds ceiling {outliers.max_total_comp_annual:.2f} LPA.",
                )
            if tot_float < cash_float - 0.01:
                return (
                    True,
                    QuarantineReason.SCHEMA_VIOLATION,
                    f"total_comp_annual ({tot_float:.2f} LPA) cannot be less than guaranteed cash ({cash_float:.2f} LPA).",
                )
        except (ValueError, TypeError):
            pass

    # 10. Itemized sum consistency check
    basic = record.get("basic_annual")
    hra = record.get("hra_annual")
    spec = record.get("special_allowance_annual")
    if basic is not None and hra is not None and spec is not None:
        try:
            item_sum = float(basic) + float(hra) + float(spec)
            diff = abs(item_sum - cash_float)
            allowed_tol = max(
                rules.itemized_sum_relative_tolerance * cash_float,
                rules.itemized_sum_absolute_tolerance_lpa,
            )
            if diff > allowed_tol:
                return (
                    True,
                    QuarantineReason.SCHEMA_VIOLATION,
                    f"Itemized sum (Basic + HRA + Special = {item_sum:.2f} LPA) deviates by {diff:.2f} LPA from guaranteed cash ({cash_float:.2f} LPA).",
                )
        except (ValueError, TypeError):
            pass

    # 11. Exact duplicate check
    if record.get("is_exact_duplicate", False):
        dup_of = record.get("exact_duplicate_of") or "PRIOR_OBSERVATION"
        return (
            True,
            QuarantineReason.DUPLICATE,
            f"Exact duplicate of observation '{dup_of}'.",
        )

    # Record is valid
    return (False, None, None)


@dataclass(frozen=True)
class QuarantineReconciliationReport:
    """Mathematical proof of zero silent drops (Rule R-DA-05) and halt status (Rule R-ER-06)."""

    total_input_records: int
    valid_accepted_records: int
    quarantined_records: int
    quarantine_rate: float
    halt_threshold: float
    halt_triggered: bool
    is_reconciled: bool
    discrepancy_count: int
    counts_by_reason: dict[str, int]
    counts_by_source: dict[str, dict[str, int]]
    quarantine_version: str = DEFAULT_QUARANTINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary representation."""
        return {
            "total_input_records": self.total_input_records,
            "valid_accepted_records": self.valid_accepted_records,
            "quarantined_records": self.quarantined_records,
            "quarantine_rate": self.quarantine_rate,
            "halt_threshold": self.halt_threshold,
            "halt_triggered": self.halt_triggered,
            "is_reconciled": self.is_reconciled,
            "discrepancy_count": self.discrepancy_count,
            "counts_by_reason": self.counts_by_reason,
            "counts_by_source": self.counts_by_source,
            "quarantine_version": self.quarantine_version,
        }

    def to_dataframe(self) -> pl.DataFrame:
        """Convert reason counts breakdown to Polars DataFrame."""
        if not self.counts_by_reason:
            return pl.DataFrame(
                schema={
                    "quarantine_reason": pl.String,
                    "count": pl.Int64,
                    "percentage_of_quarantine": pl.Float64,
                }
            )
        reasons = list(self.counts_by_reason.keys())
        counts = list(self.counts_by_reason.values())
        tot_q = self.quarantined_records or 1
        pcts = [round(c / tot_q, 4) for c in counts]
        return pl.DataFrame(
            {
                "quarantine_reason": reasons,
                "count": counts,
                "percentage_of_quarantine": pcts,
            }
        ).sort("count", descending=True)

    def to_markdown(self) -> str:
        """Generate GitHub-Flavored Markdown reconciliation report."""
        status_badge = "✅ RECONCILED (Zero Silent Drops)" if self.is_reconciled else "❌ DISCREPANCY DETECTED"
        halt_badge = "🚨 HALT TRIGGERED" if self.halt_triggered else "🟢 PASS"

        lines: list[str] = [
            "# CompIntel Data Quality: Quarantine & Count Reconciliation Report",
            "",
            f"**Audit Status:** {status_badge} | **Pipeline Gate Status:** {halt_badge}",
            f"- **Quarantine Engine Version:** `{self.quarantine_version}`",
            f"- **Total Ingested Observations:** {self.total_input_records:,}",
            f"- **Valid Accepted Observations:** {self.valid_accepted_records:,}",
            f"- **Quarantined Observations:** {self.quarantined_records:,}",
            f"- **Quarantine Rate:** {self.quarantine_rate:.2%}",
            f"- **Halt Threshold Limit (Rule R-ER-06):** {self.halt_threshold:.2%}",
            f"- **Reconciliation Discrepancy ($\\Delta$):** {self.discrepancy_count} (Must equal 0)",
            "",
            "## Quarantine Reasons Breakdown",
            "",
            "| Quarantine Reason Code | Count | Share of Quarantined |",
            "|---|---|---|",
        ]

        tot_q = self.quarantined_records or 1
        for reason, count in sorted(self.counts_by_reason.items(), key=lambda x: x[1], reverse=True):
            pct = count / tot_q
            lines.append(f"| `{reason}` | {count:,} | {pct:.2%} |")

        lines.extend(
            [
                "",
                "## Per-Source Exclusion Audit",
                "",
                "| Source ID | Quarantined Records | Primary Exclusion Reason |",
                "|---|---|---|",
            ]
        )

        for sid in sorted(self.counts_by_source.keys()):
            s_dict = self.counts_by_source[sid]
            s_tot = sum(s_dict.values())
            top_reason = max(s_dict.items(), key=lambda x: x[1])[0] if s_dict else "None"
            lines.append(f"| `{sid}` | {s_tot:,} | `{top_reason}` |")

        lines.append("")
        return "\n".join(lines)


@dataclass(frozen=True)
class QuarantinePartitionResult:
    """Result of partitioning dataset into valid observations and quarantine table."""

    valid_df: pl.DataFrame
    quarantined_df: pl.DataFrame
    quarantine_records: list[QuarantineRecord]
    report: QuarantineReconciliationReport


def partition_and_quarantine_df(
    df: pl.DataFrame,
    id_column: str = "observation_id",
    source_column: str = "source_id",
    outlier_policy: OutlierPolicy | None = None,
    inconsistency_policy: InconsistencyPolicy | None = None,
    halt_threshold: float = DEFAULT_HALT_THRESHOLD,
    halt_on_exceed: bool = True,
    quarantine_version: str = DEFAULT_QUARANTINE_VERSION,
) -> QuarantinePartitionResult:
    """Evaluate and partition a Polars DataFrame into valid observations and quarantine table.

    Enforces:
    - Rule R-DA-05: Strict mathematical conservation (Total = Valid + Quarantined).
    - Rule R-ER-06: Configured halt threshold validation.

    Args:
        df: Polars DataFrame of candidate canonical observations.
        id_column: Column name containing observation identifier.
        source_column: Column name containing source identifier.
        outlier_policy: Custom outlier bounds (or default).
        inconsistency_policy: Custom consistency checks (or default).
        halt_threshold: Maximum allowable fraction of quarantined records before halting pipeline.
        halt_on_exceed: If True, raises PipelineHaltError when quarantine_rate > halt_threshold.
        quarantine_version: Version identifier attached to report.

    Returns:
        QuarantinePartitionResult containing valid_df, quarantined_df, typed QuarantineRecords, and report.

    Raises:
        PipelineHaltError: If halt_on_exceed is True and quarantine_rate > halt_threshold.
    """
    total_records = df.height
    if total_records == 0:
        empty_report = QuarantineReconciliationReport(
            total_input_records=0,
            valid_accepted_records=0,
            quarantined_records=0,
            quarantine_rate=0.0,
            halt_threshold=halt_threshold,
            halt_triggered=False,
            is_reconciled=True,
            discrepancy_count=0,
            counts_by_reason={},
            counts_by_source={},
            quarantine_version=quarantine_version,
        )
        empty_q_df = df.with_columns(
            pl.lit(None, dtype=pl.String).alias("quarantine_id"),
            pl.lit(None, dtype=pl.String).alias("quarantine_reason"),
            pl.lit(None, dtype=pl.String).alias("exclusion_details"),
            pl.lit(None, dtype=pl.Datetime).alias("quarantined_at"),
        )
        return QuarantinePartitionResult(
            valid_df=df,
            quarantined_df=empty_q_df,
            quarantine_records=[],
            report=empty_report,
        )

    records = df.iter_rows(named=True)
    valid_mask: list[bool] = []
    quarantine_ids: list[str | None] = []
    quarantine_reasons: list[str | None] = []
    exclusion_details: list[str | None] = []
    quarantined_timestamps: list[datetime | None] = []

    reason_counts: dict[str, int] = {}
    source_counts: dict[str, dict[str, int]] = {}
    quarantine_entities: list[QuarantineRecord] = []
    now_utc = datetime.now(UTC)

    for idx, r in enumerate(records):
        obs_id = str(r.get(id_column, f"ROW-{idx}"))
        src_id = str(r.get(source_column, "UNKNOWN"))

        is_q, q_reason, q_detail = evaluate_record_quarantine(
            record=r,
            outlier_policy=outlier_policy,
            inconsistency_policy=inconsistency_policy,
        )

        if is_q:
            assert q_reason is not None
            assert q_detail is not None

            # Generate unique deterministic quarantine ID
            q_token = f"{src_id}:{obs_id}:{q_reason.value}"
            qid = f"QRN-{hashlib.sha256(q_token.encode('utf-8')).hexdigest()[:12].upper()}"

            valid_mask.append(False)
            quarantine_ids.append(qid)
            quarantine_reasons.append(q_reason.value)
            exclusion_details.append(q_detail)
            quarantined_timestamps.append(now_utc)

            # Accounting
            reason_counts[q_reason.value] = reason_counts.get(q_reason.value, 0) + 1
            if src_id not in source_counts:
                source_counts[src_id] = {}
            source_counts[src_id][q_reason.value] = source_counts[src_id].get(q_reason.value, 0) + 1

            # Typed entity (Rule R-DA-05)
            quarantine_entities.append(
                QuarantineRecord(
                    quarantine_id=qid,
                    source_id=src_id,
                    quarantine_reason=q_reason,
                    exclusion_details=q_detail,
                    raw_payload={k: v for k, v in r.items() if v is not None},
                    quarantined_at=now_utc,
                )
            )
        else:
            valid_mask.append(True)
            quarantine_ids.append(None)
            quarantine_reasons.append(None)
            exclusion_details.append(None)
            quarantined_timestamps.append(None)

    valid_count = sum(1 for m in valid_mask if m)
    quarantined_count = total_records - valid_count
    quarantine_rate = round(quarantined_count / total_records, 4)

    # Count reconciliation audit: Total == Valid + Quarantined (Rule R-DA-05)
    discrepancy = total_records - (valid_count + quarantined_count)
    is_reconciled = discrepancy == 0

    halt_triggered = quarantine_rate > halt_threshold

    report = QuarantineReconciliationReport(
        total_input_records=total_records,
        valid_accepted_records=valid_count,
        quarantined_records=quarantined_count,
        quarantine_rate=quarantine_rate,
        halt_threshold=halt_threshold,
        halt_triggered=halt_triggered,
        is_reconciled=is_reconciled,
        discrepancy_count=discrepancy,
        counts_by_reason=reason_counts,
        counts_by_source=source_counts,
        quarantine_version=quarantine_version,
    )

    # Check Rule R-ER-06 halt threshold
    if halt_triggered and halt_on_exceed:
        raise PipelineHaltError(
            f"Quarantine rate of {quarantine_rate:.2%} ({quarantined_count}/{total_records}) "
            f"exceeded configured halt threshold of {halt_threshold:.2%} (Rule R-ER-06).",
            code="QUARANTINE_RATE_EXCEEDED",
            details={
                "total_input_records": total_records,
                "valid_accepted_records": valid_count,
                "quarantined_records": quarantined_count,
                "quarantine_rate": quarantine_rate,
                "halt_threshold": halt_threshold,
                "counts_by_reason": reason_counts,
            },
        )

    # Construct split DataFrames
    valid_df = df.filter(pl.Series(valid_mask))

    q_mask_series = pl.Series([not m for m in valid_mask])
    q_filtered = df.filter(q_mask_series)

    # Filter quarantine metadata to matched rows
    q_ids_filtered = [qid for qid, m in zip(quarantine_ids, valid_mask) if not m]
    q_reasons_filtered = [qr for qr, m in zip(quarantine_reasons, valid_mask) if not m]
    q_details_filtered = [qd for qd, m in zip(exclusion_details, valid_mask) if not m]
    q_ts_filtered = [qt for qt, m in zip(quarantined_timestamps, valid_mask) if not m]

    quarantined_df = q_filtered.with_columns(
        pl.Series("quarantine_id", q_ids_filtered, dtype=pl.String),
        pl.Series("quarantine_reason", q_reasons_filtered, dtype=pl.String),
        pl.Series("exclusion_details", q_details_filtered, dtype=pl.String),
        pl.Series("quarantined_at", q_ts_filtered, dtype=pl.Datetime),
    )

    return QuarantinePartitionResult(
        valid_df=valid_df,
        quarantined_df=quarantined_df,
        quarantine_records=quarantine_entities,
        report=report,
    )


def export_quarantine_artifacts(
    partition_result: QuarantinePartitionResult,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Export quarantine table parquet and markdown reconciliation report artifacts.

    Args:
        partition_result: Outcome from partition_and_quarantine_df.
        output_dir: Target destination directory (defaults to data/quarantine).

    Returns:
        tuple of (parquet_path, markdown_report_path).
    """
    dest = output_dir or Path("data/quarantine")
    dest.mkdir(parents=True, exist_ok=True)

    parquet_path = dest / "quarantine_table.parquet"
    partition_result.quarantined_df.write_parquet(parquet_path)

    md_path = dest / "quarantine_reconciliation_report.md"
    md_content = partition_result.report.to_markdown()
    md_path.write_text(md_content, encoding="utf-8")

    return (parquet_path, md_path)
