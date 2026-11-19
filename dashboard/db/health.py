"""Live connection and canonical-schema checks for the dashboard chrome."""

from __future__ import annotations

from typing import Any

from dashboard.db.connection import DatabaseUnavailable, query_frame
from dashboard.db.queries import HEALTH, SCHEMA_TABLES

REQUIRED = {
    ("audit", "schema_migrations"),
    ("audit", "data_sources"),
    ("audit", "ingestion_runs"),
    ("core", "technologies"),
    ("core", "geographies"),
    ("analytics", "developer_survey_observations"),
    ("analytics", "community_monthly_metrics"),
    ("ml", "feature_snapshots"),
    ("ml", "model_runs"),
    ("ml", "model_predictions"),
}


def check_database() -> dict[str, Any]:
    try:
        health = query_frame(HEALTH).iloc[0].to_dict()
        tables = query_frame(
            SCHEMA_TABLES,
            {"schemas": ["raw", "staging", "core", "analytics", "ml", "audit"]},
        )
        found = set(zip(tables["table_schema"], tables["table_name"]))
        missing = sorted(REQUIRED - found)
        wrong_database = health.get("database_name") != "TechPulse-Database"
        return {
            "connected": not missing and not wrong_database,
            "database_name": health.get("database_name"),
            "postgres_version": health.get("postgres_version"),
            "checked_at": health.get("checked_at"),
            "migration_count": int(health.get("migration_count") or 0),
            "last_ingestion": health.get("last_ingestion"),
            "last_model_run": health.get("last_model_run"),
            "latest_survey_year": health.get("latest_survey_year"),
            "last_collected_at": health.get("last_collected_at"),
            "missing_relations": missing,
            "error": (
                "Connected to an unexpected database; expected TechPulse-Database."
                if wrong_database
                else (
                    None if not missing else "Required canonical relations are missing."
                )
            ),
        }
    except (DatabaseUnavailable, IndexError, KeyError, ValueError) as exc:
        return {
            "connected": False,
            "database_name": None,
            "postgres_version": None,
            "checked_at": None,
            "migration_count": 0,
            "last_ingestion": None,
            "last_model_run": None,
            "latest_survey_year": None,
            "last_collected_at": None,
            "missing_relations": [],
            "error": str(exc),
        }
