# Master Research Prompt — Hyper-Realistic Personalized Salary Prediction System

> Saved from the originating prompt that generated the six v0.1 documents.
> Committed as part of T0.01 on 2026-10-13.

---

## 0. Mission and Operating Mode

Act as an integrated research and engineering team consisting of:

- A principal machine learning researcher.
- A labor economist and compensation analytics specialist.
- A senior data engineer.
- A statistician specializing in probabilistic prediction and uncertainty quantification.
- An applied NLP and representation-learning researcher.
- A quantitative financial modeler specializing in compensation and equity.
- An MLOps and production systems architect.
- A data governance, privacy, fairness, and model-risk specialist.
- An adversarial reviewer responsible for finding flaws in every proposed design decision.

Your mission is to research, evaluate, design, and specify the strongest practically achievable personalized salary prediction system that can be implemented with currently available data, technology, budget, and computational resources.

Use the following operating principles:

**THINK 10X:** Search for meaningful improvements across the entire system, including data quality, target definition, statistical modeling, personalization, evaluation, deployment, and user experience.

**AUTOPSY:** Identify hidden assumptions, data weaknesses, methodological errors, and failure modes in every proposed component.

**PREMORTEM:** Assume the project failed after deployment. Determine the most plausible reasons and design safeguards before implementation.

**BEASTMODE:** Investigate advanced statistical, machine learning, data engineering, NLP, and simulation methods, but retain only methods that are feasible and justified by evidence.

**KILL CRITIC:** Challenge the project's assumptions. Actively seek evidence that contradicts preferred approaches. Do not agree with the user merely to be helpful.

**SCIENTIFIC RIGOR:** Distinguish established facts, empirical observations, hypotheses, engineering judgments, and unverified assumptions.

**RESOURCE AWARENESS:** Optimize for predictive performance, reliability, cost, latency, maintainability, and available computational capacity rather than architectural complexity.

**REALITY FIRST:** Never promise perfect accuracy, universal coverage, causal conclusions, or guaranteed salary outcomes. Explicitly describe what the data cannot identify.

Do not begin by writing code. Begin with research, data feasibility analysis, target definition, competing hypotheses, and a falsifiable evaluation plan.

---

## 1. Project Objective

I want to develop an advanced AI/ML-powered salary prediction and compensation intelligence platform.

The system must estimate a person's realistic compensation using all relevant, legally obtainable, empirically defensible information available at prediction time.

It must be personalized rather than merely returning a generic salary average for a job title.

It should progressively refine its estimates as users provide more useful information, while preserving uncertainty when information is missing or unreliable.

The ultimate objective is to maximize out-of-sample predictive reliability and practical usefulness, not to maximize the number of features, model parameters, technologies, or lines of code.

The system should be capable of expanding across countries, industries, occupations, career levels, employment arrangements, and compensation structures. However, do not assume that one model can reliably support every market from the beginning.

First identify the most defensible initial market and use case. Recommend a different scope if evidence shows that the proposed scope is infeasible.

Distinguish at least these prediction targets:

- Market compensation for a given role and candidate profile.
- Compensation associated with comparable employees and job opportunities.
- The distribution of plausible offers a candidate might receive during a defined job search.
- Expected compensation under explicitly stated negotiation scenarios.
- Potential compensation following a career transition or skill-development scenario.
- Comparison of current compensation against relevant market benchmarks.

Do not treat these as interchangeable prediction tasks. Specify the target variable, observation unit, prediction horizon, and assumptions for each.

---

## 2. Research Protocol and Evidence Standards

Perform current web research using primary documentation, official statistical sources, peer-reviewed research, technical papers, maintained library documentation, dataset documentation, and credible empirical studies.

Verify that cited technologies, datasets, APIs, licenses, and methods remain available and applicable.

Prioritize sources in this order where appropriate:

1. Official government and regulatory data documentation.
2. Original research papers and peer-reviewed empirical studies.
3. Official library, API, and platform documentation.
4. Reputable research organizations and transparent data providers.
5. Credible industry reports with documented methodology.
6. Community-reported compensation data, with explicit selection-bias and measurement limitations.

Use community discussions to discover practical problems and candidate data sources, not as unquestioned evidence of population-wide salary patterns.

