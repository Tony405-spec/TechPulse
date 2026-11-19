"""Held-out model evaluation and best-model selection for TechPulse."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import hashlib
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import label_binarize

from src.common import (
    DATA_DIR,
    FEATURE_COLUMNS,
    LABELS,
    MODELS_DIR,
    OUTPUTS_DIR,
    TECH_COLUMN,
    ensure_directories,
)

plt.switch_backend("Agg")


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
        lines.append(
            "| " + " | ".join(str(row[column]) for column in frame.columns) + " |"
        )
    return "\n".join(lines)


def _latest_model_paths() -> dict[str, Path]:
    """Find the latest artifact for each model.

    Returns:
        Mapping of model names to paths.
    """
    paths: dict[str, Path] = {}
    for path in sorted(
        MODELS_DIR.rglob("techpulse_*_*.joblib"),
        key=lambda item: item.stat().st_mtime_ns,
    ):
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
        probabilities = model.predict_proba(X)
        if probabilities.shape[1] == len(LABELS):
            return probabilities
        model_classes = getattr(model, "classes_", np.arange(probabilities.shape[1]))
        expanded = np.zeros((len(probabilities), len(LABELS)))
        for source_index, class_id in enumerate(model_classes):
            expanded[:, int(class_id)] = probabilities[:, source_index]
        return expanded
    predictions = model.predict(X)
    proba = np.zeros((len(predictions), len(LABELS)))
    proba[np.arange(len(predictions)), predictions] = 1
    return proba


def _metric_row(
    name: str,
    y_test: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray | None,
    status: str = "Candidate",
) -> tuple[dict[str, object], list[str]]:
    """Build one metrics row and warnings for invalid metrics."""
    warnings: list[str] = []
    present_classes = set(np.unique(y_test).tolist())
    roc_auc = np.nan
    if probabilities is not None and present_classes == {0, 1, 2}:
        try:
            roc_auc = roc_auc_score(
                label_binarize(y_test, classes=[0, 1, 2]),
                probabilities,
                average="macro",
                multi_class="ovr",
            )
        except ValueError as exc:
            warnings.append(f"{name}: ROC-AUC unavailable ({exc}).")
    else:
        warnings.append(
            f"{name}: ROC-AUC not statistically meaningful because the test split lacks all classes."
        )
    return (
        {
            "Model": name,
            "Accuracy": accuracy_score(y_test, predictions),
            "Weighted_F1": f1_score(
                y_test, predictions, average="weighted", zero_division=0
            ),
            "Precision": precision_score(
                y_test, predictions, average="weighted", zero_division=0
            ),
            "Recall": recall_score(
                y_test, predictions, average="weighted", zero_division=0
            ),
            "Macro_ROC_AUC": roc_auc,
            "Status": status,
        },
        warnings,
    )


def _plot_confusion(
    name: str, y_test: np.ndarray, predictions: np.ndarray, output_dir: Path
) -> None:
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
    plt.savefig(output_dir / f"cm_{name}.png", dpi=150)
    plt.close()


def _plot_roc(
    name: str, y_test: np.ndarray, probabilities: np.ndarray, output_dir: Path
) -> None:
    """Write a macro ROC curve PNG.

    Args:
        name: Model name.
        y_test: True labels.
        probabilities: Predicted probabilities.
    """
    y_bin = label_binarize(y_test, classes=[0, 1, 2])
    plt.figure(figsize=(7, 5))
    for index, label in enumerate(LABELS):
        if y_bin[:, index].sum() == 0:
            continue
        fpr, tpr, _ = roc_curve(y_bin[:, index], probabilities[:, index])
        plt.plot(fpr, tpr, label=label)
    plt.plot([0, 1], [0, 1], linestyle="--", color="#555555")
    plt.title(f"{name} ROC Curves")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / f"roc_{name}.png", dpi=150)
    plt.close()


def compare_and_select_best_model(
    model_paths: dict[str, Path] | None = None,
) -> pd.DataFrame:
    """Evaluate all serialized models on their held-out test set only.

    Args:
        model_paths: Optional mapping of model names to artifact paths.

    Returns:
        Model comparison DataFrame.
    """
    ensure_directories()
    model_paths = model_paths or _latest_model_paths()
    run_id = (
        next(iter(model_paths.values())).parent.name
        if model_paths
        else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    run_dir = OUTPUTS_DIR / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    artifacts: dict[str, dict] = {}
    warnings_out: list[str] = []
    split_metadata: dict[str, object] = {}
    class_reports: dict[str, object] = {}
    for name, path in model_paths.items():
        artifact = joblib.load(path)
        artifacts[name] = artifact
        split_metadata = artifact.get("split_metadata", split_metadata)
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
        _plot_confusion(name, y_test, predictions, run_dir)
        class_reports[name] = classification_report(
            y_test,
            predictions,
            labels=[0, 1, 2],
            target_names=LABELS,
            output_dict=True,
            zero_division=0,
        )
        if name in {"random_forest", "xgboost"} and set(np.unique(y_test).tolist()) == {
            0,
            1,
            2,
        }:
            _plot_roc(name, y_test, probabilities, run_dir)
        row, metric_warnings = _metric_row(name, y_test, predictions, probabilities)
        row["Path"] = str(path)
        rows.append(row)
        warnings_out.extend(metric_warnings)

    if artifacts:
        reference = next(iter(artifacts.values()))
        y_train = reference["y_train"]
        y_test = reference["y_test"]
        majority = int(pd.Series(y_train).mode().iloc[0])
        majority_predictions = np.repeat(majority, len(y_test))
        row, metric_warnings = _metric_row(
            "baseline_majority_class", y_test, majority_predictions, None
        )
        class_reports["baseline_majority_class"] = classification_report(
            y_test,
            majority_predictions,
            labels=[0, 1, 2],
            target_names=LABELS,
            output_dict=True,
            zero_division=0,
        )
        rows.append(row)
        warnings_out.extend(metric_warnings)
        if "growth_momentum_index" in reference["X_test"]:
            momentum_values = pd.to_numeric(
                reference["X_test"]["growth_momentum_index"], errors="coerce"
            ).fillna(0.5)
            momentum_predictions = np.where(
                momentum_values >= 0.65, 0, np.where(momentum_values <= 0.35, 2, 1)
            )
            row, metric_warnings = _metric_row(
                "baseline_momentum_rule", y_test, momentum_predictions, None
            )
            class_reports["baseline_momentum_rule"] = classification_report(
                y_test,
                momentum_predictions,
                labels=[0, 1, 2],
                target_names=LABELS,
                output_dict=True,
                zero_division=0,
            )
            rows.append(row)
            warnings_out.extend(metric_warnings)

    comparison = pd.DataFrame(rows)
    comparison["_xgb_priority"] = (comparison["Model"] == "xgboost").astype(int)
    comparison["_baseline_penalty"] = (
        comparison["Model"].astype(str).str.startswith("baseline_").astype(int)
    )
    comparison = comparison.sort_values(
        ["_baseline_penalty", "Weighted_F1", "Macro_ROC_AUC", "_xgb_priority"],
        ascending=[True, False, False, False],
        na_position="last",
    )
    selectable = comparison[
        ~comparison["Model"].astype(str).str.startswith("baseline_")
    ]
    best = (
        selectable.iloc[0].copy() if not selectable.empty else comparison.iloc[0].copy()
    )
    comparison.loc[comparison["Model"] == best["Model"], "Status"] = "Selected"
    public = comparison.drop(
        columns=["_xgb_priority", "_baseline_penalty", "Path"], errors="ignore"
    )
    public.to_csv(run_dir / "model_comparison.csv", index=False)
    (run_dir / "model_comparison.md").write_text(
        _to_markdown_table(public), encoding="utf-8"
    )
    reason = (
        "Selected from trainable ML models using Weighted_F1; baselines are reported for context. "
        "Metrics with missing classes are marked with NaN ROC-AUC and warnings."
    )
    (run_dir / "best_model_selection.json").write_text(
        json.dumps(
            {
                "selected_model": best["Model"],
                "file_path": best["Path"],
                "reason": reason,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    evaluation_summary = {
        "split_metadata": split_metadata,
        "warnings": sorted(set(warnings_out)),
        "per_class_metrics": class_reports,
        "probability_calibration": "not independently calibrated; probability maxima must not be described as calibrated confidence",
        "is_multiclass_test_valid": split_metadata.get("test_class_counts", {})
        and len(split_metadata.get("test_class_counts", {})) == len(LABELS),
    }
    (run_dir / "evaluation_summary.json").write_text(
        json.dumps(evaluation_summary, indent=2), encoding="utf-8"
    )
    artifact_path = MODELS_DIR / "runs" / run_id / "best_model.joblib"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifacts[str(best["Model"])], artifact_path)
    _write_dashboard_predictions(
        artifacts[str(best["Model"])],
        str(best["Model"]),
        run_dir / "technology_predictions.csv",
    )
    feature_path = DATA_DIR / "feature_matrix.csv"
    reference = next(iter(artifacts.values()), {})
    members = reference.get("train_technologies", []) + reference.get(
        "test_technologies", []
    )
    synthetic_fixture = bool(members) and all(
        str(value).startswith(("Growing_", "Stable_", "Declining_", "tech-"))
        for value in members
    )
    metadata = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_version": None,
        "code_version_note": "not available because repository has no .git metadata",
        "config_hash": None,
        "dataset_snapshot": (
            hashlib.sha256(feature_path.read_bytes()).hexdigest()
            if feature_path.exists()
            else None
        ),
        "feature_list": FEATURE_COLUMNS,
        "label_definition": "Future-window question activity / recent-window activity; see docs/MODEL_METHODOLOGY.md",
        "split_metadata": split_metadata,
        "artifact_path": str(artifact_path.relative_to(OUTPUTS_DIR.parent)),
        "artifact_checksum": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "metrics_path": "model_comparison.csv",
        "auditable": bool(
            split_metadata.get("split_strategy") == "chronological_holdout"
            and not synthetic_fixture
        ),
        "synthetic_fixture": synthetic_fixture,
    }
    (run_dir / "model_run.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    # First-run compatibility outputs are written only when absent; historical
    # artifacts are never overwritten by a later run.
    compatibility = {
        "model_comparison.csv": run_dir / "model_comparison.csv",
        "model_comparison.md": run_dir / "model_comparison.md",
        "best_model_selection.json": run_dir / "best_model_selection.json",
        "evaluation_summary.json": run_dir / "evaluation_summary.json",
    }
    for filename, source in compatibility.items():
        destination = OUTPUTS_DIR / filename
        if not destination.exists():
            destination.write_bytes(source.read_bytes())
    return public


def _write_dashboard_predictions(
    artifact: dict, model_name: str, output_path: Path
) -> None:
    """Persist technology-level predictions used by Streamlit pages."""
    feature_path = DATA_DIR / "feature_matrix.csv"
    if not feature_path.exists():
        return
    frame = pd.read_csv(feature_path)
    if not set(FEATURE_COLUMNS).issubset(frame.columns):
        return
    X = pd.DataFrame(
        artifact["imputer"].transform(frame[FEATURE_COLUMNS]), columns=FEATURE_COLUMNS
    )
    if model_name == "xgboost":
        X = X.astype("float32")
    model = artifact["model"]
    probabilities = _predict_proba(model, X)
    encoded_predictions = model.predict(X)
    labels = artifact["label_encoder"].inverse_transform(encoded_predictions)
    output = frame.copy()
    output["predicted_label"] = labels
    for index, label in enumerate(LABELS):
        output[f"prob_{label}"] = probabilities[:, index]
    output["risk_score"] = ((1 - output["prob_Growing"]) * 100).round(2)
    output["confidence"] = probabilities.max(axis=1).round(4)
    output["confidence_level"] = output["confidence"].map(
        lambda value: "Low" if value < 0.60 else "Medium" if value <= 0.80 else "High"
    )
    if TECH_COLUMN not in output:
        output[TECH_COLUMN] = output.index.astype(str)
    output.to_csv(output_path, index=False)
