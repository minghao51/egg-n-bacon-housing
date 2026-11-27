"""Live (real-network) validation of data.gov.sg pagination completeness (WS-A2).

These tests answer one question with real data rather than mocks: **is the new
hard failure in :func:`fetch_datagovsg_dataset` safe against the datasets this
repo actually ingests?** The adapter now raises
:class:`IncompleteDatasetFetchError` when the rows obtainable by following
``_links.next`` are fewer than the ``total`` a page advertises. That is only safe
if every ingested dataset really does serve exactly ``total`` rows across its
next-chain — including the two large ones (HDB rental, HDB resale) and the wide
ones that answer HTTP 413 above a certain ``limit``.

The tests are hermetic by default: ``pytestmark`` skips this whole module unless
``EGG_LIVE=1`` is set, so ``uv run pytest tests/ -q`` never touches the network.

Run them:

    EGG_LIVE=1 uv run pytest tests/ -m live -q --no-cov

Add ``EGG_LIVE_DEEP=1`` to include the full next-chain walk of every dataset
(the ``advertised total vs rows fetched`` table). It is opt-in because the two
large datasets take ~10 minutes of paced requests:

    EGG_LIVE=1 EGG_LIVE_DEEP=1 uv run pytest tests/test_live_datagovsg.py -m live \
        -q --no-cov -s

Requests are paced (``EGG_LIVE_PAUSE_SECONDS``, default 1.0s) and 429s are
retried with ``Retry-After`` — data.gov.sg rate-limits a few requests per minute
and a burst gets throttled.
"""

import os
import threading
import time
from dataclasses import dataclass

import pytest
import requests

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.adapters.exceptions import (
    DatasetFetchError,
    IncompleteDatasetFetchError,
)

_LIVE = os.environ.get("EGG_LIVE") == "1"
_DEEP = os.environ.get("EGG_LIVE_DEEP") == "1"

pytestmark = [
    pytest.mark.live,
    pytest.mark.api,
    pytest.mark.skipif(
        not _LIVE,
        reason="live network tests are opt-in: set EGG_LIVE=1 to run against data.gov.sg",
    ),
]

# Largest ``limit`` data.gov.sg serves. Above it the API answers 413 for
# datasets with wide rows, so the probe halves down like the adapter does.
_PAGE_LIMIT = 10_000
_MIN_PAGE_LIMIT = 250

_PAUSE_SECONDS = float(os.environ.get("EGG_LIVE_PAUSE_SECONDS", "1.0"))
_MAX_ATTEMPTS = 6
_MAX_RETRY_AFTER = 30.0


@dataclass(frozen=True)
class IngestedDataset:
    """One data.gov.sg resource this repo ingests, with its provenance."""

    resource_id: str
    node: str
    source: str


