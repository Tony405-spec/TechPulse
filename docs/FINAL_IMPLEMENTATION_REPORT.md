# TechPulse final implementation and research credibility report

**Verified:** 2026-11-17
**Repository:** `C:\Users\Administrator\Downloads\TechPulse-main (4)\TechPulse-main`
**Approved title retained:** *Predicting Developer Technology Decline Using Community Signals and Enterprise Adoption Patterns: A Machine Learning Approach*

## Executive finding

TechPulse is operational as a PostgreSQL-backed evidence and data-quality application. Its dashboard presents the catalogue and survey records and explicitly surfaces missing evidence. This implementation pass adds database-derived indicator readiness, profile status for stored labels/predictions/explanations, a read-only survey reconciliation report, and an ingestion guard for conflicting survey natural keys.

The database does **not** contain an auditable research model run, validated lifecycle labels, predictions, explanations, canonical feature snapshots, curated monthly community observations, verified company-technology adoption evidence, or Kenya-specific technology observations. No research classifier was trained in this pass. Existing synthetic demonstration results remain isolated and must be described as synthetic computations, not empirical findings. The approved project title and research objectives were not altered.

## Protection, changes, and database state

- The repository has no `.git` directory; a Git status or rollback point is unavailable. A pre-edit safeguard copy exists at `C:\Users\ADMINI~1\AppData\Local\Temp\techpulse-final-implementation-before`.
- PostgreSQL health passed: version 18.3, all six canonical schemas, two migrations.
- No migration, database insertion/update/deletion, or source-file edit was performed. The reconciliation used a read-only PostgreSQL transaction; it wrote only a JSON report file.
- Verified counts: 267 technologies; 684 survey observations; 0 community-month observations; 497 company profiles; 0 verified company-technology evidence rows; 0 Kenya ICT rows; 0 feature snapshots/values; 0 lifecycle labels; 0 successful research model runs; 0 persisted predictions; 0 explanation records.

### Files changed in this pass

- `dashboard/db/queries.py` — data-derived evidence snapshot and per-technology persisted assessment query.
- `dashboard/db/repositories.py` — uncached readiness read (so added observations are visible without waiting for cached catalogue data) and assessment accessor.
- `dashboard/readiness.py` — reusable indicator readiness evaluator with explicit missing/invalid/partial/available states and period summaries.
- `dashboard/page_renderer.py` — live readiness table and profile separation of persisted labels, valid predictions, and explanation rows.
- `src/cli.py` — rejects conflicting survey rows sharing the canonical technology/year key, while retaining exact-duplicate removal.
- `scripts/reconcile_survey.py` — reproducible CSV/database comparison in a read-only DB transaction.
- `tests/test_canonical_contract.py`, `tests/test_dashboard_redesign.py` — validation and readiness cases.
- `outputs/research_integrity/survey_reconciliation.json` — generated reconciliation evidence.
- `docs/FINAL_IMPLEMENTATION_REPORT.md` — this delivery record.

## Data findings and reconciliation

The reconciliation read `data/developer_survey_usage.csv` (SHA-256 `f323de9927400cd35a7f6a0a1acafcf0221bb4d8131c2f2e6b988bd46c101531`) and compared source natural keys with rows stored under `local_survey`:

| Reconciliation item | Verified result |
|---|---:|
| CSV rows read | 685 |
| Exact duplicate rows | 0 |
| Distinct `(technology_name, survey_year)` keys | 684 |
| Database rows / distinct keys | 684 / 684 |
| Source keys absent from database | 0 |
| Database keys absent from source | 0 |
| Conflicting natural keys | 1: Supabase, 2024 |

The 2024 Supabase source has separate Database and Platform rows with different usage, interest, and admiration values. The canonical uniqueness key is `(source_id, technology_id, geography_id, survey_year)` and does not include category; therefore it can retain only one category row. The stored values match the Platform row. The latest successful ingestion reports 685 read and zero written, so it cannot establish which row was retained during the earlier write. This explains the count discrepancy at the natural-key level; the earlier row-selection history remains unresolved. The updated ingestion validator now fails before writes on this ambiguity rather than choosing a row implicitly. No database values were “fixed.”

