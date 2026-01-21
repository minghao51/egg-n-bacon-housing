# Archived Notebooks

**Date Archived**: 2026-01-22
**Reason**: These notebooks are optional export utilities not required for the core housing transaction pipeline.

## Files in this Archive

### L3_upload_s3.ipynb / L3_upload_s3.py
- **Purpose**: Upload L3 parquet files to AWS S3 and Supabase
- **Status**: Deprecated - S3 tokens expired, not integrated with main pipeline
- **Use Case**: Optional backup/archival to cloud storage
- **Can be restored if**: You need S3 or Supabase integration

### L4_s3_databricks_catalog.py
- **Purpose**: Read parquet files from S3 and create Databricks Delta tables
- **Status**: Deprecated - Requires Databricks environment, depends on broken S3 uploads
- **Use Case**: Downstream analytics in Databricks platform
- **Can be restored if**: You have Databricks and need Delta tables

## Current Pipeline Architecture

The housing transaction pipeline now operates entirely with local parquet files:

```
L0 (API Collection) → Local Parquet
    ↓
L1 (Processing) → Local Parquet
    ↓
L2 (Features) → Local Parquet
    ↓
L3 (Export) → Local Parquet (no cloud export needed)
```

## Migration Notes

If you want to restore cloud export functionality:

1. **S3 Upload**: Fix AWS credentials in `L3_upload_s3.ipynb`
2. **Supabase**: Configure `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
3. **Databricks**: First fix S3 upload, then run `L4_s3_databricks_catalog.py` in Databricks

## Documentation References

These files were referenced in (now updated):
- `README.md` - L3 export section
- `docs/20250120-data-pipeline.md` - L3 Export documentation
