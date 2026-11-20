"""Central catalog of parameterized queries against canonical schemas."""

HEALTH = """
SELECT current_database() AS database_name, version() AS postgres_version,
       now() AS checked_at,
       (SELECT count(*) FROM audit.schema_migrations) AS migration_count,
       (SELECT max(finished_at) FROM audit.ingestion_runs WHERE status='succeeded') AS last_ingestion,
       (SELECT max(finished_at) FROM ml.model_runs WHERE status='succeeded') AS last_model_run,
       (SELECT max(survey_year) FROM analytics.developer_survey_observations) AS latest_survey_year,
       (SELECT max(ts) FROM (VALUES
         ((SELECT max(collected_at) FROM analytics.developer_survey_observations)),
         ((SELECT max(collected_at) FROM analytics.community_monthly_metrics)),
         ((SELECT max(collected_at) FROM analytics.live_technology_observations))
       ) AS collections(ts)) AS last_collected_at
"""

SCHEMA_TABLES = """
SELECT table_schema, table_name FROM information_schema.tables
WHERE table_schema = ANY(:schemas) AND table_type IN ('BASE TABLE','VIEW')
ORDER BY table_schema, table_name
"""

OVERVIEW = """
SELECT
 (SELECT count(*) FROM core.technologies) AS technology_count,
 ((SELECT count(*) FROM core.community_questions) +
  (SELECT count(*) FROM analytics.community_monthly_metrics) +
  (SELECT count(*) FROM analytics.developer_survey_observations) +
  (SELECT count(*) FROM analytics.developer_skill_observations) +
  (SELECT count(*) FROM analytics.job_market_observations) +
  (SELECT count(*) FROM analytics.kenya_ict_indicators) +
  (SELECT count(*) FROM analytics.training_programme_observations) +
  (SELECT count(*) FROM analytics.company_technology_evidence) +
  (SELECT count(*) FROM analytics.github_repository_observations) +
  (SELECT count(*) FROM analytics.package_registry_observations) +
  (SELECT count(*) FROM analytics.technology_release_events) +
  (SELECT count(*) FROM analytics.live_technology_observations)) AS total_observations,
 (SELECT count(*) FROM analytics.developer_survey_observations) AS survey_observations,
 (SELECT count(*) FROM analytics.developer_survey_observations s
   JOIN core.geographies g USING(geography_id) WHERE g.code='GLOBAL') AS global_survey_observations,
 (SELECT count(*) FROM core.company_profiles) AS company_profiles,
 (SELECT count(*) FROM analytics.community_monthly_metrics) AS community_observations,
 (SELECT count(*) FROM audit.source_documents) AS source_documents,
 (SELECT count(*) FROM audit.data_sources WHERE active) AS active_sources,
 (SELECT count(*) FROM audit.data_quality_checks WHERE NOT passed AND severity='critical') AS failed_critical_checks,
 (SELECT count(*) FROM analytics.developer_survey_observations s JOIN core.geographies g USING(geography_id) WHERE g.code='KE') AS kenya_survey_rows,
 (SELECT count(*) FROM analytics.kenya_ict_indicators i JOIN core.geographies g USING(geography_id) WHERE g.code='KE') AS kenya_ict_rows,
 (SELECT max(survey_year) FROM analytics.developer_survey_observations) AS latest_survey_year,
 (SELECT max(period_start) FROM analytics.community_monthly_metrics) AS latest_community_period,
 (SELECT max(finished_at) FROM audit.ingestion_runs WHERE status='succeeded') AS latest_successful_ingestion,
 (SELECT max(finished_at) FROM ml.model_runs WHERE status='succeeded') AS latest_model_run
"""

