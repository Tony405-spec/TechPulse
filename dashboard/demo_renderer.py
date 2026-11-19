"""Presentation pages backed only by the isolated synthetic SQLite database."""

from __future__ import annotations

import json
import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.ui import apply_theme
from dashboard.demo_store import DATABASE_PATH, FEATURES, read_demo_table

PAGES = [
    "Command Center",
    "Technology Explorer",
    "Technology Profile",
    "Community Health",
    "Global Rankings",
    "Enterprise Adoption",
    "Developer Sentiment",
    "Kenya Landscape",
    "Model Laboratory",
    "Explainability",
    "Data Observatory",
    "Methodology & About",
]


@st.cache_data(ttl=300, show_spinner=False)
def _table(name: str) -> pd.DataFrame:
    return read_demo_table(name)


def _banner(title: str, subtitle: str) -> None:
    apply_theme()
    st.markdown(
        f"""
        <div class="tp-hero">
          <div class="tp-kicker">TECHPULSE · ISOLATED DEMONSTRATION</div>
          <div class="tp-title">{title}</div>
          <div class="tp-subtitle">{subtitle}</div>
          <div style="margin-top:.8rem"><span class="tp-badge tp-risk-high">SYNTHETIC DEMONSTRATION DATA · NOT RESEARCH EVIDENCE</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.error(
        "Every value on this page comes from fictional, deterministic demonstration records. "
        "Do not cite these values, model metrics, company examples, predictions, or explanations as research findings.",
        icon="⚠️",
    )


def _plot_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#EAE4DF", "family": "Segoe UI, Arial, sans-serif"},
        margin={"l": 20, "r": 20, "t": 45, "b": 20},
        legend_title_text="",
    )
    fig.update_xaxes(gridcolor="#3B3634", zerolinecolor="#625955")
    fig.update_yaxes(gridcolor="#3B3634", zerolinecolor="#625955")
    return fig


def _download(frame: pd.DataFrame, file_name: str) -> None:
    st.download_button("Download CSV", frame.to_csv(index=False).encode("utf-8"), file_name=file_name, mime="text/csv")


def _techs() -> pd.DataFrame:
    return _table("technologies").merge(_table("latest_features"), on="technology_id")


def _command_center() -> None:
    _banner("Command Center", "A guided walkthrough of the application using a separate synthetic data store.")
    tech = _techs()
    evidence = _table("enterprise_evidence")
    metrics = _table("model_metrics")
    predictions = _table("predictions")
    cols = st.columns(4)
    cols[0].metric("Demo technologies", f"{len(tech):,}")
    cols[1].metric("Synthetic source rows", f"{len(_table('community_observations')):,}")
    cols[2].metric("Fictional company examples", f"{len(evidence):,}")
    cols[3].metric("Research predictions", "0")
    st.caption("The three demonstration classes are generated scenarios. They are not validated technology lifecycle outcomes.")
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Synthetic scenario distribution")
        counts = tech["synthetic_label"].value_counts().reindex(["Growing", "Stable", "Declining"], fill_value=0)
        fig = px.bar(counts.rename_axis("scenario").reset_index(name="fictional technologies"), x="scenario", y="fictional technologies", color="scenario", color_discrete_map={"Growing": "#89A98D", "Stable": "#B7A77D", "Declining": "#B97478"})
        st.plotly_chart(_plot_theme(fig), width="stretch")
    with right:
        st.subheader("Synthetic model run status")
        st.dataframe(metrics[["model_name", "accuracy", "weighted_f1", "validation_design"]], width="stretch", hide_index=True)
        st.caption("Metrics are computed on generated records only. Verified research model runs: 0.")
    st.info("Use the sidebar mode selector to return to the PostgreSQL research database. That mode never falls back to this SQLite demo store.")


def _technology_explorer() -> None:
    _banner("Technology Explorer", "Search and filter the fictional catalogue, then open a separate profile page.")
    tech = _techs()
    q = st.text_input("Search fictional technologies", placeholder="Try DemoLang or DemoDB")
    categories = ["All categories", *sorted(tech.category.unique())]
    category = st.selectbox("Category", categories)
    view = tech.copy()
    if q:
        view = view[view.name.str.contains(q, case=False, regex=False, na=False)]
    if category != "All categories":
        view = view[view.category.eq(category)]
    st.caption(f"{len(view)} synthetic catalogue records match the current filters.")
    st.dataframe(view[["name", "category", "as_of", "synthetic_label", "technology_health_score"]], width="stretch", hide_index=True)
    if view.empty:
        st.info("No synthetic technology matches. Try a different search or category.")
    else:
        st.selectbox("Profile preview", view.name.tolist(), key="explorer_profile_preview")
        _download(view, "techpulse_synthetic_technology_search.csv")


def _technology_profile() -> None:
    _banner("Technology Profile", "Historical signals, feature values, and a synthetic-only inference for one fictional technology.")
    tech = _techs()
    name = st.selectbox("Select fictional technology", tech.name.tolist())
    record = tech.loc[tech.name.eq(name)].iloc[0]
    technology_id = int(record.technology_id)
    st.subheader(f"{record.name} · {record.category}")
    st.caption("Synthetic scenario label: " + str(record.synthetic_label) + " · This is not a validated research prediction.")
    observations = _table("community_observations")
    observations = observations[observations.technology_id.eq(technology_id)].sort_values("month")
    fig = px.line(observations, x="month", y="question_volume", title="Simulated monthly question activity", labels={"month": "Simulated month", "question_volume": "Generated volume"})
    st.plotly_chart(_plot_theme(fig), width="stretch")
    features = pd.DataFrame([{"Feature": label, "Value": record[column], "Unit": unit} for label, column, unit in [
        ("Technology Health Score", "technology_health_score", "Synthetic 0-100 composite"),
        ("Growth Momentum Index", "growth_momentum_index", "Percent change"),
        ("Question Quality Score", "question_quality_score", "Percent"),
        ("Company Diversity Score", "company_diversity_score", "Synthetic sector count"),
        ("Sentiment Delta", "sentiment_delta", "Synthetic satisfaction points"),
        ("Adoption Velocity", "adoption_velocity", "Synthetic examples / quarter"),
        ("Community Decay Rate", "community_decay_rate", "Percent change; negative may indicate growth"),
    ]])
    st.subheader("Seven feature values")
    st.dataframe(features, width="stretch", hide_index=True)
    pred = _table("predictions")
    pred = pred[pred.technology_id.eq(technology_id)]
    st.subheader("Synthetic demonstration inference")
    if pred.empty:
        st.info("No synthetic inference is available for this fictional technology.")
    else:
        selected_model = st.selectbox("Demonstration model", sorted(pred.model_name.unique()))
        prediction = pred.loc[pred.model_name.eq(selected_model)].iloc[0]
        st.metric("Synthetic-only class", prediction.predicted_label)
        st.caption("Model: " + prediction.model_name + " · Scope: " + prediction.model_scope)
        probabilities = _table("prediction_probabilities")
        probabilities = probabilities.loc[probabilities.prediction_id.eq(prediction.prediction_id)].sort_values("probability", ascending=False)
        if not probabilities.empty:
            st.dataframe(probabilities[["class_name", "probability"]], width="stretch", hide_index=True)
        st.info("Risk score and confidence are not reported: the synthetic classifier is not calibrated for real-world use.")
    survey = _table("survey_observations")
    survey = survey[survey.technology_id.eq(technology_id)]
    st.subheader("Synthetic survey-like observations")
    st.dataframe(survey[["survey_year", "respondent_count", "usage_share", "interest_share", "admiration_share", "satisfaction_score", "geography"]], width="stretch", hide_index=True)
    st.subheader("Fictional enterprise examples")
    evidence = _table("enterprise_evidence")
    evidence = evidence.loc[evidence.technology_id.eq(technology_id)]
    st.dataframe(evidence[["company_name", "sector", "observation_date", "verification_status", "data_origin"]], width="stretch", hide_index=True)
    st.caption("These company relationships are synthetic examples, not real adoption evidence.")


def _community_health() -> None:
    _banner("Community Health", "Generated question and activity histories exercise the demonstration workflow.")
    technologies = _table("technologies")
    selected = st.selectbox("Fictional technology", technologies.name.tolist(), key="community_health_technology")
    tech_id = int(technologies.loc[technologies.name.eq(selected), "technology_id"].iloc[0])
    activity = _table("community_observations")
    activity = activity.loc[activity.technology_id.eq(tech_id)].sort_values("month").copy()
    activity["answer_rate"] = activity.answered_volume / activity.question_volume.clip(lower=1)
    columns = st.columns(3)
    columns[0].metric("Monthly observations", f"{len(activity):,}")
    columns[1].metric("Latest generated volume", f"{int(activity.question_volume.iloc[-1]):,}")
    columns[2].metric("Latest answer rate", f"{activity.answer_rate.iloc[-1]:.1%}")
    activity_chart = px.line(
        activity,
        x="month",
        y=["question_volume", "answered_volume", "unanswered_volume"],
        markers=True,
        title=f"Synthetic activity history · {selected}",
    )
    st.plotly_chart(_plot_theme(activity_chart), width="stretch")
    questions = _table("developer_questions")
    questions = questions.loc[questions.technology_id.eq(tech_id)].sort_values("created_at", ascending=False)
    st.subheader("Fictional discussion sample")
    st.dataframe(questions[["created_at", "title", "score", "answer_count", "sentiment", "data_origin"]], width="stretch", hide_index=True)
    _download(activity, f"{selected.lower().replace(' ', '_')}_synthetic_community.csv")
    st.caption("All question and activity records here were generated; they are not real posts or research observations.")


def _rankings() -> None:
    _banner("Global Rankings", "Comparable rankings within the synthetic scenario only; no real technology is ranked.")
    tech = _techs()
    metric_map = {
        "Health score": "technology_health_score",
        "Growth momentum": "growth_momentum_index",
        "Question quality": "question_quality_score",
        "Company diversity": "company_diversity_score",
        "Adoption velocity": "adoption_velocity",
        "Community decay": "community_decay_rate",
    }
    metric = st.selectbox("Rank by", list(metric_map))
    category = st.selectbox("Filter category", ["All categories", *sorted(tech.category.unique())])
    view = tech if category == "All categories" else tech[tech.category.eq(category)]
    view = view.sort_values(metric_map[metric], ascending=(metric == "Community decay"))
    st.dataframe(view[["name", "category", metric_map[metric], "synthetic_label"]], width="stretch", hide_index=True)
    st.caption("Ranking values are generated from the same simulated process and are not comparisons of real technologies.")
    _download(view, "techpulse_synthetic_rankings.csv")


def _enterprise() -> None:
    _banner("Enterprise Adoption", "Fictional company-to-technology examples used only to exercise this view.")
    data = _table("enterprise_adoption_observations")
    rel = _table("company_technology_relationships")
    companies = _table("company_profiles")
    technologies = _table("technologies")
    rel = rel[["relationship_id", "company_id", "technology_id", "first_observed"]]
    companies = companies[["company_id", "company_name", "sector"]]
    data = data.merge(rel, on="relationship_id").merge(companies, on="company_id").merge(technologies[["technology_id", "name", "category"]], on="technology_id")
    st.warning("All organizations and relationships below are fictional synthetic scenarios, not verified enterprise adoption evidence.")
    technology_filter = st.selectbox("Technology filter", ["All technologies", *sorted(data.name.unique())])
    sectors = sorted(data.sector.unique())
    selected = st.multiselect("Synthetic sectors", sectors, default=sectors)
    search = st.text_input("Search fictional organizations", placeholder="Fictional Demo Organization")
    data = data[data.sector.isin(selected)]
    if technology_filter != "All technologies":
        data = data.loc[data.name.eq(technology_filter)]
    if search:
        data = data.loc[data.company_name.str.contains(search, case=False, regex=False, na=False)]
    pivot = data.pivot_table(index="sector", columns="name", values="adoption_observation_id", aggfunc="count", fill_value=0)
    st.plotly_chart(_plot_theme(px.imshow(pivot, aspect="auto", color_continuous_scale=[[0, "#2C2827"], [1, "#7B3342"]], title="Fictional example counts by sector")), width="stretch")
    st.dataframe(data[["company_name", "name", "sector", "observed_at", "adoption_state", "source_description", "data_origin"]], width="stretch", hide_index=True)
    _download(data, "techpulse_synthetic_enterprise_examples.csv")


def _sentiment() -> None:
    _banner("Developer Sentiment", "Synthetic usage, interest, admiration, and satisfaction series. Sample sizes are generated.")
    data = _table("sentiment_observations")
    names = dict(zip(_table("technologies").technology_id, _table("technologies").name))
    data["technology"] = data.technology_id.map(names)
    technology = st.selectbox("Fictional technology", sorted(data.technology.unique()))
    measure = st.selectbox("Synthetic sentiment measure", ["positive_share", "neutral_share", "negative_share", "satisfaction_score"])
    data = data.loc[data.technology.eq(technology)]
    fig = px.line(data, x="month", y=measure, markers=True, title=f"Synthetic {measure.replace('_', ' ')} over time")
    st.plotly_chart(_plot_theme(fig), width="stretch")
    st.dataframe(data[["month", "positive_share", "neutral_share", "negative_share", "satisfaction_score", "sample_count", "geography", "data_origin"]], width="stretch", hide_index=True)
    _download(data, f"{technology.lower().replace(' ', '_')}_synthetic_sentiment.csv")
    st.caption("These monthly sentiments and sample counts are simulated; they are not survey responses or evidence about developers.")


def _kenya() -> None:
    _banner("Kenya Technology Landscape", "Fictional Kenya-labelled observations are shown only in the isolated synthetic database.")
    geo = _table("geographic_observations")
    kenya = geo.loc[geo.geography_code.str.startswith("KE-")].copy()
    technologies = _table("technologies")
    kenya = kenya.merge(technologies[["technology_id", "name", "category"]], on="technology_id")
    st.warning("These are invented Kenya-labelled demonstration records. They are not observations about Kenyan developers, businesses, or technology adoption.")
    st.metric("Fictional Kenya-labelled rows", f"{len(kenya):,}")
    location = st.selectbox("Fictional location", ["All locations", *sorted(kenya.geography_name.unique())])
    if location != "All locations":
        kenya = kenya.loc[kenya.geography_name.eq(location)]
    st.dataframe(kenya[["name", "category", "geography_name", "month", "synthetic_interest_index", "sample_count", "data_origin"]], width="stretch", hide_index=True)
    _download(kenya, "techpulse_fictional_kenya_demo.csv")
    st.caption("The PostgreSQL research database still has zero verified Kenya-specific technology observations.")


def _model_lab() -> None:
    _banner("Model Laboratory", "Actual classifiers trained on simulated records, evaluated chronologically, and stored with a synthetic-only scope.")
    if st.button("Train and persist all four synthetic demo models"):
        from dashboard.demo_population import train_demo_models_from_database

        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            result = train_demo_models_from_database(connection)
        st.cache_data.clear()
        st.success(
            f"Trained from SQLite feature snapshots. Best synthetic holdout model: {result['best_model']}; "
            f"persisted predictions: {result['predictions']}; SHAP explanations: {result['explanations']}."
        )
        st.rerun()
    runs = _table("model_metrics")
    metric_columns = ["model_name", "accuracy", "precision", "recall", "weighted_f1", "macro_f1", "validation_design", "train_start", "train_end", "test_start", "test_end"]
    st.dataframe(runs[metric_columns], width="stretch", hide_index=True)
    _download(runs[metric_columns], "techpulse_synthetic_model_metrics.csv")
    measure = st.selectbox("Metric", ["accuracy", "precision", "recall", "weighted_f1", "macro_f1"])
    fig = px.bar(runs, x="model_name", y=measure, color="model_name", title=f"{measure.replace('_', ' ').title()} · synthetic holdout only")
    st.plotly_chart(_plot_theme(fig), width="stretch")
    model = st.selectbox("Inspect model", runs.model_name.tolist())
    row = runs.loc[runs.model_name.eq(model)].iloc[0]
    st.subheader("Per-class metrics")
    st.dataframe(pd.DataFrame(json.loads(row.class_metrics_json)).T, width="stretch")
    st.subheader("Confusion matrix · class order Growing, Stable, Declining")
    matrix = pd.DataFrame(json.loads(row.confusion_matrix_json), index=["Actual Growing", "Actual Stable", "Actual Declining"], columns=["Pred Growing", "Pred Stable", "Pred Declining"])
    st.dataframe(matrix, width="stretch")
    st.subheader("Expanding-window time-series cross-validation")
    cv = _table("model_cv_results")
    st.dataframe(cv.loc[cv.model_name.eq(model)], width="stretch", hide_index=True)
    importance = json.loads(row.feature_importance_json) if row.feature_importance_json else {}
    if importance:
        st.subheader("Random Forest feature importance")
        importance_frame = pd.DataFrame([{"feature": key, "importance": value} for key, value in importance.items()]).sort_values("importance", ascending=False)
        st.dataframe(importance_frame, width="stretch", hide_index=True)
    st.error("These are genuine calculations on synthetic labels and test rows, but they are not research performance and do not validate the TechPulse hypothesis.")
    st.caption("Check per-class recall and the confusion matrix before interpreting aggregate scores. The synthetic labels are imbalanced, and current models perform poorly on the Declining class.")


def _explainability() -> None:
    _banner("Explainability", "SHAP values computed for a synthetic Random Forest, with explicit synthetic scope.")
    explanations = _table("explanations")
    if explanations.empty or explanations.feature.eq("unavailable").all():
        st.info("SHAP is unavailable in this synthetic environment. No research model or research explanation exists.")
        if not explanations.empty:
            st.caption(str(explanations.iloc[0].model_scope))
        return
    global_values = explanations.groupby("feature", as_index=False).mean_abs_shap.mean().sort_values("mean_abs_shap", ascending=True)
    fig = px.bar(global_values, x="mean_abs_shap", y="feature", orientation="h", title="Mean absolute SHAP · synthetic Random Forest")
    st.plotly_chart(_plot_theme(fig), width="stretch")
    technology_id = st.selectbox("Fictional technology", sorted(explanations.technology_id.dropna().unique()))
    local = explanations[explanations.technology_id.eq(technology_id)].sort_values("local_contribution")
    st.dataframe(local[["feature", "local_contribution", "mean_abs_shap", "model_scope"]], width="stretch", hide_index=True)
    st.caption("SHAP contributions describe this synthetic model's associations; they are not causal evidence or research findings.")


def _data_observatory() -> None:
    _banner("Data Observatory", "Source catalogue, generated record counts, freshness, and quality status for the isolated demo database.")
    source = _table("source_registry")
    st.dataframe(source, width="stretch", hide_index=True)
    names = [
        "technologies", "community_observations", "historical_technology_observations",
        "developer_questions", "sentiment_observations", "survey_observations",
        "company_profiles", "company_technology_relationships", "enterprise_adoption_observations",
        "enterprise_evidence", "geographic_observations", "feature_snapshots",
        "lifecycle_assessments", "model_runs", "model_metrics", "predictions",
        "prediction_probabilities", "explanations", "model_cv_results", "kenya_context",
    ]
    counts = pd.DataFrame([{"table": name, "records": len(_table(name)), "data_mode": "SYNTHETIC DEMONSTRATION DATA"} for name in names])
    st.subheader("Demo database record counts")
    st.dataframe(counts, width="stretch", hide_index=True)
    st.subheader("Validation checks")
    st.dataframe(_table("quality_checks"), width="stretch", hide_index=True)
    st.subheader("Deterministic seed execution log")
    st.dataframe(_table("demo_seed_runs"), width="stretch", hide_index=True)
    st.caption("Every generated observation carries data_origin=SYNTHETIC_DEMONSTRATION_NOT_RESEARCH_EVIDENCE.")
    st.caption("The source URL uses the reserved synthetic:// scheme and cannot be opened as an external source citation.")


def _methodology() -> None:
    _banner("Methodology & About", "Definitions, evidence boundaries, and the difference between the approved research and this interface demonstration.")
    st.markdown("### Approved research question")
    st.write("TechPulse investigates whether community signals, enterprise adoption evidence, and developer sentiment can support Growing, Stable, and Declining technology lifecycle classifications. The synthetic walkthrough does not answer that research question.")
    st.markdown("### Seven requested features")
    definitions = pd.DataFrame([
        {"Feature": "Technology Health Score", "Demo calculation": "Mean of the bounded momentum component, question quality, and inverse positive decay; scaled 0-100.", "Inputs": "Generated volume trend, answered share, and decay.", "Source": "Synthetic generator; fictional monthly observations.", "Observation period": "Rolling simulated 12-month history.", "Availability / missing treatment": "Synthetic demo only. In research mode, unavailable without valid feature snapshots; missing remains NULL, never zero."},
        {"Feature": "Growth Momentum Index", "Demo calculation": "100 × (latest 3-month mean - previous 3-month mean) / previous 3-month mean.", "Inputs": "Generated monthly question volume.", "Source": "Synthetic generator; fictional monthly observations.", "Observation period": "Two adjacent 3-month windows as of the snapshot month.", "Availability / missing treatment": "Synthetic demo only. Research value unavailable until validated monthly history exists."},
        {"Feature": "Question Quality Score", "Demo calculation": "100 × answered volume / total generated question volume.", "Inputs": "Generated answered and unanswered counts.", "Source": "Synthetic generator; fictional community rows.", "Observation period": "All monthly observations in the feature history.", "Availability / missing treatment": "Synthetic demo only. Missing research counts remain NULL; no denominator is imputed."},
        {"Feature": "Company Diversity Score", "Demo calculation": "Count of distinct sectors assigned to fictional company examples observed by the snapshot date.", "Inputs": "Generated company-sector relationships.", "Source": "Synthetic generator; fictional company examples.", "Observation period": "Cumulative only through the feature as-of date.", "Availability / missing treatment": "Not real enterprise evidence; research value unavailable with no verified company-technology panel."},
        {"Feature": "Sentiment Delta", "Demo calculation": "Latest minus earliest synthetic satisfaction score available by the as-of year (0-100 points).", "Inputs": "Generated annual satisfaction series.", "Source": "Synthetic generator; fictional survey-like rows.", "Observation period": "Annual observations through the feature as-of year.", "Availability / missing treatment": "Not actual survey sentiment. Research source has usage/interest/admiration, not an aligned satisfaction series; remains unavailable."},
        {"Feature": "Adoption Velocity", "Demo calculation": "Mean generated new-company examples per quarter across the trailing four quarters.", "Inputs": "Generated company observation dates.", "Source": "Synthetic generator; fictional company examples.", "Observation period": "Four quarters ending at the snapshot date.", "Availability / missing treatment": "Not real adoption. Research value unavailable without dated, verified company evidence; no zero-fill."},
        {"Feature": "Community Decay Rate", "Demo calculation": "100 × (previous 6-month mean - recent 6-month mean) / previous 6-month mean.", "Inputs": "Generated monthly question volume.", "Source": "Synthetic generator; fictional monthly observations.", "Observation period": "Adjacent six-month windows ending at the snapshot date.", "Availability / missing treatment": "Synthetic demo only; negative can represent growth. Research value unavailable until valid complete windows exist."},
    ])
    st.dataframe(definitions, width="stretch", hide_index=True)
    st.markdown("### Lifecycle labels and model status")
    st.write("This synthetic UI demo labels simulated windows by comparing the mean volume in the next six months with the trailing three-month mean (Growing ≥ 1.20, Declining ≤ 0.80, otherwise Stable). That is a demo rule, not the approved SRS rule. The SRS specifies Growth Momentum Index thresholds plus a trailing 12-month volume-trend direction. The available real data cannot currently support a validated three-class experiment; research model runs and predictions remain zero.")
    st.warning("Synthetic model metrics and SHAP values exist only to demonstrate application workflows. Do not cite them as research performance, predictive validity, company adoption, or Kenyan evidence.")


RENDERERS = {
    "Command Center": _command_center,
    "Technology Explorer": _technology_explorer,
    "Technology Profile": _technology_profile,
    "Community Health": _community_health,
    "Global Rankings": _rankings,
    "Enterprise Adoption": _enterprise,
    "Developer Sentiment": _sentiment,
    "Kenya Landscape": _kenya,
    "Model Laboratory": _model_lab,
    "Explainability": _explainability,
    "Data Observatory": _data_observatory,
    "Methodology & About": _methodology,
}


def render_page(title: str) -> None:
    RENDERERS[title]()
