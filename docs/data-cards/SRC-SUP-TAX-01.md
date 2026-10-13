# Data Card: O*NET 29.0 Content Model (Occupations & Technology Skills Taxonomy)

| Field | Value |
|:---|:---|
| **Source ID** | `SRC-SUP-TAX-01` |
| **Document ID** | `docs/data-cards/SRC-SUP-TAX-01.md` |
| **Short Name** | O*NET 29.0 Database |
| **Long Name** | Occupational Information Network (O*NET) 29.0 Content Model Database |
| **Provider** | U.S. Department of Labor / ETA / National Center for O*NET Development |
| **Primary URL** | https://www.onetcenter.org/database.html |
| **Licence** | Creative Commons Attribution 4.0 International (`CC-BY-4.0`) |
| **SQS / Tier** | **84.4** / `TIER_4_SUPPLEMENTARY` |
| **Ingestion Status** | `approved` |
| **Assigned Role** | Supplementary Taxonomy (Canonical Skill Entity Resolution & SOC Crosswalks) |
| **Prohibited Routing** | Wage observation tables (Non-wage dataset) |

---

## 1. Provenance, Authority & Legal Terms

* **Authority:** Administered by the National Center for O*NET Development under USDOL / ETA grant.
* **Licensing:** Licensed under `CC-BY 4.0`. Commercial and non-commercial reuse, transformation, and distribution permitted with attribution to O*NET and USDOL.
* **Personal Data:** None. Pure taxonomy and occupational characteristics.

---

## 2. Dataset Schema & Column Profiling

Acquired under `data/raw/SRC-SUP-TAX-01/` with verified SHA-256 manifest:

### 2.1 File: `occupation_data_tech.csv`
* Rows: 6 | Columns: 3 | Duplicate rows: 0

| Column | Type | Null % | Description |
|:---|:---:|:---:|:---|
| `onetsoc_code` | String | 0.0% | Standard O*NET-SOC code (e.g. `15-1252.00` Software Developers) |
| `title` | String | 0.0% | Standardized occupational title |
| `description` | String | 0.0% | Official job description and summary scope |

### 2.2 File: `technology_skills_tech_roles.csv`
* Rows: 13 | Columns: 5 | Duplicate rows: 0 (Profiled sample slice)

| Column | Type | Null % | Description |
|:---|:---:|:---:|:---|
| `onetsoc_code` | String | 0.0% | Associated O*NET-SOC code |
| `commodity_code` | Int64 | 0.0% | UNSPSC commodity classification code |
| `commodity_title` | String | 0.0% | Category (e.g. "Development software", "Database management") |
| `example_tool` | String | 0.0% | Specific technology tool (Python, Docker, AWS, Kubernetes, etc.) |
| `hot_technology` | String | 0.0% | Flag indicating high industry demand ('Y') |

---

## 3. Utility in ArthaIQ Pipelines

1. **Unstructured Skill Normalization:** Normalizes raw free-text tech skills reported by users or in survey datasets to canonical technology entities (`example_tool`).
2. **Crosswalk Ontology:** Bridges US SOC codes (`15-1252`), Indian NCO codes (`2512`), and ArthaIQ internal role families (`software_engineering`, `data_engineering`, `machine_learning`).
