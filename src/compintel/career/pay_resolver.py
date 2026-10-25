"""Pay-to-role resolver through compensation port for ArthaIQ Career Architect (Phase 15C).

Maps target compensation queries (point estimate or interval range) to grounded empirical
role cells using the decoupled CompensationPort, strictly enforcing:
- Rule R-CR-02 (Two Streams, Two Places): Pay distributions remain isolated from role graphs.
- Rule R-CR-01 (Anti-Causal Invariants): Zero claims that transitioning causes pay ₹X.
- Rule R-UQ-01 / R-UI-02 (Zero Lone Numbers): Returns calibrated quantile intervals.
- Rule R-AI-01 (Zero Fabrication / Zero Extrapolation): Cleanly abstains without extrapolating
  when target pay falls outside grounded empirical cell bounds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from compintel.career.schema import (
    CompensationEvidenceSummary,
    CompensationPort,
    PayCellMatch,
    PayCellMatchStatus,
    PayToRoleResolution,
    RoleLevel,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_SUPPORTED_FAMILY: Final[str] = "DATA"
DEFAULT_LOCATIONS: Final[list[str]] = [
    "bangalore",
    "mumbai",
    "hyderabad",
    "delhi_ncr",
    "pune",
    "remote",
]
DEFAULT_SENIORITIES: Final[list[RoleLevel]] = [
    RoleLevel.LEVEL_2_JUNIOR,
    RoleLevel.LEVEL_3_MID,
    RoleLevel.LEVEL_4_SENIOR,
]
PAY_RESOLUTION_DISCLAIMER: Final[str] = (
    "Statistical compensation distribution matching. Not an appraisal, offer, "
    "or guarantee of individual pay (Rules R-CR-01, R-UQ-01)."
)


def calculate_interval_overlap(
    t_min: float,
    t_max: float,
    p10: float,
    p90: float,
) -> tuple[float, PayCellMatchStatus]:
    """Calculate overlap ratio and containment status between target pay and empirical [P10, P90].

    Args:
        t_min: Minimum target compensation in LPA.
        t_max: Maximum target compensation in LPA.
        p10: 10th percentile empirical compensation bound.
        p90: 90th percentile empirical compensation bound.

    Returns:
        Tuple of (overlap_ratio in [0.0, 1.0], PayCellMatchStatus).
    """
    inter_len = max(0.0, min(t_max, p90) - max(t_min, p10))
    union_len = max(1e-6, max(t_max, p90) - min(t_min, p10))
    span = max(1e-6, p90 - p10)

    # Point query handling (t_min == t_max)
    if abs(t_min - t_max) < 1e-9:
        if p10 <= t_min <= p90:
            median_approx = (p10 + p90) / 2.0
            dist_from_center = abs(t_min - median_approx)
            # Overlap scales with proximity to center of empirical interval
            ratio = max(0.05, 1.0 - (dist_from_center / span))
            return (round(ratio, 4), PayCellMatchStatus.CONTAINED)

        # Point is outside [P10, P90]
        boundary_dist = p10 - t_min if t_min < p10 else t_min - p90
        margin = 0.10 * span
        status = (
            PayCellMatchStatus.NEAR_BOUNDARY
            if boundary_dist <= margin
            else PayCellMatchStatus.OUT_OF_BOUNDS
        )
        return (0.0, status)

    # Interval query handling (t_min < t_max)
    if inter_len > 0.0:
        ratio = inter_len / union_len
        return (round(min(1.0, max(0.0, ratio)), 4), PayCellMatchStatus.CONTAINED)

    # Intervals do not intersect
    boundary_dist = p10 - t_max if t_max < p10 else t_min - p90
    margin = 0.10 * span
    status = (
        PayCellMatchStatus.NEAR_BOUNDARY
        if boundary_dist <= margin
        else PayCellMatchStatus.OUT_OF_BOUNDS
    )
    return (0.0, status)


def resolve_target_pay_to_roles(
    target_pay: float | tuple[float, float],
    compensation_port: CompensationPort,
    role_family: str = DEFAULT_SUPPORTED_FAMILY,
    location_filter: str | None = None,
    locations: Sequence[str] | None = None,
    seniorities: Sequence[RoleLevel] | None = None,
) -> PayToRoleResolution:
    """Resolve target compensation against empirical role cells via decoupled port.

    Never invents, hallucinates, or extrapolates beyond grounded empirical cell distributions
    (Rule R-AI-01). If target pay is outside grounded empirical boundaries or data is sparse,
    honestly abstains and identifies nearest supported alternatives (Rule R-CR-02, R-UQ-01).

    Args:
        target_pay: Target compensation in LPA, either as a scalar or (min_lpa, max_lpa) tuple.
        compensation_port: Decoupled port providing empirical compensation cell distributions.
        role_family: Occupational family identifier (default 'DATA').
        location_filter: Optional single location to restrict search (case-insensitive).
        locations: Optional sequence of locations to query.
        seniorities: Optional sequence of RoleLevels to query.

    Returns:
        PayToRoleResolution with matched empirical cells or honest abstention
        with nearest alternatives.

    Raises:
        ValueError: If target_pay is non-positive or min_lpa > max_lpa.
    """
    # 1. Normalize target pay range
    if isinstance(target_pay, (int, float)):
        if target_pay <= 0.0:
            raise ValueError(f"target_pay must be positive, got {target_pay}")
        t_min = float(target_pay)
        t_max = float(target_pay)
    elif isinstance(target_pay, (tuple, list)):
        if len(target_pay) != 2:
            raise ValueError(
                f"target_pay interval must contain exactly 2 elements, got {len(target_pay)}"
            )
        t_min = float(target_pay[0])
        t_max = float(target_pay[1])
        if t_min <= 0.0:
            raise ValueError(f"min target_pay must be positive, got {t_min}")
        if t_min > t_max:
            raise ValueError(f"min target_pay ({t_min}) cannot exceed max target_pay ({t_max})")
    else:
        raise TypeError(
            f"target_pay must be float or tuple[float, float], got {type(target_pay).__name__}"
        )

    # 2. Validate occupational family support (Rule R-CR-04)
    if role_family.upper() != DEFAULT_SUPPORTED_FAMILY:
        return PayToRoleResolution(
            target_pay_min_lpa=t_min,
            target_pay_max_lpa=t_max,
            role_family=role_family,
            location_filter=location_filter,
            is_abstaining=True,
            abstention_reason=(
                f"Occupational family '{role_family}' is not supported in MVP (Rule R-CR-04). "
                f"Only '{DEFAULT_SUPPORTED_FAMILY}' family is currently ratified under Gate G15B."
            ),
            matched_cells=[],
            nearest_alternatives=[],
            disclaimer=PAY_RESOLUTION_DISCLAIMER,
        )

    # 3. Resolve search locations and seniorities
    if location_filter is not None:
        query_locations = [location_filter.strip().lower()]
    elif locations is not None:
        query_locations = [loc.strip().lower() for loc in locations]
    else:
        query_locations = list(DEFAULT_LOCATIONS)

    query_seniorities = list(seniorities) if seniorities is not None else list(DEFAULT_SENIORITIES)

    # 4. Query compensation port for empirical cells
    grounded_cells: list[tuple[RoleLevel, str, CompensationEvidenceSummary]] = []
    for seniority in query_seniorities:
        for loc in query_locations:
            summary = compensation_port.get_compensation_evidence(role_family, seniority, loc)
            if (
                summary.abstention_reason is None
                and summary.p10 is not None
                and summary.p50 is not None
                and summary.p90 is not None
            ):
                grounded_cells.append((seniority, loc, summary))

    # 5. Handle zero grounded cells in search space
    if not grounded_cells:
        loc_str = location_filter if location_filter else ", ".join(query_locations)
        return PayToRoleResolution(
            target_pay_min_lpa=t_min,
            target_pay_max_lpa=t_max,
            role_family=role_family,
            location_filter=location_filter,
            is_abstaining=True,
            abstention_reason=(
                f"No empirically supported compensation cells found for family '{role_family}' "
                f"across requested locations [{loc_str}] (Rule R-UQ-01)."
            ),
            matched_cells=[],
            nearest_alternatives=[],
            disclaimer=PAY_RESOLUTION_DISCLAIMER,
        )

    # 6. Evaluate each grounded cell against target compensation
    target_mid = (t_min + t_max) / 2.0
    candidate_matches: list[PayCellMatch] = []

    for seniority, loc, summary in grounded_cells:
        p10 = summary.p10
        p90 = summary.p90
        p50 = summary.p50
        assert p10 is not None and p90 is not None and p50 is not None  # Guaranteed by check above

        overlap_ratio, match_status = calculate_interval_overlap(t_min, t_max, p10, p90)
        distance_to_median = round(target_mid - p50, 2)

        candidate_matches.append(
            PayCellMatch(
                role_family=role_family,
                seniority=seniority,
                location=loc,
                compensation=summary,
                match_status=match_status,
                overlap_ratio=overlap_ratio,
                distance_to_median_lpa=distance_to_median,
            )
        )

    # 7. Check for contained matches
    contained_matches = [
        m for m in candidate_matches if m.match_status == PayCellMatchStatus.CONTAINED
    ]

    if contained_matches:
        # Sort by overlap ratio descending, then absolute distance to median ascending
        contained_matches.sort(
            key=lambda m: (-m.overlap_ratio, abs(m.distance_to_median_lpa), m.seniority)
        )
        return PayToRoleResolution(
            target_pay_min_lpa=t_min,
            target_pay_max_lpa=t_max,
            role_family=role_family,
            location_filter=location_filter,
            is_abstaining=False,
            abstention_reason=None,
            matched_cells=contained_matches,
            nearest_alternatives=[],
            disclaimer=PAY_RESOLUTION_DISCLAIMER,
        )

    # 8. Zero extrapolation: Honest abstention with nearest alternatives
    # Candidate matches do not contain target pay.
    # We never hallucinate or extrapolate linearly (Rule R-AI-01).
    global_min_p10 = min(
        m.compensation.p10 for m in candidate_matches if m.compensation.p10 is not None
    )
    global_max_p90 = max(
        m.compensation.p90 for m in candidate_matches if m.compensation.p90 is not None
    )

    if t_min > global_max_p90:
        abstention_reason = (
            f"Target compensation (₹{t_min:.1f} LPA) exceeds maximum empirical P90 "
            f"(₹{global_max_p90:.1f} LPA) across grounded role cells in family '{role_family}'. "
            "Zero extrapolation permitted under Rule R-AI-01 and Rule R-UQ-01."
        )
    elif t_max < global_min_p10:
        abstention_reason = (
            f"Target compensation (₹{t_max:.1f} LPA) is below minimum empirical P10 "
            f"(₹{global_min_p10:.1f} LPA) across grounded entry-level role cells. "
            "Zero extrapolation permitted under Rule R-AI-01 and Rule R-UQ-01."
        )
    else:
        abstention_reason = (
            f"Target compensation range [₹{t_min:.1f}, ₹{t_max:.1f}] LPA falls into an empirical "
            "distribution gap with no directly overlapping supported role cells."
        )

    # Rank alternatives by absolute distance to median
    candidate_matches.sort(key=lambda m: (abs(m.distance_to_median_lpa), m.seniority))
    nearest_alternatives = candidate_matches[:3]

    return PayToRoleResolution(
        target_pay_min_lpa=t_min,
        target_pay_max_lpa=t_max,
        role_family=role_family,
        location_filter=location_filter,
        is_abstaining=True,
        abstention_reason=abstention_reason,
        matched_cells=[],
        nearest_alternatives=nearest_alternatives,
        disclaimer=PAY_RESOLUTION_DISCLAIMER,
    )
