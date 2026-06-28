"""Held-out model evaluation and best-model selection for TechPulse."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score, roc_auc_score, roc_curve
from sklearn.preprocessing import label_binarize

from src.common import FEATURE_COLUMNS, LABELS, MODELS_DIR, OUTPUTS_DIR, ensure_directories


def _to_markdown_table(frame: pd.DataFrame) -> str:
    """Render a DataFrame as a Markdown table without optional dependencies.

    Args:
        frame: DataFrame to render.

    Returns:
        Markdown table text.
    """
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in frame.columns) + " |")
    return "\n".join(lines)


def _latest_model_paths() -> dict[str, Path]:
    """Find the latest artifact for each model.

    Returns:
        Mapping of model names to paths.
    """
    paths: dict[str, Path] = {}
    for path in sorted(MODELS_DIR.glob("techpulse_*_*.joblib")):
        name = path.stem.replace("techpulse_", "").rsplit("_", 1)[0]
        paths[name] = path
    return paths


def _predict_proba(model: object, X: pd.DataFrame) -> np.ndarray:
    """Return class probabilities when supported.

    Args:
        model: Fitted estimator.
        X: Test features.

    Returns:
        Probability matrix.
    """
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)
    predictions = model.predict(X)
    proba = np.zeros((len(predictions), len(LABELS)))
    proba[np.arange(len(predictions)), predictions] = 1
    return proba


def _plot_confusion(name: str, y_test: np.ndarray, predictions: np.ndarray) -> None:
    """Write a confusion matrix PNG.

    Args:
        name: Model name.
        y_test: True labels.
        predictions: Predicted labels.
    """
    cm = confusion_matrix(y_test, predictions, labels=[0, 1, 2])
    display = ConfusionMatrixDisplay(cm, display_labels=LABELS)
    display.plot(cmap="Greens", colorbar=False)
    plt.title(f"{name} Confusion Matrix")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / f"cm_{name}.png", dpi=150)
    plt.close()


def _plot_roc(name: str, y_test: np.ndarray, probabilities: np.ndarray) -> None:
    """Write a macro ROC curve PNG.

    Args:
        name: Model name.
        y_test: True labels.
        probabilities: Predicted probabilities.
    """
    y_bin = label_binarize(y_test, classes=[0, 1, 2])
    plt.figure(figsize=(7, 5))
    for index, label in enumerate(LABELS):
        fpr, tpr, _ = roc_curve(y_bin[:, index], probabilities[:, index])
        plt.plot(fpr, tpr, label=label)
    plt.plot([0, 1], [0, 1], linestyle="--", color="#555555")
    plt.title(f"{name} ROC Curves")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / f"roc_{name}.png", dpi=150)
    plt.close()


def compare_and_select_best_model(model_paths: dict[str, Path] | None = None) -> pd.DataFrame:
    """Evaluate all serialized models on their held-out test set only.

    Args:
        model_paths: Optional mapping of model names to artifact paths.

    Returns:
        Model comparison DataFrame.
    """
    ensure_directories()
    model_paths = model_paths or _latest_model_paths()
    rows: list[dict[str, object]] = []
    artifacts: dict[str, dict] = {}
    for name, path in model_paths.items():
        artifact = joblib.load(path)
        artifacts[name] = artifact
        X_test = pd.DataFrame(
            artifact["imputer"].transform(artifact["X_test"]),
            columns=FEATURE_COLUMNS,
        )
        if name == "xgboost":
            X_test = X_test.astype("float32")
        y_test = artifact["y_test"]
        model = artifact["model"]
        predictions = model.predict(X_test)
        probabilities = _predict_proba(model, X_test)
        try:
            roc_auc = roc_auc_score(
                label_binarize(y_test, classes=[0, 1, 2]),
                probabilities,
                average="macro",
                multi_class="ovr",
            )
        except ValueError:
            roc_auc = np.nan
        _plot_confusion(name, y_test, predictions)
        if name in {"random_forest", "xgboost"}:
            _plot_roc(name, y_test, probabilities)
        rows.append(
            {
                "Model": name,
                "Accuracy": accuracy_score(y_test, predictions),
                "Weighted_F1": f1_score(y_test, predictions, average="weighted"),
                "Macro_ROC_AUC": roc_auc,
                "Status": "Candidate",
                "Path": str(path),
            }
        )

    comparison = pd.DataFrame(rows)
    comparison["_xgb_priority"] = (comparison["Model"] == "xgboost").astype(int)
    comparison = comparison.sort_values(
        ["Weighted_F1", "Macro_ROC_AUC", "_xgb_priority"],
        ascending=[False, False, False],
        na_position="last",
    )
    best = comparison.iloc[0].copy()
    comparison.loc[comparison["Model"] == best["Model"], "Status"] = "Selected"
    public = comparison.drop(columns=["_xgb_priority", "Path"])
    public.to_csv(OUTPUTS_DIR / "model_comparison.csv", index=False)
    (OUTPUTS_DIR / "model_comparison.md").write_text(_to_markdown_table(public), encoding="utf-8")
    reason = "Highest Weighted_F1; tie broken by Macro_ROC_AUC, then XGBoost default if needed."
    (OUTPUTS_DIR / "best_model_selection.json").write_text(
        json.dumps(
            {"selected_model": best["Model"], "file_path": best["Path"], "reason": reason},
            indent=2,
        ),
        encoding="utf-8",
    )
    return public
