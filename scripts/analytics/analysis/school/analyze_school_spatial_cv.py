"""
Spatial Cross-Validation Analysis for School Impact

Tests whether school impact models generalize to new geographic areas,
guarding against spatial autocorrelation bias.

Usage:
    uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

from scripts.analytics.analysis.school.utils.spatial_validation import SpatialValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analytics/school_spatial_cv")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load and prepare data."""
    print("=" * 80)
    print("SPATIAL CROSS-VALIDATION ANALYSIS")
    print("=" * 80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    print(f"  Full dataset: {len(df):,} records")

    # Filter to 2021+ for consistency
    df = df[df["year"] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Check required columns
    required_cols = ["planning_area", "school_accessibility_score"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    print(f"  Planning areas: {df['planning_area'].nunique()}")
    print("  School data available: Yes")

    return df


def prepare_features(df, target_col="price_psf"):
    """Prepare features for spatial CV."""
    print(f"\nPreparing features for: {target_col}")

    # Drop rows with missing target
    df_model = df.dropna(subset=[target_col]).copy()

    # Feature columns
    feature_cols = [
        "floor_area_sqm",
        "remaining_lease_months",
        "school_accessibility_score",
        "school_primary_quality_score",
        "school_secondary_quality_score",
        "dist_to_nearest_mrt",
        "dist_to_nearest_hawker",
        "dist_to_nearest_supermarket",
    ]

    # Filter to available columns
    feature_cols = [col for col in feature_cols if col in df_model.columns]

    # Drop rows with NaN in features
    df_model = df_model.dropna(subset=feature_cols)

    print(f"  Features: {len(feature_cols)}")
    print(f"  Records: {len(df_model):,}")

    return df_model, feature_cols


def main():
    """Main analysis pipeline."""

    # Load data
    df = load_data()

    # Initialize validator
    validator = SpatialValidator(OUTPUT_DIR)

    # Prepare features
    df_model, feature_cols = prepare_features(df, "price_psf")

    # Extract features and target
    X = df_model[feature_cols]
    y = df_model["price_psf"]
    groups = df_model["planning_area"]

    print("\n" + "=" * 80)
    print("COMPARING CV METHODS")
    print("=" * 80)

    # Compare OLS
    print("\n1. OLS Model")
    ols_result = validator.compare_cv_methods(X, y, groups, model_type="ols")

    # Compare Random Forest
    print("\n2. Random Forest Model")
    rf_result = validator.compare_cv_methods(X, y, groups, model_type="rf")

    # Compare XGBoost
    print("\n3. XGBoost Model")
    xgb_result = validator.compare_cv_methods(X, y, groups, model_type="xgboost")

    # Save performance comparison
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    perf_df = validator.save_performance_comparison()
    print("\nPerformance Comparison:")
    print(perf_df.to_string(index=False))

    # Analyze area generalization
    print("\n" + "=" * 80)
    print("ANALYZING PLANNING AREA GENERALIZATION")
    print("=" * 80)

    area_results = validator.analyze_area_generalization(
        df_model, feature_cols, "price_psf", "planning_area"
    )

    # Test spatial autocorrelation
    print("\n" + "=" * 80)
    print("TESTING SPATIAL AUTOCORRELATION")
    print("=" * 80)

    # Get residuals from OLS
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = LinearRegression()
    model.fit(X_train, y_train)
    residuals = pd.Series(y_test - model.predict(X_test), index=X_test.index)

    moran_result = validator.test_spatial_autocorrelation(
        residuals, df_model.loc[X_test.index, ["planning_area"]]
    )

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print("\nKey findings:")
    print(f"  - Spatial generalization gap (OLS): {ols_result['gap_pct']:.1f}%")
    print(f"  - Worst generalizing area: {area_results.iloc[0]['planning_area']}")


if __name__ == "__main__":
    main()
