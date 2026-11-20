CREATE SCHEMA IF NOT EXISTS sim;
CREATE SCHEMA IF NOT EXISTS ml;

CREATE TABLE IF NOT EXISTS ml.schema_migrations (
    version text PRIMARY KEY,
    checksum char(64) NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ml.data_versions (
    data_version_id text PRIMARY KEY,
    seed integer NOT NULL,
    config_hash char(64) NOT NULL,
    generator_version text NOT NULL,
    git_commit text,
    generated_at timestamptz NOT NULL,
    expected_counts jsonb NOT NULL DEFAULT '{}'::jsonb,
    table_checksums jsonb NOT NULL DEFAULT '{}'::jsonb,
    class_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL CHECK (status IN ('generated','loaded','verified')),
    disclosure text NOT NULL DEFAULT 'SIMULATED DATA; NOT EMPIRICAL RESEARCH EVIDENCE'
);

CREATE TABLE IF NOT EXISTS sim.technology_metadata (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    technology_id text NOT NULL,
    technology_name text NOT NULL,
    category text NOT NULL CHECK (category IN ('Languages','Frameworks','Databases','Tools')),
    curve_family text NOT NULL,
    first_observed_month date NOT NULL,
    data_origin text NOT NULL CHECK (data_origin = 'SYNTHETIC_SIMULATION'),
    PRIMARY KEY (data_version_id, technology_id),
    UNIQUE (data_version_id, technology_name)
);

CREATE TABLE IF NOT EXISTS sim.company_profiles (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    company_id integer NOT NULL,
    company_name text NOT NULL,
    sector text NOT NULL,
    company_size text NOT NULL CHECK (company_size IN ('small','medium','large','enterprise')),
    ticker text,
    data_origin text NOT NULL CHECK (data_origin = 'SYNTHETIC_SIMULATION'),
    PRIMARY KEY (data_version_id, company_id),
    UNIQUE (data_version_id, company_name)
);

CREATE TABLE IF NOT EXISTS sim.stack_overflow_questions (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    technology_id text NOT NULL,
    observation_month date NOT NULL,
    question_volume integer NOT NULL CHECK (question_volume >= 0),
    answered_volume integer NOT NULL CHECK (answered_volume >= 0),
    unanswered_volume integer NOT NULL CHECK (unanswered_volume >= 0),
    answer_rate double precision NOT NULL CHECK (answer_rate BETWEEN 0 AND 1),
    closure_rate double precision NOT NULL CHECK (closure_rate BETWEEN 0 AND 1),
    mean_score double precision NOT NULL,
    seasonal_factor double precision NOT NULL CHECK (seasonal_factor > 0),
    shock_applied boolean NOT NULL,
    data_origin text NOT NULL CHECK (data_origin = 'SYNTHETIC_SIMULATION'),
    PRIMARY KEY (data_version_id, technology_id, observation_month),
    FOREIGN KEY (data_version_id, technology_id)
      REFERENCES sim.technology_metadata(data_version_id, technology_id),
    CHECK (answered_volume + unanswered_volume = question_volume)
);

CREATE TABLE IF NOT EXISTS sim.developer_survey (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    technology_id text NOT NULL,
    survey_year integer NOT NULL CHECK (survey_year BETWEEN 2000 AND 2200),
    respondent_count integer NOT NULL CHECK (respondent_count > 0),
    satisfaction_score double precision CHECK (satisfaction_score BETWEEN 0 AND 100),
    adoption_intent double precision CHECK (adoption_intent BETWEEN 0 AND 1),
    learning_curve_score double precision CHECK (learning_curve_score BETWEEN 0 AND 100),
    hype_component double precision NOT NULL,
    is_missing boolean NOT NULL DEFAULT false,
    data_origin text NOT NULL CHECK (data_origin = 'SYNTHETIC_SIMULATION'),
    PRIMARY KEY (data_version_id, technology_id, survey_year),
    FOREIGN KEY (data_version_id, technology_id)
      REFERENCES sim.technology_metadata(data_version_id, technology_id),
    CHECK (NOT is_missing OR (satisfaction_score IS NULL AND adoption_intent IS NULL AND learning_curve_score IS NULL))
);

CREATE TABLE IF NOT EXISTS sim.fortune500_stacks (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    adoption_id text NOT NULL,
    technology_id text NOT NULL,
    company_id integer NOT NULL,
    adoption_date date NOT NULL,
    end_date date,
    adoption_depth double precision NOT NULL CHECK (adoption_depth BETWEEN 0 AND 1),
    data_origin text NOT NULL CHECK (data_origin = 'SYNTHETIC_SIMULATION'),
    PRIMARY KEY (data_version_id, adoption_id),
    FOREIGN KEY (data_version_id, technology_id)
      REFERENCES sim.technology_metadata(data_version_id, technology_id),
    FOREIGN KEY (data_version_id, company_id)
      REFERENCES sim.company_profiles(data_version_id, company_id),
    CHECK (end_date IS NULL OR end_date >= adoption_date)
);

CREATE TABLE IF NOT EXISTS sim.question_company_mapping (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    mapping_id text NOT NULL,
    synthetic_question_id text NOT NULL,
    technology_id text NOT NULL,
    company_id integer NOT NULL,
    observation_month date NOT NULL,
    mapping_method text NOT NULL CHECK (mapping_method = 'SIMULATED_CO_OCCURRENCE'),
    data_origin text NOT NULL CHECK (data_origin = 'SYNTHETIC_SIMULATION'),
    PRIMARY KEY (data_version_id, mapping_id),
    FOREIGN KEY (data_version_id, technology_id, observation_month)
      REFERENCES sim.stack_overflow_questions(data_version_id, technology_id, observation_month),
    FOREIGN KEY (data_version_id, company_id)
      REFERENCES sim.company_profiles(data_version_id, company_id)
);

CREATE INDEX IF NOT EXISTS ix_sim_tech_anchor ON sim.stack_overflow_questions(data_version_id, technology_id, observation_month);
CREATE INDEX IF NOT EXISTS ix_sim_company_adoption ON sim.fortune500_stacks(data_version_id, technology_id, adoption_date);
CREATE INDEX IF NOT EXISTS ix_sim_survey_year ON sim.developer_survey(data_version_id, technology_id, survey_year);

-- Compatibility views adapt one canonical synthetic representation to the old contracts.
CREATE OR REPLACE VIEW sim.so_questions AS
SELECT data_version_id, technology_id AS technology, technology_id AS tag,
       observation_month AS creation_date, observation_month AS date,
       question_volume AS question_count, unanswered_volume AS unanswered_count,
       answered_volume AS answer_count, closure_rate, mean_score AS score,
       false AS is_closed, data_origin
FROM sim.stack_overflow_questions;

CREATE OR REPLACE VIEW sim.dev_sentiment AS
SELECT data_version_id, technology_id AS technology, survey_year,
       respondent_count, satisfaction_score,
       adoption_intent AS developer_interest_share,
       learning_curve_score, data_origin
FROM sim.developer_survey;

CREATE OR REPLACE VIEW sim.tech_metadata AS
SELECT data_version_id, technology_id AS technology,
       technology_name, category, curve_family, data_origin
FROM sim.technology_metadata;

CREATE OR REPLACE VIEW sim.stackoverflow AS
SELECT data_version_id, technology_id AS tag,
       observation_month AS date, question_volume AS question_count,
       unanswered_volume AS unanswered_count,
       (100.0 * unanswered_volume / NULLIF(question_volume, 0))::double precision AS unanswered_pct,
       answered_volume AS answer_count, closure_rate, mean_score AS score,
       data_origin
FROM sim.stack_overflow_questions;

CREATE OR REPLACE VIEW sim.company AS
SELECT data_version_id, company_id AS id, company_name AS name,
       ticker, sector, data_origin
FROM sim.company_profiles;

CREATE OR REPLACE VIEW sim.tag_company AS
SELECT data_version_id, technology_id AS tag, company_id, adoption_date,
       data_origin
FROM sim.fortune500_stacks;

CREATE OR REPLACE VIEW sim.tag AS
SELECT data_version_id, technology_id AS tag, category, data_origin
FROM sim.technology_metadata;

CREATE TABLE IF NOT EXISTS ml.feature_snapshots (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    technology_id text NOT NULL,
    anchor_date date NOT NULL,
    history_months integer NOT NULL CHECK (history_months >= 0),
    low_confidence boolean NOT NULL,
    feature_values jsonb NOT NULL,
    PRIMARY KEY (data_version_id, technology_id, anchor_date),
    FOREIGN KEY (data_version_id, technology_id)
      REFERENCES sim.technology_metadata(data_version_id, technology_id)
);

CREATE TABLE IF NOT EXISTS ml.labels (
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    technology_id text NOT NULL,
    anchor_date date NOT NULL,
    target_end_date date NOT NULL,
    trajectory_label text NOT NULL CHECK (trajectory_label IN ('Growing','Stable','Declining')),
    future_ratio double precision NOT NULL CHECK (future_ratio >= 0),
    ambiguous_case boolean NOT NULL,
    label_rule text NOT NULL,
    PRIMARY KEY (data_version_id, technology_id, anchor_date),
    FOREIGN KEY (data_version_id, technology_id, anchor_date)
      REFERENCES ml.feature_snapshots(data_version_id, technology_id, anchor_date)
);

CREATE TABLE IF NOT EXISTS ml.model_runs (
    model_run_id text PRIMARY KEY,
    data_version_id text NOT NULL REFERENCES ml.data_versions(data_version_id),
    model_name text NOT NULL,
    status text NOT NULL CHECK (status IN ('running','succeeded','failed')),
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    seed integer NOT NULL,
    protocol jsonb NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    selected_by_cv boolean NOT NULL DEFAULT false,
    artifact_uri text,
    artifact_sha256 char(64),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ml.model_metrics (
    metric_id bigserial PRIMARY KEY,
    model_run_id text NOT NULL REFERENCES ml.model_runs(model_run_id),
    evaluation_part text NOT NULL CHECK (evaluation_part IN ('outer_cv','test','baseline','ablation')),
    fold_number integer,
    metric_name text NOT NULL,
    class_label text CHECK (class_label IS NULL OR class_label IN ('Growing','Stable','Declining')),
    metric_value double precision,
    support integer CHECK (support IS NULL OR support >= 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ml_model_metric_scope
  ON ml.model_metrics(model_run_id, evaluation_part, COALESCE(fold_number,-1), metric_name, COALESCE(class_label,''));

CREATE TABLE IF NOT EXISTS ml.predictions (
    prediction_id bigserial PRIMARY KEY,
    model_run_id text NOT NULL REFERENCES ml.model_runs(model_run_id),
    data_version_id text NOT NULL,
    technology_id text NOT NULL,
    anchor_date date NOT NULL,
    predicted_label text NOT NULL CHECK (predicted_label IN ('Growing','Stable','Declining')),
    risk_score double precision NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    confidence double precision NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    low_confidence boolean NOT NULL,
    probabilities jsonb NOT NULL,
    FOREIGN KEY (data_version_id, technology_id, anchor_date)
      REFERENCES ml.feature_snapshots(data_version_id, technology_id, anchor_date),
    UNIQUE (model_run_id, data_version_id, technology_id, anchor_date)
);

CREATE TABLE IF NOT EXISTS ml.shap_global (
    model_run_id text NOT NULL REFERENCES ml.model_runs(model_run_id),
    class_label text NOT NULL CHECK (class_label IN ('Growing','Stable','Declining')),
    feature_name text NOT NULL,
    signal_family text NOT NULL CHECK (signal_family IN ('community','enterprise','sentiment')),
    mean_abs_shap double precision NOT NULL CHECK (mean_abs_shap >= 0),
    rank integer NOT NULL CHECK (rank > 0),
    PRIMARY KEY (model_run_id, class_label, feature_name)
);

CREATE TABLE IF NOT EXISTS ml.shap_local (
    prediction_id bigint NOT NULL REFERENCES ml.predictions(prediction_id),
    feature_name text NOT NULL,
    shap_value double precision NOT NULL,
    base_value double precision NOT NULL,
    explanation text NOT NULL,
    PRIMARY KEY (prediction_id, feature_name)
);

CREATE TABLE IF NOT EXISTS ml.ablation_results (
    model_run_id text NOT NULL REFERENCES ml.model_runs(model_run_id),
    signal_set text NOT NULL,
    evaluation_part text NOT NULL CHECK (evaluation_part IN ('outer_cv','test')),
    fold_number integer,
    metric_name text NOT NULL,
    metric_value double precision NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (model_run_id, signal_set, evaluation_part, fold_number, metric_name)
);

CREATE INDEX IF NOT EXISTS ix_ml_features_tech_anchor ON ml.feature_snapshots(data_version_id, technology_id, anchor_date);
CREATE INDEX IF NOT EXISTS ix_ml_labels_tech_anchor ON ml.labels(data_version_id, technology_id, anchor_date);
CREATE INDEX IF NOT EXISTS ix_ml_predictions_tech_anchor ON ml.predictions(data_version_id, technology_id, anchor_date DESC);
CREATE INDEX IF NOT EXISTS ix_ml_runs_version_status ON ml.model_runs(data_version_id, status, selected_by_cv);

CREATE OR REPLACE VIEW ml.v_latest_predictions AS
SELECT DISTINCT ON (p.data_version_id, p.technology_id)
       p.prediction_id, p.data_version_id, p.technology_id,
       t.technology_name, t.category, p.anchor_date, p.predicted_label,
       p.risk_score, p.confidence, p.low_confidence, p.probabilities,
       r.model_run_id, r.model_name
FROM ml.predictions p
JOIN ml.model_runs r ON r.model_run_id=p.model_run_id
JOIN sim.technology_metadata t
  ON t.data_version_id=p.data_version_id AND t.technology_id=p.technology_id
WHERE r.status='succeeded' AND r.selected_by_cv
ORDER BY p.data_version_id, p.technology_id, p.anchor_date DESC, p.prediction_id DESC;

CREATE OR REPLACE VIEW ml.v_dashboard_overview AS
WITH latest_version AS (
  SELECT * FROM ml.data_versions ORDER BY generated_at DESC, data_version_id DESC LIMIT 1
)
SELECT v.data_version_id, v.seed, v.generator_version, v.config_hash,
       v.class_distribution, v.status AS data_status,
       (SELECT count(*) FROM sim.technology_metadata t WHERE t.data_version_id=v.data_version_id) AS technology_count,
       (SELECT count(*) FROM sim.stack_overflow_questions q WHERE q.data_version_id=v.data_version_id) AS community_month_count,
       (SELECT count(*) FROM sim.developer_survey s WHERE s.data_version_id=v.data_version_id) AS survey_count,
       (SELECT count(*) FROM sim.fortune500_stacks f WHERE f.data_version_id=v.data_version_id) AS adoption_event_count,
       (SELECT count(*) FROM ml.labels l WHERE l.data_version_id=v.data_version_id) AS label_count,
       (SELECT count(*) FROM ml.model_runs r WHERE r.data_version_id=v.data_version_id AND r.status='succeeded') AS successful_model_count
FROM latest_version v;
