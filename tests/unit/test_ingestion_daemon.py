"""Unit tests for Dual-Cadence Ingestion & Freshness Daemon (Phase 11, T11.02, CHARTER-EXP-16).

Validates:
1. IngestionDaemonConfig validation, bounds, and defaults.
2. AutomatedCanary verification:
   - Valid schema passes with zero anomaly tags.
   - PII patterns (email, phone, PAN, Aadhaar, forbidden keywords) trigger quarantine.
   - Missing required fields, out-of-bounds YoE, and non-positive pay trigger quarantine.
   - Statutory unbundling violations (unbundled CTC > cash with no basic) trigger quarantine.
3. Fast-path queue processing:
   - Correctly updates status to 'quarantined'.
   - Accurately computes intake-to-quarantine latency.
   - Strips forbidden PII keys from stored payload.
4. Slow-path statutory auditing:
   - Audits monitored sources against config/freshness_slas.yaml.
   - Successfully verifies manifests.
5. Continuous 30-day simulation & keep criteria verification:
   - Zero 30-day staleness violations.
   - p95 latency <= 15 minutes.
   - 100/100 injected anomalies quarantined (0.00% false accept rate).
   - Peak memory well below 500 MB.
   - Verdict evaluates to PROMOTE.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from compintel.ingestion.daemon import (
    AutomatedCanary,
    DualCadenceIngestionDaemon,
    IngestionDaemonConfig,
)


def test_daemon_config_defaults_and_validation() -> None:
    """Verify default parameters and bounds for IngestionDaemonConfig."""
    cfg = IngestionDaemonConfig()
    assert cfg.fast_path_poll_interval_s == 5.0
    assert cfg.slow_path_poll_interval_s == 3600.0
    assert cfg.quarantine_latency_target_m == 15.0
    assert cfg.max_memory_rss_mb == 500.0
    assert cfg.auto_quarantine_anomalies is True
    assert cfg.zero_pii_strict is True


def test_canary_valid_payload_passes() -> None:
    """Verify that a compliant observation passes canary audit with zero reasons."""
    valid_payload = {
        "role_family": "SOFTWARE",
        "seniority": "MID",
        "location": "BLR",
        "years_experience": 4.5,
        "guaranteed_cash_annual": 28.5,
        "base_salary_annual": 18.0,
    }
    result = AutomatedCanary.audit_record(valid_payload)
    assert result.passed is True
    assert len(result.reasons) == 0
    assert result.has_pii is False
    assert result.has_schema_error is False
    assert result.has_unbundling_error is False


@pytest.mark.parametrize(
    ("pii_key", "pii_value", "expected_tag"),
    [
        ("email", "engineer@techcorp.in", "PII_KEYWORD_DETECTED"),
        ("notes", "Email me at dev@domain.com for offer copy", "PII_EMAIL_DETECTED"),
        ("phone", "+91 9876543210", "PII_KEYWORD_DETECTED"),
        ("notes", "Call +91 9876543210 anytime", "PII_PHONE_DETECTED"),
        ("pan", "ABCDE1234F", "PII_KEYWORD_DETECTED"),
        ("notes", "PAN verified: ABCDE1234F", "PII_PAN_DETECTED"),
        ("aadhaar", "1234 5678 9012", "PII_KEYWORD_DETECTED"),
        ("full_name", "Arjun Sharma", "PII_KEYWORD_DETECTED"),
    ],
)
def test_canary_pii_detection(pii_key: str, pii_value: str, expected_tag: str) -> None:
    """Verify canary detects and flags various PII patterns (Rule R-CD-06)."""
    payload = {
        "role_family": "SOFTWARE",
        "seniority": "MID",
        "location": "BLR",
        "years_experience": 3.0,
        "guaranteed_cash_annual": 22.0,
        pii_key: pii_value,
    }
    result = AutomatedCanary.audit_record(payload)
    assert result.passed is False
    assert result.has_pii is True
    assert any(expected_tag in r for r in result.reasons)


def test_canary_schema_errors() -> None:
    """Verify canary flags missing required fields and out-of-bounds YoE (Rule R-DA-03)."""
    # Missing seniority
    missing_sen = {
        "role_family": "DATA",
        "location": "HYD",
        "years_experience": 2.0,
        "guaranteed_cash_annual": 15.0,
    }
    res1 = AutomatedCanary.audit_record(missing_sen)
    assert res1.passed is False
    assert res1.has_schema_error is True
    assert any("MISSING_REQUIRED_FIELDS" in r for r in res1.reasons)

    # Negative experience
    invalid_exp = {
        "role_family": "DATA",
        "seniority": "JUNIOR",
        "location": "HYD",
        "years_experience": -2.0,
        "guaranteed_cash_annual": 15.0,
    }
    res2 = AutomatedCanary.audit_record(invalid_exp)
    assert res2.passed is False
    assert res2.has_schema_error is True
    assert any("OUT_OF_BOUNDS_EXPERIENCE" in r for r in res2.reasons)


def test_canary_statutory_unbundling_errors() -> None:
    """Verify canary flags non-positive cash and CTC headline leakage (Rule R-MD-07)."""
    # Zero or negative cash
    neg_cash = {
        "role_family": "MLAI",
        "seniority": "SENIOR",
        "location": "BLR",
        "years_experience": 8.0,
        "guaranteed_cash_annual": 0.0,
    }
    res1 = AutomatedCanary.audit_record(neg_cash)
    assert res1.passed is False
    assert res1.has_unbundling_error is True
    assert any("NON_POSITIVE_GUARANTEED_CASH" in r for r in res1.reasons)

    # CTC headline leak without basic breakdown
    ctc_leak = {
        "role_family": "MLAI",
        "seniority": "SENIOR",
        "location": "BLR",
        "years_experience": 8.0,
        "guaranteed_cash_annual": 45.0,
        "ctc_annual": 75.0,
        "is_unbundled_aggregate": True,
    }
    res2 = AutomatedCanary.audit_record(ctc_leak)
    assert res2.passed is False
    assert res2.has_unbundling_error is True
    assert any("UNBUNDLED_CTC_LEAKAGE_DETECTED" in r for r in res2.reasons)


def test_fast_path_processing_and_latency() -> None:
    """Verify fast-path queue assigns quarantine status, strips PII, and tracks latency."""
    daemon = DualCadenceIngestionDaemon()
    sub_time = datetime.now(UTC) - timedelta(minutes=5)

    raw_submission = {
        "role_family": "SOFTWARE",
        "seniority": "SENIOR",
        "location": "NCR",
        "years_experience": 9.0,
        "guaranteed_cash_annual": 55.0,
        "full_name": "Sensitive Contributor",
        "email": "test@domain.com",
    }

    processed = daemon.process_submission_payload(raw_submission, submission_time=sub_time)
    assert processed["status"] == "quarantined"
    assert processed["latency_seconds"] >= 290.0  # Approx 5 minutes
    # PII keys must be completely removed from clean output payload
    assert "full_name" not in processed
    assert "email" not in processed
    assert processed["canary_passed"] is False
    assert len(processed["quarantine_reasons"]) > 0


def test_slow_path_statutory_audit() -> None:
    """Verify slow-path publication audit reads freshness SLAs and audits manifests."""
    daemon = DualCadenceIngestionDaemon()
    result = daemon.run_slow_path_cycle(sources_to_audit=["SRC-SUP-MAC-01", "SRC-IND-OFF-01"])
    assert result["sources_audited"] == 2
    assert "SRC-SUP-MAC-01" in result["details"]
    assert "SRC-IND-OFF-01" in result["details"]


def test_continuous_30_day_simulation_and_keep_criteria() -> None:
    """Verify full 30-day continuous simulation achieves PROMOTE verdict on all 4 keep criteria."""
    daemon = DualCadenceIngestionDaemon()
    report = daemon.run_continuous_30_day_simulation(
        n_submissions_per_day=30,
        n_anomalous_injected=100,
        random_seed=42,
    )

    assert report["charter_id"] == "CHARTER-EXP-16"
    assert report["verdict"] == "PROMOTE"

    criteria = report["keep_criteria"]
    # Criterion 1: Zero 30-day staleness violations
    assert criteria["criterion_1_staleness_violations"]["passed"] is True
    assert "0 violations" in criteria["criterion_1_staleness_violations"]["value"]

    # Criterion 2: Latency <= 15 min
    assert criteria["criterion_2_ingestion_latency"]["passed"] is True
    assert criteria["criterion_2_ingestion_latency"]["p95_minutes"] <= 15.0

    # Criterion 3: 100/100 quarantined (0.00% false accepts)
    assert criteria["criterion_3_canary_quarantine_rate"]["passed"] is True
    assert criteria["criterion_3_canary_quarantine_rate"]["false_accept_rate_percent"] == 0.00
    assert criteria["criterion_3_canary_quarantine_rate"]["quarantined_count"] == "100/100"

    # Criterion 4: Zero PII and memory <= 500 MB
    assert criteria["criterion_4_zero_pii_and_memory"]["passed"] is True
    assert criteria["criterion_4_zero_pii_and_memory"]["peak_memory_mb"] <= 500.0
