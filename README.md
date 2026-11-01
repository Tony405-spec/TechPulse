# TechPulse

**Assessing developer technology trajectories with community signals and transparent validation**
Final-year BSc Data Science project · KCA University · 2026

TechPulse is a research prototype that combines community activity, developer-survey summaries, SQL analytics and a Streamlit dashboard to explore `Growing`, `Stable` and `Declining` technology-trajectory labels. It is designed to make the data flow and evaluation visible, not to make investment or hiring decisions.

## What it contains

- Python ingestion, validation, feature engineering and model-comparison pipeline.
- Twelve PostgreSQL analytics queries, from descriptive trends to diversity and technology-health summaries.
- Candidate models: Logistic Regression, K-Nearest Neighbours, Random Forest and XGBoost where class support allows.
- Majority-class and momentum-rule baselines.
- Streamlit views for overview, rankings, model performance and methodology.
- Explainability outputs and Docker packaging.

## Evaluation snapshot and interpretation

The committed local development snapshot in `outputs/model_comparison.md` reports:

| Model | Accuracy | Weighted F1 |
|---|---:|---:|
| Random Forest | 0.966 | 0.955 |
| Majority-class baseline | 0.966 | 0.949 |

The Random Forest matches the simple baseline on accuracy and is only modestly higher on weighted F1. Macro ROC-AUC is unavailable in this snapshot because the held-out split does not support the calculation. This is not evidence of reliable real-world forecasting; inspect the per-class results and data limitations before interpreting the model.

## Data and limitations

The repository includes a local CSV development fallback. The pipeline can also use PostgreSQL when `DATABASE_URL` is configured. Official Stack Overflow Developer Survey data can be acquired with `scripts/acquire_public_data.py` and is aggregated into technology-year usage, interest and admiration shares.

The current local fallback also contains deterministic development proxies for company adoption, metadata and mappings. Those proxies are useful for exercising the application and pipeline, but they are not evidence of actual enterprise technology use. The local community observations predate the 2021–2024 survey summaries, so those survey shares are not valid as-of features for the local historical prediction rows. Survey responses are self-selected and do not represent all developers.

Treat the dashboard as an academic research aid. Do not use its predictions as the basis for technology investment, hiring, platform migration or strategy decisions. See [methodology](docs/methodology.md), [data provenance](outputs/data_provenance.json) and the [architecture diagram](docs/architecture-simple.mmd).

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

Run the tests, pipeline, then dashboard:

```bash
python -m pytest tests/ -v
python pipeline/run_pipeline.py
python -m streamlit run dashboard/app.py
```

With no `DATABASE_URL`, the app uses the local development CSVs. For database mode, configure `DATABASE_URL` in the environment. Do not commit credentials or copy the development-only placeholder secret from `.env.example` into a real deployment.

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

## Data use

Respect the source data licences recorded in the provenance files. Do not commit secrets, private datasets, or data that identifies individuals. Generated models and run outputs should be recreated locally unless an artifact is intentionally reviewed for publication.

## Live technology observations

The **Live Technology Intelligence** page supplements the saved research catalogue with bounded observations from GitHub, Stack Exchange, PyPI and npm. Collection is user-triggered from the dashboard or can run independently through `python scripts/collect_live_data.py` and `python scripts/schedule_live_data.py`. The scheduler supports a one-shot run with `--once` and configurable catalogue selections.

Associations between catalogue technologies and package names are explicit in `data/live_package_map.json`. Observations retain source identifiers and collection timestamps. PostgreSQL mode writes to the additive `techpulse_live_observations` table; local mode appends to `outputs/live_data/live_observations.csv`. Existing pipeline inputs, labels and saved predictions are not changed by live collection. These supplemental counts are descriptive only: stars, questions and package downloads do not establish adoption, unique users or production use. See `docs/LIVE_DATA_IMPLEMENTATION_PLAN.md` for the collection design and limitations.

Copy `.env.example` to `.env` for optional API credentials and settings. Public APIs can be used anonymously within their lower rate limits. Never commit `.env` or credentials.

## Dashboard guides and evidence

Beginner, technical and five-minute presentation guides are provided in `docs/` in Markdown and PDF formats. Browser screenshots for the nine dashboard pages are indexed in `outputs/live_data_screenshots/index_live_data.md`. The live-data test report is `outputs/live_data_test_report.md`.