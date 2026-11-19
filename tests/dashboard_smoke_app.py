"""Tiny Streamlit harness used to smoke-test each dashboard page renderer."""

import streamlit as st

from dashboard.page_renderer import PAGES, render_page

selected = st.selectbox("Smoke-test page", PAGES, label_visibility="collapsed")
render_page(selected)
