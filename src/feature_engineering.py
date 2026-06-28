"""Feature engineering for the TechPulse predictive matrix."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.common import (
    CATEGORY_COLUMN,
    DATA_DIR,
    FEATURE_COLUMNS,
    LOGS_DIR,
    OUTPUTS_DIR,
    TECH_COLUMN,
    ensure_directories,
    normalise_name,
)

LOGGER = logging.getLogger(__name__)


def _configure_logger(log_path: Path | None = None) -> logging.Logger:
    """Configure and return the feature engineering logger.

    Args:
        log_path: Optional log file path.

    Returns:
        Configured logger.
    """
    ensure_directories()
    target = log_path or LOGS_DIR / "feature_engineering.log"
    logger = logging.getLogger("techpulse.feature_engineering")
    logger.setLevel(logging.INFO)
    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        handler = logging.FileHandler(target, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def _column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first matching column using tolerant name matching.

    Args:
        frame: DataFrame to inspect.
        candidates: Candidate column names.

    Returns:
        Matching column name or None.
    """
    lookup = {normalise_name(column): column for column in frame.columns}
    for candidate in candidates:
        match = lookup.get(normalise_name(candidate))
        if match:
            return match
    return None


def _tech_col(frame: pd.DataFrame) -> str | None:
    """Find a technology identifier column.

    Args:
        frame: DataFrame to inspect.

    Returns:
        Technology column name or None.
    """
    return _column(frame, ["technology_name", "technology", "tag", "tech", "name"])


def _date_col(frame: pd.DataFrame) -> str | None:
    """Find a date-like column.

    Args:
        frame: DataFrame to inspect.

    Returns:
        Date column name or None.
    """
    return _column(
        frame,
        ["date_col", "creation_date", "created_at", "question_date", "date", "adoption_date"],
    )


def _minmax(series: pd.Series) -> pd.Series:
    """Min-max normalise a series to [0, 1].

    Args:
        series: Numeric values.

    Returns:
        Normalised values.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    min_value = numeric.min()
    max_value = numeric.max()
    if pd.isna(min_value) or pd.isna(max_value):
        return numeric
    if np.isclose(max_value, min_value):
        return numeric.where(numeric.isna(), 0.5)
    return (numeric - min_value) / (max_value - min_value)


def _base_technologies(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the one-row-per-technology base table.

    Args:
        datasets: Source datasets.

    Returns:
        DataFrame with technology names and categories.
    """
    names: set[str] = set()
    categories: dict[str, str] = {}
    for frame in datasets.values():
        tech = _tech_col(frame)
        if tech is None:
            continue
        for value in frame[tech].dropna().astype(str):
            names.add(value)
        category = _column(frame, ["category", "technology_category", "type"])
        if category:
            for _, row in frame[[tech, category]].dropna(subset=[tech]).iterrows():
                categories[str(row[tech])] = str(row[category]) if pd.notna(row[category]) else "Other"
    return pd.DataFrame(
        {
            TECH_COLUMN: sorted(names),
            CATEGORY_COLUMN: [categories.get(name, "Other") for name in sorted(names)],
        }
    )


