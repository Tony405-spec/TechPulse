"""Observed community metrics, separated from proxy-based model features."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell
from dashboard.data import load_community, load_survey

render_shell("Community Health", "Inspect activity and unanswered-question signals from the observed community file.", "COMMUNITY SIGNALS")
disclaimer_panel()
community = load_community()
if community.empty or not {"tag", "question_count"}.issubset(community.columns):
    st.warning("Community observations are missing or do not contain the expected tag and question_count columns.")
    st.stop()

summary = community.groupby("tag", dropna=True).agg(questions=("question_count", "sum"), records=("question_count", "size"), unanswered=("unanswered_count", "sum") if "unanswered_count" in community else ("question_count", "sum")).reset_index()
summary["unanswered_share_pct"] = (100 * summary["unanswered"] / summary["questions"].replace(0, pd.NA)).round(2)
name = st.selectbox("Choose a technology tag", sorted(summary["tag"].astype(str).tolist(), key=str.casefold))
row = summary.loc[summary["tag"].astype(str) == name].iloc[0]
c1,c2,c3=st.columns(3)
c1.metric("Observed questions", f"{int(row['questions']):,}")
c2.metric("Source records", f"{int(row['records']):,}")
c3.metric("Unanswered share", f"{row['unanswered_share_pct']:.1f}%" if pd.notna(row['unanswered_share_pct']) else "Unavailable")

selected=community.loc[community["tag"].astype(str)==name].dropna(subset=["date"]).copy()
if not selected.empty:
    monthly=selected.assign(month=selected["date"].dt.to_period("M").dt.to_timestamp()).groupby("month",as_index=False).agg(questions=("question_count","sum"))
    fig=px.line(monthly,x="month",y="questions",markers=True,title=f"Observed monthly question volume: {name}")
    fig.update_traces(line_color="#6D6255", marker_color="#6D6255")
    fig.update_layout(xaxis_title="Month",yaxis_title="Questions in source data",paper_bgcolor="#F3EEE7",plot_bgcolor="#F3EEE7",font_color="#3A3734")
    st.plotly_chart(fig,use_container_width=True)
    st.caption(f"Horizontal axis: calendar month. Vertical axis: sum of questions recorded for this tag. Observed range: {monthly['month'].min():%Y-%m} to {monthly['month'].max():%Y-%m}.")
    st.caption("A rise or fall describes this source's activity only. It does not show all developer use or establish why activity changed.")
else:
    st.info("No dated records are available for this tag. Missing history is not plotted as zero.")

survey=load_survey()
st.markdown("### Developer survey measures")
if survey.empty:
    st.info("No `data/developer_survey_usage.csv` file is present in this checkout. Survey measures cannot be displayed from this run.")
elif "technology" in survey and str(name).casefold() in survey["technology"].astype(str).str.casefold().values:
    sr=survey.loc[survey["technology"].astype(str).str.casefold()==str(name).casefold()].copy()
    if "survey_year" in sr:
        st.dataframe(sr.sort_values("survey_year"),use_container_width=True,hide_index=True)
    else:
        st.dataframe(sr,use_container_width=True,hide_index=True)
    st.caption("Survey shares are self-selected respondent aggregates. They are shown separately and are not treated as time-aligned inputs to historical predictions.")
else:
    st.info("No matching survey aggregate is available for this technology. Survey data, when present, is kept separate from the earlier community history.")
with st.expander("What these health signals mean"):
    st.write("Question volume is a measure of recorded participation on the source platform. Unanswered share is unanswered questions divided by question count when both fields are present. Neither directly measures software quality, total usage, causes of change, or future trajectory.")
