ALTER TABLE ml.data_versions
  ADD COLUMN IF NOT EXISTS git_dirty boolean NOT NULL DEFAULT false;

ALTER TABLE ml.model_runs
  ADD COLUMN IF NOT EXISTS git_commit text;
ALTER TABLE ml.model_runs
  ADD COLUMN IF NOT EXISTS git_dirty boolean NOT NULL DEFAULT false;
