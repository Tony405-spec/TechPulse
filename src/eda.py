"""Exploratory data analysis reporting for TechPulse."""

from __future__ import annotations

import json
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
    _plot_technology_frequency(datasets)
    _plot_community_activity(datasets)
    _plot_sentiment_distribution(datasets)
    (OUTPUTS_DIR / "eda_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def _first_column(frame: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {column.lower(): column for column in frame.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def _plot_technology_frequency(datasets: dict[str, pd.DataFrame]) -> None:
    frame = datasets.get("so_questions", pd.DataFrame())
    tech = _first_column(frame, ["technology", "tag", "technology_name"])
    volume = _first_column(frame, ["question_count", "count"])
    if frame.empty or tech is None:
        return
    counts = (
        frame.assign(_volume=pd.to_numeric(frame[volume], errors="coerce").fillna(1) if volume else 1)
        .groupby(tech)["_volume"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
    )
    plt.figure(figsize=(10, 6))
    counts.sort_values().plot(kind="barh", color="#00ff41")
    plt.title("Top Technologies by Community Question Volume")
    plt.xlabel("Questions")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "eda_technology_frequency.png", dpi=150)
    plt.close()


def _plot_community_activity(datasets: dict[str, pd.DataFrame]) -> None:
    frame = datasets.get("so_questions", pd.DataFrame())
    date = _first_column(frame, ["creation_date", "date", "created_at"])
    volume = _first_column(frame, ["question_count", "count"])
    if frame.empty or date is None:
        return
    work = frame.copy()
    work[date] = pd.to_datetime(work[date], errors="coerce")
    work["_volume"] = pd.to_numeric(work[volume], errors="coerce").fillna(1) if volume else 1
    monthly = work.dropna(subset=[date]).set_index(date)["_volume"].resample("MS").sum()
    if monthly.empty:
        return
    plt.figure(figsize=(10, 5))
    monthly.plot(color="#00d9ff")
    plt.title("Community Activity Trend")
    plt.ylabel("Questions")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "eda_community_activity_trend.png", dpi=150)
    plt.close()


def _plot_sentiment_distribution(datasets: dict[str, pd.DataFrame]) -> None:
    frame = datasets.get("dev_sentiment", pd.DataFrame())
    score = _first_column(frame, ["satisfaction_score", "satisfaction", "sentiment_score"])
    if frame.empty or score is None:
        return
    values = pd.to_numeric(frame[score], errors="coerce").dropna()
    if values.empty:
        return
    plt.figure(figsize=(8, 5))
    values.plot(kind="hist", bins=20, color="#bf00ff", edgecolor="#111111")
    plt.title("Developer Sentiment Distribution")
    plt.xlabel("Satisfaction Score")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "eda_sentiment_distribution.png", dpi=150)
    plt.close()
