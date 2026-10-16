#!/usr/bin/env python3
"""Canonical data reproduction and lineage engine for CompIntel (Task T3.13).

Rebuilds canonical datasets from verified raw manifests, computes deterministic
cryptographic snapshot hashes, attaches provenance tiers and cluster IDs, enforces
quarantine policies, validates schema contracts, and produces immutable lineage manifests.

Governed by:
- Rule R-DA-01: Licence gate blocks unapproved sources.
- Rule R-DA-02: Immutable raw zone; lineage recorded (commit, config, manifests, schema).
- Rule R-DA-03: Raw values preserved beside normalized values.
- Rule R-DA-04: Mandatory provenance metadata attached to every record.
- Rule R-DA-05: Count reconciliation (Total = Valid + Quarantined, Delta = 0).
- Rule R-DA-06: Deduplication and clustering occur before splits.
- Rule R-DA-08: Data is gitignored; manifests are committed.
- Rule R-MD-07: Anti-heuristic CTC unbundling.
- ADR-0006: Deterministic snapshot identifier and idempotent clean runs.

Usage:
    uv run python scripts/reproduce_data.py [--verify-idempotence] [--snapshot SNAP-XXX]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl

# Ensure src/ is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from compintel.errors import DataContractError
from compintel.ingestion.connector import get_connector
from compintel.ingestion.lineage import (
    DataSnapshotLineage,
    compute_dataframe_content_hash,
    create_snapshot_lineage,
    save_lineage,
)
from compintel.ingestion.manifest import verify_licence_gate, verify_manifest
from compintel.normalization.titles import normalize_title
from compintel.quality.dedup import deduplicate_records_df
from compintel.quality.scoring import attach_source_quality_scores_df
from compintel.schema.canonical import CURRENT_SCHEMA_VERSION, validate_observations_df
from compintel.schema.enums import (
    MetroLocation,
    PayPeriod,
    ProvenanceTier,
    QuarantineReason,
    RoleFamily,
    SeniorityLevel,
    TaxBasis,
)


@dataclass(frozen=True)
class ReproductionResult:
    """Outcome of canonical dataset reproduction run."""

    snapshot_id: str
    manifest_hash: str
    git_commit: str
    config_hash: str
    schema_version: str
    total_records: int
    valid_records: int
    quarantined_records: int
    reconciliation_delta: int
    data_hash: str
    parquet_path: Path
    lineage_path: Path
    valid_df: pl.DataFrame
    quarantine_df: pl.DataFrame
    lineage: DataSnapshotLineage


def _parse_float(val: Any) -> float | None:
    """Parse numeric float from string/number safely."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.upper() == "NA" or s.upper() == "NULL":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _map_location_str(loc_str: str | None) -> MetroLocation:
    """Normalize raw location string to MetroLocation enum."""
    if not loc_str:
        return MetroLocation.OTHER
    normalized = loc_str.strip().upper()
    if any(k in normalized for k in ["BANGALORE", "BENGALURU", "BLR"]):
        return MetroLocation.BENGALURU
    if any(k in normalized for k in ["HYDERABAD", "HYD", "SECUNDERABAD"]):
        return MetroLocation.HYDERABAD
    if any(k in normalized for k in ["DELHI", "NCR", "GURGAON", "GURUGRAM", "NOIDA"]):
        return MetroLocation.NCR
    if any(k in normalized for k in ["MUMBAI", "BOM", "NAVI MUMBAI", "THANE"]):
        return MetroLocation.MUMBAI
    if any(k in normalized for k in ["PUNE", "PNQ"]):
        return MetroLocation.PUNE
    if any(k in normalized for k in ["CHENNAI", "MADRAS", "CHE"]):
        return MetroLocation.CHENNAI
    return MetroLocation.OTHER


