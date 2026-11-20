"""Run the deterministic simulation, verified load, features, grouped modelling and SHAP."""

from __future__ import annotations

import json
import logging

from src.db.load_sim import load_corpus
from src.db.migrate import apply_migrations
from src.experiment.features import persist_features
from src.experiment.modeling import run_experiment
from src.simulate import simulate_corpus


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Applying idempotent migrations to dedicated simulation database")
    apply_migrations()
    logging.info("Generating configured simulation corpus")
    corpus = simulate_corpus()
    logging.info("Loading and verifying simulated source tables")
    load_result = load_corpus(corpus)
    logging.info("Persisting as-of feature snapshots and shared-labeller targets")
    feature_result = persist_features(corpus)
    logging.info("Training grouped nested models and computing explanations")
    experiment = run_experiment(corpus.data_version["data_version_id"])
    print(json.dumps({"load": load_result, "features": feature_result,
                      "experiment": experiment.result_summary}, indent=2, default=str))


if __name__ == "__main__":
    main()
