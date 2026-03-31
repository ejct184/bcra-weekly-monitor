"""Generate publication-quality charts for BCRA Weekly Monitor."""

import argparse
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .config import CHARTS_DIR, CHART_WIDTH_PX, CHART_DPI, CHART_DAYS
from .excel_reader import read_excel_data


def setup_publication_style():
    """Configure matplotlib for publication-quality charts."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "grid.alpha": 0.3,
        "lines.linewidth": 1.5,
    })


def calculate_monthly_pct_change(df: pd.DataFrame, series: str) -> pd.DataFrame:
    """Calculate rolling 30-day log percentage change."""
    data = df[["fecha", series]].dropna().copy()
    data = data.sort_values("fecha").reset_index(drop=True)

    # Calculate 30-day rolling log change
    data["pct_change"] = np.nan
    for i in range(30, len(data)):
        current = data.iloc[i][series]
        past = data.iloc[i - 30][series]
        if current > 0 and past > 0:
            data.loc[data.index[i], "pct_change"] = (np.log(current) - np.log(past)) * 100

    return data


def filter_last_n_days(df: pd.DataFrame, days: int = 365) -> pd.DataFrame:
    """Filter dataframe to last N days."""
    if df.empty:
        return df
    cutoff = df["fecha"].max() - timedelta(days=days)
    return df[df["fecha"] >= cutoff].copy()


def create_chart(
    dates: pd.Series,
    values: pd.Series,
    title: str,
    ylabel: str,
    filename: str,
    color: str = "#2E86AB",
    show_zero_line: bool = False,
    ylim: tuple = None,
) -> Path:
    """Create a single chart and save to file."""
    setup_publication_style()

    fig_width = CHART_WIDTH_PX / CHART_DPI
    fig, ax = plt.subplots(figsize=(fig_width, fig_width * 0.5), dpi=CHART_DPI)

    # Plot data
    ax.plot(dates, values, color=color, linewidth=1.5)
    ax.fill_between(dates, values, alpha=0.1, color=color)

    # Set y-axis limits if specified
    if ylim:
        ax.set_ylim(ylim)

    # Zero line if needed
    if show_zero_line:
        ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)

    # Format
    ax.set_title(title, pad=10)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")

    # Date formatting
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    plt.xticks(rotation=45, ha="right")

    # Add date range annotation
    date_range = f"{dates.min().strftime('%d/%m/%Y')} - {dates.max().strftime('%d/%m/%Y')}"
    ax.annotate(
        date_range,
        xy=(0.99, 0.02),
        xycoords="axes fraction",
        ha="right",
        va="bottom",
        fontsize=8,
        color="gray",
    )

    plt.tight_layout()

    # Save
    filepath = CHARTS_DIR / filename
    fig.savefig(filepath, dpi=CHART_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return filepath


def generate_reserves_chart() -> Path:
    """Generate Reservas Internacionales monthly % change chart."""
    df = read_excel_data()
    data = calculate_monthly_pct_change(df, "Reservas internacionales")
    data = filter_last_n_days(data, CHART_DAYS)
    data = data.dropna(subset=["pct_change"])

    return create_chart(
        dates=data["fecha"],
        values=data["pct_change"],
        title="Reservas Internacionales - Variación Mensual",
        ylabel="Variación (%)",
        filename="reservas_pct_change.png",
        color="#2E86AB",
        show_zero_line=True,
    )


def generate_base_monetaria_chart() -> Path:
    """Generate Base Monetaria monthly % change chart."""
    df = read_excel_data()
    data = calculate_monthly_pct_change(df, "Base monetaria")
    data = filter_last_n_days(data, CHART_DAYS)
    data = data.dropna(subset=["pct_change"])

    return create_chart(
        dates=data["fecha"],
        values=data["pct_change"],
        title="Base Monetaria - Variación Mensual",
        ylabel="Variación (%)",
        filename="base_monetaria_pct_change.png",
        color="#A23B72",
        show_zero_line=True,
    )


def generate_m2_chart() -> Path:
    """Generate M2 Transaccional monthly % change chart."""
    df = read_excel_data()
    data = calculate_monthly_pct_change(df, "M2 transaccional del sector privado")
    data = filter_last_n_days(data, CHART_DAYS)
    data = data.dropna(subset=["pct_change"])

    return create_chart(
        dates=data["fecha"],
        values=data["pct_change"],
        title="M2 Transaccional - Variación Mensual",
        ylabel="Variación (%)",
        filename="m2_pct_change.png",
        color="#F18F01",
        show_zero_line=True,
    )


def generate_exchange_rate_chart() -> Path:
    """Generate Tipo de Cambio level chart (not % change)."""
    df = read_excel_data()
    series = "Tipo de cambio minorista (promedio vendedor)"
    data = df[["fecha", series]].dropna().copy()
    data = filter_last_n_days(data, CHART_DAYS)

    # Set y-axis limits: 1000 to 1700, with dynamic upper limit if data exceeds 1700
    y_min = 1000
    y_max = 1700
    max_value = data[series].max()
    if max_value > y_max:
        # Add 10% margin above the max value
        y_max = max_value * 1.1

    return create_chart(
        dates=data["fecha"],
        values=data[series],
        title="Tipo de Cambio Oficial",
        ylabel="ARS por USD",
        filename="tipo_cambio_nivel.png",
        color="#C73E1D",
        show_zero_line=False,
        ylim=(y_min, y_max),
    )


def generate_badlar_chart() -> Path:
    """Generate Tasa BADLAR level chart."""
    df = read_excel_data()
    series = "Tasa de interés BADLAR de bancos privados"
    data = df[["fecha", series]].dropna().copy()
    data = filter_last_n_days(data, CHART_DAYS)

    # Set y-axis limits: 0 to 40%, with dynamic upper limit if data exceeds 40
    y_min = 0
    y_max = 40
    max_value = data[series].max()
    if max_value > y_max:
        # Add 10% margin above the max value
        y_max = max_value * 1.1

    return create_chart(
        dates=data["fecha"],
        values=data[series],
        title="Tasa BADLAR",
        ylabel="Tasa (%)",
        filename="badlar_nivel.png",
        color="#6B46C1",
        show_zero_line=False,
        ylim=(y_min, y_max),
    )


def generate_all_charts() -> dict:
    """Generate all charts and return paths."""
    charts = {}

    charts["reservas"] = generate_reserves_chart()
    print(f"Generated: {charts['reservas']}")

    charts["base_monetaria"] = generate_base_monetaria_chart()
    print(f"Generated: {charts['base_monetaria']}")

    charts["m2"] = generate_m2_chart()
    print(f"Generated: {charts['m2']}")

    charts["tipo_cambio"] = generate_exchange_rate_chart()
    print(f"Generated: {charts['tipo_cambio']}")

    charts["badlar"] = generate_badlar_chart()
    print(f"Generated: {charts['badlar']}")

    return charts


def preview_charts():
    """Generate charts and open for preview."""
    import webbrowser
    import tempfile
    import os

    charts = generate_all_charts()

    # Create simple HTML preview
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>BCRA Charts Preview</title></head>
    <body style="font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px;">
        <h1>BCRA Charts Preview</h1>
    """

    for name, path in charts.items():
        html += f'<h2>{name}</h2><img src="file:///{path}" style="max-width: 100%;"><hr>'

    html += "</body></html>"

    # Save and open
    preview_file = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False)
    preview_file.write(html)
    preview_file.close()

    webbrowser.open(f"file:///{preview_file.name}")
    print(f"\nPreview opened in browser: {preview_file.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate BCRA charts")
    parser.add_argument("--preview", action="store_true", help="Open charts in browser")
    args = parser.parse_args()

    if args.preview:
        preview_charts()
    else:
        generate_all_charts()
        print("\nAll charts generated successfully!")
