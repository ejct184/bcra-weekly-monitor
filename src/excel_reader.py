"""Read and process Excel data for BCRA Weekly Monitor."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .config import (
    EXCEL_FILE,
    SERIES_WITH_CHANGES,
    SERIES_LAST_VALUE_ONLY,
    SERIES_DISPLAY_NAMES,
)


@dataclass
class SeriesSummary:
    """Summary data for a single series."""
    name: str
    display_name: str
    last_value: float
    last_date: datetime
    weekly_change: Optional[float] = None  # Log diff × 100
    monthly_change: Optional[float] = None  # Log diff × 100
    is_new: bool = False  # For series like inflation/REM, flag if new data


def read_excel_data() -> pd.DataFrame:
    """Load and parse the Excel file."""
    df = pd.read_excel(EXCEL_FILE)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)
    return df


def calculate_log_change(current: float, previous: float) -> float:
    """Calculate log difference × 100 (percentage change approximation)."""
    if pd.isna(current) or pd.isna(previous) or previous <= 0 or current <= 0:
        return np.nan
    return (np.log(current) - np.log(previous)) * 100


def get_value_n_days_ago(df: pd.DataFrame, series: str, days: int) -> Tuple[Optional[float], Optional[datetime]]:
    """Get the value of a series approximately N days ago."""
    series_data = df[["fecha", series]].dropna()
    if series_data.empty:
        return None, None

    last_date = series_data["fecha"].max()
    target_date = last_date - timedelta(days=days)

    # Find closest date to target
    idx = (series_data["fecha"] - target_date).abs().idxmin()
    row = series_data.loc[idx]
    return row[series], row["fecha"]


def get_last_value(df: pd.DataFrame, series: str) -> Tuple[Optional[float], Optional[datetime]]:
    """Get the last non-null value and its date for a series."""
    series_data = df[["fecha", series]].dropna()
    if series_data.empty:
        return None, None
    last_row = series_data.iloc[-1]
    return last_row[series], last_row["fecha"]


def check_if_new_data(df: pd.DataFrame, series: str, days_threshold: int = 7) -> bool:
    """Check if the series has new data within the last N days."""
    _, last_date = get_last_value(df, series)
    if last_date is None:
        return False
    today = datetime.now()
    return (today - last_date).days <= days_threshold


def process_series_with_changes(df: pd.DataFrame, series: str) -> SeriesSummary:
    """Process a series that needs weekly/monthly change calculations."""
    last_value, last_date = get_last_value(df, series)

    if last_value is None:
        return SeriesSummary(
            name=series,
            display_name=SERIES_DISPLAY_NAMES.get(series, series),
            last_value=np.nan,
            last_date=datetime.now(),
        )

    # Weekly change (7 days ago)
    week_ago_value, _ = get_value_n_days_ago(df, series, 7)
    weekly_change = calculate_log_change(last_value, week_ago_value) if week_ago_value else None

    # Monthly change (30 days ago)
    month_ago_value, _ = get_value_n_days_ago(df, series, 30)
    monthly_change = calculate_log_change(last_value, month_ago_value) if month_ago_value else None

    return SeriesSummary(
        name=series,
        display_name=SERIES_DISPLAY_NAMES.get(series, series),
        last_value=last_value,
        last_date=last_date,
        weekly_change=weekly_change,
        monthly_change=monthly_change,
    )


def process_series_last_value(df: pd.DataFrame, series: str) -> SeriesSummary:
    """Process a series that only reports last value."""
    last_value, last_date = get_last_value(df, series)
    is_new = check_if_new_data(df, series)

    return SeriesSummary(
        name=series,
        display_name=SERIES_DISPLAY_NAMES.get(series, series),
        last_value=last_value if last_value is not None else np.nan,
        last_date=last_date if last_date is not None else datetime.now(),
        is_new=is_new,
    )


def get_all_summaries() -> List[SeriesSummary]:
    """Get summaries for all configured series."""
    df = read_excel_data()
    summaries = []

    # Process series with changes
    for series in SERIES_WITH_CHANGES:
        if series in df.columns:
            summaries.append(process_series_with_changes(df, series))

    # Process series with last value only
    for series in SERIES_LAST_VALUE_ONLY:
        if series in df.columns:
            summaries.append(process_series_last_value(df, series))

    return summaries


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with thousands separator and decimal places."""
    if pd.isna(value):
        return "N/A"
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:,.{decimals}f}M"
    elif abs(value) >= 1_000:
        return f"{value:,.{decimals}f}"
    else:
        return f"{value:.{decimals}f}"


def format_change(value: Optional[float]) -> str:
    """Format a percentage change with sign."""
    if value is None or pd.isna(value):
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def get_summary_table() -> str:
    """Generate a formatted summary table for display/debugging."""
    summaries = get_all_summaries()

    lines = ["=" * 80]
    lines.append("BCRA Data Summary")
    lines.append("=" * 80)

    for s in summaries:
        lines.append(f"\n{s.display_name}")
        lines.append(f"  Last Value: {format_number(s.last_value)} (as of {s.last_date.strftime('%Y-%m-%d')})")
        if s.weekly_change is not None:
            lines.append(f"  Weekly Change: {format_change(s.weekly_change)}")
        if s.monthly_change is not None:
            lines.append(f"  Monthly Change: {format_change(s.monthly_change)}")
        if s.is_new:
            lines.append(f"  ** New data available **")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def get_chart_data(series: str, days: int = 365) -> pd.DataFrame:
    """Get data for chart generation (last N days)."""
    df = read_excel_data()
    if series not in df.columns:
        return pd.DataFrame()

    cutoff_date = df["fecha"].max() - timedelta(days=days)
    chart_data = df[df["fecha"] >= cutoff_date][["fecha", series]].copy()
    chart_data = chart_data.dropna()
    return chart_data


if __name__ == "__main__":
    # Test the module
    print(get_summary_table())
