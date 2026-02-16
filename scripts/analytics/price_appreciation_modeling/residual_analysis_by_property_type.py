"""Residual analysis for property-type-specific price appreciation models.

Analyzes residuals separately for HDB, Condo, and EC models to identify
property-type-specific issues and improvements.

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/residual_analysis_by_property_type.py
"""

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Add project root to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config

# Configure logging
logger = logging.getLogger(__name__)


def analyze_residuals_for_property_type(
    predictions_df: pd.DataFrame, property_type: str, output_dir: Path
):
    """Analyze residuals for a specific property type.

    Args:
        predictions_df: DataFrame with actual, predicted, residual columns
        property_type: Name of property type (HDB, Condo, EC)
        output_dir: Directory to save plots
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Analyzing {property_type} Residuals")
    logger.info(f"{'='*60}")

    # Filter for this property type
    if "property_type" in predictions_df.columns:
        df = predictions_df[predictions_df["property_type"] == property_type].copy()
    else:
        df = predictions_df.copy()

    if len(df) == 0:
        logger.warning(f"  No predictions found for {property_type}")
        return

    residuals = df["actual"] - df["predicted"]
    y_pred = df["predicted"]
    y_actual = df["actual"]

    logger.info(f"  Sample size: {len(df):,}")

    # 1. Distribution analysis
    logger.info("\n  [1/4] Distribution Analysis")

    stats_dict = {
        "mean": residuals.mean(),
        "std": residuals.std(),
        "median": residuals.median(),
        "skewness": stats.skew(residuals),
        "kurtosis": stats.kurtosis(residuals),
    }

    logger.info(f"    Mean: {stats_dict['mean']:.2f}")
    logger.info(f"    Std: {stats_dict['std']:.2f}")
    logger.info(f"    Median: {stats_dict['median']:.2f}")
    logger.info(f"    Skewness: {stats_dict['skewness']:.2f}")
    logger.info(f"    Kurtosis: {stats_dict['kurtosis']:.2f}")

    # Histogram + Q-Q plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].hist(residuals, bins=50, density=True, alpha=0.7, edgecolor="black", color="steelblue")
    axes[0].axvline(0, color="red", linestyle="--", linewidth=2, label="Zero")
    axes[0].set_xlabel("Residuals (Actual - Predicted)")
    axes[0].set_ylabel("Density")
    axes[0].set_title(f"{property_type}: Residual Distribution")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    stats.probplot(residuals, dist="norm", plot=axes[1])
    axes[1].set_title(f"{property_type}: Q-Q Plot (Normality Check)")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / f"{property_type.lower()}_residual_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"    Saved: {property_type.lower()}_residual_distribution.png")

    # 2. Heteroscedasticity check
    logger.info("\n  [2/4] Heteroscedasticity Check")

    abs_residuals = np.abs(residuals)
    corr, p_value = stats.pearsonr(y_pred, abs_residuals)

    logger.info(f"    Correlation (|residuals| vs fitted): {corr:.4f}")
    logger.info(f"    P-value: {p_value:.4f}")
    logger.info(f"    Heteroscedastic: {p_value < 0.05}")

    # Plot residuals vs fitted
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].scatter(y_pred, residuals, alpha=0.1, s=1, color="steelblue")
    axes[0].axhline(0, color="red", linestyle="--", linewidth=2)
    axes[0].set_xlabel("Fitted Values (Predicted YoY %)")
    axes[0].set_ylabel("Residuals")
    axes[0].set_title(f"{property_type}: Residuals vs Fitted")
    axes[0].grid(True, alpha=0.3)

    axes[1].scatter(y_actual, residuals, alpha=0.1, s=1, color="steelblue")
    axes[1].axhline(0, color="red", linestyle="--", linewidth=2)
    axes[1].set_xlabel("Actual Values (YoY %)")
    axes[1].set_ylabel("Residuals")
    axes[1].set_title(f"{property_type}: Residuals vs Actual")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / f"{property_type.lower()}_heteroscedasticity.png", dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"    Saved: {property_type.lower()}_heteroscedasticity.png")

    # 3. Error magnitude analysis
    logger.info("\n  [3/4] Error Magnitude Analysis")

    # Categorize errors
    excellent = (abs_residuals < 5).sum()
    good = ((abs_residuals >= 5) & (abs_residuals < 10)).sum()
    moderate = ((abs_residuals >= 10) & (abs_residuals < 20)).sum()
    large = ((abs_residuals >= 20) & (abs_residuals < 50)).sum()
    extreme = (abs_residuals >= 50).sum()

    logger.info(f"    Excellent (<5%): {excellent:,} ({excellent/len(df)*100:.1f}%)")
    logger.info(f"    Good (5-10%): {good:,} ({good/len(df)*100:.1f}%)")
    logger.info(f"    Moderate (10-20%): {moderate:,} ({moderate/len(df)*100:.1f}%)")
    logger.info(f"    Large (20-50%): {large:,} ({large/len(df)*100:.1f}%)")
    logger.info(f"    Extreme (>50%): {extreme:,} ({extreme/len(df)*100:.1f}%)")

    # 4. Actual vs Predicted plot
    logger.info("\n  [4/4] Actual vs Predicted")

    fig, ax = plt.subplots(figsize=(8, 8))

    # Scatter plot
    ax.scatter(y_actual, y_pred, alpha=0.1, s=1, color="steelblue")

    # Perfect prediction line
    min_val = min(y_actual.min(), y_pred.min())
    max_val = max(y_actual.max(), y_pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2, label="Perfect Prediction")

    ax.set_xlabel("Actual YoY Change (%)")
    ax.set_ylabel("Predicted YoY Change (%)")
    ax.set_title(f"{property_type}: Actual vs Predicted")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add R² annotation
    r2 = stats_dict.get("r2", np.nan)
    if not np.isnan(r2):
        ax.text(0.05, 0.95, f"R² = {r2:.4f}", transform=ax.transAxes, fontsize=12,
                verticalalignment="top", bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_dir / f"{property_type.lower()}_actual_vs_predicted.png", dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"    Saved: {property_type.lower()}_actual_vs_predicted.png")

    return stats_dict


def main():
    """Run residual analysis for all property types."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Residual Analysis by Property Type")
    logger.info("=" * 60)

    # Setup output directory
    output_dir = (
        Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "residual_analysis_by_property_type"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load predictions from property-type models
    predictions_path = (
        Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "models_by_property_type" / "all_predictions.parquet"
    )

    logger.info(f"\nLoading predictions from {predictions_path}")
    predictions_df = pd.read_parquet(predictions_path)
    logger.info(f"  Loaded {len(predictions_df):,} predictions")

    # Load model comparison for R² values
    comparison_path = (
        Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "models_by_property_type" / "model_comparison.csv"
    )
    comparison_df = pd.read_csv(comparison_path)

    # Add R² to predictions
    predictions_with_r2 = predictions_df.merge(
        comparison_df[["property_type", "test_r2"]], on="property_type", how="left"
    )

    # Analyze each property type
    results = {}
    for prop_type in ["HDB", "Condo", "EC"]:
        prop_df = predictions_with_r2[predictions_with_r2["property_type"] == prop_type].copy()
        if len(prop_df) > 0:
            r2_val = comparison_df[comparison_df["property_type"] == prop_type]["test_r2"].values[0]
            prop_df["r2"] = r2_val
            stats_dict = analyze_residuals_for_property_type(prop_df, prop_type, output_dir)
            results[prop_type] = stats_dict

    # Summary comparison
    logger.info("\n" + "=" * 60)
    logger.info("RESIDUAL STATISTICS COMPARISON")
    logger.info("=" * 60)

    summary_data = []
    for prop_type, stats_dict in results.items():
        summary_data.append({
            "Property Type": prop_type,
            "Mean Residual": f"{stats_dict['mean']:.2f}",
            "Std Residual": f"{stats_dict['std']:.2f}",
            "Skewness": f"{stats_dict['skewness']:.2f}",
            "Kurtosis": f"{stats_dict['kurtosis']:.2f}",
        })

    summary_df = pd.DataFrame(summary_data)
    logger.info("\n" + summary_df.to_string(index=False))

    # Save summary
    summary_path = output_dir / "residual_comparison.csv"
    summary_df.to_csv(summary_path, index=False)
    logger.info(f"\n  Saved summary to {summary_path}")

    # Generate recommendations
    logger.info("\n" + "=" * 60)
    logger.info("RECOMMENDATIONS BY PROPERTY TYPE")
    logger.info("=" * 60)

    recommendations = {}

    # HDB recommendations
    if "HDB" in results:
        hdb_stats = results["HDB"]
        hdb_rec = []

        if abs(hdb_stats["skewness"]) > 1:
            hdb_rec.append("• Moderate skewness detected - consider separating resale vs BTO")

        if hdb_stats["kurtosis"] > 10:
            hdb_rec.append("• Heavy tails - investigate outliers (possibly unusual transactions)")

        hdb_rec.extend([
            "• Add town-level features (mature vs non-mature estates)",
            "• Add proximity to specific amenities (premium malls, top schools)",
            "• Separate models for different room types (2-room, 3-room, 4-room, 5-room, multi-gen)",
        ])

        recommendations["HDB"] = hdb_rec

    # Condo recommendations
    if "Condo" in results:
        condo_stats = results["Condo"]
        condo_rec = []

        if abs(condo_stats["skewness"]) > 1:
            condo_rec.append("• High skewness - separate luxury/mass-market models needed")

        if condo_stats["kurtosis"] > 10:
            condo_rec.append("• Extreme outliers - handle luxury properties separately")

        condo_rec.extend([
            "• Add freehold vs leasehold indicator",
            "• Add project quality indicators (developer reputation, facilities)",
            "• Separate models by price segment (mass, mid, luxury)",
            "• Add strata-titled shophouse detection (different dynamics)",
        ])

        recommendations["Condo"] = condo_rec

    # EC recommendations
    if "EC" in results:
        ec_stats = results["EC"]
        ec_rec = []

        if ec_stats["std"] < 10:
            ec_rec.append("• Low variance - excellent predictability")

        ec_rec.extend([
            "• Add proximity to HDB towns (EC buyers often HDB upgraders)",
            "• Add timing features ( privatisation milestones)",
            "• Monitor market segment (HDB upgraders vs private condo downgraders)",
        ])

        recommendations["EC"] = ec_rec

    # Print recommendations
    for prop_type, recs in recommendations.items():
        logger.info(f"\n{prop_type}:")
        for rec in recs:
            logger.info(f"  {rec}")

    # Save recommendations
    with open(output_dir / "recommendations.txt", "w") as f:
        f.write("RESIDUAL ANALYSIS RECOMMENDATIONS BY PROPERTY TYPE\n")
        f.write("=" * 60 + "\n\n")

        for prop_type, recs in recommendations.items():
            f.write(f"{prop_type}:\n")
            for rec in recs:
                f.write(f"  {rec}\n")
            f.write("\n")

    logger.info(f"\n  Saved recommendations to {output_dir / 'recommendations.txt'}")

    logger.info("\n" + "=" * 60)
    logger.info("Residual Analysis Complete!")
    logger.info("=" * 60)
    logger.info(f"\nOutputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
