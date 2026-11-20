"""Diagnostic-only analysis of the v1 synthetic label/noise ceiling.

This script reconstructs the simulator's latent curves from the checked-in
seed/configuration solely for oracle diagnostics. Latent values are never
persisted, added to ml.feature_snapshots, or used by the production pipeline.
It reads the existing v1 labels/features/predictions and does not write to DB.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.migrate import _database_url
from src.experiment.features import FEATURE_COLUMNS, _slope
from src.experiment.modeling import _make_pipeline, grouped_cv_splits, grouped_train_test_indices
from src.simulate import _latent_curve
from src.experiment.features import read_training_frame
from sqlalchemy import create_engine, text

CLASSES = ["Growing", "Stable", "Declining"]


def config(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def reconstruct_latent_curves(sim_cfg: dict) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Replay only the initial RNG draws made by simulate_corpus's tech loop."""
    rng = np.random.default_rng(int(sim_cfg["seed"]))
    categories = list(sim_cfg["categories"])
    cat_weights = np.asarray(list(sim_cfg["categories"].values()), dtype=float)
    cat_weights /= cat_weights.sum()
    families = list(sim_cfg["curve_families"])
    family_weights = np.asarray(list(sim_cfg["curve_families"].values()), dtype=float)
    family_weights /= family_weights.sum()
    count, months = int(sim_cfg["technology_count"]), int(sim_cfg["months"])
    category_factor = {c: float(rng.lognormal(0, 0.12)) for c in categories}
    curves, family_by_tech = {}, {}
    for idx in range(1, count + 1):
        tid = f"SIM-TECH-{idx:04d}"
        category = str(rng.choice(categories, p=cat_weights))
        family = str(rng.choice(families, p=family_weights))
        curves[tid] = _latent_curve(rng, family, months, sim_cfg, category_factor[category])
        family_by_tech[tid] = family
    return curves, family_by_tech


def latent_features(curve: np.ndarray, anchor_index: int, family: str) -> dict:
    history = curve[: anchor_index + 1]
    result = {"family": family, "month_index": anchor_index}
    for window in (3, 6, 12, 24):
        values = history[-window:]
        result[f"log_level_{window}"] = float(np.log1p(np.mean(values)))
        result[f"slope_{window}"] = _slope(values)
        result[f"relative_slope_{window}"] = float(_slope(values) / max(np.mean(values), 1e-9))
        result[f"volatility_{window}"] = float(np.std(values) / max(np.mean(values), 1e-9)) if len(values) > 1 else np.nan
    if len(history) >= 12:
        result["acceleration_6"] = _slope(history[-6:]) - _slope(history[-12:-6])
    else:
        result["acceleration_6"] = np.nan
    result["peak_drawdown"] = float((np.max(history) - history[-1]) / max(np.max(history), 1e-9))
    result["years_since_peak"] = int(len(history) - 1 - np.argmax(history))
    return result


