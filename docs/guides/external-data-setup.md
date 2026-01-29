# External Data Setup Guide

This guide covers downloading and setting up external data sources required for the Egg-n-Bacon Housing pipeline.

## Overview

The pipeline requires several external data sources:

| Category | Source | Automation | Refresh Frequency |
|----------|--------|------------|-------------------|
| Amenity Datasets | data.gov.sg API | ✅ Automated | On demand |
| HDB Rental Data | data.gov.sg API | ✅ Automated | Monthly |
| URA Rental Index | data.gov.sg API | ✅ Automated | Quarterly |
| URA Transactions | URA Website | ❌ Manual | Quarterly |
| HDB Resale Prices | data.gov.sg API | ✅ Automated | Via L0 pipeline |

## Quick Start

### 1. Automated Downloads (Recommended)

Run the unified refresh pipeline to download all automated data sources:

```bash
# Check what's missing (dry run)
uv run python scripts/data/download/refresh_external_data.py --dry-run

# Download all missing data
uv run python scripts/data/download/refresh_external_data.py

# Force refresh all data
uv run python scripts/data/download/refresh_external_data.py --force-all
```

### 2. Manual Downloads

URA private property transaction files must be downloaded manually from the URA website (see [Manual Downloads](#manual-downloads) below).

---

## Automated Downloads

### Amenity Datasets (data.gov.sg)

**Location:** `data/manual/csv/datagov/`

**Phase 1 Datasets:**
- PreSchoolsLocation.geojson
- NParksParksandNatureReserves.geojson
- MasterPlan2019SDCPParkConnectorLinelayerGEOJSON.geojson
- MasterPlan2019SDCPWaterbodylayerKML.kml
- Kindergartens.geojson
- GymsSGGEOJSON.geojson
- HawkerCentresGEOJSON.geojson
- SupermarketsGEOJSON.geojson
- WaterActivitiesSG.geojson

**Phase 2 Datasets:**
- MRTStations.geojson
- ChildCareServices.geojson
- MRTStationExits.geojson

**Individual Download:**
```bash
# Download phase 1 only
uv run python scripts/data/download/download_datagov_datasets.py --phase 1

# Download phase 2 only
uv run python scripts/data/download/download_datagov_datasets.py --phase 2

# Download all phases
uv run python scripts/data/download/download_datagov_datasets.py --phase all

# Force re-download
uv run python scripts/data/download/download_datagov_datasets.py --phase all --force
```

**Refresh via Pipeline:**
```bash
uv run python scripts/data/download/refresh_external_data.py --amenities
```

### HDB Rental Data (data.gov.sg)

**Location:** `data/parquets/L1/housing_hdb_rental.parquet`

**Source:** Renting Out of Flats from Jan 2021

**Individual Download:**
```bash
uv run python scripts/data/download/download_hdb_rental_data.py
```

**Refresh via Pipeline:**
```bash
uv run python scripts/data/download/refresh_external_data.py --hdb
```

### URA Rental Index (data.gov.sg)

**Location:** `data/parquets/L2/ura_rental_index.parquet`

**Source:** URA Private Residential Property Rental Index

**Individual Download:**
```bash
uv run python scripts/data/download/download_ura_rental_index.py
```

**Refresh via Pipeline:**
```bash
uv run python scripts/data/download/refresh_external_data.py --ura
```

---

## Manual Downloads

### URA Private Property Transactions

These files **must be downloaded manually** from the URA website as they require CAPTCHA verification.

**Required Files:**

1. **EC Residential Transaction** (latest file)
   - Filename pattern: `ECResidentialTransactionYYYYMMDDhhmmss.csv`
   - Contains: Executive Condo transaction data

2. **Residential Transaction** (multiple files)
   - Filename pattern: `ResidentialTransactionYYYYMMDDhhmmss.csv`
   - Contains: Private residential property transaction data
   - Download all available files for complete history

**Download Steps:**

1. Visit URA Transaction Bulk Download:
   ```
   https://www.ura.gov.sg/property-market-information/transaction-bulk-download
   ```

2. Complete the CAPTCHA verification

3. Download the following:
   - **EC Residential Transaction** → Download latest file
   - **Residential Transaction** → Download all files

4. Extract ZIP files (if applicable)

5. Place CSV files in:
   ```
   data/manual/csv/ura/
   ```

**Expected Structure:**
```
data/manual/csv/ura/
├── ECResidentialTransaction20260121003532.csv
├── ResidentialTransaction20260121003944.csv
├── ResidentialTransaction20260121004101.csv
├── ResidentialTransaction20260121004213.csv
└── ... (multiple files)
```

**Validation:**

After downloading, validate the files:
```bash
uv run python scripts/utils/validate_ura_data.py
```

---

## Refresh Pipeline

The `refresh_external_data.py` script provides a unified interface for checking and refreshing all external data.

### Usage

```bash
# Check all data sources (dry run)
uv run python scripts/data/download/refresh_external_data.py --dry-run

# Download all missing data
uv run python scripts/data/download/refresh_external_data.py

# Download specific categories
uv run python scripts/data/download/refresh_external_data.py --amenities --ura

# Force refresh all data
uv run python scripts/data/download/refresh_external_data.py --force-all

# Download specific amenity phase
uv run python scripts/data/download/refresh_external_data.py --amenities --phase 2
```

### Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Check for missing files without downloading |
| `--force-all` | Force refresh all data even if files exist |
| `--amenities` | Check/download amenity datasets |
| `--phase {1\|2\|all}` | Which amenity phase (default: all) |
| `--ura` | Check/download URA rental index |
| `--hdb` | Check/download HDB rental data |

### Output

The script provides:
1. **Status check** of all external data files
2. **Summary** of missing vs existing files
3. **Automated downloads** for supported sources
4. **Instructions** for manual downloads (URA transactions)

Example output:
```
================================================================================
DATA REFRESH SUMMARY
================================================================================

✅ Existing files (3):
  [Amenity (all)] PreSchoolsLocation.geojson
  [Amenity (all)] MRTStations.geojson
  [URA Rental Index] ura_rental_index.parquet

❌ Missing files (1):
  [HDB Rental Data] housing_hdb_rental.parquet

================================================================================
DOWNLOADING MISSING DATA
================================================================================

🚀 Running: download_hdb_rental_data.py
...
✅ download_hdb_rental_data.py completed successfully

================================================================================
REFRESH COMPLETE
================================================================================
✅ Successful downloads: 1
```

---

## File Locations Reference

### Automated Downloads

| Data Type | Location | Script |
|-----------|----------|--------|
| Amenity GeoJSONs | `data/manual/csv/datagov/` | `download_datagov_datasets.py` |
| HDB Rental Data | `data/parquets/L1/housing_hdb_rental.parquet` | `download_hdb_rental_data.py` |
| URA Rental Index | `data/parquets/L2/ura_rental_index.parquet` | `download_ura_rental_index.py` |

### Manual Downloads

| Data Type | Location | Download URL |
|-----------|----------|--------------|
| URA Transactions | `data/manual/csv/ura/` | URA Website |

### Generated/Processed Data

| Data Type | Location | Generated By |
|-----------|----------|--------------|
| HDB Transactions | `data/parquets/L1/housing_hdb_transaction.parquet` | L0 pipeline |
| Condo Transactions | `data/parquets/L1/housing_condo_transaction.parquet` | L1 pipeline |
| EC Transactions | `data/parquets/L1/housing_ec_transaction.parquet` | L1 pipeline |
| Geocoded Properties | `data/parquets/L2/housing_unique_searched.parquet` | L1 pipeline |
| Unified Dataset | `data/parquets/L3/housing_unified.parquet` | L3 pipeline |

---

## Troubleshooting

### Network Errors

**Error:** `Network unavailable. Cannot download data.`

**Solution:** Check your internet connection and ensure the data.gov.sg API is accessible.

```bash
# Test network connectivity
curl -I https://data.gov.sg
```

### Permission Errors

**Error:** `Permission denied` when writing to directories

**Solution:** Ensure proper permissions on data directories:

```bash
chmod -R 755 data/
```

### Missing Dependencies

**Error:** `ModuleNotFoundError: No module named 'requests'`

**Solution:** Install dependencies:

```bash
uv sync
```

### API Rate Limiting

**Error:** HTTP 429 (Too Many Requests) from data.gov.sg

**Solution:** The scripts include rate limiting delays. If you encounter this:
1. Wait a few minutes
2. Re-run the download script
3. Use `--phase 1` and `--phase 2` separately to reduce concurrent requests

### Corrupted Downloads

**Error:** Script reports download success but file is corrupted

**Solution:** Delete the corrupted file and re-download:

```bash
# Find and delete corrupted file
rm data/manual/csv/datagov/CorruptedFile.geojson

# Re-download
uv run python scripts/data/download/download_datagov_datasets.py --force
```

---

## Maintenance Schedule

### Recommended Refresh Intervals

| Data Source | Frequency | Reason |
|-------------|-----------|--------|
| Amenity Datasets | Quarterly | New amenities open, facilities change |
| HDB Rental Data | Monthly | Latest rental rates |
| URA Rental Index | Quarterly | Updated quarterly by URA |
| URA Transactions | Quarterly | New transaction data released |

### Automation

Set up a cron job or scheduled task to refresh data automatically:

```bash
# Example: Refresh all data on the 1st of each month
# Add to crontab (crontab -e):
0 0 1 * * cd /path/to/egg-n-bacon-housing && uv run python scripts/data/download/refresh_external_data.py
```

---

## Additional Resources

- [data.gov.sg API Documentation](https://data.gov.sg/developer)
- [URA Property Market Information](https://www.ura.gov.sg/property-market-information)
- [HDB Resale Data Portal](https://services2.hdb.gov.sg/webapp/BR12AWResaleTransactions/BTWEBResaleTransaction)
- [Pipeline Guide](./l2-pipeline.md)
- [Architecture Overview](../architecture.md)

---

**Last Updated:** 2026-01-28
