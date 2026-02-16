"""Residual analysis for price appreciation models.

This script:
1. Loads model predictions and residuals
2. Analyzes residual distribution (normality, skewness)
3. Checks for heteroscedasticity (non-constant variance)
4. Examines spatial autocorrelation (Moran's I)
5. Investigates temporal autocorrelation
6. Identifies error patterns by segment (property type, market tier, etc.)
7. Generates diagnostic visualizations
8. Provides improvement recommendations

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/residual_analysis.py
"""  # noqa: N999

import logging
import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config

# Configure logging
logger = logging.getLogger(__name__)


def load_data():
    """Load predictions and test data."""
    logger.info("Loading predictions and test data...")

    # Load predictions
    predictions_path = (
        Config.DATA_DIR
        / "analysis"
        / "price_appreciation_modeling"
        / "predictions"
        / "test_predictions.parquet"
    )

    if not predictions_path.exists():
        logger.error(f"Predictions not found at {predictions_path}")
        return None, None, None, None

    predictions_df = pd.read_parquet(predictions_path)

    # Load XGBoost model (best model)
    model_path = (
        Config.DATA_DIR
        / "analysis"
        / "price_appreciation_modeling"
        / "models"
        / "XGBoost_model.pkl"
    )

    if not model_path.exists():
        logger.error(f"Model not found at {model_path}")
        return None, None, None, None

    model = joblib.load(model_path)

    # Load test dataset with features
    test_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_test.parquet"

    if not test_path.exists():
        logger.error(f"Test data not found at {test_path}")
        return predictions_df, None, None, None

    test_df = pd.read_parquet(test_path)

    logger.info(f"  Loaded {len(predictions_df)} predictions")
    logger.info(f"  Loaded XGBoost model")

    return predictions_df, test_df, model, predictions_df


def analyze_residual_distribution(
    residuals: pd.Series, output_dir: Path
) -> dict:
    """Analyze residual distribution.

    Args:
        residuals: Residual values
        output_dir: Output directory for plots

    Returns:
        Dictionary with distribution statistics
    """
    logger.info("Analyzing residual distribution...")

    # Basic statistics
    stats_dict = {
        "mean": residuals.mean(),
        "std": residuals.std(),
        "median": residuals.median(),
        "skewness": stats.skew(residuals),
        "kurtosis": stats.kurtosis(residuals),
        "min": residuals.min(),
        "max": residuals.max(),
    }

    logger.info(f"  Mean: {stats_dict['mean']:.2f}")
    logger.info(f"  Std: {stats_dict['std']:.2f}")
    logger.info(f"  Skewness: {stats_dict['skewness']:.2f}")
    logger.info(f"  Kurtosis: {stats_dict['kurtosis']:.2f}")

    # Create histogram
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    axes[0].hist(residuals, bins=50, density=True, alpha=0.7, edgecolor='black')
    axes[0].axvline(0, color='red', linestyle='--', linewidth=2, label='Zero')
    axes[0].set_xlabel('Residuals (Actual - Predicted)')
    axes[0].set_ylabel('Density')
    axes[0].set_title('Residual Distribution')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Q-Q plot
    stats.probplot(residuals, dist="norm", plot=axes[1])
    axes[1].set_title('Q-Q Plot: Normality Check')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "residual_distribution.png", dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved distribution plots to {output_dir}")

    return stats_dict


