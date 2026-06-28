"""Compatibility entry point for SHAP explainability.

The redesigned explainability implementation lives in :mod:`src.shap_analysis`.
This module keeps legacy CI jobs that execute ``python src/explain.py`` working.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    """Run SHAP analysis when best-model artifacts are available.

    Returns:
        None.
    """
    try:
        from src.shap_analysis import run_shap_analysis

        importance = run_shap_analysis()
    except Exception as exc:  # noqa: BLE001
        print(
            "SHAP analysis skipped. Run training and evaluation first so "
            f"best-model artifacts exist. Reason: {exc}"
        )
        return
    print(importance.to_string(index=False))


if __name__ == "__main__":
    main()
