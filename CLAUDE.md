# BCRA Weekly Monitor

Automated weekly digest of Argentina's Central Bank (BCRA) publications and data releases.

## Project Goal

Build a system that:
1. Scrapes bcra.gob.ar weekly for new content
2. Compiles a formatted digest with key excerpts, tables and charts
3. Emails the digest every Monday morning

## Tech Stack

- Python 3.10+
- `requests` + `BeautifulSoup4` for scraping (upgrade to `playwright` if JS-rendered)
- GitHub Actions for weekly scheduling (possibly, lets discuss it)
- SendGrid or Gmail API for email delivery
- JSON file for state tracking (what's been processed)

## Content to Monitor

From https://www.bcra.gob.ar/:

| Content Type | Location | Frequency |
|--------------|-----------------|-----------|
| Noticias | /noticias/ | Ad-hoc|
| Informes | /informes/ | Monthly/Quarterly |
| Monetary Policy Statements| /politica-monetaria/ | Ad-hoc |

**First task**: Explore the actual BCRA website structure to identify exact URLs and page layouts before writing scrapers.

## High-Frequency Data (Excel Integration)

An Excel file in the project directory (`seriesAPI_BCRA_Digest.xlsx`) contains additional daily high-frequency data that I update weekly.

### Data Series to Track

| Series | Description | Unity |
|--------|-------------|--------|
| Base monetaria | Base monetaria | Millones de ARS |
| Tasa de interés BADLAR de bancos privados | Tasa BADLAR | puntos porcentuales |
| Reservas internacionales | Reservas internacionales | Millones de USD |
| Tipo de cambio minorista (promedio vendedor) | Tipo de cambio oficial | pesos argentinos por usd |
| Mediana de la variación interanual próximos 12 meses del índice de precios al consumidor del relevamiento de expectativas de mercado| Mediana de la inflación anual esperada proximos 12 meses REM| Puntos porcentuales |
| M2 transaccional del sector privado | M2 transaccional del sector privado | Millones de ARS|
|Variación mensual del índice de precios al consumidor| Inflación Mensual| Puntos Porcentuales


### Excel Structure

The workbook has:
Raw daily data with columns
- Date format: YYYY-MM-DD ("fecha" column is the daily indicator)
- Most recent data at bottom

### Weekly Digest Integration

The script should:
1. Read the Excel file
2. For all the series but "Tasa de interés BADLAR de bancos privados","Mediana de la variación interanual próximos 12 meses del índice de precios al consumidor del relevamiento de expectativas de mercado" and "Variación mensual del índice de precios al consumidor" calculate week-over-week and monthly changes ( log difference * 100 ) for the last available value
3. Generate summary table for the email:
   - Current value
   - Weekly change
   - Monthly change (if data available)
4. For the series "Tasa de interés BADLAR de bancos privados" ,"Mediana de la variación interanual próximos 12 meses del índice de precios al consumidor del relevamiento de expectativas de mercado" and "Variación mensual del índice de precios al consumidor"  just report Last Available Value [an indicate if there is a a new available inflation expectations (REM) / inflation data ]
4. Create simple daily charts [showing 1 year of data]:
   - Reserves monthly change (%)
   - Monetary base monthly change
   - M2 monthly change
   - Exchange rate level
5. Embed table and charts in the HTML email

### Chart Specifications

If generating charts:
- Use the publication quality plots SKILL
- Size: ~600px wide for email compatibility
- Spanish labels (e.g., "Reservas Internacionales (%)")
- Include date range in chart title

## Project Structure

```
bcra-monitor/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── src/
│   ├── scraper.py          # Web scraping logic
│   ├── excel_reader.py     # Read and process Excel data
│   ├── charts.py           # Generate matplotlib charts
│   ├── digest.py           # Compile content into digest
│   ├── emailer.py          # Email sending logic
│   └── main.py             # Orchestrate the workflow
├── templates/
│   └── email_template.html # HTML email template
├── data/
│   ├── bcra_data.xlsx      # High-frequency data (manually updated)
│   ├── state.json          # Track processed items
│   └── charts/             # Generated chart images
├── .github/
│   └── workflows/
│       └── weekly-digest.yml  # GitHub Actions schedule
└── .env.example            # Environment variables template
```

## Output Format

Weekly email digest with sections:

1. **Header**: "BCRA Monitor Semanal - [date range]"
2. **Datos de la Semana** (table):
   | Variable | Último | Var. Semanal | Var. Mensual |
   |----------|--------|--------------|--------------|
   | Reservas (USD mm) | 28,450 | -320 (-1.1%) | -1,200 (-4.0%) |
   | Base Monetaria (ARS bn) | 12,500 | +180 (+1.5%) | +850 (+7.3%) |
   | TC Oficial | 1,050 | +15 (+1.4%) | +62 (+6.3%) |
3. **Gráficos**: Embedded charts for key variables.
4. **Política Monetaria**: Any IPOM updates (and summary), or new comunicados de política monetaria (and summary)
5. **Informes**: Resumen de Nuevos: Informes Monetarios Mensuales / Relevamiento de Expectativas de Mercado (REM) / Boletín Estadístico
6. **Noticias**: Resumen de Nuevas noticias del BCRA

Keep formatting clean and professional. Content in Spanish.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Required packages:
# requests, beautifulsoup4, openpyxl, pandas, matplotlib, sendgrid (or google-api-python-client for Gmail)

# Run scraper manually (test)
python src/main.py --dry-run

# Run full workflow (scrape + email)
python src/main.py

# Check what's in state file
cat data/state.json

# Preview charts only (for testing)
python src/charts.py --preview
```

## Environment Variables

```
SENDGRID_API_KEY=xxx        # Or use Gmail
EMAIL_TO=your@email.com
EMAIL_FROM=bcra-monitor@yourdomain.com
```

## Development Workflow

1. **Phase 1**: Website exploration - Map BCRA site structure, identify URLs
2. **Phase 2**: Excel integration - Build reader for `seriesAPI_BCRA_Digest.xlsx`, calculate changes, generate charts
3. **Phase 3**: Build scraper - Start with comunicados, then expand to other content types
4. **Phase 4**: Digest formatting - Create HTML email template combining data tables, charts, and scraped content
5. **Phase 5**: Email integration - Connect SendGrid/Gmail
6. **Phase 6**: Scheduling - Set up GitHub Actions
7. **Phase 7**: Testing - Run for 2-3 weeks manually before automating

## Important Notes

- BCRA website may change structure; build scrapers defensively
- Some content is PDF-based; may need `pdfplumber` or similar for extraction
- Rate limit requests to avoid being blocked (add delays between fetches)
- Store state in JSON to track last run date and processed item IDs
- All content should preserve original Spanish text
- NEVER USE CHECKMARK CHARACTERS OR EMOJIS IN THE CODE

## Error Handling

- If scraping fails, send a "digest unavailable" email with error summary
- Log all errors to a file for debugging
- Don't crash on individual page failures; continue with other content types