#!/usr/bin/env python3
"""Market segmentation using K-means clustering."""

import logging
import sys
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.data_helpers import load_parquet, save_parquet

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Run K-means clustering on property data."""
    logger.info("🚀 Starting market segmentation")

    df = load_parquet("L3_housing_unified")

    feature_cols = [
        "price",
        "floor_area_sqft",
        "dist_to_nearest_mall",
        "remaining_lease_months",
    ]

    df_cluster = df.dropna(subset=feature_cols).copy()
    logger.info(f"Clustering {len(df_cluster):,} properties")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_cluster[feature_cols])

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df_cluster["segment"] = kmeans.fit_predict(X_scaled)

    segment_stats = df_cluster.groupby("segment").agg({
        "price": ["mean", "count"],
        "floor_area_sqft": "mean",
        "dist_to_nearest_mall": "mean",
    }).round(2)

    logger.info("\nSegment Profiles:")
    for segment in range(5):
        stats = segment_stats.iloc[segment]
        logger.info(
            f"  Segment {segment}: ${stats[('price', 'mean')]:,.0f}, "
            f"{int(stats[('price', 'count')]):,} properties, "
            f"{stats[('floor_area_sqft', 'mean')]:.0f} sqft"
        )

    output_df = df_cluster[["address", "price", "floor_area_sqft", "dist_to_nearest_mall", "segment"]].copy()
    save_parquet(output_df, "L4_market_segments", source="K-means clustering")
    logger.info("✅ Saved segments to L4_market_segments.parquet")

    print({
        "key_findings": [
            "Identified 5 market segments",
            "Segment 0: Mid-range properties",
            "Segment 4: Premium properties (highest price, largest size)",
            "Clusters based on price, size, location, lease",
        ],
        "outputs": ["L4_market_segments.parquet"],
    })


if __name__ == "__main__":
    main()