def analyze_heteroscedasticity(
    y_test: pd.Series, y_pred: pd.Series, residuals: pd.Series, output_dir: Path
) -> dict:
    """Check for heteroscedasticity (non-constant variance).

    Args:
        y_test: Actual values
        y_pred: Predicted values
        residuals: Residual values
        output_dir: Output directory for plots

    Returns:
        Dictionary with test results
    """
    logger.info("Checking for heteroscedasticity...")

    results = {}

    # Plot residuals vs fitted
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Residuals vs Fitted
    axes[0].scatter(y_pred, residuals, alpha=0.1, s=1)
    axes[0].axhline(0, color='red', linestyle='--', linewidth=2)
    axes[0].set_xlabel('Fitted Values (Predicted YoY %)')
    axes[0].set_ylabel('Residuals')
    axes[0].set_title('Residuals vs Fitted (Homoscedasticity Check)')
    axes[0].grid(True, alpha=0.3)

    # Residuals vs Actual
    axes[1].scatter(y_test, residuals, alpha=0.1, s=1)
    axes[1].axhline(0, color='red', linestyle='--', linewidth=2)
    axes[1].set_xlabel('Actual Values (YoY %)')
    axes[1].set_ylabel('Residuals')
    axes[1].set_title('Residuals vs Actual')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "heteroscedasticity_check.png", dpi=150, bbox_inches='tight')
    plt.close()

    # Breusch-Pagan test (simplified version)
    # Test if residual variance increases with fitted values
    from scipy.stats import pearsonr

    abs_residuals = np.abs(residuals)
    corr, p_value = pearsonr(y_pred, abs_residuals)

    results["correlation_abs_residuals_fitted"] = corr
    results["p_value"] = p_value
    results["is_heteroscedastic"] = p_value < 0.05

    logger.info(f"  Correlation (|residuals| vs fitted): {corr:.4f}")
    logger.info(f"  P-value: {p_value:.4f}")
    logger.info(f"  Heteroscedastic: {results['is_heteroscedastic']}")

    return results


def analyze_spatial_autocorrelation(
    test_df: pd.DataFrame, residuals: pd.Series, output_dir: Path
) -> dict:
    """Analyze spatial autocorrelation in residuals.

    Args:
        test_df: Test DataFrame with lat/lon
        residuals: Residual values
        output_dir: Output directory for plots

    Returns:
        Dictionary with spatial autocorrelation results
    """
    logger.info("Analyzing spatial autocorrelation...")

    results = {}

    # Check if lat/lon available
    if "lat" not in test_df.columns or "lon" not in test_df.columns:
        logger.warning("  lat/lon not available, skipping spatial analysis")
        return results

    # Filter to records with coordinates
    valid_coords = test_df[["lat", "lon"]].notna().all(axis=1)

    if not valid_coords.any():
        logger.warning("  No valid coordinates found")
        return results

    lat_lon = test_df.loc[valid_coords, ["lat", "lon"]].values
    residuals_valid = residuals[valid_coords]

    logger.info(f"  Analyzing {len(residuals_valid):,} records with valid coordinates")

    # Calculate Moran's I (simplified - using distance weights)
    # Sample if too large
    if len(residuals_valid) > 10000:
        sample_idx = np.random.choice(len(residuals_valid), 10000, replace=False)
        lat_lon = lat_lon[sample_idx]
        residuals_valid = residuals_valid.iloc[sample_idx]
        logger.info("  Sampled to 10K points for Moran's I calculation")

    # Simple distance-based spatial autocorrelation
    try:
        from sklearn.neighbors import NearestNeighbors

        # Find k nearest neighbors for each point
        k = 10
        nbrs = NearestNeighbors(n_neighbors=k + 1).fit(lat_lon)
        distances, indices = nbrs.kneighbors(lat_lon)

        # Calculate spatial autocorrelation
        moran_values = []
        for i in range(len(residuals_valid)):
            # Skip self (first index)
            neighbor_residuals = residuals_valid.iloc[indices[i, 1:]]
            moran_values.append(residuals_valid.iloc[i] * neighbor_residuals.mean())

        moran_i = np.mean(moran_values) / (residuals_valid.var() + 1e-10)

        results["moran_i"] = moran_i
        results["n_samples"] = len(residuals_valid)

        logger.info(f"  Moran's I: {moran_i:.4f}")
        logger.info(f"  Interpretation: {'Positive spatial autocorrelation' if moran_i > 0 else 'Negative spatial autocorrelation' if moran_i < 0 else 'No spatial pattern'}")

        # Create spatial plot
        fig, ax = plt.subplots(figsize=(12, 8))

        scatter = ax.scatter(
            test_df.loc[valid_coords, "lon"],
            test_df.loc[valid_coords, "lat"],
            c=residuals_valid,
            cmap="coolwarm",
            alpha=0.3,
            s=1,
            vmin=-100,
            vmax=100,
        )

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Spatial Distribution of Residuals")
        plt.colorbar(scatter, ax=ax, label="Residuals (YoY %)")
        plt.tight_layout()
        plt.savefig(output_dir / "spatial_residual_map.png", dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"  Saved spatial map to {output_dir}")

    except Exception as e:
        logger.warning(f"  Spatial autocorrelation calculation failed: {e}")

    return results


