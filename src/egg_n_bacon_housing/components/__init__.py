"""Pipeline components (Hamilton DAG nodes)."""

import importlib as _importlib

_m01 = _importlib.import_module("egg_n_bacon_housing.components.01_ingestion")
_m02 = _importlib.import_module("egg_n_bacon_housing.components.02_cleaning")
_m03 = _importlib.import_module("egg_n_bacon_housing.components.03_features")
_m04 = _importlib.import_module("egg_n_bacon_housing.components.04_export")
_m05 = _importlib.import_module("egg_n_bacon_housing.components.05_metrics")
_m06 = _importlib.import_module("egg_n_bacon_housing.components.06_analytics")

ing = _m01
clean = _m02
feat = _m03
exp = _m04
met = _m05
an = _m06

__all__ = ["ing", "clean", "feat", "exp", "met", "an"]
