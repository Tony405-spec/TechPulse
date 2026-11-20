# TechPulse Presentation QA Report

Date: 19 November 2026

## Final artifact checks

- Exactly 7 slides; 4:3 dimensions (10 × 7.5 inches), matching the supplied KCA template.
- Opened in Microsoft PowerPoint automation; editable text and shape objects, one native editable objective table, and screenshot image objects.
- Original KCA cover/logo, institutional design/footer, and closing design retained.
- Seven slides exported from PowerPoint as 960 × 720 PNG images and visually inspected individually.
- Speaker notes are populated on all 7 slides. Allocated timings total exactly 10:00.
- The lifecycle illustration is labelled conceptual, not observed data.
- All six approved specific objectives and the approved general objective are represented.
- Slide 3 citations come from the approved proposal; they are framed as reported by that proposal, not independently re-reviewed.
- Slide 4 identifies all seven synthetic demonstration indicators and formulas, their synthetic-only status, and a potential circular-label risk.
- Slide 5 uses genuine screenshots from the repository user-manual capture set and manifest; modes and screenshot purpose are labelled.
- The PDF was exported from the revised PowerPoint and has exactly 7 pages.
- No database writes/migrations/data corrections, model training, or app-code changes were made for this presentation.

## Existing-presentation assessment

The earlier deck preserved the seven-slide structure and evidence boundaries, but its PPTX had flattened each slide to one image because the Artifact Session exporter failed. That prevented normal editing and lacked enough assessor-facing literature/method detail. This revision uses native PowerPoint text, shapes, an editable objective table, notes and screenshot objects.

## Evidence sources inspected

- Approved proposal PDF: title, general/specific objectives, significance, methodology, candidate sources and cited literature.
- docs/FINAL_IMPLEMENTATION_REPORT.md: source readiness, validation problems, synthetic/research separation and objective evidence.
- docs/MODEL_EVALUATION_REPORT.md and docs/MODEL_METHODOLOGY.md: no auditable research run; proposed temporal safeguards; target definition conflict.
- dashboard/demo_population.py and dashboard/demo_store.py: synthetic feature and label formulas; code paths include formula variants.
- docs/user_manual/screenshot_manifest.json: provenance and scope of application screenshots.
- The local app endpoint at localhost:8501 did not respond during this revision; screenshots are from the manual capture set, not a fresh live capture.

## Claims that cannot be substantiated

- Any research accuracy, weighted F1, class-level recall, confusion matrix, calibrated risk score, or research SHAP interpretation.
- Verified company-to-technology adoption or Kenya-specific technology observations.
- A complete research feature/label dataset or a trained research classifier.
- Public deployment, completed dissertation, or impact on developer/organisational decisions.
- Exhaustive novelty of the proposal’s gap; it is presented as the proposal’s review-based gap only.

## Research limitations to state

- Stack Exchange history is blocked by an impossible iOS count (0 questions; 181,334 unanswered); the source was not altered.
- Survey CSV has 685 rows and 684 technology-year keys; the collision remains unresolved.
- Survey years 2021–24 do not align with community 2016–18; 497 company profiles are not verified adoption evidence.
- No verified Kenya records, canonical research feature snapshots, lifecycle labels, trained research run, predictions or explanations.
- Potential target leakage: SRS uses GMI to define labels while GMI is also a candidate feature; legacy future-window labels differ. Supervisor clarification is required.
- Synthetic demo generators contain formula variants. Their outputs validate demonstration wiring only, not research performance.

## Hypothetical rubric self-assessment (not an official KCA rubric)

| Dimension | Weight | Self-score | Reason |
|---|---:|---:|---|
| Research problem, background and gap | 15 | 12 | Specific approved problem and qualified review gap; no systematic-review claim. |
| Objectives, significance and literature | 10 | 7 | All objectives retained; relevant cited studies have concise scope limits. |
| Methodology and technical justification | 20 | 12 | Cutoff/horizon, temporal evaluation and leakage are explicit; research labels remain unresolved. |
| System implementation and demonstration | 15 | 12 | Genuine local Streamlit/PostgreSQL evidence; synthetic screen clearly labelled. |
| Results, evaluation and interpretation | 20 | 4 | No valid research experiment/results; integrity is clear but the central empirical result is unavailable. |
| Objective achievement, limitations and conclusion | 10 | 8 | All six objective statuses and next steps stated. |
| Presentation quality and academic communication | 10 | 8 | Seven-slide KCA style, native editable content, diagrams/table, notes and mode labels. |
| **Total** | **100** | **63** | **Self-assessment only; limited by missing valid research results.** |

