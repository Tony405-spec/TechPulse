"""Tests for feature engineering outputs."""

from __future__ import annotations

import pandas as pd

from src.common import FEATURE_COLUMNS, OBSERVATION_MONTH_COLUMN, TARGET_LEAKAGE_COLUMNS
from src.feature_engineering import (
    compute_feature_matrix,
    _sentiment_features,
    _enterprise_features,
    _enterprise_as_of,
)
import logging


def test_target_columns_are_not_model_features():
    """Assert future-window target fields cannot leak into model features."""
    assert set(FEATURE_COLUMNS).isdisjoint(TARGET_LEAKAGE_COLUMNS)


def test_all_seven_features_present(sample_datasets, tmp_path):
    """Assert the model contract contains all seven named SRS indicators."""
    frame = compute_feature_matrix(sample_datasets, tmp_path / "feature_matrix.csv")
    assert len(FEATURE_COLUMNS) == 7
    assert {
        "technology_health_score", "growth_momentum_index", "question_quality_score",
        "company_diversity_score", "sentiment_delta", "adoption_velocity",
        "community_decay_rate",
    } == set(FEATURE_COLUMNS)
    assert set(FEATURE_COLUMNS).issubset(frame.columns)


def test_usage_share_is_not_substituted_for_satisfaction_delta():
    frame = pd.DataFrame({
        "technology": ["Python", "Python"],
        "survey_year": [2021, 2024],
        "developer_usage_share": [0.2, 0.8],
    })
    result = _sentiment_features(frame, logging.getLogger("feature-contract-test"))
    assert result.empty


def test_sentiment_delta_uses_only_explicit_satisfaction_scores():
    frame = pd.DataFrame({
        "technology": ["Python", "Python"],
        "survey_year": [2021, 2024],
        "satisfaction_score": [60.0, 75.0],
        "developer_usage_share": [0.2, 0.8],
    })
    result = _sentiment_features(frame, logging.getLogger("feature-contract-test"))
    assert result.loc[0, "sentiment_delta"] == 15.0


def test_enterprise_indicators_require_cited_evidence_and_leave_unapproved_formula_missing():
    logger = logging.getLogger("enterprise-evidence-contract-test")
    unsupported = pd.DataFrame({
        "technology": ["Python"],
        "company_name": ["Example Corp"],
        "adoption_date": ["2024-01-01"],
        "source_class": ["reported"],
    })
    assert _enterprise_features(unsupported, pd.DataFrame(), logger).empty

    supported = unsupported.assign(source_url=["https://example.org/report"])
    result = _enterprise_features(supported, pd.DataFrame(), logger)
    assert len(result) == 1
    assert pd.isna(result.loc[0, "company_diversity_score"])

    observation = pd.Timestamp("2024-06-01")
    diversity, velocity = _enterprise_as_of(
        {"fortune500_stacks": unsupported, "company_profiles": pd.DataFrame()},
        "Python",
        observation,
    )
    assert pd.isna(diversity) and pd.isna(velocity)


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