# Every resource_id the pipeline fetches through ``fetch_datagovsg_dataset``:
# the ``@parameterize``d core datasets in components/ingestion/datagov.py, the
# module-level constants there and in macro.py, and the train-station codes in
# geojson.py. Keep this list in step with those modules — a dataset that starts
# being ingested but is not probed here is a pagination risk nobody measured.
INGESTED_DATASETS: tuple[IngestedDataset, ...] = (
    IngestedDataset("d_8e4c50283fb7052a391dfb746a05c853", "raw_rental_index", "datagov.py:129"),
    IngestedDataset("d_c9f57187485a850908655db0e8cfe651", "raw_hdb_rental", "datagov.py:135"),
    IngestedDataset("d_688b934f82c1059ed0a6993d2a829089", "raw_school_directory", "datagov.py:141"),
    IngestedDataset("d_8b84c4ee58e3cfc0ece0d773c8ca6abc", "raw_hdb_resale", "datagov.py:54"),
    IngestedDataset("d_17f5382f26140b1fdae0ba2ef6239d2f", "raw_hdb_property_info", "datagov.py:56"),
    IngestedDataset(
        "d_bb771c5189ce18007621533dd36142bb", "raw_income_by_planning_area", "datagov.py:57"
    ),
    IngestedDataset(
        "d_c4bd082b48fa7611713f39e23d250c27", "raw_green_mark_buildings", "datagov.py:58"
    ),
    IngestedDataset(
        "d_07b1eeeb22efdf7faf5bd6a13667359d", "raw_dwelling_units_by_town", "datagov.py:59"
    ),
    IngestedDataset(
        "d_48143be392f1ed22f0700835212e5a60", "raw_median_annual_value", "datagov.py:60"
    ),
    IngestedDataset(
        "d_0a6c6d71f6fa14e2d27e406f1d018439", "raw_hdb_resident_population", "datagov.py:61"
    ),
    IngestedDataset(
        "d_d312a5b127e1ae74299b8ae664cedd4e", "raw_train_station_codes", "geojson.py:204"
    ),
    IngestedDataset("d_bdaff844e3ef89d39fceb962ff8f0791", "macro_cpi", "macro.py:39"),
    IngestedDataset("d_a5ff719648a0e6d4b4c623ee383ab686", "macro_gdp", "macro.py:40"),
    IngestedDataset("d_b0da22a41f952764376a2b7b5b0f2533", "macro_unemployment", "macro.py:41"),
    IngestedDataset("d_14f63e595975691e7c24a27ae4c07c79", "macro_hdb_rpi", "macro.py:42"),
    IngestedDataset("d_97f8a2e995022d311c6c68cfda6d034c", "macro_ura_ppi", "macro.py:43"),
    IngestedDataset("d_5fe5a4bb4a1ecc4d8a56a095832e2b24", "macro_bank_rates", "macro.py:44"),
    IngestedDataset("d_64f98475cef1e94300362cb400a50012", "macro_wage_growth", "macro.py:45"),
)

# The small datasets the repo hard-fails on (``required=True`` bronze nodes) or
# reads whole. Fetching these end-to-end through the real adapter is cheap enough
# to do on every live run, which is what proves the completeness check does not
# fire on a genuinely complete dataset.
END_TO_END_DATASETS: tuple[IngestedDataset, ...] = tuple(
    ds
    for ds in INGESTED_DATASETS
    if ds.resource_id
    in {
        "d_8e4c50283fb7052a391dfb746a05c853",  # 525 rows
        "d_688b934f82c1059ed0a6993d2a829089",  # 337 rows
        "d_bb771c5189ce18007621533dd36142bb",  # 30 rows
        "d_48143be392f1ed22f0700835212e5a60",  # 80 rows
        "d_0a6c6d71f6fa14e2d27e406f1d018439",  # 104 rows
    }
)

_ids = [ds.resource_id for ds in INGESTED_DATASETS]
_node_ids = {ds.resource_id: ds.node for ds in INGESTED_DATASETS}


class _Pacer:
    """Minimum spacing between outbound requests, shared by every probe."""

    def __init__(self, interval_seconds: float):
        self._interval = max(0.0, interval_seconds)
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def wait(self) -> None:
        if self._interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self._interval
            delay = slot - now
        if delay:
            time.sleep(delay)


_PACER = _Pacer(_PAUSE_SECONDS)
_HTTP = requests.Session()


def _get_page(resource_id: str, limit: int, offset: int | None = None) -> dict:
    """One ``datastore_search`` page body, paced and 429-tolerant.

    Raises:
        _PageTooLargeError: The API answered 413, so the caller must lower ``limit``.
    """
    url = f"{datagovsg.resource_url(resource_id)}&limit={limit}"
    if offset is not None:
        url = f"{url}&offset={offset}"
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        _PACER.wait()
        response = _HTTP.get(url, timeout=120, headers={"User-Agent": "egg-n-bacon-live-tests"})
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "")
            delay = (
                float(retry_after) if retry_after.isdigit() else min(2**attempt, _MAX_RETRY_AFTER)
            )
            time.sleep(min(delay, _MAX_RETRY_AFTER))
            continue
        if response.status_code == 413:
            raise _PageTooLargeError(f"413 at limit={limit} for {resource_id}")
        response.raise_for_status()
        return response.json()
    raise AssertionError(f"data.gov.sg kept answering 429 for {resource_id} after {_MAX_ATTEMPTS}")


