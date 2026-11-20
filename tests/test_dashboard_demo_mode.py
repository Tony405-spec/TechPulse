"""PostgreSQL-backed, provenance-isolated demonstration mode tests."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest

from dashboard.demo_renderer import PAGES
from dashboard.demo_store import ROOT, demo_engine, demo_schema_available, read_demo_table
from dashboard.model_selection import select_best_synthetic_model

ROOT = Path(__file__).resolve().parents[1]


def test_demo_schema_is_postgres_and_explicitly_synthetic():
    assert demo_schema_available()
    for table in ["technologies", "community_observations", "survey_observations", "enterprise_evidence", "feature_snapshots", "predictions", "explanations"]:
        data = read_demo_table(table)
        assert not data.empty
        assert set(data.data_mode) == {"SYNTHETIC DEMONSTRATION DATA"}
        assert set(data.data_origin) == {"SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE"}
    assert read_demo_table("kenya_context").empty
    kenya = read_demo_table("geographic_observations")
    assert (kenya.geography_code.str.startswith("KE-")).sum() >= 500
    evidence = read_demo_table("enterprise_evidence")
    assert evidence.verification_status.str.contains("NOT VERIFIED").all()
    assert evidence.source_url.str.startswith("synthetic://").all()
    with demo_engine().connect() as connection:
        assert connection.execute(text("SELECT current_database()")).scalar() == "techpulse_rebuild_dev"
        fk_count = connection.execute(text("SELECT count(*) FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='demo' AND c.contype='f'")).scalar()
        assert fk_count >= 10
        assert connection.execute(text("SELECT count(*) FROM demo.technologies")).scalar() == 210
        assert connection.execute(text("SELECT count(*) FROM demo.predictions")).scalar() == 840
        assert connection.execute(text("SELECT count(*) FROM ml.model_runs WHERE status='succeeded'")).scalar() == 0


def test_demo_model_results_are_isolated_and_dynamic():
    metrics = read_demo_table("model_metrics")
    runs = read_demo_table("model_runs")
    assert set(metrics.model_name) == {"Logistic Regression", "K-Nearest Neighbours", "Random Forest", "XGBoost"}
    assert metrics.data_mode.eq("SYNTHETIC DEMONSTRATION DATA").all()
    assert metrics.validation_design.str.contains("synthetic", case=False).all()
    assert metrics.class_metrics_json.map(lambda value: set(json.loads(value)) == {"Growing", "Stable", "Declining"}).all()
    selection = select_best_synthetic_model(metrics, runs, cv_results=read_demo_table("model_cv_results"))
    assert selection is not None
    assert selection["scope"] == "SYNTHETIC DEMONSTRATION ONLY"
    assert selection["model_name"] == metrics.sort_values("macro_f1", ascending=False).iloc[0].model_name
    assert selection["comparison_count"] == 4
    assert selection["validation_weighted_f1_std"] is not None
    for run in runs.itertuples(index=False):
        artifact = ROOT / run.artifact_uri
        assert artifact.is_file()
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == run.artifact_sha256
    persisted = read_demo_table("model_selection_records")
    selected = persisted.loc[persisted.selection_key.eq("synthetic_demo")].iloc[0]
    assert selected.selection_status == "selected"
    assert selected.model_run_id == selection["model_run_id"]
    assert selected.primary_metric == "macro_f1"


def test_application_exposes_postgres_demo_mode_without_sqlite_fallback():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=90).run(timeout=90)
    assert not app.exception
    mode = next(element for element in app.selectbox if element.label == "Data mode")
    assert mode.value == "Simulation · PostgreSQL"
    mode.set_value("Legacy demo · PostgreSQL").run(timeout=90)
    assert not app.exception
    assert any("SYNTHETIC DEMONSTRATION DATA" in element.value for element in app.warning)
    mode.set_value("Research · PostgreSQL").run(timeout=90)
    assert not app.exception
    assert any("RESEARCH MODE" in element.value for element in app.error)


def test_demo_search_filters_database_catalogue():
    app = AppTest.from_file(str(ROOT / "tests" / "dashboard_demo_smoke_app.py"), default_timeout=60).run(timeout=60)
    app.selectbox[0].set_value("Technology Explorer").run(timeout=60)
    search = next(element for element in app.text_input if element.label == "Search fictional technologies")
    search.set_value("DemoLang").run(timeout=60)
    assert app.dataframe[0].value["name"].tolist() == ["DemoLang"]


def test_latest_demo_scenarios_include_three_labels():
    latest = read_demo_table("latest_features")
    assert set(latest.synthetic_label) == {"Growing", "Stable", "Declining"}


def test_scaled_demo_counts_probabilities_and_lineage():
    minimums = {
        "technologies": 150, "community_observations": 3000,
        "historical_technology_observations": 3000, "developer_questions": 5000,
        "sentiment_observations": 2000, "company_profiles": 300,
        "company_technology_relationships": 1500, "enterprise_adoption_observations": 2000,
        "geographic_observations": 500, "feature_snapshots": 150,
        "lifecycle_assessments": 150, "predictions": 150, "explanations": 150,
    }
    with demo_engine().connect() as connection:
        for table, minimum in minimums.items():
            assert connection.execute(text(f'SELECT count(*) FROM demo."{table}"')).scalar() >= minimum
        assert connection.execute(text("SELECT min(total), max(total) FROM (SELECT prediction_id, sum(probability) total FROM demo.prediction_probabilities GROUP BY prediction_id) p")).first()[0] >= .99999
        assert connection.execute(text("SELECT count(*) FROM demo.explanations WHERE mean_abs_shap IS NOT NULL AND local_contribution IS NOT NULL")).scalar() >= 150
        assert connection.execute(text("SELECT count(*) FROM demo.model_cv_results")).scalar() >= 8
        assert connection.execute(text("SELECT count(*) FROM demo.demo_seed_runs WHERE status='succeeded'")).scalar() >= 1


@pytest.mark.parametrize("page", PAGES)
def test_synthetic_demo_pages_render(page: str):
    app = AppTest.from_file(str(ROOT / "tests" / "dashboard_demo_smoke_app.py"), default_timeout=60).run(timeout=60)
    selector = next(element for element in app.selectbox if element.label == "Synthetic demo page")
    selector.set_value(page).run(timeout=60)
    assert not app.exception, f"Synthetic demo page failed to render: {page}"
