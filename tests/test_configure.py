"""Tests for configure() patterns in mrt_line_mapping and school_features."""

import json

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


class TestMrtLineMappingConfigure:
    """Verify mrt_line_mapping.configure() sets paths and resets caches."""

    def test_configure_sets_config_dir(self, tmp_path):
        from egg_n_bacon_housing.utils import mrt_line_mapping

        mrt_line_mapping.configure(tmp_path)
        assert mrt_line_mapping._config_dir == tmp_path

    def test_configure_loads_json_lines(self, tmp_path):
        from egg_n_bacon_housing.utils import mrt_line_mapping

        lines_data = {"TEST": {"name": "Test Line", "color": "#FFFFFF", "tier": 1}}
        (tmp_path / "mrt_lines.json").write_text(json.dumps(lines_data))

        mrt_line_mapping.configure(tmp_path)
        lines = mrt_line_mapping.get_mrt_lines()
        assert "TEST" in lines
        assert lines["TEST"]["name"] == "Test Line"

    def test_configure_loads_json_station_mapping(self, tmp_path):
        from egg_n_bacon_housing.utils import mrt_line_mapping

        stations_data = {"TEST STATION": ["NSL"]}
        (tmp_path / "mrt_stations.json").write_text(json.dumps(stations_data))

        mrt_line_mapping.configure(tmp_path)
        mapping = mrt_line_mapping.get_station_lines_mapping()
        assert "TEST STATION" in mapping
        assert mapping["TEST STATION"] == ["NSL"]

    def test_reconfigure_resets_cached_lookups(self, tmp_path):
        """The stale-cache bug: reconfigure must invalidate _MRT_LINES."""
        from egg_n_bacon_housing.utils import mrt_line_mapping

        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        (dir_a / "mrt_lines.json").write_text(
            json.dumps({"LINE_A": {"name": "A", "color": "#A", "tier": 1}})
        )
        (dir_b / "mrt_lines.json").write_text(
            json.dumps({"LINE_B": {"name": "B", "color": "#B", "tier": 2}})
        )

        mrt_line_mapping.configure(dir_a)
        lines_a = mrt_line_mapping.get_mrt_lines()
        assert "LINE_A" in lines_a

        mrt_line_mapping.configure(dir_b)
        lines_b = mrt_line_mapping.get_mrt_lines()
        assert "LINE_B" in lines_b
        assert "LINE_A" not in lines_b

    def test_unconfigured_falls_back_to_defaults(self):
        from egg_n_bacon_housing.utils import mrt_line_mapping

        mrt_line_mapping.configure.__wrapped__ if hasattr(
            mrt_line_mapping.configure, "__wrapped__"
        ) else None
        mrt_line_mapping._config_dir = None
        mrt_line_mapping._MRT_LINES = None
        lines = mrt_line_mapping.get_mrt_lines()
        assert "NSL" in lines
        assert lines["NSL"]["tier"] == 1


class TestSchoolFeaturesConfigure:
    """Verify school_features.configure() sets paths correctly."""

    def test_configure_sets_paths(self, tmp_path):
        from egg_n_bacon_housing.utils import school_features

        bronze_dir = tmp_path / "bronze"
        data_dir = tmp_path / "data"
        school_features.configure(bronze_dir, data_dir)
        assert school_features._paths["bronze_dir"] == bronze_dir
        assert school_features._paths["data_dir"] == data_dir

    def test_load_reference_data_uses_configured_path(self, tmp_path):
        from egg_n_bacon_housing.utils import school_features

        bronze_dir = tmp_path / "bronze"
        external_dir = bronze_dir / "external"
        external_dir.mkdir(parents=True)
        data_dir = tmp_path / "data"

        tiers = {"primary": [{"school_name": "Test"}]}
        (external_dir / "school_tiers.json").write_text(json.dumps(tiers))

        school_features.configure(bronze_dir, data_dir)
        result = school_features._load_reference_data("school_tiers.json")
        assert result is not None
        assert "primary" in result

    def test_load_school_tiers_falls_back_to_csv(self, tmp_path):
        from egg_n_bacon_housing.utils import school_features

        bronze_dir = tmp_path / "bronze"
        data_dir = tmp_path / "data"
        csv_dir = data_dir / "manual" / "csv"
        csv_dir.mkdir(parents=True)

        pd.DataFrame({"school_name": ["CSV School"], "tier": [1]}).to_csv(
            csv_dir / "school_tiers_primary.csv", index=False
        )

        school_features.configure(bronze_dir, data_dir)
        primary, _ = school_features.load_school_tiers()
        assert len(primary) == 1
        assert primary.iloc[0]["school_name"] == "CSV School"

    def test_reconfigure_updates_paths(self, tmp_path):
        from egg_n_bacon_housing.utils import school_features

        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        school_features.configure(dir_a, tmp_path)
        assert school_features._paths["bronze_dir"] == dir_a

        school_features.configure(dir_b, tmp_path)
        assert school_features._paths["bronze_dir"] == dir_b
