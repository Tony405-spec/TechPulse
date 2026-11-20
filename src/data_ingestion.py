"""Database ingestion and quality validation for TechPulse."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd

from src.common import DATA_DIR, OUTPUTS_DIR, ensure_directories

LOGGER = logging.getLogger(__name__)
TABLES = [
    "so_questions",
    "dev_sentiment",
    "fortune500_stacks",
    "company_profiles",
    "tech_metadata",
    "question_company_mapping",
]
KEY_COLUMNS = {
    "so_questions": ["technology", "tag", "creation_date", "date"],
    "dev_sentiment": ["technology", "survey_year", "satisfaction_score"],
    "fortune500_stacks": ["technology", "company_id", "adoption_date"],
    "company_profiles": ["company_id", "sector", "company_name"],
    "tech_metadata": ["technology", "technology_name", "category"],
    "question_company_mapping": ["question_id", "company_id", "technology"],
}

REQUIRED_COLUMNS = {
    "so_questions": ["technology", "creation_date"],
    "dev_sentiment": ["technology", "survey_year"],
    "fortune500_stacks": ["technology", "company_id", "adoption_date"],
    "company_profiles": ["company_id", "company_name"],
    "tech_metadata": ["technology", "category"],
    "question_company_mapping": ["question_id", "company_id", "technology"],
}


def _validate_frame(table: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Validate one ingested table and return a quality summary.

    Args:
        table: Source table name.
        frame: Loaded pandas DataFrame.

    Returns:
        A JSON-serialisable quality summary.
    """
    row_count = int(len(frame))
    LOGGER.info("%s row count: %s", table, row_count)
    issues: list[dict[str, Any]] = []
    missing_required = sorted(set(REQUIRED_COLUMNS.get(table, [])) - set(frame.columns))
    if missing_required:
        issues.append({"type": "missing_required_columns", "columns": missing_required})
    if row_count < 50:
        message = f"{table} contains fewer than 50 rows ({row_count})."
        LOGGER.warning(message)
        issues.append({"type": "minimum_rows", "message": message})

    missingness = {
        str(column): (
            round(float(frame[column].isna().mean() * 100), 2) if row_count else None
        )
        for column in frame.columns
    }
    date_ranges: dict[str, dict[str, str | None]] = {}
    for candidate in ["creation_date", "date", "adoption_date", "survey_year"]:
        if candidate in frame.columns:
            if candidate == "survey_year":
                years = pd.to_numeric(frame[candidate], errors="coerce").dropna()
                years = years.loc[years.between(1900, 2200)]
                if not years.empty:
                    date_ranges[candidate] = {
                        "earliest_year": str(int(years.min())),
                        "latest_year": str(int(years.max())),
                    }
                continue
            values = pd.to_datetime(frame[candidate], errors="coerce")
            if values.notna().any():
                date_ranges[candidate] = {
                    "earliest": values.min().date().isoformat(),
                    "latest": values.max().date().isoformat(),
                }
    technology_columns = [
        column
        for column in ["technology", "technology_name", "tag"]
        if column in frame.columns
    ]
    technology_count = (
        int(frame[technology_columns[0]].nunique()) if technology_columns else None
    )

    for column in KEY_COLUMNS.get(table, []):
        if column not in frame.columns:
            continue
        null_pct = float(frame[column].isna().mean() * 100)
        if null_pct > 5:
            LOGGER.warning("%s.%s has %.2f%% nulls.", table, column, null_pct)
            issues.append(
                {"type": "null_threshold", "column": column, "null_pct": null_pct}
            )

    if table == "dev_sentiment" and "satisfaction_score" not in frame.columns:
        issues.append(
            {
                "type": "semantic_gap",
                "message": "No satisfaction_score is present; usage, interest and admiration are not developer satisfaction sentiment.",
            }
        )

    quality_passed = (
        row_count >= 50
        and not missing_required
        and not any(issue.get("type") == "null_threshold" for issue in issues)
        and not any(issue.get("type") == "semantic_gap" for issue in issues)
    )

    return {
        "row_count": row_count,
        "column_count": int(len(frame.columns)),
        "technology_count": technology_count,
        "missingness_pct": missingness,
        "date_ranges": date_ranges,
        "issues": issues,
        "passed": quality_passed,
    }


