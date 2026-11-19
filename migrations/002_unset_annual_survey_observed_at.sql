-- Annual survey rows have a year, not a verified event date; do not invent Jan 1 timestamps.
UPDATE analytics.developer_survey_observations AS survey
SET observed_at = NULL
FROM audit.data_sources AS source
WHERE source.source_id = survey.source_id
  AND source.source_key = 'local_survey'
  AND survey.observed_at IS NOT NULL;
