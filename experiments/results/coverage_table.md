# Cell Coverage Map & Sufficiency Audit (Task T2.07)

| Dimension | Total Defined Cells | Passing C1 Floor | Coverage % | Status |
|:---|:---:|:---:|:---:|:---|
| **Core Cells** (Tier-1 Tech Hubs) | 12 | 0 | 0.0% | FAIL (Kill Criterion 1) |
| **Extended Cells** (Tier-2 & Rare Bands) | 72 | 0 | 0.0% | ABSTENTION_ZONE |
| **All Level-0 Cells** | 84 | 0 | 0.0% | HALT -> T2.10 |

---

## 1. Core Cells Audit (Kill Criterion 1 Evaluation)

| Cell ID | Role Family | Location | Seniority | N_raw | N_eff | SQS Avg | C1 (>=50) | C2 Floor | C3 Recency | Grade |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `SWE.BLR.JR` | SWE | BLR | JR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `SWE.BLR.MID` | SWE | BLR | MID | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `SWE.BLR.SR` | SWE | BLR | SR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `SWE.HYD.MID` | SWE | HYD | MID | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `SWE.HYD.SR` | SWE | HYD | SR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `SWE.NCR.MID` | SWE | NCR | MID | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `SWE.NCR.SR` | SWE | NCR | SR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `DATA.BLR.MID` | DATA | BLR | MID | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `DATA.BLR.SR` | DATA | BLR | SR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `MLAI.BLR.SR` | MLAI | BLR | SR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `MLAI.HYD.SR` | MLAI | HYD | SR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |
| `MLAI.NCR.SR` | MLAI | NCR | SR | 0 | 0.0 | 0.0 | FAIL | FAIL | FAIL | `ABSTAINED` |

---

## 2. Empirical Exploratory Survey Density Audit (Diagnostic)

Public developer survey samples (Stack Overflow 2023 & 2024, ai-jobs) were audited to assess available observations in the wild:

- **Total Indian Tech Respondents Audited:** ~170 survey observations.
- **Geographic Granularity Barrier:** Global developer surveys record `Country = India` without city-level tags. 100% of respondents map to `OTHER`.
- **Tier-1 Hub Density:** `BLR = 0`, `HYD = 0`, `NCR = 0` in public survey microdata.
- **Measure Conflation Barrier:** Survey compensation (`CompTotal`) is self-reported aggregate total compensation conflating variable pay and equity (`R-MD-07`).

| Family | Location | Seniority | Exploratory Survey Count | Direct PT1 N_eff | Deficit to Floor |
|:---|:---:|:---:|:---:|:---:|:---:|
| SWE | BLR | JR | 0 | 0.0 | -50 |
| SWE | BLR | MID | 0 | 0.0 | -50 |
| SWE | BLR | SR | 0 | 0.0 | -50 |
| SWE | HYD | MID | 0 | 0.0 | -50 |
| SWE | HYD | SR | 0 | 0.0 | -50 |
| SWE | NCR | MID | 0 | 0.0 | -50 |
| SWE | NCR | SR | 0 | 0.0 | -50 |
| DATA | BLR | MID | 0 | 0.0 | -50 |
| DATA | BLR | SR | 0 | 0.0 | -50 |
| MLAI | BLR | SR | 0 | 0.0 | -50 |
| MLAI | HYD | SR | 0 | 0.0 | -50 |
| MLAI | NCR | SR | 0 | 0.0 | -50 |

---

## 3. Pre-Registration Verdict

> [!CAUTION]
> **KILL CRITERION 1 TRIGGERED:** N_eff < 50 for all 12 core cells.
> Per `sufficiency-v1.yaml` Section 9 and `rules.md` R-WF-01 / R-EV-07, all machine learning modelling is HALTED.
> The project MUST pivot directly to **Task T2.10** to design the primary data acquisition programme (ArthaIQ voluntary intake & enterprise partnerships).
