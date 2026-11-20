# TechPulse

**Predicting Developer Technology Decline Using Community Signals and Enterprise Adoption Patterns: A Machine Learning Approach**
Final-year BSc Data Science project · KCA University · 2026

This is the approved project title. The current supplied evidence does not support a validated decline prediction; the implementation and presentation materials state that limitation rather than changing the research question or presenting unsupported results.

TechPulse is a research prototype that combines community activity, developer-survey summaries, SQL analytics and a Streamlit dashboard to explore `Growing`, `Stable` and `Declining` technology-trajectory labels. It is designed to make the data flow and evaluation visible, not to make investment or hiring decisions.

## What it contains

- Python ingestion, validation, feature engineering and model-comparison pipeline.
- Twelve PostgreSQL analytics queries, from descriptive trends to diversity and technology-health summaries.
- Candidate models: Logistic Regression, K-Nearest Neighbours, Random Forest and XGBoost where class support allows.
- Majority-class and momentum-rule baselines.
- Streamlit views for overview, rankings, model performance and methodology.
- Explainability outputs and Docker packaging.

## Historical evaluation records

The current files contain conflicting prior-run metrics: this README had Random Forest accuracy 0.966 / weighted F1 0.955, while outputs/model_comparison.md records XGBoost accuracy 1.000 / weighted F1 1.000. The run artifacts needed to reconcile those figures are absent from this supplied folder. Neither is a current, independently auditable result. See docs/DATA_LINEAGE_AUDIT.md; new runs are stored under versioned outputs/runs directories.

## Data and limitations

The repository includes local CSV development files. The new canonical CLI uses PostgreSQL only when DATABASE_URL is configured; connection failure is explicit. Official Stack Overflow Developer Survey data is represented by a pre-aggregated local summary with incomplete file-level provenance.

The current local fallback also contains deterministic development proxies for company adoption, metadata and mappings. Those proxies are useful for exercising the application and pipeline, but they are not evidence of actual enterprise technology use. The local community observations predate the 2021–2024 survey summaries, so those survey shares are not valid as-of features for the local historical prediction rows. Survey responses are self-selected and do not represent all developers.

Treat the dashboard as an academic research aid. Do not use its predictions as the basis for technology investment, hiring, platform migration or strategy decisions. See [methodology](docs/methodology.md), [data provenance](outputs/data_provenance.json) and the [architecture diagram](docs/architecture-simple.mmd).

## Canonical PostgreSQL workflow

The legacy SQL files and six-table ingestion adapter are retained for historical comparison. The canonical, additive PostgreSQL contract is in the numbered `migrations/` directory. It separates raw payloads, staging, curated facts, analytics, ML runs, and audit lineage. No tables are dropped or renamed.

```bash
python -m pip install -r requirements.txt
# Set DATABASE_URL in an ignored local .env or environment variable.
python -m techpulse.cli db-migrate
python -m techpulse.cli db-health
python -m techpulse.cli validate-data
python -m techpulse.cli ingest --source survey --from-year 2021
```

db-migrate, db-health, and ingest require a reachable configured PostgreSQL database. They never fall back to CSV. Ingestion records raw payloads and promotes Stack Exchange monthly aggregates, global/unspecified survey reports, and company profiles into their matching canonical tables. The supplied Stack Exchange rows end in 2018, so --from-year 2021 produces no community rows. The company file does not produce adoption claims. Use --source survey or --source fortune while the Stack Exchange source is under review; --source all correctly fails the critical data gate. See the PostgreSQL/pgAdmin4 setup, ingestion notes, and lineage audit in docs/.

The official DataCamp-hosted Stack Overflow question-count CSV is now identified in `docs/SOURCE_REGISTER.md` and matches `data/stackexchange (1).csv` by SHA-256. It contains two invalid zero-total snapshots on 2018-02-21: `ios` has 0 questions and 181,334 unanswered, and `amazon-mws` has 0 questions and 0 unanswered. The values are cumulative tag-count snapshots, not daily new-question counts. The raw files remain unchanged; `validate-data` rejects the source and canonical ingestion does not promote it. A presentation feasibility audit is documented in `docs/THREE_DAY_PRESENTATION_RESCUE.md`.

## Run locally

