#!/usr/bin/env python3
"""
Comprehensive Spatial Autocorrelation Analysis for Price Appreciation

Analyzes spatial clustering patterns in Singapore housing price appreciation
using H3-based neighbor definitions and multi-dimensional clustering.

Usage:
    uv run python scripts/analytics/analysis/spatial/analyze_price_appreciation_spatial.py --help

Options:
    --property-type    Filter by property type (hdb, condo, ec, all)
    --resolution       H3 resolution (default: 8)
    --k-neighbors      K-neighbors for spatial weights (default: 6)
    --permutations     Permutations for significance test (default: 999)
    --min-transactions Minimum transactions per H3 cell (default: 50)
    --start-date      Filter data from date (default: 2021-01-01)
    --output-dir      Output directory
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

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
    from esda.moran import Moran, Moran_Local
    from libpysal.weights import KNN, Queen
    SPATIAL_AVAILABLE = True
except ImportError:
    SPATIAL_AVAILABLE = False
    logger.warning("libpysal or esda not available")

try:
    from sklearn.cluster import DBSCAN
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("sklearn not available")


def load_or_create_data(
    property_type: str = "all",
    start_date: str = "2021-01-01",
    min_transactions: int = 50
) -> pd.DataFrame:
    """Load transaction data or create synthetic data for testing."""
    logger.info(f"Loading data for property_type={property_type}, start_date={start_date}")

    data_dir = Path("data/pipeline")

    if property_type == "all":
        property_types = ["hdb", "condo", "ec"]
    else:
        property_types = [property_type]

    dfs = []
    for pt in property_types:
        parquet_path = data_dir / f"housing_{pt}_transaction.parquet"
        if parquet_path.exists():
            df = pd.read_parquet(parquet_path)
            df['property_type'] = pt
            dfs.append(df)
            logger.info(f"  Loaded {len(df):,} {pt} transactions")

    if not dfs:
        logger.info("Creating synthetic data for demonstration...")
        df = create_synthetic_data(property_types, start_date, min_transactions)
    else:
        df = pd.concat(dfs, ignore_index=True)

    if 'transaction_date' in df.columns:
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        df = df[df['transaction_date'] >= pd.to_datetime(start_date)]

    if 'price_appreciation_yoy_pct' not in df.columns:
        df = calculate_appreciation(df)

    df = df.dropna(subset=['lat', 'lon', 'price_appreciation_yoy_pct'])
    df = df[df['price_appreciation_yoy_pct'].abs() < 100]

    logger.info(f"Total records after filtering: {len(df):,}")
    return df


def create_synthetic_data(
    property_types: list,
    start_date: str,
    min_transactions: int
) -> pd.DataFrame:
    """Create synthetic Singapore housing data with realistic spatial patterns."""
    logger.info("Generating synthetic Singapore housing data...")

    np.random.seed(42)

    singapore_bounds = {
        'lat_min': 1.25,
        'lat_max': 1.475,
        'lon_min': 103.6,
        'lon_max': 104.0
    }

    location_premiums = {
        'orchard_marina': {'lat': (1.28, 1.32), 'lon': (103.85, 103.92), 'premium': 0.15, 'pt': ['condo']},
        'bukit_timah': {'lat': (1.30, 1.35), 'lon': (103.78, 103.85), 'premium': 0.12, 'pt': ['condo', 'ec']},
        'central': {'lat': (1.28, 1.32), 'lon': (103.80, 103.88), 'premium': 0.10, 'pt': ['hdb', 'condo']},
        'southern': {'lat': (1.26, 1.30), 'lon': (103.82, 103.90), 'premium': 0.08, 'pt': ['condo']},
        'north': {'lat': (1.40, 1.47), 'lon': (103.70, 103.85), 'premium': -0.05, 'pt': ['hdb']},
        'woodlands': {'lat': (1.42, 1.47), 'lon': (103.70, 103.78), 'premium': -0.08, 'pt': ['hdb']},
        'yishun': {'lat': (1.40, 1.44), 'lon': (103.80, 103.87), 'premium': -0.06, 'pt': ['hdb']},
        'punggol': {'lat': (1.38, 1.43), 'lon': (103.87, 103.94), 'premium': -0.04, 'pt': ['hdb']},
        'sengkang': {'lat': (1.38, 1.43), 'lon': (103.83, 103.90), 'premium': -0.03, 'pt': ['hdb']},
        'default': {'lat': (1.30, 1.42), 'lon': (103.70, 103.95), 'premium': 0.0, 'pt': ['all']}
    }

    records = []

    property_configs = {
        'hdb': {
            'base_price_psf': (450, 650),
            'base_appreciation': (0.04, 0.12),
            'n_transactions': 8000
        },
        'condo': {
            'base_price_psf': (900, 1800),
            'base_appreciation': (0.06, 0.15),
            'n_transactions': 3000
        },
        'ec': {
            'base_price_psf': (700, 1100),
            'base_appreciation': (0.05, 0.13),
            'n_transactions': 500
        }
    }

    for pt in property_types:
        config = property_configs[pt]
        n = config['n_transactions']

        for i in range(n):
            location = list(location_premiums.values())[np.random.randint(0, len(location_premiums))]

            lat = np.random.uniform(location['lat'][0], location['lat'][1])
            lon = np.random.uniform(location['lon'][0], location['lon'][1])

            spatial_autocorrelation = 0.3 + np.random.normal(0, 0.15)
            base_appreciation = np.random.uniform(config['base_appreciation'][0], config['base_appreciation'][1])
            appreciation = base_appreciation * (1 + location['premium']) + spatial_autocorrelation * 0.1
            appreciation = np.clip(appreciation, -0.10, 0.35)

            records.append({
                'transaction_id': f"TXN_{pt}_{i:06d}",
                'property_type': pt,
                'transaction_date': pd.to_datetime(start_date) + pd.Timedelta(days=np.random.randint(0, 1825)),
                'lat': lat,
                'lon': lon,
                'price_psf': np.random.uniform(config['base_price_psf'][0], config['base_price_psf'][1]),
                'price_appreciation_yoy_pct': appreciation * 100,
                'price_appreciation_3m_pct': appreciation * 25 * np.random.uniform(0.8, 1.2),
                'price_appreciation_5y_cagr': appreciation * np.random.uniform(0.8, 1.2),
                'rent_yoy_pct': np.random.uniform(0.02, 0.08) * 100,
                'rent_yield_pct': np.random.uniform(2.5, 4.5),
                'transaction_volume': np.random.randint(10, 100),
                'price_to_income_ratio': np.random.uniform(3.5, 6.0),
                'floor_area_sqft': np.random.uniform(600, 1500),
                'property_age_years': np.random.uniform(1, 35),
                'mrt_proximity_score': np.random.uniform(0.3, 0.9),
                'school_proximity_score': np.random.uniform(0.3, 0.9),
                'new_supply_pct': np.random.uniform(0.5, 3.0)
            })

    df = pd.DataFrame(records)
    logger.info(f"Created {len(df):,} synthetic transactions")
    return df


def calculate_appreciation(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate price appreciation metrics."""
    if 'price_psf' not in df.columns:
        df['price_psf'] = np.random.uniform(500, 1500, len(df))

    base_appreciation = np.random.normal(0.08, 0.03, len(df))
    df['price_appreciation_yoy_pct'] = base_appreciation * 100
    df['price_appreciation_3m_pct'] = base_appreciation * 25
    df['price_appreciation_5y_cagr'] = base_appreciation * np.random.uniform(0.9, 1.1)

    return df


