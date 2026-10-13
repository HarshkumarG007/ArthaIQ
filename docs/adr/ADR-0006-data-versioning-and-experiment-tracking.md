# ADR-0006: Data Versioning and Experiment Tracking

| Field | Value |
|---|---|
| Status | **Proposed** |
| Decided at | T3.13 |
| Relates to | `architecture.md` section 8, `rules.md` R-DA-02, R-MD-10 |

---

## Context

Every reported metric must reproduce from a commit hash, data snapshot id and seed with one documented command (NFR-01). The data is sensitive and large; it is gitignored. A versioning strategy is needed that (a) tracks lineage without committing data files, and (b) is lightweight enough for one developer.

## Options

| Option | Mechanism | Pro | Con |
|---|---|---|---|
| Content-hashed manifests (proposed default) | SHA-256 of each raw file written to a YAML manifest in `data/raw/<source_id>/manifest.yaml`; manifests are committed | No new infrastructure; lineage is auditable from the manifest | Manual download if raw files are lost |
| DVC (Data Version Control) | `.dvc` pointer files committed; data in remote storage (S3, GCS, etc.) | Pull-and-reproduce with `dvc pull`; integrates with CI | Adds a remote storage dependency; overhead for one developer |
| Git LFS | Large files stored in LFS | Simple `git pull` | LFS quotas; not great for frequent binary updates |

**Proposed:** content-hashed manifests as the default. Add DVC only if remote storage becomes necessary (e.g., for CI or collaboration).

## Experiment tracking

| Option | Mechanism | Pro | Con |
|---|---|---|---|
| File-based run records (proposed default) | Each run writes `config.yaml`, `metrics.json`, `snapshot_id`, `commit`, library versions to `experiments/results/<run_id>/` | Zero infrastructure; fully reproducible | No comparison UI; search requires grep |
| MLflow | Server or file-store backend | Comparison UI; artifact tracking | Extra service; overkill for one developer |

**Proposed:** file-based records committed to `experiments/results/` (small JSON and YAML only, no Parquet or pickle). MLflow added only if collaboration requires it.

## Data snapshot id

Every canonical dataset snapshot is identified by:
- A deterministic hash of the manifest files it was built from.
- The code commit that produced it.
- The config hash.

The snapshot id is stored in every model bundle and API response.

## Decision

**Pending.** Finalized at T3.13 once `make reproduce-data` produces identical hashes on two clean runs.

## Consequences

- `data/` is gitignored; manifests in `data/raw/<source_id>/manifest.yaml` are committed.
- Every training run produces a `run_id` directory in `experiments/results/` with a reproduction command.
- `make final-eval` writes a lock file that prevents re-running against the test set (R-MD-02).
- If DVC is adopted later, this ADR is updated with the remote backend choice.

## Change log

| Date | Change |
|---|---|
| 2026-10-13 | Stub created at T0.04 |
