# Integrations

## External APIs

### Singapore Government Data

| Source | Usage | Script/Notebook |
|--------|-------|-----------------|
| **OneMap API** | Geocoding, postal search, planning area boundaries | `scripts/core/geocoding.py`, `scripts/utils/refresh_onemap_token.py` |
| **URA** (Urban Redevelopment Authority) | Property transaction data, rental index | `scripts/data/download/download_ura_rental_index.py` |
| **Data.gov.sg** | Open data (schools, etc.) | `scripts/data/download/download_datagov_datasets.py` |
| **HDB** | Housing transaction data | `scripts/data/download/download_hdb_rental_data.py` |

### AI/ML Services

| Service | Purpose | Integration |
|---------|---------|-------------|
| **Google Generative AI** (Gemini) | LLM analysis | `langchain-google-genai==2.0.0` in notebooks |
| **Databricks** | SQL/DataFrame agents | `langchain_databricks` in notebooks |

### Data Processing

| Service | Purpose | Notes |
|---------|---------|-------|
| **Jina AI** | Web scraping/conversion | `JINA_AI` env var configured |
| **FAISS** | Vector store for embeddings | Notebook exploration only |

## Databases

### Local SQLite

- **Purpose**: Data quality tracking and baseline snapshots
- **Location**: `scripts/core/data_quality.py`, `scripts/utils/data_quality_report.py`
- **Tables**: `run_snapshots`, `historical_baselines`

### Vector Store

- **FAISS**: Used in `notebooks/exploration/ZZ_pyspark-dataframe-loader-langchain.py` for RAG/embeddings

## Auth & Identity

| Provider | Status | Configuration |
|----------|--------|---------------|
| **Supabase** | Configured but not detected in code | `SUPABASE_URL`, `SUPABASE_KEY` env vars |

## Storage

| Service | Purpose | Integration |
|---------|---------|-------------|
| **AWS S3** | Potential export/dashboard hosting | `boto3` in `scripts/core/stages/export/dashboard_exporter.py:411` |

## Environment Variables

```env
ONEMAP_EMAIL=
ONEMAP_EMAIL_PASSWORD=
ONEMAP_TOKEN=
GOOGLE_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
JINA_AI=
```

## Webhooks

No webhooks detected in codebase.

## CDN/Static Assets

- **KaTeax** (CDN): Math rendering
- **Shiki**: Built-in syntax highlighting (no external CDN)
