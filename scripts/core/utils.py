"""Utility functions for analytics scripts.

This module provides common utility functions used across analytics scripts,
including path management, progress tracking, and output directory handling.
"""

import sys
from pathlib import Path
from typing import Optional


def add_project_to_path(file_path: Optional[Path] = None) -> Path:
    """Add project root to Python path from any script location.

    This function automatically detects the project root directory by looking
    for the 'scripts' directory in the file path and navigating up to it.

    Args:
        file_path: Path to the current script (typically use __file__).
                  If None, uses the current working directory.

    Returns:
        Path object pointing to the project root directory.

    Example:
        >>> from scripts.core.utils import add_project_to_path
        >>> from pathlib import Path
        >>> project_root = add_project_to_path(Path(__file__))
        >>> from scripts.core.config import Config
    """
    if file_path is None:
        file_path = Path.cwd()

    # Convert to Path object if string
    file_path = Path(file_path)

    # Find the project root by looking for 'scripts' directory
    path_parts = file_path.parts

    if 'scripts' in path_parts:
        # Get index of 'scripts' directory
        scripts_index = path_parts.index('scripts')
        # Navigate up to project root (parent of 'scripts')
        project_root = Path(*path_parts[:scripts_index])
    else:
        # Fallback: assume we're in a subdirectory, go up until we find project root markers
        project_root = file_path
        for _ in range(10):  # Safety limit
            if (project_root / 'scripts').exists() or \
               (project_root / 'pyproject.toml').exists() or \
               (project_root / 'data').exists():
                break
            project_root = project_root.parent

    # Add to sys.path if not already present
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    return project_root


def get_analysis_output_dir(script_name: str) -> Path:
    """Get standardized output directory for an analysis script.

    Args:
        script_name: Name of the script (e.g., 'mrt_impact', 'lease_decay')

    Returns:
        Path object for the output directory.

    Example:
        >>> from scripts.core.utils import get_analysis_output_dir
        >>> from scripts.core.config import Config
        >>> output_dir = get_analysis_output_dir('mrt_impact')
        >>> output_dir.mkdir(exist_ok=True, parents=True)
    """
    from scripts.core.config import Config
    output_dir = Config.DATA_DIR / "analysis" / script_name
    output_dir.mkdir(exist_ok=True, parents=True)
    return output_dir


def get_pipeline_output_dir(pipeline_name: str) -> Path:
    """Get standardized output directory for a pipeline script.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'forecast_prices', 'calculate_affordability')

    Returns:
        Path object for the output directory.

    Example:
        >>> from scripts.core.utils import get_pipeline_output_dir
        >>> output_dir = get_pipeline_output_dir('forecast_prices')
    """
    from scripts.core.config import Config
    output_dir = Config.DATA_DIR / "pipelines" / pipeline_name
    output_dir.mkdir(exist_ok=True, parents=True)
    return output_dir
