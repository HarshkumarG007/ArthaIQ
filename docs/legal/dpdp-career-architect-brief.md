# ArthaIQ Regulatory Brief for Counsel: Career Architect
**Digital Personal Data Protection Act, 2023 & Consumer Protection Compliance**

| Field | Value |
|---|---|
| Document ID | `BRIEF-DPDP-CAREER-ARCH-01` |
| Governing Statutes | Digital Personal Data Protection Act, 2023 (DPDP Act 2023); Consumer Protection Act, 2019; IT Act, 2000 & IT Rules 2021 |
| Target System | ArthaIQ Career Architect (Phase 15, PRD v1.2 FR-21 to FR-26) |
| Author | CompIntel Engineering & Product Governance |
| Target Reviewer | External Legal Counsel (Tech & Regulatory Practice) |
| Status | **DRAFT FOR COUNSEL REVIEW** |
| Scheduled Review Date | **2026-11-05** |
| Relates to | PRD v1.2 Section 12 & 13; ADR-0010, ADR-0011, ADR-0012, ADR-0013; Rules `R-CR-01` to `R-CR-15` |

---

## 1. Executive Summary & Purpose

This brief prepares legal counsel for regulatory review of the **ArthaIQ Career Architect** subsystem prior to user-facing deployment. Career Architect introduces competency gap mapping, topological career progression roadmaps, and deterministic flaw-finding practice workspaces for tech professionals in India.

Because career guidance platforms frequently encounter regulatory scrutiny regarding (a) handling of detailed career histories and résumés under India's **Digital Personal Data Protection Act, 2023 ("DPDP Act")**, and (b) deceptive earning claims or "skill ROI" promises under the **Consumer Protection Act, 2019 ("CPA 2019")**, ArthaIQ has architected the feature around strict technical and statutory invariants.

Counsel is requested to review:
1. The **Local-First Browser Storage Architecture** eliminating server-side career profile retention.
2. The mandatory **18+ Age Declaration Gate** fulfilling Section 9 DPDP Act obligations.
3. The **Statutory Anti-Causal Pay Invariant** mitigating misleading advertisement liability under CPA 2019.
4. The **Transient Untrusted Input Processing Model** ensuring zero persistence of uploaded or pasted text.

---

## 2. Statutory Compliance Architecture

