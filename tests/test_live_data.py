"""Mocked collector and historical persistence tests for live API sources."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from src.live_data import collectors
from src.live_data.storage import append_observations, load_observations


class FakeResponse:
    def __init__(self, payload, status=200, headers=None, text=""):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}

    def get(self, *_args, **_kwargs):
        response = self.responses.pop(0)
        return response


def find_metric(records, metric):
    return [row for row in records if row["metric_name"] == metric]


def test_github_collector_normalizes_repo_activity(monkeypatch):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "total_count": 1,
        "incomplete_results": False,
        "items": [{
            "full_name": "example/python-demo", "html_url": "https://github.com/example/python-demo",
            "stargazers_count": 8, "forks_count": 2, "created_at": now.isoformat(),
            "pushed_at": now.isoformat(), "language": "Python",
        }],
    }
    monkeypatch.setattr(collectors, "get_json", lambda *_a, **_k: payload)
    records = collectors.github_observations("Python", FakeSession([]))
    assert find_metric(records, "repositories_matching_query")[0]["metric_value"] == 1
    assert find_metric(records, "repository_stars")[0]["metric_value"] == 8
    assert find_metric(records, "repository_forks")[0]["source_identifier"] == "example/python-demo"
    assert find_metric(records, "primary_language")[0]["metric_text"] == "Python"


def test_github_rejects_missing_items(monkeypatch):
    monkeypatch.setattr(collectors, "get_json", lambda *_a, **_k: {"total_count": 1})
    with pytest.raises(collectors.ApiCollectionError, match="items array"):
        collectors.github_observations("Python", FakeSession([]))


def test_stackexchange_collects_tag_and_paged_questions(monkeypatch):
    payloads = [
        {"items": [{"name": "python", "count": 1000}]},
        {"items": [{"question_id": 17, "creation_date": 1782864000, "answer_count": 0, "title": "Question"}], "has_more": True},
        {"items": [{"question_id": 18, "creation_date": 1782950400, "answer_count": 2, "title": "Answered question"}], "has_more": False},
    ]
    monkeypatch.setattr(collectors, "get_json", lambda *_a, **_k: payloads.pop(0))
    records = collectors.stackexchange_observations("python", FakeSession([]))
    assert find_metric(records, "tag_total_questions")[0]["metric_value"] == 1000
    assert find_metric(records, "unanswered_questions_last_30d_sampled")[0]["metric_value"] == 1
    event = find_metric(records, "question_created")[0]
    assert event["source_identifier"] == "question:17"
    assert event["observed_at"] < event["collected_at"]
    assert len(find_metric(records, "question_created")) == 2
    assert find_metric(records, "answered_questions_last_30d_sampled")[0]["metric_value"] == 1


def test_stackexchange_api_error_is_reported(monkeypatch):
    monkeypatch.setattr(collectors, "get_json", lambda *_a, **_k: {"items": []})
    with pytest.raises(collectors.ApiCollectionError, match="was not found"):
        collectors.stackexchange_observations("missing-tag", FakeSession([]))


def test_pypi_metadata_and_release_timestamps(monkeypatch):
    payload = {
        "info": {"version": "2.0"},
        "releases": {
            "1.0": [{"upload_time_iso_8601": "2024-01-01T00:00:00Z"}],
            "2.0": [{"upload_time_iso_8601": "2026-10-15T00:00:00Z"}],
        },
    }
    monkeypatch.setattr(collectors, "get_json", lambda *_a, **_k: payload)
    records = collectors.pypi_observations("mongodb", FakeSession([]), {"mongodb": {"pypi": "pymongo"}})
    assert find_metric(records, "latest_version")[0]["metric_text"] == "2.0"
    assert find_metric(records, "releases_last_30d")[0]["metric_value"] >= 1
    assert len(find_metric(records, "release_published")) == 2
    assert "downloads" not in {row["metric_name"] for row in records}


def test_npm_metadata_and_downloads(monkeypatch):
    payloads = [
        {"time": {"created": "2020-01-01T00:00:00.000Z", "1.0.0": "2024-01-01T00:00:00.000Z", "2.0.0": "2026-10-15T00:00:00.000Z"}, "versions": {"2.0.0": {"repository": {"url": "https://github.com/example/package"}}}, "dist-tags": {"latest": "2.0.0"}},
        {"downloads": 12345, "start": "2026-10-01", "end": "2026-10-31"},
    ]
    monkeypatch.setattr(collectors, "get_json", lambda *_a, **_k: payloads.pop(0))
    records = collectors.npm_observations("mongodb", FakeSession([]), {"mongodb": {"npm": "mongodb"}})
    assert find_metric(records, "downloads_last_month")[0]["metric_value"] == 12345
    assert find_metric(records, "latest_version")[0]["metric_text"] == "2.0.0"
    assert len(find_metric(records, "release_published")) == 2


def test_http_retry_for_rate_limit(monkeypatch):
    session = FakeSession([
        FakeResponse({"message": "rate limit"}, status=429, headers={"Retry-After": "0"}),
        FakeResponse({"ok": True}),
    ])
    monkeypatch.setattr(collectors.time, "sleep", lambda _delay: None)
    result = collectors.get_json(session, "https://unit.test/api")
    assert result == {"ok": True}


def test_permanent_http_error_is_reported_without_retry():
    session = FakeSession([FakeResponse({"message": "not found"}, status=404)])
    with pytest.raises(collectors.ApiCollectionError, match="HTTP 404"):
        collectors.get_json(session, "https://unit.test/missing", retries=0)


def test_stack_exchange_backoff_retry(monkeypatch):
    session = FakeSession([FakeResponse({"backoff": 0}), FakeResponse({"items": []})])
    waits = []
    result = collectors.get_json(session, "https://unit.test/api", sleep=waits.append)
    assert result == {"items": []}
    assert waits == [0]


def test_missing_package_mapping_skips_registry(monkeypatch):
    monkeypatch.setattr(collectors, "load_package_map", lambda: {})
    assert collectors.pypi_observations("actionscript") == []
    assert collectors.npm_observations("actionscript") == []


def test_invalid_package_map_is_reported_without_blocking_job(monkeypatch):
    from src.live_data import service

    def invalid_map():
        raise collectors.ApiCollectionError("invalid mapping JSON")

    monkeypatch.setattr(service, "load_package_map", invalid_map)
    monkeypatch.setattr(service, "update_status", lambda *_a, **_k: None)
    result = service.collect_live_data("mongodb", ["pypi", "npm"])
    assert result["pypi"]["status"] == "failed"
    assert result["npm"]["status"] == "failed"


def test_csv_persistence_deduplicates_without_overwriting_history(tmp_path, monkeypatch):
    from src.live_data import storage

    monkeypatch.setattr(storage, "LIVE_DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "CSV_PATH", tmp_path / "observations.csv")
    monkeypatch.setattr(storage, "database_url", lambda: None)
    base = {
        "technology_id": "mongodb", "technology": "mongodb", "source": "github",
        "metric_name": "repository_stars", "metric_value": 10, "metric_text": None,
        "collected_at": "2026-10-30T10:00:00Z", "source_identifier": "example/mongodb",
        "metadata_json": "{}",
    }
    first = {**base, "observed_at": "2026-10-30T10:00:00Z"}
    second = {**base, "metric_value": 12, "observed_at": "2026-10-31T10:00:00Z", "collected_at": "2026-10-31T10:00:00Z"}
    assert append_observations([first, first]) == 1
    assert append_observations([second]) == 1
    loaded = load_observations()
    assert loaded["metric_value"].tolist() == [10, 12]
    assert loaded["observed_at"].tolist() == ["2026-10-30T10:00:00Z", "2026-10-31T10:00:00Z"]


def test_sqlalchemy_persistence_has_unique_history_key(tmp_path):
    pytest.importorskip("sqlalchemy")
    record = {
        "technology_id": "mongodb", "technology": "mongodb", "source": "github",
        "metric_name": "repository_stars", "metric_value": 10.0, "metric_text": None,
        "observed_at": "2026-10-30T10:00:00Z", "collected_at": "2026-10-30T10:00:01Z",
        "source_identifier": "example/mongodb", "metadata_json": "{}",
    }
    url = f"sqlite:///{tmp_path / 'live.sqlite'}"
    assert append_observations([record], url=url) == 1
    assert append_observations([record], url=url) == 0
    loaded = load_observations(url=url)
    assert len(loaded) == 1
    assert loaded.iloc[0]["source_identifier"] == "example/mongodb"


def test_invalid_observation_is_rejected():
    record = {
        "technology_id": "mongodb", "technology": "mongodb", "source": "github",
        "metric_name": "repository_stars", "metric_value": float("nan"), "metric_text": None,
        "observed_at": "2026-10-30T10:00:00Z", "collected_at": "2026-10-30T10:00:01Z",
        "source_identifier": "example/mongodb", "metadata_json": "{}",
    }
    with pytest.raises(ValueError, match="invalid metric"):
        append_observations([record], url="")
