"""Prepare policy impact findings from L3/L5 data.

This script analyzes HDB transaction data post-2022 to extract policy impact insights.
It calculates DiD statistics, YoY growth rates, and volume changes by region.
"""

import logging

import numpy as np
import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# Regional classification for DiD analysis
CCR_REGIONS = [
    'Bukit Timah', 'Downtown Core', 'Marine Parade', 'Newton',
    'Orchard', 'Outram', 'River Valley', 'Rochor', 'Singapore River', 'Straits View'
]

RCR_REGIONS = [
    'Bishan', 'Bukit Merah', 'Geylang', 'Kallang', 'Lavender',
    'Marina East', 'Marina South', 'Novena', 'Queenstown',
    'Southern Islands', 'Tanglin', 'Toa Payoh'
]

# All other areas are OCR


def classify_region(planning_area: str) -> str:
    """Classify planning area into CCR/RCR/OCR."""
    if pd.isna(planning_area):
        return 'Unknown'
    if planning_area in CCR_REGIONS:
        return 'CCR'
    elif planning_area in RCR_REGIONS:
        return 'RCR'
    else:
        return 'OCR'


def load_hdb_post2022_data() -> pd.DataFrame:
    """Load L3 unified data and filter to HDB post-2022."""
    logger.info("=" * 60)
    logger.info("Loading L3 Unified Data (HDB, post-2022)")
    logger.info("=" * 60)

    # Try housing_unified first (L3 output), fallback to direct path
    try:
        df = load_parquet("housing_unified")
    except ValueError:
        # Load directly from L3 directory
        l3_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
        logger.info(f"Loading from direct path: {l3_path}")
        df = pd.read_parquet(l3_path)

    if df.empty:
        logger.error("No data loaded")
        return pd.DataFrame()

    logger.info(f"Loaded {len(df):,} total transactions")

    # Filter to HDB
    df_hdb = df[df['property_type'] == 'HDB'].copy()
    logger.info(f"HDB transactions: {len(df_hdb):,} ({len(df_hdb)/len(df)*100:.1f}%)")

    # Filter to post-2022
    df_hdb['transaction_date'] = pd.to_datetime(df_hdb['transaction_date'])
    df_post2022 = df_hdb[df_hdb['transaction_date'] >= '2022-01-01'].copy()
    logger.info(f"Post-2022 HDB transactions: {len(df_post2022):,}")

    # Add temporal columns
    df_post2022['year'] = df_post2022['transaction_date'].dt.year
    df_post2022['month'] = df_post2022['transaction_date'].dt.to_period('M').astype(str)

    return df_post2022


def load_growth_metrics() -> pd.DataFrame:
    """Load L5 growth metrics and filter to HDB post-2022."""
    logger.info("=" * 60)
    logger.info("Loading L5 Growth Metrics")
    logger.info("=" * 60)

    try:
        growth_df = load_parquet("L5_growth_metrics_by_area")
        logger.info(f"Loaded {len(growth_df):,} growth metric records")
    except ValueError:
        # Load directly from pipeline directory
        l5_path = Config.PARQUETS_DIR / "L5_growth_metrics_by_area.parquet"
        logger.info(f"Loading from direct path: {l5_path}")
        growth_df = pd.read_parquet(l5_path)
        logger.info(f"Loaded {len(growth_df):,} growth metric records")
    except Exception as e:
        logger.warning(f"Could not load L5 growth metrics: {e}")
        return pd.DataFrame()

    # Filter to post-2022 (month format is 'YYYY-MM')
    if not growth_df.empty and 'month' in growth_df.columns:
        growth_post2022 = growth_df[growth_df['month'] >= '2022-01'].copy()
        logger.info(f"Post-2022 growth metrics: {len(growth_post2022):,} records")
        return growth_post2022

    return growth_df


