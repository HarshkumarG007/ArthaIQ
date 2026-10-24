"""Unit and property-based tests for compintel.career.gap (Task T15.16).

Verifies Rule R-CR-03 (State Beats Score), recency auditing, prerequisite blocking,
and core mathematical invariants (Non-negativity, Monotonicity, Idempotence)
using deterministic unit tests and Hypothesis property-based testing.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from compintel.career.engine import CareerEngine, FilesystemTaxonomyAdapter
from compintel.career.gap import (
    evaluate_competency_gap,
    get_actionable_gaps,
    get_required_nodes_for_level,
    is_record_stale,
)
from compintel.career.graph import load_data_family_graph
from compintel.career.schema import (
    CompetencyGraphManifest,
    EvidenceLedger,
    EvidenceRecord,
    EvidenceType,
    RoleLevel,
    VerificationState,
)

DATA_NODE_IDS = [
    "data.anl.l2_eda",
    "data.anl.l2_hygiene",
    "data.anl.l2_sql_basic",
    "data.anl.l3_dashboard",
    "data.anl.l3_sql_adv",
    "data.gen.l2_ethics",
    "data.gen.l2_prob_decomp",
    "data.gen.l3_docs",
    "data.gen.l3_stakeholder",
    "data.sci.l3_exp_design",
    "data.sci.l3_feat_eng",
    "data.sci.l3_ml_supervised",
    "data.sci.l4_bigdata",
    "data.sci.l4_causal",
]


@pytest.fixture(scope="module")
def data_graph() -> CompetencyGraphManifest:
    """Fixture providing cached DATA family competency DAG manifest."""
    return load_data_family_graph()


def test_is_record_stale() -> None:
    """Verify recency auditing flags records older than max_age_days (ADR-0011)."""
    ref_date = "2026-10-24T12:00:00Z"

    # Fresh record: 30 days old
    fresh_ts = "2026-09-24T12:00:00Z"
    assert not is_record_stale(fresh_ts, as_of_date=ref_date, max_age_days=730)

    # Stale record: 800 days old (recorded in 2024)
    stale_ts = "2024-08-01T12:00:00Z"
    assert is_record_stale(stale_ts, as_of_date=ref_date, max_age_days=730)

    # Boundary test: exactly 730 days old -> not strictly greater, so False
    exact_ts = "2024-10-24T12:00:00Z"
    assert not is_record_stale(exact_ts, as_of_date=ref_date, max_age_days=730)


def test_get_required_nodes_for_level(data_graph: CompetencyGraphManifest) -> None:
    """Verify required nodes include direct role targets plus transitive prerequisites."""
    # Junior Level 2
    l2_nodes = get_required_nodes_for_level(RoleLevel.LEVEL_2_JUNIOR, data_graph)
    l2_ids = {n.id for n in l2_nodes}
    assert "data.anl.l2_eda" in l2_ids
    assert "data.anl.l2_sql_basic" in l2_ids
    # Level 4 node must not be in Level 2 requirements
    assert "data.sci.l4_bigdata" not in l2_ids

    # Senior Level 4
    l4_nodes = get_required_nodes_for_level(RoleLevel.LEVEL_4_SENIOR, data_graph)
    l4_ids = {n.id for n in l4_nodes}
    # Direct Senior nodes
    assert "data.sci.l4_bigdata" in l4_ids
    assert "data.sci.l4_causal" in l4_ids
    # Transitive prerequisites (e.g. ML supervised, SQL advanced, basic SQL)
    assert "data.sci.l3_ml_supervised" in l4_ids
    assert "data.anl.l2_sql_basic" in l4_ids


def test_empty_ledger_all_unproven(data_graph: CompetencyGraphManifest) -> None:
    """Verify evaluating an empty ledger reports all requirements as unproven gaps."""
    empty_ledger = EvidenceLedger(
        ledger_version="v1.0",
        records={},
        last_updated="2026-10-24T12:00:00Z",
    )
    report = evaluate_competency_gap(
        ledger=empty_ledger,
        target_level=RoleLevel.LEVEL_3_MID,
        graph=data_graph,
        target_role="Mid Data Analyst",
    )

    assert report.demonstrated_count == 0
    assert report.self_reported_count == 0
    assert report.unproven_count == report.total_required
    assert len(report.gap_nodes) == report.total_required
    assert report.total_required > 0

    # Actionable gaps must only be nodes with no prerequisites
    actionable = get_actionable_gaps(report)
    assert len(actionable) > 0
    for g in actionable:
        assert g.prerequisites_satisfied is True
        assert len(g.missing_prerequisites) == 0


def test_fully_demonstrated_ledger_zero_gaps(data_graph: CompetencyGraphManifest) -> None:
    """Verify evaluating a ledger with all requirements demonstrated produces zero gaps."""
    required = get_required_nodes_for_level(RoleLevel.LEVEL_3_MID, data_graph)
    records = {
        node.id: EvidenceRecord(
            competency_id=node.id,
            state=VerificationState.DEMONSTRATED,
            evidence_type=EvidenceType.FLAW_SCENARIO,
            recorded_at="2026-10-20T10:00:00Z",
        )
        for node in required
    }
    full_ledger = EvidenceLedger(
        ledger_version="v1.0",
        records=records,
        last_updated="2026-10-24T12:00:00Z",
    )
    report = evaluate_competency_gap(
        ledger=full_ledger,
        target_level=RoleLevel.LEVEL_3_MID,
        graph=data_graph,
    )

    assert len(report.gap_nodes) == 0
    assert len(report.actionable_gap_nodes) == 0
    assert len(report.blocked_gap_nodes) == 0
    assert report.demonstrated_count == report.total_required
    assert report.unproven_count == 0
    assert report.self_reported_count == 0


def test_prerequisite_blocking_behavior(data_graph: CompetencyGraphManifest) -> None:
    """Verify nodes with unfulfilled prerequisites are categorized as blocked gaps."""
    # data.anl.l2_hygiene requires data.anl.l2_sql_basic
    # Initially: both unproven
    ledger = EvidenceLedger(
        records={},
        last_updated="2026-10-24T12:00:00Z",
    )
    rep1 = evaluate_competency_gap(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        graph=data_graph,
    )
    assert "data.anl.l2_sql_basic" in rep1.actionable_gap_nodes
    assert "data.anl.l2_hygiene" in rep1.blocked_gap_nodes

    # Demonstrate basic SQL -> hygiene should become actionable
    records = {
        "data.anl.l2_sql_basic": EvidenceRecord(
            competency_id="data.anl.l2_sql_basic",
            state=VerificationState.DEMONSTRATED,
            evidence_type=EvidenceType.CODE_EXERCISE,
            recorded_at="2026-10-24T12:00:00Z",
        )
    }
    ledger2 = EvidenceLedger(records=records, last_updated="2026-10-24T12:00:00Z")
    rep2 = evaluate_competency_gap(
        ledger=ledger2,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        graph=data_graph,
    )
    assert "data.anl.l2_sql_basic" not in rep2.gap_nodes
    assert "data.anl.l2_hygiene" in rep2.actionable_gap_nodes
    assert "data.anl.l2_hygiene" not in rep2.blocked_gap_nodes


def test_recency_auditing_in_gap_report(data_graph: CompetencyGraphManifest) -> None:
    """Verify records older than staleness threshold trigger recheck_suggested count."""
    records = {
        "data.anl.l2_sql_basic": EvidenceRecord(
            competency_id="data.anl.l2_sql_basic",
            state=VerificationState.DEMONSTRATED,
            evidence_type=EvidenceType.SELF_ATTESTATION,
            recorded_at="2023-01-01T00:00:00Z",  # ~3.5 years old
        )
    }
    ledger = EvidenceLedger(records=records, last_updated="2026-10-24T12:00:00Z")
    report = evaluate_competency_gap(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        graph=data_graph,
        as_of_date="2026-10-24T12:00:00Z",
        max_age_days=730,
    )

    assert report.recheck_suggested_count == 1
    sql_gap = next(g for g in report.gaps if g.competency_id == "data.anl.l2_sql_basic")
    assert sql_gap.recheck_suggested is True


def test_career_engine_evaluate_gap_integration() -> None:
    """Verify CareerEngine integrates with gap evaluation cleanly."""
    adapter = FilesystemTaxonomyAdapter()
    engine = CareerEngine(taxonomy_port=adapter)

    ledger = EvidenceLedger(records={}, last_updated="2026-10-24T12:00:00Z")
    report = engine.evaluate_gap(
        ledger=ledger,
        target_level=RoleLevel.LEVEL_2_JUNIOR,
        target_role="Junior Data Analyst",
    )

    assert report.target_role == "Junior Data Analyst"
    assert report.target_level == RoleLevel.LEVEL_2_JUNIOR
    assert report.total_required > 0
    assert report.unproven_count == report.total_required


# ==============================================================================
# Property-Based Testing (Hypothesis) for Core Mathematical Invariants
# ==============================================================================

# Strategy for generating arbitrary EvidenceRecord dictionaries
evidence_state_strategy = st.sampled_from(
    [
        VerificationState.UNPROVEN,
        VerificationState.SELF_REPORTED,
        VerificationState.DEMONSTRATED,
    ]
)
evidence_type_strategy = st.sampled_from(
    [
        EvidenceType.SELF_ATTESTATION,
        EvidenceType.FLAW_SCENARIO,
        EvidenceType.CODE_EXERCISE,
        EvidenceType.PORTFOLIO_ARTIFACT,
    ]
)


@st.composite
def arbitrary_ledger_strategy(draw: st.DrawFn) -> EvidenceLedger:
    """Generate arbitrary randomized EvidenceLedgers over the DATA family competencies."""
    selected_nodes = draw(st.lists(st.sampled_from(DATA_NODE_IDS), unique=True))
    records: dict[str, EvidenceRecord] = {}
    for node_id in selected_nodes:
        state = draw(evidence_state_strategy)
        # Skip UNPROVEN in explicit records or keep them
        records[node_id] = EvidenceRecord(
            competency_id=node_id,
            state=state,
            evidence_type=draw(evidence_type_strategy),
            recorded_at="2026-10-20T12:00:00Z",
        )
    return EvidenceLedger(records=records, last_updated="2026-10-24T12:00:00Z")


@settings(max_examples=50, deadline=None)
@given(
    ledger=arbitrary_ledger_strategy(),
    level=st.sampled_from(
        [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR]
    ),
)
def test_property_non_negativity_and_closure(
    data_graph: CompetencyGraphManifest,
    ledger: EvidenceLedger,
    level: RoleLevel,
) -> None:
    """Invariant 1: Non-negativity and complete state partition accounting."""
    report = evaluate_competency_gap(
        ledger=ledger,
        target_level=level,
        graph=data_graph,
    )

    # Non-negativity
    assert report.total_required >= 0
    assert report.demonstrated_count >= 0
    assert report.self_reported_count >= 0
    assert report.unproven_count >= 0
    assert len(report.gap_nodes) >= 0
    assert len(report.actionable_gap_nodes) >= 0
    assert len(report.blocked_gap_nodes) >= 0

    # Exact state partition accounting
    assert (
        report.total_required
        == report.demonstrated_count + report.self_reported_count + report.unproven_count
    )
    # Gap partition accounting
    assert len(report.gap_nodes) == len(report.actionable_gap_nodes) + len(report.blocked_gap_nodes)
    assert len(report.gaps) == report.total_required


@settings(max_examples=50, deadline=None)
@given(
    ledger=arbitrary_ledger_strategy(),
    level=st.sampled_from(
        [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR]
    ),
)
def test_property_idempotence(
    data_graph: CompetencyGraphManifest,
    ledger: EvidenceLedger,
    level: RoleLevel,
) -> None:
    """Invariant 2: Idempotence f(L) == f(L)."""
    rep1 = evaluate_competency_gap(ledger=ledger, target_level=level, graph=data_graph)
    rep2 = evaluate_competency_gap(ledger=ledger, target_level=level, graph=data_graph)

    assert rep1.model_dump() == rep2.model_dump()


@settings(max_examples=50, deadline=None)
@given(
    ledger=arbitrary_ledger_strategy(),
    level=st.sampled_from(
        [RoleLevel.LEVEL_2_JUNIOR, RoleLevel.LEVEL_3_MID, RoleLevel.LEVEL_4_SENIOR]
    ),
    target_node_id=st.sampled_from(DATA_NODE_IDS),
)
def test_property_monotonicity_under_promotion(
    data_graph: CompetencyGraphManifest,
    ledger: EvidenceLedger,
    level: RoleLevel,
    target_node_id: str,
) -> None:
    """Invariant 3: Promoting a node to Demonstrated never increases open gaps."""
    rep_before = evaluate_competency_gap(ledger=ledger, target_level=level, graph=data_graph)

    # Promote target_node_id to DEMONSTRATED
    new_records = dict(ledger.records)
    new_records[target_node_id] = EvidenceRecord(
        competency_id=target_node_id,
        state=VerificationState.DEMONSTRATED,
        evidence_type=EvidenceType.FLAW_SCENARIO,
        recorded_at="2026-10-24T12:00:00Z",
    )
    promoted_ledger = EvidenceLedger(records=new_records, last_updated="2026-10-24T12:00:00Z")
    rep_after = evaluate_competency_gap(
        ledger=promoted_ledger, target_level=level, graph=data_graph
    )

    # Gaps can never increase
    assert len(rep_after.gap_nodes) <= len(rep_before.gap_nodes)
    # Demonstrated count can never decrease
    assert rep_after.demonstrated_count >= rep_before.demonstrated_count
