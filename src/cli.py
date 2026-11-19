"""Operational commands for the canonical TechPulse PostgreSQL warehouse."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
load_dotenv(ROOT / ".env", override=False)


def _engine():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required for PostgreSQL commands; no CSV fallback is performed."
        )
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with python -m pip install -r requirements.txt"
        ) from exc
    # requirements.txt provides psycopg2-binary. SQLAlchemy 2 defaults a
    # plain postgresql:// URL to psycopg (v3), which is not installed here.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url.removeprefix("postgresql://")
    return create_engine(url, pool_pre_ping=True)


def db_migrate() -> None:
    from sqlalchemy import text

    engine = _engine()
    migration_files = sorted(MIGRATIONS.glob("*.sql"))
    if not migration_files:
        raise FileNotFoundError(f"No SQL migrations found under {MIGRATIONS}")
    applied_versions: list[str] = []
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit"))
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS audit.schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now(), checksum text NOT NULL)"
            )
        )
        for path in migration_files:
            migration = path.stem
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            previous = conn.execute(
                text("SELECT checksum FROM audit.schema_migrations WHERE version=:v"),
                {"v": migration},
            ).scalar()
            if previous:
                if previous != checksum:
                    raise RuntimeError(
                        f"Applied migration checksum differs for {migration}; create a new migration rather than editing history."
                    )
                print(f"{migration} already applied")
                continue
            # Execute the repository-controlled file as a whole: splitting on
            # semicolons breaks quoted strings and comments.
            conn.exec_driver_sql(sql)
            conn.execute(
                text(
                    "INSERT INTO audit.schema_migrations(version,checksum) VALUES(:v,:c)"
                ),
                {"v": migration, "c": checksum},
            )
            applied_versions.append(migration)
    print(
        "Applied migrations: " + ", ".join(applied_versions)
        if applied_versions
        else "All migrations already applied"
    )


def db_health() -> None:
    from sqlalchemy import text

    with _engine().connect() as conn:
        version = conn.execute(text("SELECT version() ")).scalar_one()
        schemas = (
            conn.execute(
                text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw','staging','core','analytics','ml','audit') ORDER BY schema_name"
                )
            )
            .scalars()
            .all()
        )
        migration_count = conn.execute(
            text("SELECT count(*) FROM audit.schema_migrations")
        ).scalar_one()
    print(
        json.dumps(
            {
                "postgresql": version,
                "schemas": schemas,
                "migration_count": migration_count,
                "healthy": len(schemas) == 6,
            },
            indent=2,
        )
    )


def validate_data() -> dict[str, Any]:
    """Profile repository source files without imputing or rewriting values."""
    files = [
        DATA / name
        for name in (
            "stackexchange.csv",
            "developer_survey_usage.csv",
            "fortune.csv",
            "ev311.csv",
            "files.csv",
        )
    ]
    report: dict[str, Any] = {
        "created_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "sources": [],
        "critical_issues": [],
    }
    for path in files:
        if not path.exists():
            report["sources"].append(
                {"path": str(path.relative_to(ROOT)), "status": "missing"}
            )
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size == 0:
            report["sources"].append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "status": "empty",
                    "sha256": digest,
                    "rows": 0,
                }
            )
            continue
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            report["sources"].append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "status": "empty",
                    "sha256": digest,
                    "rows": 0,
                }
            )
            continue
        dates = {}
        for col in frame.columns:
            if col.lower() in {"date", "creation_date", "period", "survey_year"}:
                source_values = (
                    frame[col].astype("string")
                    if col.lower() == "survey_year"
                    else frame[col]
                )
                parsed = pd.to_datetime(source_values, errors="coerce")
                if parsed.notna().any():
                    dates[col] = {
                        "min": parsed.min().isoformat(),
                        "max": parsed.max().isoformat(),
                        "invalid": int(parsed.isna().sum()),
                    }
        source_profile: dict[str, Any] = {
            "path": str(path.relative_to(ROOT)),
            "status": "present",
            "sha256": digest,
            "rows": int(len(frame)),
            "columns": list(frame.columns),
            "null_rate": frame.isna().mean().round(6).to_dict(),
            "duplicate_rows": int(frame.duplicated().sum()),
            "date_coverage": dates,
        }
        source_key = {
            "stackexchange.csv": "stackexchange",
            "developer_survey_usage.csv": "survey",
            "fortune.csv": "fortune",
        }.get(path.name)
        if source_key:
            try:
                _, strict_report = _validate_ingest_input(source_key, frame)
                source_profile["critical_validation"] = strict_report
            except ValueError as exc:
                source_profile["critical_validation"] = {
                    "passed": False,
                    "error": str(exc),
                }
                report["critical_issues"].append(
                    {"source": path.name, "error": str(exc)}
                )
        report["sources"].append(source_profile)
    run_dir = OUTPUTS / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%S%fZ")
    report_path = run_dir / f"data_quality_{run_id}.json"
    report["report_path"] = str(report_path.relative_to(ROOT))
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    return report


def _validate_ingest_input(
    key: str, frame: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reject malformed critical fields and report duplicates before DB writes."""
    required = {
        "stackexchange": ["tag", "date", "question_count", "unanswered_count"],
        "survey": [
            "technology_name",
            "survey_year",
            "respondent_count",
            "developer_usage_share",
            "developer_interest_share",
            "developer_admiration_share",
        ],
        "fortune": ["rank", "name"],
    }[key]
    missing_columns = sorted(set(required) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"{key} is missing critical columns: {missing_columns}")
    duplicate_rows = int(frame.duplicated().sum())
    original_rows = len(frame)
    clean = frame.drop_duplicates().copy()
    if key == "survey":
        # The canonical table's unique key is technology + geography + year;
        # the local input has no category column in that key. Identical rows
        # remain safely deduplicable above, but conflicting values must not be
        # silently resolved by row order during an upsert.
        natural_key = ["technology_name", "survey_year"]
        conflicts = clean.loc[
            clean.duplicated(natural_key, keep=False)
        ].sort_values(natural_key)
        if not conflicts.empty:
            examples = conflicts[natural_key].drop_duplicates().head(10).to_dict("records")
            raise ValueError(
                "survey contains conflicting source rows for the canonical "
                f"technology/year key; resolve source categories or schema mapping before ingest; keys={examples}"
            )
    null_counts = clean[required].isna().sum().to_dict()
    if any(null_counts.values()):
        raise ValueError(f"{key} has nulls in required fields: {null_counts}")
    date_coverage = None
    if key == "stackexchange":
        dates = pd.to_datetime(clean["date"], errors="coerce")
        questions = pd.to_numeric(clean["question_count"], errors="coerce")
        unanswered = pd.to_numeric(clean["unanswered_count"], errors="coerce")
        invalid = (
            dates.isna()
            | questions.isna()
            | unanswered.isna()
            # This source is a daily snapshot of cumulative tag totals. A zero
            # total is therefore invalid for a tag already present in the
            # source, even when unanswered_count is also zero.
            | (questions <= 0)
            | (unanswered < 0)
            | (unanswered > questions)
        )
        if invalid.any():
            raise ValueError(
                "stackexchange has "
                f"{int(invalid.sum())} invalid dates, non-positive cumulative counts, "
                "or impossible unanswered counts; "
                f"examples={clean.loc[invalid, ['tag', 'date', 'question_count', 'unanswered_count']].head(10).to_dict('records')}"
            )
        date_coverage = {
            "start": dates.min().date().isoformat(),
            "end": dates.max().date().isoformat(),
        }
    elif key == "survey":
        years = pd.to_numeric(clean["survey_year"], errors="coerce")
        if years.isna().any() or ((years < 2000) | (years > 2100)).any():
            raise ValueError("survey contains invalid survey_year values")
        for column in [
            "developer_usage_share",
            "developer_interest_share",
            "developer_admiration_share",
        ]:
            values = pd.to_numeric(clean[column], errors="coerce")
            if values.isna().any() or ((values < 0) | (values > 1)).any():
                raise ValueError(
                    f"survey.{column} contains missing values or shares outside [0,1]"
                )
        date_coverage = {
            "start_year": int(years.min()),
            "end_year": int(years.max()),
        }
    report = {
        "source_rows": int(original_rows),
        "rows_after_deduplication": int(len(clean)),
        "duplicate_rows_removed": duplicate_rows,
        "nulls_in_critical_columns": null_counts,
        "date_coverage": date_coverage,
        "critical_validation": "passed",
    }
    return clean, report


