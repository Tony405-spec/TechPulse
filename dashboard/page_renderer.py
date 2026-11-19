"""PostgreSQL-backed renderers for all TechPulse dashboard pages."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components.ui import apply_theme, disclaimer_panel, render_shell
from dashboard.db.connection import DatabaseUnavailable
from dashboard.db import repositories as repo
from dashboard.readiness import indicator_readiness

KENYA_WARNING = "Kenya-specific technology-market evidence is currently limited. Global survey data is shown separately and must not be interpreted as Kenyan developer behaviour."

PAGES = [
    "Executive Overview",
    "Technology Explorer",
    "Kenya Technology Landscape",
    "Technology Rankings",
    "Community Health",
    "Market and Skills Signals",
    "Prediction Explorer",
    "Model Performance",
    "Live Technology Intelligence",
    "Data Provenance and Quality",
    "About and Responsible Use",
]

PAGE_SUBTITLES = {
    "Executive Overview": "Start here: review the available evidence, its coverage, and what the current data can support.",
    "Technology Explorer": "Find a canonical technology and inspect its source records, geographic scope, and validated results.",
    "Kenya Technology Landscape": "Review records verified as Kenya-specific; global observations are kept separate.",
    "Technology Rankings": "Compare technologies using named source measures; unavailable growth measures are withheld.",
    "Community Health": "Inspect the monthly community series and its validation status before interpreting activity.",
    "Market and Skills Signals": "Explore reported survey measures and any verified Kenya training or job records.",
    "Prediction Explorer": "Inspect persisted predictions only when a valid research model run and matching feature snapshot exist.",
    "Model Performance": "Review registered research evaluations, class metrics, and baselines when they are available.",
    "Live Technology Intelligence": "View timestamped external snapshots as descriptive context, not proof of adoption.",
    "Data Provenance and Quality": "Trace registered sources, ingestion status, table coverage, and blocked validation records.",
    "About and Responsible Use": "Read the research question, interpretation guidance, and limits on responsible use.",
}

def _db_error(exc: Exception) -> None:
    st.error("TechPulse cannot read its configured PostgreSQL database.")
    st.caption(str(exc))
    st.markdown(
        "Check that PostgreSQL is running, `.env` contains the connection for `TechPulse-Database`, and the `techpulse_app` role has read access. The dashboard does not switch to CSV when PostgreSQL is unavailable."
    )


def _freshness(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Unavailable"
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M UTC")


def _download(frame: pd.DataFrame, key: str) -> None:
    if frame.empty:
        st.caption("No rows are available to export.")
        return
    left, right = st.columns(2)
    with left:
        st.download_button(
            "Download CSV",
            frame.to_csv(index=False).encode("utf-8-sig"),
            f"techpulse_{key}.csv",
            "text/csv",
            key=f"{key}_csv",
        )
    with right:
        safe_frame = frame.astype(object).where(pd.notna(frame), None)
        payload = json.dumps(
            safe_frame.to_dict(orient="records"),
            default=str,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
        st.download_button(
            "Download JSON",
            payload,
            f"techpulse_{key}.json",
            "application/json",
            key=f"{key}_json",
        )


def _overview() -> None:
    st.warning(KENYA_WARNING, icon="⚠️")
    data = repo.overview()
    row = data.iloc[0]
    sources = repo.source_status()
    ke = repo.kenya_observations()
    predictions = repo.predictions()
    valid_sources = (
        int(sources.run_status.eq("succeeded").sum()) if not sources.empty else 0
    )
    blocked_sources = (
        int(
            (
                sources.run_status.eq("failed")
                | (sources.severity.eq("critical") & ~sources.passed.fillna(True))
            ).sum()
        )
        if not sources.empty
        else 0
    )
    cols = st.columns(3)
    cols[0].metric(
        "Technologies",
        f"{int(row.technology_count):,}",
        help="Canonical catalogue entries, not a count of technologies with validated lifecycle assessments.",
    )
    cols[1].metric(
        "Survey observation rows",
        f"{int(row.survey_observations):,}",
        help="Stored survey summary rows. These are not unique individual respondents or current measurements.",
    )
    cols[2].metric(
        "Community observations",
        f"{int(row.community_observations):,}",
        help="Validated curated monthly community records. The currently blocked source contributes no rows.",
    )
    cols = st.columns(3)
    cols[0].metric(
        "Verified Kenya observations",
        f"{len(ke):,}",
        help="Records explicitly verified as Kenya scoped; global survey rows and company profiles are excluded.",
    )
    cols[1].metric(
        "Valid sources",
        f"{valid_sources:,}",
        help="Registered source runs currently marked succeeded.",
    )
    cols[2].metric(
        "Blocked sources",
        f"{blocked_sources:,}",
        help="Failed sources or sources with failed critical quality checks.",
    )
    cols = st.columns(2)
    cols[0].metric(
        "Company profiles",
        f"{int(row.company_profiles):,}",
        "Directory only",
        help="Company directory profiles do not show which technologies those companies use.",
    )
    model_run_value = (
        "None"
        if pd.isna(row.latest_model_run)
        else pd.Timestamp(row.latest_model_run).strftime("%Y-%m-%d")
    )
    cols[1].metric(
        "Latest model run",
        model_run_value,
        help="Date of the latest registered successful model run, if one exists.",
    )
    st.caption(
        f"Global/unspecified survey rows: {int(row.global_survey_observations):,} · Latest survey period: {row.latest_survey_year or 'Unavailable'} · Latest community period: {row.latest_community_period or 'Unavailable'} · Last successful ingestion: {_freshness(row.latest_successful_ingestion)}. Survey years are not exact observation dates."
    )
    st.info(
        "Research status: no validated lifecycle labels, model run, or persisted predictions are currently available. Counts on this page describe source coverage, not technology health or adoption."
    )
    with st.expander("Research indicator readiness and definitions"):
        readiness_facts = repo.indicator_evidence()
        if readiness_facts.empty:
            st.info("No readiness evidence snapshot was returned by PostgreSQL.")
        else:
            st.dataframe(
                indicator_readiness(readiness_facts.iloc[0].to_dict()),
                width="stretch",
                hide_index=True,
            )
            persisted_features = int(readiness_facts.iloc[0].persisted_feature_values or 0)
            st.caption(
                f"Persisted non-missing feature values: {persisted_features:,}. Input readiness is not a model result; a calculation is only represented as executed when a traceable feature value is persisted."
            )
        st.caption(
            "Unavailable means the required validated evidence is absent; it is not a measured zero."
        )
    st.subheader("Evidence coverage")
    st.dataframe(
        sources[
            [
                c
                for c in [
                    "source_key",
                    "publisher",
                    "geographic_scope",
                    "source_class",
                    "run_status",
                    "rows_read",
                    "rows_written",
                    "error_summary",
                ]
                if c in sources
            ]
        ],
        width="stretch",
        hide_index=True,
    )
    if sources.empty:
        st.info("No sources are registered in the canonical source registry.")
    st.subheader("Technologies with available evidence")
    tech = repo.technologies()
    if tech.empty:
        st.info("No technology records are available.")
    else:
        tech["supporting_records"] = tech["survey_records"].fillna(0) + tech[
            "community_records"
        ].fillna(0)
        st.dataframe(
            tech.sort_values("supporting_records", ascending=False).head(15),
            width="stretch",
            hide_index=True,
        )
    st.subheader("Prediction coverage")
    if predictions.empty:
        st.info(
            "No valid persisted predictions exist. Prediction class counts are withheld until a valid model run and feature snapshot are present."
        )
    else:
        st.bar_chart(predictions["predicted_label"].value_counts())


def _explorer() -> None:
    technologies = repo.technologies()
    if technologies.empty:
        st.info("No canonical technologies are available in PostgreSQL.")
        return
    search = st.text_input("Search technologies", placeholder="Search a canonical name")
    view = technologies
    if search:
        view = view[
            view.canonical_name.str.contains(search, case=False, regex=False, na=False)
        ]
    if view.empty:
        st.info("No technology matches that search.")
        return
    name = st.selectbox("Technology", view.canonical_name.tolist())
    row = view.loc[view.canonical_name == name].iloc[0]
    st.markdown(f"## {name}")
    st.caption(f"Canonical technology ID: {int(row.technology_id)}")
    assessments = repo.technology_assessments(int(row.technology_id))
    pred = repo.predictions()
    pred = pred[pred.technology.eq(name)] if not pred.empty else pred
    st.subheader("Assessment and prediction status")
    status_cols = st.columns(3)
    status_cols[0].metric(
        "Persisted lifecycle labels", f"{len(assessments):,}",
        help="Stored research labels; their presence alone does not validate label methodology or model performance.",
    )
    status_cols[1].metric("Persisted valid predictions", f"{len(pred):,}")
    explanation_count = (
        sum(len(repo.prediction_explanations(int(pid))) for pid in pred.prediction_id)
        if not pred.empty else 0
    )
    status_cols[2].metric("Prediction explanation rows", f"{explanation_count:,}")
    if assessments.empty:
        st.info("No persisted lifecycle assessment or training label is recorded for this technology.")
    else:
        st.dataframe(assessments, width="stretch", hide_index=True)
    if pred.empty:
        st.info("No persisted prediction linked to a current successful model run and matching feature snapshot exists.")
    if explanation_count == 0:
        st.caption("No stored model explanation is available. A rule-based assessment is not presented as a prediction.")
    metadata_left, metadata_right = st.columns([1, 2])
    with metadata_left:
        st.markdown("**Categories**")
        st.write(row.categories or "Not recorded")
    with metadata_right:
        st.markdown("**Catalogue description**")
        st.write(row.description or "No source description is recorded.")
    with st.expander("Aliases and catalogue details"):
        st.write(row.aliases or "No aliases are recorded.")
    survey = repo.survey(geography="GLOBAL")
    survey = survey[survey.technology.eq(name)] if not survey.empty else survey
    community = repo.community()
    community = (
        community[community.technology.eq(name)] if not community.empty else community
    )
    live = repo.live_observations()
    live = live[live.technology.eq(name)] if not live.empty else live
    ke = repo.kenya_observations()
    ke = (
        ke[ke.technology.eq(name)]
        if not ke.empty and "technology" in ke
        else pd.DataFrame()
    )
    st.subheader("Source coverage")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Evidence": "Global/unspecified survey",
                    "Records": len(survey),
                    "Class": "Reported, global / unspecified",
                },
                {
                    "Evidence": "Community activity",
                    "Records": len(community),
                    "Class": "Observed source history; geography as recorded",
                },
                {
                    "Evidence": "Live observations",
                    "Records": len(live),
                    "Class": "Supplementary external observations",
                },
                {
                    "Evidence": "Verified Kenya observations",
                    "Records": len(ke),
                    "Class": "Only verified Kenya-scoped records",
                },
            ]
        ),
        width="stretch",
        hide_index=True,
    )
    if not survey.empty:
        st.subheader("Developer survey (geography remains explicit)")
        st.dataframe(survey, width="stretch", hide_index=True)
    else:
        st.info("No survey observations are available for this technology.")
    if not community.empty:
        st.subheader("Community activity")
        st.dataframe(community, width="stretch", hide_index=True)
        if community.period_start.notna().any():
            st.line_chart(community.set_index("period_start")["question_count"])
    else:
        st.info(
            "No community activity is available for this technology; unavailable data is not treated as zero."
        )
    if not ke.empty:
        st.subheader("Verified Kenyan observations")
        st.dataframe(ke, width="stretch", hide_index=True)
    else:
        st.info(
            "No verified Kenya-specific observations are available for this technology."
        )
    if not live.empty:
        st.subheader("GitHub and package registry observations")
        st.dataframe(live, width="stretch", hide_index=True)
        st.caption(
            "Stars, question counts, package downloads and release activity do not establish production use or adoption."
        )
    st.subheader("Latest validated prediction")
    if pred.empty:
        st.info(
            "No prediction is available because a validated feature snapshot or model run is missing."
        )
    else:
        st.dataframe(pred.head(1), width="stretch", hide_index=True)


def _kenya() -> None:
    data = repo.kenya_observations()
    if data.empty:
        st.info("No verified Kenya-specific data is currently available.")
        st.caption(
            "Global survey rows and company profiles are not counted as Kenya-specific technology evidence."
        )
        return
    st.subheader("Verified Kenya-only observations")
    st.dataframe(data, width="stretch", hide_index=True)
    st.caption(
        "Global comparison evidence is separate and does not contribute to the Kenya-only count."
    )


def _rankings() -> None:
    tech = repo.technologies()
    survey = repo.survey(geography="GLOBAL")
    community = repo.community()
    if tech.empty:
        st.info("No canonical technology evidence is available to rank.")
        return
    options = [
        "Activity",
        "Momentum",
        "Developer interest",
        "Community health",
        "Evidence coverage",
        "Recent growth",
    ]
    metric = st.selectbox("Ranking metric", options)
    frame = tech.copy()
    definition, period, support, observed = (
        "Count of source observation records",
        "All recorded periods",
        "supporting_records",
        "Derived from observed source records",
    )
    frame["supporting_records"] = frame.survey_records.fillna(
        0
    ) + frame.community_records.fillna(0)
    if metric == "Activity":
        frame["metric_value"] = frame.community_records
        definition, period, support, observed = (
            "Number of monthly community source records; not total technology use",
            "Available community periods",
            "community_records",
            "Observed count",
        )
    elif metric in {"Momentum", "Recent growth"}:
        st.info(
            "A time-aware community series is not available in the database; no growth or momentum rank is calculated."
        )
        return
    elif metric == "Developer interest":
        vals = (
            survey.groupby("technology", as_index=False).agg(
                metric_value=("interest_share", "mean"),
                supporting_records=("survey_year", "count"),
            )
            if not survey.empty
            else pd.DataFrame()
        )
        if vals.empty:
            st.info("No developer-interest observations are available.")
            return
        frame = frame.merge(
            vals, left_on="canonical_name", right_on="technology", how="inner"
        )
        definition, period, support, observed = (
            "Mean reported interest share within the selected source rows; geography stays labeled",
            "Survey years represented in source rows",
            "supporting_records",
            "Reported survey measure",
        )
    elif metric == "Community health":
        if community.empty or "answer_rate" not in community:
            st.info(
                "Community health cannot be ranked because community observations are absent or blocked."
            )
            return
        vals = community.groupby("technology", as_index=False).agg(
            metric_value=("answer_rate", "mean"),
            supporting_records=("period_start", "count"),
        )
        frame = frame.merge(
            vals, left_on="canonical_name", right_on="technology", how="inner"
        )
        definition, period, support, observed = (
            "Mean answer rate as reported in the community monthly metrics",
            "Available community periods",
            "supporting_records",
            "Derived from observed community records",
        )
    else:
        frame["metric_value"] = frame.supporting_records
        definition, period, support, observed = (
            "Available survey plus community record count; source types are not equivalent",
            "All recorded periods",
            "supporting_records",
            "Derived coverage count",
        )
    frame = frame.dropna(subset=["metric_value"]).sort_values(
        "metric_value", ascending=False
    )
    st.caption(
        f"Definition: {definition} · Period: {period} · Supporting-record field: {support} · Evidence: {observed}. Missing records are not ranked as zero."
    )
    st.dataframe(
        frame[
            [
                c
                for c in [
                    "canonical_name",
                    "metric_value",
                    "supporting_records",
                    "survey_records",
                    "community_records",
                ]
                if c in frame
            ]
        ],
        width="stretch",
        hide_index=True,
    )
    _download(frame, "rankings")


def _community() -> None:
    data = repo.community()
    if data.empty:
        blocked = repo.community_block()
        st.error(
            "Community activity is unavailable because the source failed critical validation."
        )
        if blocked.empty:
            st.warning(
                "PostgreSQL has no monthly community facts or registered StackExchange validation record. The local file is not loaded by this dashboard."
            )
        else:
            row = blocked.iloc[0]
            st.write(
                {
                    "Source": row.source_key,
                    "Status": row.status,
                    "Validation": row.details,
                    "Error summary": row.error_summary,
                    "Report": row.report,
                }
            )
        st.markdown(
            "**Expected schema:** tag, date, question_count, unanswered_count. The source has an invalid row where unanswered questions exceed question volume. Correct it against the original source, record the correction and checksum, rerun `python -m techpulse.cli validate-data`, then `python -m techpulse.cli ingest --source stackexchange`. No row is silently omitted."
        )
        return
    st.subheader("Community source health")
    names = sorted(data.technology.dropna().unique(), key=str.casefold)
    selected = st.selectbox("Technology", names)
    view = data[data.technology == selected].sort_values("period_start")
    st.dataframe(view, width="stretch", hide_index=True)
    st.line_chart(
        view.set_index("period_start")[["question_count", "unanswered_count"]]
    )
    st.caption(
        f"Coverage: {view.period_start.min()} to {view.period_start.max()}. Source timestamps are shown per row; gaps are not filled with zero."
    )


def _market() -> None:
    survey = repo.survey()
    if survey.empty:
        st.info("No developer-survey observations are available.")
    else:
        years = sorted(survey.survey_year.dropna().astype(int).unique())
        selected_year = st.selectbox("Survey year", years, index=len(years) - 1)
        geo = st.selectbox(
            "Geography",
            [
                "All recorded geographies",
                *sorted(survey.geography_code.dropna().astype(str).unique()),
            ],
        )
        frame = survey[survey.survey_year == selected_year]
        if geo != "All recorded geographies":
            frame = frame[frame.geography_code == geo]
        st.warning(
            "Global/unspecified survey observations remain separate from Kenyan evidence and do not represent Kenyan developer behaviour."
        )
        st.dataframe(frame, width="stretch", hide_index=True)
        st.caption(
            "Usage, interest and admiration are separate reported shares. Years and geographies are not combined in cross-period comparisons."
        )
    st.subheader("Training and public jobs")
    ke = repo.kenya_observations()
    training = ke[ke.record_type.eq("training programme")] if not ke.empty else ke
    jobs = ke[ke.record_type.eq("job market")] if not ke.empty else ke
    st.write(
        {
            "Verified Kenya training observations": len(training),
            "Terms-reviewed Kenya job observations": len(jobs),
        }
    )
    if training.empty and jobs.empty:
        st.info(
            "No verified Kenya training outcome or legally reviewed public job-market observations are available."
        )


def _predictions() -> None:
    data = repo.predictions()
    if data.empty:
        st.info(
            "No prediction is available because a validated feature snapshot or model run is missing."
        )
        return
    technology = st.selectbox(
        "Technology", sorted(data.technology.unique(), key=str.casefold)
    )
    row = data[data.technology == technology].iloc[0]
    st.markdown(f"### {technology}: {row.predicted_label}")
    st.caption(
        f"Model run {row.model_run_id} · Feature snapshot {_freshness(row.feature_snapshot_date)} · Predicted {_freshness(row.predicted_at)}"
    )
    confidence = max(
        (
            float(value)
            for value in [
                row.probability_growing,
                row.probability_stable,
                row.probability_declining,
            ]
            if pd.notna(value)
        ),
        default=None,
    )
    st.write(
        {
            "Probabilities calibrated": (
                bool(row.metadata.get("probabilities_calibrated", False))
                if isinstance(row.metadata, dict)
                else "Not recorded"
            ),
            "Confidence (maximum class score)": confidence,
            "Evidence coverage": row.evidence_coverage,
            "Uncertainty": row.uncertainty,
            "Artifact checksum": row.artifact_checksum,
        }
    )
    st.bar_chart(
        pd.Series(
            {
                "Growing": row.probability_growing,
                "Stable": row.probability_stable,
                "Declining": row.probability_declining,
            },
            name="Model score",
        )
    )
    explanations = repo.prediction_explanations(int(row.prediction_id))
    if not explanations.empty:
        st.dataframe(explanations, width="stretch", hide_index=True)
    st.caption(
        "Feature attributions describe model associations, not causes. Uncalibrated scores are not probabilities of real-world success."
    )


def _models() -> None:
    data = repo.model_runs()
    if data.empty:
        st.info(
            "No valid model run is recorded in PostgreSQL. Historical files and test fixture artifacts are not treated as current model evidence."
        )
        return
    data = data.drop_duplicates(
        subset=["model_run_id", "candidate_id", "metric_name", "split_name"]
    )
    st.dataframe(data, width="stretch", hide_index=True)
    class_metrics = repo.model_class_metrics()
    baselines = repo.baselines()
    if not class_metrics.empty:
        st.subheader("Per-class precision, recall, F1, and support")
        st.dataframe(class_metrics, width="stretch", hide_index=True)
    if not baselines.empty:
        st.subheader("Persisted majority-class and momentum baselines")
        st.dataframe(baselines, width="stretch", hide_index=True)
    st.caption(
        "Only PostgreSQL model registry rows are shown. Each run is labeled with freshness and validity; predictions additionally require a successful recent run, a matching feature snapshot, and persisted labels."
    )
    st.warning(
        "Confusion matrices, calibration details, and per-class support are shown only when persisted in the model registry."
    )


def _live() -> None:
    data = repo.live_observations()
    if data.empty:
        st.info("No live technology observations are recorded in PostgreSQL.")
        return
    st.dataframe(data, width="stretch", hide_index=True)
    _download(data, "live_observations")
    st.caption(
        "GitHub stars, Stack Exchange questions, npm downloads and package activity do not prove adoption or production use. Observation and collection timestamps are distinct."
    )


def _provenance() -> None:
    data = repo.provenance()
    st.subheader("Registered sources and lineage")
    if data.empty:
        st.info("The canonical source registry is empty.")
    else:
        st.dataframe(data, width="stretch", hide_index=True)
        _download(data, "source_provenance")
    counts = repo.table_counts()
    st.subheader("Canonical table row estimates")
    st.dataframe(counts, width="stretch", hide_index=True)
    _download(counts, "canonical_table_counts")
    blocked = repo.community_block()
    if not blocked.empty:
        st.subheader("Blocked sources")
        st.dataframe(blocked, width="stretch", hide_index=True)
    st.caption(
        "Counts for `pg_stat_user_tables` are PostgreSQL estimates. Exact source-quality metrics remain in run reports and quality-check records."
    )


def _about() -> None:
    st.markdown(
        "TechPulse is an academic decision-support and research project examining developer-community activity, survey signals and documented technology-market evidence."
    )
    st.markdown("### Interpretation")
    st.write(
        "Observed facts are stored with source and geography. Derived measures are calculated from recorded observations. Predictions require validated feature snapshots and successful model runs. Proxy values and missing evidence must be labeled, never presented as observations."
    )
    st.warning(KENYA_WARNING)
    st.markdown("### Responsible use")
    st.write(
        "Predictions do not guarantee technology success, employment outcomes, business results, investment performance, hiring success, or migration decisions. Use this system for exploratory research with source coverage, uncertainty and limitations in view."
    )
    st.markdown("### Definitions")
    st.write(
        "A trajectory label compares a defined future activity window with a recent window. A survey usage share describes its reported respondent sample. An API snapshot is a collected point in time. None independently proves production use or causation."
    )


RENDERERS = {
    "Executive Overview": _overview,
    "Technology Explorer": _explorer,
    "Kenya Technology Landscape": _kenya,
    "Technology Rankings": _rankings,
    "Community Health": _community,
    "Market and Skills Signals": _market,
    "Prediction Explorer": _predictions,
    "Model Performance": _models,
    "Live Technology Intelligence": _live,
    "Data Provenance and Quality": _provenance,
    "About and Responsible Use": _about,
}


def render_page(title: str) -> None:
    apply_theme()
    render_shell(
        title,
        PAGE_SUBTITLES.get(
            title,
            "PostgreSQL-backed evidence for technology trends, coverage and research context.",
        ),
        "TECHPULSE RESEARCH",
    )
    disclaimer_panel()
    try:
        RENDERERS[title]()
    except (DatabaseUnavailable, KeyError, ValueError, TypeError) as exc:
        _db_error(exc)
