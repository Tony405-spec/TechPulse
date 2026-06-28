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

from src.common import DISCLAIMER, OUTPUTS_DIR  # noqa: E402


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
    for column in ["Accuracy", "Weighted_F1", "Macro_ROC_AUC"]:
        if column in frame:
            frame[column] = frame[column].round(4)
    return frame


st.title("Model Performance")
st.info(DISCLAIMER)
comparison = load_comparison()
if comparison.empty:
    st.warning("No model comparison found. Run the pipeline first.")
else:
    st.dataframe(
        comparison.style.apply(
            lambda row: ["background-color: #D1FAE5" if row.get("Status") == "Selected" else "" for _ in row],
            axis=1,
        ),
        use_container_width=True,
        hide_index=True,
    )
    selection_path = OUTPUTS_DIR / "best_model_selection.json"
    if selection_path.exists():
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        st.success(f"Selected model: {selection['selected_model']} because {selection['reason']}")
        cm_path = OUTPUTS_DIR / f"cm_{selection['selected_model']}.png"
        if cm_path.exists():
            st.image(str(cm_path), caption="Best model confusion matrix")
    st.markdown(
        """
        **Accuracy** is the share of held-out predictions that were correct.
        **Weighted F1** balances precision and recall while respecting class frequency.
        **Macro ROC-AUC** measures ranking quality across classes with equal class weight.
        """
    )
