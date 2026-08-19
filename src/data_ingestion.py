"""Database ingestion and quality validation for TechPulse."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd

from src.common import DATA_DIR, OUTPUTS_DIR, ensure_directories

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
    except ImportError as exc:
        raise ImportError("Install project dependencies with `pip install -r requirements.txt`.") from exc

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return load_local_development_datasets()

    try:
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError as exc:
        raise ImportError("PostgreSQL ingestion requires sqlalchemy and psycopg2-binary.") from exc

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            inspector = inspect(connection)
            available_tables = set(inspector.get_table_names())
            missing_tables = set(TABLES).difference(available_tables)
            if missing_tables:
                raise RuntimeError(
                    "PostgreSQL database is reachable but missing required tables: "
                    f"{sorted(missing_tables)}"
                )
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
    _write_source_manifest("postgresql", "Loaded required TechPulse tables from DATABASE_URL.")
    return datasets


def load_local_development_datasets() -> dict[str, pd.DataFrame]:
    """Load repository CSV data when PostgreSQL is not configured.

    The local repository contains the original descriptive analytics CSV inputs
    rather than the full six-table warehouse. Missing signal tables are derived
    deterministically and marked as development/demo data in the source manifest.

    Returns:
        Six DataFrames matching the expected ingestion contract.

    Raises:
        FileNotFoundError: If the required local CSVs are absent.
    """
    ensure_directories()
    stack_path = DATA_DIR / "stackexchange.csv"
    fortune_path = DATA_DIR / "fortune.csv"
    missing = [str(path) for path in (stack_path, fortune_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "DATABASE_URL is not configured and required local CSV files are missing: "
            f"{missing}"
        )

    so_questions = pd.read_csv(stack_path)
    so_questions = so_questions.rename(columns={"tag": "technology", "date": "creation_date"})
    so_questions["tag"] = so_questions["technology"]
    so_questions["creation_date"] = pd.to_datetime(so_questions["creation_date"], errors="coerce")
    so_questions["answer_count"] = (
        pd.to_numeric(so_questions["question_count"], errors="coerce").fillna(0)
        - pd.to_numeric(so_questions["unanswered_count"], errors="coerce").fillna(0)
    ).clip(lower=0)
    so_questions["is_closed"] = False

    company_profiles = pd.read_csv(fortune_path).rename(
        columns={"rank": "company_id", "name": "company_name"}
    )
    techs = sorted(so_questions["technology"].dropna().astype(str).unique())
    sectors = company_profiles[["company_id", "sector"]].dropna().drop_duplicates()
    if sectors.empty:
        sectors = pd.DataFrame({"company_id": [1], "sector": ["Unknown"]})

    stack_rows: list[dict[str, object]] = []
    for index, technology in enumerate(techs):
        sector_sample = sectors.iloc[index % len(sectors) : index % len(sectors) + 5]
        if sector_sample.empty:
            sector_sample = sectors.head(5)
        for offset, row in sector_sample.reset_index(drop=True).iterrows():
            stack_rows.append(
                {
                    "technology": technology,
                    "company_id": int(row["company_id"]),
                    "adoption_date": pd.Timestamp("2017-01-01") + pd.DateOffset(months=index + offset),
                    "source_type": "demo_derived_from_local_csv",
                }
            )
    fortune500_stacks = pd.DataFrame(stack_rows)

    yearly = (
        so_questions.assign(year=so_questions["creation_date"].dt.year)
        .groupby(["technology", "year"], as_index=False)
        .agg(question_count=("question_count", "sum"), unanswered_count=("unanswered_count", "sum"))
    )
    yearly["satisfaction_score"] = (
        100
        * (1 - yearly["unanswered_count"] / yearly["question_count"].replace(0, pd.NA))
    ).clip(lower=0, upper=100)
    dev_sentiment = yearly.rename(columns={"year": "survey_year"})[
        ["technology", "survey_year", "satisfaction_score"]
    ]
    dev_sentiment["source_type"] = "demo_proxy_from_unanswered_rate"

    tech_metadata = pd.DataFrame(
        {
            "technology": techs,
            "technology_name": techs,
            "category": [infer_category(technology) for technology in techs],
            "source_type": "demo_inferred_category",
        }
    )
    question_company_mapping = fortune500_stacks.reset_index().rename(columns={"index": "question_id"})[
        ["question_id", "company_id", "technology", "source_type"]
    ]
    datasets = {
        "so_questions": so_questions,
        "dev_sentiment": dev_sentiment,
        "fortune500_stacks": fortune500_stacks,
        "company_profiles": company_profiles,
        "tech_metadata": tech_metadata,
        "question_company_mapping": question_company_mapping,
    }
    report = {name: _validate_frame(name, frame) for name, frame in datasets.items()}
    (OUTPUTS_DIR / "data_quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_source_manifest(
        "local_development_csv",
        "PostgreSQL DATABASE_URL was not set. Stack Exchange and Fortune CSVs were loaded; "
        "missing sentiment, adoption-stack, metadata, and mapping tables were deterministically "
        "derived for development only.",
    )
    return datasets


def infer_category(technology: str) -> str:
    """Infer a broad dashboard category for local development data."""
    value = technology.lower()
    if any(token in value for token in ["sql", "mongo", "db", "redis", "dynamodb"]):
        return "Databases"
    if any(token in value for token in ["android", "ios", "django", "rails", "spring"]):
        return "Frameworks"
    if any(token in value for token in ["python", "java", "c#", "php", "actionscript"]):
        return "Languages"
    if any(token in value for token in ["aws", "amazon", "azure", "cloud", "paypal", "stripe"]):
        return "Cloud/Platforms"
    return "Tools"


def _write_source_manifest(source_mode: str, note: str) -> None:
    """Write data-source provenance for dashboards and reports."""
    manifest = {
        "source_mode": source_mode,
        "note": note,
        "required_tables": TABLES,
    }
    (OUTPUTS_DIR / "data_sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