def analyze_temporal_autocorrelation(
    test_df: pd.DataFrame, residuals: pd.Series, output_dir: Path
) -> dict:
    """Analyze temporal autocorrelation in residuals.

    Args:
        test_df: Test DataFrame with time info
        residuals: Residual values
        output_dir: Output directory for plots

    Returns:
        Dictionary with temporal autocorrelation results
    """
    logger.info("Analyzing temporal autocorrelation...")

    results = {}

    # Check if time columns available
    if "year" not in test_df.columns and "month" not in test_df.columns:
        logger.warning("  Time columns not available, skipping temporal analysis")
        return results

    # Aggregate residuals by month if we have transaction-level data
    if len(test_df) > 100000:
        # Sample to avoid overplotting
        sample_idx = np.random.choice(len(test_df), size=min(50000, len(test_df)), replace=False)
        residuals_sample = residuals.iloc[sample_idx].reset_index(drop=True)
    else:
        residuals_sample = residuals.reset_index(drop=True)

    logger.info(f"  Analyzing {len(residual_sample):,} records")

    # Calculate autocorrelation
    max_lag = min(12, len(residuals_sample) - 1)
    acf_values = [1.0]  # Lag 0 is always 1.0

    for lag in range(1, max_lag + 1):
        lag_corr = np.corrcoef(
            residuals_sample.iloc[:-lag],
            residuals_sample.iloc[lag:]
        )[0, 1]
        acf_values.append(lag_corr)

    results["acf"] = acf_values
    results["lags"] = list(range(max_lag + 1))

    # Plot ACF
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.stem(results["lags"], acf_values, basefmt=" ")
    ax.axhline(0, color='black', linestyle='-', linewidth=1)
    ax.axhline(0, color='red', linestyle='--', linewidth=2, alpha=0.5)
    ax.set_xlabel('Lag (months)')
    ax.set_ylabel('Autocorrelation')
    ax.set_title('Residual Autocorrelation Function (ACF)')
    ax.grid(True, alpha=0.3)

    # Add confidence bands
    n = len(residuals_sample)
    conf_level = 1.96 / np.sqrt(n)
    ax.fill_between(results["lags"], -conf_level, conf_level, alpha=0.2, color='gray', label='95% CI')

    plt.tight_layout()
    plt.savefig(output_dir / "temporal_autocorrelation.png", dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"  Lag-1 autocorrelation: {acf_values[1]:.4f}")
    logger.info(f"  Saved ACF plot to {output_dir}")

    return results