# One uncached snapshot of the evidence needed to judge whether each named
# research indicator can be calculated. Counts alone never turn missing data
# into a measured zero; validity and observation periods are included.
INDICATOR_EVIDENCE = """
SELECT
 (SELECT count(*) FROM analytics.community_monthly_metrics) AS community_rows,
 (SELECT count(*) FROM analytics.community_monthly_metrics m
   WHERE m.period_start IS NOT NULL AND m.observed_at IS NOT NULL
     AND m.question_count > 0 AND m.unanswered_count BETWEEN 0 AND m.question_count
     AND m.answer_rate BETWEEN 0 AND 1) AS valid_community_rows,
 (SELECT count(*) FROM core.community_questions q
   WHERE q.observed_at IS NOT NULL AND q.source_question_id IS NOT NULL
     AND q.technology_id IS NOT NULL AND q.answer_count IS NOT NULL
     AND q.answer_count >= 0) AS valid_question_rows,
 (SELECT count(DISTINCT date_trunc('month',m.period_start))
   FROM analytics.community_monthly_metrics m
   WHERE m.period_start IS NOT NULL AND m.observed_at IS NOT NULL
     AND m.question_count > 0 AND m.unanswered_count BETWEEN 0 AND m.question_count
     AND m.answer_rate BETWEEN 0 AND 1) AS valid_community_months,
 (SELECT min(period_start) FROM analytics.community_monthly_metrics) AS community_start,
 (SELECT max(period_start) FROM analytics.community_monthly_metrics) AS community_end,
 (SELECT count(*) FROM audit.data_sources s
   JOIN audit.ingestion_runs r USING(source_id)
   WHERE s.source_key='local_stackexchange' AND r.status='failed') AS stackexchange_failed_runs,
 (SELECT count(*) FROM audit.data_quality_checks q
   JOIN audit.ingestion_runs r USING(run_id)
   JOIN audit.data_sources s USING(source_id)
   WHERE s.source_key='local_stackexchange' AND q.severity='critical' AND NOT q.passed) AS stackexchange_critical_failures,
 (SELECT count(*) FROM analytics.developer_survey_observations s
   WHERE s.survey_year IS NOT NULL AND s.respondent_count > 0
     AND s.usage_share IS NOT NULL AND s.interest_share IS NOT NULL
     AND s.admiration_share IS NOT NULL) AS valid_survey_rows,
 (SELECT min(survey_year) FROM analytics.developer_survey_observations) AS survey_start_year,
 (SELECT max(survey_year) FROM analytics.developer_survey_observations) AS survey_end_year,
 (SELECT count(*) FROM analytics.company_technology_evidence e
   JOIN analytics.company_technology_evidence_sources es USING(evidence_id)
   LEFT JOIN audit.source_documents d USING(document_id)
   LEFT JOIN audit.data_sources s ON s.source_id=es.source_id
   WHERE e.source_class IN ('observed','reported') AND e.observed_at IS NOT NULL
     AND e.technology_id IS NOT NULL AND e.company_id IS NOT NULL
     AND (s.source_id IS NOT NULL OR d.document_id IS NOT NULL)) AS sourced_adoption_rows,
 (SELECT count(DISTINCT e.company_id) FROM analytics.company_technology_evidence e
   JOIN analytics.company_technology_evidence_sources es USING(evidence_id)
   LEFT JOIN audit.source_documents d USING(document_id)
   LEFT JOIN audit.data_sources s ON s.source_id=es.source_id
   WHERE e.source_class IN ('observed','reported') AND e.observed_at IS NOT NULL
     AND e.technology_id IS NOT NULL AND e.company_id IS NOT NULL
     AND (s.source_id IS NOT NULL OR d.document_id IS NOT NULL)) AS sourced_adoption_companies,
 (SELECT min(e.observed_at)::date FROM analytics.company_technology_evidence e
   JOIN analytics.company_technology_evidence_sources es USING(evidence_id)
   LEFT JOIN audit.source_documents d USING(document_id)
   LEFT JOIN audit.data_sources s ON s.source_id=es.source_id
   WHERE e.source_class IN ('observed','reported') AND e.observed_at IS NOT NULL
     AND e.technology_id IS NOT NULL AND e.company_id IS NOT NULL
     AND (s.source_id IS NOT NULL OR d.document_id IS NOT NULL)) AS adoption_start,
 (SELECT max(e.observed_at)::date FROM analytics.company_technology_evidence e
   JOIN analytics.company_technology_evidence_sources es USING(evidence_id)
   LEFT JOIN audit.source_documents d USING(document_id)
   LEFT JOIN audit.data_sources s ON s.source_id=es.source_id
   WHERE e.source_class IN ('observed','reported') AND e.observed_at IS NOT NULL
     AND e.technology_id IS NOT NULL AND e.company_id IS NOT NULL
     AND (s.source_id IS NOT NULL OR d.document_id IS NOT NULL)) AS adoption_end,
 (SELECT count(*) FROM ml.feature_values v JOIN ml.feature_snapshots fs USING(snapshot_id)
   WHERE NOT v.is_missing AND v.feature_value IS NOT NULL) AS persisted_feature_values,
 (SELECT count(DISTINCT v.feature_name) FROM ml.feature_values v JOIN ml.feature_snapshots fs USING(snapshot_id)
   WHERE NOT v.is_missing AND v.feature_value IS NOT NULL) AS persisted_feature_names,
 (SELECT COALESCE(array_agg(DISTINCT v.feature_name), ARRAY[]::text[])
   FROM ml.feature_values v JOIN ml.feature_snapshots fs USING(snapshot_id)
   WHERE NOT v.is_missing AND v.feature_value IS NOT NULL) AS persisted_feature_name_list,
 (SELECT min(fs.as_of_date) FROM ml.feature_values v JOIN ml.feature_snapshots fs USING(snapshot_id)
   WHERE NOT v.is_missing AND v.feature_value IS NOT NULL) AS feature_start,
 (SELECT max(fs.as_of_date) FROM ml.feature_values v JOIN ml.feature_snapshots fs USING(snapshot_id)
   WHERE NOT v.is_missing AND v.feature_value IS NOT NULL) AS feature_end,
 (SELECT count(*) FROM ml.technology_labels) AS lifecycle_labels,
 (SELECT count(*) FROM ml.model_runs WHERE status='succeeded' AND finished_at IS NOT NULL) AS successful_model_runs,
 (SELECT count(*) FROM ml.model_predictions p JOIN ml.model_runs r USING(model_run_id)
   WHERE r.status='succeeded' AND r.finished_at IS NOT NULL) AS persisted_predictions,
 (SELECT count(*) FROM ml.prediction_explanations) AS explanation_rows
"""

