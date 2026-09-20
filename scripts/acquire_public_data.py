"""Acquire permitted public datasets used by TechPulse."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_acquisition.developer_survey import build_developer_survey_usage  # noqa: E402


def main() -> None:
    """Acquire and aggregate public data sources."""
    parser = argparse.ArgumentParser(description="Acquire permitted public TechPulse datasets.")
    parser.add_argument("--years", nargs="*", type=int, default=[2021, 2022, 2023, 2024])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    usage = build_developer_survey_usage(years=tuple(args.years), refresh=args.refresh)
    print(
        "Stack Overflow Developer Survey usage rows="
        f"{len(usage)} technologies={usage['technology_name'].nunique()}"
    )


if __name__ == "__main__":
    main()
