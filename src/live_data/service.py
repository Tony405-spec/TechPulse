"""Coordinate source-level collection, validation, persistence and status."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

from src.data_ingestion import append_external_observations
from src.live_data.collectors import COLLECTORS, load_package_map
from src.live_data.storage import update_status

LOGGER = logging.getLogger(__name__)
SOURCES = tuple(COLLECTORS)


def collect_live_data(technology: str, sources: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Collect selected sources for one catalog technology; isolate each source failure."""
    if not technology or not technology.strip():
        raise ValueError("A technology name is required")
    load_dotenv()
    chosen = sources or list(SOURCES)
    invalid = set(chosen).difference(SOURCES)
    if invalid:
        raise ValueError(f"Unknown live data source(s): {sorted(invalid)}")
    try:
        package_map = load_package_map()
        package_map_error = None
    except Exception as exc:
        package_map = {}
        package_map_error = f"{type(exc).__name__}: {exc}"
        LOGGER.exception("The explicit package map could not be loaded")
    outcomes: dict[str, dict[str, Any]] = {}
    for source in chosen:
        if source in {"pypi", "npm"}:
            if package_map_error:
                update_status(source, status="failed", technology=technology, error=package_map_error)
                outcomes[source] = {"status": "failed", "records_written": 0, "message": package_map_error}
                continue
            mapped = any(key.casefold() == technology.casefold() and source in packages for key, packages in package_map.items())
            if not mapped:
                note = f"No {source} package is mapped to this catalog technology. Add a verified mapping in data/live_package_map.json."
                update_status(source, status="skipped", technology=technology, error=note)
                outcomes[source] = {"status": "skipped", "records_written": 0, "message": note}
                continue
        update_status(source, status="running", technology=technology)
        try:
            records = COLLECTORS[source](technology)
            written = append_external_observations(records)
            outcome = {"status": "success", "records_written": written, "observations_returned": len(records)}
            update_status(source, status="success", technology=technology, records=written)
            LOGGER.info("Collected %s: %s records for %s", source, written, technology)
        except Exception as exc:  # isolate APIs and allow other source results to be saved
            message = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("Live %s collection failed for %s", source, technology)
            outcome = {"status": "failed", "records_written": 0, "message": message}
            update_status(source, status="failed", technology=technology, error=message)
        outcomes[source] = outcome
    return outcomes
