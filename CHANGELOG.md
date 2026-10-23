# Changelog

All notable changes to the **ArthaIQ** compensation intelligence platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-24

### 🚀 General Availability (GA) Official Release

ArthaIQ v1.0.0 represents the milestone culmination of Phases 0 through 14, delivering an evidence-backed, mathematically sound, privacy-first compensation intelligence and decision-support platform for India tech careers.

### Added
- **Calibrated Compensation Engine (PT1):**
  - Rung F Level 2 Conformal CatBoost quantile regression predicting guaranteed cash annual (`guaranteed_cash_annual` in nominal INR LPA) across tech role families (Software Engineering, Data, Machine Learning).
  - Split conformal prediction intervals delivering mathematically grounded 80% empirical coverage ([75.0%, 85.0%] acceptance window).
  - Group-conditional slice-adaptive conformal calibration with Empirical Bayes shrinkage (`EXP-13`), reducing cross-slice variance by 89.05% with +0.95% median width change.
- **Interactive Negotiation Scenario Modeler (PT4):**
  - Constrained monotonic counterfactual quantile inversion (`EXP-15`) allowing candidates to evaluate competing offers and trade-offs without lone numbers.
  - Gaussian copula multi-component joint dependency structure (`EXP-PGM-01r`) capturing realistic rank-correlations between base cash, equity grants, and variable bonuses (|Δρ| = 0.0388 <= 0.050) with sub-millisecond CPU simulation latency ($p_{95} = 0.86\text{ ms}$).
  - India New Tax Regime (Section 115BAC, Finance Act 2023/2024) take-home monthly net income calculator.
- **Evidence Grading & Principled Abstention:**
  - Decoupled two-dimensional evidence framework: Source Provenance (Tiers A-D, SQSF scoring) and Prediction Support ($S_1-S_5$).
  - Principled abstention on thin realization cells; zero fabricated or point-estimate numbers (`R-UQ-01`).
  - Compare-only quarantine for current compensation (`R-MD-13`) to eliminate anchoring bias.
- **Enterprise B2B Syndication Protocol (`SRC-B2B-01`):**
  - Bilateral enterprise employer compensation intake protocol with cryptographic HMAC-SHA256 tenant token isolation.
  - Differential privacy small-cell aggregation engine (`B2BPrivacyPooler`) enforcing $k_{\min} \ge 5$ anonymity floor (`R-DA-10`), ₹50,000 INR wage coarsening, and quarterly date coarsening (`YYYY-Q#`).
  - Competition Commission of India (CCI) wage benchmarking safe harbor compliance ($\ge 5$ distinct employers, $\le 35.0\%$ maximum single-tenant share, $\ge 3$ months historical lag).
  - Automated scrubbing of 18 forbidden direct PII keys (Aadhaar, PAN, phone, names, emails, bank accounts).
  - Deductive accounting identity validation (`guaranteed_cash == basic + allowances`).
- **Privacy-First Data Architecture & DPDPA 2023 Compliance:**
  - Zero server-side PII storage, user accounts, or tracking.
  - Granular, unbundled voluntary contribution consent with cryptographic receipt tokens.
  - Self-contained client-side data inspection and local erasure cascades.
  - DPDPA 2023 Statutory Impact Assessment and Privacy Notice.
- **Frontend Design & Accessibility:**
  - Custom design tokens: "The Span" (cobalt on cool paper with blue-black ink, IBM Plex typography).
  - 100% WCAG 2.2 AA compliant with zero axe accessibility violations.
  - High-contrast dark mode and light mode with accessible SVG data visualizations.
  - 7 high-resolution screenshots with comprehensive tour embedded in `README.md`.
- **Pre-Registered Future Modeling Charters:**
  - `CHARTER-EXP-10r-v2`: Employer talent-flow mobility graph embeddings under dense B2B syndication panels (Rank 9).
  - `CHARTER-CAREER-TRAJ-r-v2`: Multi-period longitudinal career trajectory modeling (Rank 10).
  - Macro regime feature long-range calendar trigger pre-registered for October 2028.
- **Verification & Test Suite:**
  - 1,080+ automated Python unit, property, contract, and integration tests passing 100% green.
  - 96 frontend Vitest tests in `apps/web` passing 100% green.
  - 9 architectural import-linter contracts enforced.
  - Zero known CVEs in Python and Node dependency trees.

### Changed
- Production champion bundle updated to v1.0.0 with SliceAdaptiveConformalRegressor and dual-cadence freshness daemon support.
- Evidence register updated with 30 empirical claims with full provenance and validation logs.
- Document versions bumped to v1.0.0 General Availability.

---

## [0.9.0] - 2026-10-21
- Phase 9 Production API, Docker preview infrastructure, ASVS Level 2 security controls, and Fairness Audit v2.

## [0.6.0] - 2026-10-18
- Phases 3-6 Baseline benchmarks, Conformal CQR engine, and progressive personalization tiers L0-L2.

## [0.1.0] - 2026-10-13
- Phase 0-1 Document foundations, target specifications (PT1-PT6), source audit, and ADR-0001 to ADR-0009 stubs.
