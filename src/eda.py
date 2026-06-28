"""Exploratory data analysis reporting for TechPulse."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.common import OUTPUTS_DIR, ensure_directories


def generate_eda_report(datasets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Generate a lightweight EDA report for all loaded datasets.

    Args:
        datasets: Mapping of dataset names to DataFrames.

    Returns:
        Dictionary with shape, missingness, and column summaries.
    """
    ensure_directories()
    report: dict[str, Any] = {}
    for name, frame in datasets.items():
        report[name] = {
            "rows": int(len(frame)),
            "columns": int(len(frame.columns)),
            "column_names": frame.columns.tolist(),
            "missing_values": frame.isna().sum().astype(int).to_dict(),
        }
    (OUTPUTS_DIR / "eda_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