For every important claim, provide a source, publication or update date when available, a concise interpretation, and a description of the limitations.

Maintain an evidence register with these fields:

- Claim or design decision.
- Supporting source.
- Contradictory evidence.
- Evidence quality.
- Confidence level.
- Practical implication.
- Validation experiment required.

Separate verified facts from recommendations and hypotheses.

If a source cannot be verified, mark it unverified. Never invent dataset availability, sample sizes, prices, API capabilities, performance results, or experimental findings.

---

## 3. Critically Audit the Initial Architecture

Evaluate the following proposed approaches rather than automatically accepting them:

- A four-stage ingestion, feature engineering, hybrid modeling, and inference architecture.
- Quantile regression using LightGBM or CatBoost.
- Ordinal job-level classification.
- Sentence-transformer skill embeddings.
- Employer relationship graphs, PageRank, Node2Vec, and graph neural networks.
- Career progression and promotion-velocity features.
- Hierarchical Bayesian personalization.
- Conformal prediction intervals.
- SHAP explanations.
- Separate public-equity and private-company equity valuation.
- Negotiation and job-search scenario simulation.
- PostgreSQL, DuckDB, Parquet, Polars, FastAPI, and optional vector search.

For each proposed component, answer:

1. What exact problem does it solve?
2. What evidence supports its usefulness for salary prediction?
3. What data does it require?
4. What is the simplest credible alternative?
5. What computational and operational costs does it introduce?
6. How could it fail?
7. What experiment would determine whether it is worth keeping?
8. Under what conditions should it be rejected?

Do not introduce deep learning, graph neural networks, LLM-based feature extraction, vector databases, or distributed infrastructure merely because they are modern.

Prefer the least complex model that satisfies the required accuracy, calibration, latency, and maintainability constraints.

---

## 4. Data Source Discovery and Feasibility

Conduct a structured investigation of legally accessible compensation and labor-market datasets.

Investigate relevant sources, including but not limited to:

- Government wage and employment surveys.
- Occupational wage statistics.
- Regulatory wage disclosures.
- Public job postings with compensation ranges.
- Licensed salary survey providers.
- Publicly disclosed compensation information.
- Voluntarily contributed salary and offer records.
- Employer career pages and compensation bands.
- Company financial filings.
- Public economic indicators.
- Occupational and skill taxonomies.
- Publicly available career and skills datasets.
- Research datasets and benchmark datasets.

For an India-first implementation, explicitly investigate Periodic Labour Force Survey data, Ministry of Labour and Employment occupational wage sources, and other appropriate Indian labor-market data.

For a US implementation, investigate BLS occupational wage data and Department of Labor wage disclosures, alongside suitable compensation datasets.

Do not assume that a US-specific source generalizes to India or that official occupation statistics resolve individual technology-company compensation.

For each candidate source, document:

| Field | Description |
|---|---|
| Official URL and provider | Primary-source URL |
| Country and population covered | Scope |
| Occupations and industries covered | Coverage |
| Time span and update frequency | Freshness |
| Record-level vs. aggregated | Granularity |
| Available compensation fields | Fields |
| Sample size, if documented | Scale |
| Geographic and occupational resolution | Detail |
| Compensation type | Offered / accepted / reported / realized |
| Currency and pay-period definitions | Normalization |
| Missingness and duplicate risks | Quality |
| Selection and reporting bias | Bias |
| Licensing, access, commercial use | Licence |
| Collection and processing costs | Cost |
| Refresh feasibility | Freshness |
| Integration complexity | Effort |
| Likely contribution to each PT | Utility |

Classify each source as: ground-truth source · population benchmark · market signal · supplementary feature source · unsuitable.

Develop a source-quality scoring framework. Do not assume that all sources deserve equal weight.

Investigate whether the available evidence is sufficient to estimate the intended target before proposing advanced models.

If the data is insufficient, identify the smallest viable data acquisition or survey program that could close the gap.

Do not recommend unauthorized scraping or collection of personal data in violation of applicable law, terms, or privacy requirements.

---

## 5. Define Compensation Correctly

Design a canonical compensation schema.

At minimum, investigate the separate modeling of:

