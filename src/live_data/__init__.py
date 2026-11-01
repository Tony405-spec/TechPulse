"""Incremental public API observations, separate from model training inputs."""

from src.live_data.service import collect_live_data

__all__ = ["collect_live_data"]
