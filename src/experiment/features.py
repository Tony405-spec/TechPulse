"""As-of feature engineering from the three simulated signal families."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.db.migrate import _database_url, apply_migrations
from src.labels import load_label_config
from src.simulate import SimulationCorpus

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

FEATURE_COLUMNS = [
    "community_log_volume_mean_12", "community_slope_6", "community_slope_12",
    "community_acceleration_6", "community_volatility_12", "community_answer_rate_6",
    "community_closure_rate_6", "community_score_slope_6", "community_decay_rate",
    "growth_momentum_index", "enterprise_adoption_breadth", "enterprise_adoption_depth",
    "enterprise_breadth_change_6m", "enterprise_sector_diversity",
    "sentiment_satisfaction", "sentiment_intent", "sentiment_learning_curve",
    "sentiment_trajectory", "sentiment_missing", "sentiment_satisfaction_missing",
    "sentiment_intent_missing", "sentiment_learning_missing", "category", "history_months",
    "low_confidence",
]


def _slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return float("nan")
    return float(np.polyfit(np.arange(len(values), dtype=float), values.astype(float), 1)[0])


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator is None or not np.isfinite(denominator) or abs(denominator) < 1e-12:
        return float("nan")
    return float(numerator / denominator)


def build_features(corpus: SimulationCorpus, anchors: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compute one row per label anchor using no record later than anchor_date."""
    tech_meta = corpus.tables["technology_metadata"].set_index("technology_id")
    company_frame = corpus.tables["company_profiles"]
    company_sector = company_frame.set_index("company_id").sector.to_dict()
    n_companies = max(1, len(company_frame))
    n_sectors = max(1, company_frame.sector.nunique())
    questions = {k:g.sort_values("observation_month") for k,g in corpus.tables["stack_overflow_questions"].groupby("technology_id")}
    adoptions = {k:g.sort_values("adoption_date") for k,g in corpus.tables["fortune500_stacks"].groupby("technology_id")}
    surveys = {k:g.sort_values("survey_year") for k,g in corpus.tables["developer_survey"].groupby("technology_id")}
    empty_adoptions = corpus.tables["fortune500_stacks"].iloc[:0]
    rows: list[dict[str, Any]] = []
    label_config = load_label_config()
    anchor_frame = corpus.anchor_labels if anchors is None else anchors
    for anchor in anchor_frame.itertuples(index=False):
        tid=anchor.technology_id; anchor_date=anchor.anchor_date
        anchor_np=np.datetime64(anchor_date,"D")
        history_months=int(anchor.history_months)
        q=questions[tid]
        q_dates=q.observation_month.to_numpy(dtype="datetime64[D]")
        q_end=int(np.searchsorted(q_dates,anchor_np,side="right"))
        end=max(0,q_end)
        vol=q.question_volume.to_numpy(dtype=float)[:end]
        ans=q.answer_rate.to_numpy(dtype=float)[:end]; close=q.closure_rate.to_numpy(dtype=float)[:end]; score=q.mean_score.to_numpy(dtype=float)[:end]
        volume12=vol[-12:]; volume6=vol[-6:]; prior6=vol[-12:-6]
        slope6=_slope(volume6); prior_slope=_slope(prior6)
        avg6=float(np.mean(volume6)) if len(volume6) else np.nan
        prev6=float(np.mean(prior6)) if len(prior6) else np.nan
        last3=float(np.mean(vol[-3:])) if len(vol) else np.nan
        previous3=float(np.mean(vol[-6:-3])) if len(vol)>=6 else np.nan
        gmi=100.0*_safe_div(last3-previous3,previous3)
        decay=100.0*_safe_div(prev6-avg6,prev6)
        # A linear continuation from the last observed month forecasts the mean
        # of the next six months using the trailing-three-month label baseline.
        projected_future_mean=(float(vol[-1])+slope6*3.5) if len(vol) and np.isfinite(slope6) else np.nan
        baseline_ratio=_safe_div(projected_future_mean,last3)

        adoption=adoptions.get(tid,empty_adoptions)
        ad_dates=adoption.adoption_date.to_numpy(dtype="datetime64[D]")
        ad_end=int(np.searchsorted(ad_dates,anchor_np,side="right"))
        prior_date=(pd.Timestamp(anchor_date)-pd.DateOffset(months=6)).date()
        prior_np=np.datetime64(prior_date,"D")
        ad_prior=int(np.searchsorted(ad_dates,prior_np,side="right"))
        ad_company=adoption.company_id.to_numpy(dtype=int)
        ad_depth=adoption.adoption_depth.to_numpy(dtype=float)
        ad_end_dates=np.array([np.datetime64(v,"D") if pd.notna(v) else np.datetime64("NaT","D") for v in adoption.end_date],dtype="datetime64[D]")
        active_mask=(ad_end_dates[:ad_end].astype("int64") == np.iinfo(np.int64).min) | (ad_end_dates[:ad_end]>=anchor_np)
        prior_mask=(ad_end_dates[:ad_prior].astype("int64") == np.iinfo(np.int64).min) | (ad_end_dates[:ad_prior]>=prior_np)
        active_ids=np.unique(ad_company[:ad_end][active_mask]); prior_ids=np.unique(ad_company[:ad_prior][prior_mask])
        breadth=len(active_ids)/n_companies; breadth_prior=len(prior_ids)/n_companies
        sector_counts=pd.Series([company_sector[int(cid)] for cid in active_ids]).value_counts().to_numpy(dtype=float)
        if len(sector_counts)>1 and sector_counts.sum()>0:
            shares=sector_counts/sector_counts.sum(); sector_diversity=float(-(shares*np.log(shares)).sum()/np.log(n_sectors))
        else: sector_diversity=0.0
        active_depth=ad_depth[:ad_end][active_mask]

        survey=surveys.get(tid)
        survey_missing=1; satisfaction=intent=learning=np.nan; satisfaction_trend=np.nan
        if survey is not None and not survey.empty:
            survey_dates=pd.to_datetime(survey.survey_year.astype(str)+"-06-30").to_numpy(dtype="datetime64[D]")
            s_end=int(np.searchsorted(survey_dates,anchor_np,side="right"))
            s=survey.iloc[:s_end]
            valid=s[~s.is_missing]
            if len(valid):
                latest=valid.iloc[-1]; survey_missing=0
                satisfaction=float(latest.satisfaction_score); intent=float(latest.adoption_intent); learning=float(latest.learning_curve_score)
                satisfaction_trend=_slope(valid.satisfaction_score.to_numpy(dtype=float)) if len(valid)>=2 else np.nan
        satisfaction_missing=int(pd.isna(satisfaction)); intent_missing=int(pd.isna(intent)); learning_missing=int(pd.isna(learning))
        category=str(tech_meta.loc[tid,"category"])
        row = {
            "data_version_id": corpus.data_version["data_version_id"], "technology_id": tid,
            "anchor_date": anchor_date, "history_months": history_months,
            "low_confidence": bool(anchor.low_confidence),
            "feature_values": {
                "community_log_volume_mean_12": float(np.log1p(np.mean(volume12))) if len(volume12) else np.nan,
                "community_slope_6": slope6,
                "community_slope_12": _slope(volume12),
                "community_acceleration_6": slope6-prior_slope if np.isfinite(prior_slope) else np.nan,
                "community_volatility_12": _safe_div(float(np.std(volume12, ddof=1)) if len(volume12)>1 else np.nan, float(np.mean(volume12)) if len(volume12) else np.nan),
                "community_answer_rate_6": float(np.mean(ans[-6:])) if len(ans) else np.nan,
                "community_closure_rate_6": float(np.mean(close[-6:])) if len(close) else np.nan,
                "community_score_slope_6": _slope(score[-6:]),
                "community_decay_rate": decay, "growth_momentum_index": gmi,
                "enterprise_adoption_breadth": breadth,
                "enterprise_adoption_depth": float(np.mean(active_depth)) if len(active_depth) else 0.0,
                "enterprise_breadth_change_6m": breadth-breadth_prior,
                "enterprise_sector_diversity": sector_diversity,
                "sentiment_satisfaction": satisfaction, "sentiment_intent": intent,
                "sentiment_learning_curve": learning, "sentiment_trajectory": satisfaction_trend,
                "sentiment_missing": survey_missing, "sentiment_satisfaction_missing": satisfaction_missing,
                "sentiment_intent_missing": intent_missing, "sentiment_learning_missing": learning_missing,
                "category": category, "history_months": history_months, "low_confidence": int(bool(anchor.low_confidence)),
            },
        }
        row["trend_baseline_label"] = "Growing" if baseline_ratio >= float(label_config["growing_ratio_threshold"]) else "Declining" if baseline_ratio <= float(label_config["declining_ratio_threshold"]) else "Stable"
        # Persist the fixed benchmark decision with the snapshot for evaluation,
        # but keep it out of FEATURE_COLUMNS so it cannot become a model input.
        row["feature_values"]["trend_baseline_label"] = row["trend_baseline_label"]
        rows.append(row)
    return pd.DataFrame(rows)


