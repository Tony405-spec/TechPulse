"""Integration checks use only the dedicated throwaway techpulse_sim_test DB."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from src.db.migrate import apply_migrations


TEST_URL = os.getenv("TECHPULSE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="Set TECHPULSE_TEST_DATABASE_URL to techpulse_sim_test.")


def test_migrations_apply_and_rerun_cleanly_on_test_database():
    first = apply_migrations(TEST_URL)
    second = apply_migrations(TEST_URL)
    assert isinstance(first, list)
    assert second == []
    engine = create_engine(TEST_URL)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM ml.schema_migrations")).scalar() >= 1
            schemas = set(connection.execute(text("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name IN ('sim','ml')
            """)).scalars())
            assert schemas == {"sim", "ml"}
    finally:
        engine.dispose()


def test_simulation_schema_views_expose_legacy_contracts():
    engine = create_engine(TEST_URL)
    try:
        with engine.connect() as connection:
            expected = {
                "sim.so_questions": {"technology","tag","creation_date","question_count","unanswered_count"},
                "sim.dev_sentiment": {"technology","survey_year","satisfaction_score"},
                "sim.tech_metadata": {"technology","technology_name","category"},
                "sim.stackoverflow": {"tag","date","question_count","unanswered_pct"},
                "sim.tag_company": {"tag","company_id","adoption_date"},
            }
            for relation, columns in expected.items():
                schema, name = relation.split(".")
                actual = set(connection.execute(text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema=:schema AND table_name=:name
                """), {"schema": schema, "name": name}).scalars())
                assert columns <= actual, (relation, columns - actual)
            assert connection.execute(text("""
                SELECT to_regclass('ml.watchlist') IS NOT NULL
            """)).scalar_one()
    finally:
        engine.dispose()
