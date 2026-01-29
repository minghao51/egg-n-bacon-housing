# Analytics Scripts

This directory contains all analytics-related scripts for the Singapore housing market analysis system.

## Structure

### `calculate/`
Metrics calculation scripts that compute various market indicators and indices.

- **calculate_l3_metrics.py** - Calculate L3 housing market metrics (price growth, PSF, volume, momentum)
- **calculate_affordability.py** - Compute affordability index by planning area
- **calculate_income_estimates.py** - Estimate household income using HDB loan eligibility data
- **calculate_coming_soon_metrics.py** - Calculate metrics for upcoming launches
- **calculate_condo_amenities.py** - Calculate amenity features for condominiums

**Usage:**
```bash
# Calculate market metrics
uv run python scripts/analytics/calculate/calculate_l3_metrics.py

# Calculate affordability
uv run python scripts/analytics/calculate/calculate_affordability.py
```

### `forecast/`
Time-series forecasting scripts for predicting future market trends.

- **forecast_prices.py** - Forecast housing prices using Prophet (6-month and 1-year horizons)
- **forecast_yields.py** - Forecast rental yields for different planning areas

**Usage:**
```bash
# Forecast prices
uv run python scripts/analytics/forecast/forecast_prices.py

# Forecast yields
uv run python scripts/analytics/forecast/forecast_yields.py
```

### `segmentation/`
Market segmentation scripts that create property classifications and clusters.

- **create_market_segmentation.py** - Create price tier classifications (Mass Market, Mid-Tier, Luxury)
- **create_period_segmentation.py** - Create period-dependent market segmentation (5-year buckets)
- **quick_cluster_profiles.py** - Generate cluster profiles for market segments

**Usage:**
```bash
# Create market segmentation
uv run python scripts/analytics/segmentation/create_market_segmentation.py

# Create period segmentation
uv run python scripts/analytics/segmentation/create_period_segmentation.py
```

### `analysis/`
In-depth analytical scripts organized by focus area.

#### `analysis/spatial/`
Spatial analysis and geospatial clustering.

- **analyze_spatial_hotspots.py** - Identify price hotspots and coldspots
- **analyze_spatial_autocorrelation.py** - Analyze spatial autocorrelation in prices
- **analyze_h3_clusters.py** - H3 grid-based spatial clustering analysis

#### `analysis/amenity/`
Amenity impact analysis on property prices.

- **analyze_amenity_impact.py** - Analyze amenity impact on prices (temporal, within-town, grid-based)
- **analyze_feature_importance.py** - ML-based feature importance analysis

#### `analysis/market/`
Broad market trend analysis.

- **analyze_hdb_rental_market.py** - HDB rental market analysis
- **analyze_lease_decay.py** - Lease decay impact analysis
- **analyze_policy_impact.py** - Government policy impact assessment
- **market_segmentation_advanced.py** - Advanced market segmentation techniques

#### `analysis/mrt/`
MRT station impact analysis.

- **analyze_mrt_impact.py** - Overall MRT proximity impact on prices
- **analyze_mrt_heterogeneous.py** - Heterogeneous MRT effects across property types
- **analyze_mrt_by_property_type.py** - MRT impact by property type

## Common Patterns

All analytics scripts follow these conventions:

1. **Import paths**: Use relative imports from project root
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent))
   from core.config import Config
   ```

2. **Logging**: Configure logging for output
   ```python
   import logging
   logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
   ```

3. **Output**: Save results to `data/analysis/` or `data/forecasts/`

## Dependencies

- `pandas`, `numpy` - Data manipulation
- `prophet` - Time-series forecasting
- `scikit-learn` - Machine learning
- `plotly` - Visualization
- `statsmodels` - Statistical analysis

## Running Scripts

From project root:
```bash
# Calculate metrics
uv run python scripts/analytics/calculate/calculate_l3_metrics.py

# Run forecast
uv run python scripts/analytics/forecast/forecast_prices.py

# Create segmentation
uv run python scripts/analytics/segmentation/create_market_segmentation.py

# Run analysis
uv run python scripts/analytics/analysis/spatial/analyze_spatial_hotspots.py
```

## Output Locations

- **Metrics**: `data/analysis/`
- **Forecasts**: `data/forecasts/`
- **Segmentations**: `data/analysis/market_segmentation/`
- **Analysis results**: `data/analysis/`

## Related Documentation

- [Architecture Documentation](../../docs/architecture.md)
- [Quick Start Guide](../../docs/guides/quick-start.md)
- [Data Reference](../../docs/guides/data-reference.md)