- Annual base salary.
- Guaranteed cash compensation.
- Target and realized performance bonuses.
- Commission and variable compensation.
- Sign-on bonuses.
- Recurring allowances.
- Benefits with defensible monetary valuation.
- Public-company equity grants and vesting.
- Private-company stock options and restricted equity.
- First-year compensation.
- Recurring annual compensation.
- Realized equity proceeds, where observable.
- Hourly, contract, and part-time compensation.

Clearly distinguish reported total compensation, annualized compensation, realized earnings, and expected future value.

Define consistent treatment for:

- Currency conversion.
- Nominal versus inflation-adjusted amounts.
- Annualization and working hours.
- Taxes and employer contributions.
- One-time versus recurring payments.
- Vesting schedules.
- Unvested equity.
- Equity volatility and liquidity.
- Missing compensation components.
- Outliers and inconsistent reports.

Never combine incomparable compensation measures without an explicit normalization policy.

For equity, investigate suitable methods for publicly traded shares, private-company options, private restricted stock, and uncertain liquidity outcomes.

Do not use Black–Scholes as a universal private-equity value estimator. Explicitly account for the fact that an option's theoretical value, a reported grant value, and realized employee proceeds are different quantities.

For private equity, investigate cap-table dilution, strike price, vesting, liquidation preferences, exercise costs, taxes, financing scenarios, liquidity probabilities, and exit outcomes where data supports them.

---

## 6. Model the Real-World Factors

Construct a structured feature taxonomy.

Investigate the following feature families.

### A. Role and Responsibility

- Occupation taxonomy.
- Job title normalization.
- Actual responsibilities and scope.
- Individual contributor versus management track.
- Seniority and standardized career level.
- Team, budget, and decision-making responsibility.
- Industry and business function.

### B. Experience and Career History

- Relevant versus total experience.
- Dated employment history.
- Promotions and level transitions.
- Scope of responsibility over time.
- Career breaks and employment gaps when relevant and lawfully used.
- Tenure patterns.
- Internal versus external transitions.
- Reliability of self-reported history.

### C. Skills and Demonstrated Capability

- Skill relevance to the target role.
- Skill depth and demonstrated proficiency.
- Project complexity and measurable outcomes.
- Specialized versus widely available skills.
- Complementary skill combinations.
- Recency of experience.
- Certifications and formal qualifications where relevant.
- Resume and project-text representations.
- Portfolio evidence quality.

Do not treat a keyword, certification, public repository, or embedding similarity score as direct proof of proficiency.

### D. Employer and Business Context

- Employer identity and size.
- Industry and business model.
- Company stage and financial circumstances.
- Compensation philosophy and pay bands.
- Hiring level and role scope.
- Public versus private ownership.
- Revenue, profitability, and capital availability when defensible.
- Employer compensation history.
- Relevant labor-market competition.

Investigate employer graphs only if representative data exists. Avoid turning prestige rankings into unexplained salary multipliers.

### E. Location and Work Arrangement

- Country, region, and city.
- Local labor-market conditions.
- On-site, hybrid, and remote work.
- Employer location versus worker location.
- Cross-border employment.
- Local salary norms.
- Inflation and currency conditions.
- Cost of living and purchasing power.

Keep nominal compensation, purchasing power, and local affordability as distinct outputs.

### F. Macroeconomic and Market Conditions

- Vacancy and hiring trends.
- Relevant occupation supply and demand.
- Sector-specific layoffs and expansions.
- Interest rates and investment conditions.
- Inflation.
- Currency fluctuations.
- Technology-sector hiring conditions.
- Changes in labor regulation.

Only use information that was available at the prediction timestamp.

### G. Transactional and Negotiation Context

- Competing offers.
- Recruiter-provided compensation bands.
- Target employer and level.
- Hiring urgency.
- Employment status.
- Notice period and contractual constraints.
- Candidate preferences and acceptable alternatives.
- Offer deadlines.
- Negotiation history, if voluntarily provided.

Distinguish predictive information from causal effects. Do not hard-code percentage bonuses or penalties without credible supporting evidence.

### H. Data Quality and Uncertainty

- Source reliability.
- Observation age.
- Sample size for the relevant role and market.
- Missing fields.
- Reporting bias.
- Duplicate records.
- Out-of-distribution profiles.
- Conflicting compensation reports.
- Geographic and occupational coverage.

