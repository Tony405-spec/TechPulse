# TechPulse ⚡

> **Predicting Developer Technology Decline Using Community Signals and Enterprise Adoption Patterns**
> A Machine Learning Platform · KCA University BSc. Data Science · Final Year Project 2026

![Python](https://img.shields.io/badge/PYTHON-3.10+-00FF00?style=for-the-badge&logo=python&logoColor=white&labelColor=0D1117&color=00FF00)
![PostgreSQL](https://img.shields.io/badge/DATABASE-PostgreSQL_14+-00FF00?style=for-the-badge&logo=postgresql&logoColor=white&labelColor=0D1117&color=00FF00)
![scikit-learn](https://img.shields.io/badge/ML-scikit--learn-00FF00?style=for-the-badge&logo=scikitlearn&logoColor=white&labelColor=0D1117&color=00FF00)
![XGBoost](https://img.shields.io/badge/ML-XGBoost-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
![SHAP](https://img.shields.io/badge/XAI-SHAP-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
![Streamlit](https://img.shields.io/badge/DASHBOARD-Streamlit-00FF00?style=for-the-badge&logo=streamlit&logoColor=white&labelColor=0D1117&color=00FF00)
![Queries](https://img.shields.io/badge/SQL-12_QUERIES-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
![License](https://img.shields.io/badge/LICENSE-MIT-00FF00?style=for-the-badge&logoColor=white&labelColor=0D1117&color=00FF00)
[![CI](https://github.com/skynet-datagrid-labs/TechPulse/actions/workflows/ci.yml/badge.svg)](https://github.com/skynet-datagrid-labs/TechPulse/actions/workflows/ci.yml)

---

## What is TechPulse?

Technology adoption decisions carry measurable financial and career risk. When a technology enters silent decline, organisations face costly migrations and developers face obsolescence — yet most stakeholders still rely on trend articles and informal opinion rather than empirical evidence.

**TechPulse** is a supervised machine learning system that classifies software technologies as **Growing**, **Stable**, or **Declining** by fusing three distinct signal families:

| Signal Family | Source | What it Captures |
|---|---|---|
| **Community Activity** | Stack Overflow Q&A data | Question volumes, engagement rates, closure rates, answer quality |
| **Enterprise Adoption** | Fortune 500 technology stacks | Adoption depth, sector spread, company diversity |
| **Developer Sentiment** | Annual developer surveys | Satisfaction scores, adoption intent, learning curve ratings |

TechPulse extends the existing [`developer-ecosystem-analytics`](https://gist.github.com/Tony405-spec/82bbd137d85ada850acdffc90c192486) repository — which already aggregates six real-world datasets and twelve descriptive SQL analytics queries — by adding a supervised predictive layer, SHAP explainability, and a publicly deployed interactive dashboard.

> The existing SQL pipeline remains fully intact. TechPulse adds prediction capability on top of it — it does not replace it.

---

## System Architecture

TechPulse is organised into four conceptual layers:

```
┌─────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                     │
│         Streamlit Dashboard · Streamlit Cloud           │
│  Search · Risk Scores · Trends · SHAP · Rankings        │
├─────────────────────────────────────────────────────────┤
│                 EXPLAINABILITY LAYER                    │
│              SHAP TreeExplainer / LinearExplainer       │
│     Global Feature Importance · Per-Prediction SHAP     │
├─────────────────────────────────────────────────────────┤
│            FEATURE ENGINEERING & MODELLING LAYER        │
│   7 Engineered Features · LR · KNN · RF · XGBoost      │
│        5-Fold CV · Weighted F1 · Hyperparameter Tuning  │
├─────────────────────────────────────────────────────────┤
│                     DATA LAYER                          │
│              PostgreSQL 14+ · 6 Datasets                │
│   SO Questions · Sentiment · Fortune500 · Metadata      │
│         12 Descriptive SQL Queries (pre-existing)       │
└─────────────────────────────────────────────────────────┘
```

---

## Engineered Features

Seven predictive features are derived from the six source datasets. All features are min-max normalised to [0, 1].

| Feature | Description | Source Dataset(s) |
|---|---|---|
| `technology_health_score` | Weighted composite of community activity, sentiment, and adoption signals | All 6 datasets (extends SQL Query 9) |
| `growth_momentum_index` | 3-month vs 12-month question volume ratio — measures acceleration | SO Questions |
| `question_quality_score` | Mean answer count × (1 − closure rate) per technology tag | SO Questions |
| `company_diversity_score` | Count of distinct Fortune 500 sectors adopting the technology | Fortune 500 Stacks + Company Profiles |
| `sentiment_delta` | Most recent developer satisfaction score minus earliest available score | Developer Sentiment Survey |
| `adoption_velocity` | Mean new company adoptions per quarter over trailing 4 quarters | Fortune 500 Stacks |
| `community_decay_rate` | % decline in SO question volume over trailing 6 months | SO Questions |

---

## Classification Models

Four classifiers are trained, evaluated, and compared. The model with the highest **weighted F1-score** on the held-out test set is selected for dashboard deployment and SHAP analysis.

| Model | Role | Primary Metrics |
|---|---|---|
| **Logistic Regression** | Interpretable baseline; coefficients compared to SHAP values | Accuracy, Weighted F1 |
| **K-Nearest Neighbours** | Non-parametric baseline; local clustering detection | Accuracy |
| **Random Forest** | Primary advanced model; native feature importances | Accuracy, Weighted F1, ROC-AUC |
| **XGBoost** | Expected best performer on tabular data; gradient boosting with regularisation | Accuracy, Weighted F1, ROC-AUC |

**Evaluation protocol:** 80/20 stratified train-test split · 5-fold stratified cross-validation · `RANDOM_STATE = 42` throughout · Weighted F1 as primary selection criterion (not accuracy) · SHAP applied to best-performing model.

**Target classes:** `Growing` · `Stable` · `Declining`

---

## Dashboard Pages

The interactive Streamlit dashboard is publicly deployed and provides five pages:

| Page | Description |
|---|---|
| **Home / Search** | Search technologies by name; filter by category; view trajectory labels and risk scores |
| **Technology Detail** | Trajectory prediction, risk score gauge, confidence indicator, trend charts, SHAP feature importance, Fortune 500 enterprise adoption heatmap |
| **Global Rankings** | All technologies ranked by risk score (0–100); filterable by category and trajectory label; CSV export |
| **Model Performance** | Four-model comparison table; confusion matrix for best model; plain-English metric explanations |
| **About / Documentation** | Project context, data source licences, model limitations disclaimer, ORCID, GitHub links |

**Risk Score:** Derived as `(1 − P(Growing)) × 100`. A score of 0 means minimal decline risk; 100 means maximum.

**Confidence Indicator:** `Low` if max class probability < 0.60 · `Medium` if 0.60–0.80 · `High` if > 0.80

---

## SQL Query Pipeline (Foundation Layer)

The twelve SQL queries in `queries/` remain the analytical foundation of TechPulse. They are consumed by the feature engineering pipeline and remain independently executable for descriptive analytics.

| Tier | Query | Analytical Function |
|---|---|---|
| **Basic** | Q1 | Top trending technologies by engagement velocity |
| | Q2 | Technology learning difficulty ranking |
| | Q3 | Monthly adoption trend analysis |
| **Intermediate** | Q4 | Company-level tagging volume aggregation |
| | Q5 | Category-level technology rollups |
| | Q6 | Hardest technology per company by adoption friction |
| | Q7 | Growth momentum scoring (velocity + acceleration) |
| **Advanced** | Q8 | Parent-company consolidated technology portfolio analysis |
| | Q9 | Composite technology health scoring (multi-factor weighted) |
| | Q10 | Question quality assessment by response rate and closure ratio |
| | Q11 | Intraday posting pattern analysis |
| | Q12 | Technology stack diversity metrics per company |

Execute any query directly:
```bash
psql "$DATABASE_URL" -f queries/01_basic/query1_top_technologies.sql
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Git

### Installation

```bash
git clone https://github.com/skynet-datagrid-labs/TechPulse.git
cd TechPulse
pip install -r requirements.txt
```

### Environment Setup

```bash
cp .env.example .env
# Edit .env and set your DATABASE_URL:
# DATABASE_URL=postgresql://username:password@localhost:5432/techpulse_db
```

### Run the Full ML Pipeline

```bash
python pipeline/run_pipeline.py
```

This executes all stages end-to-end: data ingestion → EDA → feature engineering → labelling → model training (LR, KNN, RF, XGBoost) → evaluation → SHAP analysis. A timestamped execution log is written to `logs/`.

### Launch the Dashboard Locally

```bash
streamlit run dashboard/app.py
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
TechPulse/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── queries/                           # 12 SQL analytics queries (foundation layer)
│   ├── 01_basic/
│   ├── 02_intermediate/
│   └── 03_advanced/
│
├── data/
│   └── feature_matrix.csv             # Output of feature engineering pipeline
│
├── notebooks/
│   ├── 01_EDA.ipynb
│   ├── 02_Feature_Engineering.ipynb
│   └── 03_Modelling_Evaluation.ipynb
│
├── src/                               # Core ML pipeline modules
│   ├── data_ingestion.py              # FR-01: DB connection and validation
│   ├── eda.py                         # FR-02: EDA report generation
│   ├── feature_engineering.py         # FR-03: 7 engineered features
│   ├── labelling.py                   # FR-04: Trajectory label assignment
│   ├── model_training.py              # FR-05 to FR-09: All 4 classifiers
│   ├── evaluation.py                  # FR-10: Model comparison and selection
│   └── shap_analysis.py               # FR-11: SHAP explainer and plots
│
├── dashboard/                         # Streamlit application
│   ├── app.py
│   ├── pages/
│   │   ├── 1_Home.py
│   │   ├── 2_Rankings.py
│   │   ├── 3_Model_Performance.py
│   │   └── 4_About.py
│   └── components/
│       ├── tech_detail_panel.py
│       ├── trend_charts.py
│       ├── shap_viewer.py
│       └── enterprise_heatmap.py
│
├── pipeline/
│   └── run_pipeline.py                # Master orchestration script
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_features.py
│   ├── test_labelling.py
│   └── test_models.py
│
├── outputs/                           # EDA charts, model comparison, SHAP plots
├── models/                            # Serialised model files (gitignored)
└── logs/                              # Pipeline execution logs (gitignored)
```

---

## Data Sources and Licences

| Dataset | Source | Licence |
|---|---|---|
| Stack Overflow Questions & Tags | Stack Exchange Data Dump | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Developer Sentiment Survey | Stack Overflow Developer Survey 2023/2024 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Fortune 500 Tech Stacks | Aggregated public sources | Open data, aggregated |
| Company Profiles | Aggregated public sources | Open data, aggregated |
| Technology Metadata | Compiled from public registries | Open data |
| Question-Company Mapping | Derived from SO + company datasets | Derived, CC BY-SA 4.0 inherited |

All data is used exclusively for academic research and analytical purposes in accordance with the applicable licences. No personal data is processed.

---

## Academic Context

```
Institution  : KCA University — School of Technology (SoT)
Programme    : Bachelor of Science in Data Science
Course       : STU 4101 — Final Year Project I
Student      : Kitili Tony Kenga
Reg. Number  : 24/03652
ORCID        : 0009-0007-6899-8590
Supervisor   : Dr. Rufus Gireka
Submitted    : 27th June 2026
```

---

## Disclaimer

> TechPulse predictions are for **informational and research purposes only**.
> They must not be used as the sole basis for technology investment, hiring, platform migration, or strategic decisions.
> Prediction accuracy is bounded by the quality and recency of the source datasets.
> All outputs should be interpreted alongside domain expertise and additional evidence.

---

## Citation

If you use TechPulse in your research, please cite:

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

*TechPulse · Skynet DataGrid Labs · KCA University · 2026*
