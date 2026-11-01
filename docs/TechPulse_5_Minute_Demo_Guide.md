# TechPulse Five-Minute Assessor Demonstration

**Target duration:** 5 minutes  
**Launch:** `python -m streamlit run dashboard/app.py` then open `http://localhost:8501`  
**Example record:** `actionscript` (saved class Declining in the current local snapshot)

> Demonstrate only what is present. The dashboard displays saved results. It does not train the model or run new predictions on selection.

## Before the assessor arrives

1. Start the app from the project root and check that **Start Here** loads.
2. Confirm the **Development Data** badge appears.
3. Keep the browser at Start Here. Have the current app screenshots available as backup.
4. Remember that the current comparison metrics and label summary disagree with the current feature table. State this before interpreting the score table.

## Five-minute route

### 0:00-0:30 | Start Here

**Navigate:** Start Here is the landing page.  
**Say:** “TechPulse is an academic research prototype for exploring technology trajectories using community activity and saved model outputs. I will show how to inspect the evidence and where the current limitations appear.”  
**Point out:** Purpose, Development Data badge, and artifact warnings.  
**Transition:** “I will find one technology and see what historical activity is actually available.”

### 0:30-1:15 | Technology Explorer

![Technology Explorer page](../outputs/live_data_screenshots/02-technology-explorer.png)

**Click and do:** Open **Technology Explorer**. In **Search technology names**, enter `actionscript` and press Enter. Choose `actionscript` under **Choose a technology** if it is not already selected.  
**Say:** “This page retrieves the saved technology row. The historical line shows monthly questions for this tag in the local community source; it is not total technology usage or evidence of cause.”  
**Point out:** Search, saved class, available signals, and chart period. Do not describe the saved target label as the model's output.

### 1:15-1:55 | Community Health

**Click and do:** Open **Community Health**. Select `actionscript` under **Choose a technology tag**.  
**Say:** “This view summarizes the source-file question volume and unanswered share. It describes one community source only. Missing survey data is called out rather than filled with invented numbers.”  
**Point out:** Observed questions, source records, unanswered share, and monthly time axis.  
**Transition:** “Next I will inspect the model's saved row and explain the risk formula.”

### 1:55-2:45 | Prediction Explorer

![Prediction Explorer page](../outputs/live_data_screenshots/05-prediction-explorer.png)

**Click and do:** Open **Prediction Explorer**. Search for `actionscript`; select it.  
**Say:** “The saved class for ActionScript in this snapshot is Declining. I can inspect the saved probability scores and input signals. This is retrieval of a pipeline result, not a new prediction.”  
**Explain:** The maximum class score is the saved confidence indicator. The risk indicator is `(1 - P(Growing)) × 100`. A value near 97.5 is not a 97.5% chance of failure; it is the complement of the Growing score.  
**Point out:** Class, score chart, risk indicator, and SHAP attribution if present. SHAP is model attribution, not causation.

### 2:45-3:20 | Technology Rankings

**Click and do:** Open **Technology Rankings**. Leave all filters at their defaults, then point to the chart and table. Optionally enter `actionscript` in **Search technologies**.  
**Say:** “The filters and download control operate on saved rows. The ranking orders a derived indicator when class probabilities are present. It is not a measure of technology quality or enterprise adoption.”  
**Point out:** Category, class, search, sort, and **Download visible rows as CSV**.

### 3:20-4:10 | Model Performance & Validation

![Model Performance and Validation page](../outputs/live_data_screenshots/06-model-performance.png)

**Click and do:** Open **Model Performance & Validation**. Read the red audit warning before the table.  
**Say:** “The stored CSV reports 1.0000 metrics for four candidates. But this checkout has no run-level evaluation summary, no baseline row, and its label summary does not match the current 53-row feature matrix. These recorded numbers are not independently verifiable as current-run performance, so I do not claim the system is reliable.”  
**Point out:** Missing run summary, missing baseline, label-support counts and metric explanations.  
**Technical note:** Source code uses a stratified random 80/20 split, not a time-forward validation.

### 4:10-4:40 | Methodology & Data

**Click and do:** Open **Methodology & Data**. Show the six-table contract and expand one SQL query if time allows.  
**Say:** “The local fallback has observed community rows and company profiles, but stack relations, metadata and mappings may be deterministic proxies. The SQL files also need schema reconciliation before execution against the warehouse.”

### 4:40-5:00 | Close

**Say:** “The contribution at this stage is a working, inspectable research prototype and an honest presentation of its data and evaluation boundaries. The next work is to reconcile artifacts, obtain time-aligned research-grade sources, and rerun evaluation with a recorded baseline and per-class metrics. Thank you; I welcome your questions.”

## Optional live-data detour (about 20 seconds)

If the assessor asks about current external observations, open **Live Technology Intelligence** and select `mongodb` from the existing catalogue. Point to the per-source collection timestamps, sample indicators and Stack Exchange activity chart. Say: “These are real public API observations collected at the timestamps shown. They add context to the dashboard but remain outside the historical feature table, training, saved predictions and evaluation until their temporal alignment and measurement quality are separately validated.”

Do not launch a fresh collection during the timed presentation unless API access and the saved connection are already confirmed. The dashboard page itself reads stored observations and does not call APIs on page load.

## Likely assessor questions

**Does selecting a technology create a prediction?** No. It selects a saved row from `outputs/technology_predictions.csv`.

**What does the risk indicator mean?** The complement of the saved Growing score, scaled from 0 to 100. It is not a validated probability of failure or decline.

**Why not report the perfect metrics as success?** They are recorded in a CSV but their run-level summary is absent, the comparison has no baseline row, and the label summary conflicts with the current feature matrix.

**Why include a baseline?** It answers whether added model complexity improves on a simple reference such as always predicting the most common training class.

**Are the company adoption values observed?** Local company-stack, category and mapping records are development proxies and must not be described as measured enterprise usage.

**What would improve the research validity?** Reconcile source lineage and saved runs; use temporally appropriate observations; preserve group/time split metadata; report all class support and per-class results; and compare with baseline models.

## Backup and timing checklist

- Keep the browser ready at Start Here and the screenshots available.
- If the live app becomes slow, use the screenshots but explicitly say they are captures of the application, not live outputs.
- Do not claim on-demand inference, real enterprise adoption, causal explanations, or validated future decline probabilities.
- Leave at least 20 seconds for the closing statement and questions.
