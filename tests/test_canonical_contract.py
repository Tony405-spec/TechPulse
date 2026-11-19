"""Guardrails for the new canonical contract and leakage boundaries."""

from pathlib import Path
import logging

import pandas as pd
import pytest

from src.common import FEATURE_COLUMNS, TARGET_LEAKAGE_COLUMNS
from src.model_training import _cv_splitter, _split
from src.cli import _validate_ingest_input

ROOT = Path(__file__).resolve().parents[1]


def test_migration_is_additive_and_contains_canonical_schemas():
    sql = (
        (ROOT / "migrations" / "001_canonical_schema.sql")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert all(
        f"create schema if not exists {name}" in sql
        for name in ["raw", "staging", "core", "analytics", "ml", "audit"]
    )
    assert "drop table" not in sql and "drop schema" not in sql
    for table in [
        "data_sources",
        "source_documents",
        "ingestion_runs",
        "community_monthly_metrics",
        "developer_survey_observations",
        "feature_snapshots",
        "model_predictions",
        "prediction_explanations",
    ]:
        assert "create table if not exists" in sql and table in sql


def test_feature_contract_has_all_seven_srs_indicators_without_target_leakage():
    assert set(FEATURE_COLUMNS).isdisjoint(TARGET_LEAKAGE_COLUMNS)
    assert len(FEATURE_COLUMNS) == 7
    assert {"company_diversity_score", "adoption_velocity"}.issubset(FEATURE_COLUMNS)


def test_random_split_is_not_used_when_observation_dates_are_missing():
    frame = pd.DataFrame(
        {
            "trajectory_label": ["Growing"] * 6 + ["Stable"] * 6,
            **{c: [0.5] * 12 for c in FEATURE_COLUMNS},
        }
    )
    with pytest.raises(ValueError, match="observation_month"):
        _split(frame)


def test_model_selection_folds_are_forward_in_time():
    months = pd.Series(pd.date_range("2024-01-01", periods=8, freq="MS").repeat(3))
    labels = [0, 1, 2] * 8
    folds = _cv_splitter(
        pd.Series(labels).to_numpy(), months, logging.getLogger("test")
    )
    for train_indices, validation_indices in folds:
        assert months.iloc[train_indices].max() < months.iloc[validation_indices].min()


def test_ingestion_deduplicates_identical_rows_and_reports_counts():
    source = pd.DataFrame(
        {
            "technology_name": ["Python", "Python"],
            "survey_year": [2024, 2024],
            "respondent_count": [100, 100],
            "developer_usage_share": [0.5, 0.5],
            "developer_interest_share": [0.4, 0.4],
            "developer_admiration_share": [0.6, 0.6],
        }
    )
    clean, report = _validate_ingest_input("survey", source)
    assert len(clean) == 1
    assert report["duplicate_rows_removed"] == 1


def test_ingestion_rejects_out_of_range_survey_share():
    source = pd.DataFrame(
        {
            "technology_name": ["Python"],
            "survey_year": [2024],
            "respondent_count": [100],
            "developer_usage_share": [1.2],
            "developer_interest_share": [0.4],
            "developer_admiration_share": [0.6],
        }
    )
    with pytest.raises(ValueError, match="outside"):
        _validate_ingest_input("survey", source)


def test_ingestion_rejects_conflicting_survey_rows_for_database_natural_key():
    source = pd.DataFrame(
        {
            "technology_name": ["Supabase", "Supabase"],
            "category": ["Database", "Platform"],
            "survey_year": [2024, 2024],
            "respondent_count": [100, 90],
            "developer_usage_share": [0.2, 0.3],
            "developer_interest_share": [0.4, 0.5],
            "developer_admiration_share": [0.6, 0.7],
        }
    )
    with pytest.raises(ValueError, match="conflicting source rows"):
        _validate_ingest_input("survey", source)


def test_stackexchange_ingestion_rejects_zero_cumulative_count():
    source = pd.DataFrame(
        {
            "tag": ["amazon-mws"],
            "date": ["2018-02-21"],
            "question_count": [0],
            "unanswered_count": [0],
        }
    )
    with pytest.raises(ValueError, match="non-positive cumulative counts"):
        _validate_ingest_input("stackexchange", source)
