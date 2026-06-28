"""Tests for model training and evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score

from src.common import MODELS_DIR, OUTPUTS_DIR
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
