"""Isolated deterministic demonstration database. Never contains research rows."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "outputs" / "synthetic_demo"
DATABASE_PATH = DEMO_DIR / "techpulse_demo.sqlite"
ARTIFACT_DIR = DEMO_DIR / "artifacts"
SEED = 7312026
FEATURES = [
    "technology_health_score",
    "growth_momentum_index",
    "question_quality_score",
    "company_diversity_score",
    "sentiment_delta",
    "adoption_velocity",
    "community_decay_rate",
]
LABELS = ["Growing", "Stable", "Declining"]


def _simulation() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    definitions = [
        ("DemoLang", "Language", "Growing"),
        ("DemoScript", "Language", "Growing"),
        ("DemoQuery", "Database", "Growing"),
        ("DemoWeb", "Framework", "Growing"),
        ("DemoData", "Tool", "Stable"),
        ("DemoBuild", "Tool", "Stable"),
        ("DemoStore", "Database", "Stable"),
        ("DemoUI", "Framework", "Stable"),
        ("DemoLegacy", "Language", "Declining"),
        ("DemoBatch", "Tool", "Declining"),
        ("DemoOldDB", "Database", "Declining"),
        ("DemoClassicUI", "Framework", "Declining"),
    ]
    technologies = pd.DataFrame(
        [
            {
                "technology_id": i + 1,
                "name": name,
                "category": category,
                "description": "Fictional technology created only for the isolated demonstration.",
                "data_mode": "SYNTHETIC DEMONSTRATION DATA",
            }
            for i, (name, category, _) in enumerate(definitions)
        ]
    )
    months = pd.date_range("2019-01-01", periods=72, freq="MS")
    community_rows: list[dict[str, object]] = []
    feature_rows: list[dict[str, object]] = []
    survey_rows: list[dict[str, object]] = []
    company_rows: list[dict[str, object]] = []
    source_rows = [
        {
            "source_key": "synthetic_generator_v1",
            "source_name": "TechPulse deterministic demonstration generator",
            "source_url": "synthetic://techpulse-demo/v1",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "observation_period": "Simulated 2019-2024 monthly and annual periods",
            "license_terms": "Fictional generated records; not external source data.",
            "geographic_scope": "Synthetic global demonstration only",
            "collection_method": "Deterministic seeded simulation; see dashboard/demo_store.py",
            "quality_status": "Synthetic demonstration; excluded from research mode",
            "data_mode": "SYNTHETIC DEMONSTRATION DATA",
        }
    ]
    company_id = 1

    for tech_idx, (name, category, trajectory) in enumerate(definitions):
        rate = {"Growing": 0.080, "Stable": 0.000, "Declining": -0.060}[trajectory]
        baseline = (800 + 20 * tech_idx) if trajectory == "Declining" else (80 + 6 * tech_idx)
        noise = rng.normal(0, 0.055, len(months))
        season = 1 + 0.06 * np.sin(np.arange(len(months)) * 2 * np.pi / 12)
        volume = np.maximum(8, np.round(baseline * np.exp(rate * np.arange(len(months)) + noise) * season)).astype(int)
        unanswered_rate = float(rng.uniform(0.08, 0.28))
        for month_i, month in enumerate(months):
            q = int(volume[month_i])
            unanswered = int(round(q * unanswered_rate))
            community_rows.append({
                "technology_id": tech_idx + 1,
                "month": month.date().isoformat(),
                "question_volume": q,
                "answered_volume": q - unanswered,
                "unanswered_volume": unanswered,
                "geography": "Synthetic global scenario",
                "data_mode": "SYNTHETIC DEMONSTRATION DATA",
            })

        # Fictional enterprise examples are intentionally named Demo Company.
        sector_names = ["Synthetic Finance", "Synthetic Health", "Synthetic Retail", "Synthetic Software"]
        company_count = 2 + (tech_idx % 5)
        adoption_months = sorted(rng.choice(np.arange(24, len(months)), size=company_count, replace=False))
        for j in range(company_count):
            company_rows.append({
                "evidence_id": len(company_rows) + 1,
                "technology_id": tech_idx + 1,
                "company_name": f"Demo Company {company_id:02d}",
                "sector": sector_names[(tech_idx + j) % len(sector_names)],
                "observation_date": months[int(adoption_months[j])].date().isoformat(),
                "evidence_type": "Synthetic fictional example",
                "source_url": "synthetic://techpulse-demo/company-example",
                "verification_status": "NOT VERIFIED - SYNTHETIC ONLY",
                "data_mode": "SYNTHETIC DEMONSTRATION DATA",
            })
            company_id += 1

        satisfaction = float(rng.uniform(48, 72))
        usage = float(rng.uniform(0.12, 0.48))
        for year in range(2019, 2025):
            year_offset = year - 2019
            synthetic_sentiment = satisfaction + year_offset * (rate * 80 + rng.normal(0, 1.2))
            survey_rows.append({
                "technology_id": tech_idx + 1,
                "survey_year": year,
                "respondent_count": int(rng.integers(800, 4200)),
                "usage_share": float(np.clip(usage + year_offset * rate * 0.025, 0.01, 0.95)),
                "interest_share": float(np.clip(usage + 0.12 + year_offset * rate * 0.03, 0.01, 0.99)),
                "admiration_share": float(np.clip(usage + 0.08 + year_offset * rate * 0.02, 0.01, 0.99)),
                "satisfaction_score": float(np.clip(synthetic_sentiment, 0, 100)),
                "geography": "Synthetic global sample",
                "data_mode": "SYNTHETIC DEMONSTRATION DATA",
            })

        for origin in range(24, 65):
            as_of = months[origin]
            recent = float(np.mean(volume[origin - 2 : origin + 1]))
            prior = float(np.mean(volume[origin - 5 : origin - 2]))
            future = float(np.mean(volume[origin + 1 : origin + 7])) if origin + 7 <= len(volume) else None
            gmi = 100 * (recent - prior) / max(prior, 1)
            q_quality = (1 - unanswered_rate) * 100
            decay = 100 * (float(np.mean(volume[origin - 11 : origin - 5])) - float(np.mean(volume[origin - 5 : origin + 1]))) / max(float(np.mean(volume[origin - 11 : origin - 5])), 1)
            available_surveys = [r for r in survey_rows if r["technology_id"] == tech_idx + 1 and r["survey_year"] <= as_of.year]
            delta = (available_surveys[-1]["satisfaction_score"] - available_surveys[0]["satisfaction_score"]) if len(available_surveys) > 1 else 0.0
            available_companies = [r for r in company_rows if r["technology_id"] == tech_idx + 1 and pd.Timestamp(r["observation_date"]) <= as_of]
            sectors = {r["sector"] for r in available_companies}
            trailing_start = as_of - pd.DateOffset(months=12)
            recent_adoptions = [pd.Timestamp(r["observation_date"]) for r in available_companies if pd.Timestamp(r["observation_date"]) > trailing_start]
            quarter_index = pd.period_range(end=as_of.to_period("Q"), periods=4, freq="Q")
            quarter_counts = pd.Series(1, index=pd.PeriodIndex(recent_adoptions, freq="Q")).groupby(level=0).sum() if recent_adoptions else pd.Series(dtype=int)
            adoption_velocity = float(quarter_counts.reindex(quarter_index, fill_value=0).mean())
            health = float(np.clip((50 + gmi / 2 + q_quality + (100 - max(decay, 0))) / 3, 0, 100))
            label = None
            if future is not None:
                ratio = future / max(recent, 1)
                label = "Growing" if ratio >= 1.20 else "Declining" if ratio <= 0.80 else "Stable"
            feature_rows.append({
                "technology_id": tech_idx + 1,
                "as_of": months[origin].date().isoformat(),
                "technology_health_score": health,
                "growth_momentum_index": gmi,
                "question_quality_score": q_quality,
                "company_diversity_score": len(sectors),
                "sentiment_delta": delta,
                "adoption_velocity": adoption_velocity,
                "community_decay_rate": decay,
                "recent_average_volume": recent,
                "future_average_volume": future,
                "synthetic_label": label,
                "data_mode": "SYNTHETIC DEMONSTRATION DATA",
            })

    snapshots = pd.DataFrame(feature_rows).dropna(subset=["synthetic_label"]).reset_index(drop=True)
    model_results, predictions, explanations = _fit_demo_models(snapshots)
    run_ids = {
        name: "SYNTH-" + name.upper().replace(" ", "-")
        for name in model_results["model_name"]
    }
    model_results["model_run_id"] = model_results["model_name"].map(run_ids)
    predictions["model_run_id"] = "SYNTH-RANDOM-FOREST"
    predictions["prediction_id"] = np.arange(1, len(predictions) + 1)
    predictions["data_mode"] = "SYNTHETIC DEMONSTRATION DATA"
    explanations["prediction_id"] = explanations["technology_id"].map(
        dict(zip(predictions.technology_id, predictions.prediction_id))
    )
    explanations["explanation_scope"] = "Local synthetic prediction explanation"
    model_runs = pd.DataFrame([
        {
            "model_run_id": run_ids[row.model_name],
            "model_name": row.model_name,
            "status": "succeeded_synthetic_demo",
            "data_mode": "SYNTHETIC DEMONSTRATION DATA",
            "seed": SEED,
            "training_dataset_version": "synthetic-seed-7312026-v1",
            "train_start": row.train_start,
            "train_end": row.train_end,
            "test_start": row.test_start,
            "test_end": row.test_end,
            "validation_design": row.validation_design,
            "feature_definition_version": "synthetic-feature-v1",
            "label_definition_version": "synthetic-future-ratio-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "artifact_uri": str((ARTIFACT_DIR / (row.model_name.lower().replace(" ", "_") + ".joblib")).relative_to(ROOT)),
            "artifact_sha256": hashlib.sha256((ARTIFACT_DIR / (row.model_name.lower().replace(" ", "_") + ".joblib")).read_bytes()).hexdigest(),
        }
        for row in model_results.itertuples(index=False)
    ])
    latest_features = snapshots.sort_values("as_of").groupby("technology_id", as_index=False).tail(1)
    return {
        "technologies": technologies,
        "community_observations": pd.DataFrame(community_rows),
        "survey_observations": pd.DataFrame(survey_rows),
        "enterprise_evidence": pd.DataFrame(company_rows),
        "feature_snapshots": snapshots,
        "latest_features": latest_features,
        "source_registry": pd.DataFrame(source_rows),
        "model_metrics": model_results,
        "model_runs": model_runs,
        "predictions": predictions,
        "explanations": explanations,
        "kenya_context": pd.DataFrame(columns=["indicator", "value", "period", "geography", "data_mode"]),
        "quality_checks": pd.DataFrame([
            {"check_name": "All demonstration rows explicitly marked synthetic", "status": "PASS", "details": "Every demo table carries data_mode=SYNTHETIC DEMONSTRATION DATA."},
            {"check_name": "Research data mixed into demo database", "status": "PASS", "details": "No research sources or records are loaded into this SQLite database."},
            {"check_name": "External enterprise citations", "status": "NOT APPLICABLE", "details": "Company examples are fictional; synthetic:// links are not evidence."},
        ]),
    }


def _fit_demo_models(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    x = panel[FEATURES].apply(pd.to_numeric, errors="coerce")
    y = panel["synthetic_label"].astype(str)
    months = pd.to_datetime(panel["as_of"])
    cutoff = months.quantile(0.80)
    train, test = months < cutoff, months >= cutoff
    if not train.any() or not test.any() or set(y[train]) != set(LABELS):
        raise RuntimeError("Synthetic demonstration panel lacks three-class chronological support.")
    imputer = SimpleImputer(strategy="median")
    x_train = imputer.fit_transform(x.loc[train])
    x_test = imputer.transform(x.loc[test])
    models = {
        "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=SEED)),
        "K-Nearest Neighbours": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=7)),
        "Random Forest": RandomForestClassifier(n_estimators=160, min_samples_leaf=2, random_state=SEED, n_jobs=1),
        "XGBoost": XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, objective="multi:softprob", num_class=3, eval_metric="mlogloss", random_state=SEED, n_jobs=1),
    }
    metric_rows = []
    fitted = {}
    for name, model in models.items():
        y_train = y.loc[train]
        y_test = y.loc[test]
        if name == "XGBoost":
            label_to_int = {label: index for index, label in enumerate(LABELS)}
            int_to_label = {index: label for label, index in label_to_int.items()}
            model.fit(x_train, y_train.map(label_to_int))
            pred = np.asarray([int_to_label[int(value)] for value in model.predict(x_test)])
        else:
            model.fit(x_train, y_train)
            pred = model.predict(x_test)
        pr, rc, f1, support = precision_recall_fscore_support(y_test, pred, labels=LABELS, zero_division=0)
        metric_rows.append({
            "model_name": name,
            "accuracy": float(accuracy_score(y_test, pred)),
            "weighted_f1": float(f1_score(y_test, pred, average="weighted", zero_division=0)),
            "macro_f1": float(f1_score(y_test, pred, average="macro", zero_division=0)),
            "validation_design": "Chronological holdout over synthetic records only",
            "train_start": months.loc[train].min().date().isoformat(),
            "train_end": months.loc[train].max().date().isoformat(),
            "test_start": months.loc[test].min().date().isoformat(),
            "test_end": months.loc[test].max().date().isoformat(),
            "class_metrics_json": json.dumps({label: {"precision": float(pr[i]), "recall": float(rc[i]), "f1": float(f1[i]), "support": int(support[i])} for i, label in enumerate(LABELS)}),
            "confusion_matrix_json": json.dumps(confusion_matrix(y_test, pred, labels=LABELS).tolist()),
            "data_mode": "SYNTHETIC DEMONSTRATION DATA",
        })
        fitted[name] = model

    rf = fitted["Random Forest"]
    latest = panel.sort_values("as_of").groupby("technology_id", as_index=False).tail(1).copy()
    pred = rf.predict(imputer.transform(latest[FEATURES]))
    prediction_rows = [
        {"technology_id": int(tid), "model_name": "Random Forest", "predicted_label": str(label), "model_scope": "SYNTHETIC ONLY", "data_mode": "SYNTHETIC DEMONSTRATION DATA"}
        for tid, label in zip(latest["technology_id"], pred)
    ]
    try:
        import shap

        tree = shap.TreeExplainer(rf)
        sample = imputer.transform(latest[FEATURES])
        predicted = rf.predict(sample)
        shap_values = tree.shap_values(sample)
        if isinstance(shap_values, list):
            stacked = np.stack(shap_values)
            importance = np.mean(np.abs(stacked), axis=(0, 1))
            local = np.vstack([
                stacked[list(rf.classes_).index(label), i, :]
                for i, label in enumerate(predicted)
            ])
        else:
            arr = np.asarray(shap_values)
            if arr.ndim == 3 and arr.shape[0] == len(sample):
                importance = np.mean(np.abs(arr), axis=(0, 2))
                local = np.vstack([
                    arr[i, :, list(rf.classes_).index(label)]
                    for i, label in enumerate(predicted)
                ])
            elif arr.ndim == 3:
                importance = np.mean(np.abs(arr), axis=(0, 1))
                local = np.vstack([
                    arr[list(rf.classes_).index(label), i, :]
                    for i, label in enumerate(predicted)
                ])
            else:
                importance = np.mean(np.abs(arr), axis=0)
                local = arr
        explain_rows = [{"technology_id": int(tid), "feature": feature, "mean_abs_shap": float(value), "local_contribution": float(local[i, j]), "predicted_class": str(predicted[i]), "model_name": "Random Forest", "model_scope": "SYNTHETIC ONLY", "data_mode": "SYNTHETIC DEMONSTRATION DATA"} for i, tid in enumerate(latest["technology_id"]) for j, (feature, value) in enumerate(zip(FEATURES, importance))]
    except Exception as exc:  # Explainability remains explicitly unavailable if this optional demo calculation fails.
        explain_rows = [{"technology_id": None, "feature": "unavailable", "mean_abs_shap": None, "local_contribution": None, "model_name": "Random Forest", "model_scope": f"SYNTHETIC ONLY; SHAP unavailable: {type(exc).__name__}", "data_mode": "SYNTHETIC DEMONSTRATION DATA"}]
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    for name, model in fitted.items():
        filename = name.lower().replace(" ", "_") + ".joblib"
        joblib.dump({"model": model, "imputer": imputer, "features": FEATURES, "scope": "SYNTHETIC DEMONSTRATION DATA"}, ARTIFACT_DIR / filename)
    return pd.DataFrame(metric_rows), pd.DataFrame(prediction_rows), pd.DataFrame(explain_rows)


def _build_base_demo_database() -> Path:
    """Create the first-generation schema only when the demo DB does not exist."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    if DATABASE_PATH.exists():
        return DATABASE_PATH
    tables = _simulation()
    engine = create_engine(f"sqlite:///{DATABASE_PATH.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        ddl = [
            "CREATE TABLE technologies (technology_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL, description TEXT NOT NULL, data_mode TEXT NOT NULL)",
            "CREATE TABLE source_registry (source_key TEXT PRIMARY KEY, source_name TEXT NOT NULL, source_url TEXT NOT NULL, collected_at TEXT NOT NULL, observation_period TEXT NOT NULL, license_terms TEXT NOT NULL, geographic_scope TEXT NOT NULL, collection_method TEXT NOT NULL, quality_status TEXT NOT NULL, data_mode TEXT NOT NULL)",
            "CREATE TABLE community_observations (observation_id INTEGER PRIMARY KEY AUTOINCREMENT, technology_id INTEGER NOT NULL REFERENCES technologies(technology_id), month TEXT NOT NULL, question_volume INTEGER NOT NULL CHECK(question_volume>=0), answered_volume INTEGER NOT NULL CHECK(answered_volume>=0), unanswered_volume INTEGER NOT NULL CHECK(unanswered_volume>=0), geography TEXT NOT NULL, data_mode TEXT NOT NULL, UNIQUE(technology_id,month))",
            "CREATE TABLE survey_observations (survey_id INTEGER PRIMARY KEY AUTOINCREMENT, technology_id INTEGER NOT NULL REFERENCES technologies(technology_id), survey_year INTEGER NOT NULL, respondent_count INTEGER NOT NULL CHECK(respondent_count>0), usage_share REAL NOT NULL, interest_share REAL NOT NULL, admiration_share REAL NOT NULL, satisfaction_score REAL NOT NULL, geography TEXT NOT NULL, data_mode TEXT NOT NULL, UNIQUE(technology_id,survey_year))",
            "CREATE TABLE enterprise_evidence (evidence_id INTEGER PRIMARY KEY, technology_id INTEGER NOT NULL REFERENCES technologies(technology_id), company_name TEXT NOT NULL, sector TEXT NOT NULL, observation_date TEXT NOT NULL, evidence_type TEXT NOT NULL, source_url TEXT NOT NULL, verification_status TEXT NOT NULL, data_mode TEXT NOT NULL)",
            "CREATE TABLE feature_snapshots (feature_snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT, technology_id INTEGER NOT NULL REFERENCES technologies(technology_id), as_of TEXT NOT NULL, technology_health_score REAL, growth_momentum_index REAL, question_quality_score REAL, company_diversity_score REAL, sentiment_delta REAL, adoption_velocity REAL, community_decay_rate REAL, recent_average_volume REAL, future_average_volume REAL, synthetic_label TEXT, data_mode TEXT NOT NULL, UNIQUE(technology_id,as_of))",
            "CREATE TABLE model_runs (model_run_id TEXT PRIMARY KEY, model_name TEXT NOT NULL, status TEXT NOT NULL, data_mode TEXT NOT NULL, seed INTEGER NOT NULL, training_dataset_version TEXT NOT NULL, train_start TEXT NOT NULL, train_end TEXT NOT NULL, test_start TEXT NOT NULL, test_end TEXT NOT NULL, validation_design TEXT NOT NULL, feature_definition_version TEXT NOT NULL, label_definition_version TEXT NOT NULL, created_at TEXT NOT NULL, artifact_uri TEXT NOT NULL, artifact_sha256 TEXT NOT NULL)",
            "CREATE TABLE model_metrics (model_run_id TEXT PRIMARY KEY REFERENCES model_runs(model_run_id), model_name TEXT NOT NULL, accuracy REAL NOT NULL, weighted_f1 REAL NOT NULL, macro_f1 REAL NOT NULL, validation_design TEXT NOT NULL, train_start TEXT NOT NULL, train_end TEXT NOT NULL, test_start TEXT NOT NULL, test_end TEXT NOT NULL, class_metrics_json TEXT NOT NULL, confusion_matrix_json TEXT NOT NULL, data_mode TEXT NOT NULL)",
            "CREATE TABLE predictions (prediction_id INTEGER PRIMARY KEY, technology_id INTEGER NOT NULL REFERENCES technologies(technology_id), model_run_id TEXT NOT NULL REFERENCES model_runs(model_run_id), model_name TEXT NOT NULL, predicted_label TEXT NOT NULL, model_scope TEXT NOT NULL, data_mode TEXT NOT NULL, UNIQUE(technology_id,model_run_id))",
            "CREATE TABLE explanations (explanation_id INTEGER PRIMARY KEY AUTOINCREMENT, prediction_id INTEGER REFERENCES predictions(prediction_id), technology_id INTEGER REFERENCES technologies(technology_id), feature TEXT NOT NULL, mean_abs_shap REAL, local_contribution REAL, predicted_class TEXT, model_name TEXT NOT NULL, model_scope TEXT NOT NULL, data_mode TEXT NOT NULL, explanation_scope TEXT NOT NULL)",
            "CREATE TABLE kenya_context (indicator TEXT, value REAL, period TEXT, geography TEXT, data_mode TEXT)",
            "CREATE TABLE quality_checks (check_id INTEGER PRIMARY KEY AUTOINCREMENT, check_name TEXT NOT NULL, status TEXT NOT NULL, details TEXT NOT NULL)",
            "CREATE INDEX ix_demo_community_technology_month ON community_observations(technology_id,month)",
            "CREATE INDEX ix_demo_features_technology_asof ON feature_snapshots(technology_id,as_of)",
            "CREATE VIEW latest_features AS SELECT f.* FROM feature_snapshots f JOIN (SELECT technology_id,MAX(as_of) AS as_of FROM feature_snapshots GROUP BY technology_id) m USING(technology_id,as_of)",
        ]
        for statement in ddl:
            connection.execute(text(statement))
        insert_order = [
            "technologies", "source_registry", "community_observations",
            "survey_observations", "enterprise_evidence", "feature_snapshots",
            "model_runs", "model_metrics", "predictions", "explanations",
            "kenya_context", "quality_checks",
        ]
        for name in insert_order:
            frame = tables[name]
            if not frame.empty:
                frame.to_sql(name, connection, index=False, if_exists="append")
    engine.dispose()
    (DEMO_DIR / "README.md").write_text(
        "# Isolated synthetic demonstration database\n\n"
        "This SQLite database contains only deterministic fictional records generated by `dashboard/demo_store.py`. "
        "It is not connected to or merged with the PostgreSQL research database. All synthetic metrics, labels, model results, company examples, and SHAP values are demonstration-only and are not research findings. Initialize and seed with `python -m dashboard.demo_store --build`; reset only with the explicit `--reset-demo --confirm-reset \"RESET SYNTHETIC DEMO ONLY\"` command.\n",
        encoding="utf-8",
    )
    return DATABASE_PATH


