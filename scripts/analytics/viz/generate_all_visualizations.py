"""
Main Visualization Runner for Spatial Autocorrelation Analysis

Generate all visualizations for spatial clustering analysis.

Usage:
    uv run python scripts/analytics/viz/generate_all_visualizations.py

Options:
    --spatial     Generate spatial cluster visualizations (maps, Moran scatter)
    --evolution   Generate cluster evolution visualizations (timelines, Sankey)
    --profiles    Generate cluster profile visualizations (feature importance, radar)
    --all         Generate all visualizations (default)
    --dashboard   Generate summary dashboard only
"""

import argparse
import logging
import sys

from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from visualize_spatial_clusters import (
        generate_all_visualizations as gen_spatial,
        plot_morans_i_bars,
        plot_moran_scatter,
        plot_lisa_cluster_distribution,
        plot_appreciation_hotspots_map,
        plot_cluster_hex_map,
        plot_comprehensive_cluster_distribution,
        plot_appreciation_by_cluster,
        plot_cluster_risk_return,
        OUTPUT_DIR as SPATIAL_DIR
    )
except ImportError as e:
    logger.warning(f"Could not import spatial visualizations: {e}")
    gen_spatial = None

try:
    from visualize_cluster_evolution import (
        generate_all_evolution_visualizations as gen_evolution,
        plot_transition_heatmap,
        plot_evolution_timeline,
        plot_cluster_counts_stacked,
        plot_cluster_stability_scores,
        plot_transition_flow_summary,
        OUTPUT_DIR as EVOLUTION_DIR
    )
except ImportError as e:
    logger.warning(f"Could not import evolution visualizations: {e}")
    gen_evolution = None

try:
    from visualize_cluster_profiles import (
        generate_all_profile_visualizations as gen_profiles,
        plot_feature_importance,
        plot_combined_importance,
        plot_cluster_radar_chart,
        plot_cluster_comparison_matrix,
        plot_property_type_comparison,
        plot_summary_dashboard,
        OUTPUT_DIR as PROFILES_DIR
    )
except ImportError as e:
    logger.warning(f"Could not import profile visualizations: {e}")
    gen_profiles = None


def ensure_output_dirs():
    """Ensure all output directories exist."""
    for dir_path in [
        Path("data/analysis/spatial_autocorrelation"),
        Path("data/analysis/spatial_autocorrelation/geojson")
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")


def run_spatial_visualizations():
    """Run spatial cluster visualizations."""
    logger.info("=" * 60)
    logger.info("GENERATING SPATIAL CLUSTER VISUALIZATIONS")
    logger.info("=" * 60)
    ensure_output_dirs()
    if gen_spatial:
        gen_spatial()
    else:
        logger.error("Spatial visualization module not available")
        sys.exit(1)


def run_evolution_visualizations():
    """Run cluster evolution visualizations."""
    logger.info("=" * 60)
    logger.info("GENERATING CLUSTER EVOLUTION VISUALIZATIONS")
    logger.info("=" * 60)
    ensure_output_dirs()
    if gen_evolution:
        gen_evolution()
    else:
        logger.error("Evolution visualization module not available")
        sys.exit(1)


def run_profile_visualizations():
    """Run cluster profile visualizations."""
    logger.info("=" * 60)
    logger.info("GENERATING CLUSTER PROFILE VISUALIZATIONS")
    logger.info("=" * 60)
    ensure_output_dirs()
    if gen_profiles:
        gen_profiles()
    else:
        logger.error("Profile visualization module not available")
        sys.exit(1)


def run_dashboard():
    """Generate summary dashboard only."""
    logger.info("=" * 60)
    logger.info("GENERATING SUMMARY DASHBOARD")
    logger.info("=" * 60)
    ensure_output_dirs()
    try:
        from visualize_cluster_profiles import plot_summary_dashboard
        plot_summary_dashboard(save=True)
        logger.info("Dashboard generated successfully!")
    except ImportError:
        logger.error("Dashboard module not available")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate spatial autocorrelation visualizations"
    )
    parser.add_argument(
        "--spatial",
        action="store_true",
        help="Generate spatial cluster visualizations"
    )
    parser.add_argument(
        "--evolution",
        action="store_true",
        help="Generate cluster evolution visualizations"
    )
    parser.add_argument(
        "--profiles",
        action="store_true",
        help="Generate cluster profile visualizations"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all visualizations (default)"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Generate summary dashboard only"
    )

    args = parser.parse_args()

    if not any([args.spatial, args.evolution, args.profiles, args.dashboard, args.all]):
        args.all = True

    logger.info("Starting visualization generation...")
    logger.info(f"Working directory: {Path.cwd()}")

    ensure_output_dirs()

    if args.all:
        if gen_spatial:
            run_spatial_visualizations()
        if gen_evolution:
            run_evolution_visualizations()
        if gen_profiles:
            run_profile_visualizations()
        run_dashboard()
    elif args.spatial:
        run_spatial_visualizations()
    elif args.evolution:
        run_evolution_visualizations()
    elif args.profiles:
        run_profile_visualizations()
    elif args.dashboard:
        run_dashboard()

    logger.info("=" * 60)
    logger.info("VISUALIZATION GENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Output directory: {Path('data/analysis/spatial_autocorrelation')}")
    logger.info("Generated files:")
    for f in Path("data/analysis/spatial_autocorrelation").glob("*.png"):
        logger.info(f"  - {f.name}")


if __name__ == "__main__":
    main()
