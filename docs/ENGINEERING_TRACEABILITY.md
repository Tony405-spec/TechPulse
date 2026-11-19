# TechPulse engineering and academic traceability

**Reviewed:** 2026-11-17
**Scope:** proposal, SRS, SDS, implementation plan, and Work-in-Progress test plan supplied with the project.

This register connects documented expectations to the current code and the evidence actually available. “Implemented” means the application has code for the requirement; it does not imply the research objective has been empirically validated.

| Requirement / reference | Implementation location | Evidence / status |
|---|---|---|
| Six logical source datasets, minimum 50 rows and required fields (SRS FR-01) | `src/data_ingestion.py`, `src/research_readiness.py` | Validators and hard gate implemented. PostgreSQL extraction currently fails several logical-source contracts; therefore feature/label/model stages stop. |
| Canonical normalized PostgreSQL architecture and lineage (SDS) | `migrations/001_canonical_schema.sql`, `src/data_ingestion.py`, `techpulse/` | Canonical schema and read-only compatibility projection implemented. No migration was run in this pass. |
| Descriptive summaries, missingness, distributions, date coverage, correlations (SRS FR-02) | `src/eda.py` | Implemented; reports include input hashes, date/missingness profiles, correlations with n>=30, plots where numeric values exist. Empty sources are handled. |
| Seven named indicators and 0–1 feature contract (SRS FR-03) | `src/common.py`, `src/feature_engineering.py` | All seven fields are represented. Unsupported evidence remains NaN; company diversity is withheld pending formula approval; survey usage/interest/admiration are not substituted for satisfaction. |
| Growing / Stable / Declining lifecycle labels (SRS FR-04) | `src/labelling.py`, `src/research_readiness.py` | Not empirically implemented under an approved definition. SRS GMI/slope rule differs from the legacy future-ratio rule and may reuse GMI as both target and predictor. Default label path is now blocked unless explicitly enabled as exploratory. |
| Four candidate classifiers, temporal splits and weighted F1 (WIP test plan / SDS) | `src/model_training.py`, `src/evaluation.py` | Code remains; direct default research training requires PostgreSQL-only provenance and all six source contracts passing. No valid data reaches that stage today; no research model was trained. |
| Stored predictions and explanations (SDS) | `dashboard/db/`, `src/shap_analysis.py` | Canonical persistence and read paths exist. Research DB currently has no verified run, predictions, or explanations. Synthetic demonstration equivalents are isolated in SQLite. |
| Current application journey and dashboard (SRS FR-11) | `dashboard/`, `streamlit_app.py` | Research and Synthetic Demonstration modes remain separate. PostgreSQL dashboard reads current canonical data and exposes missing evidence. Synthetic walkthrough uses its own SQLite store. |
| Deterministic, repeatable synthetic walkthrough (latest user directive) | `dashboard/demo_store.py`, `dashboard/demo_population.py`, `outputs/synthetic_demo/techpulse_demo.sqlite` | Existing SQLite store expanded in place through migration 003 and SQL-verified: 210 technologies, 15,120 community rows, 8,400 fictional questions, 3,360 annual survey-like rows, 300 company profiles, 1,500 company-technology relationships, 2,000 adoption observations, 1,260 geographic rows, 8,820 feature snapshots, 4 trained synthetic model runs, 840 predictions and 1,470 SHAP explanations. Generated records carry explicit synthetic origin and are not research evidence. |
| Survey source/database reconciliation | `scripts/reconcile_survey.py`, `outputs/research_integrity/survey_reconciliation.json`, `src/cli.py` | Read-only comparison is reproducible; identifies 685 source records vs 684 natural keys and the Supabase 2024 category conflict. Ingestion now rejects ambiguous conflicting keys. |
| Stack Exchange data integrity | `src/data_ingestion.py`, `src/cli.py`, `tests/test_canonical_contract.py` | Invalid zero-total cumulative snapshots are rejected; raw CSV is preserved. No replacement observations were fabricated. |
| Kenya-specific observations | Canonical DB: `core.kenya_ict_context` | No rows found. The project must present Kenya coverage as a limitation unless verified sources are supplied. |
| Validation approach: random stratified holdout vs chronological validation (SRS/WIP vs current implementation) | `src/model_training.py`, `docs/MODEL_METHODOLOGY.md` | Documents conflict. Current implementation uses chronological splitting; supervisor confirmation is required before claiming full document compliance. |
| Timing and usability acceptance thresholds (WIP test plan) | `tests/`, dashboard | Automated suite verifies core contracts and render paths. No formal latency benchmark, assistive-technology audit, or user study was run in this delivery. Do not claim those thresholds passed. |

## Legacy six-table adapter to canonical PostgreSQL mapping

| Legacy pipeline frame | Canonical source / mapping | Current constraint |
|---|---|---|
| `so_questions` | `core.community_questions` and `analytics.community_monthly_metrics` | No curated monthly facts currently available; bad upstream Stack Exchange snapshots remain blocked. |
| `dev_sentiment` | `analytics.developer_survey_observations` | Global/unspecified usage, interest and admiration data; no satisfaction measure. |
| `fortune500_stacks` | `analytics.company_technology_evidence` joined to source lineage | Zero source-supported adoption rows. Company profiles alone are not adoption. |
| `company_profiles` | `core.company_profiles` | Directory/profile metadata only. |
| `tech_metadata` | `core.technologies`, categories and memberships | No reviewed category-to-indicator measurement evidence. |
| `question_company_mapping` | No supported canonical relation | Not projected or synthesized. |
| `feature_matrix` | `ml.feature_snapshots` plus `ml.feature_values` | No canonical snapshots currently persisted. |
| `technology_predictions` | `ml.model_runs`, `ml.model_predictions`, `ml.prediction_explanations` | No verified research run, predictions or explanation rows. |

## Academic decisions still needed

1. Confirm one lifecycle-label rule and prediction horizon, and prevent target/predictor circularity.
2. Confirm temporal holdout and cross-validation requirements where the supplied documents conflict.
3. Approve an operational formula for company diversity and confirm evidence needed for adoption velocity.
4. Decide whether verified Kenya-specific analysis is a mandatory result or a documented coverage limitation.
5. Decide how to represent the Supabase 2024 category distinction without collapsing conflicting source observations.
6. Confirm whether the project may be defended as a feasibility and data-quality contribution if the necessary historical evidence cannot be obtained in time, while retaining the approved title/objectives.
