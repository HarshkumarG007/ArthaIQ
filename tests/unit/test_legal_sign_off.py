"""Unit tests verifying legal, privacy, terms, disclaimers, and consent documents.

Adheres to:
- PRD Section 12 (Out of scope & rejected uses) & Section 13 (Legal/ethics)
- PRD FR-18 & design.md Section 8 (Statutory DisclaimerLine)
- ADR-0008 (Privacy, consent, retention and k_min)
- Rules R-DA-07, R-DA-10, R-MD-13, R-UI-05
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_LEGAL_DIR = REPO_ROOT / "docs" / "legal"
WEB_COMPONENTS_DIR = REPO_ROOT / "apps" / "web" / "src" / "components"


def test_legal_documentation_files_exist() -> None:
    """Verify that all four required legal and privacy documents exist and are populated."""
    expected_files = [
        "terms-of-service.md",
        "privacy-notice.md",
        "disclaimers-and-notices.md",
        "legal-privacy-sign-off.md",
    ]
    for filename in expected_files:
        filepath = DOCS_LEGAL_DIR / filename
        assert filepath.exists(), f"Missing legal document: {filepath}"
        content = filepath.read_text(encoding="utf-8")
        assert len(content.strip()) > 500, f"Document {filename} is unexpectedly short"


def test_terms_of_service_critical_clauses() -> None:
    """Verify Terms of Service contains statutory decision-support and anti-screening clauses."""
    tos_path = DOCS_LEGAL_DIR / "terms-of-service.md"
    content = tos_path.read_text(encoding="utf-8")

    # Decision support & non-reliance
    assert "Decision Support Only" in content
    assert "Not an Offer or Guarantee" in content
    assert "Not Professional Advice" in content

    # Prohibition on candidate ranking or screening (PRD Section 12)
    assert "Candidate Screening or Ranking" in content
    assert "screen, rank, blacklist, filter, or evaluate job applicants" in content

    # Prohibition on document uploads (ADR-0008)
    assert "upload physical or digital documents" in content
    assert "payslips, Form 16s" in content

    # Jurisdiction
    assert "Republic of India" in content
    assert "Bengaluru, Karnataka" in content


def test_privacy_notice_statutory_protections() -> None:
    """Verify Privacy Notice complies with DPDPA 2023, identity separation, and k_min."""
    privacy_path = DOCS_LEGAL_DIR / "privacy-notice.md"
    content = privacy_path.read_text(encoding="utf-8")

    # Statute citation
    assert "Digital Personal Data Protection Act, 2023" in content
    assert "DPDPA 2023" in content

    # Identity separation (ADR-0008)
    assert "identity.contributor_identities" in content
    assert "app.contributions" in content
    assert "contributor_key" in content

    # k_min anonymization floor
    assert "k_{\\min} \\ge 5" in content or "k_min" in content
    assert "5 distinct natural persons" in content

    # Retention and erasure cascade
    assert "24 months" in content
    assert "Operational Erasure Cascade" in content
    assert "/v1/me/data" in content

    # Compare-only isolation
    assert "COMPARE_ONLY" in content or "Compare-Only" in content
    assert "feat_l3_current_guaranteed_cash" in content


def test_disclaimer_line_ui_exact_match() -> None:
    """Verify that DisclaimerLine.tsx matches the copy in disclaimers-and-notices.md."""
    register_path = DOCS_LEGAL_DIR / "disclaimers-and-notices.md"
    disclaimer_ts_path = WEB_COMPONENTS_DIR / "DisclaimerLine.tsx"

    register_content = register_path.read_text(encoding="utf-8")
    component_content = disclaimer_ts_path.read_text(encoding="utf-8")

    expected_copy = (
        "This range is an estimate from data of varying quality. "
        "It is not an offer, appraisal or guarantee."
    )

    assert expected_copy in register_content, "Disclaimer missing from legal register"

    # Normalize whitespace in JSX component to account for multi-line formatting
    normalized_component = " ".join(component_content.split())
    assert expected_copy in normalized_component, "Disclaimer in DisclaimerLine.tsx has drifted"


def test_contribution_consent_ui_match() -> None:
    """Verify ContributionFlow.tsx consent labels match disclaimers-and-notices.md."""
    register_path = DOCS_LEGAL_DIR / "disclaimers-and-notices.md"
    contribution_ts_path = WEB_COMPONENTS_DIR / "ContributionFlow.tsx"

    register_content = register_path.read_text(encoding="utf-8")
    flow_content = contribution_ts_path.read_text(encoding="utf-8")

    # Benchmarking label
    bench_label = "Use my pay data for salary range estimates"
    assert bench_label in register_content
    assert bench_label in flow_content

    # Research label
    research_label = "Use my data for anonymised research and trend reports (optional)"
    assert research_label in register_content
    assert research_label in flow_content

    # Contact label
    contact_label = "Contact me if my contribution is queried for quality review (optional)"
    assert contact_label in register_content
    assert contact_label in flow_content

    # DPDPA statutory notice
    dpdpa_notice = "Under DPDPA 2023, you have the right to withdraw consent"
    assert dpdpa_notice in register_content
    assert dpdpa_notice in flow_content


def test_compare_only_copy_match() -> None:
    """Verify PayCompare.tsx contains compare-only explanatory caveats."""
    pay_compare_ts = WEB_COMPONENTS_DIR / "PayCompare.tsx"
    component_content = pay_compare_ts.read_text(encoding="utf-8")

    caveat_text = (
        "Your pay may reflect things this estimate does not include, "
        "such as scope, employer or timing."
    )
    assert caveat_text in component_content, "Contextual caveat missing from PayCompare.tsx"

    storage_text = "never stored or used to train models"
    assert storage_text in component_content, "Storage disclosure missing from PayCompare.tsx"


def test_sign_off_record_ratification() -> None:
    """Verify Legal and Privacy Sign-Off Record contains all 10 audit points and GO."""
    signoff_path = DOCS_LEGAL_DIR / "legal-privacy-sign-off.md"
    content = signoff_path.read_text(encoding="utf-8")

    assert "APPROVED & RATIFIED" in content
    assert "10-Point Legal and Privacy Compliance Audit Matrix" in content

    # Check that all 10 items passed
    for i in range(1, 11):
        assert f"| **{i}** |" in content, f"Missing audit item #{i}"

    assert content.count("**PASS**") >= 10
    assert content.count("RATIFIED (GO)") >= 3