def ingest(source: str, from_year: int) -> None:
    """Store retained local inputs in raw source_records with deterministic idempotency."""
    from sqlalchemy import text

    engine = _engine()
    files = {
        "stackexchange": "stackexchange.csv",
        "survey": "developer_survey_usage.csv",
        "fortune": "fortune.csv",
    }
    selected = files if source == "all" else {source: files[source]}
    with engine.begin() as conn:
        for key, filename in selected.items():
            path = DATA / filename
            if not path.exists() or path.stat().st_size == 0:
                raise FileNotFoundError(
                    f"Configured ingestion source is missing or empty: {path}"
                )
            raw_frame = pd.read_csv(path)
            try:
                frame, input_report = _validate_ingest_input(key, raw_frame)
            except ValueError as exc:
                _record_failed_ingestion(engine, key, filename, path, raw_frame, exc)
                raise
            date_col = (
                "date"
                if key == "stackexchange"
                else "survey_year" if key == "survey" else None
            )
            if date_col:
                date_values = (
                    frame[date_col].astype("string")
                    if date_col == "survey_year"
                    else frame[date_col]
                )
                years = pd.to_datetime(date_values, errors="coerce").dt.year
                frame = frame.loc[years >= from_year].copy()
            source_class = "reported" if key == "survey" else "unknown"
            source_id = conn.execute(
                text("""
                INSERT INTO audit.data_sources(source_key,publisher,title,url,licence_terms,methodology,geographic_scope,source_class,metadata)
                VALUES(:key,:publisher,:title,:url,:licence,:method,:geo,:class,CAST(:meta AS jsonb))
                ON CONFLICT(source_key) DO UPDATE SET title=EXCLUDED.title, source_class=EXCLUDED.source_class
                RETURNING source_id
            """),
                {
                    "key": f"local_{key}",
                    "publisher": "Unverified local file attribution",
                    "title": filename,
                    "url": None,
                    "licence": "Unverified; review before redistribution",
                    "method": "Repository snapshot; source methodology not supplied with the file",
                    "geo": "global_or_unspecified",
                    "class": source_class,
                    "meta": json.dumps(
                        {
                            "path": f"data/{filename}",
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        }
                    ),
                },
            ).scalar_one()
            geography_id = conn.execute(text("""
                INSERT INTO core.geographies(code,name,level) VALUES('GLOBAL','Global / geography unspecified','global')
                ON CONFLICT(code) DO UPDATE SET name=EXCLUDED.name RETURNING geography_id
            """)).scalar_one()
            run_id = conn.execute(
                text("""
                INSERT INTO audit.ingestion_runs(source_id,status,source_version,checksum,rows_read,config_hash,report)
                VALUES(:source,'running',:version,:checksum,:rows,:config,'{}'::jsonb) RETURNING run_id
            """),
                {
                    "source": source_id,
                    "version": path.name,
                    "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "rows": input_report["source_rows"],
                    "config": hashlib.sha256(f"{key}:{from_year}".encode()).hexdigest(),
                },
            ).scalar_one()
            conn.execute(
                text("""
                INSERT INTO audit.source_documents(source_id,title,retrieved_at,checksum,geography,metadata)
                VALUES(:source,:title,now(),:checksum,'global_or_unspecified',CAST(:meta AS jsonb))
                ON CONFLICT DO NOTHING
            """),
                {
                    "source": source_id,
                    "title": filename,
                    "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "meta": json.dumps(
                        {
                            "repository_path": f"data/{filename}",
                            "publication_period": "not established",
                        }
                    ),
                },
            )
            retained = 0
            for idx, row in frame.iterrows():
                payload = {
                    k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()
                }
                encoded = json.dumps(payload, sort_keys=True, default=str)
                checksum = hashlib.sha256(encoded.encode()).hexdigest()
                natural_key = f"{filename}:{idx}"
                raw_result = conn.execute(
                    text("""
                    INSERT INTO raw.source_records(source_id,run_id,natural_key,observed_at,payload,checksum)
                    VALUES(:source,:run,:key,NULL,CAST(:payload AS jsonb),:checksum)
                    ON CONFLICT(source_id,natural_key,checksum) DO NOTHING
                """),
                    {
                        "source": source_id,
                        "run": run_id,
                        "key": natural_key,
                        "payload": encoded,
                        "checksum": checksum,
                    },
                )
                retained += max(raw_result.rowcount, 0)
                if key == "fortune":
                    conn.execute(
                        text("""
                        INSERT INTO core.company_profiles(source_id,source_company_id,company_name,sector,metadata)
                        VALUES(:source,:external_id,:name,:sector,CAST(:meta AS jsonb))
                        ON CONFLICT(source_id,source_company_id) DO UPDATE SET company_name=EXCLUDED.company_name,
                          sector=EXCLUDED.sector,metadata=EXCLUDED.metadata
                    """),
                        {
                            "source": source_id,
                            "external_id": str(payload.get("rank")),
                            "name": str(payload.get("name") or "Unknown company"),
                            "sector": payload.get("sector"),
                            "meta": json.dumps(
                                {
                                    "title": payload.get("title"),
                                    "ticker": payload.get("ticker"),
                                    "hq": payload.get("hq"),
                                    "source_limit": "company profile only; no technology adoption claim",
                                }
                            ),
                        },
                    )
                    continue
                tech_name = str(
                    payload.get("technology_name")
                    or payload.get("technology")
                    or payload.get("tag")
                    or ""
                ).strip()
                if not tech_name:
                    continue
                technology_id = conn.execute(
                    text("""
                    INSERT INTO core.technologies(canonical_name) VALUES(:name)
                    ON CONFLICT(canonical_name) DO UPDATE SET canonical_name=EXCLUDED.canonical_name
                    RETURNING technology_id
                """),
                    {"name": tech_name},
                ).scalar_one()
                if key == "stackexchange":
                    observed = pd.to_datetime(payload.get("date"), errors="coerce")
                    if pd.isna(observed):
                        continue
                    period = observed.date().replace(day=1)
                    count = pd.to_numeric(
                        payload.get("question_count"), errors="coerce"
                    )
                    unanswered = pd.to_numeric(
                        payload.get("unanswered_count"), errors="coerce"
                    )
                    if (
                        pd.isna(count)
                        or count < 0
                        or pd.isna(unanswered)
                        or unanswered < 0
                    ):
                        continue
                    count, unanswered = int(count), int(unanswered)
                    unanswered = min(unanswered, count)
                    natural = f"{tech_name}:{period.isoformat()}"
                    conn.execute(
                        text("""
                        INSERT INTO analytics.community_monthly_metrics
                          (technology_id,geography_id,source_id,period_start,observed_at,question_count,unanswered_count,answer_rate,source_metadata)
                        VALUES(:tech,:geo,:source,:period,:observed,:count,:unanswered,
                          CASE WHEN :count=0 THEN NULL ELSE (:count-:unanswered)::numeric/:count END,CAST(:meta AS jsonb))
                        ON CONFLICT(technology_id,geography_id,source_id,period_start) DO UPDATE SET
                          question_count=EXCLUDED.question_count,unanswered_count=EXCLUDED.unanswered_count,
                          answer_rate=EXCLUDED.answer_rate,observed_at=EXCLUDED.observed_at
                    """),
                        {
                            "tech": technology_id,
                            "geo": geography_id,
                            "source": source_id,
                            "period": period,
                            "observed": observed.to_pydatetime(),
                            "count": count,
                            "unanswered": unanswered,
                            "meta": json.dumps(
                                {
                                    "natural_key": natural,
                                    "source_class": "unknown",
                                    "geography_note": "not specified in source",
                                }
                            ),
                        },
                    )
                elif key == "survey":
                    year = int(payload["survey_year"])
                    values = {
                        name: pd.to_numeric(payload.get(col), errors="coerce")
                        for name, col in {
                            "usage": "developer_usage_share",
                            "interest": "developer_interest_share",
                            "admiration": "developer_admiration_share",
                        }.items()
                    }
                    respondent_count = pd.to_numeric(
                        payload.get("respondent_count"), errors="coerce"
                    )
                    conn.execute(
                        text("""
                        INSERT INTO analytics.developer_survey_observations
                          (source_id,technology_id,geography_id,survey_year,observed_at,respondent_count,
                           worked_with_count,want_to_work_with_count,admired_count,usage_share,interest_share,admiration_share,source_class,metadata)
                        VALUES(:source,:tech,:geo,:year,NULL,:respondents,:worked,:wanted,:admired,
                          :usage,:interest,:admiration,'reported',CAST(:meta AS jsonb))
                        ON CONFLICT(source_id,technology_id,geography_id,survey_year) DO UPDATE SET
                          respondent_count=EXCLUDED.respondent_count,usage_share=EXCLUDED.usage_share,
                          interest_share=EXCLUDED.interest_share,admiration_share=EXCLUDED.admiration_share,
                          observed_at=NULL,metadata=EXCLUDED.metadata
                    """),
                        {
                            "source": source_id,
                            "tech": technology_id,
                            "geo": geography_id,
                            "year": year,
                            "respondents": (
                                None
                                if pd.isna(respondent_count)
                                else int(respondent_count)
                            ),
                            "worked": payload.get("worked_with_count"),
                            "wanted": payload.get("want_to_work_with_count"),
                            "admired": payload.get("admired_count"),
                            "usage": values["usage"],
                            "interest": values["interest"],
                            "admiration": values["admiration"],
                            "meta": json.dumps(
                                {
                                    "source_type": payload.get("source_type"),
                                    "geography_note": "survey sample is global/unspecified",
                                }
                            ),
                        },
                    )
            conn.execute(
                text(
                    """UPDATE audit.ingestion_runs SET finished_at=now(),status='succeeded',rows_written=:written,
                report=CAST(:report AS jsonb) WHERE run_id=:run"""
                ),
                {
                    "written": retained,
                    "report": json.dumps(
                        {
                            "source_file": filename,
                            "from_year": from_year,
                            "rows_read": input_report["source_rows"],
                            **input_report,
                            "rows_after_year_filter": len(frame),
                            "rows_written": retained,
                            "geographic_scope": "global_or_unspecified",
                        }
                    ),
                    "run": run_id,
                },
            )
            conn.execute(
                text(
                    """INSERT INTO audit.data_quality_checks(run_id,check_name,severity,passed,observed_value,details)
                VALUES(:run,'raw_record_retention','info',true,CAST(:value AS jsonb),'Source rows retained idempotently; see source limitation metadata')"""
                ),
                {
                    "run": run_id,
                    "value": json.dumps(
                        {
                            "rows_written": retained,
                            **input_report,
                            "rows_after_year_filter": len(frame),
                        }
                    ),
                },
            )
            print(
                f"{key}: rows_read={len(frame)} raw_rows={retained}; curated data loaded where mapped; from_year={from_year}"
            )
    print(
        "Ingestion completed. Community aggregates, survey reports, and company profiles were promoted only into their corresponding canonical tables. No company technology adoption was inferred."
    )