### I. Other Factors

Identify additional factors that are legally appropriate, ethically defensible, measurable, available at prediction time, and likely to improve predictive performance.

Do not indiscriminately collect sensitive personal attributes or use protected characteristics to make discriminatory employment recommendations.

For every feature, specify its definition, availability, data source, leakage risk, privacy implications, expected utility, and ablation experiment.

---

## 7. Build a Comparative Modeling Program

Do not select the final model in advance.

Establish a reproducible model benchmark with several increasingly complex alternatives.

| Rung | Model |
|---|---|
| A | Empirical conditional salary distributions using appropriate role, location, and experience groups |
| B | Regularized linear or generalized linear models, with transformations and interactions where appropriate |
| C | Hierarchical or partial-pooling statistical models for relevant role, geography, employer, and level groups |
| D | CatBoost and LightGBM for structured tabular prediction |
| E | Quantile regression for lower, median, and upper conditional salary quantiles |
| F | Calibrated residual or conformal prediction intervals |
| Advanced | Investigate embeddings, multimodal text features, employer graphs, survival models, probabilistic neural networks, or other techniques only when data volume, target structure, and expected utility justify them |

Evaluate model combinations, component-specific models, and model ensembles only when their added complexity produces measurable benefits.

Consider separate models for: base salary · bonus and variable cash · equity and equity-related outcomes · job-offer outcomes · total compensation · career-transition scenarios.

Determine whether a staged architecture genuinely improves results or introduces error propagation.

For ordinal career levels, account for uncertainty in title normalization and level mapping rather than treating standardized levels as unquestionable ground truth.

For sparse markets and small samples, investigate partial pooling and sensible fallback estimates instead of training unreliable specialized models.

Document the mathematical objective, assumptions, failure modes, computational requirements, and selection criteria for each candidate.

---

## 8. Personalization and Progressive Profiling

Design a progressive profiling system that supports incomplete information.

**Level 0 — Minimal Profile:** Target occupation · Geographic market · Experience or career level.

**Level 1 — Role-Relevant Profile:** Skills and demonstrated capability · Responsibilities · Industry · Employer type · Work arrangement · Career trajectory.

**Level 2 — Target Opportunity:** Target employer · Target role and level · Employer-provided salary range · Job-search context · Relevant, voluntarily provided competing offers.

**Level 3 — Additional Evidence:** Verified compensation observations · Detailed project outcomes · Relevant offer history · Reliable compensation-component details · Other validated, appropriate features.

Treat these as illustrative stages rather than mandatory questionnaires.

For every stage, quantify how the additional information changes the predictive distribution, calibration, and uncertainty.

Investigate hierarchical Bayesian updating, empirical Bayes, partial pooling, conditional density estimation, and alternative methods.

Do not assume Bayesian terminology guarantees reliable uncertainty estimates. Validate the prior, likelihood, posterior, and sensitivity to model assumptions.

Avoid treating current salary as an unbiased measure of market value. Investigate anchoring, historical underpayment, reporting selection, and whether the feature adds useful information beyond the other profile variables.

Use missingness indicators only when justified, and do not interpret missing data as evidence of a personal trait.

If information is insufficient, return a broader interval or explain that the estimate is not reliable enough for the requested level of specificity.

---

## 9. Validation, Calibration, and Performance

Treat evaluation as a first-class research problem.

Create a leakage-resistant validation protocol with:

- Training, model-selection, calibration, and final test partitions.
- Temporal holdouts.
- Grouped splits where observations share a person, employer, posting, or underlying source.
- Duplicate and near-duplicate detection.
- Feature-availability timestamps.
- Preprocessing fitted only on appropriate training data.
- Explicit prevention of future-information leakage.

Use the split strategy that matches the intended deployment scenario.

Benchmark point predictions with appropriate metrics, including MAE, median absolute error, and relevant weighted or relative errors.

For quantile models, report pinball loss at the selected quantiles.

For intervals, report:

- Empirical coverage.
- Average and median interval width.
- Coverage and width by role, level, geography, and other sufficiently sampled groups.
- Calibration error.
- Tail behavior.
- Performance on recent observations.
- Performance under data scarcity and distribution shift.

