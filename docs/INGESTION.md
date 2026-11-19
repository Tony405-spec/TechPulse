# Ingestion and reproducible runs

## Commands

From the repository root:

```bash
python -m techpulse.cli db-migrate
python -m techpulse.cli db-health
python -m techpulse.cli validate-data
python -m techpulse.cli ingest --source survey --from-year 2021
```

The database commands require DATABASE_URL and fail on a missing or unavailable configured database. They never silently switch to CSV. validate-data is local and read-only; it writes a timestamped profile beneath outputs/runs and does not replace old reports. It exits nonzero when a critical source check fails. The current Stack Exchange CSV fails on its ios 2018-02-21 row (0 questions, 181334 unanswered); ingestion refuses that source until the data is corrected or its provenance independently explains it.

## Current adapters

The first local adapter version accepts stackexchange.csv, developer_survey_usage.csv, and fortune.csv. It stores source rows and checksums in raw.source_records, documents source files, creates an ingestion_runs record, and upserts only relevant curated facts. Use the survey or fortune source independently while the critical Stack Exchange row is unresolved; ingest --source all fails atomically:

- Stack Exchange monthly tag aggregates to core.technologies and analytics.community_monthly_metrics.
- Survey-year usage/interest/admiration aggregates to analytics.developer_survey_observations.
- Company descriptors to core.company_profiles.

These inputs have incomplete licensing/extraction provenance. The source registry labels those limits. The survey aggregate is reported and global/unspecified. The community file has no verified geography. Company profiles never populate company technology evidence. Proxy adoption and mapping tables are not ingested.

## Quality and retention

Each payload is JSONB with a deterministic row key and SHA-256 content checksum; duplicate reruns are idempotent. Ingestion errors and quality checks have dedicated audit tables. A complete source-specific critical validation gate (including terms review, normalized aliases, and curated foreign-key coverage) is still required before treating these rows as research-grade. The current CLI is an initial reproducible local-file adapter, not a claim that every source has passed independent validation.

--from-year filters the source observation year without filling missing dates or creating zero rows. The current Stack Exchange input ends in 2018, so it contributes no records for a 2021 start. Survey rows cover 2021–2024; they remain global survey evidence and cannot be used as Kenya observations. Annual survey rows have a `survey_year`; `observed_at` remains NULL because the supplied aggregate does not provide a verified observation day.

## Snapshot and model workflow

Every future feature snapshot should include a source checksum, as-of date, feature-definition version and source lineage. Future-window values are labels only. Live API observations are stored separately; adding them to training needs a documented as-of-time, leakage, coverage, comparability, and validation review. Historical feature/label/model reports in the checkout are not overwritten; new model outputs are stored beneath a run-specific outputs/runs directory and candidate artifacts beneath models/runs.

The legacy pipeline/run_pipeline.py still uses its six-table adapter and should be considered historical until it is fully migrated to the canonical adapter and the canonical PostgreSQL feature-store workflow.
