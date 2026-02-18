"""PDF download and text extraction for BCRA reports."""

import argparse
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

import requests
import pdfplumber

from .config import DATA_DIR


# Directory for storing extracted PDF texts
PDF_TEXTS_DIR = DATA_DIR / "pdf_texts"
PDF_TEXTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PDFContent:
    """Extracted content from a PDF."""
    url: str
    title: str
    text: str
    page_count: int
    success: bool
    error: Optional[str] = None


def download_pdf(url: str) -> Tuple[Optional[Path], Optional[str]]:
    """Download a PDF to a temporary file."""
    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()

        # Check if it's actually a PDF
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not url.endswith(".pdf"):
            return None, f"Not a PDF: {content_type}"

        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_file.close()

        return Path(temp_file.name), None

    except Exception as e:
        return None, str(e)


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 20) -> Tuple[str, int]:
    """Extract text from a PDF file."""
    text_parts = []
    page_count = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)

            # Extract text from pages (limit to avoid huge PDFs)
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Página {i + 1} ---\n{page_text}")

            if page_count > max_pages:
                text_parts.append(f"\n[... Documento truncado: {page_count - max_pages} páginas adicionales ...]")

    except Exception as e:
        text_parts.append(f"Error extracting text: {e}")

    return "\n\n".join(text_parts), page_count


def process_pdf(url: str, title: str = "") -> PDFContent:
    """Download and extract text from a PDF."""
    # Download
    pdf_path, error = download_pdf(url)
    if error:
        return PDFContent(
            url=url,
            title=title,
            text="",
            page_count=0,
            success=False,
            error=error,
        )

    try:
        # Extract text
        text, page_count = extract_text_from_pdf(pdf_path)

        return PDFContent(
            url=url,
            title=title,
            text=text,
            page_count=page_count,
            success=True,
        )

    finally:
        # Clean up temp file
        if pdf_path and pdf_path.exists():
            pdf_path.unlink()


def save_pdf_text(content: PDFContent, filename: str) -> Path:
    """Save extracted PDF text to a file for later summarization."""
    filepath = PDF_TEXTS_DIR / f"{filename}.txt"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Título: {content.title}\n")
        f.write(f"URL: {content.url}\n")
        f.write(f"Páginas: {content.page_count}\n")
        f.write("=" * 60 + "\n\n")
        f.write(content.text)

    return filepath


def get_summary_prompt(content: PDFContent) -> str:
    """Generate a prompt for Claude Code to summarize the PDF."""
    return f"""Por favor, genera un resumen ejecutivo en español (2-3 párrafos) del siguiente informe del BCRA.

Título: {content.title}
URL: {content.url}
Páginas: {content.page_count}

Incluye:
- Principales conclusiones
- Datos destacados (cifras clave)
- Cambios respecto al informe anterior (si se mencionan)

--- CONTENIDO DEL DOCUMENTO ---

{content.text[:15000]}  # Limit text for context window

--- FIN DEL DOCUMENTO ---

Resumen ejecutivo:"""


def test_pdf_processor(url: str):
    """Test PDF processing with a given URL."""
    print(f"Processing: {url}")

    content = process_pdf(url, "Test PDF")

    if content.success:
        print(f"\nSuccess!")
        print(f"Pages: {content.page_count}")
        print(f"Text length: {len(content.text)} chars")
        print(f"\nFirst 500 chars:\n{content.text[:500]}")

        # Save for inspection
        filepath = save_pdf_text(content, "test_pdf")
        print(f"\nSaved to: {filepath}")
    else:
        print(f"\nFailed: {content.error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF processor for BCRA reports")
    parser.add_argument("--test", type=str, help="Test with a PDF URL")
    args = parser.parse_args()

    if args.test:
        test_pdf_processor(args.test)
    else:
        print("Usage: python -m src.pdf_processor --test <pdf_url>")
        print("\nExample URLs:")
        print("  https://www.bcra.gob.ar/Pdfs/PublicacionesEstadisticas/ipom0126.pdf")
