# TechPulse

> Assessing Developer Technology Trajectories Using Community Signals and Transparent Validation  
> KCA University BSc. Data Science Final Year Project 2026

![Python](https://img.shields.io/badge/PYTHON-3.10+-00FF00?style=for-the-badge&logo=python&logoColor=white&labelColor=0D1117&color=00FF00)
![PostgreSQL](https://img.shields.io/badge/DATABASE-PostgreSQL_14+-00FF00?style=for-the-badge&logo=postgresql&logoColor=white&labelColor=0D1117&color=00FF00)
![scikit-learn](https://img.shields.io/badge/ML-scikit--learn-00FF00?style=for-the-badge&logo=scikitlearn&logoColor=white&labelColor=0D1117&color=00FF00)
![XGBoost](https://img.shields.io/badge/ML-XGBoost-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
![SHAP](https://img.shields.io/badge/XAI-SHAP-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
![Streamlit](https://img.shields.io/badge/DASHBOARD-Streamlit-00FF00?style=for-the-badge&logo=streamlit&logoColor=white&labelColor=0D1117&color=00FF00)
![License](https://img.shields.io/badge/LICENSE-MIT-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)

TechPulse is a supervised machine-learning and dashboard project that classifies software-technology trajectory observations as `Growing`, `Stable`, or `Declining`.

It combines community activity with clearly marked development proxies for enterprise adoption and developer sentiment, then presents trajectory estimates, decline-risk style rankings, model confidence, SHAP explanations, baselines, and validation diagnostics through a Streamlit dashboard.

The current implementation is runnable end to end for development using local repository CSVs. It also includes a PostgreSQL ingestion path for a fuller research warehouse when `DATABASE_URL` is configured. Local development output is useful for engineering validation, not for claiming real-world decline prediction accuracy.

---

## Current Implementation Status

Implemented and verified:

- PostgreSQL-first data ingestion with environment-based `DATABASE_URL`.
- Local CSV development fallback using `data/stackexchange.csv` and `data/fortune.csv`.
- Data-source provenance written to `outputs/data_sources.json`.
- EDA reporting and charts under `outputs/`.
- Technology-month feature matrix with observation months and future-window target fields.
- Future-window trajectory labelling based on later community activity, with future target fields excluded from model features.
- Chronological train/test validation when observation months are available.
- Logistic Regression, K-Nearest Neighbours, Random Forest, and XGBoost where class support allows them.
- Majority-class and momentum-rule baselines in `outputs/model_comparison.csv`.
- Weighted F1, accuracy, precision, recall, ROC-AUC only when statistically meaningful, confusion matrices, and `outputs/evaluation_summary.json`.
- Best-model persistence in `models/best_model.joblib`.
- Dashboard prediction artifact in `outputs/technology_predictions.csv`.
- SHAP global and local explanation artifacts.
- Presentation-ready Streamlit dashboard with a dark terminal/technology-intelligence visual identity.
- Dockerfile and `.dockerignore`.
- GitHub Actions CI workflow for tests, pipeline smoke test, and Docker build.

Verified locally:

```text
pytest tests/ -v
19 passed
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

## Streamlit Verification

```text
python -m streamlit run dashboard/app.py --server.headless=true --server.port=8501
```

The current dashboard uses a restrained institutional data-intelligence visual system. Previously captured green-terminal screenshots were removed from the README because they no longer represent the application after the redesign.

To refresh these screenshots after a dashboard change, start Streamlit and run:

```text
node scripts/capture_live_evidence.js
```

---

## Important Data Note

When `DATABASE_URL` is not set, TechPulse runs in local development mode.

In this mode:

- `data/stackexchange.csv` supplies Stack Exchange community activity.
- `data/fortune.csv` supplies Fortune-style company profile data.
- `data/developer_survey_usage.csv`, when present, supplies observed Stack Overflow Developer Survey technology usage, interest, and admiration shares.
- Adoption-stack, metadata, and question-company mapping tables remain deterministic development proxies unless a PostgreSQL research warehouse supplies real tables.
- The dashboard clearly marks this as development data.

Development data is suitable for smoke testing, dashboard demonstrations, validating pipeline integration, and UI development. It is not suitable for final empirical research claims, real investment decisions, or claiming real-world prediction accuracy.

For research-grade output, configure PostgreSQL with the full expected warehouse schema and set `DATABASE_URL`.

---

## System Architecture

Simple recruiter-friendly view:

```mermaid
flowchart LR
    classDef source fill:#06222b,stroke:#00d9ff,color:#e8fbff,stroke-width:1.5px
    classDef analytics fill:#09241f,stroke:#00c896,color:#eafff8,stroke-width:1.5px
    classDef feature fill:#0b2514,stroke:#00ff66,color:#effff3,stroke-width:1.5px
    classDef ml fill:#2b1807,stroke:#ff9f1c,color:#fff3e0,stroke-width:1.5px
    classDef explain fill:#2b0f2f,stroke:#ff3d9a,color:#ffeafa,stroke-width:1.5px
    classDef app fill:#082333,stroke:#00d9ff,color:#e8fbff,stroke-width:1.5px
    classDef user fill:#f2f5f4,stroke:#9aa7a0,color:#101418,stroke-width:1.5px
    classDef devops fill:#0d1b35,stroke:#6ea8ff,color:#edf5ff,stroke-width:1.5px

    DATA["Raw Ecosystem Data<br/>Stack Exchange, sentiment,<br/>Fortune 500, metadata"]:::source
    INGEST["Ingestion and Validation<br/>PostgreSQL or local CSV fallback"]:::analytics
    SQL["12 SQL Analytics Queries<br/>descriptive foundation"]:::analytics
    SIGNALS["7 Predictive Signals<br/>health, momentum, quality,<br/>diversity, sentiment, adoption, decay"]:::feature
    LABELS["Target Labels<br/>Growing, Stable, Declining"]:::feature
    MODELS["Model Competition<br/>LR, KNN, Random Forest, XGBoost"]:::ml
    SELECT["Champion Model<br/>selected by Weighted F1"]:::ml
    SHAP["SHAP Explainability<br/>global and local reasons"]:::explain
    PREDICT["Prediction Engine<br/>trajectory, risk, confidence"]:::app
    DASH["Streamlit Intelligence Platform<br/>Command Center, Rankings,<br/>Model Laboratory, Methodology"]:::app
    USERS["Decision Support<br/>developers, researchers,<br/>engineering and technology leaders"]:::user
    DEVOPS["Reproducibility<br/>pytest, flake8, CI, Docker"]:::devops

    DATA -->|raw records| INGEST -->|validated data| SQL -->|aggregated signals| SIGNALS
    SIGNALS --> LABELS --> MODELS --> SELECT --> SHAP
    SELECT --> PREDICT
    SHAP --> PREDICT
    PREDICT --> DASH --> USERS
    DEVOPS -. validates and packages .-> INGEST
    DEVOPS -. tests pipeline and app .-> DASH
```

Detailed implementation architecture:

```mermaid
flowchart TB
    classDef source fill:#06222b,stroke:#00d9ff,color:#e8fbff,stroke-width:1.5px
    classDef ingest fill:#071c18,stroke:#21d19f,color:#eafff8,stroke-width:1.5px
    classDef storage fill:#211032,stroke:#bf66ff,color:#f5eaff,stroke-width:1.5px
    classDef sql fill:#09241f,stroke:#00c896,color:#eafff8,stroke-width:1.5px
    classDef feature fill:#0b2514,stroke:#00ff66,color:#effff3,stroke-width:1.5px
    classDef target fill:#2a2308,stroke:#ffc857,color:#fff8db,stroke-width:1.5px
    classDef ml fill:#2b1807,stroke:#ff9f1c,color:#fff3e0,stroke-width:1.5px
    classDef eval fill:#2d2706,stroke:#ffd43b,color:#fffbd1,stroke-width:1.5px
    classDef explain fill:#2b0f2f,stroke:#ff3d9a,color:#ffeafa,stroke-width:1.5px
    classDef app fill:#082333,stroke:#00d9ff,color:#e8fbff,stroke-width:1.5px
    classDef artifact fill:#161b22,stroke:#8fb7a1,color:#e6fff1,stroke-width:1.5px
    classDef user fill:#f2f5f4,stroke:#9aa7a0,color:#101418,stroke-width:1.5px
    classDef devops fill:#0d1b35,stroke:#6ea8ff,color:#edf5ff,stroke-width:1.5px
    classDef caution fill:#301d05,stroke:#ffc857,color:#fff8db,stroke-width:1.5px,stroke-dasharray: 5 3

    subgraph SOURCES["DATA SOURCES AND RESEARCH SIGNALS"]
        SO["Stack Overflow / Stack Exchange<br/>questions, tags, unanswered pressure,<br/>historical activity"]:::source
        SENT["Developer Sentiment Signal<br/>satisfaction, adoption intent,<br/>learning difficulty, sentiment trends"]:::source
        ENT["Enterprise Adoption<br/>Fortune 500 technology usage,<br/>companies, industries, sectors"]:::source
        COMP["Company Metadata<br/>company profiles, sectors,<br/>parent-company relationships"]:::source
        TECH["Technology Metadata<br/>technology names, categories,<br/>aliases and relationships"]:::source
        LOCAL["Local Development CSVs<br/>data/stackexchange.csv<br/>data/fortune.csv"]:::caution
    end

    subgraph INGEST["DATA INGESTION AND QUALITY CONTROL"]
        ENV["Environment Configuration<br/>DATABASE_URL, APP_ENV,<br/>MODEL_PATH, JWT_SECRET placeholder"]:::ingest
        ING["src/data_ingestion.py<br/>PostgreSQL-first loader"]:::ingest
        FALLBACK["CSV Development Fallback<br/>deterministic derived demo tables<br/>clearly marked as development data"]:::caution
        SCHEMA["Schema Validation<br/>required tables and columns"]:::ingest
        QUALITY["Data Quality Diagnostics<br/>missing values, invalid types,<br/>low row counts, malformed records"]:::ingest
        CLEAN["Cleaning and Normalization<br/>date parsing, numeric coercion,<br/>technology-name standardization"]:::ingest
        PROVENANCE["Data Provenance Report<br/>outputs/data_sources.json<br/>outputs/data_quality_report.json"]:::artifact
    end

    subgraph STORAGE["POSTGRESQL DATA LAYER / LOCAL DEVELOPMENT FRAMES"]
        PG["PostgreSQL 14+ Warehouse<br/>used when DATABASE_URL is configured"]:::storage
        T1["so_questions"]:::storage
        T2["dev_sentiment"]:::storage
        T3["fortune500_stacks"]:::storage
        T4["company_profiles"]:::storage
        T5["tech_metadata"]:::storage
        T6["question_company_mapping"]:::storage
        DEVFRAMES["Development DataFrames<br/>same six-table contract<br/>derived where source tables are absent"]:::caution
    end

    subgraph SQL["SQL ANALYTICS FOUNDATION - 12 QUERIES"]
        subgraph BASIC["Basic Analytics"]
            Q1["Q1 Trending Technologies"]:::sql
            Q2["Q2 Learning Difficulty"]:::sql
            Q3["Q3 Monthly Trends"]:::sql
        end
        subgraph INTERMEDIATE["Intermediate Analytics"]
            Q4["Q4 Company Tag Volume"]:::sql
            Q5["Q5 Category Rollups"]:::sql
            Q6["Q6 Hardest Tech per Company"]:::sql
            Q7["Q7 Growth Momentum"]:::sql
        end
        subgraph ADVANCED["Advanced Analytics"]
            Q8["Q8 Parent-Company Portfolio"]:::sql
            Q9["Q9 Technology Health Score"]:::sql
            Q10["Q10 Question Quality"]:::sql
            Q11["Q11 Intraday Patterns"]:::sql
            Q12["Q12 Stack Diversity"]:::sql
        end
        RESULTS["results/ and SQL outputs<br/>descriptive analytics foundation"]:::artifact
    end

    subgraph FEATURES["FEATURE ENGINEERING ENGINE"]
        FE["src/feature_engineering.py<br/>aggregation, historical windows,<br/>missing-value handling, outlier-safe ratios"]:::feature
        F1["Technology Health Score"]:::feature
        F2["Growth Momentum Index"]:::feature
        F3["Question Quality Score"]:::feature
        F4["Company Diversity Score"]:::feature
        F5["Sentiment Delta"]:::feature
        F6["Adoption Velocity"]:::feature
        F7["Community Decay Rate"]:::feature
        NORM["Feature Validation<br/>min-max normalization to 0..1<br/>feature_schema.json"]:::feature
        MATRIX["data/feature_matrix.csv<br/>technology-month panel"]:::artifact
    end

    subgraph TARGETS["TARGET ENGINEERING"]
        LAB["src/labelling.py<br/>future-window trajectory labels"]:::target
        GROW["Growing"]:::target
        STABLE["Stable"]:::target
        DECLINE["Declining"]:::target
        DIST["outputs/labelling_summary.json<br/>class distribution"]:::artifact
    end

    subgraph ML["MACHINE LEARNING EXPERIMENTATION"]
        TRAIN["src/model_training.py<br/>RANDOM_STATE = 42"]:::ml
        SPLIT["Chronological Train-Test Split"]:::ml
        CV["Stratified CV<br/>only when class counts support it"]:::ml
        TUNE["Hyperparameter Tuning<br/>reasonable grids/random search"]:::ml
        LR["Logistic Regression<br/>interpretable baseline"]:::ml
        KNN["K-Nearest Neighbours<br/>non-parametric baseline"]:::ml
        RF["Random Forest<br/>ensemble classifier"]:::ml
        XGB["XGBoost<br/>gradient boosting classifier"]:::ml
        PROBA["Class Probability Estimation<br/>P(Growing), P(Stable), P(Declining)"]:::ml
    end

    subgraph EVALUATION["MODEL EVALUATION AND SELECTION"]
        EVAL["src/evaluation.py<br/>held-out metrics and comparison"]:::eval
        M1["Accuracy"]:::eval
        M2["Precision"]:::eval
        M3["Recall"]:::eval
        M4["Weighted F1<br/>primary selection metric"]:::eval
        M5["ROC-AUC<br/>where calculable"]:::eval
        M6["Confusion Matrix"]:::eval
        COMPARE["Model Comparison<br/>outputs/model_comparison.csv"]:::artifact
        BEST["Best Model / Champion<br/>selected by Weighted F1"]:::eval
    end

    subgraph ARTIFACTS["MODEL AND ANALYTICS ARTIFACTS"]
        MODELFILE["models/best_model.joblib<br/>selected estimator and preprocessing metadata"]:::artifact
        MODELMETA["Feature columns, class labels,<br/>train/test split metadata"]:::artifact
        PREDCSV["outputs/technology_predictions.csv<br/>technology-level predictions"]:::artifact
        EDA["outputs/eda_report.json<br/>EDA plots and data summaries"]:::artifact
    end

    subgraph SHAP["EXPLAINABILITY LAYER"]
        SHAPRUN["src/shap_analysis.py<br/>explains champion model"]:::explain
        GLOBAL["Global Explanation<br/>feature importance, summary plot,<br/>SHAP bar chart"]:::explain
        LOCALX["Local Explanation<br/>technology-specific feature contributions"]:::explain
        SHAPOUT["SHAP Artifacts<br/>global_feature_importance.csv<br/>shap_per_prediction.json<br/>shap_summary_beeswarm.png"]:::artifact
    end

    subgraph PREDICT["PREDICTION ENGINE"]
        SELECTTECH["Selected Technology"]:::app
        VECTOR["Seven-Signal Feature Vector"]:::app
        PREP["Preprocessing Metadata<br/>imputation and feature ordering"]:::app
        CHAMP["Champion Model Inference"]:::app
        CLASSES["Predicted Trajectory<br/>Growing / Stable / Declining"]:::app
        RISK["Decline Risk Score<br/>(1 - P(Growing)) x 100"]:::app
        CONF["Confidence<br/>max(class probability)"]:::app
        WHY["SHAP Explanation<br/>why the model estimated this"]:::app
    end

    subgraph DASH["TECHPULSE INTELLIGENCE PLATFORM - STREAMLIT"]
        APP["dashboard/app.py<br/>custom navigation and terminal UI shell"]:::app
        UI["dashboard/components/ui.py<br/>status badges, metric cards,<br/>shared theme and sidebar"]:::app
        HOME["Command Center<br/>KPIs, search, trajectory,<br/>probabilities, signal matrix"]:::app
        RANK["Global Rankings<br/>risk filters, category filters,<br/>top-risk chart, CSV export"]:::app
        LABVIEW["Model Laboratory<br/>champion model, metrics,<br/>confusion matrix, metric explainers"]:::app
        ABOUT["About / Methodology<br/>research context, limitations,<br/>data licences, academic context"]:::app
        EMPTY["Honest Empty States<br/>missing history and enterprise detail<br/>shown as unavailable, not zero"]:::caution
    end

    subgraph USERS["USER DECISION SUPPORT"]
        DS["Data Scientist"]:::user
        LEAD["Technology Leader"]:::user
        MANAGER["Engineering Manager"]:::user
        RECRUITER["Recruiter"]:::user
        RESEARCHER["Researcher"]:::user
        DEV["Developer"]:::user
        SUPPORT["Analytical Decision Support<br/>not automated decision making"]:::user
    end

    subgraph DEVOPS["REPRODUCIBILITY, TESTING, AND DELIVERY"]
        GIT["GitHub Repository"]:::devops
        ACTIONS["GitHub Actions"]:::devops
        TESTS["pytest tests/<br/>ingestion, features, labelling, models"]:::devops
        LINT["flake8 src tests"]:::devops
        PIPECI["Pipeline Smoke Test<br/>python pipeline/run_pipeline.py"]:::devops
        DOCKER["Dockerfile<br/>containerized Streamlit app"]:::devops
        ENVSEC["Secrets and Config<br/>.env excluded, .env.example safe"]:::devops
    end

    SO -->|raw community signal| ING
    SENT -->|sentiment signal| ING
    ENT -->|adoption signal| ING
    COMP -->|company context| ING
    TECH -->|technology context| ING
    LOCAL -->|when DATABASE_URL is empty| FALLBACK
    ENV --> ING
    ING --> SCHEMA --> QUALITY --> CLEAN --> PROVENANCE
    ING -->|validated records| PG
    FALLBACK -->|development records| DEVFRAMES
    PG --> T1 & T2 & T3 & T4 & T5 & T6
    DEVFRAMES --> T1 & T2 & T3 & T4 & T5 & T6

    T1 & T2 & T3 & T4 & T5 & T6 -->|analytical SQL| BASIC
    BASIC --> INTERMEDIATE --> ADVANCED --> RESULTS
    RESULTS -->|aggregated signals| FE
    T1 -->|volume, quality, decay| FE
    T2 -->|sentiment trend| FE
    T3 -->|adoption velocity| FE
    T4 -->|sector diversity| FE
    T5 -->|categories| FE

    FE --> F1 & F2 & F3 & F4 & F5 & F6 & F7
    F1 & F2 & F3 & F4 & F5 & F6 & F7 --> NORM --> MATRIX
    MATRIX --> LAB
    LAB --> GROW & STABLE & DECLINE
    LAB --> DIST
    MATRIX --> TRAIN
    DIST --> TRAIN

    TRAIN --> SPLIT --> CV --> TUNE
    TUNE --> LR & KNN & RF & XGB
    LR & KNN & RF & XGB --> PROBA --> EVAL
    EVAL --> M1 & M2 & M3 & M4 & M5 & M6
    M1 & M2 & M3 & M4 & M5 & M6 --> COMPARE --> BEST
    BEST --> MODELFILE
    BEST --> SHAPRUN
    TRAIN --> MODELMETA
    EVAL --> PREDCSV
    MATRIX --> EDA

    SHAPRUN --> GLOBAL & LOCALX --> SHAPOUT
    MODELFILE --> CHAMP
    MODELMETA --> PREP
    PREDCSV --> CLASSES
    SELECTTECH --> VECTOR --> PREP --> CHAMP --> PROBA
    PROBA --> CLASSES
    PROBA --> RISK
    PROBA --> CONF
    SHAPOUT --> WHY

    CLASSES & RISK & CONF & WHY --> APP
    PREDCSV --> HOME & RANK
    COMPARE --> LABVIEW
    SHAPOUT --> HOME
    PROVENANCE --> UI
    APP --> UI --> HOME & RANK & LABVIEW & ABOUT & EMPTY
    HOME & RANK & LABVIEW & ABOUT --> SUPPORT
    SUPPORT --> DS & LEAD & MANAGER & RECRUITER & RESEARCHER & DEV

    GIT --> ACTIONS
    ACTIONS --> TESTS & LINT & PIPECI
    ACTIONS --> DOCKER
    ENVSEC --> ING
    TESTS -. validates .-> ING
    TESTS -. validates .-> FE
    TESTS -. validates .-> LAB
    TESTS -. validates .-> TRAIN
    PIPECI -. regenerates .-> MATRIX
    PIPECI -. verifies .-> SHAPRUN
    DOCKER -. packages .-> APP
    EVAL -. iterative improvement .-> FE
```

Diagram source files:

- `docs/architecture-simple.mmd`
- `docs/architecture.mmd`

---

## Signal Families

| Signal Family | Source | What It Captures |
|---|---|---|
| Community Activity | Stack Overflow / Stack Exchange activity | Question volume, unanswered pressure, engagement, community decay |
| Enterprise / Company Context | Local Fortune company profiles plus optional warehouse tables | Sector context in local mode; real adoption only when supplied by a research warehouse |
| Developer Survey Usage | Official Stack Overflow Developer Survey archive | Yearly technology usage, interest, and admiration shares |

---

## Engineered Features

The pipeline produces these seven predictive features:

| Feature | Meaning |
|---|---|
| `technology_health_score` | Composite health score across available community, survey, and adoption/proxy signals |
| `growth_momentum_index` | Recent question volume relative to trailing historical activity |
| `question_quality_score` | Answer availability adjusted for closure/unresolved pressure |
| `company_diversity_score` | Breadth of observed sectors where real/proxy company context exists |
| `sentiment_delta` | As-of change in public developer-survey usage share when available |
| `adoption_velocity` | Adoption velocity where real adoption dates exist; proxy-only in local development mode |
| `community_decay_rate` | Recent decline pressure in community activity |

All seven final predictive features are normalized to `[0, 1]`.

---

## Machine Learning Pipeline

## Methodological Validity

TechPulse now uses a temporal target design when dated Stack Exchange activity is available.

- Target definition: labels compare future average monthly question volume against the recent observed average for the same technology.
- Feature observation window: model features are computed from activity up to the observation month, not from later activity.
- Prediction horizon: local development mode uses future-window community activity fields such as `future_avg_monthly_volume` only to construct labels.
- Leakage control: future-window fields are listed in `TARGET_LEAKAGE_COLUMNS` and are excluded from `FEATURE_COLUMNS`.
- Validation split: model training uses a chronological holdout when `observation_month` exists; random splitting is a fallback for small synthetic fixtures.
- Metric honesty: ROC-AUC is left unavailable when the held-out split lacks all classes, and warnings are written to `outputs/evaluation_summary.json`.
- Local-data limitation: local fallback data is not research-grade evidence of real technology decline because enterprise adoption, metadata, and mapping tables remain deterministic proxies. Survey usage is observed public data but is not the same as enterprise adoption or direct sentiment.

---

The model-training stage trains and compares:

| Model | Purpose |
|---|---|
| Logistic Regression | Interpretable baseline |
| K-Nearest Neighbours | Non-parametric baseline |
| Random Forest | Ensemble model with feature importances |
| XGBoost | Gradient boosting model for tabular classification |
| Majority-class baseline | Minimum sanity-check baseline |
| Momentum-rule baseline | Transparent non-ML comparison |

Evaluation protocol:

- `RANDOM_STATE = 42`
- chronological train/test split when observation months are available
- stratified cross-validation where class counts allow it
- baseline comparison against majority-class and momentum-rule predictors
- weighted F1 as the primary model-selection metric
- ROC-AUC only when the held-out split contains all classes
- best model persisted for dashboard use
- SHAP applied to the selected model

For small or imbalanced development datasets, cross-validation folds are reduced or heavier models are skipped when class counts cannot support them. This avoids reporting invalid experiments as if they were research-grade evidence.

---

## Dashboard

The Streamlit dashboard is implemented as a restrained institutional technology-intelligence interface using charcoal surfaces, ivory text, and champagne accents.

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

### Acquire Public Data

```bash
python scripts/acquire_public_data.py --years 2021 2022 2023 2024
```

This downloads permitted official Stack Overflow Developer Survey files into the ignored raw cache under `data/raw_external/`, then writes the derived `data/developer_survey_usage.csv` and `outputs/data_provenance.json`.

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
outputs/data_provenance.json
outputs/eda_report.json
outputs/model_comparison.csv
outputs/best_model_selection.json
outputs/evaluation_summary.json
outputs/target_leakage_columns.json
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
- Developer survey usage shares are observed public survey data, but local enterprise adoption, metadata, and mapping tables are still proxies.
- The local temporal panel may not contain all three target classes; evaluation warnings should be read before interpreting metrics.
- The current local Stack Exchange observations predate the 2021-2024 survey window, so survey usage is documented but unavailable as an as-of feature for the local 2016-2018 prediction rows.
- Historical trend and sector-level enterprise visualizations require richer source artifacts than the local fallback currently provides.
- ROC-AUC is unavailable when a held-out split lacks all classes.
- The dashboard is a research-support tool, not a guaranteed forecasting system.

---

## Data Sources and Licences

| Dataset | Source | Licence |
|---|---|---|
| Stack Overflow / Stack Exchange activity | Stack Exchange data sources | CC BY-SA where applicable |
| Developer survey usage / interest / admiration | Official Stack Overflow Developer Survey archive | ODbL 1.0 / DbCL 1.0 |
| Fortune 500 company profile data | Public/aggregated local CSV | Open/public data; not evidence of stack adoption |
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
  title        = {TechPulse: Assessing Developer Technology Trajectories Using Community Signals and Transparent Validation},
  year         = {2026},
  institution  = {KCA University},
  note         = {BSc. Data Science Final Year Project, STU 4101},
  orcid        = {0009-0007-6899-8590}
}
```

---

TechPulse · KCA University · 2026