### 2.1 Local-First Architecture & Data Minimization (DPDP Act Sec 4 & Sec 7)
- **Factual Architecture:** As ratified in [ADR-0012](file:///docs/adr/ADR-0012-local-first-profile-and-privacy-architecture.md), all user career profiles, target roles, competency gap analyses, and completed scenario evidence records are stored exclusively on the user's client device within browser IndexedDB (`arthaiq_career_store_v1`).
- **Zero Server Retention:** ArthaIQ maintains **zero** server-side relational database tables, document stores, or cloud repositories for user career profiles in the MVP.
- **Legal Characterization:** ArthaIQ operates as an episodic computational facilitator rather than a custodial data repository. The API endpoints (`POST /v1/career/evaluate-scenario`) are purely stateless, pure functions that process evaluation payloads in ephemeral RAM and return deterministic rubric scores without recording the user's identity or submission history.
- **Data Minimization:** Under Section 4 and Section 7 of the DPDP Act, processing is limited strictly to what is necessary for immediate computation. Since no personal career profile is stored server-side, risks of mass data breach, unauthorized profiling, or non-purpose retention are eliminated by design.

### 2.2 Protection of Children and Age Verification (DPDP Act Sec 9)
- **Statutory Constraint:** Section 9 of the DPDP Act prohibits data fiduciaries from:
  1. Processing personal data of a child (individual under 18 years of age) that is likely to cause any detrimental effect on the well-being of a child.
  2. Tracking or behavioral monitoring of children, or targeted advertising directed at children.
- **Implementation Gate:**
  - Before a user can initialize a Career Architect evidence ledger, an explicit age declaration modal is presented:
    > *"I confirm that I am 18 years of age or older, and legally eligible for employment under applicable Indian law."*
  - The affirmative acknowledgment is recorded locally in IndexedDB with a timestamp and version tag (`age_decl_v1`).
  - If a user declines or indicates they are under 18, Career Architect profile features are disabled. The user is redirected to static, publicly available general learning resources without profile tracking.

### 2.3 Prevention of Misleading Claims & Deceptive Trade Practices (Consumer Protection Act 2019)
- **Statutory Risk:** EdTech and career platforms routinely face regulatory enforcement under CPA 2019 Section 2(28) (Misleading Advertisements) and Section 10 for marketing statements that guarantee compensation hikes, promise specific salary bumps per certificate, or publish misleading "average graduate CTC" claims.
- **Statutory Anti-Causal Pay Invariant (Rule `R-CR-01`, ADR-0010):**
  - ArthaIQ strictly prohibits and algorithmically prevents any causal pay claims. The platform **never** displays statements such as *"Learning Kubernetes will raise your compensation by ₹3,50,000"* or *"Certified Data Analysts earn 40% more."*
  - Output formats return only empirical population quantiles ($P_{10}, P_{50}, P_{90}$) conditioned on verifiable market covariates (e.g. Total YoE, City, Role Family), completely decoupled from individual skill acquisition.
- **Two Streams, Two Places UI Invariant (Rule `R-CR-02`):**
  - Compensation intelligence and competency requirements are rendered in physically distinct UI panels with separate semantic headers. Zero composite "readiness scores" or "market value scores" are generated.
- **Practice Scenario Disclaimer:**
  - Flaw-finding scenarios assess practical diagnostic capability on synthetic code and schemas; they carry prominent statutory copy confirming they do not constitute formal academic qualifications, government-recognized credentials, or employment guarantees.

### 2.4 Transient Processing of Pasted Text & Résumés (Rule `R-CR-09`, `R-DA-07`)
- **Factual Architecture:** When a user pastes a job description or résumé into Career Architect intake, the text is treated as **untrusted data**.
- **Ephemeral RAM Processing:**
  - If client-side tokenization is supported, text never leaves the browser.
  - If server-side tokenization is invoked, text is parsed in ephemeral worker memory solely to extract standardized skill strings (e.g., `SQL`, `Pandas`).
  - The raw text payload is immediately garbage-collected and permanently destroyed from memory.
  - Telemetry logs strictly strip all raw text, names, emails, phone numbers, and company names via regex sanitization before emission.

### 2.5 Data Principal Statutory Rights (DPDP Act Sec 11, 12, 13)
The system provides immediate, self-service statutory mechanisms in the UI (`/career/privacy`):
1. **Right to Access & Data Portability (Sec 11):** Single-click `Export Career Profile` button exports the entire IndexedDB ledger into an open, structured JSON archive (`arthaiq-career-export.json`).
2. **Right to Erasure (Sec 12):** Single-click `Purge All Career Data` button permanently deletes all IndexedDB databases, cache entries, and local keys. Because no server-side user database exists, complete erasure is instantaneous and mathematically guaranteed.
3. **Right of Grievance Redressal (Sec 13):** Contact information for the designated Data Protection & Grievance Officer (`grievance-officer@arthaiq.in`) is permanently displayed in the footer and privacy drawer, with a guaranteed 72-hour acknowledgment and 30-day resolution SLA.

---

## 3. Required Statutory In-Product Copy & Disclaimers

Counsel is requested to review and confirm the verbatim copy below:

### Copy Block A: Intake & 18+ Declaration
```text
Age & Eligibility Declaration:
By initializing Career Architect, you declare and affirm that you are 18 years of age or older and legally eligible for employment under Indian law. ArthaIQ does not knowingly process personal data or career profiles of minors.
[ ] I confirm I am 18 years of age or older.
```

### Copy Block B: Career Architect Statutory Non-Reliance Disclaimer
```text
ArthaIQ Career Architect is an ethical career decision-support intelligence platform. It provides empirical competency mapping, self-directed capability gap analysis, and deterministic flaw-finding practice. 

ArthaIQ is not an employment agency, headhunter, training institute, or credentialing authority. Completing practice scenarios, identifying competency gaps, or mastering skills does NOT guarantee employment, interviews, promotions, or any specific compensation increase. Salary distributions represent empirical statistical market benchmarks, not individual appraisals.
```

### Copy Block C: Practice Scenario Evaluation Notice
```text
Practice scenarios are simulated diagnostic exercises evaluated against deterministic rubrics using synthetic code and artifacts. Scores reflect diagnostic performance on specific test fixtures and do not constitute professional certification or pre-employment qualification.
```

---

## 4. Counsel Review Checklist & Next Steps

| Item | Focus Area | Responsible | Target Date |
|---|---|---|---|
| 1 | Validate 18+ age declaration language against DPDP Act Section 9 | External Counsel | 2026-11-05 |
| 2 | Confirm anti-causal copy satisfies CPA 2019 Misleading Advertisement guidelines | External Counsel | 2026-11-05 |
| 3 | Review transient résumé intake processing under Section 6 consent guidelines | External Counsel | 2026-11-05 |
| 4 | Ratify Data Protection Officer contact details and grievance SLA | Compliance Lead | 2026-11-05 |
| 5 | Execute Phase 15A Gate G15A ratification upon legal sign-off receipt | Engineering Lead | 2026-11-05 |
