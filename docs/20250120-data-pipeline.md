# Data Pipeline Documentation

**Last Updated**: 2025-01-20
**Status**: ✅ Operational

---

## Overview

The Egg-n-Bacon-Housing data pipeline collects, processes, and engineers features from Singapore housing data sources. This document provides detailed information about each pipeline level, data sources, transformations, and outputs.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      L0: Data Collection                    │
│  External APIs → Raw Parquet Files + Metadata              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                     L1: Data Processing                     │
│  Raw Data → Cleaned & Standardized Parquet Files           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   L2: Feature Engineering                   │
│  Processed Data → Feature-Rich Parquet Files               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                       L3: Export                            │
│  Feature Data → S3 / Supabase / Applications               │
└─────────────────────────────────────────────────────────────┘
```

---

## L0: Data Collection

### Purpose
Collect raw data from external government APIs and web sources.

### Data Sources

#### 1. data.gov.sg API
**Notebooks**: `L0_datagovsg.ipynb`

**Datasets Collected**:
- `raw_datagov_general_sale` - General property sale statistics
- `raw_datagov_rental_index` - Rental price indices over time
- `raw_datagov_price_index` - Property price indices
- `raw_datagov_median_price_by_property_type` - Median prices by property type
- `raw_datagov_private_transactions_property_type` - Private property transactions
- `raw_datagov_resale_flat_2015_2016` - HDB resale flats (2015-2016)
- `raw_datagov_resale_flat_2017_onwards` - HDB resale flats (2017+)
- `raw_datagov_resale_flat_price_2017onwards` - HDB resale prices (2017+)
- `raw_datagov_resale_flat_price_2015_2016_api` - HDB resale prices via API

**API Endpoint**: `https://data.gov.sg/api/action/datastore_search`

**Update Frequency**: Monthly

**Data Volume**: ~100K rows per dataset

#### 2. OneMap API
**Notebooks**: `L0_onemap.ipynb`

**Datasets Collected**:
- `raw_onemap_planning_area_names` - Singapore planning areas
- `raw_onemap_household_income` - Household income by planning area

**API Authentication**: Email/password required

**API Endpoints**:
- Planning Area Search: `https://www.onemap.gov.sg/apis/planning-area`
- Household Income: `https://www.onemap.gov.sg/api/public/popapi/getHouseholdIncome`

**Update Frequency**: Quarterly

**Data Volume**: ~50 rows per dataset

#### 3. Wikipedia Scraping
**Notebooks**: `L0_wiki.ipynb`

**Datasets Collected**:
- `raw_wiki_shopping_mall` - Singapore shopping malls list

**Source**: Wikipedia page scraping

**Update Frequency**: As needed (manual)

**Data Volume**: ~200 rows

### Output Format

All L0 datasets are saved as parquet files with the following structure:
```python
{
    "dataset_name": "raw_<source>_<data_type>",
    "rows": <count>,
    "created": "<timestamp>",
    "source": "<API or website>",
    "checksum": "<sha256>"
}
```

### Metadata Tracking

All datasets are tracked in `data/metadata.json`:
```json
{
    "raw_datagov_general_sale": {
        "path": "raw_data/raw_datagov_general_sale.parquet",
        "version": "2025-01-20",
        "rows": 15000,
        "created": "2025-01-20T10:00:00Z",
        "source": "data.gov.sg API",
        "checksum": "abc123...",
        "mode": "overwrite"
    }
}
```

### Error Handling

- **API failures**: Logged, retry with exponential backoff
- **Empty responses**: Warning logged, empty dataset created
- **Malformed data**: Error logged, notebook stops

---

## L1: Data Processing

### Purpose
Clean, standardize, and transform raw data into analysis-ready formats.

### Processing Steps

#### 1. URA Transaction Processing
**Notebooks**: `L1_ura_transactions_processing.ipynb`

**Input**: CSV files from URA (Urban Redevelopment Authority)

