"""Tests for ingestion — raw_condo_transactions (via raw_dataset)."""

import pandas as pd
import pytest

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.components.ingestion import datagov as datagov_nodes

pytestmark = pytest.mark.unit

CONDO_PARAMS = dict(
    resource_id="d_2fd959a62c2d04c67a5a7c7538c53ddd",
    cache_id="bronze_condo_raw",
    cache_filenames=("raw_condo_transactions.parquet",),
    display_name="condo",
    error_name="condo_resale",
)


def _get_ingestion_module():
    from egg_n_bacon_housing.components import ingestion

    return ingestion


class TestRawCondoTransactions:
    def test_prefers_bronze_cache(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        expected = pd.DataFrame([{"price": 800000, "date": "2024-01"}])
        tmp_path.mkdir(parents=True, exist_ok=True)
        expected.to_parquet(tmp_path / "raw_condo_transactions.parquet", index=False)

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pytest.fail("should not fetch when cache exists"),
        )

        result = ingestion.raw_dataset(bronze_dir=tmp_path, **CONDO_PARAMS)
        pd.testing.assert_frame_equal(result, expected)

    def test_raises_on_empty_fetch(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pd.DataFrame(),
        )

        with pytest.raises(RuntimeError, match="Core dataset fetch failed: condo_resale"):
            ingestion.raw_dataset(bronze_dir=tmp_path, **CONDO_PARAMS)

    def test_fetches_and_caches(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        fetched_data = pd.DataFrame([{"price": 900000, "date": "2024-03"}])

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: fetched_data)
        monkeypatch.setattr(datagov_nodes, "cached_call", lambda cache_id, fn: fn())

        result = ingestion.raw_dataset(bronze_dir=tmp_path, **CONDO_PARAMS)
        assert len(result) == 1
        assert (tmp_path / "raw_condo_transactions.parquet").exists()

    def test_raises_on_none_fetch(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: None)
        monkeypatch.setattr(datagov_nodes, "cached_call", lambda cache_id, fn: fn())

        with pytest.raises(RuntimeError, match="Core dataset fetch failed: condo_resale"):
            ingestion.raw_dataset(bronze_dir=tmp_path, **CONDO_PARAMS)

    def test_uses_condo_resale_dataset_id(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        calls = []
        fetched_data = pd.DataFrame([{"price": 1}])

        def tracking_fetch(url, dataset_id, use_cache=False):
            calls.append(dataset_id)
            return fetched_data

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", tracking_fetch)
        monkeypatch.setattr(datagov_nodes, "cached_call", lambda cache_id, fn: fn())

        ingestion.raw_dataset(bronze_dir=tmp_path, **CONDO_PARAMS)
        assert calls[0] == CONDO_PARAMS["resource_id"]
