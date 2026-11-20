# TechPulse final presentation runbook

## Start the application

From PowerShell in the project root:

```powershell
python -m techpulse.cli db-health
python -m dashboard.postgres_demo_migration --source outputs/synthetic_demo/techpulse_demo.sqlite
python -m streamlit run dashboard/app.py
```

The migration command verifies the checksum and row counts when repeated; it will not replace existing PostgreSQL records: `python -m dashboard.postgres_demo_migration --source outputs/synthetic_demo/techpulse_demo.sqlite`. Destructive reset is not used for ordinary refreshes; it requires an SQLite backup and explicit confirmation: `python -m dashboard.demo_store --reset-demo --confirm-reset "RESET SYNTHETIC DEMO ONLY"`. Open the local Streamlit URL, normally `http://localhost:8501`.

Fresh sidebar sessions default to **Synthetic demonstration · PostgreSQL** for a populated walkthrough. Choose **Research data · PostgreSQL** explicitly to inspect genuine research evidence. If PostgreSQL is unavailable, research mode reports the error and stays in research mode. It never falls back to the demo database. Synthetic pages display a persistent synthetic-data notice.

## Ten-minute walkthrough

### 0:00–1:30 — Research mode and the approved question

Select **Research data · PostgreSQL** in the sidebar. Show the Command Center/Executive Overview and the technology catalogue. State the approved question: whether community, enterprise adoption, and developer sentiment can help classify technology trajectories as Growing, Stable, or Declining. Point out that no validated research model or prediction is currently persisted.

### 1:30–3:00 — Genuine evidence and data quality

Open Data Provenance and Quality and Community Health. Show the official Stack Overflow course source, the two zero-total observations, and the critical validation record. Explain that the source consists of cumulative snapshots; the raw CSV remains unchanged and ingestion stays blocked until an authoritative correction is available.

### 3:00–4:00 — Real research-mode empty states

Open Technology Explorer and search for Python. Show available survey records and that community, enterprise, Kenya, prediction, and SHAP coverage remain unavailable where the canonical database has no rows. Missing evidence is not zero adoption.

### 4:00–4:20 — Make the mode change explicit

Use the sidebar selector to choose **Synthetic demonstration · PostgreSQL**. Pause on the banner. Say that all subsequent charts, records, company examples, model metrics, predictions, and explanations are fictional demonstration outputs, not research evidence.

### 4:20–6:00 — Synthetic technology profile

Open Technology Explorer, search `DemoLang`, then open Technology Profile. Show simulated monthly activity, the seven calculated feature values, generated survey-like series, and the synthetic-only inference. The fictional technology names are deliberate and do not represent real stacks.

### 6:00–7:00 — Enterprise and geography boundaries

Open Enterprise Adoption. Show fictional `Demo Company` rows, synthetic URI references, and `NOT VERIFIED - SYNTHETIC ONLY` status. Open Kenya Landscape and explain that the demo deliberately contains no Kenya indicators; the global simulation is not relabelled as Kenyan evidence.

### 7:00–8:40 — Synthetic model laboratory and explanations

Open Model Laboratory. The four classifiers are fitted on generated feature snapshots and evaluated on a chronological synthetic holdout. Show per-class metrics and the confusion matrix, while reading the synthetic warning. Note that the labels are imbalanced and all four models have weak recall for Declining; Logistic Regression predicts only Stable. Open Explainability to show SHAP from the synthetic Random Forest. Explain that these are calculations on simulated data and do not validate the original research hypothesis.

### 8:40–9:30 — Data Observatory and methodology

Open Data Observatory to show the separate source registry, table counts, and quality checks. Open Methodology & About to show feature definitions and the difference between the demonstration label rule and the SRS label definition.

### 9:30–10:00 — Return to research mode

Switch back to **Research data · PostgreSQL**. Close by restating that the interface is operational, the synthetic walkthrough demonstrates UI functionality, and a valid three-class research model still requires suitable verified time-aligned data.

## Do not claim

- Synthetic model accuracy, F1, confusion matrices, predictions, or SHAP as research results.
- Fictional company examples as enterprise adoption evidence.
- Synthetic global survey-like rows as a developer survey.
- A Kenya-specific adoption rate or developer trend.
- A synthetic class assignment as the validated SRS lifecycle label.

## Safe recovery during the presentation

- If PostgreSQL is down, stay in Research mode long enough to state the connection issue, then explicitly select Synthetic demonstration mode. Do not let the app switch modes without the presenter choosing it.
- If the synthetic store is missing, run `python -m dashboard.postgres_demo_migration --source outputs/synthetic_demo/techpulse_demo.sqlite` and refresh the page.
- If port 8501 is already serving this TechPulse checkout, use the existing local URL. Otherwise start Streamlit with `python -m streamlit run dashboard/app.py --server.port 8502`.
