"""Generate confidence intervals for ensemble predictions.

Uses bootstrapping and quantile-based methods to generate prediction intervals
at multiple confidence levels (68%, 95%, 99%).

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/generate_confidence_intervals.py
"""

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Add project root to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config

# Configure logging
logger = logging.getLogger(__name__)


def bootstrap_predictions(predictions: np.ndarray, n_bootstraps: int = 1000, random_state: int = 42):
    """Generate bootstrap samples for confidence intervals.

    Args:
        predictions: Array of predictions
        n_bootstraps: Number of bootstrap iterations
        random_state: Random seed

    Returns:
        Bootstrap samples array (n_bootstraps, n_samples)
    """
    np.random.seed(random_state)
    n_samples = len(predictions)

    bootstrap_samples = []
    for _ in range(n_bootstraps):
        # Resample with replacement
        indices = np.random.choice(n_samples, size=n_samples, replace=True)
        bootstrap_sample = predictions[indices]
        bootstrap_samples.append(bootstrap_sample)

    return np.array(bootstrap_samples)


def calculate_quantile_intervals(residuals: np.ndarray, confidence_levels: list = [0.68, 0.95, 0.99]):
    """Calculate prediction intervals based on residual quantiles.

    Args:
        residuals: Array of residuals (actual - predicted)
        confidence_levels: List of confidence levels

    Returns:
        Dictionary of intervals for each confidence level
    """
    intervals = {}

    for level in confidence_levels:
        alpha = 1 - level
        lower_bound = np.percentile(residuals, alpha / 2 * 100)
        upper_bound = np.percentile(residuals, (1 - alpha / 2) * 100)

        intervals[level] = {
            "lower": lower_bound,
            "upper": upper_bound,
            "width": upper_bound - lower_bound,
        }

    return intervals


def generate_adaptive_intervals(predictions_df: pd.DataFrame, n_bins: int = 10):
    """Generate prediction intervals that vary with predicted value.

    Creates intervals that are wider for more uncertain predictions.

    Args:
        predictions_df: DataFrame with actual, predicted, residual columns
        n_bins: Number of bins to group predictions by value

    Returns:
        DataFrame with adaptive intervals
    """
    # Create bins based on predicted values
    predictions_df = predictions_df.copy()
    predictions_df["pred_bin"] = pd.cut(
        predictions_df["predicted"],
        bins=n_bins,
        labels=False,
        duplicates="drop"
    )

    # Calculate intervals for each bin
    bin_stats = []

    for bin_id in predictions_df["pred_bin"].unique():
        if pd.isna(bin_id):
            continue

        bin_data = predictions_df[predictions_df["pred_bin"] == bin_id]
        bin_residuals = bin_data["residual"].values
        bin_pred_mean = bin_data["predicted"].mean()

        # Calculate intervals
        intervals = calculate_quantile_intervals(bin_residuals)

        bin_stats.append({
            "bin": bin_id,
            "pred_mean": bin_pred_mean,
            "n_samples": len(bin_data),
            "ci_68_lower": intervals[0.68]["lower"],
            "ci_68_upper": intervals[0.68]["upper"],
            "ci_95_lower": intervals[0.95]["lower"],
            "ci_95_upper": intervals[0.95]["upper"],
            "ci_99_lower": intervals[0.99]["lower"],
            "ci_99_upper": intervals[0.99]["upper"],
        })

    return pd.DataFrame(bin_stats)


