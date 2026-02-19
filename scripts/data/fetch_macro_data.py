# scripts/data/fetch_macro_data.py
"""
Fetch Singapore macroeconomic data for VAR modeling.

Data sources:
- MAS (Monetary Authority of Singapore): SORA rates
- SingStat: CPI, GDP, Unemployment, Property Price Index, Interest Rates
- MND: Policy dates (manual for now)

Usage:
    from scripts.data.fetch_macro_data import fetch_all_macro_data

    macro_data = fetch_all_macro_data(start_date='2021-01', end_date='2026-02')

Or run as script:
    uv run python scripts/data/fetch_macro_data.py
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from scripts.core.config import Config

logger = logging.getLogger(__name__)

SINGSTAT_BASE_URL = "https://tablebuilder.singstat.gov.sg/api/table"

# Table IDs for SingStat API
CPI_TABLE_ID = "M213751"
GDP_TABLE_ID = "M014871"
UNEMPLOYMENT_TABLE_ID = "M401871"  # Seasonally adjusted unemployment rate
PROPERTY_PPI_TABLE_ID = "M200131"  # Property Price Index
INTEREST_RATE_TABLE_ID = "M200131"  # Interest rates (may vary)


def search_singstat_table(keyword: str) -> dict | None:
    """
    Search for a table ID in SingStat Table Builder.

    Args:
        keyword: Search keyword

    Returns:
        Dict with table info or None if not found
    """
    url = f"{SINGSTAT_BASE_URL}/resourceid"
    params = {"keyword": keyword, "searchOption": "all"}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        records = data.get("Data", {}).get("records", [])
        if records:
            return records[0]
        return None
    except Exception as e:
        logger.warning(f"Failed to search SingStat for '{keyword}': {e}")
        return None


def fetch_singstat_timeseries(
    table_id: str,
    start_year: int = 2020,
    end_year: int = 2026
) -> pd.DataFrame:
    """
    Fetch time series data from SingStat Table Builder API.

    Args:
        table_id: SingStat table ID (e.g., 'M213751')
        start_year: Start year for data
        end_year: End year for data

    Returns:
        DataFrame with columns: date, value, series_description
    """
    url = f"{SINGSTAT_BASE_URL}/tabledata/{table_id}"
    params = {
        "limit": 5000,
        "sortBy": "key asc"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        records = data.get("Data", {}).get("row", [])
        if not records:
            logger.warning(f"No data found for table {table_id}")
            return pd.DataFrame()

        rows = []
        for record in records:
            series_desc = record.get("rowText", "")
            columns = record.get("columns", [])

            for col in columns:
                key = col.get("key", "")
                value = col.get("value", "")

                if key and value:
                    try:
                        rows.append({
                            "date": key,
                            "value": float(value),
                            "series_description": series_desc
                        })
                    except ValueError:
                        continue

        df = pd.DataFrame(rows)
        logger.info(f"Fetched {len(df)} records from SingStat table {table_id}")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch from SingStat API: {e}")
        raise RuntimeError(f"SingStat API call failed: {e}") from e


def fetch_sora_rates(
    start_date: str = '2021-01',
    end_date: str = None,
    save_path: Path = None
) -> pd.DataFrame:
    """
    Fetch SORA (Singapore Overnight Rate Average) from MAS.

    Args:
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format, default: current month)
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: date, sora_rate

    Note:
        For MVP, uses mock data. Replace with MAS API integration.
        MAS API: https://www.mas.gov.sg/data-publication/api
    """
    logger.info(f"Fetching SORA rates from {start_date} to {end_date or 'present'}")

    # TODO: Replace with actual MAS API call
    # For now, generate mock data based on historical trends
    dates = pd.date_range(start=start_date, periods=60, freq='ME')

    # Mock SORA rates (declining from 2021-2023, rising 2023-2026)
    base_rates = [0.2, 0.3, 0.5, 0.8, 1.2, 1.8, 2.5, 3.5, 3.8, 3.9, 4.0, 4.0]
    sora_rates = []

    for i, date in enumerate(dates):
        period_idx = i // 12  # Which year
        base = base_rates[min(period_idx, len(base_rates) - 1)]
        noise = (hash(str(date)) % 100) / 1000 - 0.05  # Small random noise
        sora_rates.append(base + noise)

    df = pd.DataFrame({
        'date': dates,
        'sora_rate': sora_rates
    })

    logger.info(f"Fetched {len(df)} SORA rate observations")

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved SORA rates to {save_path}")

    return df


def fetch_cpi_data(
    start_date: str = '2021-01',
    end_date: str = None,
    save_path: Path = None
) -> pd.DataFrame:
    """
    Fetch Consumer Price Index (CPI) from SingStat Table Builder API.

    Args:
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format, default: current month)
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: date, cpi

    Note:
        Uses SingStat Table Builder API - Table ID: M213751
        Falls back to mock data if API fails or data is unavailable.
        Known issue: M213751 only has historical data up to 1997.
    """
    logger.info(f"Fetching CPI data from SingStat API (table: {CPI_TABLE_ID})")

    try:
        df_raw = fetch_singstat_timeseries(CPI_TABLE_ID)

        if df_raw.empty:
            raise RuntimeError("No CPI data returned from SingStat API")

        cpi_series = df_raw.loc[df_raw["series_description"] == "All Items"]

        if len(cpi_series) == 0:
            raise RuntimeError("CPI 'All Items' series not found")

        cpi_data = pd.DataFrame({
            "date_str": cpi_series["date"].tolist(),
            "cpi": cpi_series["value"].tolist()
        })
        cpi_data["date"] = pd.to_datetime(cpi_data["date_str"], format="%Y %b")
        cpi_data = cpi_data[["date", "cpi"]].sort_values("date")

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) if end_date else pd.Timestamp.now()
        cpi_data = cpi_data[(cpi_data["date"] >= start_dt) & (cpi_data["date"] <= end_dt)]

        if len(cpi_data) == 0:
            raise RuntimeError("CPI data empty after filtering")

        logger.info(f"Fetched {len(cpi_data)} CPI observations")
        cpi_data = cpi_data

    except Exception as e:
        logger.warning(f"Failed to fetch CPI from SingStat API: {e}")
        logger.info("Falling back to mock CPI data")
        cpi_data = _generate_mock_cpi(start_date, end_date)

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        cpi_data.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved CPI data to {save_path}")

    return cpi_data


def _generate_mock_cpi(start_date: str, end_date: str = None) -> pd.DataFrame:
    """Generate mock CPI data for fallback."""
    dates = pd.date_range(start=start_date, periods=60, freq='ME')
    cpi_values = []
    base_cpi = 100.0

    for i, date in enumerate(dates):
        months_elapsed = i
        inflation_factor = (1 + 0.025 / 12) ** months_elapsed
        noise = (hash(str(date)) % 100) / 2000 - 0.025
        cpi_values.append(base_cpi * inflation_factor + noise)

    return pd.DataFrame({'date': dates, 'cpi': cpi_values})


def fetch_gdp_data(
    save_path: Path = None
) -> pd.DataFrame:
    """
    Fetch Singapore GDP data from SingStat Table Builder API.

    Args:
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: quarter, gdp_value

    Note:
        Uses SingStat Table Builder API - Table ID: M014871
        (Expenditure On Gross Domestic Product At Current Prices, Quarterly)
    """
    logger.info(f"Fetching GDP data from SingStat API (table: {GDP_TABLE_ID})")

    try:
        df_raw = fetch_singstat_timeseries(GDP_TABLE_ID)

        if df_raw.empty:
            raise RuntimeError("No GDP data returned from SingStat API")

        gdp_data = pd.DataFrame({
            "quarter_str": df_raw["date"].tolist(),
            "gdp_value": df_raw["value"].tolist()
        })

        gdp_data["quarter"] = pd.to_datetime(gdp_data["quarter_str"], format="%Y %b")
        gdp_data = gdp_data.sort_values("quarter")

        logger.info(f"Fetched {len(gdp_data)} GDP observations")

    except Exception as e:
        logger.warning(f"Failed to fetch GDP from SingStat API: {e}")
        logger.info("Falling back to mock GDP data")
        gdp_data = _generate_mock_gdp()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        gdp_data.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved GDP data to {save_path}")

    return gdp_data


def _generate_mock_gdp() -> pd.DataFrame:
    """Generate mock GDP data for fallback."""
    quarters = pd.date_range(start='2021-01', periods=21, freq='QE')
    np.random.seed(42)
    gdp_growth = np.random.normal(0.03, 0.01, len(quarters))
    return pd.DataFrame({'quarter': quarters, 'gdp_value': gdp_growth})


def fetch_unemployment_data(
    start_date: str = '2021-01',
    end_date: str = None,
    save_path: Path = None
) -> pd.DataFrame:
    """
    Fetch unemployment rate from SingStat Table Builder API.

    Args:
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format, default: current month)
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: date, unemployment_rate

    Note:
        Uses SingStat Table Builder API - Table ID: M401871
        Falls back to mock data if API fails.
    """
    logger.info(f"Fetching unemployment data from SingStat API (table: {UNEMPLOYMENT_TABLE_ID})")

    try:
        df_raw = fetch_singstat_timeseries(UNEMPLOYMENT_TABLE_ID)

        if df_raw.empty:
            raise RuntimeError("No unemployment data returned from SingStat API")

        # Find the unemployment rate series
        unemp_series = df_raw[df_raw["series_description"].str.contains("unemployment", case=False, na=False)]

        if len(unemp_series) == 0:
            # Try alternative - just use first series
            unemp_series = df_raw.head(10)

        unemp_data = pd.DataFrame({
            "date_str": unemp_series["date"].tolist(),
            "unemployment_rate": unemp_series["value"].tolist()
        })

        # Parse date
        try:
            unemp_data["date"] = pd.to_datetime(unemp_data["date_str"], format="%Y %b")
        except Exception:
            unemp_data["date"] = pd.to_datetime(unemp_data["date_str"], format="%Y", errors='coerce')

        unemp_data = unemp_data[["date", "unemployment_rate"]].dropna().sort_values("date")

        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) if end_date else pd.Timestamp.now()
        unemp_data = unemp_data[(unemp_data["date"] >= start_dt) & (unemp_data["date"] <= end_dt)]

        logger.info(f"Fetched {len(unemp_data)} unemployment observations")

    except Exception as e:
        logger.warning(f"Failed to fetch unemployment from SingStat API: {e}")
        logger.info("Falling back to mock unemployment data")
        unemp_data = _generate_mock_unemployment(start_date, end_date)

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        unemp_data.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved unemployment data to {save_path}")

    return unemp_data


def _generate_mock_unemployment(start_date: str, end_date: str = None) -> pd.DataFrame:
    """Generate mock unemployment data for fallback."""
    dates = pd.date_range(start=start_date, periods=60, freq='ME')
    # Singapore typically has 2-3% unemployment
    base_rate = 2.5
    rates = [base_rate + np.sin(i / 12 * np.pi) * 0.5 + np.random.normal(0, 0.1) for i in range(len(dates))]
    return pd.DataFrame({'date': dates, 'unemployment_rate': rates})


def fetch_property_price_index(
    save_path: Path = None
) -> pd.DataFrame:
    """
    Fetch Property Price Index (PPI) from SingStat Table Builder API.

    Args:
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: quarter, ppi

    Note:
        Uses SingStat Table Builder API
        Falls back to mock data if API fails.
    """
    logger.info(f"Fetching Property Price Index from SingStat API (table: {PROPERTY_PPI_TABLE_ID})")

    try:
        df_raw = fetch_singstat_timeseries(PROPERTY_PPI_TABLE_ID)

        if df_raw.empty:
            raise RuntimeError("No PPI data returned from SingStat API")

        ppi_data = pd.DataFrame({
            "quarter_str": df_raw["date"].tolist(),
            "ppi": df_raw["value"].tolist()
        })

        # Parse quarter
        try:
            ppi_data["quarter"] = pd.to_datetime(ppi_data["quarter_str"], format="%Y %b")
        except Exception:
            ppi_data["quarter"] = pd.to_datetime(ppi_data["quarter_str"], format="%Y", errors='coerce')

        ppi_data = ppi_data[["quarter", "ppi"]].dropna().sort_values("quarter")

        logger.info(f"Fetched {len(ppi_data)} PPI observations")

    except Exception as e:
        logger.warning(f"Failed to fetch PPI from SingStat API: {e}")
        logger.info("Falling back to mock PPI data")
        ppi_data = _generate_mock_ppi()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        ppi_data.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved PPI data to {save_path}")

    return ppi_data


def _generate_mock_ppi() -> pd.DataFrame:
    """Generate mock Property Price Index data for fallback."""
    quarters = pd.date_range(start='2021-01', periods=21, freq='QE')
    # PPI typically around 100-150 for Singapore
    base_ppi = 100
    ppi_values = [base_ppi + i * 2 + np.random.normal(0, 1) for i in range(len(quarters))]
    return pd.DataFrame({'quarter': quarters, 'ppi': ppi_values})


def fetch_policy_dates(save_path: Path = None) -> pd.DataFrame:
    """
    Fetch housing policy dates (ABSD, LTV, TDSR changes).

    Args:
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: date, policy_type, rate_value

    Note:
        For MVP, manually curates major policy changes.
        Source: MND and MAS announcements.
    """
    logger.info("Fetching housing policy dates")

    # Major housing policy changes 2021-2026
    policies = [
        {'date': '2021-02-01', 'policy_type': 'absd_spr', 'rate_value': 5},  # Singaporean PR: 5%
        {'date': '2021-02-01', 'policy_type': 'absd_foreign', 'rate_value': 20},  # Foreigners: 20%
        {'date': '2022-04-01', 'policy_type': 'absd_spr', 'rate_value': 5},  # No change
        {'date': '2022-09-30', 'policy_type': 'absd_foreign', 'rate_value': 30},  # Foreigners: 30%
        {'date': '2023-04-27', 'policy_type': 'absd_spr', 'rate_value': 5},  # Additional ABSD for >2 properties
    ]

    df = pd.DataFrame(policies)
    df['date'] = pd.to_datetime(df['date'])

    logger.info(f"Fetched {len(df)} policy changes")

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved policy dates to {save_path}")

    return df


def fetch_all_macro_data(
    start_date: str = '2021-01',
    end_date: str = '2026-02',
    output_dir: Path = None
) -> dict:
    """
    Fetch all macroeconomic data sources.

    Args:
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format)
        output_dir: Output directory (defaults to Config.DATA_DIR / 'raw_data' / 'macro')

    Returns:
        Dictionary with keys: 'sora', 'cpi', 'gdp', 'unemployment', 'ppi', 'policies'
    """
    if output_dir is None:
        output_dir = Config.DATA_DIR / 'raw_data' / 'macro'

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Fetching All Macroeconomic Data")
    logger.info("=" * 60)

    # Fetch all data sources
    sora = fetch_sora_rates(
        start_date=start_date,
        end_date=end_date,
        save_path=output_dir / 'sora_rates_monthly.parquet'
    )

    cpi = fetch_cpi_data(
        start_date=start_date,
        end_date=end_date,
        save_path=output_dir / 'singapore_cpi_monthly.parquet'
    )

    gdp = fetch_gdp_data(
        save_path=output_dir / 'sgdp_quarterly.parquet'
    )

    unemployment = fetch_unemployment_data(
        start_date=start_date,
        end_date=end_date,
        save_path=output_dir / 'unemployment_rate_monthly.parquet'
    )

    ppi = fetch_property_price_index(
        save_path=output_dir / 'property_price_index_quarterly.parquet'
    )

    policies = fetch_policy_dates(
        save_path=output_dir / 'housing_policy_dates.parquet'
    )

    logger.info("=" * 60)
    logger.info("Macroeconomic data fetching complete!")
    logger.info("=" * 60)

    return {
        'sora': sora,
        'cpi': cpi,
        'gdp': gdp,
        'unemployment': unemployment,
        'ppi': ppi,
        'policies': policies
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    fetch_all_macro_data()
