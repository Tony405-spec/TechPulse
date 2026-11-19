"""Run a source-aware, non-training feasibility audit for the final demo.

The source is a time series of cumulative Stack Overflow tag snapshots. This
script quarantines invalid source rows, derives one observed end-of-month
snapshot per tag, and checks whether the existing three-class thresholds have
support in a time-purged holdout. It does not train or persist a model.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs" / "presentation_rescue"
SOURCE_FILE = DATA / "stackexchange (1).csv"
PRIMARY_FILE = DATA / "stackexchange.csv"
SOURCE_URL = (
    "https://assets.datacamp.com/production/repositories/3567/datasets/"
    "1e9257c9d86e03a979124c6d99a0ff154da953fd/stackexchange.csv"
)
SOURCE_SHA256 = "2f3404dc403331a3be28ce4e40ae6d92adf5f86daa02b0c5eee695d535ec08f1"
REQUIRED_COLUMNS = [
    "tag",
    "date",
    "question_count",
    "question_pct",
    "unanswered_count",
    "unanswered_pct",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_source() -> tuple[pd.DataFrame, dict[str, object]]:
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(f"Verified source copy is missing: {SOURCE_FILE}")
    source_hash = _sha256(SOURCE_FILE)
    if source_hash != SOURCE_SHA256:
        raise ValueError(
            "The verified source-copy checksum changed; stop and reconcile the "
            f"source before using it (observed SHA-256 {source_hash})."
        )
    source = pd.read_csv(SOURCE_FILE)
    if list(source.columns) != REQUIRED_COLUMNS:
        raise ValueError(f"Unexpected source columns: {list(source.columns)}")
    source["date"] = pd.to_datetime(source["date"], errors="coerce")
    for column in REQUIRED_COLUMNS[2:]:
        source[column] = pd.to_numeric(source[column], errors="coerce")

    primary_hash = _sha256(PRIMARY_FILE) if PRIMARY_FILE.is_file() else None
    primary_matches = None
    if PRIMARY_FILE.is_file():
        primary = pd.read_csv(PRIMARY_FILE)
        primary["date"] = pd.to_datetime(primary["date"], errors="coerce")
        source_sorted = source.sort_values(["tag", "date"]).reset_index(drop=True)
        primary_sorted = primary.sort_values(["tag", "date"]).reset_index(drop=True)
        same_keys = source_sorted[["tag", "date"]].equals(
            primary_sorted[["tag", "date"]]
        )
        same_counts = all(
            np.array_equal(
                pd.to_numeric(source_sorted[column], errors="coerce").to_numpy(),
                pd.to_numeric(primary_sorted[column], errors="coerce").to_numpy(),
            )
            for column in ("question_count", "unanswered_count")
        )
        same_shares = all(
            np.allclose(
                pd.to_numeric(source_sorted[column], errors="coerce").to_numpy(),
                pd.to_numeric(primary_sorted[column], errors="coerce").to_numpy(),
                rtol=0,
                atol=1e-6,
                equal_nan=True,
            )
            for column in ("question_pct", "unanswered_pct")
        )
        primary_matches = bool(same_keys and same_counts and same_shares)

    source_metadata = {
        "source_url": SOURCE_URL,
        "source_file": str(SOURCE_FILE.relative_to(ROOT)),
        "source_sha256": source_hash,
        "primary_file": str(PRIMARY_FILE.relative_to(ROOT)),
        "primary_sha256": primary_hash,
        "primary_matches_source": primary_matches,
    }
    return source, source_metadata


def _quality_audit(source: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    dates = source["date"]
    questions = source["question_count"]
    unanswered = source["unanswered_count"]
    conditions = {
        "invalid_date": dates.isna(),
        "missing_count": questions.isna() | unanswered.isna(),
        "non_positive_cumulative_total": questions.le(0),
        "negative_count": questions.lt(0) | unanswered.lt(0),
        "unanswered_exceeds_total": unanswered.gt(questions),
        "invalid_question_share": ~source["question_pct"].between(0, 1),
        "invalid_unanswered_share": ~source["unanswered_pct"].between(0, 1),
    }
    reasons = pd.DataFrame(conditions, index=source.index)
    invalid = reasons.any(axis=1)
    examples = source.loc[invalid, REQUIRED_COLUMNS].copy()
    examples["quality_flags"] = reasons.loc[invalid].apply(
        lambda row: ", ".join(row.index[row].tolist()), axis=1
    )
    summary = {
        "rows": int(len(source)),
        "tags": int(source["tag"].nunique()),
        "date_start": dates.min().date().isoformat() if dates.notna().any() else None,
        "date_end": dates.max().date().isoformat() if dates.notna().any() else None,
        "exact_duplicate_rows": int(source.duplicated().sum()),
        "invalid_rows_union": int(invalid.sum()),
        "invalid_counts_by_rule": {
            key: int(mask.sum()) for key, mask in conditions.items()
        },
        "invalid_examples": examples.astype(object).where(
            pd.notna(examples), None
        ).to_dict("records"),
    }
    return reasons, summary


def _monthly_snapshots(source: pd.DataFrame, reasons: pd.DataFrame) -> pd.DataFrame:
    invalid = reasons.any(axis=1)
    usable = source.loc[~invalid].copy()
    usable["observation_month"] = (
        usable["date"].dt.to_period("M").dt.to_timestamp()
    )
    snapshots = (
        usable.sort_values("date")
        .groupby(["tag", "observation_month"], as_index=False)
        .tail(1)
        .sort_values(["tag", "observation_month"])
        .reset_index(drop=True)
    )
    snapshots["source_date"] = snapshots["date"].dt.strftime("%Y-%m-%d")
    snapshots["date"] = snapshots["observation_month"].dt.strftime("%Y-%m-%d")
    return snapshots[
        [
            "tag",
            "observation_month",
            "source_date",
            "question_count",
            "question_pct",
            "unanswered_count",
            "unanswered_pct",
        ]
    ]


def _candidate_panel(
    snapshots: pd.DataFrame, history_months: int, future_months: int
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for tag, group in snapshots.groupby("tag"):
        series = (
            group.set_index("observation_month")
            .sort_index()
            .asfreq("MS")
        )
        last_position = len(series) - future_months
        for position in range(history_months - 1, last_position):
            history = series.iloc[position - history_months + 1 : position + 1]
            future = series.iloc[position + 1 : position + 1 + future_months]
            if history["question_pct"].isna().any() or future["question_pct"].isna().any():
                continue
            recent_share = float(history["question_pct"].tail(3).mean())
            future_share = float(future["question_pct"].mean())
            ratio = future_share / max(recent_share, 1e-12)
            if ratio >= 1.20:
                label = "Growing"
            elif ratio <= 0.80:
                label = "Declining"
            else:
                label = "Stable"
            rows.append(
                {
                    "tag": str(tag),
                    "observation_month": series.index[position],
                    "target_end_month": future.index[-1],
                    "recent_question_share": recent_share,
                    "future_question_share": future_share,
                    "future_to_recent_ratio": ratio,
                    "candidate_label": label,
                }
            )
    return pd.DataFrame(rows)


def _counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    return {
        label: int(frame[column].value_counts().get(label, 0))
        for label in ("Growing", "Stable", "Declining")
    }


def _build_report(
    quality: dict[str, object],
    source_metadata: dict[str, object],
    snapshots: pd.DataFrame,
    three_month: pd.DataFrame,
    twelve_month: pd.DataFrame,
) -> tuple[dict[str, object], str]:
    latest_origin = pd.Timestamp(three_month["observation_month"].max())
    training = three_month.loc[
        three_month["target_end_month"] < latest_origin
    ].copy()
    holdout = three_month.loc[
        three_month["observation_month"] == latest_origin
    ].copy()
    twelve_origin = pd.Timestamp(twelve_month["observation_month"].max())
    twelve_training = twelve_month.loc[
        twelve_month["target_end_month"] < twelve_origin
    ]
    twelve_holdout = twelve_month.loc[
        twelve_month["observation_month"] == twelve_origin
    ]

    decision = (
        "not trained: Declining has zero support in the purged training set and "
        "zero support in the latest holdout"
        if training.empty
        or holdout.empty
        or _counts(training, "candidate_label")["Declining"] == 0
        or _counts(holdout, "candidate_label")["Declining"] == 0
        else "not trained by this audit: full supervised review is still required"
    )
    summary: dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source_metadata,
        "quality": quality,
        "monthly_snapshot_rows": int(len(snapshots)),
        "monthly_tags": int(snapshots["tag"].nunique()),
        "monthly_rows_per_tag": {
            "min": int(snapshots.groupby("tag").size().min()),
            "median": float(snapshots.groupby("tag").size().median()),
            "max": int(snapshots.groupby("tag").size().max()),
        },
        "candidate_definition": {
            "signal": "question_pct, the source's relative share of questions by tag",
            "history_months": 6,
            "recent_window_months": 3,
            "outcome_window_months": 3,
            "growing_ratio": 1.2,
            "declining_ratio": 0.8,
            "limitation": "candidate historical relative-share label only; not enterprise adoption or technology lifecycle decline",
        },
        "three_month_panel": {
            "rows": int(len(three_month)),
            "origin_months": int(three_month["observation_month"].nunique()),
            "first_origin": pd.Timestamp(
                three_month["observation_month"].min()
            ).date().isoformat(),
            "last_origin": latest_origin.date().isoformat(),
            "all_panel_class_counts": _counts(three_month, "candidate_label"),
            "purged_training_rows": int(len(training)),
            "purged_training_end": (
                pd.Timestamp(training["observation_month"].max()).date().isoformat()
                if not training.empty
                else None
            ),
            "purged_training_class_counts": _counts(training, "candidate_label"),
            "latest_holdout_rows": int(len(holdout)),
            "latest_holdout_class_counts": _counts(holdout, "candidate_label"),
            "model_status": decision,
        },
        "twelve_month_horizon": {
            "panel_rows": int(len(twelve_month)),
            "origin_months": int(twelve_month["observation_month"].nunique()),
            "latest_origin": twelve_origin.date().isoformat(),
            "purged_training_rows": int(len(twelve_training)),
            "holdout_rows": int(len(twelve_holdout)),
            "decision": (
                "no training history remains after purging all training outcomes "
                "that overlap the latest holdout's feature period"
                if twelve_training.empty
                else "training rows remain, but class and sample review is required"
            ),
        },
        "research_scope": (
            "global Stack Overflow tag-relative question-share feasibility only; "
            "not Kenya-specific, not verified enterprise adoption, and not a "
            "validated technology-decline prediction"
        ),
    }
    markdown = f"""# TechPulse source and model feasibility check

