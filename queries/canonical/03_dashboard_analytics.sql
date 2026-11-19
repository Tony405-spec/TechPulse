-- Coverage first: rows are observations, not adoption counts.
SELECT ds.source_key, ds.geographic_scope, ds.source_class,
       count(m.period_start) AS monthly_rows,
       min(m.period_start) AS first_period, max(m.period_start) AS last_period,
       count(DISTINCT m.technology_id) AS technologies
FROM audit.data_sources ds
LEFT JOIN analytics.community_monthly_metrics m USING(source_id)
GROUP BY ds.source_key, ds.geographic_scope, ds.source_class
ORDER BY ds.source_key;

-- Community trend by source geography. A NULL month remains absent coverage.
SELECT t.canonical_name, g.code AS geography, m.period_start,
       m.question_count, m.unanswered_count, m.answer_rate, ds.source_key
FROM analytics.community_monthly_metrics m
JOIN core.technologies t USING(technology_id)
JOIN core.geographies g USING(geography_id)
JOIN audit.data_sources ds USING(source_id)
ORDER BY t.canonical_name, g.code, m.period_start;

-- Company technology evidence is empty unless a source-backed claim was loaded.
SELECT count(*) AS evidence_rows,
       count(*) FILTER (WHERE source_class='proxy') AS proxy_rows,
       count(*) FILTER (WHERE source_class IN ('observed','reported')) AS documented_rows
FROM analytics.company_technology_evidence;
