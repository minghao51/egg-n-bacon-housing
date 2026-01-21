# Exploration Notebooks

**Status**: Experimental / Testing
**Purpose**: Early-stage exploration, proof-of-concepts, and experimental features

This folder contains notebooks that were used for exploration and testing but are not part of the main housing transaction data pipeline.

## Contents

### Test & Experimentation Notebooks

#### AI/Agent Testing
- `gemini-simple-call.ipynb` / `.py` - Testing Google Gemini API integration
- `pandas_agent.ipynb` / `.py` - Testing LangChain pandas agent for data analysis

#### Geospatial Experiments
- `hexgrid_test.ipynb` / `.py` - Testing hexagonal grid generation for Singapore regions

### Databricks & Spark (ZZ_ prefix = experimental/archived)

These were experiments with Databricks and LangChain integrations:

- `ZZ_Databricks Test Query.py` - Testing Databricks SQL queries
- `ZZ_pyspark-dataframe-loader-langchain.py` - Exploring PySpark DataFrame loaders with LangChain
- `ZZ_spark-dataframe-agent-langchain.py` - Testing Spark DataFrame agent for querying
- `ZZ_sql-database-agent-langchain.py` - SQL database agent experimentation

**Note**: These require Databricks runtime environment and are not part of the local pipeline.

## Usage

These notebooks are **not required** for the main pipeline but can be useful for:

1. **Learning**: Understanding how different APIs (Gemini, LangChain) work
2. **Reference**: Examples of integration patterns that might be reused
3. **Experimentation**: Trying new features before adding to the main pipeline

## Main Pipeline vs. Exploration

**Main Pipeline** (in parent `notebooks/` directory):
- `L0_*` - Data collection from APIs
- `L1_*` - Data processing and cleaning
- `L2_*` - Feature engineering
- These are productionized and maintained

**Exploration** (this folder):
- Experimental features
- Proof-of-concepts
- Testing new libraries/APIs
- Not actively maintained
- May be outdated or broken

## Running These Notebooks

```bash
# Example: Run Gemini test notebook
uv run jupyter notebook notebooks/exploration/gemini-simple-call.ipynb

# Example: Run hexgrid test
uv run python notebooks/exploration/hexgrid_test.py
```

**Warning**: Some notebooks may require additional API keys or setup not covered in the main `.env.example` file.

---

**Last Updated**: 2026-01-22
**Moved to exploration**: To simplify main notebooks directory
