"""TechPulse Streamlit dashboard entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import DISCLAIMER  # noqa: E402

st.set_page_config(page_title="TechPulse", page_icon="⚡", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #F8FAFC; color: #111827; }
    div[data-testid="stDataFrame"] { border: 1px solid #D1D5DB; border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.info(DISCLAIMER)

pages = [
    st.Page("pages/1_Home.py", title="Home", icon=":material/search:"),
    st.Page("pages/2_Rankings.py", title="Rankings", icon=":material/leaderboard:"),
    st.Page("pages/3_Model_Performance.py", title="Model Performance", icon=":material/analytics:"),
    st.Page("pages/4_About.py", title="About", icon=":material/info:"),
]
navigation = st.navigation(pages)
navigation.run()
