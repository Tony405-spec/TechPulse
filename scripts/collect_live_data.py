"""Run one bounded live-data collection job independently of Streamlit."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from src.live_data.service import SOURCES, collect_live_data  # noqa: E402
from src.live_data.storage import LIVE_DATA_DIR, read_status, update_status  # noqa: E402


def default_technologies(limit: int = 10) -> list[str]:
    """Pick a bounded set from the existing prediction catalogue by local activity."""
    import pandas as pd

    predictions_path = ROOT / "outputs" / "technology_predictions.csv"
    stack_path = ROOT / "data" / "stackexchange.csv"
    if not predictions_path.exists():
        raise FileNotFoundError("The saved technology catalogue is missing: outputs/technology_predictions.csv")
    predictions = pd.read_csv(predictions_path)
    if "technology_name" not in predictions:
        raise ValueError("The saved technology catalogue has no technology_name column")
    catalog = predictions["technology_name"].dropna().astype(str).drop_duplicates().tolist()
    if stack_path.exists():
        community = pd.read_csv(stack_path)
        if {"tag", "question_count"}.issubset(community.columns):
            weights = community.groupby("tag")["question_count"].sum().to_dict()
            catalog.sort(key=lambda name: (-float(weights.get(name, 0) or 0), name.casefold()))
    return catalog[:max(1, limit)]


def validate_catalog_technologies(values: list[str]) -> list[str]:
    """Require explicit targets to exist in the saved TechPulse catalogue."""
    import pandas as pd

    path = ROOT / "outputs" / "technology_predictions.csv"
    if not path.exists():
        raise FileNotFoundError("The saved technology catalogue is missing: outputs/technology_predictions.csv")
    frame = pd.read_csv(path)
    if "technology_name" not in frame:
        raise ValueError("The saved technology catalogue has no technology_name column")
    canonical = {value.casefold(): value for value in frame["technology_name"].dropna().astype(str).drop_duplicates()}
    unknown = [value for value in values if value.casefold() not in canonical]
    if unknown:
        raise ValueError(f"Technology not found in the saved TechPulse catalogue: {unknown}")
    return list(dict.fromkeys(canonical[value.casefold()] for value in values))


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technology", action="append", help="Technology in the existing saved catalogue; repeat to collect more than one")
    parser.add_argument("--source", action="append", choices=SOURCES, help="Restrict source; may be repeated")
    parser.add_argument("--max-technologies", type=int, default=int(os.getenv("TECHPULSE_LIVE_MAX_TECHNOLOGIES", "5")))
    args = parser.parse_args()
    technologies = validate_catalog_technologies(args.technology) if args.technology else default_technologies(args.max_technologies)
    LIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LIVE_DATA_DIR / "collection.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    update_status(job={"status": "running", "job_type": "manual", "pid": os.getpid(), "started_at": pd_now(), "technologies": technologies})
    results = {}
    for technology in technologies:
        results[technology] = collect_live_data(technology, args.source)
    failures = [
        f"{technology}/{source}: {result['message']}"
        for technology, outcomes in results.items()
        for source, result in outcomes.items()
        if result["status"] == "failed"
    ]
    update_status(job={
        "status": "completed_with_errors" if failures else "completed",
        "job_type": "manual",
        "pid": os.getpid(),
        "finished_at": pd_now(),
        "technologies": technologies,
        "failures": failures,
    })
    print(json.dumps(results, indent=2))
    return 1 if failures else 0


def pd_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
