import pandas as pd

from src.data_ingestion import _validate_frame
from src.eda import _date_coverage, _profile


def test_profile_handles_empty_source_frame(tmp_path):
    result = _profile("empty_source", pd.DataFrame(), tmp_path)
    assert result["rows"] == 0
    assert result["columns"] == 0
    assert result["numeric_summary"] == {}
    assert result["class_distribution"]["status"].startswith("not evaluated")


def test_survey_year_is_reported_as_year_not_unix_timestamp():
    frame = pd.DataFrame({"survey_year": [2021, 2024]})
    assert _date_coverage(frame)["survey_year"]["start_year"] == 2021
    assert _date_coverage(frame)["survey_year"]["end_year"] == 2024
    assert _validate_frame("dev_sentiment", frame)["date_ranges"]["survey_year"] == {
        "earliest_year": "2021",
        "latest_year": "2024",
    }
