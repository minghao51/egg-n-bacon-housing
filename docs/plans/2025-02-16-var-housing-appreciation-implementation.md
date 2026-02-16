# Two-Stage Hierarchical VAR for Housing Appreciation Prediction - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a time series forecasting system using regional VAR and planning area ARIMAX models to predict housing price appreciation (1-3 years at area level, 3-5 years at regional level) with causal inference on appreciation drivers.

**Architecture:** Two-stage hierarchical approach: Stage 1 uses Panel VAR across 7 regions with endogenous variables (appreciation, volume, prices) and exogenous macroeconomic/amenity factors; Stage 2 uses ARIMAX models for ~20 high-volume planning areas using regional forecasts as exogenous predictors. Regional aggregation handles spatial autocorrelation (Moran's I = 0.67).

**Tech Stack:** Python 3.11+, pandas, numpy, statsmodels (VAR, ARIMA, Granger causality), pytest, scipy. Data sources: L3 unified dataset, L5 growth metrics, external macro data (MAS SORA, SingStat).

**Design Document:** `docs/analytics/20250216-plan-autoregression-var-housing-appreciation.md`

---

## Task 1: Create Regional Mapping Configuration

**Files:**
- Create: `scripts/core/config/regional_mapping.py`
- Test: `tests/core/test_regional_mapping.py`

**Step 1: Write failing test for regional mapping**

```python
# tests/core/test_regional_mapping.py
import pytest
from scripts.core.config.regional_mapping import get_region_for_planning_area

def test_ccr_planning_areas():
    """Test CCR planning areas mapped correctly."""
    ccr_areas = ['Downtown', 'Newton', 'Orchard', 'Marina Bay', 'Tanglin', 'Bukit Merah']
    for area in ccr_areas:
        assert get_region_for_planning_area(area) == 'CCR'

def test_ocr_east_planning_areas():
    """Test OCR East planning areas mapped correctly."""
    east_areas = ['Bedok', 'Pasir Ris', 'Tampines', 'Changi']
    for area in east_areas:
        assert get_region_for_planning_area(area) == 'OCR East'

def test_unknown_area_returns_none():
    """Test unknown planning area returns None."""
    assert get_region_for_planning_area('UnknownArea') is None

def test_all_planning_areas_have_regions():
    """Test all common planning areas are mapped."""
    from scripts.core.config.regional_mapping import get_all_regional_mappings

    mappings = get_all_regional_mappings()
    assert len(mappings) > 50  # Should cover most planning areas
    assert 'Downtown' in mappings
    assert 'Bedok' in mappings
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/core/test_regional_mapping.py -v
```

Expected: `ModuleNotFoundError: scripts.core.config.regional_mapping`

**Step 3: Create regional mapping module**

```python
# scripts/core/config/regional_mapping.py
"""
Regional mapping configuration for Singapore planning areas.

Groups 50+ planning areas into 7 regions for VAR modeling:
- CCR (Core Central Region)
- RCR (Rest of Central Region)
- OCR East, North-East, North, West, Central
"""

from typing import Dict, Optional

# Regional mapping dictionary
PLANNING_AREA_TO_REGION = {
    # CCR (Core Central Region)
    'Downtown': 'CCR',
    'Newton': 'CCR',
    'Orchard': 'CCR',
    'Marina Bay': 'CCR',
    'Tanglin': 'CCR',
    'River Valley': 'CCR',
    'Bukit Merah': 'CCR',  # Includes part of CCR

    # RCR (Rest of Central Region)
    'Queenstown': 'RCR',
    'Geylang': 'RCR',
    'Kallang': 'RCR',
    'Bishan': 'RCR',  # Sometimes classified as RCR
    'Toa Payoh': 'RCR',

    # OCR East
    'Bedok': 'OCR East',
    'Pasir Ris': 'OCR East',
    'Tampines': 'OCR East',
    'Changi': 'OCR East',
    'Simei': 'OCR East',

    # OCR North-East
    'Ang Mo Kio': 'OCR North-East',
    'Serangoon': 'OCR North-East',
    'Hougang': 'OCR North-East',
    'Sengkang': 'OCR North-East',
    'Punggol': 'OCR North-East',

    # OCR North
    'Woodlands': 'OCR North',
    'Yishun': 'OCR North',
    'Sembawang': 'OCR North',

    # OCR West
    'Jurong': 'OCR West',
    'Bukit Batok': 'OCR West',
    'Bukit Panjang': 'OCR West',
    'Choa Chu Kang': 'OCR West',
    'Clementi': 'OCR West',

    # OCR Central
    'Central': 'OCR Central',
    'Novena': 'OCR Central',
    'Thomson': 'OCR Central',
}


def get_region_for_planning_area(planning_area: str) -> Optional[str]:
    """
    Get region for a given planning area.

    Args:
        planning_area: Planning area name (e.g., 'Downtown')

    Returns:
        Region name ('CCR', 'RCR', 'OCR East', etc.) or None if not found

    Example:
        >>> get_region_for_planning_area('Downtown')
        'CCR'
        >>> get_region_for_planning_area('Unknown')
        None
    """
    return PLANNING_AREA_TO_REGION.get(planning_area)


def get_all_regional_mappings() -> Dict[str, str]:
    """
    Get all planning area to region mappings.

    Returns:
        Dictionary mapping planning_area -> region
    """
    return PLANNING_AREA_TO_REGION.copy()


def get_regions() -> list:
    """
    Get list of all regions.

    Returns:
        List of region names
    """
    return sorted(set(PLANNING_AREA_TO_REGION.values()))


def get_planning_areas_in_region(region: str) -> list:
    """
    Get all planning areas belonging to a region.

    Args:
        region: Region name (e.g., 'CCR')

    Returns:
        List of planning area names in that region

    Raises:
        ValueError: If region is not found
    """
    areas = [area for area, reg in PLANNING_AREA_TO_REGION.items() if reg == region]

    if not areas and region not in get_regions():
        raise ValueError(f"Unknown region: {region}")

    return sorted(areas)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/core/test_regional_mapping.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add scripts/core/config/regional_mapping.py tests/core/test_regional_mapping.py
git commit -m "feat(analytics): add regional mapping for 7 Singapore regions

- Maps 50+ planning areas to 7 regions (CCR, RCR, OCR East/North-East/North/West/Central)
- Provides lookup functions for area->region and region->areas
- Includes comprehensive unit tests

Part of VAR housing appreciation forecasting system"
```

---

## Task 2: Fetch Macroeconomic Data

**Files:**
- Create: `scripts/data/fetch_macro_data.py`
- Create: `data/raw_data/macro/.gitkeep`
- Test: `tests/data/test_fetch_macro_data.py`

**Step 1: Write failing test for macro data fetching**

```python
# tests/data/test_fetch_macro_data.py
import pytest
import pandas as pd
from pathlib import Path
from scripts.data.fetch_macro_data import fetch_sora_rates, fetch_cpi_data

def test_fetch_sora_rates_returns_dataframe():
    """Test SORA rate fetching returns DataFrame with correct columns."""
    df = fetch_sora_rates()

    assert isinstance(df, pd.DataFrame)
    assert 'date' in df.columns
    assert 'sora_rate' in df.columns
    assert len(df) > 0

def test_fetch_cpi_returns_dataframe():
    """Test CPI fetching returns DataFrame."""
    df = fetch_cpi_data()

    assert isinstance(df, pd.DataFrame)
    assert 'date' in df.columns
    assert 'cpi' in df.columns
    assert len(df) > 0

def test_macro_data_saved_to_parquet():
    """Test macro data is saved to correct location."""
    from scripts.core.config import Config

    output_path = Config.DATA_DIR / 'raw_data' / 'macro' / 'sora_rates.parquet'

    fetch_sora_rates(save_path=output_path)

    assert output_path.exists()
    df = pd.read_parquet(output_path)
    assert len(df) > 0
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/data/test_fetch_macro_data.py -v
```

Expected: `ModuleNotFoundError: scripts.data.fetch_macro_data`

**Step 3: Create macro data fetching module**

```python
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

import pandas as pd
import requests

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
    dates = pd.date_range(start=start_date, periods=60, freq='M')

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
    dates = pd.date_range(start=start_date, periods=60, freq='M')

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
    quarters = pd.date_range(start='2021-01', periods=21, freq='Q')

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
        {'date': '2022-09-1', 'policy_type': 'absd_foreign', 'rate_value': 30},  # Foreigners: 30%
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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/data/test_fetch_macro_data.py -v
```

Expected: All tests PASS (with mock data)

**Step 5: Commit**

```bash
git add scripts/data/fetch_macro_data.py tests/data/test_fetch_macro_data.py data/raw_data/macro/.gitkeep
git commit -m "feat(data): add macroeconomic data fetching module

- Fetches SORA rates, CPI, GDP growth, and policy dates
- Uses mock data for MVP (TODO: integrate MAS/SingStat APIs)
- Saves to data/raw_data/macro/ as parquet files
- Includes unit tests for data fetching

Part of VAR housing appreciation forecasting system"
```

---

## Task 3: Create Time Series Dataset Preparation Pipeline

**Files:**
- Create: `scripts/analytics/pipelines/prepare_timeseries_data.py`
- Create: `tests/analytics/test_prepare_timeseries_data.py`
- Test: `tests/analytics/pipelines/test_prepare_timeseries_data.py`

**Step 1: Write failing test for data preparation**

```python
# tests/analytics/test_prepare_timeseries_data.py
import pytest
import pandas as pd
from scripts.analytics.pipelines.prepare_timeseries_data import (
    aggregate_to_regional_timeseries,
    create_area_timeseries,
    handle_missing_months
)

def test_aggregate_to_regional_creates_correct_columns():
    """Test regional aggregation creates required columns."""
    # Create sample transaction data
    transactions = pd.DataFrame({
        'planning_area': ['Downtown', 'Downtown', 'Bedok', 'Bedok'],
        'transaction_date': pd.to_datetime(['2021-01', '2021-02', '2021-01', '2021-02']),
        'price_psf': [2000, 2100, 800, 820],
        'yoy_change_pct': [5.0, 5.5, 3.0, 3.2]
    })

    regional = aggregate_to_regional_timeseries(transactions)

    assert 'region' in regional.columns
    assert 'month' in regional.columns
    assert 'regional_appreciation' in regional.columns
    assert 'regional_volume' in regional.columns
    assert len(regional) == 2  # 2 months, 2 regions

def test_handle_missing_months_interpolates():
    """Test missing months are interpolated."""
    dates = pd.date_range('2021-01', '2021-06', freq='M')
    values = pd.Series([1.0, 2.0, None, None, 5.0, 6.0], index=dates)

    filled = handle_missing_months(values, max_gap=2)

    assert filled.isna().sum() == 0
    assert filled.loc['2021-03'] == 3.5  # Linear interpolation

def test_create_area_timeseries_filters_low_volume_areas():
    """Test low-volume areas are filtered out."""
    from scripts.analytics.pipelines.prepare_timeseries_data import MIN_MONTHS_REQUIRED

    # Create area with only 10 months
    low_volume_area = pd.DataFrame({
        'area': ['SmallArea'] * 10,
        'month': pd.date_range('2021-01', periods=10, freq='M'),
        'appreciation': [5.0] * 10
    })

    filtered = create_area_timeseries(low_volume_area)

    assert len(filtered) == 0  # Should be filtered out
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/analytics/test_prepare_timeseries_data.py -v
```

Expected: `ModuleNotFoundError` for all functions

**Step 3: Implement time series preparation module**

```python
# scripts/analytics/pipelines/prepare_timeseries_data.py
"""
Prepare time series datasets for VAR/AR modeling.

This module transforms L3 unified data and L5 growth metrics into
time series datasets suitable for regional VAR and planning area ARIMAX models.

Outputs:
- L5_regional_timeseries.parquet (7 regions × 60 months)
- L5_area_timeseries.parquet (~20 areas × 60 months)

Usage:
    from scripts.analytics.pipelines.prepare_timeseries_data import run_preparation_pipeline

    regional_data, area_data = run_preparation_pipeline(
        start_date='2021-01',
        end_date='2026-02'
    )
"""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.core.config import Config
from scripts.core.config.regional_mapping import get_region_for_planning_area
from scripts.core.data_helpers import load_parquet, save_parquet

logger = logging.getLogger(__name__)

# Constants
MIN_MONTHS_REQUIRED = 24  # Minimum months for planning area
MIN_MONTHS_REGIONAL = 30  # Minimum months for regional


def load_l3_unified_data() -> pd.DataFrame:
    """Load L3 unified dataset."""
    logger.info("Loading L3 unified dataset...")

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not path.exists():
        logger.error(f"L3 unified dataset not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Ensure date columns
    if 'transaction_date' in df.columns:
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])

    logger.info(f"Loaded {len(df):,} transactions from L3")

    return df


def load_l5_growth_metrics() -> pd.DataFrame:
    """Load L5 growth metrics."""
    logger.info("Loading L5 growth metrics...")

    path = Config.PARQUETS_DIR / "L5" / "growth_metrics_by_area.parquet"

    if not path.exists():
        logger.warning(f"L5 growth metrics not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Ensure month column
    if 'month' in df.columns:
        if df['month'].dtype == 'object':
            df['month'] = pd.to_datetime(df['month'], format='%Y-%m')

    logger.info(f"Loaded {len(df)} growth metric records")

    return df


def load_macro_data() -> dict:
    """Load macroeconomic data."""
    logger.info("Loading macroeconomic data...")

    macro_dir = Config.DATA_DIR / 'raw_data' / 'macro'

    macro_data = {}

    # SORA rates
    sora_path = macro_dir / 'sora_rates_monthly.parquet'
    if sora_path.exists():
        macro_data['sora'] = pd.read_parquet(sora_path)
        logger.info(f"Loaded SORA rates: {len(macro_data['sora'])} months")
    else:
        logger.warning(f"SORA rates not found: {sora_path}")

    # CPI
    cpi_path = macro_dir / 'singapore_cpi_monthly.parquet'
    if cpi_path.exists():
        macro_data['cpi'] = pd.read_parquet(cpi_path)
        logger.info(f"Loaded CPI: {len(macro_data['cpi'])} months")
    else:
        logger.warning(f"CPI not found: {cpi_path}")

    # GDP (quarterly - will be interpolated to monthly)
    gdp_path = macro_dir / 'sgdp_quarterly.parquet'
    if gdp_path.exists():
        macro_data['gdp'] = pd.read_parquet(gdp_path)
        logger.info(f"Loaded GDP: {len(macro_data['gdp'])} quarters")
    else:
        logger.warning(f"GDP not found: {gdp_path}")

    return macro_data


def aggregate_to_regional_timeseries(
    transactions: pd.DataFrame,
    growth_metrics: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregate transaction data to regional monthly time series.

    Args:
        transactions: L3 unified dataset with planning_area, transaction_date
        growth_metrics: L5 growth metrics with planning_area, month, yoy_change_pct

    Returns:
        Regional timeseries with columns:
        - region, month, regional_appreciation, regional_volume, regional_price_psf
    """
    logger.info("Aggregating to regional time series...")

    # Add region to transactions
    transactions = transactions.copy()
    transactions['region'] = transactions['planning_area'].apply(get_region_for_planning_area)

    # Filter to successful geocoding
    if 'lat' in transactions.columns:
        before_count = len(transactions)
        transactions = transactions.dropna(subset=['lat'])
        logger.info(f"Dropped {before_count - len(transactions)} without coordinates")

    # Create month column
    transactions['month'] = transactions['transaction_date'].dt.to_period('M').astype(str)

    # Aggregate to regional-month level
    regional_agg = transactions.groupby(['region', 'month']).agg({
        'price_psf': ['median', 'mean'],
        'yoy_change_pct': 'median',
        'address': 'count'  # Transaction count
    }).reset_index()

    # Flatten column names
    regional_agg.columns = ['region', 'month', 'regional_price_psf_median',
                          'regional_price_psf_mean', 'regional_appreciation', 'regional_volume']

    # Rename for clarity
    regional_agg = regional_agg.rename(columns={
        'regional_price_psf_median': 'regional_price_psf'
    })

    # Select final columns
    regional_agg = regional_agg[['region', 'month', 'regional_appreciation',
                                 'regional_volume', 'regional_price_psf']]

    # Convert month to datetime
    regional_agg['month'] = pd.to_datetime(regional_agg['month'])

    # Filter to regions with sufficient data
    region_counts = regional_agg.groupby('region').size()
    valid_regions = region_counts[region_counts >= MIN_MONTHS_REGIONAL].index
    regional_agg = regional_agg[regional_agg['region'].isin(valid_regions)]

    logger.info(f"Created regional timeseries: {len(regional_agg)} records, {len(valid_regions)} regions")

    return regional_agg


def handle_missing_months(
    series: pd.Series,
    max_gap: int = 2
) -> pd.Series:
    """
    Handle missing months in time series.

    Args:
        series: Time series with DatetimeIndex
        max_gap: Maximum gap (months) to interpolate

    Returns:
        Series with missing values handled
    """
    if series.isna().sum() == 0:
        return series

    # Find gaps
    missing = series.isna()

    # Interpolate small gaps
    if max_gap > 0:
        interpolated = series.interpolate(method='linear', limit=max_gap)
    else:
        interpolated = series

    # Log remaining gaps
    remaining_gaps = interpolated.isna().sum()
    if remaining_gaps > 0:
        logger.warning(f"{remaining_gaps} months still missing after interpolation")

    return interpolated


def create_area_timeseries(
    transactions: pd.DataFrame,
    growth_metrics: pd.DataFrame
) -> pd.DataFrame:
    """
    Create planning area time series for top areas by volume.

    Args:
        transactions: L3 unified dataset
        growth_metrics: L5 growth metrics

    Returns:
        Area timeseries with columns:
        - area, month, area_appreciation, mrt_within_1km, hawker_within_1km
    """
    logger.info("Creating planning area time series...")

    # Create month column
    transactions = transactions.copy()
    transactions['month'] = transactions['transaction_date'].dt.to_period('M').astype(str)

    # Calculate transaction volume per area
    area_volume = transactions.groupby('planning_area').size().sort_values(ascending=False)

    # Select top 20 areas
    top_areas = area_volume.head(20).index.tolist()
    logger.info(f"Selected top {len(top_areas)} areas by volume")

    # Filter to top areas
    top_transactions = transactions[transactions['planning_area'].isin(top_areas)]

    # Aggregate to area-month level
    area_agg = top_transactions.groupby(['planning_area', 'month']).agg({
        'yoy_change_pct': 'median',
        'price_psf': 'median',
        'address': 'count'
    }).reset_index()

    area_agg.columns = ['area', 'month', 'area_appreciation', 'area_price_psf', 'area_volume']

    # Add amenity features (from original data)
    amenity_cols = ['mrt_within_1km', 'hawker_within_1km', 'school_within_1km']

    # Aggregate amenities to area-month (use mean)
    amenity_agg = top_transactions.groupby(['planning_area', 'month'])[amenity_cols].mean().reset_index()
    amenity_agg.columns = ['area', 'month'] + [f'{col}_mean' for col in amenity_cols]

    # Merge
    area_agg = area_agg.merge(amenity_agg, on=['area', 'month'], how='left')

    # Convert month to datetime
    area_agg['month'] = pd.to_datetime(area_agg['month'])

    # Filter to areas with sufficient months
    area_counts = area_agg.groupby('area').size()
    valid_areas = area_counts[area_counts >= MIN_MONTHS_REQUIRED].index
    area_agg = area_agg[area_agg['area'].isin(valid_areas)]

    logger.info(f"Created area timeseries: {len(area_agg)} records, {len(valid_areas)} areas")

    return area_agg


def merge_macro_data(
    regional_data: pd.DataFrame,
    macro_data: dict
) -> pd.DataFrame:
    """Merge macroeconomic data into regional timeseries."""
    logger.info("Merging macroeconomic data...")

    # Merge SORA
    if 'sora' in macro_data:
        sora = macro_data['sora'].copy()
        sora['month'] = pd.to_datetime(sora['date']).dt.to_period('M').dt.to_timestamp()

        regional_data = regional_data.merge(
            sora[['month', 'sora_rate']],
            on='month',
            how='left'
        )

        # Forward-fill missing rates
        regional_data['sora_rate'] = regional_data['sora_rate'].fillna(method='ffill')

    # Merge CPI
    if 'cpi' in macro_data:
        cpi = macro_data['cpi'].copy()
        cpi['month'] = pd.to_datetime(cpi['date']).dt.to_period('M').dt.to_timestamp()

        regional_data = regional_data.merge(
            cpi[['month', 'cpi']],
            on='month',
            how='left'
        )

        # Interpolate missing CPI
        regional_data['cpi'] = regional_data['cpi'].interpolate(method='linear', limit=3)

    # Merge GDP (quarterly - convert to monthly)
    if 'gdp' in macro_data:
        gdp = macro_data['gdp'].copy()
        gdp['month'] = gdp['quarter']

        regional_data = regional_data.merge(
            gdp[['month', 'gdp_growth']],
            on='month',
            how='left'
        )

        # Forward-fill quarterly data to monthly
        regional_data['gdp_growth'] = regional_data['gdp_growth'].fillna(method='ffill')

    logger.info("Macroeconomic data merged")

    return regional_data


def cap_outliers(df: pd.DataFrame, column: str, lower: float = -50, upper: float = 50) -> pd.DataFrame:
    """Cap outliers in appreciation column."""
    if column not in df.columns:
        return df

    before_count = ((df[column] < lower) | (df[column] > upper)).sum()

    df[column] = df[column].clip(lower=lower, upper=upper)

    if before_count > 0:
        logger.warning(f"Capped {before_count} outliers in {column} at [{lower}, {upper}]")

    return df


def run_preparation_pipeline(
    start_date: str = '2021-01',
    end_date: str = '2026-02'
) -> tuple:
    """
    Run complete time series data preparation pipeline.

    Args:
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format)

    Returns:
        Tuple of (regional_data, area_data) DataFrames
    """
    logger.info("=" * 60)
    logger.info("Time Series Data Preparation Pipeline")
    logger.info("=" * 60)

    # Load data
    transactions = load_l3_unified_data()
    growth_metrics = load_l5_growth_metrics()
    macro_data = load_macro_data()

    if transactions.empty:
        logger.error("No transaction data available")
        return pd.DataFrame(), pd.DataFrame()

    # Aggregate to regional
    regional_data = aggregate_to_regional_timeseries(transactions, growth_metrics)

    # Create area timeseries
    area_data = create_area_timeseries(transactions, growth_metrics)

    # Merge macro data
    regional_data = merge_macro_data(regional_data, macro_data)

    # Handle missing months
    for region in regional_data['region'].unique():
        mask = regional_data['region'] == region
        regional_data.loc[mask, 'regional_appreciation'] = handle_missing_months(
            regional_data.loc[mask, 'regional_appreciation']
        )

    # Cap outliers
    regional_data = cap_outliers(regional_data, 'regional_appreciation')
    area_data = cap_outliers(area_data, 'area_appreciation')

    # Save outputs
    l5_dir = Config.PARQUETS_DIR / "L5"
    l5_dir.mkdir(exist_ok=True)

    regional_path = l5_dir / "regional_timeseries.parquet"
    area_path = l5_dir / "area_timeseries.parquet"

    save_parquet(regional_data, "L5_regional_timeseries", source="prepare_timeseries_pipeline")
    save_parquet(area_data, "L5_area_timeseries", source="prepare_timeseries_pipeline")

    logger.info("=" * 60)
    logger.info("Time series preparation complete!")
    logger.info(f"  Regional: {len(regional_data)} records, {len(regional_data['region'].unique())} regions")
    logger.info(f"  Area: {len(area_data)} records, {len(area_data['area'].unique())} areas")
    logger.info("=" * 60)

    return regional_data, area_data


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    run_preparation_pipeline()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/analytics/test_prepare_timeseries_data.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add scripts/analytics/pipelines/prepare_timeseries_data.py tests/analytics/test_prepare_timeseries_data.py
git commit -m "feat(analytics): add time series data preparation pipeline

- Aggregates L3/L5 data to regional and area timeseries
- Handles missing months via interpolation
- Caps outliers at ±50% appreciation
- Merges macroeconomic data (SORA, CPI, GDP)
- Outputs L5_regional_timeseries and L5_area_timeseries

Part of VAR housing appreciation forecasting system"
```

---

## Task 4: Implement Regional VAR Model Training

**Files:**
- Create: `scripts/analytics/models/regional_var.py`
- Create: `tests/analytics/models/test_regional_var.py`

**Step 1: Write failing test for VAR model**

```python
# tests/analytics/models/test_regional_var.py
import pytest
import pandas as pd
import numpy as np
from scripts.analytics.models.regional_var import (
    RegionalVARModel,
    check_stationarity,
    select_lag_order
)

def test_regional_var_model_initialization():
    """Test VAR model can be initialized."""
    model = RegionalVARModel(region='CCR')

    assert model.region == 'CCR'
    assert model.model is None  # Not fitted yet

def test_check_stationarity_with_stationary_series():
    """Test stationarity check identifies stationary series."""
    # Generate stationary AR(1) series
    np.random.seed(42)
    stationary_series = np.random.normal(0, 1, 100)

    is_stationary, p_value = check_stationarity(stationary_series)

    assert is_stationary is True
    assert p_value < 0.05

def test_select_lag_order_returns_valid_lag():
    """Test lag order selection returns valid lag (1-6)."""
    # Generate VAR(1) data
    np.random.seed(42)
    T = 100
    Y = np.zeros((T, 2))
    for t in range(1, T):
        Y[t] = 0.5 * Y[t-1] + np.random.normal(0, 0.1, 2)

    data = pd.DataFrame(Y, columns=['appreciation', 'volume'])

    lag = select_lag_order(data, max_lag=6)

    assert 1 <= lag <= 6

def test_fit_and_forecast():
    """Test model can be fitted and generate forecasts."""
    # Create sample regional data
    dates = pd.date_range('2021-01', periods=50, freq='M')
    data = pd.DataFrame({
        'month': dates,
        'regional_appreciation': np.random.normal(5, 2, 50),
        'regional_volume': np.random.normal(100, 20, 50),
        'regional_price_psf': np.random.normal(1500, 300, 50)
    })

    model = RegionalVARModel(region='TestRegion')
    model.fit(data)

    assert model.model is not None
    assert model.lag_order is not None

    # Generate forecast
    forecast = model.forecast(horizon=12)

    assert len(forecast) == 12
    assert 'forecast_mean' in forecast.columns
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/analytics/models/test_regional_var.py -v
```

Expected: `ModuleNotFoundError: scripts.analytics.models.regional_var`

**Step 3: Implement regional VAR model**

```python
# scripts/analytics/models/regional_var.py
"""
Regional VAR (Vector Autoregression) model for housing appreciation forecasting.

This module implements Stage 1 of the two-stage hierarchical VAR approach:
- Estimate regional VAR with endogenous variables (appreciation, volume, price)
- Include exogenous macroeconomic variables (interest rate, CPI, GDP)
- Provide forecasting with confidence intervals
- Enable causal inference (Granger causality, IRF, FEVD)

Usage:
    from scripts.analytics.models.regional_var import RegionalVARModel

    model = RegionalVARModel(region='CCR')
    model.fit(regional_data)
    forecast = model.forecast(horizon=36)
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

logger = logging.getLogger(__name__)


def check_stationarity(series: pd.Series, significance_level: float = 0.05) -> Tuple[bool, float]:
    """
    Check if time series is stationary using Augmented Dickey-Fuller test.

    Args:
        series: Time series data
        significance_level: Threshold for rejecting null hypothesis

    Returns:
        Tuple of (is_stationary, p_value)
    """
    try:
        # Drop NaN values
        series_clean = series.dropna()

        if len(series_clean) < 20:
            logger.warning("Series too short for stationarity test, assuming non-stationary")
            return False, 1.0

        # Run ADF test
        result = adfuller(series_clean, autolag='AIC')

        p_value = result[1]
        is_stationary = p_value < significance_level

        return is_stationary, p_value

    except Exception as e:
        logger.error(f"Stationarity test failed: {e}")
        return False, 1.0


def select_lag_order(data: pd.DataFrame, max_lag: int = 6) -> int:
    """
    Select optimal lag order for VAR model using AIC.

    Args:
        data: Time series data (endogenous variables only)
        max_lag: Maximum lag order to test

    Returns:
        Optimal lag order (1-6)
    """
    try:
        model = VAR(data)
        lag_order = model.select_order(maxlags=max_lag)

        # Use AIC (Akaike Information Criterion)
        selected_lag = lag_order.aic

        # Ensure lag is within bounds
        selected_lag = max(1, min(selected_lag, max_lag))

        return selected_lag

    except Exception as e:
        logger.error(f"Lag selection failed: {e}")
        return 3  # Default fallback


class RegionalVARModel:
    """Regional VAR model for housing appreciation forecasting."""

    def __init__(self, region: str):
        """
        Initialize regional VAR model.

        Args:
            region: Region name (e.g., 'CCR', 'RCR')
        """
        self.region = region
        self.model: Optional[VAR] = None
        self.lag_order: Optional[int] = None
        self.endog_vars: list = []
        self.exog_vars: list = []
        self.is_fitted = False

        # Data splits
        self.Y_train: Optional[pd.DataFrame] = None
        self.X_train: Optional[pd.DataFrame] = None
        self.Y_test: Optional[pd.DataFrame] = None
        self.X_test: Optional[pd.DataFrame] = None

    def fit(
        self,
        data: pd.DataFrame,
        endog_vars: list = None,
        exog_vars: list = None,
        test_size: int = 12
    ):
        """
        Fit regional VAR model.

        Args:
            data: Regional time series data
            endog_vars: Endogenous variable names (default: appreciation, volume, price_psf)
            exog_vars: Exogenous variable names (default: sora_rate, cpi, gdp_growth)
            test_size: Number of months to hold out for testing
        """
        logger.info(f"Fitting VAR model for region: {self.region}")

        # Default variables
        if endog_vars is None:
            endog_vars = ['regional_appreciation', 'regional_volume', 'regional_price_psf']
        if exog_vars is None:
            exog_vars = ['sora_rate', 'cpi', 'gdp_growth']

        self.endog_vars = endog_vars
        self.exog_vars = exog_vars

        # Prepare data
        data = data.sort_values('month').reset_index(drop=True)

        # Check stationarity and apply differencing if needed
        Y = data[endog_vars].copy()

        for var in endog_vars:
            is_stationary, p_value = check_stationarity(Y[var])

            if not is_stationary:
                logger.info(f"{var} is non-stationary (p={p_value:.3f}), applying first difference")
                Y[var] = Y[var].diff()

        # Drop NaN from differencing
        Y = Y.dropna()

        # Prepare exogenous variables
        X = data[exog_vars].loc[Y.index] if all(v in data.columns for v in exog_vars) else None

        # Train/test split
        if test_size > 0:
            split_idx = len(Y) - test_size
            self.Y_train = Y.iloc[:split_idx]
            self.Y_test = Y.iloc[split_idx:]
            self.X_train = X.iloc[:split_idx] if X is not None else None
            self.X_test = X.iloc[split_idx:] if X is not None else None
        else:
            self.Y_train = Y
            self.X_train = X
            self.Y_test = None
            self.X_test = None

        logger.info(f"Train size: {len(self.Y_train)}, Test size: {len(self.Y_test) if self.Y_test is not None else 0}")

        # Select lag order
        self.lag_order = select_lag_order(self.Y_train, max_lag=6)
        logger.info(f"Selected lag order: {self.lag_order}")

        # Fit VAR model
        try:
            if self.X_train is not None:
                self.model = VAR(endog=self.Y_train, exog=self.X_train).fit(self.lag_order)
            else:
                self.model = VAR(endog=self.Y_train).fit(self.lag_order)

            self.is_fitted = True
            logger.info(f"VAR model fitted successfully for {self.region}")

        except Exception as e:
            logger.error(f"VAR fitting failed for {self.region}: {e}")
            raise

        return self

    def forecast(
        self,
        horizon: int = 12,
        exog_future: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Generate forecasts with confidence intervals.

        Args:
            horizon: Forecast horizon (months)
            exog_future: Future exogenous variables (required if model has exog)

        Returns:
            DataFrame with columns: month, forecast_mean, ci_lower_95, ci_upper_95
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before forecasting")

        logger.info(f"Generating {horizon}-month forecast for {self.region}")

        try:
            # Generate forecast
            forecast_result = self.model.forecast(
                y=self.Y_train.values,
                steps=horizon,
                exog_future=exog_future.values if exog_future is not None else None
            )

            # Get confidence intervals
            # Note: statsmodels VAR forecast doesn't directly support CIs
            # We'll use a simple approximation based on residual std
            forecast_mean = forecast_result[:, 0]  # First variable = appreciation

            # Calculate residual std from training
            residuals = self.model.resid[:, 0]  # Appreciation residuals
            residual_std = residuals.std()

            # Approximate CI: mean ± z * std * sqrt(horizon)
            # z = 1.96 for 95% CI
            ci_half_width = 1.96 * residual_std * np.sqrt(np.arange(1, horizon + 1))

            ci_lower = forecast_mean - ci_half_width
            ci_upper = forecast_mean + ci_half_width

            # Create forecast DataFrame
            last_month = self.Y_train.index[-1]
            forecast_months = pd.date_range(start=last_month, periods=horizon + 1, freq='M')[1:]

            forecast_df = pd.DataFrame({
                'month': forecast_months,
                'forecast_mean': forecast_mean,
                'ci_lower_95': ci_lower,
                'ci_upper_95': ci_upper
            })

            return forecast_df

        except Exception as e:
            logger.error(f"Forecasting failed for {self.region}: {e}")
            raise

    def granger_causality_tests(self, variable: str = 'regional_appreciation') -> Dict[str, float]:
        """
        Perform Granger causality tests for appreciation.

        Args:
            variable: Target variable to test (default: appreciation)

        Returns:
            Dictionary of variable -> p_value for Granger causality
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before Granger tests")

        logger.info(f"Performing Granger causality tests for {self.region}")

        # Prepare data with all variables
        all_vars = self.endog_vars
        data = self.Y_train[all_vars]

        results = {}

        for test_var in all_vars:
            if test_var == variable:
                continue

            try:
                # Test if test_var Granger-causes variable
                test_data = data[[variable, test_var]]
                gc_result = grangercausalitytests(test_data, maxlag=2, verbose=False)

                # Extract p-value from F-test (lag=1)
                p_value = gc_result[1][0]['ssr_ftest'][1]

                results[test_var] = p_value

                logger.info(f"  {test_var} -> {variable}: p = {p_value:.4f}")

            except Exception as e:
                logger.warning(f"Granger test failed for {test_var}: {e}")
                results[test_var] = 1.0  # Fail-safe: not significant

        return results

    def evaluate(self) -> Dict[str, float]:
        """
        Evaluate model on test set.

        Returns:
            Dictionary with RMSE, MAE, MAPE
        """
        if self.Y_test is None or self.Y_test.empty:
            logger.warning("No test set available for evaluation")
            return {}

        logger.info(f"Evaluating model for {self.region}")

        # Generate forecast for test period
        try:
            forecast = self.forecast(
                horizon=len(self.Y_test),
                exog_future=self.X_test
            )

            # Compare to actual (first variable = appreciation)
            actual = self.Y_test['regional_appreciation'].values
            predicted = forecast['forecast_mean'].values

            # Calculate metrics
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))
            mae = np.mean(np.abs(actual - predicted))
            mape = np.mean(np.abs((actual - predicted) / actual)) * 100

            metrics = {
                'rmse': rmse,
                'mae': mae,
                'mape': mape
            }

            logger.info(f"  RMSE: {rmse:.2f}, MAE: {mae:.2f}, MAPE: {mape:.2f}%")

            return metrics

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/analytics/models/test_regional_var.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add scripts/analytics/models/regional_var.py tests/analytics/models/test_regional_var.py
git commit -m "feat(analytics): implement regional VAR model

- Implements VAR model for regional appreciation forecasting
- Includes stationarity checking via ADF test
- Automatic lag order selection (AIC-optimized, 1-6 lags)
- Granger causality testing for causal inference
- Forecast generation with 95% confidence intervals
- Model evaluation (RMSE, MAE, MAPE)

Part of VAR housing appreciation forecasting system"
```

---

## Task 5: Implement Planning Area ARIMAX Model

**Files:**
- Create: `scripts/analytics/models/area_arimax.py`
- Create: `tests/analytics/models/test_area_arimax.py`

**Step 1: Write failing test for ARIMAX model**

```python
# tests/analytics/models/test_area_arimax.py
import pytest
import pandas as pd
import numpy as np
from scripts.analytics.models.area_arimax import (
    AreaARIMAXModel,
    select_arima_order
)

def test_area_arimax_initialization():
    """Test ARIMAX model can be initialized."""
    model = AreaARIMAXModel(area='Downtown', region='CCR')

    assert model.area == 'Downtown'
    assert model.region == 'CCR'
    assert model.model is None

def test_select_arima_order():
    """Test ARIMA order selection."""
    # Generate AR(2) series
    np.random.seed(42)
    T = 100
    series = np.zeros(T)
    for t in range(2, T):
        series[t] = 0.5 * series[t-1] + 0.3 * series[t-2] + np.random.normal(0, 0.1)

    order = select_arima_order(series, max_p=6)

    assert order[0] >= 1  # AR order >= 1
    assert order[1] == 0  # No differencing (stationary)
    assert order[2] >= 0  # MA order

def test_fit_and_forecast():
    """Test ARIMAX can be fitted and forecast."""
    # Create sample area data
    dates = pd.date_range('2021-01', periods=50, freq='M')
    data = pd.DataFrame({
        'month': dates,
        'area_appreciation': np.random.normal(5, 2, 50),
        'regional_appreciation': np.random.normal(5, 2, 50),
        'mrt_within_1km': np.random.randint(0, 3, 50),
        'hawker_within_1km': np.random.randint(0, 3, 50)
    })

    model = AreaARIMAXModel(area='Downtown', region='CCR')
    model.fit(data)

    assert model.is_fitted

    # Forecast
    forecast = model.forecast(horizon=12, regional_forecast=pd.DataFrame({
        'month': pd.date_range('2025-03', periods=12, freq='M'),
        'regional_appreciation': np.random.normal(5, 2, 12)
    }))

    assert len(forecast) == 12
    assert 'forecast_mean' in forecast.columns
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/analytics/models/test_area_arimax.py -v
```

Expected: `ModuleNotFoundError: scripts.analytics.models.area_arimax`

**Step 3: Implement ARIMAX model**

```python
# scripts/analytics/models/area_arimax.py
"""
Planning Area ARIMAX model for housing appreciation forecasting.

This module implements Stage 2 of the two-stage hierarchical VAR approach:
- Estimate ARIMAX models for individual planning areas
- Use regional VAR forecasts as exogenous predictors
- Include local amenity features (MRT, hawker, school)
- Generate forecasts with uncertainty quantification

Usage:
    from scripts.analytics.models.area_arimax import AreaARIMAXModel

    model = AreaARIMAXModel(area='Downtown', region='CCR')
    model.fit(area_data, regional_forecast)
    forecast = model.forecast(horizon=12, regional_forecast)
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

logger = logging.getLogger(__name__)


def select_arima_order(
    series: pd.Series,
    max_p: int = 6,
    max_d: int = 1,
    max_q: int = 1
) -> tuple:
    """
    Select optimal ARIMA order using grid search with AIC.

    Args:
        series: Time series data
        max_p: Maximum AR order
        max_d: Maximum differencing order
        max_q: Maximum MA order

    Returns:
        Tuple of (p, d, q) order
    """
    best_aic = float('inf')
    best_order = (1, 0, 0)  # Default fallback

    series_clean = series.dropna()

    if len(series_clean) < 30:
        logger.warning("Series too short for order selection, using (1,0,0)")
        return best_order

    # Grid search
    for p in range(1, max_p + 1):
        for d in range(max_d + 1):
            for q in range(max_q + 1):
                try:
                    model = ARIMA(series_clean, order=(p, d, q))
                    fitted = model.fit()

                    if fitted.aic < best_aic:
                        best_aic = fitted.aic
                        best_order = (p, d, q)

                except Exception:
                    continue

    logger.info(f"Selected ARIMA order: {best_order} (AIC={best_aic:.2f})")

    return best_order


class AreaARIMAXModel:
    """Planning area ARIMAX model with regional forecasts as exogenous predictors."""

    def __init__(self, area: str, region: str):
        """
        Initialize area ARIMAX model.

        Args:
            area: Planning area name (e.g., 'Downtown')
            region: Parent region name (e.g., 'CCR')
        """
        self.area = area
        self.region = region
        self.model: Optional[ARIMA] = None
        self.order: Optional[tuple] = None
        self.exog_vars: list = []
        self.is_fitted = False

        # Training data
        self.y_train: Optional[pd.Series] = None
        self.X_train: Optional[pd.DataFrame] = None

    def fit(
        self,
        data: pd.DataFrame,
        endog_var: str = 'area_appreciation',
        exog_vars: list = None,
        test_size: int = 12
    ):
        """
        Fit ARIMAX model for planning area.

        Args:
            data: Area time series data
            endog_var: Target variable name
            exog_vars: Exogenous variable names (regional forecast + amenities)
            test_size: Test set size (months)
        """
        logger.info(f"Fitting ARIMAX model for area: {self.area}")

        # Default exogenous variables
        if exog_vars is None:
            exog_vars = ['regional_appreciation', 'mrt_within_1km_mean', 'hawker_within_1km_mean']

        # Filter to available variables
        available_exog = [v for v in exog_vars if v in data.columns]
        self.exog_vars = available_exog

        logger.info(f"Endogenous: {endog_var}, Exogenous: {available_exog}")

        # Prepare data
        data = data.sort_values('month').reset_index(drop=True)

        y = data[endog_var].copy()
        X = data[available_exog].copy() if available_exog else None

        # Train/test split
        if test_size > 0:
            split_idx = len(y) - test_size
            self.y_train = y.iloc[:split_idx]
            y_test = y.iloc[split_idx:]
            self.X_train = X.iloc[:split_idx] if X is not None else None
            X_test = X.iloc[split_idx:] if X is not None else None
        else:
            self.y_train = y
            self.X_train = X
            y_test = None
            X_test = None

        logger.info(f"Train size: {len(self.y_train)}, Test size: {len(y_test) if y_test is not None else 0}")

        # Check stationarity
        from scripts.analytics.models.regional_var import check_stationarity

        is_stationary, p_value = check_stationarity(self.y_train)

        if not is_stationary:
            logger.info(f"Series non-stationary (p={p_value:.3f}), applying differencing")
            self.y_train = self.y_train.diff().dropna()
            # Align X with differenced y
            if self.X_train is not None:
                self.X_train = self.X_train.iloc[1:]

        # Select ARIMA order
        self.order = select_arima_order(self.y_train, max_p=6, max_d=1, max_q=1)

        # Fit model
        try:
            if self.X_train is not None and not self.X_train.empty:
                self.model = ARIMA(
                    endog=self.y_train,
                    exog=self.X_train,
                    order=self.order
                ).fit()
            else:
                self.model = ARIMA(
                    endog=self.y_train,
                    order=self.order
                ).fit()

            self.is_fitted = True
            logger.info(f"ARIMAX{self.order} fitted successfully for {self.area}")

        except Exception as e:
            logger.error(f"ARIMAX fitting failed for {self.area}: {e}")
            raise

        return self

    def forecast(
        self,
        horizon: int = 12,
        exog_future: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Generate forecasts with confidence intervals.

        Args:
            horizon: Forecast horizon (months)
            exog_future: Future exogenous variables (required if model has exog)

        Returns:
            DataFrame with columns: month, forecast_mean, ci_lower_95, ci_upper_95
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before forecasting")

        logger.info(f"Generating {horizon}-month forecast for {self.area}")

        try:
            # Prepare future exogenous variables
            if self.exog_vars and exog_future is not None:
                X_future = exog_future[self.exog_vars]
            else:
                X_future = None

            # Generate forecast
            forecast_result = self.model.get_forecast(
                steps=horizon,
                exog=X_future
            )

            # Extract forecast and confidence intervals
            forecast_mean = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=0.05)

            # Create forecast DataFrame
            last_month = self.y_train.index[-1]
            forecast_months = pd.date_range(start=last_month, periods=horizon + 1, freq='M')[1:]

            forecast_df = pd.DataFrame({
                'month': forecast_months,
                'forecast_mean': forecast_mean.values,
                'ci_lower_95': conf_int.iloc[:, 0].values,
                'ci_upper_95': conf_int.iloc[:, 1].values
            })

            return forecast_df

        except Exception as e:
            logger.error(f"Forecasting failed for {self.area}: {e}")
            raise

    def evaluate(self, actual: pd.Series) -> dict:
        """
        Evaluate model against actual values.

        Args:
            actual: Actual appreciation values

        Returns:
            Dictionary with RMSE, MAE, MAPE
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before evaluation")

        logger.info(f"Evaluating model for {self.area}")

        try:
            # Generate forecast for same period as actual
            forecast = self.forecast(
                horizon=len(actual),
                exog_future=self.X_test if self.X_test is not None else None
            )

            # Compare to actual
            actual_values = actual.values
            predicted_values = forecast['forecast_mean'].values

            # Calculate metrics
            rmse = np.sqrt(np.mean((actual_values - predicted_values) ** 2))
            mae = np.mean(np.abs(actual_values - predicted_values))

            # MAPE (handle zeros)
            mask = actual_values != 0
            mape = np.mean(np.abs((actual_values[mask] - predicted_values[mask]) / actual_values[mask])) * 100

            metrics = {
                'rmse': rmse,
                'mae': mae,
                'mape': mape
            }

            logger.info(f"  RMSE: {rmse:.2f}, MAE: {mae:.2f}, MAPE: {mape:.2f}%")

            return metrics

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/analytics/models/test_area_arimax.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add scripts/analytics/models/area_arimax.py tests/analytics/models/test_area_arimax.py
git commit -m "feat(analytics): implement planning area ARIMAX model

- Implements ARIMAX model for area-level appreciation forecasting
- Uses regional VAR forecasts as exogenous predictors
- Includes local amenity features (MRT, hawker, school)
- Automatic ARIMA order selection via grid search (AIC-optimized)
- Forecast generation with 95% confidence intervals
- Model evaluation metrics (RMSE, MAE, MAPE)

Part of VAR housing appreciation forecasting system"
```

---

## Task 6: Implement Cross-Validation Pipeline

**Files:**
- Create: `scripts/analytics/pipelines/cross_validate_timeseries.py`
- Create: `tests/analytics/pipelines/test_cross_validate.py`

**Step 1: Write failing test**

```python
# tests/analytics/pipelines/test_cross_validate.py
import pytest
import pandas as pd
from scripts.analytics.pipelines.cross_validate_timeseries import (
    run_rolling_validation,
    evaluate_model_performance
)

def test_rolling_validation_returns_metrics():
    """Test rolling validation returns performance metrics."""
    # Create sample regional data
    dates = pd.date_range('2021-01', periods=48, freq='M')
    data = pd.DataFrame({
        'month': dates,
        'region': ['CCR'] * 48,
        'regional_appreciation': [5.0 + i * 0.1 for i in range(48)],
        'regional_volume': [100] * 48,
        'regional_price_psf': [1500] * 48
    })

    results = run_rolling_validation(
        data=data,
        region='CCR',
        n_folds=3,
        forecast_horizon=6
    )

    assert 'fold_metrics' in results
    assert 'mean_rmse' in results
    assert len(results['fold_metrics']) == 3

def test_evaluate_model_performance():
    """Test performance evaluation."""
    actual = pd.Series([5.0, 5.5, 6.0, 6.5])
    forecast = pd.Series([5.2, 5.3, 6.1, 6.8])

    metrics = evaluate_model_performance(actual, forecast)

    assert 'rmse' in metrics
    assert 'mae' in metrics
    assert metrics['rmse'] > 0
```

**Step 2: Run tests**

```bash
uv run pytest tests/analytics/pipelines/test_cross_validate.py -v
```

**Step 3: Implement cross-validation**

```python
# scripts/analytics/pipelines/cross_validate_timeseries.py
"""
Cross-validation pipeline for VAR/ARIMAX models.

Implements expanding window validation for robust performance estimation.

Usage:
    from scripts.analytics.pipelines.cross_validate_timeseries import run_cross_validation

    results = run_cross_validation(
        regional_data=regional_df,
        area_data=area_df,
        n_folds=5
    )
"""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

from scripts.analytics.models.regional_var import RegionalVARModel
from scripts.analytics.models.area_arimax import AreaARIMAXModel

logger = logging.getLogger(__name__)


def evaluate_model_performance(actual: pd.Series, forecast: pd.Series) -> Dict[str, float]:
    """
    Calculate performance metrics.

    Args:
        actual: Actual values
        forecast: Forecasted values

    Returns:
        Dictionary with RMSE, MAE, MAPE, directional_accuracy
    """
    # Align indices
    aligned_actual, aligned_forecast = actual.align(forecast, join='inner')

    if len(aligned_actual) == 0:
        logger.warning("No overlapping data for evaluation")
        return {}

    # Calculate metrics
    rmse = np.sqrt(np.mean((aligned_actual - aligned_forecast) ** 2))
    mae = np.mean(np.abs(aligned_actual - aligned_forecast))

    # MAPE (handle zeros)
    mask = aligned_actual != 0
    if mask.sum() > 0:
        mape = np.mean(np.abs((aligned_actual[mask] - aligned_forecast[mask]) / aligned_actual[mask])) * 100
    else:
        mape = np.nan

    # Directional accuracy
    actual_changes = np.sign(aligned_actual.diff().dropna())
    forecast_changes = np.sign(aligned_forecast.diff().dropna())
    directional_accuracy = (actual_changes == forecast_changes).mean() * 100

    return {
        'rmse': rmse,
        'mae': mae,
        'mape': mape,
        'directional_accuracy': directional_accuracy
    }


def run_rolling_validation(
    data: pd.DataFrame,
    region: str,
    n_folds: int = 5,
    forecast_horizon: int = 12
) -> Dict:
    """
    Run expanding window cross-validation for regional VAR.

    Args:
        data: Regional time series data
        region: Region name
        n_folds: Number of validation folds
        forecast_horizon: Forecast horizon (months)

    Returns:
        Dictionary with fold_metrics, mean_rmse, mean_mae, etc.
    """
    logger.info(f"Running rolling validation for {region}: {n_folds} folds, {forecast_horizon}-month horizon")

    fold_metrics = []
    min_train_size = 30  # Minimum training size

    for fold in range(n_folds):
        train_end = min_train_size + fold * 3  # Expand by 3 months each fold

        if train_end + forecast_horizon > len(data):
            logger.warning(f"Fold {fold}: insufficient data, skipping")
            continue

        # Split data
        train_data = data.iloc[:train_end]
        test_data = data.iloc[train_end:train_end + forecast_horizon]

        logger.info(f"Fold {fold}: Train size={len(train_data)}, Test size={len(test_data)}")

        try:
            # Fit model
            model = RegionalVARModel(region=region)
            model.fit(train_data, test_size=0)

            # Forecast
            forecast = model.forecast(horizon=forecast_horizon)

            # Evaluate
            actual = test_data['regional_appreciation'].reset_index(drop=True)
            predicted = forecast['forecast_mean']

            metrics = evaluate_model_performance(actual, predicted)
            metrics['fold'] = fold

            fold_metrics.append(metrics)

            logger.info(f"  Fold {fold} RMSE: {metrics['rmse']:.2f}, MAE: {metrics['mae']:.2f}")

        except Exception as e:
            logger.error(f"Fold {fold} failed: {e}")
            continue

    # Aggregate metrics
    if fold_metrics:
        mean_rmse = np.mean([m['rmse'] for m in fold_metrics])
        mean_mae = np.mean([m['mae'] for m in fold_metrics])
        mean_directional = np.mean([m['directional_accuracy'] for m in fold_metrics])
    else:
        mean_rmse = mean_mae = mean_directional = np.nan

    results = {
        'region': region,
        'n_folds': len(fold_metrics),
        'fold_metrics': fold_metrics,
        'mean_rmse': mean_rmse,
        'mean_mae': mean_mae,
        'mean_directional_accuracy': mean_directional
    }

    logger.info(f"Validation complete: RMSE={mean_rmse:.2f}, MAE={mean_mae:.2f}, DirAcc={mean_directional:.1f}%")

    return results


def run_cross_validation(
    regional_data: pd.DataFrame,
    area_data: pd.DataFrame,
    n_folds: int = 5
) -> Dict:
    """
    Run complete cross-validation for all models.

    Args:
        regional_data: Regional time series
        area_data: Area time series
        n_folds: Number of validation folds

    Returns:
        Dictionary with regional and area results
    """
    logger.info("=" * 60)
    logger.info("Cross-Validation Pipeline")
    logger.info("=" * 60)

    results = {
        'regional': {},
        'area': {}
    }

    # Regional cross-validation
    for region in regional_data['region'].unique():
        region_data = regional_data[regional_data['region'] == region]

        if len(region_data) < 36:  # Need at least 36 months
            logger.warning(f"Skipping {region}: insufficient data")
            continue

        region_results = run_rolling_validation(
            data=region_data,
            region=region,
            n_folds=n_folds,
            forecast_horizon=12
        )

        results['regional'][region] = region_results

    # Area cross-validation (simplified - just 1 fold for speed)
    for area in area_data['area'].unique()[:10]:  # Test 10 areas for now
        area_data_subset = area_data[area_data['area'] == area]

        if len(area_data_subset) < 30:
            continue

        logger.info(f"Validating area: {area}")

        try:
            # Simple train/test split
            train_size = int(len(area_data_subset) * 0.8)
            train_data = area_data_subset.iloc[:train_size]
            test_data = area_data_subset.iloc[train_size:]

            # Fit model
            model = AreaARIMAXModel(area=area, region='Unknown')
            model.fit(train_data, test_size=0)

            # Forecast
            regional_forecast = pd.DataFrame({
                'month': test_data['month'],
                'regional_appreciation': test_data['regional_appreciation']  # Use actual as proxy
            })

            forecast = model.forecast(horizon=len(test_data), exog_future=regional_forecast)

            # Evaluate
            actual = test_data['area_appreciation'].reset_index(drop=True)
            predicted = forecast['forecast_mean']

            metrics = evaluate_model_performance(actual, predicted)
            results['area'][area] = metrics

            logger.info(f"  {area} RMSE: {metrics['rmse']:.2f}")

        except Exception as e:
            logger.error(f"Area validation failed for {area}: {e}")
            continue

    logger.info("=" * 60)
    logger.info("Cross-validation complete!")
    logger.info("=" * 60)

    return results
```

**Step 4: Run tests**

```bash
uv run pytest tests/analytics/pipelines/test_cross_validate.py -v
```

**Step 5: Commit**

```bash
git add scripts/analytics/pipelines/cross_validate_timeseries.py tests/analytics/pipelines/test_cross_validate.py
git commit -m "feat(analytics): implement cross-validation pipeline

- Expanding window validation (5 folds)
- Evaluates regional VAR and area ARIMAX models
- Calculates RMSE, MAE, MAPE, directional accuracy
- Handles model failures gracefully

Part of VAR housing appreciation forecasting system"
```

---

## Task 7: Implement Forecasting Pipeline

**Files:**
- Create: `scripts/analytics/pipelines/forecast_appreciation.py`
- Create: `tests/analytics/pipelines/test_forecast_appreciation.py`

**Step 1: Write failing test**

```python
# tests/analytics/pipelines/test_forecast_appreciation.py
import pytest
import pandas as pd
from scripts.analytics.pipelines.forecast_appreciation import (
    run_forecasting_pipeline,
    generate_regional_forecasts
)

def test_generate_regional_forecasts():
    """Test regional forecast generation."""
    # Create sample regional data
    dates = pd.date_range('2021-01', periods=50, freq='M')
    data = pd.DataFrame({
        'month': dates,
        'region': ['CCR'] * 50,
        'regional_appreciation': [5.0 + i * 0.1 for i in range(50)],
        'regional_volume': [100] * 50,
        'regional_price_psf': [1500] * 50
    })

    forecasts = generate_regional_forecasts(
        regional_data=data,
        horizon_months=12
    )

    assert len(forecasts) == 7  # Should have forecasts (even if some fail)
    assert all('forecast_mean' in fc.columns for fc in forecasts if fc is not None)

def test_run_forecasting_pipeline():
    """Test complete forecasting pipeline."""
    results = run_forecasting_pipeline(
        scenario='baseline',
        horizon_months=12
    )

    assert 'regional_forecasts' in results
    assert 'area_forecasts' in results
```

**Step 2: Run tests**

```bash
uv run pytest tests/analytics/pipelines/test_forecast_appreciation.py -v
```

**Step 3: Implement forecasting pipeline**

```python
# scripts/analytics/pipelines/forecast_appreciation.py
"""
Forecasting pipeline for housing appreciation predictions.

Generates multi-scenario forecasts (baseline, bullish, bearish, policy shock)
for regional VAR and planning area ARIMAX models.

Usage:
    from scripts.analytics.pipelines.forecast_appreciation import run_forecasting_pipeline

    forecasts = run_forecasting_pipeline(scenario='baseline', horizon_months=36)
"""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

from scripts.analytics.models.regional_var import RegionalVARModel
from scripts.analytics.models.area_arimax import AreaARIMAXModel
from scripts.core.data_helpers import load_parquet

logger = logging.getLogger(__name__)


def generate_regional_forecasts(
    regional_data: pd.DataFrame,
    horizon_months: int = 36,
    scenario: str = 'baseline'
) -> List[Dict]:
    """
    Generate forecasts for all regions.

    Args:
        regional_data: Regional time series data
        horizon_months: Forecast horizon
        scenario: 'baseline', 'bullish', 'bearish', or 'policy_shock'

    Returns:
        List of forecast DataFrames (one per region)
    """
    logger.info(f"Generating regional forecasts: scenario={scenario}, horizon={horizon_months}")

    forecasts = []

    for region in regional_data['region'].unique():
        region_data = regional_data[regional_data['region'] == region].copy()

        try:
            # Fit model
            model = RegionalVARModel(region=region)
            model.fit(region_data, test_size=0)

            # Apply scenario adjustments
            if scenario == 'bullish':
                # Lower interest rates
                region_data['sora_rate'] = region_data['sora_rate'] - 0.01
            elif scenario == 'bearish':
                # Higher interest rates
                region_data['sora_rate'] = region_data['sora_rate'] + 0.01
            elif scenario == 'policy_shock':
                # Additional ABSD (reduce appreciation)
                region_data['regional_appreciation'] = region_data['regional_appreciation'] - 2.0

            # Re-fit with scenario adjustments
            model.fit(region_data, test_size=0)

            # Generate forecast
            forecast = model.forecast(horizon=horizon_months)
            forecast['region'] = region
            forecast['scenario'] = scenario

            forecasts.append(forecast)

            logger.info(f"  {region}: {len(forecast)} months forecasted")

        except Exception as e:
            logger.error(f"Regional forecast failed for {region}: {e}")
            forecasts.append(None)

    logger.info(f"Generated {len([f for f in forecasts if f is not None])} regional forecasts")

    return forecasts


def generate_area_forecasts(
    area_data: pd.DataFrame,
    regional_forecasts: List[pd.DataFrame],
    horizon_months: int = 24
) -> List[pd.DataFrame]:
    """
    Generate forecasts for planning areas using regional forecasts as inputs.

    Args:
        area_data: Area time series data
        regional_forecasts: Regional forecast DataFrames
        horizon_months: Forecast horizon

    Returns:
        List of forecast DataFrames (one per area)
    """
    logger.info(f"Generating area forecasts: horizon={horizon_months}")

    forecasts = []

    # Create region -> forecast mapping
    regional_fc_dict = {}
    for fc in regional_forecasts:
        if fc is not None:
            region = fc['region'].iloc[0]
            regional_fc_dict[region] = fc

    for area in area_data['area'].unique()[:20]:  # Top 20 areas
        area_subset = area_data[area_data['area'] == area].copy()

        if len(area_subset) < 24:
            logger.warning(f"Skipping {area}: insufficient data")
            continue

        # Get parent region
        from scripts.core.config.regional_mapping import get_region_for_planning_area
        region = get_region_for_planning_area(area)

        if region is None or region not in regional_fc_dict:
            logger.warning(f"Skipping {area}: unknown region or no regional forecast")
            continue

        regional_fc = regional_fc_dict[region]

        try:
            # Fit model
            model = AreaARIMAXModel(area=area, region=region)

            # Check if required exog vars exist
            required_vars = ['regional_appreciation', 'mrt_within_1km_mean', 'hawker_within_1km_mean']
            available_vars = [v for v in required_vars if v in area_subset.columns]

            if len(available_vars) < 2:
                logger.warning(f"Skipping {area}: insufficient exogenous variables")
                continue

            model.fit(area_subset, exog_vars=available_vars, test_size=0)

            # Prepare regional forecast as exog
            exog_future = pd.DataFrame({
                'month': regional_fc['month'],
                'regional_appreciation': regional_fc['forecast_mean']
            })

            # Add amenity constants (use last observed value)
            for var in available_vars:
                if var != 'regional_appreciation' and var in area_subset.columns:
                    exog_future[var] = area_subset[var].iloc[-1]

            # Generate forecast
            forecast = model.forecast(horizon=horizon_months, exog_future=exog_future)
            forecast['area'] = area

            forecasts.append(forecast)

            logger.info(f"  {area}: {len(forecast)} months forecasted")

        except Exception as e:
            logger.error(f"Area forecast failed for {area}: {e}")
            continue

    logger.info(f"Generated {len(forecasts)} area forecasts")

    return forecasts


def run_forecasting_pipeline(
    scenario: str = 'baseline',
    horizon_months: int = 36
) -> Dict:
    """
    Run complete forecasting pipeline.

    Args:
        scenario: Forecast scenario ('baseline', 'bullish', 'bearish', 'policy_shock')
        horizon_months: Forecast horizon in months

    Returns:
        Dictionary with regional_forecasts, area_forecasts, metadata
    """
    logger.info("=" * 60)
    logger.info("Forecasting Pipeline")
    logger.info(f"Scenario: {scenario}, Horizon: {horizon_months} months")
    logger.info("=" * 60)

    # Load prepared time series data
    try:
        regional_data = load_parquet("L5_regional_timeseries")
        area_data = load_parquet("L5_area_timeseries")
    except Exception as e:
        logger.error(f"Failed to load time series data: {e}")
        return {}

    # Generate regional forecasts
    regional_forecasts = generate_regional_forecasts(
        regional_data=regional_data,
        horizon_months=horizon_months,
        scenario=scenario
    )

    # Generate area forecasts
    area_forecasts = generate_area_forecasts(
        area_data=area_data,
        regional_forecasts=regional_forecasts,
        horizon_months=min(horizon_months, 24)  # Cap areas at 24 months
    )

    results = {
        'regional_forecasts': regional_forecasts,
        'area_forecasts': area_forecasts,
        'metadata': {
            'scenario': scenario,
            'horizon_months': horizon_months,
            'n_regions': len([f for f in regional_forecasts if f is not None]),
            'n_areas': len(area_forecasts)
        }
    }

    logger.info("=" * 60)
    logger.info("Forecasting complete!")
    logger.info(f"  Regions: {results['metadata']['n_regions']}")
    logger.info(f"  Areas: {results['metadata']['n_areas']}")
    logger.info("=" * 60)

    return results
```

**Step 4: Run tests**

```bash
uv run pytest tests/analytics/pipelines/test_forecast_appreciation.py -v
```

**Step 5: Commit**

```bash
git add scripts/analytics/pipelines/forecast_appreciation.py tests/analytics/pipelines/test_forecast_appreciation.py
git commit -m "feat(analytics): implement forecasting pipeline

- Generates multi-scenario forecasts (baseline/bullish/bearish/policy)
- Regional VAR forecasts (36-month horizon)
- Area ARIMAX forecasts (24-month horizon)
- Includes scenario adjustments (interest rates, policy shocks)
- Robust error handling for failed models

Part of VAR housing appreciation forecasting system"
```

---

## Completion Checklist

Before considering the implementation complete:

- [ ] All 7 tasks committed (regional mapping, macro data, data prep, VAR model, ARIMAX model, cross-validation, forecasting)
- [ ] All tests passing (`uv run pytest tests/analytics/ -v`)
- [ ] Test coverage >80% (`uv run pytest --cov=scripts/analytics --cov-report=html`)
- [ ] Documentation updated (design doc, planning doc)
- [ ] Error logging functional
- [ ] Backtesting validated (2021-2026 accuracy >70%)

---

**End of Implementation Plan**
