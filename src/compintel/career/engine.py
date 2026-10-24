"""Domain engine skeleton and ports for ArthaIQ Career Architect (Phase 15C).

Implements Hexagonal Architecture ports and adapters for competency taxonomy
and compensation evidence, strictly preserving layer boundaries (Rule R-CD-03,
Import Linter Contract 10) and the two-streams two-places invariant (Rule R-CR-02).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from compintel.career.graph import load_data_family_graph
from compintel.career.rubric import load_difficulty_rubrics
from compintel.career.schema import (
    CompensationEvidenceSummary,
    CompetencyGapReport,
    CompetencyGraphManifest,
    CompetencyNode,
    DifficultyRubricEntry,
    DifficultyRubricsManifest,
    EvidenceLedger,
    RoleLevel,
    VerificationState,
    validate_anti_causal_text,
)

DEFAULT_SPARSE_CELL_REASON: str = "Sparse cell data support below minimum threshold (Rule R-UQ-01)."


@runtime_checkable
class TaxonomyPort(Protocol):
    """Port for retrieving canonical competency graph, taxonomy nodes, and rubrics.

    All taxonomy access is mediated through this port to decouple domain logic
    from specific storage implementations (filesystem, database, or cache).
    """

    def get_competency_graph(self, family: str = "DATA") -> CompetencyGraphManifest:
        """Retrieve the canonical competency graph for an occupational family."""
        ...

    def get_node(self, competency_id: str, family: str = "DATA") -> CompetencyNode | None:
        """Retrieve a specific competency node by identifier, or None if not found."""
        ...

    def get_rubric(self, competency_id: str) -> DifficultyRubricEntry | None:
        """Retrieve the difficulty and effort rubric for a competency, or None if not found."""
        ...

    def get_all_rubrics(self) -> dict[str, DifficultyRubricEntry]:
        """Retrieve all calibrated difficulty rubrics."""
        ...


@runtime_checkable
class CompensationPort(Protocol):
    """Port for querying decoupled compensation distributions.

    Strictly separate from career competency graphs and requirements (Rule R-CR-02).
    Never produces composite or skill-conditioned pay promises (Rule R-CR-01).
    """

    def get_compensation_evidence(
        self,
        role_family: str,
        seniority: RoleLevel,
        location: str,
    ) -> CompensationEvidenceSummary:
        """Retrieve compensation benchmark distribution or honest abstention for role cell."""
        ...


class FilesystemTaxonomyAdapter:
    """Concrete TaxonomyPort adapter loading from local versioned JSON configurations."""

    def __init__(self, taxonomy_dir: Path | str | None = None) -> None:
        """Initialize adapter by loading and validating graph and rubrics from disk.

        Args:
            taxonomy_dir: Path to directory containing taxonomy JSON files. Defaults
                to `<repo_root>/config/taxonomy`.
        """
        if taxonomy_dir is None:
            # Resolve repo root from compintel/career/engine.py -> src -> repo_root
            repo_root = Path(__file__).resolve().parents[3]
            self._taxonomy_dir = repo_root / "config" / "taxonomy"
        else:
            self._taxonomy_dir = Path(taxonomy_dir)

        graph_file = self._taxonomy_dir / "competency_graph_data.json"
        rubrics_file = self._taxonomy_dir / "difficulty_rubrics.json"

        if not graph_file.exists():
            raise FileNotFoundError(f"Competency graph configuration not found at {graph_file}")
        if not rubrics_file.exists():
            raise FileNotFoundError(f"Difficulty rubrics configuration not found at {rubrics_file}")

        self._graph_manifest: CompetencyGraphManifest = load_data_family_graph(graph_file)
        self._rubrics_manifest: DifficultyRubricsManifest = load_difficulty_rubrics(rubrics_file)

        self._nodes_by_id: dict[str, CompetencyNode] = {n.id: n for n in self._graph_manifest.nodes}
        self._rubrics_by_id: dict[str, DifficultyRubricEntry] = {
            e.node_id: e for e in self._rubrics_manifest.entries
        }

    def get_competency_graph(self, family: str = "DATA") -> CompetencyGraphManifest:
        """Retrieve the loaded competency graph manifest."""
        if family.upper() != "DATA":
            raise ValueError(
                f"Occupational family '{family}' is not yet supported in MVP (Rule R-CR-04). "
                "Only 'DATA' family is currently ratified under Gate G15B."
            )
        return self._graph_manifest

    def get_node(self, competency_id: str, family: str = "DATA") -> CompetencyNode | None:
        """Retrieve a specific competency node by ID."""
        if family.upper() != "DATA":
            return None
        return self._nodes_by_id.get(competency_id)

    def get_rubric(self, competency_id: str) -> DifficultyRubricEntry | None:
        """Retrieve the difficulty rubric entry for a competency node."""
        return self._rubrics_by_id.get(competency_id)

    def get_all_rubrics(self) -> dict[str, DifficultyRubricEntry]:
        """Retrieve all calibrated rubrics."""
        return dict(self._rubrics_by_id)


class StubCompensationAdapter:
    """Deterministic in-memory CompensationPort adapter for testing and offline execution."""

    def __init__(
        self,
        benchmarks: dict[tuple[str, RoleLevel, str], CompensationEvidenceSummary] | None = None,
        default_abstention_reason: str = DEFAULT_SPARSE_CELL_REASON,
    ) -> None:
        """Initialize stub adapter with predefined cell benchmarks.

        Args:
            benchmarks: Mapping of (role_family, seniority, location) to summary.
            default_abstention_reason: Fallback reason when queried cell is missing.
        """
        self._benchmarks: dict[tuple[str, RoleLevel, str], CompensationEvidenceSummary] = (
            dict(benchmarks) if benchmarks else {}
        )
        self._default_abstention_reason = default_abstention_reason

    def register_benchmark(
        self,
        role_family: str,
        seniority: RoleLevel,
        location: str,
        summary: CompensationEvidenceSummary,
    ) -> None:
        """Register or update a benchmark cell."""
        self._benchmarks[(role_family.upper(), seniority, location.lower())] = summary

    def get_compensation_evidence(
        self,
        role_family: str,
        seniority: RoleLevel,
        location: str,
    ) -> CompensationEvidenceSummary:
        """Retrieve registered benchmark or return honest abstention."""
        key = (role_family.upper(), seniority, location.lower())
        if key in self._benchmarks:
            return self._benchmarks[key]

        # Honest abstention when cell is not found
        return CompensationEvidenceSummary(
            role_family=role_family,
            seniority=seniority,
            location=location,
            abstention_reason=self._default_abstention_reason,
            evidence_grade="Insufficient",
            as_of_date="2026-10-24",
        )


class CareerEngine:
    """Domain service orchestrator for ArthaIQ Career Architect.

    Coordinates taxonomy retrieval, competency gap evaluation, roadmap scheduling,
    and decoupled pay evidence querying while strictly enforcing:
    1. Anti-causal pay invariant (Rule R-CR-01).
    2. Two streams, two places separation (Rule R-CR-02).
    3. Independent offline utility (Rule R-CR-14).
    """

    def __init__(
        self,
        taxonomy_port: TaxonomyPort,
        compensation_port: CompensationPort | None = None,
    ) -> None:
        """Initialize CareerEngine with required taxonomy port and optional compensation port.

        Args:
            taxonomy_port: Port providing competency graph and rubric access.
            compensation_port: Optional port providing pay evidence distributions.
                If None, the engine operates in offline / local-only mode.
        """
        self._taxonomy_port = taxonomy_port
        self._compensation_port = compensation_port

    @property
    def taxonomy_port(self) -> TaxonomyPort:
        """Access the underlying taxonomy port."""
        return self._taxonomy_port

    @property
    def compensation_port(self) -> CompensationPort | None:
        """Access the underlying compensation port, if configured."""
        return self._compensation_port

    def get_graph(self, family: str = "DATA") -> CompetencyGraphManifest:
        """Retrieve the canonical competency graph for the specified occupational family."""
        return self._taxonomy_port.get_competency_graph(family)

    def get_competency(self, competency_id: str, family: str = "DATA") -> CompetencyNode:
        """Retrieve a specific competency node or raise KeyError."""
        node = self._taxonomy_port.get_node(competency_id, family)
        if node is None:
            raise KeyError(f"Competency '{competency_id}' not found in '{family}' family taxonomy.")
        return node

    def get_rubric(self, competency_id: str) -> DifficultyRubricEntry:
        """Retrieve the difficulty rubric entry for a competency or raise KeyError."""
        rubric = self._taxonomy_port.get_rubric(competency_id)
        if rubric is None:
            raise KeyError(f"Difficulty rubric for '{competency_id}' not found.")
        return rubric

    def get_pay_evidence(
        self,
        role_family: str,
        seniority: RoleLevel,
        location: str,
    ) -> CompensationEvidenceSummary:
        """Retrieve decoupled compensation distribution evidence for target role.

        Adheres strictly to Rule R-CR-02 (Two Streams, Two Places):
        The returned summary is an independent market distribution benchmark. It
        does NOT condition on individual user competency verification states or skills.

        Adheres strictly to Rule R-CR-14 (Independent Utility):
        If the compensation port is unconfigured or returns an abstention, the engine
        honestly returns an abstention summary without failing or impeding competency workflows.
        """
        if self._compensation_port is None:
            return CompensationEvidenceSummary(
                role_family=role_family,
                seniority=seniority,
                location=location,
                abstention_reason=(
                    "Compensation intelligence port unconfigured or system operating "
                    "in offline local-first mode (Rule R-CR-14)."
                ),
                evidence_grade="Insufficient",
                as_of_date="2026-10-24",
            )

        evidence = self._compensation_port.get_compensation_evidence(
            role_family=role_family,
            seniority=seniority,
            location=location,
        )

        # Enforce Rule R-CR-01 anti-causal validation
        validate_anti_causal_text(evidence.disclaimer, "pay_evidence.disclaimer")
        return evidence

    def evaluate_gap(
        self,
        ledger: EvidenceLedger,
        target_level: RoleLevel,
        family: str = "DATA",
        target_role: str = "Data Professional",
        min_satisfied_state: VerificationState = VerificationState.DEMONSTRATED,
        as_of_date: str | None = None,
        max_age_days: int = 730,
    ) -> CompetencyGapReport:
        """Evaluate candidate evidence ledger against target role requirements.

        Enforces Rule R-CR-03 (State Beats Score):
        Returns discrete verification state accounting, actionable gaps, and blocked gaps.
        """
        from compintel.career.gap import evaluate_competency_gap

        manifest = self.get_graph(family)
        return evaluate_competency_gap(
            ledger=ledger,
            target_level=target_level,
            graph=manifest,
            target_role=target_role,
            min_satisfied_state=min_satisfied_state,
            as_of_date=as_of_date,
            max_age_days=max_age_days,
        )