Run the reconciliation again with `python -m scripts.reconcile_survey`. It creates/overwrites only `outputs/research_integrity/survey_reconciliation.json`; the script neither creates an ingestion run nor mutates PostgreSQL. Validation now reports the source as blocked until category semantics or the key mapping are reviewed.

The source registry still describes local file attribution as unverified and has no source URL or confirmed licence. Survey rows are global/unspecified summaries from 2021–2024, not individual-level responses, not a satisfaction series, and not Kenya evidence. Company profiles do not document technology use. The blocked Stack Exchange source contains impossible zero-total records in the upstream resource; its ingestion gate remains unchanged and active.

## Dynamic indicator readiness

Readiness is fetched from current database evidence, including valid observation timestamps and ranges, not inferred from table existence. A displayed “Available” status means the input checks are met; it does **not** mean an indicator was calculated. The overview separately reports persisted feature values. At this verification:

| Indicator | Current input status | Main reason |
|---|---|---|
| Technology Health Score | Invalid source data | No curated community series; Stack Exchange validation is blocked; no approved composite calculation is persisted. |
| Growth Momentum Index | Invalid source data | No valid dated monthly community observations; source failure remains recorded. |
| Question Quality Score | Invalid source data | No curated question-level outcome observations or approved calculation. |
| Company Diversity Score | Unavailable | No dated, source-linked company-to-technology adoption observations. |
| Sentiment Delta | Unavailable | Available survey measures are usage, interest, and admiration, not time-aligned developer satisfaction. |
| Adoption Velocity | Unavailable | No source-linked dated adoption events across quarterly periods. |
| Community Decay Rate | Invalid source data | No valid recent/prior six-month community windows. |

The profile page reports persisted label count, valid persisted prediction count, and stored explanation count separately. A label is not described as a prediction; a stored record alone is not described as validated model performance. The database currently yields zero for all three on technology profiles. The period and source-coverage tables remain visible below the status section.

## Methodology and model decision

The SRS describes Sentiment Delta as change in developer satisfaction, Adoption Velocity as new company adoptions per quarter averaged across four trailing quarters, and Community Decay Rate across six months. The current canonical evidence does not meet those input definitions. Averages of survey usage/interest/admirations, company directory sizes, package downloads, stars, or global data labeled as Kenyan would not be valid substitutes.

The SRS lifecycle rule derives Growing/Stable/Declining from Growth Momentum Index and a trailing-12-month question-volume trend. Because GMI is also intended as an input feature, this can make the target circular. The current code's legacy future-window ratio labeler is also not the same rule as the SRS definition. The approved Proposal/SRS/SDS therefore need supervisor reconciliation before labels or training are changed. The documents also differ on random stratified versus chronological validation and on evaluation metric emphasis. No methodology was silently changed.

No research model was trained or evaluated. Current run/prediction/explanation counts are zero, and past generated/demo artifacts are excluded from empirical claims. The separate demo mode performs actual computations on isolated synthetic records; those computations do not estimate performance on real technologies. Do not present synthetic accuracy, F1, or SHAP output as research findings.

## Application and workflows exercised

- Live app opened at `http://localhost:8501` in Research data · PostgreSQL mode; accessibility content showed canonical DB connected and the research overview rendered.
- PostgreSQL health command passed.
- The readiness evidence query and evaluator were executed against the live database.
- Survey reconciliation completed with the counts above and an explicit no-database-write result.
- Focused AppTest and contract tests passed (results below).
- The app’s existing page-level and demo-mode suite covers navigation, render smoke checks, technology search/no-results, synthetic isolation, and demo model artifact consistency. This pass did not manually click every page control, exercise every download in a browser, inspect at multiple physical screen widths, or run assistive-technology checks. Those checks must not be claimed as completed.

The accessible browser tree confirmed the active research mode, actual overview counts, a blocked source, and no model run. It did not expand the readiness disclosure during the manual browser inspection; the readiness computation was directly exercised and covered by automated tests.

## Tests and verification

