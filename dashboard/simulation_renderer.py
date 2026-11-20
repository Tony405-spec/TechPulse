"""Friendly, database-backed presentation layer for the simulated experiment."""

from __future__ import annotations

import json
import uuid
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import roc_curve

from dashboard import simulation_data as data

CLASSES = ["Growing", "Stable", "Declining"]
COLORS = {"Growing": "#22C55E", "Stable": "#F59E0B", "Declining": "#F43F5E"}
ICONS = {"Growing": "↗", "Stable": "→", "Declining": "↘"}
FRIENDLY_FEATURES = {
    "community_slope_12": "Community activity trend (12 months)",
    "community_slope_6": "Community activity trend (6 months)",
    "community_decay_rate": "Community activity decay",
    "growth_momentum_index": "Recent community momentum",
    "enterprise_adoption_breadth": "Breadth of simulated company adoption",
    "enterprise_adoption_depth": "Depth of simulated company adoption",
    "sentiment_satisfaction": "Simulated developer satisfaction",
    "sentiment_intent": "Simulated adoption intent",
    "sentiment_learning_curve": "Simulated learning curve",
}


def _theme() -> tuple[str, str, str]:
    with st.sidebar:
        st.markdown("### Appearance")
        light = st.toggle("Light mode", value=False, key="simulation_light_mode")
    bg, surface, fg = ("#F5F7FB", "#FFFFFF", "#162033") if light else ("#0B1020", "#121A2F", "#F1F5F9")
    muted = "#58677D" if light else "#A4B1C5"
    border = "#D8DFEA" if light else "#26324A"
    st.markdown(f"""
    <style>
      :root {{ --tp-bg:{bg}; --tp-surface:{surface}; --tp-fg:{fg}; --tp-muted:{muted}; --tp-border:{border}; }}
      html, body, [data-testid="stAppViewContainer"] {{ background:var(--tp-bg); color:var(--tp-fg); font-family:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; }}
      [data-testid="stHeader"] {{ background:transparent; }}
      [data-testid="stSidebar"] {{ background:var(--tp-surface); border-right:1px solid var(--tp-border); }}
      .block-container {{ max-width: 1380px; padding-top:1.35rem; padding-bottom:3rem; }}
      h1,h2,h3 {{ color:var(--tp-fg); letter-spacing:-.025em; }}
      p, label, li {{ color:var(--tp-fg); }}
      [data-testid="stCaptionContainer"] {{ color:var(--tp-muted); }}
      [data-testid="stMetric"] {{ background:var(--tp-surface); border:1px solid var(--tp-border); border-radius:12px; padding:14px 16px; }}
      [data-testid="stMetricValue"] {{ font-variant-numeric:tabular-nums; }}
      [data-testid="stMetricValue"] > div {{ font-size:1.65rem !important; }}
      [data-testid="stVerticalBlockBorderWrapper"] {{ border-color:var(--tp-border); border-radius:14px; }}
      [data-testid="stSelectbox"] [data-baseweb="select"] > div,
      [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{ background:var(--tp-surface) !important; color:var(--tp-fg) !important; border-color:var(--tp-border) !important; }}
      [data-testid="stSelectbox"] [role="combobox"], [data-testid="stMultiSelect"] [role="combobox"] {{ background:var(--tp-surface) !important; color:var(--tp-fg) !important; }}
      [data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input {{ color:var(--tp-fg) !important; }}
      [data-testid="stSelectbox"] .react-aria-ComboBox, [data-testid="stMultiSelect"] .react-aria-ComboBox {{ background:var(--tp-surface) !important; color:var(--tp-fg) !important; border:1px solid var(--tp-border) !important; border-radius:8px !important; }}
      [data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"] {{ background:var(--tp-surface) !important; color:var(--tp-fg) !important; border-color:var(--tp-border) !important; }}
      [data-testid="stSelectbox"] .react-aria-ComboBox input, [data-testid="stMultiSelect"] .react-aria-ComboBox input {{ background:transparent !important; color:var(--tp-fg) !important; }}
      [data-testid="stSelectbox"] svg, [data-testid="stMultiSelect"] svg {{ fill:var(--tp-muted) !important; }}
      .stButton > button {{ background:var(--tp-surface) !important; color:var(--tp-fg) !important; border:1px solid var(--tp-border) !important; border-radius:10px !important; }}
      [data-testid^="stBaseButton-"] {{ background:var(--tp-surface) !important; color:var(--tp-fg) !important; border:1px solid var(--tp-border) !important; border-radius:10px !important; }}
      .stButton > button:hover {{ border-color:#60A5FA !important; color:var(--tp-fg) !important; }}
      [data-testid="stTextInput"] input {{ background:var(--tp-surface) !important; color:var(--tp-fg) !important; border-color:var(--tp-border) !important; }}
      [data-testid="stTextInput"] input::placeholder {{ color:var(--tp-muted) !important; opacity:1; }}
      [data-baseweb="popover"] {{ background:var(--tp-surface) !important; }}
      [data-baseweb="tab-list"] {{ gap:.4rem; border-bottom:1px solid var(--tp-border); }}
      [data-baseweb="tab"] {{ padding:.72rem 1rem; }}
      [data-testid="stDataFrame"] {{ border:1px solid var(--tp-border); border-radius:10px; overflow:hidden; }}
      .tp-eyebrow {{ color:var(--tp-muted); text-transform:uppercase; letter-spacing:.11em; font-weight:650; font-size:.72rem; }}
      .tp-status {{ display:inline-flex; align-items:center; gap:.48rem; border:1px solid var(--tp-border); border-radius:999px; padding:.46rem .76rem; background:var(--tp-surface); font-size:.83rem; white-space:nowrap; }}
      .tp-dot {{ width:.56rem; height:.56rem; background:#22C55E; border-radius:50%; box-shadow:0 0 0 3px rgba(34,197,94,.14); }}
      .tp-sim {{ color:#FBBF24; font-weight:700; }}
      .tp-label {{ font-weight:750; font-size:1.45rem; line-height:1.2; }}
      .tp-muted {{ color:var(--tp-muted); font-size:.91rem; }}
      .tp-tag {{ display:inline-block; border:1px solid var(--tp-border); border-radius:999px; padding:.2rem .58rem; margin-right:.35rem; color:var(--tp-muted); font-size:.75rem; }}
      .tp-note {{ border-left:3px solid #F59E0B; padding:.68rem .9rem; background:var(--tp-surface); border-radius:0 9px 9px 0; }}
      @media (max-width: 760px) {{ .block-container {{ padding-left:.8rem; padding-right:.8rem; }} [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap; gap:.6rem; }} }}
    </style>
    """, unsafe_allow_html=True)
    return bg, surface, fg


