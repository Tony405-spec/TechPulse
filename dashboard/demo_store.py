"""PostgreSQL access to isolated synthetic demonstration records."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "outputs" / "synthetic_demo"
DATABASE_PATH = DEMO_DIR / "techpulse_demo.sqlite"  # read-only migration source only
ARTIFACT_DIR = DEMO_DIR / "artifacts"
SEED = 7312026
FEATURES = ["technology_health_score", "growth_momentum_index", "question_quality_score", "company_diversity_score", "sentiment_delta", "adoption_velocity", "community_decay_rate"]
LABELS = ["Growing", "Stable", "Declining"]
_ALLOWED_TABLES = {
    "technologies", "community_observations", "survey_observations", "enterprise_evidence",
    "feature_snapshots", "latest_features", "source_registry", "model_runs", "model_metrics",
    "predictions", "explanations", "kenya_context", "quality_checks",
    "historical_technology_observations", "developer_questions", "sentiment_observations",
    "company_profiles", "company_technology_relationships", "enterprise_adoption_observations",
    "geographic_observations", "lifecycle_assessments", "prediction_probabilities",
    "model_configurations", "model_cv_results", "demo_seed_runs",
    "model_selection_records",
}


def demo_engine():
    """Return the application's shared PostgreSQL engine."""
    from dashboard.db.connection import get_engine
    return get_engine()


def read_demo_table(table: str) -> pd.DataFrame:
    """Read one allow-listed table from PostgreSQL schema ``demo``."""
    if table not in _ALLOWED_TABLES:
        raise ValueError("Table is not part of the isolated synthetic demo schema.")
    engine = demo_engine()
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            return pd.read_sql_query(text(f'SELECT * FROM demo."{table}"'), connection)


def demo_schema_available() -> bool:
    """Whether the configured PostgreSQL database has the migrated demo schema."""
    engine = demo_engine()
    try:
        with engine.connect() as connection:
            return bool(connection.execute(text("SELECT to_regnamespace('demo') IS NOT NULL")).scalar())
    except Exception:
        return False