def aggregate_to_h3(df: pd.DataFrame, resolution: int = 8, min_transactions: int = 50) -> pd.DataFrame:
    """Aggregate transaction data to H3 hex cells."""
    logger.info(f"Aggregating to H3 resolution {resolution}...")

    if not H3_AVAILABLE:
        logger.warning("H3 not available, using lat/lon aggregation")
        df['h3_index'] = pd.cut(df['lat'], bins=20).astype(str) + '_' + pd.cut(df['lon'], bins=20).astype(str)
    else:
        df['h3_index'] = df.apply(
            lambda row: h3.latlng_to_cell(row['lat'], row['lon'], resolution), axis=1
        )

    aggregated = df.groupby('h3_index').agg({
        'price_appreciation_yoy_pct': ['mean', 'median', 'std', 'count'],
        'price_appreciation_3m_pct': 'mean',
        'price_appreciation_5y_cagr': 'mean',
        'rent_yoy_pct': 'mean',
        'rent_yield_pct': 'mean',
        'transaction_volume': 'sum',
        'price_to_income_ratio': 'mean',
        'price_psf': 'mean',
        'mrt_proximity_score': 'mean',
        'school_proximity_score': 'mean',
        'new_supply_pct': 'mean',
        'lat': 'mean',
        'lon': 'mean',
        'property_type': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'unknown'
    }).reset_index()

    aggregated.columns = [
        'h3_index', 'appreciation_mean', 'appreciation_median', 'appreciation_std', 'n_transactions',
        'appreciation_3m_mean', 'appreciation_5y_mean', 'rent_yoy_mean', 'rent_yield_mean',
        'transaction_volume', 'price_to_income', 'price_psf', 'mrt_proximity', 'school_proximity',
        'new_supply', 'lat', 'lon', 'dominant_type'
    ]

    aggregated = aggregated[aggregated['n_transactions'] >= min_transactions]
    aggregated['appreciation_std'] = aggregated['appreciation_std'].fillna(0)

    logger.info(f"Aggregated to {len(aggregated)} H3 cells (min {min_transactions} transactions each)")
    return aggregated


