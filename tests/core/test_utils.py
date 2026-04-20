"""Tests for scripts.core.utils."""

import sys
from pathlib import Path

from scripts.core.utils import add_project_to_path, get_analysis_output_dir, get_pipeline_output_dir


class TestAddProjectToPath:
    """Test add_project_to_path function."""

    def test_returns_path_object(self):
        result = add_project_to_path(Path(__file__))
        assert isinstance(result, Path)

    def test_detects_project_root_from_scripts(self):
        result = add_project_to_path(Path(__file__))
        assert result.name in ("egg-n-bacon-housing", "tests") or (result / "scripts").exists()

    def test_adds_to_sys_path(self):
        len(sys.path)
        result = add_project_to_path(Path(__file__))
        assert str(result) in sys.path

    def test_idempotent(self):
        add_project_to_path(Path(__file__))
        count_before = sys.path.count(str(add_project_to_path(Path(__file__))))
        add_project_to_path(Path(__file__))
        count_after = sys.path.count(str(add_project_to_path(Path(__file__))))
        assert count_before == count_after

    def test_with_none_uses_cwd(self):
        result = add_project_to_path(None)
        assert isinstance(result, Path)

    def test_with_string_path(self):
        result = add_project_to_path(str(Path(__file__)))
        assert isinstance(result, Path)

    def test_fallback_when_no_scripts_in_path(self):
        result = add_project_to_path(Path("/tmp/some_random_dir"))
        assert isinstance(result, Path)


class TestGetAnalysisOutputDir:
    """Test get_analysis_output_dir function."""

    def test_returns_path(self, mock_config):
        result = get_analysis_output_dir("test_analysis")
        assert isinstance(result, Path)

    def test_creates_directory(self, mock_config):
        result = get_analysis_output_dir("test_analysis")
        assert result.exists()

    def test_directory_name_matches(self, mock_config):
        result = get_analysis_output_dir("mrt_impact")
        assert result.name == "mrt_impact"

    def test_under_analysis_subdir(self, mock_config):
        result = get_analysis_output_dir("test_analysis")
        assert "analysis" in result.parts


class TestGetPipelineOutputDir:
    """Test get_pipeline_output_dir function."""

    def test_returns_path(self, mock_config):
        result = get_pipeline_output_dir("test_pipeline")
        assert isinstance(result, Path)

    def test_creates_directory(self, mock_config):
        result = get_pipeline_output_dir("test_pipeline")
        assert result.exists()

    def test_directory_name_matches(self, mock_config):
        result = get_pipeline_output_dir("forecast_prices")
        assert result.name == "forecast_prices"
