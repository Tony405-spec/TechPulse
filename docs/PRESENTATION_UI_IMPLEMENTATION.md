# Presentation dashboard: run and demonstration notes

## Start the app

Open PowerShell in the repository root and run:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env so DATABASE_URL points to the local techpulse_sim PostgreSQL database.
python -m src.db.migrate
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8502
```

Create the `techpulse_sim` database in PostgreSQL/pgAdmin before running the migration. Keep `.env` local and never commit credentials. The migration is additive and idempotent. The prepared local database has `004_simulation_watchlist` applied and its simulation corpus loaded. A GitHub clone does not contain the PostgreSQL database; on a separate empty `techpulse_sim` database, run `python -m src.run_all` once to generate and train the clearly labelled simulation before starting Streamlit. Do not run it against the prepared presentation database because it reruns training. The app opens at `http://127.0.0.1:8502`.

For the presentation, do **not** run `python -m src.run_all`; the verified v1 data and saved model outputs already exist. That command rebuilds/reruns the experiment pipeline.

## What the three tabs demonstrate

- **Predict:** search the 300 profiles by familiar real technology names, filter by category, view a saved simulated result when one exists, inspect three synthetic signal timelines, read stored local SHAP contributions, compare up to three saved results, download one result as CSV, and maintain a PostgreSQL watchlist tied to the Streamlit browser session.
- **Models:** compare four candidate models and two baselines using grouped-CV macro-F1, OvR ROC-AUC, ECE, and Brier score; view the once-only held-out results for the selected model and baselines; inspect the held-out confusion matrix, one-vs-rest ROC, descriptive reliability plot, per-class metrics, and signal-family ablation.
- **Insights:** inspect generated class counts, source row totals, stored global SHAP, and the data-version provenance record. Expand “About this data” for the label rule, validation protocol, pending supervisor clarification, and limitations.

The default mode is **Simulation · PostgreSQL**, with a persistent notice that real names are display labels only and all attached histories and outcomes are simulated. Names are mapped to the 300 IDs in a deterministic, display-only catalog; the simulator, database rows, features, labels, and fitted models are unchanged. The other modes are separate: **Research · PostgreSQL** carries a red notice that verified Kenya-specific and enterprise-adoption evidence is absent; **Legacy demo · PostgreSQL** identifies its separate demo schema.

## Three-minute evaluator route

1. Start on **Predict**. Say: “This is a simulated workflow demonstration. The catalog uses familiar technology names, but every signal and result is generated. There are 300 simulated profiles; saved held-out results currently cover only 60.”
2. Search/select **React**. Point out the saved simulated class, date, probabilities, and the notice that the scenario does not describe React's actual trajectory. The probabilities are **not calibrated** and are not a reliable confidence claim or decision recommendation.
3. Scroll to the signal charts and local SHAP waterfall. Explain that the community, enterprise, and sentiment series are generated, and SHAP describes associations the fitted model used, not causes.
4. Open **Models**. Show Random Forest grouped-CV macro-F1 `0.563 ± 0.006`, held-out macro-F1 `0.572`, and Declining recall `0.561`. Explain that unselected candidate models were not scored on the held-out groups. The reliability plot is a descriptive check, not calibration.
5. Open **Insights**. Show the generated class distribution and provenance record. Finish by stating that the run validates a reproducible software workflow under the simulator, not real-world prediction, enterprise adoption, or Kenya-specific technology patterns.

## Current scope and honest limitations

- The interface uses cached, parameterized PostgreSQL queries in `dashboard/simulation_data.py` and persisted `sim`/`ml` rows and views. The watchlist is the one intentional UI write and is stored by browser session in `ml.watchlist`.
- The saved prediction catalogue covers 60 of 300 simulated profiles. The other 240 show a clear no-prediction state; the app does not generate a new prediction. Real product names are only display aliases and are not matched to real product evidence.
- Raw model probabilities are not calibrated. No calibrated confidence bands, OOF coverage curves, or accuracy-versus-coverage records exist yet. The app states this rather than inventing a confidence band.
- Candidate models without a saved holdout score are labelled “not tested on holdout by design”.
- CSV export is implemented. PNG/PDF export and PostgreSQL/bundle backend parity remain pending.
- The simulator, labels, class distribution, features, model runs, and database rows were not changed for the display-name update. The alias map affects only the Streamlit presentation. The additive watchlist migration does not change experiment rows.

## Verification record

- `python -m pytest tests/test_simulation_dashboard.py tests/test_dashboard_demo_mode.py::test_application_exposes_postgres_demo_mode_without_sqlite_fallback -q`: **4 passed** after adding the display-name catalog and final UI updates.
- Full `python -m pytest tests/ -q`: **93 passed, 22 failed, 2 skipped**. The failures are existing integration expectations for unavailable legacy `demo` tables and research schema relations in the configured database; the configured `techpulse_sim` database is intentionally the isolated simulation DB. The new dashboard-specific tests passed in that run.
- `python -m py_compile dashboard\app.py dashboard\simulation_data.py dashboard\simulation_renderer.py tests\test_simulation_dashboard.py`: PASS.
- Browser check against `http://127.0.0.1:8502`: all three tabs rendered, 14 Plotly charts were present across the dashboard, the React simulated example showed its saved result, no placeholder names or browser page errors appeared, and the health endpoint returned HTTP 200.
- At a 390 px mobile viewport, document width was 390 px with no horizontal page overflow. Dark mode controls and select fields were checked for readable contrast.
- Screenshots were captured with the installed Microsoft Edge headless binary after the final changes; see `docs/screenshots/`. The bundled Computer Use runtime could not initialize because its kernel asset path was missing, so browser verification used Edge through Playwright.
- The full suite result above predates the final display-name and presentation-only changes; the focused dashboard checks and compilation were rerun after those changes and passed.

