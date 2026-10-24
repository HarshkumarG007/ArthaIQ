"""Deterministic competency gap evaluation engine for ArthaIQ Career Architect (Phase 15C).

Enforces Rule R-CR-03 (State Beats Score), Rule R-CR-01 (Anti-Causal Invariants),
and core mathematical properties:
1. Non-negativity: gaps and unproven counts are mathematically >= 0.
2. Monotonicity: advancing a verification state never increases open gaps.
3. Idempotence: evaluation over identical ledger state produces identical results.
4. Prerequisite awareness: distinguishes actionable gaps from blocked gaps.
5. Recency auditing: records older than max_age_days flag recheck_suggested.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from compintel.career.graph import get_prerequisite_closure
from compintel.career.schema import (
    CompetencyGap,
    CompetencyGapReport,
    CompetencyGraphManifest,
    CompetencyNode,
    EvidenceLedger,
    RoleLevel,
    VerificationState,
)
from compintel.career.validators import validate_graph_acyclicity

DEFAULT_MAX_RECORD_AGE_DAYS: Final[int] = 730  # ~24 months staleness threshold


def parse_iso_timestamp(ts: str) -> datetime:
    """Parse ISO-8601 timestamp string into UTC datetime object."""
    clean_ts = ts.strip()
    if clean_ts.endswith("Z"):
        clean_ts = clean_ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(clean_ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def is_record_stale(
    recorded_at: str,
    as_of_date: str | None = None,
    max_age_days: int = DEFAULT_MAX_RECORD_AGE_DAYS,
) -> bool:
    """Check if an evidence record exceeds the recency threshold (ADR-0011).

    Args:
        recorded_at: ISO-8601 recorded timestamp.
        as_of_date: Optional reference timestamp. Defaults to current UTC time.
        max_age_days: Number of days before suggesting a re-check. Default is 730 days.

    Returns:
        True if record age strictly exceeds max_age_days, False otherwise.
    """
    record_dt = parse_iso_timestamp(recorded_at)
    ref_dt = parse_iso_timestamp(as_of_date) if as_of_date else datetime.now(UTC)
    delta_days = (ref_dt - record_dt).total_seconds() / 86400.0
    return delta_days > max_age_days


def get_required_nodes_for_level(
    target_level: RoleLevel,
    graph: CompetencyGraphManifest,
) -> list[CompetencyNode]:
    """Retrieve all competency nodes required directly or as prerequisites for target level.

    Args:
        target_level: Target seniority level (Junior L2, Mid L3, Senior L4).
        graph: Canonical competency graph manifest.

    Returns:
        Topologically ordered list of all required CompetencyNode instances.
    """
    node_map = {n.id: n for n in graph.nodes}

    # Identify nodes directly targeting the desired level
    direct_target_ids: set[str] = {n.id for n in graph.nodes if target_level in n.target_levels}

    # Expand to transitive prerequisite closure
    all_required_ids: set[str] = set(direct_target_ids)
    for t_id in direct_target_ids:
        for p_id in get_prerequisite_closure(t_id, graph):
            all_required_ids.add(p_id)

    # Return in topological dependency order
    topological_order = validate_graph_acyclicity(graph.nodes)
    return [node_map[n_id] for n_id in topological_order if n_id in all_required_ids]


def check_prerequisites_satisfied(
    competency_id: str,
    ledger: EvidenceLedger,
    graph: CompetencyGraphManifest,
    min_satisfied_state: VerificationState = VerificationState.DEMONSTRATED,
) -> tuple[bool, list[str]]:
    """Determine whether all immediate prerequisites for a competency are satisfied in ledger.

    Args:
        competency_id: ID of the competency to inspect.
        ledger: Client evidence ledger.
        graph: Competency graph manifest.
        min_satisfied_state: Minimum verification state to qualify as satisfied.

    Returns:
        Tuple of (all_satisfied_bool, list_of_missing_prerequisite_ids).
    """
    node_map = {n.id: n for n in graph.nodes}
    node = node_map.get(competency_id)
    if node is None:
        raise KeyError(f"Competency '{competency_id}' not found in competency graph.")

    missing: list[str] = []
    for prereq_id in node.prerequisite_ids:
        record = ledger.records.get(prereq_id)
        if record is None:
            missing.append(prereq_id)
            continue

        is_unsatisfied = (
            min_satisfied_state == VerificationState.DEMONSTRATED
            and record.state != VerificationState.DEMONSTRATED
        ) or (
            min_satisfied_state == VerificationState.SELF_REPORTED
            and record.state
            not in (
                VerificationState.SELF_REPORTED,
                VerificationState.DEMONSTRATED,
            )
        )
        if is_unsatisfied:
            missing.append(prereq_id)

    return (len(missing) == 0, missing)


def evaluate_competency_gap(
    ledger: EvidenceLedger,
    target_level: RoleLevel,
    graph: CompetencyGraphManifest,
    target_role: str = "Data Professional",
    min_satisfied_state: VerificationState = VerificationState.DEMONSTRATED,
    as_of_date: str | None = None,
    max_age_days: int = DEFAULT_MAX_RECORD_AGE_DAYS,
) -> CompetencyGapReport:
    """Evaluate candidate evidence ledger against target role requirements.

    Enforces Rule R-CR-03: State Beats Score. Computes discrete counts of
    demonstrated, self-reported, and unproven requirements with explicit gap lists.
    Guarantees non-negativity, monotonicity, and idempotence.

    Args:
        ledger: Client-side career evidence ledger.
        target_level: Target seniority level.
        graph: Canonical competency graph manifest.
        target_role: Human-readable role title.
        min_satisfied_state: Threshold verification state required for satisfaction.
        as_of_date: Reference ISO date for recency calculations.
        max_age_days: Staleness threshold in days.

    Returns:
        Structured CompetencyGapReport diagnostic.
    """
    required_nodes = get_required_nodes_for_level(target_level, graph)
    total_required = len(required_nodes)

    demonstrated_count = 0
    self_reported_count = 0
    unproven_count = 0
    recheck_suggested_count = 0

    gap_nodes: list[str] = []
    actionable_gap_nodes: list[str] = []
    blocked_gap_nodes: list[str] = []
    gaps: list[CompetencyGap] = []

    for node in required_nodes:
        record = ledger.records.get(node.id)

        # Determine current state and staleness
        if record is not None:
            current_state = record.state
            recheck_flag = is_record_stale(
                record.recorded_at, as_of_date=as_of_date, max_age_days=max_age_days
            )
        else:
            current_state = VerificationState.UNPROVEN
            recheck_flag = False

        if recheck_flag:
            recheck_suggested_count += 1

        # Count accounting
        if current_state == VerificationState.DEMONSTRATED:
            demonstrated_count += 1
        elif current_state == VerificationState.SELF_REPORTED:
            self_reported_count += 1
        else:
            unproven_count += 1

        # Determine satisfaction
        if min_satisfied_state == VerificationState.DEMONSTRATED:
            is_satisfied = current_state == VerificationState.DEMONSTRATED
        elif min_satisfied_state == VerificationState.SELF_REPORTED:
            is_satisfied = current_state in (
                VerificationState.SELF_REPORTED,
                VerificationState.DEMONSTRATED,
            )
        else:
            is_satisfied = True

        # Check prerequisite satisfaction
        prereqs_ok, missing_prereqs = check_prerequisites_satisfied(
            node.id,
            ledger=ledger,
            graph=graph,
            min_satisfied_state=min_satisfied_state,
        )

        if not is_satisfied:
            gap_nodes.append(node.id)
            if prereqs_ok:
                actionable_gap_nodes.append(node.id)
            else:
                blocked_gap_nodes.append(node.id)

        gaps.append(
            CompetencyGap(
                competency_id=node.id,
                required_level=target_level,
                current_state=current_state,
                is_satisfied=is_satisfied,
                prerequisites_satisfied=prereqs_ok,
                missing_prerequisites=missing_prereqs,
                recheck_suggested=recheck_flag,
            )
        )

    return CompetencyGapReport(
        target_role=target_role,
        target_level=target_level,
        total_required=total_required,
        demonstrated_count=demonstrated_count,
        self_reported_count=self_reported_count,
        unproven_count=unproven_count,
        recheck_suggested_count=recheck_suggested_count,
        gap_nodes=gap_nodes,
        actionable_gap_nodes=actionable_gap_nodes,
        blocked_gap_nodes=blocked_gap_nodes,
        gaps=gaps,
    )


def get_actionable_gaps(report: CompetencyGapReport) -> list[CompetencyGap]:
    """Retrieve only the open gaps that are immediately actionable (prerequisites met)."""
    return [g for g in report.gaps if not g.is_satisfied and g.prerequisites_satisfied]
