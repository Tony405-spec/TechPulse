"""Transactional loader and post-load verification for generated simulation data."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.engine import Engine

from src.db.migrate import _database_url, apply_migrations
from src.simulate import SimulationCorpus, TABLES, _frame_checksum

load_dotenv()


def _clean_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    records = clean.to_dict(orient="records")
    for row in records:
        for key, value in row.items():
            if hasattr(value, "item"):
                row[key] = value.item()
            if pd.isna(row[key]) if not isinstance(row[key], (list, dict)) else False:
                row[key] = None
    return records


def _db_frame(connection, table_name: str, version_id: str) -> pd.DataFrame:
    return pd.read_sql(text(f'SELECT * FROM sim."{table_name}" WHERE data_version_id=:v'), connection, params={"v": version_id})


def _verify(connection, corpus: SimulationCorpus) -> dict[str, Any]:
    version = corpus.data_version
    version_id = version["data_version_id"]
    observed_counts: dict[str, int] = {}
    observed_checksums: dict[str, str] = {}
    for table_name in TABLES:
        observed_counts[table_name] = int(connection.execute(
            text(f'SELECT count(*) FROM sim."{table_name}" WHERE data_version_id=:v'), {"v": version_id}
        ).scalar_one())
        observed = _db_frame(connection, table_name, version_id)
        observed_checksums[table_name] = _frame_checksum(observed)
        if observed_counts[table_name] != version["expected_counts"][table_name]:
            raise RuntimeError(f"Row-count mismatch in {table_name}: expected {version['expected_counts'][table_name]}, got {observed_counts[table_name]}.")
        if observed_checksums[table_name] != version["table_checksums"][table_name]:
            raise RuntimeError(f"Checksum mismatch in {table_name}: generated {version['table_checksums'][table_name]}, read back {observed_checksums[table_name]}.")
    orphan_checks = {
        "community": """SELECT count(*) FROM sim.stack_overflow_questions q LEFT JOIN sim.technology_metadata t USING(data_version_id,technology_id) WHERE q.data_version_id=:v AND t.technology_id IS NULL""",
        "survey": """SELECT count(*) FROM sim.developer_survey q LEFT JOIN sim.technology_metadata t USING(data_version_id,technology_id) WHERE q.data_version_id=:v AND t.technology_id IS NULL""",
        "adoption_technology": """SELECT count(*) FROM sim.fortune500_stacks a LEFT JOIN sim.technology_metadata t USING(data_version_id,technology_id) WHERE a.data_version_id=:v AND t.technology_id IS NULL""",
        "adoption_company": """SELECT count(*) FROM sim.fortune500_stacks a LEFT JOIN sim.company_profiles c USING(data_version_id,company_id) WHERE a.data_version_id=:v AND c.company_id IS NULL""",
        "mapping_question_month": """SELECT count(*) FROM sim.question_company_mapping m LEFT JOIN sim.stack_overflow_questions q USING(data_version_id,technology_id,observation_month) WHERE m.data_version_id=:v AND q.technology_id IS NULL""",
        "mapping_company": """SELECT count(*) FROM sim.question_company_mapping m LEFT JOIN sim.company_profiles c USING(data_version_id,company_id) WHERE m.data_version_id=:v AND c.company_id IS NULL""",
    }
    orphan_counts = {name: int(connection.execute(text(query), {"v": version_id}).scalar_one()) for name, query in orphan_checks.items()}
    if any(orphan_counts.values()):
        raise RuntimeError(f"Foreign-key verification failed: {orphan_counts}")
    return {"row_counts": observed_counts, "checksums": observed_checksums, "orphan_counts": orphan_counts}


def load_corpus(corpus: SimulationCorpus, url: str | None = None, *, engine: Engine | None = None) -> dict[str, Any]:
    """Insert one corpus version atomically, verify it, and safely support reruns."""
    target_url = _database_url(url or os.getenv("DATABASE_URL"))
    owned = engine is None
    db = engine or create_engine(target_url, pool_pre_ping=True)
    try:
        # Migration runner also validates the target name. The committed schema is
        # required before the single loader transaction starts.
        apply_migrations(target_url, engine=db)
        version = corpus.data_version
        with db.begin() as connection:
            existing = connection.execute(
                text("SELECT data_version_id,config_hash,expected_counts,table_checksums,class_distribution,status FROM ml.data_versions WHERE data_version_id=:id"),
                {"id": version["data_version_id"]},
            ).mappings().one_or_none()
            if existing:
                if existing["config_hash"].strip() != version["config_hash"]:
                    raise RuntimeError("Data-version id exists with a different config hash; refusing overwrite.")
                verification = _verify(connection, corpus)
                if existing["expected_counts"] != version["expected_counts"]:
                    raise RuntimeError("Existing data-version expected counts differ from this generator output.")
                connection.execute(text("UPDATE ml.data_versions SET status='verified' WHERE data_version_id=:id"), {"id": version["data_version_id"]})
                return {"inserted": False, "status": "verified", **verification}

            connection.execute(text("""
                INSERT INTO ml.data_versions
                (data_version_id,seed,config_hash,generator_version,git_commit,generated_at,
                 expected_counts,table_checksums,class_distribution,status,disclosure)
                VALUES (:id,:seed,:hash,:generator,:commit,:generated,
                        CAST(:counts AS jsonb),CAST(:checksums AS jsonb),CAST(:distribution AS jsonb),'generated',:disclosure)
            """), {"id": version["data_version_id"], "seed": version["seed"], "hash": version["config_hash"],
                "generator": version["generator_version"], "commit": version["git_commit"], "generated": version["generated_at"],
                "counts": json.dumps(version["expected_counts"], sort_keys=True),
                "checksums": json.dumps(version["table_checksums"], sort_keys=True),
                "distribution": json.dumps(version["class_distribution"], sort_keys=True), "disclosure": version["disclosure"]})

            metadata = MetaData()
            for table_name in TABLES:
                target = Table(table_name, metadata, schema="sim", autoload_with=connection)
                records = _clean_records(corpus.tables[table_name])
                for offset in range(0, len(records), 2000):
                    connection.execute(target.insert(), records[offset:offset+2000])
            connection.execute(text("UPDATE ml.data_versions SET status='loaded' WHERE data_version_id=:id"), {"id": version["data_version_id"]})
            verification = _verify(connection, corpus)
            connection.execute(text("""
                UPDATE ml.data_versions SET status='verified',
                    expected_counts=CAST(:counts AS jsonb), table_checksums=CAST(:checksums AS jsonb)
                WHERE data_version_id=:id
            """), {"id": version["data_version_id"],
                "counts": json.dumps(verification["row_counts"], sort_keys=True),
                "checksums": json.dumps(verification["checksums"], sort_keys=True)})
            return {"inserted": True, "status": "verified", **verification}
    finally:
        if owned:
            db.dispose()


if __name__ == "__main__":
    from src.simulate import simulate_corpus
    result = load_corpus(simulate_corpus())
    print(json.dumps(result, indent=2, default=str))
