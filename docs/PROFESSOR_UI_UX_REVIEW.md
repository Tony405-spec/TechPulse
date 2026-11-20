# TechPulse UI/UX and functional quality review

**Review date:** 2026-11-17  
**Application:** Streamlit research mode backed by PostgreSQL `TechPulse-Database`  
**Scope:** Interface and workflow improvements only. No research data, database rows, schema, model artifacts, or research objectives were changed.

## Initial findings

The existing dark theme and named navigation were already consistent, and the application clearly separated PostgreSQL research mode from its synthetic demonstration mode. The rendered overview nevertheless showed duplicate counts for the same 684 survey rows, clipped metric labels, and a clipped `Unavailable` model-run value. Page introductions were generic, and Technology Explorer rendered catalogue metadata as a raw object. Research indicators and the absence of an actual lifecycle experiment were harder to understand at first glance. Streamlit also emitted deprecation warnings for `use_container_width`.

The connected research database currently reports 267 catalogue technologies, 684 global/unspecified survey rows, 0 curated community observations, 497 company profiles, 0 verified Kenya observations, 1 blocked source, 0 model runs, and 0 predictions. Company profiles are directory metadata and do not establish technology use. The validated research state cannot support lifecycle scores, labels, model metrics, or explanations.

## Changes made

- Added task-oriented descriptions for all 11 research pages.
- Replaced the duplicated overview count with separate survey-row and curated-community counts. Reduced the metric grid to three columns, added concise definitions, and displayed `None` for the absent model run so the value remains legible.
- Added an expandable readiness table for the seven named research indicators. It gives the current evidence gap for each measure and says that unavailable is not a measured zero.
- Replaced Technology Explorer's raw metadata object with labelled catalogue fields and a collapsed aliases section.
- Reduced the repeated general disclaimer from a large alert to a compact caption; page-specific warnings remain visible.
- Replaced deprecated `use_container_width=True` calls in research pages, synthetic demonstration pages, and the shared technology profile component with `width="stretch"`.
- Added tests for page-introduction coverage, indicator readiness, technology search matching, and no-result messaging.

## Evaluation rubric

Scores are strict examiner-style estimates based on the rendered desktop interface, the observed database state, code review, and automated checks. They are not results from a participant usability study.

| Area | Weight | Initial | Final | Evidence and remaining limit |
|---|---:|---:|---:|---|
| Visual design and consistency | 15 | 9 | 11 | Existing dark theme retained; metric labels are clearer in the observed 1280 px desktop view. Tables still use standard Streamlit styling; small-screen behavior was not measured. |
| Navigation and information architecture | 15 | 11 | 12 | All 11 research sections remain available and now describe their task in the page heading. No navigation redesign was needed. |
| Usability and interaction quality | 20 | 11 | 14 | Explorer metadata is labelled; metric meanings are available by help text; search and no-result states are covered by AppTest. Not every individual control was manually operated in a browser. |
| Data visualization and interpretability | 15 | 7 | 8 | Evidence counts and source tables are distinguished. Research time-series charts cannot be shown meaningfully while curated community evidence is empty. |
| Academic credibility and transparency | 15 | 12 | 14 | Indicator gaps, source coverage, geography, and absence of model runs are explicit. The central predictive experiment remains unsupported by current data. |
| Performance, accessibility and responsiveness | 10 | 6 | 7 | PostgreSQL health passed, existing repository caching remains in use, and deprecated width calls were removed. No assistive-technology or mobile-width audit was performed. |
| Presentation readiness | 10 | 6 | 8 | The overview now gives a clearer start and evidence status. The student must present the system as an operational research/data-quality prototype, not a validated predictor. |
| **Total** | **100** | **62** | **74** | The remaining score ceiling is driven mainly by missing research evidence and incomplete accessibility/responsive evaluation. |

## Verification

- `python -m pytest -q`: **85 passed, 16 warnings** in 64.51 seconds.
- The suite rendered every research page against the current database and every synthetic demonstration page. The research search filter and no-result state were tested with Streamlit `AppTest`.
- `python -m compileall -q dashboard tests`: passed.
- `python -m techpulse.cli db-health`: passed; PostgreSQL 18.3, all canonical schemas present, 2 migrations recorded.
- Rendered browser inspection: Executive Overview and Technology Explorer on the live PostgreSQL application. The overview displayed the actual research counts and the Explorer showed labelled metadata and explicit missing-evidence states.
- The 16 remaining warnings are dependency/runtime warnings from Matplotlib/Pyparsing, pytest-asyncio, Joblib, and scikit-learn. No test failure remains.
- Source scan confirmed there are no remaining `use_container_width` calls in `dashboard/`.

## Remaining limitations

- No valid curated Stack Exchange monthly observations; ingestion remains blocked by impossible source rows.
- No verified technology-to-company adoption evidence, Kenya-specific technology observations, validated lifecycle labels, persisted research model run, predictions, or explanations.
- Survey summaries are global/unspecified context, not Kenya evidence or individual-level observations.
- This review did not train a model, repair source data, alter the database, validate a research hypothesis, or conduct formal accessibility testing.
- Some controls were checked through page rendering and focused AppTest coverage; the browser audit did not manually exercise every download, ranking selector, or data-table action.

## Files changed

- `dashboard/page_renderer.py`
- `dashboard/components/ui.py`
- `dashboard/components/tech_detail_panel.py`
- `dashboard/demo_renderer.py`
- `tests/test_dashboard_redesign.py`
- `docs/PROFESSOR_UI_UX_REVIEW.md`

No database changes were made.
