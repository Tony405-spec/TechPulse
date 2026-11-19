# TechPulse repository audit and data lineage

**Audit date:** 2026-11-08 · **Repository:** supplied `TechPulse-main` folder · **Commit:** unavailable (folder contains no `.git`).

## Findings

The project contains two incompatible historical contracts. `docs/schema_diagram.md`, `queries/`, and `tech_risk_query.sql` refer to the descriptive `company`, `fortune500`, `stackoverflow`, `tag_company`, and `tag_type` model. `src/data_ingestion.py` instead queries six unrelated tables: `so_questions`, `dev_sentiment`, `fortune500_stacks`, `company_profiles`, `tech_metadata`, and `question_company_mapping`. Neither should be treated as the canonical schema. The new additive schema is in `migrations/001_canonical_schema.sql`; legacy material is retained as historical context.

The survey aggregate is present: 685 rows, years 2021–2024, six categories, with respondent/count and usage/interest/admiration fields. The file's `source_type` names the official Stack Overflow survey, but the local copy contains no per-year URLs, license record, respondent-level source files, or aggregation script. The aggregate is global/unspecified, self-selected, and not direct sentiment. It is not a Kenyan signal.

The primary community CSV has 45,238 monthly tag observations from 2016-01-01 through 2018-09-25. It is stale for current-market claims, and the source extraction/provenance is not documented. One critical record is internally impossible: ios on 2018-02-21 has 0 questions and 181,334 unanswered. Canonical ingestion rejects the full source until this row is corrected or its provenance supports another interpretation. `stackexchange (1).csv` has the same row count but differs in content; it remains an un-ingested alternate. The two Fortune CSVs contain 500 matching records after row normalization; `(1)` is a duplicate. They describe company profiles, apparently an old Fortune 500 snapshot, and do not prove technology adoption. The two EV311 CSVs are byte-identical municipal service data unrelated to this study; `files.csv` is empty.

The local fallback's adoption stack and question-company mappings are deterministic synthetic proxies. Its technology categories are rule-inferred. Keep those out of evidence claims. Existing live GitHub, Stack Exchange, npm and PyPI observations are supplementary snapshots. A company or repository location is not a validated Kenya signal. Live data is not included in the historical predictors.

`outputs/model_comparison.md` and screenshots are previous-run evidence, not a reproducible evaluation for the supplied tree. The feature matrix, prediction CSV, and serialized model artifacts referred to by some reports are absent here. No metric from those previous artifacts is promoted as a current result. Existing target logic compares recent and future activity; future values are outcomes only. A missing target window cannot be called Stable.

The final verification suite writes synthetic test fixtures beneath outputs/runs and models/runs. These test-run artifacts are marked by outputs/test_fixture_runs.json and model_run.json, excluded from current dashboard model views, and are not research results.

No Kenya-specific market observations were found in `data/`. Communications Authority reports and Kenya's Digital Economy Blueprint are registered as research leads, not loaded data. No values have been invented or backfilled. No lawful public job dataset or local training outcome dataset was identified in the supplied files.

The CA portal describes quarterly provider-reported market statistics and notes that accuracy depends on provider compliance returns. It is a credible research lead for sector context, but its indicators do not measure developer technology use; publication-level reuse terms still need review before ingestion.

## Lineage files and authoritative current contract

- Machine-readable inventory: `outputs/data_lineage.json`.
- Human-readable source/methodology register: this report and `docs/SOURCE_REGISTER.md`.
- Canonical PostgreSQL contract: `migrations/001_canonical_schema.sql`, schemas `raw`, `staging`, `core`, `analytics`, `ml`, and `audit`.
- Legacy material remains in place and should be read as superseded when it describes old table contracts, generated adoption, random splits, or historical scores.

## Data disposition

| Input | Status | Geographic scope | Use |
|---|---|---|---|
| Stack Exchange monthly aggregate | observed file; provenance incomplete | site-wide/unspecified | Historical community activity only; no Kenya label |
| Survey aggregate, 2021–2024 | reported survey summary; source_type asserted | global/unspecified | Contextual survey comparison; not historical as-of features unless year precedes snapshot |
| Fortune 500 profile file | observed file; attribution/date incomplete | largely US | Company directory context only; never adoption |
| Generated adoption/mapping tables | proxy | none | Development only; exclude from market evidence and model |
| Inferred categories | inferred | none | Navigation aid with explicit inferred label |
| Live APIs | externally collected | query-dependent | Timestamped descriptive panel only pending independent leakage, coverage, comparability and legal review |
| Kenyan indicators/jobs/training | missing | Kenya | Show unavailable; do not impute zero |

## Repository coverage

The audit covered README, every docs Markdown/Mermaid/PDF, source and model pipeline packages, Streamlit dashboard and views, scripts, SQL queries, tests, CSV/JSON data, output reports/screenshots, dependency files, and `.env.example`. PDF text was inspected; PDFs were retained unchanged. Existing docs that propose random stratified splits or targets such as 80% accuracy are superseded by the temporal evaluation requirements in `docs/MODEL_METHODOLOGY.md`.
