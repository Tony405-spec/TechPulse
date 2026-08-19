"""Global risk rankings page."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import CATEGORY_COLUMN, DATA_DIR, DISCLAIMER, LABEL_COLUMN, OUTPUTS_DIR, TECH_COLUMN  # noqa: E402
from dashboard.components.ui import disclaimer_panel, render_shell  # noqa: E402


@st.cache_data
def load_rankings() -> pd.DataFrame:
    """Load and score ranked technologies.

    Returns:
        Rankings DataFrame.
    """
    prediction_path = OUTPUTS_DIR / "technology_predictions.csv"
    path = prediction_path if prediction_path.exists() else DATA_DIR / "feature_matrix.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if "risk_score" in frame:
        frame["Risk Score"] = frame["risk_score"].round().astype(int)
    else:
        frame["Risk Score"] = ((1 - frame["growth_momentum_index"].fillna(0.5)) * 100).astype(int)
    if "confidence_level" in frame:
        frame["Confidence Level"] = frame["confidence_level"]
    else:
        frame["Confidence Level"] = "Unavailable"
    if "predicted_label" in frame:
        frame[LABEL_COLUMN] = frame["predicted_label"]
    return frame.sort_values("Risk Score", ascending=False).reset_index(drop=True)


render_shell(
    "Global Technology Risk Index",
    "Technologies ranked by estimated decline risk.",
    "GLOBAL RANKINGS",
)
disclaimer_panel()
data = load_rankings()
if data.empty:
    st.warning("No rankings available. Run the pipeline first.")
else:
    if "risk_score" not in data.columns:
        st.warning("Probability-based risk scores are unavailable. Current ranking uses feature proxies.")
    filter_cols = st.columns([1.2, 1.2, 1.6, 1.6])
    category_options = ["All Categories"] + sorted(data[CATEGORY_COLUMN].dropna().astype(str).unique().tolist())
    with filter_cols[0]:
        category = st.selectbox("Category", category_options)
    with filter_cols[1]:
        label = st.selectbox("Trajectory Label", ["All", "Growing", "Stable", "Declining"])
    with filter_cols[2]:
        risk_range = st.slider("Risk Range", 0, 100, (0, 100))
    with filter_cols[3]:
        search = st.text_input("Search", placeholder="Filter technologies")
    filtered = data.copy()
    if category != "All Categories":
        filtered = filtered[filtered[CATEGORY_COLUMN].astype(str) == category]
    if label != "All":
        filtered = filtered[filtered[LABEL_COLUMN] == label]
    filtered = filtered[
        (filtered["Risk Score"] >= risk_range[0]) & (filtered["Risk Score"] <= risk_range[1])
    ]
    if search:
        filtered = filtered[
            filtered[TECH_COLUMN].astype(str).str.contains(search, case=False, regex=False, na=False)
        ]
    chart_data = filtered.nlargest(12, "Risk Score").sort_values("Risk Score")
    if not chart_data.empty:
        fig = px.bar(
            chart_data,
            x="Risk Score",
            y=TECH_COLUMN,
            orientation="h",
            color="Risk Score",
            color_continuous_scale=["#00ff66", "#ffc857", "#ff5c7a"],
            title="Highest Risk Technologies",
            hover_data=[CATEGORY_COLUMN, LABEL_COLUMN, "Confidence Level"],
            range_x=[0, 100],
        )
        fig.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
    table = filtered[[TECH_COLUMN, CATEGORY_COLUMN, LABEL_COLUMN, "Risk Score", "Confidence Level"]].copy()
    table.insert(0, "Rank", range(1, len(table) + 1))
    table.columns = ["Rank", "Technology Name", "Category", "Trajectory Label", "Risk Score", "Confidence Level"]
    st.subheader("Risk Index Table")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button("Download CSV", table.to_csv(index=False), "techpulse_rankings.csv", "text/csv")
