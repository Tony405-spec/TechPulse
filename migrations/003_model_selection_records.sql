-- Persist a traceable model-selection decision without making a hardcoded winner.
CREATE TABLE IF NOT EXISTS ml.model_selection_records (
  selection_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  selected_candidate_id bigint REFERENCES ml.model_candidates(candidate_id),
  cohort_key text NOT NULL,
  primary_metric text NOT NULL CHECK (primary_metric IN ('macro_f1','weighted_f1')),
  selection_status text NOT NULL CHECK (selection_status IN ('selected','inconclusive')),
  criteria jsonb NOT NULL,
  evaluated_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_model_selection_latest
  ON ml.model_selection_records(evaluated_at DESC);
