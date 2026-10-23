"""Unit tests for Phase 14 B2B Syndication Connector and Differential Privacy Engine.

Verifies:
1. B2BSyndicationConnector extraction, PII rejection, and accounting identity validation.
2. B2BPrivacyPooler k-anonymity, wage coarsening, quarterly coarsening, and CCI safe harbor checks.
3. Strict compliance with Rule R-DA-10, Rule R-UQ-01, Rule R-UQ-05, and DPDPA 2023.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from compintel.ingestion import B2BPrivacyPooler, B2BSyndicationConnector, get_connector
from compintel.ingestion.manifest import generate_source_manifest


@pytest.fixture
def mock_b2b_dir(tmp_path: Path) -> Path:
    """Create a temporary B2B source directory with manifest and mock data."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    b2b_dir = tmp_path / "SRC-B2B-01"
    b2b_dir.mkdir(parents=True)

    records = [
        {
            "pseudonym_token": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
            "reference_quarter": "2026-Q2",
            "role_title": "Senior Backend Engineer",
            "job_family": "SOFTWARE_ENGINEERING",
            "seniority_level": "SENIOR",
            "years_of_experience_total": 7.5,
            "years_at_employer": 2.0,
            "metro_tier": "TIER_1_METRO",
            "location_city": "Bengaluru",
            "work_mode": "HYBRID",
            "employer_tier": "TIER_1_PRODUCT",
            "employer_scale": "ENTERPRISE",
            "industry_sector": "FINTECH",
            "prior_employer_cluster": "EMP-CLUST-042",
            "basic_salary_annual": 1800000.0,
            "fixed_allowances_annual": 600000.0,
            "guaranteed_cash_annual": 2400000.0,
            "variable_bonus_target_annual": 400000.0,
            "variable_bonus_actual_annual": 380000.0,
            "equity_grant_annualized": 800000.0,
            "retention_bonus_annualized": 0.0,
            "signing_bonus_annualized": 0.0,
            "statutory_benefits_annual": 216000.0,
            "total_cost_to_company_annual": 3816000.0,
            "is_individual_contributor": True,
            "highest_education": "BACHELORS",
            "college_tier": "TIER_1",
            "is_pay_transparent_disclosure": True,
        },
        {
            "pseudonym_token": "b2c3d4e5f60718293a4b5c6d7e8f90a1",
            "reference_quarter": "2026-Q2",
            "role_title": "Lead Data Scientist",
            "job_family": "DATA_SCIENCE",
            "seniority_level": "STAFF",
            "years_of_experience_total": 10.0,
            "years_at_employer": 3.5,
            "metro_tier": "TIER_1_METRO",
            "location_city": "Hyderabad",
            "work_mode": "REMOTE",
            "employer_tier": "TIER_1_PRODUCT",
            "employer_scale": "ENTERPRISE",
            "industry_sector": "ECOMMERCE",
            "prior_employer_cluster": "EMP-CLUST-042",
            "basic_salary_annual": 2500000.0,
            "fixed_allowances_annual": 700000.0,
            "guaranteed_cash_annual": 3200000.0,
            "variable_bonus_target_annual": 600000.0,
            "variable_bonus_actual_annual": 650000.0,
            "equity_grant_annualized": 1200000.0,
            "retention_bonus_annualized": 0.0,
            "signing_bonus_annualized": 0.0,
            "statutory_benefits_annual": 300000.0,
            "total_cost_to_company_annual": 5300000.0,
            "is_individual_contributor": False,
            "highest_education": "MASTERS",
            "college_tier": "TIER_1",
            "is_pay_transparent_disclosure": True,
        },
    ]

    parquet_path = b2b_dir / "b2b_syndication_tranches.parquet"
    df = pl.DataFrame(records)
    df.write_parquet(parquet_path)

    generate_source_manifest(
        source_id="SRC-B2B-01",
        raw_dir=tmp_path,
        repo_root=repo_root,
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Connector Tests
# ---------------------------------------------------------------------------


def test_b2b_connector_extracts_parquet(mock_b2b_dir: Path) -> None:
    """Verify B2BSyndicationConnector parses parquet files into RawRecords."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    connector = get_connector("SRC-B2B-01", raw_dir=mock_b2b_dir, repo_root=repo_root)
    assert isinstance(connector, B2BSyndicationConnector)

    records = list(connector.extract_raw_records())
    assert len(records) == 2
    for r in records:
        assert r.source_id == "SRC-B2B-01"
        assert r.license_id == "PROPRIETARY-B2B-CONSORTIUM-GRANT"
        assert "role_title" in r.raw_payload
        assert "guaranteed_cash_annual" in r.raw_payload
        assert r.record_hash is not None


def test_b2b_connector_extracts_csv(tmp_path: Path) -> None:
    """Verify B2BSyndicationConnector falls back to CSV when parquet is absent."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    b2b_dir = tmp_path / "SRC-B2B-01"
    b2b_dir.mkdir(parents=True)

    csv_path = b2b_dir / "b2b_syndication_tranches.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "pseudonym_token",
                "role_title",
                "basic_salary_annual",
                "fixed_allowances_annual",
                "guaranteed_cash_annual",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "pseudonym_token": "tok123",
                "role_title": "Backend Engineer",
                "basic_salary_annual": "1000000",
                "fixed_allowances_annual": "500000",
                "guaranteed_cash_annual": "1500000",
            }
        )

    generate_source_manifest(
        source_id="SRC-B2B-01",
        raw_dir=tmp_path,
        repo_root=repo_root,
    )

    connector = B2BSyndicationConnector(raw_dir=tmp_path, repo_root=repo_root)
    records = list(connector.extract_raw_records())
    assert len(records) == 1
    assert records[0].raw_payload["role_title"] == "Backend Engineer"