TECHNOLOGY_ASSESSMENTS = """
SELECT l.label, l.as_of_date, l.target_end_date, ld.name AS label_definition,
       ld.version AS label_version, fs.source_snapshot
FROM ml.technology_labels l
JOIN ml.feature_snapshots fs USING(snapshot_id)
LEFT JOIN ml.label_definitions ld USING(label_definition_id)
WHERE l.technology_id=:technology_id
ORDER BY l.as_of_date DESC
"""

SOURCES = """
SELECT s.source_id, s.source_key, s.publisher, s.title, s.url, s.licence_terms,
       s.methodology, s.geographic_scope, s.source_class, s.metadata,
       r.run_id, r.status AS run_status, r.started_at, r.finished_at,
       r.rows_read, r.rows_written, r.report, r.error_summary,
       q.check_name, q.severity, q.passed, q.details, q.observed_value, q.checked_at
FROM audit.data_sources s
LEFT JOIN LATERAL (SELECT * FROM audit.ingestion_runs ir WHERE ir.source_id=s.source_id ORDER BY started_at DESC LIMIT 1) r ON true
LEFT JOIN LATERAL (SELECT * FROM audit.data_quality_checks dc WHERE dc.run_id=r.run_id ORDER BY checked_at DESC LIMIT 1) q ON true
ORDER BY s.source_key
"""

TECHNOLOGIES = """
SELECT t.technology_id, t.canonical_name, t.description,
       COALESCE(array_agg(DISTINCT a.alias) FILTER (WHERE a.alias IS NOT NULL), '{}') AS aliases,
       COALESCE(array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL), '{}') AS categories,
       count(DISTINCT s.observation_id) AS survey_records,
       count(DISTINCT cm.period_start) AS community_records,
       max(s.survey_year) AS latest_survey_year,
       max(cm.period_start) AS latest_community_period
FROM core.technologies t
LEFT JOIN core.technology_aliases a USING(technology_id)
LEFT JOIN core.technology_category_memberships m USING(technology_id)
LEFT JOIN core.technology_categories c USING(category_id)
LEFT JOIN analytics.developer_survey_observations s USING(technology_id)
LEFT JOIN analytics.community_monthly_metrics cm USING(technology_id)
GROUP BY t.technology_id
ORDER BY t.canonical_name
"""

SURVEY = """
SELECT t.canonical_name AS technology, s.survey_year, g.code AS geography_code,
       g.name AS geography, s.respondent_count, s.worked_with_count,
       s.want_to_work_with_count, s.admired_count, s.usage_share,
       s.interest_share, s.admiration_share, s.observed_at, s.collected_at,
       src.source_key, src.publisher, src.url, src.licence_terms, s.metadata
FROM analytics.developer_survey_observations s
LEFT JOIN core.technologies t USING(technology_id)
LEFT JOIN core.geographies g USING(geography_id)
LEFT JOIN audit.data_sources src ON src.source_id=s.source_id
WHERE (CAST(:year AS integer) IS NULL OR s.survey_year=CAST(:year AS integer))
  AND (CAST(:geography AS text) IS NULL OR g.code=CAST(:geography AS text))
ORDER BY s.survey_year DESC, t.canonical_name
"""

