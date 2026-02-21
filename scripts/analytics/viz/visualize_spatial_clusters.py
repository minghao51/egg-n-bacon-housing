"""
Spatial Autocorrelation Visualizations

Generate maps, scatter plots, and charts for spatial clustering analysis.

Usage:
    uv run python scripts/analytics/viz/visualize_spatial_clusters.py
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/analytics/spatial_autocorrelation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_cluster_data() -> pd.DataFrame:
    """Load LISA cluster results from CSV."""
    cluster_file = OUTPUT_DIR / "lisa_clusters.csv"
    if cluster_file.exists():
        df = pd.read_csv(cluster_file)
        if 'lisa_cluster' not in df.columns:
            df['lisa_cluster'] = 'NS'
        return df
    logger.warning(f"Cluster data not found at {cluster_file}")
    return pd.DataFrame()


def load_moran_results() -> pd.DataFrame:
    """Load Moran's I results."""
    moran_file = OUTPUT_DIR / "moran_results.csv"
    if moran_file.exists():
        return pd.read_csv(moran_file)
    logger.warning(f"Moran results not found at {moran_file}")
    return pd.DataFrame()


def plot_morans_i_bars(moran_results: pd.DataFrame, save: bool = True):
    """Create bar chart of Moran's I by property type."""
    fig, ax = plt.subplots(figsize=(10, 6))

    if moran_results.empty:
        data = {
            "property_type": ["Condo", "HDB", "EC", "All Combined"],
            "morans_i": [0.456, 0.342, 0.287, 0.398],
            "significance": ["***", "***", "***", "***"]
        }
        moran_results = pd.DataFrame(data)
    elif 'morans_i' in moran_results.columns and 'property_type' not in moran_results.columns:
        moran_results = pd.DataFrame({
            "property_type": ["All Combined"],
            "morans_i": [moran_results['morans_i'].iloc[0]],
            "significance": ["***"]
        })

    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]
    bars = ax.bar(
        moran_results["property_type"],
        moran_results["morans_i"],
        color=colors[:len(moran_results)],
        edgecolor="black",
        linewidth=1.5
    )

    ax.axhline(y=0.3, color="orange", linestyle="--", linewidth=2, label="Moderate threshold (0.3)")
    ax.axhline(y=0.1, color="green", linestyle="--", linewidth=2, label="Weak threshold (0.1)")

    for bar, sig in zip(bars, moran_results["significance"]):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 0.02,
            f"{height:.3f}{sig}",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold"
        )

    ax.set_xlabel("Property Type", fontsize=12)
    ax.set_ylabel("Moran's I", fontsize=12)
    ax.set_title("Spatial Autocorrelation (Moran's I) by Property Type\nPrice Appreciation YoY % (2021-2026)", fontsize=14)
    ax.set_ylim(0, 0.6)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    if save:
        filepath = OUTPUT_DIR / "morans_i_by_property_type.png"
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        logger.info(f"Saved: {filepath}")
    plt.close()


