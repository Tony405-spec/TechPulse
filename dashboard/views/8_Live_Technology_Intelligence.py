"""Supplementary, timestamped public-API indicators for catalog technologies."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell
from dashboard.data import load_live_observations, load_live_status, load_predictions
from src.live_data.storage import LIVE_DATA_DIR, read_status, update_status

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ["github", "stackexchange", "pypi", "npm"]
SOURCE_LABELS = {"github": "GitHub", "stackexchange": "Stack Exchange", "pypi": "PyPI", "npm": "npm"}

render_shell("Live Technology Intelligence", "Inspect timestamped public API observations alongside TechPulse's existing research catalogue.", "LIVE DATA")
disclaimer_panel()
st.info("These API snapshots are supplementary descriptive indicators. They are stored separately from the historical research dataset and are not model inputs.")

catalogue, _ = load_predictions()
if catalogue.empty or "technology_name" not in catalogue:
    st.warning("The existing saved technology catalogue is unavailable. Restore or regenerate its normal pipeline artifact before exploring live sources.")
    st.stop()
technologies = sorted(catalogue["technology_name"].dropna().astype(str).unique().tolist(), key=str.casefold)
status_data = load_live_status()
source_status = status_data.get("sources", {})
latest_success = [entry for entry in source_status.values() if entry.get("last_success") and entry.get("technology") in technologies]
latest_success.sort(key=lambda entry: entry["last_success"], reverse=True)
preferred = latest_success[0].get("technology") if latest_success else None
selected_index = technologies.index(preferred) if preferred in technologies else 0
selected = st.selectbox("Choose a technology from the TechPulse catalogue", technologies, index=selected_index)

status_rows = []
for source in SOURCES:
    entry = source_status.get(source, {})
    status_rows.append({
        "Source": SOURCE_LABELS[source],
        "Last attempt": entry.get("last_attempt", "Not collected"),
        "Last successful collection": entry.get("last_success", "Not collected"),
        "Status": entry.get("status", "Not collected"),
        "Technology": entry.get("technology", "—"),
        "Rows added": entry.get("records_written", "—"),
        "Latest message": entry.get("error") or "—",
    })
st.markdown("### Collection status")
st.caption("Status describes the latest collector attempt; it is not a real-time API health probe. Data remains available if a later request fails.")
st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)

job = status_data.get("job", {})
if job.get("status") == "running":
    st.info(f"A background collection job is running (started {job.get('started_at', 'time unavailable')}). Use **Reload data** to check for completion.")
else:
    if st.button("Collect selected technology now", type="primary", key="live_collect"):
        LIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        start_time = pd.Timestamp.now(tz="UTC").isoformat()
        update_status(job={"status": "starting", "job_type": "manual", "started_at": start_time, "technology": selected})
        log_handle = (LIVE_DATA_DIR / "collection.log").open("ab")
        try:
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "scripts" / "collect_live_data.py"), "--technology", selected],
                cwd=ROOT,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            log_handle.close()
            current = read_status().get("job", {})
            if not (current.get("pid") == process.pid and current.get("status") in {"completed", "completed_with_errors"}):
                update_status(job={"status": "running", "job_type": "manual", "pid": process.pid, "started_at": start_time, "technology": selected})
            st.success("Collection started in a separate process. This page stays responsive while the APIs are queried.")
            st.caption("When finished, use **Reload data** below to view the new observations and source status.")
        except OSError as exc:
            log_handle.close()
            update_status(job={"status": "failed_to_start", "job_type": "manual", "technology": selected, "error": str(exc)})
            st.error(f"Could not start collection: {exc}")
if st.button("Reload data", key="reload_live_data"):
    load_live_observations.clear()
    st.rerun()

try:
    observations = load_live_observations()
except Exception as exc:
    observations = pd.DataFrame()
    st.error(f"The configured observation store could not be read: {exc}")

st.markdown("### Technology indicators")
if observations.empty:
    st.info("No live API observations have been collected yet. Select a catalog technology and use the background collection button above.")
    st.caption("A scheduled first collection can also be run independently with `python scripts/schedule_live_data.py --once`.")
    st.stop()
technology_id = selected.strip().casefold()
observations = observations.loc[observations["technology_id"].astype(str) == technology_id].copy()
if observations.empty:
    st.info(f"No live observations are stored for {selected}. The latest observations for other catalog technologies remain available.")
    st.stop()
observations["observed_at"] = pd.to_datetime(observations["observed_at"], errors="coerce", utc=True)
observations["collected_at"] = pd.to_datetime(observations["collected_at"], errors="coerce", utc=True)
observations["metric_value"] = pd.to_numeric(observations["metric_value"], errors="coerce")
observations = observations.dropna(subset=["observed_at", "collected_at"])
last_refresh = observations["collected_at"].max()
st.caption(f"Technology: {selected} · last stored observation collected {last_refresh.strftime('%Y-%m-%d %H:%M UTC')}. Observation dates are source dates where available; snapshots are otherwise timestamped when collected.")

summary_rows = []
additive_metrics = {"repositories_matching_query", "repositories_in_recent_update_sample", "repositories_pushed_last_30d_in_sample", "repository_stars", "repository_forks", "tag_total_questions", "questions_created_last_30d_sampled", "answered_questions_last_30d_sampled", "unanswered_questions_last_30d_sampled", "question_created", "release_published", "versions_with_release_files", "published_versions", "releases_last_30d", "downloads_last_month"}
for (source, metric), group in observations.groupby(["source", "metric_name"]):
    most_recent = group["collected_at"].max()
    snapshot = group.loc[group["collected_at"] == most_recent]
    text_values = sorted(snapshot["metric_text"].dropna().astype(str).unique().tolist())
    values = snapshot["metric_value"].dropna()
    if text_values:
        display_value = ", ".join(text_values[:8]) + (f" (+{len(text_values) - 8} more)" if len(text_values) > 8 else "")
    elif not values.empty:
        numeric_value = float(values.sum() if metric in additive_metrics else values.mean())
        display_value = f"{numeric_value:,.0f}" if numeric_value.is_integer() else f"{numeric_value:,.3f}"
    else:
        display_value = "Unavailable"
    summary_rows.append({
        "Source": SOURCE_LABELS.get(source, source), "Metric": metric, "Latest value": display_value,
        "Rows in snapshot": len(snapshot), "Observation timestamp": snapshot["observed_at"].max(),
        "Collection timestamp": most_recent,
    })
summary_frame = pd.DataFrame(summary_rows)
st.markdown("### Latest source indicators")
headline_metrics = [
    ("github", "repository_stars", "GitHub sampled stars"),
    ("stackexchange", "tag_total_questions", "Stack Exchange tag questions"),
    ("pypi", "releases_last_30d", "PyPI releases · 30 days"),
    ("npm", "downloads_last_month", "npm downloads · last month"),
]
available_headlines = [item for item in headline_metrics if ((summary_frame["Source"] == SOURCE_LABELS[item[0]]) & (summary_frame["Metric"] == item[1])).any()]
if available_headlines:
    cards = st.columns(len(available_headlines))
    for card, (source, metric, label) in zip(cards, available_headlines):
        value = summary_frame.loc[(summary_frame["Source"] == SOURCE_LABELS[source]) & (summary_frame["Metric"] == metric), "Latest value"].iloc[0]
        try:
            numeric_value = float(str(value).replace(",", ""))
            display_value = f"{numeric_value / 1_000_000:.2f}M" if numeric_value >= 1_000_000 else f"{numeric_value:,.0f}"
        except ValueError:
            display_value = value
        card.metric(label, display_value)
with st.expander("Latest indicators by source and metric"):
    st.dataframe(summary_frame, use_container_width=True, hide_index=True)

numeric = observations.dropna(subset=["metric_value"])
if not numeric.empty:
    st.markdown("### Historical observations")
    source_options = sorted(numeric["source"].unique(), key=lambda value: SOURCE_LABELS.get(value, value))
    source_index = source_options.index("stackexchange") if "stackexchange" in source_options else 0
    chosen_source = st.selectbox("Data source", source_options, index=source_index, format_func=lambda value: SOURCE_LABELS.get(value, value))
    source_frame = numeric.loc[numeric["source"] == chosen_source]
    metric_options = sorted(source_frame["metric_name"].unique())
    preferred_metric = "question_created" if chosen_source == "stackexchange" and "question_created" in metric_options else metric_options[0]
    chosen_metric = st.selectbox("Metric", metric_options, index=metric_options.index(preferred_metric))
    metric_frame = source_frame.loc[source_frame["metric_name"] == chosen_metric].copy()
    metric_frame["observation date"] = metric_frame["observed_at"].dt.floor("D")
    additive = chosen_metric in {"repository_stars", "repository_forks", "question_created", "release_published"}
    aggregator = "sum" if additive else "mean"
    daily = metric_frame.groupby("observation date", as_index=False)["metric_value"].agg(aggregator)
    daily = daily.rename(columns={"metric_value": chosen_metric})
    if len(daily) > 1:
        fig = px.line(daily, x="observation date", y=chosen_metric, markers=True, title=f"{SOURCE_LABELS.get(chosen_source, chosen_source)} · {chosen_metric}")
        fig.update_traces(line_color="#6D6255", marker_color="#6D6255")
        fig.update_layout(xaxis_title="Observation date", yaxis_title=chosen_metric, paper_bgcolor="#F3EEE7", plot_bgcolor="#F3EEE7", font_color="#3A3734")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Only one observation date is available for this metric; a time-series trend is not yet estimable.")
    collection_dates = metric_frame["collected_at"].dt.floor("D").drop_duplicates().sort_values()
    frequency = "irregular / insufficient history" if len(collection_dates) < 2 else f"approximately every {(collection_dates.diff().dropna().dt.total_seconds().median() / 86400):.1f} days"
    first_date, last_date = metric_frame["observed_at"].min(), metric_frame["observed_at"].max()
    st.caption(f"Source: {SOURCE_LABELS.get(chosen_source, chosen_source)} · Observation period: {first_date:%Y-%m-%d} to {last_date:%Y-%m-%d} · Collection frequency: {frequency} · Missing dates are not filled or interpreted as zero.")
    if chosen_source == "github":
        st.caption("GitHub repository search returns a bounded, query-matched public repository sample. Stars and repository metadata do not establish enterprise adoption or actual technology usage.")
    elif chosen_source == "stackexchange":
        st.caption("Stack Exchange measures activity in one tagged question community. Question or answer volume is not a direct measure of adoption; recent question results are capped and marked as sampled.")
    elif chosen_source == "pypi":
        st.caption("PyPI release metadata describes the explicitly mapped package. The official PyPI JSON endpoint does not provide usable download counts; its deprecated downloads field is ignored.")
    elif chosen_source == "npm":
        st.caption("npm monthly downloads describe the mapped package downloads, not unique users, installations in production, or enterprise adoption.")
else:
    st.info("The selected source has no numeric observations for this technology yet. Text metadata remains available in the table above.")

with st.expander("How this relates to the research model"):
    st.write("Live API snapshots are stored in `techpulse_live_observations` in PostgreSQL or `outputs/live_data/live_observations.csv` in local fallback mode. They do not alter `data/feature_matrix.csv`, historical labels, fitted models, or evaluation artifacts. A future modelling change requires a separate timestamp-alignment, leakage, comparability, missingness, and validation study.")
    st.write("Only explicitly mapped packages are queried. Review `data/live_package_map.json` before adding a mapping; similarly named packages should not be treated as proof that a technology uses that package.")
