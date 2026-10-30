"""Machine Learning & AI (MLAI) taxonomy ingestion entrypoint (Task T19.01).

Ingests labour taxonomy definitions from O*NET 28.0 (15-1299.09 AI / ML Specialists,
15-1299.08 Data Scientists) and ESCO v1.1.1 (Transversal Skills) under CC BY 4.0
and European Commission Open Reuse terms with SHA-256 manifest verification.
"""

from __future__ import annotations

from compintel.career.ingestion import (
    TaxonomyBundle,
    generate_mlai_family_taxonomy,
)

__all__ = ["generate_mlai_family_taxonomy", "TaxonomyBundle"]

if __name__ == "__main__":
    bundle, b_path, m_path = generate_mlai_family_taxonomy()
    sha_short = bundle.manifest.bundle_sha256[:16]
    print(f"Generated {b_path.name} ({len(bundle.elements)} elements, SHA-256: {sha_short}...)")
    print(f"Generated {m_path.name}")
