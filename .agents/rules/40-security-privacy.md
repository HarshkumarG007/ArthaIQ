---
trigger: model_decision
description: Information security, OWASP ASVS standards, India DPDP Act 2023, and CCI antitrust safe harbors
---

# Security & Statutory Privacy Rules (R-SC, R-DA, R-FA)

Consult canonical specification in `docs/rules/40-security-privacy.md`.

## Key Invariants
1. **R-SC-01:** 100% compliance with OWASP ASVS v4.0.3 Level 1 controls.
2. **R-SC-02:** Zero hardcoded secrets, keys, or salts in Git. Automated secret scanning in CI.
3. **R-SC-03:** Clean `pip-audit` (0 CVEs) and clean `npm audit` before merge.
4. **R-SC-07:** Absolute prohibition on runtime LLM on serving path without formal ADR.
5. **R-DA-07:** Direct PII (Aadhaar, PAN, phone, email, names, bank accounts) permanently barred.
6. **R-DA-10:** Small-cell anonymity floor: suppress any aggregate with $< k_{\min} = 5$ persons.
7. **R-FA-01:** Decision support only; candidate ranking and screening strictly prohibited.
8. **R-FA-02:** Demographic attributes (gender, caste, religion, age) permanently banned.
9. **R-FA-04:** Current pay quarantined to `COMPARE_ONLY` to dismantle historical anchoring.
10. **Statutory Standards:** India DPDP Act 2023 18+ declaration, local erasure, CCI anti-collusion safe harbors (>= 5 employers, <= 35% share, >= 3 months lag, ₹50k coarsening).
