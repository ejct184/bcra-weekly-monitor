"""Generate summaries using Claude API for BCRA reports."""

import os
import json
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic

from .config import DATA_DIR
from .pdf_processor import process_pdf


# Cache file for storing generated summaries
SUMMARIES_CACHE_FILE = DATA_DIR / "summaries_cache.json"


def load_summaries_cache() -> dict:
    """Load cached summaries from file."""
    if SUMMARIES_CACHE_FILE.exists():
        try:
            with open(SUMMARIES_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_summaries_cache(cache: dict):
    """Save summaries cache to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARIES_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# Reports that should receive AI summaries
REPORTS_NEEDING_SUMMARY = [
    "informe monetario mensual",
    "relevamiento de expectativas",
]

POLICY_NEEDING_SUMMARY = [
    "ipom",
    "informe de política monetaria",
    "comunicado",
]


@dataclass
class SummaryResult:
    """Result of a summary generation."""
    success: bool
    summary: str
    error: Optional[str] = None


def get_anthropic_client() -> Optional[Anthropic]:
    """Get Anthropic client if API key is available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)


def needs_summary(title: str, item_type: str = "report") -> bool:
    """Check if an item needs a summary based on its title."""
    title_lower = title.lower()

    if item_type == "report":
        return any(pattern in title_lower for pattern in REPORTS_NEEDING_SUMMARY)
    elif item_type == "policy":
        return any(pattern in title_lower for pattern in POLICY_NEEDING_SUMMARY)

    return False


def generate_summary(text: str, title: str, max_tokens: int = 500) -> SummaryResult:
    """Generate a summary using Claude API."""
    client = get_anthropic_client()

    if not client:
        return SummaryResult(
            success=False,
            summary="",
            error="ANTHROPIC_API_KEY not configured"
        )

    # Truncate text if too long (to manage costs)
    max_text_length = 15000
    if len(text) > max_text_length:
        text = text[:max_text_length] + "\n\n[... documento truncado ...]"

    prompt = f"""Genera un resumen ejecutivo en español del siguiente documento del Banco Central de la República Argentina (BCRA).

Título del documento: {title}

FORMATO REQUERIDO:
1. Primera línea: Título descriptivo del resumen (será mostrado en negrita)
2. Línea en blanco
3. Lista de 4-6 puntos clave usando viñetas (•)

Cada punto debe ser conciso (1-2 oraciones) e incluir:
• Principales conclusiones o decisiones
• Datos y cifras clave (porcentajes, montos, variaciones)
• Cambios respecto a períodos anteriores

Ejemplo de formato:
Resumen del Informe Monetario Mensual - Enero 2026

• La Base Monetaria se contrajo 1,6% en términos reales durante el mes.
• El BCRA adquirió USD 1.158 millones en el mercado de cambios.
• Los depósitos a plazo fijo se expandieron en términos reales.

--- CONTENIDO DEL DOCUMENTO ---

{text}

--- FIN DEL DOCUMENTO ---

Resumen:"""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Fast and cost-effective
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        summary = response.content[0].text.strip()

        return SummaryResult(
            success=True,
            summary=summary
        )

    except Exception as e:
        return SummaryResult(
            success=False,
            summary="",
            error=str(e)
        )