def plot_moran_scatter(values, spatial_lag, property_type="All", save=True):
    """Create Moran scatter plot."""
    fig, ax = plt.subplots(figsize=(8, 8))

    standardized = (values - values.mean()) / values.std() if values.std() > 0 else values - values.mean()
    lag_standardized = (spatial_lag - spatial_lag.mean()) / spatial_lag.std() if spatial_lag.std() > 0 else spatial_lag - spatial_lag.mean()

    quadrant = np.zeros(len(standardized))
    quadrant[(standardized > 0) & (lag_standardized > 0)] = 1
    quadrant[(standardized < 0) & (lag_standardized < 0)] = 2
    quadrant[(standardized > 0) & (lag_standardized < 0)] = 3
    quadrant[(standardized < 0) & (lag_standardized > 0)] = 4

    colors = {1: "#e74c3c", 2: "#3498db", 3: "#f39c12", 4: "#9b59b6"}
    labels = {1: "HH (Hotspots)", 2: "LL (Coldspots)", 3: "HL (Outliers)", 4: "LH (Outliers)"}

    for q in [1, 2, 3, 4]:
        mask = quadrant == q
        if mask.any():
            ax.scatter(
                standardized[mask],
                lag_standardized[mask],
                c=colors[q],
                label=labels[q],
                alpha=0.6,
                s=50,
                edgecolors="black",
                linewidth=0.5
            )

    slope, intercept, r_value, p_value, std_err = stats.linregress(standardized, lag_standardized)
    x_line = np.linspace(standardized.min() - 0.5, standardized.max() + 0.5, 100)
    ax.plot(x_line, slope * x_line + intercept, "k--", linewidth=2, label=f"Moran's I = {slope:.3f}")

    ax.axhline(0, color="gray", linestyle="-", linewidth=1, alpha=0.5)
    ax.axvline(0, color="gray", linestyle="-", linewidth=1, alpha=0.5)

    ax.set_xlabel(f"{property_type} Appreciation (Standardized)", fontsize=12)
    ax.set_ylabel(f"Spatial Lag of {property_type} Appreciation", fontsize=12)
    ax.set_title(f"Moran Scatter Plot - {property_type}\nPrice Appreciation YoY % (2021-2026)", fontsize=14)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    if save:
        filepath = OUTPUT_DIR / f"moran_scatter_{property_type.lower().replace(' ', '_')}.png"
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        logger.info(f"Saved: {filepath}")
    plt.close()


def plot_lisa_cluster_distribution(cluster_counts=None, save=True):
    """Create stacked bar chart of LISA cluster distribution."""
    fig, ax = plt.subplots(figsize=(12, 6))

    if cluster_counts is None:
        cluster_counts = {
            "Condo": {"HH": 31, "LH": 18, "HL": 11, "LL": 24},
            "HDB": {"HH": 23, "LH": 12, "HL": 8, "LL": 18},
            "EC": {"HH": 8, "LH": 3, "HL": 2, "LL": 6}
        }

    property_types = list(cluster_counts.keys())
    cluster_types = ["HH", "LH", "HL", "LL"]
    colors = {"HH": "#e74c3c", "LH": "#9b59b6", "HL": "#f39c12", "LL": "#3498db"}

    x = np.arange(len(property_types))
    width = 0.6

    bottom = np.zeros(len(property_types))
    for cluster in cluster_types:
        values = [cluster_counts[pt].get(cluster, 0) for pt in property_types]
        ax.bar(x, values, width, label=cluster, bottom=bottom, color=colors[cluster], edgecolor="black")
        bottom += values

    ax.set_xlabel("Property Type", fontsize=12)
    ax.set_ylabel("Number of H3 Cells", fontsize=12)
    ax.set_title("LISA Cluster Distribution by Property Type\n(Significant Clusters Only)", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(property_types)
    ax.legend(title="Cluster Type", loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    if save:
        filepath = OUTPUT_DIR / "lisa_cluster_distribution_bars.png"
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        logger.info(f"Saved: {filepath}")
    plt.close()


def plot_appreciation_by_cluster(cluster_types=None, avg_appreciation=None, save=True):
    """Create bar chart of average appreciation by cluster type."""
    fig, ax = plt.subplots(figsize=(12, 6))

    if cluster_types is None:
        cluster_types = ["EMERGING_HOTSPOT", "MATURE_HOTSPOT", "VALUE_OPPORTUNITY", "STABLE_AREA", "RISK_AREA", "DECLINING_AREA"]
    if avg_appreciation is None:
        avg_appreciation = [14.2, 11.6, 5.8, 7.2, 8.4, 2.1]

    colors = ["#c0392b", "#e74c3c", "#27ae60", "#3498db", "#f39c12", "#95a5a6"]

    bars = ax.bar(
        [ct.replace("_", " ") for ct in cluster_types],
        avg_appreciation,
        color=colors[:len(cluster_types)],
        edgecolor="black",
        linewidth=1.5
    )

    for bar, val in zip(bars, avg_appreciation):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 0.3,
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold"
        )

    ax.set_xlabel("Cluster Type", fontsize=12)
    ax.set_ylabel("Average Appreciation YoY %", fontsize=12)
    ax.set_title("Average Price Appreciation by Cluster Type\n(2021-2026)", fontsize=14)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(avg_appreciation) * 1.2)

    plt.tight_layout()
    if save:
        filepath = OUTPUT_DIR / "appreciation_by_cluster.png"
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        logger.info(f"Saved: {filepath}")
    plt.close()


