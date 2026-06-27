"""Housing market metrics — affordability classification.

Only ``classify_affordability`` is exposed; it is consumed by the Hamilton DAG
node in ``components/metrics.py``. The legacy analytics chain (price strata,
stratified median, PSF, volume, momentum, monthly metrics) lived here previously
but had no callers -- the live DAG computes those metrics via dedicated nodes.
"""

_DEFAULT_AFFORDABILITY_THRESHOLDS: dict[str, float] = {
    "affordable": 5.0,
    "moderate": 7.0,
    "expensive": 9.0,
}


def classify_affordability(ratio: float, thresholds: dict[str, float] | None = None) -> str:
    """Classify affordability based on ratio.

    Args:
        ratio: Affordability ratio
        thresholds: Optional thresholds dict with keys 'affordable',
            'moderate', 'expensive'. Defaults to standard Singapore thresholds.

    Returns:
        Classification string
    """
    if thresholds is None:
        thresholds = _DEFAULT_AFFORDABILITY_THRESHOLDS
    if ratio < thresholds["affordable"]:
        return "Affordable"
    if ratio < thresholds["moderate"]:
        return "Moderate"
    if ratio < thresholds["expensive"]:
        return "Expensive"
    return "Severely Unaffordable"
