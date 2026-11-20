-- Persist the selected synthetic demonstration model from comparable stored runs.
CREATE TABLE IF NOT EXISTS demo.model_selection_records (
  selection_key text PRIMARY KEY,
  model_run_id text REFERENCES demo.model_runs(model_run_id),
  primary_metric text NOT NULL CHECK (primary_metric = 'macro_f1'),
  primary_score numeric,
  selection_status text NOT NULL CHECK (selection_status IN ('selected','inconclusive')),
  criteria jsonb NOT NULL,
  evaluated_at timestamptz NOT NULL DEFAULT now(),
  data_origin text NOT NULL CHECK (data_origin = 'SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE')
);

WITH scored AS (
  SELECT mm.model_run_id, mm.macro_f1, mm.weighted_f1, mm.accuracy,
         LEAST(
           (mm.class_metrics_json::jsonb #>> '{Growing,recall}')::numeric,
           (mm.class_metrics_json::jsonb #>> '{Stable,recall}')::numeric,
           (mm.class_metrics_json::jsonb #>> '{Declining,recall}')::numeric
         ) AS worst_class_recall,
         LEAST(
           (mm.class_metrics_json::jsonb #>> '{Growing,f1}')::numeric,
           (mm.class_metrics_json::jsonb #>> '{Stable,f1}')::numeric,
           (mm.class_metrics_json::jsonb #>> '{Declining,f1}')::numeric
         ) AS worst_class_f1
  FROM demo.model_metrics mm
  JOIN demo.model_runs mr USING (model_run_id)
  WHERE mr.status = 'succeeded_synthetic_demo'
    AND mm.data_mode = 'SYNTHETIC DEMONSTRATION DATA'
    AND (mm.class_metrics_json::jsonb #>> '{Growing,support}')::integer >= 10
    AND (mm.class_metrics_json::jsonb #>> '{Stable,support}')::integer >= 10
    AND (mm.class_metrics_json::jsonb #>> '{Declining,support}')::integer >= 10
)
INSERT INTO demo.model_selection_records
  (selection_key, model_run_id, primary_metric, primary_score,
   selection_status, criteria, data_origin)
SELECT 'synthetic_demo', model_run_id, 'macro_f1', macro_f1, 'selected',
       jsonb_build_object(
         'scope', 'synthetic demonstration only',
         'tie_breakers', jsonb_build_array('worst_class_recall','worst_class_f1','weighted_f1','accuracy'),
         'weighted_f1', weighted_f1, 'accuracy', accuracy,
         'worst_class_recall', worst_class_recall, 'worst_class_f1', worst_class_f1
       ),
       'SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE'
FROM scored
ORDER BY macro_f1 DESC, worst_class_recall DESC, worst_class_f1 DESC,
         weighted_f1 DESC, accuracy DESC, model_run_id
LIMIT 1
ON CONFLICT (selection_key) DO UPDATE SET
  model_run_id=EXCLUDED.model_run_id,
  primary_metric=EXCLUDED.primary_metric,
  primary_score=EXCLUDED.primary_score,
  selection_status=EXCLUDED.selection_status,
  criteria=EXCLUDED.criteria,
  evaluated_at=now(),
  data_origin=EXCLUDED.data_origin;

INSERT INTO demo.model_selection_records
  (selection_key, model_run_id, primary_metric, primary_score,
   selection_status, criteria, data_origin)
SELECT 'synthetic_demo', NULL, 'macro_f1', NULL, 'inconclusive',
       '{"reason":"No eligible synthetic evaluation with minimum class support"}'::jsonb,
       'SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE'
WHERE NOT EXISTS (
  SELECT 1 FROM demo.model_selection_records WHERE selection_key='synthetic_demo'
)
ON CONFLICT (selection_key) DO NOTHING;