def test_b2b_connector_rejects_pii(tmp_path: Path) -> None:
    """Verify B2BSyndicationConnector strictly rejects payloads containing forbidden PII."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    b2b_dir = tmp_path / "SRC-B2B-01"
    b2b_dir.mkdir(parents=True)

    records = [
        {
            "pseudonym_token": "tok123",
            "role_title": "Backend Engineer",
            "email": "employee@example.com",  # Forbidden PII
            "guaranteed_cash_annual": 1500000.0,
        }
    ]
    df = pl.DataFrame(records)
    df.write_parquet(b2b_dir / "b2b_syndication_tranches.parquet")

    generate_source_manifest(
        source_id="SRC-B2B-01",
        raw_dir=tmp_path,
        repo_root=repo_root,
    )

    connector = B2BSyndicationConnector(raw_dir=tmp_path, repo_root=repo_root)
    with pytest.raises(ValueError, match="Forbidden PII keys detected"):
        list(connector.extract_raw_records())


def test_b2b_connector_validates_accounting_identity(tmp_path: Path) -> None:
    """Verify B2BSyndicationConnector enforces guaranteed_cash == basic + fixed_allowances."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    b2b_dir = tmp_path / "SRC-B2B-01"
    b2b_dir.mkdir(parents=True)

    records = [
        {
            "pseudonym_token": "tok123",
            "role_title": "Backend Engineer",
            "basic_salary_annual": 1000000.0,
            "fixed_allowances_annual": 500000.0,
            "guaranteed_cash_annual": 1800000.0,  # Accounting mismatch (expected 1500000.0)
        }
    ]
    df = pl.DataFrame(records)
    df.write_parquet(b2b_dir / "b2b_syndication_tranches.parquet")

    generate_source_manifest(
        source_id="SRC-B2B-01",
        raw_dir=tmp_path,
        repo_root=repo_root,
    )

    connector = B2BSyndicationConnector(raw_dir=tmp_path, repo_root=repo_root)
    with pytest.raises(ValueError, match="Accounting mismatch in B2B record"):
        list(connector.extract_raw_records())


# ---------------------------------------------------------------------------
# Privacy Pooler Tests
# ---------------------------------------------------------------------------


def test_derive_pseudonym_token() -> None:
    """Verify deterministic and salted HMAC-SHA256 pseudonym generation."""
    emp_id = "EMP-00123"
    salt_1 = b"salt-alpha-2026"
    salt_2 = b"salt-beta-2026"

    token_1 = B2BPrivacyPooler.derive_pseudonym_token(emp_id, salt_1)
    token_1_repeat = B2BPrivacyPooler.derive_pseudonym_token(emp_id, salt_1)
    token_2 = B2BPrivacyPooler.derive_pseudonym_token(emp_id, salt_2)

    assert token_1 == token_1_repeat
    assert token_1 != token_2
    assert len(token_1) == 64

    with pytest.raises(ValueError, match="must be non-empty"):
        B2BPrivacyPooler.derive_pseudonym_token("", salt_1)


