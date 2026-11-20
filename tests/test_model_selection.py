"""Selection must be dynamic and inconclusive without complete comparable evidence."""

import pandas as pd

from dashboard.model_selection import select_best_model


def _fixtures():
    runs = pd.DataFrame([
        {"model_run_id": f"r{i}", "candidate_id": i, "model_name": name,
         "metric_name": metric, "metric_value": value, "run_freshness": "valid",
         "candidate_status": "succeeded", "status": "succeeded", "split_name": "test",
         "auditable": True, "feature_snapshot_id": "snapshot-a", "label_definition_id": 1,
         "label_name": "future-window", "label_version": "1", "split_metadata": {"method": "temporal"}}
        for i, name, score in [(1, "Model A", .72), (2, "Model B", .68)]
        for metric, value in [("macro_f1", score), ("weighted_f1", score + .05), ("accuracy", score + .06)]
    ])
    class_rows = []
    for candidate, scores in [(1, (.72, .80, .60)), (2, (.68, .72, .63))]:
        for label, f1 in zip(("Growing", "Stable", "Declining"), scores):
            class_rows.append({"candidate_id": candidate, "class_name": label,
                               "precision": f1, "recall": f1, "f1": f1, "support": 20})
    return runs, pd.DataFrame(class_rows)


def test_macro_f1_selects_winner_and_exposes_class_metrics():
    runs, classes = _fixtures()
    result = select_best_model(runs, classes)
    assert result["model_name"] == "Model A"
    assert result["macro_f1"] == .72
    assert len(result["class_metrics"]) == 3


def test_no_evaluations_is_inconclusive():
    runs, classes = _fixtures()
    assert select_best_model(runs.iloc[0:0], classes) is None


def test_incompatible_cohorts_do_not_produce_winner():
    runs, classes = _fixtures()
    runs.loc[runs.model_name.eq("Model B"), "feature_snapshot_id"] = "snapshot-b"
    assert select_best_model(runs, classes) is None


def test_insufficient_class_support_does_not_produce_winner():
    runs, classes = _fixtures()
    classes.loc[(classes.candidate_id.eq(1)) & (classes.class_name.eq("Declining")), "support"] = 4
    assert select_best_model(runs, classes) is None


def test_new_eligible_evaluation_changes_the_dynamic_winner():
    runs, classes = _fixtures()
    before = select_best_model(runs, classes)
    new_run = runs[runs.candidate_id.eq(2)].copy()
    new_run["model_run_id"] = "r3"
    new_run["candidate_id"] = 3
    new_run["model_name"] = "Model C"
    new_run.loc[new_run.metric_name.eq("macro_f1"), "metric_value"] = .91
    new_run.loc[new_run.metric_name.eq("weighted_f1"), "metric_value"] = .90
    new_run.loc[new_run.metric_name.eq("accuracy"), "metric_value"] = .89
    new_classes = classes[classes.candidate_id.eq(2)].copy()
    new_classes["candidate_id"] = 3
    new_classes["f1"] = [.90, .91, .92]
    new_classes["recall"] = [.90, .91, .92]
    after = select_best_model(pd.concat([runs, new_run]), pd.concat([classes, new_classes]))
    assert before["model_name"] == "Model A"
    assert after["model_name"] == "Model C"


def test_tied_macro_f1_uses_class_performance_tie_breaker():
    runs, classes = _fixtures()
    runs.loc[(runs.model_name.eq("Model A")) & runs.metric_name.eq("macro_f1"), "metric_value"] = .70
    runs.loc[(runs.model_name.eq("Model B")) & runs.metric_name.eq("macro_f1"), "metric_value"] = .70
    # Model B has stronger weakest-class recall/F1.
    result = select_best_model(runs, classes)
    assert result["model_name"] == "Model B"
