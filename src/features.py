"""Compatibility entry point for feature matrix generation.

The redesigned pipeline lives in :mod:`src.feature_engineering`. This module is
kept so legacy CI jobs that execute ``python src/features.py`` continue to work.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.feature_engineering import compute_feature_matrix  # noqa: E402


def main() -> None:
    """Run a best-effort feature generation command.

    Returns:
        None.
    """
    try:
        from src.data_ingestion import load_and_validate_datasets

        datasets = load_and_validate_datasets()
        compute_feature_matrix(datasets)
        print("Feature matrix generated at data/feature_matrix.csv")
    except Exception as exc:  # noqa: BLE001
        print(
            "Feature generation skipped. Configure DATABASE_URL and install "
            f"dependencies to run against PostgreSQL. Reason: {exc}"
        )


if __name__ == "__main__":
    main()