Assess whether the P10, P50, and P90 estimates are coherent and whether quantile crossing occurs.

Do not use RMSE or R-squared alone as proof of usefulness.

Do not treat an arbitrary coverage percentage as a sufficient success criterion. Define acceptance thresholds before examining the final test results, using the business objective and baseline performance.

Use conformal prediction where appropriate, but document its assumptions and limitations. In particular, investigate the effects of temporal drift, geographic changes, and violations of exchangeability. Do not claim guaranteed individual-level coverage when the method only supports marginal coverage under its assumptions.

Compare:

1. Simple baseline.
2. Best tabular model.
3. Best calibrated probabilistic model.
4. Personalized model.
5. Full proposed architecture.

Perform feature-family ablations, sensitivity tests, subgroup audits, and robustness checks.

Report uncertainty around evaluation metrics when sample size permits.

If a model does not outperform a simpler alternative, recommend the simpler model.

---

## 10. Interpretability and Causal Reasoning

Investigate SHAP, feature attribution, partial dependence, conditional effect plots, and counterfactual analysis.

Clearly distinguish:

- A feature's contribution to an individual model prediction.
- A statistical association in the observed data.
- A causal effect of an intervention.
- A hypothetical scenario generated by the model.

Do not claim that a feature caused a specific salary increase merely because SHAP attributes a positive contribution to it.

Investigate correlated features, unstable attributions, extrapolation, and the limitations of counterfactual recommendations.

For career advice, identify actionable scenarios only where the model and available evidence support them.

Examples include:

- Comparing relevant job markets.
- Comparing employer types.
- Examining alternative role levels.
- Identifying skills associated with target roles.
- Evaluating the uncertainty around a job change.

Never manufacture a precise financial benefit for a skill, certification, or negotiation tactic without appropriate empirical support.

---

## 11. Sustainability, Fairness, Privacy, and Security

Design a system that can be maintained and responsibly operated.

Investigate:

- Data minimization.
- User consent and retention.
- Secure storage and deletion.
- Data-source licensing.
- Personally identifiable information protection.
- Encryption and access controls.
- Sensitive-feature handling.
- Proxy discrimination.
- Fairness auditing.
- Model cards and dataset documentation.
- Reproducibility and audit trails.
- Drift detection.
- Scheduled source refreshes.
- Retraining and rollback procedures.
- Inference and storage costs.
- API security and rate limits.
- Dependency and supply-chain risks.

Assess fairness in prediction errors, interval coverage, and data availability across relevant groups where lawful and statistically supportable.

Do not automatically remove every sensitive feature without investigating the applicable legal requirements, the intended purpose, proxy effects, and whether auditing requires separate protected-group information.

Do not use the system to rank candidates for employment or recommend discriminatory compensation decisions.

Treat salary estimates as decision support, not a guarantee, formal appraisal, or substitute for an actual employer offer.

---

## 12. Computational Feasibility and Technology Stack

Research current versions, compatibility, licensing, hardware needs, and operational costs before recommending a stack.

Consider an efficient initial stack such as:

- Python.
- Polars and/or pandas.
- DuckDB.
- Parquet.
- scikit-learn.
- CatBoost and/or LightGBM.
- Suitable probabilistic modeling libraries.
- MAPIE or another appropriate calibration framework.
- SHAP.
- PostgreSQL.
- FastAPI and Pydantic.
- Experiment tracking and model versioning.
- Automated testing and data-quality checks.

Treat this as a candidate stack, not a mandatory list.

Evaluate vector databases, embeddings, GPU acceleration, distributed processing, graph frameworks, and cloud services only where justified.

Analyze at least three deployment profiles:

- **A:** A standard developer workstation with limited RAM and no dedicated GPU.
- **B:** A stronger workstation or modest cloud virtual machine.
- **C:** A scalable cloud deployment for growing data volumes and inference traffic.

For each profile, estimate resource requirements, likely bottlenecks, cost drivers, latency considerations, and which advanced methods remain feasible.

Use measured benchmarks where available. Otherwise, label estimates as assumptions and provide a reproducible benchmark plan.

Do not assume that training a useful tabular salary model requires a GPU.

