# User Persona Hypotheses, Jobs-to-be-Done & Interview Protocol (T1.03)

| Field | Value |
|:---|:---|
| **Document ID** | `docs/research/03-users.md` |
| **Task** | T1.03 — Write persona hypotheses, jobs to be done, and interview guide |
| **Status** | Complete v1.0 |
| **Date** | 2026-10-13 |
| **Governs** | User Research Synthesis (`T1.04`), PRD Personas (`PRD.md` Section 3), UX Design Requirements (`design.md`) |
| **Methodological Invariant** | User personas are hypotheses until tested against real qualitative interviews (`T1.04`). We design for real cognitive frictions, CTC unbundling confusions, and power asymmetries in Indian tech careers. |

---

## 1. Executive Summary & Research Mandate

In the Indian technology job market, compensation negotiations and career decisions take place under extreme **information asymmetry**. While employers possess aggregated payroll benchmarks, recruiter intelligence, and rigid compensation bands, job seekers and employees rely on:
1. Fragmented social chatter (Reddit `r/developersIndia`, Blind, Fishbowl, WhatsApp/Telegram groups) dominated by self-selected top-percentile anomalies;
2. Scraped review aggregators (AmbitionBox, Glassdoor) reporting unbundled, stale, or generic averages that conflate IT service sweatshops with Tier-1 product multinationals; and
3. Opaque HR offer breakdowns that disguise low fixed cash behind inflated headline Cost to Company (CTC) figures.

**Task T1.03** formalizes our foundational hypotheses regarding who ArthaIQ serves, what decisions they are trying to make, and how we will rigorously validate these assumptions through empirical user interviews in **Task T1.04**.

---

## 2. Persona Hypotheses

We hypothesize four primary user personas across the Indian technology employment landscape:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              ARTHAIQ PERSONA HYPOTHESES                                │
│                                                                                        │
│  [PRIMARY PERSONA]                                                                     │
│  P1: The Offer Evaluator (Mid-level SDE / Data Scientist, 3–7 YOE)                     │
│      Context: Actively holding 1–2 offers; trying to decipher CTC and counter-offer.   │
│                                                                                        │
│  [SECONDARY PERSONA]                                                                   │
│  P2: The Market Check / Appraisal Preparer (Senior Engineer, 7–12 YOE)                 │
│      Context: Pre-appraisal cycle or retention discussion; benchmarking parity.        │
│                                                                                        │
│  [TRANSITION PERSONA]                                                                  │
│  P3: The Service-to-Product / Stack Transitioner (Junior to Mid, 2–6 YOE)              │
│      Context: Moving from legacy IT services (TCS/Wipro) to GCC or product startup.    │
│                                                                                        │
│  [INSTITUTIONAL / LEADERSHIP PERSONA]                                                  │
│  P4: The Hiring Lead / Engineering Manager (10+ YOE)                                   │
│      Context: Structuring fair offer bands within team budget; reducing attrition.     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Persona P1: The Offer Evaluator (Primary Persona)

* **Archetype:** *"Aditya / Sneha" — Mid-Level Software Engineer II / Data Scientist*
* **Demographics & Profile:**
  - **Experience:** 3.5 to 6 years of relevant experience ($YOE$).
  - **Location:** Bengaluru (HSR Layout / Outer Ring Road) or Hyderabad (HITEC City).
  - **Current Compensation:** ₹14.0 LPA CTC (₹11.5 LPA Guaranteed Cash).
  - **Education:** B.Tech from Tier-2 / Tier-3 engineering college.
  - **Target Roles:** SDE-2 (Backend, Distributed Systems, ML Engineering).
* **Current Situation & Trigger Event:**
  - Has just received an offer from a mid-market product company or Global Capability Center (GCC) stating **"CTC: ₹24.0 LPA"**.
  - Wondering: *"How much of this ₹24 LPA is actually guaranteed cash hitting my bank account, and is this at the 25th, 50th, or 80th percentile for 4 YOE in Bengaluru?"*
* **Key Pain Points:**
  - **The CTC Deception:** The offer includes ₹3.0 LPA performance bonus (variable), ₹1.2 LPA employer PF/gratuity, and ₹4.0 LPA ESOPs (vesting over 4 years with a 1-year cliff). Real guaranteed fixed cash is only ₹15.8 LPA.
  - **The Single-Number Fallacy:** Glassdoor states "Average SDE-2 Salary: ₹18 LPA", which gives no visibility into the spread between IT service firms (₹8–₹12 LPA) and Tier-1 product firms (₹24–₹38 LPA).
  - **Fear of Leaving Money on the Table:** Paralyzed between accepting immediately and risking the offer by asking for ₹18 LPA fixed cash.
