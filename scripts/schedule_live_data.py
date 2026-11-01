"""Daily scheduler for live sources; run as a service/task outside Streamlit."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from scripts.collect_live_data import default_technologies, validate_catalog_technologies  # noqa: E402
from src.live_data.service import SOURCES, collect_live_data  # noqa: E402
from src.live_data.storage import LIVE_DATA_DIR, read_status, update_status  # noqa: E402


def scheduled_technologies(limit: int) -> list[str]:
    configured = os.getenv("TECHPULSE_LIVE_TECHNOLOGIES", "").strip()
    if configured:
        values = list(dict.fromkeys(value.strip() for value in configured.split(",") if value.strip()))
        return validate_catalog_technologies(values)
    return default_technologies(limit)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-hours", type=float, default=float(os.getenv("TECHPULSE_LIVE_INTERVAL_HOURS", "24")))
    parser.add_argument("--max-technologies", type=int, default=int(os.getenv("TECHPULSE_LIVE_MAX_TECHNOLOGIES", "5")))
    parser.add_argument("--once", action="store_true", help="Run one scheduled batch and exit")
    args = parser.parse_args()
    if args.interval_hours <= 0:
        parser.error("--interval-hours must be positive")
    LIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LIVE_DATA_DIR / "scheduler.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    interval = timedelta(hours=args.interval_hours)
    next_run = datetime.now(timezone.utc)
    while True:
        wait = (next_run - datetime.now(timezone.utc)).total_seconds()
        if wait > 0:
            time.sleep(wait)
        active_job = read_status().get("job", {})
        while active_job.get("status") in {"starting", "running"}:
            logging.info("Another live collection job is active; waiting before starting scheduled batch")
            time.sleep(5)
            active_job = read_status().get("job", {})
        targets = scheduled_technologies(args.max_technologies)
        update_status(job={"status": "running", "job_type": "scheduled", "scheduler_started_at": datetime.now(timezone.utc).isoformat(), "technologies": targets})
        failures = []
        for technology in targets:
            for source, outcome in collect_live_data(technology).items():
                if outcome["status"] == "failed":
                    failures.append(f"{technology}/{source}: {outcome['message']}")
        update_status(job={
            "status": "completed_with_errors" if failures else "completed",
            "job_type": "scheduled",
            "scheduler": "completed_with_errors" if failures else "completed",
            "scheduler_finished_at": datetime.now(timezone.utc).isoformat(),
            "scheduler_failures": failures,
        })
        logging.info("Batch complete: technologies=%d failures=%d", len(targets), len(failures))
        if args.once:
            return 1 if failures else 0
        next_run = datetime.now(timezone.utc) + interval


if __name__ == "__main__":
    raise SystemExit(main())
