"""
VAR Forecast Visualizations

Generate visualizations for VAR-based housing price forecasts:
1. Planning Area Forecast Comparison (horizontal bar chart)
2. Current Price vs Forecast (scatter plot with quadrants)

Usage:
    uv run python scripts/analytics/viz/visualize_var_forecasts.py
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/analysis/price_forecasts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Region to planning area mapping
REGION_TO_AREAS = {
    "CCR": [
        "DOWNTOWN CORE", "TANGLIN", "NEWTON", "ORCHARD", "RIVER VALLEY",
        "MARINA SOUTH", "OUTRAM", "BUKIT TIMAH", "NOVENA", "MUSEUM", "SINGAPORE RIVER"
    ],
    "RCR": [
        "BISHAN", "BUKIT MERAH", "GEYLANG", "KALLANG", "MARINE PARADE",
        "QUEENSTOWN", "TOA PAYOH", "ROCHOR"
    ],
    "OCR Central": [
        "BISHAN", "TOA PAYOH", "SERANGOON", "KALLANG"
    ],
    "OCR East": [
        "BEDOK", "CHANGI", "PASIR RIS", "PUNGGOL", "TAMPINES"
    ],
    "OCR North-East": [
        "ANG MO KIO", "HOUGANG", "SENGKANG", "SERANGOON"
    ],
    "OCR North": [
        "WOODLANDS", "SEMBAWANG", "YISHUN", "MANDAI", "LIM CHU KANG"
    ],
    "OCR West": [
        "BUKIT BATOK", "BUKIT PANJANG", "CHOA CHU KANG", "CLEMENTI", "JURONG EAST",
        "JURONG WEST", "TENGAH"
    ]
}

# Region colors for plotting
REGION_COLORS = {
    "CCR": "#e74c3c",
    "RCR": "#3498db",
    "OCR Central": "#e67e22",
    "OCR East": "#2ecc71",
    "OCR North-East": "#9b59b6",
    "OCR North": "#f39c12",
    "OCR West": "#1abc9c"
}


def load_regional_forecasts() -> pd.DataFrame:
    """Load regional forecast data."""
    # Try to use the report CSV with adjusted values first
    forecast_file = Path("forecasts_for_report.csv")
    if forecast_file.exists():
        df = pd.read_csv(forecast_file)
        # Clean up column names
        df.columns = df.columns.str.strip().str.lower()

        # Parse percentage values (remove % and ±)
        for col in ["baseline", "bearish", "bullish"]:
            df[col] = df[col].astype(str).str.rstrip("%").astype(float)

        df["confidence"] = df["confidence"].astype(str).str.replace("±", "").str.rstrip("%").astype(float)

        # Map region names to match format
        df["region"] = df["region"].str.replace("OCR CENTRAL", "OCR Central")
        df["region"] = df["region"].str.replace("OCR EAST", "OCR East")
        df["region"] = df["region"].str.replace("OCR NORTH-EAST", "OCR North-East")
        df["region"] = df["region"].str.replace("OCR NORTH", "OCR North")
        df["region"] = df["region"].str.replace("OCR WEST", "OCR West")

        logger.info(f"Loaded {len(df)} regional forecasts from report CSV")
        return df

    # Fallback to original CSV
    forecast_file = Path("regional_forecasts_final.csv")
    if forecast_file.exists():
        df = pd.read_csv(forecast_file)
        df.columns = df.columns.str.strip().str.lower()
        logger.info(f"Loaded {len(df)} regional forecasts from original CSV")
        return df

    # Final fallback: hardcoded values (from report)
    logger.warning("No forecast CSV found, using hardcoded values")
    return pd.DataFrame({
        "region": ["CCR", "OCR Central", "OCR East", "OCR North",
                   "OCR North-East", "OCR West", "RCR"],
        "baseline": [2.5, 5.5, 3.7, 8.3, 9.6, 9.4, 2.6],
        "bearish": [0.0, 3.0, 1.2, 5.8, 7.1, 6.9, 0.1],
        "bullish": [4.5, 7.5, 5.7, 10.3, 11.6, 11.4, 4.6],
        "confidence": [28.2, 16.2, 35.7, 54.4, 67.8, 59.9, 55.5]
    })


def get_current_prices_by_area() -> pd.DataFrame:
    """Get current median PSF by planning area from L3 data."""
    try:
        df = load_parquet("L3_housing_unified")

        # Filter to recent data (2025-2026)
        df = df[pd.to_datetime(df["transaction_date"]).dt.year >= 2025]

        # Group by planning_area and get median price_psf
        area_prices = df.groupby("planning_area").agg({
            "price_psf": "median"
        }).reset_index()

        area_prices.columns = ["planning_area", "median_psf"]
        logger.info(f"Computed median prices for {len(area_prices)} planning areas")
        return area_prices

    except Exception as e:
        logger.error(f"Failed to load current prices: {e}")
        # Return fallback data for top areas
        return pd.DataFrame({
            "planning_area": [
                "Pasir Ris", "Tampines", "Bedok", "Woodlands", "Hougang",
                "Sengkang", "Punggol", "Jurong East", "Bishan", "Bukit Batok",
                "Yishun", "Clementi", "Serangoon", "Ang Mo Kio", "Toa Payoh"
            ],
            "median_psf": [
                1050, 1180, 1020, 980, 1080,
                1120, 1150, 1100, 1350, 950,
                920, 1080, 1200, 980, 1250
            ]
        })


def map_area_forecasts(area_prices: pd.DataFrame, regional_forecasts: pd.DataFrame) -> pd.DataFrame:
    """Map regional forecasts to planning areas."""
    # Create reverse mapping from planning area to region
    area_to_region = {}
    for region, areas in REGION_TO_AREAS.items():
        for area in areas:
            area_to_region[area] = region

    # Add region to area_prices
    area_prices["region_clean"] = area_prices["planning_area"].map(area_to_region)

    # Drop areas without region mapping
    area_prices = area_prices.dropna(subset=["region_clean"])

    # Clean region names in regional_forecasts
    regional_forecasts["region_clean"] = regional_forecasts["region"].str.strip()

    # Merge forecasts with area prices
    merged = area_prices.merge(
        regional_forecasts[["region_clean", "baseline", "bearish", "bullish", "confidence"]],
        on="region_clean",
        how="left"
    )

    # Sort by baseline forecast (descending) and take top 15
    merged = merged.dropna(subset=["baseline"])
    merged = merged.sort_values("baseline", ascending=True).tail(15)

    return merged


def plot_planning_area_forecasts(forecast_data: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Create horizontal bar chart of planning area forecasts."""
    fig, ax = plt.subplots(figsize=(12, 9))

    # Sort by baseline forecast (descending for horizontal chart)
    plot_data = forecast_data.sort_values("baseline", ascending=True)

    # Create color array based on region
    colors = plot_data["region_clean"].map(REGION_COLORS)

    # Create horizontal bar chart
    bars = ax.barh(
        y=plot_data["planning_area"],
        width=plot_data["baseline"],
        color=colors,
        edgecolor="black",
        linewidth=1.5
    )

    # Add error bars for confidence intervals
    ax.errorbar(
        x=plot_data["baseline"],
        y=range(len(plot_data)),
        xerr=plot_data["confidence"],
        fmt="none",
        ecolor="black",
        elinewidth=1.5,
        capsize=4,
        alpha=0.7
    )

    # Customize chart
    ax.set_xlabel("24-Month Forecast Appreciation (%)", fontsize=12, fontweight="bold")
    ax.set_title("Planning Area Housing Price Forecasts (24-Month)\nTop 15 Areas by Expected Growth",
                 fontsize=14, fontweight="bold", pad=20)
    ax.set_ylabel("Planning Area", fontsize=12, fontweight="bold")

    # Add grid
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Add value labels on bars
    for i, (bar, value, conf) in enumerate(zip(bars, plot_data["baseline"], plot_data["confidence"])):
        ax.text(value + 0.3, i, f"{value:.1f}%",
                va="center", fontsize=10, fontweight="bold")
        ax.text(value, i - 0.35, f"±{conf:.1f}%",
                va="center", fontsize=8, color="gray", ha="center")

    # Create legend for regions
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color, edgecolor="black", label=region)
                      for region, color in REGION_COLORS.items()
                      if region in plot_data["region_clean"].values]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=10, title="Region")

    # Set xlim with padding
    max_val = plot_data["baseline"].max()
    ax.set_xlim(0, max_val + 5)

    plt.tight_layout()

    if save:
        output_path = OUTPUT_DIR / "planning_area_forecasts.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved planning area forecasts to {output_path}")

    return fig