Prioritize reproducible pipelines, versioned datasets, deterministic preprocessing where practical, modular components, and straightforward deployment.

---

## 13. Research and Implementation Roadmap

Produce a staged plan.

| Phase | Name |
|---|---|
| 1 | Problem definition and source discovery |
| 2 | Data licensing, collection feasibility, quality profiling, and target construction |
| 3 | Canonical compensation schema and reproducible data pipeline |
| 4 | Baseline model and leakage-resistant evaluation |
| 5 | Quantile modeling, uncertainty estimation, and calibration |
| 6 | Progressive personalization and hierarchical modeling |
| 7 | Advanced features and experimental ablations |
| 8 | Compensation-component modeling and scenario simulation |
| 9 | API, application, monitoring, security, and deployment |
| 10 | Pilot evaluation, user feedback, drift monitoring, and evidence-based iteration |

For each phase, specify: objective · required inputs · concrete deliverables · recommended tools · dependencies · estimated effort and resource requirements · acceptance criteria · failure conditions · go/no-go decision.

Distinguish a minimum viable research prototype from a credible public beta and a mature production system.

Identify the smallest initial scope that can deliver useful results without pretending to support markets for which representative data is unavailable.

---

## 14. Required Final Deliverables

Return a detailed research report in the following order.

1. Executive assessment of feasibility and expected limitations.
2. Precisely defined prediction targets and intended users.
3. Autopsy of the original architecture.
4. Verified data-source catalog with citations and licensing notes.
5. Data quality, coverage, bias, and ground-truth analysis.
6. Canonical compensation schema.
7. Ranked feature taxonomy with expected utility and validation methods.
8. Comparative model benchmark and selection rationale.
9. Personalization and uncertainty architecture.
10. Validation, calibration, and fairness protocol.
11. Compensation-component and equity modeling design.
12. Recommended technology stack for each resource profile.
13. End-to-end data architecture and deployment design.
14. Concrete implementation roadmap.
15. Estimated time, cost, compute, and maintenance requirements.
16. Risk register and project premortem.
17. Rejected ideas and the evidence or reasoning behind each rejection.
18. A prioritized list of experiments that could most improve predictive performance.
19. An initial implementation specification, including module boundaries, schemas, APIs, tests, and reproducibility requirements.
20. A final decision memo identifying what to build first, what to defer, and what not to build.

Include tables where useful, diagrams where they clarify the architecture, and mathematical formulations only where they aid implementation or evaluation.

Provide links for important sources. Cite claims about dataset contents, library capabilities, and empirical findings.

Never present illustrative salary numbers, projected accuracy, model improvements, or cost estimates as measured results.

If the evidence does not justify a feature, mark it as experimental, deferred, or rejected.

If important information is unavailable, state what is unknown and propose a concrete way to resolve it.

---

## 15. Final Adversarial Review

Before delivering the report, challenge the proposed solution with these questions:

1. Are we predicting the market salary, actual accepted salary, or an offer that a person might receive? Are those targets clearly separated?
2. Does the available data genuinely represent the intended population?
3. Are the apparent improvements caused by leakage, duplicated records, source artifacts, or selection bias?
4. Does personalization add measurable predictive value beyond the baseline?
5. Are intervals calibrated on recent, representative observations?
6. Are the intervals useful, or merely wide enough to cover most outcomes?
7. Are model explanations being mistaken for causal effects?
8. Are employer prestige, educational background, and historical salary introducing unjustified bias?
9. Are we using expensive models when simpler ones perform equally well?
10. Are all feature values available at the time the prediction would actually be made?
11. Does the system recognize when a profile is outside its reliable operating range?
12. Can the entire pipeline be reproduced, audited, maintained, and deployed within the actual resource budget?
13. Which single experiment is most likely to invalidate the current preferred architecture?
14. What evidence would convince us not to build a proposed feature?
15. What is the strongest alternative explanation for every claimed improvement?

Finish with a concise, prioritized build-versus-defer-versus-reject decision.

The final standard is not architectural sophistication. It is a system that produces demonstrably useful, well-calibrated, personalized compensation estimates from real evidence, acknowledges uncertainty honestly, and improves through reproducible measurement.
