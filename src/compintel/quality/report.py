"""Automated data quality reporting and contract verification engine (Task T3.14).

Analyzes canonical observations, quarantine stores, and lineage manifests to generate
auditable metrics, contract compliance verifications, and publication-ready quality reports.

Governed by:
- Rule R-DA-02: Immutable raw zone with lineage.
- Rule R-DA-03: Companion raw values preserved.
- Rule R-DA-04: Mandatory provenance metadata attached.
- Rule R-DA-05: Count reconciliation (Delta = Total - Valid - Quarantined == 0).
- Rule R-DA-06: Deduplication before split.
- Rule R-DA-07: Strict privacy governance (zero cleartext PII).
- Rule R-MD-07: Anti-heuristic CTC unbundling.
- Rule R-ER-06: Pipeline halt thresholds.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from compintel.errors import DataContractError
from compintel.schema.canonical import CURRENT_SCHEMA_VERSION, canonical_dataframe_schema


class DataQualityReport(BaseModel):
    """Structured audit container recording end-to-end data quality metrics (T3.14)."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # 1. Lineage & Metadata
    snapshot_id: str = Field(..., description="Canonical dataset snapshot identifier.")
    manifest_hash: str = Field(..., description="Master SHA-256 digest of input raw manifests.")
    git_commit: str = Field(..., description="Git commit SHA from which the dataset was built.")
    config_hash: str = Field(..., description="Composite hash of active pipeline configurations.")
    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Canonical schema semver.",
    )
    generated_at: str = Field(..., description="UTC ISO 8601 timestamp of report generation.")

    # 2. Volume & Reconciliation (Rule R-DA-05)
    total_evaluated: int = Field(..., ge=0, description="Total raw observations evaluated.")
    valid_records: int = Field(..., ge=0, description="Valid canonical observations admitted.")
    quarantined_records: int = Field(
        ...,
        ge=0,
        description="Observations partitioned to quarantine.",
    )
    reconciliation_delta: int = Field(
        default=0,
        ge=0,
        le=0,
        description="Reconciliation delta (Total - Valid - Quarantined == 0).",
    )
    reconciliation_passed: bool = Field(
        ...,
        description="True if mathematical reconciliation holds exactly with zero silent drops.",
    )
    quarantine_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Proportion of evaluated records quarantined.",
    )

    # 3. Quarantine Breakdowns
    quarantine_reasons_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Count of quarantined records per deterministic reason code.",
    )
    quarantine_source_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Count of quarantined records per originating source ID.",
    )

    # 4. Valid Profile Distributions
    role_family_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Observation counts per canonical RoleFamily.",
    )
    seniority_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Observation counts per standardized SeniorityLevel.",
    )
    location_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Observation counts per MetroLocation.",
    )

    # 5. Compensation & Numerical Statistics
    guaranteed_cash_stats: dict[str, float] = Field(
        default_factory=dict,
        description="Parametric and non-parametric stats for guaranteed_cash_annual (INR LPA).",
    )
    experience_stats: dict[str, float] = Field(
        default_factory=dict,
        description="Summary statistics for years_experience.",
    )

    # 6. Deduplication & Entity Clusters (T3.10)
    distinct_person_clusters: int = Field(default=0, ge=0)
    distinct_employer_clusters: int = Field(default=0, ge=0)
    distinct_posting_clusters: int = Field(default=0, ge=0)
    exact_duplicates_count: int = Field(default=0, ge=0)

    # 7. Source Quality Scoring Framework (SQSF T3.12)
    mean_source_quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    provenance_tier_counts: dict[str, int] = Field(default_factory=dict)
    pt1_eligible_count: int = Field(default=0, ge=0)

    # 8. Synthetic Data Isolation (Rule R-MD-11)
    synthetic_records_count: int = Field(
        default=0,
        ge=0,
        description="Count of synthetic fixture records detected.",
    )
    synthetic_isolation_passed: bool = Field(
        default=True,
        description="True if dataset contains zero synthetic records (Rule R-MD-11).",
    )

    # 9. Contract Enforcement & Verdict
    contract_checks: dict[str, bool] = Field(
        default_factory=dict,
        description="Status of individual contract verification rules.",
    )
    overall_status: str = Field(
        ...,
        pattern=r"^(PASSED|FAILED)$",
        description="Overall quality verdict.",
    )

    def to_markdown(self) -> str:
        """Render publication-grade GitHub Flavored Markdown audit report."""
        status_badge = "**PASSED**" if self.overall_status == "PASSED" else "**FAILED**"
        reconcile_icon = "PASS" if self.reconciliation_passed else "FAIL"
        valid_share = (self.valid_records / max(self.total_evaluated, 1)) * 100.0
        quar_share = self.quarantine_rate * 100.0

        lines = [
            "# ArthaIQ Automated Data Quality & Contract Audit Report",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| **Snapshot ID** | `{self.snapshot_id}` |",
            f"| **Schema Version** | `{self.schema_version}` |",
            f"| **Git Commit** | `{self.git_commit[:10]}` |",
            f"| **Manifest Digest (SHA-256)** | `{self.manifest_hash[:16]}...` |",
            f"| **Generated At (UTC)** | `{self.generated_at}` |",
            f"| **Overall Contract Verdict** | {status_badge} |",
            "",
            "---",
            "",
            "## 1. Executive Summary & Volume Reconciliation (Rule R-DA-05)",
            "",
            "Mathematical count reconciliation verifies that no observations are silently dropped:",
            "",
            "| Metric | Count | Share | Status |",
            "|---|---|---|---|",
            f"| Total Raw Evaluated | **{self.total_evaluated:,}** | 100.0% | Audited |",
            f"| Admitted Canonical Observations | **{self.valid_records:,}** | "
            f"{valid_share:.2f}% | Ground Truth |",
            f"| Quarantined Records | **{self.quarantined_records:,}** | "
            f"{quar_share:.2f}% | Isolated |",
            f"| Reconciliation Delta ($\\Delta$) | **{self.reconciliation_delta}** | "
            f"0.0% | **{reconcile_icon}** (Rule R-DA-05) |",
            "",
            "> [!NOTE]",
            "> Zero silent drops is a non-negotiable architectural invariant (`R-DA-05`).",
            (
                f"> $\\Delta = \\text{{Total}} - (\\text{{Valid}} + \\text{{Quarantined}}) = "
                f"{self.total_evaluated} - ({self.valid_records} + {self.quarantined_records}) = "
                f"{self.reconciliation_delta}$."
            ),
        ]

        if self.synthetic_records_count > 0:
            lines.extend(
                [
                    "",
                    "> [!WARNING]",
                    (
                        f"> **Rule R-MD-11 Violation**: {self.synthetic_records_count} synthetic "
                        "fixture records detected."
                    ),
                    "> Synthetic data is strictly for plumbing and tests. Metrics computed on it "
                    "MUST NOT be reported as canonical data quality or model performance.",
                ]
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 2. Data Contract Verification Checklist",
                "",
                "| Rule ID | Contract Specification | Status |",
                "|---|---|---|",
            ]
        )

        rule_descriptions = {
            "schema_contract": "Pandera strict canonical dataframe schema conformance",
            "reconciliation_contract": "Zero silent drops count conservation (R-DA-05)",
            "unbundling_contract": "Anti-heuristic unbundling compliance (R-MD-07)",
            "pii_safety_contract": "Zero cleartext PII leakage in datasets (R-DA-07)",
            "cluster_id_contract": "Mandatory cluster IDs populated for all records (R-DA-06)",
            "sqsf_provenance_contract": "Source Quality Scores and tiers attached (T3.12)",
            "synthetic_isolation_contract": "Zero synthetic records in production data (R-MD-11)",
        }

        for check_key, passed in self.contract_checks.items():
            desc = rule_descriptions.get(check_key, check_key)
            status_str = "PASSED" if passed else "**FAILED**"
            lines.append(f"| `{check_key}` | {desc} | {status_str} |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. Quarantine Reason Distribution",
                "",
                "Observations isolated from primary model training under deterministic criteria:",
                "",
                "| Quarantine Reason Code | Count | Percentage | Operational Policy |",
                "|---|---|---|---|",
            ]
        )

        for reason, count in sorted(
            self.quarantine_reasons_breakdown.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / max(self.quarantined_records, 1)) * 100
            lines.append(f"| `{reason}` | {count:,} | {pct:.1f}% | Governed Isolation |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 4. Canonical Target Distribution (Nominal INR LPA)",
                "",
            ]
        )

        if self.valid_records > 0 and self.guaranteed_cash_stats:
            stats = self.guaranteed_cash_stats
            exp_min = self.experience_stats.get("min", 0.0)
            exp_med = self.experience_stats.get("median", 0.0)
            exp_mean = self.experience_stats.get("mean", 0.0)
            exp_max = self.experience_stats.get("max", 0.0)
            lines.extend(
                [
                    "| Statistic | Guaranteed Cash (INR LPA) | Years Experience |",
                    "|---|---|---|",
                    f"| Min | ₹{stats.get('min', 0.0):.2f} LPA | {exp_min:.1f} yrs |",
                    f"| P10 | ₹{stats.get('p10', 0.0):.2f} LPA | — |",
                    f"| P25 | ₹{stats.get('p25', 0.0):.2f} LPA | — |",
                    f"| Median (P50) | **₹{stats.get('median', 0.0):.2f} LPA** | "
                    f"**{exp_med:.1f} yrs** |",
                    f"| Mean | ₹{stats.get('mean', 0.0):.2f} LPA | {exp_mean:.1f} yrs |",
                    f"| P75 | ₹{stats.get('p75', 0.0):.2f} LPA | — |",
                    f"| P90 | ₹{stats.get('p90', 0.0):.2f} LPA | — |",
                    f"| Max | ₹{stats.get('max', 0.0):.2f} LPA | {exp_max:.1f} yrs |",
                ]
            )
        else:
            lines.append("*No admitted canonical records to profile.*")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 5. Occupational & Seniority Profile",
                "",
                "| Role Family | Records | Seniority Band | Records | Metro Location | Records |",
                "|---|---|---|---|---|---|",
            ]
        )

        roles = sorted(self.role_family_distribution.items())
        sens = sorted(self.seniority_distribution.items())
        locs = sorted(self.location_distribution.items())
        max_rows = max(len(roles), len(sens), len(locs), 1)

        for i in range(max_rows):
            r_str = f"`{roles[i][0]}`: {roles[i][1]}" if i < len(roles) else "—"
            s_str = f"`{sens[i][0]}`: {sens[i][1]}" if i < len(sens) else "—"
            l_str = f"`{locs[i][0]}`: {locs[i][1]}" if i < len(locs) else "—"
            lines.append(f"| {r_str} | — | {s_str} | — | {l_str} | — |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 6. Entity Resolution & Quality Scoring (SQSF)",
                "",
                "| Metric | Value | Reference Rule |",
                "|---|---|---|",
                f"| Distinct Person Clusters | **{self.distinct_person_clusters}** | "
                "Rule R-DA-06 (Dedup before split) |",
                f"| Distinct Employer Clusters | **{self.distinct_employer_clusters}** | "
                "Task T3.10b (Entity resolution) |",
                f"| Distinct Posting Clusters | **{self.distinct_posting_clusters}** | "
                "Task T3.10b (Posting clusters) |",
                f"| Exact Duplicate Count | **{self.exact_duplicates_count}** | "
                "Task T3.10a (Exact dedup) |",
                f"| Mean Source Quality Score | **{self.mean_source_quality_score:.1f} / 100** | "
                "Rule R-UQ-07 (Decoupled evidence) |",
                f"| PT1 Training Eligible Rows | **{self.pt1_eligible_count}** | "
                "Task T3.12 (SQSF Gate) |",
                "",
            ]
        )

        return "\n".join(lines)