def plot_price_vs_forecast(forecast_data: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Create scatter plot of current price vs forecast with quadrants."""
    fig, ax = plt.subplots(figsize=(12, 10))

    # Calculate medians for quadrant lines
    price_median = forecast_data["median_psf"].median()
    forecast_median = forecast_data["baseline"].median()

    # Create quadrant background colors
    ax.axvline(price_median, color="gray", linestyle="--", linewidth=2, alpha=0.5)
    ax.axhline(forecast_median, color="gray", linestyle="--", linewidth=2, alpha=0.5)

    # Color points by forecast value
    scatter = ax.scatter(
        forecast_data["median_psf"],
        forecast_data["baseline"],
        c=forecast_data["baseline"],
        cmap="RdYlGn",
        s=200,
        alpha=0.7,
        edgecolors="black",
        linewidth=1.5
    )

    # Add labels for each point
    for _, row in forecast_data.iterrows():
        ax.annotate(
            row["planning_area"],
            (row["median_psf"], row["baseline"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            alpha=0.8
        )

    # Customize chart
    ax.set_xlabel("Current Median PSF ($)", fontsize=12, fontweight="bold")
    ax.set_ylabel("24-Month Forecast Appreciation (%)", fontsize=12, fontweight="bold")
    ax.set_title("Current Price vs Forecast Appreciation\nIdentifying Undervalued Opportunities",
                 fontsize=14, fontweight="bold", pad=20)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Forecast (%)", fontsize=11, fontweight="bold")

    # Add quadrant labels
    ax.text(price_median * 0.7, forecast_median * 1.5,
            "🔥 UNDERRATED GEMS\nLow Price, High Growth",
            ha="center", va="center", fontsize=11, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#d5f4e6", alpha=0.7))

    ax.text(price_median * 1.3, forecast_median * 1.5,
            "💎 PREMIUM GROWTH\nHigh Price, High Growth",
            ha="center", va="center", fontsize=11, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffeaa7", alpha=0.7))

    ax.text(price_median * 0.7, forecast_median * 0.5,
            "🏠 AFFORDABLE\nSlow Growth",
            ha="center", va="center", fontsize=11, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#dfe6e9", alpha=0.7))

    ax.text(price_median * 1.3, forecast_median * 0.5,
            "⚠️  MAY BE OVERVALUED\nHigh Price, Low Growth",
            ha="center", va="center", fontsize=11, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffcccc", alpha=0.7))

    # Set axis limits with padding
    ax.set_xlim(forecast_data["median_psf"].min() - 50,
                forecast_data["median_psf"].max() + 50)
    ax.set_ylim(0, forecast_data["baseline"].max() + 2)

    plt.tight_layout()

    if save:
        output_path = OUTPUT_DIR / "price_vs_forecast_scatter.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved price vs forecast scatter to {output_path}")

    return fig


def main():
    """Generate all VAR forecast visualizations."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("Starting VAR forecast visualization generation...")

    # Load data
    regional_forecasts = load_regional_forecasts()
    area_prices = get_current_prices_by_area()

    # Map regional forecasts to planning areas
    forecast_data = map_area_forecasts(area_prices, regional_forecasts)

    logger.info(f"Generated forecast data for {len(forecast_data)} planning areas")

    # Generate visualizations
    logger.info("Generating planning area forecast chart...")
    plot_planning_area_forecasts(forecast_data, save=True)

    logger.info("Generating price vs forecast scatter plot...")
    plot_price_vs_forecast(forecast_data, save=True)

    logger.info(f"All visualizations saved to {OUTPUT_DIR}")

    # Print summary
    print("\n" + "="*60)
    print("VAR FORECAST VISUALIZATIONS GENERATED")
    print("="*60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"  - planning_area_forecasts.png")
    print(f"  - price_vs_forecast_scatter.png")
    print(f"\nAreas analyzed: {len(forecast_data)}")
    print(f"Highest forecast: {forecast_data['baseline'].max():.1f}%")
    print(f"Lowest forecast: {forecast_data['baseline'].min():.1f}%")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
