#!/usr/bin/env bash
set -euo pipefail
cd /workspaces/TechPulse

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m src.db.migrate

# Reuse a complete seeded database after a Codespaces rebuild. If it is empty
# or incomplete, rerun the deterministic, upserting pipeline to finish setup.
python - <<'PY'
import subprocess
import sys
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg2://techpulse_sim_app@postgres:5432/techpulse_sim")
query = text("""
SELECT
  (SELECT count(*) FROM ml.data_versions WHERE status='verified') AS versions,
  (SELECT count(*) FROM sim.technology_metadata) AS technologies,
  (SELECT count(*) FROM ml.feature_snapshots) AS features,
  (SELECT count(*) FROM ml.model_runs WHERE status='succeeded' AND selected_by_cv) AS selected_runs,
  (SELECT count(*) FROM ml.predictions) AS predictions,
  (SELECT count(*) FROM ml.shap_global) AS global_explanations
""")
with engine.connect() as connection:
    counts = connection.execute(query).mappings().one()
if all(int(value) > 0 for value in counts.values()):
    print("TechPulse simulation database is already initialized; reusing it.")
else:
    print("Preparing the reproducible TechPulse simulation and model outputs. This first setup may take several minutes.")
    subprocess.run([sys.executable, "-m", "src.run_all"], check=True)
engine.dispose()
PY
