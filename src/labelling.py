"""Trajectory labelling rules for TechPulse."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from src.common import DATA_DIR, LABEL_COLUMN, LOGS_DIR, OUTPUTS_DIR, ensure_directories

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
    """Assign one trajectory label from rule inputs.

    Args:
        row: Feature matrix row.
        logger: Labelling logger.

    Returns:
        One of Growing, Stable, or Declining.
    """
    momentum = row.get("growth_momentum_index")
    slope = row.get("so_volume_trend_slope", 0)
    r_squared = row.get("r_squared", 0)
    months = row.get("so_months_observed", 12)
    if pd.notna(months) and months < 12:
        logger.info("%s has <12 months of SO data; using Momentum Index only.", row.get("technology_name"))
        if momentum > 0.70:
            return "Growing"
        if momentum < 0.40:
            return "Declining"
        return "Stable"
    if momentum > 0.70 and slope > 0 and r_squared > 0.6:
        return "Growing"
    if momentum < 0.40 or (slope < 0 and r_squared > 0.6):
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
    logger.info("Class distribution: %s", summary)
    (OUTPUTS_DIR / "labelling_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    frame.to_csv(output_path, index=False)
    return frame
