#!/usr/bin/env python3
"""Impute rental yields using planning area averages - fully vectorized."""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.data_helpers import load_parquet, save_parquet

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Main function to impute rental yields."""
    logger.info("🚀 Starting rental yield imputation")

    df = load_parquet("L3_housing_unified")
    logger.info(f"Loaded {len(df):,} records")

    original_coverage = df['rental_yield_pct'].notna().sum() / len(df) * 100
    logger.info(f"Original rental yield coverage: {original_coverage:.1f}%")

    # Load planning area yield averages
    pa_yields = load_parquet('L5_rental_yield_by_area')
    pa_median = pa_yields.set_index('planning_area')['median'].to_dict()
    logger.info(f"Loaded {len(pa_median)} planning area yields")

    # Track original vs imputed
    original_mask = df['rental_yield_pct'].notna()

    # Vectorized: map planning area to yield
    df['pa_yield'] = df['planning_area'].map(pa_median)

    # Fill missing rental_yield_pct with pa_yield
    missing_mask = df['rental_yield_pct'].isna()
    df.loc[missing_mask, 'rental_yield_pct'] = df.loc[missing_mask, 'pa_yield']

    imputed_by_pa = (missing_mask & df['rental_yield_pct'].notna()).sum()
    logger.info(f"Imputed {imputed_by_pa:,} yields by planning area")

    # Step 2: For remaining missing, use property type median
    remaining_missing = df['rental_yield_pct'].isna().sum()
    if remaining_missing > 0:
        type_medians = df.groupby('property_type')['rental_yield_pct'].transform('median')
        overall_median = df['rental_yield_pct'].median()
        fill_value = type_medians.fillna(overall_median)

        df['rental_yield_pct'] = df['rental_yield_pct'].fillna(fill_value)
        logger.info(f"Imputed {remaining_missing:,} yields by property type")

    # Mark imputed records
    df['rental_yield_imputed'] = ~original_mask

    # Clean up temp column
    df.drop(columns=['pa_yield'], inplace=True)

    final_count = df['rental_yield_pct'].notna().sum()
    coverage = final_count / len(df) * 100

    logger.info(f"✅ Rental yield coverage: {coverage:.1f}% ({final_count:,} / {len(df):,})")
    logger.info(f"   Original: {original_mask.sum():,}, Imputed: {df['rental_yield_imputed'].sum():,}")

    # Save updated dataset
    save_parquet(df, "L3_housing_unified", source="Rental yield imputation")
    logger.info("✅ Saved updated L3_housing_unified with imputed yields")


if __name__ == "__main__":
    main()
