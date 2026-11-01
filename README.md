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
