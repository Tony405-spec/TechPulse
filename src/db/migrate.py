"""Checksum-verified, transaction-safe SQL migrations for TechPulse Simulation."""

from __future__ import annotations

import hashlib
import os
import argparse
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_DIR = ROOT / "db" / "migrations"
load_dotenv(ROOT / ".env", override=False)


def _database_url(url: str | None = None) -> str:
    value = (url or os.getenv("DATABASE_URL", "")).strip()
    if not value.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError("DATABASE_URL must point to the dedicated techpulse_sim PostgreSQL database.")
    if value.startswith("postgresql://"):
        value = "postgresql+psycopg2://" + value.removeprefix("postgresql://")
    database = value.rsplit("/", 1)[-1].split("?", 1)[0]
    allowed = {os.getenv("TECHPULSE_DATABASE_NAME", "techpulse_sim"), os.getenv("TECHPULSE_TEST_DATABASE_NAME", "techpulse_sim_test")}
    if database not in allowed:
        raise RuntimeError(f"Refusing migrations against {database!r}; allowed databases are {sorted(allowed)}.")
    return value


def apply_migrations(url: str | None = None, engine: Engine | None = None) -> list[str]:
    """Apply pending SQL migrations atomically and reject edits to applied files."""
    owned_engine = engine is None
    engine = engine or create_engine(_database_url(url), pool_pre_ping=True)
    applied: list[str] = []
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS ml"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS ml.schema_migrations (
                    version text PRIMARY KEY,
                    checksum char(64) NOT NULL,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
            """))
            for path in sorted(MIGRATION_DIR.glob("*.sql")):
                source = path.read_text(encoding="utf-8")
                digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
                prior = connection.execute(
                    text("SELECT checksum FROM ml.schema_migrations WHERE version=:v"),
                    {"v": path.stem},
                ).scalar_one_or_none()
                if prior:
                    if prior.strip() != digest:
                        raise RuntimeError(f"Migration checksum mismatch for {path.name}; do not edit an applied migration.")
                    continue
                connection.exec_driver_sql(source)
                connection.execute(
                    text("INSERT INTO ml.schema_migrations(version,checksum) VALUES (:v,:c)"),
                    {"v": path.stem, "c": digest},
                )
                applied.append(path.stem)
        return applied
    finally:
        if owned_engine:
            engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply TechPulse Simulation PostgreSQL migrations")
    parser.add_argument("--test", action="store_true", help="Apply to TECHPULSE_TEST_DATABASE_URL only")
    args = parser.parse_args()
    url = os.getenv("TECHPULSE_TEST_DATABASE_URL") if args.test else os.getenv("DATABASE_URL")
    print({"target": "test" if args.test else "application", "applied": apply_migrations(url)})


if __name__ == "__main__":
    main()
