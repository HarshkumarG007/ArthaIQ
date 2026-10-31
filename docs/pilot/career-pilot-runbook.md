# ArthaIQ Career Architect — Multi-Family Pilot Cohort Deployment Runbook

| Metadata | Value |
|---|---|
| **Document ID** | `RUNBOOK-CAREER-PILOT-01` |
| **Status** | **Active** |
| **Date** | 2026-10-30 |
| **Milestone** | Phase 17: Multi-Family Pilot Cohort Deployment & Production Staging |
| **Governing Plan** | `PLAN-CAREER-PILOT-STAGING-01` |
| **Related Gate** | Gate G17 (`docs/pilot/gate-g17-staging-decision.md`) |
| **Governing Rules** | `R-WF-01`, `R-CR-01`, `R-CR-02`, `R-CR-03`, `R-CR-11`, `R-CR-12`, `R-CR-14`, `R-UQ-01`, `ADR-0010`, `ADR-0012` |

---

## 1. Executive Summary & Scope

This runbook establishes the operational procedures for the **ArthaIQ Career Architect Multi-Family Pilot**. The pilot evaluates the end-to-end Career Architect experience for verified India technology professionals across three supported role families:

- **Data & AI** (14-node competency DAG, 7 flaw-finding practice scenarios)
- **Software Engineering / SWE** (15-node competency DAG, 7 flaw-finding practice scenarios)
- **Machine Learning & AI / MLAI** (15-node competency DAG, 3 flaw-finding practice scenarios)

The pilot is strictly voluntary, non-appraisal, and governed by India DPDP Act 2023. It yields no binding pay recommendations, job offers, or certification claims. Its purpose is to evaluate comprehension, usability, and calibration within constitutional invariants.

> **Core Invariant (Rule R-CR-12, ADR-0012):** All user career profiles, gap states, and practice evidence reside exclusively on-device in `arthaiq_career_ledger` (browser IndexedDB). The backend serving layer is stateless. Zero server-side user profile storage in MVP.

---

## 2. Cohort Stratification & Recruitment Protocol

### 2.1 Target Cohort Stratification Matrix ($N = 150$)

| Stratification Axis | Subgroup | Allocation (%) | Target Count |
|---|---|:---:|:---:|
| **Role Family** | Software Engineering (`SWE`) | 50% | 75 |
| | Data & AI (`DATA`) | 50% | 75 |
| **Seniority Band** | Junior / Entry (`IC1`, 0–2 YoE) | 20% | 30 |
| | Mid-Level (`IC2`, 3–5 YoE) | 35% | 53 |
| | Senior (`IC3`, 6–9 YoE) | 35% | 53 |
| | Staff / Principal (`IC4+`, 10+ YoE) | 10% | 14 |
| **Geographic Cluster** | Bengaluru Metro (`BLR`) | 35% | 52 |
| | Delhi NCR (`DEL_NCR`) | 25% | 38 |
| | Hyderabad (`HYD`) | 20% | 30 |
| | Pune / Mumbai / Chennai | 20% | 30 |

### 2.2 Participant Eligibility Criteria

1. Active or recent technology professional in India.
2. Currently engaged in software engineering, data science, analytics, or ML/AI role.
3. Understands ArthaIQ provides decision support and does **not** offer formal salary appraisals, binding offers, or statutory tax counsel.
4. Must **not** use the platform for employer-side candidate screening or automated ranking.
5. Must provide voluntary informed consent per Section 2.3.

### 2.3 DPDP Act 2023 Participant Consent Notice

The following notice must be presented to and acknowledged by every participant **before** any platform interaction begins:

> **Consent Notice (India Digital Personal Data Protection Act 2023, Section 6)**
>
> By proceeding, you acknowledge:
>
> 1. **Purpose:** ArthaIQ Career Architect is a self-reflection and career decision-support tool. It is **not** an employer appraisal, compensation guarantee, or legal employment advice platform.
> 2. **Local-First Data Processing:** All career profile data, competency gap states, and practice attempt records are stored exclusively on your device in browser local storage (IndexedDB). ArthaIQ does **not** store, process, or transmit your personal career data to any server.
> 3. **Right to Erasure (Section 12):** You may delete all locally stored data at any time by clicking the **"Erase All My Data"** button within the platform settings. Erasure is immediate and irreversible; 0 bytes of your data is retained after erasure.
> 4. **No Profiling or Automated Decisions:** ArthaIQ does not construct user profiles on any server, does not use your data to make automated employment decisions, and does not share your data with third parties.
> 5. **Pilot Research Notice:** Aggregate, de-identified usage metrics (e.g., feature engagement rates, task completion counts) may be collected to improve the platform. These metrics cannot be used to re-identify individual participants.
>
> *Proceeding constitutes your informed voluntary consent per DPDP Act 2023 Section 6.*

---

## 3. Participant User Journey Guide

### 3.1 Step-by-Step Flow

**Step 1: Role Family Selection (Setup)**
- Navigate to the Career Architect tab.
- Select your **Role Family**: `Data & AI`, `Software Engineering`, or `Machine Learning & AI`.
- Select your **Target Level**: Junior (L2), Mid (L3), or Senior (L4).
- The platform automatically configures the correct competency graph, scenario corpus, and market pay benchmarks for your family.

