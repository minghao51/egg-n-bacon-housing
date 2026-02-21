"""Unified analysis results storage helpers.

Provides standardized functions for saving analysis results to a central location
with index tracking for easy exploration.

Usage:
    from scripts.core.stages.helpers.analysis_helpers import save_analysis_result, load_analysis_result

    # Save a result
    save_analysis_result(
        df=result_df,
        category="market",
        name="rental_yield_by_area",
        description="Rental yield statistics by planning area"
    )

    # Load a result
    df = load_analysis_result("market", "rental_yield_by_area")

    # List all results
    results = list_analysis_results()
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from scripts.core.config import Config

logger = logging.getLogger(__name__)

RESULTS_DIR = Config.ANALYTICS_DIR / "results"
INDEX_FILE = RESULTS_DIR / "index.json"


def get_results_dir(category: str = None) -> Path:
    """Get results directory, creating it if needed.

    Args:
        category: Optional category subdirectory (e.g., 'market', 'spatial')

    Returns:
        Path to results directory
    """
    if category:
        return RESULTS_DIR / category
    return RESULTS_DIR


def load_index() -> dict:
    """Load the analysis results index.

    Returns:
        Dictionary mapping category -> list of result entries
    """
    if not INDEX_FILE.exists():
        return {}

    with open(INDEX_FILE) as f:
        return json.load(f)


def save_index(index: dict):
    """Save the analysis results index.

    Args:
        index: Dictionary mapping category -> list of result entries
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def update_index(
    category: str, name: str, file_path: Path, row_count: int, description: str = None
):
    """Update the index with a new result file.

    Args:
        category: Category name (e.g., 'market', 'spatial', 'eda')
        name: Result name (without extension)
        file_path: Path to the saved file
        row_count: Number of rows in the result
        description: Optional description of the result
    """
    index = load_index()

    if category not in index:
        index[category] = []

    entry = {
        "name": name,
        "file": str(file_path.relative_to(Config.BASE_DIR)),
        "row_count": row_count,
        "updated_at": datetime.now().isoformat(),
    }

    if description:
        entry["description"] = description

    existing = [i for i, e in enumerate(index[category]) if e["name"] == name]
    if existing:
        index[category][existing[0]] = entry
    else:
        index[category].append(entry)

    save_index(index)
    logger.debug(f"Updated index: {category}/{name}")


def save_analysis_result(
    df: pd.DataFrame, category: str, name: str, description: str = None, format: str = "parquet"
) -> Path:
    """Save an analysis result to the unified results directory.

    Args:
        df: DataFrame to save
        category: Category subdirectory (e.g., 'market', 'spatial', 'eda', 'amenity')
        name: Result name (without extension)
        description: Optional description for index
        format: Output format ('parquet' or 'csv')

    Returns:
        Path to the saved file
    """
    output_dir = get_results_dir(category)
    output_dir.mkdir(parents=True, exist_ok=True)

    if format == "parquet":
        output_path = output_dir / f"{name}.parquet"
        df.to_parquet(output_path, index=False)
    elif format == "csv":
        output_path = output_dir / f"{name}.csv"
        df.to_csv(output_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")

    update_index(category, name, output_path, len(df), description)
    logger.info(f"✅ Saved {category}/{name} ({len(df):,} rows) to {output_path}")

    return output_path


def load_analysis_result(category: str, name: str) -> pd.DataFrame:
    """Load an analysis result from the unified results directory.

    Args:
        category: Category subdirectory
        name: Result name (without extension)

    Returns:
        DataFrame with the result data
    """
    index = load_index()

    if category not in index:
        raise ValueError(f"Category '{category}' not found in index")

    entries = [e for e in index[category] if e["name"] == name]
    if not entries:
        raise ValueError(f"Result '{name}' not found in category '{category}'")

    file_path = Config.BASE_DIR / entries[0]["file"]

    if file_path.suffix == ".parquet":
        return pd.read_parquet(file_path)
    elif file_path.suffix == ".csv":
        return pd.read_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")


def list_analysis_results(category: str = None) -> dict:
    """List all available analysis results.

    Args:
        category: Optional category to filter by

    Returns:
        Dictionary mapping category -> list of result entries
    """
    index = load_index()

    if category:
        return {category: index.get(category, [])}
    return index


def get_result_info(category: str, name: str) -> dict:
    """Get metadata about a specific result.

    Args:
        category: Category subdirectory
        name: Result name

    Returns:
        Dictionary with result metadata
    """
    index = load_index()

    if category not in index:
        return {}

    entries = [e for e in index[category] if e["name"] == name]
    if entries:
        return entries[0]
    return {}


def clear_category(category: str):
    """Clear all results in a category.

    Args:
        category: Category to clear
    """
    index = load_index()

    if category in index:
        for entry in index[category]:
            file_path = Config.BASE_DIR / entry["file"]
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted: {file_path}")

        index[category] = []
        save_index(index)
        logger.info(f"Cleared category: {category}")
