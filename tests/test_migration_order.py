"""Ensure schema migrations can run before optional demo data is imported."""

from src.cli import _demo_migration_ready


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class _Connection:
    def __init__(self, exists):
        self.exists = exists
        self.requested_relation = None

    def execute(self, _query, params):
        self.requested_relation = params["relation"]
        return _Result(self.exists)


def test_demo_data_migration_waits_until_source_tables_exist():
    connection = _Connection(False)
    assert not _demo_migration_ready(connection, "004_demo_latest_features")
    assert connection.requested_relation == "demo.feature_snapshots"


def test_demo_data_migration_runs_after_source_tables_exist():
    assert _demo_migration_ready(_Connection(True), "005_demo_model_selection")


def test_canonical_migrations_do_not_require_demo_tables():
    assert _demo_migration_ready(_Connection(False), "001_canonical_schema")