COMMUNITY = """
SELECT t.canonical_name AS technology, g.code AS geography_code, g.name AS geography,
       m.period_start, m.question_count, m.unanswered_count, m.answer_rate,
       m.median_score, m.observed_at, m.collected_at, s.source_key,
       s.metadata AS source_metadata, m.source_metadata AS observation_metadata
FROM analytics.community_monthly_metrics m
JOIN core.technologies t USING(technology_id)
JOIN core.geographies g USING(geography_id)
JOIN audit.data_sources s ON s.source_id=m.source_id
ORDER BY m.period_start, t.canonical_name
"""

KENYA = """
SELECT 'ICT indicator' AS record_type, i.indicator_code AS metric,
       NULL::text AS technology, i.value AS metric_value, i.unit,
       i.period_start, i.period_end, i.observed_at, i.collected_at,
       g.code AS geography_code, g.name AS geography, s.source_key,
       s.publisher, s.url, i.metadata
FROM analytics.kenya_ict_indicators i JOIN core.geographies g USING(geography_id)
LEFT JOIN audit.data_sources s ON s.source_id=i.source_id WHERE g.code='KE'
UNION ALL
SELECT 'training programme', 'participant_count', t.canonical_name,
       p.participant_count::numeric, NULL::text, p.period_start, NULL::date,
       p.observed_at, p.collected_at, g.code, g.name, s.source_key,
       s.publisher, s.url, p.metadata
FROM analytics.training_programme_observations p JOIN core.geographies g USING(geography_id)
LEFT JOIN core.technologies t ON t.technology_id=p.technology_id LEFT JOIN audit.data_sources s ON s.source_id=p.source_id
WHERE g.code='KE'
UNION ALL
SELECT 'job market', j.metric_name, t.canonical_name, j.metric_value, NULL::text,
       j.period_start, NULL::date, j.observed_at, j.collected_at, g.code, g.name,
       s.source_key, s.publisher, s.url, j.metadata
FROM analytics.job_market_observations j JOIN core.geographies g USING(geography_id)
LEFT JOIN core.technologies t ON t.technology_id=j.technology_id LEFT JOIN audit.data_sources s ON s.source_id=j.source_id
WHERE g.code='KE' AND j.terms_reviewed
UNION ALL
SELECT 'verified technology evidence', e.evidence_type, t.canonical_name,
       e.confidence, NULL::text, e.observed_at::date, NULL::date, e.observed_at,
       e.collected_at, g.code, g.name, s.source_key, s.publisher, s.url,
       jsonb_build_object('claim',e.claim,'source_class',e.source_class,'confidence',e.confidence)
FROM analytics.company_technology_evidence e JOIN core.geographies g USING(geography_id)
LEFT JOIN core.technologies t USING(technology_id)
LEFT JOIN analytics.company_technology_evidence_sources es USING(evidence_id)
LEFT JOIN audit.data_sources s ON s.source_id=es.source_id
WHERE g.code='KE' AND e.source_class IN ('observed','reported')
"""

LIVE = """
SELECT l.observation_id, s.source_key AS source, l.metric_name AS metric,
       t.canonical_name AS technology, g.code AS geography_code,
       l.metric_value, l.unit, l.observed_at, l.collected_at,
       l.coverage, l.metadata, l.source_id
FROM analytics.live_technology_observations l
LEFT JOIN audit.data_sources s USING(source_id)
LEFT JOIN core.technologies t USING(technology_id)
LEFT JOIN core.geographies g USING(geography_id)
ORDER BY l.collected_at DESC
"""

PREDICTIONS = """
SELECT p.prediction_id, t.canonical_name AS technology, g.code AS geography_code,
       p.as_of_date AS feature_snapshot_date, p.predicted_at, p.predicted_label,
       p.probability_growing, p.probability_stable, p.probability_declining,
       p.evidence_coverage, p.uncertainty, r.model_run_id, r.code_version,
       r.dataset_snapshot, r.artifact_checksum, r.finished_at,
       fs.source_snapshot, fs.config_hash AS feature_config_hash,
       ld.name AS label_name, ld.version AS label_version, p.metadata
FROM ml.model_predictions p
JOIN ml.model_runs r ON r.model_run_id=p.model_run_id
JOIN ml.feature_snapshots fs ON fs.snapshot_id=r.feature_snapshot_id
JOIN ml.technology_labels l ON l.snapshot_id=fs.snapshot_id AND l.technology_id=p.technology_id AND l.geography_id=p.geography_id
JOIN ml.label_definitions ld ON ld.label_definition_id=l.label_definition_id
JOIN core.technologies t ON t.technology_id=p.technology_id
JOIN core.geographies g ON g.geography_id=p.geography_id
WHERE r.status='succeeded' AND r.finished_at IS NOT NULL
  AND r.feature_snapshot_id IS NOT NULL
  AND p.as_of_date=fs.as_of_date
  AND r.finished_at >= now() - interval '365 days'
  AND p.predicted_at <= now()
ORDER BY p.predicted_at DESC
"""

