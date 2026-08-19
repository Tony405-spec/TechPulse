"""Home and technology search page."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.tech_detail_panel import render_detail_panel, trajectory_badge  # noqa: E402
from dashboard.components.ui import (  # noqa: E402
    FEATURE_DESCRIPTIONS,
    disclaimer_panel,
    metric_card,
    render_shell,
    risk_class,
)
from src.common import CATEGORY_COLUMN, DATA_DIR, DISCLAIMER, FEATURE_COLUMNS, LABEL_COLUMN, OUTPUTS_DIR, TECH_COLUMN  # noqa: E402


@st.cache_data
def load_features() -> pd.DataFrame:
    """Load the dashboard feature matrix.

    Returns:
        Feature matrix DataFrame.
    """
    prediction_path = OUTPUTS_DIR / "technology_predictions.csv"
    feature_path = DATA_DIR / "feature_matrix.csv"
    path = prediction_path if prediction_path.exists() else feature_path
    if not path.exists():
        return pd.DataFrame(columns=[TECH_COLUMN, CATEGORY_COLUMN, LABEL_COLUMN] + FEATURE_COLUMNS)
    return pd.read_csv(path)


def _risk(row: pd.Series) -> float:
    """Compute display risk score from feature proxies.

    Args:
        row: Feature row.

    Returns:
        Risk score.
    """
    if "risk_score" in row and pd.notna(row["risk_score"]):
        return float(row["risk_score"])
    return float((1 - float(row.get("growth_momentum_index", 0.5))) * 100)


def _confidence(row: pd.Series) -> str:
    if "confidence_level" in row and pd.notna(row["confidence_level"]):
        return str(row["confidence_level"])
    return "Unavailable"


def _probability_chart(row: pd.Series) -> go.Figure:
    probabilities = []
    for label in ["Growing", "Stable", "Declining"]:
        probabilities.append(float(row.get(f"prob_{label}", 0.0)))
    frame = pd.DataFrame({"Trajectory": ["Growing", "Stable", "Declining"], "Probability": probabilities})
    fig = px.bar(
        frame,
        x="Probability",
        y="Trajectory",
        orientation="h",
        color="Trajectory",
        color_discrete_map={"Growing": "#00ff66", "Stable": "#ffc857", "Declining": "#ff5c7a"},
        range_x=[0, 1],
        title="Class Probability Distribution",
    )
    fig.update_layout(template="plotly_dark", height=260, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def _trajectory_position(label: str) -> None:
    positions = {"Growing": 8, "Stable": 50, "Declining": 92}
    left = positions.get(label, 50)
    st.markdown(
        f"""
        <div style="position:relative;margin:1rem 0 1.4rem;padding-top:1.2rem">
          <div style="height:3px;background:linear-gradient(90deg,#00ff66,#ffc857,#ff5c7a);border-radius:99px"></div>
          <div style="position:absolute;left:{left}%;top:0;transform:translateX(-50%);color:#e6fff1;font-weight:800">▲</div>
          <div style="display:flex;justify-content:space-between;margin-top:0.35rem;color:#8fb7a1;font-size:0.84rem">
            <span>GROWING</span><span>STABLE</span><span>DECLINING</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _signal_matrix(row: pd.Series) -> None:
    st.subheader("TechPulse Signal Matrix")
    cols = st.columns(2)
    for index, feature in enumerate(FEATURE_COLUMNS):
        value = pd.to_numeric(row.get(feature), errors="coerce")
        if pd.isna(value):
            level = "Unavailable"
            display = "N/A"
        else:
            display = f"{float(value):.3f}"
            level = "High" if value >= 0.67 else "Medium" if value >= 0.34 else "Low"
        with cols[index % 2]:
            st.markdown(
                f"""
                <div class="tp-card">
                  <div class="tp-label">{feature.replace("_", " ").title()}</div>
                  <div class="tp-value">{display}</div>
                  <div class="tp-note">{level} · {FEATURE_DESCRIPTIONS.get(feature, "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _ai_interpretation(row: pd.Series, label: str, risk: float, confidence: str) -> str:
    sorted_features = (
        row[FEATURE_COLUMNS]
        .apply(pd.to_numeric, errors="coerce")
        .dropna()
        .sort_values(ascending=False)
        .head(2)
        .index.tolist()
    )
    strongest = ", ".join(feature.replace("_", " ") for feature in sorted_features) or "available signals"
    return (
        f"TechPulse estimates that {row.get(TECH_COLUMN, 'this technology')} is in a "
        f"{label} trajectory. The model associates the current prediction with strongest "
        f"available signals in {strongest}. Estimated decline risk is {risk:.1f}/100, "
        f"with {confidence.lower()} confidence."
    )


render_shell(
    "Technology Intelligence",
    "Detecting growth, stability, and decline before technology risk becomes expensive.",
    "COMMAND CENTER",
)
disclaimer_panel()
with st.spinner("Initializing TechPulse... Loading model, feature matrix, technology index, and analytics."):
    data = load_features()
if data.empty:
    st.error("NO DATA AVAILABLE. Run `python pipeline/run_pipeline.py` to generate the feature matrix and predictions.")
    st.stop()
if "risk_score" not in data.columns:
    st.warning("Model predictions are unavailable. Run `python pipeline/run_pipeline.py` to calculate probability-based risk scores.")

label_column = "predicted_label" if "predicted_label" in data else LABEL_COLUMN
kpi_cols = st.columns(5)
with kpi_cols[0]:
    metric_card("Technologies Analyzed", f"{len(data):,}", "Loaded technology index")
for idx, label in enumerate(["Growing", "Stable", "Declining"], start=1):
    pct = float((data[label_column] == label).mean() * 100) if label_column in data else 0
    with kpi_cols[idx]:
        metric_card(label, f"{pct:.1f}%", "Share of predictions")
with kpi_cols[4]:
    metric_card("Avg Decline Risk", f"{data.apply(_risk, axis=1).mean():.1f}", "0=minimal, 100=maximum")

st.subheader("Search Technology")
search = st.text_input("Technology", max_chars=100, placeholder="Search or filter by technology name", label_visibility="collapsed")
category_values = sorted(data[CATEGORY_COLUMN].dropna().astype(str).unique().tolist()) if CATEGORY_COLUMN in data else []
category = st.selectbox("Category", ["All"] + category_values)
filtered = data.copy()
if search:
    filtered = filtered[filtered[TECH_COLUMN].astype(str).str.contains(search, case=False, regex=False, na=False)]
if category != "All" and CATEGORY_COLUMN in filtered:
    filtered = filtered[filtered[CATEGORY_COLUMN].astype(str).str.casefold() == category.casefold()]

if filtered.empty:
    st.warning("No technologies found")
else:
    choices = filtered[TECH_COLUMN].astype(str).tolist()
    default_index = 0
    selected = st.selectbox("Technology Explorer", choices, index=default_index)
    if selected:
        st.session_state["selected_technology"] = selected
        row = filtered.loc[filtered[TECH_COLUMN].astype(str) == selected].iloc[0]
        label = str(row.get("predicted_label", row.get(LABEL_COLUMN, "Stable")))
        risk = _risk(row)
        confidence = _confidence(row)
        st.markdown("### Predicted Trajectory")
        st.markdown(trajectory_badge(label), unsafe_allow_html=True)
        _trajectory_position(label)
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Trajectory", label, "Model classification")
        with c2:
            metric_card("Decline Risk", f"{risk:.1f}/100", "(1 - P(Growing)) × 100")
        with c3:
            metric_card("Confidence", confidence, "Max class probability")
        st.plotly_chart(_probability_chart(row), use_container_width=True)
        st.markdown(
            f"""
            <div class="tp-card">
              <div class="tp-label">AI Interpretation</div>
              <div class="tp-note">{_ai_interpretation(row, label, risk, confidence)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _signal_matrix(row)
        render_detail_panel(row)
