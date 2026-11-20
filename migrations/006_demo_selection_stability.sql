-- Record the comparable expanding-window stability statistic for the persisted
-- synthetic winner; selection UI also recomputes candidates from source metrics.
UPDATE demo.model_selection_records AS selection
SET criteria = selection.criteria || jsonb_build_object(
      'validation_stability_metric', 'population SD of four-fold weighted F1',
      'validation_weighted_f1_std', (
        SELECT stddev_pop(cv.weighted_f1)
        FROM demo.model_runs AS run
        JOIN demo.model_cv_results AS cv USING (model_name)
        WHERE run.model_run_id=selection.model_run_id
          AND run.status='succeeded_synthetic_demo'
      ),
      'tie_breakers', jsonb_build_array(
        'worst_class_recall','worst_class_f1',
        'lower_validation_weighted_f1_standard_deviation',
        'weighted_f1','accuracy'
      )
    ),
    evaluated_at=now()
WHERE selection.selection_key='synthetic_demo';
