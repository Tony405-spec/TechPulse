"""Shared fixtures for TechPulse tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.common import FEATURE_COLUMNS, LABEL_COLUMN, LABELS


@pytest.fixture()
def sample_datasets() -> dict[str, pd.DataFrame]:
    """Return synthetic six-table datasets."""
    dates = pd.date_range("2025-01-01", periods=18, freq="MS")
    techs = ["Python", "Django", "PostgreSQL"]
    so_rows = []
    for tech in techs:
        for idx, date in enumerate(dates):
            repeats = idx + 1 if tech == "Python" else 10 if tech == "Django" else 19 - idx
            for question in range(repeats):
                so_rows.append(
                    {
                        "technology": tech,
                        "creation_date": date,
                        "answer_count": 2 + question % 3,
                        "is_closed": question % 7 == 0,
                    }
                )
    sentiment = pd.DataFrame(
        {
            "technology": techs * 2,
            "survey_year": [2024, 2024, 2024, 2026, 2026, 2026],
            "satisfaction_score": [70, 60, 65, 88, 62, 45],
        }
    )
    stacks = pd.DataFrame(
        {
            "technology": techs * 4,
            "company_id": list(range(12)),
            "adoption_date": pd.date_range("2025-01-01", periods=12, freq="QS"),
        }
    )
    profiles = pd.DataFrame(
        {
            "company_id": list(range(12)),
            "company_name": [f"Company {i}" for i in range(12)],
            "sector": ["Finance", "Retail", "Energy", "Technology"] * 3,
        }
    )
    metadata = pd.DataFrame({"technology": techs, "category": ["Languages", "Frameworks", "Databases"]})
    mapping = pd.DataFrame({"question_id": range(12), "company_id": list(range(12)), "technology": techs * 4})
    return {
        "so_questions": pd.DataFrame(so_rows),
        "dev_sentiment": sentiment,
        "fortune500_stacks": stacks,
        "company_profiles": profiles,
        "tech_metadata": metadata,
        "question_company_mapping": mapping,
    }


@pytest.fixture()
def labelled_matrix(tmp_path: Path) -> Path:
    """Create a deterministic labelled feature matrix."""
    rows = []
    for label, base in zip(LABELS, [0.85, 0.55, 0.2]):
        for idx in range(12):
            rows.append(
                {
                    "technology_name": f"{label}_{idx}",
                    "category": "Tools",
                    **{feature: min(max(base + (idx % 3) * 0.01, 0), 1) for feature in FEATURE_COLUMNS},
                    "so_volume_trend_slope": 1 if label == "Growing" else -1 if label == "Declining" else 0,
                    "r_squared": 0.8,
                    "so_months_observed": 18,
                    LABEL_COLUMN: label,
                }
            )
    path = tmp_path / "feature_matrix.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path
