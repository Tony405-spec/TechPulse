"""Typed, cached data accessors for canonical TechPulse PostgreSQL tables."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.db import queries
from dashboard.db.connection import query_frame

TTL = max(1, int(os.getenv("TECHPULSE_CACHE_TTL_SECONDS", "300")))
CANONICAL_SCHEMAS = {"raw", "staging", "core", "analytics", "ml", "audit"}


@st.cache_data(ttl=TTL, show_spinner=False)
def _read(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    return query_frame(sql, params)


def clear_read_cache() -> None:
    _read.clear()


def health_row() -> pd.DataFrame:
    return query_frame(queries.HEALTH)


def schema_tables(
    schemas: tuple[str, ...] = ("raw", "staging", "core", "analytics", "ml", "audit")
) -> pd.DataFrame:
    if not set(schemas).issubset(CANONICAL_SCHEMAS):
        raise ValueError("Only canonical TechPulse schema names can be queried.")
    return query_frame(queries.SCHEMA_TABLES, {"schemas": list(schemas)})


def overview() -> pd.DataFrame:
    return _read(queries.OVERVIEW)


def indicator_evidence() -> pd.DataFrame:
    """Read an uncached readiness snapshot so new evidence is visible immediately."""
    return query_frame(queries.INDICATOR_EVIDENCE)


def technology_assessments(technology_id: int) -> pd.DataFrame:
    return _read(queries.TECHNOLOGY_ASSESSMENTS, {"technology_id": technology_id})


def source_status() -> pd.DataFrame:
    return _read(queries.SOURCES)


def technologies() -> pd.DataFrame:
    return _read(queries.TECHNOLOGIES)


def survey(year: int | None = None, geography: str | None = None) -> pd.DataFrame:
    return _read(queries.SURVEY, {"year": year, "geography": geography})


def community() -> pd.DataFrame:
    return _read(queries.COMMUNITY)


def kenya_observations() -> pd.DataFrame:
    return _read(queries.KENYA)


def live_observations() -> pd.DataFrame:
    return _read(queries.LIVE)


def predictions() -> pd.DataFrame:
    return _read(queries.PREDICTIONS)


def model_runs() -> pd.DataFrame:
    return _read(queries.MODEL_RUNS)


def model_class_metrics() -> pd.DataFrame:
    return _read(queries.MODEL_CLASS_METRICS)


def baselines() -> pd.DataFrame:
    return _read(queries.BASELINES)


def prediction_explanations(prediction_id: int) -> pd.DataFrame:
    return _read(queries.PREDICTION_EXPLANATIONS, {"prediction_id": prediction_id})


def community_block() -> pd.DataFrame:
    return _read(queries.COMMUNITY_BLOCK)


def provenance() -> pd.DataFrame:
    return _read(queries.PROVENANCE)


def table_counts() -> pd.DataFrame:
    return _read(
        queries.TABLE_COUNTS,
        {"schemas": ["raw", "staging", "core", "analytics", "ml", "audit"]},
    )