Requires Python 3.10 or later. From the repository root:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS or Linux
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the PostgreSQL dashboard:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env  # set DATABASE_URL to your techpulse_sim PostgreSQL connection
python -m src.db.migrate
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8502
```

Create the `techpulse_sim` database in PostgreSQL/pgAdmin first and point `.env` at it. On a new empty database, run `python -m src.run_all` once to generate the simulated corpus, features, labels, and model results; this command trains models and should not be repeated just to start the presentation. The prepared local database is not included in GitHub. Fresh Streamlit sessions start in **Simulation · PostgreSQL** and read the versioned corpus and outputs from the `sim` and `ml` schemas. The UI uses familiar real technology names as display labels only. All attached histories and outputs are synthetic scenarios, not observations about the named products. It distinguishes the 60 profiles with saved held-out results from the rest of the 300-profile catalogue. Probabilities are not calibrated, and the page does not create live predictions.

The other modes remain separate: **Research · PostgreSQL** is for genuine research-source readiness, and **Legacy demo · PostgreSQL** uses a separate `demo` schema when available. Do not present generated records or metrics as empirical findings. Keep `.env` local and point `DATABASE_URL` only at `techpulse_sim`. See [PostgreSQL setup](docs/POSTGRESQL_PGADMIN4.md), [simulation limits](docs/DATA_SIMULATION.md), and the [presentation run and demo guide](docs/PRESENTATION_UI_IMPLEMENTATION.md).

The historical research pipeline in pipeline/run_pipeline.py still follows the older six-table contract and is not the canonical ingestion workflow. The Streamlit application now uses the PostgreSQL canonical schemas only; if PostgreSQL is unavailable, it displays an error instead of reading CSV artifacts. See [the dashboard data guide](docs/DASHBOARD_POSTGRESQL.md).

To build and run the container:

```bash
docker build -t techpulse .
docker run --rm -p 8501:8501 --env-file .env techpulse
```

Create `.env` locally from `.env.example` only if you need environment-file configuration; keep `.env` untracked.

## Repository map

```text
src/          ingestion, feature engineering, labels, models and evaluation
pipeline/     end-to-end local pipeline
queries/      12 SQL analytics queries
dashboard/    Streamlit app, pages and reusable components
tests/        unit and pipeline tests
data/         small local development inputs
outputs/      evaluation and provenance artifacts
models/       generated model artifacts
```

Detailed references: [SQL schema](docs/schema_diagram.md) · [methodology](docs/methodology.md) · [research proposal and design documents](docs/) · [model comparison](outputs/model_comparison.md).

## Presentation readiness and current evidence status

The current checked state and limitations are in [the final audit](docs/FINAL_AUDIT_REPORT.md), [data lineage and quality](docs/DATA_LINEAGE_AND_QUALITY.md), [model evaluation status](docs/MODEL_EVALUATION_REPORT.md), and [the v1 model diagnostics](docs/MODEL_DIAGNOSTICS.md). The genuine research mode still has no verified Kenya-specific observations or verified enterprise-adoption evidence; its blocked Stack Exchange source is not silently repaired. Separately, the dedicated `techpulse_sim` database contains the explicitly synthetic v1 experiment with saved model runs. Those simulated outputs are technical demonstrations, not research metrics. The [presentation UI implementation note](docs/PRESENTATION_UI_IMPLEMENTATION.md) gives a concise walkthrough and the limits to state aloud.

To prepare the presentation, follow the PostgreSQL dashboard steps above and use port 8502. See [pgAdmin 4 and database setup](docs/POSTGRESQL_PGADMIN4.md) if the app reports a database connection issue.

Current design references: architecture, model methodology, source register, and responsible use documents in docs/.

## Data use

Respect the source data licences recorded in the provenance files. Do not commit secrets, private datasets, or data that identifies individuals. Generated models and run outputs should be recreated locally unless an artifact is intentionally reviewed for publication.

## Live technology observations

The **Live Technology Intelligence** page supplements the saved research catalogue with bounded observations from GitHub, Stack Exchange, PyPI and npm. Collection is user-triggered from the dashboard or can run independently through `python scripts/collect_live_data.py` and `python scripts/schedule_live_data.py`. The scheduler supports a one-shot run with `--once` and configurable catalogue selections.

Associations between catalogue technologies and package names are explicit in `data/live_package_map.json`. Observations retain source identifiers and collection timestamps. PostgreSQL mode writes to the additive `techpulse_live_observations` table; local mode appends to `outputs/live_data/live_observations.csv`. Existing pipeline inputs, labels and saved predictions are not changed by live collection. These supplemental counts are descriptive only: stars, questions and package downloads do not establish adoption, unique users or production use. See `docs/LIVE_DATA_IMPLEMENTATION_PLAN.md` for the collection design and limitations.

Copy `.env.example` to `.env` for optional API credentials and settings. Public APIs can be used anonymously within their lower rate limits. Never commit `.env` or credentials.

## Dashboard guides and evidence

Beginner, technical and five-minute presentation guides are provided in `docs/` in Markdown and PDF formats. Browser screenshots for the nine dashboard pages are indexed in `outputs/live_data_screenshots/index_live_data.md`. The live-data test report is `outputs/live_data_test_report.md`.

## GitHub Codespaces

Choose **Code → Codespaces → Create codespace on main**. The repository dev-container automatically provisions a private PostgreSQL service, installs Python requirements, initializes the reproducible simulation database if needed, and starts Streamlit on forwarded port 8501. For an existing Codespace, pull `main` and run **Codespaces: Rebuild Container**. No Windows PostgreSQL install, `sudo`, or manual credentials are needed. See the [Codespaces run guide](docs/GITHUB_CODESPACES.md) and the [annotated PowerPoint walkthrough](docs/final_presentation/TechPulse_Demo_Walkthrough.pptx).
