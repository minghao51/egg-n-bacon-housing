# Pipeline Progress Report
**Date:** 2026-01-21
**Project:** egg-n-bacon-housing (Singapore Housing Data Pipeline)

---

## Executive Summary

The data pipeline execution is **approximately 40% complete**, with the **L0 (Data Collection) stage fully completed** and partial progress on L1 (Data Processing). The pipeline successfully collected **980,969 rows** of housing data across 8 datasets from data.gov.sg, OneMap API, and Wikipedia.

**Key Blockers:**
1. **L1 URA Transactions** - Geocoding 12,166 unique addresses would require 10-33 hours due to API rate limiting
2. **L1 Utilities/Amenities** - Missing source files (GeoJSON, CSV) required for school/mall/kindergarten data
3. **L2 Feature Engineering** - Blocked by missing L1 dependencies

**Recommendation:** Prioritize obtaining missing source files and consider alternative geocoding strategies (caching, batch processing, or third-party services).

---

## 1. ✅ COMPLETED: L0 Data Collection Stage

### Datasets Successfully Created

| Dataset | Rows | Description | Source |
|---------|------|-------------|--------|
| `raw_datagov_resale_flat_all` | 969,748 | HDB resale flat prices (1990-2025) | data.gov.sg API (5 CSV files) |
| `raw_datagov_resale_flat_price_2015_2016_api` | 9,200 | HDB resale API data (2015-2016) | data.gov.sg API |
| `raw_datagov_private_transactions_property_type` | 416 | Private property transactions by type | data.gov.sg API |
| `raw_datagov_general_sale` | 348 | General sale data | data.gov.sg API |
| `raw_datagov_rental_index` | 505 | Rental index data | data.gov.sg API |
| `raw_datagov_price_index` | 609 | Price index data | data.gov.sg API |
| `raw_datagov_median_price_via_property_type` | 30 | Median prices by property type | data.gov.sg API |
| `raw_wiki_shopping_mall` | 113 | Shopping malls in Singapore | Wikipedia scraping |

**Total:** 980,969 rows across 8 datasets

### Spatial Data Created
- `onemap_planning_area_polygon.shp` (628 KB) - 55 planning areas with geometry
- `onemap_planning_area_polygon.geojson` (1.2 MB) - Same data in GeoJSON format

### Technical Fixes Applied

#### 1. OneMap API Authentication
**Issue:** Initial authentication attempts failing with email/password credentials
**Solution:**
- Updated all notebooks (L0_onemap, L1_utilities, L1_ura, L2_sales) to use existing valid token from `.env`
- Added JWT expiration checking before attempting to get new token
- Implemented graceful fallback if token needs refresh

**Files Modified:**
- `notebooks/L0_onemap.py` (lines 117-108)
- `notebooks/L1_utilities_processing.py` (lines 45-99)
- `notebooks/L1_ura_transactions_processing.py` (lines 183-234)
- `notebooks/L2_sales_facilities.py` (lines 41-95)

#### 2. API Year Parameter Validation
**Issue:** OneMap API rejected `year=2024` and `year=2023` parameters
**Solution:**
- Changed to `year=2019` (API only accepts: 1998, 2008, 2014, 2019)
**File Modified:** `notebooks/L0_onemap.py` (lines 117, 141)

#### 3. Wikipedia Scraping Blocked
**Issue:** Wikipedia returning 403 Forbidden errors
**Solution:**
- Added User-Agent header to mimic browser request
**File Modified:** `notebooks/L0_wiki.py` (lines 36-41)

#### 4. Empty DataFrame Handling
**Issue:** `pd.concat()` failing when API returns no data
**Solution:**
- Added empty list checks before concatenating
- Conditional saving: only save if DataFrame is not empty
**Files Modified:**
- `notebooks/L0_datagovsg.py` (lines 84-90, 106-157, 232-233)

#### 5. File Path Resolution
**Issue:** Relative paths not working when notebooks run from project root
**Solution:**
- Changed to `pathlib.Path(__file__).parent.parent / 'data'` pattern
- Created directories if they don't exist with `mkdir(parents=True, exist_ok=True)`
**Files Modified:**
- All notebooks for consistent path handling
- `notebooks/L0_onemap.py` (lines 130-134)

---