def sample_noisy_labels(curve: np.ndarray, anchor_indices: list[int], sim_cfg: dict, lab_cfg: dict,
                        rng: np.random.Generator, repeats: int = 300) -> dict[int, np.ndarray]:
    """Resample observation noise around one fixed latent curve, then apply label rule."""
    community = sim_cfg["community"]
    ar = np.zeros(repeats)
    observations = np.zeros((repeats, len(curve)), dtype=float)
    for month in range(len(curve)):
        ar = float(community["noise_ar1"]) * ar + rng.normal(0, float(community["noise_sigma"]), repeats)
        season = 1 + float(community["seasonal_amplitude"]) * np.sin(2 * np.pi * (month % 12) / 12)
        shock = rng.random(repeats) < float(community["shock_probability"])
        shock_factor = np.ones(repeats)
        shock_factor[shock] = rng.lognormal(0, float(community["shock_log_sigma"]), int(shock.sum()))
        means = np.maximum(.2, np.exp(float(community["baseline_volume_log_mean"]) + np.log(curve[month]) + ar) * season * shock_factor)
        dispersion = float(community["overdispersion"])
        observations[:, month] = rng.negative_binomial(dispersion, dispersion / (dispersion + means))

    labels_by_anchor = {}
    recent_n, future_n = int(lab_cfg["recent_window_months"]), int(lab_cfg["future_horizon_months"])
    for idx in anchor_indices:
        recent = observations[:, idx - recent_n + 1:idx + 1]
        future = observations[:, idx + 1:idx + 1 + future_n]
        recent_mean = recent.mean(axis=1)
        raw_ratio = future.mean(axis=1) / np.maximum(recent_mean, 1e-12)
        noisy_ratio = raw_ratio.copy()
        near = ((np.abs(raw_ratio - float(lab_cfg["growing_ratio_threshold"])) <= float(lab_cfg["ambiguous_threshold_band_ratio"])) |
                (np.abs(raw_ratio - float(lab_cfg["declining_ratio_threshold"])) <= float(lab_cfg["ambiguous_threshold_band_ratio"])))
        apply_noise = near & (rng.random(repeats) < float(lab_cfg["ambiguous_noise_probability"]))
        if apply_noise.any():
            factors = rng.lognormal(0, float(lab_cfg["ambiguous_future_measurement_log_sigma"]), (int(apply_noise.sum()), future_n))
            noisy_ratio[apply_noise] = (future[apply_noise] * factors).mean(axis=1) / np.maximum(recent_mean[apply_noise], 1e-12)
        label = np.full(repeats, "Stable", dtype=object)
        label[noisy_ratio >= float(lab_cfg["growing_ratio_threshold"])] = "Growing"
        label[noisy_ratio <= float(lab_cfg["declining_ratio_threshold"])] = "Declining"
        label[recent_mean < float(lab_cfg["minimum_recent_mean"])] = "UNLABELLED"
        labels_by_anchor[idx] = label
    return labels_by_anchor


