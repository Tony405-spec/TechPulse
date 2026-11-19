"""Pooled PostgreSQL connection and bounded, read-only query helpers."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)


class DatabaseUnavailable(RuntimeError):
    """Raised when the configured PostgreSQL database cannot be used."""


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise DatabaseUnavailable(
            "DATABASE_URL is not configured. Set it to the TechPulse PostgreSQL connection."
        )
    if not url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise DatabaseUnavailable("DATABASE_URL must use PostgreSQL with psycopg2.")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url.removeprefix("postgresql://")
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return one pooled SQLAlchemy engine for this dashboard process."""
    try:
        return create_engine(
            database_url(),
            pool_pre_ping=True,
            pool_size=max(1, int(os.getenv("TECHPULSE_DB_POOL_SIZE", "5"))),
            max_overflow=max(0, int(os.getenv("TECHPULSE_DB_MAX_OVERFLOW", "10"))),
            pool_timeout=max(
                1, int(os.getenv("TECHPULSE_DB_POOL_TIMEOUT_SECONDS", "10"))
            ),
            pool_recycle=1800,
            connect_args={"application_name": "techpulse_streamlit"},
        )
    except (SQLAlchemyError, ValueError) as exc:
        raise DatabaseUnavailable(f"Could not configure PostgreSQL: {exc}") from exc


def query_frame(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Execute a parameterized read query with a transaction-local timeout."""
    timeout_ms = max(
        1000, int(os.getenv("TECHPULSE_QUERY_TIMEOUT_SECONDS", "30")) * 1000
    )
    try:
        engine = get_engine()
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": str(timeout_ms)},
                )
                return pd.read_sql_query(text(sql), conn, params=params or {})
    except (SQLAlchemyError, OSError, ValueError) as exc:
        raise DatabaseUnavailable(
            "PostgreSQL query failed. Check that the server is running, the database and limited-role credentials are correct, and the role can read the canonical schemas. "
            f"Details: {exc}"
        ) from exc
