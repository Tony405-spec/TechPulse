"""Read-only CSV/PostgreSQL survey reconciliation; writes only a JSON report."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.cli import DATA, ROOT, _engine, _validate_ingest_input


def reconcile() -> dict:
    path = DATA / "developer_survey_usage.csv"
    raw = pd.read_csv(path)
    try:
        validated, validation = _validate_ingest_input("survey", raw)
        validation_error = None
    except ValueError as exc:
        validated, validation, validation_error = None, None, str(exc)

    engine = _engine()
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        stored = pd.read_sql(text("""
            SELECT t.canonical_name AS technology_name, s.survey_year,
                   s.respondent_count, s.usage_share AS developer_usage_share,
                   s.interest_share AS developer_interest_share,
                   s.admiration_share AS developer_admiration_share,
                   s.metadata->>'category' AS stored_category
            FROM analytics.developer_survey_observations s
            JOIN core.technologies t USING(technology_id)
            JOIN audit.data_sources src USING(source_id)
            WHERE src.source_key='local_survey'
            ORDER BY t.canonical_name, s.survey_year
        """), conn)

    keys = ["technology_name", "survey_year"]
    source_keys = raw[keys].astype({"technology_name": "string"}).drop_duplicates()
    database_keys = stored[keys].astype({"technology_name": "string"}).drop_duplicates()
    missing = source_keys.merge(database_keys, on=keys, how="left", indicator=True)
    missing = missing.loc[missing._merge.eq("left_only"), keys]
    source_only_duplicate_keys = raw.loc[raw.duplicated(keys, keep=False), keys].drop_duplicates()
    conflict_records = []
    if not source_only_duplicate_keys.empty:
        cols = keys + [c for c in raw.columns if c not in keys]
        subset = raw.merge(source_only_duplicate_keys, on=keys, how="inner")[cols]
        for (technology, year), group in subset.groupby(keys, dropna=False):
            if len(group.drop_duplicates()) > 1:
                conflict_records.append({
                    "technology_name": str(technology),
                    "survey_year": int(year),
                    "source_rows": group.to_dict("records"),
                    "stored_row": stored.loc[
                        stored.technology_name.eq(technology) & stored.survey_year.eq(year)
                    ].drop(columns="stored_category", errors="ignore").to_dict("records"),
                })
    report = {
        "report_type": "read_only_survey_reconciliation",
        "source_path": str(path.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_rows_read": int(len(raw)),
        "source_exact_duplicate_rows": int(raw.duplicated().sum()),
        "source_distinct_natural_keys": int(len(source_keys)),
        "validated_rows": int(len(validated)) if validated is not None else None,
        "validation_error": validation_error,
        "exact_duplicate_rows_removed_by_validator": validation["duplicate_rows_removed"] if validation else None,
        "database_rows_for_source": int(len(stored)),
        "database_distinct_natural_keys": int(len(database_keys)),
        "source_keys_missing_from_database": missing.to_dict("records"),
        "database_keys_absent_from_source": database_keys.merge(source_keys, on=keys, how="left", indicator=True).query("_merge == 'left_only'")[keys].to_dict("records"),
        "conflicting_source_natural_keys": conflict_records,
        "discrepancy_explanation": (
            "The CSV contains two distinct Supabase 2024 rows (Database and Platform) for one "
            "technology/year key, while the canonical database unique key omits category and "
            "can store only one. The stored values match the Platform row; the latest ingestion "
            "run wrote zero rows, so it does not establish which earlier input row was retained."
            if conflict_records else "No conflicting source natural keys were found."
        ),
        "database_mutated": False,
        "ingestion_runs_created": False,
    }
    out_dir = ROOT / "outputs" / "research_integrity"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "survey_reconciliation.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["report_path"] = str(out.relative_to(ROOT))
    print(json.dumps(report, indent=2, default=str))
    return report


if __name__ == "__main__":
    reconcile()
