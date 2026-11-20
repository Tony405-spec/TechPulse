# Proposal: a separate TechPulse simulation v2

**Status:** Proposal only; requires supervisor/user approval. No simulator or label configuration has been changed. `sim-v1-s42` and all v1 results remain intact.

## Why a v2 proposal is needed

The v1 A0 diagnostic used seed 42 and a clean, committed implementation. A privileged model with as-of features plus true latent state reached grouped-CV macro-F1 **0.600 ± 0.022**, below the requested approximate 0.75 gate. In 300 resampled observation series per technology, the stored trajectory label matched the modal resampled label only **42.7%** of the time on average. This indicates that v1's label is highly sensitive to its stochastic observation process.

## Proposed single change

For a new `sim-v2-s42` only, increase the negative-binomial dispersion parameter for monthly community counts from **18 to 36**, keeping the existing 3-month/6-month shared labeller, thresholds, anchor dates, seed, technology/company counts, latent curve families, AR(1) term, seasonal component, and shock process unchanged.

In the current parameterization, a higher negative-binomial dispersion parameter reduces count variance toward the Poisson limit. At an illustrative expected monthly count of 60, the count-only coefficient of variation is approximately 0.258 at dispersion 18 and 0.211 at dispersion 36. This is a pre-specified, modest change to the measurement-noise assumption for aggregated monthly activity, not a setting chosen to improve a model metric. The simulator has no empirical source calibration for this value, so it must be described as a scenario assumption—not as an estimate of Stack Exchange behavior.

## Approval and execution conditions

Before running v2, the supervisor should confirm that this scenario change is acceptable and that retaining the 3/6-month label rule is consistent with the thesis objective despite the documented GMI/slope deviation. If approved:

1. Implement v2 as a new version with its own data version, configuration hash, database rows, and explicitly tagged source origin. Never alter or replace v1 records.
2. Record and commit the exact v2 config/code/settings before generation or any v2 model-result review; write down the commit and clean/dirty status.
3. Generate and validate the v2 corpus once. Report its realized class balance and label-stability diagnostic without quota tuning.
4. Only after that checkpoint, train using the already specified grouped-CV protocol. Report v1 and v2 side by side and explain the changed noise assumption in the dissertation and UI.
5. If v2 still has a low diagnostic ceiling, report that result. Do not change settings repeatedly to chase a score.

No v2 data, labels, predictions, or model results exist at the time of this proposal.

