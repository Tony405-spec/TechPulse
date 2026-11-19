"""Hard gates that prevent demo/proxy inputs from reaching research modeling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ResearchReadinessError(RuntimeError):
    """Raised when the current inputs cannot support research computation."""


def require_research_source_manifest(path: Path) -> dict[str, Any]:
    """Require a PostgreSQL source manifest with no synthetic/proxy inputs."""
    if not path.exists():
        raise ResearchReadinessError(f"Source manifest is missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mode = str(manifest.get("source_mode", ""))
    tables = manifest.get("tables", {})
    proxy_tables = sorted(
        name for name, details in tables.items()
        if bool(details.get("is_proxy"))
    )
    if not mode.startswith("postgresql") or manifest.get("research_grade") is not True or proxy_tables:
        raise ResearchReadinessError(
            "Research computation blocked: inputs are not exclusively PostgreSQL research sources. "
            f"source_mode={mode or 'unknown'}; proxy_tables={proxy_tables}."
        )
    return manifest


def require_validated_research_datasets(path: Path) -> dict[str, Any]:
    """Require all six SRS datasets to pass configured source-quality checks."""
    if not path.exists():
        raise ResearchReadinessError(f"Data-quality report is missing: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    readiness = report.get("_pipeline_readiness", {})
    failed = sorted(
        name for name, result in report.items()
        if name != "_pipeline_readiness" and not result.get("passed", False)
    )
    critical = int(readiness.get("critical_community_validation_failures", 0) or 0)
    if failed or critical or not readiness.get("all_datasets_passed", False):
        raise ResearchReadinessError(
            "Research feature/model stages blocked by the SRS data-quality gate. "
            f"failed_datasets={failed}; critical_community_validation_failures={critical}. "
            "Review outputs/data_quality_report.json; no labels or research model were created."
        )
    return report
