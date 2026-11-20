-- Demo-only latest snapshot view, copied from the reviewed synthetic source view.
CREATE OR REPLACE VIEW demo.latest_features AS
SELECT DISTINCT ON (technology_id) *
FROM demo.feature_snapshots
ORDER BY technology_id, as_of DESC;
