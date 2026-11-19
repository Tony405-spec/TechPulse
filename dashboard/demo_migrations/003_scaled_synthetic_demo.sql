-- Additive schema for the isolated SQLite synthetic demonstration environment.
-- Research PostgreSQL schemas are not altered by this migration.

CREATE TABLE IF NOT EXISTS historical_technology_observations (
    observation_id INTEGER PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(technology_id),
    month TEXT NOT NULL,
    search_interest_index REAL NOT NULL CHECK(search_interest_index BETWEEN 0 AND 100),
    ecosystem_activity_index REAL NOT NULL CHECK(ecosystem_activity_index BETWEEN 0 AND 100),
    release_activity_index REAL NOT NULL CHECK(release_activity_index BETWEEN 0 AND 100),
    observation_type TEXT NOT NULL,
    data_origin TEXT NOT NULL,
    UNIQUE(technology_id, month)
);

CREATE TABLE IF NOT EXISTS developer_questions (
    question_id TEXT PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(technology_id),
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    discussion_text TEXT NOT NULL,
    score INTEGER NOT NULL,
    answer_count INTEGER NOT NULL CHECK(answer_count >= 0),
    sentiment TEXT NOT NULL CHECK(sentiment IN ('positive','neutral','negative')),
    geography TEXT NOT NULL,
    data_origin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sentiment_observations (
    sentiment_id INTEGER PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(technology_id),
    month TEXT NOT NULL,
    positive_share REAL NOT NULL CHECK(positive_share BETWEEN 0 AND 1),
    neutral_share REAL NOT NULL CHECK(neutral_share BETWEEN 0 AND 1),
    negative_share REAL NOT NULL CHECK(negative_share BETWEEN 0 AND 1),
    satisfaction_score REAL NOT NULL CHECK(satisfaction_score BETWEEN 0 AND 100),
    sample_count INTEGER NOT NULL CHECK(sample_count > 0),
    geography TEXT NOT NULL,
    data_origin TEXT NOT NULL,
    CHECK(abs(positive_share + neutral_share + negative_share - 1.0) < 0.00001),
    UNIQUE(technology_id, month)
);

CREATE TABLE IF NOT EXISTS company_profiles (
    company_id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE,
    sector TEXT NOT NULL,
    headquarters_label TEXT NOT NULL,
    founded_year INTEGER NOT NULL CHECK(founded_year BETWEEN 1850 AND 2026),
    employee_band TEXT NOT NULL,
    data_origin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS company_technology_relationships (
    relationship_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES company_profiles(company_id),
    technology_id INTEGER NOT NULL REFERENCES technologies(technology_id),
    relationship_type TEXT NOT NULL,
    first_observed TEXT NOT NULL,
    data_origin TEXT NOT NULL,
    UNIQUE(company_id, technology_id)
);

CREATE TABLE IF NOT EXISTS enterprise_adoption_observations (
    adoption_observation_id INTEGER PRIMARY KEY,
    relationship_id INTEGER NOT NULL REFERENCES company_technology_relationships(relationship_id),
    observed_at TEXT NOT NULL,
    adoption_state TEXT NOT NULL CHECK(adoption_state IN ('exploring','piloting','deployed','maintained','retired')),
    source_description TEXT NOT NULL,
    data_origin TEXT NOT NULL,
    UNIQUE(relationship_id, observed_at)
);

CREATE TABLE IF NOT EXISTS geographic_observations (
    geographic_observation_id INTEGER PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(technology_id),
    geography_code TEXT NOT NULL,
    geography_name TEXT NOT NULL,
    month TEXT NOT NULL,
    synthetic_interest_index REAL NOT NULL CHECK(synthetic_interest_index BETWEEN 0 AND 100),
    sample_count INTEGER NOT NULL CHECK(sample_count > 0),
    data_origin TEXT NOT NULL,
    UNIQUE(technology_id, geography_code, month)
);

CREATE TABLE IF NOT EXISTS lifecycle_assessments (
    assessment_id INTEGER PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(technology_id),
    feature_snapshot_id INTEGER NOT NULL REFERENCES feature_snapshots(feature_snapshot_id),
    lifecycle_label TEXT NOT NULL CHECK(lifecycle_label IN ('Growing','Stable','Declining')),
    target_end TEXT NOT NULL,
    label_definition TEXT NOT NULL,
    data_origin TEXT NOT NULL,
    UNIQUE(technology_id, feature_snapshot_id)
);

CREATE TABLE IF NOT EXISTS prediction_probabilities (
    prediction_id INTEGER NOT NULL REFERENCES predictions(prediction_id),
    class_name TEXT NOT NULL CHECK(class_name IN ('Growing','Stable','Declining')),
    probability REAL NOT NULL CHECK(probability BETWEEN 0 AND 1),
    data_origin TEXT NOT NULL,
    PRIMARY KEY(prediction_id, class_name)
);

CREATE TABLE IF NOT EXISTS model_configurations (
    model_name TEXT PRIMARY KEY,
    algorithm TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    seed INTEGER NOT NULL,
    feature_version TEXT NOT NULL,
    label_version TEXT NOT NULL,
    data_origin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_cv_results (
    model_name TEXT NOT NULL,
    fold_number INTEGER NOT NULL,
    train_start TEXT NOT NULL,
    train_end TEXT NOT NULL,
    validation_start TEXT NOT NULL,
    validation_end TEXT NOT NULL,
    accuracy REAL NOT NULL,
    weighted_f1 REAL NOT NULL,
    data_origin TEXT NOT NULL,
    PRIMARY KEY(model_name, fold_number)
);

CREATE TABLE IF NOT EXISTS demo_seed_runs (
    seed_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_version TEXT NOT NULL,
    seed INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status TEXT NOT NULL,
    generated_counts_json TEXT NOT NULL,
    inserted_counts_json TEXT NOT NULL,
    skipped_counts_json TEXT NOT NULL,
    rejected_counts_json TEXT NOT NULL,
    data_origin TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_demo_history_technology_month
    ON historical_technology_observations(technology_id, month);
CREATE INDEX IF NOT EXISTS ix_demo_questions_technology_created
    ON developer_questions(technology_id, created_at);
CREATE INDEX IF NOT EXISTS ix_demo_sentiment_technology_month
    ON sentiment_observations(technology_id, month);
CREATE INDEX IF NOT EXISTS ix_demo_relationship_technology_company
    ON company_technology_relationships(technology_id, company_id);
CREATE INDEX IF NOT EXISTS ix_demo_geo_technology_month
    ON geographic_observations(technology_id, geography_code, month);
CREATE INDEX IF NOT EXISTS ix_demo_predictions_probabilities
    ON prediction_probabilities(prediction_id, class_name);
