"""Export Career Architect Pydantic v2 schemas to standard JSON Schema files.

Emits JSON Schemas to config/schemas/ for frontend validation and contract parity.
"""

from __future__ import annotations

import json
from pathlib import Path

from compintel.career.schema import (
    CompetencyGapReport,
    CompetencyGraphManifest,
    CompetencyNode,
    DifficultyRubricsManifest,
    EvidenceLedger,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "config" / "schemas"


def export_schemas() -> None:
    """Generate and write JSON schemas to config/schemas/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    schemas = {
        "competency_node.json": CompetencyNode.model_json_schema(),
        "competency_graph_manifest.json": CompetencyGraphManifest.model_json_schema(),
        "evidence_ledger.json": EvidenceLedger.model_json_schema(),
        "competency_gap_report.json": CompetencyGapReport.model_json_schema(),
        "difficulty_rubrics_manifest.json": DifficultyRubricsManifest.model_json_schema(),
    }

    for filename, schema_dict in schemas.items():
        out_path = OUTPUT_DIR / filename
        out_path.write_text(json.dumps(schema_dict, indent=2) + "\n", encoding="utf-8")
        print(f"Exported {filename} ({len(json.dumps(schema_dict))} bytes)")


if __name__ == "__main__":
    export_schemas()
