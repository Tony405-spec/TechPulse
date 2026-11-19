"""Evidence-based readiness assessment for the seven SRS indicators.

This module deliberately reports input readiness separately from persisted
calculations. The criteria are conservative and can be unit tested without a
database connection.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def indicator_readiness(facts: dict[str, Any]) -> pd.DataFrame:
    """Return a transparent, data-derived readiness table for one DB snapshot."""
    community = int(facts.get("valid_community_rows") or 0)
    raw_community = int(facts.get("community_rows") or 0)
    months = int(facts.get("valid_community_months") or 0)
    question_rows = int(facts.get("valid_question_rows") or 0)
    adoption = int(facts.get("sourced_adoption_rows") or 0)
    companies = int(facts.get("sourced_adoption_companies") or 0)
    failed = int(facts.get("stackexchange_failed_runs") or 0) + int(
        facts.get("stackexchange_critical_failures") or 0
    )
    survey = int(facts.get("valid_survey_rows") or 0)

    rows: list[dict[str, str]] = []

    def add(name: str, needed: str, okay: bool, period: str, missing: str,
            evidence_count: int, community_dependent: bool = False) -> None:
        status = (
            "Available" if okay else
            "Invalid source data" if community_dependent and (raw_community > community or (failed and community == 0)) else
            "Partially available" if evidence_count > 0 else
            "Unavailable"
        )
        rows.append({
            "Research indicator": name,
            "Input readiness": status,
            "Evidence period": period,
            "Required inputs": needed,
            "Missing evidence / limitation": "None identified in readiness checks." if okay else missing,
        })

    community_period = _period(facts.get("community_start"), facts.get("community_end"))
    adoption_period = _period(facts.get("adoption_start"), facts.get("adoption_end"))
    survey_period = _period(facts.get("survey_start_year"), facts.get("survey_end_year"))
    add("Technology Health Score", "Validated community, survey and other specified component inputs with an approved formula.", community >= 12 and survey > 0, f"Community {community_period}; survey {survey_period}", "A valid community history and documented component formula are required; current survey rows are not a substitute for missing components.", community + survey, True)
    add("Growth Momentum Index", "Valid, dated monthly community observations across a sufficient trend window.", community >= 12 and months >= 12, community_period, "At least 12 valid monthly observations across 12 distinct months are required; the Stack Exchange source is blocked if its validation failed.", community, True)
    add("Question Quality Score", "Curated question-level records with dated outcomes and an approved quality formula.", question_rows > 0, community_period, "No validated question-level outcome records or approved formula are available.", question_rows, True)
    add("Company Diversity Score", "Dated, source-linked company-to-technology adoption evidence and an approved diversity formula.", adoption > 0 and companies >= 2, adoption_period, "Company profiles do not establish adoption; dated, source-linked evidence from multiple companies is required.", adoption)
    add("Sentiment Delta", "Time-aligned developer satisfaction observations in comparable periods.", False, survey_period, "The survey table contains usage, interest and admiration shares, not a satisfaction score; no comparable satisfaction series is available.", 0)
    add("Adoption Velocity", "Verified timestamped adoption events across at least four quarterly periods.", adoption >= 4 and _quarter_span(facts.get("adoption_start"), facts.get("adoption_end")) >= 4, adoption_period, "Four quarterly periods of verified, dated adoption events are required; company directory rows are not adoption events.", adoption)
    add("Community Decay Rate", "Valid monthly community observations covering recent and prior six-month windows.", community >= 12 and months >= 12, community_period, "Two valid six-month community windows are required; no valid time-aligned series is currently established.", community, True)
    return pd.DataFrame(rows)


def _period(start: Any, end: Any) -> str:
    if start is None or pd.isna(start):
        return "Unavailable"
    if end is None or pd.isna(end):
        return str(start)
    return f"{start} to {end}"


def _quarter_span(start: Any, end: Any) -> int:
    if start is None or end is None or pd.isna(start) or pd.isna(end):
        return 0
    a, b = pd.Timestamp(start), pd.Timestamp(end)
    return max(0, (b.year - a.year) * 4 + b.quarter - a.quarter + 1)