def calculate_regional_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly aggregates by region (CCR/RCR/OCR)."""
    logger.info("=" * 60)
    logger.info("Calculating Regional Aggregates")
    logger.info("=" * 60)

    # Classify regions
    df['region'] = df['planning_area'].apply(classify_region)

    # Count by region
    region_counts = df['region'].value_counts()
    logger.info("\nTransaction Counts by Region:")
    for region in ['CCR', 'RCR', 'OCR', 'Unknown']:
        count = region_counts.get(region, 0)
        logger.info(f"  {region}: {count:,} transactions")

    # Calculate monthly aggregates
    monthly = df.groupby(['region', 'month']).agg({
        'price': ['median', 'mean', 'count'],
        'price_psf': ['median', 'mean'] if 'price_psf' in df.columns else 'count'
    }).reset_index()

    monthly.columns = ['_'.join(col).strip('_') for col in monthly.columns]
    monthly = monthly.rename(columns={'region_': 'region', 'month_': 'month'})

    # Sort for time series
    monthly = monthly.sort_values(['region', 'month'])

    logger.info(f"\nCalculated aggregates for {len(monthly)} region-month combinations")

    return monthly


def analyze_policy_events(monthly: pd.DataFrame) -> dict:
    """Analyze price and volume changes around policy events."""
    logger.info("=" * 60)
    logger.info("Analyzing Policy Events")
    logger.info("=" * 60)

    policy_events = {
        'apr_2023': '2023-04',
        'sep_2023': '2023-09',
        'dec_2023': '2023-12'
    }

    results = {}

    for event_name, event_month in policy_events.items():
        logger.info(f"\n--- {event_name.upper()} ({event_month}) ---")

        # Get pre and post periods (3 months each)
        event_date = pd.to_datetime(event_month)

        pre_months = pd.date_range(end=event_date - pd.DateOffset(months=1), periods=3, freq='M').strftime('%Y-%m').tolist()
        post_months = pd.date_range(start=event_date, periods=6, freq='M').strftime('%Y-%m').tolist()

        event_results = {}

        for region in ['CCR', 'OCR']:
            region_data = monthly[monthly['region'] == region]

            # Pre period
            pre_data = region_data[region_data['month'].isin(pre_months)]
            pre_price = pre_data['price_median'].mean() if not pre_data.empty else np.nan

            # Post period
            post_data = region_data[region_data['month'].isin(post_months)]
            post_price = post_data['price_median'].mean() if not post_data.empty else np.nan

            # Calculate change
            if not np.isnan(pre_price) and not np.isnan(post_price):
                price_change_pct = ((post_price - pre_price) / pre_price) * 100
                price_change_abs = post_price - pre_price

                event_results[region] = {
                    'pre_price': pre_price,
                    'post_price': post_price,
                    'price_change_pct': price_change_pct,
                    'price_change_abs': price_change_abs,
                    'pre_volume': pre_data['price_count'].sum() if not pre_data.empty else 0,
                    'post_volume': post_data['price_count'].sum() if not post_data.empty else 0
                }

                logger.info(f"\n{region}:")
                logger.info(f"  Pre-period median: ${pre_price:,.0f}")
                logger.info(f"  Post-period median: ${post_price:,.0f}")
                logger.info(f"  Price change: {price_change_pct:+.2f}% (${price_change_abs:,.0f})")
                logger.info(f"  Volume: {event_results[region]['pre_volume']} → {event_results[region]['post_volume']}")

        # Calculate DiD
        if 'CCR' in event_results and 'OCR' in event_results:
            ccr_change = event_results['CCR']['price_change_pct']
            ocr_change = event_results['OCR']['price_change_pct']
            did_estimate = ccr_change - ocr_change

            logger.info(f"\nDiD Estimate: {did_estimate:+.2f} percentage points")
            logger.info(f"  (CCR {ccr_change:+.2f}% - OCR {ocr_change:+.2f}%)")

            results[event_name] = {
                'event_month': event_month,
                'ccr': event_results.get('CCR', {}),
                'ocr': event_results.get('OCR', {}),
                'did_estimate_pct': did_estimate
            }

    return results


def analyze_yoy_trends(df: pd.DataFrame, growth_df: pd.DataFrame) -> dict:
    """Analyze YoY growth trends by region."""
    logger.info("=" * 60)
    logger.info("Analyzing YoY Growth Trends")
    logger.info("=" * 60)

    df = df.copy()
    df['region'] = df['planning_area'].apply(classify_region)

    # Calculate YoY growth by region and year
    yearly = df.groupby(['region', 'year'])['price'].median().reset_index()
    yearly['yoy_growth'] = yearly.groupby('region')['price'].pct_change() * 100

    logger.info("\nYear-over-Year Price Growth by Region:")
    for region in ['CCR', 'RCR', 'OCR']:
        region_data = yearly[yearly['region'] == region].sort_values('year')
        logger.info(f"\n{region}:")
        for _, row in region_data.iterrows():
            if not pd.isna(row['yoy_growth']):
                logger.info(f"  {int(row['year'])}: {row['yoy_growth']:+.2f}% (median: ${row['price']:,.0f})")

    # Pre vs post policy comparison
    pre_policy = yearly[yearly['year'].isin([2022, 2023])].groupby('region')['yoy_growth'].mean()
    post_policy = yearly[yearly['year'].isin([2024, 2025])].groupby('region')['yoy_growth'].mean()

    logger.info("\nAverage YoY Growth:")
    logger.info("Pre-Policy (2022-2023):")
    for region in ['CCR', 'RCR', 'OCR']:
        if region in pre_policy.index:
            logger.info(f"  {region}: {pre_policy[region]:+.2f}%")

    logger.info("\nPost-Policy (2024-2025):")
    for region in ['CCR', 'RCR', 'OCR']:
        if region in post_policy.index:
            logger.info(f"  {region}: {post_policy[region]:+.2f}%")

    return {
        'yearly_by_region': yearly,
        'pre_policy_avg': pre_policy.to_dict(),
        'post_policy_avg': post_policy.to_dict()
    }


def calculate_appreciation_hotspots(df: pd.DataFrame) -> pd.DataFrame:
    """Identify top/bottom performing planning areas."""
    logger.info("=" * 60)
    logger.info("Identifying Appreciation Hotspots")
    logger.info("=" * 60)

    # Calculate YoY growth by planning area
    area_yearly = df.groupby(['planning_area', 'year'])['price'].median().reset_index()
    area_yearly['yoy_growth'] = area_yearly.groupby('planning_area')['price'].pct_change() * 100

    # Filter to 2023-2025 for post-policy analysis
    recent = area_yearly[area_yearly['year'] >= 2023]
    area_stats = recent.groupby('planning_area')['yoy_growth'].agg(['mean', 'median', 'count']).reset_index()
    area_stats = area_stats[area_stats['count'] >= 2]  # At least 2 years of data
    area_stats = area_stats.sort_values('mean', ascending=False)

    logger.info("\nTop 5 Planning Areas (YoY Growth):")
    for _, row in area_stats.head(5).iterrows():
        logger.info(f"  {row['planning_area']}: {row['mean']:+.2f}% (median: {row['median']:+.2f}%)")

    logger.info("\nBottom 5 Planning Areas (YoY Growth):")
    for _, row in area_stats.tail(5).iterrows():
        logger.info(f"  {row['planning_area']}: {row['mean']:+.2f}% (median: {row['median']:+.2f}%)")

    return area_stats


def main():
    """Main analysis pipeline."""
    logger.info("\n" + "=" * 60)
    logger.info("POLICY IMPACT FINDINGS ANALYSIS")
    logger.info("=" * 60 + "\n")

    # Load data
    df = load_hdb_post2022_data()
    growth_df = load_growth_metrics()

    if df.empty:
        logger.error("No data available for analysis")
        return

    # Calculate regional aggregates
    monthly = calculate_regional_aggregates(df)

    # Analyze policy events
    policy_results = analyze_policy_events(monthly)

    # Analyze YoY trends
    yoy_results = analyze_yoy_trends(df, growth_df)

    # Identify hotspots
    hotspots = calculate_appreciation_hotspots(df)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"\nTotal HDB transactions (post-2022): {len(df):,}")
    logger.info(f"Date range: {df['transaction_date'].min().date()} to {df['transaction_date'].max().date()}")
    logger.info(f"Planning areas: {df['planning_area'].nunique()}")
    logger.info(f"Regions: CCR ({len(df[df['region']=='CCR']):,}), RCR ({len(df[df['region']=='RCR']):,}), OCR ({len(df[df['region']=='OCR']):,})")

    return {
        'monthly': monthly,
        'policy_results': policy_results,
        'yoy_results': yoy_results,
        'hotspots': hotspots
    }


if __name__ == '__main__':
    main()