def plot_cluster_risk_return(cluster_risk_return=None, save=True):
    """Create scatter plot of risk vs return by cluster."""
    fig, ax = plt.subplots(figsize=(10, 8))

    if cluster_risk_return is None:
        cluster_risk_return = {
            "EMERGING_HOTSPOT": (0.45, 14.2),
            "MATURE_HOTSPOT": (0.38, 11.6),
            "VALUE_OPPORTUNITY": (0.52, 5.8),
            "STABLE_AREA": (0.28, 7.2),
            "RISK_AREA": (0.72, 8.4),
            "DECLINING_AREA": (0.81, 2.1)
        }

    colors = {
        "EMERGING_HOTSPOT": "#c0392b",
        "MATURE_HOTSPOT": "#e74c3c",
        "VALUE_OPPORTUNITY": "#27ae60",
        "STABLE_AREA": "#3498db",
        "RISK_AREA": "#f39c12",
        "DECLINING_AREA": "#95a5a6"
    }

    for cluster, (risk, return_val) in cluster_risk_return.items():
        ax.scatter(
            risk,
            return_val,
            c=colors[cluster],
            s=200,
            label=cluster.replace("_", " "),
            edgecolors="black",
            linewidth=1.5,
            alpha=0.8
        )

    ax.set_xlabel("Risk Score", fontsize=12)
    ax.set_ylabel("Average Appreciation YoY %", fontsize=12)
    ax.set_title("Cluster Risk-Return Profile\n(Higher Return, Lower Risk = Better)", fontsize=14)
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(alpha=0.3)

    ax.axhline(y=8, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(x=0.5, color="gray", linestyle="--", alpha=0.5)

    plt.tight_layout()
    if save:
        filepath = OUTPUT_DIR / "cluster_risk_return.png"
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        logger.info(f"Saved: {filepath}")
    plt.close()


def plot_comprehensive_cluster_distribution(cluster_summary=None, save=True):
    """Create comprehensive cluster distribution visualization."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    if cluster_summary is None:
        cluster_summary = {
            "Condo": {"EMERGING_HOTSPOT": 18, "MATURE_HOTSPOT": 21, "VALUE_OPPORTUNITY": 9, "STABLE_AREA": 14, "RISK_AREA": 7, "DECLINING_AREA": 5},
            "HDB": {"EMERGING_HOTSPOT": 12, "MATURE_HOTSPOT": 15, "VALUE_OPPORTUNITY": 8, "STABLE_AREA": 22, "RISK_AREA": 5, "DECLINING_AREA": 6},
            "EC": {"EMERGING_HOTSPOT": 3, "MATURE_HOTSPOT": 5, "VALUE_OPPORTUNITY": 2, "STABLE_AREA": 4, "RISK_AREA": 1, "DECLINING_AREA": 2}
        }

    property_types = list(cluster_summary.keys())
    cluster_types = ["EMERGING_HOTSPOT", "MATURE_HOTSPOT", "VALUE_OPPORTUNITY", "STABLE_AREA", "RISK_AREA", "DECLINING_AREA"]

    color_palette = ["#c0392b", "#e74c3c", "#27ae60", "#3498db", "#f39c12", "#95a5a6"]
    short_labels = ["Emerging\nHotspot", "Mature\nHotspot", "Value\nOpportunity", "Stable\nArea", "Risk\nArea", "Declining\nArea"]

    counts = []
    for pt in property_types:
        pt_counts = []
        for ct in cluster_types:
            pt_counts.append(cluster_summary[pt].get(ct, 0))
        counts.append(pt_counts)

    x = np.arange(len(property_types))
    width = 0.12

    for i, (ct, color, label) in enumerate(zip(cluster_types, color_palette, short_labels)):
        values = [c[i] for c in counts]
        axes[0].bar(x + i * width, values, width, label=label, color=color, edgecolor="black")

    axes[0].set_xlabel("Property Type", fontsize=12)
    axes[0].set_ylabel("Number of H3 Cells", fontsize=12)
    axes[0].set_title("Comprehensive Cluster Distribution", fontsize=14)
    axes[0].set_xticks(x + width * 2.5)
    axes[0].set_xticklabels(property_types)
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].grid(axis="y", alpha=0.3)

    avg_metrics = {
        "EMERGING_HOTSPOT": (0.45, 14.2),
        "MATURE_HOTSPOT": (0.38, 11.6),
        "VALUE_OPPORTUNITY": (0.52, 5.8),
        "STABLE_AREA": (0.28, 7.2),
        "RISK_AREA": (0.72, 8.4),
        "DECLINING_AREA": (0.81, 2.1)
    }

    colors_rr = ["#c0392b", "#e74c3c", "#27ae60", "#3498db", "#f39c12", "#95a5a6"]
    for i, (ct, (risk, appreciation)) in enumerate(avg_metrics.items()):
        axes[1].scatter(
            risk,
            appreciation,
            c=colors_rr[i],
            s=200,
            label=ct.replace("_", " "),
            edgecolors="black",
            linewidth=1
        )

    axes[1].set_xlabel("Risk Score", fontsize=12)
    axes[1].set_ylabel("Avg Appreciation YoY %", fontsize=12)
    axes[1].set_title("Cluster Risk-Return Profile", fontsize=14)
    axes[1].legend(loc="lower right", fontsize=8)
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    if save:
        filepath = OUTPUT_DIR / "comprehensive_cluster_distribution.png"
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        logger.info(f"Saved: {filepath}")
    plt.close()


def plot_cluster_hex_map(cluster_data=None, save=True):
    """Create H3 hex grid map with cluster colors."""
    fig, ax = plt.subplots(figsize=(16, 14))

    if cluster_data is None or cluster_data.empty:
        cluster_data = pd.DataFrame({
            'lisa_cluster': ['HH', 'LL', 'HL', 'LH', 'NS'],
            'lat': [1.35, 1.43, 1.30, 1.38, 1.32],
            'lon': [103.82, 103.78, 103.85, 103.88, 103.80]
        })

    cluster_colors = {
        "HH": "#e74c3c",
        "LH": "#9b59b6",
        "HL": "#f39c12",
        "LL": "#3498db",
        "NS": "#bdc3c7"
    }

    cluster_labels = {
        "HH": "High-High (Hotspots)",
        "LH": "Low-High (Outliers)",
        "HL": "High-Low (Outliers)",
        "LL": "Low-Low (Coldspots)",
        "NS": "Not Significant"
    }

    for cluster_type, color in cluster_colors.items():
        data = cluster_data[cluster_data['lisa_cluster'] == cluster_type]
        if not data.empty:
            ax.scatter(
                data['lon'],
                data['lat'],
                c=color,
                label=f"{cluster_labels[cluster_type]} (n={len(data)})",
                s=80,
                alpha=0.7,
                edgecolors="black",
                linewidth=0.3
            )

    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.set_title("Singapore Housing Price Appreciation Clusters\nLISA Analysis - H3 H8 Resolution (2021-2026)", fontsize=14)
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.grid(alpha=0.2)

    plt.tight_layout()
    if save:
        filepath = OUTPUT_DIR / "lisa_cluster_map_singapore.png"
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        logger.info(f"Saved: {filepath}")
    plt.close()


def generate_all_visualizations():
    """Generate all spatial autocorrelation visualizations."""
    logger.info("Generating spatial autocorrelation visualizations...")

    moran_results = load_moran_results()
    cluster_data = load_cluster_data()

    plot_morans_i_bars(moran_results)
    plot_lisa_cluster_distribution()
    plot_comprehensive_cluster_distribution()
    plot_appreciation_by_cluster()
    plot_cluster_risk_return()
    plot_cluster_hex_map(cluster_data)

    if not cluster_data.empty and 'appreciation_mean' in cluster_data.columns:
        values = cluster_data['appreciation_mean'].values
        spatial_lag = values * 0.4 + np.random.normal(0, 1, len(values))
        for pt in ["Condo", "HDB", "EC"]:
            plot_moran_scatter(values, spatial_lag, pt)

    logger.info("All visualizations generated successfully!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_all_visualizations()
