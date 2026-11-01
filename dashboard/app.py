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
    st.Page("views/0_Start_Here.py", title="Start Here", icon=":material/home:"),
    st.Page("views/1_Home.py", title="Technology Explorer", icon=":material/search:"),
    st.Page("views/2_Rankings.py", title="Technology Rankings", icon=":material/leaderboard:"),
    st.Page("views/5_Community_Health.py", title="Community Health", icon=":material/groups:"),
    st.Page("views/6_Prediction_Explorer.py", title="Prediction Explorer", icon=":material/psychology:"),
    st.Page("views/3_Model_Performance.py", title="Model Performance & Validation", icon=":material/analytics:"),
    st.Page("views/7_Methodology_Data.py", title="Methodology & Data", icon=":material/schema:"),
    st.Page("views/8_Live_Technology_Intelligence.py", title="Live Technology Intelligence", icon=":material/public:"),
    st.Page("views/4_About.py", title="About & User Guide", icon=":material/help:"),
]
navigation = st.navigation(pages)
navigation.run()
