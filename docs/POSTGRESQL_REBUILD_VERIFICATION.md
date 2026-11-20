# TechPulse PostgreSQL rebuild — verification report

**Verified:** 19 November 2026 (Africa/Nairobi)  
**Work folder:** `C:\Users\Administrator\Downloads\TechPulse-main (4)\TechPulse-main`  
**Development database:** `techpulse_rebuild_dev` on local PostgreSQL 18.3  
**Scope:** isolated integration of existing synthetic demonstration records and runtime reads into PostgreSQL. This report supersedes older statements in presentation notes that described SQLite as the active demo runtime.

## Changes made

- `dashboard/app.py`: synthetic mode now reads PostgreSQL schema `demo`; no SQLite path is selected by the application.
- `dashboard/demo_store.py`: fixed-table, read-only PostgreSQL access only.
- `dashboard/demo_renderer.py`: removed the SQLite training action, reads imported PostgreSQL records, and dynamically shows the synthetic-only macro-F1 leader and class metrics.
- `dashboard/postgres_demo_migration.py`: one-time read-only SQLite source importer with integrity check, source checksum, row reconciliation, PostgreSQL constraints/indexes, and checksum-protected repeat behavior. A different source checksum stops without replacement.
- `dashboard/model_selection.py`: conservative persisted-result selector; requires comparable evaluation cohorts, all three lifecycle classes, and minimum class support. Research selector returns no winner when evidence is absent.
- `dashboard/page_renderer.py`, `dashboard/db/queries.py`: dynamic research winner section and class results, with an explicit no-evidence state and visible note that macro F1 differs from SRS FR-10.
- `dashboard/db/health.py`: expected database can be configured for isolated development while production default remains `TechPulse-Database`.
- `migrations/003_model_selection_records.sql`, `004_demo_latest_features.sql`, `005_demo_model_selection.sql`, `006_demo_selection_stability.sql`: additive selection storage and PostgreSQL latest-feature view; no table-drop migration.
- `tests/test_model_selection.py`, `tests/test_dashboard_demo_mode.py`, `tests/test_dashboard_postgres.py`, `tests/test_dashboard_redesign.py`: selection, PostgreSQL demo, connectivity and empty-catalogue tests.
- `docs/REQUIREMENTS_TRACEABILITY_POSTGRESQL.md`, `docs/POSTGRESQL_DEMO_MIGRATION.md`, this report, and README/startup updates.

The pre-existing `dashboard/demo_population.py` remains as an unused legacy fixture-generation module. It is not imported by Streamlit. SQLite code remains only in that archived module and the explicit, read-only migration utility; the operational app data access is PostgreSQL-only.

## Database and backup changes

- Created `techpulse_rebuild_dev`; did not alter `TechPulse-Database`, `techpulse_db`, or unrelated databases.
- Created restricted login `techpulse_rebuild_app`, with SELECT access for this development database. Streamlit does not use the PostgreSQL administrator role.
- Applied numbered migrations 001–006 in the new database; health check reported all canonical schemas and 6 migrations.
- Imported the existing SQLite fixture into schema `demo`. `PRAGMA integrity_check` was `ok`; source checksum: `f035a6a9baa246b4e42e2663e5c7f58de8de419233a2db7c37f0cd0c944b3caf`.
- The migration source SHA and counts are recorded in `demo.migration_manifest`. Repeating with the same file verified counts without rewriting records.
- Verified 14 demo foreign keys and zero orphans in community-to-technology, prediction-to-model/technology, and adoption-to-relationship checks.
- Verified the custom-format development backup can be listed by `pg_restore`: `docs/.codex-build/postgresql_rebuild/backups/techpulse_rebuild_dev_final_20261119.dump` (2,335,520 bytes; 461 TOC lines). Earlier source database and SQLite backups remain in the same backup folder.
- Local `.env` points to the development role/database and is Git-ignored. No credential was added to tracked source or logs.

## Data inventory

The imported 25 source tables contained:

| Data | Rows |
|---|---:|
| Technologies | 210 |
| Community observations | 15,120 |
| Historical technology observations | 7,560 |
| Developer question scenarios | 8,400 |
| Sentiment observations | 15,120 |
| Survey-like synthetic observations | 3,360 |
| Fictional company profiles | 300 |
| Company-technology relationships | 1,500 |
| Fictional adoption scenarios | 2,000 |
| Generated geographic scenarios | 1,260 |
| Feature snapshots | 8,820 |
| Synthetic lifecycle assessments | 210 |
| Synthetic model runs / evaluation records | 4 / 4 |
| Synthetic predictions / probability records | 840 / 2,520 |
| Synthetic explanation rows | 1,470 |

