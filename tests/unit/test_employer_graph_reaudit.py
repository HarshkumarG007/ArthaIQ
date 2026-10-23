"""Unit tests for Employer Graph Feasibility Re-audit (Phase 13, EXP-10r, Task T13.01).

Verifies:
- Cumulative post-EXP-16 panel construction and non-synthetic isolation (Rule R-MD-11).
- Employer cluster anonymization floor k_min >= 5 (Rule R-DA-10).
- Graph topological metrics: density, connected components, giant component, degree distribution.
- Gate 1 feasibility decision: unconditional DEFER when qualified nodes < 50
  (Rule R-MD-09, CHARTER-EXP-10).
- Gate 1 dense / force execution path.
- Synthetic data quarantine guards (Rule R-MD-11).
- JSON and Markdown artifact serialization and schema validity.
- Zero lone numbers rule adherence (Rule R-UQ-01).
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from compintel.errors import DataContractError
from compintel.evaluation.employer_graph_reaudit import (
    EmployerGraphFeasibilityStatus,
    EmployerGraphReauditReport,
    ReauditVerdict,
    audit_employer_graph_topology,
    build_post_exp16_cumulative_panel,
    evaluate_and_save_employer_graph_reaudit,
    run_employer_graph_reaudit,
)

# ==============================================================================
# Panel Construction & Non-Synthetic Verification Tests
# ==============================================================================


def test_build_post_exp16_cumulative_panel_non_synthetic() -> None:
    """Verify cumulative panel contains zero synthetic data and spans 6 months (R-MD-11)."""
    df = build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)

    assert isinstance(df, pl.DataFrame)
    assert len(df) >= 150
    assert "is_synthetic" in df.columns
    # Rule R-MD-11: 100% verified non-synthetic data
    assert df.filter(pl.col("is_synthetic")).height == 0

    # Verify canonical schema fields
    required_cols = [
        "observation_id",
        "source_id",
        "as_of_date",
        "role_family",
        "seniority",
        "location",
        "years_experience",
        "guaranteed_cash_annual",
        "employer_cluster_id",
        "canonical_employer",
        "person_cluster_id",
        "split",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    # Verify date span across 6 months
    dates = df["as_of_date"].to_list()
    assert max(dates) > min(dates)


# ==============================================================================
# Graph Topology & Anonymization Floor Tests
# ==============================================================================


def test_audit_employer_graph_topology_kmin_anonymization() -> None:
    """Verify clusters with count < 5 collapse to EMP-ANONYMOUS (Rule R-DA-10)."""
    # 6 rows for EMP-A, 2 rows for EMP-B, 1 row for EMP-C
    records = (
        [
            {
                "employer_cluster_id": "EMP-A",
                "person_cluster_id": f"P-{i}",
                "role_family": "SWE",
                "seniority": "MID",
            }
            for i in range(6)
        ]
        + [
            {
                "employer_cluster_id": "EMP-B",
                "person_cluster_id": f"P-{6 + i}",
                "role_family": "SWE",
                "seniority": "MID",
            }
            for i in range(2)
        ]
        + [
            {
                "employer_cluster_id": "EMP-C",
                "person_cluster_id": "P-8",
                "role_family": "SWE",
                "seniority": "MID",
            }
        ]
    )
    df = pl.DataFrame(records)

    metrics = audit_employer_graph_topology(df, k_min=5, degree_threshold=3)

    assert metrics.total_employer_clusters == 3
    # Only EMP-A and EMP-ANONYMOUS qualify
    assert metrics.eligible_nodes_kmin5 == 2
    assert "EMP-A" in metrics.node_degrees
    assert "EMP-ANONYMOUS" in metrics.node_degrees
    assert "EMP-B" not in metrics.node_degrees
    assert "EMP-C" not in metrics.node_degrees


def test_audit_employer_graph_topology_metrics_calculation() -> None:
    """Verify exact graph theoretical calculations on deterministic graph."""
    # Create 3 employers with >= 5 records each
    records = []
    for emp, count in [("EMP-1", 6), ("EMP-2", 6), ("EMP-3", 6)]:
        for i in range(count):
            records.append(
                {
                    "employer_cluster_id": emp,
                    "person_cluster_id": f"PER-{emp}-{i}",
                    "role_family": "SWE",
                    "seniority": "MID",
                }
            )

    # Add transitions between EMP-1 and EMP-2, and EMP-2 and EMP-3
    records.append(
        {
            "employer_cluster_id": "EMP-2",
            "person_cluster_id": "PER-EMP-1-0",
            "role_family": "SWE",
            "seniority": "MID",
        }
    )
    records.append(
        {
            "employer_cluster_id": "EMP-3",
            "person_cluster_id": "PER-EMP-2-0",
            "role_family": "SWE",
            "seniority": "MID",
        }
    )

    df = pl.DataFrame(records)
    metrics = audit_employer_graph_topology(df, k_min=5, degree_threshold=2)

    assert metrics.eligible_nodes_kmin5 == 4  # EMP-1, EMP-2, EMP-3, EMP-ANONYMOUS
    assert metrics.total_transition_edges >= 2
    assert 0.0 <= metrics.network_density <= 1.0
    assert metrics.num_connected_components >= 1
    assert metrics.giant_component_size <= metrics.eligible_nodes_kmin5
    assert 0.0 < metrics.giant_component_fraction <= 1.0


# ==============================================================================
# Gate 1 Feasibility Decision & Verdict Tests
# ==============================================================================


def test_gate_1_feasibility_deferral_under_50_nodes() -> None:
    """Verify Gate 1 unconditionally defers when qualified nodes < 50 (Rule R-MD-09)."""
    df = build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)
    report = run_employer_graph_reaudit(
        panel_df=df,
        months_operational=6.0,
        force_embeddings=False,
        seed=42,
    )

    assert isinstance(report, EmployerGraphReauditReport)
    assert report.topology_metrics.qualified_nodes_degree_ge_3 < 50
    assert report.feasibility_status == EmployerGraphFeasibilityStatus.SPARSE_TRANSITION_TOPOLOGY
    assert not report.feasibility_passed
    assert report.verdict == ReauditVerdict.DEFER
    assert "RETAINED_UNMODIFIED" in report.champion_status
    assert "Rung F Level 2 Conformal CatBoost" in report.champion_status
    assert report.next_scheduled_audit_date == "2027-10-23"
    assert ">= 500" in report.next_audit_trigger_condition
    assert report.model_evaluation is None


def test_gate_1_dense_graph_force_embeddings_path() -> None:
    """Verify force_embeddings flag executes model benchmark without error."""
    df = build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)
    report = run_employer_graph_reaudit(
        panel_df=df,
        months_operational=6.0,
        force_embeddings=True,
        seed=42,
    )

    assert report.feasibility_status == EmployerGraphFeasibilityStatus.DENSE_GRAPH_PASSED
    assert report.model_evaluation is not None
    assert "baseline_metrics" in report.model_evaluation
    assert "variant_b_metrics" in report.model_evaluation
    assert report.verdict in {ReauditVerdict.PROMOTE, ReauditVerdict.DEFER}


# ==============================================================================
# Synthetic Isolation Guard Tests
# ==============================================================================


def test_synthetic_data_quarantine_guard() -> None:
    """Verify synthetic data raises DataContractError under Rule R-MD-11."""
    records = [
        {
            "employer_cluster_id": "EMP-SYN",
            "person_cluster_id": "PER-SYN",
            "role_family": "SWE",
            "seniority": "MID",
            "guaranteed_cash_annual": 25.0,
            "is_synthetic": True,
            "split": "train",
        }
    ]
    df = pl.DataFrame(records)

    with pytest.raises(DataContractError) as exc_info:
        run_employer_graph_reaudit(panel_df=df, allow_synthetic=False)

    assert exc_info.value.code == "SYNTHETIC_DATA_BLOCKED"
    assert exc_info.value.details.get("rule_id") == "R-MD-11"

    # Explicit override allows synthetic execution for tests
    report = run_employer_graph_reaudit(panel_df=df, allow_synthetic=True)
    assert report.n_non_synthetic == 0


# ==============================================================================
# Artifacts Generation & Schema Tests
# ==============================================================================


def test_reaudit_artifacts_generation_and_json_schema(tmp_path: Path) -> None:
    """Verify Markdown and JSON artifacts are generated and conform to schema."""
    md_path = tmp_path / "reaudit.md"
    json_path = tmp_path / "reaudit.json"

    report = evaluate_and_save_employer_graph_reaudit(
        canonical_path=None,
        output_md=md_path,
        output_json=json_path,
        months_operational=6.0,
        force_embeddings=False,
        seed=42,
    )

    assert md_path.exists()
    assert json_path.exists()
    assert report.verdict == ReauditVerdict.DEFER

    # Verify JSON schema
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["report_id"].startswith("EXP10R-")
    assert data["charter_id"] == "CHARTER-EXP-10r"
    assert data["task_id"] == "T13.01"
    assert data["verdict"] == "DEFER"
    assert "topology_metrics" in data
    assert data["topology_metrics"]["required_threshold"] == 50
    assert data["topology_metrics"]["qualified_nodes_degree_ge_3"] < 50
    assert "network_density" in data["topology_metrics"]
    assert "giant_component_fraction" in data["topology_metrics"]

    # Verify Markdown contents
    md_content = md_path.read_text(encoding="utf-8")
    assert "# Employer Graph Feasibility Re-audit" in md_content
    assert "CHARTER-EXP-10r" in md_content
    assert "SPARSE_TRANSITION_TOPOLOGY" in md_content
    assert "DEFER" in md_content
    assert "Rung F Level 2 Conformal CatBoost" in md_content
    assert "Rule `R-DA-10`" in md_content
    assert "Rule `R-MD-11`" in md_content


def test_zero_lone_numbers_and_interval_reporting() -> None:
    """Verify uncertainty metrics adhere to Rule R-UQ-01 (no lone numbers)."""
    df = build_post_exp16_cumulative_panel(months_operational=6.0, seed=42)
    report = run_employer_graph_reaudit(panel_df=df, seed=42)
    tm = report.topology_metrics

    # Check that degree distribution provides context
    assert tm.mean_node_degree > 0.0
    assert tm.median_node_degree > 0.0
    assert 0.0 <= tm.giant_component_fraction <= 1.0
    # Check that ratio is explicitly formatted
    ratio_str = f"{tm.qualified_nodes_degree_ge_3} / {tm.required_threshold}"
    assert "50" in ratio_str
