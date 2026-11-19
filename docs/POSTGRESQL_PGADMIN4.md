# PostgreSQL, pgAdmin 4, and the dashboard

TechPulse uses the canonical PostgreSQL schemas `raw`, `staging`, `core`, `analytics`, `ml`, and `audit`. The dashboard reads only these schemas. It does not use the legacy CSV warehouse contract and does not fall back to local CSV when PostgreSQL is unavailable.

## Existing local database

The project is configured for `localhost:5432`, database `TechPulse-Database`. Register the server in pgAdmin using your local administrator account, then select that database. Do not use the administrator account in Streamlit.

From the repository root, apply or verify the schema:

```powershell
python -m techpulse.cli db-migrate
python -m techpulse.cli db-health
```

The migration is additive and checksum-protected. Do not edit an applied migration; add a new numbered migration for schema changes.

## Dashboard role and connection

The dashboard role is `techpulse_app`. It has login access and read-only `SELECT` access to the canonical schemas. It is not a superuser, database owner, or ingestion role. The dashboard query layer also starts every query transaction in read-only mode.

Copy `.env.example` to `.env` and configure:

```dotenv
DATABASE_URL=postgresql+psycopg2://techpulse_app@localhost:5432/TechPulse-Database
TECHPULSE_DB_POOL_SIZE=5
TECHPULSE_DB_MAX_OVERFLOW=10
TECHPULSE_DB_POOL_TIMEOUT_SECONDS=10
TECHPULSE_QUERY_TIMEOUT_SECONDS=30
TECHPULSE_CACHE_TTL_SECONDS=300
```

Supply the role password via the ignored local `.env` variable `PGPASSWORD` or a PostgreSQL passfile. Keep `.env`, passfiles, and backups out of source control. `.env.example` contains no password. SQLAlchemy/psycopg2 handles the hyphen in the database name as part of the database path; do not add SQL identifier quotes to the URL.

For a new database, create the role as a DBA and grant only what the dashboard needs:

```sql
CREATE ROLE techpulse_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
GRANT CONNECT ON DATABASE "TechPulse-Database" TO techpulse_app;
GRANT USAGE ON SCHEMA raw, staging, core, analytics, ml, audit TO techpulse_app;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, staging, core, analytics, ml, audit TO techpulse_app;
```

Set its password interactively in pgAdmin or with `\password techpulse_app` in `psql`; do not put a real password into a SQL file. A separate migration owner and ingestion writer should own schema changes and ingestion writes.

## Start Streamlit

```powershell
python -m streamlit run dashboard/app.py
```

The sidebar reports database connectivity, database name, PostgreSQL version, migration count, last ingestion, latest observation, and last successful model run. When the connection or schema check fails, each page shows a useful database error and does not substitute CSV data.

## pgAdmin validation queries

Use the read-only examples under `queries/canonical/`. For a quick check:

```sql
SELECT version(), current_database();
SELECT version, applied_at, checksum FROM audit.schema_migrations ORDER BY applied_at;
SELECT source_key, geographic_scope, source_class FROM audit.data_sources ORDER BY source_key;
SELECT code, name FROM core.geographies ORDER BY code;
SELECT count(*) FROM analytics.developer_survey_observations;
SELECT count(*) FROM analytics.community_monthly_metrics;
```

## Troubleshooting

- **PostgreSQL unavailable:** verify the service is running and `localhost:5432` accepts connections.
- **Password authentication failed:** check the local `.env` `PGPASSWORD` or passfile and confirm it belongs to `techpulse_app`.
- **Permission denied:** grant database `CONNECT`, canonical schema `USAGE`, and table `SELECT` to `techpulse_app`; do not elevate it to a superuser.
- **Unexpected database name:** confirm the URL ends with `/TechPulse-Database`.
- **Canonical relation missing:** run `python -m techpulse.cli db-migrate` as the migration owner, then restart Streamlit.
- **Community Health shows blocked:** inspect the failed run in `audit.ingestion_runs`, the row in `audit.ingestion_errors`, and the critical check in `audit.data_quality_checks`. The current source has `question_count=0` and `unanswered_count=181334` for `ios` on 2018-02-21. Correct it against its originating source and preserve the original checksum before re-ingestion; do not silently delete or clamp the record.
- **Empty Kenya, live, or prediction pages:** empty means no qualifying canonical records were found. It is not a zero-valued observation. Global survey rows and company profiles are not Kenyan technology evidence.

## Backup and restore

Use pgAdmin's Backup and Restore dialogs, or `pg_dump --format=custom` and `pg_restore` against a protected backup location. Restore to a separate database first and verify `audit.schema_migrations` and `python -m techpulse.cli db-health`. Do not use database drops or schema resets against this database as an application reset procedure.
