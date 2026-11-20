# TechPulse current system capability audit

**Prepared:** 20 November 2026  
**Purpose:** Give Claude (or another reviewer) an accurate project baseline for writing a focused implementation prompt, especially for improving the existing user interface without overstating the research evidence.  
**Project checkout audited:** `C:\Users\Administrator\Downloads\TechPulse-main (4)\TechPulse-main`  
**Last verified application state:** 19 November 2026, with a small uncommitted Streamlit simulation-mode change described below.

## Executive summary

TechPulse currently has two distinct bodies of work:

1. A pre-existing research and data-quality application for examining source readiness. It explicitly reports when source evidence, labels, model runs, or predictions are unavailable. Its pages cover source quality, ingestion, research readiness, model registry/evaluation, and related database status.
2. A newly persisted **synthetic simulation experiment** in a dedicated PostgreSQL database (`techpulse_sim`), with a reproducible generator, feature snapshots, labels, grouped model evaluation, predictions, SHAP records, and ablation results. A Streamlit mode was added to display these records.

The simulation is useful for demonstrating the end-to-end technical workflow. It is **not empirical evidence** about real technologies, real enterprise adoption, developer opinion, Kenya, or real-world decline prediction. The system does not currently have verified Kenya-specific observations or verified enterprise-adoption evidence. That distinction must remain prominent in any redesign or presentation.

The app was started at `http://127.0.0.1:8502` and its Streamlit AppTest smoke run completed with no exceptions. Port 8501 belongs to a separate pre-existing process and was not replaced. The full test suite was not run as part of starting the app.

## What is implemented and evidenced

### 1. Research and source-readiness application

- Existing Streamlit entry point: `dashboard/app.py`.
- Existing research pages are rendered through `dashboard/page_renderer.py`; database readiness and source/research pages are also supported by modules under `dashboard/` and `dashboard/db/`.
- Research mode reads PostgreSQL and communicates when inputs are unavailable. It must not display synthetic counts as research observations.
- Separate legacy synthetic-demo code remains under `dashboard/demo_*.py`. Its expected `demo` schema was not present in the configured simulation database when checked; that mode is not the same as the new `sim`/`ml` experiment.
- The app currently offers three data modes: Research data, Synthetic demonstration, and Simulation experiment. The Simulation experiment mode is currently the default in the edited working tree.

### 2. Reproducible simulation and PostgreSQL data

- A dedicated `techpulse_sim` database holds schemas `sim` and `ml`; a separate `techpulse_sim_test` database is configured for tests. The original research/dev databases were not modified by this experiment.
- The simulation uses seed 42, 300 synthetic technology identifiers, and 500 synthetic company profiles. Names and observations are generated fictional data.
- Canonical `sim` source-table counts verified in `docs/DATA_SIMULATION.md`: 300 technology metadata rows, 500 company profiles, 36,000 community-month observations, 3,000 synthetic survey rows, 77,610 simulated adoption events, and 27,080 simulated co-occurrence mappings.
- The generated label distribution is Growing 1,808; Stable 2,458; Declining 1,434 (5,700 labelled anchors). It was accepted as realized, with no quota tuning.
- Version `sim-v1-s42-6c310c4cd1ba` is recorded as verified with configuration hash, source counts/checksums, seed, generator version, git provenance, and synthetic-data disclosure.
- SQL migrations define the canonical tables, compatibility views, constraints, model/evaluation tables, and dashboard views. `src/db/load_sim.py` loads generated output transactionally and verifies counts/checksums/referential integrity.
- Relevant documentation includes `docs/DATA_SIMULATION.md`, `docs/FEATURE_DICTIONARY.md`, migration/schema files in `db/migrations/`, and the experiment code in `src/experiment/`.

### 3. Features, labels, and model experiment