**Step 2: Competency Gap Map Exploration**
- View your personal gap map showing all competencies for your selected family.
- Each node displays its state: `Unproven` (grey), `Self-reported` (amber), or `Demonstrated` (green).
- Filter by cluster category to focus on specific domains.
- Note: The gap map reflects only your local on-device ledger.

**Step 3: Topological Roadmap & Pacing**
- Navigate to the Roadmap Plan tab.
- Adjust the weekly available hours pacing slider (5 / 10 / 15 / 20 h/wk).
- The roadmap calculates conservative effort ranges ($[H_{\min}, H_{\max}]$) — these are heuristic estimates only, not guarantees.
- Review the decoupled market pay context panel for your role and city; note the $P_{10}$, $P_{50}$, $P_{90}$ distributions.

**Step 4: Practice Scenario Flaw Identification**
- Navigate to the Practice tab.
- Select a practice scenario for your current priority competency.
- Read the code or data artifact carefully.
- Select the flaws you identify using the checkbox interface.
- Submit your attempt. The rubric scorer evaluates deterministically (no AI model involvement, < 5ms latency).
- Review your detailed score report showing: points awarded, false flag deductions, and competencies demonstrated.

**Step 5: Evidence Ledger Verification**
- Navigate to the Evidence Ledger tab.
- Review your ledger showing all recorded demonstration events.
- Verify the **Erase All My Data** button is visible and functional — test it in a private session to confirm immediate erasure.

**Step 6: Pilot Exit Survey**
- Complete the structured 5-question exit survey provided by the pilot team.
- Key comprehension check: "Does the ArthaIQ pay range represent a guarantee, or a statistical market distribution?"

---

## 4. Privacy & Data Erasure Protocol

### 4.1 Verifying Local-First Storage

Before any participant session, the operator verifies:

1. Open browser DevTools → Application → IndexedDB → `arthaiq_career_ledger`
2. Confirm three object stores exist: `competency_states`, `attempt_records`, `user_profile`
3. Confirm no data exists before participant interactions begin
4. After interactions, confirm data is present locally only (no network transmissions to remote profile endpoints)

### 4.2 DPDP Sec 12 Hard Purge Execution

To perform the Section 12 right-to-erasure wipe:

1. Navigate to Career Architect → Settings (gear icon)
2. Click **"Erase All My Data"**
3. Confirm the purge dialog
4. Verify in DevTools → IndexedDB that all three object stores are empty (0 records)
5. Verify browser network log shows no POST/PUT to remote endpoints during erasure
6. **Expected result:** 0 bytes residual, 0 server calls, immediate effect

---

## 5. Staging Environment Quickstart

### 5.1 Prerequisites

- Docker Desktop installed and running
- 8 GB free RAM minimum
- Node.js 22+ and Python 3.12+ (for local verification only)

### 5.2 Build & Launch Preview Environment

```bash
# 1. Build production web bundle
npm run build --prefix apps/web

# 2. Start the staging environment (from project root)
docker-compose -f infra/docker/docker-compose.staging.yml up --build

# 3. Verify all containers healthy
docker-compose -f infra/docker/docker-compose.staging.yml ps

# 4. Access the platform
# Web UI:  http://localhost:8080
# API:     http://localhost:8000/v1/health
# Docs:    http://localhost:8000/docs
```

### 5.3 Health Checks

| Endpoint | Expected Response |
|---|---|
| `GET /livez` | `{"status": "alive"}` |
| `GET /v1/health` | `{"status": "healthy", "version": "1.x.x"}` |
| `GET http://localhost:8080` | ArthaIQ SPA root page loads |

### 5.4 Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| `api` container fails health check | DB not ready | Wait 30s for Postgres to initialize |
| Web Worker sandbox fails silently | CSP blocks `blob:` URIs | Verify `worker-src 'self' blob:` in Nginx CSP |
| IndexedDB empty after profile creation | Browser private/incognito mode | Use standard browser window for pilot sessions |
| Practice scoring takes > 5ms | CPU throttling | Disable browser throttle in DevTools |

---

## 6. Pilot Operations Responsibilities

| Role | Responsibility |
|---|---|
| **Pilot Coordinator** | Participant recruitment, consent collection, exit survey distribution |
| **Privacy Officer** | DPDP consent audit, erasure verification, aggregate telemetry review |
| **Platform Operator** | Staging environment deployment, health monitoring, incident response |
| **ML Governance Lead** | Calibration comprehension validation, scorecard metric sign-off |

---

## 7. Exit Criteria & Gate G17 Decision

The Gate G17 governance panel reviews the pilot readiness upon completion of T17.02 and T17.03. The panel ratifies **GO** only when:

| Check | Target |
|---|---|
| `M-STG-01` Calibration Comprehension | ≥ 90% |
| `M-STG-02` Task Completion Rate | ≥ 95% |
| `M-STG-03` Deterministic Scoring Variance | σ² = 0.000 |
| `M-STG-04` Scoring Latency p95 | ≤ 5 ms |
| `M-STG-05` Local Storage Footprint | ≤ 100 KB |
| `M-STG-06` DPDP Sec 12 Hard Purge Residual | = 0 bytes |
| `M-STG-07` Zero Causal Promises | 0 violations |
| `M-STG-08` Anti-Credentialism | 0 violations |
| `M-STG-09` Two Streams Two Places Decoupling | 100% |
| `M-STG-10` Cross-Family Pacing DAG Monotonicity | 100% |

