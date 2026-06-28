"""Plotly trend charts for TechPulse technology details."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def _insufficient(frame: pd.DataFrame) -> bool:
    """Return whether a trend frame has fewer than three points.

    Args:
        frame: Trend DataFrame.

    Returns:
        True when plotting should be skipped.
    """
    return frame is None or len(frame) < 3


def so_volume_chart(frame: pd.DataFrame):
    """Create a monthly Stack Overflow volume line chart.

    Args:
        frame: DataFrame with date and value columns.

    Returns:
        Plotly figure or None.
    """
    if _insufficient(frame):
        return None
    fig = px.line(frame, x="date", y="value", markers=True)
    fig.update_yaxes(rangemode="tozero")
    return fig


def sentiment_chart(frame: pd.DataFrame):
    """Create a developer sentiment trend chart.

    Args:
        frame: DataFrame with date and value columns.

    Returns:
        Plotly figure or None.
    """
    if _insufficient(frame):
        return None
    fig = px.line(frame, x="date", y="value", markers=True)
    fig.update_yaxes(rangemode="tozero")
    return fig


def adoption_chart(frame: pd.DataFrame):
    """Create an annual company adoption bar chart.

    Args:
        frame: DataFrame with date and value columns.

    Returns:
        Plotly figure or None.
    """
    if _insufficient(frame):
        return None
    fig = px.bar(frame, x="date", y="value")
    fig.update_yaxes(rangemode="tozero")
    return fig
