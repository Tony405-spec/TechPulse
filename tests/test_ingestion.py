"""Tests for data ingestion contracts."""

from __future__ import annotations

import json

from src.data_ingestion import TABLES, _validate_frame, load_local_development_datasets
from src.common import OUTPUTS_DIR


def test_all_six_tables_loaded(sample_datasets):
    """Assert all six required datasets are represented."""
    assert set(sample_datasets) == set(TABLES)


def test_minimum_row_count(sample_datasets):
    """Assert fixture datasets contain at least one row."""
    for frame in sample_datasets.values():
        assert len(frame) >= 1


def test_data_quality_report_written(sample_datasets):
    """Assert the quality report JSON can be written after validation."""
    report = {name: _validate_frame(name, frame) for name, frame in sample_datasets.items()}
    path = OUTPUTS_DIR / "data_quality_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report), encoding="utf-8")
    assert path.exists()


def test_local_manifest_marks_proxy_tables():
    """Assert local fallback provenance distinguishes proxy tables."""
    load_local_development_datasets()
    manifest = json.loads((OUTPUTS_DIR / "data_sources.json").read_text(encoding="utf-8"))
    assert manifest["source_mode"] == "local_development_csv"
    assert manifest["research_grade"] is False
    assert manifest["tables"]["fortune500_stacks"]["is_proxy"] is True
    assert "is_proxy" in manifest["tables"]["dev_sentiment"]
