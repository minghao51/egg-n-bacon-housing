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

import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet, save_parquet
from scripts.core.regional_mapping import get_region_for_planning_area

logger = logging.getLogger(__name__)

# Constants
MIN_MONTHS_REQUIRED = 24  # Minimum months for planning area
MIN_MONTHS_REGIONAL = 30  # Minimum months for regional


def load_l3_unified_data() -> pd.DataFrame:
    """Load L3 unified dataset."""
    logger.info("Loading L3 unified dataset...")

    # Check if L3 unified dataset exists, if not, use alternative
    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not path.exists():
        # Try alternative locations or return empty DataFrame
        logger.warning(f"L3 unified dataset not found: {path}")
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

    try:
        df = load_parquet("L5_growth_metrics_by_area")
    except Exception:
        logger.warning("L5 growth metrics not found")
        return pd.DataFrame()

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

    # Only include if they exist
    available_amenity_cols = [c for c in amenity_cols if c in top_transactions.columns]

    if available_amenity_cols:
        # Aggregate amenities to area-month (use mean)
        amenity_agg = top_transactions.groupby(['planning_area', 'month'])[available_amenity_cols].mean().reset_index()
        amenity_agg.columns = ['area', 'month'] + [f'{col}_mean' for col in available_amenity_cols]

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
        regional_data['sora_rate'] = regional_data['sora_rate'].ffill()

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
        # Convert quarter to month (start of quarter)
        gdp['month'] = pd.to_datetime(gdp['quarter']).dt.to_period('M').dt.to_timestamp()

        regional_data = regional_data.merge(
            gdp[['month', 'gdp_growth']],
            on='month',
            how='left'
        )

        # Forward-fill quarterly data to monthly
        regional_data['gdp_growth'] = regional_data['gdp_growth'].ffill()

        # Fill any remaining NaN with mean
        regional_data['gdp_growth'] = regional_data['gdp_growth'].fillna(regional_data['gdp_growth'].mean())

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
