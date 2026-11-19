# PostgreSQL dashboard guide

## Data access rules

Every Streamlit page uses `dashboard/db/repositories.py`. SQL text is centralized in `dashboard/db/queries.py`; connection pooling, timeouts, read-only transactions, and typed database errors are in `dashboard/db/connection.py`. Health and required-schema checks are in `dashboard/db/health.py`. Read queries are cached for the configured short TTL. Query parameters are bound values. No Streamlit page reads the legacy schema, local CSV inputs, or model files.

If `DATABASE_URL` is absent, invalid, pointed to the wrong database, or PostgreSQL is unavailable, the sidebar and affected page show an error. The app never silently switches to CSV.

## Page-to-table mapping

| Page | Canonical source tables |
|---|---|
| Executive Overview | `core.technologies`, `audit.data_sources`, `audit.ingestion_runs`, `audit.data_quality_checks`, `analytics.developer_survey_observations`, `analytics.community_monthly_metrics`, `ml.model_runs`, `ml.model_predictions` |
| Technology Explorer | `core.technologies`, `core.technology_aliases`, `core.technology_category_memberships`, `analytics.developer_survey_observations`, `analytics.community_monthly_metrics`, `analytics.live_technology_observations`, verified `analytics` Kenya observations, valid `ml.model_predictions` |
| Kenya Technology Landscape | `analytics.kenya_ict_indicators`, `analytics.training_programme_observations`, reviewed `analytics.job_market_observations`, explicit-geography `analytics.company_technology_evidence` |
| Technology Rankings | canonical technology counts and `analytics.developer_survey_observations` / `analytics.community_monthly_metrics` |
| Community Health | `analytics.community_monthly_metrics`, `audit.data_sources`, `audit.ingestion_runs`, `audit.ingestion_errors`, `audit.data_quality_checks` |
| Market and Skills Signals | `analytics.developer_survey_observations`, `analytics.developer_skill_observations`, Kenya-scoped training and terms-reviewed job observations |
| Prediction Explorer | `ml.model_predictions`, `ml.model_runs`, `ml.feature_snapshots`, `ml.technology_labels`, `ml.label_definitions`, `ml.prediction_explanations` |
| Model Performance | `ml.model_runs`, `ml.model_candidates`, `ml.model_metrics`, `ml.model_class_metrics`, `ml.baseline_results` when recorded |
| Live Technology Intelligence | `analytics.live_technology_observations`, `audit.data_sources` |
| Data Provenance and Quality | `audit.data_sources`, `audit.source_documents`, `audit.ingestion_runs`, `audit.ingestion_errors`, `audit.data_quality_checks`, PostgreSQL table statistics |
| About and Responsible Use | Static methodology and responsible-use language; contains no data query |

The dashboard creates **no PostgreSQL views**. All pages read canonical tables through repository queries. Empty relation results remain empty and are labeled unavailable; they are not converted to zero or imputed.

## Prediction validity

Predictions are displayed only when the prediction joins to a successful recent model run, a persisted feature snapshot, a label definition, and matching technology/geography labels. The prediction's as-of date must match the feature snapshot date, and the prediction timestamp cannot be in the future. Synthetic test-run artifacts in `outputs/` are not read by the dashboard.

## Evidence interpretation

Survey pages retain survey year and geography. The Kenya landscape only queries records whose canonical geography is `KE`, with source-class/terms checks where relevant. Global/unspecified survey data is always labeled separately. A company profile does not count as technology adoption. GitHub stars, Stack Exchange questions, package releases, and downloads are supplementary indicators, not proof of production use.

## Run and troubleshoot

See [PostgreSQL and pgAdmin 4 setup](POSTGRESQL_PGADMIN4.md). Start the application from the repository root:

```powershell
python -m streamlit run dashboard/app.py
```

The test suite includes repository integration checks and renders every page against the current database. For manual verification, inspect the sidebar's connection/schema status, open each page, and confirm the empty Kenya, community-blocked, and no-prediction states match current source coverage.
