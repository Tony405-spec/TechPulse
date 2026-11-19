SELECT ds.source_key, ds.source_class, ds.geographic_scope, count(sr.source_record_id) AS retained_raw_records,
       min(sr.observed_at) AS earliest_observed_at, max(sr.observed_at) AS latest_observed_at,
       max(sr.collected_at) AS last_collected_at
FROM audit.data_sources ds LEFT JOIN raw.source_records sr USING(source_id)
GROUP BY ds.source_key, ds.source_class, ds.geographic_scope ORDER BY ds.source_key;

SELECT g.code AS geography, count(*) AS observation_rows
FROM analytics.community_monthly_metrics m JOIN core.geographies g USING(geography_id)
GROUP BY g.code ORDER BY g.code;
