"""Residual analysis for price appreciation models - Simplified.

Analyzes XGBoost model residuals and generates diagnostic plots.

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/residual_analysis_simple.py
"""  # noqa: N999

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config

# Configure logging
logger = logging.getLogger(__name__)


def main():
    """Run residual analysis."""
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

    # Load predictions
    logger.info("\nLoading predictions...")
    predictions_path = (
        Config.DATA_DIR
        / "analysis"
        / "price_appreciation_modeling"
        / "predictions"
        / "test_predictions.parquet"
    )

    predictions_df = pd.read_parquet(predictions_path)
    logger.info(f"  Loaded {len(predictions_df):,} predictions")

    # Extract variables
    y_test = predictions_df["actual"]
    y_pred = predictions_df["XGBoost_predicted"]
    residuals = predictions_df["XGBoost_residual"]

    # 1. Distribution analysis
    logger.info("\n[1/5] Analyzing residual distribution...")

    stats_dict = {
        "mean": residuals.mean(),
        "std": residuals.std(),
        "median": residuals.median(),
        "skewness": stats.skew(residuals),
        "kurtosis": stats.kurtosis(residuals),
    }

    logger.info(f"  Mean: {stats_dict['mean']:.2f}")
    logger.info(f"  Std: {stats_dict['std']:.2f}")
    logger.info(f"  Skewness: {stats_dict['skewness']:.2f}")
    logger.info(f"  Kurtosis: {stats_dict['kurtosis']:.2f}")

    # Histogram
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

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

    logger.info(f"  Saved to {output_dir / 'residual_distribution.png'}")

    # 2. Heteroscedasticity
    logger.info("\n[2/5] Checking for heteroscedasticity...")

    # Correlation between |residuals| and fitted values
    abs_residuals = np.abs(residuals)
    corr, p_value = stats.pearsonr(y_pred, abs_residuals)

    logger.info(f"  Correlation (|residuals| vs fitted): {corr:.4f}")
    logger.info(f"  P-value: {p_value:.4f}")
    logger.info(f"  Heteroscedastic: {p_value < 0.05}")

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].scatter(y_pred, residuals, alpha=0.1, s=1)
    axes[0].axhline(0, color='red', linestyle='--', linewidth=2)
    axes[0].set_xlabel('Fitted Values (Predicted YoY %)')
    axes[0].set_ylabel('Residuals')
    axes[0].set_title('Residuals vs Fitted')
    axes[0].grid(True, alpha=0.3)

    axes[1].scatter(y_test, residuals, alpha=0.1, s=1)
    axes[1].axhline(0, color='red', linestyle='--', linewidth=2)
    axes[1].set_xlabel('Actual Values (YoY %)')
    axes[1].set_ylabel('Residuals')
    axes[1].set_title('Residuals vs Actual')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "heteroscedasticity_check.png", dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved to {output_dir / 'heteroscedasticity_check.png'}")

    # 3. Spatial autocorrelation (simplified)
    logger.info("\n[3/5] Checking spatial patterns...")

    # Load test data for coordinates
    test_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_test.parquet"
    test_df = pd.read_parquet(test_path)

    # Align indices by resetting both to sequential integers
    # The predictions DataFrame has fewer rows due to dropping missing values during training
    test_df_aligned = test_df.reset_index(drop=True)
    residuals_aligned = residuals.reset_index(drop=True)

    # Ensure both have the same length (use minimum to avoid index errors)
    min_len = min(len(test_df_aligned), len(residuals_aligned))
    test_df_aligned = test_df_aligned.iloc[:min_len]
    residuals_aligned = residuals_aligned.iloc[:min_len]

    valid_coords = test_df_aligned[["lat", "lon"]].notna().all(axis=1)

    if valid_coords.sum() > 0:
        # Sample for spatial analysis
        sample_size = min(10000, valid_coords.sum())
        sample_idx = np.random.choice(valid_coords[valid_coords].index, sample_size, replace=False)

        lat_lon = test_df_aligned.loc[sample_idx, ["lat", "lon"]].values
        residuals_spatial = residuals_aligned.loc[sample_idx].values

        # Simple spatial autocorrelation (nearby points)
        from sklearn.neighbors import NearestNeighbors

        k = 10
        nbrs = NearestNeighbors(n_neighbors=k + 1).fit(lat_lon)
        distances, indices = nbrs.kneighbors(lat_lon)

        # Calculate spatial lag of residuals
        spatial_lags = []
        for i in range(len(residuals_spatial)):
            neighbor_residuals = residuals_spatial[indices[i, 1:]]
            spatial_lags.append(residuals_spatial[i] * neighbor_residuals.mean())

        moran_i = np.mean(spatial_lags) / (residuals_spatial.var() + 1e-10)

        logger.info(f"  Moran's I: {moran_i:.4f}")
        logger.info(f"  Interpretation: {'Positive spatial clustering' if moran_i > 0 else 'No pattern'}")

    # 4. Temporal autocorrelation
    logger.info("\n[4/5] Checking temporal patterns...")

    # Sample for temporal analysis
    sample_size = min(50000, len(residuals))
    residuals_sample = residuals.sample(sample_size, random_state=42).reset_index(drop=True)

    max_lag = min(12, len(residuals_sample) - 1)
    acf_values = [1.0]

    for lag in range(1, max_lag + 1):
        lag_corr = np.corrcoef(
            residuals_sample.iloc[:-lag],
            residuals_sample.iloc[lag:]
        )[0, 1]
        acf_values.append(lag_corr)

    logger.info(f"  Lag-1 autocorrelation: {acf_values[1]:.4f}")
    logger.info(f"  Interpretation: {'Positive autocorrelation' if acf_values[1] > 0.1 else 'No significant autocorrelation'}")

    # Plot ACF
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.stem(range(max_lag + 1), acf_values, basefmt=" ")
    ax.axhline(0, color='black', linestyle='-', linewidth=1)
    ax.axhline(0, color='red', linestyle='--', linewidth=2, alpha=0.5)
    ax.set_xlabel('Lag (months)')
    ax.set_ylabel('Autocorrelation')
    ax.set_title('Residual Autocorrelation Function (ACF)')
    ax.grid(True, alpha=0.3)

    n = len(residuals_sample)
    conf_level = 1.96 / np.sqrt(n)
    ax.fill_between(range(max_lag + 1), -conf_level, conf_level, alpha=0.2, color='gray', label='95% CI')

    plt.tight_layout()
    plt.savefig(output_dir / "temporal_autocorrelation.png", dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"  Saved to {output_dir / 'temporal_autocorrelation.png'}")

    # 5. Generate recommendations
    logger.info("\n[5/5] Generating recommendations...")

    recommendations = []

    # Based on diagnostics
    if abs(stats_dict["skewness"]) > 1:
        recommendations.append("• High residual skewness detected. Consider target transformation (log, Box-Cox) or use robust regression models.")

    if stats_dict["kurtosis"] > 10:
        recommendations.append("• Heavy tails in residuals (extreme errors). Consider separate models for luxury properties or outlier removal.")

    if p_value < 0.05:
        recommendations.append("• Heteroscedasticity detected. Variance increases with fitted values. Use weighted regression or robust standard errors.")

    if moran_i > 0.1:
        recommendations.append("• Positive spatial autocorrelation detected. Residuals cluster geographically. Add spatial lag features or regional models.")

    if abs(acf_values[1]) > 0.1:
        recommendations.append("• Temporal autocorrelation detected. Add autoregressive features or use time series models.")

    # General recommendations
    recommendations.extend([
        "",
        "General Improvements:",
        "• Add polynomial features (squared distances, interaction terms)",
        "• Add more temporal lags (2-year, 3-year)",
        "• Separate models by property type (HDB, Condo, EC)",
        "• Ensemble methods (stacking multiple models)",
        "• Cross-validation with spatial folds (leave-one-area-out)",
        "• Add macroeconomic features (interest rates, policy changes)",
    ])

    # Save recommendations
    with open(output_dir / "improvement_recommendations.txt", "w") as f:
        f.write("MODEL IMPROVEMENT RECOMMENDATIONS\n")
        f.write("=" * 60 + "\n\n")

        for rec in recommendations:
            f.write(rec + "\n")

    logger.info(f"\n  Saved to {output_dir / 'improvement_recommendations.txt'}")

    # Print recommendations
    logger.info("\n" + "=" * 60)
    logger.info("IMPROVEMENT RECOMMENDATIONS")
    logger.info("=" * 60)

    for rec in recommendations:
        logger.info(rec)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Residual Analysis Complete!")
    logger.info("=" * 60)

    logger.info(f"Outputs saved to: {output_dir}")
    logger.info("\nGenerated files:")
    logger.info("  - residual_distribution.png (histogram + Q-Q plot)")
    logger.info("  - heteroscedasticity_check.png (residuals vs fitted/actual)")
    logger.info("  - temporal_autocorrelation.png (ACF plot)")
    logger.info("  - improvement_recommendations.txt (action items)")

    logger.info("\nKey Diagnostic Results:")
    logger.info(f"  Residual Mean: {stats_dict['mean']:.2f} (bias)")
    logger.info(f"  Residual Std: {stats_dict['std']:.2f} (typical error)")
    logger.info(f"  Skewness: {stats_dict['skewness']:.2f} (asymmetry)")
    logger.info(f"  Kurtosis: {stats_dict['kurtosis']:.2f} (heavy tails > 10)")
    logger.info(f"  Heteroscedastic: {p_value < 0.05} (variance not constant)")
    logger.info(f"  Moran's I: {moran_i:.4f} (spatial clustering)")
    logger.info(f"  Lag-1 ACF: {acf_values[1]:.4f} (temporal pattern)")


if __name__ == "__main__":
    main()
