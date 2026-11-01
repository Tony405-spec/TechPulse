"""Additive PostgreSQL or CSV persistence for timestamped live observations."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from src.common import OUTPUTS_DIR

OBSERVATION_COLUMNS = [
    "technology_id", "technology", "source", "metric_name", "metric_value", "metric_text",
    "observed_at", "collected_at", "source_identifier", "metadata_json",
]
OBSERVATION_KEY = ["technology_id", "source", "metric_name", "source_identifier", "observed_at"]
LIVE_DATA_DIR = OUTPUTS_DIR / "live_data"
CSV_PATH = LIVE_DATA_DIR / "live_observations.csv"
STATUS_PATH = LIVE_DATA_DIR / "status.json"
TABLE_NAME = "techpulse_live_observations"


class PersistenceError(RuntimeError):
    """Live data could not be persisted in the configured source mode."""


def database_url() -> str | None:
    load_dotenv()
    value = os.getenv("DATABASE_URL", "").strip()
    return value or None


def _validate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for record in records:
        missing = [name for name in OBSERVATION_COLUMNS if name not in record]
        if missing:
            raise ValueError(f"Observation is missing required fields: {missing}")
        if record["source"] not in {"github", "stackexchange", "pypi", "npm"}:
            raise ValueError(f"Unknown live data source: {record['source']}")
        if not record["technology_id"] or not record["metric_name"] or not record["source_identifier"]:
            raise ValueError("Observation identity fields cannot be empty")
        value = record["metric_value"]
        if value is not None and (not isinstance(value, (int, float)) or not pd.notna(value)):
            raise ValueError(f"Observation contains an invalid metric value: {value!r}")
        try:
            pd.Timestamp(record["observed_at"])
            pd.Timestamp(record["collected_at"])
            json.loads(record["metadata_json"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Observation contains an invalid timestamp or metadata JSON") from exc
        cleaned.append({name: record[name] for name in OBSERVATION_COLUMNS})
    return cleaned


def append_observations(records: list[dict[str, Any]], *, url: str | None = None) -> int:
    """Persist valid observations, keeping historical rows and dropping duplicate keys."""
    if not records:
        return 0
    cleaned = _validate_records(records)
    effective_url = url if url is not None else database_url()
    if effective_url:
        return _append_postgres(cleaned, effective_url)
    return _append_csv(cleaned)


def _append_csv(records: list[dict[str, Any]]) -> int:
    LIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    incoming = pd.DataFrame(records, columns=OBSERVATION_COLUMNS)
    existing = pd.read_csv(CSV_PATH) if CSV_PATH.exists() and CSV_PATH.stat().st_size else pd.DataFrame(columns=OBSERVATION_COLUMNS)
    before = len(existing)
    combined = pd.concat([existing, incoming], ignore_index=True)
    combined = combined.drop_duplicates(OBSERVATION_KEY, keep="first")
    added = len(combined) - before
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".tmp", dir=LIVE_DATA_DIR, delete=False) as handle:
            temp_path = handle.name
            combined.to_csv(handle, index=False)
        os.replace(temp_path, CSV_PATH)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
    return added


def _append_postgres(records: list[dict[str, Any]], url: str) -> int:
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise PersistenceError("Install SQLAlchemy and psycopg2-binary to persist live observations in PostgreSQL") from exc
    engine = create_engine(url, pool_pre_ping=True)
    try:
        table = TABLE_NAME
        is_postgres = engine.dialect.name == "postgresql"
        timestamp_type = "TIMESTAMPTZ" if is_postgres else "TIMESTAMP"
        metadata_type = "JSONB NOT NULL DEFAULT '{}'::jsonb" if is_postgres else "TEXT NOT NULL DEFAULT '{}'"
        metadata_param = "CAST(:metadata_json AS jsonb)" if is_postgres else ":metadata_json"
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table} (
                technology_id TEXT NOT NULL,
                technology TEXT NOT NULL,
                source TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value DOUBLE PRECISION NULL,
                metric_text TEXT NULL,
                observed_at {timestamp_type} NOT NULL,
                collected_at {timestamp_type} NOT NULL,
                source_identifier TEXT NOT NULL,
                metadata_json {metadata_type},
                PRIMARY KEY (technology_id, source, metric_name, source_identifier, observed_at)
            )
        """
        verb = "INSERT" if is_postgres else "INSERT OR IGNORE"
        conflict = "ON CONFLICT (technology_id, source, metric_name, source_identifier, observed_at) DO NOTHING" if is_postgres else ""
        insert_sql = f"""
            {verb} INTO {table} ({', '.join(OBSERVATION_COLUMNS)})
            VALUES (:technology_id, :technology, :source, :metric_name, :metric_value, :metric_text,
                    :observed_at, :collected_at, :source_identifier, {metadata_param})
            {conflict}
        """
        params = []
        for item in records:
            row = dict(item)
            row["observed_at"] = pd.Timestamp(row["observed_at"]).to_pydatetime()
            row["collected_at"] = pd.Timestamp(row["collected_at"]).to_pydatetime()
            params.append(row)
        with engine.begin() as connection:
            connection.execute(text(create_sql))
            result = connection.execute(text(insert_sql), params)
            return int(result.rowcount or 0)
    except Exception as exc:  # database driver raises multiple backend-specific errors
        raise PersistenceError(f"Could not persist observations to PostgreSQL table {table}: {exc}") from exc
    finally:
        engine.dispose()


def load_observations(*, url: str | None = None) -> pd.DataFrame:
    """Read from the configured PostgreSQL warehouse, or the established CSV fallback."""
    effective_url = url if url is not None else database_url()
    if effective_url:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(effective_url, pool_pre_ping=True)
            try:
                with engine.connect() as connection:
                    return pd.read_sql(text(f"SELECT {', '.join(OBSERVATION_COLUMNS)} FROM {TABLE_NAME}"), connection)
            finally:
                engine.dispose()
        except Exception as exc:
            message = str(exc).casefold()
            if TABLE_NAME.casefold() in message and any(token in message for token in ("does not exist", "no such table", "undefinedtable")):
                return pd.DataFrame(columns=OBSERVATION_COLUMNS)
            raise PersistenceError(f"Could not read PostgreSQL table {TABLE_NAME}: {exc}") from exc
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        return pd.DataFrame(columns=OBSERVATION_COLUMNS)
    try:
        frame = pd.read_csv(CSV_PATH)
        return frame.reindex(columns=OBSERVATION_COLUMNS)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise PersistenceError(f"Could not read live observation CSV: {exc}") from exc


def read_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {"sources": {}}
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"sources": {}}
    except (OSError, json.JSONDecodeError):
        return {"sources": {}}


def update_status(source: str | None = None, *, status: str | None = None, technology: str | None = None, records: int | None = None, error: str | None = None, job: dict[str, Any] | None = None) -> None:
    LIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = read_status()
    data.setdefault("sources", {})
    now = pd.Timestamp.now(tz="UTC").isoformat()
    if source:
        entry = data["sources"].setdefault(source, {})
        entry.update({"status": status, "last_attempt": now, "technology": technology, "error": error})
        if status == "success":
            entry.update({"last_success": now, "records_written": records or 0, "error": None})
    if job is not None:
        data["job"] = {**data.get("job", {}), **job}
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".tmp", dir=LIVE_DATA_DIR, delete=False) as handle:
            temp_path = handle.name
            json.dump(data, handle, indent=2)
        os.replace(temp_path, STATUS_PATH)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
