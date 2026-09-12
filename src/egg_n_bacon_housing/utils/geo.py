"""Geodesic helpers shared by the proximity and school feature modules."""

import numpy as np

_EARTH_RADIUS_M = 6_371_000

__all__ = ["haversine_metres", "haversine_distance"]


def haversine_metres(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """Vectorized great-circle distance in metres (haversine formula).

    Accepts scalars or array-likes for each coordinate; arrays broadcast
    element-wise and the result is a float ndarray. This is the single
    implementation behind ``haversine_distance`` and the proximity/school
    feature computations.
    """
    lat1, lon1, lat2, lon2 = (
        np.radians(np.asarray(a, dtype=float)) for a in (lat1, lon1, lat2, lon2)
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * np.arcsin(np.sqrt(a)) * _EARTH_RADIUS_M


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Scalar great-circle distance in metres between two (lat, lon) points.

    Thin wrapper over :func:`haversine_metres` so the scalar and vectorized
    paths can never drift apart.
    """
    return float(haversine_metres(lat1, lon1, lat2, lon2))
