"""Source provenance, workflow, labels and the twelve SQL analytics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.components.ui import disclaimer_panel, render_shell
from dashboard.data import DATA, OUTPUTS, load_community, load_survey, read_json_artifact, source_manifest

render_shell("Methodology & Data", "Trace the local source files through labels, model artifacts and SQL analysis.", "RESEARCH METHODS")
disclaimer_panel()

st.markdown("### How data becomes an output")
cols=st.columns(5)
steps=[("1. Sources","Community CSV, company profiles and optional survey aggregates"),("2. Ingest","CSV fallback or configured PostgreSQL warehouse"),("3. Features","Seven engineered signals with explicit provenance limits"),("4. Labels & models","Future-window labels, candidate classifiers and baselines"),("5. Saved results","Prediction, evaluation and SHAP artifacts read by the UI")]
for c,(head,body) in zip(cols,steps):
    with c:
        st.markdown(f"**{head}**")
        st.write(body)
        if head != steps[-1][0]: st.markdown("↓")

manifest=source_manifest()
st.markdown("### Active source and artifacts")
st.write(manifest.get("note", "No explanatory source note is recorded in the current manifest."))
tables=manifest.get("tables",{})
if tables:
    st.dataframe(pd.DataFrame([{"Warehouse table":k,"Source":v.get("source","not recorded"),"Development proxy":v.get("is_proxy","not recorded"),"Rows":v.get("rows","not recorded"),"Use limit":v.get("use_limit","")} for k,v in tables.items()]),use_container_width=True,hide_index=True)
else:
    st.info("The manifest in this checkout records expected table names but not a per-table provenance breakdown. See the report files and source code for details.")
community,survey=load_community(),load_survey()
if not community.empty and "date" in community:
    d=community["date"].dropna()
    st.caption(f"Community file: {len(community):,} rows; {community['tag'].nunique() if 'tag' in community else 'unknown'} tags; observed dates {d.min().date() if len(d) else 'unknown'} to {d.max().date() if len(d) else 'unknown'}.")
st.caption(f"Survey aggregate file: {'present ('+format(len(survey),',')+' rows)' if not survey.empty else 'absent in this checkout'}. Survey shares are not merged into the local historical prediction rows.")

st.markdown("### Six-table warehouse contract")
contract=pd.DataFrame([
 {"Table":"so_questions","Local source / status":"stackexchange.csv; observed community rows","Interpretation":"Tags, dates and unanswered measures"},
 {"Table":"dev_sentiment","Local source / status":"No survey CSV in this checkout","Interpretation":"Historical local version derives a proxy from unanswered share"},
 {"Table":"fortune500_stacks","Local source / status":"Development proxy","Interpretation":"Not observed company technology adoption"},
 {"Table":"company_profiles","Local source / status":"fortune.csv; 500 company profiles","Interpretation":"Profiles do not prove technology use"},
 {"Table":"tech_metadata","Local source / status":"Rule-derived development metadata","Interpretation":"Grouping metadata, not verified source facts"},
 {"Table":"question_company_mapping","Local source / status":"Development mapping","Interpretation":"Not an observed question-company relationship"},
])
st.dataframe(contract,use_container_width=True,hide_index=True)
st.caption("The logical schema document and SQL files describe a related descriptive-analysis schema (company, tag_company, tag_type, stackoverflow, and others). These query files must be reconciled with the six-table ingestion contract before executing them against a warehouse.")

st.markdown("### Supplementary live API observations")
st.write("GitHub, Stack Exchange, PyPI and npm observations use the same ingestion boundary and configured PostgreSQL/CSV storage mode. They are retained separately from the six historical tables and are not model inputs. See **Live Technology Intelligence** for source status, collection times, sampling notes, and observed history.")
st.caption("Only explicitly mapped PyPI/npm package names are queried. Current stars, question counts and download totals are collection-time measurements; they are never back-filled into the historical prediction period.")

with st.expander("Target label definition"):
    st.write("The implemented label compares future average monthly question volume with a recent activity average. A ratio of 1.20 or above is Growing; 0.80 or below is Declining; intermediate ratios are Stable. Future target fields must not be model inputs. Class counts in saved summary artifacts should be reconciled before reporting results.")
with st.expander("Feature engineering signals"):
    features=read_json_artifact(str(OUTPUTS/"feature_schema.json"))
    st.write("The current schema artifact lists the signal names. Their precise calculations are in `src/feature_engineering.py`; local proxy values for company adoption, categories, and mappings are not observed measurements.")
    if isinstance(features,list): st.code("\n".join(f"- {f}" for f in features))
with st.expander("Validation, leakage and temporal alignment"):
    st.write("The training source in this checkout performs a stratified random 80/20 split. This is not a time-forward holdout and may allow nearby observations from a technology to occur across both partitions. The saved evaluation summary is absent here, and local label summaries conflict with the feature matrix. Do not claim temporal generalisation or valid three-class performance from these artifacts. The community observations are historical; available public survey aggregates are absent in this local copy, and survey years 2021-2024 would not be as-of features for 2016-2018 rows.")

st.markdown("### Twelve SQL analytics")
st.write("The repository preserves twelve descriptive PostgreSQL query files. They answer useful exploratory questions, but query files use the legacy analytical schema noted above. Inspect the purpose and SQL before running against a database.")
query_titles={1:"Most active technologies",2:"Unanswered question share",3:"Monthly activity trend",4:"Company technology breadth",5:"Category-level activity",6:"Hardest technology per company",7:"Growth momentum",8:"Parent-company portfolio",9:"Technology health composite",10:"Question quality",11:"Daily activity pattern",12:"Company diversity"}
query_details={
 1:"Ranks tags by question volume and reports unanswered totals, average unanswered share, and active dates.",
 2:"Finds high unanswered shares among tags that meet a minimum question-volume threshold.",
 3:"Returns monthly question counts, unanswered measures, and a three-month lag for trend comparison.",
 4:"Counts distinct tags linked to each company and orders companies by portfolio breadth.",
 5:"Summarizes volume, unanswered share, and variation by technology category.",
 6:"Ranks the highest-friction technology for each company using question volume and unanswered share.",
 7:"Compares a recent 30-day window with an earlier activity window to describe momentum.",
 8:"Compares parent-company and subsidiary portfolios and community question totals.",
 9:"Builds a descriptive health score from activity, unanswered share, and active-day coverage.",
 10:"Summarizes question volume, unanswered share, and quality groupings by tag.",
 11:"Compares aggregate question activity by day of week.",
 12:"Uses technology-category breadth to describe company portfolio diversity.",
}
query_root=Path(__file__).resolve().parents[2]/"queries"
files=sorted(query_root.rglob("query*.sql"))
for path in files:
    import re
    match=re.search(r"query(\d+)_",path.name)
    number=int(match.group(1)) if match else 0
    with st.expander(f"Q{number:02}: {query_titles.get(number,path.stem)} — {path.parent.name}"):
        st.write(query_details.get(number,"Descriptive SQL analysis in the repository."))
        st.caption("Expected outputs depend on the referenced database tables. Verify table compatibility and data lineage before execution.")
        try: st.code(path.read_text(encoding="utf-8"),language="sql")
        except OSError: st.info("The SQL file could not be read.")

st.markdown("### Reproducibility files")
for name in ["data_sources.json","data_quality_report.json","evaluation_summary.json","model_comparison.csv","labelling_summary.json"]:
    p=OUTPUTS/name
    st.write(f"- `{name}`: {'available' if p.exists() else 'not present in this checkout'}")
