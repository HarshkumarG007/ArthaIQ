# ArthaIQ Public Beta Pilot Plan (T10.01)

| Metadata | Details |
|---|---|
| **Author** | ArthaIQ Core Engineering & Product Governance |
| **Date** | 2026-10-21 |
| **Status** | **Ratified** (Task T10.01, Phase 10) |
| **Milestone** | Phase 10: Pilot, Monitoring and Iteration |
| **Relates to** | PRD Sections 8 & 11, `rules.md`, `architecture.md` Section 14, ADR-0008, ADR-0009, Gate G9/G10 |

---

## 1. Executive Summary & Purpose

Following the formal ratification of **Gate G9 (Public-Beta Readiness)**, this Pilot Plan establishes the operational protocol, participant cohort stratification, pre-registered statistical and user-experience evaluation metrics, feedback instrumentation, and Gate G10 exit criteria for the **ArthaIQ Public Beta Pilot**.

The objective of the pilot is to **learn from real-world usage while keeping calibration honest and uncompromised** (Phase 10 Charter). The pilot operates as a controlled, evidence-weighted decision-support environment, deliberately avoiding engagement-maximizing gamification, retention streaks, or speculative career appraisal algorithms per PRD Section 11 and Rule `R-UI-05`.

---

## 2. Cohort Stratification & Recruitment Topology

To evaluate performance across diverse compensation dynamics while preventing demographic skew, the pilot cohort is stratified across three operational dimensions (Role Family, Seniority Band, and Geographic Cluster) with a target recruitment sample of **$N = 100$ to $250$ verified tech professionals in India**.

### 2.1 Target Stratification Matrix

| Stratification Axis | Subgroup Dimension | Target Allocation (%) | Target Count ($N=150$) | Primary Operational Risk |
|---|---|---|---|---|
| **Role Family** | Software Engineering (`SWE`) | 55.0% | 82 | Baseline density anchor |
| | Data Science & Analytics (`DATA`) | 25.0% | 38 | Title ambiguity (Data Analyst vs Scientist) |
| | Machine Learning & AI (`MLAI`) | 20.0% | 30 | High variance, boutique compensation |
| **Seniority Band** | Entry / Associate (`IC1`, 0–2 YoE) | 15.0% | 22 | Campus band clustering |
| | Mid-Level (`IC2`, 3–5 YoE) | 30.0% | 45 | High switching frequency |
| | Senior (`IC3`, 6–9 YoE) | 35.0% | 53 | Core market liquidity |
| | Staff / Principal (`IC4`+, 10+ YoE) | 15.0% | 23 | Heteroskedastic dispersion |
| | Engineering Management (`M1/M2`) | 5.0% | 7 | Equity vs cash unbundling confusion |
| **Geographic Cluster** | Bengaluru Metro (`BLR`) | 35.0% | 52 | Market anchor; highest density |
| | Delhi NCR (`DEL_NCR`) | 25.0% | 38 | Corporate & consumer tech mix |
| | Hyderabad (`HYD`) | 20.0% | 30 | Enterprise GCC & cloud concentration |
| | Pune / Mumbai / Chennai (`METRO_TIER2`) | 20.0% | 30 | Cost-of-living dispersion |

### 2.2 Recruitment Channels & Eligibility Criteria
1. **Recruitment Channels:**
   - Voluntary professional network outreach across verified tech communities (alumni networks, technical open-source maintainers, local technical meetups).
   - Enterprise and startup voluntary contribution programme via primary intake connector (`SRC-INT-VOL-01`).
2. **Participant Eligibility Constraints:**
   - Must hold an active or recent technology role in India.
   - Must understand that ArthaIQ provides decision support and does not offer formal salary appraisals, binding job offers, or statutory tax counsel.
   - Strictly prohibited from using the platform for employer-side candidate screening or automated ranking (PRD Section 12).

---

## 3. Pre-Registered Success Metrics (PRD Section 11)

In compliance with Rule `R-WF-01` and PRD Section 11, all evaluation thresholds are pre-registered **prior to pilot launch**. These metrics govern the Gate G10 Production Decision:

