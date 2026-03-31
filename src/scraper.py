"""Web scraper for BCRA news, reports, and policy updates."""

import argparse
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .config import (
    BCRA_NEWS_API,
    BCRA_INFORMES_URL,
    BCRA_POLITICA_URL,
    BCRA_COMUNICADOS_URL,
    STATE_FILE,
    DATA_DIR,
)


@dataclass
class NewsItem:
    """A news item from BCRA."""
    id: str
    title: str
    date: str
    excerpt: str
    url: str
    category: str = "Noticias"
    is_new: bool = False  # True if not seen in previous run


@dataclass
class ReportItem:
    """A report from BCRA."""
    id: str
    title: str
    date: str
    url: str
    pdf_url: Optional[str] = None
    category: str = "Informes"
    is_new: bool = False  # True if not seen in previous run


@dataclass
class PolicyItem:
    """A monetary policy statement from BCRA."""
    id: str
    title: str
    date: str
    url: str
    pdf_url: Optional[str] = None
    category: str = "Política Monetaria"
    is_new: bool = False  # True if not seen in previous run


def load_state() -> dict:
    """Load the state file tracking processed items."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed_ids": [], "last_run": None}


def save_state(state: dict):
    """Save the state file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def fetch_news(days: int = 7) -> List[NewsItem]:
    """Fetch news from BCRA API."""
    items = []
    cutoff_date = datetime.now() - timedelta(days=days)
    found_old_item = False

    try:
        page = 1
        max_pages = 5  # Limit pages to avoid too many requests

        while page <= max_pages and not found_old_item:
            response = requests.get(
                BCRA_NEWS_API,
                params={"page": page, "lang": "es"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success") or not data.get("data", {}).get("posts"):
                break

            for post in data["data"]["posts"]:
                # Parse date (format: "29 de enero de 2026")
                date_str = post.get("date", "")
                try:
                    post_date = parse_spanish_date(date_str)
                except Exception:
                    post_date = datetime.now()

                # Check if we've gone past our date range
                if post_date < cutoff_date:
                    found_old_item = True
                    continue

                items.append(NewsItem(
                    id=str(post.get("id", "")),
                    title=clean_html(post.get("title", "")),
                    date=date_str,
                    excerpt=clean_html(post.get("excerpt", "")),
                    url=post.get("permalink", ""),
                ))

            # Check pagination
            pagination = data.get("data", {}).get("pagination", {})
            if page >= pagination.get("total_pages", 1):
                break
            page += 1
            time.sleep(0.5)  # Rate limiting

    except Exception as e:
        print(f"Error fetching news: {e}")

    return items


def parse_spanish_date(date_str: str) -> datetime:
    """Parse Spanish date format like '29 de enero de 2026'."""
    months = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }

    parts = date_str.lower().replace(" de ", " ").split()
    if len(parts) >= 3:
        day = int(parts[0])
        month = months.get(parts[1], 1)
        year = int(parts[2])
        return datetime(year, month, day)
    return datetime.now()


def clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(strip=True)


def parse_short_spanish_date(date_str: str) -> Optional[datetime]:
    """Parse short Spanish date format like '06 feb 2026' or '29 ene 2026'."""
    months = {
        "ene": 1, "feb": 2, "mar": 3, "abr": 4,
        "may": 5, "jun": 6, "jul": 7, "ago": 8,
        "sep": 9, "oct": 10, "nov": 11, "dic": 12
    }

    try:
        parts = date_str.lower().strip().split()
        if len(parts) >= 3:
            day = int(parts[0])
            month = months.get(parts[1], 1)
            year = int(parts[2])
            return datetime(year, month, day)
    except:
        pass
    return None


def format_date_spanish(dt: datetime) -> str:
    """Format datetime to Spanish date string like '06 de febrero de 2026'."""
    months = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    return f"{dt.day} de {months[dt.month]} de {dt.year}"


def extract_pdf_from_page(page_url: str) -> Optional[str]:
    """Navigate to a page and extract the PDF link.

    Used for IPOM reports where the link goes to an HTML page
    that contains the actual PDF download link.
    """
    try:
        response = requests.get(page_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Look for PDF links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.endswith(".pdf"):
                # Ensure full URL
                if href.startswith("http"):
                    return href
                else:
                    return f"https://www.bcra.gob.ar{href}"
    except Exception:
        pass

    return None


def scrape_informes() -> List[ReportItem]:
    """Scrape the informes page for specific reports only.

    Only captures the most recent of each:
    - Informe Monetario Mensual (1 most recent)
    - Relevamiento de Expectativas de Mercado (REM) (1 most recent)
    """
    items = []
    seen_ids = set()

    # Limits per report type (only capture the most recent of each)
    MAX_INFORME_MONETARIO = 1
    MAX_REM = 1
    informe_monetario_count = 0
    rem_count = 0

    # Specific patterns to match (case insensitive)
    WANTED_REPORTS = [
        "informe monetario mensual",
        "relevamiento de expectativas",
    ]

    try:
        response = requests.get(BCRA_INFORMES_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all table rows that contain report info
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            # Check for links in this row
            link = row.find("a", href=True)
            if not link:
                continue

            href = link["href"]
            text = link.get_text(strip=True)
            text_lower = text.lower()

            # Check if it matches any of the wanted reports
            if not any(pattern in text_lower for pattern in WANTED_REPORTS):
                continue

            # Skip navigation/generic links
            if len(text) < 10:
                continue

            # Check limits per report type - only capture the most recent of each
            is_informe_monetario = "informe monetario mensual" in text_lower
            is_rem = "relevamiento de expectativas" in text_lower

            if is_informe_monetario and informe_monetario_count >= MAX_INFORME_MONETARIO:
                continue
            if is_rem and rem_count >= MAX_REM:
                continue

            # Generate unique ID from URL
            item_id = href.rstrip("/").split("/")[-1].replace(".pdf", "").replace(".asp", "")

            # Skip duplicates
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            # Extract date from the last cell (última actualización)
            date_str = cells[-1].get_text(strip=True)
            parsed_date = parse_short_spanish_date(date_str)
            if parsed_date:
                formatted_date = format_date_spanish(parsed_date)
            else:
                formatted_date = date_str if date_str else datetime.now().strftime("%Y-%m-%d")

            full_url = href if href.startswith("http") else f"https://www.bcra.gob.ar{href}"

            # Check if it's a PDF link or need to extract from page
            if href.endswith(".pdf"):
                pdf_url = full_url
            else:
                # Navigate to the page and find the PDF
                pdf_url = extract_pdf_from_page(full_url)
                time.sleep(0.3)  # Rate limiting

            items.append(ReportItem(
                id=item_id,
                title=text,
                date=formatted_date,
                url=full_url,
                pdf_url=pdf_url,
            ))

            # Increment counters after adding the item
            if is_informe_monetario:
                informe_monetario_count += 1
            if is_rem:
                rem_count += 1

    except Exception as e:
        print(f"Error scraping informes: {e}")

    return items


def scrape_latest_comunicado() -> Optional[PolicyItem]:
    """Scrape the latest comunicado from the comunicados page.

    Returns only the most recent comunicado de política monetaria.
    The page has a table structure with rows containing:
    - First cell: link with title
    - Second cell: date (e.g., "15 dic 2025")
    """
    try:
        response = requests.get(BCRA_COMUNICADOS_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find table rows - comunicados are in a table
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # First cell should have the link
            link = cells[0].find("a", href=True)
            if not link:
                continue

            href = link["href"]
            title = link.get_text(strip=True)

            # Skip short titles (navigation links)
            if len(title) < 15:
                continue

            # Skip IPOM links - those are handled separately
            title_lower = title.lower()
            if "ipom" in title_lower or "informe de política monetaria" in title_lower:
                continue

            # Must be a politica-monetaria or noticias page
            if "/politica-monetaria/" not in href and "/noticias/" not in href:
                continue

            # Generate ID from URL
            item_id = href.rstrip("/").split("/")[-1].replace(".pdf", "")

            full_url = href if href.startswith("http") else f"https://www.bcra.gob.ar{href}"

            # Second cell has the date (e.g., "15 dic 2025")
            date_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            parsed_date = parse_short_spanish_date(date_str)
            if parsed_date:
                formatted_date = format_date_spanish(parsed_date)
            else:
                formatted_date = date_str if date_str else datetime.now().strftime("%Y-%m-%d")

            # Use actual title from the page, prefixed with "Comunicado:"
            display_title = f"Comunicado: {title}"

            return PolicyItem(
                id=item_id,
                title=display_title,
                date=formatted_date,
                url=full_url,
                pdf_url=None,
                category="Comunicado",
            )

    except Exception as e:
        print(f"Error scraping comunicados: {e}")

    return None


def scrape_politica_monetaria() -> List[PolicyItem]:
    """Scrape monetary policy page for IPOM and Comunicados.

    Only captures:
    - Informe de Política Monetaria (IPOM) - only the most recent one
    - Comunicados de Política Monetaria - only the most recent one
    """
    items = []
    seen_ids = set()
    ipom_count = 0
    MAX_IPOM = 1  # Only capture the most recent IPOM

    # Patterns to match for IPOM
    IPOM_PATTERNS = [
        "informe de política monetaria",
        "ipom",
    ]

    try:
        response = requests.get(BCRA_POLITICA_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find IPOM in table rows
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 4:
                link = row.find("a", href=True)
                if not link:
                    continue

                href = link["href"]
                text = link.get_text(strip=True)
                text_lower = text.lower()

                # Only look for IPOM here
                is_ipom = any(pattern in text_lower for pattern in IPOM_PATTERNS)
                if not is_ipom:
                    continue

                if len(text) < 10:
                    continue

                # Check if we've already captured enough IPOMs
                if ipom_count >= MAX_IPOM:
                    continue

                item_id = href.rstrip("/").split("/")[-1].replace(".pdf", "").replace(".asp", "")

                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                # Extract date from the last cell
                date_str = cells[-1].get_text(strip=True)
                parsed_date = parse_short_spanish_date(date_str)
                if parsed_date:
                    formatted_date = format_date_spanish(parsed_date)
                else:
                    formatted_date = date_str if date_str else datetime.now().strftime("%Y-%m-%d")

                ipom_count += 1

                full_url = href if href.startswith("http") else f"https://www.bcra.gob.ar{href}"

                # Check if it's already a PDF or need to extract from page
                if href.endswith(".pdf"):
                    pdf_url = full_url
                else:
                    pdf_url = extract_pdf_from_page(full_url)
                    time.sleep(0.3)  # Rate limiting

                items.append(PolicyItem(
                    id=item_id,
                    title=text,
                    date=formatted_date,
                    url=full_url,
                    pdf_url=pdf_url,
                    category="IPOM",
                ))

    except Exception as e:
        print(f"Error scraping política monetaria: {e}")

    # Also get the latest comunicado from the dedicated comunicados page
    comunicado = scrape_latest_comunicado()
    if comunicado and comunicado.id not in seen_ids:
        items.append(comunicado)

    return items


def mark_items_as_new(items: list, state: dict) -> list:
    """Mark each item's is_new flag based on whether it was previously processed."""
    processed = set(state.get("processed_ids", []))
    for item in items:
        item.is_new = item.id not in processed
    return items


def filter_new_items(items: list, state: dict) -> list:
    """Filter out already processed items (returns only new ones)."""
    processed = set(state.get("processed_ids", []))
    return [item for item in items if item.id not in processed]


def mark_as_processed(items: list, state: dict) -> dict:
    """Mark items as processed in state."""
    processed = set(state.get("processed_ids", []))
    for item in items:
        processed.add(item.id)
    state["processed_ids"] = list(processed)
    return state


def scrape_all(days: int = 7, ignore_state: bool = False) -> dict:
    """Scrape all content sources.

    Returns all items with is_new flag set based on state.
    Only truly new items (not in previous state) will have is_new=True.
    """
    state = {} if ignore_state else load_state()
    processed = set(state.get("processed_ids", []))

    # Fetch news
    print("Fetching news...")
    news = fetch_news(days)
    # Mark is_new flag on each item
    mark_items_as_new(news, state)
    new_news_count = sum(1 for n in news if n.is_new)
    print(f"  Found {len(news)} items, {new_news_count} new")

    # Scrape informes
    print("Scraping informes...")
    reports = scrape_informes()
    mark_items_as_new(reports, state)
    new_reports_count = sum(1 for r in reports if r.is_new)
    print(f"  Found {len(reports)} items, {new_reports_count} new")

    # Scrape policy
    print("Scraping política monetaria...")
    policy = scrape_politica_monetaria()
    mark_items_as_new(policy, state)
    new_policy_count = sum(1 for p in policy if p.is_new)
    print(f"  Found {len(policy)} items, {new_policy_count} new")

    # Return ALL items (not filtered), with is_new flag set
    return {
        "news": news,
        "reports": reports,
        "policy": policy,
        "state": state,
    }


def test_scraper():
    """Test the scraper and print results."""
    print("=" * 60)
    print("BCRA Scraper Test")
    print("=" * 60)

    results = scrape_all(days=7, ignore_state=True)

    print("\n--- NEWS ---")
    for item in results["news"][:5]:
        print(f"\n{item.title}")
        print(f"  Date: {item.date}")
        print(f"  URL: {item.url}")
        print(f"  Excerpt: {item.excerpt[:100]}...")

    print("\n--- REPORTS ---")
    for item in results["reports"][:5]:
        print(f"\n{item.title}")
        print(f"  URL: {item.url}")

    print("\n--- POLICY ---")
    for item in results["policy"][:5]:
        print(f"\n{item.title}")
        print(f"  URL: {item.url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BCRA web scraper")
    parser.add_argument("--test", action="store_true", help="Run test mode")
    args = parser.parse_args()

    if args.test:
        test_scraper()
    else:
        results = scrape_all()
        print(f"\nTotal new items: {len(results['news']) + len(results['reports']) + len(results['policy'])}")
