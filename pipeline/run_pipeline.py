"""Master TechPulse pipeline orchestration script."""

from __future__ import annotations

import hashlib
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import data_ingestion, eda, evaluation, feature_engineering, labelling, model_training, shap_analysis  # noqa: E402
from src.common import DATA_DIR, LOGS_DIR, ensure_directories  # noqa: E402


def _md5(path: Path) -> str:
    """Compute an MD5 checksum for a file.

    Args:
        path: File path.

    Returns:
        Hex digest.
    """
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _configure_pipeline_logger() -> logging.Logger:
    """Configure timestamped pipeline logging.

    Returns:
        Pipeline logger.
    """
    ensure_directories()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = logging.getLogger("techpulse.pipeline")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOGS_DIR / f"pipeline_{stamp}.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def run_pipeline() -> list[tuple[str, str]]:
    """Run FR-01 through FR-11 end-to-end.

    Returns:
        List of step outcomes as (step, status).

    Raises:
        Exception: Re-raises the first failed step after logging stack trace.
    """
    logger = _configure_pipeline_logger()
    outcomes: list[tuple[str, str]] = []
    datasets = None
    steps = [
        ("FR-01 data_ingestion.load_and_validate_datasets", lambda: data_ingestion.load_and_validate_datasets()),
        ("FR-02 eda.generate_eda_report", lambda: eda.generate_eda_report(datasets)),
        ("FR-03 feature_engineering.compute_feature_matrix", lambda: feature_engineering.compute_feature_matrix(datasets)),
        ("FR-04 labelling.assign_trajectory_labels", lambda: labelling.assign_trajectory_labels()),
        ("FR-05-FR-09 model_training.train_all_models", lambda: model_training.train_all_models()),
        ("FR-10 evaluation.compare_and_select_best_model", lambda: evaluation.compare_and_select_best_model()),
        ("FR-11 shap_analysis.run_shap_analysis", lambda: shap_analysis.run_shap_analysis()),
    ]
    for name, action in steps:
        try:
            logger.info("Starting %s", name)
            result = action()
            if name.startswith("FR-01"):
                datasets = result
            if name.startswith("FR-03"):
                logger.info("feature_matrix.csv MD5=%s", _md5(DATA_DIR / "feature_matrix.csv"))
            outcomes.append((name, "PASS"))
            logger.info("Completed %s", name)
        except Exception as exc:
            outcomes.append((name, "FAIL"))
            logger.error("%s failed: %s: %s", name, type(exc).__name__, exc)
            logger.error(traceback.format_exc())
            print_summary(outcomes)
            raise
    print_summary(outcomes)
    return outcomes


def print_summary(outcomes: list[tuple[str, str]]) -> None:
    """Print a compact step outcome table.

    Args:
        outcomes: Step outcomes.

    Returns:
        None.
    """
    print("\nTechPulse Pipeline Summary")
    print("Step | Status")
    print("--- | ---")
    for step, status in outcomes:
        print(f"{step} | {status}")


if __name__ == "__main__":
    run_pipeline()