* **Psychological State:** Anxious, skeptical of HR explanations, overwhelmed by anecdotal flexes on social media.

---

### Persona P2: The Appraisal Preparer / Market Checker

* **Archetype:** *"Rohan" — Senior Backend / Platform Engineer*
* **Demographics & Profile:**
  - **Experience:** 8 to 11 years of experience ($YOE$).
  - **Location:** Pune (Hinjawadi / Magarpatta) or Gurgaon (Cyber City).
  - **Current Compensation:** ₹28.0 LPA Guaranteed Cash + ₹4.0 LPA Annual Bonus.
  - **Employer Type:** Established European GCC or Indian Unicorn.
* **Current Situation & Trigger Event:**
  - Annual appraisal cycle is 6 weeks away. Suspects internal compensation has stagnated compared to fresh market hires.
  - Wondering: *"Has market compensation for 9 YOE in Pune moved up to ₹38 LPA, or is my current ₹28 LPA still competitive?"*
* **Key Pain Points:**
  - **Lack of Objective Benchmark Evidence:** Has to negotiate against an engineering director armed with corporate Radford/Aon salary survey data that employees cannot see.
  - **Risk of Overplaying Hand:** Threatening to resign without knowing whether the broader market will actually clear at higher pay.
  - **Senior Band Dispersion:** Senior pay variance is huge ($P_{10} = ₹22\ \text{LPA}$, $P_{90} = ₹55+\ \text{LPA}$). Needs to know where his tech stack (Go/Kubernetes/Kafka) positions him.

---

### Persona P3: The Service-to-Product Transitioner

* **Archetype:** *"Pooja" — Software Engineer transitioning out of IT Services*
* **Demographics & Profile:**
  - **Experience:** 3 to 5 years of experience ($YOE$).
  - **Location:** Chennai or Hyderabad.
  - **Current Employer:** Top-5 IT Services firm (TCS, Infosys, Wipro, Cognizant, Accenture).
  - **Current Compensation:** ₹6.5 LPA CTC (₹5.2 LPA Guaranteed Cash).
  - **Skills:** Java, Spring Boot, SQL, currently self-learning AWS and microservices.
* **Current Situation & Trigger Event:**
  - Actively interviewing with GCCs, product startups, and tech boutiques to break out of legacy service pay brackets.
* **Key Pain Points:**
  - **The "Previous CTC Anchor" Trap:** Recruiters demand current payslips and attempt to cap offers at a standard "30% hike on current fixed pay" (offering ₹6.8 LPA fixed), even though standard entry-level pay for the target role is ₹14.0 LPA.
  - **Legitimate Market Floor Ignorance:** Does not know what the justifiable 25th percentile ($P_{25}$) fixed cash is for product engineering roles, making it hard to counter lowball anchoring.
* **Psychological State:** Eager for upward mobility, vulnerable to aggressive recruiter anchoring, determined to validate legitimate market parity.

---

### Persona P4: The Engineering Manager / Team Lead

* **Archetype:** *"Karthik" — Engineering Manager / Tech Lead*
* **Demographics & Profile:**
  - **Experience:** 12 to 16 years ($YOE$).
  - **Location:** Bengaluru.
  - **Team Scope:** Manages 8–14 software engineers and data scientists.
* **Current Situation & Trigger Event:**
  - Preparing internal compensation adjustment proposals for budget reviews and structuring offer packages for 3 open requisitions.
* **Key Pain Points:**
  - **Attrition Blind Spots:** Team members leaving for competitor offers without leadership understanding market shifts.
  - **Internal Pay Disparity:** Managing friction between legacy employees on older bands and new external hires brought in at current market rates.
  - **Radford/Mercer OOD (Out-of-Date) Lag:** Corporate compensation survey reports lag dynamic tech market realities by 9 to 15 months.

---

## 3. Jobs-to-be-Done (JTBD) Framework

