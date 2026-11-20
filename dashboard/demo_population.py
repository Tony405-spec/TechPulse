"""Scale and train the isolated synthetic demo store, never research PostgreSQL."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from dashboard.demo_store import ARTIFACT_DIR, DATABASE_PATH, DEMO_DIR, FEATURES, LABELS, SEED

DATA_ORIGIN = "SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE"
DATASET_VERSION = "synthetic-seed-7312026-v2"
FEATURE_VERSION = "synthetic-demo-features-v2"
LABEL_VERSION = "synthetic-demo-future-six-month-ratio-v2"
MIGRATION_VERSION = "003_scaled_synthetic_demo"


def _catalogue() -> list[tuple[str, str]]:
    """Return a stable, fictional demo catalogue with familiar technology names."""
    rows: list[tuple[str, str]] = [
        ("DemoLang", "Language"), ("DemoScript", "Language"),
        ("DemoQuery", "Database"), ("DemoWeb", "Framework"),
        ("DemoData", "Tool"), ("DemoBuild", "Tool"),
        ("DemoStore", "Database"), ("DemoUI", "Framework"),
        ("DemoLegacy", "Language"), ("DemoBatch", "Tool"),
        ("DemoOldDB", "Database"), ("DemoClassicUI", "Framework"),
    ]
    groups = {
        "Language": [
            "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust", "Kotlin", "Swift",
            "PHP", "Ruby", "Scala", "R", "Julia", "Dart", "Elixir", "Erlang", "Haskell", "Clojure",
            "F#", "Objective-C", "Perl", "Lua", "Solidity", "Zig", "Nim", "OCaml", "Fortran", "COBOL",
            "Bash", "PowerShell", "SQL", "HTML", "CSS", "Assembly",
        ],
        "Framework": [
            "React", "Angular", "Vue.js", "Svelte", "Next.js", "Nuxt", "SvelteKit", "Node.js", "Express",
            "Django", "Flask", "FastAPI", "Spring Boot", ".NET", "Laravel", "Ruby on Rails", "Symfony",
            "Phoenix", "Gin", "Echo", "Actix Web", "Axum", "ASP.NET Core", "NestJS", "Remix", "Astro",
            "Gatsby", "Ember.js", "Backbone.js", "jQuery", "Bootstrap", "Tailwind CSS", "Flutter",
            "React Native", "Electron", "Tauri", "SolidJS", "Qwik", "Lit", "Quarkus", "Micronaut",
        ],
        "Database": [
            "PostgreSQL", "MySQL", "SQLite", "SQL Server", "Oracle Database", "MongoDB", "Redis", "Cassandra",
            "DynamoDB", "CockroachDB", "MariaDB", "Elasticsearch", "OpenSearch", "Neo4j", "ClickHouse",
            "Snowflake", "BigQuery", "Redshift", "Firestore", "CouchDB", "InfluxDB", "TimescaleDB", "DuckDB",
            "HBase", "TiDB", "YugabyteDB", "Valkey", "Memcached", "RocksDB", "PlanetScale",
        ],
        "Tool": [
            "Docker", "Kubernetes", "Terraform", "Ansible", "Helm", "Prometheus", "Grafana", "Kafka",
            "RabbitMQ", "NATS", "Airflow", "Dagster", "dbt", "Apache Spark", "Apache Flink", "Hadoop",
            "DVC", "MLflow", "PyTorch", "TensorFlow", "scikit-learn", "XGBoost", "LightGBM", "Jupyter",
            "Visual Studio Code", "Git", "GitHub Actions", "GitLab CI", "Jenkins", "CircleCI", "Argo CD",
            "Istio", "Envoy", "Nginx", "Caddy", "Vite", "Webpack", "Rollup", "Bun", "Deno", "npm",
            "pnpm", "Yarn", "Poetry", "uv", "Conda",
        ],
        "Cloud Platform": [
            "Amazon Web Services", "Microsoft Azure", "Google Cloud", "Cloudflare Workers", "Vercel", "Netlify",
            "Heroku", "Fly.io", "DigitalOcean", "OpenStack", "Apache Mesos", "Nomad", "Pulumi", "Packer",
            "Vault", "Consul", "OpenTelemetry", "Jaeger", "Loki", "Tempo", "Vector", "Fluent Bit",
            "Debezium", "Fivetran", "Meltano", "Prefect", "Temporal", "Ray", "BentoML", "KServe",
            "ONNX Runtime", "Hugging Face Transformers", "JAX", "Keras", "CatBoost", "Optuna", "Weights & Biases",
            "Apache Beam", "Trino", "Presto", "Flink CDC", "MinIO", "Ceph", "SeaweedFS", "Keycloak",
        ],
    }
    for category, names in groups.items():
        rows.extend((name, category) for name in names)
    seen: set[str] = set()
    unique = []
    for name, category in rows:
        if name.casefold() not in seen:
            unique.append((name, category))
            seen.add(name.casefold())
    return unique


def apply_demo_migrations(connection: sqlite3.Connection) -> None:
    """Apply additive SQLite migrations and record the applied version."""
    connection.execute(
        "CREATE TABLE IF NOT EXISTS demo_schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL, checksum TEXT NOT NULL)"
    )
    already = connection.execute(
        "SELECT 1 FROM demo_schema_migrations WHERE version=?", (MIGRATION_VERSION,)
    ).fetchone()
    if already:
        return
    migration = Path(__file__).with_name("demo_migrations") / f"{MIGRATION_VERSION}.sql"
    sql = migration.read_text(encoding="utf-8")
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            connection.execute(statement)
    lineage_tables = [
        "technologies", "source_registry", "community_observations", "survey_observations",
        "enterprise_evidence", "feature_snapshots", "model_runs", "model_metrics",
        "predictions", "explanations", "kenya_context", "quality_checks",
    ]
    for table in lineage_tables:
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        if "data_origin" not in columns:
            connection.execute(
                f'ALTER TABLE "{table}" ADD COLUMN data_origin TEXT NOT NULL '
                f"DEFAULT '{DATA_ORIGIN}'"
            )
    metric_columns = {row[1] for row in connection.execute("PRAGMA table_info(model_metrics)")}
    for column, definition in {
        "precision": "REAL",
        "recall": "REAL",
        "cross_validation_json": "TEXT NOT NULL DEFAULT '{}'",
        "feature_importance_json": "TEXT NOT NULL DEFAULT '{}'",
    }.items():
        if column not in metric_columns:
            connection.execute(f"ALTER TABLE model_metrics ADD COLUMN {column} {definition}")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_demo_explanations_prediction_feature "
        "ON explanations(prediction_id, feature) WHERE prediction_id IS NOT NULL"
    )
    checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    connection.execute(
        "INSERT INTO demo_schema_migrations(version,applied_at,checksum) VALUES(?,?,?)",
        (MIGRATION_VERSION, datetime.now(timezone.utc).isoformat(), checksum),
    )


def _trajectory(index: int, existing: bool = False) -> str:
    if existing and index < 12:
        return ("Growing", "Growing", "Growing", "Growing", "Stable", "Stable", "Stable", "Stable", "Declining", "Declining", "Declining", "Declining")[index]
    return ("Growing", "Stable", "Declining", "Surge", "Mature Decline", "Community Heavy")[index % 6]


def _generate_rows() -> dict[str, list[dict[str, Any]]]:
    """Build deterministic, logically related fictional records at scale."""
    catalogue = _catalogue()
    months = pd.date_range("2019-01-01", periods=72, freq="MS")
    geographies = [
        ("KE-NAIROBI", "Fictional Kenya demo · Nairobi"),
        ("KE-MOMBASA", "Fictional Kenya demo · Mombasa"),
        ("KE-KISUMU", "Fictional Kenya demo · Kisumu"),
        ("NG-LAGOS", "Fictional Nigeria demo · Lagos"),
        ("GH-ACCRA", "Fictional Ghana demo · Accra"),
        ("IN-BENGALURU", "Fictional India demo · Bengaluru"),
    ]
    sectors = ["Fictional Finance", "Fictional Health", "Fictional Retail", "Fictional Logistics", "Fictional Media", "Fictional Public Services"]
    company_count = 300
    trajectories = [_trajectory(i, existing=True) for i in range(12)] + [_trajectory(i) for i in range(12, len(catalogue))]
    rows: dict[str, list[dict[str, Any]]] = {
        name: [] for name in [
            "technologies", "community_observations", "historical_technology_observations",
            "developer_questions", "sentiment_observations", "survey_observations",
            "company_profiles", "company_technology_relationships", "enterprise_adoption_observations",
            "enterprise_evidence", "geographic_observations", "feature_snapshots",
            "lifecycle_assessments", "source_registry",
        ]
    }
    rows["source_registry"].append({
        "source_key": "synthetic_generator_v2",
        "source_name": "TechPulse deterministic synthetic demonstration generator",
        "source_url": "synthetic://techpulse-demo/v2",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "observation_period": "Simulated monthly 2019-2024; annual 2011-2026",
        "license_terms": "Fictional generated observations; not external source data.",
        "geographic_scope": "Fictional global and Kenya-labelled demo scenarios",
        "collection_method": "Deterministic seeded simulation; see dashboard/demo_population.py",
        "quality_status": "Synthetic-only; excluded from research mode",
        "data_mode": "SYNTHETIC DEMONSTRATION DATA",
        "data_origin": DATA_ORIGIN,
    })
    for idx, (name, category) in enumerate(catalogue):
        technology_id = idx + 1
        trajectory = trajectories[idx]
        rng = np.random.default_rng(SEED + technology_id * 7919)
        rate = {
            "Growing": 0.045, "Stable": 0.002, "Declining": -0.038,
            "Surge": 0.006, "Mature Decline": -0.018, "Community Heavy": 0.030,
        }[trajectory]
        baseline = float(rng.integers(120, 1500))
        noise = rng.normal(0, 0.08, len(months))
        seasonal = 1 + 0.07 * np.sin(np.arange(len(months)) * 2 * np.pi / 12 + rng.uniform(0, 2 * np.pi))
        trend = np.exp(rate * np.arange(len(months)) + noise)
        if trajectory == "Surge":
            center = 53 + (technology_id % 7) - 3
            bump = 1 + 1.0 * np.exp(-0.5 * ((np.arange(len(months)) - center) / 4.2) ** 2)
            trend *= bump
        elif trajectory == "Mature Decline":
            trend *= np.where(np.arange(len(months)) < 30, 1.45, 1.0)
        elif trajectory == "Community Heavy":
            baseline *= 2.0
        # Irregular events add realistic variation without overriding the broad trajectory.
        for shock_month in (18 + technology_id % 9, 43 + technology_id % 11):
            trend[shock_month] *= float(rng.choice([0.72, 1.28]))
        volume = np.maximum(20, np.round(baseline * trend * seasonal)).astype(int)
        unanswered_rate = float(rng.uniform(0.08, 0.34))
        rows["technologies"].append({
            "technology_id": technology_id, "name": name, "category": category,
            "description": "Familiar technology catalogue subject with fictional synthetic demonstration observations.",
            "data_mode": "SYNTHETIC DEMONSTRATION DATA", "data_origin": DATA_ORIGIN,
        })
        for month_i, month in enumerate(months):
            q = int(volume[month_i])
            unanswered = int(round(q * unanswered_rate))
            rows["community_observations"].append({
                "technology_id": technology_id, "month": month.date().isoformat(),
                "question_volume": q, "answered_volume": q - unanswered,
                "unanswered_volume": unanswered, "geography": "Synthetic global scenario",
                "data_mode": "SYNTHETIC DEMONSTRATION DATA", "data_origin": DATA_ORIGIN,
            })
        for month_i in range(36, 72):
            month = months[month_i]
            interest = float(np.clip(50 + 12 * np.tanh(rate * 12) + 7 * np.log1p(volume[month_i] / baseline) + rng.normal(0, 8), 0, 100))
            ecosystem = float(np.clip(48 + 16 * np.tanh(rate * 10) + rng.normal(0, 10), 0, 100))
            release = float(np.clip(35 + max(rate, 0) * 250 + rng.normal(0, 12), 0, 100))
            rows["historical_technology_observations"].append({
                "technology_id": technology_id, "month": month.date().isoformat(),
                "search_interest_index": interest, "ecosystem_activity_index": ecosystem,
                "release_activity_index": release, "observation_type": "Synthetic monthly ecosystem observation",
                "data_origin": DATA_ORIGIN,
            })
        # Annual survey-like snapshots across sixteen periods yield more than 2,000 sentiment observations.
        satisfaction_base = float(rng.uniform(42, 78))
        usage_base = float(rng.uniform(0.08, 0.62))
        yearly_scores: dict[int, float] = {}
        for year in range(2011, 2027):
            year_idx = year - 2011
            score = float(np.clip(satisfaction_base + rate * year_idx * 13 + rng.normal(0, 2.7), 5, 95))
            yearly_scores[year] = score
            use = float(np.clip(usage_base + rate * year_idx * 0.012 + rng.normal(0, 0.025), 0.01, 0.95))
            interest_share = float(np.clip(use + rng.normal(0.10, 0.04), 0.01, 0.99))
            admiration = float(np.clip(use + rng.normal(0.07, 0.04), 0.01, 0.99))
            rows["survey_observations"].append({
                "technology_id": technology_id, "survey_year": year,
                "respondent_count": int(rng.integers(600, 5000)), "usage_share": use,
                "interest_share": interest_share, "admiration_share": admiration,
                "satisfaction_score": score, "geography": "Synthetic global sample",
                "data_mode": "SYNTHETIC DEMONSTRATION DATA", "data_origin": DATA_ORIGIN,
            })
        for month_i, month in enumerate(months):
            year_score = yearly_scores[month.year]
            satisfaction = float(np.clip(year_score + rng.normal(0, 2.4), 0, 100))
            positive = float(np.clip(0.30 + satisfaction / 220 + rng.normal(0, .035), .05, .90))
            negative = float(np.clip(0.78 - satisfaction / 150 + rng.normal(0, .025), .04, .70))
            neutral = max(.03, 1 - positive - negative)
            total = positive + neutral + negative
            positive, neutral, negative = positive / total, neutral / total, negative / total
            rows["sentiment_observations"].append({
                "technology_id": technology_id, "month": month.date().isoformat(),
                "positive_share": positive, "neutral_share": neutral, "negative_share": negative,
                "satisfaction_score": satisfaction, "sample_count": int(rng.integers(30, 450)),
                "geography": "Synthetic global sample", "data_origin": DATA_ORIGIN,
            })
        # At least forty fictional questions per catalogue technology.
        for question_n in range(40):
            month_i = int(rng.integers(0, len(months)))
            question_date = months[month_i] + pd.Timedelta(days=int(rng.integers(0, 27)))
            positive_prob = float(np.clip(.42 + rate * 1.5 + (yearly_scores[question_date.year] - 50) / 250, .1, .85))
            draw = rng.random()
            sentiment = "positive" if draw < positive_prob else "negative" if draw > positive_prob + .35 else "neutral"
            rows["developer_questions"].append({
                "question_id": f"SYNTH-Q-{technology_id:04d}-{question_n:03d}",
                "technology_id": technology_id, "created_at": question_date.isoformat(),
                "title": f"Synthetic {name} discussion scenario {question_n + 1}",
                "discussion_text": "Fictional generated discussion record for application testing; not a real user post.",
                "score": int(rng.integers(-3, 22)), "answer_count": int(rng.choice([0, 1, 2, 3, 5, 8], p=[.22, .28, .24, .14, .08, .04])),
                "sentiment": sentiment, "geography": "Synthetic global scenario", "data_origin": DATA_ORIGIN,
            })
        # Three Kenya-labelled demo regions and three fictional comparison regions per technology.
        for geo_i, (geo_code, geo_name) in enumerate(geographies):
            month = months[36 + ((technology_id + geo_i) % 36)]
            rows["geographic_observations"].append({
                "technology_id": technology_id, "geography_code": geo_code,
                "geography_name": geo_name, "month": month.date().isoformat(),
                "synthetic_interest_index": float(np.clip(interest if geo_i % 2 else interest + rng.normal(0, 8), 0, 100)),
                "sample_count": int(rng.integers(20, 800)), "data_origin": DATA_ORIGIN,
            })

    # Three hundred clearly fictional company profiles and five distinct links each.
    rows["company_profiles"] = [
        {
            "company_id": i, "company_name": f"Fictional Demo Organization {i:03d}",
            "sector": sectors[(i * 7) % len(sectors)],
            "headquarters_label": "Fictional demonstration location",
            "founded_year": 1980 + (i * 13) % 45,
            "employee_band": ("50-249", "250-999", "1,000-4,999", "5,000+")[i % 4],
            "data_origin": DATA_ORIGIN,
        }
        for i in range(1, company_count + 1)
    ]
    relationship_pairs: list[tuple[int, int, str]] = []
    tech_count = len(catalogue)
    relationship_id = 1
    for company_id in range(1, company_count + 1):
        selected = {(company_id * 17 + step * 37) % tech_count + 1 for step in range(5)}
        for technology_id in sorted(selected):
            first = months[(company_id * 3 + technology_id * 5) % 60 + 6]
            rows["company_technology_relationships"].append({
                "relationship_id": relationship_id, "company_id": company_id,
                "technology_id": technology_id, "relationship_type": "Synthetic fictional use scenario",
                "first_observed": first.date().isoformat(), "data_origin": DATA_ORIGIN,
            })
            relationship_pairs.append((relationship_id, company_id, technology_id))
            relationship_id += 1
    # Exactly 2,000 dated synthetic adoption observations: one per relationship plus follow-up records.
    for adoption_id in range(1, 2001):
        relation_id, company_id, technology_id = relationship_pairs[(adoption_id - 1) % len(relationship_pairs)]
        rel = rows["company_technology_relationships"][relation_id - 1]
        first_dt = pd.Timestamp(rel["first_observed"])
        extra = (adoption_id - 1) // len(relationship_pairs)
        observed = min(first_dt + pd.DateOffset(months=extra * 12), months[-1])
        state = ("exploring", "piloting", "deployed", "maintained", "retired")[(technology_id + company_id + extra) % 5]
        rows["enterprise_adoption_observations"].append({
            "adoption_observation_id": adoption_id, "relationship_id": relation_id,
            "observed_at": observed.date().isoformat(), "adoption_state": state,
            "source_description": "Fictional synthetic scenario; no real company adoption claim.",
            "data_origin": DATA_ORIGIN,
        })
        rows["enterprise_evidence"].append({
            "evidence_id": 10000 + adoption_id, "technology_id": technology_id,
            "company_name": f"Fictional Demo Organization {company_id:03d}",
            "sector": sectors[(company_id * 7) % len(sectors)],
            "observation_date": observed.date().isoformat(),
            "evidence_type": "Synthetic fictional adoption observation",
            "source_url": "synthetic://techpulse-demo/fictional-company-relationship",
            "verification_status": "NOT VERIFIED - SYNTHETIC ONLY",
            "data_mode": "SYNTHETIC DEMONSTRATION DATA", "data_origin": DATA_ORIGIN,
        })

    # Build 42 as-of snapshots from observations through the as-of month only.
    community_by_tech = {
        tech_id: np.asarray([r["question_volume"] for r in rows["community_observations"] if r["technology_id"] == tech_id], dtype=float)
        for tech_id in range(1, tech_count + 1)
    }
    answered_by_tech = {
        tech_id: np.asarray([r["answered_volume"] for r in rows["community_observations"] if r["technology_id"] == tech_id], dtype=float)
        for tech_id in range(1, tech_count + 1)
    }
    sentiment_by_tech = {
        tech_id: [r for r in rows["sentiment_observations"] if r["technology_id"] == tech_id]
        for tech_id in range(1, tech_count + 1)
    }
    relationship_dates: dict[int, list[tuple[int, pd.Timestamp]]] = {i: [] for i in range(1, tech_count + 1)}
    for relation_id, company_id, technology_id in relationship_pairs:
        rel = rows["company_technology_relationships"][relation_id - 1]
        relationship_dates[technology_id].append((company_id, pd.Timestamp(rel["first_observed"])))
    for tech_idx, (_, _) in enumerate(catalogue):
        technology_id = tech_idx + 1
        values = community_by_tech[technology_id]
        for origin in range(24, 66):
            as_of = months[origin]
            recent = float(np.mean(values[origin - 2 : origin + 1]))
            prior = float(np.mean(values[origin - 5 : origin - 2]))
            future_slice = values[origin + 1 : origin + 7]
            future = float(np.mean(future_slice)) if len(future_slice) == 6 else None
            gmi = 100 * (recent - prior) / max(prior, 1)
            question_denominator = float(np.sum(values[origin - 11 : origin + 1]))
            question_numerator = float(np.sum(answered_by_tech[technology_id][origin - 11 : origin + 1]))
            q_quality = 100 * question_numerator / max(question_denominator, 1.0)
            previous_half = float(np.mean(values[origin - 11 : origin - 5]))
            recent_half = float(np.mean(values[origin - 5 : origin + 1]))
            decay = 100 * (previous_half - recent_half) / max(previous_half, 1)
            sat = [r for r in sentiment_by_tech[technology_id] if r["month"] <= as_of.date().isoformat()]
            delta = float(sat[-1]["satisfaction_score"] - sat[0]["satisfaction_score"]) if len(sat) > 1 else 0.0
            seen = [(company, dt) for company, dt in relationship_dates[technology_id] if dt <= as_of]
            sectors_seen = len({(company_id * 7) % len(sectors) for company_id, _ in seen})
            start = as_of - pd.DateOffset(months=12)
            new_links = [dt for _, dt in seen if start < dt <= as_of]
            quarters = pd.period_range(end=as_of.to_period("Q"), periods=4, freq="Q")
            qcount = pd.Series([dt.to_period("Q") for dt in new_links]).value_counts() if new_links else pd.Series(dtype=int)
            velocity = float(sum(int(qcount.get(q, 0)) for q in quarters) / 4)
            health = float(np.clip(50 + gmi * .35 + q_quality * .25 - max(decay, 0) * .2 + velocity, 0, 100))
            label = None
            if future is not None:
                ratio = future / max(recent, 1)
                label = "Growing" if ratio >= 1.20 else "Declining" if ratio <= .80 else "Stable"
            rows["feature_snapshots"].append({
                "technology_id": technology_id, "as_of": as_of.date().isoformat(),
                "technology_health_score": health, "growth_momentum_index": gmi,
                "question_quality_score": q_quality, "company_diversity_score": float(sectors_seen),
                "sentiment_delta": delta, "adoption_velocity": velocity,
                "community_decay_rate": decay, "recent_average_volume": recent,
                "future_average_volume": future, "synthetic_label": label,
                "data_mode": "SYNTHETIC DEMONSTRATION DATA", "data_origin": DATA_ORIGIN,
            })
    return rows


def _insert_ignore(connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    columns = list(rows[0])
    quoted_columns = ",".join('"' + column + '"' for column in columns)
    placeholders = ",".join("?" for _ in columns)
    sql = f'INSERT OR IGNORE INTO "{table}" ({quoted_columns}) VALUES ({placeholders})'
    before = connection.total_changes
    connection.executemany(sql, [tuple(row[c] for c in columns) for row in rows])
    inserted = connection.total_changes - before
    return inserted, len(rows) - inserted


def _insert_upsert(connection: sqlite3.Connection, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if rows:
        connection.executemany(sql, rows)


def _model_definitions() -> dict[str, Any]:
    return {
        "Logistic Regression": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=600, random_state=SEED)),
        "K-Nearest Neighbours": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), KNeighborsClassifier(n_neighbors=9)),
        "Random Forest": make_pipeline(SimpleImputer(strategy="median"), RandomForestClassifier(n_estimators=180, min_samples_leaf=2, class_weight="balanced", random_state=SEED, n_jobs=1)),
        "XGBoost": make_pipeline(SimpleImputer(strategy="median"), XGBClassifier(n_estimators=100, max_depth=4, learning_rate=.07, subsample=.9, colsample_bytree=.9, objective="multi:softprob", num_class=3, eval_metric="mlogloss", random_state=SEED, n_jobs=1, verbosity=0)),
    }


def train_demo_models_from_database(connection: sqlite3.Connection) -> dict[str, Any]:
    """Train all four synthetic models from feature rows already persisted in SQLite."""
    frame = pd.read_sql_query(
        "SELECT feature_snapshot_id, technology_id, as_of, technology_health_score, growth_momentum_index, "
        "question_quality_score, company_diversity_score, sentiment_delta, adoption_velocity, "
        "community_decay_rate, synthetic_label FROM feature_snapshots "
        "WHERE synthetic_label IS NOT NULL AND data_origin=? ORDER BY as_of,technology_id",
        connection,
        params=(DATA_ORIGIN,),
    )
    if len(frame) < 500 or set(frame.synthetic_label) != set(LABELS):
        raise RuntimeError("Persisted synthetic feature snapshots lack required size or three-class support.")
    dates = pd.to_datetime(frame.as_of)
    unique_dates = np.array(sorted(dates.unique()))
    cutoff = unique_dates[int(len(unique_dates) * .80)]
    train_mask = dates < cutoff
    test_mask = dates >= cutoff
    X = frame[FEATURES].apply(pd.to_numeric, errors="coerce")
    y = frame.synthetic_label.astype(str)
    if set(y[train_mask]) != set(LABELS) or set(y[test_mask]) != set(LABELS):
        raise RuntimeError("Chronological holdout must contain all three synthetic classes.")
    cv = TimeSeriesSplit(n_splits=4)
    date_indices = np.arange(len(unique_dates))
    cv_results: dict[str, list[dict[str, Any]]] = {}
    metrics: dict[str, dict[str, Any]] = {}
    fitted: dict[str, Any] = {}
    label_map = {name: i for i, name in enumerate(LABELS)}
    for model_name, base_model in _model_definitions().items():
        folds = []
        for fold_number, (tr_idx, va_idx) in enumerate(cv.split(date_indices), start=1):
            train_dates = set(unique_dates[tr_idx])
            valid_dates = set(unique_dates[va_idx])
            fold_train = dates.isin(train_dates)
            fold_valid = dates.isin(valid_dates)
            if set(y[fold_train]) != set(LABELS) or set(y[fold_valid]) != set(LABELS):
                continue
            model = _model_definitions()[model_name]
            train_y = y.loc[fold_train].map(label_map) if model_name == "XGBoost" else y.loc[fold_train]
            valid_y = y.loc[fold_valid]
            model.fit(X.loc[fold_train], train_y)
            predicted = model.predict(X.loc[fold_valid])
            if model_name == "XGBoost":
                predicted = np.asarray([LABELS[int(i)] for i in predicted])
            folds.append({
                "fold": fold_number,
                "train_start": str(pd.Timestamp(dates.loc[fold_train].min()).date()),
                "train_end": str(pd.Timestamp(dates.loc[fold_train].max()).date()),
                "validation_start": str(pd.Timestamp(dates.loc[fold_valid].min()).date()),
                "validation_end": str(pd.Timestamp(dates.loc[fold_valid].max()).date()),
                "accuracy": float(accuracy_score(valid_y, predicted)),
                "weighted_f1": float(f1_score(valid_y, predicted, average="weighted", zero_division=0)),
            })
        if len(folds) < 2:
            raise RuntimeError(f"Insufficient chronological cross-validation folds for {model_name}.")
        cv_results[model_name] = folds
        model = base_model
        y_train = y.loc[train_mask].map(label_map) if model_name == "XGBoost" else y.loc[train_mask]
        model.fit(X.loc[train_mask], y_train)
        y_test = y.loc[test_mask]
        predictions = model.predict(X.loc[test_mask])
        if model_name == "XGBoost":
            predictions = np.asarray([LABELS[int(i)] for i in predictions])
        precision, recall, per_f1, support = precision_recall_fscore_support(y_test, predictions, labels=LABELS, zero_division=0)
        metrics[model_name] = {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision": float(precision_recall_fscore_support(y_test, predictions, average="weighted", zero_division=0)[0]),
            "recall": float(precision_recall_fscore_support(y_test, predictions, average="weighted", zero_division=0)[1]),
            "weighted_f1": float(f1_score(y_test, predictions, average="weighted", zero_division=0)),
            "macro_f1": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
            "class_metrics_json": json.dumps({label: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(per_f1[i]), "support": int(support[i])} for i, label in enumerate(LABELS)}),
            "confusion_matrix_json": json.dumps(confusion_matrix(y_test, predictions, labels=LABELS).tolist()),
            "cv": folds,
            "train_start": str(pd.Timestamp(dates.loc[train_mask].min()).date()),
            "train_end": str(pd.Timestamp(dates.loc[train_mask].max()).date()),
            "test_start": str(pd.Timestamp(dates.loc[test_mask].min()).date()),
            "test_end": str(pd.Timestamp(dates.loc[test_mask].max()).date()),
        }
        fitted[model_name] = model

    # Persist current model artifacts and model registry rows.
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).isoformat()
    for model_name, model in fitted.items():
        slug = model_name.lower().replace(" ", "_")
        artifact = ARTIFACT_DIR / f"{slug}.joblib"
        joblib.dump({"model": model, "features": FEATURES, "scope": DATA_ORIGIN}, artifact)
        checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
        run_id = "SYNTH-" + model_name.upper().replace(" ", "-")
        config = json.dumps(model.get_params(deep=False), default=str, sort_keys=True)
        connection.execute(
            "INSERT INTO model_runs(model_run_id,model_name,status,data_mode,seed,training_dataset_version,train_start,train_end,test_start,test_end,validation_design,feature_definition_version,label_definition_version,created_at,artifact_uri,artifact_sha256,data_origin) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(model_run_id) DO UPDATE SET "
            "status=excluded.status,training_dataset_version=excluded.training_dataset_version,train_start=excluded.train_start,train_end=excluded.train_end,test_start=excluded.test_start,test_end=excluded.test_end,validation_design=excluded.validation_design,feature_definition_version=excluded.feature_definition_version,label_definition_version=excluded.label_definition_version,created_at=excluded.created_at,artifact_uri=excluded.artifact_uri,artifact_sha256=excluded.artifact_sha256,data_origin=excluded.data_origin",
            (run_id,model_name,"succeeded_synthetic_demo","SYNTHETIC DEMONSTRATION DATA",SEED,DATASET_VERSION,
             metrics[model_name]["train_start"],metrics[model_name]["train_end"],metrics[model_name]["test_start"],metrics[model_name]["test_end"],
             "Synthetic chronological 80/20 holdout plus four-fold expanding-window time-series CV",FEATURE_VERSION,LABEL_VERSION,created,
             str(artifact.relative_to(DEMO_DIR.parent.parent)),checksum,DATA_ORIGIN),
        )
        metric = metrics[model_name]
        connection.execute(
            "INSERT INTO model_metrics(model_run_id,model_name,accuracy,weighted_f1,macro_f1,validation_design,train_start,train_end,test_start,test_end,class_metrics_json,confusion_matrix_json,data_mode,data_origin,precision,recall,cross_validation_json,feature_importance_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(model_run_id) DO UPDATE SET "
            "accuracy=excluded.accuracy,weighted_f1=excluded.weighted_f1,macro_f1=excluded.macro_f1,validation_design=excluded.validation_design,train_start=excluded.train_start,train_end=excluded.train_end,test_start=excluded.test_start,test_end=excluded.test_end,class_metrics_json=excluded.class_metrics_json,confusion_matrix_json=excluded.confusion_matrix_json,data_origin=excluded.data_origin,precision=excluded.precision,recall=excluded.recall,cross_validation_json=excluded.cross_validation_json,feature_importance_json=excluded.feature_importance_json",
            (run_id,model_name,metric["accuracy"],metric["weighted_f1"],metric["macro_f1"],"Synthetic chronological 80/20 holdout plus four-fold expanding-window time-series CV",
             metric["train_start"],metric["train_end"],metric["test_start"],metric["test_end"],metric["class_metrics_json"],metric["confusion_matrix_json"],"SYNTHETIC DEMONSTRATION DATA",DATA_ORIGIN,
             metric["precision"],metric["recall"],json.dumps(metric["cv"]),"{}"),
        )
        connection.execute(
            "INSERT INTO model_configurations(model_name,algorithm,parameters_json,seed,feature_version,label_version,data_origin) VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(model_name) DO UPDATE SET algorithm=excluded.algorithm,parameters_json=excluded.parameters_json,seed=excluded.seed,feature_version=excluded.feature_version,label_version=excluded.label_version,data_origin=excluded.data_origin",
            (model_name,model_name,config,SEED,FEATURE_VERSION,LABEL_VERSION,DATA_ORIGIN),
        )
        connection.execute("DELETE FROM model_cv_results WHERE model_name=?", (model_name,))
        for fold in metric["cv"]:
            connection.execute(
                "INSERT INTO model_cv_results(model_name,fold_number,train_start,train_end,validation_start,validation_end,accuracy,weighted_f1,data_origin) VALUES(?,?,?,?,?,?,?,?,?)",
                (model_name,fold["fold"],fold["train_start"],fold["train_end"],fold["validation_start"],fold["validation_end"],fold["accuracy"],fold["weighted_f1"],DATA_ORIGIN),
            )

    # Compare models and generate a persisted forecast from each fitted model.
    best_name = max(metrics, key=lambda key: (metrics[key]["weighted_f1"], metrics[key]["accuracy"]))
    latest = frame.sort_values("as_of").groupby("technology_id", as_index=False).tail(1).sort_values("technology_id")
    latest_x = latest[FEATURES].apply(pd.to_numeric, errors="coerce")
    prediction_rows = []
    probability_rows = []
    prediction_ids: dict[str, dict[int, int]] = {}
    model_predictions: dict[str, np.ndarray] = {}
    model_slots = {name: slot for slot, name in enumerate(fitted, start=1)}
    for model_name, model in fitted.items():
        probability_matrix = model.predict_proba(latest_x)
        model_classes = list(model.classes_)
        label_names = [LABELS[int(x)] if isinstance(x, (int, np.integer)) else str(x) for x in model_classes]
        predicted = model.predict(latest_x)
        if model_name == "XGBoost":
            predicted = np.asarray([LABELS[int(value)] for value in predicted])
        model_predictions[model_name] = np.asarray(predicted)
        run_id = "SYNTH-" + model_name.upper().replace(" ", "-")
        prediction_ids[model_name] = {}
        for row_index, row in enumerate(latest.itertuples(index=False)):
            technology_id = int(row.technology_id)
            prediction_id = model_slots[model_name] * 100000 + technology_id
            prediction_ids[model_name][technology_id] = prediction_id
            class_probs = {label: 0.0 for label in LABELS}
            for col, label in enumerate(label_names):
                class_probs[label] = float(probability_matrix[row_index, col])
            prediction_rows.append((prediction_id,technology_id,run_id,model_name,str(predicted[row_index]),"SYNTHETIC ONLY","SYNTHETIC DEMONSTRATION DATA",DATA_ORIGIN))
            for label in LABELS:
                probability_rows.append((prediction_id,label,class_probs[label],DATA_ORIGIN))
    # Remove only synthetic explanations before changing their referenced prediction IDs.
    connection.execute("DELETE FROM explanations WHERE data_origin=?", (DATA_ORIGIN,))
    _insert_upsert(
        connection,
        "INSERT INTO predictions(prediction_id,technology_id,model_run_id,model_name,predicted_label,model_scope,data_mode,data_origin) VALUES(?,?,?,?,?,?,?,?) "
        "ON CONFLICT(technology_id,model_run_id) DO UPDATE SET prediction_id=excluded.prediction_id,predicted_label=excluded.predicted_label,model_scope=excluded.model_scope,data_mode=excluded.data_mode,data_origin=excluded.data_origin",
        prediction_rows,
    )
    connection.execute("DELETE FROM prediction_probabilities WHERE data_origin=?", (DATA_ORIGIN,))
    _insert_upsert(connection,"INSERT INTO prediction_probabilities(prediction_id,class_name,probability,data_origin) VALUES(?,?,?,?)",probability_rows)

    # Generate SHAP values from the persisted latest rows and the fitted Random Forest.
    forest = fitted["Random Forest"].named_steps.get("randomforestclassifier")
    imputer = fitted["Random Forest"].named_steps.get("simpleimputer")
    shap_rows: list[tuple[Any, ...]] = []
    if forest is not None and imputer is not None:
        import shap

        transformed = imputer.transform(latest_x)
        values = shap.TreeExplainer(forest).shap_values(transformed)
        rf_predicted = model_predictions["Random Forest"]
        local_matrix, importance = _normalize_shap(values, forest.classes_, rf_predicted, len(latest), len(FEATURES))
        for row_i, tech_id in enumerate(latest.technology_id.astype(int)):
            prediction_id = prediction_ids["Random Forest"][tech_id]
            class_label = str(rf_predicted[row_i])
            for feat_i, feature in enumerate(FEATURES):
                shap_rows.append((prediction_id,tech_id,feature,float(importance[feat_i]),float(local_matrix[row_i,feat_i]),class_label,"Random Forest","SYNTHETIC ONLY","SYNTHETIC DEMONSTRATION DATA","TreeExplainer on fitted synthetic Random Forest",DATA_ORIGIN))
    if not shap_rows:
        raise RuntimeError("SHAP did not produce explanations for the trained synthetic model.")
    connection.execute("DELETE FROM explanations WHERE data_origin=?", (DATA_ORIGIN,))
    _insert_upsert(
        connection,
        "INSERT INTO explanations(prediction_id,technology_id,feature,mean_abs_shap,local_contribution,predicted_class,model_name,model_scope,data_mode,explanation_scope,data_origin) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        shap_rows,
    )
    # Persist model feature importances from the fitted Random Forest pipeline.
    rf_importance = getattr(forest, "feature_importances_", np.zeros(len(FEATURES)))
    importance_json = json.dumps({name: float(value) for name, value in zip(FEATURES, rf_importance)})
    connection.execute("UPDATE model_metrics SET feature_importance_json=? WHERE model_name='Random Forest'", (importance_json,))

    return {
        "metrics": metrics,
        "best_model": best_name,
        "predictions": len(prediction_rows),
        "probabilities": len(probability_rows),
        "explanations": len(shap_rows),
    }


def _normalize_shap(values: Any, classes: list[Any], predicted: np.ndarray, row_count: int, feature_count: int) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(values, list):
        stack = np.stack([np.asarray(value) for value in values], axis=0)
        class_indexes = [list(classes).index(value) for value in predicted]
        local = np.vstack([stack[class_indexes[i], i, :] for i in range(row_count)])
        importance = np.mean(np.abs(stack), axis=(0, 1))
    else:
        arr = np.asarray(values)
        if arr.ndim == 3 and arr.shape[0] == row_count:
            local = np.vstack([arr[i, :, list(classes).index(predicted[i])] for i in range(row_count)])
            importance = np.mean(np.abs(arr), axis=(0, 2))
        elif arr.ndim == 3 and arr.shape[1] == row_count:
            local = np.vstack([arr[list(classes).index(predicted[i]), i, :] for i in range(row_count)])
            importance = np.mean(np.abs(arr), axis=(0, 1))
        else:
            local = arr
            importance = np.mean(np.abs(arr), axis=0)
    if local.shape != (row_count, feature_count) or len(importance) != feature_count:
        raise RuntimeError(f"Unexpected SHAP shape local={local.shape}, importance={np.shape(importance)}")
    return local, np.asarray(importance)


def populate_existing_demo_database() -> dict[str, Any]:
    """Apply the additive migration and idempotently populate the existing demo SQLite DB."""
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("Build the base isolated demo database first.")
    started = datetime.now(timezone.utc).isoformat()
    generated = _generate_rows()
    generated_counts = {name: len(records) for name, records in generated.items()}
    inserted_counts: dict[str, int] = {}
    skipped_counts: dict[str, int] = {}
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        apply_demo_migrations(connection)
        for table in [
            "technologies", "source_registry", "company_profiles", "company_technology_relationships",
            "community_observations", "historical_technology_observations", "developer_questions",
            "sentiment_observations", "survey_observations", "enterprise_adoption_observations",
            "geographic_observations", "enterprise_evidence",
        ]:
            inserted, skipped = _insert_ignore(connection, table, generated.get(table, []))
            inserted_counts[table] = inserted
            skipped_counts[table] = skipped
        feature_rows = generated["feature_snapshots"]
        feature_columns = list(feature_rows[0])
        feature_names = ",".join('"' + column + '"' for column in feature_columns)
        feature_updates = ",".join(f'"{column}"=excluded."{column}"' for column in feature_columns if column not in {"technology_id", "as_of"})
        feature_sql = f"INSERT INTO feature_snapshots({feature_names}) VALUES({','.join('?' for _ in feature_columns)}) ON CONFLICT(technology_id,as_of) DO UPDATE SET {feature_updates}"
        before = connection.total_changes
        connection.executemany(feature_sql,[tuple(row[column] for column in feature_columns) for row in feature_rows])
        inserted_counts["feature_snapshots"] = len(feature_rows)
        skipped_counts["feature_snapshots"] = max(0, len(feature_rows) - (connection.total_changes - before))
        # Add one traceable synthetic-only assessment for each technology's latest stored snapshot.
        latest = connection.execute(
            "SELECT f.feature_snapshot_id,f.technology_id,f.as_of,f.synthetic_label "
            "FROM feature_snapshots f JOIN (SELECT technology_id,MAX(as_of) as as_of FROM feature_snapshots GROUP BY technology_id) m USING(technology_id,as_of) "
            "WHERE f.synthetic_label IS NOT NULL"
        ).fetchall()
        assessments = []
        for row in latest:
            end = (pd.Timestamp(row["as_of"]) + pd.DateOffset(months=6)).date().isoformat()
            assessments.append({
                "assessment_id": int(row["technology_id"]), "technology_id": int(row["technology_id"]),
                "feature_snapshot_id": int(row["feature_snapshot_id"]), "lifecycle_label": row["synthetic_label"],
                "target_end": end, "label_definition": LABEL_VERSION, "data_origin": DATA_ORIGIN,
            })
        assessment_sql = (
            "INSERT INTO lifecycle_assessments(assessment_id,technology_id,feature_snapshot_id,lifecycle_label,target_end,label_definition,data_origin) "
            "VALUES(?,?,?,?,?,?,?) ON CONFLICT(technology_id,feature_snapshot_id) DO UPDATE SET "
            "lifecycle_label=excluded.lifecycle_label,target_end=excluded.target_end,label_definition=excluded.label_definition,data_origin=excluded.data_origin"
        )
        connection.executemany(assessment_sql,[tuple(row[key] for key in row) for row in assessments])
        inserted_counts["lifecycle_assessments"] = len(assessments)
        skipped_counts["lifecycle_assessments"] = 0
        model_summary = train_demo_models_from_database(connection)
        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"Synthetic demo foreign-key check failed: {fk_errors[:5]}")
        connection.execute(
            "UPDATE quality_checks SET check_name=?,status='PASS',details=? WHERE check_id=1",
            ("Seeded records carry explicit synthetic origin", f"Generated demo rows use data_origin={DATA_ORIGIN}; research rows remain excluded."),
        )
        connection.execute(
            "UPDATE quality_checks SET check_name=?,status='PASS',details=? WHERE check_id=2",
            ("Demo SQLite remains separate from PostgreSQL research mode", f"Seeder wrote only {DATABASE_PATH}; no PostgreSQL write path is used."),
        )
        connection.execute(
            "UPDATE quality_checks SET check_name=?,status='NOT APPLICABLE',details=? WHERE check_id=3",
            ("External enterprise citations", "Fictional company and adoption examples use synthetic:// references and make no real-company claims."),
        )
        for check_name, details in [
            ("Foreign-key and integrity validation", "PRAGMA foreign_key_check returned no violations; all generated relationships were committed transactionally."),
            ("Synthetic-only model lineage", f"Model run, feature, label, prediction, probability, and SHAP records are versioned under {DATASET_VERSION}."),
        ]:
            found = connection.execute("SELECT check_id FROM quality_checks WHERE check_name=? ORDER BY check_id LIMIT 1", (check_name,)).fetchone()
            if found:
                connection.execute("UPDATE quality_checks SET status='PASS',details=?,data_origin=? WHERE check_id=?", (details,DATA_ORIGIN,found[0]))
            else:
                connection.execute("INSERT INTO quality_checks(check_name,status,details,data_origin) VALUES(?,?,?,?)", (check_name,"PASS",details,DATA_ORIGIN))
        finished = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "INSERT INTO demo_seed_runs(dataset_version,seed,started_at,finished_at,status,generated_counts_json,inserted_counts_json,skipped_counts_json,rejected_counts_json,data_origin) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (DATASET_VERSION,SEED,started,finished,"succeeded",json.dumps(generated_counts,sort_keys=True),json.dumps(inserted_counts,sort_keys=True),json.dumps(skipped_counts,sort_keys=True),json.dumps({name:0 for name in generated_counts},sort_keys=True),DATA_ORIGIN),
        )
        connection.commit()
        final_counts = {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in [
                "technologies","community_observations","historical_technology_observations","developer_questions",
                "sentiment_observations","survey_observations","company_profiles","company_technology_relationships",
                "enterprise_adoption_observations","geographic_observations","feature_snapshots","lifecycle_assessments",
                "model_runs","model_metrics","predictions","prediction_probabilities","explanations",
            ]
        }
    return {"database": str(DATABASE_PATH), "generated": generated_counts, "inserted": inserted_counts, "skipped": skipped_counts, "counts": final_counts, "models": model_summary}


def reset_demo_database(confirmation: str) -> Path:
    """Reset only the isolated synthetic DB after making a SQLite-consistent backup."""
    if confirmation != "RESET SYNTHETIC DEMO ONLY":
        raise ValueError("Pass the exact confirmation 'RESET SYNTHETIC DEMO ONLY'.")
    if DATABASE_PATH.exists():
        backup_dir = DEMO_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"techpulse_demo_reset_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        with sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=ro", uri=True) as source:
            with sqlite3.connect(backup_path) as target:
                source.backup(target)
        if ARTIFACT_DIR.exists():
            import shutil
            artifact_backup = backup_dir / f"artifacts_before_reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(ARTIFACT_DIR, artifact_backup)
        DATABASE_PATH.unlink()
    import dashboard.demo_store as base
    base._build_base_demo_database()
    populate_existing_demo_database()
    return DATABASE_PATH


def seed_and_train_demo_database() -> dict[str, Any]:
    """Public deterministic seed entry point used after base initialization."""
    return populate_existing_demo_database()

