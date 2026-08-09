# TechPulse 
## System Architecture

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'background': '#0a0a0a',
    'primaryColor': '#00ff41',
    'primaryBorderColor': '#00ff41',
    'primaryTextColor': '#00ff41',
    'lineColor': '#00ff41',
    'secondaryColor': '#0d1f0d',
    'tertiaryColor': '#0a0a0a',
    'fontFamily': 'monospace',
    'fontSize': '14px',
    'mainBkg': '#0a0a0a',
    'nodeBorder': '#00ff41',
    'nodeTextColor': '#00ff41',
    'titleColor': '#00ff41',
    'edgeLabelBackground': '#0a0a0a',
    'nodeTextColor': '#00ff41',
    'clusterBkg': '#0a0a0a',
    'clusterBorder': '#00ff41',
    'clusterTextColor': '#00ff41'
  }
}}%%

graph TB
    %% --- Cyber-Punk Style Definitions ---
    classDef user fill:#00ff41,stroke:#00ff41,stroke-width:2px,color:#0a0a0a,font-weight:bold,font-family:monospace;
    classDef dash fill:#0d1f0d,stroke:#00ff41,stroke-width:2px,color:#00ff41,font-weight:bold,font-family:monospace;
    classDef explain fill:#0d1f0d,stroke:#ff00ff,stroke-width:2px,color:#ff00ff,font-weight:bold,font-family:monospace;
    classDef model fill:#0d1f0d,stroke:#00ffff,stroke-width:2px,color:#00ffff,font-weight:bold,font-family:monospace;
    classDef feature fill:#0d1f0d,stroke:#ffaa00,stroke-width:2px,color:#ffaa00,font-weight:bold,font-family:monospace;
    classDef data fill:#0d1f0d,stroke:#00ff41,stroke-width:2px,color:#00ff41,font-weight:bold,font-family:monospace;
    classDef external fill:#0d1f0d,stroke:#ff4444,stroke-width:2px,color:#ff4444,font-weight:bold,font-family:monospace;
    classDef infra fill:#0d1f0d,stroke:#8888ff,stroke-width:2px,color:#8888ff,font-weight:bold,font-family:monospace;
    classDef core fill:#00ff41,stroke:#00ff41,stroke-width:3px,color:#0a0a0a,font-weight:bold,font-family:monospace;

    %% --- USER / ENTRY POINT ---
    U["> USER // RESEARCHER <"]:::user

    %% --- PRESENTATION LAYER ---
    subgraph PL["[ PRESENTATION LAYER ] — STREAMLIT DASHBOARD"]
        D1["[HOME] Search & Filter"]:::dash
        D2["[DETAIL] Trajectory · Risk · Trends"]:::dash
        D3["[RANKINGS] Sortable · Export"]:::dash
        D4["[PERFORMANCE] 4-Model Comparison"]:::dash
        D5["[ABOUT] Documentation"]:::dash
    end

    %% --- EXPLAINABILITY LAYER ---
    subgraph EL["[ EXPLAINABILITY LAYER ] — SHAP"]
        SH1["Global Feature Importance"]:::explain
        SH2["Per-Prediction SHAP"]:::explain
        SH3["Summary Plot"]:::explain
        SH4["Dependence Plots"]:::explain
    end

    %% --- MODELLING LAYER ---
    subgraph ML["[ MODELLING LAYER ] — CLASSIFICATION"]
        M1["Logistic Regression"]:::model
        M2["K-Nearest Neighbours"]:::model
        M3["Random Forest"]:::model
        M4["⚡ XGBoost ★"]:::model
        M5["5-Fold Stratified CV"]:::model
        M6["Weighted F1 Selection"]:::model
        M7["Hyperparameter Tuning"]:::model
    end

    %% --- FEATURE ENGINEERING LAYER ---
    subgraph FE["[ FEATURE ENGINEERING ] — 7 SIGNALS"]
        F1["Health Score"]:::feature
        F2["Growth Momentum"]:::feature
        F3["Question Quality"]:::feature
        F4["Company Diversity"]:::feature
        F5["Sentiment Delta"]:::feature
        F6["Adoption Velocity"]:::feature
        F7["Community Decay"]:::feature
    end

    %% --- DATA LAYER ---
    subgraph DL["[ DATA LAYER ] — POSTGRESQL 14+"]
        D6["Stack Overflow Q&A"]:::data
        D7["Dev Sentiment Survey"]:::data
        D8["Fortune 500 Stacks"]:::data
        D9["Company Profiles"]:::data
        D10["Tech Metadata"]:::data
        D11["Question-Company Map"]:::data
    end

    %% --- SQL QUERY LAYER ---
    subgraph SQL["[ SQL PIPELINE ] — 12 QUERIES"]
        SQ1["Q1-Q3: Basic"]:::infra
        SQ2["Q4-Q7: Intermediate"]:::infra
        SQ3["Q8-Q12: Advanced"]:::infra
    end

    %% --- DEPLOYMENT & INFRASTRUCTURE ---
    subgraph OPS["[ DEPLOYMENT ] — DEVOPS"]
        O1["Docker Container"]:::infra
        O2["Streamlit Cloud"]:::infra
        O3["GitHub Actions CI"]:::infra
        O4["Prometheus"]:::infra
        O5["ELK Stack"]:::infra
    end

    %% --- EXTERNAL SOURCES ---
    subgraph EX["[ EXTERNAL DATA ] — SOURCES"]
        E1["Stack Exchange ★ CC BY-SA"]:::external
        E2["SO Survey ★ CC BY-SA"]:::external
        E3["Fortune 500 ★ Open"]:::external
        E4["Company Registry ★ Open"]:::external
        E5["Tech Registries ★ Open"]:::external
    end

    %% --- FLOW CONNECTIONS ---
    E1 -->|"INGEST"| D6
    E2 -->|"INGEST"| D7
    E3 -->|"INGEST"| D8
    E4 -->|"INGEST"| D9
    E5 -->|"INGEST"| D10
    
    D6 -->|"JOIN"| D11
    D7 -->|"JOIN"| D11
    D8 -->|"JOIN"| D11
    D9 -->|"JOIN"| D11
    D10 -->|"JOIN"| D11
    
    D6 -->|"QUERY"| SQL
    D7 -->|"QUERY"| SQL
    D8 -->|"QUERY"| SQL
    D9 -->|"QUERY"| SQL
    D10 -->|"QUERY"| SQL
    D11 -->|"QUERY"| SQL
    
    SQL -->|"FEATURES"| FE
    
    D6 -->|"VOLUME"| F1
    D7 -->|"SENTIMENT"| F1
    D8 -->|"ADOPTION"| F1
    D9 -->|"PROFILES"| F1
    D10 -->|"METADATA"| F1
    D6 -->|"VELOCITY"| F2
    D6 -->|"QUALITY"| F3
    D8 -->|"DIVERSITY"| F4
    D9 -->|"SECTORS"| F4
    D7 -->|"TREND"| F5
    D8 -->|"GROWTH"| F6
    D6 -->|"DECAY"| F7
    
    F1 -->|"NORMALIZE"| LB
    F2 -->|"NORMALIZE"| LB
    F3 -->|"NORMALIZE"| LB
    F4 -->|"NORMALIZE"| LB
    F5 -->|"NORMALIZE"| LB
    F6 -->|"NORMALIZE"| LB
    F7 -->|"NORMALIZE"| LB
    
    LB["[ LABELLING ] Growing · Stable · Declining"]:::core
    
    LB -->|"80/20 SPLIT"| M5
    M5 -->|"TRAIN"| M1
    M5 -->|"TRAIN"| M2
    M5 -->|"TRAIN"| M3
    M5 -->|"TRAIN"| M4
    M1 -->|"EVAL"| M5
    M2 -->|"EVAL"| M5
    M3 -->|"EVAL"| M5
    M4 -->|"EVAL"| M5
    M5 -->|"SELECT"| M6
    M6 -->|"TUNE"| M7
    M7 -->|"OPTIMIZE"| M4
    
    M4 -->|"EXPLAIN"| SH1
    M4 -->|"EXPLAIN"| SH2
    M4 -->|"EXPLAIN"| SH3
    M4 -->|"EXPLAIN"| SH4
    
    SH1 -->|"RENDER"| D1
    SH2 -->|"RENDER"| D1
    SH3 -->|"RENDER"| D1
    SH4 -->|"RENDER"| D1
    M4 -->|"PREDICT"| D1
    M4 -->|"PREDICT"| D2
    M4 -->|"PREDICT"| D3
    M1 -->|"METRICS"| D4
    M2 -->|"METRICS"| D4
    M3 -->|"METRICS"| D4
    M4 -->|"METRICS"| D4
    LB -->|"STATS"| D1
    LB -->|"STATS"| D2
    LB -->|"STATS"| D3
    
    U -->|"ACCESS"| D1
    D1 -->|"NAVIGATE"| D2
    D1 -->|"NAVIGATE"| D3
    D1 -->|"NAVIGATE"| D4
    D1 -->|"NAVIGATE"| D5
    
    M4 -->|"EXPORT"| O1
    O1 -->|"DEPLOY"| O2
    PL -->|"HOSTED"| O2
    O3 -->|"CI/CD"| O1
    O4 -->|"MONITOR"| O2
    O5 -->|"LOG"| O2

    %% --- Styling Subgraphs ---
    style PL fill:#0a0a0a,stroke:#00ff41,stroke-width:2px,color:#00ff41
    style EL fill:#0a0a0a,stroke:#ff00ff,stroke-width:2px,color:#ff00ff
    style ML fill:#0a0a0a,stroke:#00ffff,stroke-width:2px,color:#00ffff
    style FE fill:#0a0a0a,stroke:#ffaa00,stroke-width:2px,color:#ffaa00
    style DL fill:#0a0a0a,stroke:#00ff41,stroke-width:2px,color:#00ff41
    style SQL fill:#0a0a0a,stroke:#8888ff,stroke-width:2px,color:#8888ff
    style OPS fill:#0a0a0a,stroke:#8888ff,stroke-width:2px,color:#8888ff
    style EX fill:#0a0a0a,stroke:#ff4444,stroke-width:2px,color:#ff4444