def _git_provenance(root: Path | None = None) -> tuple[str | None, bool]:
    root = root or Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True, timeout=3).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True, timeout=3).stdout.strip())
        return commit, dirty
    except (OSError, subprocess.SubprocessError):
        return None, True


def persist_features(corpus: SimulationCorpus, features: pd.DataFrame | None = None, url: str | None = None) -> dict[str, Any]:
    """Persist as-of snapshots and their shared-labeller targets into PostgreSQL."""
    target = _database_url(url or os.getenv("DATABASE_URL"))
    engine = create_engine(target, pool_pre_ping=True)
    try:
        apply_migrations(target, engine=engine)
        frame = features if features is not None else build_features(corpus)
        commit, dirty = _git_provenance()
        labels = corpus.anchor_labels.dropna(subset=["trajectory_label"])
        with engine.begin() as connection:
            version_id = corpus.data_version["data_version_id"]
            version_exists = connection.execute(text("SELECT 1 FROM ml.data_versions WHERE data_version_id=:v AND status='verified'"), {"v": version_id}).scalar_one_or_none()
            if not version_exists:
                raise RuntimeError(f"Verified data version {version_id} is not present in PostgreSQL.")
            connection.execute(text("UPDATE ml.data_versions SET git_commit=:commit,git_dirty=:dirty WHERE data_version_id=:v"), {"commit": commit, "dirty": dirty, "v": version_id})
            feature_records = []
            for row in frame.itertuples(index=False):
                values = {k: (None if pd.isna(v) else float(v) if isinstance(v, (np.floating, float)) else int(v) if isinstance(v, (np.integer,)) else v) for k,v in row.feature_values.items()}
                feature_records.append({"data_version_id": row.data_version_id, "technology_id": row.technology_id,
                    "anchor_date": row.anchor_date, "history_months": row.history_months,
                    "low_confidence": row.low_confidence, "feature_values": json.dumps(values, allow_nan=False)})
            feature_table = "ml.feature_snapshots"
            for chunk_start in range(0, len(feature_records), 500):
                chunk=feature_records[chunk_start:chunk_start+500]
                sql=text("""INSERT INTO ml.feature_snapshots(data_version_id,technology_id,anchor_date,history_months,low_confidence,feature_values)
                    VALUES (:data_version_id,:technology_id,:anchor_date,:history_months,:low_confidence,CAST(:feature_values AS jsonb))
                    ON CONFLICT(data_version_id,technology_id,anchor_date) DO UPDATE SET history_months=EXCLUDED.history_months,low_confidence=EXCLUDED.low_confidence,feature_values=EXCLUDED.feature_values""")
                connection.execute(sql, chunk)
            label_records = []
            for row in labels.itertuples(index=False):
                if row.trajectory_label not in {"Growing","Stable","Declining"}:
                    continue
                label_records.append({"data_version_id": row.data_version_id,"technology_id": row.technology_id,
                    "anchor_date": row.anchor_date,"target_end_date": row.target_end_date,
                    "trajectory_label": row.trajectory_label,"future_ratio": float(row.future_ratio),
                    "ambiguous_case": bool(row.ambiguous_case),"label_rule": row.label_rule})
            connection.execute(text("""INSERT INTO ml.labels(data_version_id,technology_id,anchor_date,target_end_date,trajectory_label,future_ratio,ambiguous_case,label_rule)
                VALUES (:data_version_id,:technology_id,:anchor_date,:target_end_date,:trajectory_label,:future_ratio,:ambiguous_case,:label_rule)
                ON CONFLICT(data_version_id,technology_id,anchor_date) DO UPDATE SET target_end_date=EXCLUDED.target_end_date,trajectory_label=EXCLUDED.trajectory_label,future_ratio=EXCLUDED.future_ratio,ambiguous_case=EXCLUDED.ambiguous_case,label_rule=EXCLUDED.label_rule"""), label_records)
            return {"feature_count": len(feature_records), "label_count": len(label_records), "git_commit": commit, "git_dirty": dirty}
    finally:
        engine.dispose()


