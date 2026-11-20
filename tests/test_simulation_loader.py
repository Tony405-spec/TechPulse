import os

import pytest
from sqlalchemy import create_engine, text

from src.db.load_sim import load_corpus
from src.db.migrate import apply_migrations
from src.simulate import simulate_corpus


TEST_URL = os.getenv("TECHPULSE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="Set TECHPULSE_TEST_DATABASE_URL to the dedicated techpulse_sim_test DB.")


@pytest.fixture(scope="module")
def corpus():
    return simulate_corpus()


def test_loader_loads_verifies_and_is_idempotent(corpus):
    apply_migrations(TEST_URL)
    first = load_corpus(corpus, TEST_URL)
    second = load_corpus(corpus, TEST_URL)
    # This dedicated test DB may already contain the same deterministic version
    # from an earlier test run; both first-load and rerun paths are valid.
    assert first["inserted"] in {True, False}
    assert second["inserted"] is False
    assert first["row_counts"] == corpus.data_version["expected_counts"]
    assert set(first["orphan_counts"].values()) == {0}
    engine = create_engine(TEST_URL)
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT seed,config_hash,generator_version,git_commit,status,class_distribution FROM ml.data_versions WHERE data_version_id=:v"), {"v": corpus.data_version["data_version_id"]}).mappings().one()
            assert version["seed"] == 42
            assert version["config_hash"].strip() == corpus.data_version["config_hash"]
            assert version["generator_version"] == corpus.data_version["generator_version"]
            assert version["status"] == "verified"
            assert version["class_distribution"] == corpus.data_version["class_distribution"]
            assert connection.execute(text("SELECT count(*) FROM ml.feature_snapshots WHERE data_version_id=:v"), {"v": corpus.data_version["data_version_id"]}).scalar_one() == 0
    finally:
        engine.dispose()
