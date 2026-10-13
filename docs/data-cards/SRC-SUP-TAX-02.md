# Data Card: ESCO Skills Classification v1.1

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-SUP-TAX-02` |
| **Document ID** | `docs/data-cards/SRC-SUP-TAX-02.md` |
| **Short Name** | ESCO Skills Taxonomy v1.1 |
| **Long Name** | European Skills, Competences, Qualifications and Occupations (ESCO) v1.1.1 |
| **Provider** | Directorate-General for Employment, Social Affairs and Inclusion, European Commission |
| **Primary URL** | https://esco.ec.europa.eu/ |
| **Licence** | European Commission Open Data (`ODbL-1.0` compatible) |
| **SQS / Tier** | **79.8** / `TIER_4_SUPPLEMENTARY` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Supplementary Taxonomy (Skill Hierarchy Graph & Distance Regularization) |
| **Prohibited Routing** | Wage observation tables |

---

## 1. Provenance, Licensing & Schema Profiling

* **Authority:** European Commission official multilinguistic classification of skills and occupations.
* **Licensing:** Open Data under European Commission Decision 2011/833/EU. Free commercial and research reuse with attribution.

Acquired under `data/raw/SRC-SUP-TAX-02/` with verified SHA-256 manifest:

### File: `esco_skills_tech_hierarchy.csv`
* Rows: 7 | Columns: 5 | Duplicate rows: 0 (Profiled sample slice)

| Column | Type | Null % | Example Values | Description |
|:---|:---:|:---:|:---|:---|
| `concept_uri` | String | 0.0% | `http://data.europa.eu/esco/skill/..` | Persistent semantic URI |
| `skill_label` | String | 0.0% | "Python (computer programming)" | Canonical skill name |
| `skill_type` | String | 0.0% | "knowledge", "skill/competence" | Skill ontology type |
| `reuse_level` | String | 0.0% | "sector-specific", "cross-sector" | Breadth of applicability |
| `parent_skill_group` | String | 0.0% | "Programming languages", "AI" | Parent hierarchy node |

---

## 2. Utility in ArthaIQ Modeling

* **Skill Graph Distance:** In Phase 4 feature engineering, the ESCO parent node hierarchy is used to compute graph distance between technical skills. For example, a candidate with Python and Go shares the `Programming languages` parent, while cloud computing and Kubernetes share `ICT infrastructure`, allowing regularized shrinkage priors across related tech stacks.