- Baseline before this pass: `python -m pytest -q` — 85 passed, 16 warnings (recorded in the preceding UI review).
- Focused changed-area tests: `python -m pytest tests/test_canonical_contract.py tests/test_dashboard_redesign.py -q` — **20 passed**.
- Full test suite after the final readiness edge-case test: `python -m pytest -q` — **90 passed, 16 warnings in 77.35 seconds**.
- `python -m compileall -q dashboard src scripts tests` — passed.
- `python -m techpulse.cli db-health` — passed; PostgreSQL 18.3, six schemas, two migrations.
- `python -m scripts.reconcile_survey` — passed as a read-only DB comparison; identified the Supabase 2024 collision and generated the JSON report.
- App render: verified in the browser against the live PostgreSQL research database.

Warnings are dependency/runtime notices from Matplotlib/Pyparsing, Joblib, and scikit-learn; the full suite reported 16 warnings and no failures.

## Limitations and remaining risks

1. There is no evidence-backed three-class predictive experiment. The title remains the approved title, but the presentation must clearly say that the model objective is not currently demonstrated empirically.
2. Stack Exchange input remains blocked by the source's impossible records; neither raw file was altered.
3. Survey category collisions cannot be represented by the existing natural key. Resolving this may require an approved source mapping or schema decision; no migration was made.
4. Survey aggregation lineage and reuse/licence details remain incomplete. The attribution presently stored in PostgreSQL is explicitly unverified.
5. Enterprise adoption and Kenya-specific technology evidence remain absent.
6. The SRS target may reuse GMI as a predictor, risking circular labels; code label construction differs from the written rule. Split guidance also conflicts across the academic artifacts.
7. Readiness checks are conservative screens. They do not define formulas where the SRS or SDS is ambiguous, prove sampling representativeness, or certify any incoming record without provenance review.
8. No verified Git history exists; use the safeguard copy and this enumerated record for recovery/change review.

## Startup and safe demonstration

From PowerShell at the repository root:

```powershell
python -m techpulse.cli db-health
python -m streamlit run dashboard/app.py
```

Open the URL Streamlit prints (normally `http://localhost:8501`). If port 8501 is already occupied by the running TechPulse instance, use it; otherwise choose a second port with `python -m streamlit run dashboard/app.py --server.port 8502`. Research mode requires the configured PostgreSQL service and `.env` connection. The dashboard does not automatically fall back. Do not run migrations or ingestion during the presentation. `python -m scripts.reconcile_survey` is an optional, read-only terminal demonstration.

## Eight-minute demonstration script

1. **0:00–0:45 — Research question.** Read the approved title and explain the intended community, developer-signal, enterprise-evidence, and lifecycle-prediction question. Say explicitly that this app session demonstrates evidence and workflow, not a validated decline predictor.
2. **0:45–1:30 — Startup and database.** Run `db-health`; point out PostgreSQL 18.3, six schemas, two migrations, and Research mode. State that no DB writes or migrations are part of the demo.
3. **1:30–2:30 — Overview.** Show 267 catalogue entries and 684 global/unspecified survey rows; contrast these with zero curated community observations, zero verified Kenya observations, and no model run. Explain missing is not zero-valued technology health.
4. **2:30–3:30 — Indicator readiness.** Expand Research indicator readiness. Explain that statuses derive from current validated rows and observation windows; “Available” means inputs pass, not a prediction. Highlight absent satisfaction/adoption inputs.
5. **3:30–4:30 — Technology Explorer.** Search for a known technology and inspect its profile. Point out global survey periods, absent community/adoption evidence, and separate counts for lifecycle labels, predictions, and explanation rows.
6. **4:30–5:30 — Provenance and quality.** Open Data Provenance and Quality. Show the failed Stack Exchange source and explain why impossible source values remain untouched and block ingestion.
7. **5:30–6:30 — Reconciliation.** Run `python -m scripts.reconcile_survey` or open the JSON. Explain the 685 source rows / 684 natural keys and the two category-specific Supabase 2024 rows that collide with the DB key. Say the retained Platform values are known but earlier write history is unresolved.
8. **6:30–7:15 — Model and explainability.** Open Model Performance and Prediction Explorer. Show no research run, metrics, predictions, or explanations. Do not quote synthetic demo scores as evidence.
9. **7:15–8:00 — Limitations and contribution.** Summarize source validation, lineage, explicit missing-data states, temporal methodology controls, and research readiness. Close with the supervisor decisions below.

