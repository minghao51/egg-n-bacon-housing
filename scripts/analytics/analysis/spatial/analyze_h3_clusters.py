#!/usr/bin/env python3
"""
Analyze H3 Clusters using DBSCAN.

Discovers natural property clusters based on location and attributes.

Usage:
    uv run python scripts/analysis/analyze_h3_clusters.py --help
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
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available")


def load_property_data() -> pd.DataFrame:
    """Load unified property data with features."""
    logger.info("Loading property data...")
    
    possible_paths = [
        Config.PARQUETS_DIR / "L3" / "housing_unified.parquet",
        Config.PARQUETS_DIR / "L2" / "housing_multi_amenity_features.parquet",
        Config.DATA_DIR / "analysis" / "market_segmentation" / "housing_unified_segmented.parquet"
    ]
    
    df = None
    for path in possible_paths:
        if path.exists():
            df = pd.read_parquet(path)
            logger.info(f"Loaded {len(df):,} records from {path}")
            break
    
    if df is None:
        logger.error("No suitable property data found")
        return pd.DataFrame()
    
    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """Prepare features for clustering."""
    logger.info("Preparing features for clustering...")
    
    feature_cols = ['price_psf', 'floor_area_sqm', 'rental_yield_pct', 'remaining_lease_months']
    available_cols = [c for c in feature_cols if c in df.columns]
    
    if not available_cols:
        logger.warning("No clustering features available, using defaults")
        available_cols = ['price_psf', 'floor_area_sqm']
    
    df_clean = df.dropna(subset=available_cols)
    logger.info(f"Records after dropping missing: {len(df_clean):,}")
    
    if len(df_clean) < 50:
        logger.error("Insufficient data for clustering")
        return None, None, None
    
    X = df_clean[available_cols].copy()
    
    for col in X.columns:
        if X[col].std() == 0:
            X[col] = 1
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return df_clean, X_scaled, available_cols


def run_dbscan(X_scaled: np.ndarray, eps: float = 0.5, min_samples: int = 10) -> np.ndarray:
    """Run DBSCAN clustering."""
    logger.info(f"Running DBSCAN (eps={eps}, min_samples={min_samples})...")
    
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = dbscan.fit_predict(X_scaled)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    logger.info(f"Clusters found: {n_clusters}")
    logger.info(f"Noise points: {n_noise} ({n_noise/len(labels)*100:.1f}%)")
    
    return labels


def compute_silhouette(X_scaled: np.ndarray, labels: np.ndarray) -> float:
    """Compute silhouette score for cluster quality."""
    if len(set(labels)) < 2:
        return -1
    
    mask = labels != -1
    if mask.sum() < 2:
        return -1
    
    score = silhouette_score(X_scaled[mask], labels[mask])
    logger.info(f"Silhouette score: {score:.4f}")
    return score


def create_cluster_profiles(df: pd.DataFrame, labels: np.ndarray, feature_cols: list) -> pd.DataFrame:
    """Create statistical profiles per cluster."""
    logger.info("Creating cluster profiles...")
    
    df_result = df.copy()
    df_result['cluster_id'] = labels
    
    cluster_profiles = df_result[df_result['cluster_id'] >= 0].groupby('cluster_id').agg({
        'price_psf': ['mean', 'std', 'count'],
        'floor_area_sqm': 'mean',
        'rental_yield_pct': 'mean',
        'remaining_lease_months': 'mean'
    })
    
    cluster_profiles.columns = ['_'.join(col).strip() for col in cluster_profiles.columns.values]
    cluster_profiles = cluster_profiles.reset_index()
    
    return cluster_profiles


def name_clusters(profiles: pd.DataFrame, feature_cols: list) -> dict:
    """Assign descriptive names to clusters based on characteristics."""
    names = {}
    
    if 'price_psf_mean' in profiles.columns:
        price_median = profiles['price_psf_mean'].median()
        yield_median = profiles.get('rental_yield_pct_mean', pd.Series([0])).median()
        
        for _, row in profiles.iterrows():
            name_parts = []
            
            if row.get('price_psf_mean', 0) > price_median * 1.2:
                name_parts.append("Premium")
            elif row.get('price_psf_mean', 0) < price_median * 0.8:
                name_parts.append("Budget")
            
            if 'rental_yield_pct_mean' in row.index:
                if row['rental_yield_pct_mean'] > yield_median * 1.2:
                    name_parts.append("Yield")
                elif row['rental_yield_pct_mean'] < yield_median * 0.8:
                    name_parts.append("Low-Yield")
            
            if not name_parts:
                name_parts.append("Standard")
            
            names[int(row['cluster_id'])] = " ".join(name_parts)
    
    return names


def summarize_results(labels: np.ndarray, silhouette_score: float, profiles: pd.DataFrame, names: dict) -> list:
    """Generate key findings summary."""
    findings = []
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    findings.append(f"Clusters found: {n_clusters}")
    findings.append(f"Noise points: {n_noise} ({n_noise/len(labels)*100:.1f}%)")
    findings.append(f"Silhouette score: {silhouette_score:.4f}")
    
    for _, row in profiles.iterrows():
        cluster_id = int(row['cluster_id'])
        name = names.get(cluster_id, f"Cluster {cluster_id}")
        count = int(row.get('price_psf_count', row.get('floor_area_sqm_count', 0)))
        findings.append(f"  {name}: {count} properties")
    
    return findings


def main():
    start_time = datetime.now()
    
    logger.info("="*60)
    logger.info("H3 CLUSTER ANALYSIS (DBSCAN)")
    logger.info("="*60)
    
    if not H3_AVAILABLE or not SKLEARN_AVAILABLE:
        logger.error("Required packages not available: h3, scikit-learn")
        return
    
    df = load_property_data()
    if df.empty:
        logger.error("No data available")
        return
    
    df_clean, X_scaled, feature_cols = prepare_features(df)
    if df_clean is None:
        return
    
    labels = run_dbscan(X_scaled, eps=0.5, min_samples=10)
    
    silhouette = compute_silhouette(X_scaled, labels)
    
    profiles = create_cluster_profiles(df_clean, labels, feature_cols)
    names = name_clusters(profiles, feature_cols)
    
    df_clean['cluster_id'] = labels
    df_clean['cluster_name'] = df_clean['cluster_id'].map(
        lambda x: names.get(x, 'Noise') if x >= 0 else 'Noise'
    )
    
    output_dir = Config.ANALYSIS_OUTPUT_DIR / "analyze_h3_clusters"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df_clean[['property_index', 'lat', 'lon', 'cluster_id', 'cluster_name'] + feature_cols].to_csv(
        output_dir / "property_clusters.csv", index=False
    )
    logger.info(f"Saved: {output_dir / 'property_clusters.csv'}")
    
    profiles['cluster_name'] = profiles['cluster_id'].map(names)
    profiles.to_csv(output_dir / "cluster_profiles.csv", index=False)
    logger.info(f"Saved: {output_dir / 'cluster_profiles.csv'}")
    
    findings = summarize_results(labels, silhouette, profiles, names)
    for f in findings:
        logger.info(f"  {f}")
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(json.dumps({
        "script": "analyze_h3_clusters",
        "status": "success",
        "key_findings": findings,
        "outputs": [
            str(output_dir / "property_clusters.csv"),
            str(output_dir / "cluster_profiles.csv")
        ],
        "duration_seconds": round(duration, 2)
    }))
    
    logger.info("="*60)
    logger.info("H3 cluster analysis complete!")
    logger.info("="*60)


if __name__ == "__main__":
    main()
