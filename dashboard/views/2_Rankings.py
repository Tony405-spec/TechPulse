"""Transparent ranking and filters over saved technology records."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell
from dashboard.data import load_predictions, risk_from_probability

render_shell("Technology Rankings", "Filter saved technology records and compare the indicators available in this snapshot.", "COMPARE")
disclaimer_panel()
frame, probabilities = load_predictions()
if frame.empty:
    st.info("No saved technology rows are available yet. Run the pipeline to create them.")
    st.stop()
if probabilities:
    frame["Risk indicator"] = frame["prob_Growing"].map(risk_from_probability)
else:
    st.warning("Class probabilities are not present. A probability-based risk ranking cannot be calculated; showing saved rows without inventing a score.")
    frame["Risk indicator"] = pd.NA
frame["Trajectory"] = frame.get("predicted_label", frame.get("trajectory_label", "Unavailable")).astype(str)

controls = st.columns(4)
with controls[0]:
    cats = sorted(frame["category"].dropna().astype(str).unique()) if "category" in frame else []
    cat = st.selectbox("Technology category", ["All categories", *cats])
with controls[1]:
    label = st.selectbox("Saved trajectory", ["All classes", "Growing", "Stable", "Declining"])
with controls[2]:
    search = st.text_input("Search technologies", placeholder="Type part of a name")
with controls[3]:
    order = st.selectbox("Sort records by", ["Highest risk first", "Lowest risk first", "Name A to Z"])

view = frame.copy()
if cat != "All categories" and "category" in view:
    view = view[view["category"].astype(str) == cat]
if label != "All classes":
    view = view[view["Trajectory"] == label]
if search:
    view = view[view["technology_name"].str.contains(search, case=False, regex=False, na=False)]
if order == "Name A to Z":
    view = view.sort_values("technology_name", key=lambda x: x.str.casefold())
else:
    view = view.sort_values("Risk indicator", ascending=order == "Lowest risk first", na_position="last")
st.caption(f"Showing {len(view):,} of {len(frame):,} saved records. Filters only select rows; they do not generate predictions.")
if view.empty:
    st.info("No records match these filters. Change a filter or clear the search.")
else:
    if probabilities:
        chart = view.dropna(subset=["Risk indicator"]).head(15)
        fig = px.bar(chart.sort_values("Risk indicator"), x="Risk indicator", y="technology_name", color="Trajectory", orientation="h", title="Saved records with the highest derived risk indicator", color_discrete_map={"Growing":"#527D5A","Stable":"#8B6C37","Declining":"#8B443D"}, hover_data=["category"] if "category" in view else None)
        fig.update_layout(xaxis_title="Derived indicator (0-100)", yaxis_title="Technology", paper_bgcolor="#F3EEE7", plot_bgcolor="#F3EEE7", font_color="#3A3734")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("The indicator is (1 - saved P(Growing)) × 100. It is not a validated probability of failure or decline.")
    cols = [c for c in ["technology_name", "category", "Trajectory", "Risk indicator", "confidence", "confidence_level"] if c in view]
    table = view[cols].rename(columns={"technology_name":"Technology", "category":"Category", "confidence":"Maximum class probability", "confidence_level":"Confidence band"})
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button("Download visible rows as CSV", table.to_csv(index=False).encode("utf-8"), file_name="techpulse_visible_rankings.csv", mime="text/csv")
with st.expander("What a ranking can and cannot tell you"):
    st.write("A ranking sorts the saved model-derived indicator, when probabilities exist. It is not a ranking of popularity, software quality, enterprise use or future success. The records are a single saved snapshot, and class support and data provenance affect interpretation.")
