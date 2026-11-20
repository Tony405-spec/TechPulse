"""Deterministic synthetic corpus generator; it has no database or file writes."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.labels import label_trajectory, load_label_config

GENERATOR_VERSION = "techpulse-simulator-v1"
SYNTHETIC = "SYNTHETIC_SIMULATION"
TABLES = (
    "technology_metadata",
    "company_profiles",
    "stack_overflow_questions",
    "developer_survey",
    "fortune500_stacks",
    "question_company_mapping",
)


@dataclass
class SimulationCorpus:
    tables: dict[str, pd.DataFrame]
    data_version: dict[str, Any]
    anchor_labels: pd.DataFrame


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _frame_checksum(frame: pd.DataFrame) -> str:
    normalized = frame.copy()
    for column in normalized.columns:
        if pd.api.types.is_datetime64_any_dtype(normalized[column]):
            normalized[column] = normalized[column].astype("string")
        elif normalized[column].dtype == object:
            normalized[column] = normalized[column].map(lambda x: x.isoformat() if hasattr(x, "isoformat") else x)
    normalized = normalized.reindex(sorted(normalized.columns), axis=1)
    normalized = normalized.sort_values(list(normalized.columns), kind="mergesort", na_position="first").reset_index(drop=True)
    payload = normalized.to_json(orient="records", date_format="iso", double_precision=15, default_handler=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _month_dates(start: str, count: int) -> list[date]:
    return [period.to_timestamp().date() for period in pd.period_range(start=start, periods=count, freq="M")]


def _latent_curve(rng: np.random.Generator, family: str, months: int, cfg: dict[str, Any], category_factor: float) -> np.ndarray:
    p = cfg["curve_parameters"]
    x = np.linspace(0.0, 1.0, months)
    scale = rng.uniform(float(p["latent_scale_min"]), float(p["latent_scale_max"])) * category_factor
    floor = float(p["latent_floor"])
    if family == "plateau":
        curve = floor + scale * (0.72 + 0.12 * np.sin(2 * np.pi * x + rng.uniform(0, 2 * np.pi)))
    elif family == "logistic_growth":
        rate = rng.lognormal(float(p["growth_rate_log_mean"]), float(p["growth_rate_log_sigma"])) / 1000
        midpoint = rng.uniform(0.3, 0.72)
        sig = 1 / (1 + np.exp(-np.clip((x - midpoint) * rate * 100, -30, 30)))
        curve = floor + scale * (0.12 + 0.88 * sig)
    elif family == "post_peak_decay":
        peak = rng.uniform(float(p["peak_time_min"]), float(p["peak_time_max"]))
        decay = rng.uniform(float(p["decay_rate_min"]), float(p["decay_rate_max"]))
        curve = floor + scale * np.where(x <= peak, 0.12 + 0.88 * x / max(peak, 0.01), 1.0 * np.exp(-decay * (x - peak)))
    elif family == "late_surge":
        midpoint = rng.uniform(0.65, 0.88)
        sig = 1 / (1 + np.exp(-np.clip((x - midpoint) * rng.uniform(12, 24), -30, 30)))
        curve = floor + scale * (0.08 + 0.92 * sig)
    else:  # hype_then_collapse
        peak = rng.uniform(0.2, 0.5)
        curve = floor + scale * np.where(x <= peak, 0.2 + 0.8 * x / peak, np.exp(-rng.uniform(2.0, 5.0) * (x - peak)))
    curve *= rng.lognormal(0, float(p["category_amplitude_sigma"]))
    return np.maximum(curve, 0.03)


def _logit_probability(x: float) -> float:
    return float(1 / (1 + math.exp(-max(-30.0, min(30.0, x)))))


def simulate_corpus(
    simulation_config: dict[str, Any] | None = None,
    label_config: dict[str, Any] | None = None,
    *,
    simulation_config_path: str | Path | None = None,
    label_config_path: str | Path | None = None,
    git_commit: str | None = None,
) -> SimulationCorpus:
    """Build all source tables deterministically for a given seed/configuration."""
    root = Path(__file__).resolve().parents[1]
    sim_cfg = simulation_config or _read_yaml(simulation_config_path or root / "config" / "simulation.yaml")
    lab_cfg = label_config or load_label_config(label_config_path)
    seed = int(sim_cfg["seed"])
    rng = np.random.default_rng(seed)
    config_hash = _canonical_hash({"simulation": sim_cfg, "labels": lab_cfg})
    version_id = f"sim-v1-s{seed}-{config_hash[:12]}"
    if git_commit is None:
        try:
            git_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=2, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            git_commit = None

    categories = list(sim_cfg["categories"])
    category_weights = np.array(list(sim_cfg["categories"].values()), dtype=float)
    category_weights /= category_weights.sum()
    families = list(sim_cfg["curve_families"])
    family_weights = np.array(list(sim_cfg["curve_families"].values()), dtype=float)
    family_weights /= family_weights.sum()
    count = int(sim_cfg["technology_count"])
    months = int(sim_cfg["months"])
    dates = _month_dates(sim_cfg["start_month"], months)
    category_factor = {category: float(rng.lognormal(0, 0.12)) for category in categories}
    technologies: list[dict[str, Any]] = []
    curves: dict[str, np.ndarray] = {}
    for idx in range(1, count + 1):
        tech_id = f"SIM-TECH-{idx:04d}"
        category = str(rng.choice(categories, p=category_weights))
        family = str(rng.choice(families, p=family_weights))
        curve = _latent_curve(rng, family, months, sim_cfg, category_factor[category])
        curves[tech_id] = curve
        technologies.append({"data_version_id": version_id, "technology_id": tech_id,
            "technology_name": f"Synthetic {category[:-1] if category.endswith('s') else category} {idx:04d}",
            "category": category, "curve_family": family, "first_observed_month": dates[0], "data_origin": SYNTHETIC})
    tech_df = pd.DataFrame(technologies)

    companies: list[dict[str, Any]] = []
    sectors = ["finance", "health", "retail", "manufacturing", "telecommunications", "public_services", "education", "energy"]
    sizes = ["small", "medium", "large", "enterprise"]
    for company_id in range(1, int(sim_cfg["company_count"]) + 1):
        companies.append({"data_version_id": version_id, "company_id": company_id,
            "company_name": f"Synthetic Corporation {company_id:04d}",
            "sector": str(rng.choice(sectors)), "company_size": str(rng.choice(sizes, p=[.15,.3,.35,.2])),
            "ticker": None, "data_origin": SYNTHETIC})
    company_df = pd.DataFrame(companies)
    company_sector_effect = rng.normal(0, float(sim_cfg["enterprise"]["sector_effect_sigma"]), len(sectors))
    sector_index = {s: i for i, s in enumerate(sectors)}
    company_effect = rng.normal(0, float(sim_cfg["enterprise"]["company_effect_sigma"]), len(companies))

    community_cfg = sim_cfg["community"]
    question_rows: list[dict[str, Any]] = []
    tech_month_counts: dict[tuple[str, int], int] = {}
    latent_observed: dict[str, np.ndarray] = {}
    for tech_idx, tech in enumerate(technologies):
        tid = tech["technology_id"]
        curve = curves[tid]
        ar_state = 0.0
        observed = np.empty(months, dtype=float)
        for m, obs_date in enumerate(dates):
            ar_state = float(community_cfg["noise_ar1"]) * ar_state + rng.normal(0, float(community_cfg["noise_sigma"]))
            season = 1 + float(community_cfg["seasonal_amplitude"]) * math.sin(2 * math.pi * (obs_date.month - 1) / 12)
            shock = bool(rng.random() < float(community_cfg["shock_probability"]))
            shock_factor = rng.lognormal(0, float(community_cfg["shock_log_sigma"])) if shock else 1.0
            volume_mean = max(0.2, math.exp(float(community_cfg["baseline_volume_log_mean"]) + math.log(float(curve[m])) + ar_state) * season * shock_factor)
            dispersion = float(community_cfg["overdispersion"])
            volume = int(rng.negative_binomial(dispersion, dispersion / (dispersion + volume_mean)))
            answer_rate = min(.99, max(.02, _logit_probability(float(community_cfg["answer_rate_logit_mean"]) + rng.normal(0, float(community_cfg["engagement_noise_sigma"])))))
            closure_rate = min(.99, max(.01, _logit_probability(float(community_cfg["closure_rate_logit_mean"]) + rng.normal(0, float(community_cfg["engagement_noise_sigma"])))))
            answered = int(rng.binomial(volume, answer_rate))
            observed[m] = float(volume)
            tech_month_counts[(tid, m)] = volume
            question_rows.append({"data_version_id": version_id, "technology_id": tid, "observation_month": obs_date,
                "question_volume": volume, "answered_volume": answered, "unanswered_volume": volume-answered,
                "answer_rate": answered / volume if volume else 0.0, "closure_rate": closure_rate,
                "mean_score": float(rng.normal(0.4 + 0.2 * math.log1p(curve[m]), 0.7)),
                "seasonal_factor": season, "shock_applied": shock, "data_origin": SYNTHETIC})
        latent_observed[tid] = observed
    questions_df = pd.DataFrame(question_rows)

    # Survey is annual and noisy; missing survey measurements remain NULL.
    survey_cfg = sim_cfg["sentiment"]
    survey_rows: list[dict[str, Any]] = []
    for tech in technologies:
        tid = tech["technology_id"]
        for survey_year in range(pd.Timestamp(dates[0]).year, pd.Timestamp(dates[-1]).year + 1):
            m = min(months - 1, max(0, (survey_year - pd.Timestamp(dates[0]).year) * 12 + 5))
            missing = bool(rng.random() < float(survey_cfg["missing_rate"]))
            respondents = int(rng.integers(int(survey_cfg["annual_respondents_min"]), int(survey_cfg["annual_respondents_max"]) + 1))
            hype = float(rng.normal(0, float(survey_cfg["hype_sigma"])))
            satisfaction = float(np.clip(65 + 8 * math.log1p(curves[tid][m]) + rng.normal(0, float(survey_cfg["noise_sigma"])) + hype, 0, 100))
            intent = float(np.clip(.25 + .17 * math.log1p(curves[tid][m]) + rng.normal(0, float(survey_cfg["intent_noise_sigma"])) + hype / 200, 0, 1))
            learning = float(np.clip(50 + rng.normal(0, float(survey_cfg["noise_sigma"])) - 3 * math.log1p(curves[tid][m]), 0, 100))
            survey_rows.append({"data_version_id": version_id, "technology_id": tid, "survey_year": survey_year,
                "respondent_count": respondents, "satisfaction_score": None if missing else satisfaction,
                "adoption_intent": None if missing else intent, "learning_curve_score": None if missing else learning,
                "hype_component": hype, "is_missing": missing, "data_origin": SYNTHETIC})
    survey_df = pd.DataFrame(survey_rows)

    # Adoption history is a simulated process with lag and company/sector random effects.
    enterprise_cfg = sim_cfg["enterprise"]
    adoption_rows: list[dict[str, Any]] = []
    event_counter = 0
    for tech in technologies:
        tid = tech["technology_id"]
        curve = curves[tid]
        sector_effects = np.array([company_sector_effect[sector_index[c["sector"]]] for c in companies])
        lags = rng.integers(int(enterprise_cfg["lag_months_min"]), int(enterprise_cfg["lag_months_max"])+1, size=(months, len(companies)))
        month_indices = np.arange(months)[:, None]
        signal_indices = np.maximum(0, month_indices-lags)
        lagged_signal = curve[signal_indices]
        logits = float(enterprise_cfg["latent_sensitivity"]) * (lagged_signal - float(enterprise_cfg["latent_midpoint"])) + sector_effects[None, :] + company_effect[None, :]
        probs = float(enterprise_cfg["monthly_adoption_hazard"]) / (1 + np.exp(-np.clip(logits, -30, 30)))
        hits = rng.random((months, len(companies))) < probs
        has_hit = hits.any(axis=0)
        first_month = hits.argmax(axis=0)
        for ci in np.flatnonzero(has_hit):
            m = int(first_month[ci])
            event_counter += 1
            adoption_rows.append({"data_version_id": version_id, "adoption_id": f"SIM-ADOPT-{event_counter:07d}",
                "technology_id": tid, "company_id": companies[int(ci)]["company_id"], "adoption_date": dates[m], "end_date": None,
                "adoption_depth": float(rng.beta(float(enterprise_cfg["depth_beta_alpha"]), float(enterprise_cfg["depth_beta_beta"]))),
                "data_origin": SYNTHETIC})
    adoption_df = pd.DataFrame(adoption_rows, columns=["data_version_id","adoption_id","technology_id","company_id","adoption_date","end_date","adoption_depth","data_origin"])

    map_rate = float(sim_cfg["mapping"]["adoption_event_mapping_rate"])
    mapping_rows: list[dict[str, Any]] = []
    for event in adoption_rows:
        if rng.random() <= map_rate:
            m = dates.index(event["adoption_date"])
            mapping_rows.append({"data_version_id": version_id, "mapping_id": f"SIM-MAP-{len(mapping_rows)+1:07d}",
                "synthetic_question_id": f"SIM-Q-{event['technology_id']}-{m:03d}", "technology_id": event["technology_id"],
                "company_id": event["company_id"], "observation_month": event["adoption_date"],
                "mapping_method": "SIMULATED_CO_OCCURRENCE", "data_origin": SYNTHETIC})
    mapping_df = pd.DataFrame(mapping_rows, columns=["data_version_id","mapping_id","synthetic_question_id","technology_id","company_id","observation_month","mapping_method","data_origin"])

    # Anchor targets are measured from observed community series. Ambiguous noise is
    # added to the future-window measurement before calling the shared labeller.
    anchor_rows: list[dict[str, Any]] = []
    every = int(sim_cfg["anchor_every_months"])
    minimum_history = int(sim_cfg["minimum_history_months"])
    band = float(lab_cfg["ambiguous_threshold_band_ratio"])
    ambiguous_probability = float(lab_cfg["ambiguous_noise_probability"])
    ambiguous_sigma = float(lab_cfg["ambiguous_future_measurement_log_sigma"])
    recent_n = int(lab_cfg["recent_window_months"])
    horizon = int(lab_cfg["future_horizon_months"])
    for tech in technologies:
        tid = tech["technology_id"]
        values = latent_observed[tid]
        for anchor_idx in range(minimum_history-1, months-horizon, every):
            if anchor_idx + horizon >= months:
                continue
            recent = values[anchor_idx-recent_n+1:anchor_idx+1].tolist()
            future = values[anchor_idx+1:anchor_idx+1+horizon].tolist()
            recent_mean = float(np.mean(recent))
            raw_ratio = float(np.mean(future) / recent_mean) if recent_mean >= float(lab_cfg["minimum_recent_mean"]) else None
            is_ambiguous = raw_ratio is not None and (abs(raw_ratio - float(lab_cfg["growing_ratio_threshold"])) <= band or abs(raw_ratio - float(lab_cfg["declining_ratio_threshold"])) <= band)
            noisy = bool(is_ambiguous and rng.random() < ambiguous_probability)
            measured_future = (np.array(future) * rng.lognormal(0, ambiguous_sigma, len(future))).tolist() if noisy else future
            result = label_trajectory(recent, measured_future, lab_cfg)
            anchor_rows.append({"data_version_id": version_id, "technology_id": tid,
                "anchor_date": dates[anchor_idx], "target_end_date": dates[anchor_idx+horizon],
                "trajectory_label": result["label"], "future_ratio": result["ratio"],
                "ambiguous_case": bool(is_ambiguous), "ambiguity_noise_applied": noisy,
                "history_months": anchor_idx+1, "low_confidence": anchor_idx+1 < int(sim_cfg["low_confidence_below_history_months"]),
                "label_rule": str(lab_cfg["version"])})
    anchor_df = pd.DataFrame(anchor_rows)
    valid_labels = anchor_df.dropna(subset=["trajectory_label"])
    distribution = {key: int(value) for key, value in valid_labels["trajectory_label"].value_counts().reindex(["Growing","Stable","Declining"], fill_value=0).items()}
    table_map = {"technology_metadata": tech_df, "company_profiles": company_df,
        "stack_overflow_questions": questions_df, "developer_survey": survey_df,
        "fortune500_stacks": adoption_df, "question_company_mapping": mapping_df}
    checksums = {name: _frame_checksum(table_map[name]) for name in TABLES}
    counts = {name: int(len(table_map[name])) for name in TABLES}
    version = {"data_version_id": version_id, "seed": seed, "config_hash": config_hash,
        "generator_version": GENERATOR_VERSION, "git_commit": git_commit,
        "generated_at": datetime.now(timezone.utc), "expected_counts": counts,
        "table_checksums": checksums, "class_distribution": distribution,
        "valid_anchor_count": int(len(valid_labels)),
        "disclosure": "SIMULATED DATA; NOT EMPIRICAL RESEARCH EVIDENCE"}
    return SimulationCorpus(table_map, version, anchor_df)


if __name__ == "__main__":
    corpus = simulate_corpus()
    print(json.dumps({"data_version": {k: v for k, v in corpus.data_version.items() if k not in {"generated_at"}},
                      "generated_at": corpus.data_version["generated_at"].isoformat(),
                      "realized_label_distribution": corpus.data_version["class_distribution"]}, indent=2, default=str))
