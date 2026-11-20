ALTER TABLE ml.shap_global DROP CONSTRAINT IF EXISTS shap_global_signal_family_check;
ALTER TABLE ml.shap_global ADD CONSTRAINT shap_global_signal_family_check
  CHECK (signal_family IN ('community','enterprise','sentiment','context'));
