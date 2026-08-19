"""Model training for TechPulse classifiers."""

from __future__ import annotations

import logging
import inspect
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier

from src.common import (
    DATA_DIR,
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    LABEL_ENCODING,
    LABELS,
    LOGS_DIR,
    MODELS_DIR,
    RANDOM_STATE,
    ensure_directories,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class OrderedLabelEncoder:
    """Small ordered encoder preserving the required class mapping."""

    classes_: tuple[str, ...] = tuple(LABELS)

    def transform(self, labels: pd.Series | list[str] | np.ndarray) -> np.ndarray:
        """Encode labels using 0=Growing, 1=Stable, 2=Declining.

        Args:
            labels: Labels to encode.

        Returns:
            Integer encoded labels.
        """
        return np.array([LABEL_ENCODING[str(label)] for label in labels], dtype=int)

    def inverse_transform(self, encoded: np.ndarray | list[int]) -> np.ndarray:
        """Decode integer labels back to strings.

        Args:
            encoded: Encoded labels.

        Returns:
            Decoded label names.
        """
        return np.array([self.classes_[int(value)] for value in encoded])


class ContiguousLabelClassifier:
    """Adapter for estimators that require contiguous labels in small folds."""

    def __init__(self, model: Any, all_classes: list[int] | None = None) -> None:
        self.model = model
        self.all_classes = all_classes or [0, 1, 2]
        self.classes_: np.ndarray | None = None

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "ContiguousLabelClassifier":
        self.classes_ = np.array(sorted(np.unique(y).tolist()), dtype=int)
        remap = {original: index for index, original in enumerate(self.classes_)}
        y_internal = np.array([remap[int(value)] for value in y], dtype=int)
        self.model.fit(X, y_internal)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.classes_ is None:
            raise RuntimeError("Model has not been fitted.")
        internal = self.model.predict(X)
        return np.array([self.classes_[int(value)] for value in internal], dtype=int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.classes_ is None:
            raise RuntimeError("Model has not been fitted.")
        internal_proba = self.model.predict_proba(X)
        full = np.zeros((len(internal_proba), len(self.all_classes)))
        for internal_index, original_class in enumerate(self.classes_):
            full[:, int(original_class)] = internal_proba[:, internal_index]
        return full


def _configure_logger() -> logging.Logger:
    """Configure the model training logger.

    Returns:
        Configured logger.
    """
    ensure_directories()
    logger = logging.getLogger("techpulse.model_training")
    logger.setLevel(logging.INFO)
    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        handler = logging.FileHandler(LOGS_DIR / "model_training.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def load_feature_matrix(path: Path | None = None) -> pd.DataFrame:
    """Load the labelled feature matrix.

    Args:
        path: Optional CSV path.

    Returns:
        Feature matrix DataFrame.

    Raises:
        FileNotFoundError: If the CSV is missing.
        ValueError: If required columns are absent.
    """
    path = path or DATA_DIR / "feature_matrix.csv"
    if not path.exists():
        raise FileNotFoundError(f"Feature matrix not found: {path}")
    frame = pd.read_csv(path)
    required = set(FEATURE_COLUMNS + [LABEL_COLUMN])
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Feature matrix missing required columns: {sorted(missing)}")
    return frame


def _split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, OrderedLabelEncoder]:
    """Create the sacred stratified train/test split.

    Args:
        frame: Labelled feature matrix.

    Returns:
        X_train, X_test, y_train, y_test, and ordered encoder.
    """
    encoder = OrderedLabelEncoder()
    X = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    y = encoder.transform(frame[LABEL_COLUMN])
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=RANDOM_STATE,
    )
    return X_train, X_test, y_train, y_test, encoder


def _fit_logistic(X_train: pd.DataFrame, y_train: np.ndarray, logger: logging.Logger) -> LogisticRegression:
    """Fit Logistic Regression with convergence retry.

    Args:
        X_train: Imputed training features.
        y_train: Encoded training labels.
        logger: Training logger.

    Returns:
        Trained LogisticRegression estimator.
    """
    base_params = {
        "C": 1.0,
        "max_iter": 300,
        "random_state": RANDOM_STATE,
    }
    if "multi_class" in inspect.signature(LogisticRegression).parameters:
        base_params["multi_class"] = "ovr"
    model = LogisticRegression(**base_params)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(X_train, y_train)
    if any(issubclass(warning.category, ConvergenceWarning) for warning in caught):
        logger.warning("LogisticRegression convergence warning; retrying with saga.")
        retry_params = {
            "C": 1.0,
            "max_iter": 1000,
            "solver": "saga",
            "random_state": RANDOM_STATE,
        }
        if "multi_class" in inspect.signature(LogisticRegression).parameters:
            retry_params["multi_class"] = "ovr"
        model = LogisticRegression(**retry_params)
        model.fit(X_train, y_train)
    logger.info("Logistic regression coefficients: %s", model.coef_.tolist())
    return model


def _fit_knn(X_train: pd.DataFrame, y_train: np.ndarray, cv: StratifiedKFold, logger: logging.Logger) -> KNeighborsClassifier:
    """Fit KNN with grid search over k.

    Args:
        X_train: Imputed training features.
        y_train: Encoded training labels.
        cv: Stratified CV splitter.
        logger: Training logger.

    Returns:
        Best KNN estimator.
    """
    grid = GridSearchCV(
        KNeighborsClassifier(),
        {"n_neighbors": [3, 5, 7, 9, 11]},
        cv=cv,
        scoring="f1_weighted",
    )
    grid.fit(X_train, y_train)
    means = grid.cv_results_["mean_test_score"]
    if np.allclose(means, means[0]):
        logger.info("All KNN k values tied; defaulting to k=5.")
        model = KNeighborsClassifier(n_neighbors=5)
        model.fit(X_train, y_train)
        return model
    logger.info("Best KNN k=%s", grid.best_params_["n_neighbors"])
    return grid.best_estimator_


def _cv_splitter(y_train: np.ndarray, logger: logging.Logger) -> StratifiedKFold:
    """Create a stratified CV splitter that respects small local datasets."""
    _, counts = np.unique(y_train, return_counts=True)
    min_class_count = int(counts.min())
    if min_class_count < 2:
        raise ValueError(
            "At least two training records per class are required for stratified cross-validation."
        )
    n_splits = min(5, min_class_count)
    if n_splits < 5:
        logger.warning(
            "Using %s-fold stratified CV because the least-populated class has only %s training rows.",
            n_splits,
            min_class_count,
        )
    return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)