def _plot_layout(fig: go.Figure, bg: str, surface: str, fg: str) -> go.Figure:
    fig.update_layout(
        template="plotly_white" if bg == "#F5F7FB" else "plotly_dark",
        paper_bgcolor=surface, plot_bgcolor=surface, font={"color": fg, "family": "Inter, sans-serif"},
        margin={"l": 18, "r": 18, "t": 88, "b": 18}, title={"font": {"size": 15, "color": fg}, "y": 0.98, "yanchor": "top"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.12, "x": 0, "font": {"color": fg}},
    )
    fig.update_xaxes(gridcolor="rgba(130,150,180,.14)", zerolinecolor="rgba(130,150,180,.2)", color=fg)
    fig.update_yaxes(gridcolor="rgba(130,150,180,.14)", zerolinecolor="rgba(130,150,180,.2)", color=fg)
    return fig


def _table(frame: pd.DataFrame, bg: str, surface: str, fg: str, height: int | None = None) -> None:
    """Render a compact table using the active light/dark palette."""
    if frame.empty:
        st.caption("No rows to display.")
        return
    values = [["—" if pd.isna(value) else str(value) for value in frame[column]] for column in frame.columns]
    border = "#26324A" if bg == "#0B1020" else "#D8DFEA"
    header = "#22304A" if bg == "#0B1020" else "#E9EEF7"
    fig = go.Figure(data=[go.Table(
        columnwidth=[max(1, min(3, len(str(col)) / 8)) for col in frame.columns],
        header={"values": list(frame.columns), "fill_color": header, "font": {"color": fg, "size": 12},
                "align": "left", "line_color": border, "height": 34},
        cells={"values": values, "fill_color": surface, "font": {"color": fg, "size": 11},
               "align": "left", "line_color": border, "height": 32},
    )])
    fig.update_layout(paper_bgcolor=surface, plot_bgcolor=surface, margin={"l": 0, "r": 0, "t": 4, "b": 4},
                      height=height or max(95, 38 + 34 * len(frame)))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}