def _record_failed_ingestion(
    engine: Any,
    key: str,
    filename: str,
    path: Path,
    frame: pd.DataFrame,
    error: ValueError,
) -> None:
    """Persist critical validation failures separately from the rolled-back load."""
    from sqlalchemy import text

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    failure = str(error)
    examples: list[dict[str, Any]] = []
    if key == "stackexchange" and {
        "tag",
        "date",
        "question_count",
        "unanswered_count",
    }.issubset(frame.columns):
        question_count = pd.to_numeric(frame["question_count"], errors="coerce")
        unanswered = pd.to_numeric(frame["unanswered_count"], errors="coerce")
        invalid = (
            (question_count < 0) | (unanswered < 0) | (unanswered > question_count)
        )
        examples = frame.loc[invalid].head(10).to_dict("records")
    report = {
        "validation_status": "blocked",
        "validation_error": failure,
        "rows_read": int(len(frame)),
        "rows_written": 0,
        "source_path": f"data/{filename}",
        "source_sha256": digest,
        "invalid_examples": examples,
    }
    with engine.begin() as conn:
        source_id = conn.execute(
            text("""
                INSERT INTO audit.data_sources
                  (source_key,publisher,title,licence_terms,methodology,geographic_scope,source_class,metadata)
                VALUES(:key,'Unverified local file attribution',:title,
                  'Unverified; review before redistribution',
                  'Repository snapshot failed critical validation; no observations promoted.',
                  'unknown','unknown',CAST(:metadata AS jsonb))
                ON CONFLICT(source_key) DO UPDATE SET metadata=EXCLUDED.metadata,
                  methodology=EXCLUDED.methodology
                RETURNING source_id
            """),
            {"key": f"local_{key}", "title": filename, "metadata": json.dumps(report)},
        ).scalar_one()
        run_id = conn.execute(
            text("""
                INSERT INTO audit.ingestion_runs
                  (source_id,finished_at,status,source_version,checksum,rows_read,rows_written,report,error_summary)
                VALUES(:source,now(),'failed',:version,:checksum,:rows,0,CAST(:report AS jsonb),:error)
                RETURNING run_id
            """),
            {
                "source": source_id,
                "version": filename,
                "checksum": digest,
                "rows": len(frame),
                "report": json.dumps(report, default=str),
                "error": failure[:4000],
            },
        ).scalar_one()
        conn.execute(
            text("""
                INSERT INTO audit.ingestion_errors(run_id,source_record_key,error_type,message,record)
                VALUES(:run,:record_key,'critical_validation',:message,CAST(:record AS jsonb))
            """),
            {
                "run": run_id,
                "record_key": f"{filename}:invalid-row",
                "message": failure[:4000],
                "record": json.dumps(examples[0] if examples else {}, default=str),
            },
        )
        conn.execute(
            text("""
                INSERT INTO audit.data_quality_checks(run_id,check_name,severity,passed,observed_value,details)
                VALUES(:run,'critical_source_validation','critical',false,CAST(:observed AS jsonb),:details)
            """),
            {
                "run": run_id,
                "observed": json.dumps(
                    {"source_rows": len(frame), "invalid_examples": examples},
                    default=str,
                ),
                "details": failure[:4000],
            },
        )
        conn.execute(
            text("""
                INSERT INTO audit.source_documents(source_id,title,retrieved_at,checksum,geography,metadata)
                VALUES(:source,:title,now(),:checksum,'unknown',CAST(:metadata AS jsonb))
                ON CONFLICT DO NOTHING
            """),
            {
                "source": source_id,
                "title": filename,
                "checksum": digest,
                "metadata": json.dumps(
                    {"coverage_start": "2016-01-01", "coverage_end": "2018-09-25"}
                ),
            },
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m techpulse.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("db-migrate")
    sub.add_parser("db-health")
    sub.add_parser("validate-data")
    ing = sub.add_parser("ingest")
    ing.add_argument(
        "--source", choices=["all", "stackexchange", "survey", "fortune"], default="all"
    )
    ing.add_argument("--from-year", type=int, default=2016)
    args = parser.parse_args(argv)
    if args.command == "db-migrate":
        db_migrate()
    elif args.command == "db-health":
        db_health()
    elif args.command == "validate-data":
        report = validate_data()
        if report["critical_issues"]:
            raise SystemExit(
                f"Critical data-quality issues were found; see {report['report_path']}."
            )
    elif args.command == "ingest":
        ingest(args.source, args.from_year)


if __name__ == "__main__":
    main()