def read_training_frame(url: str | None = None, data_version_id: str | None = None) -> pd.DataFrame:
    target = _database_url(url or os.getenv("DATABASE_URL"))
    engine=create_engine(target, pool_pre_ping=True)
    try:
        sql="""SELECT f.data_version_id,f.technology_id,f.anchor_date,f.history_months,f.low_confidence,f.feature_values,
                     l.trajectory_label,l.future_ratio,l.ambiguous_case,t.category
              FROM ml.feature_snapshots f JOIN ml.labels l USING(data_version_id,technology_id,anchor_date)
              JOIN sim.technology_metadata t USING(data_version_id,technology_id)
              WHERE (:v IS NULL OR f.data_version_id=:v)
              ORDER BY f.technology_id,f.anchor_date"""
        frame=pd.read_sql(text(sql),engine,params={"v":data_version_id})
        if frame.empty:
            return frame
        values=pd.json_normalize(frame.pop("feature_values").map(lambda x: x if isinstance(x,dict) else json.loads(x)))
        # These are also first-class snapshot columns; the normalized JSON copy
        # would otherwise create duplicate DataFrame column names.
        values=values.drop(columns=[c for c in ("category","history_months","low_confidence") if c in values],errors="ignore")
        return pd.concat([frame.reset_index(drop=True),values.reset_index(drop=True)],axis=1)
    finally:
        engine.dispose()