```

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

## Live Demo

The interactive Streamlit dashboard is currently under active development. Below is a preview demonstrating one of the core descriptive SQL queries that powers TechPulse's analytics foundation: identifying which technologies generate the most developer questions on Stack Overflow.

![Live Demo](https://github.com/skynet-datagrid-labs/TechPulse/blob/main/assets/query.gif)

**What this query reveals:**

The demo runs the following SQL query against the Stack Overflow dataset:

```sql
SELECT 
    tag,
    SUM(question_count) AS total_questions,
    SUM(unanswered_count) AS total_unanswered,
    (AVG(unanswered_pct))::numeric(10,2) AS avg_unanswered_pct,
    COUNT(DISTINCT date) AS days_with_activity
FROM stackoverflow
GROUP BY tag
ORDER BY total_questions DESC
LIMIT 10;
```

**Results interpretation:**

This query returns the top 10 technologies ranked by total question volume on Stack Overflow. These findings provide critical community signal inputs for TechPulse's predictive layer:

- **JavaScript**, **Python**, and **Java** consistently dominate total question volume, reflecting their large active developer communities.
- The `avg_unanswered_pct` column reveals which technologies have the highest proportion of unanswered questions — a potential early indicator of community fragmentation or declining expert availability.
- Technologies with high total questions but a rising unanswered percentage may be entering a "community fatigue" phase, a signal that TechPulse's machine learning models incorporate as part of the `community_decay_rate` and `technology_health_score` features.
- The `days_with_activity` metric provides a measure of sustained engagement consistency; technologies with fewer active days relative to their total volume may experience seasonal or event-driven interest rather than steady community health.

These descriptive insights form the foundation upon which TechPulse's predictive features are engineered. The dashboard will eventually display not only these descriptive statistics but also forward-looking trajectory classifications for each technology.

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
```

