"""Smoke coverage for the PostgreSQL-backed presentation mode."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from dashboard import simulation_data
from dashboard.technology_catalog import DISPLAY_CATALOG, with_display_names

ROOT = Path(__file__).resolve().parents[1]


def test_simulation_data_access_returns_database_backed_shapes():
    overview = simulation_data.get_overview()
    technologies = simulation_data.get_technologies(str(overview["data_version_id"]))
    assert overview["data_status"] == "verified"
    assert len(technologies) == int(overview["technology_count"]) == 300
    assert technologies.prediction_id.notna().sum() == 60
    assert set(technologies.loc[technologies.prediction_id.notna(), "predicted_label"]) <= {
        "Growing", "Stable", "Declining"
    }
    assert technologies.technology_name.nunique() == 300
    assert not technologies.technology_name.str.startswith("Synthetic ").any()
    assert {"Java", "Python", "React", "PostgreSQL"} <= set(technologies.technology_name)
    assert technologies.loc[technologies.technology_name.eq("React"), "prediction_id"].notna().any()


def test_display_aliases_are_stable_for_a_watchlist_subset():
    catalog_name = DISPLAY_CATALOG["Languages"][39]
    raw_subset = pd.DataFrame({
        "technology_id": ["SIM-TECH-0999"],
        "technology_name": ["Synthetic Language 0999"],
        "category": ["Languages"],
        "category_ordinal": [40],
    })
    assert with_display_names(raw_subset).iloc[0].technology_name == catalog_name


def test_simulation_app_renders_all_tabs_without_exceptions():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=90).run(timeout=90)
    assert not app.exception
    mode = next(element for element in app.selectbox if element.label == "Data mode")
    assert mode.value == "Simulation · PostgreSQL"
    assert [tab.label for tab in app.tabs] == ["🔎  Predict", "📊  Models", "💡  Insights"]
    assert any("Simulation only" in element.value for element in app.markdown)
    technology = next(element for element in app.selectbox if element.label == "Technology")
    technology.set_value("React").run(timeout=90)
    assert not app.exception
    assert any("Probability is not calibrated" in element.value for element in app.warning)

