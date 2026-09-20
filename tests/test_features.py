"""Tests for feature engineering outputs."""

from __future__ import annotations

from src.common import FEATURE_COLUMNS, OBSERVATION_MONTH_COLUMN, TARGET_LEAKAGE_COLUMNS
from src.feature_engineering import compute_feature_matrix


def test_target_columns_are_not_model_features():
    """Assert future-window target fields cannot leak into model features."""
    assert set(FEATURE_COLUMNS).isdisjoint(TARGET_LEAKAGE_COLUMNS)


def test_all_seven_features_present(sample_datasets, tmp_path):
    """Assert all seven features are present."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    assert set(FEATURE_COLUMNS).issubset(frame.columns)


def test_temporal_feature_matrix_contains_observation_and_future_windows(sample_datasets, tmp_path):
    """Assert temporal rows include observation and future target windows."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    assert OBSERVATION_MONTH_COLUMN in frame.columns
    assert {"recent_avg_monthly_volume", "future_avg_monthly_volume"}.issubset(frame.columns)


def test_feature_values_in_range(sample_datasets, tmp_path):
    """Assert normalised features are in [0, 1]."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    values = frame[FEATURE_COLUMNS].stack().dropna()
    assert ((values >= 0) & (values <= 1)).all()


def test_no_nulls_above_threshold(sample_datasets, tmp_path):
    """Assert core community features have sufficient coverage."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    core_features = ["growth_momentum_index", "question_quality_score", "community_decay_rate"]
    assert (frame[core_features].isna().mean() < 0.5).all()
