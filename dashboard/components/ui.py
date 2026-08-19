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
    "technology_health_score": "Composite health across community, adoption, and sentiment signals.",
    "growth_momentum_index": "Recent question volume compared with the trailing activity window.",
    "question_quality_score": "Answer availability adjusted for closure or unresolved-question pressure.",
    "company_diversity_score": "Breadth of enterprise sector adoption.",
    "sentiment_delta": "Change in developer satisfaction across available observations.",
    "adoption_velocity": "Recent pace of new enterprise adoption.",
    "community_decay_rate": "Recent community activity decline pressure.",
}


def apply_theme() -> None:
    """Install the TechPulse terminal visual system."""
    st.markdown(
        """
        <style>
        :root {
            --tp-bg: #05070b;
            --tp-panel: #0b1116;
            --tp-panel-2: #101922;
            --tp-border: #1c7f4a;
            --tp-green: #00ff66;
            --tp-cyan: #00d9ff;
            --tp-purple: #bf66ff;
            --tp-pink: #ff3d9a;
            --tp-text: #e6fff1;
            --tp-muted: #8fb7a1;
            --tp-warn: #ffc857;
            --tp-danger: #ff5c7a;
        }
        .stApp {
            background:
                radial-gradient(circle at 20% 0%, rgba(0, 217, 255, 0.08), transparent 28rem),
                linear-gradient(180deg, #05070b 0%, #07100c 100%);
            color: var(--tp-text);
            font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
        }
        section[data-testid="stSidebar"] {
            background: #060b0f;
            border-right: 1px solid rgba(0, 255, 102, 0.28);
        }
        section[data-testid="stSidebar"] * { color: #d9ffe7; }
        h1, h2, h3 {
            color: var(--tp-green);
            letter-spacing: 0;
        }
        p, li, span, label { color: #d9ffe7; }
        .tp-hero {
            border: 1px solid rgba(0, 255, 102, 0.35);
            background: linear-gradient(135deg, rgba(0, 255, 102, 0.10), rgba(0, 217, 255, 0.05));
            padding: 1.2rem 1.4rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .tp-kicker { color: var(--tp-cyan); font-size: 0.78rem; text-transform: uppercase; }
        .tp-title { color: var(--tp-green); font-size: 2rem; font-weight: 800; line-height: 1.1; }
        .tp-subtitle { color: #bfe8d0; max-width: 64rem; }
        .tp-card {
            border: 1px solid rgba(0, 255, 102, 0.24);
            background: rgba(9, 16, 22, 0.92);
            padding: 1rem;
            border-radius: 8px;
            min-height: 6.4rem;
            box-shadow: 0 0 0 1px rgba(0,0,0,0.25);
        }
        .tp-card:hover { border-color: rgba(0, 217, 255, 0.46); }
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
        .tp-online { color: var(--tp-green); }
        .tp-dev { color: var(--tp-warn); }
        .tp-risk-high { color: var(--tp-danger); }
        .tp-risk-med { color: var(--tp-warn); }
        .tp-risk-low { color: var(--tp-green); }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(0, 255, 102, 0.24);
            border-radius: 8px;
        }
        .stButton button, .stDownloadButton button {
            background: #0b1512;
            border: 1px solid rgba(0, 255, 102, 0.7);
            color: var(--tp-green);
            border-radius: 6px;
            font-weight: 700;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            border-color: rgba(0, 255, 102, 0.45);
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
    st.sidebar.markdown("## TECHPULSE")
    st.sidebar.markdown("Technology Intelligence Platform")
    st.sidebar.markdown("---")
    st.sidebar.markdown("⌂ COMMAND CENTER")
    st.sidebar.markdown("◉ TECHNOLOGY EXPLORER")
    st.sidebar.markdown("◈ GLOBAL RANKINGS")
    st.sidebar.markdown("◫ MODEL LABORATORY")
    st.sidebar.markdown("⚙ ABOUT / METHODOLOGY")
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