def build_canonical_dataset(
    repo_root: Path,
    raw_dir: Path | None = None,
    config_dir: Path | None = None,
    canonical_dir: Path | None = None,
    quarantine_dir: Path | None = None,
    verify_manifests: bool = True,
) -> ReproductionResult:
    """Build canonical compensation observations from verified raw manifests (T3.13).

    Enforces all quality, normalization, deduplication, quarantine, and schema contracts.
    """
    root = Path(repo_root).resolve()
    raw_path = Path(raw_dir).resolve() if raw_dir else root / "data" / "raw"
    cfg_path = Path(config_dir).resolve() if config_dir else root / "config"
    canon_path = Path(canonical_dir).resolve() if canonical_dir else root / "data" / "canonical"
    quar_path = Path(quarantine_dir).resolve() if quarantine_dir else root / "data" / "quarantine"

    canon_path.mkdir(parents=True, exist_ok=True)
    quar_path.mkdir(parents=True, exist_ok=True)
    snapshots_dir = canon_path / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    # 1. Manifest verification across all candidate / approved sources (Rule R-DA-01, R-DA-02)
    active_source_dirs = sorted(raw_path.glob("*/manifest.yaml"))
    if not active_source_dirs:
        raise FileNotFoundError(f"No source directories with manifest.yaml found in {raw_path}")

    for m_file in active_source_dirs:
        sid = m_file.parent.name
        if verify_manifests:
            verify_licence_gate(sid, repo_root=root)
            verify_manifest(m_file)

    # 2. Extract records and transform to canonical candidates
    total_evaluated = 0
    valid_observations: list[dict[str, Any]] = []
    quarantine_records: list[dict[str, Any]] = []

    def record_quarantine(
        sid: str,
        rid: str,
        code: QuarantineReason,
        detail: str,
        payload_summary: str = "",
    ) -> None:
        quarantine_records.append(
            {
                "observation_id": f"QUAR-{sid}-{rid}",
                "source_id": sid,
                "source_record_id": str(rid),
                "quarantine_reason": code.value,
                "quarantine_detail": detail,
                "raw_summary": payload_summary[:150],
                "quarantined_at": datetime.now(UTC).isoformat(),
            }
        )

    # -------------------------------------------------------------------------
    # A. Governed Voluntary Intake: SRC-INT-VOL-01 (Single PT1 Ground Truth)
    # -------------------------------------------------------------------------
    vol_conn = get_connector("SRC-INT-VOL-01", raw_dir=raw_path, repo_root=root)
    for raw_rec in vol_conn.extract_raw_records():
        total_evaluated += 1
        p = raw_rec.raw_payload
        sub_id = str(p.get("submission_id", f"VOL-{total_evaluated}"))
        sub_date_str = str(p.get("submission_date", "2024-06-15"))
        as_of = date.fromisoformat(sub_date_str)

        # Monetary fields
        basic_monthly = _parse_float(p.get("basic_salary_monthly_inr")) or 0.0
        fixed_allow_monthly = _parse_float(p.get("fixed_allowances_monthly_inr")) or 0.0
        guaranteed_annual_inr = _parse_float(p.get("guaranteed_cash_annual_inr")) or (
            (basic_monthly + fixed_allow_monthly) * 12.0
        )
        variable_annual_inr = _parse_float(p.get("variable_bonus_target_annual_inr")) or 0.0
        equity_annual_inr = _parse_float(p.get("equity_grant_annualized_inr")) or 0.0
        ctc_annual_inr = _parse_float(p.get("total_ctc_annual_inr")) or (
            guaranteed_annual_inr + variable_annual_inr + equity_annual_inr
        )
        take_home_monthly = _parse_float(p.get("take_home_monthly_inr")) or 0.0

        guaranteed_lpa = guaranteed_annual_inr / 100_000.0
        basic_lpa = (basic_monthly * 12.0) / 100_000.0
        fixed_allow_lpa = (fixed_allow_monthly * 12.0) / 100_000.0
        variable_lpa = variable_annual_inr / 100_000.0
        equity_lpa = equity_annual_inr / 100_000.0
        total_comp_lpa = (
            guaranteed_annual_inr + variable_annual_inr + equity_annual_inr
        ) / 100_000.0
        ctc_lpa = ctc_annual_inr / 100_000.0
        take_home_lpa = (take_home_monthly * 12.0) / 100_000.0

        # Profile fields
        raw_role = str(p.get("role_family", "SWE"))
        fam = (
            RoleFamily(raw_role) if raw_role in RoleFamily._value2member_map_ else RoleFamily.OTHER
        )
        norm_title_res = normalize_title(raw_role)
        canon_title = norm_title_res.canonical_title

        raw_sen = str(p.get("seniority_level", "MID")).upper()
        sen_map = {
            "ENTRY": SeniorityLevel.JR,
            "MID": SeniorityLevel.MID,
            "SENIOR": SeniorityLevel.SR,
            "STAFF": SeniorityLevel.STAFF,
            "PRINCIPAL": SeniorityLevel.PRINCIPAL,
        }
        seniority = sen_map.get(raw_sen, SeniorityLevel.MID)

        raw_loc = str(p.get("metro_location", "BENGALURU"))
        loc = _map_location_str(raw_loc)
        yoe = _parse_float(p.get("yoe_total")) or 0.0

        # Build canonical observation dict
        obs = {
            "observation_id": f"OBS-{raw_rec.source_id}-{sub_id}",
            "source_id": raw_rec.source_id,
            "source_version": raw_rec.source_version,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "license_id": raw_rec.license_id,
            "provenance_tier": ProvenanceTier.TIER_A.value,
            "as_of_date": as_of,
            "ingested_at": raw_rec.retrieved_at,
            "is_synthetic": False,
            "role_family": fam.value,
            "canonical_title": canon_title,
            "raw_title": raw_role,
            "seniority": seniority.value,
            "location": loc.value,
            "raw_location": raw_loc,
            "years_experience": yoe,
            "education_level": str(p.get("education_level", "B.Tech / B.E.")),
            "skills": [fam.value, canon_title],
            "guaranteed_cash_annual": guaranteed_lpa,
            "basic_annual": basic_lpa,
            "hra_annual": None,
            "special_allowance_annual": None,
            "fixed_allowances_annual": fixed_allow_lpa,
            "variable_cash_annual": variable_lpa,
            "signon_bonus_cash": 0.0,
            "equity_annual_val": equity_lpa,
            "total_comp_annual": total_comp_lpa,
            "ctc_annual": ctc_lpa,
            "take_home_annual": take_home_lpa,
            "advertised_min_annual": None,
            "advertised_max_annual": None,
            "raw_pay_amount": guaranteed_annual_inr,
            "raw_currency": "INR",
            "raw_pay_period": PayPeriod.ANNUAL.value,
            "raw_tax_basis": TaxBasis.GROSS_PRETAX.value,
            "is_unbundled_aggregate": False,
            "quarantine_status": False,
            "quarantine_reason": None,
        }
        valid_observations.append(obs)

    # -------------------------------------------------------------------------
    # B. Stack Overflow Surveys: SRC-KAG-SO-01 & SRC-KAG-SO-02
    # -------------------------------------------------------------------------
    for sid in ["SRC-KAG-SO-01", "SRC-KAG-SO-02"]:
        so_conn = get_connector(sid, raw_dir=raw_path, repo_root=root)
        for raw_rec in so_conn.extract_raw_records():
            total_evaluated += 1
            p = raw_rec.raw_payload
            rid = str(p.get("ResponseId", f"{total_evaluated}"))
            country = str(p.get("Country", "")).strip()

            if country != "India":
                record_quarantine(
                    sid,
                    rid,
                    QuarantineReason.GEO_OUT_OF_SCOPE,
                    f"Non-India geography: {country}",
                    payload_summary=str(p),
                )
                continue

            emp = str(p.get("Employment", "")).lower()
            if "full-time" not in emp or "part-time" in emp or "student" in emp:
                record_quarantine(
                    sid,
                    rid,
                    QuarantineReason.NON_FULLTIME,
                    f"Non-full-time employment status: {emp[:40]}",
                    payload_summary=str(p),
                )
                continue

            comp_val = _parse_float(p.get("CompTotal"))
            if comp_val is None:
                record_quarantine(
                    sid,
                    rid,
                    QuarantineReason.MISSING_PAY,
                    "CompTotal is null or missing",
                    payload_summary=str(p),
                )
                continue

            curr = str(p.get("Currency", "")).upper()
            if "INR" not in curr:
                record_quarantine(
                    sid,
                    rid,
                    QuarantineReason.CURRENCY_MISMATCH,
                    f"Reported currency '{curr}' is not INR",
                    payload_summary=str(p),
                )
                continue

            lpa = comp_val / 100_000.0
            if lpa < 0.5 or lpa > 500.0:
                record_quarantine(
                    sid,
                    rid,
                    QuarantineReason.OUTLIER,
                    f"Reported compensation {lpa:.2f} LPA outside bounds [0.5, 500.0]",
                    payload_summary=str(p),
                )
                continue

            # Per Rule R-MD-07: Survey CompTotal is bundled aggregate CTC without itemization
            record_quarantine(
                sid,
                rid,
                QuarantineReason.UNBUNDLED_AGGREGATE,
                "Self-reported aggregate CompTotal without itemized basic/allowance breakdown (Rule R-MD-07)",
                payload_summary=str(p),
            )

    # -------------------------------------------------------------------------
    # C. AI Jobs in Data: SRC-KAG-AIJ-01 & SRC-KAG-AIJ-02
    # -------------------------------------------------------------------------
    for sid in ["SRC-KAG-AIJ-01", "SRC-KAG-AIJ-02"]:
        aij_conn = get_connector(sid, raw_dir=raw_path, repo_root=root)
        for raw_rec in aij_conn.extract_raw_records():
            total_evaluated += 1
            p = raw_rec.raw_payload
            rid = f"{sid}-{total_evaluated}"
            residence = str(p.get("employee_residence", "")).strip().upper()

            if residence != "IN":
                record_quarantine(
                    sid,
                    rid,
                    QuarantineReason.GEO_OUT_OF_SCOPE,
                    f"Non-India employee residence: {residence}",
                    payload_summary=str(p),
                )
                continue

            # Non-itemized survey pay
            record_quarantine(
                sid,
                rid,
                QuarantineReason.UNBUNDLED_AGGREGATE,
                "Bundled aggregate pay without statutory breakdown (Rule R-MD-07)",
                payload_summary=str(p),
            )

    # -------------------------------------------------------------------------
    # D. Statutory Corporate Remuneration: SRC-SUP-CORP-01
    # -------------------------------------------------------------------------
    corp_conn = get_connector("SRC-SUP-CORP-01", raw_dir=raw_path, repo_root=root)
    for raw_rec in corp_conn.extract_raw_records():
        total_evaluated += 1
        p = raw_rec.raw_payload
        comp_name = str(p.get("company_name", "IT_CORP"))
        record_quarantine(
            "SRC-SUP-CORP-01",
            comp_name,
            QuarantineReason.ENTERPRISE_AGGREGATE,
            f"Statutory enterprise census median for {comp_name}; not an individual observation",
            payload_summary=str(p),
        )

    # -------------------------------------------------------------------------
    # E. Official Indian Labor Statistics: SRC-IND-OFF-01 & SRC-IND-OFF-03
    # -------------------------------------------------------------------------
    for sid, code_val in [
        ("SRC-IND-OFF-01", QuarantineReason.ENTERPRISE_AGGREGATE),
        ("SRC-IND-OFF-03", QuarantineReason.ENTERPRISE_AGGREGATE),
    ]:
        off_conn = get_connector(sid, raw_dir=raw_path, repo_root=root)
        for raw_rec in off_conn.extract_raw_records():
            total_evaluated += 1
            record_quarantine(
                sid,
                f"{sid}-{total_evaluated}",
                code_val,
                "National macro labor quantile summary; quarantined from PT1 individual training",
                payload_summary=str(raw_rec.raw_payload),
            )

    # -------------------------------------------------------------------------
    # F. US Regulatory Disclosures: SRC-USA-BLS-01, SRC-USA-DOL-01, SRC-USA-DOL-02
    # -------------------------------------------------------------------------
    for sid in ["SRC-USA-BLS-01", "SRC-USA-DOL-01", "SRC-USA-DOL-02"]:
        us_conn = get_connector(sid, raw_dir=raw_path, repo_root=root)
        for raw_rec in us_conn.extract_raw_records():
            total_evaluated += 1
            record_quarantine(
                sid,
                f"{sid}-{total_evaluated}",
                QuarantineReason.GEO_OUT_OF_SCOPE,
                "United States labor disclosures quarantined from India tech model under Rule R-MD-08",
                payload_summary=str(raw_rec.raw_payload),
            )

    # 3. Assemble Polars DataFrames and apply quality enrichment
    valid_df = pl.DataFrame(valid_observations)
    quarantine_df = pl.DataFrame(quarantine_records)

    # Mathematical reconciliation proof: Delta = Total - (Valid + Quarantined) == 0 (Rule R-DA-05)
    reconciliation_delta = total_evaluated - (valid_df.height + quarantine_df.height)
    if reconciliation_delta != 0:
        raise DataContractError(
            f"Rule R-DA-05 violation: Total ({total_evaluated}) != "
            f"Valid ({valid_df.height}) + Quarantined ({quarantine_df.height}). Delta={reconciliation_delta}",
            code="RECONCILIATION_COUNT_MISMATCH",
        )

    # Attach Source Quality Scores (SQSF T3.12)
    valid_df = attach_source_quality_scores_df(valid_df, config_dir=cfg_path, strict=False)

    # Run Deduplication & Cluster ID Assignment (T3.10)
    valid_df = deduplicate_records_df(valid_df)

    # Validate schema contract (Pandera bulk validation)
    validated_df = validate_observations_df(valid_df)

    # Sort deterministically by observation_id
    sorted_valid_df = validated_df.sort("observation_id")
    sorted_quar_df = (
        quarantine_df.sort(["source_id", "observation_id"])
        if quarantine_df.height > 0
        else quarantine_df
    )

    # 4. Compute Content Hashes and Lineage Snapshot ID (ADR-0006)
    data_hash = compute_dataframe_content_hash(sorted_valid_df)
    lineage = create_snapshot_lineage(
        raw_dir=raw_path,
        config_dir=cfg_path,
        record_count=sorted_valid_df.height,
        quarantined_count=sorted_quar_df.height,
        data_hash=data_hash,
        repo_root=root,
        metadata={"polars_version": pl.__version__, "schema_version": CURRENT_SCHEMA_VERSION},
    )

    # 5. Persist canonical artifacts
    canonical_parquet_path = canon_path / "canonical_observations.parquet"
    snapshot_parquet_path = snapshots_dir / f"{lineage.snapshot_id}.parquet"
    sorted_valid_df.write_parquet(canonical_parquet_path)
    sorted_valid_df.write_parquet(snapshot_parquet_path)

    # Persist quarantine artifact
    quarantine_parquet_path = quar_path / "quarantine_records.parquet"
    sorted_quar_df.write_parquet(quarantine_parquet_path)

    # Persist lineage JSON manifests
    lineage_json_path = canon_path / "canonical_lineage.json"
    snapshot_lineage_path = snapshots_dir / f"{lineage.snapshot_id}_lineage.json"
    save_lineage(lineage, lineage_json_path)
    save_lineage(lineage, snapshot_lineage_path)

    return ReproductionResult(
        snapshot_id=lineage.snapshot_id,
        manifest_hash=lineage.manifest_hash,
        git_commit=lineage.git_commit,
        config_hash=lineage.config_hash,
        schema_version=lineage.schema_version,
        total_records=total_evaluated,
        valid_records=sorted_valid_df.height,
        quarantined_records=sorted_quar_df.height,
        reconciliation_delta=reconciliation_delta,
        data_hash=data_hash,
        parquet_path=canonical_parquet_path,
        lineage_path=lineage_json_path,
        valid_df=sorted_valid_df,
        quarantine_df=sorted_quar_df,
        lineage=lineage,
    )