def load_and_validate_datasets() -> dict[str, pd.DataFrame]:
    """Load all six PostgreSQL datasets and write a data quality report.

    Returns:
        A dictionary mapping required table names to pandas DataFrames.

    Raises:
        EnvironmentError: If DATABASE_URL is not configured.
        ConnectionError: If the PostgreSQL connection cannot be opened.
        RuntimeError: If a required table cannot be loaded.
    """
    ensure_directories()
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise ImportError(
            "Install project dependencies with `pip install -r requirements.txt`."
        ) from exc

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        if os.environ.get(
            "TECHPULSE_ALLOW_LOCAL_DEVELOPMENT_DATA", ""
        ).strip().lower() in {"1", "true", "yes"}:
            return load_local_development_datasets()
        raise EnvironmentError(
            "DATABASE_URL is required for the research pipeline. The CSV development adapter creates proxy tables and is disabled by default; set TECHPULSE_ALLOW_LOCAL_DEVELOPMENT_DATA=true only for non-research exploration."
        )

    try:
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError as exc:
        raise ImportError(
            "PostgreSQL ingestion requires sqlalchemy and psycopg2-binary."
        ) from exc

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                inspector = inspect(connection)
                available_tables = set(inspector.get_table_names())
                if set(TABLES).issubset(available_tables):
                    datasets = {
                        table: pd.read_sql(text(f"SELECT * FROM {table}"), connection)
                        for table in TABLES
                    }
                    source_mode = "postgresql_legacy_read_only"
                    table_lineage = {
                        table: {"relation": f"public.{table}", "is_proxy": False}
                        for table in TABLES
                    }
                else:
                    schemas = set(connection.execute(text("""
                        SELECT schema_name FROM information_schema.schemata
                        WHERE schema_name IN ('core','analytics','audit')
                    """)).scalars().all())
                    if not {"core", "analytics", "audit"}.issubset(schemas):
                        raise RuntimeError(
                            "PostgreSQL is reachable, but neither the six legacy source tables nor the canonical TechPulse schemas are available."
                        )
                    datasets = _load_canonical_dataset_compatibility(connection, text)
                    source_mode = "postgresql_canonical_compatibility"
                    table_lineage = {
                        "so_questions": {
                            "relation": "core.community_questions; analytics.community_monthly_metrics",
                            "is_proxy": False,
                        },
                        "dev_sentiment": {
                            "relation": "analytics.developer_survey_observations",
                            "is_proxy": False,
                            "semantic_note": "Usage/interest/admiration only; satisfaction is absent.",
                        },
                        "fortune500_stacks": {
                            "relation": "analytics.company_technology_evidence with source lineage",
                            "is_proxy": False,
                        },
                        "company_profiles": {
                            "relation": "core.company_profiles",
                            "is_proxy": False,
                        },
                        "tech_metadata": {
                            "relation": "core.technologies and category memberships",
                            "is_proxy": False,
                        },
                        "question_company_mapping": {
                            "relation": None,
                            "is_proxy": False,
                            "status": "not represented in canonical schema",
                        },
                    }
            report = {
                name: _validate_frame(name, frame) for name, frame in datasets.items()
            }
            if source_mode == "postgresql_canonical_compatibility":
                with connection.begin():
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                    critical_community_failures = int(connection.execute(text("""
                        SELECT count(*)
                        FROM audit.data_quality_checks q
                        JOIN audit.ingestion_runs r USING(run_id)
                        JOIN audit.data_sources s USING(source_id)
                        WHERE s.source_key='local_stackexchange'
                          AND q.severity='critical' AND NOT q.passed
                    """)).scalar_one())
            else:
                critical_community_failures = 0
            report["_pipeline_readiness"] = {
                "source_mode": source_mode,
                "all_datasets_passed": all(
                    value["passed"] for value in report.values()
                ),
                "critical_community_validation_failures": critical_community_failures,
                "note": "A structurally loaded dataset can still be inadequate for modeling; labels and temporal coverage require independent checks.",
            }
            report_path = OUTPUTS_DIR / "data_quality_report.json"
            report_path.write_text(
                json.dumps(report, indent=2, default=str), encoding="utf-8"
            )
            for name, frame in datasets.items():
                table_lineage[name]["rows"] = int(len(frame))
                table_lineage[name]["validation_passed"] = report[name]["passed"]
            _write_source_manifest(
                source_mode,
                "Read-only PostgreSQL source extraction through the legacy or documented canonical compatibility mapping.",
                table_lineage,
            )
    except RuntimeError:
        raise
    except SQLAlchemyError as exc:
        raise ConnectionError(
            "Failed to connect to PostgreSQL using DATABASE_URL."
        ) from exc

    return datasets