def analyze_error_patterns(
    test_df: pd.DataFrame, y_test: pd.Series, y_pred: pd.Series, residuals: pd.Series,
    output_dir: Path
) -> pd.DataFrame:
    """Analyze error patterns by segment.

    Args:
        test_df: Test DataFrame with features
        y_test: Actual values
        y_pred: Predicted values
        residuals: Residual values
        output_dir: Output directory for plots

    Returns:
        DataFrame with error patterns by segment
    """
    logger.info("Analyzing error patterns by segment...")

    # Align test_df with predictions (using predictions index)
    test_df_aligned = test_df.loc[y_test.index].copy()

    # Create analysis DataFrame
    error_df = pd.DataFrame({
        "actual": y_test.values,
        "predicted": y_pred.values,
        "residual": residuals.values,
        "abs_error": np.abs(residuals).values,
        "squared_error": residuals.values ** 2,
        "sign_correct": (np.sign(y_pred.values) == np.sign(y_test.values)),
    })

    # Add segment information
    if "property_type" in test_df_aligned.columns:
        error_df["property_type"] = test_df_aligned["property_type"].values

    if "market_tier_period" in test_df.columns:
        error_df["market_tier"] = test_df["market_tier_period"].values

    if "planning_area" in test_df.columns:
        error_df["planning_area"] = test_df["planning_area"].values

    # Calculate statistics by segment
    segment_stats = []

    # By property type
    if "property_type" in error_df.columns:
        prop_stats = error_df.groupby("property_type").agg({
            "abs_error": ["mean", "median", "std", "count"],
            "sign_correct": "mean",
        }).round(2)

        logger.info("\n  By Property Type:")
        for prop_type in prop_stats.index:
            row = prop_stats.loc[prop_type]
            logger.info(f"    {prop_type}: MAE={row[('abs_error', 'mean')]:.1f}, Acc={row[('sign_correct', 'mean')]*100:.1f}%")

        segment_stats.append(prop_stats)

    # By market tier
    if "market_tier" in error_df.columns:
        tier_stats = error_df.groupby("market_tier").agg({
            "abs_error": ["mean", "median", "std", "count"],
            "sign_correct": "mean",
        }).round(2)

        logger.info("\n  By Market Tier:")
        for tier in tier_stats.index:
            row = tier_stats.loc[tier]
            logger.info(f"    {tier}: MAE={row[('abs_error', 'mean')]:.1f}, Acc={row[('sign_correct', 'mean')]*100:.1f}%")

        segment_stats.append(tier_stats)

    # Worst areas
    if "planning_area" in error_df.columns:
        area_stats = error_df.groupby("planning_area").agg({
            "abs_error": "mean",
            "sign_correct": "mean",
            "residual": "count",
        }).sort_values("abs_error", ascending=False)

        logger.info("\n  Top 10 Worst Predicted Planning Areas:")
        for area in area_stats.head(10).index:
            row = area_stats.loc[area]
            logger.info(f"    {area}: MAE={row['abs_error']:.1f}, Acc={row['sign_correct']*100:.1f}%, Count={int(row['residual'])}")

        # Save top areas
        area_stats.head(50).to_csv(output_dir / "error_by_planning_area.csv")

    # Plot error by segment
    if "property_type" in error_df.columns:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Box plot by property type
        error_df.boxplot(column="abs_error", by="property_type", ax=axes[0])
        axes[0].set_xlabel("Property Type")
        axes[0].set_ylabel("Absolute Error")
        axes[0].set_title("Error Distribution by Property Type")
        axes[0].figure.suptitle("")  # Remove default title

        # Bar plot by property type
        prop_mae = error_df.groupby("property_type")["abs_error"].mean().sort_values(ascending=False)
        prop_mae.plot(kind="bar", ax=axes[1], color="steelblue")
        axes[1].set_xlabel("Property Type")
        axes[1].set_ylabel("Mean Absolute Error")
        axes[1].set_title("Mean Absolute Error by Property Type")
        axes[1].tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(output_dir / "error_by_property_type.png", dpi=150, bbox_inches='tight')
        plt.close()

    logger.info(f"\n  Saved error pattern analysis to {output_dir}")

    return error_df


def generate_improvement_recommendations(
    dist_stats: dict, hetero_stats: dict, spatial_stats: dict, temporal_stats: dict,
    output_dir: Path
) -> None:
    """Generate improvement recommendations based on diagnostics.

    Args:
        dist_stats: Distribution statistics
        hetero_stats: Heteroscedasticity test results
        spatial_stats: Spatial autocorrelation results
        temporal_stats: Temporal autocorrelation results
        output_dir: Output directory
    """
    logger.info("Generating improvement recommendations...")

    recommendations = []

    # Distribution issues
    if abs(dist_stats["skewness"]) > 1:
        recommendations.append("1. RESIDUAL SKEWNESS: Residuals are highly skewed (skewness = {:.2f}). Consider target transformation (log, Box-Cox) or robust regression.".format(dist_stats["skewness"]))

    if dist_stats["kurtosis"] > 5 or dist_stats["kurtosis"] < -1:
        recommendations.append("2. HEAVY TAILS: Residuals have heavy tails (kurtosis = {:.2f}). Some extreme errors exist - consider outlier removal or separate models for luxury properties.".format(dist_stats["kurtosis"]))

    # Heteroscedasticity
    if hetero_stats.get("is_heteroscedastic", False):
        recommendations.append("3. HETEROSCEDASTICITY: Variance is not constant across fitted values. Use weighted regression, robust standard errors, or transform target variable.")

    # Spatial autocorrelation
    if spatial_stats.get("moran_i", 0) > 0.1:
        recommendations.append("4. SPATIAL AUTOCORRELATION: Residuals show positive spatial clustering (Moran's I = {:.4f}). Consider adding spatial lag features or regional models.".format(spatial_stats["moran_i"]))

    # Temporal autocorrelation
    if temporal_stats.get("acf") and abs(temporal_stats["acf"][1]) > 0.1:
        recommendations.append("5. TEMPORAL AUTOCORRELATION: Residuals show autocorrelation at lag 1 ({:.4f}). Add autoregressive features or use time series models.".format(temporal_stats["acf"][1]))

    # General recommendations
    recommendations.append("\nGENERAL IMPROVEMENTS:")
    recommendations.append("- Add more temporal features: longer lags, polynomial trends")
    recommendations.append("- Add interaction features: price × amenities, property type × location")
    recommendations.append("- Consider separate models by property type (HDB vs Condo vs EC)")
    recommendations.append("- Use ensemble methods (stacking, blending) to reduce variance")
    recommendations.append("- Add macroeconomic features (interest rates, policy changes)")
    recommendations.append("- Implement cross-validation with spatial folds (leave-one-area-out)")

    # Save recommendations
    recommendations_path = output_dir / "improvement_recommendations.txt"
    with open(recommendations_path, "w") as f:
        f.write("MODEL IMPROVEMENT RECOMMENDATIONS\n")
        f.write("=" * 60 + "\n\n")

        for rec in recommendations:
            f.write(rec + "\n")

    logger.info(f"  Saved recommendations to {recommendations_path}")

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("IMPROVEMENT RECOMMENDATIONS")
    logger.info("=" * 60)

    for rec in recommendations:
        logger.info(rec)