class _PageTooLargeError(Exception):
    """HTTP 413: the snapshot request exceeded the API's response-size cap."""


def _first_page(resource_id: str, limit: int = _PAGE_LIMIT) -> tuple[dict, int]:
    """First page plus the ``limit`` the API actually served it at."""
    while limit >= _MIN_PAGE_LIMIT:
        try:
            payload = _get_page(resource_id, limit)
        except _PageTooLargeError:
            limit //= 2
            continue
        return payload, limit
    raise AssertionError(f"{resource_id} rejected every limit down to {_MIN_PAGE_LIMIT}")


def _result(payload: dict) -> dict:
    assert payload.get("success") is True, f"success not true: {payload.get('error')}"
    return payload["result"]


def _next_offset(result: dict) -> int | None:
    """Offset carried by the page's ``next`` link, or ``None`` when pagination ends."""
    links = result.get("_links") or {}
    next_url = links.get("next")
    if not next_url:
        return None
    query = next_url.split("?", 1)[-1]
    for part in query.split("&"):
        if part.startswith("offset="):
            return int(part.split("=", 1)[1])
    return None


def _row_id(record: dict) -> object:
    return record.get("_id")


class TestEndToEndThroughTheAdapter:
    """The real ingestion call must return the whole dataset, not raise."""

    @pytest.mark.parametrize(
        "dataset", END_TO_END_DATASETS, ids=[ds.node for ds in END_TO_END_DATASETS]
    )
    def test_small_ingested_dataset_fetches_completely(self, dataset: IngestedDataset):
        first, _limit = _first_page(dataset.resource_id)
        advertised = _result(first)["total"]

        # No cache: this is the live path, including the terminal completeness
        # reconciliation that raises IncompleteDatasetFetchError.
        frame = datagovsg.fetch_datagovsg_dataset(
            datagovsg.resource_url(dataset.resource_id),
            dataset.resource_id,
            use_cache=False,
        )

        assert not frame.empty, f"{dataset.node} returned an empty frame"
        assert len(frame) == advertised, (
            f"{dataset.node} ({dataset.resource_id}): adapter returned {len(frame)} rows, "
            f"source advertises total={advertised}"
        )


