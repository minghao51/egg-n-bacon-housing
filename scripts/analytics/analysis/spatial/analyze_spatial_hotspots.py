#!/usr/bin/env python3
"""
Analyze Spatial Hotspots using Getis-Ord Gi* statistic.

Identifies statistically significant high/low rental price clusters (hotspots/coldspots)
by H3 hex grid.

Usage:
    uv run python scripts/analysis/analyze_spatial_hotspots.py --help
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add project root to Python path
from scripts.core.utils import add_project_to_path

add_project_to_path(Path(__file__))

from scripts.core.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    import h3
    from shapely.geometry import Polygon
    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False
    logger.warning("h3 or geopandas not available - H3 grid operations disabled")

try:
    from esda.getisord import G_Local
    from libpysal.weights import KNN, Queen
    SPATIAL_AVAILABLE = True
except ImportError:
    SPATIAL_AVAILABLE = False
    logger.warning("libpysal or esda not available - spatial statistics disabled")


def load_rental_data() -> pd.DataFrame:
    """Load HDB rental data with geocoding.

    Joins L1 rental data (monthly_rent) with L2 geocoded property data (lat/lon).
    """
    logger.info("Loading HDB rental data with geocoding...")

    # Load L1 rental data
    rental_path = Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet"
    if not rental_path.exists():
        logger.error(f"Rental data not found: {rental_path}")
        return pd.DataFrame()

    rental_df = pd.read_parquet(rental_path)
    logger.info(f"Loaded {len(rental_df):,} rental records from L1")

    # Load L2 geocoded property data
    geo_path = Config.PARQUETS_DIR / "L2" / "housing_unique_searched.parquet"
    if not geo_path.exists():
        logger.error(f"Geocoded data not found: {geo_path}")
        return pd.DataFrame()

    geo_df = pd.read_parquet(geo_path)
    # Filter only successfully geocoded properties
    geo_df = geo_df[geo_df['search_result'] == 0].copy()
    geo_df = geo_df.rename(columns={'LATITUDE': 'lat', 'LONGITUDE': 'lon'})
    logger.info(f"Loaded {len(geo_df):,} geocoded properties from L2")

    # Create join key from rental data
    rental_df['join_key'] = rental_df['block'].astype(str) + '_' + rental_df['street_name'].str.upper()

    # Create join key from geo data (BLK_NO + ROAD_NAME)
    geo_df['join_key'] = geo_df['BLK_NO'].astype(str) + '_' + geo_df['ROAD_NAME'].str.upper()

    # Join rental data with geocoded data
    df = rental_df.merge(geo_df[['join_key', 'lat', 'lon']], on='join_key', how='inner')
    df['rent_approval_date'] = pd.to_datetime(df['rent_approval_date'], errors='coerce')

    logger.info(f"Joined to {len(df):,} geocoded rental records")
    logger.info(f"Geocoding coverage: {len(df) / len(rental_df) * 100:.1f}%")

    return df


def aggregate_to_h3(df: pd.DataFrame, resolution: int = 8) -> pd.DataFrame:
    """Aggregate rental data to H3 hex cells."""
    logger.info(f"Aggregating to H3 resolution {resolution}...")

    df = df.dropna(subset=['lat', 'lon', 'monthly_rent'])

    df['h3_index'] = df.apply(
        lambda row: h3.latlng_to_cell(row['lat'], row['lon'], resolution), axis=1
    )

    aggregated = df.groupby('h3_index').agg({
        'monthly_rent': ['median', 'mean', 'count'],
        'lat': 'mean',
        'lon': 'mean'
    }).reset_index()

    aggregated.columns = ['h3_index', 'median_rent', 'mean_rent', 'count', 'lat', 'lon']
    logger.info(f"Aggregated to {len(aggregated)} H3 cells")
    return aggregated


def compute_gistar(aggregated_df: pd.DataFrame, k_neighbors: int = 8) -> pd.DataFrame:
    """Compute Getis-Ord Gi* statistic for each H3 cell."""
    logger.info("Computing Getis-Ord Gi* statistic...")

    df = aggregated_df.copy()

    coords = df[['lat', 'lon']].values

    from libpysal.weights import KNN
    weights = KNN.from_array(coords, k=k_neighbors)
    weights.transform = 'r'

    y = df['median_rent'].values
    gstar = G_Local(y, weights, star=True, permutations=99)

    df['gi_star'] = gstar.Z
    df['gi_pvalue'] = gstar.p_sim

    def classify_gi(z, p):
        if p > 0.05:
            return 'not_significant'
        elif z > 2.58:
            return 'hotspot'
        elif z > 1.96:
            return 'weak_hotspot'
        elif z < -2.58:
            return 'coldspot'
        elif z < -1.96:
            return 'weak_coldspot'
        else:
            return 'not_significant'

    df['classification'] = df.apply(lambda row: classify_gi(row['gi_star'], row['gi_pvalue']), axis=1)

    return df


def create_geojson(df: pd.DataFrame, resolution: int) -> dict:
    """Create GeoJSON from H3 cells with Gi* results."""
    logger.info("Creating GeoJSON output...")

    features = []
    for _, row in df.iterrows():
        cell_boundary = h3.cell_to_boundary(row['h3_index'])

        coords = [[cell_boundary[i][1], cell_boundary[i][0]] for i in range(len(cell_boundary))]
        coords.append(coords[0])

        feature = {
            "type": "Feature",
            "properties": {
                "h3_index": row['h3_index'],
                "gi_star": round(row['gi_star'], 4),
                "p_value": round(row['gi_pvalue'], 4),
                "classification": row['classification'],
                "median_rent": round(row['median_rent'], 2),
                "cell_count": int(row['count'])
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def summarize_results(df: pd.DataFrame) -> list:
    """Generate key findings summary."""
    findings = []

    hotspots = df[df['classification'] == 'hotspot']
    coldspots = df[df['classification'] == 'coldspot']

    findings.append(f"Total H3 cells analyzed: {len(df):,}")
    findings.append(f"Hotspots (99% confidence): {len(hotspots)}")
    findings.append(f"Coldspots (99% confidence): {len(coldspots)}")

    if len(hotspots) > 0:
        top_hotspot = hotspots.nlargest(1, 'gi_star').iloc[0]
        findings.append(f"Top hotspot: {top_hotspot['h3_index']} (Gi*={top_hotspot['gi_star']:.2f})")

    if len(coldspots) > 0:
        top_coldspot = coldspots.nsmallest(1, 'gi_star').iloc[0]
        findings.append(f"Top coldspot: {top_coldspot['h3_index']} (Gi*={top_coldspot['gi_star']:.2f})")

    return findings


def main():
    start_time = datetime.now()

    logger.info("="*60)
    logger.info("SPATIAL HOTSPOT ANALYSIS (Getis-Ord Gi*)")
    logger.info("="*60)

    if not H3_AVAILABLE or not SPATIAL_AVAILABLE:
        logger.error("Required packages not available: h3, geopandas, libpysal, esda")
        return

    resolution = 8
    k_neighbors = 8

    df = load_rental_data()
    if df.empty:
        logger.error("No data available")
        return

    aggregated = aggregate_to_h3(df, resolution)

    if len(aggregated) < 10:
        logger.error("Insufficient data for spatial analysis")
        return

    result_df = compute_gistar(aggregated, k_neighbors)

    output_dir = Config.ANALYSIS_OUTPUT_DIR / "analyze_spatial_hotspots"
    output_dir.mkdir(parents=True, exist_ok=True)

    result_df.to_csv(output_dir / "hotspot_stats.csv", index=False)
    logger.info(f"Saved: {output_dir / 'hotspot_stats.csv'}")

    geojson = create_geojson(result_df, resolution)
    with open(output_dir / "hotspots.geojson", 'w') as f:
        json.dump(geojson, f)
    logger.info(f"Saved: {output_dir / 'hotspots.geojson'}")

    findings = summarize_results(result_df)
    for f in findings:
        logger.info(f"  {f}")

    duration = (datetime.now() - start_time).total_seconds()

    print(json.dumps({
        "script": "analyze_spatial_hotspots",
        "status": "success",
        "key_findings": findings,
        "outputs": [
            str(output_dir / "hotspot_stats.csv"),
            str(output_dir / "hotspots.geojson")
        ],
        "duration_seconds": round(duration, 2)
    }))

    logger.info("="*60)
    logger.info("Hotspot analysis complete!")
    logger.info("="*60)


if __name__ == "__main__":
    main()