def main() -> None:
    sim_cfg, lab_cfg = config("config/simulation.yaml"), config("config/labels.yaml")
    curves, families = reconstruct_latent_curves(sim_cfg)
    engine = create_engine(_database_url())
    try:
        frame = read_training_frame()
        with engine.connect() as conn:
            actual_labels = pd.read_sql(text("""
                SELECT l.technology_id,l.anchor_date,l.trajectory_label,l.future_ratio,l.ambiguous_case,
                       t.category,t.curve_family
                FROM ml.labels l JOIN sim.technology_metadata t
                  ON t.data_version_id=l.data_version_id AND t.technology_id=l.technology_id
                WHERE l.data_version_id=(SELECT data_version_id FROM ml.data_versions ORDER BY generated_at DESC LIMIT 1)
                ORDER BY l.technology_id,l.anchor_date
            """), conn)
            test = pd.read_sql(text("""
                SELECT p.technology_id,p.anchor_date,l.trajectory_label,p.predicted_label,
                       t.category,t.curve_family
                FROM ml.predictions p JOIN ml.model_runs r USING(model_run_id)
                JOIN ml.labels l ON l.data_version_id=p.data_version_id AND l.technology_id=p.technology_id AND l.anchor_date=p.anchor_date
                JOIN sim.technology_metadata t ON t.data_version_id=p.data_version_id AND t.technology_id=p.technology_id
                WHERE r.selected_by_cv AND r.status='succeeded'
            """), conn)
            run = conn.execute(text("""SELECT r.model_run_id,r.git_commit,r.git_dirty,r.model_name
                FROM ml.model_runs r WHERE r.selected_by_cv AND r.status='succeeded'
                ORDER BY r.started_at DESC LIMIT 1""")).mappings().first()
    finally:
        engine.dispose()

    # Reconstructed family identity is checked against the persisted generation.
    mismatch = actual_labels.apply(lambda r: families[r.technology_id] != r.curve_family, axis=1).any()
    if mismatch:
        raise RuntimeError("Latent curve replay did not match persisted curve-family assignments.")

    # Oracle folds use only the designated 80% training groups. No diagnostic
    # model is fitted or scored on held-out test groups.
    months = pd.PeriodIndex(actual_labels.anchor_date, freq="M")
    indices = np.asarray((months.year - 2015) * 12 + months.month - 1, dtype=int)
    oracle_rows = [latent_features(curves[row.technology_id], int(idx), families[row.technology_id])
                   for row, idx in zip(actual_labels.itertuples(index=False), indices)]
    y = actual_labels.trajectory_label.astype(str).reset_index(drop=True)
    groups = actual_labels.technology_id.astype(str).reset_index(drop=True)
    train_idx, _ = grouped_train_test_indices(y, groups)
    latent_X = pd.get_dummies(pd.DataFrame(oracle_rows), columns=["family"], dtype=float).reset_index(drop=True)
    observed_X = pd.get_dummies(frame[FEATURE_COLUMNS].copy(), columns=["category"], dtype=float).reset_index(drop=True)
    augmented_X = pd.concat([observed_X, latent_X.add_prefix("latent_")], axis=1)
    y_train, groups_train = y.iloc[train_idx].reset_index(drop=True), groups.iloc[train_idx].reset_index(drop=True)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    oracle_scores = {}
    for oracle_name, oracle_X in [("latent_only", latent_X), ("asof_features_plus_latent", augmented_X)]:
        oracle_train = oracle_X.iloc[train_idx].reset_index(drop=True)
        folds = []
        for fold, (tr, va) in enumerate(cv.split(oracle_train, y_train, groups_train), 1):
            model = RandomForestClassifier(n_estimators=400, min_samples_leaf=3, class_weight="balanced_subsample", n_jobs=-1, random_state=4200 + fold)
            model.fit(oracle_train.iloc[tr], y_train.iloc[tr])
            pred = model.predict(oracle_train.iloc[va])
            folds.append({"fold": fold, "macro_f1": float(f1_score(y_train.iloc[va], pred, labels=CLASSES, average="macro")),
                          "declining_recall": float(recall_score(y_train.iloc[va], pred, labels=CLASSES, average=None)[CLASSES.index("Declining")]),
                          "n": int(len(va)), "groups": int(groups_train.iloc[va].nunique())})
        oracle_scores[oracle_name] = {"folds": folds, "mean_macro_f1": float(np.mean([r["macro_f1"] for r in folds])),
                                      "sd_macro_f1": float(np.std([r["macro_f1"] for r in folds], ddof=1)),
                                      "mean_declining_recall": float(np.mean([r["declining_recall"] for r in folds]))}

    # Resampled observation-noise stability: current labels remain the fixed comparison.
    grouped_labels = {tid: part for tid, part in actual_labels.groupby("technology_id", sort=True)}
    stability_rows = []
    stability_by_family = []
    for idx, (tid, part) in enumerate(grouped_labels.items(), 1):
        anchors = [int((pd.Timestamp(d).year - 2015) * 12 + pd.Timestamp(d).month - 1) for d in part.anchor_date]
        sample = sample_noisy_labels(curves[tid], anchors, sim_cfg, lab_cfg, np.random.default_rng(100_000 + idx))
        for row, anchor_idx in zip(part.itertuples(index=False), anchors):
            resampled = sample[anchor_idx]
            valid = resampled != "UNLABELLED"
            modal_agreement = max(np.mean(resampled[valid] == c) for c in CLASSES) if valid.any() else np.nan
            original_agreement = float(np.mean(resampled[valid] == row.trajectory_label)) if valid.any() else np.nan
            stability_rows.append({"technology_id": tid, "curve_family": row.curve_family, "category": row.category,
                                   "original_label": row.trajectory_label, "modal_agreement": modal_agreement,
                                   "original_agreement": original_agreement, "label_coverage": float(valid.mean())})
    stability = pd.DataFrame(stability_rows)

    # Existing grouped-CV family ablations are read as diagnosis, not retuned here.
    with create_engine(_database_url()).connect() as conn:
        ablation = pd.read_sql(text("""SELECT signal_set,avg(metric_value) mean_macro_f1,stddev_samp(metric_value) sd_macro_f1
          FROM ml.ablation_results WHERE model_run_id=(SELECT model_run_id FROM ml.model_runs WHERE selected_by_cv AND status='succeeded' ORDER BY started_at DESC LIMIT 1)
          AND evaluation_part='outer_cv' AND metric_name='macro_f1' GROUP BY signal_set ORDER BY mean_macro_f1 DESC"""), conn)

    # Learning curve only uses the 80% training-group partition; held-out groups are untouched.
    train_frame = frame.iloc[train_idx].reset_index(drop=True)
    X = train_frame[FEATURE_COLUMNS].copy(); X["category"] = X["category"].astype("string")
    ty = train_frame.trajectory_label.astype(str).reset_index(drop=True)
    tg = train_frame.technology_id.astype(str).reset_index(drop=True)
    lc_folds = grouped_cv_splits(X, ty, tg)
    learning_rows = []
    for fraction in (.25, .50, .75, 1.0):
        scores=[]
        for fold, (tr, va) in enumerate(lc_folds, 1):
            available = sorted(tg.iloc[tr].unique())
            per_group_label = {g: ty.iloc[np.flatnonzero(tg.to_numpy() == g)].mode().iloc[0] for g in available}
            group_frame = pd.DataFrame({"group": available, "label": [per_group_label[g] for g in available]})
            rng = np.random.default_rng(7000 + fold)
            chosen=[]
            for label, part in group_frame.groupby("label"):
                ids=part.group.to_numpy(); rng.shuffle(ids); chosen.extend(ids[:max(1, int(round(len(ids)*fraction)))])
            fit_mask = tg.iloc[tr].isin(chosen).to_numpy()
            fit_idx = tr[fit_mask]
            pipe = _make_pipeline("random_forest", FEATURE_COLUMNS, {"min_samples_leaf": 5})
            pipe.fit(X.iloc[fit_idx], ty.iloc[fit_idx])
            pred=pipe.predict(X.iloc[va])
            scores.append(float(f1_score(ty.iloc[va], pred, labels=CLASSES, average="macro")))
        learning_rows.append({"fraction": fraction, "mean_macro_f1": float(np.mean(scores)), "sd_macro_f1": float(np.std(scores, ddof=1)),
                              "mean_train_groups": round(float(np.mean([len(set(tg.iloc[tr].unique()))*fraction for tr, _ in lc_folds])))})

    # Test error analysis is descriptive only; the held-out results are not retuned.
    test["correct"] = test.trajectory_label == test.predicted_label
    class_errors = test.groupby("trajectory_label").agg(n=("correct", "size"), accuracy=("correct", "mean")).reset_index()
    category_errors = test.groupby("category").agg(n=("correct", "size"), accuracy=("correct", "mean")).reset_index()
    family_errors = test.groupby("curve_family").agg(n=("correct", "size"), accuracy=("correct", "mean")).reset_index()
    family_confusion = pd.crosstab(test.curve_family, test.predicted_label, normalize="index").round(3)

    print(json.dumps({
        "diagnostic_version": "v1-noise-ceiling-diagnostic-1",
        "data_version": "sim-v1-s42-6c310c4cd1ba",
        "diagnostic_git_commit": __import__("subprocess").run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "diagnostic_git_dirty": bool(__import__("subprocess").run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()),
        "model_run_provenance": dict(run),
        "oracle_definition": "Two diagnostic-only random forests evaluated by 5-fold StratifiedGroupKFold within the designated 80% training groups: latent history through T (3/6/12/24-month levels/slopes/volatility, acceleration, drawdown, years since peak, known generator family) and as-of observed features augmented with that latent history. No future values; no held-out test groups used.",
        "oracle_results": oracle_scores,
        "label_stability": {"resamples_per_technology": 300,
                            "mean_modal_label_agreement": float(stability.modal_agreement.mean()),
                            "mean_flip_rate_vs_modal": float(1-stability.modal_agreement.mean()),
                            "mean_resample_agreement_with_stored_label": float(stability.original_agreement.mean()),
                            "valid_label_coverage": float(stability.label_coverage.mean())},
        "stability_by_family": stability.groupby("curve_family").agg(n=("modal_agreement","size"),modal_agreement=("modal_agreement","mean"),agreement_with_stored=("original_agreement","mean")).reset_index().to_dict("records"),
        "learning_curve_training_groups_only": learning_rows,
        "existing_signal_ablation": ablation.to_dict("records"),
        "heldout_error_analysis_descriptive_only": {"by_class": class_errors.to_dict("records"), "by_category": category_errors.to_dict("records"), "by_family": family_errors.to_dict("records"), "family_prediction_proportions": family_confusion.reset_index().to_dict("records")},
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
