#!/usr/bin/env bash
set -euo pipefail
cd /workspaces/TechPulse

if curl --silent --fail http://127.0.0.1:8501/_stcore/health >/dev/null; then
  exit 0
fi

nohup .venv/bin/python -m streamlit run dashboard/app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  >/tmp/techpulse-streamlit.log 2>&1 </dev/null &

for _ in $(seq 1 30); do
  if curl --silent --fail http://127.0.0.1:8501/_stcore/health >/dev/null; then
    echo "TechPulse is running on port 8501. Open the forwarded Codespaces port."
    exit 0
  fi
  sleep 1
done
cat /tmp/techpulse-streamlit.log
exit 1
