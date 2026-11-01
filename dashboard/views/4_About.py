"""Always-available beginner guide, glossary and responsible-use statement."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell

ROOT=Path(__file__).resolve().parents[2]
render_shell("About & User Guide", "Help for navigating the research prototype and interpreting its saved results.", "HELP")
disclaimer_panel()

st.markdown("### Quick guide")
st.markdown("1. Open **Start Here** for purpose and limitations.\n2. Use **Technology Explorer** to search and view observed community activity.\n3. Use **Technology Rankings** to filter saved records.\n4. Use **Prediction Explorer** to inspect a stored result.\n5. Use **Model Performance & Validation** to review evaluation artifacts and caveats.\n6. Use **Methodology & Data** for sources, feature definitions and SQL query files.")
st.info("Every result is either source observation, a derived metric, or a saved model output. Check the page caption and Methodology & Data before interpreting it.")

st.markdown("### Glossary")
glossary={
"Machine learning":"A method that fits patterns in example data to make classifications or estimates.",
"Classification":"Assigning an observation to a category, here Growing, Stable or Declining.",
"Feature / signal":"A measured or derived input supplied to a model.",
"Target label":"The category the model is trained to predict, derived here from later activity relative to recent activity.",
"Training data":"Examples used to fit model parameters.",
"Test data":"Examples held out from model fitting to estimate performance; it must represent the intended use and avoid leakage.",
"Baseline":"A simple reference such as always predicting the most frequent training class.",
"Accuracy":"The fraction of all test examples classified correctly; it can hide poor results for rare classes.",
"Precision":"Among examples predicted as a class, the proportion that truly belongs to that class.",
"Recall":"Among true examples of a class, the proportion the model finds.",
"F1 score":"A combined summary of precision and recall.",
"Weighted F1":"F1 averaged across classes with weights based on each class's support.",
"Macro F1":"F1 averaged equally across classes, giving rare classes more influence than weighted F1.",
"Cross-validation":"Repeated internal train/validation splits used for model selection; not a replacement for a sound final test set.",
"Feature importance":"A measure of how a model uses input variables; it does not establish causation.",
"SHAP":"A method that attributes a model output across its input features relative to a reference.",
"PostgreSQL":"A relational database system supported by the project's ingestion pipeline.",
"Data provenance":"Information about where data came from and how it was transformed.",
"Data leakage":"Information unavailable at prediction time influencing training or evaluation.",
"Prediction probability":"A model's estimated class score; unless calibrated and validated, it is not a guarantee.",
}
for term,definition in glossary.items():
    with st.expander(term): st.write(definition)

st.markdown("### Frequently asked questions")
faqs={
"Does selecting a technology run a new prediction?":"No. The current dashboard reads saved pipeline outputs. It does not create predictions for new input.",
"Does a high risk score mean failure is likely?":"No. Where probabilities exist it is (1 - P(Growing)) × 100, a complement of the model's Growing score. It is not validated probability of decline or failure.",
"Why are some charts unavailable?":"The app omits charts when matching dated observations are absent. Missing history is not treated as zero activity.",
"Are company technology records observed in the local mode?":"No. The repository's local fallback derives deterministic company-stack and mapping proxies. Fortune profiles alone do not prove a company uses a technology.",
"Why should I be cautious about model metrics?":"Saved artifacts in this checkout lack a run-level evaluation summary and have label-summary inconsistencies. The recorded metrics cannot currently be independently audited from this checkout.",
"Can I use TechPulse to make hiring or migration decisions?":"No. It is an academic research aid, not professional decision support or a guarantee of future technology performance.",
}
for q,a in faqs.items():
    with st.expander(q): st.write(a)

docs=ROOT/"docs"
st.markdown("### Downloadable guides")
for name in ["TechPulse_User_Manual.pdf","TechPulse_Technical_Reference.pdf","TechPulse_5_Minute_Demo_Guide.pdf"]:
    f=docs/name
    if f.exists():
        st.download_button(f"Download {name.replace('_',' ')}",data=f.read_bytes(),file_name=name,mime="application/pdf")
    else:
        st.caption(f"{name} is not yet present in this checkout.")