**Outputs**:
- `L1_housing_ec_transaction` - Executive condo transactions
- `L1_housing_condo_transaction` - Private condominium transactions
- `L1_housing_hdb_transaction` - HDB transactions

**Transformations**:
- Column name standardization
- Data type conversion
- Date parsing and standardization
- Price per sqft calculation
- Geocoding (if applicable)
- Duplicate removal
- Outlier detection and filtering

**Quality Checks**:
- No null critical fields (price, date, property_id)
- Valid date ranges
- Positive prices
- Unique property IDs

#### 2. Utilities Processing
**Notebooks**: `L1_utilities_processing.ipynb`

**Input**: Raw data from L0, OneMap API queries

**Outputs**:
- `L1_school_queried` - Schools with geospatial data
- `L1_mall_queried` - Shopping malls with geospatial data
- `L1_waterbody` - Water bodies in Singapore
- `L1_amenity` - General amenities

**Transformations**:
- Geospatial queries (lat/lng → postal code, planning area)
- Distance calculations
- Category standardization
- Address parsing
- Data enrichment from multiple sources

**API Calls**:
- OneMap Geocoding API
- OneMap Reverse Geocoding API

**Rate Limiting**:
- 1 request per second (respectful API usage)
- Retry on 429 (Too Many Requests)

### Data Schema Examples

#### Transaction Data (L1)
```python
{
    "transaction_id": "str",
    "property_type": "str",  # condo, ec, hdb
    "price": "float64",
    "price_per_sqft": "float64",
    "date": "datetime64",
    "postal_code": "int",
    "planning_area": "str",
    "floor_size": "float64",
    "lease_remaining": "int",  # years
    "source": "str"  # URA, HDB resale, etc.
}
```

#### Amenity Data (L1)
```python
{
    "amenity_id": "str",
    "name": "str",
    "category": "str",  # school, mall, mrt, etc.
    "latitude": "float64",
    "longitude": "float64",
    "postal_code": "int",
    "planning_area": "str",
    "address": "str"
}
```

---

## L2: Feature Engineering

### Purpose
Create features for machine learning and analysis from processed data.

### Feature Categories

#### 1. Property Features
**Notebooks**: `L2_sales_facilities.ipynb`

**Input**: L1 transaction data, L1 amenity data

**Outputs**:
- `L3_property` - Enhanced property data with features
- `L3_private_property_facilities` - Private property facilities
- `L3_property_nearby_facilities` - Nearby amenities counts
- `L3_property_transactions_sales` - Transaction sales data
- `L3_property_listing_sales` - Listing sales data

**Features Created**:
- Distance to nearest MRT station
- Number of schools within 1km
- Number of malls within 1km
- Distance to CBD
- Planning area average income
- Age of property
- Freehold vs leasehold
- Remaining lease years

#### 2. Distance Features
**Calculations**:
- Haversine distance for lat/lng
- Walking distance (via OneMap routing API, optional)
- Driving distance (via OneMap routing API, optional)

#### 3. Aggregation Features
**By Planning Area**:
- Average price per sqft
- Median transaction volume
- Price growth rate
- Rental yield

**By Time Period**:
- Monthly transaction counts
- Quarterly price indices
- Year-over-year changes

### Feature Engineering Pipeline

```
L1 Data
    ↓
Geospatial Join (properties ↔ amenities)
    ↓
Distance Calculations (within 1km, 2km, 5km)
    ↓
Aggregation (counts, averages, min/max)
    ↓
Temporal Features (month, year, day of week)
    ↓
Interaction Features (price × distance, etc.)
    ↓
L2/L3 Data
```

### Feature Selection

**Used for Modeling**:
- Distance to MRT (top predictor)
- Planning area (categorical)
- Property type (categorical)
- Floor size
- Lease remaining years
- Age of property
- Nearby school count

**Dropped**:
- Redundant features (high correlation >0.95)
- Low variance features (<1% variance)
- Leakage features (future information)

---

## L3: Export

### Purpose
Export processed and feature-engineered data to external systems.

### Export Destinations