- 5,700 feature snapshots and 5,700 labels are persisted. Features are computed from records available at or before each anchor; target labels use the following six-month window and are stored separately.
- The shared label rule compares the trailing-three-month mean to the next-six-month mean: Growing at ratio >=1.20, Declining at <=0.80, otherwise Stable. This is a documented deviation from the GMI/slope rule described in project documentation and still needs supervisor clarification.
- Community, enterprise, sentiment, category, history-length, and missingness features are persisted. Thin-history rows are retained and flagged.
- Model evaluation groups by technology ID, so windows for the same synthetic technology do not cross train/test boundaries. Five-fold grouped cross-validation is used. Features are imputed/encoded/scaled within pipelines/folds. The implementation includes a leakage integrity test.
- Successful model/baseline runs persisted: Logistic Regression, KNN, Random Forest, XGBoost, majority-class baseline, and recent-trend baseline. Random Forest was selected by cross-validation macro-F1.
- Persisted records include 1,140 held-out prediction rows across the selected model and baselines, 102 global SHAP rows, 48 local SHAP rows, and 35 ablation rows. The dashboard view `ml.v_latest_predictions` intentionally returns only the latest selected-model prediction per technology: 60 rows, since the held-out set contains 60 technology groups.
- Last verified metrics: selected Random Forest grouped-CV macro-F1 0.563 ± 0.006; single held-out test macro-F1 0.572, accuracy 0.568, Declining recall about 0.561, macro one-vs-rest ROC-AUC about 0.752. Chronological secondary macro-F1 was about 0.556. No candidate exceeded the pre-identified suspicious 0.95 macro-F1 threshold.
- Ablation suggests little gain from added signal families in this synthetic run: community-only grouped-CV macro-F1 about 0.570; community+enterprise about 0.572; all three families about 0.563. Do not claim that enterprise or sentiment features materially improve prediction.
- These are calculations on simulator-generated records/labels, not real-world model validation.

### 4. New Streamlit simulation experience

New file: `dashboard/simulation_renderer.py`. `dashboard/app.py` was modified to expose a Simulation experiment mode and currently defaults to it. The new mode reads from PostgreSQL through SQLAlchemy and uses Streamlit resource/data caches.

The current three tabs are:

- **Predict:** searches among held-out predicted technologies, shows saved predicted class, stored class probabilities, confidence, risk score context, anchor date, thin-history indicator, a session-only watchlist, and persisted local SHAP rows when present.
- **Models:** shows persisted run metadata, grouped-CV scores, selected-model test scores, the held-out confusion matrix, one-vs-rest ROC curves derived from saved held-out probabilities, and grouped-CV ablation results.
- **Insights:** shows synthetic dataset row totals, generated class distribution, data-version provenance, stored global SHAP features, and a clear absence-of-real/ Kenya-specific evidence statement.

Database connection errors are shown in the app with a command to run the pipeline. The app includes a visible warning that results are synthetic.

## Verification actually performed

- `python -m py_compile dashboard\simulation_renderer.py dashboard\app.py`: completed successfully.
- PostgreSQL read checks: confirmed connection to `techpulse_sim`, both schemas, overview view, persisted predictions, selected model, SHAP and ablation query shapes.
- Streamlit `AppTest.from_file('dashboard/app.py').run()`: completed with no Streamlit exceptions after fixing a chart dependency issue and handling model runs with no test metadata. The test showed all three tabs.
- Streamlit health endpoint: `http://127.0.0.1:8502/_stcore/health` returned HTTP 200 / `ok`.
- The original listener on port 8501 remained untouched. It was not verified as the simulation app; port 8502 is the verified instance from this run.
- Full `pytest` suite, cross-backend parity, and a fresh end-to-end regeneration/training run were **not** executed during this UI launch task. Do not label them as passing.

## Current worktree and provenance notes

At audit time, Git status showed:

- Modified: `dashboard/app.py`
- Untracked: `dashboard/simulation_renderer.py`
- The latest committed HEAD reported by Git was `5d80e58` (`Correct persisted inner CV protocol description`).
- The data version records run commit `f7a6538901b68b9ebd3b58559d540879044ccd0c`. The later dashboard edits have not been committed and are not part of that model-run commit.

No database schema or data changes were made while launching the UI.

## What is incomplete, risky, or should not be represented as complete

