"""Compatibility entry point for model training.

The redesigned training implementation lives in :mod:`src.model_training`.
This module keeps legacy CI jobs that execute ``python src/train.py`` working.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_training import train_all_models  # noqa: E402


def main() -> None:
    """Run model training when a labelled feature matrix is available.

    Returns:
        None.
    """
    try:
        artifacts = train_all_models()
    except Exception as exc:  # noqa: BLE001
        print(
            "Model training skipped. Run the pipeline first so "
            f"data/feature_matrix.csv exists. Reason: {exc}"
        )
        return
    for name, path in artifacts.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