def _so_features(so_questions: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    """Compute Stack Overflow community features.

    Args:
        so_questions: Stack Overflow question rows.
        logger: Feature engineering logger.

    Returns:
        DataFrame keyed by technology name.
    """
    tech = _tech_col(so_questions)
    date = _date_col(so_questions)
    if tech is None or date is None:
        logger.warning("SO features missing technology or date column.")
        return pd.DataFrame(columns=[TECH_COLUMN])

    frame = so_questions.copy()
    frame[date] = pd.to_datetime(frame[date], errors="coerce")
    reference_date = frame[date].max()
    logger.info("SO REFERENCE_DATE=%s from %s.%s", reference_date, "so_questions", date)
    answer_col = _column(frame, ["answer_count", "answers", "num_answers"])
    closed_col = _column(frame, ["is_closed", "closed", "closed_date"])
    frame["_answers"] = pd.to_numeric(frame[answer_col], errors="coerce") if answer_col else np.nan
    if closed_col:
        frame["_closed"] = frame[closed_col].notna()
        if frame[closed_col].dropna().isin([0, 1, True, False]).all():
            frame["_closed"] = frame[closed_col].astype(bool)
    else:
        frame["_closed"] = False

    rows: list[dict[str, float | str]] = []
    for technology, group in frame.dropna(subset=[tech, date]).groupby(tech):
        recent_3 = group[group[date] >= reference_date - pd.DateOffset(months=3)]
        recent_12 = group[group[date] >= reference_date - pd.DateOffset(months=12)]
        prev_6 = group[
            (group[date] < reference_date - pd.DateOffset(months=6))
            & (group[date] >= reference_date - pd.DateOffset(months=12))
        ]
        recent_6 = group[group[date] >= reference_date - pd.DateOffset(months=6)]
        monthly = group.set_index(date).resample("MS").size()
        rows.append(
            {
                TECH_COLUMN: str(technology),
                "growth_momentum_index": len(recent_3) / max(len(recent_12), 1),
                "question_quality_score": group["_answers"].mean()
                * (1 - group["_closed"].mean()),
                "community_decay_rate": max(
                    (len(prev_6) - len(recent_6)) / max(len(prev_6), 1), 0
                ),
                "so_volume_trend_slope": _trend_slope(monthly),
                "r_squared": _trend_r_squared(monthly),
                "so_months_observed": int(monthly.shape[0]),
                "so_question_volume": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def _trend_slope(series: pd.Series) -> float:
    """Compute a linear trend slope for a monthly series.

    Args:
        series: Time-indexed monthly values.

    Returns:
        Linear regression slope, or 0.0 with insufficient data.
    """
    if len(series) < 2:
        return 0.0
    x_values = np.arange(len(series), dtype=float)
    return float(np.polyfit(x_values, series.to_numpy(dtype=float), 1)[0])


def _trend_r_squared(series: pd.Series) -> float:
    """Compute R-squared for a simple monthly trend line.

    Args:
        series: Time-indexed monthly values.

    Returns:
        R-squared value.
    """
    if len(series) < 2 or np.isclose(series.var(), 0):
        return 0.0
    x_values = np.arange(len(series), dtype=float)
    y_values = series.to_numpy(dtype=float)
    slope, intercept = np.polyfit(x_values, y_values, 1)
    predicted = slope * x_values + intercept
    ss_res = float(np.sum((y_values - predicted) ** 2))
    ss_tot = float(np.sum((y_values - np.mean(y_values)) ** 2))
    return 0.0 if np.isclose(ss_tot, 0) else 1 - ss_res / ss_tot


def _enterprise_features(
    stacks: pd.DataFrame, profiles: pd.DataFrame, logger: logging.Logger
) -> pd.DataFrame:
    """Compute enterprise adoption features.

    Args:
        stacks: Fortune 500 stack rows.
        profiles: Company profile rows.
        logger: Feature engineering logger.

    Returns:
        DataFrame keyed by technology name.
    """
    tech = _tech_col(stacks)
    company = _column(stacks, ["company_id", "company", "company_name"])
    if tech is None or company is None:
        logger.warning("Enterprise features missing technology or company column.")
        return pd.DataFrame(columns=[TECH_COLUMN])
    sector = _column(profiles, ["sector", "industry"])
    profile_company = _column(profiles, ["company_id", "company", "company_name"])
    merged = stacks.copy()
    if sector and profile_company:
        merged = merged.merge(
            profiles[[profile_company, sector]],
            left_on=company,
            right_on=profile_company,
            how="left",
        )
    date = _date_col(stacks)
    rows = []
    for technology, group in merged.groupby(tech):
        row: dict[str, float | str] = {
            TECH_COLUMN: str(technology),
            "company_diversity_score": float(group[sector].nunique()) if sector else np.nan,
        }
        if date:
            adoption_dates = pd.to_datetime(group[date], errors="coerce")
            reference_date = adoption_dates.max()
            logger.info("Enterprise REFERENCE_DATE=%s from fortune500_stacks.%s", reference_date, date)
            trailing = group[adoption_dates >= reference_date - pd.DateOffset(months=12)]
            quarters = pd.to_datetime(trailing[date], errors="coerce").dt.to_period("Q")
            row["adoption_velocity"] = quarters.groupby(quarters).size().mean()
        else:
            row["adoption_velocity"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _sentiment_features(sentiment: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    """Compute developer sentiment delta by technology.

    Args:
        sentiment: Developer sentiment rows.
        logger: Feature engineering logger.

    Returns:
        DataFrame keyed by technology name.
    """
    tech = _tech_col(sentiment)
    score = _column(sentiment, ["satisfaction_score", "satisfaction", "sentiment_score"])
    period = _column(sentiment, ["survey_year", "year", "period", "date_col", "date"])
    if tech is None or score is None or period is None:
        logger.warning("Sentiment delta missing technology, score, or period column.")
        return pd.DataFrame(columns=[TECH_COLUMN])
    frame = sentiment.copy()
    frame["_score"] = pd.to_numeric(frame[score], errors="coerce")
    frame["_period"] = pd.to_datetime(frame[period].astype(str), errors="coerce")
    if frame["_period"].isna().all():
        frame["_period"] = pd.to_numeric(frame[period], errors="coerce")
    rows = []
    for technology, group in frame.dropna(subset=["_score", "_period"]).groupby(tech):
        ordered = group.sort_values("_period")
        rows.append(
            {
                TECH_COLUMN: str(technology),
                "sentiment_delta": float(ordered["_score"].iloc[-1] - ordered["_score"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def compute_feature_matrix(
    datasets: dict[str, pd.DataFrame],
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Compute and persist all seven normalised predictive features.

    Args:
        datasets: Source table DataFrames keyed by required dataset name.
        output_path: Optional CSV output path.

    Returns:
        Feature matrix with one row per technology.
    """
    logger = _configure_logger()
    ensure_directories()
    output_path = output_path or DATA_DIR / "feature_matrix.csv"
    features = _base_technologies(datasets)

    parts = [
        _so_features(datasets.get("so_questions", pd.DataFrame()), logger),
        _enterprise_features(
            datasets.get("fortune500_stacks", pd.DataFrame()),
            datasets.get("company_profiles", pd.DataFrame()),
            logger,
        ),
        _sentiment_features(datasets.get("dev_sentiment", pd.DataFrame()), logger),
    ]
    for part in parts:
        if not part.empty:
            features = features.merge(part, on=TECH_COLUMN, how="left")

    raw_features = features[FEATURE_COLUMNS].copy() if set(FEATURE_COLUMNS).issubset(features.columns) else None
    if raw_features is None:
        for column in FEATURE_COLUMNS:
            if column not in features:
                logger.warning("%s missing; setting individual values to NaN.", column)
                features[column] = np.nan

    health_parts = [
        features["growth_momentum_index"],
        features["question_quality_score"],
        features["company_diversity_score"],
        features["sentiment_delta"],
        1 - features["community_decay_rate"],
    ]
    features["technology_health_score"] = pd.concat(health_parts, axis=1).mean(axis=1)

    missing_counts = features[FEATURE_COLUMNS].isna().sum(axis=1)
    excluded = features.loc[missing_counts > 3, TECH_COLUMN].tolist()
    for technology in excluded:
        logger.info("Excluding %s because more than 3 of 7 features are missing.", technology)
    features = features.loc[missing_counts <= 3].copy()
    for column in FEATURE_COLUMNS:
        missing = int(features[column].isna().sum())
        if missing:
            logger.info("%s has %s missing values retained as NaN.", column, missing)
        features[column] = _minmax(features[column])

    features.to_csv(output_path, index=False)
    (OUTPUTS_DIR / "feature_schema.json").write_text(
        pd.Series(FEATURE_COLUMNS).to_json(orient="values"), encoding="utf-8"
    )
    return features
