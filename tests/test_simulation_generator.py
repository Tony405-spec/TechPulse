from src.labels import label_trajectory
from src.simulate import TABLES, simulate_corpus


def test_shared_label_rule_boundaries_and_missing_windows():
    config = {
        "recent_window_months": 3, "future_horizon_months": 6,
        "growing_ratio_threshold": 1.2, "declining_ratio_threshold": .8,
        "minimum_recent_mean": 1,
    }
    assert label_trajectory([10, 10, 10], [12] * 6, config)["label"] == "Growing"
    assert label_trajectory([10, 10, 10], [8] * 6, config)["label"] == "Declining"
    assert label_trajectory([10, 10, 10], [10] * 6, config)["label"] == "Stable"
    assert label_trajectory([10, 10], [10] * 6, config)["label"] is None


def test_generator_is_seeded_and_has_expected_source_shapes():
    first = simulate_corpus()
    second = simulate_corpus()
    assert first.data_version["config_hash"] == second.data_version["config_hash"]
    assert first.data_version["table_checksums"] == second.data_version["table_checksums"]
    assert set(first.tables) == set(TABLES)
    assert len(first.tables["technology_metadata"]) == 300
    assert len(first.tables["company_profiles"]) == 500
    assert len(first.tables["stack_overflow_questions"]) == 36_000
    assert first.data_version["class_distribution"] == {
        "Growing": sum(first.anchor_labels.trajectory_label == "Growing"),
        "Stable": sum(first.anchor_labels.trajectory_label == "Stable"),
        "Declining": sum(first.anchor_labels.trajectory_label == "Declining"),
    }
    assert all(set(frame.data_origin.unique()) <= {"SYNTHETIC_SIMULATION"} for frame in first.tables.values())
    assert first.anchor_labels.trajectory_label.dropna().isin(["Growing", "Stable", "Declining"]).all()

