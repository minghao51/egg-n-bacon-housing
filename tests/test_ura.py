"""Tests for the URA Data Service adapter and condo bronze merge.

All transport is mocked — no test here talks to the live URA API.
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests
from requests import RequestException

from egg_n_bacon_housing.adapters import ura
from egg_n_bacon_housing.adapters.exceptions import (
    CredentialError,
    DatasetFetchError,
    URAAuthError,
)
from egg_n_bacon_housing.components.ingestion.ura_csv import (
    _normalize_ura_api_rows,
    raw_condo_transactions,
)

pytestmark = pytest.mark.unit

ACCESS_KEY = "test-access-key"
TOKEN = "test-token"


def _response(payload=None, *, status=200, text=None, content_type="application/json"):
    response = MagicMock()
    response.status_code = status
    response.headers = {"content-type": content_type}
    if payload is not None:
        response.text = json.dumps(payload)
        response.json.return_value = payload
    else:
        response.text = text or ""
        if text is not None and content_type == "application/json":
            response.json.return_value = json.loads(text)
    response.raise_for_status.side_effect = (
        RequestException(f"HTTP {status}") if status >= 400 else None
    )
    return response


def _mock_session_get(handler):
    """Patch requests.Session.get; handler gets (url, headers, params)."""

    def side_effect(url, headers=None, params=None, timeout=None):
        return handler(url, headers or {}, params or {})

    return patch.object(requests.Session, "get", side_effect=side_effect)


class TestFetchUraToken:
    def test_returns_result_field(self):
        with _mock_session_get(
            lambda url, headers, params: _response({"Status": "Success", "Result": TOKEN})
        ):
            assert ura.fetch_ura_token(ACCESS_KEY, use_cache=False) == TOKEN

    def test_session_sends_browser_headers(self):
        session = ura._get_session()
        assert "Mozilla" in session.headers["User-Agent"]
        assert session.headers["Accept"].startswith("application/json")
        assert "eservice.ura.gov.sg" in session.headers["Referer"]

    def test_missing_key_raises_credential_error(self):
        with pytest.raises(CredentialError, match="URA_API_ACCESS_KEY"):
            ura.fetch_ura_token("", use_cache=False)

    def test_invalid_key_raises_ura_auth_error(self):
        payload = {"Status": "Error", "Message": "Invalid Access Key"}
        with _mock_session_get(lambda url, headers, params: _response(payload)):
            with pytest.raises(URAAuthError, match="Invalid Access Key"):
                ura.fetch_ura_token(ACCESS_KEY, use_cache=False)

    def test_cached_path_uses_cached_call(self):
        with patch.object(ura, "cached_call", return_value=TOKEN) as mock_cache:
            assert ura.fetch_ura_token(ACCESS_KEY, use_cache=True, cache_manager=object()) == TOKEN
        mock_cache.assert_called_once()
        assert mock_cache.call_args.kwargs["duration_hours"] == ura._TOKEN_CACHE_HOURS

    def test_token_cache_id_is_per_access_key(self):
        """Cache ids must differ per access key so rotation never serves a wrong-key token."""
        id_a = ura._token_cache_id("key-a")
        id_b = ura._token_cache_id("key-b")
        assert id_a != id_b
        assert id_a.startswith("ura_api_token:")
        assert id_b.startswith("ura_api_token:")

    def test_two_access_keys_get_distinct_cache_entries(self, tmp_path):
        """Two different access keys produce two cache entries; a repeat of the
        first key is served from cache without another token request."""
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")
        manager = cache.CacheManager(tmp_path, use_caching=True)

        seen_keys = []

        def handler(url, headers, params):
            seen_keys.append(headers.get("AccessKey"))
            key = headers.get("AccessKey")
            return _response({"Status": "Success", "Result": f"token-for-{key}"})

        with _mock_session_get(handler):
            token_a1 = ura.fetch_ura_token("key-a", cache_manager=manager)
            token_b = ura.fetch_ura_token("key-b", cache_manager=manager)
            token_a2 = ura.fetch_ura_token("key-a", cache_manager=manager)

        assert token_a1 == "token-for-key-a"
        assert token_b == "token-for-key-b"
        assert token_a2 == "token-for-key-a"  # served from cache, not re-fetched
        assert seen_keys == ["key-a", "key-b"]  # key-a fetched exactly once
        assert len(list(tmp_path.glob("*.json"))) == 2  # two distinct entries


class TestFetchResiTransactions:
    def _rows_payload(self):
        return {
            "Status": "Success",
            "Result": [
                {
                    "project": "TEST CONDO",
                    "street": "TEST STREET",
                    "marketSegment": "OCR",
                    "transaction": [
                        {
                            "area": "100",
                            "contractDate": "0522",
                            "price": "1000000",
                            "propertyType": "Condominium",
                            "typeOfArea": "Strata",
                            "typeOfSale": "3",
                            "district": "19",
                            "floorRange": "04-06",
                            "noOfUnits": "1",
                            "tenure": "99 yrs lease commencing from 2007",
                        }
                    ],
                }
            ],
        }

    def test_happy_path_sends_service_and_batch(self):
        seen = {}

        def handler(url, headers, params):
            seen["url"] = url
            seen["params"] = params
            seen["headers"] = headers
            return _response(self._rows_payload())

        with _mock_session_get(handler):
            rows = ura.fetch_resi_transactions(ACCESS_KEY, TOKEN, batch=2)
        assert len(rows) == 1
        assert seen["params"] == {"service": "PMI_Resi_Transaction", "batch": "2"}
        assert seen["headers"]["Token"] == TOKEN
        assert seen["headers"]["AccessKey"] == ACCESS_KEY

    def test_invalid_token_raises_ura_auth_error(self):
        payload = {"Status": "Error", "Message": "Invalid token"}
        with _mock_session_get(lambda url, headers, params: _response(payload)):
            with pytest.raises(URAAuthError, match="Invalid token"):
                ura.fetch_resi_transactions(ACCESS_KEY, TOKEN, batch=1)

    def test_other_error_is_dataset_fetch_error_not_auth(self):
        payload = {"Status": "Error", "Message": "Invalid service."}
        with _mock_session_get(lambda url, headers, params: _response(payload)):
            with pytest.raises(DatasetFetchError, match="Invalid service"):
                ura.fetch_resi_transactions(ACCESS_KEY, TOKEN, batch=1)

    def test_non_json_response_raises(self):
        response = _response(text="<html>challenge</html>", content_type="text/html")
        response.json.side_effect = ValueError("no json")
        with patch.object(requests.Session, "get", return_value=response):
            with pytest.raises(DatasetFetchError, match="non-JSON"):
                ura.fetch_resi_transactions(ACCESS_KEY, TOKEN, batch=1)

    def test_retries_429_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("tenacity.nap.sleep", lambda _s: None)
        responses = iter(
            [
                _response(status=429),
                _response(status=429),
                _response({"Status": "Success", "Result": []}),
            ]
        )

        with patch.object(requests.Session, "get", side_effect=lambda *a, **kw: next(responses)):
            rows = ura.fetch_resi_transactions(ACCESS_KEY, TOKEN, batch=1)
        assert rows == []

    def test_exhausted_retries_raise(self, monkeypatch):
        monkeypatch.setattr("tenacity.nap.sleep", lambda _s: None)
        with patch.object(requests.Session, "get", return_value=_response(status=503)):
            with pytest.raises(RequestException):
                ura.fetch_resi_transactions(ACCESS_KEY, TOKEN, batch=1)


class TestFetchAllResiTransactions:
    def _ok(self, batch_marker):
        return _response({"Status": "Success", "Result": [{"batch": batch_marker}]})

    def test_fetches_all_batches(self):
        calls = []

        def handler(url, headers, params):
            calls.append(params["batch"])
            return self._ok(params["batch"])

        with patch.object(ura, "fetch_ura_token", return_value=TOKEN):
            with _mock_session_get(handler):
                rows = ura.fetch_all_resi_transactions(ACCESS_KEY, use_cache=False)
        assert calls == ["1", "2", "3", "4"]
        assert [r["batch"] for r in rows] == ["1", "2", "3", "4"]

    def test_refreshes_token_once_on_auth_error(self):
        def fetch_resi(access_key, token, batch, session=None):
            if token == "stale-token":
                raise URAAuthError("Invalid token")
            return [{"batch": batch}]

        token_mock = patch.object(
            ura, "fetch_ura_token", side_effect=["stale-token", "fresh-token"]
        )
        with token_mock as token_calls:
            with patch.object(ura, "fetch_resi_transactions", side_effect=fetch_resi):
                rows = ura.fetch_all_resi_transactions(ACCESS_KEY, use_cache=False)
        assert [r["batch"] for r in rows] == [1, 2, 3, 4]
        assert token_calls.call_count == 2  # initial + one refresh

    def test_refreshed_token_written_back_to_cache(self, tmp_path):
        """T5: a force-refreshed token must replace the rejected cached one.

        Without the write-back, the stale token stays cached for its full TTL
        and every run repeats the reject+refresh cycle. Here run 2 must be
        served the refreshed token from cache with no second auth failure."""
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")
        manager = cache.CacheManager(tmp_path, use_caching=True)
        # Seed the cache with the token URA is about to reject.
        manager.set(ura._token_cache_id(ACCESS_KEY), "stale-token")

        token_calls: list[str] = []
        rejected: list[str] = []

        def handler(url, headers, params):
            if "insertNewToken" in url:
                token_calls.append(headers.get("AccessKey"))
                return _response({"Status": "Success", "Result": "fresh-token"})
            if headers.get("Token") == "stale-token":
                rejected.append(params["batch"])
                return _response({"Status": "Error", "Message": "Invalid token"})
            return self._ok(params["batch"])

        with _mock_session_get(handler):
            first = ura.fetch_all_resi_transactions(ACCESS_KEY, cache_manager=manager)
            second = ura.fetch_all_resi_transactions(ACCESS_KEY, cache_manager=manager)

        assert [r["batch"] for r in first] == ["1", "2", "3", "4"]
        assert [r["batch"] for r in second] == ["1", "2", "3", "4"]
        assert rejected == ["1"]  # run 1 rejected once; run 2 had no auth failure
        assert token_calls == [ACCESS_KEY]  # token fetched once, then cache-served

    def test_forced_no_cache_run_does_not_write_token_back(self, tmp_path):
        """use_cache=False bypasses the cache entirely — not even a refreshed
        token is written back."""
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")
        manager = cache.CacheManager(tmp_path, use_caching=True)

        tokens = iter(["flaky-token", "fresh-token"])

        def handler(url, headers, params):
            if "insertNewToken" in url:
                return _response({"Status": "Success", "Result": next(tokens)})
            if headers.get("Token") == "flaky-token":
                return _response({"Status": "Error", "Message": "Invalid token"})
            return self._ok(params["batch"])

        with _mock_session_get(handler):
            rows = ura.fetch_all_resi_transactions(
                ACCESS_KEY, use_cache=False, cache_manager=manager
            )

        assert [r["batch"] for r in rows] == ["1", "2", "3", "4"]
        assert list(tmp_path.glob("*.json")) == []  # nothing written to the cache

    def test_second_auth_error_propagates(self):
        with patch.object(ura, "fetch_ura_token", return_value=TOKEN):
            with patch.object(
                ura,
                "fetch_resi_transactions",
                side_effect=URAAuthError("Invalid token"),
            ):
                with pytest.raises(URAAuthError):
                    ura.fetch_all_resi_transactions(ACCESS_KEY, use_cache=False)

    def test_missing_key_raises(self):
        with pytest.raises(CredentialError):
            ura.fetch_all_resi_transactions("")


class TestNormalizeUraApiRows:
    def _entry(self, *, market_segment="OCR", **tx_overrides):
        tx = {
            "area": "100",
            "contractDate": "0522",
            "price": "1000000",
            "typeOfArea": "Strata",
            "typeOfSale": "3",
            "district": "19",
            "floorRange": "04-06",
            "noOfUnits": "1",
            "tenure": "99 yrs lease commencing from 2007",
            "propertyType": "Condominium",
        }
        tx.update(tx_overrides)
        return {
            "project": "TEST CONDO",
            "street": "TEST STREET",
            "marketSegment": market_segment,
            "transaction": [tx],
        }

    def test_strata_area_maps_to_sqft(self):
        df = _normalize_ura_api_rows([self._entry()])
        row = df.iloc[0]
        assert row["area_sqft"] == 100.0
        assert row["area_sqm"] == pytest.approx(100 / 10.7639)
        assert row["unit_price_psf"] == pytest.approx(10000.0)

    def test_land_area_maps_to_sqm(self):
        df = _normalize_ura_api_rows([self._entry(typeOfArea="Land", area="257")])
        row = df.iloc[0]
        assert row["area_sqm"] == 257.0
        assert row["area_sqft"] == pytest.approx(257 * 10.7639)

    def test_contract_date_mmyy(self):
        df = _normalize_ura_api_rows([self._entry(contractDate="0123")])
        assert df.iloc[0]["transaction_date"] == pd.Timestamp("2023-01-01")

    def test_code_mappings(self):
        df = _normalize_ura_api_rows([self._entry(typeOfSale="1", market_segment="CCR")])
        row = df.iloc[0]
        assert row["type_of_sale"] == "New Sale"
        assert row["market_segment"] == "Core Central Region"
        assert row["property_type"] == "condo"
        assert row["property_subtype"] == "Condominium"
        assert row["floor_level"] == "04 to 06"

    def test_dash_floor_range_preserved(self):
        df = _normalize_ura_api_rows([self._entry(floorRange="-")])
        assert df.iloc[0]["floor_level"] == "-"

    def test_bad_contract_date_dropped(self):
        df = _normalize_ura_api_rows([self._entry(contractDate="xxxx")])
        assert df.empty

    def test_unparseable_dates_dropped_with_count_warning(self, caplog):
        """WO-7: transaction rows lost to unparseable contractDate are counted."""
        import logging

        entries = [
            self._entry(contractDate="0124"),
            self._entry(contractDate="xxxx"),
            self._entry(contractDate="alsobad"),
        ]

        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.components.ingestion.ura_csv"
        ):
            df = _normalize_ura_api_rows(entries)

        assert len(df) == 1
        warnings = [r for r in caplog.records if "unparseable" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        assert warnings[0].levelno == logging.WARNING
        message = warnings[0].getMessage()
        assert "dropped 2/3 row(s)" in message
        assert "kept 1" in message

    def test_all_parseable_dates_do_not_warn(self, caplog):
        import logging

        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.components.ingestion.ura_csv"
        ):
            df = _normalize_ura_api_rows([self._entry(contractDate="0124")])

        assert len(df) == 1
        assert not [r for r in caplog.records if "unparseable" in r.getMessage()]

    def test_empty_rows(self):
        assert _normalize_ura_api_rows([]).empty

    def test_sqft_conversion_uses_shared_constant(self):
        """WS14: the local _SQFT_PER_SQM was replaced by hdb_lookups.SQFT_PER_SQM."""
        from egg_n_bacon_housing.components.ingestion import ura_csv
        from egg_n_bacon_housing.utils.hdb_lookups import SQFT_PER_SQM

        assert ura_csv.SQFT_PER_SQM is SQFT_PER_SQM
        assert SQFT_PER_SQM == 10.7639


class TestRawCondoTransactionsLiveMerge:
    def _bronze(self, tmp_path):
        """Bronze dir whose sibling manual dir is tmp_path/manual."""
        bronze = tmp_path / "pipeline" / "01_bronze"
        bronze.mkdir(parents=True, exist_ok=True)
        return bronze

    def _write_csv(self, tmp_path, price="1,000,000", sale_date="Jan-25"):
        csv_path = tmp_path / "manual" / "csv" / "ura"
        csv_path.mkdir(parents=True, exist_ok=True)
        (csv_path / "ResidentialTransaction2025.csv").write_text(
            "Project Name,Transacted Price ($),Area (SQFT),Sale Date,Street Name,"
            "Type of Sale,Number of Units,Tenure,Postal District,Market Segment,"
            "Floor Level,Type of Area,Area (SQM),Unit Price ($ PSF),Unit Price ($ PSM),"
            "Nett Price($),Property Type\n"
            f'OLD CONDO,"{price}",1000,{sale_date},OLD STREET,Resale,1,'
            "99 yrs lease commencing from 2007,19,Outside Central Region,01 to 03,"
            "Strata,92.9,1000,10764,-,Condominium\n"
        )

    def _write_ec_csv(self, tmp_path):
        csv_path = tmp_path / "manual" / "csv" / "ura"
        csv_path.mkdir(parents=True, exist_ok=True)
        (csv_path / "ECResidentialTransaction2025.csv").write_text(
            "Project Name,Transacted Price ($),Area (SQFT),Sale Date,Street Name,"
            "Type of Sale,Number of Units,Floor Level\n"
            'TEST EC,"1,200,000",900,Feb-25,EC STREET,Resale,1,07 to 09\n'
        )

    def _api_rows(self):
        """Raw URA API-shaped rows (the node normalizes them itself)."""
        return [
            {
                "project": "OLD CONDO",
                "street": "OLD STREET",
                "marketSegment": "OCR",
                "transaction": [
                    {
                        "area": "1000",
                        "contractDate": "0125",
                        "price": "1000000",
                        "typeOfArea": "Strata",
                        "typeOfSale": "3",
                        "district": "19",
                        "floorRange": "01-03",
                        "noOfUnits": "1",
                        "tenure": "99 yrs lease commencing from 2007",
                    }
                ],
            },
            {
                "project": "NEW CONDO",
                "street": "NEW STREET",
                "marketSegment": "RCR",
                "transaction": [
                    {
                        "area": "800",
                        "contractDate": "0726",
                        "price": "1600000",
                        "typeOfArea": "Strata",
                        "typeOfSale": "1",
                        "district": "12",
                        "floorRange": "-",
                        "noOfUnits": "1",
                        "tenure": "Freehold",
                    }
                ],
            },
        ]

    def test_merges_api_with_csv_and_dedupes(self, tmp_path):
        bronze = self._bronze(tmp_path)
        self._write_csv(tmp_path)
        with patch.object(ura, "fetch_all_resi_transactions", return_value=self._api_rows()):
            result = raw_condo_transactions(
                bronze, manual_dir=tmp_path / "manual", ura_api_access_key=ACCESS_KEY
            )

        # CSV row + overlapping API row dedupe to ONE; fresh API row survives.
        assert len(result) == 2
        assert set(result["project_name"]) == {"OLD CONDO", "NEW CONDO"}
        assert (bronze / "raw_condo_transactions.parquet").exists()

    def test_csv_only_when_no_key(self, tmp_path):
        bronze = self._bronze(tmp_path)
        self._write_csv(tmp_path)
        with patch.object(
            ura, "fetch_all_resi_transactions", side_effect=AssertionError("must not fetch")
        ):
            result = raw_condo_transactions(
                bronze, manual_dir=tmp_path / "manual", ura_api_access_key=""
            )
        assert list(result["project_name"]) == ["OLD CONDO"]
        assert result.iloc[0]["property_subtype"] == "Condominium"

    def test_ec_csv_is_included_with_preserved_subtype(self, tmp_path):
        bronze = self._bronze(tmp_path)
        self._write_csv(tmp_path)
        self._write_ec_csv(tmp_path)

        result = raw_condo_transactions(
            bronze, manual_dir=tmp_path / "manual", ura_api_access_key=""
        )

        assert set(result["project_name"]) == {"OLD CONDO", "TEST EC"}
        ec_row = result[result["project_name"] == "TEST EC"].iloc[0]
        assert ec_row["property_type"] == "condo"
        assert ec_row["property_subtype"] == "Executive Condominium"

    def test_api_failure_falls_back_to_csv(self, tmp_path):
        bronze = self._bronze(tmp_path)
        self._write_csv(tmp_path)
        with patch.object(
            ura,
            "fetch_all_resi_transactions",
            side_effect=DatasetFetchError("URA down"),
        ):
            result = raw_condo_transactions(
                bronze, manual_dir=tmp_path / "manual", ura_api_access_key=ACCESS_KEY
            )
        assert list(result["project_name"]) == ["OLD CONDO"]

    def test_api_only_when_no_csvs(self, tmp_path):
        bronze = self._bronze(tmp_path)
        with patch.object(ura, "fetch_all_resi_transactions", return_value=self._api_rows()):
            result = raw_condo_transactions(
                bronze, manual_dir=tmp_path / "manual", ura_api_access_key=ACCESS_KEY
            )
        assert set(result["project_name"]) == {"OLD CONDO", "NEW CONDO"}

    def test_no_csvs_and_no_key_raises(self, tmp_path):
        bronze = self._bronze(tmp_path)
        with pytest.raises(RuntimeError, match="condo_resale"):
            raw_condo_transactions(bronze, manual_dir=tmp_path / "manual", ura_api_access_key="")

    def test_empty_api_response_falls_back_to_csv(self, tmp_path):
        bronze = self._bronze(tmp_path)
        self._write_csv(tmp_path)
        with patch.object(ura, "fetch_all_resi_transactions", return_value=[]):
            result = raw_condo_transactions(
                bronze, manual_dir=tmp_path / "manual", ura_api_access_key=ACCESS_KEY
            )
        assert list(result["project_name"]) == ["OLD CONDO"]
