"""Readiness gates keep incomplete and demonstration data out of research ML."""

import json

import pytest

from src.research_readiness import (
    ResearchReadinessError,
    require_research_source_manifest,
    require_validated_research_datasets,
)


def test_research_manifest_rejects_demo_and_proxy_sources(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "source_mode": "local_development_csv",
        "research_grade": False,
        "tables": {"fortune500_stacks": {"is_proxy": True}},
    }))
    with pytest.raises(ResearchReadinessError, match="not exclusively PostgreSQL"):
        require_research_source_manifest(path)


def test_research_manifest_accepts_postgres_only_sources(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "source_mode": "postgresql_canonical_compatibility",
        "research_grade": True,
        "tables": {"community": {"is_proxy": False}},
    }))
    assert require_research_source_manifest(path)["research_grade"] is True


def test_dataset_gate_stops_when_any_source_fails_or_community_is_blocked(tmp_path):
    path = tmp_path / "quality.json"
    path.write_text(json.dumps({
        "so_questions": {"passed": False},
        "dev_sentiment": {"passed": True},
        "_pipeline_readiness": {
            "all_datasets_passed": False,
            "critical_community_validation_failures": 1,
        },
    }))
    with pytest.raises(ResearchReadinessError, match="failed_datasets=.*so_questions"):
        require_validated_research_datasets(path)


def test_dataset_gate_accepts_all_validated_source_contracts(tmp_path):
    path = tmp_path / "quality.json"
    names = ["so_questions", "dev_sentiment", "fortune500_stacks", "company_profiles", "tech_metadata", "question_company_mapping"]
    report = {name: {"passed": True} for name in names}
    report["_pipeline_readiness"] = {
        "all_datasets_passed": True,
        "critical_community_validation_failures": 0,
    }
    path.write_text(json.dumps(report))
    assert require_validated_research_datasets(path)["_pipeline_readiness"]["all_datasets_passed"]