Using the standard Christensen / Ulwick Jobs-to-be-Done methodology, we define the core functional, emotional, and social jobs:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              CORE FUNCTIONAL & EMOTIONAL JOBS                          │
│                                                                                        │
│  1. Unbundle the Offer: Dissect a multi-component CTC package into verified guaranteed │
│     pre-tax annual cash and isolate speculative components.                            │
│                                                                                        │
│  2. Calibrate Market Position: Determine where a profile sits within the empirical    │
│     distribution (P10, P50, P90) conditional on role, YOE, stack, and city.            │
│                                                                                        │
│  3. Defend Counter-Offers: Obtain objective, evidence-backed distribution spans to     │
│     counter recruiter lowball anchors without emotional conjecture.                    │
│                                                                                        │
│  4. Evaluate Career Upside: Assess realistic compensation deltas before investing in  │
│     role transitions, stack upskilling, or city relocations.                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Job Statements:

| Persona | Trigger / Situation | Motivation / Action | Desired Outcome | Primary Target |
|:---|:---|:---|:---|:---:|
| **P1** | **When I** receive an offer letter with an impressive but confusing CTC headline, | **I want to** unbundle it into guaranteed annual cash and compare it to real conditional percentiles ($P_{10}, P_{50}, P_{90}$), | **So that I can** confidently accept, negotiate a specific counter-offer, or reject without regret. | **PT1, PT6** |
| **P2** | **When I** prepare for my annual appraisal or discuss promotion compensation with my director, | **I want to** benchmark my current pay against verified senior cohort distributions, | **So that I can** state an evidence-backed case for salary realignment backed by market realities. | **PT6, PT2** |
| **P3** | **When I** interview for my first product-company or GCC role coming from IT services, | **I want to** know the market floor ($P_{10}$–$P_{25}$) for the role rather than accepting a flat 30% hike on my depressed baseline, | **So that I can** break free from previous salary anchoring and claim market parity. | **PT1, PT4** |
| **P4** | **When I** review salary bands for my engineering team or extend offers to candidates, | **I want to** inspect calibrated market spans and inter-quartile ranges across skill specializations, | **So that I can** maintain equitable internal parity and prevent costly resignations. | **PT1, PT2** |

---

## 4. Recruiting Criteria & Sampling Matrix for Human Interviews (`T1.04`)

To ensure empirical validity in Task **T1.04**, user interviews must be recruited across a balanced quota matrix rather than convenient peer sampling:

### 4.1 Sample Size & Quota Distribution ($N = 10 \pm 2$)

| Dimension | Target Allocation | Quota Minimum | Rationale |
|:---|:---:|:---:|:---|
| **Experience ($YOE$)** | 1–3 YOE: 2 participants<br>3–7 YOE: 5 participants<br>7–12 YOE: 3 participants<br>12+ YOE: 2 participants | $\ge 2$ in each bracket | Captures the transition from fresher anchoring to senior equity dispersion. |
| **Employer Tier** | Tier-1 Product / FAANG: 3<br>GCC / Tech Captive: 4<br>Mid-Market / High-Growth Startup: 3<br>IT Services / System Integrator: 2 | $\ge 2$ in each tier | Tests how unbundling pain points differ between services (pure cash) and product (RSUs/bonuses). |
| **Role Specialization** | Backend / Fullstack Software Engineering: 6<br>Data Science / Analytics: 3<br>ML / AI Engineering: 3 | $\ge 3$ Data/ML roles | Validates whether ML practitioners experience unique compensation premiums. |
| **Metro Hub** | Bengaluru: 6<br>Hyderabad: 3<br>Pune / NCR / Chennai: 3 | $\ge 6$ outside BLR | Checks whether non-Bengaluru tech workers face distinct regional discount anxieties. |

### 4.2 Candidate Screener Questions
1. *"Are you currently employed as a software engineer, data scientist, or ML engineer in India?"* (Must be YES).
2. *"Have you evaluated a new job offer or gone through an internal compensation review within the past 18 months?"* (Must be YES).
3. *"Does your current or recent compensation package include more than one component (e.g. basic, allowances, bonus, PF, equity)?"* (Must be YES).

---

## 5. Semi-Structured User Interview Protocol (45 Minutes)

### Pre-Interview Consent & Privacy Briefing (2 mins)
> *"Hello [Name], thank you for joining. We are conducting research into how technology professionals in India navigate compensation, offer evaluations, and career decisions. Your responses will be completely anonymized under strict academic and research standards. No company names, individual identities, or proprietary details will be publicly shared. We do not ask for confidential employer trade secrets. Are you comfortable if we record audio notes for internal synthesis?"*