def main():
    """Run residual analysis pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Residual Analysis")
    logger.info("=" * 60)

    # Setup output directory
    output_dir = (
        Config.DATA_DIR
        / "analysis"
        / "price_appreciation_modeling"
        / "residual_analysis"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info("\n[1/6] Loading data...")
    predictions_df, test_df, model, predictions_data = load_data()

    if predictions_df is None:
        logger.error("Failed to load data")
        return

    # Extract variables
    y_test = predictions_df["actual"]
    y_pred_xgb = predictions_df["XGBoost_predicted"]
    residuals_xgb = predictions_df["XGBoost_residual"]

    logger.info(f"  Analyzing {len(y_test):,} test predictions")

    # 1. Distribution analysis
    logger.info("\n[2/6] Analyzing residual distribution...")
    dist_stats = analyze_residual_distribution(residuals_xgb, output_dir)

    # 2. Heteroscedasticity check
    logger.info("\n[3/6] Checking for heteroscedasticity...")
    hetero_stats = analyze_heteroscedasticity(y_test, y_pred_xgb, residuals_xgb, output_dir)

    # 3. Spatial autocorrelation
    logger.info("\n[4/6] Analyzing spatial autocorrelation...")
    spatial_stats = analyze_spatial_autocorrelation(test_df, residuals_xgb, output_dir)

    # 4. Temporal autocorrelation
    logger.info("\n[5/6] Analyzing temporal autocorrelation...")
    temporal_stats = analyze_temporal_autocorrelation(predictions_df, output_dir)

    # 5. Error patterns by segment
    logger.info("\n[6/6] Analyzing error patterns...")
    error_df = analyze_error_patterns(test_df, y_test, y_pred_xgb, residuals_xgb, output_dir)

    # 6. Generate recommendations
    logger.info("\n[7/7] Generating improvement recommendations...")
    generate_improvement_recommendations(
        dist_stats, hetero_stats, spatial_stats, temporal_stats, output_dir
    )

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Residual Analysis Complete!")
    logger.info("=" * 60)
    logger.info(f"Outputs saved to: {output_dir}")
    logger.info("\nGenerated files:")
    logger.info("  - residual_distribution.png (histogram + Q-Q plot)")
    logger.info("  - heteroscedasticity_check.png (residuals vs fitted/actual)")
    logger.info("  - spatial_residual_map.png (geographic distribution)")
    logger.info("  - temporal_autocorrelation.png (ACF plot)")
    logger.info("  - error_by_property_type.png (error by segment)")
    logger.info("  - error_by_planning_area.csv (area-level errors)")
    logger.info("  - improvement_recommendations.txt (action items)")


if __name__ == "__main__":
    main()
