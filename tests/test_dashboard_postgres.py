"""Dashboard PostgreSQL contract and integration tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dashboard.db import repositories as repo
from dashboard.db.connection import database_url, get_engine
from dashboard.db.health import check_database
from dashboard.db.queries import PREDICTIONS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def reset_db_caches():
    get_engine.cache_clear()
    repo.clear_read_cache()
    yield
    get_engine.cache_clear()
    repo.clear_read_cache()


def test_database_url_handles_hyphen_and_psycopg2():
    monkey_url = "postgresql://read_user@localhost:5432/TechPulse-Database"
    from dashboard.db import connection

    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = monkey_url
    try:
        assert (
            database_url()
            == "postgresql+psycopg2://read_user@localhost:5432/TechPulse-Database"
        )
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old
        connection.get_engine.cache_clear()


def test_successful_postgres_connectivity_and_health():
    result = check_database()
    assert result["connected"] is True, result["error"]
    assert result["database_name"] == "TechPulse-Database"
    assert "PostgreSQL" in result["postgres_version"]
    assert result["migration_count"] >= 1
    assert result["missing_relations"] == []


def test_invalid_connection_is_reported_without_csv_fallback(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://invalid:invalid@127.0.0.1:1/TechPulse-Database",
    )
    get_engine.cache_clear()
    result = check_database()
    assert result["connected"] is False
    assert result["error"]


def test_invalid_connection_renders_explicit_error_state(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://invalid:invalid@127.0.0.1:1/TechPulse-Database",
    )
    get_engine.cache_clear()
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=45).run(
        timeout=45
    )
    next(element for element in app.selectbox if element.label == "Data mode").set_value(
        "Research data · PostgreSQL"
    ).run(timeout=45)
    assert not app.exception
    rendered = " ".join(
        element.value for element in app.error if hasattr(element, "value")
    )
    assert (
        "PostgreSQL unavailable" in rendered
        or "cannot read its configured PostgreSQL" in rendered
    )
    assert "csv" not in rendered.casefold()


def test_schema_discovery_is_limited_to_canonical_schemas():
    tables = repo.schema_tables()
    assert {"core", "analytics", "ml", "audit"}.issubset(set(tables.table_schema))
    with pytest.raises(ValueError, match="canonical"):
        repo.schema_tables(("public",))


def test_parameterized_survey_filter_and_empty_result():
    expected = repo.survey(geography="GLOBAL")
    if expected.empty:
        pytest.skip("Integration database has not loaded the survey source.")
    assert set(expected.geography_code.dropna()) == {"GLOBAL"}
    assert repo.survey(year=9999).empty


def test_empty_and_blocked_community_state_is_recorded_in_postgres():
    assert repo.community().empty
    blocked = repo.community_block()
    if blocked.empty:
        pytest.skip("Integration database has no recorded blocked community run.")
    assert not blocked.empty
    assert blocked.iloc[0].status == "failed"
    report = blocked.iloc[0].report
    assert report["invalid_examples"][0]["tag"] == "ios"
    assert report["invalid_examples"][0]["unanswered_count"] == 181334


def test_missing_kenya_data_and_global_separation():
    assert repo.kenya_observations().empty
    global_rows = repo.survey(geography="GLOBAL")
    kenya_rows = repo.survey(geography="KE")
    if global_rows.empty:
        pytest.skip("Integration database has not loaded the survey source.")
    assert set(global_rows.geography_code.dropna()) == {"GLOBAL"}
    assert kenya_rows.empty


def test_stale_predictions_are_filtered_and_missing_predictions_render_as_empty():
    assert "interval '365 days'" in PREDICTIONS
    assert "r.feature_snapshot_id IS NOT NULL" in PREDICTIONS
    assert "r.status='succeeded'" in PREDICTIONS
    assert repo.predictions().empty


def test_every_streamlit_page_renders_against_current_database():
    from streamlit.testing.v1 import AppTest
    from dashboard.page_renderer import PAGES

    for title in PAGES:
        app = AppTest.from_file(
            str(ROOT / "tests" / "dashboard_smoke_app.py"), default_timeout=45
        ).run(timeout=45)
        app.selectbox[0].set_value(title).run(timeout=45)
        assert not app.exception, f"Page failed to render: {title}"


def test_no_page_uses_legacy_csv_contract():
    for path in (ROOT / "dashboard" / "views").glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert "dashboard.data" not in content
        assert "read_csv" not in content
    app_code = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
    assert "load_predictions" not in app_code
