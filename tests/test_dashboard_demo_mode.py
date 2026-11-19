"""Isolation and rendering checks for the synthetic demonstration mode."""

from __future__ import annotations

import json
import hashlib
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import inspect
from streamlit.testing.v1 import AppTest

from dashboard.demo_renderer import PAGES
from dashboard.demo_store import DATABASE_PATH, demo_engine, read_demo_table


def test_demo_store_is_separate_and_explicitly_synthetic():
    assert DATABASE_PATH.name == "techpulse_demo.sqlite"
    assert "synthetic_demo" in str(DATABASE_PATH)
    for table in [
        "technologies",
        "community_observations",
        "survey_observations",
        "enterprise_evidence",
        "feature_snapshots",
        "predictions",
        "explanations",
    ]:
        data = read_demo_table(table)
        assert not data.empty
        assert set(data["data_mode"]) == {"SYNTHETIC DEMONSTRATION DATA"}
        assert set(data["data_origin"]) == {"SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE"}
    assert read_demo_table("kenya_context").empty
    kenya = read_demo_table("geographic_observations")
    assert (kenya.geography_code.str.startswith("KE-")).sum() >= 500
    assert kenya.data_origin.eq("SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE").all()
    evidence = read_demo_table("enterprise_evidence")
    assert evidence.verification_status.str.contains("NOT VERIFIED").all()
    assert evidence.source_url.str.startswith("synthetic://").all()
    with demo_engine().connect() as connection:
        inspector = inspect(connection)
        assert inspector.get_foreign_keys("community_observations")
        assert inspector.get_foreign_keys("predictions")
        table_names = set(inspector.get_table_names())
        assert "model_runs" in table_names
        assert "developer_questions" in table_names
        assert "enterprise_adoption_observations" in table_names
    with sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_demo_models_are_isolated_and_temporally_described():
    metrics = read_demo_table("model_metrics")
    assert set(metrics.model_name) == {
        "Logistic Regression",
        "K-Nearest Neighbours",
        "Random Forest",
        "XGBoost",
    }
    assert metrics.data_mode.eq("SYNTHETIC DEMONSTRATION DATA").all()
    assert metrics.validation_design.str.contains("synthetic", case=False).all()
    assert metrics.test_start.max() > metrics.train_start.min()
    assert metrics.class_metrics_json.map(lambda x: set(json.loads(x)) == {"Growing", "Stable", "Declining"}).all()
    runs = read_demo_table("model_runs")
    assert runs.training_dataset_version.eq("synthetic-seed-7312026-v2").all()
    for run in runs.itertuples(index=False):
        artifact = Path(__file__).resolve().parents[1] / run.artifact_uri
        assert artifact.is_file()
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == run.artifact_sha256


def test_application_exposes_separate_demo_mode_without_silent_fallback():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "dashboard" / "app.py"), default_timeout=90).run(timeout=90)
    assert not app.exception
    mode = next(element for element in app.selectbox if element.label == "Data mode")
    mode.set_value("Synthetic demonstration · separate SQLite").run(timeout=90)
    assert not app.exception
    assert any("SYNTHETIC DEMONSTRATION DATA" in element.value for element in app.warning)


def test_fresh_application_session_defaults_to_synthetic_demo_mode():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "dashboard" / "app.py"), default_timeout=90).run(timeout=90)
    assert not app.exception
    mode = next(element for element in app.selectbox if element.label == "Data mode")
    assert mode.value.startswith("Synthetic demonstration")
    assert any("SYNTHETIC DEMONSTRATION DATA" in element.value for element in app.warning)


def test_demo_search_filters_the_fictional_catalogue():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "tests" / "dashboard_demo_smoke_app.py"), default_timeout=60).run(timeout=60)
    app.selectbox[0].set_value("Technology Explorer").run(timeout=60)
    search = next(element for element in app.text_input if element.label == "Search fictional technologies")
    search.set_value("DemoLang").run(timeout=60)
    assert app.dataframe[0].value["name"].tolist() == ["DemoLang"]


def test_latest_demo_scenarios_include_all_three_classes():
    latest = read_demo_table("latest_features")
    assert set(latest.synthetic_label) == {"Growing", "Stable", "Declining"}


def test_scaled_demo_counts_probabilities_and_database_lineage():
    minimums = {
        "technologies": 150,
        "community_observations": 3000,
        "historical_technology_observations": 3000,
        "developer_questions": 5000,
        "sentiment_observations": 2000,
        "company_profiles": 300,
        "company_technology_relationships": 1500,
        "enterprise_adoption_observations": 2000,
        "geographic_observations": 500,
        "feature_snapshots": 150,
        "lifecycle_assessments": 150,
        "predictions": 150,
        "explanations": 150,
    }
    with sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=ro", uri=True) as connection:
        for table, minimum in minimums.items():
            count = connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            assert count >= minimum, f"{table}: expected at least {minimum}, got {count}"
        latest = read_demo_table("latest_features")
        feature_columns = [
            "technology_health_score", "growth_momentum_index", "question_quality_score",
            "company_diversity_score", "sentiment_delta", "adoption_velocity", "community_decay_rate",
        ]
        assert latest[feature_columns].notna().all(axis=1).sum() >= 150
        probability_range = connection.execute(
            "SELECT min(total),max(total) FROM "
            "(SELECT prediction_id,sum(probability) total FROM prediction_probabilities GROUP BY prediction_id)"
        ).fetchone()
        assert probability_range[0] >= .99999 and probability_range[1] <= 1.00001
        assert connection.execute(
            "SELECT count(*) FROM explanations WHERE mean_abs_shap IS NOT NULL AND local_contribution IS NOT NULL"
        ).fetchone()[0] >= 150
        assert connection.execute("SELECT count(*) FROM model_cv_results").fetchone()[0] >= 8
        assert connection.execute("SELECT count(*) FROM demo_seed_runs WHERE status='succeeded'").fetchone()[0] >= 1


@pytest.mark.parametrize("page", ["Technology Profile", "Enterprise Adoption", "Developer Sentiment", "Model Laboratory", "Explainability"])
def test_demo_analytical_pages_render_interactive_charts(page: str):
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "tests" / "dashboard_demo_smoke_app.py"), default_timeout=60).run(timeout=60)
    app.selectbox[0].set_value(page).run(timeout=60)
    assert not app.exception
    assert len(app.get("plotly_chart")) >= 1, f"Expected chart on {page}"


@pytest.mark.parametrize("page", PAGES)
def test_synthetic_demo_pages_render(page: str):
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "tests" / "dashboard_demo_smoke_app.py"), default_timeout=60).run(timeout=60)
    selector = next(element for element in app.selectbox if element.label == "Synthetic demo page")
    selector.set_value(page).run(timeout=60)
    assert not app.exception, f"Synthetic demo page failed to render: {page}"
