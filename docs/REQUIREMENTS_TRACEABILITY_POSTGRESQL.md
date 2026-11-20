# TechPulse PostgreSQL rebuild requirements traceability

This matrix maps the approved proposal, SRS, SDS and implementation plan found in `docs/` to the existing implementation. “Pending” means the current repository or database does not yet provide the evidence; it is not a claim of completion.

## Source documents reviewed

| Source | Finding |
|---|---|
| Project Proposal | Defines the research title and objectives; does not establish verified enterprise or Kenya observations in the checked data. |
| SRS | FR-01–FR-20 and NFR-* identifiers. FR-10 explicitly selects the highest **weighted F1** model. |
| SDS | Describes a PostgreSQL data layer and the four model families. |
| Implementation Plan | Reviewed as provided in `docs/implementation_plan.pdf`; current source data and test evidence are summarized in the implementation report. |
| Software Test Plan | No separate test-plan file was present in the repository. Existing `tests/` and SRS validation criteria were used; this does not substitute for an approved test plan. |
| Literature Review | No separate literature-review document was present. The proposal’s included references remain the available source. |

## Traceability

| Requirement source | Actual requirement | Database implementation | Application implementation | Test / verification |
|---|---|---|---|---|
| SRS FR-01 | Ingest and validate the six PostgreSQL source datasets | `raw`, `staging`, `audit`, `core`, `analytics` in migrations 001–002 | `techpulse.cli validate-data`, `ingest`, canonical PostgreSQL repositories | `tests/test_ingestion.py`, `tests/test_data_validation.py`; rerun required for final branch |
| SRS FR-02–FR-04 | EDA, feature engineering and lifecycle target assignment | `ml.feature_snapshots`, `ml.feature_values`, `ml.label_definitions`, `ml.technology_labels` | `src/` and `ml_pipeline/`; no valid research feature/label population is currently evidenced | Existing feature/label tests; research execution remains pending |
| SRS FR-05–FR-09 | Train Logistic Regression, KNN, Random Forest and XGBoost with a time-aware split | `ml.model_runs`, `ml.model_candidates`, `ml.model_metrics`, `ml.model_class_metrics` | Training modules and model registry queries | `tests/test_models.py`; current canonical PostgreSQL has no eligible research run |
| SRS FR-10 | Compare models and select by highest weighted F1 | Evaluation metrics in `ml.model_metrics` | Research Model Performance page | Conflict: additional user prompt requests macro F1. This new criterion must be documented as a deviation from FR-10 and must never be represented as unchanged approved SRS wording. |
| Additional model-selection prompt | Macro F1 primary, class support required, class-level F1/recall, inconclusive when evidence insufficient | `ml.model_selection_records` schema migration; source evaluation metrics remain in `demo.model_metrics` for synthetic demonstrations | `dashboard/model_selection.py` dynamically ranks PostgreSQL evaluation results; research pages show no winner without eligible research evidence; synthetic pages clearly label demo results | `tests/test_model_selection.py` and PostgreSQL demo integration tests |
| SRS FR-11, FR-15 | SHAP feature importance and explanation viewer | `ml.prediction_explanations` | Prediction and model pages show only persisted records | Existing tests; no research explanations are persisted |
| SRS FR-12–FR-19 | Search, profiles, trend/ranking pages, adoption, model performance, disclaimers and documentation | Canonical entities, observations and provenance relations in migrations 001–002 | PostgreSQL research pages in `dashboard/page_renderer.py` | Dashboard tests; dataset-specific pages may correctly show empty states |
| SRS NFR-SE-02 | Keep PostgreSQL credentials out of source | `.env.example` placeholders; `.env` ignored | SQLAlchemy connection reads `DATABASE_URL` | Inspect tracked files and repository ignore rules |
| SRS NFR-RL-01 / NFR-MA-03 | Idempotent pipeline and fixed random state | Source keys, natural keys and migration checksums | Ingestion and model pipeline code | Existing pipeline tests; rerun after implementation changes |
| SDS PostgreSQL data layer | Use PostgreSQL as persistent data layer | Canonical schemas and numbered migrations; isolated synthetic records are in PostgreSQL schema `demo` | Research and synthetic Streamlit readers use configured PostgreSQL; SQLite access remains only in the read-only import utility and legacy, non-runtime generator module | Full suite: 100 passed, 5 skipped; see `docs/POSTGRESQL_REBUILD_VERIFICATION.md` |
| User architecture prompt | One PostgreSQL operational database, synthetic and research provenance separated | Development database `techpulse_rebuild_dev`; schema `demo`; source checksum and counts persisted in `demo.migration_manifest` | App has PostgreSQL research and PostgreSQL synthetic views, with distinct data modes and no silent fallback | 27 targeted tests plus full suite; SQLite runtime removal confirmed by app dependency path inspection |

## Conflicts and limitations

1. The SRS FR-10 selection criterion is weighted F1; the new prompt requires macro F1. The latter is an implementation change that requires supervisor approval or an approved SRS revision.
2. The SRS specifies a fixed random state of 42 under NFR-MA-03; existing synthetic model code uses another documented seed. Seed behavior must be resolved against the approved experiment before research runs are created.
3. No separate Test Plan or Literature Review file was found. No test cases or sources are fabricated to fill that gap.
4. Synthetic generated records can exercise the interface but cannot substantiate the research question, enterprise adoption, Kenya-specific findings, or real-world model performance.