| ID | Metric Name | Definition & Measurement Formula | Pre-Registered Target / SLA | Governing Rule / Contract |
|---|---|---|---|---|
| **M-01** | **Comprehension Rate** | Proportion of pilot users who correctly identify on exit check that The Span represents an empirical statistical range, not a guaranteed offer or employer appraisal | $\ge 90.0\%$ | Rule R-FA-04, PRD Section 11 |
| **M-02** | **Task Completion Rate** | Proportion of submitted valid profiles resulting in either a supported estimate or an explicit, calibrated abstention notice | $\ge 95.0\%$ | PRD Section 11 |
| **M-03** | **Abstention Integrity** | Zero lone salary numbers or speculative bounds rendered when cell support is thin ($N < 10$) | Strictly $100.0\%$ | Rules R-UQ-01, R-UQ-02, R-MD-08 |
| **M-04** | **Realized Conformal Coverage** | Empirical coverage of nominal 80% prediction intervals ($[\text{P10}, \text{P90}]$) against newly contributed realized compensation observations | $75.0\% \le \text{Coverage} \le 85.0\%$ | PRD NFR-01, Rule R-UQ-03 |
| **M-05** | **Interval Usefulness** | Median width ratio ($\text{Width} / \text{Median Pay}$) across supported queries | $\le 0.45$ | Rule R-UQ-04, PRD FR-05 |
| **M-06** | **Contribution Opt-In Rate** | Proportion of estimate viewers who voluntarily initiate the verified contribution flow | $\ge 15.0\%$ | PRD Section 11 |
| **M-07** | **Contribution Validity Rate** | Proportion of voluntary pay submissions satisfying schema, denomination, and quarantine sanity bounds | $\ge 90.0\%$ | Rules R-DA-04, R-DA-05 |
| **M-08** | **Serving Latency SLA** | p95 HTTP inference latency across Profile B preview deployment under concurrent pilot load | $\le 50\text{ ms}$ (Target $\le 10\text{ ms}$) | PRD NFR-02, ADR-0009 |
| **M-09** | **Operational Uptime & Errors** | Server error rate (HTTP 500) and unhandled exceptions across all pilot traffic | $< 0.1\%$ ($99.9\%$ availability) | PRD NFR-07, Rule R-ER-04 |
| **M-10** | **Zero PII Exposure** | Zero raw PII (names, contact info, PAN/Aadhaar tokens, device MACs) logged or stored in telemetry or feedback stores | Strictly $0$ incidents ($100.0\%$) | Rules R-CD-06, R-DA-07, DPDPA 2023 |
| **M-11** | **Operational Erasure Time** | End-to-end execution latency of data deletion request (`DELETE /v1/me/data`) across all operational datastores | $< 2.0\text{ seconds}$ | ADR-0008, DPDPA 2023 |

---

## 4. Privacy-Preserving Feedback Instrumentation

To collect qualitative user sentiment without compromising privacy, ArthaIQ implements a zero-PII feedback intake service (`POST /v1/feedback`) adhering to DPDPA 2023 and Rules `R-CD-06`, `R-DA-07`, and `R-UI-05`.

### 4.1 In-Product Feedback Card Architecture
- Rendered non-intrusively below the results screen (`EstimateScreen.tsx`) after the user interacts with The Span or receives an abstention notice.
- Comprises three simple, non-coercive inputs:
  1. **Clarity Rating:** 1 to 5 scale (*"How clear was the compensation span and evidence description?"*).
  2. **Usefulness Rating:** 1 to 5 scale (*"How useful is this range for your career decision support?"*).
  3. **Comprehension Verification:** Single checkbox: *"I understand this is an evidence-backed range, not a salary guarantee or binding appraisal."*
  4. **Optional Qualitative Notes:** Free-form text area ($\le 500$ characters).

### 4.2 Automated PII Scrubbing Engine
Before qualitative feedback comments are persisted or logged, they are routed through an automated server-side sanitization scrubber that strips:
- Email addresses (`[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` $\to$ `[REDACTED_EMAIL]`)
- Indian phone numbers (`(?:\+91\|0)?[6-9]\d{9}` $\to$ `[REDACTED_PHONE]`)
- Permanent Account Number (PAN) tokens (`[A-Z]{5}[0-9]{4}[A-Z]{1}` $\to$ `[REDACTED_PAN]`)
- Aadhaar 12-digit tokens (`\d{4}\s?\d{4}\s?\d{4}` $\to$ `[REDACTED_AADHAAR]`)

