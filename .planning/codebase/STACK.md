# Technology Stack

**Analysis Date:** 2026-02-02

## Languages

**Primary:**
- Python 3.11+ - Core data pipeline, analytics, and web applications

**Secondary:**
- JavaScript - Node.js dependencies for markdown processing
- TypeScript - Type definitions for JavaScript packages

## Runtime

**Environment:**
- Python 3.11+ 
- Node.js (for markdown processing dependencies)

**Package Manager:**
- uv 0.x - Python package management and dependency resolution
- npm - Node.js package management
- Lockfile: pyproject.toml (uv), package.json (npm)

## Frameworks

**Core:**
- Streamlit 1.x - Interactive web dashboard and visualization application
- Pandas 2.0+ - Data manipulation and analysis
- Scikit-learn 1.x - Machine learning algorithms
- LangChain 0.3+ - LLM integration and agent frameworks
- LangGraph 0.2+ - Workflow orchestration for AI agents
- GeoPandas - Geospatial data processing

**Testing:**
- pytest 7.0+ - Unit and integration testing
- Ruff 0.1+ - Linting and code formatting

**Build/Dev:**
- Jupyter 1.0+ - Interactive development environment
- Jupytext 1.16+ - Notebook-text pairing
- uv - Development environment management

## Key Dependencies

**Critical:**
- Pandas 2.0+ - Core data processing for all housing analytics
- Streamlit 1.x - Web dashboard interface
- GeoPandas - Location-based data processing
- Scikit-learn - Machine learning for market segmentation
- LangChain 0.3+ - Google AI integration
- LangGraph 0.2+ - Agent workflow management

**Infrastructure:**
- boto3 - AWS S3 integration for data storage
- Supabase - Database backend
- Requests - HTTP client for external APIs
- Tenacity - Retry logic for API calls
- python-dotenv - Environment variable management

## Configuration

**Environment:**
- Environment variables managed through .env file
- Centralized configuration in scripts/core/config.py
- Path-based configuration for data directories

**Build:**
- pyproject.toml - Project configuration and dependencies
- jupytext.toml - Notebook synchronization settings
- pytest.ini - Test configuration

## Platform Requirements

**Development:**
- Python 3.11+ runtime
- uv package manager
- Jupyter notebook support
- Git version control

**Production:**
- Python 3.11+ runtime
- Streamlit server for web application
- Supabase database
- AWS S3 for data storage

---

*Stack analysis: 2026-02-02*
