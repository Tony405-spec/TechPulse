"""TechPulse Streamlit dashboard entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.ui import apply_theme  # noqa: E402

st.set_page_config(page_title="TechPulse", page_icon="TP", layout="wide")
apply_theme()

pages = [
    st.Page("views/1_Home.py", title="Command Center", icon=":material/search:"),
    st.Page("views/2_Rankings.py", title="Global Rankings", icon=":material/leaderboard:"),
    st.Page("views/3_Model_Performance.py", title="Model Laboratory", icon=":material/analytics:"),
    st.Page("views/4_About.py", title="About / Methodology", icon=":material/info:"),
]
navigation = st.navigation(pages)
navigation.run()
