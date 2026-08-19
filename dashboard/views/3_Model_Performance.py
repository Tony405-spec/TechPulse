"""Model performance dashboard page."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import OUTPUTS_DIR  # noqa: E402
from dashboard.components.ui import disclaimer_panel, metric_card, render_shell  # noqa: E402


@st.cache_data
def load_comparison() -> pd.DataFrame:
    """Load model comparison metrics.

    Returns:
        Comparison DataFrame.
    """
    path = OUTPUTS_DIR / "model_comparison.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    for column in ["Accuracy", "Weighted_F1", "Precision", "Recall", "Macro_ROC_AUC"]:
        if column in frame:
            frame[column] = frame[column].round(4)
    return frame


render_shell(
    "Model Laboratory",
    "Four classifiers evaluated using held-out test metrics and weighted F1 model selection.",
    "MODEL PERFORMANCE",
)
disclaimer_panel()
comparison = load_comparison()
if comparison.empty:
    st.warning("No model comparison found. Run the pipeline first.")
else:
    selection_path = OUTPUTS_DIR / "best_model_selection.json"
    if selection_path.exists():
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        selected_model = selection["selected_model"]
        selected_row = comparison.loc[comparison["Model"] == selected_model].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Champion Model", selected_model.replace("_", " ").title(), "Selected by Weighted F1")
        with c2:
            metric_card("Weighted F1", f"{selected_row.get('Weighted_F1', 0):.4f}", "Primary metric")
        with c3:
            metric_card("Accuracy", f"{selected_row.get('Accuracy', 0):.4f}", "Held-out split")
        with c4:
            metric_card("Models Evaluated", "4", "LR · KNN · RF · XGBoost")
        st.caption(selection["reason"])
    st.subheader("Model Comparison")
    st.dataframe(
        comparison.style.apply(
            lambda row: ["background-color: #123923; color: #e6fff1" if row.get("Status") == "Selected" else "" for _ in row],
            axis=1,
        ),
        use_container_width=True,
        hide_index=True,
    )
    if selection_path.exists():
        cm_path = OUTPUTS_DIR / f"cm_{selection['selected_model']}.png"
        if cm_path.exists():
            st.subheader("Best Model — Confusion Matrix")
            st.image(str(cm_path), caption="Held-out test confusion matrix")
    st.subheader("Pipeline Transparency")
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1:
        metric_card("Data Sources", "6", "Expected warehouse tables")
    with p2:
        metric_card("Features", "7", "Predictive signals")
    with p3:
        metric_card("Classes", "3", "Growing · Stable · Declining")
    with p4:
        metric_card("Cross Validation", "5-fold", "Reduced only for tiny demo splits")
    with p5:
        metric_card("Train / Test", "80 / 20", "Stratified split")
    for title, body in {
        "What is Weighted F1?": "A balance of precision and recall that accounts for class frequency. TechPulse uses it as the primary selection metric because technology classes may be imbalanced.",
        "What is Precision?": "Precision asks: when the model predicts a class, how often is that prediction correct?",
        "What is Recall?": "Recall asks: of all actual examples in a class, how many did the model find?",
        "What is ROC-AUC?": "ROC-AUC measures how well probability scores rank classes. It may be unavailable when a small test split lacks one class.",
        "Why not select by accuracy only?": "Accuracy can look strong on imbalanced data while hiding weak minority-class performance. Weighted F1 is more informative for this project.",
    }.items():
        with st.expander(title):
            st.write(body)
