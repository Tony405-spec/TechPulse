# TechPulse incremental live-data implementation plan

Updated: 1 November 2026

This plan records the repository audit, incremental implementation and evidence for live public-source observations. Live observations are intentionally not added to the historical model dataset.

## Milestone 1 — Repository audit

**Status: complete.** Existing application, six-table ingestion contract, source CSV fallback, feature/label/model workflow, dashboard routes, test suite and local artefact provenance were inspected.

Integration findings:

- `src/data_ingestion.py` owns the six existing PostgreSQL tables and the no-database CSV fallback. A configured unavailable database is surfaced rather than silently switching to CSV.
- `pipeline/run_pipeline.py` consumes those six dataframes to regenerate historical features, labels, models and evaluation outputs. Public API observations must not be merged into that training flow without a separate temporal study.
- The dashboard uses `dashboard/app.py` for navigation and `dashboard/data.py` for cached reads. Existing pages are retained.
- The checked-out historical community source is `data/stackexchange.csv`; its tags provide the current catalogue context. The existing local company profile file is not evidence of company technology adoption.
- The working tree already contained user changes from the preceding redesign. They were preserved; `.env` contents were not printed or copied, and the file was not modified.
- Baseline before implementation: `python -m pytest tests/ -q` — **26 passed, 2 warnings** in 57.83 seconds. Both were existing scikit-learn feature-name warnings in `test_random_state_reproducibility`.

## Milestone 2 — GitHub

**Status: complete.** `src/live_data/collectors.py` queries GitHub repository search with optional `GITHUB_TOKEN`, bounded pagination and GitHub rate-limit retry handling. It records query match counts, sampled repository stars/forks/languages, repository age and days since last push. A real MongoDB collection returned and persisted 984 normalized rows. Sampled repository metrics are not described as product usage or enterprise adoption.

## Milestone 3 — Stack Exchange

**Status: complete.** The collector reads a tag's all-time question count and paginates a capped sample of questions created in the last 30 days. It stores answered/unanswered sample counts and per-question activity with question ID, event date and collection date. It supports optional `STACKEXCHANGE_KEY`, site configuration and API backoff. A real MongoDB-tag collection returned and persisted 10 rows.

## Milestone 4 — PyPI and npm

**Status: complete.** Registries are queried only for explicit package mappings in `data/live_package_map.json`. PyPI release history comes from release file upload timestamps; PyPI's documented deprecated downloads field is ignored. npm release dates and last-month download totals are collected from npm's public endpoints. Real MongoDB mappings returned and persisted 178 PyPI rows and 968 npm rows. Package aliases should be reviewed for research relevance before adding.

## Milestone 5 — Dashboard and storage

**Status: complete.** The existing navigation gains **Live Technology Intelligence**. Page reads use the ingestion module and cache database/CSV reads briefly; they do not call external APIs. Manual collection starts `scripts/collect_live_data.py` in a separate process. Status and collection errors are source-specific, previous rows are retained, and charts label date ranges and irregular collection frequency. The daily `scripts/schedule_live_data.py` process works without Streamlit and can be supervised by Windows Task Scheduler or another service manager. Edge captures demonstrate the page with actual stored MongoDB observations; the screenshot index and contact sheet are under `outputs/live_data_screenshots/`.

Persistence extension: additive PostgreSQL table `techpulse_live_observations`, created on first write, or CSV fallback at `outputs/live_data/live_observations.csv`. The composite natural key prevents duplicate observations while retaining later snapshots. `src/data_ingestion.py` exposes append/read functions for the existing ingestion boundary. The original six-table contract is unchanged and live observations do not become training features.

## Milestone 6 — Tests, docs and visual evidence

**Status: complete.** Mocked tests cover each collector, rate limits/backoff, missing API fields, pagination, explicit package mappings, timestamp preservation, CSV deduplication and SQLAlchemy persistence via SQLite. All nine dashboard routes are part of the `AppTest` smoke test. Final suite: **41 passed, 2 existing scikit-learn warnings**. Real HTTP collections completed for GitHub, Stack Exchange, PyPI and npm on MongoDB and persisted 2,140 normalized rows. Final test evidence is in `outputs/live_data_test_report.md`; screenshots and a contact sheet are in `outputs/live_data_screenshots/`.

## Runtime configuration and operations

Copy `.env.example` to `.env`, then optionally set GitHub and Stack Exchange credentials. Never commit `.env`. Defaults use 15-second request timeouts, three retries, two pages of at most 100 results per paginated endpoint, five technologies per daily batch and a 24-hour interval. These limits are configurable via the documented `TECHPULSE_*` variables. A scheduler batch uses top technologies by existing local community volume, unless `TECHPULSE_LIVE_TECHNOLOGIES` is provided.

Commands from repository root:

```bash
python scripts/collect_live_data.py --technology mongodb
python scripts/schedule_live_data.py --once
python scripts/schedule_live_data.py
```

## Research and API limitations

- GitHub search is a bounded name/description match over public repositories; the sample does not represent all repositories or actual usage.
- Stack Exchange activity is a site-specific question signal. Recent samples stop at the configured page cap; incomplete samples are identified in metadata.
- PyPI official JSON exposes release metadata, but its `downloads` key is deprecated and always `-1`; no PyPI download estimate is presented.
- npm last-month downloads are package downloads, not unique users, production installs or enterprise adoption.
- Current stars, tag counts, npm downloads and release metadata observed at collection time must not be back-projected into earlier prediction periods. Release upload dates are source-provided event dates, not collection dates.
- APIs can change, rate-limit, return incomplete search results or become unreachable. Failed source attempts retain prior persisted observations and are visible in status.
- The automated database persistence test uses a temporary SQLite SQLAlchemy database to exercise insert/read/deduplicate behavior; a dedicated PostgreSQL integration-test database was not used. The live collection itself used the runtime-configured PostgreSQL/CSV storage path.
- No new metric is used in feature engineering, labels, prediction, training, SHAP, or evaluation. A future change requires a documented as-of-time and leakage review, measurement-comparability review, sufficient historic coverage and new validated experiments.

## Official API documentation

- [GitHub REST repository search and API rate limits](https://docs.github.com/en/rest/search/search#search-repositories), [rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Stack Exchange API](https://api.stackexchange.com/docs), [paging and backoff](https://api.stackexchange.com/docs/paging)
- [PyPI JSON API](https://docs.pypi.org/api/json/)
- [npm public registry API](https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md), [package metadata](https://github.com/npm/registry/blob/main/docs/responses/package-metadata.md)

## Implementation file inventory

**Added:** `src/live_data/__init__.py`, `src/live_data/collectors.py`, `src/live_data/storage.py`, `src/live_data/service.py`, `scripts/collect_live_data.py`, `scripts/schedule_live_data.py`, `data/live_package_map.json`, `dashboard/views/8_Live_Technology_Intelligence.py`, `tests/test_live_data.py`, `docs/LIVE_DATA_IMPLEMENTATION_PLAN.md`, `outputs/live_data_test_report.md`, and browser captures/index under `outputs/live_data_screenshots/`.

**Extended:** `src/data_ingestion.py` with live observation store entry points; `dashboard/app.py`, `dashboard/data.py`, and `dashboard/views/7_Methodology_Data.py`; `.env.example`, `.gitignore`, `requirements.txt`, `README.md`; `scripts/capture_redesign_screenshots.py`; and the existing user manual, technical reference, and five-minute demonstration guide (including their generated PDFs).

Existing six-table datasets, CSV fallback, model/label pipeline, historical outputs, other dashboard pages and design components remain in place. Live rows are intentionally not returned as model training data.