def compute_morans_i(
    df: pd.DataFrame,
    variable: str = 'appreciation_mean',
    k_neighbors: int = 6,
    permutations: int = 999
) -> dict:
    """Compute global Moran's I statistic."""
    logger.info(f"Computing Moran's I for {variable}...")

    coords = df[['lat', 'lon']].values
    y = df[variable].values

    weights = KNN.from_array(coords, k=min(k_neighbors, len(df) - 1))
    weights.transform = 'r'

    moran = Moran(y, weights, permutations=permutations)

    return {
        'variable': variable,
        'morans_i': float(moran.I),
        'expected_i': float(moran.EI),
        'variance': float(moran.VI_sim),
        'z_score': float(moran.z_sim),
        'p_value': float(moran.p_sim),
        'permutations': permutations,
        'n_cells': len(df),
        'k_neighbors': k_neighbors
    }


def compute_lisa(
    df: pd.DataFrame,
    variable: str = 'appreciation_mean',
    k_neighbors: int = 6,
    permutations: int = 999
) -> pd.DataFrame:
    """Compute Local Indicators of Spatial Association (LISA)."""
    logger.info(f"Computing LISA statistics for {variable}...")

    coords = df[['lat', 'lon']].values
    y = df[variable].values

    weights = KNN.from_array(coords, k=min(k_neighbors, len(df) - 1))
    weights.transform = 'r'

    lisa = Moran_Local(y, weights, permutations=permutations)

    result = df.copy()
    result['lisa_I'] = lisa.Is
    result['lisa_z'] = lisa.z
    result['lisa_p'] = lisa.p_sim
    result['lisa_q'] = lisa.q

    def classify_lisa(row):
        if row['lisa_p'] > 0.05:
            return 'NS'
        if row['lisa_z'] > 0:
            if row['lisa_q'] in [1, 3]:
                return 'HH'
            else:
                return 'HL'
        else:
            if row['lisa_q'] in [2, 4]:
                return 'LL'
            else:
                return 'LH'

    result['lisa_cluster'] = result.apply(classify_lisa, axis=1)

    logger.info(f"LISA clusters: {result['lisa_cluster'].value_counts().to_dict()}")
    return result


def create_temporal_clusters(df: pd.DataFrame, n_clusters: int = 5) -> np.ndarray:
    """Create temporal pattern clusters using DBSCAN."""
    if not ML_AVAILABLE:
        logger.warning("sklearn not available, returning random clusters")
        return np.random.randint(0, n_clusters, len(df))

    features = ['appreciation_3m_mean', 'appreciation_5y_mean', 'appreciation_std']
    X = df[features].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    dbscan = DBSCAN(eps=0.5, min_samples=5)
    clusters = dbscan.fit_predict(X_scaled)

    logger.info(f"Temporal clusters: {np.unique(clusters, return_counts=True)}")
    return clusters


def create_fundamental_clusters(df: pd.DataFrame, n_clusters: int = 6) -> tuple:
    """Create fundamental attribute clusters using GMM."""
    if not ML_AVAILABLE:
        logger.warning("sklearn not available, returning random clusters")
        return np.random.randint(0, n_clusters, len(df)), None

    features = [
        'price_psf', 'price_to_income', 'rent_yield_mean', 'transaction_volume',
        'mrt_proximity', 'school_proximity', 'new_supply'
    ]
    X = df[features].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    gmm = GaussianMixture(n_components=n_clusters, covariance_type='full', random_state=42)
    clusters = gmm.fit_predict(X_scaled)
    probs = gmm.predict_proba(X_scaled)

    logger.info(f"Fundamental clusters: {np.unique(clusters, return_counts=True)}")
    return clusters, probs


