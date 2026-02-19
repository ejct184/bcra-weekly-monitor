# BCRA Weekly Monitor

Automated weekly digest of Argentina's Central Bank (BCRA) publications and financial data.

## Overview

This system automatically:
1. Reads high-frequency financial data from an Excel file
2. Generates charts for key monetary indicators
3. Scrapes BCRA website for new reports, policy documents, and news
4. Generates AI summaries of PDF reports using Claude
5. Compiles everything into a formatted HTML email digest
6. Sends the digest via Gmail SMTP

## Project Structure

```
bcra-monitor/
├── src/
│   ├── main.py           # Orchestrator - runs the full workflow
│   ├── config.py         # Configuration, constants, environment variables
│   ├── excel_reader.py   # Reads/processes seriesAPI_BCRA_Digest.xlsx
│   ├── charts.py         # Generates matplotlib charts (4 PNGs)
│   ├── scraper.py        # Scrapes BCRA website for news/reports/policy
│   ├── summarizer.py     # AI summaries via Claude Haiku API
│   ├── digest.py         # Compiles HTML email from all components
│   ├── emailer.py        # Sends email via Gmail SMTP
│   └── pdf_processor.py  # Downloads and extracts text from PDFs
├── templates/
│   └── email_template.html   # Jinja2 HTML template for the digest
├── data/
│   ├── seriesAPI_BCRA_Digest.xlsx  # Input data (manually updated)
│   ├── state.json                  # Tracks processed items
│   ├── summaries_cache.json        # Cached AI summaries
│   ├── digest_preview.html         # Last generated preview
│   └── charts/                     # Generated chart images
├── .github/
│   └── workflows/
│       └── weekly-digest.yml   # GitHub Actions (manual trigger)
├── CLAUDE.md             # Project instructions for Claude Code
├── INSTRUCTIONS.md       # Setup and usage guide
└── requirements.txt      # Python dependencies
```

## Key Files

### Source Code

| File | Purpose |
|------|---------|
| [main.py](src/main.py) | Entry point. Orchestrates the 6-step workflow: Excel → Charts → Scrape → Summarize → Build → Send |
| [config.py](src/config.py) | Central configuration. Defines data series, BCRA URLs, display names, loads env vars |
| [excel_reader.py](src/excel_reader.py) | Reads Excel data, calculates weekly/monthly log changes for financial series |
| [charts.py](src/charts.py) | Generates 4 charts: Reserves %, Base Monetaria %, M2 %, Exchange Rate level |
| [scraper.py](src/scraper.py) | Fetches news from BCRA API, scrapes reports and policy pages, tracks new items |
| [summarizer.py](src/summarizer.py) | Downloads PDFs, extracts text, generates AI summaries with Claude Haiku |
| [digest.py](src/digest.py) | Assembles all content into HTML using Jinja2 template |
| [emailer.py](src/emailer.py) | Sends multipart email with embedded chart images via Gmail SMTP |
| [pdf_processor.py](src/pdf_processor.py) | PDF download and text extraction using pdfplumber |

### Data Series Tracked

**With Weekly/Monthly Changes:**
- Reservas Internacionales (USD millions)
- Base Monetaria (ARS millions)
- Tipo de Cambio Oficial
- M2 Transaccional

**Last Value Only:**
- Tasa BADLAR (%)
- Inflacion Esperada REM (%)
- Inflacion Mensual (%)

## Installation

```bash
# Clone repository
git clone <repository-url>
cd bcra-monitor

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file with:

```env
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
EMAIL_TO=recipient@email.com
ANTHROPIC_API_KEY=sk-ant-...
```

**Gmail App Password**: Generate at Google Account → Security → 2-Step Verification → App passwords

## Usage

```bash
# Preview only (no email sent)
python -m src.main --dry-run

# Full run with email
python -m src.main

# Force reprocess all items
python -m src.main --force

# Custom date range (days to look back)
python -m src.main --days 14

# Preview charts only
python -m src.charts --preview
```

## Output

The digest includes:

1. **Datos de la Semana** - Table with current values and changes
2. **Graficos** - 4 embedded charts
3. **Politica Monetaria** - IPOM and policy communications with AI summaries
4. **Informes** - Monthly reports (Informe Monetario, REM) with AI summaries
5. **Noticias** - Recent BCRA news items

See [data/digest_preview.html](data/digest_preview.html) for a sample output.

## GitHub Actions

The workflow in `.github/workflows/weekly-digest.yml` supports:
- Manual trigger via `workflow_dispatch`
- Inputs: `days` (lookback period), `dry_run` (boolean)

**Note:** Currently running manually. Scheduled automation (Monday 7:00 AM Argentina) to be configured later.

## Dependencies

- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `pandas` / `openpyxl` - Excel data handling
- `matplotlib` - Chart generation
- `pdfplumber` - PDF text extraction
- `jinja2` - HTML templating
- `anthropic` - Claude API for AI summaries
- `python-dotenv` - Environment variable loading

## Development Notes

- All content is in Spanish
- State tracking prevents duplicate processing
- AI summaries are cached to reduce API costs
- Charts are embedded as inline images (Content-ID)
- Log difference × 100 used for percentage change calculations
