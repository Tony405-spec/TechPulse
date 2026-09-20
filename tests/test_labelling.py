"""Tests for trajectory labelling."""

from __future__ import annotations

from src.common import LABEL_COLUMN, OUTPUTS_DIR
from src.labelling import assign_trajectory_labels


def test_labels_are_valid(labelled_matrix):
    """Assert labels are from the allowed set."""
    frame = assign_trajectory_labels(labelled_matrix, labelled_matrix)
    assert set(frame[LABEL_COLUMN]).issubset({"Growing", "Stable", "Declining"})


def test_no_unlabelled_rows(labelled_matrix):
    """Assert every row receives a label."""
    frame = assign_trajectory_labels(labelled_matrix, labelled_matrix)
    assert frame[LABEL_COLUMN].isna().sum() == 0


def test_label_distribution_logged(labelled_matrix):
    """Assert labelling summary JSON is written."""
    assign_trajectory_labels(labelled_matrix, labelled_matrix)
    assert (OUTPUTS_DIR / "labelling_summary.json").exists()


def test_future_window_labels_drive_temporal_targets(tmp_path):
    """Assert labels use future volume, not contemporaneous feature values."""
    path = tmp_path / "temporal.csv"
    import pandas as pd

    pd.DataFrame(
        [
            {
                "technology_name": "future-growth",
                "growth_momentum_index": 0.1,
                "recent_avg_monthly_volume": 10,
                "future_avg_monthly_volume": 13,
            },
            {
                "technology_name": "future-decline",
                "growth_momentum_index": 0.9,
                "recent_avg_monthly_volume": 10,
                "future_avg_monthly_volume": 7,
            },
        ]
    ).to_csv(path, index=False)
    frame = assign_trajectory_labels(path, path)
    labels = dict(zip(frame["technology_name"], frame["trajectory_label"]))
    assert labels["future-growth"] == "Growing"
    assert labels["future-decline"] == "Declining"
