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

The source register records a checksum-verified DataCamp-hosted Stack Overflow question-count download used during the local audit. That exact audit copy is not redistributed in this repository because its reuse terms were not established. The repository's existing `data/stackexchange.csv` remains unchanged; its validation identifies an impossible `ios` snapshot (0 questions and 181,334 unanswered) on 2018-02-21. These are cumulative tag-count snapshots, not daily new-question counts. `validate-data` rejects the source and canonical ingestion does not promote it. A presentation feasibility audit is documented in `docs/THREE_DAY_PRESENTATION_RESCUE.md`.

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

Run the tests and dashboard:

```bash
python -m pytest tests/ -v
python -m streamlit run dashboard/app.py
```

Fresh Streamlit sessions start in **Synthetic demonstration · separate SQLite** for a populated walkthrough. Select **Research data · PostgreSQL** explicitly for genuine research records; the modes use separate databases and never fall back into each other. Initialize or idempotently refresh the isolated seeded SQLite store with `python -m dashboard.demo_store --build`. It lives at `outputs/synthetic_demo/techpulse_demo.sqlite` and is populated with 210 technologies, 15,120 monthly community rows, 8,400 fictional discussions, 3,360 survey-like observations, 300 fictional company profiles, 2,000 adoption scenarios, 1,260 geographic scenarios (630 Kenya-labelled fictional examples), 8,820 feature snapshots, four trained synthetic model runs, 840 persisted predictions, probabilities and 1,470 SHAP explanations. All records carry `SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE` and must not be cited as research evidence. A controlled reset makes a backup first: `python -m dashboard.demo_store --reset-demo --confirm-reset "RESET SYNTHETIC DEMO ONLY"`.

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

The current checked state and limitations are in [the final audit](docs/FINAL_AUDIT_REPORT.md), [data lineage and quality](docs/DATA_LINEAGE_AND_QUALITY.md), [model evaluation status](docs/MODEL_EVALUATION_REPORT.md), and the [three-day rescue and implementation status](docs/THREE_DAY_PRESENTATION_RESCUE.md). Use the [presentation route](docs/PRESENTATION_DEMO_GUIDE.md) for research mode and the [final presentation runbook](docs/FINAL_PRESENTATION_RUNBOOK.md) for the explicitly synthetic walkthrough. PostgreSQL has 2 migrations and 267 technologies, but no curated community rows, Kenya observations, live observations, or valid canonical model runs/predictions. The local Stack Exchange validation is intentionally blocked by two impossible zero-total source records; synthetic model results are not research metrics.

To prepare the presentation in PowerShell, run `python -m techpulse.cli db-health` and then `python -m streamlit run dashboard/app.py`. See [pgAdmin 4 and database setup](docs/POSTGRESQL_PGADMIN4.md) if health reports a connection or schema issue.

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

For setup of a Codespace-local PostgreSQL database, first-run simulation, and Streamlit port forwarding, follow [the GitHub Codespaces run guide](docs/GITHUB_CODESPACES.md). The annotated presentation walkthrough is [here](docs/final_presentation/TechPulse_Demo_Walkthrough.pptx).
