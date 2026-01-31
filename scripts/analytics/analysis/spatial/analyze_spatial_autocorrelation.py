#!/usr/bin/env python3
"""
Analyze Spatial Autocorrelation using Moran's I and LISA.

Quantifies spatial clustering strength and identifies local clusters/outliers.

Usage:
    uv run python scripts/analysis/analyze_spatial_autocorrelation.py --help
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import h3
    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False
    logger.warning("h3 not available")

try:
    from libpysal.weights import KNN
    from esda.moran import Moran, Moran_Local
    SPATIAL_AVAILABLE = True
except ImportError:
    SPATIAL_AVAILABLE = False
    logger.warning("libpysal or esda not available")


def load_rental_data() -> pd.DataFrame:
    """Load HDB rental data."""
    logger.info("Loading HDB rental data...")
    path = Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet"
    if not path.exists():
        logger.error(f"Rental data not found: {path}")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df['rent_approval_date'] = pd.to_datetime(df['rent_approval_date'], errors='coerce')
    logger.info(f"Loaded {len(df):,} rental records")
    return df


def aggregate_to_h3(df: pd.DataFrame, resolution: int = 8) -> pd.DataFrame:
    """Aggregate rental data to H3 hex cells."""
    logger.info(f"Aggregating to H3 resolution {resolution}...")
    
    df = df.dropna(subset=['lat', 'lon', 'monthly_rent'])
    
    df['h3_index'] = df.apply(
        lambda row: h3.latlng_to_cell(row['lat'], row['lon'], resolution), axis=1
    )
    
    aggregated = df.groupby('h3_index').agg({
        'monthly_rent': 'median',
        'lat': 'mean',
        'lon': 'mean'
    }).reset_index()
    
    aggregated.columns = ['h3_index', 'median_rent', 'lat', 'lon']
    logger.info(f"Aggregated to {len(aggregated)} H3 cells")
    return aggregated


def compute_moran_i(df: pd.DataFrame, k_neighbors: int = 8) -> dict:
    """Compute global Moran's I statistic."""
    logger.info("Computing global Moran's I...")
    
    coords = df[['lat', 'lon']].values
    y = df['median_rent'].values
    
    weights = KNN.from_array(coords, k=k_neighbors)
    weights.transform = 'r'
    
    moran = Moran(y, weights, permutations=99)
    
    return {
        'morans_i': moran.I,
        'expected_i': moran.EI,
        'variance': moran.VI_sim,
        'z_score': moran.z_sim,
        'p_value': moran.p_sim,
        'permutations': 99
    }


def compute_lisa(df: pd.DataFrame, k_neighbors: int = 8) -> pd.DataFrame:
    """Compute Local Indicators of Spatial Association (LISA)."""
    logger.info("Computing LISA statistics...")
    
    coords = df[['lat', 'lon']].values
    y = df['median_rent'].values
    
    weights = KNN.from_array(coords, k=k_neighbors)
    weights.transform = 'r'
    
    lisa = Moran_Local(y, weights, permutations=99)
    
    result = df.copy()
    result['lisa_z'] = lisa.Z
    result['lisa_p'] = lisa.p_sim
    result['local_moran'] = lisa.Is
    
    def classify_lisa(z, p):
        if p > 0.05:
            return 'NS'
        elif z > 0 and lisa.q[result.index[result.index.get_loc(i)]] in [1, 3]:
            return 'HH'
        elif z < 0 and lisa.q[result.index[result.index.get_loc(i)]] in [2, 4]:
            return 'LL'
        elif z > 0 and lisa.q[result.index[result.index.get_loc(i)]] in [2, 4]:
            return 'HL'
        else:
            return 'LH'
    
    result['lisa_cluster'] = 'NS'
    for i in result.index:
        idx = result.index.get_loc(i)
        if result.loc[i, 'lisa_p'] <= 0.05:
            q_val = lisa.q[idx]
            if result.loc[i, 'lisa_z'] > 0:
                result.loc[i, 'lisa_cluster'] = 'HH' if q_val in [1, 3] else 'HL'
            else:
                result.loc[i, 'lisa_cluster'] = 'LL' if q_val in [2, 4] else 'LH'
    
    return result


def summarize_results(moran_result: dict, lisa_df: pd.DataFrame) -> list:
    """Generate key findings summary."""
    findings = []
    
    findings.append(f"Global Moran's I: {moran_result['morans_i']:.4f}")
    findings.append(f"Z-score: {moran_result['z_score']:.2f}")
    findings.append(f"P-value: {moran_result['p_value']:.4f}")
    
    if moran_result['morans_i'] > 0.3:
        interpretation = "Moderate positive spatial clustering"
    elif moran_result['morans_i'] > 0.1:
        interpretation = "Weak positive spatial clustering"
    elif moran_result['morans_i'] > -0.1:
        interpretation = "No significant spatial pattern"
    else:
        interpretation = "Negative spatial autocorrelation"
    findings.append(f"Interpretation: {interpretation}")
    
    cluster_counts = lisa_df['lisa_cluster'].value_counts()
    for cluster, count in cluster_counts.items():
        if cluster != 'NS':
            findings.append(f"{cluster} clusters: {count}")
    
    return findings


def main():
    start_time = datetime.now()
    
    logger.info("="*60)
    logger.info("SPATIAL AUTOCORRELATION ANALYSIS (Moran's I + LISA)")
    logger.info("="*60)
    
    if not H3_AVAILABLE or not SPATIAL_AVAILABLE:
        logger.error("Required packages not available: h3, libpysal, esda")
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
    
    moran_result = compute_moran_i(aggregated, k_neighbors)
    
    for key, value in moran_result.items():
        logger.info(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
    
    lisa_df = compute_lisa(aggregated, k_neighbors)
    
    output_dir = Config.ANALYSIS_OUTPUT_DIR / "analyze_spatial_autocorrelation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    moran_df = pd.DataFrame([moran_result])
    moran_df.to_csv(output_dir / "moran_results.csv", index=False)
    logger.info(f"Saved: {output_dir / 'moran_results.csv'}")
    
    lisa_df.to_csv(output_dir / "lisa_results.csv", index=False)
    logger.info(f"Saved: {output_dir / 'lisa_results.csv'}")
    
    findings = summarize_results(moran_result, lisa_df)
    for f in findings:
        logger.info(f"  {f}")
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(json.dumps({
        "script": "analyze_spatial_autocorrelation",
        "status": "success",
        "key_findings": findings,
        "outputs": [
            str(output_dir / "moran_results.csv"),
            str(output_dir / "lisa_results.csv")
        ],
        "duration_seconds": round(duration, 2)
    }))
    
    logger.info("="*60)
    logger.info("Spatial autocorrelation analysis complete!")
    logger.info("="*60)


if __name__ == "__main__":
    main()
