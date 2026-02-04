"""
Base classes and utilities for common script patterns.

This module provides reusable components for scripts to reduce boilerplate
and ensure consistency across the codebase.

Usage:
    from scripts.core.script_base import ScriptBase, setup_script_environment

    # Simple script setup
    class MyScript(ScriptBase):
        def run(self):
            logger = self.get_logger()
            logger.info("Starting script")
            # Your script logic here

    if __name__ == "__main__":
        script = MyScript()
        script.execute()
"""

import argparse
import logging
import sys
from pathlib import Path

from scripts.core.config import Config
from scripts.core.logging_config import get_logger, setup_logging_from_env


def setup_script_environment(project_root: Path | None = None) -> Path:
    """
    Setup the Python path for scripts.

    This ensures that imports work correctly regardless of where the script
    is located in the project.

    Args:
        project_root: Path to project root (auto-detected if None)

    Returns:
        Path to project root

    Example:
        >>> from pathlib import Path
        >>> from scripts.core.script_base import setup_script_environment
        >>>
        >>> root = setup_script_environment()
        >>> print(f"Project root: {root}")
    """
    if project_root is None:
        # Auto-detect: look for scripts/ directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent

    # Add to path if not already there
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    return project_root


class ScriptBase:
    """
    Base class for scripts with common functionality.

    Provides:
    - Automatic path setup
    - Logging configuration
    - Config validation
    - Argument parsing helpers
    - Error handling

    Example:
        >>> from scripts.core.script_base import ScriptBase
        >>>
        >>> class ProcessDataScript(ScriptBase):
        ...     def add_arguments(self, parser):
        ...         parser.add_argument("--input", required=True)
        ...         parser.add_argument("--output", required=True)
        ...
        ...     def run(self, args):
        ...         logger = self.get_logger()
        ...         logger.info(f"Processing {args.input}")
        ...         # Your logic here
        ...
        >>> if __name__ == "__main__":
        ...     script = ProcessDataScript()
        ...     script.execute()
    """

    def __init__(self, description: str | None = None):
        """
        Initialize the script.

        Args:
            description: Script description for help text
        """
        self.description = description or self.__class__.__name__
        self.logger = None
        self.args = None

    def setup_environment(self) -> None:
        """Setup Python path and environment."""
        setup_script_environment()

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        setup_logging_from_env()

    def validate_config(self) -> None:
        """Validate application configuration."""
        try:
            Config.validate()
        except ValueError as e:
            self.get_logger().error(f"Configuration error: {e}")
            sys.exit(1)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add script-specific arguments.

        Override this method to add custom arguments.

        Args:
            parser: Argument parser to add arguments to

        Example:
            >>> def add_arguments(self, parser):
            ...     parser.add_argument("--input", required=True, help="Input file")
            ...     parser.add_argument("--output", required=True, help="Output file")
        """
        pass

    def parse_arguments(self) -> argparse.Namespace:
        """
        Parse command-line arguments.

        Returns:
            Parsed arguments

        Example:
            >>> args = self.parse_arguments()
            >>> print(args.input)
        """
        parser = argparse.ArgumentParser(
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Add common arguments
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Logging level (default: INFO)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output (same as --log-level=DEBUG)",
        )

        # Add script-specific arguments
        self.add_arguments(parser)

        return parser.parse_args()

    def get_logger(self) -> logging.Logger:  # type: ignore
        """
        Get logger for this script.

        Returns:
            Configured logger instance

        Example:
            >>> logger = self.get_logger()
            >>> logger.info("Script started")
        """
        if self.logger is None:
            self.logger = get_logger(self.__class__.__name__)
        return self.logger

    def run(self, args: argparse.Namespace) -> None:
        """
        Main script logic.

        Override this method to implement your script logic.

        Args:
            args: Parsed command-line arguments

        Example:
            >>> def run(self, args):
            ...     logger = self.get_logger()
            ...     logger.info(f"Processing {args.input}")
            ...     # Your logic here
        """
        raise NotImplementedError("Subclasses must implement run()")

    def execute(self) -> None:
        """
        Execute the complete script workflow.

        This method orchestrates the script execution:
        1. Setup environment
        2. Setup logging
        3. Validate configuration
        4. Parse arguments
        5. Run main logic
        6. Handle errors

        Example:
            >>> if __name__ == "__main__":
            ...     script = MyScript()
            ...     script.execute()
        """
        try:
            # Setup
            self.setup_environment()
            self.setup_logging()
            self.validate_config()

            # Parse arguments
            self.args = self.parse_arguments()

            # Adjust log level if verbose flag
            if self.args.verbose:
                import logging

                logging.getLogger().setLevel(logging.DEBUG)

            # Run main logic
            self.run(self.args)

        except KeyboardInterrupt:
            self.get_logger().info("Script interrupted by user")
            sys.exit(130)  # Standard exit code for SIGINT
        except Exception as e:
            logger = self.get_logger()
            logger.exception(f"Script failed: {e}")
            sys.exit(1)


def simple_script_wrapper(main_func):
    """
    Decorator to wrap simple scripts with common setup.

    Use this for scripts that don't need the full ScriptBase class.

    Args:
        main_func: Main function to wrap

    Example:
        >>> from scripts.core.script_base import simple_script_wrapper
        >>>
        >>> @simple_script_wrapper
        ... def main():
        ...     logger = get_logger(__name__)
        ...     logger.info("Simple script running")
        ...     # Your logic here
    """

    def wrapper():
        setup_script_environment()
        setup_logging_from_env()
        try:
            Config.validate()
        except ValueError as e:
            logger = get_logger(__name__)
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

        return main_func()

    return wrapper