def test_apply_k_anonymity_floor() -> None:
    """Verify Rule R-DA-10 k_min >= 5 aggregation floor collapses small clusters."""
    records = [
        {"role": "SWE", "seniority": "MID", "location": "BLR", "prior_employer_cluster": "COMP-A"},
        {"role": "SWE", "seniority": "MID", "location": "BLR", "prior_employer_cluster": "COMP-A"},
        {"role": "SWE", "seniority": "MID", "location": "BLR", "prior_employer_cluster": "COMP-A"},
        {"role": "SWE", "seniority": "MID", "location": "BLR", "prior_employer_cluster": "COMP-A"},
        {"role": "SWE", "seniority": "MID", "location": "BLR", "prior_employer_cluster": "COMP-A"},
        {"role": "SWE", "seniority": "MID", "location": "BLR", "prior_employer_cluster": "COMP-B"},
        {"role": "SWE", "seniority": "MID", "location": "BLR", "prior_employer_cluster": "COMP-B"},
    ]

    pooled = B2BPrivacyPooler.apply_k_anonymity_floor(records, k_min=5)
    comp_a_count = sum(1 for r in pooled if r["prior_employer_cluster"] == "COMP-A")
    comp_b_count = sum(1 for r in pooled if r["prior_employer_cluster"] == "COMP-B")
    anon_count = sum(1 for r in pooled if r["prior_employer_cluster"] == "EMP-ANONYMOUS")

    assert comp_a_count == 5
    assert comp_b_count == 0
    assert anon_count == 2


def test_apply_wage_coarsening() -> None:
    """Verify continuous wage amounts are coarsened to nearest ₹50,000 steps."""
    records = [
        {
            "basic_salary_annual": 1220000.0,
            "guaranteed_cash_annual": 1260000.0,
            "ctc_annual": 1845000.0,
        },
        {"basic_salary_annual": "invalid", "guaranteed_cash_annual": None},
    ]

    coarsened = B2BPrivacyPooler.apply_wage_coarsening(records, bin_step_inr=50000.0)
    assert coarsened[0]["basic_salary_annual"] == 1200000.0
    assert coarsened[0]["guaranteed_cash_annual"] == 1250000.0
    assert coarsened[0]["ctc_annual"] == 1850000.0
    assert coarsened[1]["basic_salary_annual"] == "invalid"
    assert coarsened[1]["guaranteed_cash_annual"] is None


def test_apply_quarterly_coarsening() -> None:
    """Verify calendar dates are mapped to quarterly antitrust-safe buckets."""
    assert B2BPrivacyPooler.apply_quarterly_coarsening("2026-01-15") == "2026-Q1"
    assert B2BPrivacyPooler.apply_quarterly_coarsening("2026-05-30") == "2026-Q2"
    assert B2BPrivacyPooler.apply_quarterly_coarsening("2026-08-01T12:00:00Z") == "2026-Q3"
    assert B2BPrivacyPooler.apply_quarterly_coarsening(datetime(2026, 11, 25)) == "2026-Q4"
    assert B2BPrivacyPooler.apply_quarterly_coarsening("2026-Q3") == "2026-Q3"

    with pytest.raises(ValueError, match="Invalid date format"):
        B2BPrivacyPooler.apply_quarterly_coarsening("not-a-date")

    with pytest.raises(TypeError, match="Expected str or datetime"):
        B2BPrivacyPooler.apply_quarterly_coarsening(12345)  # type: ignore[arg-type]


def test_verify_cci_safe_harbor() -> None:
    """Verify CCI safe harbor checks minimum 5 employers and maximum 35% concentration."""
    # Compliant cohort: 5 employers with equal 20% share (2 records each, 10 total)
    compliant_records = [{"tenant_token": f"tenant_{i % 5}"} for i in range(10)]
    ok, msg = B2BPrivacyPooler.verify_cci_safe_harbor(compliant_records)
    assert ok is True
    assert "CCI safe harbor satisfied" in msg

    # Non-compliant: only 3 employers
    under_threshold = [{"tenant_token": f"tenant_{i % 3}"} for i in range(10)]
    ok, msg = B2BPrivacyPooler.verify_cci_safe_harbor(under_threshold)
    assert ok is False
    assert "has only 3 distinct employers" in msg

    # Non-compliant: 5 employers, but tenant_0 has 50% concentration (> 35%)
    concentrated_records = (
        [{"tenant_token": "tenant_0"}] * 10
        + [{"tenant_token": "tenant_1"}] * 2
        + [{"tenant_token": "tenant_2"}] * 2
        + [{"tenant_token": "tenant_3"}] * 3
        + [{"tenant_token": "tenant_4"}] * 3
    )
    ok, msg = B2BPrivacyPooler.verify_cci_safe_harbor(concentrated_records)
    assert ok is False
    assert "maximum allowed share is 35.0%" in msg
