# TechPulse final demonstration and defence notes

## Seven-minute demonstration sequence

| Time | Show | Explain |
|---|---|---|
| 0:00–0:45 | State the approved research title and problem | The project investigates whether developer-community signals and enterprise adoption patterns can support lifecycle analysis. Do not imply that the research hypothesis has been empirically validated. |
| 0:45–1:30 | Select **Research data · PostgreSQL**; show database health and Executive Overview | This mode reads canonical research schemas. The development copy currently has no eligible lifecycle labels, trained research model, persisted predictions, verified enterprise evidence or Kenya-specific technology observations. Missing evidence is shown as unavailable. |
| 1:30–2:15 | Open **Data Provenance and Quality** | Explain source lineage, validation state and why a source that fails consistency checks is blocked instead of silently corrected. The synthetic evidence is not mixed into research tables. |
| 2:15–2:30 | Switch to **Synthetic demonstration · PostgreSQL** | Point out the warning: the generated records are fictional training/demo data stored in a separate PostgreSQL schema. |
| 2:30–3:30 | Open **Technology Explorer** and inspect one generated profile | Demonstrate search and its saved time-series/feature values. Say these are deterministic scenarios, not real technology observations. |
| 3:30–5:00 | Open **Model Laboratory** | Compare the four previously executed synthetic model records. Random Forest ranks first on synthetic macro F1 (0.5093); show class precision/recall/F1 and confusion matrix. Emphasize its Declining recall is 0.1267, which is poor. |
| 5:00–5:45 | Show a synthetic prediction and stored explanation | Explain that the displayed prediction and SHAP record are tied to synthetic model artifacts. SHAP associations do not establish cause. A class score is not the model's general accuracy. |
| 5:45–6:30 | Return to Research mode, open Model Performance and Kenya page | Both have honest empty states for research model evidence and Kenya-specific observations. This is a current research limitation, not an application failure. |
| 6:30–7:00 | Summarize contribution and limits | Show the PostgreSQL provenance separation, repeatable import checksum, validation behavior and reproducible test result. State what must be collected and approved before empirical conclusions. |

### Before the presentation

1. Start PostgreSQL service and confirm `techpulse_rebuild_dev` is available.
2. From the project folder run `python -m streamlit run dashboard/app.py`.
3. Confirm `http://127.0.0.1:8501/_stcore/health` returns `ok`.
4. Do not run migrations, ingestion or source import during the presentation.
5. Keep the research view and demo view clearly distinguished throughout.

### Do not demonstrate or claim

- Do not describe the four model scores as empirical research results or the best model for real technologies.
- Do not claim that the app predicts actual technology decline from verified historical evidence.
- Do not describe fictional company profiles or generated Kenya-labelled rows as adoption/market observations.
- Do not show prediction class distributions as research evidence.
- Do not call stored synthetic SHAP rows explanations of real-world behavior.

## Likely examiner questions

**Does TechPulse currently predict real technology decline?**  
No. This development database has no eligible research lifecycle labels or model run. The visible four-model comparison is an executed synthetic demonstration and is labelled as such. Research prediction claims require valid longitudinal observations, a defensible target definition, an out-of-time evaluation and adequate class support.

**Which model is best?**  
Within the stored synthetic holdout only, Random Forest has the highest macro F1 at 0.5093. It has 0.1267 recall for Declining, so the result is weak for the central class. There is no established best research model.

**Why use macro F1?**  
The additional model-selection directive requests macro F1 because it weights each class equally. However, approved SRS FR-10 says choose by weighted F1. The current requested implementation follows macro F1 for the demonstration selector and explicitly records the conflict. The research criterion requires supervisor approval or a formal SRS revision.

**Does the synthetic Kenya page provide evidence about Kenyan technology use?**  
No. Kenya-labelled examples are generated fictional scenarios. The development database has zero verified Kenya-specific technology observations, and no Kenya research conclusion is drawn.

**Do the company records prove enterprise adoption?**  
No. They are fictional generated examples. The app distinguishes them from verified enterprise evidence; the development research schema currently has no verified enterprise adoption observations.

**Why is SQLite still present in the repository?**  
The original file is preserved as a read-only migration source and backup. The Streamlit runtime reads PostgreSQL only. A legacy, inactive SQLite generator module remains for provenance and has been removed from the application call path.

**How do you know the migration did not alter the source records?**  
The source was opened read-only and passed SQLite `integrity_check`. The PostgreSQL import records a SHA-256 and exact per-table counts. A repeat with the same checksum verified the current counts; a different checksum is rejected rather than silently replacing data.

**What is the current contribution if there is no research model?**  
The implementation demonstrates an auditable PostgreSQL structure, strict data provenance separation, validation and empty-state handling, a reproducible synthetic integration, and a complete UI path for exploring model records. It does not claim that the research hypothesis is validated.

**What must happen before reporting empirical model performance?**  
Resolve source validation and licensing, obtain enough valid longitudinal observations, predefine the label horizon and thresholds, prevent feature/label leakage, use chronological validation, persist a canonical feature snapshot and run metadata, and evaluate all models on the same eligible cohort.

## Supervisor clarification required

1. Confirm macro F1 versus the SRS FR-10 weighted-F1 rule.
2. Confirm random seed 42 from SRS NFR-MA-03 versus the fixed synthetic demonstration seed 7312026. The demo seed must not be substituted for research protocol.
3. Approve the label horizon and definitions for Growing, Stable and Declining before research labelling.
4. Confirm the source PostgreSQL database and which verified research rows should be copied into the isolated development DB; no unreviewed data merge was performed.
5. Confirm whether the final research title/objective permits a descriptive or exploratory result if evidence remains insufficient for three-class decline prediction.
6. Provide/approve a separate Software Test Plan if institutionally required. No separate plan file was present in the selected folder.
7. Confirm whether the proposal's embedded references satisfy the project's literature-review submission requirement; no separate literature-review file was present.
