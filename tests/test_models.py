"""Tests for model training and evaluation artifacts."""

from __future__ import annotations

import joblib
import json
import pandas as pd
from sklearn.metrics import accuracy_score

from src.common import FEATURE_COLUMNS, LABEL_COLUMN, OUTPUTS_DIR
from src.evaluation import compare_and_select_best_model
from src.model_training import train_all_models


def test_all_four_models_serialised(labelled_matrix):
    """Assert all four model artifacts are serialized."""
    artifacts = train_all_models(labelled_matrix)
    assert len(artifacts) == 4
    assert all(path.exists() for path in artifacts.values())


def test_model_comparison_csv_exists(labelled_matrix):
    """Assert model comparison CSV is produced."""
    artifacts = train_all_models(labelled_matrix)
    compare_and_select_best_model(artifacts)
    assert (OUTPUTS_DIR / "model_comparison.csv").exists()


def test_best_model_selection_json_exists(labelled_matrix):
    """Assert best model JSON is produced."""
    artifacts = train_all_models(labelled_matrix)
    compare_and_select_best_model(artifacts)
    assert (OUTPUTS_DIR / "best_model_selection.json").exists()


def test_model_comparison_includes_baselines(labelled_matrix):
    """Assert baseline rows are reported beside ML models."""
    artifacts = train_all_models(labelled_matrix)
    comparison = compare_and_select_best_model(artifacts)
    assert {"baseline_majority_class", "baseline_momentum_rule"}.issubset(set(comparison["Model"]))


def test_invalid_multiclass_auc_is_marked_unavailable(tmp_path):
    """Assert incomplete test classes produce ROC-AUC warnings instead of fake scores."""
    rows = []
    for month_index, month in enumerate(pd.date_range("2025-01-01", periods=12, freq="MS")):
        label = "Growing" if month_index % 3 == 0 else "Stable"
        for tech_index in range(4):
            rows.append(
                {
                    "technology_name": f"tech-{tech_index}",
                    "observation_month": month.date().isoformat(),
                    **{feature: 0.7 if label == "Growing" else 0.4 for feature in FEATURE_COLUMNS},
                    LABEL_COLUMN: label,
                }
            )
    path = tmp_path / "two_class_temporal.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    artifacts = train_all_models(path)
    comparison = compare_and_select_best_model(artifacts)
    summary = json.loads((OUTPUTS_DIR / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert comparison["Macro_ROC_AUC"].isna().all()
    assert summary["is_multiclass_test_valid"] is False
    assert summary["warnings"]


def test_random_state_reproducibility(labelled_matrix):
    """Train twice and assert deterministic logistic-regression test accuracy."""
    first = train_all_models(labelled_matrix)["logistic_regression"]
    second = train_all_models(labelled_matrix)["logistic_regression"]
    first_artifact = joblib.load(first)
    second_artifact = joblib.load(second)
    X1 = first_artifact["imputer"].transform(first_artifact["X_test"])
    X2 = second_artifact["imputer"].transform(second_artifact["X_test"])
    acc1 = accuracy_score(first_artifact["y_test"], first_artifact["model"].predict(X1))
    acc2 = accuracy_score(second_artifact["y_test"], second_artifact["model"].predict(X2))
    assert acc1 == acc2
