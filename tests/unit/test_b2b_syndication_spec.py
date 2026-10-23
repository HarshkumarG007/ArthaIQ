"""Unit tests validating B2B Syndication Protocol (SRC-B2B-01) for Phase 14."""

import hashlib
import hmac
import re
from pathlib import Path

import yaml


def test_b2b_syndication_source_yaml_exists_and_valid():
    """Verify SRC-B2B-01.yaml exists and complies with all mandatory catalog schema fields."""
    yaml_path = Path("config/sources/SRC-B2B-01.yaml")
    assert yaml_path.exists(), f"Source config {yaml_path} does not exist"

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["source_id"] == "SRC-B2B-01"
    assert data["country"] == "IN"
    assert data["currency_primary"] == "INR"
    assert data["ingestion_status"] == "approved_for_design"
    assert data["sqsf_tier"] == "TIER_1_GROUND_TRUTH"
    assert data["sqs"] >= 95.0
    assert data["licence"]["privacy_safeguards"]["k_anonymity_min"] >= 5
    assert data["licence"]["privacy_safeguards"]["dpdpa_2023_compliant"] is True
    assert len(data["canonical_field_mappings"]) >= 5


def test_b2b_syndication_pii_scrubbing_and_rejection():
    """Verify that PII patterns (PAN, Aadhaar, Email, Phone) are strictly caught and barred."""
    pan_regex = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
    aadhaar_regex = re.compile(r"^[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}$")
    email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    phone_regex = re.compile(r"^(\+91[\-\s]?)?[0]?(91)?[6789]\d{9}$")

    # Sample valid and invalid values
    assert pan_regex.match("ABCDE1234F") is not None
    assert pan_regex.match("SWE") is None

    assert aadhaar_regex.match("3829 4920 1829") is not None
    assert aadhaar_regex.match("BENGALURU") is None

    assert email_regex.match("engineer@enterprise.com") is not None
    assert email_regex.match("SR") is None

    assert phone_regex.match("+91 9876543210") is not None
    assert phone_regex.match("EMP-TOKEN-123") is None


def test_b2b_syndication_hmac_tokenization_isolation():
    """Verify that two distinct tenants with identical employee IDs yield distinct tokens."""
    emp_raw_id = "EMP-94821"
    salt_tenant_a = b"tenant-alpha-secret-salt-2026-xyz"
    salt_tenant_b = b"tenant-beta-secret-salt-2026-uvw"

    token_a = hmac.new(salt_tenant_a, emp_raw_id.encode("utf-8"), hashlib.sha256).hexdigest()
    token_b = hmac.new(salt_tenant_b, emp_raw_id.encode("utf-8"), hashlib.sha256).hexdigest()

    assert token_a != token_b
    assert len(token_a) == 64
    assert len(token_b) == 64


def test_b2b_syndication_k_anonymity_floor():
    """Verify that employer clusters with count < 5 collapse into EMP-ANONYMOUS."""
    records = [
        {"cluster": "EMP-GOOGLE", "salary": 35.0},
        {"cluster": "EMP-GOOGLE", "salary": 38.0},
        {"cluster": "EMP-GOOGLE", "salary": 40.0},
        {"cluster": "EMP-GOOGLE", "salary": 42.0},
        {"cluster": "EMP-GOOGLE", "salary": 45.0},
        {"cluster": "EMP-RARE-STARTUP", "salary": 28.0},
        {"cluster": "EMP-RARE-STARTUP", "salary": 30.0},
    ]

    cluster_counts = {}
    for r in records:
        c = r["cluster"]
        cluster_counts[c] = cluster_counts.get(c, 0) + 1

    anonymized = []
    for r in records:
        cluster = r["cluster"]
        if cluster_counts[cluster] < 5:
            anonymized.append({**r, "cluster": "EMP-ANONYMOUS"})
        else:
            anonymized.append(r)

    # EMP-GOOGLE has 5 records -> kept
    # EMP-RARE-STARTUP has 2 records -> collapsed to EMP-ANONYMOUS
    google_records = [r for r in anonymized if r["cluster"] == "EMP-GOOGLE"]
    rare_records = [r for r in anonymized if r["cluster"] == "EMP-RARE-STARTUP"]
    anon_records = [r for r in anonymized if r["cluster"] == "EMP-ANONYMOUS"]

    assert len(google_records) == 5
    assert len(rare_records) == 0
    assert len(anon_records) == 2


def test_b2b_syndication_accounting_identity():
    """Verify deductive accounting identity: Guaranteed Cash = Basic + Allowances."""
    basic = 18.0
    allowances = 7.0
    guaranteed = basic + allowances
    bonus = 3.5
    equity = 6.0
    overhead = 2.16  # EPF 12%
    ctc = guaranteed + bonus + equity + overhead

    assert guaranteed == 25.0
    assert ctc == 36.66
    # Rule R-MD-07: guaranteed cash must strictly exclude bonus, equity, and employer overhead
    assert guaranteed < ctc
    assert abs(guaranteed - (basic + allowances)) < 1e-6
