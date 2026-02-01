# Analytics Scripts

This directory contains analytical functions and modules for the Singapore housing market analysis system.

**Note:** Pipeline scripts (executable scripts with `main()` functions) are located in `scripts/analytics/pipelines/`. This directory contains analytical functions and modules.

## Structure

### `analysis/`
In-depth analytical functions organized by focus area.

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

## Running Analysis Scripts

From project root:
```bash
# Run spatial analysis
uv run python scripts/analytics/analysis/spatial/analyze_spatial_hotspots.py

# Run amenity impact analysis
uv run python scripts/analytics/analysis/amenity/analyze_amenity_impact.py

# Run market analysis
uv run python scripts/analytics/analysis/market/analyze_hdb_rental_market.py
```

## Running Pipeline Scripts

Analytics pipelines (executable scripts) are located in `scripts/analytics/pipelines/`:

```bash
# Forecast prices
uv run python scripts/analytics/pipelines/forecast_prices_pipeline.py

# Calculate affordability
uv run python scripts/analytics/pipelines/calculate_affordability_pipeline.py

# Generate cluster profiles
uv run python scripts/analytics/pipelines/cluster_profiles_pipeline.py
```

See `scripts/PIPELINE_GUIDE.md` for complete pipeline documentation.

## Common Patterns

All analytics functions follow these conventions:

1. **Import paths**: Use relative imports from project root
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent))
   from scripts.core.config import Config
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

## Output Locations

- **Analysis results**: `data/analysis/`
- **Forecasts**: `data/forecasts/`
- **Segmentations**: `data/analysis/market_segmentation/`

## Related Documentation

- [Pipeline Guide](../PIPELINE_GUIDE.md)
- [Architecture Documentation](../../docs/architecture.md)
- [Quick Start Guide](../../docs/guides/quick-start.md)
- [Data Reference](../../docs/guides/data-reference.md)
