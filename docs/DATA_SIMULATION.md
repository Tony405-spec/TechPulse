# TechPulse simulation data

## Disclosure and scope

The `sim` schema contains a deterministic synthetic scenario generated with seed
42 for software-engineering demonstration and pipeline validation. It contains
300 synthetic technology identifiers and 500 synthetic company profiles. The
database retains generated labels such as `Synthetic Framework 0001` and
`Synthetic Corporation 0001`; they are not observations of actual products or
organisations.

For presentation usability, the Streamlit simulation view maps the 300 technology
IDs to familiar real technology names, such as Python and PostgreSQL. This is a
display-only alias catalog; it does not change the database, simulator, features,
labels, predictions, or model outputs. Every signal history and outcome remains a
generated scenario attached to a name. It must not be interpreted as evidence
about the named technology's real Stack Exchange activity, enterprise adoption,
developer opinion, Kenyan use, or market trajectory. The UI states this disclosure
next to the catalog and saved result.

The six canonical source tables are `technology_metadata`, `company_profiles`,
`stack_overflow_questions`, `developer_survey`, `fortune500_stacks`, and
`question_company_mapping`. Each row is marked `SYNTHETIC_SIMULATION`; the
mapping table is simulated co-occurrence and does not link a real question to a
real company. Legacy table names are compatibility views over these tables.

## Scenario assumptions

The generator uses the checked-in `config/simulation.yaml`. It produces monthly
community-volume observations, annual noisy survey measurements, and lagged
synthetic company adoption events. Latent technology trajectories are sampled
from the configured curve families. The configured family weights are scenario
assumptions, not class quotas. Noise and ambiguity perturbations are applied
before target labelling. The generator never changes a label after the shared
labeller has assigned it.

The loaded realization contains 36,000 community-month rows, 3,000 survey rows,
77,610 adoption events, and 27,080 simulated mappings. These counts describe this
seed/configuration realization only. They are not estimates of real-world volume
or adoption prevalence.

## Target rule and documented deviation

For an anchor date, the shared labeller compares the trailing three-month mean
community volume with the mean over the following six months:

- `Growing` when the future/recent ratio is at least 1.20.
- `Declining` when the ratio is at most 0.80.
- `Stable` otherwise.

The thresholds and window lengths are in `config/labels.yaml`. The project
proposal/SRS also describes a GMI/slope-based lifecycle rule. This simulation
uses the already shared future-window-ratio labeller instead; that is a
methodological deviation, not a reconciliation of the documents. It is recorded
pending supervisor clarification. GMI remains a predictor in this exploratory
simulation, but it is calculated only from observations available at or before
the anchor; no future-window values are included in features.

The realized anchor-label counts are Growing 1,808; Stable 2,458; Declining
1,434 (5,700 total). This distribution is reported as generated and is not tuned
to a target balance.

## Reproducibility and limitations

`ml.data_versions` records the seed, SHA-256 hash of both YAML configurations,
generator version, source-table checksums, row counts, realized class counts,
Git commit, dirty-worktree flag, and disclosure. The corpus loader verifies each
table after insertion and checks foreign-key integrity. Rerunning with the same
seed/configuration is idempotent. No original research source is repaired,
overwritten, or silently substituted by this simulation.

Models trained from this corpus can test software workflow and method behavior
under the specified scenario. They cannot establish predictive performance on
real technologies or support an empirical claim about technology decline.
