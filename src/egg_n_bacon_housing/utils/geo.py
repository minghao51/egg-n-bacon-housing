"""Geodesic helpers shared by the proximity and school feature modules."""

import numpy as np
import numpy.typing as npt

_EARTH_RADIUS_M = 6_371_000

__all__ = ["haversine_metres", "haversine_distance"]


def haversine_metres(
    lat1: npt.ArrayLike, lon1: npt.ArrayLike, lat2: npt.ArrayLike, lon2: npt.ArrayLike
) -> np.ndarray:
    """Vectorized great-circle distance in metres (haversine formula).

    Accepts scalars or array-likes for each coordinate; arrays broadcast
    element-wise and the result is a float ndarray. This is the single
    implementation behind ``haversine_distance`` and the proximity/school
    feature computations.
    """
    lat1_rad = np.radians(np.asarray(lat1, dtype=float))
    lon1_rad = np.radians(np.asarray(lon1, dtype=float))
    lat2_rad = np.radians(np.asarray(lat2, dtype=float))
    lon2_rad = np.radians(np.asarray(lon2, dtype=float))
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    return 2 * np.arcsin(np.sqrt(a)) * _EARTH_RADIUS_M


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Scalar great-circle distance in metres between two (lat, lon) points.

    Thin wrapper over :func:`haversine_metres` so the scalar and vectorized
    paths can never drift apart.
    """
    return float(haversine_metres(lat1, lon1, lat2, lon2))
