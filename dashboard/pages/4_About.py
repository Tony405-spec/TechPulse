"""About and documentation page."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common import DISCLAIMER  # noqa: E402

st.title("About TechPulse")
st.info(DISCLAIMER)
st.write(
    """
    TechPulse is a KCA University BSc. Data Science final year project that predicts
    whether software technologies are Growing, Stable, or Declining by combining
    Stack Overflow community activity, Fortune 500 adoption, and developer sentiment.
    """
)
st.subheader("Data Sources and Licences")
st.write(
    """
    Stack Overflow Questions and Developer Survey signals are attributed to Stack
    Exchange and Stack Overflow under CC BY-SA 4.0. Fortune 500 stacks, company
    profiles, and technology metadata are aggregated from public open-data sources
    for academic research.
    """
)
st.subheader("Limitations")
st.write(
    """
    Predictions depend on source-data quality, recency, and coverage. The dashboard
    should support investigation, not replace expert judgement.
    """
)
st.link_button("GitHub Repository", "https://github.com/skynet-datagrid-labs/TechPulse")
st.link_button("Dissertation PDF", "https://github.com/skynet-datagrid-labs/TechPulse")
st.write(
    "Student: Kitili Tony Kenga | ORCID: 0009-0007-6899-8590 | "
    "KCA University BSc. Data Science 2026"
)