1. **Research validity:** no verified real enterprise adoption evidence, no verified Kenya-specific observations, and no supported real-world three-class prediction are available. Synthetic outputs cannot fill this evidence gap.
2. **Research-objective reconciliation:** the simulator label rule differs from the GMI/slope rule in the SRS/proposal. Supervisor clarification remains outstanding; do not silently retitle or redefine the thesis.
3. **UI completeness:** the new simulation UI is functional but deliberately minimal. It has no polished design system, responsive-layout QA, accessibility audit, guided user journey, export controls, or comprehensive empty/error-state treatment. It is not yet a “professor-level” finished product.
4. **Prediction coverage:** only the held-out technology groups have saved predictions. The UI search is over saved predictions, not all 300 technologies. Do not imply arbitrary live prediction for every technology.
5. **Watchlist:** it exists only in Streamlit session state; it is not persisted to PostgreSQL or across sessions.
6. **Uncertainty and confidence:** the UI currently shows probability/confidence fields, but calibration limits and the synthetic-only context need stronger explanation in the interaction design. Do not style the risk score as an actionable real-world warning.
7. **Model comparison display:** test-set evaluation is intentionally performed once for the selected model; candidate models that were not selected may have no held-out test metrics. The UI should explain blank/absent results, not fabricate them or evaluate models repeatedly on the test set.
8. **Charts:** ROC curves are reconstructed from stored test probabilities and labels; show their held-out/synthetic nature. SHAP effects are model explanations, not causal drivers.
9. **Backend fallback:** the requested read-only bundle export and PostgreSQL/bundle parity backend were not implemented in this stage. Current new simulation mode requires PostgreSQL.
10. **Full quality gate:** the whole test suite, full Streamlit UI interaction coverage, deployment/package checks, and reproducibility from a clean database have not been re-verified after the current uncommitted UI change.
11. **Legacy modes:** research and old demo modes coexist with the new simulation mode. Their purpose, schemas, names, and default should be simplified only after checking requirements and ensuring users cannot confuse research evidence with simulated data.

## Suggested direction for a Claude implementation prompt

Ask Claude to work from this audit and inspect the repository before editing. The prompt should direct Claude to:

- Preserve the existing folder layout, PostgreSQL schemas, simulation config, seed, class distribution, label rule, and stored research boundaries unless the supervisor explicitly approves a change.
- Improve UI/UX as a thin presentation layer over the real database records; do not create mock values or static result cards. Clearly separate Research and Simulation modes and make the active mode unmistakable.
- Design a polished, accessible, responsive academic dashboard around the three user tasks: inspect an available prediction; understand how the model was evaluated; inspect data provenance, quality, limitations, and explanations.
- Make prediction coverage explicit (60 held-out groups with saved outputs; not all technologies), label confidence and risk carefully, explain missingness, and make local SHAP language non-causal.
- Use graceful loading, empty, stale, and database-error states. Do not rely on fragile optional chart dependencies; test every tab with the actual configured database and without it.
- Keep the app query-driven from PostgreSQL and add/maintain tests for data-access shapes and UI smoke behavior. Run the focused tests and full relevant suite, reporting real PASS/FAIL output.
- Keep changes focused on UI/UX and reliability. Avoid introducing new infrastructure, changing the experiment, regenerating results, adding an unapproved data source, or changing thesis scope.
- End with a file-by-file change summary, verification log, remaining caveats, and a short evaluator demonstration path. Never report planned/unverified work as completed.

## Prompt-ready baseline statement

> TechPulse now has a reproducible PostgreSQL-backed synthetic experiment and a minimal three-tab Streamlit view on top of an existing research/source-readiness app. The experiment contains 300 fictional technologies, 500 fictional companies, 5,700 as-of feature/label anchors, grouped technology-level evaluation, 1,140 held-out model/baseline rows, and persisted SHAP/ablation outputs. The selected Random Forest achieved grouped-CV macro-F1 0.563 ± 0.006 and one held-out macro-F1 0.572 on simulator-generated labels. The new UI smoke check passed, but the full test suite and bundle backend parity were not run/implemented. There is no verified Kenya-specific or enterprise evidence and no validated real-world decline prediction. Improve the app’s UI/UX and operational robustness without changing the dataset, label logic, research scope, database evidence, or making synthetic results look empirical.
