"""SHAP explainability generation for TechPulse."""

from __future__ import annotations

import json
import logging
from datetime import datetime

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.common import FEATURE_COLUMNS, MODELS_DIR, OUTPUTS_DIR, RANDOM_STATE, TECH_COLUMN, ensure_directories

LOGGER = logging.getLogger(__name__)


def _load_selection() -> dict[str, str]:
    """Load best-model metadata.

    Returns:
        Best model selection dictionary.
    """
    return json.loads((OUTPUTS_DIR / "best_model_selection.json").read_text(encoding="utf-8"))


def _coerce_values(values: object) -> np.ndarray:
    """Coerce SHAP values from model-specific formats into an array.

    Args:
        values: SHAP values returned by an explainer.

    Returns:
        SHAP values as an ndarray.
    """
    if isinstance(values, list):
        return np.mean(np.abs(np.stack(values)), axis=0)
    array = np.asarray(values)
    if array.ndim == 3:
        return np.mean(np.abs(array), axis=2)
    return array


def run_shap_analysis() -> pd.DataFrame:
    """Compute SHAP values for the selected model on the training split only.

    Returns:
        Global feature importance DataFrame.
    """
    ensure_directories()
    selection = _load_selection()
    model_name = selection["selected_model"]
    artifact = joblib.load(selection["file_path"])
    X_train = pd.DataFrame(
        artifact["imputer"].transform(artifact["X_train"]),
        columns=FEATURE_COLUMNS,
    )
    if len(X_train) > 500:
        LOGGER.warning("SHAP input capped at 500 training samples for runtime control.")
        X_train = X_train.sample(500, random_state=RANDOM_STATE)
    model = artifact["model"]
    if model_name in {"random_forest", "xgboost"}:
        explainer = shap.TreeExplainer(model)
    elif model_name == "logistic_regression":
        explainer = shap.LinearExplainer(model, X_train)
    else:
        LOGGER.warning("Falling back to KernelExplainer for %s.", model_name)
        explainer = shap.KernelExplainer(model.predict_proba, shap.sample(X_train, min(50, len(X_train)), random_state=RANDOM_STATE))

    values = explainer.shap_values(X_train.astype("float32") if model_name == "xgboost" else X_train)
    shap_values = _coerce_values(values)
    np.save(OUTPUTS_DIR / "shap_values.npy", shap_values)
    joblib.dump(explainer, MODELS_DIR / f"shap_explainer_{datetime.now().strftime('%Y%m%d')}.joblib")
    importance = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "mean_abs_shap": np.mean(np.abs(shap_values), axis=0),
        }
    ).sort_values("mean_abs_shap", ascending=False)
    importance.to_csv(OUTPUTS_DIR / "global_feature_importance.csv", index=False)

    representative = []
    raw_train = artifact["X_train"].copy()
    for index in list(raw_train.index[:20]):
        values_for_row = shap_values[list(raw_train.index).index(index)].tolist()
        representative.append(
            {
                TECH_COLUMN: str(index),
                "feature_shap_values": dict(zip(FEATURE_COLUMNS, values_for_row)),
            }
        )
    (OUTPUTS_DIR / "shap_per_prediction.json").write_text(json.dumps(representative, indent=2), encoding="utf-8")

    shap.summary_plot(shap_values, X_train, show=False)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "shap_summary_beeswarm.png", dpi=150)
    plt.close()
    shap.summary_plot(shap_values, X_train, plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "shap_bar_chart.png", dpi=150)
    plt.close()
    return importance