MODEL_RUNS = """
SELECT r.model_run_id, r.started_at, r.finished_at, r.status, r.code_version,
       r.config_hash, r.dataset_snapshot, r.feature_snapshot_id,
       r.label_definition_id,
       fs.as_of_date AS feature_snapshot_date, fs.source_snapshot,
       ld.name AS label_name, ld.version AS label_version, r.seed,
       r.split_metadata, r.feature_definitions, r.hyperparameters,
       CASE WHEN r.status <> 'succeeded' THEN 'not successful'
            WHEN r.finished_at < now() - interval '365 days' THEN 'stale'
            WHEN r.feature_snapshot_id IS NULL THEN 'missing feature snapshot'
            WHEN r.finished_at > now() THEN 'future run timestamp'
            ELSE 'valid' END AS run_freshness,
       r.artifact_path, r.artifact_checksum, r.metadata,
       c.candidate_id, c.model_name, c.status AS candidate_status,
       mm.split_name, mm.metric_name, mm.metric_value, mm.support, mm.auditable,
       mm.metadata AS metric_metadata
FROM ml.model_runs r LEFT JOIN ml.feature_snapshots fs ON fs.snapshot_id=r.feature_snapshot_id
LEFT JOIN ml.label_definitions ld USING(label_definition_id)
LEFT JOIN ml.model_candidates c USING(model_run_id)
LEFT JOIN ml.model_metrics mm USING(model_run_id)
ORDER BY r.started_at DESC
"""

MODEL_CLASS_METRICS = """
SELECT c.model_run_id, c.model_name, m.class_name, m.precision, m.recall, m.f1, m.support
FROM ml.model_class_metrics m JOIN ml.model_candidates c USING(candidate_id)
ORDER BY c.model_run_id, c.model_name, m.class_name
"""

BASELINES = """
SELECT model_run_id, baseline_name, split_name, metrics, class_support, metadata
FROM ml.baseline_results ORDER BY model_run_id, baseline_name, split_name
"""

PREDICTION_EXPLANATIONS = """
SELECT e.prediction_id, e.feature_name, e.attribution, e.method, e.interpretation
FROM ml.prediction_explanations e WHERE e.prediction_id=:prediction_id
ORDER BY abs(e.attribution) DESC
"""

COMMUNITY_BLOCK = """
SELECT s.source_key, s.metadata, r.run_id, r.status, r.error_summary, r.report,
       q.severity, q.passed, q.details, q.observed_value, q.checked_at
FROM audit.data_sources s
LEFT JOIN LATERAL (SELECT * FROM audit.ingestion_runs ir WHERE ir.source_id=s.source_id ORDER BY started_at DESC LIMIT 1) r ON true
LEFT JOIN LATERAL (SELECT * FROM audit.data_quality_checks dc WHERE dc.run_id=r.run_id ORDER BY checked_at DESC LIMIT 1) q ON true
WHERE s.source_key='local_stackexchange'
"""

PROVENANCE = """
SELECT s.source_key, s.publisher, s.title, s.url, s.licence_terms,
       s.methodology, s.geographic_scope, s.source_class, s.metadata,
       d.publication_period, d.retrieved_at, d.checksum, d.geography AS document_geography,
       r.run_id, r.started_at, r.finished_at, r.status, r.rows_read, r.rows_written,
       r.report, r.error_summary,
       q.check_name, q.severity, q.passed, q.observed_value, q.details, q.checked_at
FROM audit.data_sources s LEFT JOIN audit.source_documents d USING(source_id)
LEFT JOIN audit.ingestion_runs r USING(source_id)
LEFT JOIN audit.data_quality_checks q USING(run_id)
ORDER BY s.source_key, r.started_at DESC
"""

TABLE_COUNTS = """
SELECT schemaname AS table_schema, relname AS table_name, n_live_tup AS estimated_rows
FROM pg_stat_user_tables WHERE schemaname=ANY(:schemas)
ORDER BY schemaname, relname
"""
