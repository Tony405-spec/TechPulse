"""Acquire Stack Overflow Developer Survey technology usage data."""

from __future__ import annotations

import csv
import json
import time
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.common import BASE_DIR, DATA_DIR, OUTPUTS_DIR, ensure_directories
from src.technology_normalization import normalize_technology_name

SURVEY_YEARS = (2021, 2022, 2023, 2024)
MEDIA_BASE_URL = "https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive"
SOURCE_REPO_URL = "https://github.com/StackExchange/Survey"
SURVEY_SITE_URL = "https://survey.stackoverflow.co/"
RAW_DIR = DATA_DIR / "raw_external" / "stackoverflow_survey"
DERIVED_PATH = DATA_DIR / "developer_survey_usage.csv"
PROVENANCE_PATH = OUTPUTS_DIR / "data_provenance.json"

TECHNOLOGY_COLUMNS = {
    "LanguageHaveWorkedWith": ("Language", "worked_with"),
    "LanguageWantToWorkWith": ("Language", "want_to_work_with"),
    "DatabaseHaveWorkedWith": ("Database", "worked_with"),
    "DatabaseWantToWorkWith": ("Database", "want_to_work_with"),
    "PlatformHaveWorkedWith": ("Platform", "worked_with"),
    "PlatformWantToWorkWith": ("Platform", "want_to_work_with"),
    "WebframeHaveWorkedWith": ("Web Framework", "worked_with"),
    "WebframeWantToWorkWith": ("Web Framework", "want_to_work_with"),
    "MiscTechHaveWorkedWith": ("Other Framework/Library", "worked_with"),
    "MiscTechWantToWorkWith": ("Other Framework/Library", "want_to_work_with"),
    "ToolsTechHaveWorkedWith": ("Tool", "worked_with"),
    "ToolsTechWantToWorkWith": ("Tool", "want_to_work_with"),
}

ADMIRATION_COLUMNS = {
    "LanguageAdmired": ("Language", "admired"),
    "DatabaseAdmired": ("Database", "admired"),
    "PlatformAdmired": ("Platform", "admired"),
    "WebframeAdmired": ("Web Framework", "admired"),
    "MiscTechAdmired": ("Other Framework/Library", "admired"),
    "ToolsTechAdmired": ("Tool", "admired"),
}


@dataclass(frozen=True)
class DownloadedFile:
    """Metadata for one downloaded public file."""

    year: int
    kind: str
    url: str
    path: str
    bytes: int


