# Model evaluation status

**Checked:** 2026-11-13

## Current defensible result

There is currently **no auditable research evaluation metric to report**. The canonical PostgreSQL database contains zero model runs, predictions, class metrics, baselines, feature snapshots, and prediction explanations. The supplied `data/feature_matrix.csv` is absent. Curated community monthly metrics are also zero because ingestion is blocked by an impossible source row.

The 46 filesystem run manifests inspected are all synthetic test fixtures or explicitly listed in the test-fixture registry. Their perfect-looking result summaries exercise serialization and dashboard code; they do not measure predictive skill on the supplied research data. They are preserved, excluded from the current dashboard, and excluded here. Therefore accuracy, weighted F1, per-class results, calibration, confusion matrix and uncertainty for the research question are **not available**. This is not a zero score; the evaluation has not been validly run.

## Method implemented and its limits

The codebase contains features based on technology health, growth momentum, question quality and community decay; Growing/Stable/Declining labels based on future-vs-recent activity; Logistic Regression, KNN, Random Forest and XGBoost candidates; majority and momentum baselines; and chronological holdout / forward-fold safeguards. Existing tests confirm feature/target separation and forward-in-time folds. These are implementation capabilities, not evidence that a model was validly trained on this project's actual dataset.

The current supplied observations are 2016–2018, incomplete in provenance, and blocked by the impossible `ios` observation. The survey aggregate spans 2021–2024 and cannot be joined backward to make features for the older community windows. There is no defensible current Kenyan trajectory label set. Rebuilding and scoring now would either fail the quality gate or rely on incompatible/unverified evidence; no such scores are reported.

## Next valid experiment

After source verification and a documented corrected data version:

1. Build monthly technology features using only observations at or before each cutoff; retain coverage/missingness and input checksums.
2. Construct future-window labels separately, excluding incomplete outcome windows and all future-derived columns from `X`.
3. Use chronological expanding/walk-forward validation, with a held-out period and any class-absent split called out explicitly.
4. Compare majority and momentum baselines with regularized Logistic Regression and Random Forest; add a boosting candidate only if class support and sample size justify it.
5. Save per-class support, precision, recall, F1, macro/weighted F1, accuracy, confusion matrix, calibration/uncertainty where support permits, split dates, class counts, parameters, input snapshot/checksum, and selected model identifier.
6. Persist the results under a new model-run ID without overwriting historical artifacts. Interpret SHAP/features as model associations, not causes.

Until this work is possible, the presentation should show the Model Performance page's explicit empty state and explain why reporting the synthetic fixture's perfect score would be misleading.