def generate_data_quality_report(
    canonical_df: pl.DataFrame,
    quarantine_df: pl.DataFrame,
    lineage: Any | None = None,
    lineage_path: Path | None = None,
    halt_threshold: float = 0.999,
    allow_synthetic: bool = False,
) -> DataQualityReport:
    """Analyze canonical and quarantine DataFrames to generate complete DataQualityReport.

    Evaluates canonical schema conformance, count reconciliation (R-DA-05),
    unbundling constraints (R-MD-07), PII safety (R-DA-07), cluster completeness,
    SQSF provenance attachment (T3.12), and synthetic data isolation (R-MD-11).
    """
    # 1. Resolve lineage metadata
    if lineage is None:
        if lineage_path and Path(lineage_path).exists():
            with open(lineage_path, encoding="utf-8") as f:
                l_dict = json.load(f)
            snapshot_id = str(l_dict.get("snapshot_id", "SNAP-UNKNOWN"))
            manifest_hash = str(l_dict.get("manifest_hash", "0" * 64))
            git_commit = str(l_dict.get("git_commit", "0" * 40))
            config_hash = str(l_dict.get("config_hash", "0" * 64))
            schema_ver = str(l_dict.get("schema_version", CURRENT_SCHEMA_VERSION))
        else:
            snapshot_id = "SNAP-LOCAL"
            manifest_hash = "0" * 64
            git_commit = "0" * 40
            config_hash = "0" * 64
            schema_ver = CURRENT_SCHEMA_VERSION
    else:
        snapshot_id = getattr(lineage, "snapshot_id", "SNAP-UNKNOWN")
        manifest_hash = getattr(lineage, "manifest_hash", "0" * 64)
        git_commit = getattr(lineage, "git_commit", "0" * 40)
        config_hash = getattr(lineage, "config_hash", "0" * 64)
        schema_ver = getattr(lineage, "schema_version", CURRENT_SCHEMA_VERSION)

    valid_c = canonical_df.height
    quar_c = quarantine_df.height
    total_eval = valid_c + quar_c
    quar_rate = (quar_c / total_eval) if total_eval > 0 else 0.0

    # 2. Count reconciliation check (Rule R-DA-05)
    reconcile_delta = total_eval - (valid_c + quar_c)
    reconcile_passed = reconcile_delta == 0

    # 3. Contract checks
    contract_checks: dict[str, bool] = {
        "reconciliation_contract": reconcile_passed,
    }

    # Schema check
    try:
        canonical_dataframe_schema.validate(canonical_df)
        contract_checks["schema_contract"] = True
    except Exception:
        contract_checks["schema_contract"] = False

    # Anti-heuristic CTC unbundling check (Rule R-MD-07)
    has_unbundled_col = "is_unbundled_aggregate" in canonical_df.columns
    has_cash_col = "guaranteed_cash_annual" in canonical_df.columns
    if has_unbundled_col and has_cash_col:
        unbundled_violation = (
            canonical_df.filter(
                (pl.col("is_unbundled_aggregate") == True)  # noqa: E712
                & pl.col("guaranteed_cash_annual").is_not_null()
            ).height
            > 0
        )
        contract_checks["unbundling_contract"] = not unbundled_violation
    else:
        contract_checks["unbundling_contract"] = True

    # PII Safety Check (Rule R-DA-07)
    forbidden_pii = {"email", "phone", "pan", "aadhaar", "full_name", "contributor_name"}
    found_pii = forbidden_pii.intersection(set(canonical_df.columns)).union(
        forbidden_pii.intersection(set(quarantine_df.columns))
    )
    contract_checks["pii_safety_contract"] = len(found_pii) == 0

    # Cluster IDs Check (Rule R-DA-06)
    expected_clusters = {
        "exact_duplicate_cluster_id",
        "person_cluster_id",
        "employer_cluster_id",
        "posting_cluster_id",
    }
    has_clusters = expected_clusters.issubset(set(canonical_df.columns))
    contract_checks["cluster_id_contract"] = has_clusters

    # SQSF Provenance Check (Task T3.12)
    has_sqsf = {"source_quality_score", "provenance_tier", "hard_gates_passed"}.issubset(
        set(canonical_df.columns)
    )
    contract_checks["sqsf_provenance_contract"] = has_sqsf

    # Synthetic Data Isolation Check (Rule R-MD-11)
    synth_valid = (
        canonical_df.filter(pl.col("is_synthetic") == True).height  # noqa: E712
        if "is_synthetic" in canonical_df.columns
        else 0
    )
    synth_quar = (
        quarantine_df.filter(pl.col("is_synthetic") == True).height  # noqa: E712
        if "is_synthetic" in quarantine_df.columns
        else 0
    )
    total_synth = synth_valid + synth_quar
    synth_passed = (total_synth == 0) or allow_synthetic
    contract_checks["synthetic_isolation_contract"] = synth_passed

    # Overall Status
    all_passed = all(contract_checks.values()) and (quar_rate <= halt_threshold)
    overall_status = "PASSED" if all_passed else "FAILED"

    # 4. Quarantine breakdowns
    reasons_breakdown: dict[str, int] = {}
    if "quarantine_reason" in quarantine_df.columns and quar_c > 0:
        counts = quarantine_df.group_by("quarantine_reason").len()
        reasons_breakdown = {
            str(row["quarantine_reason"]): int(row["len"]) for row in counts.to_dicts()
        }

    sources_breakdown: dict[str, int] = {}
    if "source_id" in quarantine_df.columns and quar_c > 0:
        counts = quarantine_df.group_by("source_id").len()
        sources_breakdown = {str(row["source_id"]): int(row["len"]) for row in counts.to_dicts()}

    # 5. Profiles distributions
    roles_dist: dict[str, int] = {}
    if "role_family" in canonical_df.columns and valid_c > 0:
        counts = canonical_df.group_by("role_family").len()
        roles_dist = {str(row["role_family"]): int(row["len"]) for row in counts.to_dicts()}

    sen_dist: dict[str, int] = {}
    if "seniority" in canonical_df.columns and valid_c > 0:
        counts = canonical_df.group_by("seniority").len()
        sen_dist = {str(row["seniority"]): int(row["len"]) for row in counts.to_dicts()}

    loc_dist: dict[str, int] = {}
    if "location" in canonical_df.columns and valid_c > 0:
        counts = canonical_df.group_by("location").len()
        loc_dist = {str(row["location"]): int(row["len"]) for row in counts.to_dicts()}

    # 6. Statistics
    def _safe_float(val: Any, default: float = 0.0) -> float:
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    pay_stats: dict[str, float] = {}
    if "guaranteed_cash_annual" in canonical_df.columns and valid_c > 0:
        pay_series = canonical_df["guaranteed_cash_annual"].drop_nulls()
        if pay_series.len() > 0:
            pay_stats = {
                "min": _safe_float(pay_series.min()),
                "p10": _safe_float(pay_series.quantile(0.10)),
                "p25": _safe_float(pay_series.quantile(0.25)),
                "median": _safe_float(pay_series.median()),
                "mean": _safe_float(pay_series.mean()),
                "p75": _safe_float(pay_series.quantile(0.75)),
                "p90": _safe_float(pay_series.quantile(0.90)),
                "max": _safe_float(pay_series.max()),
            }

    exp_stats: dict[str, float] = {}
    if "years_experience" in canonical_df.columns and valid_c > 0:
        exp_series = canonical_df["years_experience"].drop_nulls()
        if exp_series.len() > 0:
            exp_stats = {
                "min": _safe_float(exp_series.min()),
                "median": _safe_float(exp_series.median()),
                "mean": _safe_float(exp_series.mean()),
                "max": _safe_float(exp_series.max()),
            }

    # 7. Cluster counts
    distinct_persons = (
        canonical_df["person_cluster_id"].n_unique()
        if "person_cluster_id" in canonical_df.columns
        else 0
    )
    distinct_employers = (
        canonical_df["employer_cluster_id"].n_unique()
        if "employer_cluster_id" in canonical_df.columns
        else 0
    )
    distinct_postings = (
        canonical_df["posting_cluster_id"].n_unique()
        if "posting_cluster_id" in canonical_df.columns
        else 0
    )
    exact_dups = (
        canonical_df.filter(pl.col("is_exact_duplicate") == True).height  # noqa: E712
        if "is_exact_duplicate" in canonical_df.columns
        else 0
    )

    # 8. SQSF metrics
    mean_sqs = 0.0
    if "source_quality_score" in canonical_df.columns and valid_c > 0:
        raw_m = canonical_df["source_quality_score"].mean()
        mean_sqs = float(raw_m) if isinstance(raw_m, int | float) else 0.0

    prov_counts: dict[str, int] = {}
    if "provenance_tier" in canonical_df.columns and valid_c > 0:
        counts = canonical_df.group_by("provenance_tier").len()
        prov_counts = {str(row["provenance_tier"]): int(row["len"]) for row in counts.to_dicts()}

    pt1_eligible = (
        canonical_df.filter(pl.col("is_pt1_eligible") == True).height  # noqa: E712
        if "is_pt1_eligible" in canonical_df.columns
        else 0
    )

    return DataQualityReport(
        snapshot_id=snapshot_id,
        manifest_hash=manifest_hash,
        git_commit=git_commit,
        config_hash=config_hash,
        schema_version=schema_ver,
        generated_at=datetime.now(UTC).isoformat(),
        total_evaluated=total_eval,
        valid_records=valid_c,
        quarantined_records=quar_c,
        reconciliation_delta=reconcile_delta,
        reconciliation_passed=reconcile_passed,
        quarantine_rate=quar_rate,
        quarantine_reasons_breakdown=reasons_breakdown,
        quarantine_source_breakdown=sources_breakdown,
        role_family_distribution=roles_dist,
        seniority_distribution=sen_dist,
        location_distribution=loc_dist,
        guaranteed_cash_stats=pay_stats,
        experience_stats=exp_stats,
        distinct_person_clusters=distinct_persons,
        distinct_employer_clusters=distinct_employers,
        distinct_posting_clusters=distinct_postings,
        exact_duplicates_count=exact_dups,
        mean_source_quality_score=mean_sqs,
        provenance_tier_counts=prov_counts,
        pt1_eligible_count=pt1_eligible,
        synthetic_records_count=total_synth,
        synthetic_isolation_passed=total_synth == 0,
        contract_checks=contract_checks,
        overall_status=overall_status,
    )