class TestPaginationArithmetic:
    """Cheap 1-2 request probe of the arithmetic the completeness check relies on.

    This is what would fail first if a real source's ``next`` chain stopped
    short of its advertised ``total`` — the exact scenario that would make the
    A2 hard failure break production ingestion. The full walk in
    ``TestDeepNextWalk`` confirms the whole chain; this confirms the endpoint
    (last page fills exactly ``total - offset``) that any early stop would
    break.
    """

    @pytest.mark.parametrize("resource_id", _ids, ids=[_node_ids[rid] for rid in _ids])
    def test_next_chain_ends_exactly_at_advertised_total(self, resource_id: str):
        first, limit = _first_page(resource_id)
        result = _result(first)
        total = result["total"]
        records = result["records"]

        assert len(records) == min(limit, total), (
            f"{resource_id}: first page returned {len(records)} rows for "
            f"limit={limit}, total={total}"
        )

        next_offset = _next_offset(result)
        if total <= limit:
            # The whole dataset fits in one page: pagination must terminate
            # immediately (data.gov.sg still emits an offset > total here).
            assert next_offset is None or next_offset > total, (
                f"{resource_id}: total={total} fits in one page but next points at "
                f"offset={next_offset}"
            )
            return

        last_offset = ((total - 1) // limit) * limit
        tail = _result(_get_page(resource_id, limit, offset=last_offset))
        tail_records = tail["records"]
        assert len(tail_records) == total - last_offset, (
            f"{resource_id}: last page at offset={last_offset} returned "
            f"{len(tail_records)} rows; advertised total={total} needs "
            f"{total - last_offset}. Following next would end short of total."
        )
        # The final page must not claim a different total (a drifting total is
        # the other way a completeness check can misfire on live data).
        assert tail["total"] == total, (
            f"{resource_id}: total drifted mid-walk ({total} -> {tail['total']})"
        )
        tail_next = _next_offset(tail)
        assert tail_next is None or tail_next > total, (
            f"{resource_id}: after the last page next points at offset={tail_next} "
            f"but total={total}"
        )


@pytest.mark.skipif(
    not _DEEP,
    reason="full next-chain walk of every dataset is opt-in: set EGG_LIVE_DEEP=1",
)
class TestDeepNextWalk:
    """Advertised total vs rows obtainable by following ``next`` — the table.

    Every ingested dataset is walked end to end at the largest page size the API
    accepts, so the printed rows are the evidence on whether A2's hard failure
    can fire in production.
    """

    @pytest.mark.parametrize("resource_id", _ids, ids=[_node_ids[rid] for rid in _ids])
    def test_every_advertised_row_is_reachable_by_following_next(self, resource_id: str):
        first, limit = _first_page(resource_id)
        result = _result(first)
        total = result["total"]

        rows = 0
        pages = 0
        seen_ids: set[object] = set()
        duplicates = 0
        next_url = result.get("_links", {}).get("next")
        payload = first
        last_total: int | None = None
        started = time.monotonic()
        while True:
            result = _result(payload)
            page_total = result.get("total")
            if isinstance(page_total, int) and not isinstance(page_total, bool):
                last_total = page_total
            records = result.get("records") or []
            pages += 1
            rows += len(records)
            for record in records:
                rid = _row_id(record)
                if rid is None:
                    continue
                if rid in seen_ids:
                    duplicates += 1
                seen_ids.add(rid)
            next_url = (result.get("_links") or {}).get("next")
            if not next_url:
                break
            offset = _next_offset(result)
            if offset is not None and offset > total:
                break
            payload = _get_page(resource_id, limit, offset=None if offset is None else offset)
            if pages > 200:  # a runaway must fail, not hang the live run
                raise AssertionError(f"{resource_id}: pagination did not terminate")

        print(
            f"\nLIVE-PROBE {_node_ids[resource_id]:32s} {resource_id} "
            f"advertised_total={total:<8d} rows_via_next={rows:<8d} pages={pages:<3d} "
            f"dup_ids={duplicates} last_page_total={last_total} "
            f"limit={limit} elapsed={time.monotonic() - started:.1f}s"
        )

        assert rows == total, (
            f"{resource_id} ({_node_ids[resource_id]}): following next yielded "
            f"{rows} rows but the source advertises total={total}. A2's "
            "IncompleteDatasetFetchError would fire on this real dataset."
        )
        assert duplicates == 0, (
            f"{resource_id}: {duplicates} duplicate _id row(s) across pages — total "
            "counts rows the next-chain repeats, which the row-count check reads as a gap"
        )
        assert last_total in (None, total), (
            f"{resource_id}: total drifted during the walk ({total} -> {last_total})"
        )


class TestFailureShapes:
    """The new failure paths must fire on real error responses, not silently pass."""

    def test_unknown_resource_id_raises_instead_of_returning_empty(self):
        # A 404 body ("The resource could not be found.") is not a JSON page;
        # the adapter must raise rather than publish an empty dataset.
        bogus = "d_00000000000000000000000000000000"
        with pytest.raises(DatasetFetchError):
            datagovsg.fetch_datagovsg_dataset(datagovsg.resource_url(bogus), bogus, use_cache=False)

    def test_incomplete_error_is_the_importable_contract(self):
        # The exception the live assertions above depend on, pinned by identity
        # so a rename in the adapter cannot leave these tests asserting a
        # different error than the one callers catch.
        from egg_n_bacon_housing.adapters import exceptions

        assert exceptions.IncompleteDatasetFetchError is IncompleteDatasetFetchError
        assert issubclass(IncompleteDatasetFetchError, DatasetFetchError)