def _model_name(value: str) -> str:
    return value.replace("_", " ").title()


def _feature_name(value: str) -> str:
    return FRIENDLY_FEATURES.get(value, value.replace("_", " ").capitalize())


def render_simulation_app() -> None:
    """Render the three presentation tabs using persisted PostgreSQL evidence."""
    bg, surface, fg = _theme()
    try:
        overview = data.get_overview()
        if not overview:
            st.error("There isn’t a simulation data version in PostgreSQL yet.")
            st.caption("Build and verify the research demo database first:")
            st.code("python -m src.run_all", language="bash")
            return
        technologies = data.get_technologies(str(overview["data_version_id"]))
        runs = data.get_model_runs()
    except Exception as exc:
        st.title("TechPulse")
        st.error("We couldn’t connect to the simulation database.")
        st.caption(f"Connection detail: {exc}")
        st.info("Start PostgreSQL and confirm DATABASE_URL in .env points to the dedicated techpulse_sim database. Then apply any pending schema migrations:")
        st.code("python -m src.db.migrate", language="bash")
        st.caption("If PostgreSQL is reachable but the simulation tables are empty, load the corpus with:")
        st.code("python -m src.run_all", language="bash")
        return

    session_id = st.session_state.setdefault("techpulse_browser_session_id", str(uuid.uuid4()))
    st.markdown('<div class="tp-eyebrow">Research prototype · trajectory analysis</div>', unsafe_allow_html=True)
    header, status = st.columns([2.4, 1])
    with header:
        st.title("TechPulse")
        st.caption("Explore simulated signals attached to familiar technology names.")
    with status:
        st.markdown(f"""
        <div class="tp-status"><span class="tp-dot"></span>Connected to PostgreSQL<br>
        <span class="tp-sim">SIMULATION · FICTIONAL DATA</span></div>
        <div style="text-align:right;margin-top:.45rem;color:{'#58677D' if bg == '#F5F7FB' else '#A4B1C5'};font-size:.78rem">Version {overview['data_version_id']}</div>
        """, unsafe_allow_html=True)
    st.markdown('<div class="tp-note"><b>Simulation only.</b> Technology names are real labels; all activity histories, adoption events, survey responses, labels, and model results are generated scenarios. They are not observations about the named technologies, real enterprise adoption, developer opinion, Kenya, or market outcomes.</div>', unsafe_allow_html=True)

    tabs = st.tabs(["🔎  Predict", "📊  Models", "💡  Insights"])
    with tabs[0]:
        _predict_tab(overview, technologies, session_id, bg, surface, fg)
    with tabs[1]:
        _models_tab(runs, bg, surface, fg)
    with tabs[2]:
        _insights_tab(overview, runs, bg, surface, fg)


