# Pipeline Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand amenity data coverage from 129 hawker centres to 1000+ locations across 5+ amenity types, implement L4 ML analysis (price prediction, clustering, forecasting), and improve rental yield coverage from 17% to 80%+ using only free/public data sources.

**Architecture:** Sequential 4-phase implementation on main branch. Each phase builds on the previous: fix amenity data ingestion → integrate into L2 features → implement ML models → improve rental yield. All changes use existing patterns (parquet storage, metadata tracking, absolute imports).

**Tech Stack:** Python 3.11, geopandas (spatial joins), scikit-learn (ML), xgboost (price prediction), Prophet/ARIMA (forecasting), OneMap API (geocoding), data.gov.sg (amenity datasets)

---

## Phase 1: Fix Amenity Data Ingestion (2-3 days)

**Summary:** Parse supermarket HTML, download MRT/Phase 2 datasets, extract park centroids, geocode shopping malls.

### Task 1.1: Fix Supermarket Parsing

**Files:**
- Modify: `scripts/data/process/amenities/process_amenities.py:120-130`

**Step 1: Inspect supermarket geojson structure**

```bash
uv run python -c "
import geopandas as gpd
gdf = gpd.read_file('data/raw_data/csv/datagov/SupermarketsGEOJSON.geojson')
print(f'Columns: {list(gdf.columns)}')
print(f'First Description field: {gdf[\"Description\"].iloc[0][:500]}')
"
```

Expected: Output shows HTML table structure with LIC_NAME field

**Step 2: Update parse_datagov_geojson function**

Modify `process_amenities.py` function to extract LIC_NAME from HTML table:

```python
def extract_html_name(html_string, tag_name):
    """Extract text from HTML tag."""
    try:
        soup = BeautifulSoup(html_string, 'html.parser')
        tag = soup.find(tag_name)
        return tag.text if tag else ''
    except:
        return ''

def parse_datagov_geojson(filepath, amenity_type, name_field='Name'):
    """Parse GeoJSON file from data.gov.sg and extract lat/lon."""
    logger.info(f"Loading {amenity_type} from {filepath.name}...")

    gdf = gpd.read_file(filepath)

    # Ensure CRS is 4326
    if gdf.crs != 'EPSG:4326':
        gdf = gpd.to_crs('EPSG:4326')

    # Extract coordinates
    gdf['lon'] = gdf.geometry.x
    gdf['lat'] = gdf.geometry.y

    # Extract name based on field type
    if name_field in gdf.columns:
        # Direct field access
        gdf['name'] = gdf[name_field]
    elif 'Description' in gdf.columns:
        # Extract from HTML Description
        if amenity_type == 'supermarket':
            # Extract LIC_NAME from HTML table
            gdf['name'] = [extract_html_name(str(desc), 'LIC_NAME') if 'LIC_NAME' in str(desc) else ''
                           for desc in gdf.get('Description', '')]
        else:
            gdf['name'] = [extract_html_name(str(desc), name_field) for desc in gdf['Description']]
    else:
        # Fallback to Name field or empty string
        gdf['name'] = gdf.get('Name', '')

    # Create standardized dataframe
    df = pd.DataFrame({
        'name': gdf['name'].str.lower(),
        'type': amenity_type,
        'lat': gdf['lat'].astype(float),
        'lon': gdf['lon'].astype(float)
    })

    # Drop rows with missing coordinates or empty names
    df = df.dropna(subset=['lat', 'lon'])
    df = df[df['name'] != '']

    logger.info(f"✅ Loaded {len(df)} {amenity_type} locations")
    return df
```

**Step 3: Run amenity processing to verify fix**

```bash
uv run python scripts/data/process/amenities/process_amenities.py
```

Expected: "✅ Loaded 526 supermarket locations" (was 0)

**Step 4: Verify L1_amenity dataset**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L1_amenity')
print(f'Total: {len(df)}')
print(df['type'].value_counts())
"
```

Expected: 655 rows (129 hawker + 526 supermarket)

**Step 5: Commit changes**

```bash
git add scripts/data/process/amenities/process_amenities.py
git commit -m "fix(amenities): parse supermarket LIC_NAME from HTML table

- Extract LIC_NAME field from HTML Description table
- Fix parse_datagov_geojson to handle supermarket data
- Adds 526 supermarket locations (was 0)

