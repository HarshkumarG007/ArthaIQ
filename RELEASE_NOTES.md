# ArthaIQ v1.0.0 — General Availability (GA) Release

**Release Date:** October 24, 2026  
**License:** Apache 2.0  
**Status:** Production Ready / General Availability  

ArthaIQ is an ethical, evidence-backed compensation intelligence and decision-support platform designed specifically for tech professionals in India. Version 1.0.0 marks the completion of the 15-phase foundational engineering and governance roadmap (Phases 0 through 14).

---

## 🌟 What's Inside ArthaIQ v1.0.0

### 1. Calibrated Quantile Pay Prediction
- **True Guaranteed Cash (PT1):** Predicts guaranteed cash annual (`guaranteed_cash_annual` in nominal INR LPA) unbundled from opaque CTC gimmicks.
- **Conformal Uncertainty Intervals:** Provides 80% coverage intervals with zero lone salary numbers.
- **Slice-Adaptive Shrinkage (EXP-13):** Eliminates coverage gaps across experience tiers and roles using Empirical Bayes calibration.
- **Principled Abstention:** Explicitly abstains on thin realization cells rather than fabricating inaccurate point estimates.

### 2. Interactive Negotiation Scenario Modeler (PT4)
- **Monotonic Counterfactuals (EXP-15):** Model trade-offs across competing offers and salary components without heuristic multipliers.
- **Gaussian Copula Correlation (EXP-PGM-01r):** Captures realistic joint dependencies between base cash, equity grants, and variable bonuses.
- **Indian Tax Computation (Section 115BAC):** Instant take-home monthly cash estimates under the New Tax Regime.

### 3. Enterprise B2B Syndication & Differential Privacy (`SRC-B2B-01`)
- **Cryptographic Tenant Isolation:** HMAC-SHA256 salted tokens guarantee zero cross-tenant linkage.
- **Small-Cell Aggregation Floor ($k_{\min} \ge 5$):** Prevents individual identification in compensation reporting cohorts.
- **CCI Wage Benchmarking Safe Harbor:** Multi-employer pooling, $\le 35.0\%$ concentration cap, and $\ge 3$ months historical lag ensure complete anti-trust compliance.
- **Deductive Accounting Validation:** Enforces `guaranteed_cash == basic + fixed_allowances`.

### 4. Privacy-First by Design (DPDPA 2023)
- **Zero Server-Side User Accounts:** No personal identities, emails, or phone numbers are stored on servers.
- **Granular Consent & Receipts:** Cryptographic receipt tokens accompany all voluntary submissions.
- **Client-Side Data Management:** Full local data inspection and single-click erasure cascades.

### 5. Premium Accessible Web Dashboard
- **"The Span" Design System:** Cobalt on cool paper with blue-black ink, paired with IBM Plex Sans and IBM Plex Serif.
- **100% WCAG 2.2 AA Compliance:** Screen-reader accessible SVG distributions and zero axe violations.
- **Dual Theme Support:** High-contrast light and dark modes.

---

## 🧪 Verification & Quality Benchmarks

- **Automated Tests:** 1,080+ Python tests and 96 frontend Vitest tests passing 100% green.
- **Security Audit:** 0 known CVEs (`pip-audit`), 0 hardcoded secrets (Gitleaks clean), Bandit SAST clean, OWASP ASVS Level 2 verified.
- **Performance:** Sub-5ms API inference latency ($p_{95} = 4.32\text{ ms}$), 0.136ms rollback capability.
- **Reproducibility:** 100% deterministic bitwise pipeline reproduction (`make reproduce-data`).

---

## 📦 Installation & Quickstart

```bash
# Clone the repository
git clone https://github.com/HarshkumarG007/ArthaIQ.git
cd ArthaIQ

# Install Python environment with uv
uv sync

# Run tests
uv run pytest tests/

# Launch backend API
uv run uvicorn compintel.serving.app:app --host 0.0.0.0 --port 8000

# Launch frontend web app
cd apps/web
npm install
npm run dev
```