def main() -> int:
    """CLI entrypoint for make reproduce-data."""
    parser = argparse.ArgumentParser(
        description="CompIntel canonical data reproduction & lineage engine (T3.13)."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root,
        help="Repository root directory.",
    )
    parser.add_argument(
        "--verify-idempotence",
        action="store_true",
        help="Run reproduction twice consecutively to verify identical cryptographic snapshot and data hashes.",
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        default=None,
        help="Expected snapshot ID to verify against.",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("  CompIntel Canonical Data Reproduction & Lineage Pipeline (Task T3.13)")
    print("  Rules: R-DA-01, R-DA-02, R-DA-03, R-DA-04, R-DA-05, R-DA-06, R-DA-08; ADR-0006")
    print("=" * 80)

    try:
        run1 = build_canonical_dataset(repo_root=args.repo_root)

        print("\n--- Run 1 Execution Summary ---")
        print(f"  Snapshot ID            : {run1.snapshot_id}")
        print(f"  Manifest Hash (SHA256) : {run1.manifest_hash}")
        print(f"  Git Commit             : {run1.git_commit}")
        print(f"  Config Hash (SHA256)   : {run1.config_hash}")
        print(f"  Schema Version         : {run1.schema_version}")
        print(f"  Total Ingested Records : {run1.total_records}")
        print(f"  Valid Canonical Records: {run1.valid_records}")
        print(f"  Quarantined Records    : {run1.quarantined_records}")
        print(
            f"  Count Reconciliation   : Delta = {run1.reconciliation_delta} (PROVEN: Total = Valid + Quarantined)"
        )
        print(f"  Data Hash (SHA256)     : {run1.data_hash}")
        print(f"  Parquet Artifact       : {run1.parquet_path}")
        print(f"  Lineage Manifest       : {run1.lineage_path}")

        if args.snapshot and run1.snapshot_id != args.snapshot:
            print(
                f"\n[ERROR] Snapshot mismatch! Expected: {args.snapshot}, Got: {run1.snapshot_id}",
                file=sys.stderr,
            )
            return 1

        if args.verify_idempotence:
            print("\n--- Running Clean Run 2 for Idempotency Verification ---")
            run2 = build_canonical_dataset(repo_root=args.repo_root)

            assert run1.snapshot_id == run2.snapshot_id, (
                f"Snapshot ID mismatch: {run1.snapshot_id} != {run2.snapshot_id}"
            )
            assert run1.manifest_hash == run2.manifest_hash, (
                f"Manifest hash mismatch: {run1.manifest_hash} != {run2.manifest_hash}"
            )
            assert run1.config_hash == run2.config_hash, (
                f"Config hash mismatch: {run1.config_hash} != {run2.config_hash}"
            )
            assert run1.data_hash == run2.data_hash, (
                f"Data content hash mismatch: {run1.data_hash} != {run2.data_hash}"
            )
            assert run1.total_records == run2.total_records, "Total record count mismatch"
            assert run1.valid_records == run2.valid_records, "Valid record count mismatch"
            assert run1.quarantined_records == run2.quarantined_records, (
                "Quarantined count mismatch"
            )

            print(
                "  [SUCCESS] Idempotency Verified! Two clean runs produced 100% identical snapshot and data hashes."
            )

        print("\n" + "=" * 80)
        print("  Canonical Data Pipeline Successfully Reproduced!")
        print("=" * 80 + "\n")
        return 0

    except Exception as exc:
        print(f"\n[FATAL ERROR] Reproduction failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
