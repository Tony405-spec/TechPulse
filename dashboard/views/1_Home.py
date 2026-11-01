"""Search technology rows and inspect observed community activity."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell
from dashboard.data import load_community, load_predictions

render_shell("Technology Explorer", "Find a technology, then compare its saved model row with observed community activity.", "EXPLORE")
disclaimer_panel()
rows, has_probabilities = load_predictions()
if rows.empty or "technology_name" not in rows:
    st.warning("No technology records are available. Run `python pipeline/run_pipeline.py` from the project root to regenerate the local pipeline artifacts.")
    st.stop()

terms = rows["technology_name"].dropna().astype(str).sort_values(key=lambda x: x.str.casefold()).unique().tolist()
search = st.text_input("Search technology names", placeholder="For example: python, amazon, or react")
filtered = rows[rows["technology_name"].str.contains(search, case=False, regex=False, na=False)] if search else rows
if "category" in filtered:
    categories = ["All categories"] + sorted(filtered["category"].dropna().astype(str).unique().tolist())
    category = st.selectbox("Category", categories)
    if category != "All categories":
        filtered = filtered[filtered["category"].astype(str) == category]
if filtered.empty:
    st.info("No matching technology was found. Try a shorter search or clear the category filter.")
    st.stop()

selected = st.selectbox("Choose a technology", filtered["technology_name"].tolist())
row = filtered.loc[filtered["technology_name"] == selected].iloc[0]
label = str(row.get("predicted_label", row.get("trajectory_label", "Unavailable")))
st.markdown(f"### {selected}")
a, b, c = st.columns(3)
with a:
    st.metric("Saved trajectory class", label)
with b:
    if has_probabilities and pd.notna(row.get("risk_score")):
        st.metric("Derived risk indicator", f"{float(row['risk_score']):.1f}/100")
    else:
        st.metric("Derived risk indicator", "Unavailable")
with c:
    conf = row.get("confidence_level", "Unavailable")
    st.metric("Saved confidence band", str(conf))
st.caption("This selector reads a saved row; it does not run a new prediction.")

community = load_community()
if not community.empty and {"tag", "date", "question_count"}.issubset(community.columns):
    available_tags = community["tag"].dropna().astype(str).unique()
    matches = [tag for tag in available_tags if tag.casefold() == str(selected).casefold()]
    if matches:
        monthly = community.loc[community["tag"] == matches[0]].dropna(subset=["date"])
        monthly = monthly.assign(month=monthly["date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False)["question_count"].sum()
        fig = px.line(monthly, x="month", y="question_count", markers=True, title=f"Observed Stack Exchange questions tagged {matches[0]}")
        fig.update_traces(line_color="#6D6255", marker_color="#6D6255")
        fig.update_layout(xaxis_title="Month", yaxis_title="Question count", paper_bgcolor="#F3EEE7", plot_bgcolor="#F3EEE7", font_color="#3A3734")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("WHAT THIS SHOWS: monthly question volume in the local community CSV. It indicates activity in this source, not total developer use, technology quality, or future success.")
        st.caption(f"Observed period: {monthly['month'].min():%Y-%m} to {monthly['month'].max():%Y-%m}.")
    else:
        st.info("No exact tag match exists in the community CSV for this selected technology. The chart is omitted rather than treating missing history as zero.")
else:
    st.info("Historical community observations are unavailable in the local project files.")

signals = [c for c in ["technology_health_score", "growth_momentum_index", "question_quality_score", "company_diversity_score", "sentiment_delta", "adoption_velocity", "community_decay_rate"] if c in row.index]
st.markdown("### Available model input signals")
if signals:
    values = pd.DataFrame({"Signal": signals, "Value": [pd.to_numeric(row[x], errors="coerce") for x in signals]})
    values["Value"] = values["Value"].round(3)
    st.dataframe(values, use_container_width=True, hide_index=True)
else:
    st.info("No engineered signal columns are present in this artifact.")
with st.expander("How to interpret this page"):
    st.write("WHAT IS THIS? A saved technology record alongside an observed source trend. WHY DOES IT MATTER? It lets you inspect the evidence behind a row. HOW DO I USE IT? Search by name and select a record. LIMITATION: historical community data may not match the model observation period, and proxy-derived signals are not direct measurements.")