Generated UTC: {summary['generated_at_utc']}

## Verified source

- Official DataCamp course resource: {SOURCE_URL}
- Exact source-copy SHA-256: `{source_metadata['source_sha256']}`
- Source rows: {quality['rows']:,}; technologies/tags: {quality['tags']}; date range: {quality['date_start']} to {quality['date_end']}.
- The local primary CSV matches the exact source copy on tag/date keys and count columns; share columns are equal within 1e-6 decimal serialization tolerance: **{source_metadata['primary_matches_source']}**.
- These are dated snapshots of cumulative totals and relative shares. Use an observed monthly snapshot; do not sum the daily stock values as daily new activity.

## Data-quality decision

- Invalid row union: **{quality['invalid_rows_union']}** of {quality['rows']:,}.
- Invalid examples and flags:

{chr(10).join(f"  - `{row['tag']}` on {pd.Timestamp(row['date']).date()}: question_count={int(row['question_count'])}, unanswered_count={int(row['unanswered_count'])} ({row['quality_flags']})" for row in quality['invalid_examples'])}

- The invalid rows are retained in the raw source and excluded only from the derived monthly snapshot. No values were repaired or fabricated.
- Derived valid monthly snapshots: {len(snapshots):,} across {snapshots['tag'].nunique()} tags. This is a descriptive transformation, not ingestion into PostgreSQL.

