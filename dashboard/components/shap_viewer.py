"""SHAP chart components for the TechPulse dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px

from src.common import FEATURE_COLUMNS


def load_prediction_shap(path: Path, technology: str) -> dict[str, float]:
    """Load precomputed SHAP values for a technology if available.

    Args:
        path: JSON file path.
        technology: Technology name.

    Returns:
        Mapping of feature names to SHAP values.
    """
    if not path.exists():
        return {feature: 0.0 for feature in FEATURE_COLUMNS}
    records = json.loads(path.read_text(encoding="utf-8"))
    for record in records:
        if record.get("technology_name") == technology:
            return record.get("feature_shap_values", {})
    return {feature: 0.0 for feature in FEATURE_COLUMNS}


def shap_bar(values: dict[str, float]):
    """Create a horizontal SHAP contribution bar chart.

    Args:
        values: Feature to SHAP value mapping.

    Returns:
        Plotly figure.
    """
    frame = pd.DataFrame({"Feature": list(values), "SHAP": list(values.values())})
    frame["Direction"] = frame["SHAP"].apply(lambda value: "Risk-increasing" if value > 0 else "Risk-reducing")
    fig = px.bar(
        frame.sort_values("SHAP"),
        x="SHAP",
        y="Feature",
        orientation="h",
        color="Direction",
        color_discrete_map={"Risk-increasing": "#D94F3D", "Risk-reducing": "#2B6CB0"},
    )
    fig.add_vline(x=0, line_color="#111111")
    return fig


def shap_summary_sentence(values: dict[str, float], label: str, technology: str) -> str:
    """Create a plain-English SHAP summary sentence.

    Args:
        values: Feature to SHAP value mapping.
        label: Predicted trajectory label.
        technology: Technology name.

    Returns:
        Summary sentence.
    """
    strongest = max(values, key=lambda key: abs(values[key])) if values else "No feature"
    return f"{strongest} is the strongest indicator driving the {label} prediction for {technology}."
