# TechPulse source and model feasibility check

Generated UTC: 2026-11-16T20:51:38.494520+00:00

## Verified source

- Official DataCamp course resource: https://assets.datacamp.com/production/repositories/3567/datasets/1e9257c9d86e03a979124c6d99a0ff154da953fd/stackexchange.csv
- Exact source-copy SHA-256: `2f3404dc403331a3be28ce4e40ae6d92adf5f86daa02b0c5eee695d535ec08f1`
- Source rows: 45,238; technologies/tags: 53; date range: 2016-01-01 to 2018-09-25.
- The local primary CSV matches the exact source copy on tag/date keys and count columns; share columns are equal within 1e-6 decimal serialization tolerance: **True**.
- These are dated snapshots of cumulative totals and relative shares. Use an observed monthly snapshot; do not sum the daily stock values as daily new activity.

## Data-quality decision

- Invalid row union: **2** of 45,238.
- Invalid examples and flags:

  - `amazon-mws` on 2018-02-21: question_count=0, unanswered_count=0 (non_positive_cumulative_total)
  - `ios` on 2018-02-21: question_count=0, unanswered_count=181334 (non_positive_cumulative_total, unanswered_exceeds_total)

- The invalid rows are retained in the raw source and excluded only from the derived monthly snapshot. No values were repaired or fabricated.
- Derived valid monthly snapshots: 1,515 across 53 tags. This is a descriptive transformation, not ingestion into PostgreSQL.

## Three-month label feasibility

Candidate rule: compare the next 3-month mean `question_pct` with the latest 3-month mean, after six months of history; use the existing 1.20/0.80 cutoffs. This is a relative-share label, not direct developer activity, enterprise use, or lifecycle death.

- Candidate panel: 1,091 tag-month rows over 25 forecast origins.
- All eligible rows: `{"Growing": 30, "Stable": 1061, "Declining": 0}`.
- Latest origin: 2018-06-01, n=53: `{"Growing": 4, "Stable": 49, "Declining": 0}`.
- Purged training rows (target window must end before the holdout feature date): n=879: `{"Growing": 22, "Stable": 857, "Declining": 0}`.
- **Decision: not trained: Declining has zero support in the purged training set and zero support in the latest holdout.** No three-class model was trained or persisted.

## Twelve-month target feasibility

- Eligible panel origins: 10; latest origin 2017-09-01.
- Purged training rows: 0; latest-origin holdout rows: 50.
- **Decision:** no training history remains after purging all training outcomes that overlap the latest holdout's feature period.

## Scope and limitations

This check supports a presentation about source provenance, quality gating, and historical global Stack Overflow relative-share trends. It does not resolve the proposal's enterprise-adoption gap, produce Kenya evidence, validate a three-class lifecycle model, or create predictions for the dashboard. A longer, independently sourced history and supported Declining examples are required before model training is defensible.
