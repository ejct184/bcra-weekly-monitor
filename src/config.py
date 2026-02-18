"""Configuration and constants for BCRA Weekly Monitor."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHARTS_DIR = DATA_DIR / "charts"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
EXCEL_FILE = PROJECT_ROOT / "seriesAPI_BCRA_Digest.xlsx"
STATE_FILE = DATA_DIR / "state.json"

# Ensure directories exist
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Series configuration
# Series that need week-over-week and monthly changes (log diff × 100)
SERIES_WITH_CHANGES = [
    "Reservas internacionales",
    "Base monetaria",
    "Tipo de cambio minorista (promedio vendedor)",
    "M2 transaccional del sector privado",
]

# Series that only report last value (no changes calculated)
SERIES_LAST_VALUE_ONLY = [
    "Tasa de interés BADLAR de bancos privados",
    "Mediana de la variación interanual próximos 12 meses del índice de precios al consumidor del relevamiento de expectativas de mercado",
    "Variación mensual del índice de precios al consumidor",
]

# Display names for email (shorter versions)
SERIES_DISPLAY_NAMES = {
    "Reservas internacionales": "Reservas (USD mm)",
    "Base monetaria": "Base Monetaria (ARS mm)",
    "Tipo de cambio minorista (promedio vendedor)": "TC Oficial",
    "M2 transaccional del sector privado": "M2 Transaccional (ARS mm)",
    "Tasa de interés BADLAR de bancos privados": "Tasa BADLAR (%)",
    "Mediana de la variación interanual próximos 12 meses del índice de precios al consumidor del relevamiento de expectativas de mercado": "Inflación Esperada REM (%)",
    "Variación mensual del índice de precios al consumidor": "Inflación Mensual (%)",
}

# BCRA Website URLs
BCRA_NEWS_API = "https://www.bcra.gob.ar/wp-json/bcra/v1/noticias"
BCRA_INFORMES_URL = "https://www.bcra.gob.ar/informes/"
BCRA_POLITICA_URL = "https://www.bcra.gob.ar/politica-monetaria/"

# Chart settings
CHART_WIDTH_PX = 600
CHART_DPI = 100
CHART_DAYS = 365  # 1 year of data

# Load environment variables
import os
from dotenv import load_dotenv

load_dotenv()

# Email settings
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# Claude API for summaries
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