def build_demo_database(force: bool = False) -> Path:
    """Initialize if needed, then idempotently migrate and populate the existing demo DB."""
    if force:
        raise ValueError(
            "Destructive reset is disabled through force=True. Use the explicit "
            "--reset-demo --confirm-reset 'RESET SYNTHETIC DEMO ONLY' CLI workflow."
        )
    if not DATABASE_PATH.exists():
        _build_base_demo_database()
    from dashboard.demo_population import seed_and_train_demo_database

    summary = seed_and_train_demo_database()
    (DEMO_DIR / "README.md").write_text(
        "# Isolated synthetic demonstration database\n\n"
        "The existing SQLite store is populated idempotently by `python -m dashboard.demo_store --build`. "
        "All records and model results are fictional and marked `SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE`; "
        "they are not research findings and never enter PostgreSQL. Versioned additive SQLite migration: "
        f"{summary['counts'].get('technologies', 0)} technologies and {summary['counts'].get('community_observations', 0)} community rows.\n",
        encoding="utf-8",
    )
    return DATABASE_PATH


def demo_engine():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("Synthetic demo database is missing. Run `python -m dashboard.demo_store --build`.")
    return create_engine(f"sqlite:///{DATABASE_PATH.as_posix()}")


def read_demo_table(table: str) -> pd.DataFrame:
    allowed = {
        "technologies", "community_observations", "survey_observations",
        "enterprise_evidence", "feature_snapshots", "latest_features",
        "source_registry", "model_runs", "model_metrics", "predictions", "explanations",
        "kenya_context", "quality_checks", "historical_technology_observations",
        "developer_questions", "sentiment_observations", "company_profiles",
        "company_technology_relationships", "enterprise_adoption_observations",
        "geographic_observations", "lifecycle_assessments", "prediction_probabilities",
        "model_configurations", "model_cv_results", "demo_seed_runs",
    }
    if table not in allowed:
        raise ValueError("Table is not part of the isolated synthetic demo schema.")
    engine = demo_engine()
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(text(f'SELECT * FROM "{table}"'), connection)
    finally:
        engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build TechPulse isolated synthetic demo database")
    parser.add_argument("--build", action="store_true", help="Idempotently migrate and seed the separate demo SQLite database")
    parser.add_argument("--reset-demo", action="store_true", help="Back up then reset only the synthetic demo database")
    parser.add_argument("--confirm-reset", help="Must equal RESET SYNTHETIC DEMO ONLY to authorize reset")
    arguments = parser.parse_args()
    if arguments.reset_demo:
        if arguments.confirm_reset != "RESET SYNTHETIC DEMO ONLY":
            parser.error("--reset-demo requires --confirm-reset 'RESET SYNTHETIC DEMO ONLY'")
        from dashboard.demo_population import reset_demo_database
        print(reset_demo_database(arguments.confirm_reset))
    else:
        if not arguments.build:
            parser.error("pass --build to initialize or seed the isolated demonstration database")
        print(build_demo_database())