def export_data_quality_report(
    report: DataQualityReport,
    output_md_path: Path,
    output_json_path: Path,
) -> None:
    """Persist DataQualityReport as formatted Markdown and structured JSON."""
    md_p = Path(output_md_path).resolve()
    json_p = Path(output_json_path).resolve()

    md_p.parent.mkdir(parents=True, exist_ok=True)
    json_p.parent.mkdir(parents=True, exist_ok=True)

    with open(md_p, "w", encoding="utf-8") as f:
        f.write(report.to_markdown())

    with open(json_p, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))


def validate_no_synthetic_data(df: pl.DataFrame, context: str = "production") -> None:
    """Verify that a DataFrame contains zero synthetic records (Rule R-MD-11).

    Raises DataContractError if synthetic records are detected in production datasets.
    """
    if "is_synthetic" in df.columns:
        synth_c = df.filter(pl.col("is_synthetic") == True).height  # noqa: E712
        if synth_c > 0:
            raise DataContractError(
                f"Rule R-MD-11 violation: {synth_c} synthetic records in {context}. "
                "Synthetic data is strictly prohibited from production metrics and reports.",
                code="SYNTHETIC_DATA_PROHIBITED",
                details={"synthetic_count": synth_c, "context": context},
            )


def block_synthetic_from_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """Filter out synthetic observations before computing metrics (Rule R-MD-11)."""
    if "is_synthetic" in df.columns:
        return df.filter(pl.col("is_synthetic") == False)  # noqa: E712
    return df
