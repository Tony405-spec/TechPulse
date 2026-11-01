"""Shared TechPulse dashboard presentation components."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.common import DISCLAIMER, FEATURE_COLUMNS
from dashboard.data import data_mode as _data_mode, read_json_artifact

MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "knn": "K-Nearest Neighbours",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

FEATURE_DESCRIPTIONS = {
    "technology_health_score": "Composite health across community, adoption, and sentiment signals.",
    "growth_momentum_index": "Recent question volume compared with the trailing activity window.",
    "question_quality_score": "Answer availability adjusted for closure or unresolved-question pressure.",
    "company_diversity_score": "Breadth of enterprise sector adoption.",
    "sentiment_delta": "Change in developer satisfaction across available observations.",
    "adoption_velocity": "Recent pace of new enterprise adoption.",
    "community_decay_rate": "Recent community activity decline pressure.",
}


def apply_theme() -> None:
    """Install the TechPulse quiet-luxury visual system."""
    st.markdown(
        """
        <style>
        :root {
            --tp-bg: #E8DFD2;
            --tp-panel: #F3EEE7;
            --tp-panel-2: #DDD2C3;
            --tp-border: #8B7D6B;
            --tp-green: #3A3734;
            --tp-cyan: #6B5B4B;
            --tp-purple: #6B5B4B;
            --tp-pink: #76564E;
            --tp-text: #3A3734;
            --tp-muted: #5F554B;
            --tp-warn: #765E36;
            --tp-danger: #7D4038;
        }
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: #E8DFD2 !important;
            color: var(--tp-text);
            font-family: "Segoe UI", Arial, sans-serif;
            color-scheme: light;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"] { background: #E8DFD2 !important; color: #3A3734 !important; }
        [data-testid="stMain"], [data-testid="stMainBlockContainer"] { background: #E8DFD2 !important; }
        section[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background: #DDD2C3 !important;
            border-right: 1px solid #8B7D6B;
        }
        section[data-testid="stSidebar"] * { color: #3A3734; }
        h1, h2, h3 {
            color: var(--tp-green);
            letter-spacing: 0;
        }
        p, li, span, label { color: #3A3734; }
        .tp-hero {
            border: 1px solid #8B7D6B;
            background: #F3EEE7;
            padding: 1.2rem 1.4rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .tp-kicker { color: var(--tp-cyan); font-size: 0.78rem; text-transform: uppercase; }
        .tp-title { color: var(--tp-green); font-size: 2rem; font-weight: 800; line-height: 1.1; }
        .tp-subtitle { color: #514940; max-width: 64rem; }
        .tp-card {
            border: 1px solid #B8AA98;
            background: #F3EEE7;
            padding: 1rem;
            border-radius: 8px;
            min-height: 6.4rem;
            box-shadow: none;
        }
        .tp-card:hover { border-color: #8B7D6B; }
        .tp-label { color: var(--tp-muted); font-size: 0.75rem; text-transform: uppercase; }
        .tp-value { color: var(--tp-text); font-size: 1.55rem; font-weight: 800; }
        .tp-note { color: var(--tp-muted); font-size: 0.82rem; }
        .tp-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            padding: 0.22rem 0.58rem;
            border: 1px solid currentColor;
            font-size: 0.78rem;
            font-weight: 800;
        }
        .tp-online { color: #3A3734; }
        .tp-dev { color: var(--tp-warn); }
        .tp-risk-high { color: var(--tp-danger); }
        .tp-risk-med { color: var(--tp-warn); }
        .tp-risk-low { color: var(--tp-green); }
        .stApp, [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] { color: #3A3734; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { background: #F3EEE7; }
        .stButton button, .stDownloadButton button { background: #8B7D6B; color: #fff; border-color: #6D6255; }
        .stButton button:hover, .stDownloadButton button:hover { background: #6D6255; color: #fff; border-color: #3A3734; }
        input, textarea, [data-baseweb="select"] > div { background: #F7F3ED !important; color: #3A3734 !important; }
        [role="option"], [role="listbox"] { background: #F7F3ED !important; color: #3A3734 !important; }
        [data-testid="stAlert"] { color: #3A3734; }
        div[data-testid="stDataFrame"] {
            border: 1px solid #8B7D6B;
            border-radius: 8px;
        }
        .stButton button, .stDownloadButton button {
            background: #8B7D6B;
            border: 1px solid #6D6255;
            color: #ffffff;
            border-radius: 6px;
            font-weight: 700;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            border-color: #8B7D6B;
        }
        [data-testid="stMetric"] { background: #F3EEE7; border: 1px solid #8B7D6B; padding: .8rem; border-radius: 6px; }
        [data-testid="stPlotlyChart"] { background: #F3EEE7; border: 1px solid #8B7D6B; border-radius: 6px; }
        [data-testid="stDataFrame"] iframe { color-scheme: light; }
        [aria-selected="true"] { background: #8B7D6B !important; color: #ffffff !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_json(path: str) -> dict[str, Any]:
    """Load a JSON artifact safely."""
    return read_json_artifact(path)


def selected_model_name() -> str:
    """Return the selected model display name from persisted metadata."""
    selection = load_json("outputs/best_model_selection.json")
    model = str(selection.get("selected_model", "Unavailable"))
    return MODEL_LABELS.get(model, model)


def data_mode() -> str:
    """Return the current data source mode."""
    return _data_mode()


def render_sidebar() -> None:
    """Render the command-center sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Workspace context")
    st.sidebar.caption(f"Source: **{data_mode()}**")
    st.sidebar.caption(f"Saved model: **{selected_model_name()}**")
    st.sidebar.caption(f"Predictive signals: **{len(FEATURE_COLUMNS)}**")
    st.sidebar.caption("Academic research prototype")
    st.sidebar.markdown("---")
    st.sidebar.page_link("views/0_Start_Here.py", label="Return to Start Here", icon="🏠")
    st.sidebar.page_link("views/4_About.py", label="Help, glossary & FAQ", icon="❔")


def render_shell(title: str, subtitle: str, kicker: str = "TECHPULSE") -> None:
    """Render a page header and data-status badges."""
    apply_theme()
    render_sidebar()
    mode = data_mode()
    is_development = "development" in mode.casefold()
    status_badge = "DEVELOPMENT DATA" if is_development else mode.upper()
    status_class = "tp-dev" if is_development else "tp-online"
    st.markdown(
        f"""
        <div class="tp-hero">
          <div class="tp-kicker">{kicker}</div>
          <div class="tp-title">{title}</div>
          <div class="tp-subtitle">{subtitle}</div>
          <div style="margin-top:0.7rem">
            <span class="tp-badge {status_class}">● {status_badge}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> None:
    """Render a compact metric card."""
    st.markdown(
        f"""
        <div class="tp-card">
          <div class="tp-label">{label}</div>
          <div class="tp-value">{value}</div>
          <div class="tp-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def disclaimer_panel() -> None:
    """Render the research disclaimer."""
    st.warning(
        "ACADEMIC RESEARCH PROTOTYPE: "
        + DISCLAIMER
        + " Predictions are not guaranteed outcomes and are not stand-alone investment, hiring, migration, or strategy advice."
    )


def risk_class(score: float) -> str:
    """Return visual risk class for a score."""
    if score >= 70:
        return "tp-risk-high"
    if score >= 40:
        return "tp-risk-med"
    return "tp-risk-low"