def _predict_tab(overview: dict[str, Any], technologies: pd.DataFrame, session_id: str,
                 bg: str, surface: str, fg: str) -> None:
    st.subheader("Find a technology")
    st.caption("Search familiar technology names. Each name is attached to a generated profile; saved results do not describe the real technology.")
    search_col, category_col = st.columns([2, 1])
    with search_col:
        search = st.text_input("Search technologies", placeholder="Try “Python” or “PostgreSQL”", key="predict_search")
    with category_col:
        categories = ["All categories"] + sorted(technologies.category.dropna().unique().tolist())
        category = st.selectbox("Category", categories, key="predict_category")
    filtered = technologies.copy()
    if search:
        filtered = filtered[filtered.technology_name.str.contains(search, case=False, na=False)]
    if category != "All categories":
        filtered = filtered[filtered.category.eq(category)]
    if filtered.empty:
        st.info("No simulated technologies match that search. Try a shorter name or another category.")
        return

    predicted = filtered[filtered.prediction_id.notna()].copy()
    chip1, chip2 = st.columns(2)
    with chip1:
        if not predicted.empty and st.button("↘  Highest Declining probability", width="stretch"):
            selected = max(predicted.to_dict("records"), key=lambda r: _as_dict(r["probabilities"]).get("Declining", 0))
            st.session_state["predict_selected_name"] = selected["technology_name"]
    with chip2:
        growing = predicted[predicted.predicted_label.eq("Growing")]
        if not growing.empty and st.button("↗  Growing examples", width="stretch"):
            st.session_state["predict_selected_name"] = growing.sort_values("confidence", ascending=False).iloc[0].technology_name

    names = filtered.technology_name.tolist()
    if st.session_state.get("predict_selected_name") not in names:
        st.session_state["predict_selected_name"] = names[0]
    chosen_name = st.selectbox("Technology", names, key="predict_selected_name")
    selected = filtered.loc[filtered.technology_name.eq(chosen_name)].iloc[0]
    has_prediction = pd.notna(selected.prediction_id)
    anchor = selected.anchor_date if has_prediction else None
    trend_data = data.get_source_series(str(selected.technology_id), str(overview["data_version_id"]), anchor)
    latest_community_date = trend_data["community"].observation_month.max() if not trend_data["community"].empty else "unavailable"

    if has_prediction:
        probs = _as_dict(selected.probabilities)
        label = str(selected.predicted_label)
        with st.container(border=True):
            left, right = st.columns([1.6, 1])
            with left:
                st.markdown(f'<div class="tp-eyebrow">Saved simulated result · {selected.category}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="tp-label" style="color:{COLORS.get(label, fg)}">{ICONS.get(label, "•")}  {label}</div>', unsafe_allow_html=True)
                st.caption(f"Generated scenario attached to {selected.technology_name}; it is not evidence about that product’s actual trajectory.")
                st.write({"Growing": "Activity increased across the generated target window.", "Stable": "Activity stayed within the generated stable range.", "Declining": "Activity decreased across the generated target window."}.get(label, "Stored class result."))
                st.caption(f"Grouped test-set prediction · anchor {selected.anchor_date} · {_model_name(str(selected.model_name))}")
            with right:
                st.metric("Declining probability", f"{float(probs.get('Declining', 0)):.1%}")
                st.metric("Prediction source", "Held-out test")
        st.warning("Probability is not calibrated. It is not a reliability-backed confidence estimate. The current experiment has not implemented calibration or confidence bands.")
        if bool(selected.low_confidence):
            st.warning("This anchor has thin history, so the model result is additionally flagged low confidence.")
        else:
            st.caption("History flag: not marked thin by the current 24-month rule. This does not mean the model is calibrated.")
        st.caption(f"Coverage: saved test predictions are available for {int(technologies.prediction_id.notna().sum())} of {len(technologies)} simulated technologies. Others have no saved prediction; this app does not make live predictions.")

        probability_frame = pd.DataFrame({"Trajectory": CLASSES, "Probability": [float(probs.get(c, 0)) for c in CLASSES]})
        prob_fig = px.bar(probability_frame, x="Trajectory", y="Probability", color="Trajectory", color_discrete_map=COLORS,
                          title="Stored model probabilities · not calibrated")
        prob_fig.update_yaxes(range=[0, 1], tickformat=".0%")
        st.plotly_chart(_plot_layout(prob_fig, bg, surface, fg), width="stretch")
        csv = pd.DataFrame([{
            "technology": selected.technology_name, "category": selected.category, "anchor_date": selected.anchor_date,
            "prediction_source": "held_out_test", "model": selected.model_name, "predicted_label": label,
            "top_class_probability_uncalibrated": selected.confidence, "risk_score": selected.risk_score,
            **{f"p_{c.lower()}": probs.get(c) for c in CLASSES}, "data_version": overview["data_version_id"],
            "disclosure": "synthetic simulation; not empirical evidence",
        }]).to_csv(index=False).encode("utf-8")
        st.download_button("Download this result as CSV", csv, file_name=f"techpulse_{selected.technology_id}.csv", mime="text/csv")
    else:
        st.info("No saved prediction for this technology. It is outside the saved held-out prediction rows; the application will not invent a result or run a new prediction.")
        st.caption(f"Showing simulated source history through {latest_community_date} where available.")

    st.markdown("#### Three signal families")
    _signal_charts(trend_data, bg, surface, fg)
    if has_prediction:
        st.markdown("#### Why did the model lean this way?")
        explanation = data.get_local_explanation(int(selected.prediction_id))
        if explanation.empty:
            st.info("No local explanation is stored for this saved prediction.")
        else:
            exp = explanation.copy()
            exp["display_feature"] = exp.feature_name.map(_feature_name)
            exp["direction"] = np.where(exp.shap_value >= 0, "Pushed toward", "Pushed away from")
            exp["effect"] = exp.shap_value.abs()
            exp = exp.sort_values("shap_value")
            base_value = float(exp.base_value.iloc[0])
            labels = ["Baseline"] + exp.display_feature.tolist() + ["Model output"]
            measures = ["absolute"] + ["relative"] * len(exp) + ["total"]
            contributions = [base_value] + exp.shap_value.astype(float).tolist() + [0]
            fig = go.Figure(go.Waterfall(
                orientation="h", measure=measures, x=contributions, y=labels,
                increasing={"marker": {"color": "#22C55E"}}, decreasing={"marker": {"color": "#F43F5E"}},
                totals={"marker": {"color": "#60A5FA"}}, connector={"line": {"color": "#94A3B8"}},
                hovertemplate="%{y}<br>Contribution %{x:.4f}<extra></extra>",
            ))
            fig.update_layout(title="Signals associated with the model output", xaxis_title="Contribution on the stored model output scale", yaxis_title="")
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
            _table(exp[["display_feature", "direction", "shap_value"]].rename(columns={"display_feature": "Signal", "direction": "Effect", "shap_value": "Contribution"}), bg, surface, fg)
            with st.expander("Plain-English explanation details"):
                for row in exp.itertuples(index=False):
                    st.markdown(f"- **{row.display_feature}:** {row.explanation}")
            st.caption("These are associations used by the fitted model, not causes or advice.")

    with st.expander("Compare saved predictions"):
        saved = technologies[technologies.prediction_id.notna()]
        if saved.empty:
            st.info("No saved prediction rows are available for comparison.")
        else:
            compare_names = st.multiselect("Choose up to three", saved.technology_name.tolist(), max_selections=3, key="predict_compare")
            if compare_names:
                view = saved[saved.technology_name.isin(compare_names)].copy()
                view["probabilities"] = view.probabilities.map(_as_dict)
                for cls in CLASSES:
                    view[f"P({cls})"] = view.probabilities.map(lambda item: item.get(cls, 0))
                _table(view[["technology_name", "category", "anchor_date", "predicted_label", "confidence", "P(Growing)", "P(Stable)", "P(Declining)"]], bg, surface, fg)

    with st.expander("My watchlist"):
        try:
            watchlist = data.get_watchlist(session_id, str(overview["data_version_id"]))
            is_watched = str(selected.technology_id) in set(watchlist.technology_id.astype(str))
            label_text = "Remove from watchlist" if is_watched else "Add this technology"
            if st.button(label_text, key="watchlist_toggle"):
                data.set_watchlist(session_id, str(overview["data_version_id"]), str(selected.technology_id), not is_watched)
                st.rerun()
            if watchlist.empty:
                st.caption("Your list is stored in PostgreSQL for this browser session.")
            else:
                _table(watchlist[["technology_name", "added_at"]], bg, surface, fg)
        except Exception as exc:
            st.warning(f"Watchlist is unavailable: {exc}")


