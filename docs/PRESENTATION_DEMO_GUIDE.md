# TechPulse 10-minute presentation demo

## Before the assessor arrives

From PowerShell in the repository root:

```powershell
python -m techpulse.cli db-health
python -m streamlit run dashboard/app.py
```

Open the local Streamlit URL printed by the command. Confirm the sidebar says **PostgreSQL connected**, database `TechPulse-Database`, and migration count 2. Use the existing loaded database as the demo; do not run a fresh external API collection or ingestion during the timed presentation. Keep `docs/FINAL_AUDIT_REPORT.md`, `docs/MODEL_EVALUATION_REPORT.md`, and `outputs/runs/data_quality_20261113T124957254945Z.json` available as backup evidence.

The app has no validated model predictions or Kenya-specific records today. Its empty states are part of the research-integrity demonstration. Do not claim the project has a valid predicted decline, Kenyan ranking, or verified enterprise-adoption rate.

## Minute 0–1: Introduction

**Open:** **Executive Overview** (default page).
**Show:** technology and observation counts, source-health state, freshness and limitations.
**Say:** “TechPulse studies whether historical developer-community signals can help describe technology trajectories as Growing, Stable or Declining. It brings source lineage and time-aware validation into one inspectable system. A trajectory label is not a technology-quality or investment recommendation.”
**Highlight:** 267 catalogue technologies; the overview's observation counts are source records, not unique developers or adoption.

## Minute 1–2: Data and Sources

**Open:** **Data Provenance and Quality**.
**Click:** inspect the source registry and ingestion/quality rows; point to the failed `local_stackexchange` run and the successful survey source.
**Say:** “The survey aggregate is global/unspecified. The official DataCamp course CSV verifies the source and confirms two invalid zero-total rows: an `ios` row reports zero questions but 181,334 unanswered, and an `amazon-mws` row reports zero for both. We preserve the raw rows and block ingestion rather than guessing replacements.”
**Highlight:** `docs/THREE_DAY_PRESENTATION_RESCUE.md` and the newest `outputs/runs/data_quality_*.json` report record the current check. The 2016–2018 data contain cumulative snapshots, not daily arrivals.

## Minute 2–4: Technology Intelligence

**Open:** **Technology Explorer**.
**Click:** search/select **Python** in the technology control; review aliases/categories, source coverage, and the global survey rows. Then show the explicit no-community-evidence and no-prediction states.
**Say:** “This page joins the canonical catalogue to each evidence type while preserving its geography and time. Missing community history is shown as unavailable, not as zero activity. The survey is a reported global measure, not a Kenya measure.”
**Highlight:** coverage table and survey year/usage-interest columns. Do not describe the survey's reported share as live usage or causal evidence.

## Minute 4–6: Predictive Modelling

**Open:** **About and Responsible Use**, then **Prediction Explorer**.
**Click:** show the methodology description and the prediction page's unavailable state.
**Say:** “This database has no validated model run or saved predictions, so selecting a technology does not create an inference. The source ends in 2018; a source-aware three-month feasibility check contains no Declining examples in either the training or latest holdout period. No three-class model is reported.”
**Highlight:** zero canonical model runs/predictions and the statement of the limitations. Explain Growing, Stable and Declining as future-vs-recent activity categories only when their underlying windows are complete.

## Minute 6–7: Model Evaluation

**Open:** **Model Performance**.
**Click:** show the explicit no-run/no-metrics state, then open `docs/MODEL_EVALUATION_REPORT.md` if the page needs supplementary explanation.
**Say:** “Accuracy and F1 are unavailable for a valid research run. The saved perfect-looking comparison artifacts are synthetic test fixtures. Reporting them as research performance would be false. The valid next evaluation is chronological and compares majority and momentum baselines with suitable models.”
**Highlight:** no valid confusion matrix or per-class metric exists. Do not quote the synthetic scores.

## Minute 7–8: Explainability

**Open:** return to **Prediction Explorer** and point to the unavailable explanation state; optionally show the methodology's explanation section.
**Say:** “The schema and code can store feature contributions, and SHAP is available where compatible. There is no validated model prediction to explain in this database. Once generated, contributions would describe model associations, not causes.”
**Highlight:** no fabricated SHAP plot; explain that the explanation is linked to a specific saved prediction and model-run ID.

## Minute 8–9: Kenyan Context

**Open:** **Kenya Technology Landscape**.
**Click:** show the no-verified-Kenya-records state; return to **Market and Skills Signals** to show global survey coverage separately.
**Say:** “The canonical Kenya query returns no verified local technology observations. We do not turn a global survey or company-profile file into Kenyan adoption statistics. Reliable local indicators would need dated, source-linked observations and documented coverage.”
**Highlight:** explicit zero available records means evidence unavailable, not a zero adoption rate.

## Minute 9–10: Limitations and Conclusion

**Open:** **Data Provenance and Quality** or **About and Responsible Use**.
**Say:** “The working contribution today is a reproducible evidence pipeline, canonical PostgreSQL model, data-quality gate, and dashboard that exposes the limits of its evidence. The next step is to verify and reconcile sources, rebuild time-aligned features, then persist an independently auditable chronological evaluation. TechPulse should support research discussion, not high-stakes technology decisions.”
**Close:** invite questions and leave time for one.

## If something fails

- If the sidebar says PostgreSQL unavailable, check `.env`, local PostgreSQL service, and `python -m techpulse.cli db-health`; do not claim database-backed pages are live.
- If a page has no qualifying records, explain that the result is unavailable and move on; do not substitute the CSV or describe it as a database result.
- If app startup is slow, use the source validation report and audit docs as backup and state that they are saved outputs.
- Do not start API collection during the talk. Live public API counts are supplemental and are not the historical training set.

## Likely questions

**Why show no prediction?** No valid model run/prediction is persisted; the curated community input is blocked. A fabricated output would misrepresent the study.

**Why not use the perfect result in the output folder?** The run manifests classify all inspected output runs as synthetic fixtures and unauditable, with no research input snapshot.

**Is the company data enterprise adoption?** No. It is company profile data, not dated technology-use evidence.

**Is the survey about Kenya?** No. Current rows are global/unspecified and self-selected.

**What is the main next step?** Verify the community source and anomalous count, reconcile source/database records, then produce and persist time-aligned features and a chronological baseline-comparative evaluation.
