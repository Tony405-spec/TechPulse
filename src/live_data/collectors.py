"""Bounded collectors for GitHub, Stack Exchange, PyPI and npm public APIs."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
PACKAGE_MAP_PATH = ROOT / "data" / "live_package_map.json"
UTC = timezone.utc
TIMEOUT_SECONDS = max(1, int(os.getenv("TECHPULSE_API_TIMEOUT_SECONDS", "15")))
MAX_RETRIES = max(0, int(os.getenv("TECHPULSE_API_MAX_RETRIES", "3")))
MAX_PAGES = min(max(1, int(os.getenv("TECHPULSE_API_MAX_PAGES", "2"))), 10)
PAGE_SIZE = 100


class ApiCollectionError(RuntimeError):
    """A remote API failed or returned a response outside its expected shape."""


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso_utc(value: datetime | pd.Timestamp | str | None = None) -> str:
    parsed = pd.Timestamp(value if value is not None else utc_now())
    if parsed.tzinfo is None:
        parsed = parsed.tz_localize("UTC")
    else:
        parsed = parsed.tz_convert("UTC")
    return parsed.isoformat().replace("+00:00", "Z")


def _retry_delay(response: requests.Response | None, attempt: int) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), 60.0)
            except ValueError:
                pass
        reset = response.headers.get("X-RateLimit-Reset")
        remaining = response.headers.get("X-RateLimit-Remaining")
        if reset and remaining == "0":
            try:
                return min(max(float(reset) - time.time(), 0.0), 60.0)
            except ValueError:
                pass
    return min(2.0**attempt, 30.0)


def get_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    retries: int = MAX_RETRIES,
    timeout: int = TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any] | list[Any]:
    """GET validated JSON with timeouts, bounded retry and rate-limit handling."""
    response: requests.Response | None = None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response_text = getattr(response, "text", "").casefold()
            retryable = response.status_code in {429, 500, 502, 503, 504} or (
                response.status_code == 403
                and (
                    response.headers.get("X-RateLimit-Remaining") == "0"
                    or "Retry-After" in response.headers
                    or "rate limit" in response_text
                    or "secondary rate" in response_text
                )
            )
            if retryable:
                if attempt >= retries:
                    raise ApiCollectionError(f"API rate limit/server response {response.status_code}: {url}")
                delay = _retry_delay(response, attempt)
                LOGGER.warning("Retryable API response %s from %s; waiting %.1fs", response.status_code, url, delay)
                sleep(delay)
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, (dict, list)):
                raise ApiCollectionError(f"API returned {type(payload).__name__}, expected JSON object or array: {url}")
            if isinstance(payload, dict) and payload.get("backoff") is not None:
                delay = min(max(float(payload["backoff"]), 0.0), 60.0)
                if attempt >= retries:
                    raise ApiCollectionError(f"Stack Exchange requested backoff after repeated requests: {url}")
                LOGGER.warning("Stack Exchange backoff requested; waiting %.1fs", delay)
                sleep(delay)
                continue
            if isinstance(payload, dict) and payload.get("error_id"):
                raise ApiCollectionError(
                    f"Stack Exchange API error {payload.get('error_id')}: {payload.get('error_message', 'unknown error')}"
                )
            return payload
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt >= retries:
                raise ApiCollectionError(f"Request failed after {retries + 1} attempts: {url}: {exc}") from exc
            delay = min(2.0**attempt, 30.0)
            LOGGER.warning("Network error for %s; retry %s/%s in %.1fs", url, attempt + 1, retries, delay)
            sleep(delay)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise ApiCollectionError(f"HTTP {status} from {url}") from exc
        except requests.RequestException as exc:
            if attempt >= retries:
                raise ApiCollectionError(f"Request failed after {retries + 1} attempts: {url}: {exc}") from exc
            delay = min(2.0**attempt, 30.0)
            LOGGER.warning("Request error for %s; retry %s/%s in %.1fs", url, attempt + 1, retries, delay)
            sleep(delay)
    raise ApiCollectionError(f"Unable to retrieve API response: {url}")


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _observation(
    technology: str,
    source: str,
    metric: str,
    value: Any = None,
    *,
    value_text: str | None = None,
    source_id: str = "aggregate",
    observed_at: Any = None,
    collected_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    number = _number(value)
    if value is not None and number is None:
        raise ValueError(f"Invalid non-numeric observation value for {source}.{metric}: {value!r}")
    collected = collected_at or utc_now()
    observed = iso_utc(observed_at if observed_at is not None else collected)
    return {
        "technology_id": technology.strip().casefold(),
        "technology": technology.strip(),
        "source": source,
        "metric_name": metric,
        "metric_value": number,
        "metric_text": str(value_text) if value_text is not None else None,
        "observed_at": observed,
        "collected_at": iso_utc(collected),
        "source_identifier": source_id,
        "metadata_json": json.dumps(metadata or {}, sort_keys=True, separators=(",", ":")),
    }


def github_observations(technology: str, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Snapshot a capped sample of matching public repositories (not usage)."""
    session = session or requests.Session()
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    session.headers.update(headers)
    collected = utc_now()
    query = f'"{technology}" in:name,description'
    repos: list[dict[str, Any]] = []
    total_count: int | None = None
    for page in range(1, MAX_PAGES + 1):
        payload = get_json(
            session,
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": "updated", "order": "desc", "per_page": PAGE_SIZE, "page": page},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ApiCollectionError("GitHub search response is missing its items array")
        if total_count is None:
            total_count = _number(payload.get("total_count"))
        page_items = payload["items"]
        if any(not isinstance(item, dict) or not item.get("full_name") for item in page_items):
            raise ApiCollectionError("GitHub search response contains an invalid repository item")
        repos.extend(page_items)
        if not payload.get("incomplete_results") and len(repos) >= min(total_count or 0, MAX_PAGES * PAGE_SIZE):
            break
        if len(page_items) < PAGE_SIZE:
            break
    records: list[dict[str, Any]] = []
    query_id = f"repository-search:{technology.casefold()}"
    sample_meta = {"query": query, "sample_limit": MAX_PAGES * PAGE_SIZE, "sampled_repository_count": len(repos)}
    records.append(_observation(technology, "github", "repositories_matching_query", total_count, source_id=query_id, collected_at=collected, metadata=sample_meta))
    records.append(_observation(technology, "github", "repositories_in_recent_update_sample", len(repos), source_id=query_id, collected_at=collected, metadata=sample_meta))
    pushed_recently = 0
    for repo in repos:
        source_id = str(repo["full_name"])
        common_meta = {"html_url": repo.get("html_url"), "sample_order": len(records)}
        for key, metric in (("stargazers_count", "repository_stars"), ("forks_count", "repository_forks")):
            value = _number(repo.get(key))
            if value is not None:
                records.append(_observation(technology, "github", metric, value, source_id=source_id, collected_at=collected, metadata=common_meta))
        created = repo.get("created_at")
        if created:
            records.append(_observation(technology, "github", "repository_age_days", max((collected - pd.Timestamp(created).to_pydatetime()).total_seconds() / 86400, 0), source_id=source_id, observed_at=collected, collected_at=collected, metadata=common_meta))
        pushed = repo.get("pushed_at")
        if pushed:
            age_days = max((collected - pd.Timestamp(pushed).to_pydatetime()).total_seconds() / 86400, 0)
            pushed_recently += age_days <= 30
            records.append(_observation(technology, "github", "days_since_last_push", age_days, source_id=source_id, observed_at=collected, collected_at=collected, metadata=common_meta))
        language = repo.get("language")
        if language:
            records.append(_observation(technology, "github", "primary_language", source_id=source_id, value_text=str(language), observed_at=collected, collected_at=collected, metadata=common_meta))
    records.append(_observation(technology, "github", "repositories_pushed_last_30d_in_sample", pushed_recently, source_id=query_id, collected_at=collected, metadata=sample_meta))
    return records


def stackexchange_observations(technology: str, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Collect current tag counts and a bounded sample of 30-day questions."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", "TechPulse-Research/1.0 (academic prototype)")
    tag = technology.strip().casefold().replace(" ", "-")
    base = "https://api.stackexchange.com/2.3"
    collected = utc_now()
    common_params = {"site": os.getenv("TECHPULSE_STACKEXCHANGE_SITE", "stackoverflow")}
    api_key = os.getenv("STACKEXCHANGE_KEY", "").strip()
    if api_key:
        common_params["key"] = api_key
    tag_payload = get_json(session, f"{base}/tags/{quote(tag, safe='')}/info", params={**common_params, "pagesize": PAGE_SIZE})
    if not isinstance(tag_payload, dict) or not isinstance(tag_payload.get("items"), list):
        raise ApiCollectionError("Stack Exchange tag response is missing its items array")
    tag_items = tag_payload["items"]
    if not tag_items:
        raise ApiCollectionError(f"Stack Exchange tag '{tag}' was not found")
    tag_count = _number(tag_items[0].get("count"))
    from_date = int((collected - timedelta(days=30)).timestamp())
    questions: list[dict[str, Any]] = []
    max_pages = min(MAX_PAGES, 25)
    for page in range(1, max_pages + 1):
        payload = get_json(
            session,
            f"{base}/questions",
            params={**common_params, "tagged": tag, "fromdate": from_date, "sort": "creation", "order": "desc", "pagesize": PAGE_SIZE, "page": page},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ApiCollectionError("Stack Exchange questions response is missing its items array")
        items = payload["items"]
        if any(not isinstance(item, dict) or not item.get("question_id") or not item.get("creation_date") for item in items):
            raise ApiCollectionError("Stack Exchange response contains an invalid question item")
        questions.extend(items)
        if not payload.get("has_more"):
            break
    metadata = {"tag": tag, "window_days": 30, "sample_limit": PAGE_SIZE * max_pages, "sampled_questions": len(questions), "has_more": bool(payload.get("has_more", False)) if questions else False}
    records = [_observation(technology, "stackexchange", "tag_total_questions", tag_count, source_id=f"tag:{tag}", collected_at=collected, metadata={"site": "stackoverflow"})]
    records.append(_observation(technology, "stackexchange", "questions_created_last_30d_sampled", len(questions), source_id=f"tag:{tag}", collected_at=collected, metadata=metadata))
    records.append(_observation(technology, "stackexchange", "answered_questions_last_30d_sampled", sum(_number(q.get("answer_count")) is not None and _number(q.get("answer_count")) > 0 for q in questions), source_id=f"tag:{tag}", collected_at=collected, metadata=metadata))
    records.append(_observation(technology, "stackexchange", "unanswered_questions_last_30d_sampled", sum(_number(q.get("answer_count")) == 0 for q in questions), source_id=f"tag:{tag}", collected_at=collected, metadata=metadata))
    for question in questions:
        created = datetime.fromtimestamp(int(question["creation_date"]), tz=UTC)
        source_id = f"question:{question['question_id']}"
        question_meta = {"title": question.get("title"), "link": question.get("link"), "tag": tag, "site": "stackoverflow", "question_created_at": iso_utc(created)}
        records.append(_observation(technology, "stackexchange", "question_created", 1, source_id=source_id, observed_at=created, collected_at=collected, metadata=question_meta))
        answers = _number(question.get("answer_count"))
        if answers is not None:
            records.append(_observation(technology, "stackexchange", "question_answer_count", answers, source_id=source_id, observed_at=collected, collected_at=collected, metadata=question_meta))
    return records


def load_package_map(path: Path | None = None) -> dict[str, dict[str, str]]:
    if path is None:
        configured = os.getenv("TECHPULSE_PACKAGE_MAP_PATH", "").strip()
        path = Path(configured) if configured else PACKAGE_MAP_PATH
    if not path.exists():
        return {}
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApiCollectionError(f"Package mapping file is invalid: {path}") from exc
    if not isinstance(mapping, dict):
        raise ApiCollectionError("Package mapping must be a JSON object")
    normalized: dict[str, dict[str, str]] = {}
    for technology, packages in mapping.items():
        if not isinstance(packages, dict):
            continue
        normalized[str(technology).casefold()] = {str(k): str(v) for k, v in packages.items() if k in {"pypi", "npm"} and isinstance(v, str) and v.strip()}
    return normalized


def _package_for(technology: str, registry: str, package_map: dict[str, dict[str, str]] | None) -> str | None:
    mapping = package_map if package_map is not None else load_package_map()
    for key, packages in mapping.items():
        if key.casefold() == technology.casefold():
            return packages.get(registry)
    return None


def pypi_observations(technology: str, session: requests.Session | None = None, package_map: dict[str, dict[str, str]] | None = None) -> list[dict[str, Any]]:
    """Collect PyPI package metadata and release history for an explicitly mapped package."""
    package = _package_for(technology, "pypi", package_map)
    if not package:
        return []
    session = session or requests.Session()
    collected = utc_now()
    payload = get_json(session, f"https://pypi.org/pypi/{quote(package, safe='')}/json")
    if not isinstance(payload, dict) or not isinstance(payload.get("info"), dict) or not isinstance(payload.get("releases"), dict):
        raise ApiCollectionError("PyPI response is missing info or releases metadata")
    info = payload["info"]
    version = info.get("version")
    if not version:
        raise ApiCollectionError("PyPI response is missing the current version")
    releases = payload["releases"]
    recent_cutoff = collected - timedelta(days=30)
    release_dates: dict[str, datetime] = {}
    for release, files in releases.items():
        dates = []
        for file_info in files if isinstance(files, list) else []:
            uploaded = file_info.get("upload_time_iso_8601") or file_info.get("upload_time")
            if uploaded:
                parsed = pd.Timestamp(uploaded).to_pydatetime()
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                dates.append(parsed.astimezone(UTC))
        if dates:
            release_dates[str(release)] = min(dates)
    recent_count = sum(value >= recent_cutoff for value in release_dates.values())
    metadata = {"package": package, "registry": "PyPI", "downloads": "Not provided by the official PyPI JSON API"}
    records = [
        _observation(technology, "pypi", "versions_with_release_files", len(releases), source_id=package, collected_at=collected, metadata=metadata),
        _observation(technology, "pypi", "releases_last_30d", recent_count, source_id=package, collected_at=collected, metadata=metadata),
        _observation(technology, "pypi", "latest_version", value_text=str(version), source_id=package, collected_at=collected, metadata=metadata),
    ]
    for release, uploaded in release_dates.items():
        records.append(_observation(technology, "pypi", "release_published", 1, source_id=f"{package}@{release}", observed_at=uploaded, collected_at=collected, metadata=metadata))
    return records


def npm_observations(technology: str, session: requests.Session | None = None, package_map: dict[str, dict[str, str]] | None = None) -> list[dict[str, Any]]:
    """Collect npm release metadata and official monthly package download counts."""
    package = _package_for(technology, "npm", package_map)
    if not package:
        return []
    session = session or requests.Session()
    session.headers.setdefault("Accept", "application/json")
    collected = utc_now()
    payload = get_json(session, f"https://registry.npmjs.org/{quote(package, safe='')}")
    if not isinstance(payload, dict) or not isinstance(payload.get("time"), dict) or not isinstance(payload.get("dist-tags"), dict):
        raise ApiCollectionError("npm registry response is missing time or dist-tags metadata")
    release_times = payload["time"]
    versions = payload.get("versions", {})
    if not isinstance(versions, dict):
        raise ApiCollectionError("npm registry versions field is invalid")
    latest = payload["dist-tags"].get("latest")
    if not latest:
        raise ApiCollectionError("npm registry response has no latest dist-tag")
    recent_cutoff = collected - timedelta(days=30)
    release_dates: dict[str, datetime] = {}
    for version, published in release_times.items():
        if version in {"created", "modified"} or not published:
            continue
        try:
            release_dates[str(version)] = pd.Timestamp(published).to_pydatetime().astimezone(UTC)
        except (TypeError, ValueError):
            continue
    download_payload = get_json(session, f"https://api.npmjs.org/downloads/point/last-month/{quote(package, safe='')}")
    if not isinstance(download_payload, dict) or download_payload.get("downloads") is None:
        raise ApiCollectionError("npm downloads response is missing downloads")
    downloads = _number(download_payload.get("downloads"))
    if downloads is None:
        raise ApiCollectionError("npm downloads response contains an invalid downloads value")
    metadata = {"package": package, "registry": "npm", "period": download_payload.get("start", "last-month")}
    records = [
        _observation(technology, "npm", "published_versions", len(release_dates), source_id=package, collected_at=collected, metadata=metadata),
        _observation(technology, "npm", "releases_last_30d", sum(value >= recent_cutoff for value in release_dates.values()), source_id=package, collected_at=collected, metadata=metadata),
        _observation(technology, "npm", "downloads_last_month", downloads, source_id=package, collected_at=collected, metadata=metadata),
        _observation(technology, "npm", "latest_version", value_text=str(latest), source_id=package, collected_at=collected, metadata=metadata),
    ]
    if latest in versions:
        repo = versions[latest].get("repository") if isinstance(versions[latest], dict) else None
        if isinstance(repo, dict) and repo.get("url"):
            records.append(_observation(technology, "npm", "repository_url", value_text=str(repo["url"]), source_id=package, collected_at=collected, metadata=metadata))
    for version, published in release_dates.items():
        records.append(_observation(technology, "npm", "release_published", 1, source_id=f"{package}@{version}", observed_at=published, collected_at=collected, metadata=metadata))
    return records


COLLECTORS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "github": github_observations,
    "stackexchange": stackexchange_observations,
    "pypi": pypi_observations,
    "npm": npm_observations,
}
