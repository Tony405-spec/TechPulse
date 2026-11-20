"""The entry point exposes only supported, clearly separated data modes."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_app_defaults_to_simulation_and_does_not_offer_unavailable_legacy_demo():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=90).run(
        timeout=90
    )
    assert not app.exception
    mode = next(element for element in app.selectbox if element.label == "Data mode")
    assert mode.value == "Simulation · PostgreSQL"
    assert mode.options == ["Research · PostgreSQL", "Simulation · PostgreSQL"]


def test_research_mode_keeps_its_explicit_database_unavailable_state():
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=90).run(
        timeout=90
    )
    mode = next(element for element in app.selectbox if element.label == "Data mode")
    mode.set_value("Research · PostgreSQL").run(timeout=90)
    assert not app.exception
    messages = [item.value for item in app.error] + [item.value for item in app.success]
    assert any(
        "Research PostgreSQL unavailable" in message
        or "Research PostgreSQL connected" in message
        for message in messages
    )