def _signal_charts(series: dict[str, pd.DataFrame], bg: str, surface: str, fg: str) -> None:
    community, enterprise, sentiment = series["community"], series["enterprise"], series["sentiment"]
    a, b, c = st.columns(3)
    with a:
        st.markdown("**Community**")
        if community.empty:
            st.caption("No activity observations available.")
        else:
            fig = px.line(community, x="observation_month", y="question_volume", title="Generated monthly activity")
            fig.update_traces(line_color="#60A5FA")
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
            st.caption("Question volume in the simulation.")
    with b:
        st.markdown("**Enterprise**")
        if enterprise.empty:
            st.caption("No simulated company adoption events available.")
        else:
            monthly = enterprise.assign(month=pd.to_datetime(enterprise.observation_date).dt.to_period("M").astype(str)).groupby("month", as_index=False).adoption_events.sum()
            fig = px.bar(monthly, x="month", y="adoption_events", title="Generated adoption events")
            fig.update_traces(marker_color="#A78BFA")
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
            st.caption("Synthetic events; not verified company adoption.")
    with c:
        st.markdown("**Developer sentiment**")
        valid = sentiment.loc[~sentiment.is_missing].copy() if not sentiment.empty else sentiment
        if valid.empty:
            st.caption("No non-missing survey signal is available by this date.")
        else:
            normalized = valid.copy()
            for col in ["satisfaction_score", "learning_curve_score"]:
                normalized[col] = normalized[col] / 100
            fig = go.Figure()
            for name, col, color in [("Satisfaction", "satisfaction_score", "#F472B6"), ("Intent", "adoption_intent", "#34D399"), ("Learning", "learning_curve_score", "#FBBF24")]:
                fig.add_trace(go.Scatter(x=normalized.observation_date, y=normalized[col], mode="lines+markers", name=name, line={"color": color}))
            fig.update_layout(title="Generated survey indicators", yaxis={"range": [0, 1], "tickformat": ".0%"}, yaxis_title="Normalized score")
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
            st.caption("Synthetic survey responses; not a representative developer survey.")


