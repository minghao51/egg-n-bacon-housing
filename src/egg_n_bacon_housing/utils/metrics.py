"""Housing market metrics calculation functions.

This module provides functions to calculate various housing market metrics
from transaction data, including:
- Price growth rates (stratified median)
- Price per square foot (PSF)
- Transaction volume
- Market momentum
- Affordability classification
"""

from typing import Any

import pandas as pd

_DEFAULT_AFFORDABILITY_THRESHOLDS: dict[str, float] = {
    "affordable": 5.0,
    "moderate": 7.0,
    "expensive": 9.0,
}


def classify_affordability(ratio: float, thresholds: dict[str, float] | None = None) -> str:
    """Classify affordability based on ratio.

    Args:
        ratio: Affordability ratio
        thresholds: Optional thresholds dict with keys 'affordable',
            'moderate', 'expensive'. Defaults to standard Singapore thresholds.

    Returns:
        Classification string
    """
    if thresholds is None:
        thresholds = _DEFAULT_AFFORDABILITY_THRESHOLDS
    if ratio < thresholds["affordable"]:
        return "Affordable"
    if ratio < thresholds["moderate"]:
        return "Moderate"
    if ratio < thresholds["expensive"]:
        return "Expensive"
    return "Severely Unaffordable"


def assign_price_strata(
    df: pd.DataFrame,
    price_column: str = "resale_price",
    n_strata: int = 5,
    method: str = "predefined",
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
    if method == "quantile":
        strata = pd.qcut(df[price_column], q=n_strata, labels=False, duplicates="drop")
        return strata + 1

    if price_column == "resale_price":
        bins = [0, 300000, 450000, 600000, 800000, float("inf")]
        labels = ["budget", "mass_market", "mid_tier", "premium", "luxury"]
    else:
        bins = [0, 800000, 1500000, 2500000, 5000000, float("inf")]
        labels = ["budget", "mass_market", "mid_tier", "premium", "luxury"]

    return pd.cut(df[price_column], bins=bins, labels=labels)


def calculate_stratified_median(
    df: pd.DataFrame,
    group_columns: list[str],
    price_column: str = "resale_price",
    strata_column: str | None = None,
    weight_column: str | None = None,
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

    if strata_column is None:
        df["_stratum"] = assign_price_strata(df, price_column)
        strata_column = "_stratum"

    stratum_medians = df.groupby([*group_columns, strata_column])[price_column].median()

    if weight_column is None:
        weights = df.groupby([*group_columns, strata_column]).size()
        weights = weights / weights.groupby(level=group_columns).sum()
    else:
        weights = df.groupby([*group_columns, strata_column])[weight_column].sum()
        weights = weights / weights.groupby(level=group_columns).sum()

    weighted_median = (stratum_medians * weights).groupby(level=group_columns).sum()

    return weighted_median.reset_index(name="stratified_median_price")


def calculate_psf(
    df: pd.DataFrame,
    price_column: str = "resale_price",
    area_column: str = "floor_area_sqft",
    agg_method: str = "median",
) -> pd.Series:
    """Calculate price per square foot.

    Args:
        df: Transaction DataFrame
        price_column: Price column
        area_column: Floor area column (SQFT)
        agg_method: 'median' or 'mean'

    Returns:
        Series with PSF values
    """
    return df[price_column] / df[area_column]


def calculate_volume_metrics(
    df: pd.DataFrame,
    date_column: str = "month",
    geo_column: str = "planning_area",
    rolling_windows: list[int] | None = None,
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
    if rolling_windows is None:
        rolling_windows = [3, 12]
    volume = df.groupby([date_column, geo_column]).size().reset_index(name="transaction_count")

    volume = volume.sort_values([geo_column, date_column])

    for window in rolling_windows:
        volume[f"volume_{window}m_avg"] = volume.groupby(geo_column)["transaction_count"].transform(
            lambda x, w=window: x.rolling(w, min_periods=1).mean()
        )

    volume["mom_change_pct"] = volume.groupby(geo_column)["transaction_count"].transform(
        lambda x: x.pct_change() * 100
    )
    volume["yoy_change_pct"] = volume.groupby(geo_column)["transaction_count"].transform(
        lambda x: x.pct_change(12) * 100
    )

    return volume


def calculate_momentum(
    df: pd.DataFrame,
    date_column: str = "month",
    geo_column: str = "planning_area",
    price_column: str = "stratified_median_price",
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

    df["growth_3m"] = df.groupby(geo_column)[price_column].transform(
        lambda x: x.pct_change(3) * 100
    )
    df["growth_12m"] = df.groupby(geo_column)[price_column].transform(
        lambda x: x.pct_change(12) * 100
    )

    df["momentum"] = df["growth_3m"] - df["growth_12m"]

    df["momentum_signal"] = pd.cut(
        df["momentum"],
        bins=[-float("inf"), -5, -2, 2, 5, float("inf")],
        labels=[
            "strong_deceleration",
            "moderate_deceleration",
            "stable",
            "moderate_acceleration",
            "strong_acceleration",
        ],
    )

    return df


def compute_monthly_metrics(
    unified_df: pd.DataFrame, start_date: str | None = None, end_date: str | None = None
) -> pd.DataFrame:
    """Compute all monthly metrics for HDB and condo transactions.

    Args:
        unified_df: Unified transaction DataFrame with both HDB and Condo
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format)

    Returns:
        DataFrame with all metrics
    """
    hdb_df = unified_df[unified_df["property_type"] == "HDB"].copy()
    condo_df = unified_df[unified_df["property_type"] == "Condominium"].copy()

    hdb_metrics = _process_property_type(hdb_df, "HDB", start_date, end_date)

    condo_metrics = _process_property_type(condo_df, "Condo", start_date, end_date)

    return pd.concat([hdb_metrics, condo_metrics], ignore_index=True)


def _process_property_type(
    df: pd.DataFrame, property_type: str, start_date: str | None, end_date: str | None
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
    if start_date:
        df = df[df["month"] >= start_date]
    if end_date:
        df = df[df["month"] <= end_date]

    price_col = "price"
    area_col = "floor_area_sqft"
    geo_col = "planning_area"

    df["psf"] = calculate_psf(df, price_col, area_col)

    stratified_prices = calculate_stratified_median(
        df, group_columns=["month", geo_col], price_column=price_col
    )

    volume = calculate_volume_metrics(df, date_column="month", geo_column=geo_col)

    metrics = stratified_prices.merge(volume, on=["month", geo_col])

    metrics["property_type"] = property_type

    metrics = metrics.sort_values([geo_col, "month"])
    metrics["growth_rate"] = metrics.groupby(geo_col)["stratified_median_price"].transform(
        lambda x: x.pct_change() * 100
    )

    return calculate_momentum(metrics, date_column="month", geo_column=geo_col)


def validate_metrics(metrics_df: pd.DataFrame) -> dict[str, Any]:
    """Validate calculated metrics.

    Args:
        metrics_df: DataFrame with calculated metrics

    Returns:
        Dictionary with validation results
    """
    return {
        "total_records": len(metrics_df),
        "date_range": (metrics_df["month"].min(), metrics_df["month"].max()),
        "missing_values": metrics_df.isnull().sum().to_dict(),
        "outliers": {
            "growth_rate_extreme": ((metrics_df["growth_rate"].abs() > 50).sum()),
            "negative_prices": ((metrics_df["stratified_median_price"] < 0).sum()),
        },
        "geo_coverage": metrics_df["planning_area"].nunique()
        if "planning_area" in metrics_df.columns
        else None,
    }
