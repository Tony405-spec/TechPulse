"""Display recorded model metrics with explicit auditability checks."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell
from dashboard.data import DATA, OUTPUTS, artifact_consistency, load_predictions, read_csv_artifact, read_json_artifact

render_shell("Model Performance & Validation", "Compare the metric artifact with the evidence needed to interpret it.", "MODEL AUDIT")
disclaimer_panel()
metrics = read_csv_artifact(str(OUTPUTS / "model_comparison.csv"))
features = read_csv_artifact(str(DATA / "feature_matrix.csv"))
eval_meta = read_json_artifact(str(OUTPUTS / "evaluation_summary.json"))
selection = read_json_artifact(str(OUTPUTS / "best_model_selection.json"))
if metrics.empty:
    st.warning("No model comparison CSV is available. Run the pipeline to create model metrics.")
else:
    recorded = metrics.copy()
    baseline_present = "Model" in recorded and recorded["Model"].astype(str).str.contains("baseline", case=False, na=False).any()
    if not eval_meta:
        st.error("**Read this before interpreting the scores:** this checkout has no run-level evaluation summary. The displayed metrics cannot be independently tied to a documented split or held-out class distribution.")
    if not baseline_present:
        st.warning("The saved comparison contains no majority-class baseline row. The current metrics therefore do not establish improvement over that simple reference.")
    if artifact_consistency():
        st.warning("There are inconsistencies among the saved labels and run artifacts. Review the warnings on Start Here and reconcile the artifacts before making performance claims.")
    st.markdown("### Recorded model comparison")
    st.caption("Values below are read directly from `outputs/model_comparison.csv`; they are not recalculated by this page.")
    number_formats = {column: "{:.4f}" for column in ["Accuracy", "Weighted_F1", "Precision", "Recall", "Macro_ROC_AUC"] if column in recorded}
    st.dataframe(recorded.style.format(number_formats), use_container_width=True, hide_index=True)
    ml = recorded[~recorded["Model"].astype(str).str.startswith("baseline_")] if "Model" in recorded else recorded
    if {"Model", "Weighted_F1"}.issubset(ml.columns):
        plot=ml.copy()
        plot["Weighted_F1"] = pd.to_numeric(plot["Weighted_F1"], errors="coerce")
        fig=px.bar(plot,x="Weighted_F1",y="Model",orientation="h",title="Weighted F1 recorded for candidate models",range_x=[0,1])
        fig.update_traces(marker_color="#8B7D6B")
        fig.update_layout(xaxis_title="Weighted F1 (0-1)",yaxis_title="Candidate model",paper_bgcolor="#F3EEE7",plot_bgcolor="#F3EEE7",font_color="#3A3734")
        st.plotly_chart(fig,use_container_width=True)
    if not eval_meta:
        st.caption("The score table is retained as a record of the saved CSV. Split dates, held-out class counts, and probability-score validity remain unverified in this checkout.")
    if not {"Macro_F1", "Per_Class_Precision", "Per_Class_Recall"}.issubset(recorded.columns):
        st.info("Macro F1 and per-class precision/recall are not supplied in the saved comparison CSV. They are not inferred from aggregate scores.")
    if "Macro_ROC_AUC" in recorded and not eval_meta:
        st.warning("ROC-AUC values in the CSV are left as recorded, but without split class-coverage metadata their validity cannot be confirmed. AUC should be marked unavailable when required classes are absent.")
    if selection:
        st.caption(f"Saved selection record: {selection.get('selected_model','not recorded')} — {selection.get('reason','No selection rationale is recorded.')}")

st.markdown("### Label support in the current feature table")
if not features.empty and "trajectory_label" in features:
    support=features["trajectory_label"].value_counts(dropna=False).reindex(["Growing","Stable","Declining"],fill_value=0).rename_axis("Class").reset_index(name="Rows")
    support["Share (%)"]=(100*support["Rows"]/max(1,len(features))).round(1)
    st.dataframe(support,use_container_width=True,hide_index=True)
    if (support["Rows"] == 0).any():
        st.error("At least one target class has no examples in the current labeled feature table. A three-class evaluation is not supported by this table.")
else:
    st.info("A labeled feature table is not available for class-support checks.")

st.markdown("### Audit checks")
issues=artifact_consistency()
if issues:
    for issue in issues: st.warning(issue)
else:
    st.success("No obvious label-summary mismatch was found in the available artifacts. This does not replace a full evaluation audit.")

for title, body in {
    "Accuracy": "The share of all test rows classified correctly. If one class dominates, a model can score well by mostly predicting that class.",
    "Precision and recall": "Precision asks how often predictions for a class are correct. Recall asks how many actual examples of that class are found.",
    "Weighted F1": "A precision-recall balance averaged across classes with more influence from classes with more test rows. It can still hide weak performance on a rare class.",
    "Macro F1 and per-class results": "Macro F1 gives each class equal weight. Per-class precision, recall, support, and a confusion matrix help reveal which groups are missed.",
    "Why compare with a baseline?": "A majority-class baseline always predicts the most common training class. The candidate model should be compared with this simple reference to determine whether the added complexity improves the result.",
    "Split and leakage": "The training code in this checkout uses a stratified random 80/20 split, not a chronological split. Because observations are repeated across technologies and time, temporal and grouped validation should be considered before making generalisation claims.",
}.items():
    with st.expander(title): st.write(body)
