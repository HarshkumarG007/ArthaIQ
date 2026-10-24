"""Unit tests for Career Architect schema contracts (Task T15.09).

Verifies Pydantic v2 data models, provenance tracking, tri-state verification,
anti-causal string validation, and JSON schema exports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from compintel.career.schema import (
    CompetencyCategory,
    CompetencyGap,
    CompetencyGapReport,
    CompetencyGraphManifest,
    CompetencyNode,
    DifficultyRubric,
    EvidenceLedger,
    EvidenceRecord,
    EvidenceType,
    RoleLevel,
    TaxonomyLicense,
    TaxonomyProvenance,
    TaxonomySource,
    VerificationState,
    validate_anti_causal_text,
)
from compintel.schema.enums import RoleFamily

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def sample_provenance() -> TaxonomyProvenance:
    return TaxonomyProvenance(
        source_id=TaxonomySource.ONET_28_0,
        source_code="15-2051.01",
        license=TaxonomyLicense.CC_BY_4_0,
        attribution_required=True,
        attribution_text="Source: O*NET 28.0 (USDOL/ETA), adapted under CC BY 4.0.",
        modified_flag=True,
        curator="Principal Data Architect",
        curated_date="2026-10-24",
    )


@pytest.fixture
def sample_difficulty() -> DifficultyRubric:
    return DifficultyRubric(
        learning_difficulty=3.5,
        application_difficulty=3.0,
        is_heuristic=True,
    )


@pytest.fixture
def sample_node(
    sample_provenance: TaxonomyProvenance, sample_difficulty: DifficultyRubric
) -> CompetencyNode:
    return CompetencyNode(
        id="data.sql.window_functions",
        title="SQL Window Functions",
        description="Mastery of analytical window frames, PARTITION BY, and ranking functions.",
        category=CompetencyCategory.CORE_ANALYTICS,
        role_family=RoleFamily.DATA,
        target_levels=[RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID],
        prerequisite_ids=["data.sql.aggregations"],
        provenance=sample_provenance,
        difficulty=sample_difficulty,
    )


def test_valid_competency_node(sample_node: CompetencyNode) -> None:
    """Verify that a valid competency node initializes, serializes, and deserializes."""
    assert sample_node.id == "data.sql.window_functions"
    assert sample_node.role_family == RoleFamily.DATA
    assert RoleLevel.LEVEL_2_JUNIOR in sample_node.target_levels
    assert sample_node.difficulty.is_heuristic is True

    serialized = sample_node.model_dump_json()
    reconstituted = CompetencyNode.model_validate_json(serialized)
    assert reconstituted == sample_node


def test_anti_causal_validation_direct() -> None:
    """Verify validate_anti_causal_text catches forbidden causal compensation phrases."""
    with pytest.raises(ValueError, match="Prohibited causal compensation phrase"):
        validate_anti_causal_text("This skill raises compensation by 3 LPA", "description")

    with pytest.raises(ValueError, match="Prohibited causal compensation phrase"):
        validate_anti_causal_text("Learn Spark and boosts salary!", "title")

    with pytest.raises(ValueError, match="Prohibited causal compensation phrase"):
        validate_anti_causal_text("Guaranteed compensation for graduates", "description")

    with pytest.raises(ValueError, match="Prohibited causal compensation phrase"):
        validate_anti_causal_text("Expected +40% CTC bump", "description")

    # Safe descriptive text must pass cleanly
    safe_text = "Proficiency in statistical hypothesis testing and A/B test analysis."
    assert validate_anti_causal_text(safe_text, "description") == safe_text


def test_anti_causal_validation_in_competency_node(
    sample_provenance: TaxonomyProvenance, sample_difficulty: DifficultyRubric
) -> None:
    """Verify CompetencyNode validator rejects causal pay promises in title or description."""
    with pytest.raises(ValidationError, match="Rule R-CR-01 and CPA 2019"):
        CompetencyNode(
            id="data.spark.distributed",
            title="Apache Spark",
            description="Learning Spark raises compensation by 5 LPA for mid analysts.",
            category=CompetencyCategory.DATA_ENGINEERING,
            role_family=RoleFamily.DATA,
            target_levels=[RoleLevel.LEVEL_3_MID],
            provenance=sample_provenance,
            difficulty=sample_difficulty,
        )


def test_tri_state_verification_enforced() -> None:
    """Verify tri-state verification model: state beats score (Rule R-CR-03)."""
    states = [
        VerificationState.UNPROVEN,
        VerificationState.SELF_REPORTED,
        VerificationState.DEMONSTRATED,
    ]
    assert len(states) == 3

    assert VerificationState("Unproven") == VerificationState.UNPROVEN
    assert VerificationState("Self-reported") == VerificationState.SELF_REPORTED
    assert VerificationState("Demonstrated") == VerificationState.DEMONSTRATED

    with pytest.raises(ValueError):
        VerificationState("85% Mastered")


def test_taxonomy_provenance_validation() -> None:
    """Verify TaxonomyProvenance requires valid dates and sources."""
    with pytest.raises(ValidationError):
        TaxonomyProvenance(
            source_id="UNKNOWN_SOURCE",  # type: ignore[arg-type]
            source_code="123",
            license=TaxonomyLicense.CC_BY_4_0,
            attribution_text="Some text",
            curator="Curator",
            curated_date="invalid-date",
        )


def test_difficulty_rubric_heuristic_invariant() -> None:
    """Verify DifficultyRubric enforces bounds and heuristic label (Rule R-CR-05)."""
    with pytest.raises(ValidationError):
        DifficultyRubric(learning_difficulty=6.0, application_difficulty=3.0, is_heuristic=True)

    with pytest.raises(ValidationError):
        DifficultyRubric(learning_difficulty=0.5, application_difficulty=3.0, is_heuristic=True)

    with pytest.raises(ValidationError):
        DifficultyRubric(learning_difficulty=3.0, application_difficulty=3.0, is_heuristic=False)  # type: ignore[arg-type]


def test_evidence_ledger_lifecycle() -> None:
    """Verify evidence ledger stores records and serializes cleanly."""
    ledger = EvidenceLedger(
        ledger_version="v1.0",
        last_updated="2026-10-24T18:00:00Z",
        records={
            "data.sql.window_functions": EvidenceRecord(
                competency_id="data.sql.window_functions",
                state=VerificationState.DEMONSTRATED,
                evidence_type=EvidenceType.FLAW_SCENARIO,
                recorded_at="2026-10-24T18:00:00Z",
                verification_artifact_ref="scenario-sql-flaw-01",
            )
        },
    )
    assert len(ledger.records) == 1
    assert ledger.records["data.sql.window_functions"].state == VerificationState.DEMONSTRATED

    dumped = ledger.model_dump_json()
    loaded = EvidenceLedger.model_validate_json(dumped)
    assert loaded == ledger


def test_competency_gap_report_diagnostics() -> None:
    """Verify CompetencyGapReport accurately summarizes gaps."""
    report = CompetencyGapReport(
        target_role="Data Analyst",
        target_level=RoleLevel.LEVEL_3_MID,
        total_required=5,
        demonstrated_count=2,
        self_reported_count=1,
        unproven_count=2,
        gap_nodes=["data.spark.basics", "data.stats.causal_inference"],
        gaps=[
            CompetencyGap(
                competency_id="data.spark.basics",
                required_level=RoleLevel.LEVEL_3_MID,
                current_state=VerificationState.UNPROVEN,
                is_satisfied=False,
                prerequisites_satisfied=True,
            )
        ],
    )
    assert report.total_required == 5
    assert len(report.gap_nodes) == 2
    assert report.gaps[0].is_satisfied is False


def test_competency_graph_manifest(sample_node: CompetencyNode) -> None:
    """Verify CompetencyGraphManifest container validation."""
    manifest = CompetencyGraphManifest(
        graph_id="graph-data-family-v1",
        version="1.0.0",
        role_family=RoleFamily.DATA,
        nodes=[sample_node],
        created_at="2026-10-24T18:00:00Z",
        checksum_sha256="a" * 64,
    )
    assert len(manifest.nodes) == 1
    assert manifest.nodes[0].id == sample_node.id


def test_exported_json_schemas_exist_and_valid() -> None:
    """Verify exported JSON schemas exist in config/schemas/ and are valid JSON."""
    schemas_dir = REPO_ROOT / "config" / "schemas"
    assert schemas_dir.is_dir()

    expected_files = [
        "competency_node.json",
        "competency_graph_manifest.json",
        "evidence_ledger.json",
        "competency_gap_report.json",
    ]
    for filename in expected_files:
        path = schemas_dir / filename
        assert path.is_file(), f"Missing schema file: {filename}"
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert "properties" in parsed or "$defs" in parsed