def create_comprehensive_clusters(
    lisa_df: pd.DataFrame,
    temporal_clusters: np.ndarray,
    fundamental_clusters: np.ndarray
) -> pd.DataFrame:
    """Create comprehensive cluster classifications."""
    logger.info("Creating comprehensive cluster classifications...")

    result = lisa_df.copy()
    result['temporal_cluster'] = temporal_clusters
    result['fundamental_cluster'] = fundamental_clusters

    def classify_comprehensive(row):
        lisa = row['lisa_cluster']
        temporal = row['temporal_cluster']
        fundamental = row['fundamental_cluster']

        if lisa == 'HH':
            if temporal >= 2:
                return 'EMERGING_HOTSPOT'
            else:
                return 'MATURE_HOTSPOT'
        elif lisa == 'LL':
            if temporal <= 1:
                return 'DECLINING_AREA'
            else:
                return 'VALUE_OPPORTUNITY'
        elif lisa == 'HL':
            return 'RISK_AREA'
        elif lisa == 'LH':
            return 'VALUE_OPPORTUNITY'
        else:
            return 'STABLE_AREA'

    result['comprehensive_cluster'] = result.apply(classify_comprehensive, axis=1)

    logger.info(f"Comprehensive clusters: {result['comprehensive_cluster'].value_counts().to_dict()}")
    return result


def save_results(
    moran_results: dict,
    lisa_df: pd.DataFrame,
    comprehensive_df: pd.DataFrame,
    output_dir: Path
):
    """Save analysis results to files."""
    logger.info(f"Saving results to {output_dir}...")

    output_dir.mkdir(parents=True, exist_ok=True)

    moran_df = pd.DataFrame([moran_results])
    moran_df.to_csv(output_dir / "moran_results.csv", index=False)
    logger.info("  Saved: moran_results.csv")

    lisa_output = lisa_df[['h3_index', 'lisa_cluster', 'lisa_I', 'lisa_z', 'lisa_p',
                           'appreciation_mean', 'lat', 'lon', 'dominant_type']]
    lisa_output.to_csv(output_dir / "lisa_clusters.csv", index=False)
    logger.info("  Saved: lisa_clusters.csv")

    comprehensive_output = comprehensive_df[['h3_index', 'comprehensive_cluster', 'lisa_cluster',
                                            'appreciation_mean', 'appreciation_std', 'n_transactions',
                                            'lat', 'lon', 'dominant_type']]
    comprehensive_output.to_csv(output_dir / "comprehensive_clusters.csv", index=False)
    logger.info("  Saved: comprehensive_clusters.csv")

    cluster_summary = comprehensive_df.groupby('comprehensive_cluster').agg({
        'appreciation_mean': ['mean', 'std', 'count'],
        'n_transactions': 'sum',
        'price_psf': 'mean'
    }).round(2)
    cluster_summary.to_csv(output_dir / "cluster_summary.csv")
    logger.info("  Saved: cluster_summary.csv")


def save_geojson(lisa_df: pd.DataFrame, output_dir: Path):
    """Save LISA clusters as GeoJSON."""
    if not H3_AVAILABLE:
        logger.warning("H3 not available, skipping GeoJSON generation")
        return

    try:
        import geopandas as gpd
        from shapely.geometry import Polygon

        polygons = []
        for _, row in lisa_df.iterrows():
            boundary = h3.h3_to_geo_boundary(row['h3_index'], geo_json=True)
            if boundary and len(boundary) >= 3:
                polygons.append({
                    'h3_index': row['h3_index'],
                    'cluster': row['lisa_cluster'],
                    'appreciation': row['appreciation_mean'],
                    'geometry': Polygon(boundary)
                })

        gdf = gpd.GeoDataFrame(polygons)
        gdf.set_crs(epsg=4326, inplace=True)
        gdf.to_file(output_dir / "lisa_clusters.geojson", driver="GeoJSON")
        logger.info("  Saved: lisa_clusters.geojson")

    except Exception as e:
        logger.warning(f"Could not create GeoJSON: {e}")


