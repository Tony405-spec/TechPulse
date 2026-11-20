"""One-way, idempotent migration of the synthetic SQLite fixture into PostgreSQL.

SQLite is used only as a read-only migration input. Streamlit reads PostgreSQL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


def migrate(source: Path) -> dict[str, object]:
    if not source.is_file():
        raise FileNotFoundError(f"Synthetic migration source does not exist: {source}")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError("Set DATABASE_URL to the target PostgreSQL development database.")
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg2://" + database_url.removeprefix("postgresql://")
    engine = create_engine(database_url, pool_pre_ping=True)
    # A committed manifest makes repeat runs verification-only. Replacing demo
    # tables requires a separately reviewed migration and is never implicit.
    with engine.connect() as check:
        schema_exists = check.execute(text("SELECT to_regnamespace('demo') IS NOT NULL")).scalar()
        if schema_exists:
            manifest_exists = check.execute(text("""
                SELECT to_regclass('demo.migration_manifest') IS NOT NULL
            """)).scalar()
            if manifest_exists:
                previous = check.execute(text("SELECT source_sha256 FROM demo.migration_manifest ORDER BY migrated_at DESC LIMIT 1")).scalar()
                if previous == digest:
                    counts = {
                        name: int(check.execute(text(f'SELECT count(*) FROM demo."{name}"')).scalar())
                        for name in check.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='demo' AND table_type='BASE TABLE' AND table_name <> 'migration_manifest' ORDER BY table_name")).scalars()
                    }
                    engine.dispose()
                    return {"source_sha256": digest, "tables": len(counts), "row_counts": counts, "verified_existing_migration": True}
                if previous:
                    engine.dispose()
                    raise RuntimeError("A different source checksum is already migrated. Review a new versioned migration; existing demo data was not replaced.")
    with sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True) as sqlite:
        integrity = sqlite.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite migration source failed integrity_check: {integrity}")
        names = [r[0] for r in sqlite.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        tables: dict[str, pd.DataFrame] = {
            name: pd.read_sql_query(f'SELECT * FROM "{name}"', sqlite) for name in names
        }
    counts = {name: len(frame) for name, frame in tables.items()}
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS demo"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS demo.migration_manifest (
                source_sha256 text PRIMARY KEY,
                source_path text NOT NULL,
                migrated_at timestamptz NOT NULL DEFAULT now(),
                row_counts jsonb NOT NULL
            )
        """))
        # Preserve the deterministic fixture's table structure and records. The
        # schema is replaced atomically by this dedicated migration command.
        for name in tables:
            conn.execute(text(f'DROP TABLE IF EXISTS demo."{name}" CASCADE'))
        for name, frame in tables.items():
            frame.to_sql(name, conn, schema="demo", if_exists="replace", index=False, method="multi", chunksize=1000)
        conn.execute(text("""
            INSERT INTO demo.migration_manifest(source_sha256, source_path, row_counts)
            VALUES (:digest, :path, CAST(:counts AS jsonb))
            ON CONFLICT (source_sha256) DO UPDATE SET
              migrated_at=now(), source_path=EXCLUDED.source_path, row_counts=EXCLUDED.row_counts
        """), {"digest": digest, "path": str(source.resolve()), "counts": json.dumps(counts)})
        # Add the principal relational constraints after importing the unchanged
        # fixture. Abort on invalid relationships instead of silently omitting rows.
        constraints = [
            ("technologies", "technologies_pkey", "PRIMARY KEY (technology_id)"),
            ("company_profiles", "company_profiles_pkey", "PRIMARY KEY (company_id)"),
            ("company_technology_relationships", "company_technology_relationships_pkey", "PRIMARY KEY (relationship_id)"),
            ("feature_snapshots", "feature_snapshots_pkey", "PRIMARY KEY (feature_snapshot_id)"),
            ("lifecycle_assessments", "lifecycle_assessments_pkey", "PRIMARY KEY (assessment_id)"),
            ("model_runs", "model_runs_pkey", "PRIMARY KEY (model_run_id)"),
            ("predictions", "predictions_pkey", "PRIMARY KEY (prediction_id)"),
            ("community_observations", "community_tech_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("sentiment_observations", "sentiment_tech_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("survey_observations", "survey_tech_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("feature_snapshots", "feature_tech_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("predictions", "prediction_tech_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("predictions", "prediction_run_fk", "FOREIGN KEY (model_run_id) REFERENCES demo.model_runs(model_run_id)"),
            ("company_technology_relationships", "company_tech_company_fk", "FOREIGN KEY (company_id) REFERENCES demo.company_profiles(company_id)"),
            ("company_technology_relationships", "company_tech_technology_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("lifecycle_assessments", "lifecycle_technology_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("developer_questions", "questions_technology_fk", "FOREIGN KEY (technology_id) REFERENCES demo.technologies(technology_id)"),
            ("explanations", "explanations_prediction_fk", "FOREIGN KEY (prediction_id) REFERENCES demo.predictions(prediction_id)"),
            ("prediction_probabilities", "probabilities_prediction_fk", "FOREIGN KEY (prediction_id) REFERENCES demo.predictions(prediction_id)"),
        ]
        for table, constraint_name, clause in constraints:
            conn.execute(text(f'ALTER TABLE demo."{table}" ADD CONSTRAINT "{constraint_name}" {clause}'))
        conn.execute(text("CREATE INDEX community_tech_month_idx ON demo.community_observations(technology_id, month)"))
        conn.execute(text("CREATE INDEX features_tech_asof_idx ON demo.feature_snapshots(technology_id, as_of)"))
        conn.execute(text("CREATE INDEX predictions_model_idx ON demo.predictions(model_run_id)"))
        app_role_exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname='techpulse_app'")).first()
        if app_role_exists:
            conn.execute(text("GRANT USAGE ON SCHEMA demo TO techpulse_app"))
            conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA demo TO techpulse_app"))
    engine.dispose()
    return {"source_sha256": digest, "tables": len(tables), "row_counts": counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(migrate(args.source), indent=2))


if __name__ == "__main__":
    main()
