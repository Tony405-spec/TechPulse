"""Global risk rankings page."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import CATEGORY_COLUMN, DATA_DIR, DISCLAIMER, LABEL_COLUMN, TECH_COLUMN  # noqa: E402


@st.cache_data
def load_rankings() -> pd.DataFrame:
    """Load and score ranked technologies.

    Returns:
        Rankings DataFrame.
    """
    path = DATA_DIR / "feature_matrix.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame["Risk Score"] = ((1 - frame["growth_momentum_index"].fillna(0.5)) * 100).astype(int)
    frame["Confidence Level"] = frame["Risk Score"].apply(
        lambda value: "High Confidence" if value >= 80 or value <= 20 else "Medium Confidence"
    )
    return frame.sort_values("Risk Score", ascending=False).reset_index(drop=True)


st.title("Global Risk Rankings")
st.info(DISCLAIMER)
data = load_rankings()
if data.empty:
    st.warning("No rankings available. Run the pipeline first.")
else:
    category_options = ["All Categories"] + sorted(data[CATEGORY_COLUMN].dropna().astype(str).unique().tolist())
    category = st.selectbox("Category", category_options)
    label = st.selectbox("Trajectory Label", ["All", "Growing", "Stable", "Declining"])
    filtered = data.copy()
    if category != "All Categories":
        filtered = filtered[filtered[CATEGORY_COLUMN].astype(str) == category]
    if label != "All":
        filtered = filtered[filtered[LABEL_COLUMN] == label]
    table = filtered[[TECH_COLUMN, CATEGORY_COLUMN, LABEL_COLUMN, "Risk Score", "Confidence Level"]].copy()
    table.insert(0, "Rank", range(1, len(table) + 1))
    table.columns = ["Rank", "Technology Name", "Category", "Trajectory Label", "Risk Score", "Confidence Level"]
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button("Download CSV", table.to_csv(index=False), "techpulse_rankings.csv", "text/csv")
