"""Technology detail panel for TechPulse dashboard."""

from __future__ import annotations

import json

import joblib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.enterprise_heatmap import enterprise_heatmap
from dashboard.components.shap_viewer import load_prediction_shap, shap_bar, shap_summary_sentence
from dashboard.components.trend_charts import adoption_chart, sentiment_chart, so_volume_chart
from src.common import BASE_DIR, DISCLAIMER, FEATURE_COLUMNS, LABELS, OUTPUTS_DIR

LABEL_COLOURS = {"Growing": "#2E9E6B", "Stable": "#F4B942", "Declining": "#D94F3D"}


def risk_score(probabilities: dict[str, float]) -> int:
    """Compute decline risk from Growing probability.

    Args:
        probabilities: Label probability mapping.

    Returns:
        Integer risk score from 0 to 100.
    """
    return int((1 - probabilities.get("Growing", 0.0)) * 100)


def confidence_level(probabilities: dict[str, float]) -> str:
    """Compute confidence bucket from max class probability.

    Args:
        probabilities: Label probability mapping.

    Returns:
        Confidence label.
    """
    max_probability = max(probabilities.values()) if probabilities else 0
    if max_probability < 0.6:
        return "Low Confidence"
    if max_probability < 0.8:
        return "Medium Confidence"
    return "High Confidence"


def trajectory_badge(label: str) -> str:
    """Return accessible HTML for a trajectory badge.

    Args:
        label: Trajectory label.

    Returns:
        HTML badge string.
    """
    colour = LABEL_COLOURS.get(label, "#444444")
    return (
        f"<span style='background:{colour};color:#111;padding:0.25rem 0.5rem;"
        f"border-radius:4px;font-weight:700'>{label}</span>"
    )


def _model_probabilities(row: pd.Series) -> dict[str, float]:
    """Predict class probabilities for one feature row.

    Args:
        row: Feature row.

    Returns:
        Label probability mapping.
    """
    selection_path = OUTPUTS_DIR / "best_model_selection.json"
    if not selection_path.exists():
        label = row.get("trajectory_label", "Stable")
        return {name: 1.0 if name == label else 0.0 for name in LABELS}
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    artifact = joblib.load(selection["file_path"])
    feature_row = pd.DataFrame([row[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")])
    transformed = pd.DataFrame(artifact["imputer"].transform(feature_row), columns=FEATURE_COLUMNS)
    if selection["selected_model"] == "xgboost":
        transformed = transformed.astype("float32")
    probabilities = artifact["model"].predict_proba(transformed)[0]
    return dict(zip(LABELS, probabilities))


def _placeholder_trend(row: pd.Series) -> pd.DataFrame:
    """Build placeholder trend data when raw time series are unavailable.

    Args:
        row: Selected feature row.

    Returns:
        Trend DataFrame.
    """
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=3, freq="MS").strftime("%Y-%m-%d"),
            "value": [
                max(float(row.get("growth_momentum_index", 0.5)) * 60, 0),
                max(float(row.get("technology_health_score", 0.5)) * 80, 0),
                max((1 - float(row.get("community_decay_rate", 0.5))) * 100, 0),
            ],
        }
    )


def render_detail_panel(row: pd.Series) -> None:
    """Render detail tabs for a selected technology.

    Args:
        row: Selected feature row.

    Returns:
        None.
    """
    st.info(DISCLAIMER)
    technology = str(row.get("technology_name", "Unknown"))
    label = str(row.get("trajectory_label", "Stable"))
    probabilities = _model_probabilities(row)
    score = risk_score(probabilities)
    confidence = confidence_level(probabilities)
    st.subheader(technology)
    tabs = st.tabs(["Overview", "Trends", "SHAP Analysis", "Enterprise Adoption"])
    with tabs[0]:
        st.markdown(trajectory_badge(label), unsafe_allow_html=True)
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": LABEL_COLOURS.get(label)}},
                title={"text": "Risk Score"},
            )
        )
        st.plotly_chart(gauge, use_container_width=True)
        st.metric("Confidence", confidence)
        st.dataframe(row[FEATURE_COLUMNS].to_frame("Value"), use_container_width=True)
        st.caption("Data recency follows the latest date available in the source tables.")
    with tabs[1]:
        trend = _placeholder_trend(row)
        for title, chart_fn in [
            ("Monthly SO question volume", so_volume_chart),
            ("Developer sentiment score", sentiment_chart),
            ("Company adoption count", adoption_chart),
        ]:
            st.markdown(f"**{title}**")
            fig = chart_fn(trend)
            if fig is None:
                st.info("Insufficient data to plot trend for this signal")
            else:
                st.plotly_chart(fig, use_container_width=True)
    with tabs[2]:
        values = load_prediction_shap(OUTPUTS_DIR / "shap_per_prediction.json", technology)
        st.plotly_chart(shap_bar(values), use_container_width=True)
        st.write(shap_summary_sentence(values, label, technology))
    with tabs[3]:
        heatmap_data = pd.DataFrame({"sector": ["Technology"], "adoption_count": [row.get("company_diversity_score", 0)]})
        fig = enterprise_heatmap(heatmap_data)
        if fig is None:
            st.info("No Fortune 500 adoption data available for this technology")
        elif heatmap_data["adoption_count"].sum() < 3:
            st.write("Fewer than 3 adopting companies are available for this technology.")
        else:
            st.plotly_chart(fig, use_container_width=True)
