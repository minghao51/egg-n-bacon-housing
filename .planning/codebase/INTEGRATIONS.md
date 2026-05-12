# Integrations

## External APIs

### Singapore Government Data

| Source          | Usage                                              | Adapter                                         |
| --------------- | -------------------------------------------------- | ----------------------------------------------- |
| **OneMap API**  | Geocoding, postal search, planning area boundaries | `src/egg_n_bacon_housing/adapters/onemap.py`    |
| **Data.gov.sg** | Open data (schools, transactions, malls)           | `src/egg_n_bacon_housing/adapters/datagovsg.py` |
| **URA**         | Property transaction data, rental index            | `src/egg_n_bacon_housing/adapters/datagovsg.py` |
| **HDB**         | Housing transaction data                           | `src/egg_n_bacon_housing/adapters/datagovsg.py` |

### AI/ML Services

| Service                           | Purpose                 | Integration              |
| --------------------------------- | ----------------------- | ------------------------ |
| **Google Generative AI** (Gemini) | LLM analysis            | `langchain-google-genai` |
| **Jina AI**                       | Web scraping/conversion | `JINA_AI` env var        |

## Databases

### Local SQLite

- **Purpose**: Data quality tracking and baseline snapshots
- **File**: `src/egg_n_bacon_housing/utils/data_quality.py`

### Vector Store

- **FAISS**: Used in notebooks for RAG/embeddings

## Auth & Identity

| Provider     | Status     | Configuration                           |
| ------------ | ---------- | --------------------------------------- |
| **Supabase** | Configured | `SUPABASE_URL`, `SUPABASE_KEY` env vars |

## Storage

| Service    | Purpose                  | Integration                          |
| ---------- | ------------------------ | ------------------------------------ |
| **AWS S3** | Export/dashboard hosting | `boto3` in `components/04_export.py` |

## Environment Variables

```
ONEMAP_EMAIL=           # OneMap API authentication
ONEMAP_EMAIL_PASSWORD=  # OneMap API password
GOOGLE_API_KEY=         # Google APIs (geocoding, Gemini)
SUPABASE_URL=           # Supabase project URL
SUPABASE_KEY=           # Supabase anon key
JINA_AI=                # Jina AI API key
```

## Config Files

| File             | Purpose                                              |
| ---------------- | ---------------------------------------------------- |
| `config.yaml`    | Pipeline, geocoding, metrics, layer config overrides |
| `.env`           | Secrets (gitignored)                                 |
| `.env.example`   | Env var template                                     |
| `pyproject.toml` | Dependencies, Ruff, pytest, coverage, mypy           |