## 2. ⚠️ PARTIALLY COMPLETED: L1 Data Processing Stage

### L1 URA Transactions Processing

**Status:** Notebook execution started but **interrupted** due to excessive geocoding time

**What Worked:**
- Successfully loaded 14 URA CSV files:
  - EC (Executive Condominium) transactions: 2 files
  - Condo transactions: 5 files
  - Residential transactions: 7 files
  - HDB resale files: 5 files

**What Was Blocked:**
- Geocoding 12,166 unique addresses via OneMap API
- Estimated time: 10-33 hours (with rate limiting: 5-10 seconds per API call)

**Files Loaded:**
```
data/raw_data/csv/ura/
├── URA_ResidentialTransaction_EC2020_20240917220317.csv
├── URA_ResidentialTransaction_EC2021_20240917220358.csv
├── URA_ResidentialTransaction_Conda2020_20240917220234.csv
├── URA_ResidentialTransaction_Conda2021_20240917220149.csv
├── URA_ResidentialTransaction_Conda2022_20240917220116.csv
├── URA_ResidentialTransaction_Conda2023_20240917215948.csv
├── URA_ResidentialTransaction_Condo2024_20240917215852.csv
├── ResidentialTransaction20260121005130.csv
├── ResidentialTransaction20260121005233.csv
├── ResidentialTransaction20260121005346.csv
├── ResidentialTransaction20260121005450.csv
├── ResidentialTransaction20260121005601.csv
├── ResidentialTransaction20260121005715.csv
└── ResidentialTransaction20260121005734.csv

data/raw_data/csv/ResaleFlatPrices/
├── Resale Flat Prices (Based on Registration Date), From Mar 2012 to Dec 2014.csv
├── ResaleFlatPricesBasedonRegistrationDateFromJan2015toDec2016.csv
├── ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv
├── Resale Flat Prices (Based on Approval Date), 1990 - 1999.csv
└── Resale Flat Prices (Based on Approval Date), 2000 - Feb 2012.csv
```

**Progress Indicators Added:**
- Progress printing every 50 addresses
- Clear error messages for failed API calls
**File Modified:** `notebooks/L1_ura_transactions_processing.py` (lines 263-285)

**Intended Output (not created):**
- `L1_housing_ec_transaction.parquet` - EC transactions with geocoding
- `L1_housing_condo_transaction.parquet` - Condo transactions with geocoding
- `L1_housing_residential_transaction.parquet` - Residential transactions with geocoding
- `L1_housing_hdb_transaction.parquet` - HDB transactions with geocoding
- `L2_housing_unique_searched.parquet` - Unique addresses with coordinates

### L1 Utilities & Amenities Processing

**Status:** **Failed** - Missing required source files

**Missing Files:**
1. `data/raw_data/csv/datagov/Generalinformationofschools.csv` - School data
2. `data/raw_data/csv/datagov/Kindergartens.geojson` - Kindergarten locations
3. `data/raw_data/csv/datagov/GymsSGGEOJSON.geojson` - Gym locations
4. Additional GeoJSON files for hawker centres, etc.

**Configuration:**
- `school_query_onemap = False` - Attempts to load pre-existing queried data
- `mall_query_onemap = False` - Attempts to load pre-existing queried data

**Intended Output (not created):**
- `L1_school_queried.parquet` - Schools with coordinates
- `L1_mall_queried.parquet` - Malls with coordinates (113 malls to geocode)
- `L1_kindergarten.parquet` - Kindergarten locations
- `L1_gym.parquet` - Gym locations
- `L1_hawker.parquet` - Hawker centre locations
- `L1_amenity.parquet` - Combined amenities dataset

---

## 3. ❌ NOT STARTED: L2 Feature Engineering Stage

**Status:** **Blocked** - Depends on L1 outputs

**Required Dependencies (all missing):**
- `L2_housing_unique_searched.parquet` - Unique property addresses with coordinates
- `L1_amenity.parquet` - Schools, malls, kindergartens, gyms, hawker centres
- `L1_housing_condo_transaction.parquet` - Condo transaction data
- `L1_housing_ec_transaction.parquet` - EC transaction data
- `L1_housing_hdb_transaction.parquet` - HDB transaction data

