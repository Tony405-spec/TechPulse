"""Tests for public data acquisition helpers."""

from __future__ import annotations

import pandas as pd

from src.data_acquisition.developer_survey import _aggregate_year
from src.technology_normalization import normalize_technology_name


def test_technology_alias_normalization_is_conservative():
    """Assert common aliases normalize without merging unrelated names."""
    assert normalize_technology_name("React.js") == "React"
    assert normalize_technology_name("nodejs") == "Node.js"
    assert normalize_technology_name("Java") == "Java"
    assert normalize_technology_name("JavaScript") == "JavaScript"


def test_developer_survey_aggregation_counts_multiselects(tmp_path):
    """Assert survey aggregation splits official semicolon-delimited fields."""
    path = tmp_path / "results.csv"
    pd.DataFrame(
        [
            {
                "ResponseId": 1,
                "LanguageHaveWorkedWith": "JavaScript;Python",
                "LanguageWantToWorkWith": "Python",
            },
            {
                "ResponseId": 2,
                "LanguageHaveWorkedWith": "React.js",
                "LanguageWantToWorkWith": "NodeJS",
            },
        ]
    ).to_csv(path, index=False)
    frame = _aggregate_year(path, 2024, chunksize=1)
    rows = {row["technology_name"]: row for _, row in frame.iterrows()}
    assert rows["JavaScript"]["worked_with_count"] == 1
    assert rows["Python"]["worked_with_count"] == 1
    assert rows["Python"]["want_to_work_with_count"] == 1
    assert rows["React"]["worked_with_count"] == 1
    assert rows["Node.js"]["want_to_work_with_count"] == 1
