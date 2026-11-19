"""Shared TechPulse dashboard presentation components."""

from __future__ import annotations

import streamlit as st

from src.common import DISCLAIMER

FEATURE_DESCRIPTIONS = {
    "technology_health_score": "Composite of community momentum, answer quality, and activity persistence.",
    "growth_momentum_index": "Recent question volume compared with the trailing activity window.",
    "question_quality_score": "Answer availability adjusted for closure or unresolved-question pressure.",
    "community_decay_rate": "Recent community activity decline pressure.",
}


def apply_theme() -> None:
    """Install the TechPulse charcoal, linen, and oxblood visual system."""
    st.markdown(
        """
        <style>
        :root {
            --tp-bg: #171615;
            --tp-panel: #211F1E;
            --tp-panel-2: #2A2725;
            --tp-border: #49413E;
            --tp-green: #EAE4DF;
            --tp-cyan: #C0A9A1;
            --tp-purple: #9C6872;
            --tp-pink: #A34A5A;
            --tp-text: #EAE4DF;
            --tp-muted: #B4AAA4;
            --tp-warn: #C3A871;
            --tp-danger: #C4787F;
        }
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: #171615 !important;
            color: var(--tp-text);
            font-family: "Segoe UI", Arial, sans-serif;
            color-scheme: dark;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"] { background: #171615 !important; color: #EAE4DF !important; }
        [data-testid="stMain"], [data-testid="stMainBlockContainer"] { background: #171615 !important; }
        section[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background: #201E1D !important;
            border-right: 1px solid #49413E;
        }
        section[data-testid="stSidebar"] * { color: #EAE4DF; }
        h1, h2, h3 {
            color: var(--tp-green) !important;
            letter-spacing: 0;
        }
        p, li, span, label { color: #EAE4DF; }
        .tp-hero {
            border: 1px solid #49413E;
            background: #211F1E;
            padding: 1.2rem 1.4rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        .tp-kicker { color: #C0A9A1; font-size: 0.76rem; text-transform: uppercase; letter-spacing: .12em; }
        .tp-title { color: var(--tp-green); font-size: 2rem; font-weight: 800; line-height: 1.1; }
        .tp-subtitle { color: #B4AAA4; max-width: 64rem; margin-top: .4rem; }
        .tp-card {
            border: 1px solid #49413E;
            background: #211F1E;
            padding: 1rem;
            border-radius: 10px;
            min-height: 6.4rem;
            box-shadow: none;
        }
        .tp-card:hover { border-color: #A34A5A; }
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
        .tp-online { color: #9EC5A5; }
        .tp-dev { color: var(--tp-warn); }
        .tp-risk-high { color: var(--tp-danger); }
        .tp-risk-med { color: var(--tp-warn); }
        .tp-risk-low { color: #9EC5A5; }
        .stApp, [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] { color: #EAE4DF; }
        [data-testid="stDataFrame"], [data-testid="stTable"] { background: #211F1E; }
        .stButton button, .stDownloadButton button { background: #762E3D; color: #fff; border-color: #A34A5A; }
        .stButton button:hover, .stDownloadButton button:hover { background: #913B4C; color: #fff; border-color: #C4787F; }
        input, textarea, [data-baseweb="select"] > div { background: #282523 !important; color: #EAE4DF !important; }
        [role="option"], [role="listbox"] { background: #282523 !important; color: #EAE4DF !important; }
        [data-testid="stAlert"] { color: #EAE4DF; }
        div[data-testid="stDataFrame"] {
            border: 1px solid #49413E;
            border-radius: 10px;
        }
        .stButton button, .stDownloadButton button {
            background: #762E3D;
            border: 1px solid #A34A5A;
            color: #ffffff;
            border-radius: 8px;
            font-weight: 700;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            border-color: #49413E;
        }
        [data-testid="stMetric"] { background: #211F1E; border: 1px solid #49413E; padding: .8rem; border-radius: 10px; }
        [data-testid="stPlotlyChart"] { background: #211F1E; border: 1px solid #49413E; border-radius: 10px; }
        [data-testid="stDataFrame"] iframe { color-scheme: dark; }
        [aria-selected="true"] { background: #762E3D !important; color: #ffffff !important; }
        [data-testid="stSidebarNav"] { background: #201E1D; }
        [data-testid="stExpander"] { border-color: #49413E; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render static product context; database health is owned by app.py."""
    st.sidebar.markdown("---")
    st.sidebar.caption("Academic research · Source-backed evidence")


def render_shell(title: str, subtitle: str, kicker: str = "TECHPULSE") -> None:
    """Render a page header and data-status badges."""
    apply_theme()
    status_badge = "POSTGRESQL · CANONICAL DATA"
    status_class = "tp-online"
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
    st.caption(
        "Research prototype · Interpret results with the source coverage and limitations shown on this page. "
        + DISCLAIMER
    )


def risk_class(score: float) -> str:
    """Return visual risk class for a score."""
    if score >= 70:
        return "tp-risk-high"
    if score >= 40:
        return "tp-risk-med"
    return "tp-risk-low"
