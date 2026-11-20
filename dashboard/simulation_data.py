"""Typed, cached PostgreSQL access for the synthetic simulation experience."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from dashboard.technology_catalog import with_display_names

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)


@st.cache_resource
def get_engine() -> Engine:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError("DATABASE_URL is missing or is not a PostgreSQL URL.")
    database = url.rsplit("/", 1)[-1].split("?", 1)[0]
    expected = os.getenv("TECHPULSE_DATABASE_NAME", "techpulse_sim")
    if database != expected:
        raise RuntimeError(f"Simulation mode is configured only for {expected}; found {database!r}.")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url.removeprefix("postgresql://")
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=45)
def _read(sql: str, params: tuple[tuple[str, Any], ...] = ()) -> pd.DataFrame:
    with get_engine().connect() as connection:
        return pd.read_sql(text(sql), connection, params=dict(params))


def _param(**kwargs: Any) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(kwargs.items()))


def get_overview() -> dict[str, Any]:
    frame = _read("SELECT * FROM ml.v_dashboard_overview")
    return {} if frame.empty else frame.iloc[0].to_dict()


def get_technologies(data_version_id: str) -> pd.DataFrame:
    frame = _read("""
        WITH catalog AS (
            SELECT t.*,
                   row_number() OVER (PARTITION BY t.data_version_id,t.category ORDER BY t.technology_id) AS category_ordinal
            FROM sim.technology_metadata t
        )
        SELECT t.technology_id,t.technology_name,t.category,t.category_ordinal,t.curve_family,t.first_observed_month,
               p.prediction_id,p.anchor_date,p.predicted_label,p.risk_score,p.confidence,
               p.low_confidence,p.probabilities,p.model_name,p.model_run_id
        FROM catalog t
        LEFT JOIN ml.v_latest_predictions p
          ON p.data_version_id=t.data_version_id AND p.technology_id=t.technology_id
        WHERE t.data_version_id=:version
        ORDER BY t.technology_name
    """, _param(version=data_version_id))
    return with_display_names(frame)


def get_source_series(technology_id: str, data_version_id: str, anchor_date: Any) -> dict[str, pd.DataFrame]:
    params = _param(technology_id=technology_id, version=data_version_id, anchor=anchor_date)
    return {
        "community": _read("""
            SELECT observation_month,question_volume,answer_rate,mean_score
            FROM sim.stack_overflow_questions
            WHERE data_version_id=:version AND technology_id=:technology_id AND (CAST(:anchor AS date) IS NULL OR observation_month<=CAST(:anchor AS date))
            ORDER BY observation_month
        """, params),
        "enterprise": _read("""
            SELECT adoption_date AS observation_date,count(*) AS adoption_events,
                   count(DISTINCT company_id) AS companies,avg(adoption_depth) AS mean_depth
            FROM sim.fortune500_stacks
            WHERE data_version_id=:version AND technology_id=:technology_id AND (CAST(:anchor AS date) IS NULL OR adoption_date<=CAST(:anchor AS date))
            GROUP BY adoption_date ORDER BY adoption_date
        """, params),
        "sentiment": _read("""
            SELECT make_date(survey_year,6,30) AS observation_date,satisfaction_score,
                   adoption_intent,learning_curve_score,is_missing
            FROM sim.developer_survey
            WHERE data_version_id=:version AND technology_id=:technology_id
              AND (CAST(:anchor AS date) IS NULL OR make_date(survey_year,6,30)<=CAST(:anchor AS date))
            ORDER BY survey_year
        """, params),
        "features": _read("""
            SELECT feature_values FROM ml.feature_snapshots
            WHERE data_version_id=:version AND technology_id=:technology_id AND anchor_date=:anchor
        """, params),
    }


def get_local_explanation(prediction_id: int) -> pd.DataFrame:
    return _read("""
        SELECT feature_name,shap_value,base_value,explanation
        FROM ml.shap_local WHERE prediction_id=:prediction_id ORDER BY abs(shap_value) DESC
    """, _param(prediction_id=int(prediction_id)))


@st.cache_data(ttl=45)
def get_model_runs() -> pd.DataFrame:
    return _read("""
        SELECT model_run_id,model_name,selected_by_cv,status,metadata
        FROM ml.model_runs WHERE status='succeeded' ORDER BY model_name
    """)


def get_confusion_matrix(model_run_id: str) -> pd.DataFrame:
    return _read("""
        SELECT class_label AS actual_class,
               replace(metric_name,'confusion_pred_','') AS predicted_class,metric_value
        FROM ml.model_metrics
        WHERE model_run_id=:run AND evaluation_part='test' AND metric_name LIKE 'confusion_pred_%'
    """, _param(run=model_run_id))


def get_heldout_probabilities(model_run_id: str) -> pd.DataFrame:
    return _read("""
        SELECT l.trajectory_label AS actual_class,p.probabilities
        FROM ml.predictions p JOIN ml.labels l
          ON l.data_version_id=p.data_version_id AND l.technology_id=p.technology_id AND l.anchor_date=p.anchor_date
        WHERE p.model_run_id=:run ORDER BY p.technology_id,p.anchor_date
    """, _param(run=model_run_id))


def get_ablation(model_run_id: str) -> pd.DataFrame:
    return _read("""
        SELECT signal_set,avg(metric_value) AS mean_macro_f1,stddev_samp(metric_value) AS sd_macro_f1
        FROM ml.ablation_results
        WHERE model_run_id=:run AND evaluation_part='outer_cv' AND metric_name='macro_f1'
        GROUP BY signal_set ORDER BY mean_macro_f1 DESC
    """, _param(run=model_run_id))


def get_global_shap(model_run_id: str) -> pd.DataFrame:
    return _read("""
        SELECT class_label,feature_name,signal_family,mean_abs_shap,rank
        FROM ml.shap_global WHERE model_run_id=:run ORDER BY class_label,rank
    """, _param(run=model_run_id))


def get_version_record(data_version_id: str) -> pd.DataFrame:
    return _read("""
        SELECT data_version_id,seed,generator_version,config_hash,git_commit,git_dirty,
               generated_at,expected_counts,table_checksums,class_distribution,disclosure
        FROM ml.data_versions WHERE data_version_id=:version
    """, _param(version=data_version_id))


@st.cache_data(ttl=45)
def get_watchlist(session_id: str, data_version_id: str) -> pd.DataFrame:
    frame = _read("""
        WITH catalog AS (
            SELECT t.*,
                   row_number() OVER (PARTITION BY t.data_version_id,t.category ORDER BY t.technology_id) AS category_ordinal
            FROM sim.technology_metadata t
        )
        SELECT w.technology_id,t.technology_name,t.category,t.category_ordinal,w.added_at
        FROM ml.watchlist w JOIN catalog t
          ON t.data_version_id=w.data_version_id AND t.technology_id=w.technology_id
        WHERE w.browser_session_id=:session AND w.data_version_id=:version
        ORDER BY w.added_at DESC
    """, _param(session=session_id, version=data_version_id))
    return with_display_names(frame)


def set_watchlist(session_id: str, data_version_id: str, technology_id: str, added: bool) -> None:
    with get_engine().begin() as connection:
        if added:
            connection.execute(text("""
                INSERT INTO ml.watchlist(browser_session_id,data_version_id,technology_id)
                VALUES (:session,:version,:technology)
                ON CONFLICT(browser_session_id,data_version_id,technology_id) DO NOTHING
            """), {"session": session_id, "version": data_version_id, "technology": technology_id})
        else:
            connection.execute(text("""
                DELETE FROM ml.watchlist
                WHERE browser_session_id=:session AND data_version_id=:version AND technology_id=:technology
            """), {"session": session_id, "version": data_version_id, "technology": technology_id})
    get_watchlist.clear()