def _metric(meta: dict, split: str, name: str, key: str | None = None) -> float | None:
    values = meta.get(split) or {}
    value = values.get(key or name)
    if isinstance(value, dict):
        value = value.get("mean")
    return None if value is None else float(value)


def _models_tab(runs: pd.DataFrame, bg: str, surface: str, fg: str) -> None:
    st.subheader("How did the model perform?")
    st.caption("Models were evaluated using technology-grouped cross-validation. The selected model’s held-out test set was scored once.")
    if runs.empty:
        st.info("No completed model runs are recorded in PostgreSQL.")
        return
    selected = runs.loc[runs.selected_by_cv]
    if selected.empty:
        st.info("No model is marked as selected by grouped cross-validation.")
        return
    chosen = selected.iloc[0]
    chosen_meta = _as_dict(chosen.metadata)
    cv, test = chosen_meta.get("cv") or {}, chosen_meta.get("test") or {}
    metric_cols = st.columns(4)
    cv_f1 = cv.get("macro_f1") or {}
    metric_cols[0].metric("Selected model", "RF" if chosen.model_name == "random_forest" else _model_name(str(chosen.model_name)))
    metric_cols[1].metric("Grouped-CV macro-F1", f"{float(cv_f1.get('mean', 0)):.3f} ± {float(cv_f1.get('std', 0)):.3f}", help="Macro-F1 averages F1 equally across classes.")
    metric_cols[2].metric("Held-out macro-F1", f"{float(test.get('macro_f1', 0)):.3f}" if test else "Not recorded")
    metric_cols[3].metric("Held-out Declining recall", f"{float(test.get('Declining_recall', 0)):.3f}" if test else "Not recorded")
    st.markdown('<div class="tp-muted">The current experiment has no calibrated probability model. CV ECE/Brier values below are diagnostics, not calibrated confidence guarantees.</div>', unsafe_allow_html=True)

    rows = []
    for _, run in runs.iterrows():
        meta = _as_dict(run.metadata)
        cvm = meta.get("cv") or {}
        rows.append({
            "Model / baseline": (_model_name(str(run.model_name)) + (" · selected" if run.selected_by_cv else "")),
            "CV macro-F1 (mean ± SD)": f"{(cvm.get('macro_f1') or {}).get('mean', np.nan):.3f} ± {(cvm.get('macro_f1') or {}).get('std', np.nan):.3f}" if cvm.get("macro_f1") else "—",
            "CV macro OvR AUC": f"{_metric(meta, 'cv', 'roc_auc_ovr_macro'):.3f}" if _metric(meta, "cv", "roc_auc_ovr_macro") is not None else "—",
            "CV ECE": f"{_metric(meta, 'cv', 'calibration_ece_10bin'):.3f}" if _metric(meta, "cv", "calibration_ece_10bin") is not None else "—",
            "CV Brier": f"{_metric(meta, 'cv', 'brier_multiclass'):.3f}" if _metric(meta, "cv", "brier_multiclass") is not None else "—",
        })
    table = pd.DataFrame(rows)
    st.markdown("#### Model comparison")
    _table(table, bg, surface, fg)
    heldout_rows = []
    for _, run in runs.iterrows():
        meta = _as_dict(run.metadata)
        testm = meta.get("test") or {}
        if testm:
            heldout_rows.append({
                "Held-out model / baseline": _model_name(str(run.model_name)),
                "Macro-F1": f"{float(testm.get('macro_f1', np.nan)):.3f}",
                "Accuracy": f"{float(testm.get('accuracy', np.nan)):.3f}",
                "Declining recall": f"{float(testm.get('Declining_recall', np.nan)):.3f}",
            })
    st.caption("The candidate models not selected by cross-validation were not evaluated on the held-out groups, by design.")
    if heldout_rows:
        st.markdown("#### One-time held-out results")
        _table(pd.DataFrame(heldout_rows), bg, surface, fg)
    class_rows = []
    for cls in CLASSES:
        class_rows.append({
            "Class": cls,
            "CV precision / recall / F1": " / ".join(f"{float((cv.get(f'{cls}_{metric}') or {}).get('mean', np.nan)):.3f}" for metric in ["precision", "recall", "f1"]),
            "Held-out precision / recall / F1": " / ".join(f"{float(test.get(f'{cls}_{metric}', np.nan)):.3f}" for metric in ["precision", "recall", "f1"]) if test else "Not evaluated",
        })
    st.markdown("#### Per-class precision / recall / F1")
    _table(pd.DataFrame(class_rows), bg, surface, fg)
    f1_plot = pd.DataFrame([{"Model": _model_name(str(r.model_name)), "CV macro-F1": (m.get("cv") or {}).get("macro_f1", {}).get("mean", np.nan), "SD": (m.get("cv") or {}).get("macro_f1", {}).get("std", 0)} for _, r in runs.iterrows() for m in [_as_dict(r.metadata)]])
    fig = px.bar(f1_plot.sort_values("CV macro-F1"), x="CV macro-F1", y="Model", orientation="h", error_x="SD", title="Grouped-CV macro-F1 · mean with fold SD")
    st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")

    run_id = str(chosen.model_run_id)
    matrix = data.get_confusion_matrix(run_id)
    prob_rows = data.get_heldout_probabilities(run_id)
    left, right = st.columns(2)
    with left:
        st.markdown("#### Held-out confusion matrix")
        if matrix.empty:
            st.info("No held-out confusion matrix is stored.")
        else:
            grid = matrix.pivot(index="actual_class", columns="predicted_class", values="metric_value").reindex(index=CLASSES, columns=CLASSES).fillna(0)
            fig = px.imshow(grid, text_auto=True, aspect="auto", color_continuous_scale=[[0, surface], [1, "#2563EB"]],
                            labels={"x": "Predicted class", "y": "Actual class", "color": "Rows"}, title="Rows: actual · columns: predicted")
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
    with right:
        st.markdown("#### ROC · saved held-out probabilities")
        if prob_rows.empty:
            st.info("No held-out probabilities are stored for ROC analysis.")
        else:
            actual = prob_rows.actual_class.astype(str).to_numpy()
            prob_dicts = prob_rows.probabilities.map(_as_dict).tolist()
            fig = go.Figure()
            for cls in CLASSES:
                scores = np.asarray([float(p.get(cls, 0)) for p in prob_dicts])
                binary = actual == cls
                if binary.min() != binary.max():
                    fpr, tpr, _ = roc_curve(binary, scores)
                    fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=cls, line={"color": COLORS[cls]}))
            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance", line={"dash": "dash", "color": "#94A3B8"}))
            fig.update_layout(title="One-vs-rest ROC · synthetic test rows", xaxis_title="False positive rate", yaxis_title="True positive rate", xaxis={"range": [0, 1]}, yaxis={"range": [0, 1]})
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")

    st.markdown("#### Probability reliability")
    if prob_rows.empty:
        st.info("No held-out probability rows are stored.")
    else:
        all_probs = np.asarray([[float(p.get(c, 0)) for c in CLASSES] for p in prob_dicts])
        predicted_idx = all_probs.argmax(axis=1)
        confidence = all_probs.max(axis=1)
        correct = np.asarray(CLASSES)[predicted_idx] == actual
        bins = np.linspace(0, 1, 6)
        reliability = []
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (confidence >= lo) & ((confidence < hi) if hi < 1 else (confidence <= hi))
            if mask.any():
                reliability.append({"Mean top-class probability": float(confidence[mask].mean()), "Observed accuracy": float(correct[mask].mean()), "Rows": int(mask.sum())})
        if reliability:
            rel = pd.DataFrame(reliability)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=rel["Mean top-class probability"], y=rel["Observed accuracy"], mode="lines+markers", name="Held-out bins", marker={"size": 9, "color": "#60A5FA"}, customdata=rel["Rows"], hovertemplate="Probability %{x:.0%}<br>Accuracy %{y:.0%}<br>Rows %{customdata}<extra></extra>"))
            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Ideal", line={"dash": "dash", "color": "#94A3B8"}))
            fig.update_layout(title="Descriptive reliability check · held-out synthetic rows", xaxis_title="Mean top-class probability", yaxis_title="Observed accuracy", xaxis={"range": [0, 1], "tickformat": ".0%"}, yaxis={"range": [0, 1], "tickformat": ".0%"})
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
            st.caption("This chart describes the saved test outputs. It was not used to fit a calibration transform or select thresholds.")

    st.markdown("#### Signal-family ablation")
    ablation = data.get_ablation(run_id)
    if ablation.empty:
        st.info("No signal-family ablation results are stored.")
    else:
        fig = px.bar(ablation.sort_values("mean_macro_f1"), x="mean_macro_f1", y="signal_set", orientation="h", error_x="sd_macro_f1", title="Outer grouped-CV macro-F1 · mean with fold SD")
        st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
    st.info("A calibrated confidence band and accuracy-versus-coverage claim are not available: out-of-fold calibrated predictions and selective-prediction records have not been implemented. No reliability or confidence claim is inferred from the raw probabilities.")


