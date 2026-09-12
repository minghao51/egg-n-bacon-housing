"""Tests for utils/geo.py — the shared haversine implementation.

Roadmap item 13a: the scalar ``haversine_distance`` and the vectorized
``haversine_metres`` must stay numerically identical — the vectorized path is
the single implementation and the scalar is a thin wrapper.
"""

import numpy as np
import pytest

from egg_n_bacon_housing.utils.geo import haversine_distance, haversine_metres

pytestmark = pytest.mark.unit

# Singapore-ish reference pair (Marina Bay Sands -> Changi Airport): the
# great-circle distance is ~16.9 km; tolerance is loose because the exact
# figure depends on the earth-radius convention.
_MBS = (1.2834, 103.8607)
_CHANGI = (1.3644, 103.9915)


class TestHaversineMetres:
    def test_known_distance_is_in_the_right_range(self):
        dist = haversine_metres(*_MBS, *_CHANGI)
        assert 15_000 < float(dist) < 19_000

    def test_identical_points_are_zero(self):
        dist = haversine_metres(1.3521, 103.8198, 1.3521, 103.8198)
        assert float(dist) == pytest.approx(0.0, abs=1.0)

    def test_antipodal_half_circumference(self):
        dist = haversine_metres(0.0, 0.0, 0.0, 180.0)
        # Half circumference of a 6371km sphere.
        assert float(dist) == pytest.approx(np.pi * 6_371_000, rel=1e-9)

    def test_vectorized_matches_elementwise_scalars(self):
        lats1 = np.array([1.30, 1.35, 1.44])
        lons1 = np.array([103.85, 103.82, 103.77])
        lats2 = np.array([1.31, 1.40, 1.25])
        lons2 = np.array([103.84, 103.99, 103.82])

        result = haversine_metres(lats1, lons1, lats2, lons2)

        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
        for i in range(3):
            expected = haversine_distance(
                float(lats1[i]), float(lons1[i]), float(lats2[i]), float(lons2[i])
            )
            assert result[i] == pytest.approx(expected, rel=1e-12)

    def test_accepts_python_lists(self):
        result = haversine_metres([1.30, 1.35], [103.8, 103.9], [1.31, 1.36], [103.8, 103.9])
        assert result.shape == (2,)
        assert result[0] == pytest.approx(haversine_distance(1.30, 103.8, 1.31, 103.8), rel=1e-12)


class TestHaversineDistanceScalarWrapper:
    def test_symmetry(self):
        assert haversine_distance(*_MBS, *_CHANGI) == pytest.approx(
            haversine_distance(*_CHANGI, *_MBS), abs=0.1
        )

    def test_non_negative_and_zero_self_distance(self):
        assert haversine_distance(1.3, 103.8, 1.3, 103.8) >= 0.0
        assert haversine_distance(1.3, 103.8, 1.3, 103.8) == pytest.approx(0.0, abs=1.0)

    def test_returns_python_float(self):
        assert isinstance(haversine_distance(1.3, 103.8, 1.31, 103.81), float)

    def test_integer_inputs_coerced(self):
        assert haversine_distance(0, 0, 0, 180) == pytest.approx(np.pi * 6_371_000, rel=1e-9)