### Do not demonstrate as research evidence

- Synthetic/demo model metrics, generated lifecycle labels, predictions, company examples, or SHAP values.
- Package downloads, repository stars, or technology mentions as verified production adoption.
- Global survey summaries as Kenya-specific developer behaviour or as a sentiment/satisfaction delta.
- A three-class research result, validated decline prediction, or model comparison; none exists in PostgreSQL.
- Stack Exchange metrics derived by summing daily cumulative snapshots or including impossible zero-total rows.

## Likely examiner questions and defensible answers

**Q: Did you build the intended predictive model?**
A: The application and modelling components exist, but no defensible research run was produced because the canonical community observations, aligned features, and approved non-circular labels are absent. I report this as a feasibility/evidence limitation rather than substitute demo metrics.

**Q: Why not train on the available survey and company records?**
A: Survey rows are global/unspecified aggregate usage, interest, and admiration measures and are not aligned to the historical community periods. Company rows are profiles, not technology adoption observations. They cannot support the approved predictors/target without inventing evidence.

**Q: What does the 685-versus-684 difference mean?**
A: The CSV has 685 rows and 684 distinct technology/year keys. Supabase 2024 has separate Database and Platform records but the canonical key omits category. The database matches Platform. The latest successful ingestion wrote zero, so I can explain the collision but cannot prove which earlier input was applied.

**Q: Why is Stack Exchange blocked if the file came from a public source?**
A: Two upstream rows have impossible zero cumulative question totals, including an unanswered count greater than zero questions. The source remains intact; ingestion rejects the invalid records instead of fabricating corrections.

**Q: Are the dashboard’s counts evidence of technology health?**
A: No. They describe source coverage. Missing observations are not treated as a zero score or as Stable. The profile separates stored labels, successful model predictions, and explanation rows.

**Q: What is the main methodological risk?**
A: The written target uses Growth Momentum Index, which is also a proposed feature, creating potential circularity. The implementation’s legacy future-window ratio labels also differ from the SRS rule. Both require supervisor approval before a research run.

**Q: What is the project's defensible contribution today?**
A: A working evidence-backed dashboard, canonical data/provenance workflow, validation gates for impossible or ambiguous records, reproducible source reconciliation, and a transparent account of what the current data can and cannot support. This is not evidence that the prediction hypothesis is confirmed.

## Supervisor questions to send

1. Please confirm the approved Growing/Stable/Declining label definition and prediction horizon. Should labels be determined only from outcomes after the feature as-of date, and how should the written SRS GMI threshold rule be reconciled with the implementation’s future-window ratio rule?
2. What source and documentation standard qualifies as verified enterprise technology adoption (for example, a dated first-party engineering publication or product documentation), and what evidence is sufficient for company diversity and quarterly adoption velocity?
3. Is Kenya-specific analysis mandatory for the final defence, or may the student present Kenya coverage as a limitation while keeping global/unspecified observations clearly separate?
4. If valid aligned observations cannot support three classes before submission, should the project be defended as a feasibility/data-quality study while preserving the approved title and objectives, or is a formally approved objective amendment required?
5. Which methodology adjustments may be made without changing the approved objectives, especially label horizon, the possible target/GMI overlap, chronological versus random stratified validation, and the metric to emphasize?
6. For the two Supabase 2024 survey categories, should the project preserve category as part of the source key, select a documented source-consistent aggregation, or exclude the conflicting key until the data model is approved?

## Professor-style evaluation

Strict estimate against the requested 100-point rubric; scores assess the verified application and research evidence, not visual polish alone.