---

### Section 1: Professional Background & Career Context (5 mins)
1. Tell me briefly about your current role, your years of experience, and the kinds of technical problems you solve daily.
2. In what type of organization do you currently work (Product MNC, GCC, Startup, or IT Services)?
3. How many times have you switched employers or negotiated an internal compensation adjustment in your career?

---

### Section 2: Compensation Discovery & Information Channels (10 mins)
1. When you want to find out what someone with your skills and experience is worth in the market, **where do you look first?**
2. What platforms or sources have you used (e.g., Glassdoor, AmbitionBox, Levels.fyi, Reddit `r/developersIndia`, Blind, peer conversations)?
3. **What frustrates you the most about these sources?**
   - *Probe:* Have you ever encountered salary figures that seemed completely unrealistic or misleading? Why?
   - *Probe:* How do you distinguish between what people claim on social media and what real companies actually pay?

---

### Section 3: The Offer & CTC Breakdown Experience (15 mins)
1. Walk me through your most recent job offer or promotion letter. **When you opened the document, what was the headline figure, and how was it broken down?**
2. Did the offer letter differentiate between fixed cash and variable pay?
   - *Probe:* What percentage of the headline CTC was contractually guaranteed monthly cash?
   - *Probe:* Did the employer include employer Provident Fund (12%), gratuity, insurance, or joining bonus in the headline number?
3. How did you figure out your actual **monthly in-hand take-home pay** from that offer? Did you use online calculators, Excel, or ask a friend?
4. **Negotiation Dynamics:**
   - Did the recruiter ask for your current salary slips or previous CTC before making an offer?
   - How did that anchor affect your final offer? Did you attempt to negotiate, and what evidence did you use to justify your number?

---

### Section 4: Testing the ArthaIQ Concept & "The Span" (10 mins)
*(Interviewer presents a conceptual representation of The Span: an editorial card displaying conditional quantiles $P_{10}, P_{50}, P_{90}$ with an explicit evidence confidence rating and an abstention explanation).*

1. If an intelligent tool asked you for your role, experience, tech stack, and city, and returned a **calibrated span (e.g., $P_{10} = ₹16\ \text{LPA}$, $P_{50} = ₹22\ \text{LPA}$, $P_{90} = ₹31\ \text{LPA}$ guaranteed cash)** rather than a single average number:
   - How would you interpret that range?
   - What would you do with that information?
2. Notice that the number strictly measures **annual guaranteed cash**, deliberately excluding variable bonuses and equity. Is that clear, and does that help or hinder your evaluation?
3. How would you feel if the system told you: *"We do not have sufficient statistically verified evidence for 7 YOE Rust developers in Pune, so we abstain from giving an estimate rather than guessing"*?
   - Would that increase or decrease your trust in the tool?

---

### Section 5: Wrap-Up & Closing (3 mins)
1. If you had a magic wand and could change one thing about how tech salaries are disclosed and negotiated in India, what would it be?
2. Do you have any questions for us?

---

## 6. Interview Synthesis & PRD Validation Framework

Findings from Task **T1.04** will be synthesized into `docs/research/03-users.md` using the following scoring rubric to confirm or revise PRD requirements:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              HYPOTHESIS VALIDATION RUBRIC                              │
│                                                                                        │
│  H-U01: CTC Unbundling Friction                                                        │
│  • Hypothesis: >75% of candidates find CTC breakdowns confusing and struggle to        │
│    isolate guaranteed fixed cash from bonuses and statutory PF reserves.               │
│                                                                                        │
│  H-U02: Single-Number Distrust                                                         │
│  • Hypothesis: >80% of candidates distrust Glassdoor/AmbitionBox averages and prefer   │
│    an empirical spread (P10–P90) reflecting employer tier variance.                    │
│                                                                                        │
│  H-U03: Recruiter Lowball Anchoring                                                    │
│  • Hypothesis: Candidates from IT services (P3) face severe 30% hike ceiling traps     │
│    and lack objective distribution evidence to demand role parity.                     │
│                                                                                        │
│  H-U04: Abstention Value                                                               │
│  • Hypothesis: Honest abstention increases perceived technical credibility compared to │
│    generic tools that invent synthetic guesses for thin slices.                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

*Authored for ArthaIQ under Phase 1, Task T1.03.*
