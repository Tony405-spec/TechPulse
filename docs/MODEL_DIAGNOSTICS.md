# TechPulse v1 model and label-noise diagnostics

**Status:** A0 checkpoint only. A1–A4 feature/model changes have not started.  
**Data:** `sim-v1-s42-6c310c4cd1ba`, seed 42.  
**Diagnostic code:** `scripts/diagnose_simulator_ceiling.py`.  
**Diagnostic run commit:** `b26e2b2076e3c7ef1c403a89c8593426c447559d`; worktree clean.  
**Persisted model provenance:** `sim-v1-s42-6c310c4cd1ba-random_forest-f7a65389`, `git_dirty=false`.

## Gate result

The strongest diagnostic model used the persisted as-of features **plus** privileged, true latent trajectory information through anchor date T (latent multi-window levels/slopes/volatility, acceleration, drawdown, years since peak, and the generator's curve-family identity). It never received future trajectory values. Evaluation used five technology-grouped folds inside the existing 80% training partition. The held-out test groups were not used for oracle fitting or scoring.

| Diagnostic oracle | Grouped-CV macro-F1 | SD across folds | Mean Declining recall |
|---|---:|---:|---:|
| Latent trajectory only | 0.397 | 0.009 | 0.321 |
| As-of features + privileged latent state | **0.600** | 0.022 | 0.528 |

The second row is the relevant empirical diagnostic ceiling for this A0 exercise: it is the stronger of two fixed Random Forest diagnostics with information unavailable to the production model. It is not a mathematical Bayes-optimal bound; it is an empirical privileged-information estimate under this model and fold design. At **0.600**, it is below the requested approximate **0.75 macro-F1** gate. The ordinary selected Random Forest remains at grouped-CV macro-F1 **0.563 ± 0.006**; the held-out result remains **0.572**. No test-set result was used to select this diagnostic or any next step.

**Decision:** stop before A1 and request supervisor/user approval for a new simulator version. Do not edit or regenerate `sim-v1`.

## Label stability under resampled observation noise

For each of the 300 fixed latent technology trajectories, 300 independent monthly observation series were sampled with the v1 negative-binomial count, AR(1), seasonal, shock, and pre-label ambiguity-noise mechanisms. The shared 3-month versus following-6-month rule was reapplied at the stored anchor dates. No latent curve or resampled series was written to PostgreSQL.

| Measure | Result |
|---|---:|
| Mean agreement with the modal label across resamples (per anchor, then averaged) | 0.505 |
| Mean flip rate relative to that modal label | 0.495 |
| Mean resample agreement with the one stored v1 label | 0.427 |
| Anchors receiving a valid label in resamples | 1.000 |

Agreement with stored labels by family was also low: hype-then-collapse 0.423, late-surge 0.437, logistic-growth 0.447, plateau 0.419, and post-peak-decay 0.428. These are diagnostic Monte Carlo estimates under the implemented generator, not estimates about real community data. They indicate that a single generated monthly observation realization can materially change labels for an otherwise fixed latent trajectory.

## Learning curve and signal ablation

Learning-curve fits used **only the 80% training groups**, with grouped five-fold validation and the current Random Forest pipeline/leaf setting held fixed. The same folds were used at each training size.

| Fraction of training groups | Mean groups used per fold | Grouped-CV macro-F1 | SD |
|---:|---:|---:|---:|
| 25% | 48 | 0.559 | 0.018 |
| 50% | 96 | 0.565 | 0.014 |
| 75% | 144 | 0.567 | 0.015 |
| 100% | 192 | 0.566 | 0.011 |

The curve is nearly flat after the first quarter of the training groups. Under this diagnostic, additional data volume alone is unlikely to resolve the performance gap. This does not prove that more independent technologies could never help; it says the current fixed v1 signal/label setup shows little benefit from increasing the training groups from roughly 48 to 192.

The persisted signal-family ablation from the selected run gives:

| Signals | Grouped-CV macro-F1 | SD |
|---|---:|---:|
| Community + enterprise | 0.572 | 0.010 |
| Community | 0.570 | 0.012 |
| Community + sentiment | 0.563 | 0.016 |
| Community + enterprise + sentiment | 0.563 | 0.016 |
| Enterprise | 0.422 | 0.016 |
| Sentiment | 0.405 | 0.008 |
| Enterprise + sentiment | 0.401 | 0.008 |

Within v1, community features carry most of the model's signal. Enterprise adds about 0.002 macro-F1 over community alone in this grouped-CV summary; adding all signal families does not improve it. These ablations do not support a claim that enterprise or sentiment signals materially improve the result.

## Error analysis

The table below is descriptive analysis of the already-scored, once-only held-out predictions for the selected Random Forest. It was not used for model selection or threshold changes.

| Group | Held-out rows | Accuracy |
|---|---:|---:|
| Actual Declining | 287 | 0.561 |
| Actual Growing | 360 | 0.636 |
| Actual Stable | 493 | 0.523 |
| Databases | 209 | 0.579 |
| Frameworks | 342 | 0.553 |
| Languages | 304 | 0.559 |
| Tools | 285 | 0.589 |

| Curve family | Held-out rows | Accuracy | Most notable pattern |
|---|---:|---:|---|
| Hype then collapse | 114 | **0.430** | Most difficult family; 15 of 32 actual Declining cases were predicted Stable, and 22 of 50 actual Stable cases were predicted Growing. |
| Late surge | 57 | 0.544 | Small subgroup; one third of its actual Declining cases were predicted Stable (7/12). Interpret cautiously. |
| Logistic growth | 190 | 0.547 | Stable cases were split across the three predictions; Declining was often predicted Stable (25/51). |
| Plateau | 646 | 0.594 | Largest family; actual Stable cases were often predicted Growing (78/297). |
| Post-peak decay | 133 | 0.602 | Actual Declining was often predicted Stable (12/35). |

Category accuracy ranges from 0.553 to 0.589, with no large apparent category separation in this 60-technology test sample. The late-surge family has only 57 rows and should not be overinterpreted. The family/label groups are synthetic generator constructs, not real-world technology types.

## Interpretation and limits

- The label rule compares a short three-month baseline with a six-month future mean. The simulator adds count overdispersion, correlated noise, seasonality, occasional shocks, and a small ambiguity perturbation before assigning labels. The stability analysis indicates substantial sensitivity to those observation draws.
- The learning curve is flat over the observed training-group range, while the latent-only oracle is weaker than the as-of model. The combined privileged model reaches 0.600, so label/observation uncertainty and the available feature-target relationship appear to constrain this v1 experiment more than simply increasing its current training sample.
- The oracle uses privileged latent information for diagnosis only. It is not a valid production feature set and must never be persisted as an application prediction or represented as deployable performance.
- This does not validate performance on genuine technology observations. v1 is explicitly synthetic, and there are no verified Kenya-specific observations or verified enterprise-adoption observations.
- The label rule remains a documented deviation from the proposal/SRS GMI/slope lifecycle rule; supervisor clarification is still needed.

## Diagnostic protocol correction record

An initial exploratory implementation mistakenly cross-validated the latent-only diagnostic across all 300 groups, including the groups designated as the held-out test set. Those preliminary results were discarded and are not reported as valid A0 results. This was a protocol deviation: although it did not train or select a production candidate and did not alter the persisted Random Forest metrics, it did expose the held-out groups to a diagnostic model score. The v1 held-out split should therefore not be described as wholly untouched for any future model-development iteration. The final run recorded above restricts all oracle fitting/scoring and learning-curve CV to the designated 80% training groups. The selected model's already-persisted held-out rows are used only for descriptive error breakdowns. If additional model iteration is later approved, keep it strictly within training groups; any new final claim requiring an untouched test estimate should use a separately pre-registered holdout, most naturally in a separately versioned experiment.

