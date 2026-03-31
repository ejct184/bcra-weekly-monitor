"""Compile digest content from all sources."""

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .config import TEMPLATES_DIR, CHARTS_DIR
from .excel_reader import get_all_summaries, SeriesSummary, format_number, format_change


@dataclass
class DataTableRow:
    """A row in the data summary table."""
    name: str
    value: str
    value_date: str  # Date of the last value
    weekly_change: Optional[str]
    weekly_class: str
    monthly_change: Optional[str]
    monthly_class: str
    is_new: bool


@dataclass
class ChartInfo:
    """Information about an embedded chart."""
    path: Path
    title: str
    cid: str  # Content-ID for email embedding


@dataclass
class ContentItem:
    """A news/report/policy item for the digest."""
    title: str
    date: str
    url: str
    excerpt: str = ""
    summary: str = ""
    is_new: bool = False  # Flag for NUEVO badge (only True if not seen in previous run)


@dataclass
class DigestContent:
    """Complete digest content ready for rendering."""
    date_range: str
    data_table: List[DataTableRow]
    charts: List[ChartInfo]
    policy_items: List[ContentItem]
    report_items: List[ContentItem]
    news_items: List[ContentItem]


def get_change_class(value: Optional[float]) -> str:
    """Get CSS class for change value."""
    if value is None:
        return "neutral"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def build_data_table() -> List[DataTableRow]:
    """Build the data summary table from Excel data."""
    summaries = get_all_summaries()
    rows = []

    for s in summaries:
        # Format the value based on the series
        if "Tasa" in s.display_name or "Inflación" in s.display_name:
            value_str = f"{s.last_value:.2f}%"
        elif s.last_value >= 1_000_000:
            value_str = f"{s.last_value/1_000_000:,.2f}M"
        else:
            value_str = format_number(s.last_value)

        # Format the date
        value_date = s.last_date.strftime("%d/%m/%Y") if s.last_date else "N/A"

        rows.append(DataTableRow(
            name=s.display_name,
            value=value_str,
            value_date=value_date,
            weekly_change=format_change(s.weekly_change) if s.weekly_change is not None else None,
            weekly_class=get_change_class(s.weekly_change),
            monthly_change=format_change(s.monthly_change) if s.monthly_change is not None else None,
            monthly_class=get_change_class(s.monthly_change),
            is_new=s.is_new,
        ))

    return rows


def get_chart_infos() -> List[ChartInfo]:
    """Get information about generated charts."""
    charts = []

    chart_files = [
        ("reservas_pct_change.png", "Reservas Internacionales - Var. Mensual", "chart_reservas"),
        ("base_monetaria_pct_change.png", "Base Monetaria - Var. Mensual", "chart_base"),
        ("m2_pct_change.png", "M2 Transaccional - Var. Mensual", "chart_m2"),
        ("tipo_cambio_nivel.png", "Tipo de Cambio Oficial", "chart_tc"),
        ("badlar_nivel.png", "Tasa BADLAR", "chart_badlar"),
    ]

    for filename, title, cid in chart_files:
        path = CHARTS_DIR / filename
        if path.exists():
            charts.append(ChartInfo(path=path, title=title, cid=cid))

    return charts


def build_digest(
    news_items: list = None,
    report_items: list = None,
    policy_items: list = None,
    summaries: dict = None,
) -> DigestContent:
    """Build complete digest content."""

    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    date_range = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

    # Data table
    data_table = build_data_table()

    # Charts
    charts = get_chart_infos()

    # Convert scraped items to ContentItems
    def to_content_items(items, summaries_dict=None):
        if not items:
            return []
        result = []
        for item in items:
            summary = ""
            if summaries_dict and hasattr(item, 'id'):
                summary = summaries_dict.get(item.id, "")

            result.append(ContentItem(
                title=getattr(item, 'title', ''),
                date=getattr(item, 'date', ''),
                url=getattr(item, 'url', ''),
                excerpt=getattr(item, 'excerpt', ''),
                summary=summary,
                is_new=getattr(item, 'is_new', False),  # Pass the is_new flag from scraped item
            ))
        return result

    summaries = summaries or {}

    return DigestContent(
        date_range=date_range,
        data_table=data_table,
        charts=charts,
        policy_items=to_content_items(policy_items, summaries.get('policy')),
        report_items=to_content_items(report_items, summaries.get('reports')),
        news_items=to_content_items(news_items, summaries.get('news')),
    )


def format_summary_html(summary: str) -> str:
    """Convert summary text to HTML with title and bullet points.

    Expected format:
    Title line

    • Bullet point 1
    • Bullet point 2
    """
    if not summary:
        return ""

    lines = summary.strip().split('\n')
    if not lines:
        return ""

    # First non-empty line is the title
    title = ""
    bullets = []
    in_bullets = False

    for line in lines:
        line = line.strip()
        if not line:
            in_bullets = True  # Empty line separates title from bullets
            continue

        if not title and not in_bullets:
            title = line
        elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
            # Clean bullet character and add to list
            bullet_text = line.lstrip('•-* ').strip()
            if bullet_text:
                bullets.append(bullet_text)
        elif in_bullets and line:
            # Line without bullet marker, treat as bullet
            bullets.append(line)

    # Build HTML
    html_parts = []
    if title:
        html_parts.append(f'<div class="summary-title">{title}</div>')

    if bullets:
        html_parts.append('<ul class="summary-bullets">')
        for bullet in bullets:
            html_parts.append(f'<li>{bullet}</li>')
        html_parts.append('</ul>')

    return '\n'.join(html_parts)


def render_digest(content: DigestContent) -> str:
    """Render the digest to HTML."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

    # Add custom filter for summary formatting
    env.filters['format_summary'] = format_summary_html

    template = env.get_template("email_template.html")

    return template.render(
        date_range=content.date_range,
        data_table=content.data_table,
        charts=content.charts,
        policy_items=content.policy_items,
        report_items=content.report_items,
        news_items=content.news_items,
    )


def save_digest_preview(html: str, filename: str = "digest_preview.html") -> Path:
    """Save digest HTML for preview."""
    from .config import DATA_DIR

    # For preview, replace cid: references with file:// paths
    for chart in get_chart_infos():
        html = html.replace(f"cid:{chart.cid}", f"file:///{chart.path}")

    filepath = DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


if __name__ == "__main__":
    # Test digest generation
    print("Building digest...")

    content = build_digest()
    html = render_digest(content)

    preview_path = save_digest_preview(html)
    print(f"\nDigest preview saved to: {preview_path}")

    # Try to open in browser
    import webbrowser
    webbrowser.open(f"file:///{preview_path}")
