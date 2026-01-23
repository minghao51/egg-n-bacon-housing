"""Housing market metrics calculation functions.

This module provides functions to calculate various housing market metrics
from transaction data, including:
- Price growth rates (stratified median)
- Price per square meter (PSM)
- Transaction volume
- Market momentum
- Affordability index (TODO: requires income data)
- ROI potential score (TODO: requires rental data)
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ============================================================================
# STRATIFICATION
# ============================================================================

def assign_price_strata(
    df: pd.DataFrame,
    price_column: str = 'resale_price',
    n_strata: int = 5,
    method: str = 'predefined'
) -> pd.Series:
    """Assign price stratum to each transaction.

    Args:
        df: Transaction DataFrame
        price_column: Name of price column
        n_strata: Number of strata to create
        method: 'predefined' or 'quantile'

    Returns:
        Series with stratum assignments (1 to n_strata)
    """
    if method == 'quantile':
        # Data-driven: Create quantile-based strata
        strata = pd.qcut(df[price_column], q=n_strata, labels=False, duplicates='drop')
        return strata + 1  # 1-indexed

    else:  # predefined
        # Predefined price bands for Singapore (adjust as needed)
        if price_column == 'resale_price':  # HDB
            # HDB price bands (in SGD)
            bins = [0, 300000, 450000, 600000, 800000, float('inf')]
            labels = ['budget', 'mass_market', 'mid_tier', 'premium', 'luxury']
        else:  # Condo
            # Condo price bands (in SGD)
            bins = [0, 800000, 1500000, 2500000, 5000000, float('inf')]
            labels = ['budget', 'mass_market', 'mid_tier', 'premium', 'luxury']

        return pd.cut(df[price_column], bins=bins, labels=labels)


def calculate_stratified_median(
    df: pd.DataFrame,
    group_columns: List[str],
    price_column: str = 'resale_price',
    strata_column: Optional[str] = None,
    weight_column: Optional[str] = None
) -> pd.DataFrame:
    """Calculate stratified median price.

    Args:
        df: Transaction DataFrame
        group_columns: Columns to group by (e.g., ['month', 'planning_area'])
        price_column: Price column to aggregate
        strata_column: Column with stratum assignments (created if None)
        weight_column: Column for weights (None = equal weights)

    Returns:
        DataFrame with stratified median prices
    """
    df = df.copy()

    # Assign strata if not provided
    if strata_column is None:
        df['_stratum'] = assign_price_strata(df, price_column)
        strata_column = '_stratum'

    # Calculate median per stratum per group
    stratum_medians = df.groupby(group_columns + [strata_column])[price_column].median()

    # Calculate weights
    if weight_column is None:
        # Equal weights within each group
        weights = df.groupby(group_columns + [strata_column]).size()
        weights = weights / weights.groupby(level=group_columns).sum()
    else:
        # Custom weights
        weights = df.groupby(group_columns + [strata_column])[weight_column].sum()
        weights = weights / weights.groupby(level=group_columns).sum()

    # Calculate weighted median
    weighted_median = (stratum_medians * weights).groupby(level=group_columns).sum()

    return weighted_median.reset_index(name='stratified_median_price')


# ============================================================================
# CORE METRICS
# ============================================================================

def calculate_psm(
    df: pd.DataFrame,
    price_column: str = 'resale_price',
    area_column: str = 'floor_area_sqm',
    agg_method: str = 'median'
) -> pd.Series:
    """Calculate price per square meter.

    Args:
        df: Transaction DataFrame
        price_column: Price column
        area_column: Floor area column (SQM)
        agg_method: 'median' or 'mean'

    Returns:
        Series with PSM values
    """
    psm = df[price_column] / df[area_column]
    return psm


def calculate_volume_metrics(
    df: pd.DataFrame,
    date_column: str = 'month',
    geo_column: str = 'planning_area',
    rolling_windows: List[int] = [3, 12]
) -> pd.DataFrame:
    """Calculate transaction volume metrics.

    Args:
        df: Transaction DataFrame
        date_column: Date column
        geo_column: Geographic column
        rolling_windows: Rolling average windows in months

    Returns:
        DataFrame with volume metrics
    """
    # Count transactions per period
    volume = df.groupby([date_column, geo_column]).size().reset_index(name='transaction_count')

    # Sort for rolling calculations
    volume = volume.sort_values([geo_column, date_column])

    # Calculate rolling averages
    for window in rolling_windows:
        volume[f'volume_{window}m_avg'] = volume.groupby(geo_column)['transaction_count'].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )

    # Calculate changes
    volume['mom_change_pct'] = volume.groupby(geo_column)['transaction_count'].transform(
        lambda x: x.pct_change() * 100
    )
    volume['yoy_change_pct'] = volume.groupby(geo_column)['transaction_count'].transform(
        lambda x: x.pct_change(12) * 100
    )

    return volume


def calculate_growth_rate(
    prices: pd.Series,
    periods: int = 1
) -> pd.Series:
    """Calculate period-over-period growth rate.

    Args:
        prices: Price series
        periods: Number of periods to lag

    Returns:
        Growth rate as percentage
    """
    return prices.pct_change(periods=periods) * 100


def calculate_momentum(
    df: pd.DataFrame,
    date_column: str = 'month',
    geo_column: str = 'planning_area',
    price_column: str = 'stratified_median_price'
) -> pd.DataFrame:
    """Calculate market momentum (short-term acceleration).

    Momentum = 3-month growth - 12-month growth

    Args:
        df: DataFrame with price data
        date_column: Date column
        geo_column: Geographic column
        price_column: Price column

    Returns:
        DataFrame with momentum metrics
    """
    df = df.sort_values([geo_column, date_column])

    # Calculate 3M and 12M growth rates
    df['growth_3m'] = df.groupby(geo_column)[price_column].transform(
        lambda x: x.pct_change(3) * 100
    )
    df['growth_12m'] = df.groupby(geo_column)[price_column].transform(
        lambda x: x.pct_change(12) * 100
    )

    # Calculate momentum
    df['momentum'] = df['growth_3m'] - df['growth_12m']

    # Add signal
    df['momentum_signal'] = pd.cut(
        df['momentum'],
        bins=[-float('inf'), -5, -2, 2, 5, float('inf')],
        labels=['strong_deceleration', 'moderate_deceleration', 'stable',
                'moderate_acceleration', 'strong_acceleration']
    )

    return df


# ============================================================================
# ADVANCED METRICS (TODO: Need external data)
# ============================================================================

def calculate_affordability(
    property_prices: pd.Series,
    income_data: pd.Series
) -> pd.Series:
    """Calculate affordability ratio (price / income).

    Args:
        property_prices: Property price series
        income_data: Annual household income series

    Returns:
        Affordability ratio
    """
    # TODO: Implement when income data is available
    raise NotImplementedError("Affordability calculation requires income data")


def calculate_roi_score(
    feature_df: pd.DataFrame,
    rental_yield_df: Optional[pd.DataFrame] = None,
    weights: Optional[Dict[str, float]] = None
) -> pd.Series:
    """Calculate ROI potential score.

    Args:
        feature_df: DataFrame with all features (must contain: property_type, town, month)
        rental_yield_df: Optional DataFrame with rental yield data
        weights: Custom weights for each component

    Returns:
        ROI score (0-100)
    """
    # Default weights with rental yield included
    default_weights = {
        'price_momentum': 0.30,
        'rental_yield': 0.25,
        'infrastructure': 0.20,
        'amenities': 0.15,
        # Missing: economic_indicators (0.10)
    }

    if weights is None:
        weights = default_weights

    # Determine which components are available
    available_components = ['price_momentum', 'infrastructure_score', 'amenities_score']
    if rental_yield_df is not None and not rental_yield_df.empty:
        # Merge rental yield data
        merged = feature_df.merge(
            rental_yield_df[['town', 'month', 'property_type', 'rental_yield_pct']],
            on=['town', 'month', 'property_type'],
            how='left'
        )
        # Fill missing rental yields with median
        merged['rental_yield_pct'] = merged['rental_yield_pct'].fillna(merged['rental_yield_pct'].median())
        available_components.append('rental_yield_pct')
    else:
        merged = feature_df.copy()
        # Remove rental_yield from weights if not available
        weights = {k: v for k, v in weights.items() if k != 'rental_yield'}

    # Normalize weights to sum to 1
    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}

    # Calculate weighted score
    score = merged['price_momentum'] * weights['price_momentum']

    if 'rental_yield_pct' in merged.columns and 'rental_yield' in weights:
        # Normalize rental yield to 0-1 scale (assuming 0-15% range)
        score += (merged['rental_yield_pct'] / 15.0) * weights['rental_yield']

    if 'infrastructure_score' in merged.columns and 'infrastructure' in weights:
        score += merged['infrastructure_score'] * weights['infrastructure']

    if 'amenities_score' in merged.columns and 'amenities' in weights:
        score += merged['amenities_score'] * weights['amenities']

    # Rescale to 0-100
    score = (score - score.min()) / (score.max() - score.min()) * 100

    return score


# ============================================================================
# PIPELINE FUNCTIONS
# ============================================================================

def compute_monthly_metrics(
    hdf_df: pd.DataFrame,
    condo_df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """Compute all monthly metrics for HDB and condo transactions.

    Args:
        hdf_df: HDB transaction DataFrame
        condo_df: Condo transaction DataFrame
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format)

    Returns:
        DataFrame with all metrics
    """
    # Process HDB
    hdf_metrics = _process_property_type(hdf_df, 'HDB', start_date, end_date)

    # Process Condo
    condo_metrics = _process_property_type(condo_df, 'Condo', start_date, end_date)

    # Combine
    all_metrics = pd.concat([hdf_metrics, condo_metrics], ignore_index=True)

    return all_metrics


def _process_property_type(
    df: pd.DataFrame,
    property_type: str,
    start_date: Optional[str],
    end_date: Optional[str]
) -> pd.DataFrame:
    """Process transactions for a single property type.

    Args:
        df: Transaction DataFrame
        property_type: 'HDB' or 'Condo'
        start_date: Start date filter
        end_date: End date filter

    Returns:
        DataFrame with metrics for this property type
    """
    # Filter by date
    if start_date:
        df = df[df['month'] >= start_date]
    if end_date:
        df = df[df['month'] <= end_date]

    # Determine column names
    if property_type == 'HDB':
        price_col = 'resale_price'
        area_col = 'floor_area_sqm'
        geo_col = 'town'  # Will change to planning_area later
    else:  # Condo
        price_col = 'Transacted Price ($)'
        area_col = 'Area (SQM)'
        geo_col = 'Postal District'  # Will change to planning_area later

    # Add PSM
    df['psm'] = calculate_psm(df, price_col, area_col)

    # Calculate stratified median prices
    stratified_prices = calculate_stratified_median(
        df,
        group_columns=['month', geo_col],
        price_column=price_col
    )

    # Calculate volume metrics
    volume = calculate_volume_metrics(
        df,
        date_column='month',
        geo_column=geo_col
    )

    # Merge
    metrics = stratified_prices.merge(volume, on=['month', geo_col])

    # Add property type
    metrics['property_type'] = property_type

    # Calculate growth rates
    metrics = metrics.sort_values([geo_col, 'month'])
    metrics['growth_rate'] = metrics.groupby(geo_col)['stratified_median_price'].transform(
        lambda x: x.pct_change() * 100
    )

    # Calculate momentum
    metrics = calculate_momentum(
        metrics,
        date_column='month',
        geo_column=geo_col
    )

    return metrics


# ============================================================================
# VALIDATION
# ============================================================================

def validate_metrics(metrics_df: pd.DataFrame) -> Dict[str, any]:
    """Validate calculated metrics.

    Args:
        metrics_df: DataFrame with calculated metrics

    Returns:
        Dictionary with validation results
    """
    results = {
        'total_records': len(metrics_df),
        'date_range': (metrics_df['month'].min(), metrics_df['month'].max()),
        'missing_values': metrics_df.isnull().sum().to_dict(),
        'outliers': {
            'growth_rate_extreme': ((metrics_df['growth_rate'].abs() > 50).sum()),
            'negative_prices': ((metrics_df['stratified_median_price'] < 0).sum()),
        },
        'geo_coverage': metrics_df['planning_area'].nunique() if 'planning_area' in metrics_df.columns else None
    }

    return results
