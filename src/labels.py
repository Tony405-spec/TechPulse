"""Shared, config-driven trajectory labeller used by the simulation experiment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_label_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "labels.yaml"
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def label_trajectory(recent_values, future_values, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Label trailing-three-month mean against the next-six-month mean.

    Returns an incomplete result rather than manufacturing a label when either
    window is unavailable. Ambiguity influences measurement upstream only.
    """
    cfg = config or load_label_config()
    recent_n = int(cfg["recent_window_months"])
    future_n = int(cfg["future_horizon_months"])
    recent = [float(v) for v in recent_values[-recent_n:] if v is not None]
    future = [float(v) for v in future_values[:future_n] if v is not None]
    if len(recent) != recent_n or len(future) != future_n:
        return {"label": None, "ratio": None, "recent_mean": None, "future_mean": None}
    recent_mean = sum(recent) / recent_n
    future_mean = sum(future) / future_n
    if recent_mean < float(cfg["minimum_recent_mean"]):
        return {"label": None, "ratio": None, "recent_mean": recent_mean, "future_mean": future_mean}
    ratio = future_mean / recent_mean
    if ratio >= float(cfg["growing_ratio_threshold"]):
        label = "Growing"
    elif ratio <= float(cfg["declining_ratio_threshold"]):
        label = "Declining"
    else:
        label = "Stable"
    return {"label": label, "ratio": ratio, "recent_mean": recent_mean, "future_mean": future_mean}
