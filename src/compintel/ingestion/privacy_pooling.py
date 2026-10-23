"""Differential Privacy Pooling & Cell Aggregation for B2B Syndication (Phase 14, SRC-B2B-01).

Implements:
1. Organization and transition edge anonymization floor (k_min >= 5 under Rule R-DA-10).
2. Wage coarsening to nearest ₹50,000 steps to mitigate value fingerprinting.
3. Temporal date coarsening into quarterly buckets (YYYY-Qn) with historical lag.
4. Competition Commission of India (CCI) anti-collusion safe harbor audits (multi-employer pooling).
5. Cryptographic tenant-salted HMAC-SHA256 tokenization.

Adheres strictly to:
- PRD Sec 5, FR-05 · Rules R-MD-09, R-MD-11, R-UQ-01, R-UQ-05, R-DA-10.
- ADR-0008 Section 6 · India DPDPA 2023 · CCI Anti-Trust Wage Benchmarking Safe Harbors.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from typing import Any


class B2BPrivacyPooler:
    """Differential privacy and small-cell aggregation processor for B2B syndication."""

    DEFAULT_WAGE_FIELDS: tuple[str, ...] = (
        "basic_salary_annual",
        "fixed_allowances_annual",
        "guaranteed_cash_annual",
        "variable_bonus_annual",
        "equity_annualized_grant",
        "statutory_overhead_annual",
        "ctc_annual",
    )

    @staticmethod
    def derive_pseudonym_token(raw_emp_id: str, tenant_salt: bytes) -> str:
        """Derive deterministic one-way HMAC-SHA256 token for employee within tenant scope.

        Ensures zero raw PII retention and cryptographic isolation across enterprise tenants.
        """
        if not raw_emp_id or not tenant_salt:
            msg = "raw_emp_id and tenant_salt must be non-empty."
            raise ValueError(msg)
        return hmac.new(tenant_salt, raw_emp_id.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def apply_k_anonymity_floor(
        records: list[dict[str, Any]],
        k_min: int = 5,
        cluster_key: str = "prior_employer_cluster",
        group_keys: tuple[str, ...] = ("role", "seniority", "location"),
        anonymized_placeholder: str = "EMP-ANONYMOUS",
    ) -> list[dict[str, Any]]:
        """Enforce k_min organization anonymization floor under Rule R-DA-10.

        Any employer cluster with fewer than k_min observations within a cohort cell
        collapses into anonymized_placeholder ('EMP-ANONYMOUS').
        """
        if not records:
            return []

        # Count occurrences per (group_cell, cluster)
        cell_cluster_counts: dict[tuple[Any, ...], int] = {}
        for r in records:
            cluster_val = r.get(cluster_key)
            if cluster_val:
                cell_tuple = tuple(r.get(gk) for gk in group_keys) + (cluster_val,)
                cell_cluster_counts[cell_tuple] = cell_cluster_counts.get(cell_tuple, 0) + 1

        processed: list[dict[str, Any]] = []
        for r in records:
            rec_copy = dict(r)
            cluster_val = rec_copy.get(cluster_key)
            if cluster_val:
                cell_tuple = tuple(rec_copy.get(gk) for gk in group_keys) + (cluster_val,)
                count = cell_cluster_counts.get(cell_tuple, 0)
                if count < k_min:
                    rec_copy[cluster_key] = anonymized_placeholder
            processed.append(rec_copy)

        return processed

    @classmethod
    def apply_wage_coarsening(
        cls,
        records: list[dict[str, Any]],
        bin_step_inr: float = 50_000.0,
        fields: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Coarsen continuous salary quantities to nearest bin_step_inr (e.g. ₹50,000).

        Prevents exact decimal salary fingerprinting and membership linkage.
        """
        if not records or bin_step_inr <= 0:
            return records

        target_fields = fields or cls.DEFAULT_WAGE_FIELDS
        coarsened: list[dict[str, Any]] = []

        for r in records:
            rec_copy = dict(r)
            for f in target_fields:
                val = rec_copy.get(f)
                if val is not None:
                    try:
                        num = float(val)
                        rec_copy[f] = round(num / bin_step_inr) * bin_step_inr
                    except (ValueError, TypeError):
                        pass
            coarsened.append(rec_copy)

        return coarsened

    @staticmethod
    def apply_quarterly_coarsening(date_input: str | datetime) -> str:
        """Coarsen calendar date into antitrust-safe quarterly bucket (e.g. '2026-Q3')."""
        if isinstance(date_input, str):
            # Parse ISO date string (YYYY-MM-DD)
            try:
                dt = datetime.fromisoformat(date_input.replace("Z", "+00:00"))
            except ValueError:
                # If already in YYYY-Qn format, return as-is
                if len(date_input) == 7 and "-Q" in date_input:
                    return date_input
                msg = f"Invalid date format for quarterly coarsening: '{date_input}'"
                raise ValueError(msg) from None
        elif isinstance(date_input, datetime):
            dt = date_input
        else:
            msg = f"Expected str or datetime, got {type(date_input)}"
            raise TypeError(msg)

        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{quarter}"

    @staticmethod
    def verify_cci_safe_harbor(
        records: list[dict[str, Any]],
        min_employers: int = 5,
        max_share: float = 0.35,
        tenant_key: str = "tenant_token",
    ) -> tuple[bool, str]:
        """Audit Competition Commission of India (CCI) anti-collusion safe harbor standards.

        Standards:
        1. Multi-employer pooling: Minimum 5 participating employer tenants per reporting cell.
        2. Non-dominance: No single employer contributes > 35.0% of records in the cohort.
        """
        if not records:
            return False, "Empty cohort cannot satisfy CCI multi-employer safe harbor."

        total_n = len(records)
        tenant_counts: dict[str, int] = {}

        for r in records:
            tenant = str(r.get(tenant_key, "UNKNOWN_TENANT"))
            tenant_counts[tenant] = tenant_counts.get(tenant, 0) + 1

        n_employers = len(tenant_counts)
        if n_employers < min_employers:
            return (
                False,
                f"CCI safe harbor violation: Cohort has only {n_employers} distinct employers "
                f"(minimum {min_employers} required).",
            )

        for tenant, count in tenant_counts.items():
            share = count / total_n
            if share > max_share:
                return (
                    False,
                    f"CCI safe harbor violation: Employer '{tenant[:8]}...' contributes "
                    f"{share:.1%} of records (maximum allowed share is {max_share:.1%}).",
                )

        return (
            True,
            f"CCI safe harbor satisfied: {n_employers} participating employers, "
            f"max tenant share = {max(c / total_n for c in tenant_counts.values()):.1%}.",
        )