| Area | Score | Evidence |
|---|---:|---|
| Research objectives and requirements alignment | 9/15 | Title and intended objective preserved; canonical app workflow exists. The central empirical three-class prediction is not supported by stored evidence. |
| Data quality, provenance and integrity | 10/15 | Stack Exchange gate blocks invalid upstream rows; new reproducible survey reconciliation explains the natural-key collision. Survey/company attribution and licence evidence remain incomplete. |
| Feature engineering and methodology | 6/15 | Temporal/leakage controls and named indicator status are exposed. Seven defensible research features and a reconciled non-circular label method are not established. |
| ML implementation and evaluation | 1/15 | Research code exists, but zero auditable research model runs/metrics. Synthetic-only training is isolated and not empirical evidence. |
| Explainability and transparency | 5/10 | UI separates predictions and explanation records and withholds unsupported outputs. No research model is available to explain. |
| Interface design and usability | 12/15 | Professional named pages, search/profile, coverage and empty states are present; live app loaded. Full browser interaction, small-screen and accessibility audits remain incomplete. |
| Functionality and reliability | 8/10 | PostgreSQL health, database-backed app render, focused and full automated suite (see final result below). Some manual control/download/failure paths were not exercised. |
| Presentation readiness and documentation | 4/5 | Runbook, source audit, reconciliation, demo sequence, limitations, and supervisor questions are recorded. Presenter must clearly separate synthetic from research mode. |
| **Total** | **55/100** | Strongest as an operational research/data-quality prototype; not a validated lifecycle-prediction system. |

This score is an examiner-style engineering judgment, not a formal university mark. It does not claim a user study or confirmation of the thesis hypothesis.

## Final implementation addendum — 2026-11-17

This addendum supersedes earlier test counts in this report. It records the final rescue changes and verification performed after the readiness work above.

### Additional files changed

- `src/data_ingestion.py` — made canonical PostgreSQL extraction read-only, blocked implicit CSV/proxy fallback unless explicitly enabled for development, tightened SRS field/row/null and satisfaction checks, represented absent canonical sources as empty evidence, and corrected survey-year reporting (years are no longer parsed as Unix timestamps). Source manifest proxy warnings now reflect the active source mode.
- `src/research_readiness.py` — added source provenance and six-dataset readiness gates.
- `pipeline/run_pipeline.py` — runs provenance checks and EDA, then stops before feature/label/model stages if the evidence gate fails.
- `src/eda.py` — added reproducible hashed profiles, coverage/missingness summaries, distribution/correlation outputs, and safe handling of empty source frames.
- `src/common.py`, `src/feature_engineering.py` — represented the seven named SRS feature slots; prevented usage/interest/admiration from substituting for satisfaction, required traceable observed/reported adoption evidence for enterprise indicators, and left the undefined company-diversity formula unavailable.
- `src/labelling.py` — default research label creation is blocked while the written SRS rule and legacy future-ratio rule remain unreconciled. Exploratory use requires an explicit `TECHPULSE_ALLOW_EXPLORATORY_RATIO_LABELS=true` setting.
- `src/model_training.py` — default research training requires a PostgreSQL-only source manifest and all six source contracts to pass.
- `tests/test_ingestion.py`, `tests/test_features.py`, `tests/test_research_readiness.py`, `tests/test_eda_readiness.py`, `tests/test_canonical_contract.py` — added/refined contract tests for proxy isolation, source evidence, missing indicators, empty EDA inputs, year coverage, and current seven-feature SRS structure.
- `outputs/data_quality_report.json`, `outputs/data_sources.json`, `outputs/eda_report.json`, `outputs/eda/` — regenerated by the read-only pipeline attempt for the live database. No model, feature snapshot, label or prediction was generated by it.
- `docs/ENGINEERING_TRACEABILITY.md` — requirement-to-code/data/test traceability and legacy-to-canonical source mapping.

### Final data and pipeline result

`python -m techpulse.cli db-health` passed: PostgreSQL 18.3, six canonical schemas, two applied migrations. The pipeline's PostgreSQL reads and EDA passed; the explicit research data-quality gate correctly stopped later stages:

| Logical input | Current PostgreSQL rows | Result |
|---|---:|---|
| Community observations | 0 | Fails minimum 50; one critical Stack Exchange quality check remains failed. |
| Developer survey observations | 684 | Fails semantic requirement: there is no satisfaction score; values are usage, interest and admiration. |
| Source-linked company technology evidence | 0 | Fails minimum 50; no verified enterprise adoption observations. |
| Company profiles | 497 | Structural source check passes; profiles do not prove technology use or Kenya coverage. |
| Technology metadata | 267 | Fails category completeness; canonical categories are currently absent. |
| Question-to-company mapping | 0 | Relation is not represented in the canonical schema. |

