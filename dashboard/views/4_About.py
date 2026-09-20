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
    TechPulse assesses whether technology-month observations are Growing, Stable, or
    Declining by combining community activity with clearly marked development proxies.
    """,
    "Research Problem": """
    Organisations and developers often make technology adoption decisions using trend
    articles and anecdotal opinion. TechPulse turns existing descriptive ecosystem analytics
    into a reproducible supervised machine-learning workflow.
    """,
    "Objectives": """
    Engineer leakage-aware temporal features, construct future-window labels, compare
    machine-learning models against transparent baselines, explain selected model
    associations with SHAP, and present results through a Streamlit dashboard.
    """,
    "Data Sources": """
    Stack Overflow community signals, official Stack Overflow Developer Survey usage
    aggregates, company profiles, and optional warehouse tables. Local development mode
    clearly marks adoption-stack, metadata, and mapping tables as proxies.
    """,
    "Feature Engineering": """
    Seven normalized signals are used: technology health score, growth momentum index,
    question quality score, company diversity score, survey usage delta, adoption velocity,
    and community decay rate. External signals are used only when available by the
    observation month.
    """,
    "Modelling": """
    Logistic Regression, K-Nearest Neighbours, Random Forest, and XGBoost are trained
    with chronological validation when observation months are available. Majority-class
    and momentum-rule baselines are reported alongside ML models.
    """,
    "Methodological Validity": """
    Target labels are constructed from future community activity windows. Future target
    fields are excluded from model features, and ROC-AUC is not reported when the held-out
    split lacks all required classes.
    """,
    "Explainability": """
    SHAP is used to generate global feature importance and local per-technology
    explanations. Explanations describe model associations, not causal guarantees.
    """,
    "Limitations": """
    Predictions depend on data coverage, recency, schema quality, and class balance.
    Local Stack Exchange observations currently predate the acquired 2021-2024 survey
    window, and local enterprise adoption remains proxy-only. These outputs are useful
    for engineering validation, not final empirical claims.
    """,
    "Data Licences": """
    Stack Exchange activity is attributed under CC BY-SA where applicable. Stack Overflow
    Developer Survey data is used under ODbL 1.0 / DbCL 1.0. Fortune profile data is
    company context, not direct evidence of technology adoption.
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