**Intended Features:**
- Distance calculations to amenities (schools, malls, etc.)
- H3 hexagonal spatial indexing
- Planning area assignments
- Feature engineering for ML/analysis

---

## 4. Issues & Resolutions

### Critical Issues

1. **OneMap API Rate Limiting**
   - **Impact:** Geocoding 12K addresses would take 10-33 hours
   - **Root Cause:** 5-10 second delay per API call with rate limiting
   - **Status:** UNRESOLVED - Consider:
     - Batch geocoding services (Google Maps API, Mapbox)
     - Caching geocoded addresses for reuse
     - Parallel processing with multiple API keys
     - Limiting to top N most important addresses

2. **Missing Source Files**
   - **Impact:** Cannot complete L1 utilities processing
   - **Missing:** School CSV, kindergarten/gym GeoJSON files
   - **Status:** UNRESOLVED - Need to download from data.gov.sg

### Minor Issues (All Resolved)

3. **Import Path Resolution** ✅
   - Fixed relative import paths across all notebooks
   - Solution: `pathlib.Path(__file__).parent.parent / 'src'`

4. **Environment Variable Loading** ✅
   - Added `load_dotenv()` to notebooks using `.env`

5. **Character Encoding** ✅
   - URA CSV files use `latin1` encoding instead of UTF-8

6. **Text to Numeric Conversion** ✅
   - Created function to parse "61 years 04 months" format to numeric months

7. **JWT Token Management** ✅
   - Added expiration checking before using OneMap token

---

## 5. Data Quality Summary

### Successfully Collected Data

**HDB Resale flats:**
- **Time period:** 1990-2025 (35 years of data)
- **Total records:** 979K transactions
- **Data quality:** ✅ High - Official HDB data
- **Geographic coverage:** All Singapore
- **Columns:** town, flat_type, block, street_name, storey_range, floor_area_sqft, flat_model, lease_commence_date, remaining_lease_months, resale_price

**Private Property Market Indices:**
- **Time period:** Varies by dataset
- **Data quality:** ✅ High - Official URA data
- **Coverage:** Rental index, price index, median prices by property type

**Shopping Malls:**
- **Total:** 113 malls
- **Source:** Wikipedia (needs verification)
- **Data quality:** ⚠️ Medium - Web scraped data

### Not Yet Created

**Geocoded Addresses:**
- 12,166 unique property addresses need coordinates
- Includes condos, ECs, HDB blocks, residential projects

**Amenities:**
- Schools, kindergartens, gyms, hawker centres
- Dependent on missing GeoJSON files

---

## 6. Recommendations

### Immediate Actions (To Complete Pipeline)

1. **Download Missing Source Files** 🎯 **HIGH PRIORITY**
   ```bash
   # Check data.gov.sg for these datasets:
   - General information of schools (CSV)
   - Kindergartens (GeoJSON)
   - Gyms (GeoJSON)
   - Hawker centres (GeoJSON)
   ```

2. **Address Geocoding Strategy** 🎯 **HIGH PRIORITY**

   **Option A: Quick Start (Limit Scope)**
   - Geocode only top 100 most frequent addresses
   - Use for testing pipeline structure
   - Time: ~10-15 minutes

   **Option B: Complete Solution (Production)**
   - Use paid geocoding service (Google Maps: $5 per 1000 calls)
   - Cost: ~$60 for all 12K addresses
   - Time: ~1-2 hours
   - Benefits: Higher accuracy, faster, reliable

   **Option C: Free but Slow (Current Approach)**
   - OneMap API with rate limiting
   - Time: 10-33 hours
   - Cost: Free
   - Benefits: No cost, official Singapore data

3. **Skip Geocoding Temporarily** ⏩ **ALTERNATIVE**
   - Complete L1 CSV loading without geocoding
   - Skip L2 distance-to-amenities features
   - Focus on: Price trends, transaction volumes, market analysis
   - Add geocoding later when time permits

### Code Improvements

1. **Add Progress Bars** for long-running operations
   - Use `tqdm` library for API call loops
   - Already partially implemented in L1_utilities

2. **Implement Caching**
   - Cache geocoded addresses in `{address: {lat, lon}}` format
   - Save to parquet for reuse across pipeline runs
   - Avoid re-geocoding on subsequent runs