This pipeline failure is an expected, accurate research-readiness result, not a passing model run. No database write or migration occurred. No research feature matrix, lifecycle labels, trained model, research metrics, predictions, or explanation records were created. The app's research database still contains zero Kenya-specific observations. Existing legacy output/model artifacts must not be cited as current research results.

The isolated SQLite demonstration database was inspected read-only. It contains four executed synthetic-only model runs. For completeness, its stored synthetic holdout scores are:

| Synthetic model | Accuracy | Weighted F1 |
|---|---:|---:|
| Logistic Regression | 0.843 | 0.852 |
| K-Nearest Neighbours | 0.870 | 0.878 |
| Random Forest | 0.889 | 0.895 |
| XGBoost | 0.889 | 0.895 |

These scores are computations on deterministic synthetic examples only. They are **not** estimates of real-world performance, research evidence, or results for the approved thesis question. The seven-minute research defence should not show them; demonstrate synthetic mode only if the examiner wants to inspect the isolated UI workflow, and keep the synthetic label visible.

### Tests and operational verification

- `python -m pytest -q` — **99 passed, 16 warnings in 76.39 seconds**. Warnings were dependency deprecations/runtime notices from Matplotlib/Pyparsing, Joblib, and scikit-learn; no test failed.
- Focused readiness contracts — **22 passed** after the enterprise-evidence and seven-feature contract updates.
- `python -m pipeline.run_pipeline` — FR-01 extraction PASS, source/proxy gate PASS, FR-02 EDA PASS, data-quality gate FAIL as expected. It did not proceed to feature, label, model, evaluation, or SHAP stages.
- `python -m techpulse.cli db-health` — PASS, PostgreSQL 18.3, six schemas, two migrations.
- `http://localhost:8501/_stcore/health` — HTTP 200 `ok`; Streamlit process is listening on port 8501.
- No database migrations or writes were run.

The final report refresh was run after the full test suite because several tests create temporary source-manifest fixtures in the shared `outputs/` directory. The current `outputs/data_sources.json` and `outputs/data_quality_report.json` describe PostgreSQL canonical compatibility mode and the counts above.

### Exact application startup

