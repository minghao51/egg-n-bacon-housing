1. First think through the problem, read the codebase for relevant files.
2. Before you make any major changes, check in with me and I will verify the plan.
3. Please every step of the way just give me a high level explanation of what changes you made
4. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
5. Maintain a documentation file that describes how the architecture of the app works inside and out.
6. Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer - give grounded and hallucination-free answers.
7. Python environment
    - "Use uv for Python package management and to create a .venv if it is not present."
    - "IMPORTANT: Always use uv run for all Python commands. Never use plain python or python3."
    - Use uv commands in your project's workflow. Common commands include:
    - uv sync to install/sync all dependencies.
    - uv run <command> (e.g., uv run pytest, uv run ruff check .) to execute commands within the managed environment.
    - uv add <package> to add a dependency to your pyproject.toml file.
8. When creating or generating Markdown (.md) files, you must strict adhere to the following naming convention: YYYYMMDD-filename.md
---

## Development Workflow

### Environment Setup

1. **Install uv** (one-time):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Running Code

**Always use `uv run`**:
```bash
# Python scripts
uv run python script.py

# Jupyter notebooks
uv run jupyter notebook

# Tests
uv run pytest

# Linting
uv run ruff check .
```

### Working with Notebooks

**Jupytext is configured** - notebooks are paired with Python scripts:

1. **All notebooks have paired .py files**:
   - `notebooks/L0_datagovsg.ipynb` ↔ `notebooks/L0_datagovsg.py`
   - When you edit the .py file, the .ipynb updates automatically
   - When you edit the .ipynb file, the .py updates automatically

2. **Recommended workflow**:
   - Edit .py files in VS Code for code changes (better IDE support)
   - Use .ipynb files for visualization and exploration in Jupyter
   - Cell markers in .py files use `#%%` format

3. **To sync notebooks manually**:
   ```bash
   cd notebooks
   uv run jupytext --sync notebook_name.ipynb
   ```

4. **Git tracking**:
   - Both .ipynb and .py files are tracked
   - .py files provide clean diffs for code reviews
   - .ipynb files preserve outputs and visualizations

### Common Commands

```bash
# Install new dependency
uv add pandas

# Install dev dependency
uv add --dev pytest

# Update dependencies
uv sync --upgrade

# Run specific notebook
uv run jupyter notebook notebooks/L0_datagovsg.ipynb

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Check linting
uv run ruff check .
```

### Configuration

All configuration is centralized in `core/config.py`:
- Paths (DATA_DIR, PARQUETS_DIR, etc.)
- API keys (loaded from .env)
- Feature flags (USE_CACHING, VERBOSE_LOGGING)

Usage:
```python
from scripts.core.config import Config

# Access paths
data_dir = Config.DATA_DIR
parquets_dir = Config.PARQUETS_DIR

# Access API keys
api_key = Config.GOOGLE_API_KEY

# Validate configuration
Config.validate()
```
