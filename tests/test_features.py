"""Tests for feature engineering outputs."""

from __future__ import annotations

from src.common import FEATURE_COLUMNS
from src.feature_engineering import compute_feature_matrix


def test_all_seven_features_present(sample_datasets, tmp_path):
    """Assert all seven features are present."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    assert set(FEATURE_COLUMNS).issubset(frame.columns)


def test_feature_values_in_range(sample_datasets, tmp_path):
    """Assert normalised features are in [0, 1]."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    values = frame[FEATURE_COLUMNS].stack().dropna()
    assert ((values >= 0) & (values <= 1)).all()


def test_no_nulls_above_threshold(sample_datasets, tmp_path):
    """Assert no feature has 50 percent or more missing values."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    assert (frame[FEATURE_COLUMNS].isna().mean() < 0.5).all()
