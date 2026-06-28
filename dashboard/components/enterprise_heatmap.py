"""Enterprise adoption heatmap component."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def enterprise_heatmap(frame: pd.DataFrame):
    """Create a sector adoption heatmap.

    Args:
        frame: DataFrame with sector and count columns.

    Returns:
        Plotly figure or None.
    """
    if frame is None or frame.empty:
        return None
    pivot = frame.pivot_table(index="sector", values="adoption_count", aggfunc="sum")
    return px.imshow(
        pivot,
        text_auto=True,
        color_continuous_scale=["#F4B942", "#2E9E6B"],
        aspect="auto",
    )
