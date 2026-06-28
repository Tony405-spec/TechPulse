"""Tests for data ingestion contracts."""

from __future__ import annotations

import json

from src.data_ingestion import TABLES, _validate_frame
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