def _insights_tab(overview: dict[str, Any], runs: pd.DataFrame, bg: str, surface: str, fg: str) -> None:
    st.subheader("What is in this experiment?")
    st.caption("These counts describe the generated version in PostgreSQL. They are not estimates of the real technology landscape.")
    counts = st.columns(4)
    counts[0].metric("Simulated profiles · real names", f"{int(overview['technology_count']):,}")
    counts[1].metric("Synthetic community months", f"{int(overview['community_month_count']):,}")
    counts[2].metric("Generated survey rows", f"{int(overview['survey_count']):,}")
    counts[3].metric("Generated adoption events", f"{int(overview['adoption_event_count']):,}")
    distribution = overview.get("class_distribution") or {}
    dist = pd.DataFrame([{"Trajectory": cls, "Anchors": int(distribution.get(cls, 0))} for cls in CLASSES])
    dist_fig = px.bar(dist, x="Trajectory", y="Anchors", color="Trajectory", color_discrete_map=COLORS, title="Generated labels · realized distribution")
    st.plotly_chart(_plot_layout(dist_fig, bg, surface, fg), width="stretch")

    selected_run = runs.loc[runs.selected_by_cv]
    if not selected_run.empty:
        shap = data.get_global_shap(str(selected_run.iloc[0].model_run_id))
        st.markdown("#### Which signals mattered to this fitted model?")
        if shap.empty:
            st.info("No global SHAP rows are stored.")
        else:
            classes = [c for c in CLASSES if c in shap.class_label.unique()]
            chosen_class = st.selectbox("View class", classes, key="insights_shap_class")
            subset = shap.loc[shap.class_label.eq(chosen_class)].sort_values("rank").head(10).copy()
            subset["Readable signal"] = subset.feature_name.map(_feature_name)
            fig = px.bar(subset.sort_values("mean_abs_shap"), x="mean_abs_shap", y="Readable signal", color="signal_family", orientation="h", title=f"Top stored SHAP features for {chosen_class}")
            st.plotly_chart(_plot_layout(fig, bg, surface, fg), width="stretch")
            st.caption("SHAP summarizes associations in this fitted simulation model. It does not establish causal effects.")

    with st.expander("About this data and what TechPulse does not claim"):
        st.markdown("""
        **What is simulated:** all 300 profiles, 500 company profiles, monthly community counts, annual survey signals, company adoption events, labels, and model outputs in this version are generated. The UI uses real technology names as display labels only; it does not attach actual Stack Overflow, enterprise, developer-survey, or Kenyan observations to those names.

        **Label rule:** a shared labeller compares the trailing 3-month community-volume mean with the following 6-month mean. Ratio >= 1.20 is Growing; ratio <= 0.80 is Declining; otherwise Stable. This differs from the GMI/slope lifecycle rule in the project proposal/SRS and is pending supervisor clarification.

        **Evaluation:** technologies are grouped across the training and held-out split to prevent windows from the same fictional technology crossing the split. The selected model is chosen by grouped-CV macro-F1. Its held-out result was evaluated once. Other candidate models do not have held-out metrics by design.

        **Limits:** the current saved prediction set covers only held-out technologies. Probabilities are not calibrated. The simulation does not verify real enterprise adoption or Kenya-specific technology use. Model explanations describe associations, not causes.

        **Not for:** real-world market forecasts, hiring, purchasing, investment, migration, or policy decisions.
        """)
    version = data.get_version_record(str(overview["data_version_id"]))
    with st.expander("Reproducibility record"):
        if version.empty:
            st.info("No data-version record is available.")
        else:
            st.json({k: str(v) if k == "generated_at" else v for k, v in version.iloc[0].to_dict().items()})
