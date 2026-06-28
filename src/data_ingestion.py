"""Database ingestion and quality validation for TechPulse."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd

from src.common import OUTPUTS_DIR, ensure_directories

LOGGER = logging.getLogger(__name__)
TABLES = [
    "so_questions",
    "dev_sentiment",
    "fortune500_stacks",
    "company_profiles",
    "tech_metadata",
    "question_company_mapping",
]
KEY_COLUMNS = {
    "so_questions": ["technology", "tag", "creation_date", "date"],
    "dev_sentiment": ["technology", "survey_year", "satisfaction_score"],
    "fortune500_stacks": ["technology", "company_id", "adoption_date"],
    "company_profiles": ["company_id", "sector", "company_name"],
    "tech_metadata": ["technology", "technology_name", "category"],
    "question_company_mapping": ["question_id", "company_id", "technology"],
}


def _validate_frame(table: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Validate one ingested table and return a quality summary.

    Args:
        table: Source table name.
        frame: Loaded pandas DataFrame.

    Returns:
        A JSON-serialisable quality summary.
    """
    row_count = int(len(frame))
    LOGGER.info("%s row count: %s", table, row_count)
    issues: list[dict[str, Any]] = []
    if row_count < 50:
        message = f"{table} contains fewer than 50 rows ({row_count})."
        LOGGER.warning(message)
        issues.append({"type": "minimum_rows", "message": message})

    for column in KEY_COLUMNS.get(table, []):
        if column not in frame.columns:
            continue
        null_pct = float(frame[column].isna().mean() * 100)
        if null_pct > 5:
            LOGGER.warning("%s.%s has %.2f%% nulls.", table, column, null_pct)
            issues.append(
                {"type": "null_threshold", "column": column, "null_pct": null_pct}
            )

    return {"row_count": row_count, "issues": issues}


def load_and_validate_datasets() -> dict[str, pd.DataFrame]:
    """Load all six PostgreSQL datasets and write a data quality report.

    Returns:
        A dictionary mapping required table names to pandas DataFrames.

    Raises:
        EnvironmentError: If DATABASE_URL is not configured.
        ConnectionError: If the PostgreSQL connection cannot be opened.
        RuntimeError: If a required table cannot be loaded.
    """
    ensure_directories()
    try:
        from dotenv import load_dotenv
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError as exc:
        raise ImportError(
            "Database ingestion requires python-dotenv and sqlalchemy. "
            "Install project dependencies with `pip install -r requirements.txt`."
        ) from exc

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise EnvironmentError("DATABASE_URL environment variable is required.")

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            datasets: dict[str, pd.DataFrame] = {}
            report: dict[str, Any] = {}
            for table in TABLES:
                try:
                    datasets[table] = pd.read_sql(text(f"SELECT * FROM {table}"), connection)
                except SQLAlchemyError as exc:
                    raise RuntimeError(f"Failed to load required table '{table}'.") from exc
                report[table] = _validate_frame(table, datasets[table])
    except RuntimeError:
        raise
    except SQLAlchemyError as exc:
        raise ConnectionError("Failed to connect to PostgreSQL using DATABASE_URL.") from exc

    report_path = OUTPUTS_DIR / "data_quality_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return datasets
