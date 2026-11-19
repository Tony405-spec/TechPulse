# Data lineage and quality

**Checked:** 2026-11-16. The machine-readable historic audit is [final_audit_report.json](final_audit_report.json). Updated deadline findings and reproducible commands are in [THREE_DAY_PRESENTATION_RESCUE.md](THREE_DAY_PRESENTATION_RESCUE.md); the CLI writes timestamped data-quality records under `outputs/runs/`.

## Evidence classes

| Evidence class | Meaning in TechPulse | Current interpretation |
|---|---|---|
| Observed community activity | Daily snapshots of cumulative Stack Overflow tag totals and relative shares from the DataCamp course resource. | Source-level global observations only; 2016–2018, not Kenya-specific. Two invalid zero-total rows block curated ingestion. Monthly snapshots must use the last valid observed record, not sum daily stock values. |
| Derived technology indicators | Growth, rolling-window, engagement, persistence, and answer-rate features calculated from observed series. | These are transformations, not separate observations. They require a valid time series and an explicit as-of date. No canonical feature snapshot is presently loaded. |
| Reported survey statistics | Usage, interest, and admiration shares/counts from the local survey aggregation. | Global/unspecified, self-selected survey statistics. The file's 2021–2024 span is known; per-year URLs, aggregation code, and detailed licence provenance are absent. Not Kenyan measures. |
| Company profile evidence | Company identity, industry, and financial/profile fields from Fortune CSV. | Profiles alone do not establish which technologies a company uses. Do not call these enterprise adoption data. |
| Verified company technology evidence | A dated source explicitly documenting a company's use of a named technology. | No such verified evidence is currently loaded. Development mappings/proxies are not verified adoption. |
| Inferred/proxy relationships | A mapping or association derived from co-occurrence, heuristics, packages, or a demo mapping. | Must be labelled inferred/proxy and excluded from verified adoption claims and predictors unless separately justified. |
| Missing information | A source, geography, observation window, or metric is unavailable. | Keep NULL/empty and report unavailable. Never recode missing as zero or as Stable. |
| Live API observations | Timestamped snapshots from public GitHub, Stack Exchange, npm, or PyPI endpoints. | Supplementary, sample-biased evidence. Stars/downloads do not mean unique developers or production adoption. Keep outside historical training until temporal comparability is demonstrated. |

## Dataset register and quality summary

| File / database source | Coverage and size | Quality findings | Appropriate use |
|---|---|---|---|
| `data/stackexchange.csv` | 45,238 rows, 53 tags, dates 2016-01-01–2018-09-25; 0% missing cells; 0 exact duplicate rows. | The source contains two zero-total rows on 2018-02-21: `ios` has 0 questions / 181,334 unanswered; `amazon-mws` has 0 / 0. The daily rows are cumulative snapshots, not daily arrivals. Validation fails and canonical ingestion is blocked. | Historical global tag-stock/share analysis only; preserve invalid source rows and quarantine them in derived analysis. Not current, enterprise or Kenya evidence. |
| `data/stackexchange (1).csv` | 45,238 rows and same keys/counts as primary; exact SHA-256 match to DataCamp's downloadable course resource. | Alternate ISO-date serialization. The two zero-total rows are present in the upstream resource itself. Share columns differ from the primary only by float serialization (max absolute difference 0.0000005). Do not merge or overwrite. | Verified source copy; retain for lineage and comparison. |
| `data/developer_survey_usage.csv` | 685 rows; 267 identifiers; 2021–2024; no nulls or exact duplicates. | Declares Stack Overflow Developer Survey source but lacks source URLs per year, raw respondent file references, aggregation procedure, and complete licence notes. PostgreSQL has 684 rows; one-row difference is unresolved. Geography is global/unspecified. | Descriptive global survey comparison and interest/usage context. Do not join backward to 2016–2018 features or call it Kenya data. |
| `data/fortune.csv` / `data/fortune (1).csv` | 500 company profiles per file. `fortune.csv` missingness: ticker 6.4%, industry 2.6%, revenue 1.0%, profits 0.2%, profit change 12.6%. | Publisher/source extraction and use rights are not confirmed in the file. Canonical DB has 497 rows. Profiles are not stack evidence. | Company-profile context only, after provenance review. Not technology adoption. |
| `data/ev311.csv` / alternate | 36,431 records per file; operational service requests; description missing 30.1%, ZIP 15.2%, house number 11.6%, street 4.7%. | Unrelated to developer technology trajectories; includes location/address fields and should not enter this research pipeline. | Excluded. Avoid exposing or repurposing personal/location details. |
| `data/files.csv` | Empty, zero records. | No schema/data available. | None. |
| PostgreSQL canonical tables | 267 technologies; 684 global/unspecified survey rows; 497 company profiles; 0 curated community rows; 0 Kenya rows; 0 live rows. | `local_stackexchange` ingestion failed due to the critical impossible row. One source row-count discrepancy remains between survey CSV and database. | Dashboard's canonical source of truth; empty results stay visibly unavailable. |
| `outputs/runs/*/model_run.json` | 46 run manifests inspected. | All 46 classify as synthetic fixtures, either explicitly or via `outputs/test_fixture_runs.json`. No auditable research run, dataset snapshot, canonical saved prediction, or canonical model metric exists. | Software tests only; exclude from claims and presentation scores. |

## Lineage path

The intended path is `raw` immutable payload and source checksum → `staging` validated source rows → curated `core` entities and `analytics` observations → time-stamped ML feature snapshots and independently defined future labels → versioned `ml.model_runs`, evaluation metrics, predictions and explanations. `audit.data_sources`, `audit.ingestion_runs`, quality checks and schema migrations record provenance. The canonical dashboard queries the canonical PostgreSQL schemas and does not fall back to CSV.

For current status, see `python -m techpulse.cli db-health` and the run report from `python -m techpulse.cli validate-data`. The quality command's nonzero exit is an intentional block; it should only change after the source discrepancy is checked against its origin and the correction is documented. Preserve the original file/checksum and add a new derived/corrected version instead of silently editing raw input.

## Model data constraints

- Predictors must be available on or before `as_of_date`; future-window outcome fields, labels, post-outcome API snapshots, and IDs are excluded.
- Community history should be split chronologically. Walk-forward/expanding folds must keep every training timestamp earlier than its validation timestamps.
- Survey indicators are eligible only when their year is no later than the cutoff and their geography/definition is compatible; current aggregates cannot be joined backward to old community observations.
- Company profiles, deterministic mappings, and proxy adoption fields are not verified adoption signals and are prohibited from silently entering predictors.
- Incomplete future outcome windows are unlabeled, not Stable. Zero observed records and unavailable data are not interchangeable.
- Report per-class support/precision/recall/F1, confusion matrix, macro/weighted F1, class baseline, momentum baseline, dates, label parameters, input checksum, and split membership. A high score on a tiny or synthetic set is not evidence of generalization.

## Kenya coverage

The canonical Kenya observation query returned zero rows. There are no verified local developer-activity, technology-interest, company-use, skills, job-demand, or adoption observations in the current database. The dashboard's global survey rows and US-oriented company profiles are not Kenyan evidence. Additional work would require dated, source-linked Kenya observations with documented scope/licence and a defensible sampling method. Until then, show the evidence gap and use any global data only as a clearly separate reference.
