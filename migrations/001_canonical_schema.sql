-- TechPulse canonical schema v1. Additive and idempotent; never drops legacy data.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ml;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.schema_migrations (
  version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now(), checksum text NOT NULL
);
CREATE TABLE IF NOT EXISTS audit.data_sources (
  source_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_key text NOT NULL UNIQUE,
  publisher text, title text, url text, licence_terms text, methodology text,
  geographic_scope text NOT NULL DEFAULT 'unknown', source_class text NOT NULL
    CHECK (source_class IN ('observed','reported','inferred','sampled','proxy','externally_collected','unknown')),
  metadata jsonb NOT NULL DEFAULT '{}', active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit.source_documents (
  document_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  title text, url text, publication_period daterange, retrieved_at timestamptz,
  checksum text, licence_terms text, geography text, metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_source_documents_checksum
  ON audit.source_documents(source_id, checksum) WHERE checksum IS NOT NULL;
CREATE TABLE IF NOT EXISTS audit.ingestion_runs (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id bigint REFERENCES audit.data_sources,
  started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
  status text NOT NULL DEFAULT 'running' CHECK(status IN ('running','succeeded','failed','partial')),
  source_version text, checksum text, config_hash text, rows_read bigint, rows_written bigint,
  report jsonb NOT NULL DEFAULT '{}', error_summary text
);
CREATE TABLE IF NOT EXISTS audit.ingestion_errors (
  error_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid REFERENCES audit.ingestion_runs,
  occurred_at timestamptz NOT NULL DEFAULT now(), source_record_key text, error_type text, message text,
  record jsonb
);
CREATE TABLE IF NOT EXISTS audit.data_quality_checks (
  check_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid REFERENCES audit.ingestion_runs,
  check_name text NOT NULL, severity text NOT NULL CHECK(severity IN ('info','warning','critical')),
  passed boolean NOT NULL, observed_value jsonb, details text, checked_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS core.geographies (
  geography_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, code text UNIQUE NOT NULL,
  name text NOT NULL, level text NOT NULL, parent_id bigint REFERENCES core.geographies,
  source_id bigint REFERENCES audit.data_sources
);
CREATE TABLE IF NOT EXISTS core.technologies (
  technology_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, canonical_name text UNIQUE NOT NULL,
  description text, first_observed_at timestamptz, metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS core.technology_aliases (
  alias_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, technology_id bigint NOT NULL REFERENCES core.technologies,
  alias text NOT NULL, source_id bigint REFERENCES audit.data_sources, UNIQUE(alias, source_id)
);
CREATE TABLE IF NOT EXISTS core.technology_categories (
  category_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name text UNIQUE NOT NULL,
  description text, source_class text NOT NULL DEFAULT 'inferred'
);
CREATE TABLE IF NOT EXISTS core.technology_category_memberships (
  technology_id bigint REFERENCES core.technologies, category_id bigint REFERENCES core.technology_categories,
  source_id bigint REFERENCES audit.data_sources, confidence numeric CHECK(confidence BETWEEN 0 AND 1),
  PRIMARY KEY(technology_id, category_id, source_id)
);

CREATE TABLE IF NOT EXISTS raw.source_records (
  source_record_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid REFERENCES audit.ingestion_runs,
  source_id bigint REFERENCES audit.data_sources, natural_key text, observed_at timestamptz,
  collected_at timestamptz NOT NULL DEFAULT now(), payload jsonb NOT NULL, checksum text,
  UNIQUE(source_id, natural_key, checksum)
);
CREATE TABLE IF NOT EXISTS staging.validation_records (
  staging_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid REFERENCES audit.ingestion_runs,
  source_id bigint REFERENCES audit.data_sources, record jsonb NOT NULL, valid boolean NOT NULL,
  errors jsonb NOT NULL DEFAULT '[]', staged_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.community_questions (
  question_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  source_question_id text NOT NULL, technology_id bigint REFERENCES core.technologies,
  geography_id bigint REFERENCES core.geographies, observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz, answer_count integer CHECK(answer_count>=0), score integer, view_count bigint CHECK(view_count>=0),
  is_closed boolean, source_metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(source_id,source_question_id)
);
CREATE TABLE IF NOT EXISTS analytics.community_monthly_metrics (
  technology_id bigint REFERENCES core.technologies, geography_id bigint REFERENCES core.geographies,
  source_id bigint REFERENCES audit.data_sources, period_start date NOT NULL, observed_at timestamptz,
  collected_at timestamptz NOT NULL DEFAULT now(), question_count bigint CHECK(question_count>=0),
  unanswered_count bigint CHECK(unanswered_count>=0), median_score numeric, answer_rate numeric CHECK(answer_rate BETWEEN 0 AND 1),
  source_metadata jsonb NOT NULL DEFAULT '{}', PRIMARY KEY(technology_id,geography_id,source_id,period_start)
);
CREATE TABLE IF NOT EXISTS analytics.stack_exchange_tag_observations (
  observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  technology_id bigint REFERENCES core.technologies, geography_id bigint REFERENCES core.geographies,
  period_start date, question_count bigint, unanswered_count bigint, observed_at timestamptz,
  collected_at timestamptz NOT NULL DEFAULT now(), natural_key text NOT NULL, metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(source_id,natural_key)
);
CREATE TABLE IF NOT EXISTS analytics.github_repository_observations (
  observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  technology_id bigint REFERENCES core.technologies, geography_id bigint REFERENCES core.geographies,
  repository_id text NOT NULL, observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(),
  stars bigint CHECK(stars>=0), forks bigint CHECK(forks>=0), pushed_at timestamptz, created_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(source_id,repository_id,collected_at)
);
CREATE TABLE IF NOT EXISTS analytics.package_registry_observations (
  observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  technology_id bigint REFERENCES core.technologies, registry text NOT NULL, package_name text NOT NULL,
  observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(), version text, downloads bigint CHECK(downloads>=0),
  metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(source_id,registry,package_name,collected_at)
);
CREATE TABLE IF NOT EXISTS analytics.technology_release_events (
  release_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  technology_id bigint REFERENCES core.technologies, registry text, package_name text, version text,
  released_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(), metadata jsonb NOT NULL DEFAULT '{}',
  UNIQUE(source_id,registry,package_name,version)
);
CREATE TABLE IF NOT EXISTS analytics.live_technology_observations (
  observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  technology_id bigint REFERENCES core.technologies, geography_id bigint REFERENCES core.geographies,
  observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(), metric_name text NOT NULL,
  metric_value numeric, unit text, coverage jsonb NOT NULL DEFAULT '{}', metadata jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS analytics.developer_survey_observations (
  observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id bigint REFERENCES audit.data_sources,
  technology_id bigint REFERENCES core.technologies, geography_id bigint REFERENCES core.geographies,
  survey_year integer NOT NULL, observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(),
  respondent_count integer, worked_with_count integer, want_to_work_with_count integer, admired_count integer,
  usage_share numeric CHECK(usage_share BETWEEN 0 AND 1), interest_share numeric CHECK(interest_share BETWEEN 0 AND 1),
  admiration_share numeric CHECK(admiration_share BETWEEN 0 AND 1), source_class text NOT NULL DEFAULT 'reported',
  metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(source_id,technology_id,geography_id,survey_year)
);
CREATE TABLE IF NOT EXISTS analytics.developer_skill_observations (observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_id bigint REFERENCES audit.data_sources, technology_id bigint REFERENCES core.technologies,
 geography_id bigint REFERENCES core.geographies, period_start date, observed_at timestamptz,
 collected_at timestamptz NOT NULL DEFAULT now(), metric_name text NOT NULL, metric_value numeric,
 sample_size integer, source_class text NOT NULL, metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS analytics.job_market_observations (observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_id bigint REFERENCES audit.data_sources, technology_id bigint REFERENCES core.technologies,
 geography_id bigint REFERENCES core.geographies, period_start date, observed_at timestamptz,
 collected_at timestamptz NOT NULL DEFAULT now(), metric_name text NOT NULL, metric_value numeric,
 sample_size integer, terms_reviewed boolean NOT NULL DEFAULT false, source_class text NOT NULL,
 metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS analytics.kenya_ict_indicators (observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_id bigint REFERENCES audit.data_sources, geography_id bigint REFERENCES core.geographies,
 indicator_code text NOT NULL, period_start date, period_end date, observed_at timestamptz,
 collected_at timestamptz NOT NULL DEFAULT now(), value numeric, unit text, coverage jsonb NOT NULL DEFAULT '{}',
 metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(source_id,indicator_code,period_start));
CREATE TABLE IF NOT EXISTS analytics.training_programme_observations (observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_id bigint REFERENCES audit.data_sources, geography_id bigint REFERENCES core.geographies,
 programme_name text NOT NULL, technology_id bigint REFERENCES core.technologies, period_start date,
 observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(), participant_count integer,
 outcome_metric text, outcome_value numeric, source_class text NOT NULL, metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS core.company_profiles (company_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_id bigint REFERENCES audit.data_sources, source_company_id text, company_name text NOT NULL,
 country_code text, sector text, observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(),
 metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(source_id,source_company_id));
CREATE TABLE IF NOT EXISTS analytics.company_technology_evidence (evidence_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 company_id bigint REFERENCES core.company_profiles, technology_id bigint REFERENCES core.technologies,
 geography_id bigint REFERENCES core.geographies, observed_at timestamptz, collected_at timestamptz NOT NULL DEFAULT now(),
 evidence_type text NOT NULL, claim text, source_class text NOT NULL CHECK(source_class IN ('observed','reported','inferred','sampled','proxy','unknown')),
 confidence numeric CHECK(confidence BETWEEN 0 AND 1), metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS analytics.company_technology_evidence_sources (
 evidence_id bigint REFERENCES analytics.company_technology_evidence, source_id bigint REFERENCES audit.data_sources,
 document_id bigint REFERENCES audit.source_documents, source_record_key text,
 PRIMARY KEY(evidence_id,source_id,source_record_key));

CREATE TABLE IF NOT EXISTS ml.feature_snapshots (snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 created_at timestamptz NOT NULL DEFAULT now(), as_of_date date NOT NULL, source_snapshot text NOT NULL,
 config_hash text NOT NULL, feature_schema jsonb NOT NULL, code_version text, metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS ml.feature_values (snapshot_id uuid REFERENCES ml.feature_snapshots,
 technology_id bigint REFERENCES core.technologies, geography_id bigint REFERENCES core.geographies,
 feature_name text NOT NULL, feature_value numeric, is_missing boolean NOT NULL DEFAULT false,
 source_lineage jsonb NOT NULL DEFAULT '[]', PRIMARY KEY(snapshot_id,technology_id,geography_id,feature_name));
CREATE TABLE IF NOT EXISTS ml.label_definitions (label_definition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 name text UNIQUE NOT NULL, version text NOT NULL, definition text NOT NULL, parameters jsonb NOT NULL,
 predictor_exclusions jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS ml.technology_labels (snapshot_id uuid REFERENCES ml.feature_snapshots,
 technology_id bigint REFERENCES core.technologies, geography_id bigint REFERENCES core.geographies,
 label_definition_id bigint REFERENCES ml.label_definitions, as_of_date date NOT NULL,
 target_end_date date, label text CHECK(label IN ('Growing','Stable','Declining')), target_value numeric,
 metadata jsonb NOT NULL DEFAULT '{}', PRIMARY KEY(snapshot_id,technology_id,geography_id,label_definition_id));
CREATE TABLE IF NOT EXISTS ml.model_runs (model_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz, status text NOT NULL,
 code_version text, config_hash text, dataset_snapshot text, feature_snapshot_id uuid REFERENCES ml.feature_snapshots,
 label_definition_id bigint REFERENCES ml.label_definitions, seed integer, split_metadata jsonb NOT NULL DEFAULT '{}',
 feature_definitions jsonb NOT NULL DEFAULT '{}', hyperparameters jsonb NOT NULL DEFAULT '{}', artifact_path text, artifact_checksum text, metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS ml.model_candidates (candidate_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 model_run_id uuid REFERENCES ml.model_runs, model_name text NOT NULL, hyperparameters jsonb NOT NULL DEFAULT '{}', status text);
CREATE TABLE IF NOT EXISTS ml.model_metrics (metric_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 model_run_id uuid REFERENCES ml.model_runs, candidate_id bigint REFERENCES ml.model_candidates,
 split_name text NOT NULL, metric_name text NOT NULL, metric_value numeric, support integer,
 auditable boolean NOT NULL DEFAULT false, metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS ml.model_class_metrics (candidate_id bigint REFERENCES ml.model_candidates,
 class_name text NOT NULL, precision numeric, recall numeric, f1 numeric, support integer NOT NULL,
 PRIMARY KEY(candidate_id,class_name));
CREATE TABLE IF NOT EXISTS ml.model_predictions (prediction_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 model_run_id uuid REFERENCES ml.model_runs, technology_id bigint REFERENCES core.technologies,
 geography_id bigint REFERENCES core.geographies, as_of_date date NOT NULL, predicted_at timestamptz NOT NULL DEFAULT now(),
 predicted_label text CHECK(predicted_label IN ('Growing','Stable','Declining')),
 probability_growing numeric CHECK(probability_growing BETWEEN 0 AND 1),
 probability_stable numeric CHECK(probability_stable BETWEEN 0 AND 1),
 probability_declining numeric CHECK(probability_declining BETWEEN 0 AND 1),
 evidence_coverage numeric CHECK(evidence_coverage BETWEEN 0 AND 1), uncertainty numeric CHECK(uncertainty BETWEEN 0 AND 1),
 metadata jsonb NOT NULL DEFAULT '{}', UNIQUE(model_run_id,technology_id,geography_id,as_of_date));
CREATE TABLE IF NOT EXISTS ml.prediction_explanations (prediction_id bigint REFERENCES ml.model_predictions,
 feature_name text NOT NULL, attribution numeric, method text NOT NULL, interpretation text NOT NULL DEFAULT 'association',
 PRIMARY KEY(prediction_id,feature_name));
CREATE TABLE IF NOT EXISTS ml.baseline_results (result_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 model_run_id uuid REFERENCES ml.model_runs, baseline_name text NOT NULL, split_name text NOT NULL,
 metrics jsonb NOT NULL, class_support jsonb NOT NULL DEFAULT '{}', metadata jsonb NOT NULL DEFAULT '{}');

CREATE INDEX IF NOT EXISTS ix_questions_technology_date ON core.community_questions(technology_id,created_at);
CREATE INDEX IF NOT EXISTS ix_monthly_geo_period ON analytics.community_monthly_metrics(geography_id,period_start);
CREATE INDEX IF NOT EXISTS ix_survey_technology_year ON analytics.developer_survey_observations(technology_id,survey_year);
CREATE INDEX IF NOT EXISTS ix_live_technology_collected ON analytics.live_technology_observations(technology_id,collected_at);
CREATE INDEX IF NOT EXISTS ix_predictions_run_asof ON ml.model_predictions(model_run_id,as_of_date);

-- Reference geography values do not imply any observations are available.
INSERT INTO core.geographies(code,name,level)
VALUES ('GLOBAL','Global / geography unspecified','global'),
       ('KE','Kenya','country')
ON CONFLICT(code) DO NOTHING;

INSERT INTO core.technology_categories(name,description,source_class)
VALUES ('Languages','Programming and query languages','inferred'),
       ('Frameworks','Software frameworks and libraries','inferred'),
       ('Databases','Database and data-store technologies','inferred'),
       ('Cloud/Platforms','Cloud and platform technologies','inferred'),
       ('Tools','Other development tools','inferred')
ON CONFLICT(name) DO NOTHING;

COMMENT ON SCHEMA raw IS 'Immutable source payloads and reproducible collection lineage.';
COMMENT ON SCHEMA staging IS 'Validated and normalized ingestion records before curated loading.';
COMMENT ON SCHEMA core IS 'Canonical entities and event facts.';
COMMENT ON SCHEMA analytics IS 'Curated market and community observations; proxy claims are labeled.';
COMMENT ON SCHEMA ml IS 'Versioned time-aware feature, label, model and prediction artifacts.';
COMMENT ON SCHEMA audit IS 'Data source registry, run history, checks, and migration history.';
COMMENT ON TABLE analytics.live_technology_observations IS 'Supplementary snapshots; excluded from historical training absent a separate leakage review.';
COMMENT ON TABLE analytics.company_technology_evidence IS 'Evidence-backed technology claims. A company profile alone does not establish adoption.';
