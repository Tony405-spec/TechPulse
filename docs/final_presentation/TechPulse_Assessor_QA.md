# TechPulse Assessor Q&A

Answers reflect the approved proposal and implementation audit. Never present synthetic demo values as research findings.

## Research problem and contribution

**What exactly is the research problem?**  
The approved proposal says organisations and developers lack a reliable data-driven way to anticipate a software technology’s future trajectory. Existing analytics describe historical activity. TechPulse proposes combining community, enterprise-adoption and developer-sentiment signals to classify a future trajectory. Current evidence does not establish predictive performance.

**How did you establish the research gap?**  
The approved proposal cites work on GitHub starring/social coding, platform evolution, individual project evolution, and developer surveys. It frames the gap as a technology-level framework combining the three signal families. This is the proposal’s literature-review gap, not proof that no other work exists or an exhaustive systematic review.

**What is TechPulse’s actual contribution now?**  
An operational Streamlit/PostgreSQL evidence and data-quality workflow, source lineage/status reporting, separation of research and synthetic modes, and a transparent account of research readiness. It does not yet demonstrate that real technology decline can be predicted.

## Data and source credibility

**Why select these sources?**  
They correspond to the approved candidate signal families: Stack Exchange activity, annual developer surveys, and company technology-stack evidence. Their actual limitations are material: the supplied community series is blocked; the survey is global or geographically unspecified and not time-aligned with 2016–18 community data; company profiles do not prove technology usage.

**How reliable are the current observations?**  
The supplied Stack Exchange file contains an iOS row with zero questions but 181,334 unanswered; validation blocks it. The survey CSV has 685 rows and 684 distinct technology-year keys; the category collision remains unresolved. Research training was not performed on these records.

**Do company profiles prove enterprise adoption?**  
No. The audit reports 497 company profiles but zero verified company–technology adoption evidence rows. A company directory entry alone does not show use of a particular technology.

**Can you make conclusions about Kenya?**  
No. PostgreSQL has zero verified Kenya-specific technology observations. Synthetic Kenya-labelled scenarios exist only in the separate demonstration store and are fictional.

**Are the sources licensed and representative?**  
The source register notes attribution/licence terms requiring verification for some local files. The current corpus is global or US Fortune 500 oriented, not representative Kenya evidence. I make no local adoption inference.

## Labels, features and leakage

**How did you define Growing, Stable and Declining?**  
The proposal names the classes but does not establish a validated research label dataset. The synthetic demo generator compares future six-month mean question volume with recent three-month mean: ratio ≥1.20 is Growing, ≤0.80 is Declining, and otherwise Stable. Those labels are synthetic only. The SRS describes a GMI-based rule, while legacy code uses a future-window ratio. The supervisor must reconcile the research target before labelling or training.

**How will you prevent target leakage?**  
Fix an as-of time t; calculate predictors only from evidence available by t; derive labels from a later horizon t+h; remove future-window and post-outcome columns from X; and evaluate on later time periods. The written SRS uses Growth Momentum Index in the label rule while GMI is also an intended feature, creating potential circularity. Research training remains blocked until the definition is reconciled.

**What are the seven implemented feature names and formulas?**  
These are implemented in the synthetic demo generator, not in valid research snapshots. In the current scaled generator:
1. technology_health_score = clip(50 + 0.35×GMI + 0.25×Q − 0.20×max(D,0) + V, 0,100).
2. growth_momentum_index (GMI) = 100×(mean current 3 months − mean prior 3 months)/max(prior mean,1).
3. question_quality_score (Q) = 100×answered/total questions in trailing 12 months.
4. company_diversity_score = count of unique generated sectors observed by t.
5. sentiment_delta = latest − earliest generated satisfaction by t.
6. adoption_velocity (V) = new synthetic company-technology links in trailing 12 months / 4 quarters.
7. community_decay_rate (D) = 100×(prior six-month mean − recent six-month mean)/max(prior mean,1).
The generated sectors, company links, sentiment and activity series are fictional. These are demonstration formulae, not approved empirical feature definitions. Older demo code contains formula variants; slide 4 and this list use the current scaled generator.

**Why chronological validation?**  
The intended claim is forward-looking, so evaluation should train on earlier periods and test on later periods. Walk-forward or expanding-window evaluation better reflects intended use. Report class support for every split and call out splits where a class is absent.

## Models and evaluation

**Why these four classifiers?**  
They are the four model families in the approved proposal: Logistic Regression, K-Nearest Neighbours, Random Forest and XGBoost. Code or synthetic runs do not prove a research run.

**Why weighted F1?**  
Weighted F1 combines class precision and recall weighted by class support, but can still hide poor minority-class recall. Report per-class precision/recall/F1, class counts, a confusion matrix, and a simple baseline. No research metrics are currently available.

**How do you know the model generalises?**  
There is no valid research evidence for generalisation yet. It requires a later-time holdout with adequate class support, leakage controls, baselines and preserved data/run provenance. Synthetic holdout results test demo plumbing only.

**What does SHAP contribute?**  
SHAP attributes a fitted model’s outputs to its features; it does not establish causal drivers. No valid research model or predictions exist, so no research SHAP result is available. Demo SHAP is synthetic only.

## Application and objectives

**Does the application generate research predictions on demand?**  
Research prediction and model pages show an empty state because no valid research run or persisted research prediction exists. Synthetic mode stores generated runs, predictions and explanations in PostgreSQL schema `demo`, separate from research schemas. It is visibly marked and is not research evidence.

**Which objectives were achieved?**  
Slide 6 reports all six approved objective statuses. Source audit and local dashboard implementation have partial evidence. Valid research feature snapshots, labels, classifier evaluation and research SHAP are not demonstrated. Public deployment and dissertation completion were not verified by the implementation audit.

**What would you improve next?**  
Confirm the target rule/horizon and data-quality policy with the supervisor; verify or replace sources with traceable, time-aligned evidence; establish the enterprise adoption evidence standard and whether Kenya evidence is required; then run a versioned chronological experiment against baselines and report class-level metrics.

## Supervisor clarification required

1. Confirm the approved class rule and forecast horizon, and reconcile the SRS GMI rule with the legacy future-window rule.
2. Confirm what qualifies as verifiable company–technology adoption evidence.
3. Confirm whether Kenya-specific evidence is mandatory or whether the thesis scope is global.
4. Confirm acceptable source provenance/licensing and how to resolve the Stack Exchange impossible row and survey category collision.
5. Confirm chronological versus stratified evaluation expectations and the required metric emphasis.
6. Confirm whether a data-feasibility result is acceptable if validated observations remain insufficient.

## Proposal references shown on slide 3

- Borges, H. & Valente, M. T. (2018). “What’s in a GitHub star? Understanding repository starring practices in a social coding platform.” Journal of Systems and Software, 146, 112–129.
- Mens, T. & Goeminne, M. (2012). “Analysing the evolution of social coding platforms.” Science of Computer Programming, 78(8), 1034–1053.
- Syer, M. D., Adams, B., Hassan, A. E., & Godfrey, M. W. (2013). “Revisiting prior empirical findings for agile: An analysis of the RapidSMS open source project.” CASCON 2013, 49–62.
- Stack Overflow (2024). Stack Overflow Developer Survey 2024.

These citations are reproduced from the approved proposal; the presentation does not claim independent re-review of the publications.
