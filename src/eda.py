"""Reproducible exploratory summaries for the six source datasets."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from src.common import OUTPUTS_DIR, ensure_directories

plt.switch_backend("Agg")


def _fingerprint(frame: pd.DataFrame) -> str:
    payload = frame.astype("string").to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _date_coverage(frame: pd.DataFrame) -> dict[str, Any]:
    ranges: dict[str, Any] = {}
    for column in frame.columns:
        if column.casefold() in {"date", "creation_date", "adoption_date", "period", "period_start", "survey_year", "year"}:
            if column.casefold() in {"survey_year", "year"}:
                years = pd.to_numeric(frame[column], errors="coerce").dropna()
                years = years.loc[years.between(1900, 2200)]
                ranges[column] = {
                    "valid": int(len(years)),
                    "invalid_or_missing": int(len(frame[column]) - len(years)),
                    "start_year": int(years.min()) if not years.empty else None,
                    "end_year": int(years.max()) if not years.empty else None,
                }
                continue
            values = pd.to_datetime(frame[column], errors="coerce")
            valid = values.dropna()
            ranges[column] = {
                "valid": int(len(valid)),
                "invalid_or_missing": int(len(values) - len(valid)),
                "start": valid.min().isoformat() if not valid.empty else None,
                "end": valid.max().isoformat() if not valid.empty else None,
            }
    return ranges


def _profile(name: str, frame: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    numeric = frame.select_dtypes(include="number")
    category_columns = frame.select_dtypes(exclude="number").columns
    missing = frame.isna().sum()
    numeric_summary = (
        numeric.describe(percentiles=[0.25, 0.5, 0.75]).astype(object).where(
            pd.notna(numeric.describe(percentiles=[0.25, 0.5, 0.75])), None
        ).to_dict()
        if not numeric.empty
        else {}
    )
    profile: dict[str, Any] = {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "column_names": list(map(str, frame.columns)),
        "dtypes": {str(k): str(v) for k, v in frame.dtypes.items()},
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "missing": {
            str(column): {"count": int(missing[column]), "rate": float(frame[column].isna().mean())}
            for column in frame.columns
        },
        "date_coverage": _date_coverage(frame),
        "numeric_summary": numeric_summary,
        "categorical_cardinality": {str(column): int(frame[column].nunique(dropna=True)) for column in category_columns},
        "categorical_top_values": {
            str(column): {str(key): int(value) for key, value in frame[column].value_counts(dropna=False).head(10).items()}
            for column in category_columns if frame[column].nunique(dropna=True) <= 100
        },
        "input_sha256": _fingerprint(frame),
        "technology_coverage": {},
        "correlation_min_pair_n": 30,
    }
    for column in ("technology", "technology_name", "tag"):
        if column in frame:
            profile["technology_coverage"][column] = int(frame[column].nunique(dropna=True))
    if not numeric.empty:
        valid_counts = numeric.notna().astype("int64").T.dot(numeric.notna().astype("int64"))
        for method in ("pearson", "spearman"):
            corr = numeric.corr(method=method, min_periods=30)
            corr = corr.mask(valid_counts < 30)
            corr.to_csv(output_dir / f"{name}_{method}_correlation.csv", na_rep="")
            near_zero = [
                str(column) for column in numeric.columns
                if numeric[column].nunique(dropna=True) <= 1
            ]
            if method == "pearson":
                profile["near_zero_variance_numeric_columns"] = near_zero
                profile["correlation_files"] = {
                    "pearson": f"{name}_pearson_correlation.csv",
                    "spearman": f"{name}_spearman_correlation.csv",
                }
        for column in list(numeric.columns)[:6]:
            values = pd.to_numeric(numeric[column], errors="coerce").dropna()
            if values.empty:
                continue
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.hist(values, bins=min(30, max(5, int(values.nunique()))), color="#7f3b45", edgecolor="#f4f0e9")
            ax.set(title=f"{name}: {column} distribution", xlabel=str(column), ylabel="Rows")
            fig.tight_layout()
            filename = f"{name}_{column}_distribution.png"
            fig.savefig(output_dir / filename, dpi=140)
            plt.close(fig)
            profile.setdefault("distribution_plots", []).append(filename)
    else:
        profile["near_zero_variance_numeric_columns"] = []
    labels = frame.get("trajectory_label")
    if labels is not None:
        profile["class_distribution"] = labels.value_counts(dropna=False).to_dict()
    else:
        profile["class_distribution"] = {"status": "not evaluated; no approved labels supplied"}
    return profile


def _plot_community_activity(datasets: dict[str, pd.DataFrame], output_dir: Path) -> str | None:
    frame = datasets.get("so_questions", pd.DataFrame()).copy()
    tech = next((col for col in ("technology", "tag", "technology_name") if col in frame), None)
    date = next((col for col in ("creation_date", "date", "period_start") if col in frame), None)
    if frame.empty or date is None:
        return None
    frame[date] = pd.to_datetime(frame[date], errors="coerce")
    frame = frame.dropna(subset=[date])
    if frame.empty:
        return None
    frame["_month"] = frame[date].dt.to_period("M").dt.to_timestamp()
    question_count = "question_count" if "question_count" in frame else None
    cumulative_snapshot = "question_pct" in frame or "unanswered_pct" in frame
    if cumulative_snapshot and tech:
        frame = frame.sort_values(date).drop_duplicates([tech, "_month"], keep="last")
        value = pd.to_numeric(frame[question_count], errors="coerce") if question_count else pd.Series(1, index=frame.index)
        ylabel = "Last observed cumulative tag total"
        title = "Monthly last-observed Stack Overflow tag totals (cumulative snapshots)"
    elif question_count:
        value = pd.to_numeric(frame[question_count], errors="coerce")
        ylabel = "Monthly questions represented by source rows"
        title = "Monthly community question activity"
    else:
        value = pd.Series(1, index=frame.index, dtype="float64")
        ylabel = "Question rows"
        title = "Monthly community question records"
    frame["_value"] = value
    monthly = frame.groupby("_month")["_value"].sum(min_count=1).dropna()
    if monthly.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 4.5))
    monthly.plot(ax=ax, color="#7f3b45")
    ax.set(title=title, xlabel="Month", ylabel=ylabel)
    fig.tight_layout()
    filename = "community_activity_by_month.png"
    fig.savefig(output_dir / filename, dpi=140)
    plt.close(fig)
    return filename


def generate_eda_report(datasets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Write complete dataset profiles and labelled, source-aware EDA plots."""
    ensure_directories()
    output_dir = OUTPUTS_DIR / "eda"
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_count": len(datasets),
        "datasets": {},
        "source_semantics": {
            "community": "A cumulative Stack Overflow tag snapshot is not a daily question-arrival count. The activity figure selects the last monthly snapshot when percentage fields identify snapshot semantics.",
            "sentiment": "Developer usage/interest/admiration are described as survey measures, not satisfaction or sentiment unless the source supplies a satisfaction_score.",
            "enterprise": "Company profiles are not interpreted as technology adoption evidence.",
            "labels": "Class feasibility is reported only if an approved trajectory_label column is supplied; this EDA does not assign labels.",
        },
        "cross_dataset_relationships": {
            "status": "candidate joins summarized only where common technology/company keys exist; no causal interpretation",
            "technology_key_cardinality": {},
            "unmatched_join_rates": "not estimated without approved source-specific join keys",
        },
    }
    for name, frame in datasets.items():
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
        report["datasets"][safe_name] = _profile(safe_name, frame, output_dir)
    community_plot = _plot_community_activity(datasets, output_dir)
    if community_plot:
        report["community_plot"] = str(Path("eda") / community_plot)
    for key, frame in datasets.items():
        tech_column = next((c for c in ("technology", "technology_name", "tag") if c in frame), None)
        if tech_column:
            report["cross_dataset_relationships"]["technology_key_cardinality"][key] = int(frame[tech_column].nunique(dropna=True))
    key_sets: dict[str, set[str]] = {}
    for key, frame in datasets.items():
        tech_column = next((c for c in ("technology", "technology_name", "tag") if c in frame), None)
        if tech_column:
            key_sets[key] = set(frame[tech_column].dropna().astype(str).str.casefold())
    pairwise = {}
    keys = list(key_sets)
    for idx, left in enumerate(keys):
        for right in keys[idx + 1:]:
            shared = key_sets[left] & key_sets[right]
            union = key_sets[left] | key_sets[right]
            pairwise[f"{left}__{right}"] = {
                "shared_technology_names": len(shared),
                "left_only": len(key_sets[left] - key_sets[right]),
                "right_only": len(key_sets[right] - key_sets[left]),
                "jaccard_similarity": len(shared) / len(union) if union else None,
                "interpretation": "name-key overlap only; not a verified entity resolution",
            }
    report["cross_dataset_relationships"]["pairwise_name_overlap"] = pairwise
    manifest_path = OUTPUTS_DIR / "data_sources.json"
    if manifest_path.exists():
        report["source_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    report["artifacts_directory"] = str(output_dir.relative_to(OUTPUTS_DIR.parent))
    report_path = OUTPUTS_DIR / "eda_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["report_path"] = str(report_path.relative_to(OUTPUTS_DIR.parent))
    return report
