"""TechPulse application with explicit, isolated Research and Demo modes."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.db.health import check_database  # noqa: E402
from dashboard.page_renderer import PAGES as RESEARCH_PAGES, render_page as render_research_page  # noqa: E402
from dashboard.demo_renderer import PAGES as DEMO_PAGES, render_page as render_demo_page  # noqa: E402
from dashboard.demo_store import demo_schema_available  # noqa: E402
from dashboard.simulation_renderer import render_simulation_app  # noqa: E402

st.set_page_config(
    page_title="TechPulse | Evidence Dashboard", page_icon="TP", layout="wide"
)

with st.sidebar:
    st.markdown("## TechPulse")
    mode = st.selectbox(
        "Data mode",
        ["Research · PostgreSQL", "Legacy demo · PostgreSQL", "Simulation · PostgreSQL"],
        key="techpulse_data_mode_v2",
        index=2,
        help="Research records, the legacy synthetic demo, and the versioned simulation experiment use separate database schemas and disclosures.",
    )

if mode == "Research · PostgreSQL":
    health = check_database()
    with st.sidebar:
        st.error("RESEARCH MODE · NO VERIFIED KENYA-SPECIFIC OR ENTERPRISE ADOPTION EVIDENCE")
        st.caption("Research readiness is separate from the fictional simulation. Do not treat synthetic demonstration results as research findings.")
        if health["connected"]:
            st.success("Research PostgreSQL connected")
            st.caption(f"Database: {health['database_name']}")
            version = str(health["postgres_version"] or "").splitlines()[0]
            st.caption(version)
            st.caption(f"Canonical migration records: {health['migration_count']}")
            st.caption(f"Last ingestion: {health['last_ingestion'] or 'Unavailable'}")
            st.caption(f"Latest survey year: {health['latest_survey_year'] or 'Unavailable'}")
            st.caption(f"Last source data collected: {health['last_collected_at'] or 'Unavailable'}")
            st.caption(f"Last successful model run: {health['last_model_run'] or 'Unavailable'}")
        else:
            st.error("Research PostgreSQL unavailable")
            st.caption(health["error"] or "Canonical schema validation failed.")
            if health["missing_relations"]:
                st.caption(f"Missing relations: {health['missing_relations']}")
        st.caption("Research mode · canonical PostgreSQL only · no CSV/demo fallback")
    active_pages = RESEARCH_PAGES
    page_renderer = render_research_page
elif mode == "Legacy demo · PostgreSQL":
    with st.sidebar:
        st.warning("SYNTHETIC DEMONSTRATION DATA", icon="⚠️")
        st.caption("PostgreSQL demo schema; fictional records and synthetic-only metrics.")
        st.caption("Database: configured PostgreSQL · schema: demo")
    if not demo_schema_available():
        st.error("The PostgreSQL demo schema is unavailable.")
        st.code("python -m dashboard.postgres_demo_migration --source outputs/synthetic_demo/techpulse_demo.sqlite")
        st.stop()
    active_pages = DEMO_PAGES
    page_renderer = render_demo_page
else:
    render_simulation_app()
    st.stop()


def _make_page(title: str):
    def page() -> None:
        page_renderer(title)

    page.__name__ = "page_" + title.lower().replace(" ", "_")
    return page


pages = [
    st.Page(
        _make_page(title),
        title=title,
        default=(title == ("Executive Overview" if mode == "Research · PostgreSQL" else "Command Center")),
    )
    for title in active_pages
]
st.navigation(pages).run()
