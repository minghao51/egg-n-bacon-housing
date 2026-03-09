# Documentation

Welcome to the Egg-n-Bacon-Housing documentation. This hub helps you find the right documentation based on your needs.

## Quick Navigation

| I want to... | Go to |
|--------------|-------|
| **Set up and run the project** | [Getting Started](#getting-started) |
| **Understand how it works** | [Architecture](architecture.md) |
| **Contribute code** | [Contributing Guide](CONTRIBUTING.md) |
| **Run analyses** | [Analytics Guides](#analytics) |
| **Troubleshoot issues** | [Troubleshooting](#troubleshooting) |

---

## Getting Started

### New to the project? Start here:

1. **[README.md](../README.md)** - Project overview and quick start
2. **[Quick Start Guide](guides/quick-start.md)** - 5-minute setup walkthrough
3. **[Architecture Overview](architecture.md)** - System design and data flow

### First-time setup:

```bash
# Install uv package manager (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install dependencies
git clone <repo-url>
cd egg-n-bacon-housing
uv sync

# Configure API keys
cp .env.example .env
# Edit .env with your ONEMAP_EMAIL credentials

# Verify setup
uv run pytest
```

See [External Data Setup](guides/external-data-setup.md) for API key details.

---

## For Users

Run the pipeline and explore housing data:

| Guide | Description |
|-------|-------------|
| **[Usage Guide](guides/usage-guide.md)** | Common tasks and workflows |
| **[Data Reference](guides/data-reference.md)** | Available datasets and schemas |
| **[L2 Pipeline Guide](guides/l2-pipeline.md)** | Feature engineering pipeline |
| **[L4 Analysis Pipeline](guides/l4-analysis-pipeline.md)** | Running market analyses |

---

## For Contributors

Develop and improve the project:

| Guide | Description |
|-------|-------------|
| **[Contributing Guide](../CONTRIBUTING.md)** | Development workflow, standards, PR process |
| **[Testing Guide](guides/testing-guide.md)** | Writing and running tests |
| **[E2E Testing](guides/e2e-testing.md)** | Frontend end-to-end tests |
| **[Configuration Guide](guides/configuration.md)** | Environment variables and settings |
| **[CI/CD Pipeline](guides/ci-cd-pipeline.md)** | GitHub Actions workflows |

**Quick dev commands:**

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Run specific pipeline stage
uv run python scripts/run_pipeline.py --stage L0
```

---

## For Analysts

Explore housing market insights:

| Report | Topic |
|--------|-------|
| **[Key Findings](analytics/findings.md)** | Main insights from ML analysis |
| **[MRT Impact](analytics/mrt-impact.md)** | Distance to MRT effect on prices |
| **[School Quality](analytics/school-quality.md)** | School tier impact analysis |
| **[Price Forecasts](analytics/price-forecasts.md)** | Time-series predictions |
| **[Spatial Hotspots](analytics/spatial-hotspots.md)** | Geographic market clustering |
| **[Lease Decay](analytics/lease-decay.md)** | Lease remaining depreciation |
| **[Causal Inference](analytics/causal-inference-overview.md)** | Policy impact studies |

---

## Reference

### Core Documentation

| Document | Description |
|----------|-------------|
| **[Architecture](architecture.md)** | Complete system design |
| **[CLAUDE.md](../CLAUDE.md)** | Project instructions for AI assistants |
| **[API Reference](reference/api-reference.md)** | Core utilities API docs |
| **[Data Quality Monitoring](guides/data-quality-monitoring.md)** | Quality metrics and alerts |

### Specialized Guides

| Guide | Topic |
|-------|-------|
| **[MRT Features Guide](guides/mrt-features-guide.md)** | MRT distance feature engineering |
| **[CSV Download Guide](guides/csv-download-guide.md)** | Exporting data to CSV |
| **[GitHub Secrets Setup](guides/github-secrets-setup.md)** | CI/CD secrets configuration |
| **[Troubleshooting](TROUBLESHOOTING.md)** | Common issues and solutions |

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **`ModuleNotFoundError: No module named 'scripts'`** | Always run commands from project root with `uv run` |
| **`Dataset 'X' not found`** | Run preceding pipeline stages first (see [Usage Guide](guides/usage-guide.md)) |
| **`429 Too Many Requests`** | API rate limit - wait or check quota (built-in delays should prevent this) |
| **Geocoding fails (all addresses return `None`)** | Check OneMap credentials in `.env` file |
| **Tests pass in CI but fail locally** | Run `uv sync` to update dependencies |

### Getting Help

1. **Check existing docs** - Use the search in your IDE or grep the repo
2. **Review [CLAUDE.md](../CLAUDE.md)** - Has detailed project conventions
3. **Check [Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
3. **Check [GitHub Issues](../../issues)** - Someone may have solved this already
4. **Open an issue** - Include error messages, steps to reproduce, and your environment

---

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation hub
├── architecture.md              # System architecture and design
├── analytics/                   # Published analysis reports
│   ├── findings.md
│   ├── mrt-impact.md
│   └── ...
├── guides/                      # How-to guides by topic
│   ├── README.md
│   ├── quick-start.md
│   ├── usage-guide.md
│   ├── testing-guide.md
│   └── ...
├── reference/                   # API documentation
│   └── api-reference.md
├── plans/                       # Design docs and implementation notes
│   └── YYYY-MM-DD-*.md
└── archive/                     # Historical documentation
    └── superseded-*.md
```

**See**: [GitHub](../../) for project source code

---

## Conventions

- **File names**: Use `kebab-case` for guides, `YYYY-MM-DD-title.md` for dated plans
- **Audience**: Write for your target audience (users, contributors, analysts)
- **Maintenance**: Move completed implementation notes to `docs/archive/`
- **Validation**: Run `uv run python scripts/tools/validate_docs_layout.py` after changes

---

**Last Updated**: 2025-03-10