### 4.3 Feedback Data Model & API Contract
- **Endpoint:** `POST /v1/feedback`
- **Request Headers:** `X-Request-ID` (correlation ID from prior estimate or generated UUID4).
- **Request Body Schema (`FeedbackSubmissionRequest`):**
  ```json
  {
    "rating_clarity": 5,
    "rating_usefulness": 4,
    "comprehension_confirmed": true,
    "feedback_text": "The span helped me understand the difference between fixed cash and target bonus.",
    "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "surface": "estimate_screen"
  }
  ```
- **Response Schema (`FeedbackSubmissionResponse`):**
  ```json
  {
    "status": "received",
    "feedback_id": "FB-20261021-ABCD1234",
    "sanitized": true,
    "received_at_utc": "2026-10-21T13:30:00Z"
  }
  ```

---

## 5. Phased Pilot Rollout Schedule

The pilot follows a 3-stage rollout cadence over an 8-week evaluation cycle:

```
Week 1 - 2: Phase A (Dogfooding & Internal Panel) ──► N = 15 - 25
Week 3 - 5: Phase B (Closed Beta Pilot Cohort)   ──► N = 50 - 100
Week 6 - 8: Phase C (Public Beta Wave 1)         ──► N = 100 - 250 ──► Gate G10 Decision
```

### 5.1 Phase A: Internal Dogfooding (Weeks 1–2)
- **Cohort Size:** $N = 15$ to $25$ internal engineering, advisory panel, and institutional contributors.
- **Goals:** Smoke-test containerized deployment (`infra/docker/`), verify zero PII in Prometheus metrics and logs, rehearse operational erasure cascades, and validate feedback ingestion endpoint.
- **Exit Gate:** 0 high/critical issues; 100% test pass rate.

### 5.2 Phase B: Closed Beta Pilot (Weeks 3–5)
- **Cohort Size:** $N = 50$ to $100$ invited tech professionals across Bengaluru, Delhi NCR, and Hyderabad.
- **Goals:** Collect first live feedback ratings, track user comprehension checks ($\ge 90\%$), evaluate real-world voluntary contribution quality, and monitor serving latency distribution.
- **Exit Gate:** Comprehension $\ge 90\%$, latency $p_{95} \le 50\text{ ms}$, zero crashes.

### 5.3 Phase C: Public Beta Expansion (Weeks 6–8)
- **Cohort Size:** $N = 100$ to $250$ participants across all 4 metro clusters.
- **Goals:** Evaluate realized conformal coverage on newly ingested voluntary observations, run weekly PSI drift jobs (`compintel.monitoring.drift`), and verify freshness alarms (`compintel.monitoring.freshness`).
- **Exit Gate:** Gate G10 production review readiness.

---

## 6. Gate G10 Production Decision Protocol

At the conclusion of Week 8, the multidisciplinary Governance Panel (Quantitative ML, Compensation Economics, Privacy Counsel, Operations) will convene to evaluate Gate G10:

### 6.1 Unconditional GO Criteria
The platform shall be promoted to **Production (Phase 10 / T10.02)** if and only if:
1. **Comprehension Rate:** $\ge 90.0\%$ (Metric M-01).
2. **Empirical Coverage:** Realized coverage on newly contributed records is within $75.0\%$ to $85.0\%$ (Metric M-04).
3. **Abstention Adherence:** 100% adherence to thin-evidence abstention without lone salary numbers (Metric M-03).
4. **Latency & Reliability:** $p_{95} \le 50\text{ ms}$ and error rate $< 0.1\%$ across pilot lifecycle (Metrics M-08, M-09).
5. **Security & Privacy:** 0 open P0/P1 defects, 0 CVEs, 0 PII violations, and verified statutory deletion execution (Metrics M-10, M-11).

### 6.2 Mandatory NO-GO / Iterate Triggers
If any of the following occur, the decision is **NO-GO**:
- Realized conformal coverage drops below $70.0\%$ or exceeds $90.0\%$ (indicating severe calibration break or over-conservatism).
- Comprehension rate falls below $85.0\%$ (indicating users are interpreting ranges as personal guarantees).
- Any incident of PII disclosure or failure of statutory erasure cascade (`DELETE /v1/me/data`).
- **Remediation:** The platform remains in Public Beta, model bundle recalibration is triggered per `T10.05`, copy is refined, and a secondary 4-week pilot cycle is initiated.
