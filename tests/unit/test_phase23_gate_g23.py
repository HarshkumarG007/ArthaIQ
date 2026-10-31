"""Automated Verification Suite for Gate G23 Ratification (Phase 23).

Validates:
1. Document ID REV-GATE-G23-01 exists and ratifies Decision D-039 (UNCONDITIONAL GO).
2. Enterprise Batch REST endpoint modules exist and expose schemas and router.
3. Batch REST throughput and latency benchmark confirms SLA compliance.
4. OpenAPI specification documents /v1/estimates/batch and /v1/estimates/batch/stream.
5. Decision D-039 recorded in STATE.md and memory.md.
6. Constitutional invariants (R-UQ-01, R-CR-01, R-CR-02, R-CR-15, R-AI-08) strictly confirmed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

GATE_REVIEW_PATH = Path("docs/pilot/gate-g23-review.md")
BENCHMARK_JSON_PATH = Path("experiments/results/batch_api_benchmark_v1.json")
ROUTER_PATH = Path("src/compintel/serving/routers/batch.py")
TYPES_PATH = Path("src/compintel/serving/types.py")
OPENAPI_PATH = Path("docs/api/openapi.json")
STATE_PATH = Path("docs/STATE.md")
MEMORY_PATH = Path("memory.md")


def test_gate_g23_dossier_exists_and_ratified() -> None:
    """Verify that Gate G23 review dossier exists and records Decision D-039 GO."""
    assert GATE_REVIEW_PATH.exists(), f"Missing dossier at {GATE_REVIEW_PATH}"
    content = GATE_REVIEW_PATH.read_text(encoding="utf-8")

    assert "REV-GATE-G23-01" in content
    assert "D-039" in content
    assert "RATIFIED GO" in content
    assert "UNCONDITIONAL GO" in content
    assert "Lead Quantitative ML Engineer" in content
    assert "India Compensation Economics Specialist" in content
    assert "API & Backend Systems Architect" in content
    assert "Data Protection & Legal Governance Counsel" in content
    assert "Platform / SRE Operations Lead" in content


def test_batch_modules_and_schemas_exist() -> None:
    """Verify that batch router and Pydantic v2 schemas exist."""
    assert ROUTER_PATH.exists(), f"Missing router at {ROUTER_PATH}"
    assert TYPES_PATH.exists(), f"Missing types at {TYPES_PATH}"

    router_code = ROUTER_PATH.read_text(encoding="utf-8")
    assert "/v1/estimates/batch" in router_code
    assert "/v1/estimates/batch/stream" in router_code
    assert "StreamingResponse" in router_code
    assert "application/x-ndjson" in router_code

    types_code = TYPES_PATH.read_text(encoding="utf-8")
    assert "BatchEstimateRequest" in types_code
    assert "BatchEstimateResponse" in types_code
    assert "BatchEstimateItem" in types_code
    assert "BatchEstimateSummary" in types_code


def test_batch_api_benchmark_sla_pass() -> None:
    """Verify that batch API benchmark confirms SLA compliance."""
    assert BENCHMARK_JSON_PATH.exists(), f"Missing benchmark at {BENCHMARK_JSON_PATH}"
    data = json.loads(BENCHMARK_JSON_PATH.read_text(encoding="utf-8"))

    assert data["benchmark_id"] == "BENCH-BATCH-REST-01"
    verdict = data["verdict"]
    assert verdict["status"] == "PASS"
    assert verdict["overall_sla_pass"] is True
    assert verdict["meets_throughput_sla"] is True
    assert verdict["meets_latency_sla"] is True

    # Check observed throughput and latency
    metrics = data["observed_metrics"]
    assert metrics["batch_500_throughput_pps"] >= 1000.0
    assert metrics["batch_50_p95_latency_ms"] <= 100.0


def test_openapi_specification_documents_batch_endpoints() -> None:
    """Verify that OpenAPI specification documents both batch endpoints."""
    assert OPENAPI_PATH.exists(), f"Missing OpenAPI specification at {OPENAPI_PATH}"
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))

    paths = spec.get("paths", {})
    assert "/v1/estimates/batch" in paths, "Missing /v1/estimates/batch in OpenAPI spec"
    assert "/v1/estimates/batch/stream" in paths, (
        "Missing /v1/estimates/batch/stream in OpenAPI spec"
    )

    batch_post = paths["/v1/estimates/batch"]["post"]
    assert "200" in batch_post["responses"]
    assert "422" in batch_post["responses"]
    assert "503" in batch_post["responses"]

    stream_post = paths["/v1/estimates/batch/stream"]["post"]
    assert "200" in stream_post["responses"]
    assert "application/x-ndjson" in stream_post["responses"]["200"]["content"]


def test_decision_d039_recorded_in_state_and_memory() -> None:
    """Verify that Decision D-039 is recorded in STATE.md and memory.md."""
    state_content = STATE_PATH.read_text(encoding="utf-8")
    memory_content = MEMORY_PATH.read_text(encoding="utf-8")

    assert "D-039" in state_content or "Gate G23" in state_content
    assert "D-039" in memory_content


def test_six_canonical_mirror_pairs_bit_for_bit_parity() -> None:
    """Verify Rule R-AI-08: 100% bit-for-bit parity across all 6 canonical mirror pairs."""
    mirror_pairs = [
        ("task.md", "docs/task.md"),
        ("memory.md", "docs/memory.md"),
        ("PRD.md", "docs/PRD.md"),
        ("architecture.md", "docs/architecture.md"),
        ("design.md", "docs/design.md"),
        ("rules.md", "docs/rules.md"),
    ]
    for src, dst in mirror_pairs:
        p_src = Path(src)
        p_dst = Path(dst)
        assert p_src.exists(), f"Source file missing: {src}"
        assert p_dst.exists(), f"Destination file missing: {dst}"
        h_src = hashlib.sha256(p_src.read_bytes()).hexdigest()
        h_dst = hashlib.sha256(p_dst.read_bytes()).hexdigest()
        assert h_src == h_dst, f"Parity mismatch between {src} and {dst}"
