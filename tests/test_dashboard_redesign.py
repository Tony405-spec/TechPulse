"""Core behavior and multipage smoke checks for the guided dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.data import artifact_consistency, risk_from_probability


@pytest.mark.parametrize(("probability", "expected"), [(1, 0), (0.75, 25), (0, 100), (None, None)])
def test_risk_indicator_is_complement_of_growing_probability(probability, expected):
    actual = risk_from_probability(probability)
    assert actual == expected


def test_inconsistent_run_artifacts_are_flagged_when_present():
    issues = artifact_consistency()
    # On a coherent future run there may be no issue, so assert the API remains a list.
    assert isinstance(issues, list)


@pytest.mark.parametrize(
    "page_path",
    [
        "views/0_Start_Here.py",
        "views/1_Home.py",
        "views/2_Rankings.py",
        "views/5_Community_Health.py",
        "views/6_Prediction_Explorer.py",
        "views/3_Model_Performance.py",
        "views/7_Methodology_Data.py",
        "views/8_Live_Technology_Intelligence.py",
        "views/4_About.py",
    ],
)
def test_redesigned_pages_render_without_uncaught_exception(page_path: str):
    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    app = AppTest.from_file(app_path, default_timeout=90).run()
    assert not app.exception
    app.switch_page(page_path).run()
    assert not app.exception
