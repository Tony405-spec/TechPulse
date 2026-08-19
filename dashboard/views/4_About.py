"""About and documentation page."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.ui import disclaimer_panel, render_shell  # noqa: E402

render_shell(
    "About / Methodology",
    "Academic context, research design, data sources, explainability, and limitations.",
    "PROJECT DOCUMENTATION",
)
disclaimer_panel()

sections = {
    "Project Overview": """
    TechPulse predicts whether software technologies are Growing, Stable, or Declining
    by combining community activity, enterprise adoption, and developer sentiment signals.
    """,
    "Research Problem": """
    Organisations and developers often make technology adoption decisions using trend
    articles and anecdotal opinion. TechPulse turns existing descriptive ecosystem analytics
    into a reproducible supervised machine-learning workflow.
    """,
    "Objectives": """
    Engineer predictive features, train four classifiers, select the strongest model using
    weighted F1, explain predictions with SHAP, and present the results through a Streamlit
    technology intelligence dashboard.
    """,
    "Data Sources": """
    Stack Overflow community signals, developer sentiment survey signals, Fortune 500
    adoption data, company profiles, technology metadata, and question-company mappings.
    Local development mode uses repository CSVs and clearly marks derived demo tables.
    """,
    "Feature Engineering": """
    Seven normalized signals are used: technology health score, growth momentum index,
    question quality score, company diversity score, sentiment delta, adoption velocity,
    and community decay rate.
    """,
    "Modelling": """
    Logistic Regression, K-Nearest Neighbours, Random Forest, and XGBoost are trained
    with an 80/20 stratified split and stratified cross-validation where the dataset
    supports it.
    """,
    "Explainability": """
    SHAP is used to generate global feature importance and local per-technology
    explanations. Explanations describe model associations, not causal guarantees.
    """,
    "Limitations": """
    Predictions depend on data coverage, recency, schema quality, and class balance.
    Demo-derived development data is suitable for smoke testing and presentation flow,
    not for final empirical claims.
    """,
    "Data Licences": """
    Stack Exchange and Stack Overflow data are attributed under CC BY-SA 4.0 where
    applicable. Fortune 500 and technology metadata are aggregated from public/open sources
    for academic research.
    """,
    "Academic Context": """
    Institution: KCA University, School of Technology. Programme: BSc Data Science.
    Project: Final Year Project, 2026. Student: Kitili Tony Kenga. ORCID:
    0009-0007-6899-8590. Supervisor: Dr. Rufus Gireka.
    """,
}

for title, body in sections.items():
    with st.expander(title, expanded=title in {"Project Overview", "Academic Context"}):
        st.write(body)

st.subheader("System Architecture")
st.markdown(
    """
    `DATA` → `SQL ANALYTICS` → `FEATURE ENGINEERING` → `ML MODELS` → `SHAP` → `DASHBOARD`
    """
)
st.link_button("GitHub Repository", "https://github.com/Tony405-spec/TechPulse")
