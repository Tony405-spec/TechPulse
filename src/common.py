"""Shared constants and helpers for the TechPulse pipeline."""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"
OUTPUTS_DIR = BASE_DIR / "outputs"

RANDOM_STATE = 42
LABELS = ["Growing", "Stable", "Declining"]
LABEL_ENCODING = {"Growing": 0, "Stable": 1, "Declining": 2}
FEATURE_COLUMNS = [
    "technology_health_score",
    "growth_momentum_index",
    "question_quality_score",
    "company_diversity_score",
    "sentiment_delta",
    "adoption_velocity",
    "community_decay_rate",
]
LABEL_COLUMN = "trajectory_label"
TECH_COLUMN = "technology_name"
CATEGORY_COLUMN = "category"
DISCLAIMER = (
    "TechPulse predictions are for informational purposes only and should not be "
    "used as the sole basis for technology investment decisions."
)


def ensure_directories() -> None:
    """Create runtime directories required by the pipeline.

    Returns:
        None.
    """
    for path in (DATA_DIR, LOGS_DIR, MODELS_DIR, OUTPUTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def normalise_name(value: object) -> str:
    """Return a lowercase normalised string for tolerant column matching.

    Args:
        value: Value to normalise.

    Returns:
        A simplified string with separators removed.
    """
    return "".join(ch for ch in str(value).lower() if ch.isalnum())
