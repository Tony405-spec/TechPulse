# TechPulse three-day presentation rescue and implementation status

**Checked:** 2026-11-17 (audit artifacts generated 2026-11-16)
**Repository:** `C:\Users\Administrator\Downloads\TechPulse-main (4)\TechPulse-main`
**Approved project title:** *Predicting Developer Technology Decline Using Community Signals and Enterprise Adoption Patterns: A Machine Learning Approach*

> **Latest implementation amendment (2026-11-17):** The later expanded SQLite demo and populated synthetic walkthrough supersede the earlier demo counts, model scores, and interface-default descriptions below. The separate demo now contains 210 technologies, saved synthetic observations/features, four executed synthetic model runs, predictions/probabilities, and RF SHAP records. Fresh sessions default to Synthetic demonstration mode; select Research mode deliberately to show genuine PostgreSQL evidence. The research limitations, approved title, zero verified Kenya observations, blocked Stack Exchange source, and absence of a valid research model remain unchanged. See [the current implementation report and presentation script](FINAL_IMPLEMENTATION_REPORT.md#current-synthetic-demonstration-implementation-update--2026-11-17) for verified counts, model metrics, tests, startup, and examiner questions.

## Executive status

The PostgreSQL-backed research application starts, and a separately selected synthetic demo application now exercises the requested presentation workflows. The final repository test suite passes (81 tests). The official DataCamp-hosted Stack Overflow course CSV was recovered and checksum-verified. Its two zero-total records are genuine upstream anomalies, and the validator now blocks both. A reproducible, non-training feasibility audit creates a monthly last-observation snapshot without changing the source data.

The supplied evidence does **not** support the approved three-class prediction objective. The database has no curated community observations, verified enterprise technology evidence, Kenya-specific technology observations, feature snapshots, lifecycle labels, model runs, predictions, or explanations. The historical candidate labels contain no `Declining` class in the available purged training or latest holdout sets. Accordingly, no research model was trained, evaluated, persisted, or presented as a result. This project title and research objective are preserved; the evidence gap is explicit.

The most defensible presentation in the remaining time is a reproducible source-provenance, data-quality, feasibility, and application-workflow demonstration. It is not a validated technology-decline prediction demonstration.

## Final application implementation update (2026-11-17)

The sidebar now requires an explicit mode choice. **Research data · PostgreSQL** remains the default and reads only the existing canonical PostgreSQL schemas. **Synthetic demonstration · separate SQLite** reads `outputs/synthetic_demo/techpulse_demo.sqlite`. A database error never changes modes automatically.

The separate synthetic database is relational and includes keys, foreign keys, unique constraints, indexes, source metadata, observation dates, model-run metadata, quality checks, model metrics, predictions, and explanations. It contains 12 fictional technologies, 864 simulated community rows, 72 survey-like rows, 45 fictional company examples, 492 feature/label snapshots, four model runs, 12 synthetic-only predictions, 84 SHAP explanation rows, and zero Kenya indicators. Every demo table carries `SYNTHETIC DEMONSTRATION DATA`; fictional company records say `NOT VERIFIED - SYNTHETIC ONLY` and use `synthetic://` source references.

All four requested classifiers were fitted on the simulated panel and evaluated on a chronological synthetic holdout. Those are actual computations on generated labels, not research results. The run records store train/test periods, seed, dataset/feature/label versions, model artifact paths, and SHA-256 checksums. SHAP is calculated for the synthetic Random Forest only. No demo row, metric, prediction, or explanation was inserted into PostgreSQL.

Synthetic-only holdout results (training: 2021-01 through 2023-08; test: 2023-09 through 2024-05): Logistic Regression accuracy 0.843 / weighted F1 0.852; KNN 0.870 / 0.878; Random Forest 0.889 / 0.895; XGBoost 0.889 / 0.895. These scores measure the generated simulation and are displayed only in demo mode. They are not claims about real technology prediction performance.

The app presents 11 separate synthetic-mode pages, including technology search/profile, rankings, fictional enterprise examples, synthetic survey-like charts, model comparison, SHAP, data observatory, and methodology. The Kenya page intentionally has no generated national indicators. The seven feature definitions include calculation, inputs, synthetic source, observation period, availability, and missing-data treatment. The demo's six-month-future versus trailing-three-month label rule is explicitly distinguished from the SRS rule and from research results. The shared UI now uses charcoal, linen, taupe, and oxblood accents. See [the final presentation runbook](FINAL_PRESENTATION_RUNBOOK.md).

## Protection and database state

- A complete repository copy was created at `C:\Users\Administrator\Documents\Codex\2026-11-16\files-pasted-by-the-user-techpulse\work\backups\TechPulse_20261116_preimplementation`. Verification found 1,294 files and 114,557,846 bytes in both copies.
- No `.git` directory is present in the supplied repository, so there is no commit history or Git rollback point.
- PostgreSQL reports version 18.3, all six schemas (`raw`, `staging`, `core`, `analytics`, `ml`, `audit`), and two recorded migrations.
- The SDS ERD/wireframes were visually reviewed. They depict a legacy `feature_matrix`/`technology_predictions` style store and six original data sources, while the current PostgreSQL implementation is a normalized six-schema canonical contract with separate feature values, labels, runs, predictions, and explanations. The two designs are not table-for-table identical; no destructive reconciliation was attempted. The SDS also describes company-stack evidence that the supplied company-profile file does not contain.
- No database migration, ingestion, or other database write was performed. A database dump was not needed for this read-only verification; do not run migrations for the presentation.
- Read-only counts: 267 technologies; 684 survey observations; 497 company profiles; 0 community observations; 0 verified company-technology evidence rows; 0 Kenya ICT indicators; 0 live observations; 0 feature snapshots; 0 technology labels; 0 model runs; 0 predictions; 0 explanation records.
- A first exploratory count query used a guessed table name (`ml.lifecycle_labels`) and PostgreSQL correctly rejected it. The actual canonical relation is `ml.technology_labels`; the corrected inventory query above completed read-only.

## Data source, discrepancies, and feasibility

### Verified Stack Overflow source

The official DataCamp course resource is [the downloadable Stack Exchange question-count CSV](https://assets.datacamp.com/production/repositories/3567/datasets/1e9257c9d86e03a979124c6d99a0ff154da953fd/stackexchange.csv). Its downloaded copy, `data/stackexchange (1).csv`, has SHA-256 `2f3404dc403331a3be28ce4e40ae6d92adf5f86daa02b0c5eee695d535ec08f1`. The primary `data/stackexchange.csv` matches its tag/date keys and count columns; share columns agree within `1e-6` due to serialization precision. Raw files were not edited.

The 45,238 rows cover 53 tags from 2016-01-01 to 2018-09-25. They are dated snapshots of cumulative tag totals and relative shares, not daily new-question arrivals. Summing the daily stock values into monthly totals would misstate activity; the feasibility script instead keeps the last valid observed row in each tag-month.

Two rows dated 2018-02-21 have zero `question_count`:

| Tag | question_count | unanswered_count | Validation issue |
|---|---:|---:|---|
| `amazon-mws` | 0 | 0 | Zero cumulative total |
| `ios` | 0 | 181,334 | Zero total and unanswered exceeds total |

Both records are in the upstream CSV. They remain intact in the raw source and are excluded from the derived descriptive snapshot. No values were imputed or repaired. The canonical ingestion remains blocked pending source-level resolution.

### Reproducible outcome feasibility check

Run `python scripts/run_presentation_feasibility_audit.py`. The script verifies the source checksum, compares the two local CSVs, flags invalid rows, derives monthly snapshots, and writes a timestamped JSON report, Markdown report, and candidate panels under `outputs/presentation_rescue/`. It does not connect to PostgreSQL, train a model, persist predictions, or create labels in the application database.

Run `20261116T205138Z` found 1,515 valid monthly snapshots over 53 tags. A six-month history and the existing 1.20/0.80 thresholds applied to the next three-month mean `question_pct` produced 1,091 candidate tag-month rows: Growing 30, Stable 1,061, Declining 0. The latest origin was 2018-06-01 (53 tags: Growing 4, Stable 49, Declining 0). After purging training targets that overlap the latest holdout feature date, there were 879 training rows (Growing 22, Stable 857, Declining 0). This is a feasibility probe of **relative Stack Overflow tag share only**. It is not the SRS label, direct developer activity, enterprise adoption, or technology lifecycle decline.

With a twelve-month feature history and twelve-month outcome window, the latest eligible origin was 2017-09-01. Purging overlapping outcomes leaves zero training rows. Neither setup supports a three-class model. No accuracy, F1, ROC-AUC, confusion matrix, SHAP values, or model comparison from these probes is reported.

The CLI validation record is `outputs/runs/data_quality_20261116T205144562049Z.json`. It correctly fails the community source's critical gate on the same two rows; the survey and company-profile files pass their configured structural checks. A structural pass does not establish complete provenance, representativeness, adoption, or suitability as aligned training features.

### Other required evidence

- The survey summary is global/unspecified, self-selected, and spans 2021-2024. Its source-level aggregation and per-year provenance remain incomplete. It is not Kenya-specific and is not temporally aligned as a feature for the 2016-2018 community rows.
- `fortune.csv` contains company profiles, not dated company technology-use evidence. There is no verified enterprise adoption evidence in the database.
- There are no Kenya-specific developer or enterprise technology observations. National connectivity and policy context must not be relabelled as technology adoption.
- Live GitHub, Stack Exchange, npm, and PyPI collectors are supplemental snapshots, not a replacement historical panel. Stars, questions, releases, and package downloads do not establish production adoption or unique users.
- Prior perfect-looking model artifacts are synthetic test fixtures or unauditable historical outputs. They are not research metrics and must not be quoted.

## Requirements traceability and scope status

This compact traceability table is based on the approved SRS, proposal, and SDS. It records current status; it does not amend or imply approval of the academic scope.

| Requirement | Status on 2026-11-16 | Evidence / reason |
|---|---|---|
| Preserve approved title and three-class research question | Preserved | Title remains unchanged; unsupported prediction is explicitly disclosed. |
| Acquire, validate, and preserve source provenance | Partial; verified for Stack Overflow source | Official course file checksum matches; anomalies are reproducibly flagged; survey/company lineage remains incomplete. |
| Canonical PostgreSQL and source lineage | Existing implementation verified healthy | Six schemas and two migrations; no new migration required or applied. Existing database remains the source for dashboard queries. |
| Seven SRS features (Technology Health, Growth Momentum, Question Quality, Company Diversity, Sentiment Delta, Adoption Velocity, Community Decay) | Not defensibly materialized for this evidence set | Required input streams and aligned time windows are absent; no canonical feature snapshots exist. Do not substitute unverified proxies. |
| SRS lifecycle labels (momentum and trailing 12-month volume trend) | Not generated or persisted | No valid canonical feature matrix or complete aligned label outcomes; table has zero rows. The feasibility audit's relative-share classes are separate and explicitly exploratory. |
| Logistic Regression, KNN, Random Forest, XGBoost comparison and temporal evaluation | No research model run | Training data lack Declining support; 12-month purged setup has no remaining train rows. Model code/tests do not constitute a research experiment. |
| Accuracy, weighted F1, ROC-AUC, confusion matrix, cross-validation | Unavailable as research results | No eligible persisted run/test outcomes. Never quote fixture or untraceable artifact scores. |
| Model registry and predictions | Schema exists; no research rows | Feature snapshots, model runs, predictions, and explanations each count zero. |
| SHAP explanation | Unavailable | No validated model run/prediction exists to explain. SHAP associations would not imply causation. |
| Interactive Streamlit application | Starts; database health verified | `dashboard/app.py` is already running on port 8501; Streamlit health endpoint returned `200 ok`. Data-dependent pages have empty states because the corresponding canonical tables are empty. |
| Enterprise adoption analysis | Blocked by unavailable evidence | Company profiles are not technology-stack evidence. |
| Kenya-specific landscape | Blocked by unavailable observations | Kenya indicator and survey-specific counts are zero; global and macro indicators cannot fill this gap. |
| Proposed public-secondary-data scope amendment | Not exercised; requires supervisor clarification | The new directive permits investigation/acquisition but does not constitute supervisor approval of a change to the approved proposal. No new source data were acquired or loaded in this deadline pass. |

## Files changed and generated

Changed:

- `src/cli.py` — reject non-positive cumulative Stack Overflow totals and report the stricter validation reason.
- `tests/test_canonical_contract.py` — regression test for a zero/zero cumulative-count row.
- `tests/test_live_data.py` — freeze the PyPI collector clock in the time-window test so the test is date-independent.
- `scripts/run_presentation_feasibility_audit.py` — checksum-guarded, non-training feasibility audit and derived artifacts.
- `docs/SOURCE_REGISTER.md` — official resource, checksum, semantics, and terms caveat.
- `docs/DATA_LINEAGE_AND_QUALITY.md` — both anomalies and cumulative-snapshot interpretation.
- `docs/PRESENTATION_DEMO_GUIDE.md` — updated source and unsupported-model talking points.
- `README.md` — restore the approved project title and point to current source and implementation status.
- `docs/THREE_DAY_PRESENTATION_RESCUE.md` — this status, evidence, traceability, and defence guide.
- `dashboard/app.py` — explicit research versus demo mode selection and mode-specific navigation.
- `dashboard/demo_store.py` — isolated SQLite schema, deterministic synthetic data, demo model training, predictions, SHAP, and artifact hashes.
- `dashboard/demo_renderer.py` — 11 synthetic mode pages using only the demo database.
- `dashboard/components/ui.py` — charcoal, taupe, linen, and oxblood visual theme.
- `tests/dashboard_demo_smoke_app.py` and `tests/test_dashboard_demo_mode.py` — demo isolation, page, filter/search, chart, model, and artifact checks.
- `docs/FINAL_PRESENTATION_RUNBOOK.md` — startup and ten-minute presentation sequence.

Generated, reproducible records:

- `outputs/presentation_rescue/20261116T205138Z/audit.json`
- `outputs/presentation_rescue/20261116T205138Z/report.md`
- `outputs/presentation_rescue/20261116T205138Z/monthly_snapshots.csv`
- `outputs/presentation_rescue/20261116T205138Z/three_month_feasibility_panel.csv`
- `outputs/presentation_rescue/20261116T205138Z/twelve_month_feasibility_panel.csv`
- `outputs/runs/data_quality_20261116T205144562049Z.json`
- `outputs/synthetic_demo/techpulse_demo.sqlite` — isolated synthetic-only relational database.
- `outputs/synthetic_demo/artifacts/` — four checksummed synthetic-only model artifacts.

No original dataset, PDF, PostgreSQL row, or PostgreSQL schema was changed. A separate synthetic SQLite database was created for the explicitly selected walkthrough mode. Since no `.git` metadata exists, this enumerated record and the verified pre-implementation backup are the change log/recovery reference.

## Verification results

| Check | Result |
|---|---|
| Repository backup | Verified: 1,294 files and 114,557,846 bytes at source and backup; both Stack Exchange CSV hashes match the backup copy. |
| `python scripts/run_presentation_feasibility_audit.py` | Completed; official checksum matched; primary/source comparison passed; two invalid source rows; no model trained. |
| `python -m techpulse.cli validate-data` | Expected critical failure on the two zero-total community rows; timestamped report created. |
| `python -m techpulse.cli db-health` | Healthy; PostgreSQL 18.3; six schemas; two migrations. |
| Read-only canonical table inventory | Completed; counts listed above. No database writes. |
| Earlier rescue-pass `python -m pytest -q` (2026-11-16) | **60 passed**, 16 warnings, 44.67 seconds. Superseded by the final application suite below. |
| `python -m pytest tests/test_dashboard_demo_mode.py -q` | **21 passed**, including all demo pages, isolation, search, class support, model metadata, checksums, and analytical chart rendering. |
| Final `python -m pytest -q` (2026-11-17) | **81 passed**, 16 warnings, 53.54 seconds. Warnings are dependency deprecations/compatibility notices. This includes research-mode PostgreSQL checks and demo-mode checks; no test failures. |
| Streamlit process | Port 8501 was already occupied by `python -m streamlit run dashboard/app.py --server.headless true`; `http://127.0.0.1:8501/_stcore/health` returned **200 / ok**. Starting a second server on that port was correctly refused. |

## Exact start instructions

From PowerShell at the repository root:

```powershell
python -m techpulse.cli db-health
python -m dashboard.demo_store --build
python -m streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). If it reports that port 8501 is occupied and that is the already-running TechPulse instance, use that existing URL. To use a second port, run `python -m streamlit run dashboard/app.py --server.port 8502`. Choose the data mode explicitly in the sidebar. Do not run migrations, ingestion, or a live-API collection during the timed presentation. If PostgreSQL is unavailable, verify the local `.env` `DATABASE_URL` and PostgreSQL service before the presentation; switching to synthetic mode is a presenter decision and the app does not switch automatically.

For a fresh environment, use Python 3.10+, create/activate `.venv`, install `requirements.txt`, configure `DATABASE_URL` using the local ignored `.env`, and run the two commands above. Do not copy credentials into slides or source files.

## Eight-minute research-mode sequence

For the combined research/synthetic walkthrough, use [the final presentation runbook](FINAL_PRESENTATION_RUNBOOK.md).

1. **0:00-0:45 — Research problem.** State the approved title and intended three classes. Explain that the project asks whether community, enterprise, and sentiment signals can predict trajectories; this demonstration will distinguish that objective from what the data can currently support.
2. **0:45-1:45 — Startup and database.** Run `db-health`; show PostgreSQL 18.3, six schemas, and two migrations. State that the dashboard reads canonical PostgreSQL and that no database writes/migrations were made in this rescue pass.
3. **1:45-3:15 — Source provenance and quality.** Open the Data Provenance and Quality page. Show the official DataCamp source entry, the two 2018-02-21 anomalies, and the validation JSON. Explain raw preservation and why the community ingestion gate fails.
4. **3:15-4:15 — Reproducible transformation.** Run `python scripts/run_presentation_feasibility_audit.py` if time permits, or open the saved report. Explain last-observation-per-tag-month because the source contains cumulative snapshots. Show that the script neither repairs data nor writes to PostgreSQL.
5. **4:15-5:30 — Feasibility and methodology.** Show the candidate class counts, purged split, and zero Declining examples. Distinguish the probe's relative tag-share labels from the SRS label rule, which requires Growth Momentum Index plus trailing 12-month volume trend. State that no research model or metric exists.
6. **5:30-6:45 — Application journey.** Navigate Technology Explorer/Rankings, Prediction Explorer, Model Performance, and the explanation view. Demonstrate real database-backed catalogue/survey content and honest empty states for missing predictions, Kenya records, and SHAP. Explain missing is not zero.
7. **6:45-7:30 — Limitations and contribution.** State that company profiles do not prove adoption, the survey is global/unspecified, and there are no Kenya observations. The defensible contribution is source lineage, a hard data-quality gate, reproducible transformations, temporal feasibility analysis, and an application that exposes unavailable evidence.
8. **7:30-8:00 — Close.** Explain the next research step: obtain supervisor guidance, source valid time-aligned observations and verified adoption evidence, document definitions, then retrain and evaluate with a chronological holdout and persist only reproducible results.

In research mode, do not demonstrate an unsupported predicted class, research model score, SHAP chart, enterprise heatmap, or Kenya ranking. Do not call a candidate relative-share class a validated lifecycle label. Synthetic mode may show its own generated outputs only with the persistent synthetic notice described above.

## Likely examiner questions

**Why is there no model result?**
The verified historical source contains cumulative relative-share snapshots with two upstream zero-total anomalies. After preserving those rows and using complete-window candidate outcomes, the purged panel has no Declining examples; the longer 12-month setup has zero training rows after overlap purging. A three-class result would therefore be unsupported.

**Why not delete the bad rows or replace them?**
They are present in the publisher-hosted source and no authoritative correction was found. Removing them from the raw file would damage provenance. The derived feasibility analysis flags and excludes them while retaining the originals.

**What is being predicted in the feasibility audit?**
Nothing is predicted. It compares future and recent mean Stack Overflow tag question-share as a label-support probe. It does not measure technology lifecycle, enterprise adoption, or Kenyan usage, and no classifier is trained.

**Why not use the earlier 100% score?**
The prior comparison is a synthetic fixture or lacks a reproducible research input/run record. It is not a valid test result and is excluded from claims.

**Does the Fortune file show enterprise adoption?**
No. It contains company profiles and lacks verified company-technology evidence, observation dates, and adoption provenance.

**Does the survey show Kenyan developer sentiment?**
No. It is a global/unspecified self-selected survey aggregate. It cannot be presented as a Kenya sample.

**Why does the dashboard show unavailable values?**
The application queries canonical tables, which currently contain no eligible observations or model outputs for those functions. Unavailable is different from zero and safer than a fabricated value.

**What is the next defensible research action?**
Ask the supervisor whether to amend the evidence scope and label definition. Then acquire dated, reproducible community observations and verified company-technology evidence, document source terms, construct time-aligned feature snapshots/labels, and use leakage-controlled chronological evaluation.

## Supervisor clarification required

1. Does collecting additional public secondary data amend the approved proposal's existing-data-only scope, and what written approval/ethics process is required?
2. Should the SRS label rule be revised? Its Growth Momentum Index cutoffs and 12-month volume trend are specified, but the available source and current candidate feasibility rule do not operationalize the same construct.
3. What evidence standard and geographic coverage will satisfy “enterprise adoption patterns” and the intended Kenyan context? Company profiles and national connectivity indicators are not technology-adoption evidence.
4. If valid class support cannot be acquired before submission, should the dissertation report a feasibility/negative finding and defer predictive claims, or revise the study design formally?

## Remaining limitations and deferred work

The full requested end-to-end **research** path (new historical source acquisition, canonical ingestion, seven valid aligned research features, SRS labels, temporal four-model comparison, persisted research model, predictions, SHAP, and populated research analytics) is **not complete**. It is blocked by data adequacy/provenance and requires supervisor decisions on any scope or label change. Synthetic mode demonstrates end-to-end application plumbing on generated examples but is not research evidence or acceptance of the SRS. The existing codebase and schema provide pieces of the research path; passing tests and synthetic results do not establish research validity.

Before submission, rehearse application startup and database access on the presentation computer, open the saved audit/validation outputs locally, and keep the demo route to supported database views, reproducible data checks, and explicit research limitations.
