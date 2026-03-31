"""Update Excel data from BCRA API.

This module downloads the latest monetary data from the BCRA API
and updates the Excel file used by the digest.

Can be run as: python -m src.data_updater
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, date
import urllib3

from .config import EXCEL_FILE

# Suppress SSL warnings (BCRA API has certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BCRA_API_BASE = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias"

# Variable IDs from BCRA API
# 1=Reservas, 15=Base Monetaria, 4=Tipo Cambio, 7=BADLAR,
# 29=Mediana inflacion REM, 197=M2, 27=Inflacion mensual
SERIES_IDS = [1, 15, 4, 7, 29, 197, 27]


def generate_date_ranges(desde: str, hasta: str, max_days: int = 3000) -> list:
    """Generate date ranges of max_days to handle API limits."""
    desde_dt = datetime.strptime(desde, "%Y-%m-%d")
    hasta_dt = datetime.strptime(hasta, "%Y-%m-%d")
    ranges = []
    start = desde_dt
    while start <= hasta_dt:
        end = min(start + timedelta(days=max_days - 1), hasta_dt)
        ranges.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        start = end + timedelta(days=1)
    return ranges


def get_variable_names() -> dict:
    """Fetch variable names from BCRA metadata API."""
    try:
        response = requests.get(BCRA_API_BASE, verify=False, timeout=30)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return {v.get("idVariable"): v.get("descripcion") for v in results}
    except Exception as e:
        print(f"Warning: Could not fetch metadata: {e}")
    return {}


def download_series(ids: list, desde: str, hasta: str) -> pd.DataFrame:
    """Download series from BCRA API and combine into DataFrame."""
    # Get variable names
    var_names = get_variable_names()

    df_final = pd.DataFrame()

    for var_id in ids:
        nombre_var = var_names.get(var_id, f"var_{var_id}")
        todas_filas = []

        for sub_desde, sub_hasta in generate_date_ranges(desde, hasta):
            url = f"{BCRA_API_BASE}/{var_id}?desde={sub_desde}&hasta={sub_hasta}&limit=3000"
            try:
                response = requests.get(url, verify=False, timeout=60)
                if response.status_code == 200:
                    data = response.json().get("results", [])
                    if data:
                        serie = data[0].get("detalle", [])
                        todas_filas.extend(serie)
                else:
                    print(f"Error downloading {var_id} ({sub_desde} to {sub_hasta}): {response.status_code}")
            except Exception as e:
                print(f"Error downloading {var_id}: {e}")

        # Convert to DataFrame
        df_var = pd.DataFrame(todas_filas)
        if not df_var.empty:
            df_var = df_var.rename(columns={"valor": nombre_var})
            df_var = df_var[["fecha", nombre_var]]
            if df_final.empty:
                df_final = df_var
            else:
                df_final = pd.merge(df_final, df_var, on="fecha", how="outer")

        print(f"Downloaded {var_id} ({nombre_var}): {len(todas_filas)} records")

    # Clean up
    df_final["fecha"] = pd.to_datetime(df_final["fecha"], format="%Y-%m-%d", errors="coerce")
    df_final = df_final.sort_values("fecha").reset_index(drop=True)

    return df_final


def update_excel() -> pd.DataFrame:
    """Update the Excel file with fresh data from BCRA API."""
    print("Updating Excel data from BCRA API...")
    print(f"Target file: {EXCEL_FILE}")

    hoy = date.today().strftime("%Y-%m-%d")
    print(f"Date range: 2020-01-01 to {hoy}")

    df = download_series(SERIES_IDS, desde="2020-01-01", hasta=hoy)

    if not df.empty:
        df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
        print(f"Excel updated successfully: {len(df)} rows")
    else:
        print("Warning: No data downloaded, Excel not updated")

    return df


if __name__ == "__main__":
    update_excel()