3. **Error Handling**
   - Add retry logic with exponential backoff (already implemented)
   - Log failed addresses for manual review
   - Continue processing even if some lookups fail

4. **Parallel Processing**
   - Use `concurrent.futures` or `asyncio` for parallel API calls
   - Respect rate limits (OneMap: ~250 calls/minute)
   - Could reduce time by 50-70%

---

## 7. Technical Reference

### Environment Setup
- **Python:** 3.13
- **Package Manager:** `uv`
- **Key Dependencies:**
  - pandas, pyarrow (parquet files)
  - geopandas, shapely (spatial data)
  - requests, beautifulsoup4 (API/scraping)
  - python-dotenv (environment variables)
  - h3 (hexagonal spatial indexing)
  - jupyter, jupytext (notebook management)

### API Credentials Required
```
ONEMAP_EMAIL=your@email.com
ONEMAP_EMAIL_PASSWORD=yourpassword
ONEMAP_TOKEN=eyJhbGci... (valid JWT token)
GOOGLE_API_KEY=your_key (optional)
```

### File Structure
```
egg-n-bacon-housing/
├── data/
│   ├── parquets/           # All output datasets (8 created)
│   └── raw_data/
│       ├── csv/
│       │   ├── uRA/        # 14 URA transaction files
│       │   └── ResaleFlatPrices/  # 5 HDB resale files
│       └── onemap_planning_area_polygon.*  # Shapefile + GeoJSON
├── notebooks/
│   ├── L0_datagovsg.py     # ✅ Completed
│   ├── L0_onemap.py        # ✅ Completed
│   ├── L0_wiki.py          # ✅ Completed
│   ├── L1_ura_transactions_processing.py  # ⚠️ Partial (geocoding blocked)
│   ├── L1_utilities_processing.py  # ❌ Failed (missing files)
│   └── L2_sales_facilities.py  # ❌ Blocked
├── src/
│   ├── config.py           # Centralized configuration
│   └── data_helpers.py     # Load/save parquet functions
└── .env                    # API credentials
```

### Commands Used

**Run individual notebooks:**
```bash
uv run python notebooks/L0_datagovsg.py
uv run python notebooks/L0_onemap.py
uv run python notebooks/L0_wiki.py
```

**Check dataset metadata:**
```bash
uv run python -c "
from src.data_helpers import list_datasets
import json
datasets = list_datasets()
print(json.dumps(datasets, indent=2))
"
```

**Load a dataset:**
```bash
uv run python -c "
from src.data_helpers import load_parquet
df = load_parquet('raw_datagov_resale_flat_all')
print(f'Rows: {len(df):,}')
print(df.head())
"
```

---

## 8. Next Steps

### Option A: Complete Full Pipeline (Recommended for production)
1. Download missing GeoJSON/CSV files from data.gov.sg
2. Set up paid geocoding service (~$60)
3. Run L1_ura with geocoding (2 hours)
4. Run L1_utilities for amenities (30 minutes)
5. Run L2_sales_facilities for features (10 minutes)

### Option B: Minimal Viable Pipeline (Quick start)
1. Skip geocoding for now
2. Create L1 datasets from CSV files only
3. Run basic analysis on transaction volumes, prices
4. Add geocoding features later

### Option C: Hybrid Approach (Balanced)
1. Geocode top 1,000 most frequent addresses (15 minutes)
2. Complete L1 and L2 with partial geocoding
3. Iterate and add more geocoding over time

---

## Summary

**✅ What's Working:**
- Data collection from APIs (data.gov.sg, Wikipedia, OneMap)
- CSV file loading and processing
- Parquet file storage and retrieval
- OneMap API authentication
- Basic data cleaning and type conversions

**⚠️ What Needs Work:**
- Geocoding strategy (time/cost tradeoff)
- Missing source files for amenities
- Long-running task monitoring

**❌ What's Blocking:**
- L1 utilities processing (missing files)
- L2 feature engineering (depends on L1)
- Full geocoding (rate limiting)

**Overall Assessment:** The pipeline foundation is solid with 40% completion. Main blocker is geocoding strategy decision and missing amenity files. Once resolved, can complete remaining 60% in 2-3 hours.

---

**Report Generated:** 2026-01-21
**Pipeline Version:** 1.0
**Last Updated:** During session after fixing OneMap auth and completing L0 stage