def _load_canonical_dataset_compatibility(
    connection: Any, text: Any
) -> dict[str, pd.DataFrame]:
    """Map canonical read-only relations to the six SRS dataset contracts.

    The adapter does not infer company adoption or developer satisfaction.
    Missing source concepts are returned as empty/absent evidence and recorded
    in the validation report rather than synthesized.
    """
    queries = {
        "so_questions": """
            SELECT q.source_question_id AS question_id, t.canonical_name AS technology,
                   t.canonical_name AS tag, q.created_at::timestamp AS creation_date,
                   1::bigint AS question_count, q.answer_count,
                   CASE WHEN q.answer_count=0 THEN 1 ELSE 0 END::bigint AS unanswered_count,
                   q.score, q.view_count, q.is_closed, q.observed_at, s.source_key
            FROM core.community_questions q
            JOIN core.technologies t USING(technology_id)
            LEFT JOIN audit.data_sources s USING(source_id)
            WHERE q.created_at IS NOT NULL
            UNION ALL
            SELECT NULL::text, t.canonical_name, t.canonical_name, m.period_start::timestamp,
                   m.question_count, NULL::integer, m.unanswered_count, m.median_score::integer,
                   NULL::bigint, NULL::boolean, m.observed_at, s.source_key
            FROM analytics.community_monthly_metrics m
            JOIN core.technologies t USING(technology_id)
            LEFT JOIN audit.data_sources s USING(source_id)
        """,
        "dev_sentiment": """
            SELECT t.canonical_name AS technology, s.survey_year,
                   s.respondent_count, s.worked_with_count, s.want_to_work_with_count,
                   s.admired_count, s.usage_share AS developer_usage_share,
                   s.interest_share AS developer_interest_share,
                   s.admiration_share AS developer_admiration_share,
                   s.source_class, src.source_key
            FROM analytics.developer_survey_observations s
            JOIN core.technologies t USING(technology_id)
            LEFT JOIN audit.data_sources src USING(source_id)
        """,
        "fortune500_stacks": """
            SELECT t.canonical_name AS technology, e.company_id,
                   e.observed_at AS adoption_date, e.evidence_type, e.claim,
                   e.source_class, e.confidence, src.source_key, d.url AS source_url
            FROM analytics.company_technology_evidence e
            JOIN core.technologies t USING(technology_id)
            JOIN analytics.company_technology_evidence_sources es USING(evidence_id)
            LEFT JOIN audit.data_sources src ON src.source_id=es.source_id
            LEFT JOIN audit.source_documents d ON d.document_id=es.document_id
            WHERE e.source_class IN ('observed','reported') AND e.observed_at IS NOT NULL
              AND (src.source_id IS NOT NULL OR d.document_id IS NOT NULL)
        """,
        "company_profiles": """
            SELECT company_id, company_name, country_code,
                   sector, observed_at, source_id
            FROM core.company_profiles
        """,
        "tech_metadata": """
            SELECT t.technology_id, t.canonical_name AS technology,
                   t.canonical_name AS technology_name,
                   string_agg(DISTINCT c.name, ', ' ORDER BY c.name) AS category,
                   t.description, t.first_observed_at
            FROM core.technologies t
            LEFT JOIN core.technology_category_memberships m USING(technology_id)
            LEFT JOIN core.technology_categories c USING(category_id)
            GROUP BY t.technology_id
        """,
        "question_company_mapping": """
            SELECT NULL::text AS question_id, NULL::bigint AS company_id,
                   NULL::text AS technology WHERE false
        """,
    }
    return {name: pd.read_sql(text(sql), connection) for name, sql in queries.items()}


