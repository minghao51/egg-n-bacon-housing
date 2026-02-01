"""Housing market metrics calculation functions.

This module provides functions to calculate various housing market metrics
from transaction data, including:
- Price growth rates (stratified median)
- Price per square foot (PSF)
- Transaction volume
- Market momentum
- Affordability index (using estimated income data)
- ROI potential score (with rental data)
"""

from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

import numpy as np
import pandas as pd


# Default mortgage parameters
DEFAULT_DOWN_PAYMENT_PCT = 0.20
DEFAULT_INTEREST_RATE = 0.035  # 3.5%
DEFAULT_LOAN_TERM_YEARS = 25.0


# ============================================================================
# AFFORDABILITY INDEX
# ============================================================================

@dataclass
class AffordabilityResult:
    """Container for affordability calculation results."""
    planning_area: str
    median_price: float
    estimated_annual_income: float
    affordability_ratio: float
    monthly_mortgage: float
    mortgage_to_income_pct: float
    months_of_income: float
    affordability_class: str


def calculate_mortgage_payment(
    property_price: float,
    down_payment_pct: float = DEFAULT_DOWN_PAYMENT_PCT,
    interest_rate: float = DEFAULT_INTEREST_RATE,
    loan_term_years: float = DEFAULT_LOAN_TERM_YEARS
) -> float:
    """Calculate estimated monthly mortgage payment.

    Uses standard Singapore mortgage terms:
    - 20% down payment (CPF or cash)
    - 3.5% interest rate (current market rate)
    - 25-year loan term (maximum for HDB)

    Args:
        property_price: Property price in SGD
        down_payment_pct: Down payment as percentage (0.20 = 20%)
        interest_rate: Annual interest rate (0.035 = 3.5%)
        loan_term_years: Loan term in years

    Returns:
        Monthly mortgage payment in SGD
    """
    loan_amount = property_price * (1 - down_payment_pct)
    monthly_rate = interest_rate / 12
    num_payments = loan_term_years * 12

    if monthly_rate > 0:
        monthly_payment = loan_amount * (
            (monthly_rate * (1 + monthly_rate) ** num_payments) /
            ((1 + monthly_rate) ** num_payments - 1)
        )
    else:
        monthly_payment = loan_amount / num_payments

    return monthly_payment


def calculate_affordability_ratio(
    property_price: float,
    annual_household_income: float
) -> float:
    """Calculate affordability ratio (price / annual income).

    Args:
        property_price: Property price in SGD
        annual_household_income: Annual household income in SGD

    Returns:
        Affordability ratio (e.g., 5.0 means price is 5x annual income)
    """
    if annual_household_income <= 0:
        return np.nan
    return property_price / annual_household_income


def classify_affordability(ratio: float) -> str:
    """Classify affordability based on ratio.

    Singapore-specific thresholds based on housing market norms.

    Args:
        ratio: Affordability ratio

    Returns:
        Classification string
    """
    if ratio < 3.0:
        return 'Affordable'
    elif ratio < 5.0:
        return 'Moderate'
    elif ratio < 7.0:
        return 'Expensive'
    else:
        return 'Severely Unaffordable'


def calculate_affordability_metrics(
    property_price: float,
    annual_household_income: float,
    planning_area: str = None
) -> AffordabilityResult:
    """Calculate comprehensive affordability metrics.

    Args:
        property_price: Median property price in SGD
        annual_household_income: Estimated annual household income in SGD
        planning_area: Planning area name (optional)

    Returns:
        AffordabilityResult dataclass with all metrics
    """
    # Calculate affordability ratio
    ratio = calculate_affordability_ratio(property_price, annual_household_income)

    # Calculate mortgage payment
    mortgage = calculate_mortgage_payment(property_price)

    # Calculate mortgage as percentage of income
    mortgage_pct = (mortgage * 12 / annual_household_income * 100) if annual_household_income > 0 else np.nan

    # Calculate months of income to buy
    monthly_income = annual_household_income / 12
    months_of_income = property_price / monthly_income if monthly_income > 0 else np.nan

    # Classify affordability
    affordability_class = classify_affordability(ratio)

    return AffordabilityResult(
        planning_area=planning_area or '',
        median_price=property_price,
        estimated_annual_income=annual_household_income,
        affordability_ratio=ratio,
        monthly_mortgage=mortgage,
        mortgage_to_income_pct=mortgage_pct,
        months_of_income=months_of_income,
        affordability_class=affordability_class
    )