def _download(url: str, path: Path, refresh: bool = False) -> DownloadedFile:
    """Download one URL to the local raw cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not refresh:
        return DownloadedFile(int(path.parent.name), path.stem, url, str(path), path.stat().st_size)
    request = urllib.request.Request(url, headers={"User-Agent": "TechPulse academic data acquisition"})
    with urllib.request.urlopen(request, timeout=120) as response:
        path.write_bytes(response.read())
    time.sleep(0.5)
    return DownloadedFile(int(path.parent.name), path.stem, url, str(path), path.stat().st_size)


def download_survey_files(years: tuple[int, ...] = SURVEY_YEARS, refresh: bool = False) -> list[DownloadedFile]:
    """Download official Stack Overflow survey result and schema files."""
    ensure_directories()
    downloaded: list[DownloadedFile] = []
    for year in years:
        for kind in ("results", "schema"):
            url = f"{MEDIA_BASE_URL}/{year}/{kind}.csv"
            downloaded.append(_download(url, RAW_DIR / str(year) / f"{kind}.csv", refresh=refresh))
    return downloaded


def _split_multi(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def _aggregate_year(path: Path, year: int, chunksize: int = 25000) -> pd.DataFrame:
    """Aggregate one survey results file to technology-year rows."""
    counts: dict[tuple[str, str], dict[str, int]] = {}
    respondent_count = 0
    selected = set(TECHNOLOGY_COLUMNS) | set(ADMIRATION_COLUMNS)
    reader = pd.read_csv(
        path,
        usecols=lambda column: column == "ResponseId" or column in selected,
        chunksize=chunksize,
    )
    for frame in reader:
        respondent_count += int(len(frame))
        for column, (category, signal) in {**TECHNOLOGY_COLUMNS, **ADMIRATION_COLUMNS}.items():
            if column not in frame.columns:
                continue
            for value in frame[column].dropna():
                for raw_name in _split_multi(value):
                    technology = normalize_technology_name(raw_name)
                    key = (technology, category)
                    counts.setdefault(key, {"worked_with": 0, "want_to_work_with": 0, "admired": 0})
                    counts[key][signal] += 1
    rows: list[dict[str, Any]] = []
    for (technology, category), values in counts.items():
        rows.append(
            {
                "technology": technology,
                "technology_name": technology,
                "category": category,
                "survey_year": year,
                "respondent_count": respondent_count,
                "worked_with_count": values["worked_with"],
                "want_to_work_with_count": values["want_to_work_with"],
                "admired_count": values["admired"],
                "developer_usage_share": values["worked_with"] / max(respondent_count, 1),
                "developer_interest_share": values["want_to_work_with"] / max(respondent_count, 1),
                "developer_admiration_share": values["admired"] / max(respondent_count, 1),
                "source_type": "official_stackoverflow_developer_survey",
            }
        )
    return pd.DataFrame(rows)


def build_developer_survey_usage(years: tuple[int, ...] = SURVEY_YEARS, refresh: bool = False) -> pd.DataFrame:
    """Download and aggregate official survey technology usage data."""
    downloaded = download_survey_files(years=years, refresh=refresh)
    frames = [_aggregate_year(RAW_DIR / str(year) / "results.csv", year) for year in years]
    usage = pd.concat(frames, ignore_index=True)
    usage = usage.sort_values(["technology_name", "survey_year"]).reset_index(drop=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    usage.to_csv(DERIVED_PATH, index=False, quoting=csv.QUOTE_MINIMAL)
    _write_provenance(usage, downloaded)
    return usage


def _write_provenance(usage: pd.DataFrame, downloaded: list[DownloadedFile]) -> None:
    """Persist reproducible provenance for acquired survey data."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    downloaded_files = []
    for download in downloaded:
        item = dict(download.__dict__)
        try:
            item["path"] = str(Path(item["path"]).resolve().relative_to(BASE_DIR))
        except ValueError:
            pass
        downloaded_files.append(item)
    provenance = {
        "access_date": date.today().isoformat(),
        "sources": [
            {
                "source_name": "Stack Overflow Developer Survey",
                "source_url": SURVEY_SITE_URL,
                "repository_url": SOURCE_REPO_URL,
                "license": "Open Database License (ODbL) 1.0 for data; Database Contents License (DbCL) 1.0 for contents",
                "description": "Official annual survey responses aggregated into technology-year usage, interest, and admiration shares.",
                "publication_update_date": "Yearly survey releases; exact release dates are maintained by Stack Exchange in the source repository.",
                "fields_used": sorted(set(TECHNOLOGY_COLUMNS) | set(ADMIRATION_COLUMNS)),
                "transformations": [
                    "Downloaded official results.csv/schema.csv files from StackExchange/Survey via GitHub media URLs.",
                    "Split semicolon-delimited multi-select technology columns.",
                    "Applied conservative technology alias normalization.",
                    "Aggregated respondent counts to technology-year shares.",
                ],
                "limitations": [
                    "Survey respondents are self-selected and not a census of all developers.",
                    "Question names and available technology columns differ by year.",
                    "Usage/share is a developer-survey signal, not direct enterprise adoption.",
                ],
                "data_type": "observed public survey responses aggregated to derived yearly shares",
            }
        ],
        "downloaded_files": downloaded_files,
        "derived_outputs": [
            {
                "path": str(DERIVED_PATH.relative_to(BASE_DIR)),
                "rows": int(len(usage)),
                "technologies": int(usage["technology_name"].nunique()),
                "earliest_year": int(usage["survey_year"].min()),
                "latest_year": int(usage["survey_year"].max()),
            }
        ],
    }
    PROVENANCE_PATH.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