def load_local_development_datasets() -> dict[str, pd.DataFrame]:
    """Load repository CSV data when PostgreSQL is not configured.

    The local repository contains the original descriptive analytics CSV inputs
    rather than the full six-table warehouse. Missing signal tables are derived
    deterministically and marked as development/demo data in the source manifest.

    Returns:
        Six DataFrames matching the expected ingestion contract.

    Raises:
        FileNotFoundError: If the required local CSVs are absent.
    """
    ensure_directories()
    stack_path = DATA_DIR / "stackexchange.csv"
    fortune_path = DATA_DIR / "fortune.csv"
    survey_usage_path = DATA_DIR / "developer_survey_usage.csv"
    missing = [str(path) for path in (stack_path, fortune_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "DATABASE_URL is not configured and required local CSV files are missing: "
            f"{missing}"
        )

    so_questions = pd.read_csv(stack_path)
    so_questions = so_questions.rename(
        columns={"tag": "technology", "date": "creation_date"}
    )
    so_questions["tag"] = so_questions["technology"]
    so_questions["creation_date"] = pd.to_datetime(
        so_questions["creation_date"], errors="coerce"
    )
    so_questions["answer_count"] = (
        pd.to_numeric(so_questions["question_count"], errors="coerce")
        - pd.to_numeric(so_questions["unanswered_count"], errors="coerce")
    ).clip(lower=0)
    so_questions["is_closed"] = False

    company_profiles = pd.read_csv(fortune_path).rename(
        columns={"rank": "company_id", "name": "company_name"}
    )
    techs = sorted(so_questions["technology"].dropna().astype(str).unique())
    sectors = company_profiles[["company_id", "sector"]].dropna().drop_duplicates()
    if sectors.empty:
        sectors = pd.DataFrame({"company_id": [1], "sector": ["Unknown"]})

    stack_rows: list[dict[str, object]] = []
    for index, technology in enumerate(techs):
        sector_sample = sectors.iloc[index % len(sectors) : index % len(sectors) + 5]
        if sector_sample.empty:
            sector_sample = sectors.head(5)
        for offset, row in sector_sample.reset_index(drop=True).iterrows():
            stack_rows.append(
                {
                    "technology": technology,
                    "company_id": int(row["company_id"]),
                    "adoption_date": pd.Timestamp("2017-01-01")
                    + pd.DateOffset(months=index + offset),
                    "source_type": "demo_derived_from_local_csv",
                }
            )
    fortune500_stacks = pd.DataFrame(stack_rows)

    using_real_survey = survey_usage_path.exists()
    if using_real_survey:
        survey_usage = pd.read_csv(survey_usage_path)
        dev_sentiment = survey_usage[
            [
                "technology_name",
                "survey_year",
                "developer_usage_share",
                "developer_interest_share",
                "developer_admiration_share",
                "source_type",
            ]
        ].rename(columns={"technology_name": "technology"})
        dev_sentiment["source_type"] = "official_stackoverflow_developer_survey"
    else:
        yearly = (
            so_questions.assign(year=so_questions["creation_date"].dt.year)
            .groupby(["technology", "year"], as_index=False)
            .agg(
                question_count=("question_count", "sum"),
                unanswered_count=("unanswered_count", "sum"),
            )
        )
        yearly["developer_usage_share"] = (
            1 - yearly["unanswered_count"] / yearly["question_count"].replace(0, pd.NA)
        ).clip(lower=0, upper=1)
        dev_sentiment = yearly.rename(columns={"year": "survey_year"})[
            ["technology", "survey_year", "developer_usage_share"]
        ]
        dev_sentiment["source_type"] = "demo_proxy_from_unanswered_rate"

    tech_metadata = pd.DataFrame(
        {
            "technology": techs,
            "technology_name": techs,
            "category": [infer_category(technology) for technology in techs],
            "source_type": "demo_inferred_category",
        }
    )
    question_company_mapping = fortune500_stacks.reset_index().rename(
        columns={"index": "question_id"}
    )[["question_id", "company_id", "technology", "source_type"]]
    datasets = {
        "so_questions": so_questions,
        "dev_sentiment": dev_sentiment,
        "fortune500_stacks": fortune500_stacks,
        "company_profiles": company_profiles,
        "tech_metadata": tech_metadata,
        "question_company_mapping": question_company_mapping,
    }
    report = {name: _validate_frame(name, frame) for name, frame in datasets.items()}
    (OUTPUTS_DIR / "data_quality_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    _write_source_manifest(
        "local_development_csv",
        "PostgreSQL DATABASE_URL was not set. Stack Exchange and Fortune CSVs were loaded; "
        "developer survey usage is loaded when `data/developer_survey_usage.csv` is present; "
        "adoption-stack, metadata, and mapping tables remain deterministic development proxies.",
        {
            "so_questions": {
                "source": str(stack_path),
                "is_proxy": False,
                "derived_from": None,
                "rows": int(len(so_questions)),
                "use_limit": "Real local CSV input for community activity; extraction provenance must be verified before research claims.",
            },
            "company_profiles": {
                "source": str(fortune_path),
                "is_proxy": False,
                "derived_from": None,
                "rows": int(len(company_profiles)),
                "use_limit": "Real local CSV input for company metadata; not evidence of technology adoption by itself.",
            },
            "fortune500_stacks": {
                "source": "generated_local_proxy",
                "is_proxy": True,
                "derived_from": ["so_questions", "company_profiles"],
                "rows": int(len(fortune500_stacks)),
                "use_limit": "Synthetic development proxy only; must not be cited as real enterprise adoption evidence.",
            },
            "dev_sentiment": {
                "source": (
                    str(survey_usage_path)
                    if using_real_survey
                    else "generated_local_proxy"
                ),
                "is_proxy": not using_real_survey,
                "derived_from": (
                    None if using_real_survey else ["so_questions.unanswered_rate"]
                ),
                "rows": int(len(dev_sentiment)),
                "use_limit": (
                    "Observed public Stack Overflow Developer Survey technology usage shares; not direct sentiment."
                    if using_real_survey
                    else "Proxy from unanswered rate only; not a real developer sentiment survey."
                ),
            },
            "tech_metadata": {
                "source": "generated_local_proxy",
                "is_proxy": True,
                "derived_from": ["technology_name_rules"],
                "rows": int(len(tech_metadata)),
                "use_limit": "Rule-inferred category metadata for dashboard grouping only.",
            },
            "question_company_mapping": {
                "source": "generated_local_proxy",
                "is_proxy": True,
                "derived_from": ["fortune500_stacks"],
                "rows": int(len(question_company_mapping)),
                "use_limit": "Synthetic mapping for development tests only.",
            },
        },
    )
    return datasets


def infer_category(technology: str) -> str:
    """Infer a broad dashboard category for local development data."""
    value = technology.lower()
    if any(token in value for token in ["sql", "mongo", "db", "redis", "dynamodb"]):
        return "Databases"
    if any(token in value for token in ["android", "ios", "django", "rails", "spring"]):
        return "Frameworks"
    if any(token in value for token in ["python", "java", "c#", "php", "actionscript"]):
        return "Languages"
    if any(
        token in value
        for token in ["aws", "amazon", "azure", "cloud", "paypal", "stripe"]
    ):
        return "Cloud/Platforms"
    return "Tools"


def _write_source_manifest(
    source_mode: str, note: str, tables: dict[str, Any] | None = None
) -> None:
    """Write data-source provenance for dashboards and reports."""
    manifest = {
        "source_mode": source_mode,
        "note": note,
        "required_tables": TABLES,
        "tables": tables or {},
        "research_grade": source_mode.startswith("postgresql"),
        "proxy_warning": (
            "Local development mode contains deterministic proxy tables and is not research-grade evidence."
            if source_mode == "local_development_csv"
            else None
        ),
    }
    (OUTPUTS_DIR / "data_sources.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def append_external_observations(records: list[dict[str, Any]]) -> int:
    """Validate and persist additive public-source observations through TechPulse ingestion.

    These rows are deliberately kept outside the six historical research tables
    and are not returned by ``load_and_validate_datasets`` for model training.
    """
    from src.live_data.storage import append_observations

    return append_observations(records)


def load_external_observations() -> pd.DataFrame:
    """Read additive API observations using the configured warehouse/CSV mode."""
    from src.live_data.storage import load_observations

    return load_observations()
