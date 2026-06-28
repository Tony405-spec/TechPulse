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