Every synthetic row retains its synthetic mode/origin where present. The source contains 630 fictional Kenya-labelled geography rows and zero Kenya-context observations. These generated rows do not establish facts about Kenyan developers or firms. No verified enterprise adoption evidence is present.

## Models and actual evaluation values

Four already executed synthetic model artifacts were registered and loaded; artifact files and SHA-256 values were verified. They used the same synthetic training dataset version, feature/label versions and chronological split (train 2021-01 through 2023-09; test 2023-10 through 2024-06) with four expanding-window CV folds.

| Model | Accuracy | Weighted F1 | Macro F1 |
|---|---:|---:|---:|
| Random Forest | 0.7206 | 0.6966 | **0.5093** |
| K-Nearest Neighbours | 0.7101 | 0.6730 | 0.4519 |
| XGBoost | 0.7376 | 0.6856 | 0.4501 |
| Logistic Regression | 0.7206 | 0.6036 | 0.2792 |

The database-driven synthetic selector chooses Random Forest by macro F1 and records the four-fold weighted-F1 population standard deviation (0.0600) as a validation-stability measure. The per-class F1 leaders are Random Forest for Growing (0.5185), Logistic Regression for Stable (0.8376), and Random Forest for Declining (0.1905). The Declining recall of the overall winner is only 0.1267, so this is weak simulated-class performance and does not validate prediction of real technology decline.

The research model registry contains zero successful research runs in this new development database. Research mode therefore shows no best-model claim and no persisted predictions. Imported synthetic runs are never presented as research results.

## Verification executed

- New selector tests: **4 passed**.
- PostgreSQL synthetic pages and selector: **22 passed**.
- Targeted current-page and connection checks: **30 passed, 3 skipped** (the three expected empty-source/corpus-dependent cases).
- Final full suite after model selection, stability and migration-order changes: **100 passed, 5 skipped, 16 warnings**. Warnings were dependency deprecations, Windows CPU-core detection and feature-name notices; no test failures remained.
- Streamlit AppTest smoke checks rendered every synthetic and research page without app exceptions.
- Live Streamlit health endpoint: `http://127.0.0.1:8501/_stcore/health` returned HTTP 200, `ok`.
- App is running bound to localhost only at `http://127.0.0.1:8501`.

An earlier full-suite run showed three failures: one expected the original production database name while using the isolated development DB, and two expected research catalogue controls even though the new database correctly has no research technology rows. The expected database is now configurable and those empty-catalogue tests skip for an empty development corpus. The subsequent complete suite passed (100 passed, 5 skipped).

## Remaining limits / decisions

1. Research observations were not copied into the new development database. The existing source databases remain untouched; the new DB's research schemas are empty. This avoids an unreviewed cross-database merge.
2. No research feature snapshot, label set, model run, prediction, or explanation was created. No real research model was trained during this work.
3. The migration imports the existing synthetic fixture; it does not create a new synthetic data generator directly targeting PostgreSQL. A separate reviewed generation pipeline is still needed if new demo scenarios are required.
4. The current app's synthetic training is disabled; imported model runs and metrics are viewable. The broader model training workflow has not been converted to PostgreSQL end-to-end.
5. The original SQLite fixture and inactive SQLite generation code are retained for audit/migration provenance. Streamlit has no SQLite runtime route.
6. The prompt's macro-F1 rule conflicts with approved SRS FR-10, which says weighted F1. Confirm the selection criterion with the supervisor before treating the macro-F1 requirement as an approved research method.
7. The SRS NFR-MA-03 specifies random state 42, while these synthetic runs use seed 7312026. Confirm which seed governs the approved research experiment.
8. No separate Software Test Plan or Literature Review file was available in the selected project folder.
9. The selected Downloads folder is not a Git working tree. No commit or push was made.

## Run instructions

From the project folder in PowerShell, `.env` is already configured for the restricted development role/database:

```powershell
python -m streamlit run dashboard/app.py
```

Open `http://127.0.0.1:8501`. To recheck the schema, use the migration owner and then:

```powershell
python -m techpulse.cli db-health
```

The current process is already serving the app on port 8501. Stop it from its terminal with Ctrl+C before starting another copy.
