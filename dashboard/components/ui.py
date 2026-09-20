"""Shared TechPulse dashboard presentation components."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.common import DISCLAIMER, FEATURE_COLUMNS, OUTPUTS_DIR

MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "knn": "K-Nearest Neighbours",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

FEATURE_DESCRIPTIONS = {
    "technology_health_score": "Composite health across community, survey, and adoption/proxy signals.",
    "growth_momentum_index": "Recent question volume compared with the trailing activity window.",
    "question_quality_score": "Answer availability adjusted for closure or unresolved-question pressure.",
    "company_diversity_score": "Breadth of enterprise sector adoption.",
    "sentiment_delta": "Change in observed developer survey usage share when public survey data is available.",
    "adoption_velocity": "Recent pace of new enterprise adoption.",
    "community_decay_rate": "Recent community activity decline pressure.",
}


def apply_theme() -> None:
    """Install the TechPulse institutional intelligence visual system."""
    st.markdown(
        """
        <style>
        :root {
            --tp-bg: #0b0c0f;
            --tp-bg-2: #111318;
            --tp-panel: #171a20;
            --tp-panel-2: #20242c;
            --tp-elevated: #252a33;
            --tp-border: #3a3f49;
            --tp-border-soft: rgba(218, 204, 173, 0.18);
            --tp-accent: #d8c08a;
            --tp-accent-2: #a98247;
            --tp-text: #f4efe5;
            --tp-muted: #b8b0a2;
            --tp-subtle: #837c70;
            --tp-positive: #7fb394;
            --tp-warning: #d7ad62;
            --tp-negative: #c76d63;
            --tp-neutral: #9ba4b0;
        }
        .stApp {
            background: linear-gradient(180deg, var(--tp-bg) 0%, #111216 100%);
            color: var(--tp-text);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        section[data-testid="stSidebar"] {
            background: #0f1116;
            border-right: 1px solid var(--tp-border-soft);
        }
        section[data-testid="stSidebar"] * { color: var(--tp-text); }
        h1, h2, h3 {
            color: var(--tp-text);
            letter-spacing: 0;
            font-weight: 650;
        }
        p, li, span, label { color: var(--tp-text); }
        div[data-testid="stCaptionContainer"], .stCaptionContainer { color: var(--tp-muted); }
        .tp-hero {
            border: 1px solid var(--tp-border-soft);
            background: linear-gradient(135deg, rgba(216, 192, 138, 0.11), rgba(37, 42, 51, 0.92));
            padding: 1.35rem 1.5rem;
            border-radius: 8px;
            margin-bottom: 1.1rem;
        }
        .tp-kicker { color: var(--tp-accent); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }
        .tp-title { color: var(--tp-text); font-size: 2rem; font-weight: 700; line-height: 1.1; }
        .tp-subtitle { color: var(--tp-muted); max-width: 64rem; }
        .tp-card {
            border: 1px solid var(--tp-border-soft);
            background: rgba(23, 26, 32, 0.96);
            padding: 1rem;
            border-radius: 8px;
            min-height: 6.4rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        }
        .tp-card:hover { border-color: rgba(216, 192, 138, 0.42); }
        .tp-label { color: var(--tp-muted); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; }
        .tp-value { color: var(--tp-text); font-size: 1.55rem; font-weight: 700; }
        .tp-note { color: var(--tp-muted); font-size: 0.82rem; }
        .tp-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            padding: 0.22rem 0.58rem;
            border: 1px solid currentColor;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .tp-online { color: var(--tp-positive); }
        .tp-dev { color: var(--tp-warning); }
        .tp-risk-high { color: var(--tp-negative); }
        .tp-risk-med { color: var(--tp-warning); }
        .tp-risk-low { color: var(--tp-positive); }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--tp-border-soft);
            border-radius: 8px;
        }
        .stButton button, .stDownloadButton button {
            background: #171a20;
            border: 1px solid rgba(216, 192, 138, 0.58);
            color: var(--tp-accent);
            border-radius: 6px;
            font-weight: 650;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            border-color: rgba(216, 192, 138, 0.35);
            background-color: #151820;
        }
        div[data-testid="stAlert"] {
            border-radius: 8px;
            border: 1px solid var(--tp-border-soft);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_json(path: str) -> dict[str, Any]:
    """Load a JSON artifact safely."""
    target = Path(path)
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def selected_model_name() -> str:
    """Return the selected model display name from persisted metadata."""
    selection = load_json(str(OUTPUTS_DIR / "best_model_selection.json"))
    model = str(selection.get("selected_model", "Unavailable"))
    return MODEL_LABELS.get(model, model)


def data_mode() -> str:
    """Return the current data source mode."""
    manifest = load_json(str(OUTPUTS_DIR / "data_sources.json"))
    mode = str(manifest.get("source_mode", "unknown"))
    if mode == "local_development_csv":
        return "Development data"
    if mode == "postgresql":
        return "Research database"
    return "Unknown"


def render_sidebar() -> None:
    """Render the command-center sidebar."""
    st.sidebar.markdown("## TechPulse")
    st.sidebar.markdown("Research Intelligence Platform")
    st.sidebar.markdown("---")
    st.sidebar.markdown("Command Center")
    st.sidebar.markdown("Technology Explorer")
    st.sidebar.markdown("Global Rankings")
    st.sidebar.markdown("Model Laboratory")
    st.sidebar.markdown("About / Methodology")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### SYSTEM STATUS")
    st.sidebar.markdown(f"**MODEL**  \n{selected_model_name()}")
    st.sidebar.markdown(f"**DATA**  \n{data_mode()}")
    st.sidebar.markdown(f"**FEATURES**  \n{len(FEATURE_COLUMNS)} Signals")
    st.sidebar.markdown("**CLASSES**  \n3 Trajectories")
    st.sidebar.markdown("---")
    st.sidebar.caption("v1.0")


def render_shell(title: str, subtitle: str, kicker: str = "TECHPULSE") -> None:
    """Render a page header and data-status badges."""
    apply_theme()
    render_sidebar()
    mode = data_mode()
    status_badge = "DEVELOPMENT DATA" if mode == "Development data" else "SYSTEM ONLINE"
    status_class = "tp-dev" if mode == "Development data" else "tp-online"
    st.markdown(
        f"""
        <div class="tp-hero">
          <div class="tp-kicker">{kicker}</div>
          <div class="tp-title">{title}</div>
          <div class="tp-subtitle">{subtitle}</div>
          <div style="margin-top:0.7rem">
            <span class="tp-badge tp-online">● SYSTEM ONLINE</span>
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
        "RESEARCH DISCLAIMER: "
        + DISCLAIMER
        + " Predictions are not guaranteed future outcomes and should not be used as the sole basis for investment, hiring, migration, or strategy decisions."
    )


def risk_class(score: float) -> str:
    """Return visual risk class for a score."""
    if score >= 70:
        return "tp-risk-high"
    if score >= 40:
        return "tp-risk-med"
    return "tp-risk-low"
