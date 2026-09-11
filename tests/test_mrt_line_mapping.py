"""WS4: the NSL/EWL-only station->line fallback must warn once per process."""

import json
import logging

import pytest

pytestmark = pytest.mark.unit

_MAPPING_LOGGER = "egg_n_bacon_housing.utils.mrt_line_mapping"


@pytest.fixture(autouse=True)
def _reset_fallback_flag(monkeypatch):
    """Isolate the once-per-process guard between tests."""
    from egg_n_bacon_housing.utils import mrt_line_mapping

    monkeypatch.setattr(mrt_line_mapping, "_fallback_station_lines_warned", False)


def _fallback_warnings(caplog):
    return [r for r in caplog.records if "NSL/EWL" in r.getMessage()]


class TestFallbackStationLinesWarning:
    def test_fallback_warning_fires_once_per_process(self, tmp_path, caplog):
        from egg_n_bacon_housing.utils.mrt_line_mapping import (
            MrtReferenceRepository,
            _build_fallback_station_lines,
        )

        with caplog.at_level(logging.WARNING, logger=_MAPPING_LOGGER):
            repo_a = MrtReferenceRepository(tmp_path)  # no mrt_stations.json in tmp_path
            assert "TOA PAYOH" in repo_a.station_lines_mapping()
            repo_b = MrtReferenceRepository(tmp_path)
            assert repo_b.station_lines_mapping()  # second repository, same process

        warnings = _fallback_warnings(caplog)
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert "fallback" in message
        # covers only the hardcoded NSL/EWL stations while mrt_lines() knows 9
        assert str(len(_build_fallback_station_lines())) in message
        assert "9 lines" in message
        assert "interchange" in message

    def test_json_present_path_is_silent(self, tmp_path, caplog):
        from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository

        (tmp_path / "mrt_stations.json").write_text(json.dumps({"BISHAN": ["NSL", "CCL"]}))

        with caplog.at_level(logging.WARNING, logger=_MAPPING_LOGGER):
            repo = MrtReferenceRepository(tmp_path)
            assert repo.station_lines_mapping()["BISHAN"] == ["NSL", "CCL"]

        assert not _fallback_warnings(caplog)
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


class TestStationScoreBasis:
    """WO-8: the station-score arithmetic has one shared definition.

    ``MrtReferenceRepository.station_score`` and the vectorized proximity
    path (``utils.proximity``) both build on ``station_score_basis`` — this
    pins the repository score against the literal pre-extraction formula
    over a grid of tier/bonus/distance cases.
    """

    @pytest.fixture
    def repo(self, tmp_path):
        from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository

        (tmp_path / "mrt_lines.json").write_text(
            json.dumps({"NSL": {"tier": 1}, "DTL": {"tier": 2}, "BPLRT": {"tier": 3}})
        )
        (tmp_path / "mrt_stations.json").write_text(
            json.dumps(
                {
                    "SINGLE": ["NSL"],
                    "FEEDER": ["BPLRT"],
                    "DUO": ["NSL", "DTL"],
                    "TRIPLE": ["NSL", "DTL", "BPLRT"],
                }
            )
        )
        return MrtReferenceRepository(tmp_path)

    @pytest.mark.parametrize(
        "station, expected_basis",
        [
            ("SINGLE", 3),  # tier 1, one line: 4 - 1
            ("FEEDER", 1),  # tier 3 LRT feeder: 4 - 3
            ("DUO", 4),  # tier 1 + 2-line interchange bonus
            ("TRIPLE", 5),  # tier 1 (3 lines force tier 1) + both bonuses
        ],
    )
    def test_basis_values(self, repo, station, expected_basis):
        from egg_n_bacon_housing.utils.mrt_line_mapping import station_score_basis

        assert (
            station_score_basis(repo.station_lines(station), repo.station_tier(station))
            == expected_basis
        )

    @pytest.mark.parametrize("distance", [0.5, 1.0, 10.0, 500.0, 5000.0])
    def test_repository_score_matches_literal_formula(self, repo, distance):
        from egg_n_bacon_housing.utils.mrt_line_mapping import station_score_basis

        for station in ("SINGLE", "FEEDER", "DUO", "TRIPLE"):
            lines = repo.station_lines(station)
            tier = repo.station_tier(station)
            # The literal pre-extraction formula, computed independently here.
            basis = 4 - tier
            if len(lines) >= 2:
                basis += 1
            if len(lines) >= 3:
                basis += 1
            expected = (basis * 1000) / max(distance, 1)

            assert repo.station_score(station, distance) == pytest.approx(expected)
            # The proximity path's vectorized numerator uses the same basis.
            assert station_score_basis(lines, tier) * 1000 / max(distance, 1) == pytest.approx(
                expected
            )