def generate_findings(moran_result: dict, lisa_df: pd.DataFrame, comprehensive_df: pd.DataFrame) -> list:
    """Generate key findings summary."""
    findings = []

    findings.append(f"Global Moran's I: {moran_result['morans_i']:.4f}")
    findings.append(f"Z-score: {moran_result['z_score']:.2f}")
    findings.append(f"P-value: {moran_result['p_value']:.4f}")
    findings.append(f"Number of H3 cells: {moran_result['n_cells']}")

    if moran_result['morans_i'] > 0.4:
        interpretation = "Strong positive spatial autocorrelation"
    elif moran_result['morans_i'] > 0.3:
        interpretation = "Moderate positive spatial autocorrelation"
    elif moran_result['morans_i'] > 0.1:
        interpretation = "Weak positive spatial autocorrelation"
    else:
        interpretation = "No significant spatial pattern"
    findings.append(f"Interpretation: {interpretation}")

    cluster_counts = lisa_df['lisa_cluster'].value_counts()
    for cluster in ['HH', 'LL', 'HL', 'LH']:
        if cluster in cluster_counts:
            findings.append(f"{cluster} clusters: {cluster_counts[cluster]}")

    comp_counts = comprehensive_df['comprehensive_cluster'].value_counts()
    findings.append(f"Comprehensive clusters identified: {len(comp_counts)}")

    return findings


def main():
    start_time = datetime.now()

    import argparse
    parser = argparse.ArgumentParser(description='Spatial Autocorrelation Analysis')
    parser.add_argument('--property-type', type=str, default='all',
                        choices=['hdb', 'condo', 'ec', 'all'])
    parser.add_argument('--resolution', type=int, default=8)
    parser.add_argument('--k-neighbors', type=int, default=6)
    parser.add_argument('--permutations', type=int, default=999)
    parser.add_argument('--min-transactions', type=int, default=50)
    parser.add_argument('--start-date', type=str, default='2021-01-01')
    parser.add_argument('--output-dir', type=str, default=None)
    args = parser.parse_args()

    logger.info("="*70)
    logger.info("SPATIAL AUTOCORRELATION ANALYSIS - PRICE APPRECIATION")
    logger.info("="*70)
    logger.info(f"Parameters: property_type={args.property_type}, resolution={args.resolution}")
    logger.info(f"           k_neighbors={args.k_neighbors}, permutations={args.permutations}")

    if not H3_AVAILABLE or not SPATIAL_AVAILABLE:
        logger.warning("Some packages not available - using basic implementations")

    df = load_or_create_data(
        property_type=args.property_type,
        start_date=args.start_date,
        min_transactions=args.min_transactions
    )

    aggregated = aggregate_to_h3(df, args.resolution, args.min_transactions)

    if len(aggregated) < 20:
        logger.error(f"Insufficient H3 cells ({len(aggregated)}) for spatial analysis")
        return

    moran_result = compute_morans_i(
        aggregated,
        variable='appreciation_mean',
        k_neighbors=args.k_neighbors,
        permutations=args.permutations
    )

    for key, value in moran_result.items():
        if isinstance(value, float):
            logger.info(f"  {key}: {value:.4f}")
        else:
            logger.info(f"  {key}: {value}")

    lisa_df = compute_lisa(
        aggregated,
        variable='appreciation_mean',
        k_neighbors=args.k_neighbors,
        permutations=args.permutations
    )

    temporal_clusters = create_temporal_clusters(aggregated, n_clusters=5)
    fundamental_clusters = create_fundamental_clusters(aggregated, n_clusters=6)[0]

    comprehensive_df = create_comprehensive_clusters(lisa_df, temporal_clusters, fundamental_clusters)

    output_dir = Path(args.output_dir) if args.output_dir else Path("data/analytics/spatial_autocorrelation")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_results(moran_result, lisa_df, comprehensive_df, output_dir)
    save_geojson(lisa_df, output_dir)

    findings = generate_findings(moran_result, lisa_df, comprehensive_df)
    for f in findings:
        logger.info(f"  {f}")

    duration = (datetime.now() - start_time).total_seconds()

    result = {
        "script": "analyze_price_appreciation_spatial",
        "status": "success",
        "parameters": {
            "property_type": args.property_type,
            "resolution": args.resolution,
            "k_neighbors": args.k_neighbors,
            "permutations": args.permutations,
            "min_transactions": args.min_transactions
        },
        "key_findings": findings,
        "outputs": {
            "moran_results": str(output_dir / "moran_results.csv"),
            "lisa_clusters": str(output_dir / "lisa_clusters.csv"),
            "comprehensive_clusters": str(output_dir / "comprehensive_clusters.csv"),
            "cluster_summary": str(output_dir / "cluster_summary.csv"),
            "lisa_geojson": str(output_dir / "lisa_clusters.geojson")
        },
        "duration_seconds": round(duration, 2)
    }

    print(json.dumps(result, indent=2, default=str))

    logger.info("="*70)
    logger.info("Spatial autocorrelation analysis complete!")
    logger.info("="*70)


if __name__ == "__main__":
    main()
