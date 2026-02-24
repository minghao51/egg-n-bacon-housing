# CSV Download Guide for Pipeline

**Created**: 2026-01-21
**Updated**: 2026-01-21

---

## ✅ Files Downloaded and Configured

All required CSV files have been successfully downloaded and configured!

### Part 1: HDB Resale Flat Prices (2 files) ✅

**Location**: `data/raw_data/csv/`

1. ✅ `ResaleFlatPricesBasedonRegistrationDateFromJan2015toDec2016.csv`
2. ✅ `ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv`

**Source**: https://data.gov.sg/collections/189/view

---

### Part 2: URA Residential Transactions (14 files) ✅

**Location**: `data/raw_data/csv/ura/`

#### EC (Executive Condominium) Transactions - 2 files:
1. ✅ `URA_ResidentialTransaction_EC2020_20240917220317.csv`
2. ✅ `URA_ResidentialTransaction_EC2021_20240917220358.csv`

#### Condo Transactions - 5 files:
1. ✅ `URA_ResidentialTransaction_Conda2020_20240917220234.csv`
2. ✅ `URA_ResidentialTransaction_Conda2021_20240917220149.csv`
3. ✅ `URA_ResidentialTransaction_Conda2022_20240917220116.csv`
4. ✅ `URA_ResidentialTransaction_Conda2023_20240917215948.csv`
5. ✅ `URA_ResidentialTransaction_Condo2024_20240917215852.csv`

#### Additional Residential Transactions - 7 files:
1. ✅ `ResidentialTransaction20260121005130.csv`
2. ✅ `ResidentialTransaction20260121005233.csv`
3. ✅ `ResidentialTransaction20260121005346.csv`
4. ✅ `ResidentialTransaction20260121005450.csv`
5. ✅ `ResidentialTransaction20260121005601.csv`
6. ✅ `ResidentialTransaction20260121005715.csv`
7. ✅ `ResidentialTransaction20260121005734.csv`

**Source**: https://eservice.ura.gov.sg/property-market-information/pmiResidentialTransactionSearch

---

## Pipeline Updates

The `L1_ura_transactions_processing.py` notebook has been updated to:
- Use the 2 available EC files (2020-2021)
- Use all 5 Condo files (2020-2024)
- Include all 7 additional residential transaction files
- Process all 14 files into comprehensive datasets

---

## Verification

All files verified and ready:
```bash
# HDB files
ls -la data/raw_data/csv/*.csv
# Output: 2 CSV files

# URA files
ls -la data/raw_data/csv/ura/*.csv
# Output: 14 CSV files
```

**Total**: 16 CSV files ready for pipeline processing

---

## Next Steps

Run the pipeline:
```bash
echo "y
y
y
y" | uv run python run_real_pipeline.py
```

The pipeline will now process all downloaded CSV files along with API-fetched data!