## Three-month label feasibility

Candidate rule: compare the next 3-month mean `question_pct` with the latest 3-month mean, after six months of history; use the existing 1.20/0.80 cutoffs. This is a relative-share label, not direct developer activity, enterprise use, or lifecycle death.

- Candidate panel: {len(three_month):,} tag-month rows over {three_month['observation_month'].nunique()} forecast origins.
- All eligible rows: `{json.dumps(summary['three_month_panel']['all_panel_class_counts'])}`.
- Latest origin: {latest_origin.date().isoformat()}, n={len(holdout)}: `{json.dumps(summary['three_month_panel']['latest_holdout_class_counts'])}`.
- Purged training rows (target window must end before the holdout feature date): n={len(training)}: `{json.dumps(summary['three_month_panel']['purged_training_class_counts'])}`.
- **Decision: {decision}.** No three-class model was trained or persisted.

## Twelve-month target feasibility

- Eligible panel origins: {summary['twelve_month_horizon']['origin_months']}; latest origin {twelve_origin.date().isoformat()}.
- Purged training rows: {len(twelve_training)}; latest-origin holdout rows: {len(twelve_holdout)}.
- **Decision:** {summary['twelve_month_horizon']['decision']}.

## Scope and limitations

This check supports a presentation about source provenance, quality gating, and historical global Stack Overflow relative-share trends. It does not resolve the proposal's enterprise-adoption gap, produce Kenya evidence, validate a three-class lifecycle model, or create predictions for the dashboard. A longer, independently sourced history and supported Declining examples are required before model training is defensible.
"""
    return summary, markdown


def main() -> int:
    source, source_metadata = _load_source()
    reasons, quality = _quality_audit(source)
    snapshots = _monthly_snapshots(source, reasons)
    three_month = _candidate_panel(snapshots, history_months=6, future_months=3)
    twelve_month = _candidate_panel(snapshots, history_months=12, future_months=12)
    summary, markdown = _build_report(
        quality, source_metadata, snapshots, three_month, twelve_month
    )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = OUTPUTS / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / "audit.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    (output / "report.md").write_text(markdown, encoding="utf-8")
    snapshots.to_csv(output / "monthly_snapshots.csv", index=False)
    three_month.to_csv(output / "three_month_feasibility_panel.csv", index=False)
    twelve_month.to_csv(output / "twelve_month_feasibility_panel.csv", index=False)
    print(f"Feasibility audit saved to {output.relative_to(ROOT)}")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
