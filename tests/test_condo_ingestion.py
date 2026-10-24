"""Tests for ingestion — raw_condo_transactions (via raw_dataset) — and for the
project-aware condo geocoding two-pass strategy in the silver cleaning node."""

import pandas as pd
import pytest

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.utils.geocoding import Geocoder, plausible_project_match

pytestmark = pytest.mark.unit

CONDO_PARAMS = dict(
    resource_id="d_2fd959a62c2d04c67a5a7c7538c53ddd",
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

        result = ingestion.raw_dataset(bronze_dir=tmp_path, **CONDO_PARAMS)
        assert len(result) == 1
        assert (tmp_path / "raw_condo_transactions.parquet").exists()

    def test_raises_on_none_fetch(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: None)

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

        ingestion.raw_dataset(bronze_dir=tmp_path, **CONDO_PARAMS)
        assert calls[0] == CONDO_PARAMS["resource_id"]


def _get_cleaning_module():
    from egg_n_bacon_housing.components import cleaning

    return cleaning


class _ScriptedGeocoder(Geocoder):
    """Geocoder with canned exact-input lookups that records every query.

    Results map query string -> ``(lat, lon, matched_name, address)``.
    Unknown queries return null coordinates (an API miss); like the OneMap
    adapter's empty rows, only misses echo the input into ``address``.
    """

    def __init__(
        self,
        results: dict[str, tuple[float, float, str | None, str | None]],
    ):
        self.results = results
        self.calls: list[str] = []

    def geocode(self, addresses: pd.Series) -> pd.DataFrame:
        rows = []
        for addr in addresses:
            self.calls.append(str(addr))
            lat, lon, matched_name, address = self.results.get(str(addr), (None, None, None, None))
            hit = lat is not None
            rows.append(
                {
                    "input": addr,
                    "lat": lat,
                    "lon": lon,
                    "matched_name": matched_name,
                    "postal_code": None,
                    "address": address if hit else str(addr),
                }
            )
        return pd.DataFrame(rows)


class TestPlausibleProjectMatch:
    """Lexical acceptance rule for pass-1 project-query results."""

    def test_single_token_project_rejects_unrelated_candidate(self):
        assert not plausible_project_match(
            "SPOTTISWOODE",
            "THE INTERLACE",
            "220 DEPOT ROAD SINGAPORE 109684",
            street_name="SPOTTISWOODE PARK",
        )

    def test_single_token_project_accepts_street_corroborated_candidate(self):
        assert plausible_project_match(
            "SPOTTISWOODE",
            "SPOTTISWOODE 18",
            "18 SPOTTISWOODE PARK SINGAPORE 088568",
            street_name="SPOTTISWOODE PARK",
        )

    def test_single_token_project_rejects_sibling_suites_variant(self):
        """SUITES is significant: 'SPOTTISWOODE SUITES' is a sibling project.

        Supersedes the old expectation that "SPOTTISWOODE" accepts
        "SPOTTISWOODE SUITES" — sibling-named projects on the same street are
        exactly what the no-unexplained-tokens rule exists to reject.
        """
        assert not plausible_project_match(
            "SPOTTISWOODE",
            "SPOTTISWOODE SUITES",
            "18 SPOTTISWOODE PARK SINGAPORE 088568",
            street_name="SPOTTISWOODE PARK",
        )

    def test_sibling_towers_variant_on_same_street_rejected(self):
        """'THE TRELLIS' must not absorb sibling 'TRELLIS TOWERS' on one street."""
        assert not plausible_project_match(
            "THE TRELLIS",
            "TRELLIS TOWERS",
            "36 TRELLIS WALK SINGAPORE 368386",
            street_name="TRELLIS WALK",
        )

    def test_foreign_token_in_matched_name_rejected_despite_matching_address(self):
        """A foreign name cannot ride in on an address that carries the tokens."""
        assert not plausible_project_match(
            "THE TRELLIS",
            "WATTEN ONE",
            "36 TRELLIS WALK SINGAPORE 368386",
            street_name="TRELLIS WALK",
        )

    def test_parc_rosewood_accepts_condominium_suffix(self):
        """CONDOMINIUM is OneMap filler: 'PARC ROSEWOOD CONDOMINIUM' accepts."""
        assert plausible_project_match(
            "PARC ROSEWOOD",
            "PARC ROSEWOOD CONDOMINIUM",
            "71 WOODLANDS AVENUE 5 SINGAPORE 737437",
            street_name="WOODLANDS AVENUE 5",
        )

    def test_stopword_heavy_onemap_format_accepts(self):
        """Residence/condominium/Singapore filler never rejects a true match."""
        assert plausible_project_match(
            "THE INTERLACE",
            "INTERLACE CONDOMINIUM SINGAPORE",
            "180 DEWPAN AVENUE SINGAPORE 139695",
            street_name="DEWPAN AVENUE",
        )

    def test_weak_name_without_street_in_address_rejected(self):
        """Weak-name guard: token match alone is not enough without the street."""
        assert not plausible_project_match(
            "SPOTTISWOODE",
            "SPOTTISWOODE 18",
            "18 SOMEWHERE ELSE SINGAPORE 000000",
            street_name="SPOTTISWOODE PARK",
        )

    def test_the_terrace_accepts_the_terraces_name_variant(self):
        assert plausible_project_match(
            "THE TERRACE",
            "THE TERRACES AT PUNGGOL",
            "68 PUNGGOL WALK SINGAPORE 828763",
            street_name="PUNGGOL WALK",
        )

    def test_multi_token_project_rejects_partial_token_candidate(self):
        """'PARC' alone must not absorb 'PARC ROSE': ROSE never matches PARC."""
        assert not plausible_project_match(
            "PARC ROSE",
            "PARC",
            "1 ELIAS ROAD SINGAPORE 519954",
            street_name="ELIAS ROAD",
        )

    def test_parc_rose_accepts_rosewood_variant_when_street_corroborated(self):
        """ROSE~ROSEWOOD prefix tolerance; the street separates the homonyms."""
        assert plausible_project_match(
            "PARC ROSE",
            "PARC ROSEWOOD",
            "73 ELIAS ROAD SINGAPORE 519955",
            street_name="ELIAS ROAD",
        )

    def test_blank_or_na_project_rejected(self):
        assert not plausible_project_match(
            "", "THE INTERLACE", "220 DEPOT ROAD SINGAPORE 109684", street_name="DEPOT ROAD"
        )
        assert not plausible_project_match(
            pd.NA, "THE INTERLACE", "220 DEPOT ROAD SINGAPORE 109684", street_name="DEPOT ROAD"
        )


class TestCondoProjectGeocoding:
    """Project-aware condo geocoding in ``geocoded_properties`` (two-pass)."""

    def test_project_query_accepted_when_matched_name_contains_project(self):
        """A plausible project match wins and the street fallback is not queried."""
        cleaning = _get_cleaning_module()
        condo = pd.DataFrame(
            [{"address": "DEWPAN AVENUE", "project_name": "The Interlace", "price": 1_500_000.0}]
        )
        geocoder = _ScriptedGeocoder(
            {
                "The Interlace DEWPAN AVENUE Singapore": (
                    1.313,
                    103.812,
                    "THE INTERLACE",
                    "180 DEWPAN AVENUE SINGAPORE 139695",
                ),
                "DEWPAN AVENUE": (1.305, 103.805, "DEWPAN AVENUE", "DEWPAN AVENUE"),
            }
        )

        result = cleaning.geocoded_properties(pd.DataFrame(), condo, geocoder=geocoder)

        assert "The Interlace DEWPAN AVENUE Singapore" in geocoder.calls
        assert result.loc[0, "lat"] == pytest.approx(1.313)
        assert result.loc[0, "lon"] == pytest.approx(103.812)
        # Schema stability: the persisted address keeps its street-only value.
        assert result.loc[0, "address"] == "DEWPAN AVENUE"
        # Pass 2 is only for misses — the street fallback must not be queried.
        assert "DEWPAN AVENUE" not in geocoder.calls

    def test_implausible_road_match_rejected_and_street_fallback_used(self):
        """A road-only match for a project query is treated as a miss; pass 2 fills."""
        cleaning = _get_cleaning_module()
        condo = pd.DataFrame(
            [
                {
                    "address": "BUKIT TIMAH ROAD",
                    "project_name": "Waterfall Gardens",
                    "price": 1_400_000.0,
                }
            ]
        )
        geocoder = _ScriptedGeocoder(
            {
                "Waterfall Gardens BUKIT TIMAH ROAD Singapore": (
                    1.331,
                    103.807,
                    "BUKIT TIMAH ROAD",
                    "BUKIT TIMAH ROAD SINGAPORE",
                ),
                "BUKIT TIMAH ROAD": (1.332, 103.808, "BUKIT TIMAH ROAD", "BUKIT TIMAH ROAD"),
            }
        )

        result = cleaning.geocoded_properties(pd.DataFrame(), condo, geocoder=geocoder)

        assert geocoder.calls == [
            "Waterfall Gardens BUKIT TIMAH ROAD Singapore",
            "BUKIT TIMAH ROAD",
        ]
        assert result.loc[0, "lat"] == pytest.approx(1.332)
        assert result.loc[0, "lon"] == pytest.approx(103.808)
        assert result.loc[0, "address"] == "BUKIT TIMAH ROAD"

    def test_missing_project_name_geocodes_street_only(self):
        """No project_name column: condos go straight to the street-only pass."""
        cleaning = _get_cleaning_module()
        condo = pd.DataFrame([{"address": "CONDO STREET", "price": 1_500_000.0}])
        geocoder = _ScriptedGeocoder({"CONDO STREET": (1.30, 103.80, "CONDO STREET", None)})

        result = cleaning.geocoded_properties(pd.DataFrame(), condo, geocoder=geocoder)

        assert geocoder.calls == ["CONDO STREET"]
        assert result.loc[0, "lat"] == pytest.approx(1.30)

    def test_blank_or_null_project_name_geocodes_street_only(self):
        """Blank/NA project names fall through to the street-only pass like no column."""
        cleaning = _get_cleaning_module()
        condo = pd.DataFrame(
            [
                {"address": "STREET A", "project_name": "", "price": 1_500_000.0},
                {"address": "STREET B", "project_name": pd.NA, "price": 1_600_000.0},
            ]
        )
        geocoder = _ScriptedGeocoder(
            {
                "STREET A": (1.30, 103.80, "STREET A", None),
                "STREET B": (1.31, 103.81, "STREET B", None),
            }
        )

        result = cleaning.geocoded_properties(pd.DataFrame(), condo, geocoder=geocoder)

        assert geocoder.calls == ["STREET A", "STREET B"]
        assert result.loc[0, "lat"] == pytest.approx(1.30)
        assert result.loc[1, "lat"] == pytest.approx(1.31)

    def test_hdb_block_street_string_reaches_geocoder(self):
        """HDB path unchanged: the block + street address is the geocode query."""
        cleaning = _get_cleaning_module()
        hdb = pd.DataFrame([{"address": "123A LORONG 1 TOA PAYOH", "price": 500_000.0}])
        geocoder = _ScriptedGeocoder(
            {"123A LORONG 1 TOA PAYOH": (1.352, 103.855, "123A LORONG 1 TOA PAYOH", None)}
        )

        result = cleaning.geocoded_properties(hdb, pd.DataFrame(), geocoder=geocoder)

        assert geocoder.calls == ["123A LORONG 1 TOA PAYOH"]
        assert result.loc[0, "lat"] == pytest.approx(1.352)
        assert result.loc[0, "lon"] == pytest.approx(103.855)

    def test_condo_coverage_gate_fails_below_threshold(self):
        """The lenient condo coverage gate still fails on implausible-heavy runs."""
        cleaning = _get_cleaning_module()
        condo = pd.DataFrame(
            [
                {
                    "address": f"CONDOSTREET {i}",
                    "project_name": f"Project {i}",
                    "price": 1_500_000.0,
                }
                for i in range(10)
            ]
        )
        results = {
            # 2 plausible project matches; the other 8 return road-only matches.
            **{
                f"Project {i} CONDOSTREET {i} Singapore": (
                    1.3 + i / 100,
                    103.8 + i / 100,
                    f"PROJECT {i}",
                    f"1 CONDOSTREET {i} SINGAPORE 123456",
                )
                for i in range(2)
            },
            **{
                f"Project {i} CONDOSTREET {i} Singapore": (
                    1.4,
                    103.9,
                    "CONDOSTREET ROAD",
                    None,
                )
                for i in range(2, 10)
            },
        }
        geocoder = _ScriptedGeocoder(results)

        with pytest.raises(ValueError, match="condo 20.0% < threshold 30.0%"):
            cleaning.geocoded_properties(pd.DataFrame(), condo, geocoder=geocoder)

    def test_condo_coverage_gate_passes_when_plausible_plus_fallback_cover(self):
        """Plausible pass-1 hits plus pass-2 street fallbacks satisfy the gate."""
        cleaning = _get_cleaning_module()
        condo = pd.DataFrame(
            [
                {
                    "address": f"CONDOSTREET {i}",
                    "project_name": f"Project {i}",
                    "price": 1_500_000.0,
                }
                for i in range(10)
            ]
        )
        results = {
            **{
                f"Project {i} CONDOSTREET {i} Singapore": (
                    1.3 + i / 100,
                    103.8 + i / 100,
                    f"PROJECT {i}",
                    f"1 CONDOSTREET {i} SINGAPORE 123456",
                )
                for i in range(4)
            },
            **{
                f"Project {i} CONDOSTREET {i} Singapore": (
                    1.4,
                    103.9,
                    "CONDOSTREET ROAD",
                    None,
                )
                for i in range(4, 10)
            },
            # Pass-2 street fallback recovers 4 of the 6 implausible rows.
            **{
                f"CONDOSTREET {i}": (1.32 + i / 100, 103.82 + i / 100, f"CONDOSTREET {i}", None)
                for i in range(4, 8)
            },
        }
        geocoder = _ScriptedGeocoder(results)

        result = cleaning.geocoded_properties(pd.DataFrame(), condo, geocoder=geocoder)

        # 4 plausible pass-1 hits + 4 pass-2 street hits = 80% coverage.
        assert result[["lat", "lon"]].notna().all(axis=1).mean() == pytest.approx(0.8)