def _artifact(
    model: Any,
    imputer: SimpleImputer,
    encoder: OrderedLabelEncoder,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    train_technologies: list[str],
    test_technologies: list[str],
) -> dict[str, Any]:
    """Bundle a fitted model with preprocessing and evaluation split metadata.

    Args:
        model: Trained estimator.
        imputer: Fitted median imputer.
        encoder: Ordered label encoder.
        X_train: Raw training features.
        y_train: Encoded training labels.
        X_test: Raw held-out features.
        y_test: Encoded held-out labels.

    Returns:
        Serializable artifact dictionary.
    """
    return {
        "model": model,
        "imputer": imputer,
        "label_encoder": encoder,
        "feature_columns": FEATURE_COLUMNS,
        "X_train": X_train,
        "y_train": y_train,
        "X_test": X_test,
        "y_test": y_test,
        "train_technologies": train_technologies,
        "test_technologies": test_technologies,
    }


def train_all_models(feature_path: Path | None = None) -> dict[str, Path]:
    """Train LR, KNN, Random Forest, and XGBoost models.

    Args:
        feature_path: Optional labelled feature matrix path.

    Returns:
        Mapping of model names to serialized artifact paths.
    """
    logger = _configure_logger()
    production_run = feature_path is None
    frame = load_feature_matrix(feature_path)
    X_train, X_test, y_train, y_test, encoder = _split(frame)
    if "technology_name" in frame:
        train_technologies = frame.loc[X_train.index, "technology_name"].astype(str).tolist()
        test_technologies = frame.loc[X_test.index, "technology_name"].astype(str).tolist()
    else:
        train_technologies = X_train.index.astype(str).tolist()
        test_technologies = X_test.index.astype(str).tolist()
    imputer = SimpleImputer(strategy="median")
    X_train_imp = pd.DataFrame(imputer.fit_transform(X_train), columns=FEATURE_COLUMNS, index=X_train.index)
    X_test_imp = pd.DataFrame(imputer.transform(X_test), columns=FEATURE_COLUMNS, index=X_test.index)
    cv = _cv_splitter(y_train, logger)
    date_stamp = datetime.now().strftime("%Y%m%d")
    artifacts: dict[str, Path] = {}

    models: dict[str, Any] = {}
    models["logistic_regression"] = _fit_logistic(X_train_imp, y_train, logger)
    models["knn"] = _fit_knn(X_train_imp, y_train, cv, logger)
    rf_search = RandomizedSearchCV(
        RandomForestClassifier(random_state=RANDOM_STATE),
        {
            "n_estimators": [100, 200, 500],
            "max_depth": [None, 5, 10, 20],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2"],
        },
        n_iter=20 if production_run else 2,
        scoring="f1_weighted",
        cv=cv,
        random_state=RANDOM_STATE,
    )
    rf_search.fit(X_train_imp, y_train)
    models["random_forest"] = rf_search.best_estimator_
    logger.info("RF feature importances: %s", models["random_forest"].feature_importances_.tolist())

    _, train_class_counts = np.unique(y_train, return_counts=True)
    if int(train_class_counts.min()) >= 5:
        xgb_search = RandomizedSearchCV(
            XGBClassifier(random_state=RANDOM_STATE, eval_metric="mlogloss", n_jobs=1),
            {
                "n_estimators": [100, 200, 500],
                "max_depth": [3, 5, 7],
                "learning_rate": [0.01, 0.05, 0.1, 0.2],
                "subsample": [0.6, 0.8, 1.0],
                "colsample_bytree": [0.6, 0.8, 1.0],
                "min_child_weight": [1, 3, 5],
            },
            n_iter=30 if production_run else 2,
            scoring="f1_weighted",
            cv=cv,
            random_state=RANDOM_STATE,
            error_score="raise",
        )
        xgb_search.fit(X_train_imp.astype("float32"), y_train)
        models["xgboost"] = xgb_search.best_estimator_
    else:
        logger.warning(
            "Skipping XGBoost CV tuning because the least-populated training class has fewer than 5 rows."
        )
        models["xgboost"] = ContiguousLabelClassifier(
            XGBClassifier(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=RANDOM_STATE,
                eval_metric="mlogloss",
                n_jobs=1,
            )
        )
        models["xgboost"].fit(X_train_imp.astype("float32"), y_train)

    for name, model in models.items():
        preds = model.predict(X_test_imp.astype("float32") if name == "xgboost" else X_test_imp)
        logger.info("%s held-out accuracy: %.4f", name, accuracy_score(y_test, preds))
        path = MODELS_DIR / f"techpulse_{name}_{date_stamp}.joblib"
        joblib.dump(
            _artifact(
                model,
                imputer,
                encoder,
                X_train,
                y_train,
                X_test,
                y_test,
                train_technologies,
                test_technologies,
            ),
            path,
        )
        artifacts[name] = path
    return artifacts
