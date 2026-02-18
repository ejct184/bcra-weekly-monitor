# BCRA Weekly Monitor - Instructions

## Prerequisites

- Python 3.10+
- Gmail account with 2FA enabled
- Anthropic API key (for AI summaries)

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd bcra-monitor

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### 1. Create `.env` file

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Gmail SMTP credentials
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password

# Email recipients (comma-separated for multiple)
EMAIL_TO=recipient@email.com

# Anthropic API key for AI summaries
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 2. Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication (if not already enabled)
3. Go to "App passwords" (search in account settings)
4. Create a new app password for "Mail"
5. Copy the 16-character password to `GMAIL_APP_PASSWORD`

### 3. Anthropic API Key

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Copy it to `ANTHROPIC_API_KEY`

### 4. Excel Data File

Ensure `seriesAPI_BCRA_Digest.xlsx` is in the project root with the required series data.

## Running the Digest

### Dry Run (no email sent)

```bash
python -m src.main --dry-run
```

This generates a preview at `data/digest_preview.html`.

### Preview in Browser

```bash
python -m src.main --preview
```

Opens the digest in your default browser.

### Send Email

```bash
python -m src.main
```

Sends the digest email and updates the state file.

### Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Generate digest without sending email |
| `--preview` | Open digest in browser |
| `--force` | Ignore state file, process all content |
| `--days N` | Look back N days for news (default: 7) |

### Examples

```bash
# Dry run with 30 days of news
python -m src.main --dry-run --days 30

# Force reprocess everything
python -m src.main --force --preview

# Send email looking back 14 days
python -m src.main --days 14
```

## GitHub Actions Setup

### 1. Add Repository Secrets

Go to your repository Settings > Secrets and variables > Actions, and add:

| Secret | Value |
|--------|-------|
| `GMAIL_USER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | 16-character app password |
| `EMAIL_TO` | Recipient email(s) |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

### 2. Workflow Schedule

The workflow runs automatically every Monday at 7:00 AM Argentina time (10:00 UTC).

To trigger manually:
1. Go to Actions tab
2. Select "BCRA Weekly Digest"
3. Click "Run workflow"
4. Optionally set `days` and `dry_run` parameters

## Project Structure

```
bcra-monitor/
├── src/
│   ├── main.py           # Main orchestrator
│   ├── config.py         # Configuration
│   ├── excel_reader.py   # Excel data processing
│   ├── charts.py         # Chart generation
│   ├── scraper.py        # Web scraping
│   ├── pdf_processor.py  # PDF text extraction
│   ├── summarizer.py     # AI summaries (Claude API)
│   ├── digest.py         # Digest compilation
│   └── emailer.py        # Email sending
├── templates/
│   └── email_template.html
├── data/
│   ├── state.json        # Tracks processed items
│   ├── charts/           # Generated charts
│   └── digest_preview.html
├── seriesAPI_BCRA_Digest.xlsx
├── requirements.txt
├── .env                  # Your credentials (not committed)
└── .github/workflows/
    └── weekly-digest.yml
```

## State Management

The `data/state.json` file tracks which items have been processed:

- Items in state won't show "NUEVO" badge
- After email is sent, new items are added to state
- Use `--force` to ignore state and reprocess everything
- Delete `state.json` to reset (all items will show as new)

## Troubleshooting

### "ANTHROPIC_API_KEY not configured"

Ensure your `.env` file has the API key and you're running from the project directory.

### "Failed to extract PDF: Not a PDF"

Some BCRA pages link to HTML instead of PDFs. The scraper handles this gracefully.

### "No news items found"

Try increasing the `--days` parameter. News older than the specified days are filtered out.

### Gmail authentication errors

1. Verify 2FA is enabled on your Gmail account
2. Ensure you're using an App Password (not your regular password)
3. Check that "Less secure app access" is not blocking (shouldn't be needed with App Password)

### Charts not generating

Ensure the Excel file exists and has data in the expected format with a "fecha" column.