def calculate_affordability_dataframe(
    prices_df: pd.DataFrame,
    income_df: pd.DataFrame,
    price_col: str = 'median_price',
    income_col: str = 'estimated_median_annual_income',
    geo_col: str = 'planning_area'
) -> pd.DataFrame:
    """Calculate affordability metrics for multiple planning areas.

    Args:
        prices_df: DataFrame with property prices by planning area
        income_df: DataFrame with income estimates by planning area
        price_col: Column name for property price
        income_col: Column name for annual income
        geo_col: Column name for planning area

    Returns:
        DataFrame with affordability metrics for each planning area
    """
    # Merge prices and income
    df = prices_df.merge(
        income_df[[geo_col, income_col]],
        on=geo_col,
        how='left'
    )

    # Calculate metrics
    df['affordability_ratio'] = df.apply(
        lambda row: calculate_affordability_ratio(row[price_col], row[income_col]),
        axis=1
    )

    df['monthly_mortgage'] = df[price_col].apply(calculate_mortgage_payment)

    df['mortgage_to_income_pct'] = df.apply(
        lambda row: (row['monthly_mortgage'] * 12 / row[income_col] * 100) if row[income_col] > 0 else np.nan,
        axis=1
    )

    df['months_of_income'] = df.apply(
        lambda row: row[price_col] / (row[income_col] / 12) if row[income_col] > 0 else np.nan,
        axis=1
    )

    df['affordability_class'] = df['affordability_ratio'].apply(classify_affordability)

    return df


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

