# ADR-0006: Data Versioning, Lineage Tracking, and Experiment Reproducibility

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T3.13 (2026-10-16) |
| Relates to | `architecture.md` section 8 & 9, `rules.md` R-DA-01, R-DA-02, R-DA-05, R-DA-08, R-MD-10 |

---

## Context

Every reported compensation metric and model evaluation in ArthaIQ must reproduce from a git commit hash, data snapshot id, configuration digest, and seed with one documented command (NFR-01, Rule R-DA-02). Compensation data contains sensitive market observations and is gitignored per Rule R-DA-08. A versioning and lineage strategy is required that:
1. Tracks full end-to-end data lineage without committing raw or processed binary data files to Git.
2. Mathematically guarantees that zero records are silently dropped ($\Delta = \text{Total} - (\text{Valid} + \text{Quarantined}) == 0$, Rule R-DA-05).
3. Guarantees deterministic, idempotent canonical data builds from immutable raw manifests (`make reproduce-data`).
4. Binds every trained model artifact and API response to a cryptographically verifiable data snapshot identifier.

## Options Considered

| Option | Mechanism | Pro | Con | Decision |
|---|---|---|---|---|
| **Content-Hashed Manifests + Cryptographic Snapshot ID (Accepted)** | SHA-256 of raw files committed in `data/raw/<source_id>/manifest.yaml`. Lineage engine (`src/compintel/ingestion/lineage.py`) computes composite snapshot hash from manifests, git commit, config directory, and schema version. Derived data built via `make reproduce-data`. | Zero external cloud storage dependencies; auditable directly in Git; bitwise and semantic determinism verified across operating systems. | Requires manual re-run of `make reproduce-data` upon clean checkout. | **Accepted** |
| DVC (Data Version Control) | `.dvc` pointer files committed to Git; binary datasets stored in cloud object storage (S3/GCS). | Native remote cache; integrates with CI runners. | Adds cloud infrastructure dependency, egress costs, and credential management complexity for single-developer workflow. | Deferred to Phase 9 if cloud scaling requires it. |
| Git LFS | Large binary parquet files stored in Git Large File Storage. | Built-in git pull commands. | Storage bandwidth quotas; repo bloat across pipeline iterations; violates strict separation of code and data. | Rejected |

## Experiment Tracking

| Option | Mechanism | Pro | Con | Decision |
|---|---|---|---|---|
| **File-Based Run Records (Accepted)** | Each experiment run writes `config.yaml`, `metrics.json`, `lineage.json`, `snapshot_id`, `git_commit`, and library versions to `experiments/results/<run_id>/`. | Zero infrastructure overhead; fully self-contained; diffable via standard text tools. | No real-time web comparison UI; parameter search requires script inspection. | **Accepted** |
| MLflow / Weights & Biases | Centralized tracking server and dashboard. | Rich UI; automated metric charts. | Additional daemon / service dependency; overkill for initial production ladder. | Deferred |

## Decision

We accept **Content-Hashed Manifests with Cryptographic Data Snapshot Identifiers** and **File-Based Experiment Records**:

1. **Immutable Raw Zone (`data/raw/<source_id>/manifest.yaml`):**
   - Every raw dataset is accompanied by a committed YAML manifest containing SHA-256 file digests, licence ID, and timestamp.
   - Connector interface (`BaseConnector`) enforces licence verification (Rule R-DA-01) and raw file checksum verification (Rule R-DA-02) before reading any file.

2. **Deterministic Data Snapshot ID Algorithm:**
   Every canonical dataset snapshot is identified by a deterministic 12-character uppercase hexadecimal identifier:
   $$\text{snapshot\_seed} = \text{manifest\_hash} \parallel \text{git\_commit} \parallel \text{config\_hash} \parallel \text{schema\_version}$$
   $$\text{snapshot\_id} = \text{"SNAP-"} \parallel \text{SHA-256}(\text{snapshot\_seed})[0:12].\text{upper}()$$
   where:
   - `manifest_hash`: SHA-256 digest over sorted source IDs and semantic JSON representations of their `manifest.yaml` files.
   - `git_commit`: Current git commit SHA (`git rev-parse HEAD` or environment override `ARTHAIQ_COMMIT`).
   - `config_hash`: SHA-256 digest over sorted relative POSIX paths and semantic JSON representations of all configuration files in `config/`.
   - `schema_version`: Canonical schema semver string (`CURRENT_SCHEMA_VERSION = "1.0.0"`).

3. **Canonical Pipeline Execution (`make reproduce-data`):**
   - Automated via `scripts/reproduce_data.py`.
   - Ingests raw records from approved connectors.
   - Normalizes titles, seniority, and comp measures per canonical schema (`compintel.schema.canonical`).
   - Attaches Source Quality Scores (`compintel.quality.scoring`) and cluster IDs (`compintel.quality.dedup`).
   - Enforces quarantine policies (`compintel.quality.quarantine`) with mathematical count reconciliation ($\Delta = 0$).
   - Validates bulk Polars DataFrame against Pandera schema contract (`validate_observations_df`).
   - Computes deterministic data content hash (`data_hash`) via sorted NDJSON serialization.
   - Persists:
     - `data/canonical/canonical_observations.parquet`
     - `data/canonical/snapshots/<snapshot_id>.parquet`
     - `data/canonical/canonical_lineage.json`
     - `data/canonical/snapshots/<snapshot_id>_lineage.json`
     - `data/quarantine/quarantine_records.parquet`

4. **Idempotency Guarantee:**
   - Two consecutive clean runs of `make reproduce-data` on identical raw data and code produce 100% identical snapshot hashes, data hashes, and row counts. Verified by `--verify-idempotence`.

## Consequences

- `data/` is strictly gitignored (Rule R-DA-08); only `manifest.yaml` and `canonical_lineage.json` are committed.
- Any modification to raw files, source configurations, or schema immediately invalidates the snapshot hash.
- Every trained model bundle and public API response stores `data_snapshot_id`.
- `make final-eval` (T4.03) will write a lock file to `experiments/preregistration/FINAL_EVAL_LOCK` preventing unrecorded re-runs against the test set (Rule R-MD-02).

## Change Log

| Date | Change |
|---|---|
| 2026-10-13 | Initial stub proposed at T0.04 |
| 2026-10-16 | Finalized and Accepted at T3.13 upon verified idempotent implementation of `make reproduce-data` |