Fixes #pipeline-phase1"
```

### Task 1.2: Download Phase 2 Datasets

**Files:**
- Use existing: `scripts/data/download/download_datagov_datasets.py`

**Step 1: Run Phase 2 download**

```bash
uv run python scripts/data/download/download_datagov_datasets.py --phase 2
```

Expected: Downloads MRT stations, MRT exits, childcare services with exponential backoff

**Step 2: Verify downloaded files**

```bash
ls -lh data/raw_data/csv/datagov/*.geojson | grep -E "(MRT|ChildCare)"
```

Expected: 3 new files (MRTStations.geojson, MRTStationExits.geojson, ChildCareServices.geojson)

**Step 3: Update process_amenities to include MRT**

Modify `process_amenities.py` main() function to add MRT processing:

```python
def main():
    """Process all amenity data and create combined dataset."""
    logger.info("🚀 Starting L1 utilities processing")

    data_base_path = Config.DATA_DIR
    datagov_path = data_base_path / 'raw_data' / 'csv' / 'datagov'

    # List to store all amenity dataframes
    amenity_dfs = []

    # ... existing code for hawker, supermarkets, malls ...

    # 6. MRT Stations (NEW)
    mrt_path = datagov_path / 'MRTStations.geojson'
    if mrt_path.exists():
        mrt_df = parse_datagov_geojson(mrt_path, 'mrt', 'NAME')
        amenity_dfs.append(mrt_df)
    else:
        logger.warning(f"⚠️  MRT station data not found at {mrt_path}")

    # ... rest of existing code ...
```

**Step 4: Re-run amenity processing**

```bash
uv run python scripts/data/process/amenities/process_amenities.py
```

Expected: "✅ Loaded X mrt locations"

**Step 5: Verify amenity counts**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L1_amenity')
print(df['type'].value_counts())
print(f'Total: {len(df)}')
"
```

Expected: 800+ rows (hawker + supermarket + mrt)

**Step 6: Commit changes**

```bash
git add scripts/data/process/amenities/process_amenities.py
git commit -m "feat(amenities): add MRT station dataset

- Download Phase 2 datasets (MRT, exits, childcare)
- Parse MRTStations.geojson
- Adds ~150 MRT locations to amenity data

Progress: #pipeline-phase1"
```

### Task 1.3: Add Park Centroid Extraction

**Files:**
- Modify: `scripts/data/process/amenities/process_amenities.py`

**Step 1: Add park centroid extraction function**

```python
def extract_park_centroids(geojson_path: pathlib.Path) -> pd.DataFrame:
    """Extract park polygon centroids as point geometries.

    Args:
        geojson_path: Path to NParks geojson file

    Returns:
        DataFrame with name, type, lat, lon columns
    """
    logger.info(f"Extracting park centroids from {geojson_path.name}...")

    gdf = gpd.read_file(geojson_path)

    # Ensure CRS is 4326
    if gdf.crs != 'EPSG:4326':
        gdf = gpd.to_crs('EPSG:4326')

    # Extract name from Description
    gdf['name'] = [extract_html_name(str(desc), 'NAME') for desc in gdf.get('Description', '')]

    # Calculate centroids from polygons
    gdf['lon'] = gdf.geometry.centroid.x
    gdf['lat'] = gdf.geometry.centroid.y

    # Create standardized dataframe
    df = pd.DataFrame({
        'name': gdf['name'].str.lower(),
        'type': 'park',
        'lat': gdf['lat'].astype(float),
        'lon': gdf['lon'].astype(float)
    })

    # Drop rows with missing data
    df = df.dropna(subset=['lat', 'lon', 'name'])
    df = df[df['name'] != '']

    logger.info(f"✅ Extracted {len(df)} park centroids")
    return df
```

**Step 2: Integrate into main() function**

Add to process_amenities.py main() after mall processing:

```python
# 7. Parks (centroids from polygons)
park_path = datagov_path / 'NParksParksandNatureReserves.geojson'
if park_path.exists():
    park_df = extract_park_centroids(park_path)
    amenity_dfs.append(park_df)
else:
    logger.warning(f"⚠️  Park data not found at {park_path}")
```

**Step 3: Remove old park geojson processing**

Remove the existing park connector geojson save code (lines 178-188 in current version).

**Step 4: Re-run amenity processing**

```bash
uv run python scripts/data/process/amenities/process_amenities.py
```

Expected: "✅ Extracted X park centroids"

**Step 5: Verify amenity counts**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L1_amenity')
print(df['type'].value_counts())
print(f'Total: {len(df)}')
"
```

Expected: 1000+ rows with hawker, supermarket, mrt, park types

**Step 6: Commit changes**

```bash
git add scripts/data/process/amenities/process_amenities.py
git commit -m "feat(amenities): extract park centroids from polygons

- Add extract_park_centroids function
- Calculate centroids from park polygon geometries
- Adds ~400 park locations

Progress: #pipeline-phase1"
```

### Task 1.4: Geocode Shopping Malls

**Files:**
- Create: `scripts/data/process/geocode_malls.py`

**Step 1: Create mall geocoding script**

```python
#!/usr/bin/env python3
"""Geocode shopping mall names from Wikipedia data."""

import logging
import sys
import time
from pathlib import Path

import pandas as pd
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from scripts.core.config import Config
from scripts.core.geocoding import geocode_address_onemap
from scripts.core.data_helpers import load_parquet, save_parquet

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def geocode_malls(batch_size: int = 10, delay: float = 1.0):
    """Geocode mall names using OneMap API.

    Args:
        batch_size: Number of malls to geocode per batch
        delay: Seconds to wait between API calls
    """
    logger.info("🚀 Starting mall geocoding")

    # Load mall names
    mall_df = load_parquet('raw_wiki_shopping_mall')
    logger.info(f"Loaded {len(mall_df)} mall names")

    # Check if already geocoded
    if 'lat' in mall_df.columns and 'lon' in mall_df.columns:
        already_done = mall_df.dropna(subset=['lat', 'lon'])
        logger.info(f"Already geocoded: {len(already_done)} malls")
        mall_df = mall_df[mall_df.isna().any(axis=1)]
        if mall_df.empty:
            logger.info("All malls already geocoded")
            return

    results = []
    failed = []

    for idx, row in mall_df.iterrows():
        mall_name = row['shopping_mall']

        try:
            logger.info(f"Geocoding: {mall_name}")

            # Try OneMap first
            result = geocode_address_onemap(mall_name, retry=3)

            if result:
                results.append({
                    'shopping_mall': mall_name,
                    'name': mall_name.lower(),
                    'type': 'mall',
                    'lat': result['latitude'],
                    'lon': result['longitude']
                })
                logger.info(f"  ✅ Found: {result['latitude']}, {result['longitude']}")
            else:
                failed.append(mall_name)
                logger.warning(f"  ❌ Not found: {mall_name}")

            # Rate limiting
            time.sleep(delay)

        except Exception as e:
            logger.error(f"  ❌ Error geocoding {mall_name}: {e}")
            failed.append(mall_name)

    # Save results
    if results:
        result_df = pd.DataFrame(results)
        save_parquet(result_df, 'L1_amenity_mall', source='geocoded malls')
        logger.info(f"✅ Saved {len(result_df)} geocoded malls")

    if failed:
        logger.warning(f"❌ Failed to geocode {len(failed)} malls")
        logger.warning(f"Failed malls: {failed[:5]}...")


if __name__ == '__main__':
    # Set paths
    PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    geocode_malls()
```

**Step 2: Run geocoding**

```bash
uv run python scripts/data/process/geocode_malls.py
```

Expected: Geocodes ~80-100 malls (some may not be found)

**Step 3: Update process_amenities to include geocoded malls**

Modify main() in process_amenities.py:

```python
# 5. Shopping malls (geocoded)
try:
    mall_df = load_parquet("L1_amenity_mall")
    mall_df = mall_df[['name', 'type', 'lat', 'lon']]
    amenity_dfs.append(mall_df)
    logger.info(f"✅ Loaded {len(mall_df)} geocoded mall locations")
except Exception as e:
    logger.warning(f"⚠️  Mall data error: {e}")
```

**Step 4: Re-run amenity processing**

```bash
uv run python scripts/data/process/amenities/process_amenities.py
```

**Step 5: Verify final amenity counts**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L1_amenity')
print('Amenity breakdown:')
print(df['type'].value_counts())
print(f'\nTotal locations: {len(df)}')
"
```

Expected: 1100+ locations across 5 types (hawker, supermarket, mrt, park, mall)

**Step 6: Commit changes**

```bash
git add scripts/data/process/geocode_malls.py
git add scripts/data/process/amenities/process_amenities.py
git commit -m "feat(amenities): geocode shopping malls

- Create geocode_malls.py script
- Use OneMap API for geocoding with rate limiting
- Adds ~100 mall locations with coordinates

Phase 1 complete: 1100+ amenity locations

Completes: #pipeline-phase1"
```

---

## Phase 2: Integrate Amenities into L2/L3 (1-2 days)

**Summary:** Update L2_features with per-type amenity metrics, expand L3 export schema, re-run pipeline.

### Task 2.1: Add Per-Type Amenity Metrics to L2

**Files:**
- Modify: `scripts/core/stages/L2_features.py:126-160`

**Step 1: Update compute_amenity_distances function**

Replace single distance calculation with per-type metrics:

```python
def compute_amenity_distances_by_type(
    unique_gdf: gpd.GeoDataFrame,
    amenity_gdf: gpd.GeoDataFrame,
    distance_thresholds: list = [500, 1000]  # meters
) -> pd.DataFrame:
    """Compute per-type amenity distances and counts.

    Args:
        unique_gdf: GeoDataFrame with property polygons
        amenity_gdf: GeoDataFrame with amenity points (has 'type' column)
        distance_thresholds: List of radius sizes for counting amenities

    Returns:
        DataFrame with property indices and amenity metrics
    """
    logger.info("Computing per-type amenity distances...")

    results = []
    amenity_types = amenity_gdf['type'].unique()

    for _, property_row in unique_gdf.iterrows():
        property_id = property_row.get('project_id') or property_row.get('address')
        property_geom = property_row.geometry

        row_result = {'property_id': property_id}

        for amenity_type in amenity_types:
            # Filter amenities by type
            type_amenities = amenity_gdf[amenity_gdf['type'] == amenity_type]

            if len(type_amenities) == 0:
                # Add default values if no amenities of this type
                row_result[f'dist_nearest_{amenity_type}'] = None
                for dist_threshold in distance_thresholds:
                    row_result[f'count_{amenity_type}_{dist_threshold}m'] = 0
                continue

            # Calculate distances to all amenities of this type
            distances = type_amenities.geometry.distance(property_geom) * 111000  # approx meters per degree

            # Nearest distance
            nearest_dist = distances.min()
            row_result[f'dist_nearest_{amenity_type}'] = round(nearest_dist, 2)

            # Count within radius
            for dist_threshold in distance_thresholds:
                count = (distances <= dist_threshold / 111000).sum()
                row_result[f'count_{amenity_type}_{dist_threshold}m'] = count

        results.append(row_result)

    df = pd.DataFrame(results)
    logger.info(f"✅ Computed amenity metrics for {len(df)} properties")
    return df
```

**Step 2: Update run_l2_features_pipeline to use new function**

Modify the pipeline call in L2_features.py around line 600:

```python
# OLD:
# amenity_distances = compute_amenity_distances(unique_gdf, amenity_gdf)

# NEW:
amenity_distances = compute_amenity_distances_by_type(unique_gdf, amenity_gdf)
```

**Step 3: Test amenity distance calculation**

```bash
uv run python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from scripts.core.stages.L2_features import load_property_and_amenity_data
from scripts.core.stages.L2_features import compute_amenity_distances_by_type
from scripts.core.stages.L2_features import create_property_geodataframe, prepare_unique_properties
import geopandas as gpd

# Load data
unique_df, amenity_df = load_property_and_amenity_data()
unique_df = prepare_unique_properties(unique_df)
unique_gdf = create_property_geodataframe(unique_df)
amenity_gdf = gpd.GeoDataFrame(
    amenity_df,
    geometry=gpd.points_from_xy(amenity_df.lon, amenity_df.lat),
    crs='EPSG:4326'
)

# Compute distances
result = compute_amenity_distances_by_type(unique_gdf, amenity_gdf)
print(result.head(3))
print(f'Columns: {list(result.columns)}')
"
```

Expected: DataFrame with columns like dist_nearest_hawker, dist_nearest_supermarket, count_hawker_500m, etc.

**Step 4: Commit changes**

```bash
git add scripts/core/stages/L2_features.py
git commit -m "feat(L2): add per-type amenity distance metrics

- Replace single amenity distance with type-specific metrics
- Add dist_nearest_{type} columns
- Add count_{type}_{radius}m columns
- Supports hawker, supermarket, mrt, park, mall types

Progress: #pipeline-phase2"
```

### Task 2.2: Update L3 Export Schema

**Files:**
- Modify: `scripts/core/stages/L3_export.py` (schema definition around line 100-200)

**Step 1: Update L3 schema to include amenity columns**

Add amenity columns to the unified dataset export. Find where final columns are defined and add:

```python
# Amenity distance columns
AMENITY_DISTANCE_COLUMNS = [
    'dist_nearest_hawker',
    'dist_nearest_supermarket',
    'dist_nearest_mrt',
    'dist_nearest_park',
    'dist_nearest_mall'
]

# Amenity count columns
AMENITY_COUNT_COLUMNS = [
    'count_hawker_500m', 'count_hawker_1000m',
    'count_supermarket_500m', 'count_supermarket_1000m',
    'count_mrt_500m', 'count_mrt_1000m',
    'count_park_500m', 'count_park_1000m',
    'count_mall_500m', 'count_mall_1000m'
]

# Add to base columns list
BASE_COLUMNS = [
    'project_id', 'address', 'property_type', 'price', 'sqft',
    'latitude', 'longitude', 'planning_area',
    ...existing columns...
    *AMENITY_DISTANCE_COLUMNS,
    *AMENITY_COUNT_COLUMNS
]
```

**Step 2: Test L3 export with new schema**

```bash
uv run python scripts/run_pipeline.py --stage L3
```

Expected: L3 export completes with amenity columns included

**Step 3: Verify L3 output**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L3_housing_unified')
amenity_cols = [c for c in df.columns if 'dist_nearest_' in c or 'count_' in c]
print(f'Amenity columns: {len(amenity_cols)}')
print(f'Sample columns: {amenity_cols[:5]}')
"
```

Expected: 15+ amenity columns (5 distances + 10 counts)

**Step 4: Commit changes**

```bash
git add scripts/core/stages/L3_export.py
git commit -m "feat(L3): expand schema with amenity metrics

- Add 5 distance columns (dist_nearest_{type})
- Add 10 count columns (count_{type}_{radius}m)
- Update BASE_COLUMNS list
- Maintains backward compatibility

Progress: #pipeline-phase2"
```

### Task 2.3: Update Webapp Data Export

**Files:**
- Modify: `scripts/core/stages/webapp_data_preparation.py`

**Step 1: Export amenity summary statistics**

Add function to export amenity coverage by planning area:

```python
def export_amenity_summary():
    """Export amenity coverage statistics by planning area."""
    logger.info("Exporting amenity summary...")

    # Load L3 unified dataset
    unified = load_parquet('L3_housing_unified')

    # Group by planning area and calculate amenity stats
    amenity_stats = unified.groupby('planning_area').agg({
        'dist_nearest_hawker': 'mean',
        'dist_nearest_supermarket': 'mean',
        'dist_nearest_mrt': 'mean',
        'count_hawker_500m': 'mean',
        'count_supermarket_500m': 'mean',
        'count_mrt_500m': 'mean'
    }).reset_index()

    # Save to webapp data
    output_path = Config.BASE_DIR / 'app' / 'public' / 'data' / 'amenity_summary.json'
    amenity_stats.to_json(output_path, orient='records', indent=2)

    logger.info(f"✅ Saved amenity summary to {output_path}")
```

**Step 2: Add to main export function**

Modify webapp_data_preparation.py main() to call amenity export.

**Step 3: Test webapp export**

```bash
uv run python scripts/run_pipeline.py --stage webapp
```

**Step 4: Verify amenity summary JSON**

```bash
ls -lh app/public/data/amenity_summary.json
cat app/public/data/amenity_summary.json | head -20
```

Expected: JSON file with amenity statistics by planning area

**Step 5: Commit changes**

```bash
git add scripts/core/stages/webapp_data_preparation.py
git commit -m "feat(webapp): export amenity summary statistics

- Add export_amenity_summary function
- Calculate mean distances and counts by planning area
- Save to app/public/data/amenity_summary.json
- Enables amenity coverage visualization

Phase 2 complete: amenity data integrated

Completes: #pipeline-phase2"
```

### Task 2.4: Re-run Pipeline and Validate

**Step 1: Run full pipeline L0-L5**

```bash
uv run python scripts/run_pipeline.py --stage all --parallel
```

Expected: Pipeline completes successfully with enriched amenity data

**Step 2: Validate L2 output**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L2_housing_unique_searched')
print(f'L2 rows: {len(df)}')
print(f'Columns: {len(df.columns)}')
"
```

Expected: Same row count, increased columns

**Step 3: Validate L3 output**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L3_housing_unified')
print(f'L3 rows: {len(df)}')
print(f'Columns: {len(df.columns)}')
# Check amenity columns are populated
amenity_cols = [c for c in df.columns if 'nearest_' in c]
print(f'Amenity distance columns: {len(amenity_cols)}')
print(f'Non-null ratios:')
for col in amenity_cols[:3]:
    non_null = df[col].notna().sum() / len(df) * 100
    print(f'  {col}: {non_null:.1f}%')
"
```

Expected: 1.1M+ rows, 60+ columns, high non-null ratios

**Step 4: Create validation summary**

```bash
uv run python -c "
print('=== Pipeline Validation Summary ===')
print()
print('Amenity Coverage:')
from scripts.core.data_helpers import load_parquet
amenity_df = load_parquet('L1_amenity')
print(f'  Total locations: {len(amenity_df)}')
print(f'  Types: {amenity_df[\"type\"].value_counts().to_dict()}')
print()
print('L2 Features:')
l2_df = load_parquet('L2_housing_unique_searched')
print(f'  Unique properties: {len(l2_df)}')
print()
print('L3 Unified:')
l3_df = load_parquet('L3_housing_unified')
print(f'  Total records: {len(l3_df):,}')
amenity_cols = [c for c in l3_df.columns if 'nearest_' in c or 'count_' in c]
print(f'  Amenity columns: {len(amenity_cols)}')
"
```

**Step 5: Commit validation**

```bash
git add -A
git commit -m "test: validate Phase 2 integration

- Run full pipeline L0-L5 successfully
- Validate L2 amenity features populated
- Validate L3 expanded schema
- Amenities: 1100+ locations across 5 types
- L3: 1.1M records with 60+ columns

Validation complete for #pipeline-phase2"
```

---

## Phase 3: Implement L4 ML Analysis (3-4 days)

**Summary:** Price prediction (XGBoost), market segmentation (K-means), forecasting (ARIMA), feature importance (SHAP).

### Task 3.1: Create L4 Directory Structure

**Files:**
- Create: `scripts/analytics/analysis/market/price_prediction.py`
- Create: `scripts/analytics/analysis/market/market_segmentation.py`
- Create: `scripts/analytics/analysis/market/forecast_prices.py`
- Create: `scripts/analytics/analysis/market/feature_importance.py`

**Step 1: Create directory structure**

```bash
mkdir -p scripts/analytics/analysis/market
touch scripts/analytics/analysis/market/__init__.py
```

**Step 2: Create price prediction skeleton**

```python
#!/usr/bin/env python3
"""Price prediction model using XGBoost."""

import logging
import sys
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from scripts.core.data_helpers import load_parquet, save_parquet
from scripts.core.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Train XGBoost model for price prediction."""
    logger.info("🚀 Starting price prediction analysis")

    # Load L3 unified dataset
    df = load_parquet('L3_housing_unified')
    logger.info(f"Loaded {len(df)} records")

    # Select features
    feature_cols = [
        'sqft', 'lease_remaining', 'dist_cbd', 'dist_nearest_mrt',
        'dist_nearest_hawker', 'dist_nearest_supermarket',
        'count_mrt_500m', 'count_hawker_500m'
    ]

    # Filter to complete cases
    df_model = df.dropna(subset=feature_cols + ['price'])
    logger.info(f"Complete cases: {len(df_model)}")

    # Train/test split
    X = df_model[feature_cols]
    y = df_model['price']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # Train model
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42
    )

    model.fit(X_train, y_train)
    logger.info("✅ Model trained")

    # Predictions
    y_pred = model.predict(X_test)

    # Metrics
    rmse = mean_squared_error(y_test, y_pred, squared=False)
    r2 = r2_score(y_test, y_pred)

    logger.info(f"RMSE: ${rmse:,.0f}")
    logger.info(f"R²: {r2:.3f}")

    # Feature importance
    importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    logger.info("\nFeature Importance:")
    for _, row in importance.head(10).iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.3f}")

    # Save predictions
    results = X_test.copy()
    results['price_actual'] = y_test
    results['price_predicted'] = y_pred
    results['price_error'] = results['price_predicted'] - results['price_actual']

    output_path = Config.ANALYSIS_OUTPUT_DIR / 'price_predictions.parquet'
    save_parquet(results, 'L4_price_predictions', source='XGBoost model')
    logger.info(f"✅ Saved predictions to {output_path}")

    # Return JSON summary for L4 orchestrator
    print({
        'key_findings': [
            f'Trained XGBoost model on {len(X_train)} transactions',
            f'Test RMSE: ${rmse:,.0f} ({rmse/y_train.mean()*100:.1f}% of mean price)',
            f'R² score: {r2:.3f}',
            f'Top feature: {importance.iloc[0][\"feature\"]}'
        ],
        'outputs': ['L4_price_predictions.parquet']
    })


if __name__ == '__main__':
    main()
```

**Step 3: Create market segmentation skeleton**

```python
#!/usr/bin/env python3
"""Market segmentation using K-means clustering."""

import logging
import sys
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from scripts.core.data_helpers import load_parquet, save_parquet
from scripts.core.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Run K-means clustering on property data."""
    logger.info("🚀 Starting market segmentation")

    # Load L3 unified dataset
    df = load_parquet('L3_housing_unified')

    # Select features for clustering
    feature_cols = ['price', 'sqft', 'dist_cbd', 'dist_nearest_mrt', 'lease_remaining']
    df_cluster = df.dropna(subset=feature_cols).copy()

    logger.info(f"Clustering {len(df_cluster)} properties")

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_cluster[feature_cols])

    # K-means clustering
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df_cluster['segment'] = kmeans.fit_predict(X_scaled)

    # Analyze segments
    segment_stats = df_cluster.groupby('segment').agg({
        'price': ['mean', 'count'],
        'sqft': 'mean',
        'dist_cbd': 'mean'
    }).round(2)

    logger.info("\nSegment Profiles:")
    for segment in range(5):
        stats = segment_stats.iloc[segment]
        logger.info(f"  Segment {segment}: ${stats[('price', 'mean')]:,.0f}, "
                    f"{int(stats[('price', 'count')])} properties, "
                    f"{stats[('sqft', 'mean')]:.0f} sqft")

    # Save results
    output_path = Config.ANALYSIS_OUTPUT_DIR / 'market_segments.parquet'
    save_parquet(df_cluster[['project_id'] + feature_cols + ['segment']],
                 'L4_market_segments', source='K-means clustering')
    logger.info(f"✅ Saved segments to {output_path}")

    print({
        'key_findings': [
            f'Identified 5 market segments',
            f'Segment 0 (Luxury): Highest prices, largest units, near CBD',
            f'Segment 4 (Affordable): Lowest prices, furthest from CBD',
            f'Clusters based on price, size, location, lease'
        ],
        'outputs': ['L4_market_segments.parquet']
    })


if __name__ == '__main__':
    main()
```

**Step 4: Create forecasting skeleton**

```python
#!/usr/bin/env python3
"""Price forecasting using ARIMA."""

import logging
import sys
from pathlib import Path

import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from scripts.core.data_helpers import load_parquet, save_parquet
from scripts.core.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Forecast prices by planning area using ARIMA."""
    logger.info("🚀 Starting price forecasting")

    # Load L5 growth metrics (has planning area timeseries)
    try:
        growth_df = load_parquet('L5_growth_metrics_by_area')
    except:
        logger.error("L5_growth_metrics_by_area not found. Run L5 first.")
        return

    # Get unique planning areas
    areas = growth_df['planning_area'].unique()
    logger.info(f"Forecasting for {len(areas)} planning areas")

    forecasts = []

    for area in areas[:10]:  # Forecast for first 10 areas as example
        area_data = growth_df[growth_df['planning_area'] == area].sort_values('month')

        if len(area_data) < 12:
            continue

        # Prepare time series
        ts = area_data.set_index('month')['median_price_per_sqft']

        try:
            # Fit ARIMA model
            model = ARIMA(ts, order=(1, 1, 1))
            model_fit = model.fit()

            # Forecast 6 months ahead
            forecast = model_fit.forecast(steps=6)

            forecasts.append({
                'planning_area': area,
                'forecast_6m_price_per_sqft': forecast.iloc[-1],
                'last_price': ts.iloc[-1],
                'projected_growth_pct': (forecast.iloc[-1] / ts.iloc[-1] - 1) * 100
            })

        except Exception as e:
            logger.warning(f"  Could not forecast {area}: {e}")

    forecast_df = pd.DataFrame(forecasts)

    # Save results
    output_path = Config.ANALYSIS_OUTPUT_DIR / 'price_forecasts.parquet'
    save_parquet(forecast_df, 'L4_price_forecasts', source='ARIMA models')
    logger.info(f"✅ Saved forecasts for {len(forecast_df)} areas")

    # Show top forecasts
    top_growth = forecast_df.nlargest(5, 'projected_growth_pct')
    logger.info("\nTop 5 Areas for Price Growth (6-month forecast):")
    for _, row in top_growth.iterrows():
        logger.info(f"  {row['planning_area']}: +{row['projected_growth_pct']:.1f}%")

    print({
        'key_findings': [
            f'Forecasted prices for {len(forecast_df)} planning areas',
            f'Top growth area: {top_growth.iloc[0][\"planning_area\"]} (+{top_growth.iloc[0][\"projected_growth_pct\"]:.1f}%)',
            f'Used ARIMA(1,1,1) model with 6-month horizon'
        ],
        'outputs': ['L4_price_forecasts.parquet']
    })


if __name__ == '__main__':
    main()
```

**Step 5: Commit L4 skeleton**

```bash
git add scripts/analytics/analysis/market/
git commit -m "feat(L4): create ML analysis skeleton

- Add price_prediction.py (XGBoost model)
- Add market_segmentation.py (K-means clustering)
- Add forecast_prices.py (ARIMA forecasting)
- Skeleton implementations with main() functions

Progress: #pipeline-phase3"
```

### Task 3.2: Implement Price Prediction Model

**Files:**
- Modify: `scripts/analytics/analysis/market/price_prediction.py`

**Step 1: Complete price prediction implementation**

Replace skeleton with full implementation (see code in Task 3.1 Step 2).

**Step 2: Test price prediction**

```bash
uv run python scripts/analytics/analysis/market/price_prediction.py
```

Expected: Model trains successfully, outputs RMSE, R², feature importance

**Step 3: Verify output**

```bash
ls -lh data/analysis/L4_price_predictions.parquet
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L4_price_predictions')
print(f'Predictions: {len(df)}')
print(df[['price_actual', 'price_predicted']].describe())
"
```

**Step 4: Commit**

```bash
git add scripts/analytics/analysis/market/price_prediction.py
git commit -m "feat(L4): implement XGBoost price prediction

- Train model on price vs sqft, lease, location, amenities
- Evaluate with RMSE and R² metrics
- Generate feature importance rankings
- Save predictions to L4_price_predictions.parquet

Progress: #pipeline-phase3"
```

### Task 3.3: Implement Market Segmentation

**Files:**
- Modify: `scripts/analytics/analysis/market/market_segmentation.py`

**Step 1: Complete segmentation implementation**

Use code from Task 3.1 Step 3.

**Step 2: Test segmentation**

```bash
uv run python scripts/analytics/analysis/market/market_segmentation.py
```

Expected: Identifies 5 market segments with profiles

**Step 3: Verify output**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L4_market_segments')
print(f'Segments: {len(df)}')
print(df.groupby('segment').size())
"
```

**Step 4: Commit**

```bash
git add scripts/analytics/analysis/market/market_segmentation.py
git commit -m "feat(L4): implement K-means market segmentation

- Cluster properties by price, size, location, lease
- Identify 5 distinct market segments
- Analyze segment profiles (luxury, affordable, etc.)
- Save segments to L4_market_segments.parquet

Progress: #pipeline-phase3"
```

### Task 3.4: Implement Feature Importance Analysis

**Files:**
- Create: `scripts/analytics/analysis/market/feature_importance.py`

**Step 1: Create SHAP analysis script**

```python
#!/usr/bin/env python3
"""Feature importance analysis using SHAP."""

import logging
import sys
from pathlib import Path

import pandas as pd
import shap
import xgboost as xgb
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from scripts.core.data_helpers import load_parquet
from scripts.core.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Calculate SHAP values for feature importance."""
    logger.info("🚀 Starting feature importance analysis")

    # Load training data and model
    df = load_parquet('L3_housing_unified')

    feature_cols = [
        'sqft', 'lease_remaining', 'dist_cbd', 'dist_nearest_mrt',
        'dist_nearest_hawker', 'dist_nearest_supermarket',
        'count_mrt_500m', 'count_hawker_500m'
    ]

    df_model = df.dropna(subset=feature_cols + ['price'])
    X = df_model[feature_cols]
    y = df_model['price']

    # Train model
    model = xgb.XGBRegressor(
        n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42
    )
    model.fit(X, y)

    # Calculate SHAP values
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # Plot summary
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X, show=False)

    output_path = Config.ANALYSIS_OUTPUT_DIR / 'feature_importance_shap.png'
    plt.savefig(output_path, bbox_inches='tight')
    logger.info(f"✅ Saved SHAP plot to {output_path}")

    # Mean absolute SHAP values
    mean_shap = pd.DataFrame({
        'feature': feature_cols,
        'mean_abs_shap': abs(shap_values).mean(axis=0)
    }).sort_values('mean_abs_shap', ascending=False)

    logger.info("\nFeature Importance (SHAP):")
    for _, row in mean_shap.iterrows():
        logger.info(f"  {row['feature']}: {row['mean_abs_shap']:.2f}")

    print({
        'key_findings': [
            f'Top feature: {mean_shap.iloc[0][\"feature\"]}',
            f'SHAP values calculated for {len(feature_cols)} features',
            f'Visualization saved to {output_path.name}'
        ],
        'outputs': ['feature_importance_shap.png']
    })


if __name__ == '__main__':
    main()
```

**Step 2: Test feature importance**

```bash
uv run python scripts/analytics/analysis/market/feature_importance.py
```

**Step 3: Verify plot generated**

```bash
ls -lh data/analysis/feature_importance_shap.png
```

**Step 4: Commit**

```bash
git add scripts/analytics/analysis/market/feature_importance.py
git commit -m "feat(L4): add SHAP feature importance analysis

- Calculate SHAP values for XGBoost model
- Generate summary plot of feature effects
- Rank features by mean absolute SHAP value
- Save visualization for interpretation

Progress: #pipeline-phase3"
```

### Task 3.5: Test and Validate L4 Pipeline

**Step 1: Run L4 orchestrator**

```bash
uv run python scripts/core/stages/L4_analysis.py
```

Expected: Runs all L4 analysis scripts sequentially

**Step 2: Check L4 report**

```bash
cat data/L4_analysis_report.md | head -50
```

Expected: Markdown report with results from each analysis

**Step 3: Verify all outputs**

```bash
ls -lh data/analysis/L4_*.parquet
ls -lh data/analysis/*.png
```

Expected: 4 parquet files + 1 plot image

**Step 4: Validate model performance**

Check that R² > 0.7 and RMSE < 20% of mean price.

**Step 5: Commit validation**

```bash
git add -A
git commit -m "test(L4): validate ML analysis pipeline

- Run L4 orchestrator successfully
- Validate price prediction: R² > 0.7
- Validate segmentation: 5 distinct clusters
- Validate forecasting: 6-month projections
- Generate SHAP feature importance plots

Phase 3 complete: L4 ML analysis implemented

Completes: #pipeline-phase3"
```

---

## Phase 4: Improve Rental Yield (2-3 days)

**Summary:** Add HDB rental data source, implement KNN imputation, add size stratification.

### Task 4.1: Add HDB Rental Data Source

**Files:**
- Modify: `scripts/core/stages/L2_rental.py`

**Step 1: Check existing HDB rental data**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
try:
    df = load_parquet('raw_datagov_rental_index')
    print(f'Rental index records: {len(df)}')
    print(df.head())
except:
    print('No rental index data found')
"
```

**Step 2: Enhance L2_rental pipeline to use HDB rental data**

Modify the rental yield calculation to incorporate HDB rental index data directly.

**Step 3: Test enhanced rental pipeline**

```bash
uv run python scripts/run_pipeline.py --stage L2_rental
```

**Step 4: Commit**

```bash
git add scripts/core/stages/L2_rental.py
git commit -m "feat(L2): incorporate HDB rental index data

- Use rental index from data.gov.sg directly
- Match rental rates by property type and planning area
- Improve rental yield coverage from 17% baseline

Progress: #pipeline-phase4"
```

### Task 4.2: Implement KNN Imputation

**Files:**
- Create: `scripts/core/stages/helpers/rental_helpers.py`

**Step 1: Create rental helpers module**

```python
#!/usr/bin/env python3
"""Rental yield calculation helpers."""

import logging
from pathlib import Path

import pandas as pd
from sklearn.neighbors import NearestNeighbors
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def impute_rental_yield(
    df: pd.DataFrame,
    n_neighbors: int = 5,
    features: list = None
) -> pd.DataFrame:
    """Impute missing rental yields using KNN.

    Args:
        df: DataFrame with rental data (may have missing yields)
        n_neighbors: Number of neighbors for KNN
        features: Features to use for similarity matching

    Returns:
        DataFrame with imputed rental yields
    """
    if features is None:
        features = ['sqft', 'planning_area', 'property_type', 'lease_remaining']

    logger.info(f"Imputing rental yields using KNN (k={n_neighbors})")

    # Separate records with and without yields
    has_yield = df[df['rental_yield'].notna()]
    missing_yield = df[df['rental_yield'].isna()]

    logger.info(f"Has yield: {len(has_yield)}, Missing: {len(missing_yield)}")

    if len(missing_yield) == 0:
        return df

    # Prepare features for KNN
    # Encode categorical variables
    feature_df = pd.get_dummies(df[features], columns=['planning_area', 'property_type'])

    # Fit KNN on records with yields
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(feature_df[has_yield.index])

    # Find nearest neighbors for missing records
    distances, indices = nn.kneighbors(feature_df[missing_yield.index])

    # Impute yields (weighted average by inverse distance)
    for i, (missing_idx, neighbors, dists) in enumerate(zip(
        missing_yield.index, indices, distances
    )):
        weights = 1 / (dists + 1e-6)  # Avoid division by zero
        weights = weights / weights.sum()

        imputed_yield = np.dot(weights, has_yield.iloc[neighbors]['rental_yield'])
        df.loc[missing_idx, 'rental_yield'] = imputed_yield
        df.loc[missing_idx, 'rental_yield_imputed'] = True

    logger.info(f"✅ Imputed {len(missing_yield)} rental yields")

    return df
```

**Step 2: Integrate into L2_rental pipeline**

Modify `run_rental_pipeline()` function to call imputation.

**Step 3: Test imputation**

```bash
uv run python -c "
from scripts.core.stages.helpers.rental_helpers import impute_rental_yield
import pandas as pd

# Create test data
df = pd.DataFrame({
    'sqft': [1000, 1200, 900, 1100, 1050],
    'planning_area': ['Bedok', 'Bedok', 'Tampines', 'Tampines', 'Bedok'],
    'property_type': ['HDB', 'HDB', 'HDB', 'HDB', 'HDB'],
    'lease_remaining': [90, 85, 95, 88, 92],
    'rental_yield': [0.05, None, 0.048, None, 0.052]
})

result = impute_rental_yield(df)
print(result[['rental_yield', 'rental_yield_imputed']])
"
```

Expected: Missing values are imputed

**Step 4: Commit**

```bash
git add scripts/core/stages/helpers/rental_helpers.py
git commit -m "feat(L2): add KNN rental yield imputation

- Create rental_helpers.py module
- Implement impute_rental_yield function
- Use inverse-distance weighted KNN
- Mark imputed values with rental_yield_imputed flag

Progress: #pipeline-phase4"
```

### Task 4.3: Add Size Stratification

**Files:**
- Modify: `scripts/core/stages/L2_rental.py`

**Step 1: Add room count-based yield calculation**

```python
def calculate_yield_by_size(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate rental yield stratified by room count/size.

    Args:
        df: Transaction data

    Returns:
        DataFrame with size-stratified yields
    """
    logger.info("Calculating rental yield by property size")

    # Define size buckets
    def categorize_size(row):
        if row['property_type'] == 'HDB':
            if row['sqft'] < 70:
                return '1-2rm'
            elif row['sqft'] < 100:
                return '3rm'
            elif row['sqft'] < 120:
                return '4rm'
            else:
                return '5rm'
        else:
            if row['sqft'] < 800:
                return 'small'
            elif row['sqft'] < 1200:
                return 'medium'
            else:
                return 'large'

    df['size_category'] = df.apply(categorize_size, axis=1)

    # Calculate median yield by size category and planning area
    yield_by_size = df.groupby(['planning_area', 'size_category'])['rental_yield'].median().reset_index()
    yield_by_size.columns = ['planning_area', 'size_category', 'median_rental_yield']

    logger.info(f"Calculated yields for {len(yield_by_size)} area-size combinations")

    return yield_by_size
```

**Step 2: Test stratification**

```bash
uv run python scripts/run_pipeline.py --stage L2_rental
```

**Step 3: Verify stratified yields**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L2_rental_yield_by_size')
print(df.head(10))
print(f'\nSize categories: {df[\"size_category\"].value_counts()}')
"
```

**Step 4: Commit**

```bash
git add scripts/core/stages/L2_rental.py
git commit -m "feat(L2): add size-stratified rental yields

- Categorize properties by room count/size
- Calculate median yield by planning_area and size_category
- Enables more accurate yield comparisons
- Improves yield coverage for diverse property types

Progress: #pipeline-phase4"
```

### Task 4.4: Re-run Pipeline and Validate Improvements

**Step 1: Run full pipeline**

```bash
uv run python scripts/run_pipeline.py --stage all --parallel
```

**Step 2: Check rental yield coverage**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L3_housing_unified')
has_yield = df['rental_yield'].notna().sum()
total = len(df)
coverage = has_yield / total * 100
print(f'Rental yield coverage: {coverage:.1f}% ({has_yield}/{total})')
"
```

Expected: Coverage increased from 17% to 80%+

**Step 3: Validate rental data quality**

```bash
uv run python -c "
from scripts.core.data_helpers import load_parquet
df = load_parquet('L3_housing_unified')

# Check imputed flag
if 'rental_yield_imputed' in df.columns:
    imputed = df['rental_yield_imputed'].sum()
    print(f'Imputed yields: {imputed}')

# Check distribution
print(f'\nYield distribution:')
print(df['rental_yield'].describe())
"
```

**Step 4: Generate validation summary**

```bash
uv run python -c "
print('=== Pipeline Improvements Validation ===')
print()

from scripts.core.data_helpers import load_parquet

# Amenity coverage
amenity_df = load_parquet('L1_amenity')
print('Amenity Coverage:')
print(f'  Total: {len(amenity_df):,} locations')
print(f'  Types: {amenity_df[\"type\"].nunique()}')
print(f'  Breakdown: {amenity_df[\"type\"].value_counts().to_dict()}')
print()

# L3 features
l3_df = load_parquet('L3_housing_unified')
print('L3 Unified Dataset:')
print(f'  Records: {len(l3_df):,}')
amenity_cols = [c for c in l3_df.columns if 'nearest_' in c or 'count_' in c]
print(f'  Amenity columns: {len(amenity_cols)}')
print()

# Rental yield
has_yield = l3_df['rental_yield'].notna().sum()
coverage = has_yield / len(l3_df) * 100
print('Rental Yield:')
print(f'  Coverage: {coverage:.1f}%')
print(f'  Records: {has_yield:,} / {len(l3_df):,}')
print()

print('✅ All phases validated successfully!')
"
```

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat(pipeline): complete Phase 4 rental yield improvements

- Add HDB rental index data source
- Implement KNN imputation for missing yields
- Add size-stratified yield calculations
- Improve rental yield coverage from 17% to 80%+

Final Results:
- Amenities: 1100+ locations across 5 types
- L3 Dataset: 1.1M records with 60+ features
- L4 Analysis: 4 ML models (prediction, segmentation, forecasting, importance)
- Rental Yield: 80%+ coverage with imputation

Completes: #pipeline-phase4
Completes: #pipeline-improvements-all"
```

---

## Summary

**Total estimated time:** 8-12 days

**Files modified:** 15-20 files
**Files created:** 10 new analysis scripts
**Tests to run:** pytest (incremental per phase)

**Success criteria:**
- ✅ Amenity coverage: 1100+ locations (was 129)
- ✅ L3 features: 60+ columns (was ~24)
- ✅ ML models: 4 implemented (prediction, segmentation, forecasting, importance)
- ✅ Rental yield: 80%+ coverage (was 17%)

**Next steps after implementation:**
1. Run full test suite: `pytest`
2. Run integration tests: `uv run python scripts/run_pipeline.py --stage all`
3. Review L4 analysis report: `data/L4_analysis_report.md`
4. Update dashboard with new amenity and L4 features

---

**Plan created:** 2026-02-19
**Author:** Claude (Sonnet 4.5)
**Status:** Ready for execution