#### 1. S3 (Amazon Simple Storage Service)
**Notebooks**: `L3_upload_s3.ipynb`

**Purpose**: Backup and archival

**Buckets**:
- `egg-n-bacon-housing-raw` - Raw data backups
- `egg-n-bacon-housing-processed` - Processed data
- `egg-n-bacon-housing-features` - Feature-engineered data

**Upload Process**:
```python
import boto3

s3 = boto3.client('s3')
s3.upload_file(
    local_path,
    bucket_name,
    s3_path,
    ExtraArgs={'ServerSideEncryption': 'AES256'}
)
```

**Frequency**: After each successful notebook run

#### 2. Supabase (PostgreSQL Database)
**Purpose**: Production database for applications

**Tables**:
- `properties` - Master property table
- `transactions` - Transaction records
- `amenities` - Amenity locations
- `property_features` - Feature table

**Schema**:
```sql
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id VARCHAR(255) UNIQUE NOT NULL,
    property_type VARCHAR(50),
    price NUMERIC,
    price_per_sqft NUMERIC,
    floor_size NUMERIC,
    latitude NUMERIC,
    longitude NUMERIC,
    postal_code INTEGER,
    planning_area VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Upload Process**:
```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
data = df.to_dict('records')
response = supabase.table('properties').upsert(data).execute()
```

**Frequency**: Daily or on-demand

---

## Running the Pipeline

### Prerequisites

1. **Environment Setup**:
   ```bash
   uv sync
   cp .env.example .env
   # Edit .env with API keys
   ```

2. **Required API Keys**:
   - `ONEMAP_EMAIL` - For OneMap API
   - `ONEMAP_EMAIL_PASSWORD` - For OneMap API
   - `GOOGLE_API_KEY` - For LangChain agents
   - `SUPABASE_URL` - For Supabase export (optional)
   - `SUPABASE_KEY` - For Supabase export (optional)

### Execution Order

Run notebooks in order:

1. **L0: Data Collection**
   ```bash
   uv run jupyter notebook notebooks/L0_datagovsg.ipynb
   uv run jupyter notebook notebooks/L0_onemap.ipynb
   uv run jupyter notebook notebooks/L0_wiki.ipynb
   ```

2. **L1: Data Processing**
   ```bash
   uv run jupyter notebook notebooks/L1_ura_transactions_processing.ipynb
   uv run jupyter notebook notebooks/L1_utilities_processing.ipynb
   ```

3. **L2: Feature Engineering**
   ```bash
   uv run jupyter notebook notebooks/L2_sales_facilities.ipynb
   ```

4. **L3: Export** (Optional)
   ```bash
   uv run jupyter notebook notebooks/L3_upload_s3.ipynb
   ```

### Using the Paired .py Files

Alternatively, edit and run the .py files directly:

```bash
# Edit the file
code notebooks/L0_datagovsg.py

# Run the file
uv run python notebooks/L0_datagovsg.py

# Sync back to .ipynb
cd notebooks
uv run jupytext --sync L0_datagovsg.ipynb
```

---

## Data Quality & Validation

### Validation Checks

#### L0 Validation
- ✅ API response is valid JSON
- ✅ Expected fields are present
- ✅ No duplicate records
- ✅ File checksum matches

#### L1 Validation
- ✅ No null critical fields
- ✅ Valid date ranges
- ✅ Positive prices
- ✅ Valid lat/lng coordinates
- ✅ Geocoding success rate >95%

#### L2 Validation
- ✅ No negative distances
- ✅ Feature counts non-negative
- ✅ No infinite values
- ✅ Correlation matrix sanity check

#### L3 Validation
- ✅ S3 upload successful
- ✅ Supabase insert successful
- ✅ Record counts match

### Monitoring

**Track in `data/metadata.json`**:
- Dataset versions
- Checksums for integrity
- Row counts
- Timestamps
- Source lineage

**Alert on**:
- Checksum mismatches
- Missing files
- Drastic row count changes (>50%)
- Failed API calls

---

## Performance Optimization

### Parquet Optimization

**Column Pruning**:
```python
# Only load needed columns
df = pd.read_parquet(path, columns=['col1', 'col2', 'col3'])
```

**Filter Pushdown**:
```python
# Filter before loading
df = pd.read_parquet(path, filters=[('year', '>=', 2020)])
```

**Compression**:
- Using `snappy` compression (default)
- Balance between speed and size
- 50-70% compression ratio

### API Optimization

**Caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def geocode(postal_code):
    # Cached geocoding
    ...
```

