"""TechPulse application with separate Research and Simulation modes."""

from __future__ import annotations

import streamlit as st
from dashboard.db.health import check_database
from dashboard.page_renderer import (
    PAGES as RESEARCH_PAGES,
    render_page as render_research_page,
)
from dashboard.simulation_renderer import render_simulation_app

st.set_page_config(
    page_title="TechPulse | Evidence Dashboard", page_icon="TP", layout="wide"
)

with st.sidebar:
    st.markdown("## TechPulse")
    mode = st.selectbox(
        "Data mode",
        [
            "Research · PostgreSQL",
            "Simulation · PostgreSQL",
        ],
        key="techpulse_data_mode_v2",
        index=1,
        help="Research evidence and the versioned synthetic simulation are separate modes with separate disclosures.",
    )

if mode == "Research · PostgreSQL":
    health = check_database()
    with st.sidebar:
        st.error(
            "RESEARCH MODE · NO VERIFIED KENYA-SPECIFIC OR ENTERPRISE ADOPTION EVIDENCE"
        )
        st.caption(
            "Research readiness is separate from the fictional simulation. Do not treat synthetic demonstration results as research findings."
        )
        if health["connected"]:
            st.success("Research PostgreSQL connected")
            st.caption(f"Database: {health['database_name']}")
            version = str(health["postgres_version"] or "").splitlines()[0]
            st.caption(version)
            st.caption(f"Canonical migration records: {health['migration_count']}")
            st.caption(f"Last ingestion: {health['last_ingestion'] or 'Unavailable'}")
            st.caption(
                f"Latest survey year: {health['latest_survey_year'] or 'Unavailable'}"
            )
            st.caption(
                f"Last source data collected: {health['last_collected_at'] or 'Unavailable'}"
            )
            st.caption(
                f"Last successful model run: {health['last_model_run'] or 'Unavailable'}"
            )
        else:
            st.error("Research PostgreSQL unavailable")
            st.caption(health["error"] or "Canonical schema validation failed.")
            if health["missing_relations"]:
                st.caption(f"Missing relations: {health['missing_relations']}")
        st.caption("Research mode · canonical PostgreSQL only · no CSV/demo fallback")
    active_pages = RESEARCH_PAGES
    page_renderer = render_research_page
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
        default=(
            title
            == (
                "Executive Overview"
                if mode == "Research · PostgreSQL"
                else "Command Center"
            )
        ),
    )
    for title in active_pages
]
st.navigation(pages).run()
