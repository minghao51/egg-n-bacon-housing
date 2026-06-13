"""Tests for utils/data_helpers.py."""

import importlib

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _get_data_helpers_module():
    return importlib.import_module("egg_n_bacon_housing.utils.data_helpers")


def test_load_parquet_falls_back_to_filesystem_without_metadata(tmp_path, monkeypatch):
    helpers = _get_data_helpers_module()
    pipeline_dir = tmp_path / "pipeline"
    platinum_dir = pipeline_dir / "04_platinum"
    platinum_dir.mkdir(parents=True)

    pd.DataFrame([{"marker": "filesystem"}]).to_parquet(
        platinum_dir / "housing_unified.parquet",
        index=False,
    )

    monkeypatch.setattr(helpers, "PARQUETS_DIR", pipeline_dir)
    monkeypatch.setattr(helpers, "METADATA_FILE", tmp_path / "metadata.json")

    result = helpers.load_parquet("L3_housing_unified")

    assert result.loc[0, "marker"] == "filesystem"


def test_save_parquet_uses_current_medallion_layout(tmp_path, monkeypatch):
    helpers = _get_data_helpers_module()
    pipeline_dir = tmp_path / "pipeline"
    monkeypatch.setattr(helpers, "PARQUETS_DIR", pipeline_dir)
    monkeypatch.setattr(helpers, "METADATA_FILE", tmp_path / "metadata.json")

    df = pd.DataFrame([{"town": "Toa Payoh"}])

    helpers.save_parquet(df, "L1_housing_ec_transaction", source="test")

    assert (pipeline_dir / "02_silver" / "housing_ec_transaction.parquet").exists()
