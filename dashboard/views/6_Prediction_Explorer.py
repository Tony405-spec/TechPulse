"""Inspect an existing saved prediction without implying live inference."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell
from dashboard.data import OUTPUTS, load_predictions, risk_from_probability

render_shell("Prediction Explorer", "Inspect the saved class, probabilities and input signals for one technology.", "SAVED MODEL OUTPUT")
disclaimer_panel()
frame, has_probabilities = load_predictions()
if frame.empty:
    st.info("No saved technology record is available. Run the local pipeline to generate prediction artifacts.")
    st.stop()
search = st.text_input("Find a technology", placeholder="Type part of a technology name")
match = frame[frame["technology_name"].str.contains(search, case=False, regex=False, na=False)] if search else frame
if match.empty:
    st.info("No saved technology matches this search.")
    st.stop()
technology = st.selectbox("Select a saved technology", match["technology_name"].tolist())
row = match.loc[match["technology_name"] == technology].iloc[0]
label = str(row.get("predicted_label", row.get("trajectory_label", "Unavailable")))
st.markdown(f"## {technology}")
st.markdown(f"### Saved classification: **{label}**")
st.caption("This page reads pipeline outputs. Choosing a technology does not fit a model or generate a new prediction.")

if has_probabilities:
    probs = pd.DataFrame({"Class": ["Growing", "Stable", "Declining"], "Estimated model score": [row.get("prob_Growing"), row.get("prob_Stable"), row.get("prob_Declining")]})
    probs["Estimated model score"] = pd.to_numeric(probs["Estimated model score"], errors="coerce")
    risk = risk_from_probability(row.get("prob_Growing"))
    cols=st.columns(3)
    cols[0].metric("Saved class", label)
    cols[1].metric("Maximum class score", f"{float(row['confidence']):.1%}" if pd.notna(row.get("confidence")) else f"{probs['Estimated model score'].max():.1%}")
    cols[2].metric("Derived risk indicator", f"{risk:.1f}/100" if risk is not None else "Unavailable")
    fig=px.bar(probs,x="Class",y="Estimated model score",color="Class",range_y=[0,1],title="Saved class probability scores",color_discrete_map={"Growing":"#527D5A","Stable":"#8B6C37","Declining":"#8B443D"})
    fig.update_layout(xaxis_title="Trajectory class",yaxis_title="Model score (0-1)",paper_bgcolor="#F3EEE7",plot_bgcolor="#F3EEE7",font_color="#3A3734")
    st.plotly_chart(fig,use_container_width=True)
    st.info("The risk indicator is (1 - P(Growing)) × 100. It is not a separately trained or validated probability of failure or decline. The class scores are model outputs, not guarantees.")
else:
    st.warning("The saved record does not contain all three class probability columns. Probabilities, confidence and probability-based risk cannot be reconstructed reliably.")

feature_cols=[c for c in ["technology_health_score","growth_momentum_index","question_quality_score","company_diversity_score","sentiment_delta","adoption_velocity","community_decay_rate"] if c in row.index]
st.markdown("### Available input signals")
if feature_cols:
    st.dataframe(pd.DataFrame({"Signal":feature_cols,"Saved value":[row[c] for c in feature_cols]}),use_container_width=True,hide_index=True)

shap_path=OUTPUTS / "shap_per_prediction.json"
if shap_path.exists():
    try:
        shap_rows=json.loads(shap_path.read_text(encoding="utf-8"))
        item=next((x for x in shap_rows if str(x.get("technology_name","")).casefold()==str(technology).casefold()),None)
        if item and isinstance(item.get("feature_shap_values"),dict):
            vals=pd.DataFrame({"Signal":list(item["feature_shap_values"]),"SHAP contribution":list(item["feature_shap_values"].values())}).sort_values("SHAP contribution",key=lambda s:s.abs(),ascending=True)
            st.markdown("### Saved local SHAP attribution")
            fig=px.bar(vals,x="SHAP contribution",y="Signal",orientation="h",title="Contribution to this model output")
            fig.update_layout(xaxis_title="SHAP value (direction depends on model class)",yaxis_title="Input signal",paper_bgcolor="#F3EEE7",plot_bgcolor="#F3EEE7",font_color="#3A3734")
            st.plotly_chart(fig,use_container_width=True)
            st.caption("SHAP describes how this fitted model attributed its output across input signals. It does not show that a signal causes a trajectory.")
    except (OSError, ValueError, TypeError):
        st.info("The local explanation artifact could not be read; the saved prediction remains available.")
with st.expander("What is confidence?"):
    st.write("The application records the maximum class score as confidence. A high score is not a calibrated guarantee of correctness, especially when the evaluation data are small, imbalanced, or not representative.")
