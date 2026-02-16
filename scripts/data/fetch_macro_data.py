# scripts/data/fetch_macro_data.py
"""
Fetch Singapore macroeconomic data for VAR modeling.

Data sources:
- MAS (Monetary Authority of Singapore): SORA rates
- SingStat: CPI, GDP
- MND: Policy dates (manual for now)

Usage:
    from scripts.data.fetch_macro_data import fetch_all_macro_data

    macro_data = fetch_all_macro_data(start_date='2021-01', end_date='2026-02')
"""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.core.config import Config

logger = logging.getLogger(__name__)


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
    Fetch Consumer Price Index (CPI) from SingStat.

    Args:
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format, default: current month)
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: date, cpi

    Note:
        For MVP, uses mock data. Replace with SingStat API integration.
    """
    logger.info(f"Fetching CPI data from {start_date} to {end_date or 'present'}")

    # TODO: Replace with SingStat Table Builder API
    # For now, generate mock data (~2-3% annual inflation)
    dates = pd.date_range(start=start_date, periods=60, freq='ME')

    # Base CPI = 100 in 2021, grows at ~2.5% annually
    cpi_values = []
    base_cpi = 100.0

    for i, date in enumerate(dates):
        months_elapsed = i
        inflation_factor = (1 + 0.025 / 12) ** months_elapsed
        noise = (hash(str(date)) % 100) / 2000 - 0.025  # Small noise
        cpi_values.append(base_cpi * inflation_factor + noise)

    df = pd.DataFrame({
        'date': dates,
        'cpi': cpi_values
    })

    logger.info(f"Fetched {len(df)} CPI observations")

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved CPI data to {save_path}")

    return df


def fetch_gdp_data(
    save_path: Path = None
) -> pd.DataFrame:
    """
    Fetch Singapore GDP growth data (quarterly).

    Args:
        save_path: If provided, save to this parquet path

    Returns:
        DataFrame with columns: quarter, gdp_growth

    Note:
        For MVP, uses mock data. Singapore GDP growth ~3% annually.
    """
    logger.info("Fetching GDP growth data")

    # Generate quarterly data 2021 Q1 to 2026 Q1
    quarters = pd.date_range(start='2021-01', periods=21, freq='QE')

    # Mock GDP growth (3% average with volatility)
    np.random.seed(42)
    gdp_growth = np.random.normal(0.03, 0.01, len(quarters))  # Mean 3%, std 1%

    df = pd.DataFrame({
        'quarter': quarters,
        'gdp_growth': gdp_growth
    })

    logger.info(f"Fetched {len(df)} GDP observations")

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(save_path, compression='snappy', index=False)
        logger.info(f"Saved GDP data to {save_path}")

    return df


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
        Dictionary with keys: 'sora', 'cpi', 'gdp', 'policies'
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
        'policies': policies
    }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    fetch_all_macro_data()
