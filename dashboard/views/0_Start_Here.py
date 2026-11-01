"""Plain-language introduction and guided path through TechPulse."""

from __future__ import annotations

import streamlit as st

from dashboard.components.ui import disclaimer_panel, metric_card, render_shell
from dashboard.data import DATA, artifact_consistency, load_predictions, load_community, load_survey, data_mode, read_csv_artifact

render_shell("Start Here", "A short orientation to the questions, evidence and limits in TechPulse.", "WELCOME")
st.markdown("## What is TechPulse?")
st.write(
    "TechPulse is a final-year data science research prototype. It studies whether "
    "software technologies show Growing, Stable or Declining trajectories by "
    "combining historical developer-community activity with derived signals and "
    "saved machine-learning outputs. It helps users explore the evidence; it does "
    "not decide which technology an organisation should adopt."
)
disclaimer_panel()

predictions, has_probabilities = load_predictions()
community, survey = load_community(), load_survey()
c1, c2, c3 = st.columns(3)
with c1:
    metric_card("Saved technology records", f"{len(predictions):,}", "From current prediction or feature artifact")
with c2:
    metric_card("Community observations", f"{len(community):,}", "Local Stack Exchange CSV rows")
with c3:
    metric_card("Developer survey", f"{len(survey):,}" if not survey.empty else "Not present", "Separate survey aggregates; not joined to historical rows")

mode = data_mode()
st.info(f"**Recorded data mode:** {mode}. Use Methodology & Data to review the source manifest and data caveats.")
if not has_probabilities:
    st.warning("The current saved table does not include all three class probabilities. Prediction Explorer will show what is available and mark missing values.")
for issue in artifact_consistency():
    st.warning(issue)

feature_table = read_csv_artifact(str(DATA / "feature_matrix.csv"))
if "trajectory_label" in feature_table and "predicted_label" in predictions:
    st.markdown("### Labels and predictions are different fields")
    target_counts = feature_table["trajectory_label"].value_counts().reindex(["Growing", "Stable", "Declining"], fill_value=0)
    saved_counts = predictions["predicted_label"].value_counts().reindex(["Growing", "Stable", "Declining"], fill_value=0)
    left, right = st.columns(2)
    with left:
        st.caption("Observed target labels in current feature matrix")
        st.write("Growing: **{:,.0f}** · Stable: **{:,.0f}** · Declining: **{:,.0f}**".format(*(target_counts[x] for x in ["Growing", "Stable", "Declining"])))
    with right:
        st.caption("Classes in current saved predictions")
        st.write("Growing: **{:,.0f}** · Stable: **{:,.0f}** · Declining: **{:,.0f}**".format(*(saved_counts[x] for x in ["Growing", "Stable", "Declining"])))

st.markdown("## Suggested first visit")
st.markdown(
    "1. **Technology Explorer** - search for a name and view its saved community history.\n"
    "2. **Technology Rankings** - compare the saved records using the displayed risk indicator.\n"
    "3. **Community Health** - inspect activity volume and unanswered-question share.\n"
    "4. **Prediction Explorer** - interpret one saved prediction and its probabilities.\n"
    "5. **Model Performance & Validation** - compare candidates with simple baselines.\n"
    "6. **Methodology & Data** - inspect sources, labels, SQL analyses and limitations."
)
with st.expander("What do the three classes mean?"):
    st.write("The pipeline labels a record by comparing a future activity window with a recent activity window. The implementation uses a growth ratio of 1.20 or above for Growing and 0.80 or below for Declining; ratios between the thresholds are Stable. These are operational research labels, not universal definitions of technology success.")
with st.expander("How should I interpret the risk score?"):
    st.write("When saved class probabilities are present, risk is computed as (1 - estimated probability of Growing) × 100. It is a complement of the model's Growing score, not a separately validated probability that a technology will fail or decline.")
with st.expander("Is this evidence ready for real-world decisions?"):
    st.write("No. Local development mode includes derived proxy tables, source periods may not align, and saved evaluation artifacts must be checked against their split metadata. Treat outputs as exploratory research evidence only.")
