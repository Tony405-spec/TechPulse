"""Conservative model selection from persisted PostgreSQL evaluations."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

MIN_CLASS_SUPPORT = 10
REQUIRED_CLASSES = ("Growing", "Stable", "Declining")


def _cohort_key(row: pd.Series) -> tuple[str, str, str, str]:
    split = row.get("split_metadata")
    if isinstance(split, dict):
        split_value = json.dumps(split, sort_keys=True, default=str)
    else:
        split_value = str(split)
    return (
        str(row.get("dataset_snapshot")),
        str(row.get("feature_snapshot_id")),
        str(row.get("label_name")) + ":" + str(row.get("label_version")),
        split_value,
    )


def select_best_model(
    runs: pd.DataFrame, class_metrics: pd.DataFrame, min_class_support: int = MIN_CLASS_SUPPORT
) -> dict[str, Any] | None:
    """Return a winner only when comparable, complete, supported evidence exists.

    Input ``runs`` is the canonical model registry query with one row per metric.
    Macro F1 ranks overall candidates. Worst-class recall/F1 and weighted F1 are
    tie-breakers. Class-specific rankings use class F1 and minimum support.
    """
    required = {"model_run_id", "candidate_id", "model_name", "metric_name", "metric_value"}
    if runs.empty or not required.issubset(runs.columns):
        return None
    frame = runs.copy()
    frame = frame[
        frame.get("run_freshness", pd.Series("valid", index=frame.index)).eq("valid")
        & frame.get("candidate_status", pd.Series("succeeded", index=frame.index)).eq("succeeded")
        & frame.get("status", pd.Series("succeeded", index=frame.index)).eq("succeeded")
        & frame.get("split_name", pd.Series("test", index=frame.index)).astype(str).str.lower().isin({"test", "holdout", "temporal_test"})
        & frame.get("auditable", pd.Series(True, index=frame.index)).fillna(False).astype(bool)
    ]
    if "feature_snapshot_id" in frame:
        frame = frame[frame.feature_snapshot_id.notna()]
    if "label_definition_id" in frame:
        frame = frame[frame.label_definition_id.notna()]
    if frame.empty:
        return None
    frame["metric_key"] = frame.metric_name.astype(str).str.lower().str.replace(" ", "_", regex=False)
    aliases = {
        "f1_macro": "macro_f1", "macro-f1": "macro_f1",
        "f1_weighted": "weighted_f1", "weighted-f1": "weighted_f1",
        "accuracy_score": "accuracy", "cv_macro_f1_std": "stability_std",
        "macro_f1_cv_std": "stability_std", "validation_macro_f1_std": "stability_std",
    }
    frame["metric_key"] = frame.metric_key.replace(aliases)
    # Models can be compared only inside exactly matching dataset/feature/label/split cohorts.
    frame["cohort"] = frame.apply(_cohort_key, axis=1)
    eligible_group = None
    for _, group in frame.groupby("cohort", dropna=False):
        names = group.model_name.dropna().astype(str).unique()
        has_macro = group.loc[group.metric_key.eq("macro_f1"), "model_name"].nunique()
        if len(names) >= 2 and has_macro == len(names):
            eligible_group = group
            break
    if eligible_group is None:
        return None
    metrics = eligible_group.pivot_table(
        index=["candidate_id", "model_run_id", "model_name"],
        columns="metric_key", values="metric_value", aggfunc="first"
    ).reset_index()
    if "macro_f1" not in metrics or metrics.macro_f1.isna().any():
        return None
    if class_metrics.empty or not {"candidate_id", "class_name", "f1", "recall", "support"}.issubset(class_metrics.columns):
        return None
    classes = class_metrics[class_metrics.candidate_id.isin(metrics.candidate_id)].copy()
    classes = classes[classes.class_name.isin(REQUIRED_CLASSES)]
    if classes.empty:
        return None
    for candidate in metrics.candidate_id:
        found = classes[classes.candidate_id.eq(candidate)]
        if set(found.class_name) != set(REQUIRED_CLASSES) or found.support.isna().any() or (found.support < min_class_support).any():
            return None
    class_wide = classes.pivot(index="candidate_id", columns="class_name", values=["f1", "recall", "support"])
    for metric in ("f1", "recall"):
        for label in REQUIRED_CLASSES:
            metrics[f"{label.lower()}_{metric}"] = metrics.candidate_id.map(class_wide[metric][label])
    metrics["worst_class_recall"] = metrics[[f"{label.lower()}_recall" for label in REQUIRED_CLASSES]].min(axis=1)
    metrics["worst_class_f1"] = metrics[[f"{label.lower()}_f1" for label in REQUIRED_CLASSES]].min(axis=1)
    for optional in ("weighted_f1", "accuracy"):
        if optional not in metrics:
            metrics[optional] = float("nan")
    if "stability_std" not in metrics:
        metrics["stability_std"] = float("nan")
    metrics = metrics.sort_values(
        ["macro_f1", "worst_class_recall", "worst_class_f1", "weighted_f1", "accuracy", "stability_std", "model_name"],
        ascending=[False, False, False, False, False, True, True],
        na_position="last", kind="stable"
    )
    top = metrics.iloc[0]
    model_class = classes[classes.candidate_id.eq(top.candidate_id)].copy()
    class_winners: dict[str, str | None] = {}
    for label in REQUIRED_CLASSES:
        per_class = classes[classes.class_name.eq(label)].sort_values(["f1", "recall"], ascending=False)
        if per_class.empty or per_class.iloc[0].support < min_class_support:
            class_winners[label] = None
        else:
            class_winners[label] = str(metrics.loc[metrics.candidate_id.eq(per_class.iloc[0].candidate_id), "model_name"].iloc[0])
    selected = top.to_dict()
    selected["class_metrics"] = model_class.to_dict(orient="records")
    selected["class_winners"] = class_winners
    selected["comparison_count"] = int(len(metrics))
    selected["validation_stability_std"] = top.stability_std
    return selected


def select_best_synthetic_model(
    metrics: pd.DataFrame,
    runs: pd.DataFrame,
    min_class_support: int = MIN_CLASS_SUPPORT,
    cv_results: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """Select among persisted synthetic demo evaluations, never research runs."""
    required = {"model_run_id", "model_name", "macro_f1", "weighted_f1", "accuracy", "class_metrics_json"}
    run_required = {"model_run_id", "status", "data_mode", "training_dataset_version", "validation_design", "test_start", "test_end"}
    if metrics.empty or not required.issubset(metrics.columns) or not run_required.issubset(runs.columns):
        return None
    joined = metrics.merge(runs[list(run_required)], on="model_run_id", suffixes=("", "_run"))
    if "data_mode" in joined:
        joined = joined[joined.data_mode.astype(str).str.contains("SYNTHETIC", case=False)]
    joined = joined[joined.status.astype(str).eq("succeeded_synthetic_demo")]
    if joined.empty:
        return None
    for key in ("training_dataset_version", "validation_design", "test_start", "test_end"):
        if joined[key].nunique(dropna=False) != 1:
            return None
    parsed: dict[Any, dict[str, dict[str, Any]]] = {}
    for row in joined.itertuples(index=False):
        try:
            per_class = json.loads(row.class_metrics_json)
        except (TypeError, json.JSONDecodeError):
            return None
        if set(per_class) != set(REQUIRED_CLASSES):
            return None
        if any(int(per_class[label].get("support", 0)) < min_class_support for label in REQUIRED_CLASSES):
            return None
        parsed[row.model_run_id] = per_class
    joined = joined.copy()
    joined["worst_class_recall"] = joined.model_run_id.map(lambda run: min(parsed[run][label]["recall"] for label in REQUIRED_CLASSES))
    joined["worst_class_f1"] = joined.model_run_id.map(lambda run: min(parsed[run][label]["f1"] for label in REQUIRED_CLASSES))
    joined["validation_f1_std"] = float("nan")
    if cv_results is not None and {"model_name", "fold_number", "validation_start", "validation_end", "weighted_f1"}.issubset(cv_results.columns):
        folds = cv_results[cv_results.model_name.isin(joined.model_name)].copy()
        signatures = {
            name: tuple(
                folds.loc[folds.model_name.eq(name), ["fold_number", "validation_start", "validation_end"]]
                .sort_values("fold_number").itertuples(index=False, name=None)
            )
            for name in joined.model_name
        }
        compatible = bool(signatures) and len(set(signatures.values())) == 1
        if compatible:
            stability = folds.groupby("model_name").weighted_f1.std(ddof=0)
            joined["validation_f1_std"] = joined.model_name.map(stability)
    joined = joined.sort_values(
        ["macro_f1", "worst_class_recall", "worst_class_f1", "validation_f1_std", "weighted_f1", "accuracy", "model_name"],
        ascending=[False, False, False, True, False, False, True],
        na_position="last", kind="stable"
    )
    winner = joined.iloc[0]
    class_winners: dict[str, str] = {}
    for label in REQUIRED_CLASSES:
        class_run_id = max(
            parsed,
            key=lambda run: (parsed[run][label]["f1"], parsed[run][label]["recall"]),
        )
        class_winners[label] = str(
            joined.loc[joined.model_run_id.eq(class_run_id), "model_name"].iloc[0]
        )
    return {
        "model_name": winner.model_name,
        "model_run_id": winner.model_run_id,
        "macro_f1": float(winner.macro_f1),
        "weighted_f1": float(winner.weighted_f1),
        "accuracy": float(winner.accuracy),
        "evaluation_date": winner.test_end,
        "class_metrics": parsed[winner.model_run_id],
        "class_winners": class_winners,
        "comparison_count": int(len(joined)),
        "validation_weighted_f1_std": float(winner.validation_f1_std) if pd.notna(winner.validation_f1_std) else None,
        "scope": "SYNTHETIC DEMONSTRATION ONLY",
    }
