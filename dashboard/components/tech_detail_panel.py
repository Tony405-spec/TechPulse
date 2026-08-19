"""Technology detail panel for TechPulse dashboard."""

from __future__ import annotations

import json

import joblib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.shap_viewer import load_prediction_shap, shap_bar, shap_summary_sentence
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
    if all(f"prob_{label}" in row for label in LABELS):
        return {label: float(row[f"prob_{label}"]) for label in LABELS}
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


def render_detail_panel(row: pd.Series) -> None:
    """Render detail tabs for a selected technology.

    Args:
        row: Selected feature row.

    Returns:
        None.
    """
    st.info(DISCLAIMER)
    technology = str(row.get("technology_name", "Unknown"))
    label = str(row.get("predicted_label", row.get("trajectory_label", "Stable")))
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
        st.dataframe(
            pd.DataFrame(
                {
                    "Class": list(probabilities.keys()),
                    "Probability": [round(float(value), 4) for value in probabilities.values()],
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.dataframe(row[FEATURE_COLUMNS].to_frame("Value"), use_container_width=True)
        st.caption("Data recency follows the latest date available in the source tables.")
    with tabs[1]:
        st.info(
            "HISTORICAL DATA UNAVAILABLE. This visualization requires raw historical "
            "observations for the selected technology. Missing historical data is not "
            "interpreted as zero activity."
        )
    with tabs[2]:
        values = load_prediction_shap(OUTPUTS_DIR / "shap_per_prediction.json", technology)
        st.plotly_chart(shap_bar(values), use_container_width=True)
        st.write(shap_summary_sentence(values, label, technology))
    with tabs[3]:
        st.metric("Adoption Velocity", f"{float(row.get('adoption_velocity', 0) or 0):.3f}")
        st.metric("Company Diversity Score", f"{float(row.get('company_diversity_score', 0) or 0):.3f}")
        st.info(
            "Sector-level company details are unavailable in the current dashboard artifact. "
            "Run against the full PostgreSQL warehouse to enable richer enterprise heatmaps."
        )
