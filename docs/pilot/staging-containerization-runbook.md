# ArthaIQ Staging Containerization & Runbook

**Document ID:** `RUNBOOK-STAGING-CONTAINER-01`  
**System:** ArthaIQ Platform Staging  
**Version:** v1.2.0  
**Last Audited:** 2026-11-01  
**Status:** ACTIVE

---

## 1. Staging Topology & Resource Allocation

The ArthaIQ staging environment mirrors the production architecture with strict resource bounds, loopback isolation, and non-root execution.

```
                      +------------------------------------------+
                      |   Host Ingress (Browser / Client)        |
                      |   http://localhost:8080                   |
                      +--------------------+---------------------+
                                           |
                                           v
                   +-----------------------------------------------+
                   | Container: arthaiq-staging-web                |
                   | Image: nginx:1.27-alpine                      |
                   | Memory Cap: 128MB | CPU Cap: 0.25             |
                   | Hardened Nginx: CSP, nosniff, SPA fallback    |
                   +-------+-------------------------------+-------+
                           |                               |
       Static / SPA Assets |                               | Proxy /v1/, /metrics, /livez
       (pre-compiled Vite) |                               |
                           v                               v
             +---------------------------+  +-------------------------------+
             | /usr/share/nginx/html     |  | Container: arthaiq-staging-api|
             | React 18 / TypeScript SPA |  | Image: python:3.12-slim       |
             +---------------------------+  | User: compintel (UID 10001)   |
                                            | Memory Cap: 512MB | CPU: 1.0  |
                                            | Port: 127.0.0.1:8001 -> 8000  |
                                            +---------------+---------------+
                                                            |
                                                            | Database connection
                                                            v
                                            +-------------------------------+
                                            | Container: arthaiq-staging-db |
                                            | Image: postgres:16-alpine     |
                                            | Memory Cap: 256MB | CPU: 0.5  |
                                            | Port: 127.0.0.1:5433 -> 5432  |
                                            +-------------------------------+
```

### Security & Invariant Enforcements:
1. **Non-Root Execution (ASVS 14.2.1):** The API container runs exclusively as system user `compintel` (`UID 10001`).
2. **Loopback Port Isolation:** PostgreSQL (`5433:5432`) and API (`8001:8000`) bind strictly to `127.0.0.1`, preventing inadvertent external exposure. Only Nginx (`8080:80`) is exposed for ingress.
3. **Hardened Content Security Policy (ADR-0013):**
   ```nginx
   add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:; connect-src 'self'; worker-src 'self' blob:;" always;
   ```
   The `worker-src 'self' blob:` directive securely enables the offline sql.js Web Worker sandbox.
4. **Zero Lone Numbers (Rule R-UQ-01):** API responses emit full calibrated intervals ($[P_{10}, P_{50}, P_{90}]$).
5. **Decoupled Honest Abstention (Rule R-UQ-02):** Unseen or sparse queries return HTTP 200 with structured abstention codes without unhandled exceptions.

---

## 2. Standard Operating Procedures

### A. Pre-Requisite Checks
Ensure Docker Engine and Compose are available:
```bash
docker --version
docker compose version
```

On Windows, ensure Docker Desktop is started:
```powershell
Start-Process "C:\Users\Lenovo\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
```

### B. Building & Starting the Staging Stack
Compile the Vite web distribution:
```bash
npm run build --prefix apps/web
```

Launch the complete staging stack with resource quotas and health checks:
```bash
docker compose -f infra/docker/docker-compose.staging.yml up --build -d
```

### C. Monitoring & Verification
Verify container status:
```bash
docker compose -f infra/docker/docker-compose.staging.yml ps
```

Expected healthy output:
```
NAME                  IMAGE                STATUS                    PORTS
arthaiq-staging-db    postgres:16-alpine   Up (healthy)              127.0.0.1:5433->5432/tcp
arthaiq-staging-api   infra-api:staging    Up (healthy)              127.0.0.1:8001->8000/tcp
arthaiq-staging-web   infra-web:staging    Up (healthy)              0.0.0.0:8080->80/tcp
```

Execute automated staging verification:
```powershell
.venv\Scripts\python scripts/verify_staging_containerization.py
```

### D. Live Endpoint Probes
- **Liveness:**
  ```bash
  curl -i http://localhost:8080/livez
  ```
- **Readiness:**
  ```bash
  curl -i http://localhost:8080/readyz
  ```
- **Batch Compensation Inference:**
  ```bash
  curl -X POST http://localhost:8080/v1/estimates/batch \
    -H "Content-Type: application/json" \
    -d '{
      "items": [
        {"profile_id": "swe-1", "occupation_id": "SWE", "location_id": "BENGALURU", "experience": {"total_years": 4.0, "level_id": "MID"}}
      ],
      "nominal_coverage": 0.80
    }'
  ```

### E. Teardown & Clean Purge
To cleanly shut down the staging environment and remove ephemeral volumes:
```bash
docker compose -f infra/docker/docker-compose.staging.yml down -v
```

---

## 3. Incident Response & Troubleshooting

| Symptom | Cause | Remediation |
|:---|:---|:---|
| `docker API at npipe:////./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified` | Docker Desktop is not actively running in Windows session | Launch Docker Desktop from the Start Menu or run `Start-Process "C:\Users\Lenovo\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"`. |
| Port 8080 already in use | Another web server or container is using 8080 | Pass `WEB_PORT=8081 docker compose -f infra/docker/docker-compose.staging.yml up -d`. |
## 4. Batch Client SDK & CLI Verification

To evaluate candidate profiles against the staging stack via CLI:
```bash
# Evaluate candidate profiles from CSV using the CLI tool
python scripts/compintel_batch.py --input profiles.csv --output results.json --url http://localhost:8080

# Or execute with streaming NDJSON
python scripts/compintel_batch.py -i candidates.json -o evaluated.csv --stream --url http://localhost:8080
```


