# ADR-0009: Hosting Profile and Operations

| Field | Value |
|---|---|
| Status | **Accepted** |
| Decided at | T9.14 (2026-10-21) |
| Relates to | `architecture.md` sections 7 and 14, PRD NFR-02, NFR-03, NFR-07, NFR-13, `docs/research/deployment-cost-model-t914.md` |

---

## Context

Three deployment profiles are defined in `architecture.md` section 7:
- **Profile A**: Laptop/workstation (development, training, offline evaluation).
- **Profile B**: Hardened cloud virtual machine (single modest VM running Docker Compose with Nginx, FastAPI, and PostgreSQL 16).
- **Profile C**: Scalable multi-zone cloud infrastructure (ECS/Cloud Run/EKS, managed RDS Multi-AZ, CloudFront CDN, Application Load Balancers).

This ADR ratifies the deployment architecture, hosting profile, and operational procedures for the **ArthaIQ Public Beta** based on empirical latency, cold-start, memory, and cost measurements conducted in T9.03, T9.14a, and T9.14b.

## Profiles

| Profile | Hardware | Suitable for | Cost driver |
|---|---|---|---|
| A | Laptop-class CPU, limited RAM, no GPU | Research prototype, local development | Developer time only |
| B | 2 vCPU (Arm64 Graviton3 / x86_64), 4 GB RAM, 40 GB NVMe SSD | Public beta preview and launch | Single VM hours and modest SSD storage (~$28.50/mo) |
| C | Autoscaled containers, managed RDS Multi-AZ, ALB, CDN | Production enterprise scale | Managed database, container tasks, load balancers (~$184.00/mo) |

## Empirical Measurements (Verified at T9.14)

- [x] **p95 estimate latency on Profile A / B (T9.03):** Measured at **4.32 ms** across 200 benchmarked runs (substantially beating the PRD NFR-02 SLA threshold of $\le 50\text{ ms}$ by $>11\times$).
- [x] **Monthly cost estimate for Profile B:** Documented at **$28.50 / month** on AWS `t4g.medium` (Mumbai / `ap-south-1`) with co-located containerized PostgreSQL 16 on NVMe and Cloudflare edge proxy.
- [x] **Monthly cost estimate for a minimal Profile C footprint:** Documented at **$184.00 / month** (AWS ECS Fargate + Multi-AZ RDS + ALB + CloudWatch), representing an $84.5\%$ premium over Profile B.
- [x] **Cold-start time for the containerized API:** Measured at **$\approx 9.6\text{ seconds}$** total wall-clock (import and bundle validation: $9.39\text{s}$, bundle smoke test: $54\text{ms}$, app factory init: $0.57\text{ms}$, first livez probe: $41.97\text{ms}$, first estimate inference: $23.2\text{ms}$).
- [x] **Storage requirement for canonical data & database at projected scale:** Base image + DB engine: $< 1.5\text{ GB}$; 10,000 voluntary contributions + audit logs: $< 50\text{ MB}$; 40 GB gp3 SSD leaves $>90\%$ storage free.

## Decision

**Adopt Profile B as the ratified hosting profile for the ArthaIQ Public Beta.**

### Rationale:
1. **Performance SLA:** Profile B easily satisfies PRD NFR-02 with 4.32 ms p95 response time and $\sim 230\text{ req/sec}$ safe throughput capacity ($>90\times$ expected peak public beta traffic).
2. **Economic Prudence:** Profile B costs $\$28.50\text{ / month}$ vs $\$184.00\text{ / month}$ for Profile C, delivering $\$1,866\text{ / year}$ in total cost of ownership savings.
3. **Operational Simplicity:** Single-node Docker Compose topology eliminates Kubernetes / ECS orchestration overhead, network hop latency, and complex multi-service debugging while preserving container portability.
4. **Resilience & Security:** Fronted by Cloudflare proxy (DDoS mitigation, TLS termination, HTTP/3), daily encrypted S3/R2 database backups, and strict non-root container isolation (OWASP ASVS 14.2.1).

## CI/CD Pipeline

| Stage | Checks & Actions |
|---|---|
| **Pre-commit** | ruff check/format, secret scan, nbstripout, large-file guard |
| **CI: Static** | ruff, mypy strict, import-linter, Vitest, TypeScript strict |
| **CI: Tests** | Unit, property, contract, leakage, metric, and synthetic tests |
| **CI: Security** | pip-audit, npm audit, Bandit SAST, automated secret scan |
| **CI: Build** | Docker multi-stage images (`Dockerfile.api`, `Dockerfile.web`), OpenAPI schema diff |
| **Preview** | Automated deploy via `scripts/deploy_preview.py up --wait` and health verification |
| **Production** | Manual sign-off gate; canary deploy; rollback runbook |

## Operational Procedures & Rollbacks

1. **Deployment Harness:** All environments are driven declaratively via `infra/deploy/preview-env.yaml` and `scripts/deploy_preview.py`.
2. **Model Bundle Hot-Rollback:** Switching `CHAMPION_MODEL_VERSION` in the environment restores previous champion bundles without rebuilding containers ($< 2\text{ seconds}$).
3. **Container Rollback:** If an application regression is detected, Nginx upstream proxies traffic to the prior stable container tag.
4. **Database Migration Rollback:** Managed via Alembic (`make migrate-down`).
5. **Backup Lifecycle:** Automated daily encrypted `pg_dump` snapshots transferred to S3/R2 with 30-day lifecycle expiration ($RTO < 15\text{ min}$, $RPO \le 24\text{ hours}$).

## Graduation Triggers to Profile C

Migration to Profile C will be initiated only when:
- Sustained monthly query volume exceeds **500,000 requests / month**, or
- Multi-AZ automated failover is mandated by an enterprise SLA ($99.99\%$).

## Consequences

- Minimal Infrastructure as Code is codified in `infra/deploy/preview-env.yaml`.
- Detailed cost and capacity analysis is preserved in `docs/research/deployment-cost-model-t914.md`.
- Docker containers run non-root (UID 10001) with internal network bridging (`compintel-preview`).
- Secrets in production come from secure environment injection (e.g. AWS Secrets Manager / Doppler / sealed env files), never from repository files.

## Change Log

| Date | Change |
|---|---|
| 2026-10-13 | Initial stub created at T0.04 |
| 2026-10-21 | **Ratified to Accepted at T9.14b** based on empirical latency (4.32ms p95), cold-start (9.6s), and cost models ($28.50/mo vs $184/mo) |