def extract_text_from_html(url: str) -> Tuple[bool, str, Optional[str]]:
    """Extract main content text from an HTML page.

    Returns: (success, text, error)
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find the main content area
        main_content = None

        # Look for common content containers
        for selector in ["article", "main", ".content", ".post-content", ".entry-content", "#content"]:
            if selector.startswith(".") or selector.startswith("#"):
                main_content = soup.select_one(selector)
            else:
                main_content = soup.find(selector)
            if main_content:
                break

        # If no specific container found, use body
        if not main_content:
            main_content = soup.find("body") or soup

        # Extract text
        text = main_content.get_text(separator="\n", strip=True)

        # Clean up multiple newlines
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)

        if len(text) < 100:
            return False, "", "HTML content too short"

        return True, text, None

    except Exception as e:
        return False, "", str(e)


def summarize_pdf_url(url: str, title: str) -> SummaryResult:
    """Download PDF and generate summary."""
    # Download and extract text
    content = process_pdf(url, title)

    if not content.success:
        return SummaryResult(
            success=False,
            summary="",
            error=f"Failed to extract PDF: {content.error}"
        )

    if not content.text or len(content.text) < 100:
        return SummaryResult(
            success=False,
            summary="",
            error="PDF text too short or empty"
        )

    # Generate summary
    return generate_summary(content.text, title)


def summarize_html_url(url: str, title: str) -> SummaryResult:
    """Extract HTML content and generate summary."""
    success, text, error = extract_text_from_html(url)

    if not success:
        return SummaryResult(
            success=False,
            summary="",
            error=f"Failed to extract HTML: {error}"
        )

    return generate_summary(text, title)


def summarize_report(report) -> Optional[str]:
    """Summarize a report if it needs a summary."""
    if not needs_summary(report.title, "report"):
        return None

    # Try PDF URL first, then regular URL
    url = getattr(report, 'pdf_url', None) or getattr(report, 'url', '')

    if not url:
        return None

    print(f"  Generating summary for: {report.title[:50]}...")
    result = summarize_pdf_url(url, report.title)

    if result.success:
        print(f"    [OK] Summary generated ({len(result.summary)} chars)")
        return result.summary
    else:
        print(f"    [FAILED] {result.error}")
        return None


def summarize_policy(policy) -> Optional[str]:
    """Summarize a policy item if it needs a summary."""
    if not needs_summary(policy.title, "policy"):
        return None

    pdf_url = getattr(policy, 'pdf_url', None)
    html_url = getattr(policy, 'url', '')

    if not pdf_url and not html_url:
        return None

    print(f"  Generating summary for: {policy.title[:50]}...")

    # If there's a PDF URL, use PDF extraction
    if pdf_url:
        result = summarize_pdf_url(pdf_url, policy.title)
    else:
        # Otherwise, use HTML extraction (for comunicados)
        result = summarize_html_url(html_url, policy.title)

    if result.success:
        print(f"    [OK] Summary generated ({len(result.summary)} chars)")
        return result.summary
    else:
        print(f"    [FAILED] {result.error}")
        return None


def generate_all_summaries(reports: list, policy_items: list) -> dict:
    """Generate summaries for all items that need them.

    Uses a cache to avoid regenerating summaries for already-processed items.
    """
    # Load existing cache
    cache = load_summaries_cache()

    summaries = {
        "reports": {},
        "policy": {},
    }

    client = get_anthropic_client()
    if not client:
        print("  Warning: ANTHROPIC_API_KEY not set, skipping summaries")
        # Still return cached summaries if available
        for report in reports:
            if report.id in cache:
                summaries["reports"][report.id] = cache[report.id]
        for policy in policy_items:
            if policy.id in cache:
                summaries["policy"][policy.id] = cache[policy.id]
        return summaries

    cache_updated = False

    # Summarize reports
    for report in reports:
        if not needs_summary(report.title, "report"):
            continue

        # Check cache first
        if report.id in cache:
            print(f"  Using cached summary for: {report.title[:50]}...")
            summaries["reports"][report.id] = cache[report.id]
            continue

        summary = summarize_report(report)
        if summary:
            summaries["reports"][report.id] = summary
            cache[report.id] = summary
            cache_updated = True

    # Summarize policy items
    for policy in policy_items:
        if not needs_summary(policy.title, "policy"):
            continue

        # Check cache first
        if policy.id in cache:
            print(f"  Using cached summary for: {policy.title[:50]}...")
            summaries["policy"][policy.id] = cache[policy.id]
            continue

        summary = summarize_policy(policy)
        if summary:
            summaries["policy"][policy.id] = summary
            cache[policy.id] = summary
            cache_updated = True

    # Save cache if updated
    if cache_updated:
        save_summaries_cache(cache)
        print(f"  Summary cache updated ({len(cache)} items)")

    return summaries


if __name__ == "__main__":
    # Test the summarizer
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.summarizer <pdf_url>")
        print("Make sure ANTHROPIC_API_KEY is set in .env")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Testing summary for: {url}")

    result = summarize_pdf_url(url, "Test Document")

    if result.success:
        print("\n--- SUMMARY ---")
        print(result.summary)
    else:
        print(f"\nError: {result.error}")
