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
    OBSERVATION_MONTH_COLUMN,
    OUTPUTS_DIR,
    TARGET_LEAKAGE_COLUMNS,
    TECH_COLUMN,
    ensure_directories,
    normalise_name,
)
from src.technology_normalization import normalize_technology_name

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


def _category_lookup(datasets: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Return technology-to-category values where source data provides them."""
    lookup: dict[str, str] = {}
    for frame in datasets.values():
        tech = _tech_col(frame)
        category = _column(frame, ["category", "technology_category", "type"])
        if tech is None or category is None:
            continue
        for _, row in frame[[tech, category]].dropna(subset=[tech]).iterrows():
            lookup[str(row[tech])] = str(row[category]) if pd.notna(row[category]) else "Other"
    return lookup


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
    volume_col = _column(frame, ["question_count", "questions", "count"])
    unanswered_col = _column(frame, ["unanswered_count", "unanswered"])
    unanswered_pct_col = _column(frame, ["unanswered_pct", "unanswered_percentage"])
    frame["_volume"] = (
        pd.to_numeric(frame[volume_col], errors="coerce").fillna(0).clip(lower=0)
        if volume_col
        else 1.0
    )
    frame["_answers"] = pd.to_numeric(frame[answer_col], errors="coerce") if answer_col else np.nan
    if answer_col is None and unanswered_col:
        frame["_answers"] = (
            frame["_volume"] - pd.to_numeric(frame[unanswered_col], errors="coerce").fillna(0)
        ).clip(lower=0)
    if closed_col:
        frame["_closed"] = frame[closed_col].notna()
        if frame[closed_col].dropna().isin([0, 1, True, False]).all():
            frame["_closed"] = frame[closed_col].astype(bool)
    elif unanswered_pct_col:
        raw_rate = pd.to_numeric(frame[unanswered_pct_col], errors="coerce").fillna(0)
        frame["_closed"] = raw_rate.clip(lower=0, upper=100) / 100
    else:
        frame["_closed"] = 0.0

    rows: list[dict[str, float | str]] = []
    for technology, group in frame.dropna(subset=[tech, date]).groupby(tech):
        recent_3 = group[group[date] >= reference_date - pd.DateOffset(months=3)]
        recent_12 = group[group[date] >= reference_date - pd.DateOffset(months=12)]
        prev_6 = group[
            (group[date] < reference_date - pd.DateOffset(months=6))
            & (group[date] >= reference_date - pd.DateOffset(months=12))
        ]
        recent_6 = group[group[date] >= reference_date - pd.DateOffset(months=6)]
        monthly = group.set_index(date)["_volume"].resample("MS").sum()
        recent_3_volume = float(recent_3["_volume"].sum())
        recent_12_volume = float(recent_12["_volume"].sum())
        prev_6_volume = float(prev_6["_volume"].sum())
        recent_6_volume = float(recent_6["_volume"].sum())
        rows.append(
            {
                TECH_COLUMN: str(technology),
                "growth_momentum_index": recent_3_volume / max(recent_12_volume, 1),
                "question_quality_score": group["_answers"].mean()
                * (1 - group["_closed"].mean()),
                "community_decay_rate": max(
                    (prev_6_volume - recent_6_volume) / max(prev_6_volume, 1), 0
                ),
                "so_volume_trend_slope": _trend_slope(monthly),
                "r_squared": _trend_r_squared(monthly),
                "so_months_observed": int(monthly.shape[0]),
                "so_question_volume": int(group["_volume"].sum()),
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


def _static_signal_maps(
    datasets: dict[str, pd.DataFrame], logger: logging.Logger
) -> tuple[pd.DataFrame, dict[str, float], dict[str, float], dict[str, float]]:
    """Compute non-temporal proxy signals keyed by technology.

    These signals are kept out of the target calculation and are used only as
    model features. In local development mode they may be demo proxies, which is
    documented by the ingestion manifest.
    """
    enterprise = _enterprise_features(
        datasets.get("fortune500_stacks", pd.DataFrame()),
        datasets.get("company_profiles", pd.DataFrame()),
        logger,
    )
    sentiment = _sentiment_features(datasets.get("dev_sentiment", pd.DataFrame()), logger)
    base = pd.DataFrame({TECH_COLUMN: sorted(set(_category_lookup(datasets)))})
    for part in (enterprise, sentiment):
        if not part.empty:
            if base.empty:
                base = part[[TECH_COLUMN]].drop_duplicates()
            base = base.merge(part, on=TECH_COLUMN, how="outer")
    if base.empty:
        base = pd.DataFrame(columns=[TECH_COLUMN])
    diversity = dict(zip(base.get(TECH_COLUMN, []), pd.to_numeric(base.get("company_diversity_score", pd.Series(dtype=float)), errors="coerce")))
    adoption = dict(zip(base.get(TECH_COLUMN, []), pd.to_numeric(base.get("adoption_velocity", pd.Series(dtype=float)), errors="coerce")))
    sentiment_delta = dict(zip(base.get(TECH_COLUMN, []), pd.to_numeric(base.get("sentiment_delta", pd.Series(dtype=float)), errors="coerce")))
    return base, diversity, adoption, sentiment_delta


def _survey_signal_lookup(sentiment: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Prepare developer-survey signal history by normalized technology name."""
    tech = _tech_col(sentiment)
    score = _column(
        sentiment,
        [
            "developer_usage_share",
            "usage_share",
            "satisfaction_score",
            "satisfaction",
            "sentiment_score",
        ],
    )
    period = _column(sentiment, ["survey_year", "year", "period", "date_col", "date"])
    if tech is None or score is None or period is None:
        return {}
    frame = sentiment[[tech, score, period]].copy()
    frame["_tech_key"] = frame[tech].map(lambda value: normalise_name(normalize_technology_name(value)))
    frame["_score"] = pd.to_numeric(frame[score], errors="coerce")
    frame["_year"] = pd.to_numeric(frame[period], errors="coerce")
    frame = frame.dropna(subset=["_tech_key", "_score", "_year"])
    return {key: group.sort_values("_year") for key, group in frame.groupby("_tech_key")}


def _sentiment_delta_as_of(
    lookup: dict[str, pd.DataFrame], technology: str, observation_year: int
) -> float:
    """Return survey usage-share delta available by an observation year."""
    key = normalise_name(normalize_technology_name(technology))
    history = lookup.get(key)
    if history is None:
        return np.nan
    available = history.loc[history["_year"] <= observation_year]
    if len(available) < 2:
        return np.nan
    return float(available["_score"].iloc[-1] - available["_score"].iloc[0])


def _enterprise_as_of(
    datasets: dict[str, pd.DataFrame], technology: str, observation_month: pd.Timestamp
) -> tuple[float, float]:
    """Compute enterprise proxy signals using only dates up to observation month."""
    stacks = datasets.get("fortune500_stacks", pd.DataFrame())
    profiles = datasets.get("company_profiles", pd.DataFrame())
    tech = _tech_col(stacks)
    date = _date_col(stacks)
    company = _column(stacks, ["company_id", "company", "company_name"])
    if tech is None or date is None or company is None:
        return np.nan, np.nan
    group = stacks.loc[stacks[tech].astype(str) == str(technology)].copy()
    if group.empty:
        return np.nan, np.nan
    group[date] = pd.to_datetime(group[date], errors="coerce")
    observed = group.loc[group[date] <= observation_month].copy()
    if observed.empty:
        return np.nan, np.nan
    sector = _column(profiles, ["sector", "industry"])
    profile_company = _column(profiles, ["company_id", "company", "company_name"])
    diversity = np.nan
    if sector and profile_company:
        merged = observed.merge(
            profiles[[profile_company, sector]],
            left_on=company,
            right_on=profile_company,
            how="left",
        )
        diversity = float(merged[sector].nunique())
    trailing = observed.loc[observed[date] >= observation_month - pd.DateOffset(months=12)]
    quarters = pd.to_datetime(trailing[date], errors="coerce").dt.to_period("Q")
    velocity = float(quarters.groupby(quarters).size().mean()) if not trailing.empty else 0.0
    return diversity, velocity


def _temporal_so_panel(
    datasets: dict[str, pd.DataFrame],
    logger: logging.Logger,
    history_months: int = 6,
    future_months: int = 3,
) -> pd.DataFrame:
    """Build technology-month features from past data only.

    Rows represent an observation month. Feature values are computed from
    monthly Stack Overflow activity up to and including that month. Future
    volume fields are retained only for downstream target construction and are
    explicitly excluded from model features.
    """
    so_questions = datasets.get("so_questions", pd.DataFrame())
    tech = _tech_col(so_questions)
    date = _date_col(so_questions)
    if tech is None or date is None:
        logger.warning("Temporal panel skipped because SO technology/date columns are missing.")
        return pd.DataFrame()

    frame = so_questions.copy()
    frame[date] = pd.to_datetime(frame[date], errors="coerce")
    frame = frame.dropna(subset=[tech, date])
    if frame.empty:
        logger.warning("Temporal panel skipped because SO data has no valid dated rows.")
        return pd.DataFrame()
    volume_col = _column(frame, ["question_count", "questions", "count"])
    answer_col = _column(frame, ["answer_count", "answers", "num_answers"])
    unanswered_col = _column(frame, ["unanswered_count", "unanswered"])
    unanswered_pct_col = _column(frame, ["unanswered_pct", "unanswered_percentage"])
    frame["_volume"] = (
        pd.to_numeric(frame[volume_col], errors="coerce").fillna(0).clip(lower=0)
        if volume_col
        else 1.0
    )
    if answer_col:
        frame["_answers"] = pd.to_numeric(frame[answer_col], errors="coerce").fillna(0)
    elif unanswered_col:
        frame["_answers"] = (
            frame["_volume"] - pd.to_numeric(frame[unanswered_col], errors="coerce").fillna(0)
        ).clip(lower=0)
    else:
        frame["_answers"] = frame["_volume"]
    if unanswered_pct_col:
        frame["_unanswered"] = pd.to_numeric(frame[unanswered_pct_col], errors="coerce").fillna(0)
        frame["_unanswered"] = np.where(frame["_unanswered"] > 1, frame["_unanswered"] / 100, frame["_unanswered"])
    elif unanswered_col:
        frame["_unanswered"] = pd.to_numeric(frame[unanswered_col], errors="coerce").fillna(0) / frame["_volume"].replace(0, np.nan)
    else:
        frame["_unanswered"] = 0.0
    frame["_month"] = frame[date].dt.to_period("M").dt.to_timestamp()

    categories = _category_lookup(datasets)
    survey_lookup = _survey_signal_lookup(datasets.get("dev_sentiment", pd.DataFrame()))
    rows: list[dict[str, object]] = []
    for technology, group in frame.groupby(tech):
        monthly = (
            group.groupby("_month", as_index=True)
            .agg(volume=("_volume", "sum"), answers=("_answers", "sum"), unanswered_rate=("_unanswered", "mean"))
            .sort_index()
        )
        full_index = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
        monthly = monthly.reindex(full_index, fill_value=0.0)
        if len(monthly) < history_months + future_months + 1:
            continue
        for position in range(history_months - 1, len(monthly) - future_months):
            obs_month = monthly.index[position]
            history = monthly.iloc[position - history_months + 1: position + 1]
            recent = history.tail(3)
            previous = history.head(max(history_months - 3, 1))
            future = monthly.iloc[position + 1: position + 1 + future_months]
            recent_volume = float(recent["volume"].sum())
            previous_volume = float(previous["volume"].sum())
            future_volume = float(future["volume"].sum())
            recent_avg = recent_volume / max(len(recent), 1)
            future_avg = future_volume / max(len(future), 1)
            quality_denominator = float(history["volume"].sum()) or 1.0
            answer_rate = float(history["answers"].sum()) / quality_denominator
            unanswered_penalty = float(history["unanswered_rate"].mean())
            diversity, adoption_velocity = _enterprise_as_of(datasets, str(technology), obs_month)
            rows.append(
                {
                    TECH_COLUMN: str(technology),
                    CATEGORY_COLUMN: categories.get(str(technology), "Other"),
                    OBSERVATION_MONTH_COLUMN: obs_month.date().isoformat(),
                    "growth_momentum_index": recent_volume / max(float(history["volume"].sum()), 1.0),
                    "question_quality_score": max(answer_rate * (1 - unanswered_penalty), 0.0),
                    "community_decay_rate": max((previous_volume - recent_volume) / max(previous_volume, 1.0), 0.0),
                    "company_diversity_score": diversity,
                    "sentiment_delta": _sentiment_delta_as_of(
                        survey_lookup, str(technology), int(obs_month.year)
                    ),
                    "adoption_velocity": adoption_velocity,
                    "so_volume_trend_slope": _trend_slope(history["volume"]),
                    "so_months_observed": int(len(history)),
                    "so_question_volume": int(history["volume"].sum()),
                    "recent_avg_monthly_volume": recent_avg,
                    "future_avg_monthly_volume": future_avg,
                    "future_volume": future_volume,
                    "future_growth_ratio": future_avg / max(recent_avg, 1.0),
                }
            )
    return pd.DataFrame(rows)


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
    score = _column(
        sentiment,
        [
            "developer_usage_share",
            "usage_share",
            "satisfaction_score",
            "satisfaction",
            "sentiment_score",
        ],
    )
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
    temporal = _temporal_so_panel(datasets, logger)
    features = temporal if not temporal.empty else _base_technologies(datasets)

    if temporal.empty:
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
    (OUTPUTS_DIR / "target_leakage_columns.json").write_text(
        pd.Series(TARGET_LEAKAGE_COLUMNS).to_json(orient="values"), encoding="utf-8"
    )
    return features
