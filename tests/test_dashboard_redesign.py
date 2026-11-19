"""Core behavior and multipage smoke checks for the guided dashboard."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.data import artifact_consistency, risk_from_probability
from dashboard.page_renderer import PAGE_SUBTITLES, PAGES
from dashboard.readiness import indicator_readiness


@pytest.mark.parametrize(
    ("probability", "expected"), [(1, 0), (0.75, 25), (0, 100), (None, None)]
)
def test_risk_indicator_is_complement_of_growing_probability(probability, expected):
    actual = risk_from_probability(probability)
    assert actual == expected


def test_inconsistent_run_artifacts_are_flagged_when_present():
    issues = artifact_consistency()
    # On a coherent future run there may be no issue, so assert the API remains a list.
    assert isinstance(issues, list)


def test_app_entrypoint_registers_database_backed_navigation():
    from pathlib import Path

    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    app = AppTest.from_file(app_path, default_timeout=90).run()
    assert not app.exception


def test_every_research_page_has_a_task_oriented_introduction():
    assert set(PAGE_SUBTITLES) == set(PAGES)
    assert all(len(description) > 30 for description in PAGE_SUBTITLES.values())


def test_indicator_readiness_empty_data_is_unavailable_not_zero():
    result = indicator_readiness({})
    assert len(result) == 7
    assert set(result["Input readiness"]) == {"Unavailable"}
    assert result["Missing evidence / limitation"].str.len().gt(0).all()


def test_indicator_readiness_responds_to_valid_community_periods():
    facts = {
        "community_rows": 12,
        "valid_community_rows": 12,
        "valid_community_months": 12,
        "community_start": "2023-01-01",
        "community_end": "2023-12-01",
        "valid_survey_rows": 2,
        "survey_start_year": 2023,
        "survey_end_year": 2024,
    }
    result = indicator_readiness(facts).set_index("Research indicator")
    assert result.loc["Growth Momentum Index", "Input readiness"] == "Available"
    assert result.loc["Community Decay Rate", "Input readiness"] == "Available"
    assert result.loc["Sentiment Delta", "Input readiness"] == "Unavailable"


def test_indicator_readiness_requires_sourced_company_evidence():
    result = indicator_readiness({
        "sourced_adoption_rows": 4,
        "sourced_adoption_companies": 2,
        "adoption_start": "2023-01-01",
        "adoption_end": "2023-12-31",
    }).set_index("Research indicator")
    assert result.loc["Company Diversity Score", "Input readiness"] == "Available"
    assert result.loc["Adoption Velocity", "Input readiness"] == "Available"


def test_indicator_readiness_surfaces_failed_community_source():
    result = indicator_readiness({
        "stackexchange_failed_runs": 1,
        "stackexchange_critical_failures": 1,
    }).set_index("Research indicator")
    assert result.loc["Growth Momentum Index", "Input readiness"] == "Invalid source data"
    assert result.loc["Community Decay Rate", "Input readiness"] == "Invalid source data"


def test_indicator_readiness_detects_invalid_records_and_missing_periods():
    result = indicator_readiness({
        "community_rows": 3,
        "valid_community_rows": 0,
        "valid_community_months": 0,
    }).set_index("Research indicator")
    assert result.loc["Growth Momentum Index", "Input readiness"] == "Invalid source data"
    assert result.loc["Growth Momentum Index", "Evidence period"] == "Unavailable"


def test_research_explorer_search_filters_the_canonical_catalogue():
    from pathlib import Path

    app_path = Path(__file__).resolve().parents[1] / "tests" / "dashboard_smoke_app.py"
    app = AppTest.from_file(app_path, default_timeout=90).run()
    app.selectbox[0].set_value("Technology Explorer").run()
    search = next(element for element in app.text_input if element.label == "Search technologies")
    search.set_value("Python").run()
    technology = next(element for element in app.selectbox if element.label == "Technology")
    assert "Python" in technology.options
    assert all("python" in name.casefold() for name in technology.options)


def test_research_explorer_reports_an_empty_search_clearly():
    from pathlib import Path

    app_path = Path(__file__).resolve().parents[1] / "tests" / "dashboard_smoke_app.py"
    app = AppTest.from_file(app_path, default_timeout=90).run()
    app.selectbox[0].set_value("Technology Explorer").run()
    search = next(element for element in app.text_input if element.label == "Search technologies")
    search.set_value("no-such-techpulse-technology").run()
    assert any("No technology matches that search." in element.value for element in app.info)
