# Feature dictionary

All feature snapshots are anchored to a month and are calculated from simulated
records dated on or before that anchor. Labels use the subsequent six-month
window and are stored separately in `ml.labels`. The evaluation is therefore a
synthetic scenario experiment, not empirical evidence.

| Feature | Signal family | Definition / timing |
|---|---|---|
| `community_log_volume_mean_12` | Community | `log(1 + mean monthly question volume)` over up to the trailing 12 observed months. |
| `community_slope_6` | Community | Least-squares monthly slope in question volume over up to 6 prior observed months. |
| `community_slope_12` | Community | Least-squares monthly slope over up to 12 prior observed months. |
| `community_acceleration_6` | Community | Trailing-six-month slope minus the preceding-six-month slope; missing when the prior window is unavailable. |
| `community_volatility_12` | Community | Sample standard deviation divided by mean over the trailing 12 months. |
| `community_answer_rate_6` | Community | Mean answered/question rate over up to 6 prior months. |
| `community_closure_rate_6` | Community | Mean simulated closure rate over up to 6 prior months. |
| `community_score_slope_6` | Community | Least-squares slope of monthly mean score over up to 6 prior months. |
| `community_decay_rate` | Community | `100 × (previous six-month mean − recent six-month mean) / previous six-month mean`; requires both windows. |
| `growth_momentum_index` | Community | `100 × (recent three-month mean − preceding three-month mean) / preceding three-month mean`; uses history only. |
| `enterprise_adoption_breadth` | Enterprise | Distinct simulated adopting companies active by anchor divided by the 500 simulated companies. |
| `enterprise_adoption_depth` | Enterprise | Mean simulated adoption-depth value among those active events; zero when none are recorded. |
| `enterprise_breadth_change_6m` | Enterprise | Current breadth minus breadth active at the date six months before the anchor. |
| `enterprise_sector_diversity` | Enterprise | Normalized Shannon entropy across sectors represented by active simulated adopting companies. |
| `sentiment_satisfaction` | Sentiment | Latest nonmissing simulated satisfaction measurement available by June 30 of its survey year and no later than the anchor. |
| `sentiment_intent` | Sentiment | Latest available simulated adoption-intent share under the same availability rule. |
| `sentiment_learning_curve` | Sentiment | Latest available simulated learning-curve score. |
| `sentiment_trajectory` | Sentiment | Least-squares slope across nonmissing survey satisfaction observations available by anchor; a descriptive trajectory proxy, not a future outcome. |
| `sentiment_missing` | Sentiment | 1 when no nonmissing survey row is available by anchor, otherwise 0. |
| `sentiment_satisfaction_missing` | Sentiment | Indicator that satisfaction is unavailable at the anchor. |
| `sentiment_intent_missing` | Sentiment | Indicator that intent is unavailable at the anchor. |
| `sentiment_learning_missing` | Sentiment | Indicator that learning-curve score is unavailable at the anchor. |
| `category` | Context | Simulated technology category; one-hot encoded inside each training fold. |
| `history_months` | Context | Number of monthly records available through the anchor. |
| `low_confidence` | Context | True when fewer than the configured 24 months of history are available. |

Missing numeric values are retained as null in PostgreSQL and imputed inside
each training-fold pipeline. One-hot encoding and scaling are also fit inside
each fold. Missingness indicators for survey values are explicit features.
Thin-history rows remain in training/evaluation and keep their low-confidence
flag; resulting test predictions retain the flag.

The trend baseline projects from the most recent observed monthly volume using
the trailing six-month linear slope, estimates the next six-month mean, divides
by the trailing three-month mean, and applies the configured label cutoffs. It
is persisted as `trend_baseline_label` for benchmarking but is excluded from
`FEATURE_COLUMNS`, so it is never a model predictor.