**Batching**:
- Process 1000 records at a time
- Parallel processing where possible
- Rate limiting to respect API limits

---

## Troubleshooting

### Common Issues

#### 1. API Rate Limiting
**Error**: `429 Too Many Requests`

**Solution**:
- Increase delay between requests
- Check API quota limits
- Use exponential backoff

#### 2. Memory Issues
**Error**: `MemoryError` or notebook kernel crash

**Solution**:
- Process data in chunks
- Use `chunksize` parameter in pandas
- Close unused datasets

#### 3. Geocoding Failures
**Error**: `Failed to geocode postal code`

**Solution**:
- Check OneMap API status
- Verify postal code format
- Use cached results where possible

#### 4. File Not Found
**Error**: `FileNotFoundError: Parquet file not found`

**Solution**:
- Run preceding notebooks first
- Check `data/metadata.json` for dependencies
- Verify dataset was created successfully

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check dataset metadata:
```python
from src.data_helpers import list_datasets
datasets = list_datasets()
print(datasets)
```

Verify file integrity:
```python
from src.data_helpers import verify_metadata
is_valid = verify_metadata()
print(f"All datasets valid: {is_valid}")
```

---

## Maintenance

### Regular Tasks

**Weekly**:
- Run L0 notebooks to fetch latest data
- Check for API changes
- Monitor data quality

**Monthly**:
- Run full pipeline (L0→L3)
- Update feature engineering
- Review and optimize slow queries

**Quarterly**:
- Review and update documentation
- Clean up old data versions
- Performance tuning

### Data Retention

**Raw Data (L0)**: Keep 1 year
**Processed Data (L1)**: Keep 6 months
**Feature Data (L2/L3)**: Keep 3 months
**Backups (S3)**: Keep indefinitely

---

## Related Documentation

- **Architecture**: `docs/20250120-architecture.md`
- **Migration**: `docs/20250120-parquet-migration-design.md`
- **Progress**: `docs/progress/20250120-dvc-to-parquet-migration-progress.md`
- **Development**: `CLAUDE.md`

---

## Appendix: Dataset Reference

### Complete Dataset List

#### L0 Datasets (Raw)
1. `raw_datagov_general_sale`
2. `raw_datagov_rental_index`
3. `raw_datagov_price_index`
4. `raw_datagov_median_price_by_property_type`
5. `raw_datagov_private_transactions_property_type`
6. `raw_datagov_resale_flat_2015_2016`
7. `raw_datagov_resale_flat_2017_onwards`
8. `raw_datagov_resale_flat_price_2017onwards`
9. `raw_datagov_resale_flat_price_2015_2016_api`
10. `raw_onemap_planning_area_names`
11. `raw_onemap_household_income`
12. `raw_wiki_shopping_mall`

#### L1 Datasets (Processed)
1. `L1_housing_ec_transaction`
2. `L1_housing_condo_transaction`
3. `L1_housing_hdb_transaction`
4. `L2_housing_unique_full_searched`
5. `L2_housing_unique_searched`
6. `L1_school_queried`
7. `L1_mall_queried`
8. `L1_waterbody`
9. `L1_amenity`

#### L2/L3 Datasets (Features)
1. `L3_property`
2. `L3_private_property_facilities`
3. `L3_property_nearby_facilities`
4. `L3_property_transactions_sales`
5. `L3_property_listing_sales`

---

**Last Updated**: 2025-01-20
**Maintained By**: Development Team
