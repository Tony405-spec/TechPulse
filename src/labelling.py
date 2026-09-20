"""Trajectory labelling rules for TechPulse."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from src.common import DATA_DIR, LABEL_COLUMN, LOGS_DIR, OUTPUTS_DIR, ensure_directories

GROWTH_RATIO_THRESHOLD = 1.20
DECLINE_RATIO_THRESHOLD = 0.80
MIN_RECENT_AVG_VOLUME = 1.0

LOGGER = logging.getLogger(__name__)


def _configure_logger() -> logging.Logger:
    """Configure and return the labelling logger.

    Returns:
        Configured logger.
    """
    ensure_directories()
    logger = logging.getLogger("techpulse.labelling")
    logger.setLevel(logging.INFO)
    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        handler = logging.FileHandler(LOGS_DIR / "labelling.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def _label_row(row: pd.Series, logger: logging.Logger) -> str:
    """Assign one trajectory label from future activity.

    Args:
        row: Feature matrix row.
        logger: Labelling logger.

    Returns:
        One of Growing, Stable, or Declining.
    """
    if {"future_avg_monthly_volume", "recent_avg_monthly_volume"}.issubset(row.index):
        recent = pd.to_numeric(row.get("recent_avg_monthly_volume"), errors="coerce")
        future = pd.to_numeric(row.get("future_avg_monthly_volume"), errors="coerce")
        if pd.isna(recent) or pd.isna(future):
            return "Stable"
        ratio = future / max(float(recent), MIN_RECENT_AVG_VOLUME)
        if ratio >= GROWTH_RATIO_THRESHOLD:
            return "Growing"
        if ratio <= DECLINE_RATIO_THRESHOLD:
            return "Declining"
        return "Stable"

    logger.warning(
        "Future-window target columns are absent; falling back to legacy labels for %s.",
        row.get("technology_name"),
    )
    momentum = row.get("growth_momentum_index")
    if momentum > 0.70:
        return "Growing"
    if momentum < 0.40:
        return "Declining"
    return "Stable"


def assign_trajectory_labels(
    feature_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Assign Growing, Stable, or Declining labels and persist summaries.

    Args:
        feature_path: Input feature matrix CSV path.
        output_path: Output feature matrix CSV path.

    Returns:
        Updated feature matrix DataFrame.

    Raises:
        FileNotFoundError: If the feature matrix is missing.
    """
    logger = _configure_logger()
    feature_path = feature_path or DATA_DIR / "feature_matrix.csv"
    output_path = output_path or feature_path
    if not feature_path.exists():
        raise FileNotFoundError(f"Feature matrix not found: {feature_path}")
    frame = pd.read_csv(feature_path)
    frame[LABEL_COLUMN] = frame.apply(lambda row: _label_row(row, logger), axis=1)
    counts = frame[LABEL_COLUMN].value_counts().reindex(
        ["Growing", "Stable", "Declining"], fill_value=0
    )
    summary = {
        label: {"count": int(count), "percentage": float(count / max(len(frame), 1) * 100)}
        for label, count in counts.items()
    }
    summary["_method"] = {
        "target": "future_window_activity",
        "growth_ratio_threshold": GROWTH_RATIO_THRESHOLD,
        "decline_ratio_threshold": DECLINE_RATIO_THRESHOLD,
        "note": (
            "Labels compare future average monthly question volume with recent observed "
            "average volume. Future target columns are excluded from model features."
        ),
    }
    logger.info("Class distribution: %s", summary)
    (OUTPUTS_DIR / "labelling_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    frame.to_csv(output_path, index=False)
    return frame
