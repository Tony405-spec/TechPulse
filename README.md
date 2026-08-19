# TechPulse

> Predicting Developer Technology Decline Using Community Signals and Enterprise Adoption Patterns  
> KCA University BSc. Data Science Final Year Project 2026

![Python](https://img.shields.io/badge/PYTHON-3.10+-00FF00?style=for-the-badge&logo=python&logoColor=white&labelColor=0D1117&color=00FF00)
![PostgreSQL](https://img.shields.io/badge/DATABASE-PostgreSQL_14+-00FF00?style=for-the-badge&logo=postgresql&logoColor=white&labelColor=0D1117&color=00FF00)
![scikit-learn](https://img.shields.io/badge/ML-scikit--learn-00FF00?style=for-the-badge&logo=scikitlearn&logoColor=white&labelColor=0D1117&color=00FF00)
![XGBoost](https://img.shields.io/badge/ML-XGBoost-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
![SHAP](https://img.shields.io/badge/XAI-SHAP-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
![Streamlit](https://img.shields.io/badge/DASHBOARD-Streamlit-00FF00?style=for-the-badge&logo=streamlit&logoColor=white&labelColor=0D1117&color=00FF00)
![License](https://img.shields.io/badge/LICENSE-MIT-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)

TechPulse is a supervised machine-learning platform that classifies software technologies as `Growing`, `Stable`, or `Declining`.

It combines community activity, enterprise adoption, and developer sentiment signals, then presents predictions, decline risk, model confidence, SHAP explanations, rankings, and model-performance evidence through a polished Streamlit dashboard.

The current implementation is runnable end to end for development using local repository CSVs. It also includes a PostgreSQL ingestion path for a full production/research warehouse when `DATABASE_URL` is configured.

---

## Current Implementation Status

Implemented and verified:

- PostgreSQL-first data ingestion with environment-based `DATABASE_URL`.
- Local CSV development fallback using `data/stackexchange.csv` and `data/fortune.csv`.
- Data-source provenance written to `outputs/data_sources.json`.
- EDA reporting and charts under `outputs/`.
- Seven predictive features normalized to `[0, 1]`.
- Deterministic trajectory labelling.
- Four classifiers: Logistic Regression, K-Nearest Neighbours, Random Forest, and XGBoost.
- 80/20 stratified train/test split.
- Stratified cross-validation where the dataset supports it.
- Weighted F1 as the primary model-selection metric.
- Accuracy, weighted F1, precision, recall, ROC-AUC where calculable, and confusion matrices.
- Best-model persistence in `models/best_model.joblib`.
- Dashboard prediction artifact in `outputs/technology_predictions.csv`.
- SHAP global and local explanation artifacts.
- Presentation-ready Streamlit dashboard with a dark terminal/technology-intelligence visual identity.
- Dockerfile and `.dockerignore`.
- GitHub Actions CI workflow for tests, pipeline smoke test, and Docker build.

Verified locally:

```text
pytest tests/ -v
13 passed
```

```text
python pipeline/run_pipeline.py
FR-01 through FR-11 PASS
```

```text
python -m streamlit run dashboard/app.py --server.headless=true --server.port=8501
Started successfully
```

Streamlit page execution was also checked with `streamlit.testing.v1.AppTest`: the app plus all four dashboard views ran with zero exceptions.

---

## Important Data Note

When `DATABASE_URL` is not set, TechPulse runs in local development mode.

In this mode:

- `data/stackexchange.csv` supplies Stack Exchange community activity.
- `data/fortune.csv` supplies Fortune-style company profile data.
- Missing sentiment, adoption-stack, metadata, and question-company mapping tables are deterministically derived for development only.
- The dashboard clearly marks this as development data.

Development data is suitable for smoke testing, dashboard demonstrations, validating pipeline integration, and UI development. It is not suitable for final empirical research claims, real investment decisions, or claiming real-world prediction accuracy.

For research-grade output, configure PostgreSQL with the full expected warehouse schema and set `DATABASE_URL`.

---

## System Architecture

```text
EXTERNAL DATA SOURCES
        |
        v
DATA INGESTION
        |
        v
POSTGRESQL DATA LAYER / LOCAL DEVELOPMENT CSV FALLBACK
        |
        v
12 SQL ANALYTICS QUERIES
        |
        v
FEATURE ENGINEERING
        |
        v
7 PREDICTIVE FEATURES
        |
        v
TARGET LABELLING
        |
        v
TRAIN / TEST SPLIT
        |
        v
4 ML CLASSIFIERS
        |
        v
MODEL EVALUATION + BEST MODEL SELECTION
        |
        v
SHAP EXPLAINABILITY
        |
        v
MODEL + OUTPUT ARTIFACTS
        |
        v
STREAMLIT DASHBOARD
```

---

## Signal Families

| Signal Family | Source | What It Captures |
|---|---|---|
| Community Activity | Stack Overflow / Stack Exchange activity | Question volume, unanswered pressure, engagement, community decay |
| Enterprise Adoption | Fortune 500 stack/company data | Adoption depth, company diversity, sector spread, adoption velocity |
| Developer Sentiment | Survey-style sentiment signal | Satisfaction trend and sentiment delta |

---

## Engineered Features

The pipeline produces these seven predictive features:

| Feature | Meaning |
|---|---|
| `technology_health_score` | Composite health score across community, sentiment, and adoption signals |
| `growth_momentum_index` | Recent question volume relative to trailing historical activity |
| `question_quality_score` | Answer availability adjusted for closure/unresolved pressure |
| `company_diversity_score` | Breadth of enterprise sector adoption |
| `sentiment_delta` | Change in developer satisfaction across available observations |
| `adoption_velocity` | Pace of new enterprise adoption over recent quarters |
| `community_decay_rate` | Recent decline pressure in community activity |

All seven final predictive features are normalized to `[0, 1]`.

---

## Machine Learning Pipeline

The model-training stage trains and compares:

| Model | Purpose |
|---|---|
| Logistic Regression | Interpretable baseline |
| K-Nearest Neighbours | Non-parametric baseline |
| Random Forest | Ensemble model with feature importances |
| XGBoost | Gradient boosting model for tabular classification |

Evaluation protocol:

- `RANDOM_STATE = 42`
- 80/20 stratified train/test split
- stratified cross-validation where class counts allow it
- weighted F1 as the primary model-selection metric
- best model persisted for dashboard use
- SHAP applied to the selected model

For tiny development datasets, cross-validation folds are reduced only when a class has too few examples to support 5-fold CV. This prevents invalid training folds while preserving the documented 5-fold protocol for full datasets.

---

## Dashboard

The Streamlit dashboard is implemented as a technology intelligence terminal with a dark, high-contrast analytical interface.

Dashboard entry point:

```bash
python -m streamlit run dashboard/app.py
```

Dashboard areas:

| View | File | What It Shows |
|---|---|---|
| Command Center | `dashboard/views/1_Home.py` | KPIs, technology search, trajectory, decline risk, confidence, probability chart, signal matrix, SHAP/detail panel |
| Global Rankings | `dashboard/views/2_Rankings.py` | Risk ranking, trajectory/category/search/risk filters, top-risk chart, CSV export |
| Model Laboratory | `dashboard/views/3_Model_Performance.py` | Four-model comparison, champion model, metrics, confusion matrix, metric explanations |
| About / Methodology | `dashboard/views/4_About.py` | Project overview, methodology, data sources, explainability, limitations, academic context |

Shared UI components live in `dashboard/components/`.

Notable dashboard behavior:

- Risk score is calculated as `(1 - P(Growing)) * 100`.
- Confidence is based on `max(class_probability)`.
- The app uses persisted predictions instead of retraining at startup.
- Missing historical or enterprise-detail data is shown as unavailable, not fabricated.
- Development/demo data is clearly labelled.

---

## SQL Analytics Foundation

The existing descriptive SQL foundation is preserved under `queries/`:

```text
queries/
├── 01_basic/
├── 02_intermediate/
└── 03_advanced/
```

The twelve query areas are:

| Tier | Query | Analytical Function |
|---|---|---|
| Basic | Q1 | Top trending technologies by engagement velocity |
| Basic | Q2 | Technology learning difficulty ranking |
| Basic | Q3 | Monthly adoption/community trend analysis |
| Intermediate | Q4 | Company-level tagging volume aggregation |
| Intermediate | Q5 | Category-level technology rollups |
| Intermediate | Q6 | Hardest technology per company by adoption friction |
| Intermediate | Q7 | Growth momentum scoring |
| Advanced | Q8 | Parent-company consolidated technology portfolio analysis |
| Advanced | Q9 | Composite technology health scoring |
| Advanced | Q10 | Question quality assessment |
| Advanced | Q11 | Intraday posting pattern analysis |
| Advanced | Q12 | Technology stack diversity metrics |

Example:

```bash
psql "$DATABASE_URL" -f queries/01_basic/query1_top_technologies.sql
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Git
- PostgreSQL 14+ for full warehouse mode

### Install

```bash
git clone https://github.com/Tony405-spec/TechPulse.git
cd TechPulse
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Set these values as needed:

```text
DATABASE_URL=postgresql://username:password@localhost:5432/techpulse_db
JWT_SECRET=change-me-in-local-env-only
APP_ENV=development
MODEL_PATH=models/best_model.joblib
```

`DATABASE_URL` may be left empty for local development mode.

### Run Pipeline

```bash
python pipeline/run_pipeline.py
```

This writes generated artifacts to `outputs/`, `models/`, `logs/`, and `data/feature_matrix.csv`.

### Run Dashboard

```bash
python -m streamlit run dashboard/app.py
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Docker

Build:

```bash
docker build -t techpulse .
```

Run:

```bash
docker run --rm -p 8501:8501 --env-file .env techpulse
```

The container starts Streamlit on port `8501`.

---

## Project Structure

```text
TechPulse/
├── README.md
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env.example
├── .github/workflows/
│
├── data/
│   ├── stackexchange.csv
│   ├── fortune.csv
│   └── feature_matrix.csv          # generated
│
├── queries/
│   ├── 01_basic/
│   ├── 02_intermediate/
│   └── 03_advanced/
│
├── src/
│   ├── data_ingestion.py
│   ├── eda.py
│   ├── feature_engineering.py
│   ├── labelling.py
│   ├── model_training.py
│   ├── evaluation.py
│   └── shap_analysis.py
│
├── pipeline/
│   └── run_pipeline.py
│
├── dashboard/
│   ├── app.py
│   ├── views/
│   │   ├── 1_Home.py
│   │   ├── 2_Rankings.py
│   │   ├── 3_Model_Performance.py
│   │   └── 4_About.py
│   └── components/
│       ├── ui.py
│       ├── tech_detail_panel.py
│       ├── shap_viewer.py
│       ├── trend_charts.py
│       └── enterprise_heatmap.py
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_features.py
│   ├── test_labelling.py
│   └── test_models.py
│
├── outputs/                         # generated EDA, metrics, SHAP, predictions
├── models/                          # generated model artifacts
├── logs/                            # generated logs
├── notebooks/
├── assets/
└── docs/
```

---

## Generated Artifacts

The pipeline creates outputs such as:

```text
outputs/data_quality_report.json
outputs/data_sources.json
outputs/eda_report.json
outputs/model_comparison.csv
outputs/best_model_selection.json
outputs/technology_predictions.csv
outputs/global_feature_importance.csv
outputs/shap_per_prediction.json
outputs/shap_summary_beeswarm.png
outputs/shap_bar_chart.png
models/best_model.joblib
```

Large/generated artifacts are ignored where appropriate and should be regenerated by running the pipeline.

---

## Known Limitations

- The verified local run used development-mode CSV fallback, not a production PostgreSQL warehouse.
- Development-mode sentiment/adoption/metadata/mapping tables are derived for testing and presentation flow.
- Historical trend and sector-level enterprise visualizations require richer source artifacts than the local fallback currently provides.
- ROC-AUC can be unavailable on very small splits when a class is absent from the test fold.
- The dashboard is a research-support tool, not a guaranteed forecasting system.

---

## Data Sources and Licences

| Dataset | Source | Licence |
|---|---|---|
| Stack Overflow / Stack Exchange activity | Stack Exchange data sources | CC BY-SA where applicable |
| Developer sentiment signal | Stack Overflow Developer Survey-style signal | CC BY-SA where applicable |
| Fortune 500 company data | Public/aggregated sources | Open/public data |
| Company profiles | Public/aggregated sources | Open/public data |
| Technology metadata | Public registries / derived metadata | Open/public data |
| Question-company mapping | Derived analytical mapping | Derived research artifact |

All data use should respect the licences of the original sources. TechPulse does not process personal data as part of the current project workflow.

---

## Academic Context

```text
Institution  : KCA University, School of Technology (SoT)
Programme    : Bachelor of Science in Data Science
Course       : STU 4101, Final Year Project I
Student      : Kitili Tony Kenga
Reg. Number  : 24/03652
ORCID        : 0009-0007-6899-8590
Supervisor   : Dr. Rufus Gireka
Year         : 2026
```

---

## Disclaimer

TechPulse predictions are for informational and academic research purposes only.

They must not be used as the sole basis for technology investment, hiring, platform migration, or strategic decisions. Prediction quality depends on source-data quality, recency, and coverage. Interpret all outputs alongside domain expertise and additional evidence.

---

## Citation

```bibtex
@misc{kenga2026techpulse,
  author       = {Kitili Tony Kenga},
  title        = {TechPulse: Predicting Developer Technology Decline Using Community Signals and Enterprise Adoption Patterns},
  year         = {2026},
  institution  = {KCA University},
  note         = {BSc. Data Science Final Year Project, STU 4101},
  orcid        = {0009-0007-6899-8590}
}
```

---

TechPulse · KCA University · 2026