def calculate_psf(
    df: pd.DataFrame,
    price_column: str = 'resale_price',
    area_column: str = 'floor_area_sqft',
    agg_method: str = 'median'
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
    psf = df[price_column] / df[area_column]
    return psf


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
# ADVANCED METRICS (Updated with estimated income data)
# ============================================================================

def calculate_affordability(
    property_prices: Union[pd.Series, float],
    income_data: Union[pd.Series, pd.DataFrame, float],
    planning_area: Optional[str] = None
) -> Union[AffordabilityResult, pd.DataFrame]:
    """Calculate affordability ratio (price / income).

    This function now uses estimated income data based on HDB loan eligibility
    ratios as a proxy for median household income distribution.

    Args:
        property_prices: Property price(s) in SGD
        income_data: Annual household income data (Series or single value)
        planning_area: Planning area name (for single calculations)

    Returns:
        AffordabilityResult for single calculation, DataFrame for multiple
    """
    # Handle single value inputs
    if isinstance(property_prices, (int, float)) and isinstance(income_data, (int, float)):
        return calculate_affordability_metrics(
            property_price=float(property_prices),
            annual_household_income=float(income_data),
            planning_area=planning_area
        )

    # Handle DataFrame/Series inputs
    if isinstance(income_data, pd.DataFrame):
        # Assume income_data has 'planning_area' and income column
        return calculate_affordability_dataframe(
            prices_df=pd.DataFrame({'planning_area': planning_area, 'median_price': property_prices}) if isinstance(property_prices, pd.Series) else property_prices,
            income_df=income_data,
            price_col='median_price' if isinstance(property_prices, pd.DataFrame) else None,
            income_col='estimated_median_annual_income',
            geo_col='planning_area'
        )

    # Handle Series inputs
    if isinstance(property_prices, pd.Series) and isinstance(income_data, pd.Series):
        result_df = pd.DataFrame({
            'median_price': property_prices,
            'estimated_median_annual_income': income_data
        })
        return calculate_affordability_dataframe(
            prices_df=result_df,
            income_df=pd.DataFrame({'planning_area': result_df.index, 'estimated_median_annual_income': income_data}) if income_data.index.name else result_df,
            price_col='median_price',
            income_col='estimated_median_annual_income',
            geo_col='planning_area'
        )

    raise ValueError("Unsupported input types for calculate_affordability")


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
    unified_df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """Compute all monthly metrics for HDB and condo transactions.

    Args:
        unified_df: Unified transaction DataFrame with both HDB and Condo
        start_date: Start date (YYYY-MM format)
        end_date: End date (YYYY-MM format)

    Returns:
        DataFrame with all metrics
    """
    # Split by property type
    hdb_df = unified_df[unified_df['property_type'] == 'HDB'].copy()
    condo_df = unified_df[unified_df['property_type'] == 'Condominium'].copy()

    # Process HDB
    hdb_metrics = _process_property_type(hdb_df, 'HDB', start_date, end_date)

    # Process Condo
    condo_metrics = _process_property_type(condo_df, 'Condo', start_date, end_date)

    # Combine
    all_metrics = pd.concat([hdb_metrics, condo_metrics], ignore_index=True)

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

    # Determine column names (unified data uses consistent naming)
    price_col = 'price'
    area_col = 'floor_area_sqft'
    geo_col = 'planning_area'

    # Add PSF
    df['psf'] = calculate_psf(df, price_col, area_col)

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
# COMING SOON METRICS
# ============================================================================

def calculate_forecasted_metrics(
    df: pd.DataFrame,
    planning_area: str,
    horizons: List[int] = [6, 12]
) -> Dict[str, Dict[str, float]]:
    """Calculate forecasted metrics for future periods.

    Args:
        df: Transaction data with 'price' and 'transaction_date' columns
        planning_area: Filter for specific planning area
        horizons: List of forecast horizons in months

    Returns:
        Dictionary with forecasted metrics for each horizon
    """
    # Filter by planning area
    pa_df = df[df['planning_area'] == planning_area].copy()

    if len(pa_df) < 24:
        return {}

    # Aggregate by month
    pa_df['month'] = pd.to_datetime(pa_df['transaction_date']).dt.to_period('M')
    monthly = pa_df.groupby('month')['price'].median().reset_index()
    monthly.columns = ['period', 'median_price']
    monthly = monthly.sort_values('period')

    if len(monthly) < 12:
        return {}

    # Use recent 12 months for trend
    recent = monthly.tail(12)
    x = np.arange(len(recent))
    y = recent['median_price'].values

    # Linear trend
    slope, intercept = np.polyfit(x, y, 1)

    last_price = recent['median_price'].iloc[-1]
    last_date = recent['period'].iloc[-1].to_timestamp()

    forecasts = {}

    for horizon in horizons:
        predicted = last_price + (slope * horizon)

        # Confidence intervals (wider for longer horizons)
        confidence_multiplier = 1 + (horizon * 0.02)

        forecasts[f'{horizon}m'] = {
            'predicted_value': round(predicted, 2),
            'confidence_lower': round(predicted / confidence_multiplier, 2),
            'confidence_upper': round(predicted * confidence_multiplier, 2),
            'trend_pct': round(((predicted - last_price) / last_price) * 100, 2),
            'forecast_date': (last_date + pd.DateOffset(months=horizon)).strftime('%Y-%m-%d'),
        }

    return forecasts


def calculate_era_comparison(
    df: pd.DataFrame,
    planning_area: str,
    metric_column: str = 'price'
) -> Dict[str, float]:
    """Calculate metrics across Pre-COVID, COVID, and Post-COVID periods.

    Args:
        df: Transaction data
        planning_area: Filter for specific planning area
        metric_column: Column to aggregate

    Returns:
        Dictionary with era comparison metrics
    """
    pa_df = df[df['planning_area'] == planning_area].copy()

    # Extract year if needed
    if 'year' not in pa_df.columns and 'transaction_date' in pa_df.columns:
        pa_df['year'] = pd.to_datetime(pa_df['transaction_date']).dt.year

    # Assign era
    def assign_era(year):
        if year <= 2019:
            return 'pre_covid'
        elif year <= 2021:
            return 'covid'
        else:
            return 'post_covid'

    pa_df['era'] = pa_df['year'].apply(assign_era)

    # Calculate median by era
    era_medians = pa_df.groupby('era')[metric_column].median().to_dict()

    result = {
        'pre_covid_value': era_medians.get('pre_covid'),
        'covid_value': era_medians.get('covid'),
        'post_covid_value': era_medians.get('post_covid'),
    }

    # Calculate impacts
    pre = result['pre_covid_value'] or 0
    covid = result['covid_value'] or pre
    post = result['post_covid_value'] or covid

    if pre > 0:
        result['covid_impact_pct'] = round(((covid - pre) / pre) * 100, 2)
        result['recovery_pct'] = round(((post - covid) / covid) * 100, 2) if covid > 0 else 0
    else:
        result['covid_impact_pct'] = 0
        result['recovery_pct'] = 0

    # Whole period value
    result['whole_period_value'] = pa_df[metric_column].median()

    return result


def identify_coming_soon(
    df: pd.DataFrame,
    months_ahead: int = 3
) -> pd.DataFrame:
    """Identify properties that are 'coming soon' based on patterns.

    Args:
        df: Transaction data
        months_ahead: Number of months to look ahead for 'new' properties

    Returns:
        DataFrame with coming soon flagged properties
    """
    result = df.copy()

    # Convert date
    if 'transaction_date' in result.columns:
        result['transaction_date'] = pd.to_datetime(result['transaction_date'], errors='coerce')

    current_date = pd.Timestamp.now()
    cutoff_date = current_date + pd.DateOffset(months=months_ahead)

    # Coming soon criteria:
    # 1. Recent transactions (last 3 months) - "just launched"
    three_months_ago = current_date - pd.DateOffset(months=3)
    result['is_recent'] = result['transaction_date'] >= three_months_ago

    # 2. High activity areas (top 25% by recent transactions)
    recent_mask = result['transaction_date'] >= (current_date - pd.DateOffset(months=6))
    recent_activity = result[recent_mask].groupby('town').size()
    high_activity_towns = recent_activity[recent_activity >= recent_activity.quantile(0.75)].index.tolist()
    result['is_high_activity'] = result['town'].isin(high_activity_towns)

    # 3. New leases (99+ years remaining)
    if 'remaining_lease_years' in result.columns:
        result['is_new_lease'] = result['remaining_lease_years'] >= 99
    else:
        result['is_new_lease'] = False

    # Combined coming soon flag
    result['is_coming_soon'] = result['is_recent'] | result['is_high_activity'] | result['is_new_lease']

    return result


def calculate_coming_soon_score(
    property_df: pd.DataFrame,
    yield_weight: float = 0.40,
    momentum_weight: float = 0.30,
    infra_weight: float = 0.20,
    amenity_weight: float = 0.10
) -> pd.DataFrame:
    """Calculate investment scores for coming soon properties.

    Args:
        property_df: Property data with relevant columns
        yield_weight: Weight for rental yield (default 40%)
        momentum_weight: Weight for price momentum (default 30%)
        infra_weight: Weight for infrastructure (default 20%)
        amenity_weight: Weight for amenities (default 10%)

    Returns:
        DataFrame with investment scores added
    """
    result = property_df.copy()

    # 1. Rental yield score
    if 'rental_yield_pct' in result.columns:
        yield_vals = result['rental_yield_pct'].fillna(result['rental_yield_pct'].median())
        yield_max = yield_vals.max()
        if yield_max > 0:
            result['yield_score'] = (yield_vals / yield_max) * yield_weight * 100
        else:
            result['yield_score'] = yield_weight * 50
    else:
        result['yield_score'] = yield_weight * 50

    # 2. Momentum score
    if 'mom_change_pct' in result.columns:
        momentum = result['mom_change_pct'].fillna(0)
        mom_min, mom_max = momentum.min(), momentum.max()
        if mom_max > mom_min:
            result['momentum_score'] = ((momentum - mom_min) / (mom_max - mom_min)) * momentum_weight * 100
        else:
            result['momentum_score'] = momentum_weight * 50
    else:
        result['momentum_score'] = momentum_weight * 50

    # 3. Infrastructure score (inverse of MRT distance)
    if 'dist_to_nearest_mrt' in result.columns:
        mrt = result['dist_to_nearest_mrt'].fillna(result['dist_to_nearest_mrt'].median())
        mrt_min, mrt_max = mrt.min(), mrt.max()
        if mrt_max > mrt_min:
            result['infra_score'] = ((mrt_max - mrt) / (mrt_max - mrt_min)) * infra_weight * 100
        else:
            result['infra_score'] = infra_weight * 50
    else:
        result['infra_score'] = infra_weight * 50

    # 4. Amenity score
    amenity_cols = [c for c in result.columns if 'within' in c.lower() and 'km' in c.lower()]
    if amenity_cols:
        amenity_vals = result[amenity_cols].mean(axis=1).fillna(0)
        amen_min, amen_max = amenity_vals.min(), amenity_vals.max()
        if amen_max > amen_min:
            result['amenity_score'] = ((amenity_vals - amen_min) / (amen_max - amen_min)) * amenity_weight * 100
        else:
            result['amenity_score'] = amenity_weight * 50
    else:
        result['amenity_score'] = amenity_weight * 50

    # Total investment score
    result['investment_score'] = (
        result['yield_score'] +
        result['momentum_score'] +
        result['infra_score'] +
        result['amenity_score']
    )

    return result


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
