# TechPulse redesign verification report

Date: 1 November 2026

## Verification performed

- Ran `python -m pytest tests/ -q` using the checkout's available Python test environment: **26 passed, 2 warnings** in 47.38 seconds. Both warnings are scikit-learn feature-name warnings from `tests/test_models.py::test_random_state_reproducibility`.
- Ran Streamlit `AppTest` against all eight navigation routes; no page raised an exception.
- Opened the application in Microsoft Edge and captured all eight routes at desktop resolution. Screenshots and an index are in `outputs/redesign_screenshots/`.
- Reviewed the Start Here and Model Performance screenshots after the final formatting changes. The saved metric values display to four decimal places; artifact inconsistency and interpretation warnings are visible.
- Compiled the dashboard and PDF-generation scripts successfully before running them.

## Known evidence and environment limits

- The checkout records `local_development_csv` mode. No live PostgreSQL connection or current end-to-end data-ingestion/model-training run was exercised.
- `outputs/model_comparison.csv` reports perfect scores for four candidates, but the checkout has no run-level evaluation summary to tie these values to split dates and held-out class counts. It also has no majority-class baseline row.
- Saved labels disagree across artifacts: the feature matrix has 51 Declining and 2 Stable records, while the predictions file has 52 Declining and 1 Growing prediction; the separate labelling summary reports different counts. These are surfaced in the app and documentation, not silently reconciled.
- The existing model artifact is from a 36-record run, whereas the current feature/prediction artifacts have 53 rows. Its saved evaluation metadata is insufficient to validate it against the current records.
- The developer survey CSV is absent. Several signal tables are explicitly identified as local development proxies. `data/ev311.csv` is not used in the predictive workflow.
- The legacy SQL examples and schema diagram do not fully match the current six-table ingestion contract. The methodology guide calls out the mismatch; the examples have not been executed against a live database.
- Prediction Explorer reads saved predictions; it does not run on-demand inference. The displayed risk is derived from the saved probability of the Growing class and is not a probability of failure.

## Browser capture index

1. `01-start-here.png`
2. `02-technology-explorer.png`
3. `03-technology-rankings.png`
4. `04-community-health.png`
5. `05-prediction-explorer.png`
6. `06-model-performance.png`
7. `07-methodology-data.png`
8. `08-about-user-guide.png`

See `outputs/redesign_screenshots/index.md` for the generated screenshot contact sheet and page descriptions.