def plot_coverage(predictions_df: pd.DataFrame, output_dir: Path):
    """Plot actual coverage vs expected confidence levels.

    Args:
        predictions_df: DataFrame with predictions and intervals
        output_dir: Directory to save plots
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Predicted vs Actual with confidence bands
    ax = axes[0, 0]

    # Sample for plotting
    sample_size = min(5000, len(predictions_df))
    sample_df = predictions_df.sample(sample_size, random_state=42)
    sample_df = sample_df.sort_values("predicted")

    ax.scatter(sample_df["predicted"], sample_df["actual"], alpha=0.2, s=1, color="steelblue")

    # Add 95% CI bands
    yerr = 2 * sample_df["abs_residual"].median()  # Approximate 95% CI
    ax.fill_between(
        sample_df["predicted"],
        sample_df["predicted"] - yerr,
        sample_df["predicted"] + yerr,
        alpha=0.2,
        color="red",
        label="95% CI Band"
    )

    # Perfect prediction line
    min_val = min(sample_df["predicted"].min(), sample_df["actual"].min())
    max_val = max(sample_df["predicted"].max(), sample_df["actual"].max())
    ax.plot([min_val, max_val], [min_val, max_val], "k--", linewidth=1, label="Perfect Prediction")

    ax.set_xlabel("Predicted YoY Change (%)")
    ax.set_ylabel("Actual YoY Change (%)")
    ax.set_title("Predicted vs Actual with 95% CI Bands")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Residual distribution with confidence intervals
    ax = axes[0, 1]

    residuals = predictions_df["residual"].values

    ax.hist(residuals, bins=50, density=True, alpha=0.7, edgecolor="black", color="steelblue")

    # Add confidence interval markers
    intervals = calculate_quantile_intervals(residuals, [0.68, 0.95, 0.99])

    ax.axvline(0, color="red", linestyle="--", linewidth=2, label="Zero")

    y_max = ax.get_ylim()[1]

    # 68% CI
    ax.axvline(intervals[0.68]["lower"], color="orange", linestyle="-", linewidth=2, alpha=0.7)
    ax.axvline(intervals[0.68]["upper"], color="orange", linestyle="-", linewidth=2, alpha=0.7)
    ax.text(intervals[0.68]["lower"], y_max * 0.9, "68%", ha="right", color="orange", fontsize=9)
    ax.fill_betweenx([0, y_max], intervals[0.68]["lower"], intervals[0.68]["upper"], alpha=0.1, color="orange")

    # 95% CI
    ax.axvline(intervals[0.95]["lower"], color="green", linestyle="-", linewidth=2, alpha=0.7)
    ax.axvline(intervals[0.95]["upper"], color="green", linestyle="-", linewidth=2, alpha=0.7)
    ax.text(intervals[0.95]["lower"], y_max * 0.85, "95%", ha="right", color="green", fontsize=9)
    ax.fill_betweenx([0, y_max], intervals[0.95]["lower"], intervals[0.95]["upper"], alpha=0.05, color="green")

    # 99% CI
    ax.axvline(intervals[0.99]["lower"], color="purple", linestyle="-", linewidth=2, alpha=0.7)
    ax.axvline(intervals[0.99]["upper"], color="purple", linestyle="-", linewidth=2, alpha=0.7)
    ax.text(intervals[0.99]["lower"], y_max * 0.8, "99%", ha="right", color="purple", fontsize=9)
    ax.fill_betweenx([0, y_max], intervals[0.99]["lower"], intervals[0.99]["upper"], alpha=0.03, color="purple")

    ax.set_xlabel("Residuals (Actual - Predicted)")
    ax.set_ylabel("Density")
    ax.set_title("Residual Distribution with Confidence Intervals")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Prediction interval width vs predicted value
    ax = axes[1, 0]

    bin_intervals = generate_adaptive_intervals(predictions_df, n_bins=10)

    ax.plot(bin_intervals["pred_mean"], bin_intervals["ci_95_upper"] - bin_intervals["ci_95_lower"],
            marker="o", linewidth=2, markersize=8, color="steelblue", label="95% CI Width")

    ax.set_xlabel("Predicted YoY Change (%)")
    ax.set_ylabel("Interval Width (%)")
    ax.set_title("Prediction Interval Width vs Predicted Value")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 4. Coverage by segment
    ax = axes[1, 1]

    if "segment" in predictions_df.columns:
        segments = predictions_df["segment"].unique()

        coverage_data = []
        for segment in segments:
            segment_data = predictions_df[predictions_df["segment"] == segment]
            segment_residuals = segment_data["residual"].values

            intervals = calculate_quantile_intervals(segment_residuals, [0.95])

            # Calculate actual coverage
            within_ci = ((segment_residuals >= intervals[0.95]["lower"]) &
                        (segment_residuals <= intervals[0.95]["upper"])).sum()
            actual_coverage = within_ci / len(segment_residuals) * 100

            coverage_data.append({
                "segment": segment,
                "expected_coverage": 95,
                "actual_coverage": actual_coverage,
            })

        coverage_df = pd.DataFrame(coverage_data)

        x = np.arange(len(coverage_df))
        width = 0.35

        ax.bar(x - width/2, coverage_df["expected_coverage"], width,
               label="Expected", alpha=0.7, color="steelblue")
        ax.bar(x + width/2, coverage_df["actual_coverage"], width,
               label="Actual", alpha=0.7, color="orange")

        ax.set_xlabel("Segment")
        ax.set_ylabel("Coverage (%)")
        ax.set_title("95% CI Coverage by Segment")
        ax.set_xticks(x)
        ax.set_xticklabels(coverage_df["segment"], rotation=45, ha="right")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(output_dir / "confidence_intervals_analysis.png", dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"  Saved: confidence_intervals_analysis.png")


def main():
    """Generate confidence intervals for ensemble predictions."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Confidence Intervals")
    logger.info("=" * 60)

    # Setup output directory
    output_dir = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "confidence_intervals"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load ensemble predictions
    logger.info("\nLoading ensemble predictions...")
    predictions_path = (
        Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "smart_ensemble" / "ensemble_predictions.parquet"
    )

    predictions_df = pd.read_parquet(predictions_path)
    logger.info(f"  Loaded {len(predictions_df):,} predictions")

    # Add segment information
    segment_path = (
        Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "smart_ensemble" / "segment_performance.csv"
    )
    segment_df = pd.read_csv(segment_path)

    logger.info("\n" + "=" * 60)
    logger.info("OVERALL CONFIDENCE INTERVALS")
    logger.info("=" * 60)

    # Calculate global confidence intervals
    residuals = predictions_df["residual"].values
    intervals = calculate_quantile_intervals(residuals, [0.68, 0.95, 0.99])

    for level, interval in intervals.items():
        logger.info(f"\n  {int(level*100)}% Confidence Interval:")
        logger.info(f"    Lower: {interval['lower']:.2f}%")
        logger.info(f"    Upper: {interval['upper']:.2f}%")
        logger.info(f"    Width: {interval['width']:.2f}%")

    # Calculate coverage
    logger.info("\n  Actual Coverage:")

    for level in [0.68, 0.95, 0.99]:
        interval = intervals[level]
        within_ci = ((residuals >= interval["lower"]) & (residuals <= interval["upper"])).sum()
        actual_coverage = within_ci / len(residuals) * 100

        logger.info(f"    {int(level*100)}% CI: {actual_coverage:.1f}% (expected {int(level*100)}%)")

    # Calculate intervals by segment
    logger.info("\n" + "=" * 60)
    logger.info("CONFIDENCE INTERVALS BY SEGMENT")
    logger.info("=" * 60)

    # Load segment performance data
    test_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_test.parquet"
    test_df = pd.read_parquet(test_path)

    # Merge predictions with test data to get segment info
    predictions_with_segments = predictions_df.copy()
    predictions_with_segments["is_hdb"] = test_df["is_hdb"].values[:len(predictions_df)]
    predictions_with_segments["is_condo"] = test_df["is_condo"].values[:len(predictions_df)]
    predictions_with_segments["is_ec"] = test_df["is_ec"].values[:len(predictions_df)]
    predictions_with_segments["price_psf"] = test_df["price_psf"].values[:len(predictions_df)]

    # Assign segments
    predictions_with_segments["segment"] = "Unknown"
    predictions_with_segments.loc[predictions_with_segments["is_hdb"] == 1, "segment"] = "HDB"
    predictions_with_segments.loc[predictions_with_segments["is_ec"] == 1, "segment"] = "EC"

    condo_mask = predictions_with_segments["is_condo"] == 1
    predictions_with_segments.loc[
        condo_mask & (predictions_with_segments["price_psf"] < 1500), "segment"
    ] = "Mass Market"
    predictions_with_segments.loc[
        condo_mask & (predictions_with_segments["price_psf"] >= 1500) & (predictions_with_segments["price_psf"] <= 3000), "segment"
    ] = "Mid Market"
    predictions_with_segments.loc[
        condo_mask & (predictions_with_segments["price_psf"] > 3000), "segment"
    ] = "Luxury"

    segment_intervals = []

    for segment in ["HDB", "EC", "Mass Market", "Mid Market", "Luxury"]:
        segment_data = predictions_with_segments[predictions_with_segments["segment"] == segment]

        if len(segment_data) == 0:
            continue

        segment_residuals = segment_data["residual"].values
        segment_intervals_calc = calculate_quantile_intervals(segment_residuals, [0.95])

        # Calculate coverage
        within_ci = ((segment_residuals >= segment_intervals_calc[0.95]["lower"]) &
                    (segment_residuals <= segment_intervals_calc[0.95]["upper"])).sum()
        actual_coverage = within_ci / len(segment_residuals) * 100

        logger.info(f"\n  {segment}:")
        logger.info(f"    95% CI: [{segment_intervals_calc[0.95]['lower']:.2f}%, {segment_intervals_calc[0.95]['upper']:.2f}%]")
        logger.info(f"    Width: {segment_intervals_calc[0.95]['width']:.2f}%")
        logger.info(f"    Coverage: {actual_coverage:.1f}% (n={len(segment_data):,})")

        segment_intervals.append({
            "segment": segment,
            "n_samples": len(segment_data),
            "ci_95_lower": segment_intervals_calc[0.95]["lower"],
            "ci_95_upper": segment_intervals_calc[0.95]["upper"],
            "ci_95_width": segment_intervals_calc[0.95]["width"],
            "actual_coverage": actual_coverage,
        })

    # Save segment intervals
    segment_intervals_df = pd.DataFrame(segment_intervals)
    intervals_path = output_dir / "segment_intervals.csv"
    segment_intervals_df.to_csv(intervals_path, index=False)
    logger.info(f"\n  Saved segment intervals to {intervals_path}")

    # Generate predictions with intervals
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING PREDICTIONS WITH INTERVALS")
    logger.info("=" * 60)

    # Add interval columns to predictions
    predictions_with_intervals = predictions_df.copy()
    predictions_with_intervals["ci_68_lower"] = predictions_df["predicted"] + intervals[0.68]["lower"]
    predictions_with_intervals["ci_68_upper"] = predictions_df["predicted"] + intervals[0.68]["upper"]
    predictions_with_intervals["ci_95_lower"] = predictions_df["predicted"] + intervals[0.95]["lower"]
    predictions_with_intervals["ci_95_upper"] = predictions_df["predicted"] + intervals[0.95]["upper"]
    predictions_with_intervals["ci_99_lower"] = predictions_df["predicted"] + intervals[0.99]["lower"]
    predictions_with_intervals["ci_99_upper"] = predictions_df["predicted"] + intervals[0.99]["upper"]

    # Save predictions with intervals
    predictions_with_intervals_path = output_dir / "predictions_with_intervals.parquet"
    predictions_with_intervals.to_parquet(predictions_with_intervals_path, index=False)
    logger.info(f"  Saved predictions with intervals to {predictions_with_intervals_path}")

    # Generate plots
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING VISUALIZATIONS")
    logger.info("=" * 60)

    predictions_with_segments["ci_95_lower"] = (
        predictions_with_segments["predicted"] + intervals[0.95]["lower"]
    )
    predictions_with_segments["ci_95_upper"] = (
        predictions_with_segments["predicted"] + intervals[0.95]["upper"]
    )

    plot_coverage(predictions_with_segments, output_dir)

    logger.info("\n" + "=" * 60)
    logger.info("Confidence Intervals Generated!")
    logger.info("=" * 60)
    logger.info(f"\nOutputs saved to: {output_dir}")

    logger.info("\n" + "=" * 60)
    logger.info("INTERPRETATION")
    logger.info("=" * 60)
    logger.info("\nConfidence intervals provide a range of likely values for predictions:")
    logger.info("  • 68% CI: Roughly ±1 standard deviation (68% of predictions fall within)")
    logger.info("  • 95% CI: Widely used standard (95% of predictions fall within)")
    logger.info("  • 99% CI: More conservative (99% of predictions fall within)")
    logger.info("\nUsage:")
    logger.info("  • Narrow intervals = More certainty")
    logger.info("  • Wide intervals = Less certainty")
    logger.info("  • Use intervals to quantify prediction risk")


if __name__ == "__main__":
    main()
