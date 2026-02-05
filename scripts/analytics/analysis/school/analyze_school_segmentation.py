"""
Segmentation and Interaction Effects Analysis for School Impact

Analyzes how school quality effects vary across market segments:
- Property type (HDB vs Condo)
- Region (CCR vs RCR vs OCR)
- Interactions with size, location, lease

Creates 9 market segments (property_type × region) and runs separate models
to identify heterogeneous treatment effects.

Usage:
    uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import logging
import warnings

warnings.filterwarnings("ignore")

from scripts.analytics.analysis.school.utils.interaction_models import SegmentationAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analysis/school_segmentation")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load and prepare data."""
    print("=" * 80)
    print("SEGMENTATION AND INTERACTION EFFECTS ANALYSIS")
    print("=" * 80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    print(f"  Full dataset: {len(df):,} records")

    # Filter to 2021+ for consistency
    df = df[df["year"] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Check required columns
    required_cols = ["planning_area", "property_type", "school_primary_quality_score"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    print(f"  Property types: {df['property_type'].unique()}")
    print(f"  Planning areas: {df['planning_area'].nunique()}")

    return df


def prepare_features(df):
    """Prepare features for segmentation analysis."""
    print("\nPreparing features...")

    # Feature list
    feature_cols = [
        "floor_area_sqm",
        "remaining_lease_months",
        "year",
        "school_accessibility_score",
        "school_primary_quality_score",
        "school_secondary_quality_score",
        "dist_to_nearest_mrt",
        "dist_to_nearest_hawker",
    ]

    # Filter to available columns
    feature_cols = [col for col in feature_cols if col in df.columns]

    # Drop rows with NaN in features or target
    df_model = df.dropna(subset=feature_cols + ["price_psf"]).copy()

    print(f"  Features: {len(feature_cols)}")
    print(f"  Records: {len(df_model):,}")

    return df_model, feature_cols


def main():
    """Main analysis pipeline."""

    # Load data
    df = load_data()

    # Prepare features
    df_model, feature_cols = prepare_features(df)

    # Initialize analyzer
    print("\nInitializing SegmentationAnalyzer...")
    analyzer = SegmentationAnalyzer(OUTPUT_DIR)

    # Create market segments
    print("\n" + "=" * 80)
    print("STAGE 1: MARKET SEGMENTATION")
    print("=" * 80)
    df_segmented = analyzer.create_market_segments(df_model)

    # Create interaction features
    print("\n" + "=" * 80)
    print("STAGE 2: INTERACTION FEATURES")
    print("=" * 80)
    df_with_interactions = analyzer.create_interaction_features(df_segmented)

    # Run segmented models
    print("\n" + "=" * 80)
    print("STAGE 3: SEGMENTED MODELS")
    print("=" * 80)
    segment_results = analyzer.run_segmented_models(
        df_with_interactions,
        feature_cols=feature_cols,
        target_col="price_psf"
    )

    # Save segment coefficients
    print("\n" + "=" * 80)
    print("STAGE 4: SEGMENT COEFFICIENTS")
    print("=" * 80)
    coef_df = analyzer.save_segment_coefficients()

    if coef_df is not None:
        print("\nSegment Coefficients:")
        print(coef_df.to_string())

    # Compare R² across segments
    print("\n" + "=" * 80)
    print("STAGE 5: R² COMPARISON")
    print("=" * 80)
    r2_df = analyzer.compare_r2_across_segments()

    if r2_df is not None:
        print("\nR² by Segment:")
        print(r2_df.to_string(index=False))

    # Run interaction model
    print("\n" + "=" * 80)
    print("STAGE 6: INTERACTION MODEL")
    print("=" * 80)
    interaction_result = analyzer.run_interaction_model(
        df_with_interactions,
        base_features=feature_cols,
        target_col="price_psf"
    )

    # Save interaction results
    print("\n" + "=" * 80)
    print("STAGE 7: INTERACTION EFFECTS")
    print("=" * 80)
    interaction_df = analyzer.save_interaction_results()

    if interaction_df is not None:
        print("\nTop Interaction Effects:")
        print(interaction_df.head(10).to_string(index=False))

        # Count significant interactions
        n_significant = (interaction_df['abs_coef'] > 5).sum()
        print(f"\nSignificant interactions (|coef| > 5): {n_significant}")

    # Print summary
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print(f"  - segment_coefficients.csv: School effects by market segment")
    print(f"  - segment_r2_comparison.csv: Model performance by segment")
    print(f"  - interaction_model_results.csv: Interaction term coefficients")

    # Key findings
    if coef_df is not None and not coef_df.empty:
        print("\n" + "=" * 80)
        print("KEY FINDINGS")
        print("=" * 80)

        # Find segments with highest school impact
        if 'school_primary_quality_score' in coef_df.columns:
            top_segment = coef_df['school_primary_quality_score'].idxmax()
            top_coef = coef_df['school_primary_quality_score'].max()
            print(f"\nHighest school impact: {top_segment}")
            print(f"  Coefficient: {top_coef:.2f} $/psf per quality point")

            bottom_segment = coef_df['school_primary_quality_score'].idxmin()
            bottom_coef = coef_df['school_primary_quality_score'].min()
            print(f"\nLowest school impact: {bottom_segment}")
            print(f"  Coefficient: {bottom_coef:.2f} $/psf per quality point")

    if interaction_df is not None and not interaction_df.empty:
        print("\n" + "-" * 80)
        print("Top 3 Interaction Effects:")
        for _, row in interaction_df.head(3).iterrows():
            print(f"  {row['feature']}: {row['coefficient']:.2f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
