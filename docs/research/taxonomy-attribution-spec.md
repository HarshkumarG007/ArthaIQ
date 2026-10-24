# Taxonomy Licence & Provenance Audit Specification

| Field | Value |
|---|---|
| Task ID | **T15.06** |
| Governing Rules | `R-CR-04` (Taxonomy Provenance), `R-EV-03` (Zero Fabrication), `R-DA-01` (Source Manifests) |
| Relates to | PRD v1.2 FR-21, ADR-0011, Claim 32 in `docs/research/evidence-register.csv` |
| Date | **2026-10-24** |
| Status | **Audited & Ratified** |

---

## 1. Executive Summary

ArthaIQ Career Architect ingests and models occupational competencies, task statements, and technical requirements to build capability roadmaps and realistic practice scenarios. To ensure complete intellectual property hygiene, eliminate legal exposure, and maintain transparent provenance, this specification audits external labour taxonomies and defines statutory attribution obligations across the API and frontend UI.

---

## 2. Taxonomy Licence Audit

### 2.1 O*NET 28.0 (U.S. Department of Labor / Employment and Training Administration)
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Audit Finding:** **Approved for Adaptation & Commercial Ingestion.**
  O*NET is licensed under CC BY 4.0. Users are free to share, copy, adapt, transform, and build upon the material for any purpose, provided appropriate credit is given, a link to the licence is provided, and any changes made are clearly indicated.
- **Trademark Notice:** "O*NET" is a registered trademark of the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA).
- **Mandatory Statutory Attribution Copy:**
  > "This product includes information from the O*NET 28.0 Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. O*NET® is a trademark of USDOL/ETA. ArthaIQ has modified all or some of this information. USDOL/ETA has not approved, endorsed, or tested these modifications."
- **Hyperlink:** `https://www.onetcenter.org/license.html`

### 2.2 ESCO v1.1.1 (European Commission)
- **Licence:** European Commission Open Reuse Policy (Commission Decision 2011/833/EU) / CC BY 4.0.
- **Audit Finding:** **Approved for Ingestion.**
  ESCO occupational profiles and transversal skills are published for free reuse with proper attribution.
- **Mandatory Statutory Attribution Copy:**
  > "This product uses the European Skills, Competences, Qualifications and Occupations (ESCO) classification of the European Commission. © European Union, 2024. Reused under the terms of the Commission Decision 2011/833/EU."
- **Hyperlink:** `https://ec.europa.eu/esco/portal`

### 2.3 National Qualifications Register (NQR / NCVET, India)
- **Licence / Terms:** Government of India National Council for Vocational Education and Training (NCVET).
- **Audit Finding:** **Restricted / Disqualified from Direct Database Redistribution.**
  India Qualification Packs (QPs) and National Occupational Standards (NOS) are copyrighted government regulatory curricula. While publicly readable, they lack an unencumbered CC BY or open-data reuse license for redistribution, automated API serialization, or commercial derivative compilation without a formal bilateral memorandum.
- **Operational Constraint:** ArthaIQ may reference NQR QP/NOS codes as non-executable regulatory reference mappings in documentation, but **must never** redistribute raw NQR qualification packs in production database seeds or API bundles.

---

## 3. Provenance Schema Contract

Every competency node in the ArthaIQ graph (`compintel.career.taxonomy`) must strictly validate against the following Pydantic schema:

```python
class TaxonomyProvenance(BaseModel):
    source_id: Literal["ONET-28.0", "ESCO-1.1.1", "ARTHAIQ-CURATED"]
    source_code: str  # e.g., "15-2051.01" or "S1.2.3"
    license: Literal["CC-BY-4.0", "EU-OPEN-REUSE", "PROPRIETARY-INTERNAL"]
    attribution_required: bool
    attribution_text: str
    modified_flag: bool
    curator: str
    curated_date: str  # YYYY-MM-DD
```

---

## 4. UI Attribution Component Specification

### 4.1 Component Placement
The frontend application (`apps/web`) must render a dedicated, accessible attribution component `TaxonomyAttribution.tsx`:
1. **Footer Anchor:** A persistent link in the footer of all `/career` views: `Data Sources & Taxonomy Attribution`.
2. **Accessible Dialog:** Clicking the anchor opens a modal (`role="dialog"`) rendering the verbatim statutory notices for O*NET and ESCO, alongside the CC BY 4.0 hyperlink.
3. **Card Micro-Badges:** When a user inspects a specific competency node in the roadmap or gap map, an unobtrusive info icon (`source: O*NET 28.0 (adapted)`) links directly to the provenance drawer.

### 4.2 Accessibility & Contract Checks
- Must have 0 `axe-core` accessibility violations.
- Must support keyboard navigation (`Tab`, `Escape` to close).
- Contrast ratio must meet WCAG AAA ($\ge 7.0:1$) in light and dark modes.
