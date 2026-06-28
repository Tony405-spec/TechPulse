"""Home and technology search page."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.tech_detail_panel import render_detail_panel, trajectory_badge  # noqa: E402
from src.common import CATEGORY_COLUMN, DATA_DIR, DISCLAIMER, FEATURE_COLUMNS, LABEL_COLUMN, TECH_COLUMN  # noqa: E402


@st.cache_data
def load_features() -> pd.DataFrame:
    """Load the dashboard feature matrix.

    Returns:
        Feature matrix DataFrame.
    """
    path = DATA_DIR / "feature_matrix.csv"
    if not path.exists():
        return pd.DataFrame(columns=[TECH_COLUMN, CATEGORY_COLUMN, LABEL_COLUMN] + FEATURE_COLUMNS)
    return pd.read_csv(path)


def _risk(row: pd.Series) -> int:
    """Compute display risk score from feature proxies.

    Args:
        row: Feature row.

    Returns:
        Risk score.
    """
    return int((1 - float(row.get("growth_momentum_index", 0.5))) * 100)


st.title("TechPulse")
st.info(DISCLAIMER)
data = load_features()
search = st.text_input("Search technology", max_chars=100, placeholder="Python, #c, c++, .net")
category = st.selectbox("Category", ["All", "Languages", "Frameworks", "Databases", "Tools", "Other"])
filtered = data.copy()
if search:
    filtered = filtered[filtered[TECH_COLUMN].astype(str).str.contains(search, case=False, regex=False, na=False)]
if category != "All" and CATEGORY_COLUMN in filtered:
    filtered = filtered[filtered[CATEGORY_COLUMN].astype(str).str.casefold() == category.casefold()]

if filtered.empty:
    st.warning("No technologies found")
else:
    display = filtered[[TECH_COLUMN, CATEGORY_COLUMN, LABEL_COLUMN]].copy()
    display["Risk Score"] = filtered.apply(_risk, axis=1)
    display.columns = ["Technology Name", "Category", "Trajectory Label", "Risk Score"]
    st.dataframe(display, use_container_width=True, hide_index=True)
    choices = filtered[TECH_COLUMN].astype(str).tolist()
    selected = st.selectbox("Technology detail", choices)
    if selected:
        st.session_state["selected_technology"] = selected
        row = filtered.loc[filtered[TECH_COLUMN].astype(str) == selected].iloc[0]
        st.markdown(trajectory_badge(str(row.get(LABEL_COLUMN, "Stable"))), unsafe_allow_html=True)
        render_detail_panel(row)
