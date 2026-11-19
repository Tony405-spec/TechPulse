"""Streamlit entrypoint for isolated demo-mode page smoke tests."""

import streamlit as st

from dashboard.demo_renderer import PAGES, render_page

page = st.selectbox("Synthetic demo page", PAGES)
render_page(page)
