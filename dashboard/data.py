"""Shared, defensive loaders and plain calculations for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"


@st.cache_data(show_spinner=False)
def read_csv_artifact(path_string: str) -> pd.DataFrame:
    """Read a CSV artifact, treating missing or empty files as unavailable."""
    path = Path(path_string)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def read_json_artifact(path_string: str) -> dict[str, Any]:
    """Read a JSON artifact without exposing low-level errors to users."""
    path = Path(path_string)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_predictions() -> tuple[pd.DataFrame, bool]:
    """Load saved predictions, or the labeled feature table as a fallback.

    The boolean is true only when probability-bearing prediction artifacts exist.
    """
    path = OUTPUTS / "technology_predictions.csv"
    saved = path.exists()
    if not saved:
        path = DATA / "feature_matrix.csv"
    frame = read_csv_artifact(str(path)).copy()
    if "technology_name" in frame:
        frame["technology_name"] = frame["technology_name"].fillna("").astype(str)
    for col in ["risk_score", "confidence", "prob_Growing", "prob_Stable", "prob_Declining"]:
        if col in frame:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame, bool(saved and {"prob_Growing", "prob_Stable", "prob_Declining"}.issubset(frame.columns))


def load_community() -> pd.DataFrame:
    """Load and normalize local community observations."""
    frame = read_csv_artifact(str(DATA / "stackexchange.csv")).copy()
    if frame.empty:
        return frame
    if "tag" in frame:
        frame["tag"] = frame["tag"].fillna("").astype(str)
    if "date" in frame:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for col in ["question_count", "unanswered_count", "unanswered_pct", "question_pct"]:
        if col in frame:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def load_survey() -> pd.DataFrame:
    """Load survey aggregates only when the real aggregate file is present."""
    return read_csv_artifact(str(DATA / "developer_survey_usage.csv"))


def plain_label(row: pd.Series) -> str:
    """Return the prediction label with a training-label fallback."""
    return str(row.get("predicted_label", row.get("trajectory_label", "Unavailable")))


def risk_from_probability(probability_growing: Any) -> float | None:
    """Return complement-of-growing score, not probability of decline."""
    value = pd.to_numeric(probability_growing, errors="coerce")
    if pd.isna(value):
        return None
    return float((1.0 - float(value)) * 100.0)


def artifact_consistency() -> list[str]:
    """List detectable mismatches among current persisted research artifacts."""
    issues: list[str] = []
    feature = read_csv_artifact(str(DATA / "feature_matrix.csv"))
    summary = read_json_artifact(str(OUTPUTS / "labelling_summary.json"))
    if not feature.empty and "trajectory_label" in feature and summary:
        actual = feature["trajectory_label"].value_counts(dropna=False).to_dict()
        declared = {k: int(v.get("count", -1)) for k, v in summary.items() if isinstance(v, dict) and "count" in v}
        if declared and any(actual.get(label, 0) != count for label, count in declared.items()):
            issues.append("The label summary does not match the label counts in the current feature matrix.")
    if not (OUTPUTS / "evaluation_summary.json").exists():
        issues.append("The run-level evaluation summary is missing, so split dates and held-out class coverage cannot be confirmed from this checkout.")
    predictions = read_csv_artifact(str(OUTPUTS / "technology_predictions.csv"))
    if not predictions.empty and {"trajectory_label", "predicted_label"}.issubset(predictions.columns):
        if predictions["trajectory_label"].notna().sum() and not predictions["trajectory_label"].equals(predictions["predicted_label"]):
            issues.append("The saved table contains both target labels and predicted labels; they are not interchangeable.")
    return issues


def data_mode() -> str:
    """Describe the source mode recorded by the most recent pipeline run."""
    manifest = read_json_artifact(str(OUTPUTS / "data_sources.json"))
    mode = str(manifest.get("source_mode", "not recorded"))
    return {"local_development_csv": "Local development CSV", "postgresql": "PostgreSQL warehouse"}.get(mode, mode)


def source_manifest() -> dict[str, Any]:
    """Return the saved source manifest."""
    return read_json_artifact(str(OUTPUTS / "data_sources.json"))


@st.cache_data(ttl=60, show_spinner=False)
def load_live_observations() -> pd.DataFrame:
    """Read additive API observations from PostgreSQL or its CSV fallback."""
    from src.data_ingestion import load_external_observations

    return load_external_observations()


def load_live_status() -> dict[str, Any]:
    """Read the latest collection and scheduler status without a long cache."""
    from src.live_data.storage import read_status

    return read_status()