The running application is at [http://localhost:8501](http://localhost:8501). From a new PowerShell session, use:

```powershell
Set-Location "C:\Users\Administrator\Downloads\TechPulse-main (4)\TechPulse-main"
python -m techpulse.cli db-health
python -m streamlit run dashboard/app.py --server.port 8501
```

If 8501 is already in use, open the current app or start a second instance with `--server.port 8502`. For the isolated synthetic walkthrough, select **Synthetic demonstration · separate SQLite** in the sidebar. Do not run `dashboard.demo_store --build --force` during the defence; the already seeded store was verified and does not need rebuilding. Do not run migrations or ingestion commands during the presentation.

The earlier eight-minute demonstration script and examiner questions remain applicable. Start in Research mode, show data readiness and limits, and explicitly say that the empirical prediction experiment could not be run with the validated sources currently present. Do not present synthetic results as thesis findings.

## Current synthetic demonstration implementation update — 2026-11-17

This later update supersedes the old synthetic counts and scores immediately above. It records the expanded demo requested after the research-readiness implementation. It does not replace or alter the approved research objective, and it does not put synthetic observations into PostgreSQL.

### Implementation and database record

- Added `dashboard/demo_migrations/003_scaled_synthetic_demo.sql` as an additive migration to the existing SQLite demo database. No PostgreSQL schema or data was changed. Before expansion, the SQLite database was backed up to `outputs/synthetic_demo/backups/techpulse_demo_before_scale_20261117_161220.sqlite`.
- Added `dashboard/demo_population.py` for repeatable synthetic generation, validation, feature construction, chronological model training, persisted predictions and probabilities, SHAP records, and a seed-run audit log. Repeated population is idempotent for generated entity/observation keys; successful seeding is recorded as an additional audit event.
- Expanded `dashboard/demo_store.py` for migration, population, and backup-gated reset. `dashboard/app.py` opens fresh sessions in the isolated synthetic SQLite mode for a ready walkthrough; the user must explicitly select Research mode. There is no automatic fallback between modes.
- Expanded `dashboard/demo_renderer.py` with community history, expanded profile/ranking/sentiment/enterprise/geography views, database-backed model laboratory, class-level metrics and probabilities, and CSV downloads. The pages retain prominent synthetic notices. The methodology page distinguishes the demonstration's future six-month versus trailing three-month generated-volume rule from the SRS rule.
- Expanded `tests/test_dashboard_demo_mode.py` for isolation, seed counts, probabilities, labels, persisted explanations, app default, and every demo page. `tests/test_dashboard_postgres.py` selects Research mode for its failed-connection check.
- Updated the top-level `README.md`, `outputs/synthetic_demo/README.md`, `docs/ENGINEERING_TRACEABILITY.md`, `docs/THREE_DAY_PRESENTATION_RESCUE.md`, and `docs/FINAL_PRESENTATION_RUNBOOK.md` so current seed counts, mode behavior, research limitations, and safe demo instructions are recorded. Generated/updated outputs are `outputs/synthetic_demo/techpulse_demo.sqlite` and its model artifacts; the pre-expansion SQLite backup is retained under `outputs/synthetic_demo/backups/`.

The SQLite database has 210 technology records; 15,120 monthly community observations; 7,560 historical signal observations; 8,400 fictional discussion records; 15,120 generated sentiment observations; 3,360 survey-like rows; 300 fictional company profiles; 1,500 company-technology relationships; 2,000 adoption scenarios; 1,260 geographic scenarios, including 630 fictional Kenya-labelled records; 8,820 feature snapshots; 210 latest synthetic lifecycle assessments; four model runs; 840 predictions; 2,520 class probabilities; 1,470 Random Forest SHAP explanation rows; and 16 time-series CV fold results. All generated records identify as `SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE`. The Kenya examples are fabricated scenarios, not Kenya observations. These counts describe only the isolated demo database.

The existing database passed SQLite `integrity_check` (`ok`) and `foreign_key_check` (no violations). Among the 210 latest synthetic lifecycle assessments, there are 151 Stable, 43 Growing, and 16 Declining labels. The model holdout contains 1,890 monthly rows: 1,362 Stable, 307 Growing, and 221 Declining. It spans 2023-10 through 2024-06 after training data through 2023-09; all four models also have four expanding-window validation folds.

### Executed synthetic model results

These are actual metrics from saved model runs on generated features and generated labels. They are not empirical evidence or estimates for real technologies. In particular, aggregate accuracy hides poor minority-class performance.

| Model | Accuracy | Weighted F1 | Macro F1 | Declining recall |
|---|---:|---:|---:|---:|
| Logistic Regression | 0.721 | 0.604 | 0.279 | 0.000 |
| K-Nearest Neighbours | 0.710 | 0.673 | 0.452 | 0.059 |
| Random Forest | 0.721 | 0.697 | 0.509 | 0.127 |
| XGBoost | 0.738 | 0.686 | 0.450 | 0.014 |

Logistic Regression predicted only Stable on this holdout. The demo model laboratory exposes per-class results and confusion matrices, and warns about the low Declining recall. Do not describe this experiment as predicting real technology decline or as validating the thesis hypothesis.

### Current verification and startup

- All 12 synthetic dashboard pages rendered with no Streamlit exceptions in an AppTest smoke check. Community chart rendering uses Plotly because the installed Altair/jsonschema combination failed locally.
- The focused dashboard/data-readiness suite passed **51 tests** after fixing two assertions/metadata issues.
- Final `python -m pytest -q` — **102 passed, 16 warnings in 82.41 seconds**. Warnings were Matplotlib/Pyparsing deprecations, pytest-asyncio configuration, Joblib CPU discovery, and scikit-learn feature-name notices. No failures.
- `python -m techpulse.cli db-health` — PASS, PostgreSQL 18.3, all six canonical schemas, two migrations. This is a health/read-only check; no Research PostgreSQL data or schema was changed.
- The app health endpoint returned HTTP 200 (`ok`) at `http://localhost:8501/_stcore/health` after code updates.
- No new external or academic data source was acquired or verified. Research PostgreSQL remains without valid curated community observations, verified adoption observations, Kenya-specific research observations, or a canonical research model run. The Stack Exchange source remains blocked for impossible upstream zero-total rows; they were not edited or silently dropped.
- Final `python -m techpulse.cli validate-data` reproduced the input gate: local Stack Exchange CSV (45,238 rows; SHA-256 `399e605b062480664d1989e12c98b57c282c158201903d60e55cfa37d3598e26`) has two invalid cumulative snapshots on 2018-02-21; local developer survey CSV (685 rows) has a conflicting Supabase 2024 source-category key; local Fortune list has 500 structurally valid company profiles but no verified technology-use evidence. These source files were read and left unchanged. PostgreSQL `db-health` passed, but canonical research inputs remain inadequate. Synthetic/demo rows are not data sources for the research objective.

From PowerShell in the project directory, start the ready synthetic demonstration with:

```powershell
python -m dashboard.demo_store --build
python -m streamlit run dashboard/app.py --server.port 8501
```

Open `http://localhost:8501`; fresh sessions begin in the populated synthetic demo. Choose **Research data · PostgreSQL** deliberately if you need to present genuine research readiness. Keep the mode banner visible while demonstrating synthetic features. If port 8501 already hosts this checkout, use it; otherwise choose 8502.

### Eight-minute demonstration and defence notes

1. **0:00–0:45, question and contribution.** State the approved technology trajectory question, data sources, and intended Growing/Stable/Declining outcome. Explain that verified inputs are insufficient for a defensible research model; the contribution currently includes the application, provenance and validation workflow, and an honest feasibility result.
2. **0:45–1:45, verified research evidence.** Select Research mode. Show PostgreSQL health and source coverage; identify the Stack Exchange cumulative snapshot anomalies and explain that ingestion blocks rather than alters them. Distinguish 684 global survey records from satisfaction, which is not measured.
3. **1:45–2:30, limitations.** Show empty community/adoption/Kenya/prediction states. Say “unavailable” is not zero and no verified Kenya-specific observations or enterprise adoption evidence were found.
4. **2:30–2:50, mode boundary.** Select the synthetic demo and point to the persistent banner. State that no following synthetic record or result is thesis evidence.
5. **2:50–4:00, app journey.** Search a technology; show community timeline, feature values, source/availability labels, rankings and CSV export. Show fictional company and Kenya-labelled examples only with their synthetic status visible.
6. **4:00–5:45, modelling.** Show the generated-label rule, chronological holdout, four-fold CV, the four models, per-class metrics and confusion matrix. Point out imbalanced labels and poor Declining recall. If asked, show stored class probabilities and RF SHAP, explicitly limited to synthetic data.
7. **5:45–6:40, reproducibility.** Show the SQLite data observatory and seed-run record. Explain additive migration, safe repeatable seeding, integrity checks, and separate PostgreSQL research storage.
8. **6:40–8:00, close.** Return to research limitations, preserve the approved objective, and state which label/horizon, validation approach, adoption evidence, and Kenya coverage decisions need supervisor guidance.

Likely examiner questions:

- **Why are there model results if research readiness failed?** They are generated solely to verify model-to-database-to-dashboard plumbing. Their identifiers, source provenance, banners and separate SQLite location mark them as synthetic.
- **Does the 0.738 XGBoost accuracy mean the system predicts technology growth?** No. It measures generated labels on generated inputs; class imbalance and 0.014 Declining recall show the limitation even within that simulation. It is not evidence about real technologies.
- **Are the Kenya rows evidence of local technology adoption?** No. They are explicitly fabricated Kenya-labelled scenarios in demo mode. Research PostgreSQL contains zero verified Kenya observations.
- **Why not repair the source CSV?** The invalid cumulative records need an authoritative correction and provenance. Changing or dropping them without that evidence would fabricate a source correction.
- **What remains for a real experiment?** Verified time-aligned community, satisfaction, enterprise and other required observations; an approved non-circular label/horizon; sufficient examples in all classes; and a documented temporal evaluation plan.

Supervisor clarification remains necessary for: the approved lifecycle rule/horizon and target leakage; chronological versus stratified validation; company diversity/adoption-velocity definitions and qualifying evidence; whether Kenya-specific output is mandatory; how to handle the 2024 survey category collision; and whether a feasibility/data-quality defence is acceptable if adequate research observations remain unavailable.
