# Superseded: Legacy Query Methodology

This document explains the historical SQL analytics and includes company-adoption assumptions unsupported by the current local source files. Use docs/MODEL_METHODOLOGY.md for current feature/target guardrails and docs/RESPONSIBLE_USE.md for interpretation. Retained for query history.

The queries are designed to be composable and to avoid hard-coded thresholds. Where possible they normalize metrics using percentiles (via `NTILE`) so that rankings remain stable even as data volume changes.

## Scoring Themes

- **Momentum:** Compare recent activity to a prior window (e.g., last 90 days vs. prior 90). Growth ratios are treated as 1 when the prior window is zero to avoid division errors.
- **Quality:** Favor high answer rates, low closure, and healthy engagement (scores, views). Penalize unanswered or frequently closed questions.
- **Difficulty:** High learning-curve scores, low answer rates, and high closure indicate friction. Scores invert rates so that higher values mean harder.
- **Adoption depth:** Company-level `adoption_score` (0–1) and counts of strategic/active adopters surface commercial traction beyond community chatter.
- **Diversity:** Stack entropy normalizes by the number of categories so that breadth is comparable across differently sized portfolios.

## Query Highlights

- **query1_top_technologies:** Blends question velocity, growth vs. prior quarter, answer depth, strategic accounts, and survey satisfaction. Percentile normalization keeps the composite score bounded.
- **query2_tech_difficulty:** Uses answer rate, closure rate, and survey learning-curve scores to identify technologies that are hard for developers.
- **query3_monthly_trends:** Month-level time series with a 3-month lag comparison to spotlight inflections.
- **query4_companies_most_tags:** Ranks companies by total tag mentions and surfaces each company's top tag.
- **query5_tech_categories:** Category rollup for volume, engagement, and adoption breadth.
- **query6_hardest_per_company:** Selects each company's hardest technology, balancing community friction and survey difficulty.
- **query7_growth_momentum:** Short-term (30-day) acceleration vs. a 150-day baseline plus adoption depth.
- **query8_parent_company_analysis:** Aggregates adoption and question mentions by corporate family for parent/holding companies.
- **query9_tech_health_score:** Composite health index across growth, answer quality, satisfaction, adoption depth, and interest.
- **query10_question_quality:** Quality score using answer, closure, score, and view medians.
- **query11_daily_patterns:** Day-of-week and hour-of-day distributions, normalized to shares of the weekly total.
- **query12_company_diversity:** Shannon entropy over technology categories to measure stack diversity.

## Data Expectations

- All timestamps are stored in UTC (`timestamptz`); adjust `created_at` extraction if your warehouse uses naive timestamps.
- Scores (`satisfaction_score`, `adoption_score`, `learning_curve`) should be scaled 0–1. If using raw survey percentages, divide by 100 before loading.
- `company_question_mentions` can be derived via profile domain matching, email domains, or explicit tags. One-to-many mappings are supported.
- The queries avoid temporary tables; they rely on CTEs to stay portable in read-only environments.

## Validation Steps

Use `scripts/diagnostic_queries.sql` to check row counts, null density, and referential coverage before running analytics. Confirm primary key uniqueness and that foreign keys cover expected proportions of rows.
