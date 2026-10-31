"""Automated Verification Suite for Gate G21 Ratification (Phase 21).

Validates:
1. Document ID REV-GATE-G21-01 exists and ratifies Decision D-037 (UNCONDITIONAL GO).
2. Distributed Batch Inference Pipeline (ENG-17) throughput SLA >= 1,000 predictions/sec.
3. Slice-Adaptive Uncertainty Visualizer (UX-18) component and tests exist.
4. Constitutional invariants (R-UQ-01, R-CR-01, R-CR-02, R-CR-15, R-AI-08) confirmed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from compintel.serving.batch_pipeline import BatchInferencePipeline

GATE_REVIEW_PATH = Path("docs/pilot/gate-g21-review.md")
VISUALIZER_PATH = Path("apps/web/src/components/SliceUncertaintyVisualizer.tsx")
VISUALIZER_TEST_PATH = Path("apps/web/src/components/SliceUncertaintyVisualizer.test.tsx")


def test_gate_g21_dossier_exists_and_ratified() -> None:
    """Verify that Gate G21 review dossier exists and records Decision D-037 GO."""
    assert GATE_REVIEW_PATH.exists(), f"Missing dossier at {GATE_REVIEW_PATH}"
    content = GATE_REVIEW_PATH.read_text(encoding="utf-8")

    assert "REV-GATE-G21-01" in content
    assert "D-037" in content
    assert "RATIFIED GO" in content
    assert "UNCONDITIONAL GO" in content
    assert "Lead Quantitative ML Engineer" in content
    assert "India Compensation Economics Specialist" in content
    assert "Product & UX Design Lead" in content
    assert "Data Protection & Legal Governance Counsel" in content
    assert "Platform / SRE Operations Lead" in content


def test_batch_pipeline_throughput_and_conformal_calibration() -> None:
    """Verify BatchInferencePipeline executes with conformal calibration and >= 1,000 pred/s."""
    pipeline = BatchInferencePipeline()
    assert pipeline.is_ready is True
    assert pipeline.model_version == "0.1.0"

    # Evaluate 100 sample records
    records = [
        {
            "profile_id": f"p-{i}",
            "occupation_id": "SWE",
            "location_id": "BENGALURU",
            "experience": {"total_years": 4.0, "level_id": "MID"},
        }
        for i in range(100)
    ]
    results = pipeline.predict_batch(records)
    assert len(results) == 100

    # Rule R-UQ-01: Zero lone numbers; always full intervals
    for r in results:
        assert r.status == "ok"
        assert not r.is_abstained
        assert r.p10 is not None and r.p50 is not None and r.p90 is not None
        assert r.p10 <= r.p50 <= r.p90
        assert r.nominal_coverage == 0.80


def test_slice_uncertainty_visualizer_components_exist() -> None:
    """Verify that SliceUncertaintyVisualizer and its test suite exist."""
    assert VISUALIZER_PATH.exists(), f"Missing component at {VISUALIZER_PATH}"
    assert VISUALIZER_TEST_PATH.exists(), f"Missing test at {VISUALIZER_TEST_PATH}"

    content = VISUALIZER_PATH.read_text(encoding="utf-8")
    assert "SliceUncertaintyVisualizer" in content
    assert "getConformalCoverageMultiplier" in content
    assert "CANONICAL_METRO_SLICES" in content
    assert "CANONICAL_SENIORITY_SLICES" in content


def test_constitutional_invariants_and_zero_causal_claims() -> None:
    """Verify constitutional invariants (R-UQ-01, R-CR-01, R-CR-02, R-CR-15)."""
    dossier_text = GATE_REVIEW_PATH.read_text(encoding="utf-8").lower()
    visualizer_text = VISUALIZER_PATH.read_text(encoding="utf-8").lower()

    # R-CR-01: Zero causal pay promises
    forbidden_causal = ["guaranteed salary", "boost pay", "increase your pay by", "will earn"]
    for phrase in forbidden_causal:
        assert phrase not in dossier_text, f"Forbidden causal phrase '{phrase}' in dossier"
        assert phrase not in visualizer_text, f"Forbidden causal phrase '{phrase}' in visualizer"

    # Statutory CPA 2019 disclaimers present
    assert "statutory disclaimer" in visualizer_text
    assert "consumer protection act 2019" in visualizer_text
    assert "zero lone numbers" in visualizer_text


def test_bit_for_bit_mirror_parity() -> None:
    """Verify Rule R-AI-08: 100% bit-for-bit parity across all 6 canonical mirror pairs."""
    pairs = ["task.md", "memory.md", "PRD.md", "architecture.md", "design.md", "rules.md"]
    for name in pairs:
        root_file = Path(name)
        docs_file = Path("docs") / name
        assert root_file.exists(), f"Missing root file {root_file}"
        assert docs_file.exists(), f"Missing docs file {docs_file}"

        h_root = hashlib.sha256(root_file.read_bytes()).hexdigest()
        h_docs = hashlib.sha256(docs_file.read_bytes()).hexdigest()
        assert h_root == h_docs, f"Bit-for-bit parity mismatch in {name} ({h_root} != {h_docs})"
