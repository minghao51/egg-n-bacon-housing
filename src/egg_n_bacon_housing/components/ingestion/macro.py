"""Macro economic indicator nodes for bronze layer.

Fetches CPI, GDP, unemployment, bank rates, HDB RPI, URA PPI,
and wage growth from data.gov.sg pivot tables and melts them to long format.
SORA is loaded from a pre-built parquet in bronze/external.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError
from egg_n_bacon_housing.utils.bronze import read_bronze_cache, write_bronze_cache

logger = logging.getLogger(__name__)

__all__ = ["raw_macro_data"]

# Exceptions that represent expected, retrieable data-fetch/shape problems from
# data.gov.sg (network blips, adapter fetch failures, schema/shape drift in the
# returned frame). Programming bugs (TypeError/AttributeError/RuntimeError) and
# credential/config problems (CredentialError etc.) are intentionally NOT here
# -- they must propagate so they surface immediately instead of degrading the
# run to silent NaNs. See "macro.py narrow + visible" fix.
_RETRIEVABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    requests.RequestException,
    DatasetFetchError,
    KeyError,
    IndexError,
    ValueError,
)

CPI_RESOURCE_ID = "d_bdaff844e3ef89d39fceb962ff8f0791"
GDP_RESOURCE_ID = "d_a5ff719648a0e6d4b4c623ee383ab686"
UNEMPLOYMENT_RESOURCE_ID = "d_b0da22a41f952764376a2b7b5b0f2533"
HDB_RPI_RESOURCE_ID = "d_14f63e595975691e7c24a27ae4c07c79"
URA_PPI_RESOURCE_ID = "d_97f8a2e995022d311c6c68cfda6d034c"
BANK_RATES_RESOURCE_ID = "d_5fe5a4bb4a1ecc4d8a56a095832e2b24"
WAGE_GROWTH_RESOURCE_ID = "d_64f98475cef1e94300362cb400a50012"

GDP_PREFERRED_SERIES = "GDP In Chained (2015) Dollars"


# --- Per-indicator transforms (pure functions of the raw API frame) ---------


def _label_column(df: pd.DataFrame, context: str) -> str:
    """Resolve the series-label column of a data.gov.sg pivot frame.

    ONE documented fallback rule for every pivot-shaped macro source (CPI,
    unemployment, GDP, SORA, wage growth): the canonical layout is an ``_id``
    key column followed by a ``DataSeries`` label column and period columns.
    When the ``DataSeries`` header is absent (schema drift), the label column
    is assumed to be the first non-``_id`` column (position 1) — the dominant
    pre-existing behavior — and a warning names the expected header, the
    column actually used, and all available columns.
    """
    if "DataSeries" in df.columns:
        return "DataSeries"
    fallback = str(df.columns[1])
    logger.warning(
        "%s: pivot frame lacks the 'DataSeries' label column — falling back to "
        "%r (available columns: %s)",
        context,
        fallback,
        [str(col) for col in df.columns],
    )
    return fallback


def _transform_cpi(raw: pd.DataFrame) -> pd.DataFrame:
    return _melt_pivot_monthly(raw, "All Items", "cpi")


def _transform_unemployment(raw: pd.DataFrame) -> pd.DataFrame:
    return _melt_pivot_quarterly(raw, "Total Unemployment Rate", "unemployment_rate")


def _transform_gdp(raw: pd.DataFrame) -> pd.DataFrame:
    label_col = _label_column(raw, "gdp")
    gdp = _melt_pivot_quarterly(raw, GDP_PREFERRED_SERIES, "gdp", label_col=label_col)
    if gdp.empty:
        # Schema drift fallback: melt whatever the first row's series is.
        used_series = str(raw[label_col].iloc[0]).strip()
        available = sorted(raw[label_col].astype(str).str.strip().unique().tolist())
        logger.warning(
            "gdp: preferred series %r not found in pivot labels — melting the "
            "first series %r instead (available labels: %s)",
            GDP_PREFERRED_SERIES,
            used_series,
            available,
        )
        gdp = _melt_pivot_quarterly(raw, used_series, "gdp", label_col=label_col)
    return gdp


def _transform_bank_rates(raw: pd.DataFrame) -> pd.DataFrame:
    return _melt_pivot_monthly(
        raw,
        "Compounded Singapore Overnight Rate Average (SORA) - 3 Month",
        "sora_3m",
    )


def _transform_hdb_rpi(raw: pd.DataFrame) -> pd.DataFrame:
    rpi = raw[["quarter", "index"]].copy()
    rpi["index"] = pd.to_numeric(rpi["index"], errors="coerce")
    rpi = rpi.dropna(subset=["index"])
    rpi["quarter"] = _parse_datagov_quarter(rpi["quarter"])
    rpi = rpi.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
    return rpi.rename(columns={"index": "hdb_rpi"})


def _transform_ura_ppi(raw: pd.DataFrame) -> pd.DataFrame:
    ppi = raw[raw["property_type"].astype(str).str.strip() == "All Residential"].copy()
    ppi["index"] = pd.to_numeric(ppi["index"], errors="coerce")
    ppi = ppi.dropna(subset=["index"])
    ppi["quarter"] = _parse_datagov_quarter(ppi["quarter"])
    ppi = ppi.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
    return ppi[["quarter", "index"]].rename(columns={"index": "ura_ppi"})


def _transform_wage_growth(raw: pd.DataFrame) -> pd.DataFrame:
    label_col = _label_column(raw, "wage_growth")
    melted = raw.melt(id_vars=[label_col], var_name="year", value_name="wage_growth")
    melted = melted[melted[label_col].astype(str).str.strip() == "Overall Economy"]
    melted["wage_growth"] = pd.to_numeric(melted["wage_growth"], errors="coerce")
    melted["year"] = pd.to_numeric(melted["year"], errors="coerce")
    melted = melted.dropna(subset=["year", "wage_growth"])

    quarterly_rows = []
    for _, row in melted.iterrows():
        year = int(row["year"])
        for q in range(1, 5):
            quarter_date = pd.Timestamp(year=year, month=q * 3, day=1) + pd.offsets.QuarterEnd(0)
            quarterly_rows.append({"quarter": quarter_date, "wage_growth": row["wage_growth"]})
    if not quarterly_rows:
        raise DatasetFetchError("wage growth pivot matched no 'Overall Economy' rows")
    return pd.DataFrame(quarterly_rows).sort_values("quarter").reset_index(drop=True)


@dataclass(frozen=True)
class _MacroSource:
    """Declarative spec for one data.gov.sg macro indicator."""

    key: str
    filename: str
    resource_id: str
    transform: Callable[[pd.DataFrame], pd.DataFrame]
    label: str


_MACRO_SOURCES: tuple[_MacroSource, ...] = (
    _MacroSource("cpi", "cpi.parquet", CPI_RESOURCE_ID, _transform_cpi, "CPI"),
    _MacroSource(
        "unemployment",
        "unemployment.parquet",
        UNEMPLOYMENT_RESOURCE_ID,
        _transform_unemployment,
        "unemployment",
    ),
    _MacroSource("gdp", "gdp.parquet", GDP_RESOURCE_ID, _transform_gdp, "GDP"),
    _MacroSource(
        "bank_rates",
        "bank_rates.parquet",
        BANK_RATES_RESOURCE_ID,
        _transform_bank_rates,
        "bank interest rates",
    ),
    _MacroSource(
        "hdb_rpi",
        "hdb_rpi.parquet",
        HDB_RPI_RESOURCE_ID,
        _transform_hdb_rpi,
        "HDB Resale Price Index",
    ),
    _MacroSource(
        "ura_ppi",
        "ura_ppi.parquet",
        URA_PPI_RESOURCE_ID,
        _transform_ura_ppi,
        "URA Property Price Index",
    ),
    _MacroSource(
        "wage_growth",
        "wage_growth.parquet",
        WAGE_GROWTH_RESOURCE_ID,
        _transform_wage_growth,
        "wage growth",
    ),
)

# Concurrency bound for the macro fetch pool. Each source is a full paginated
# data.gov.sg round trip with retries, so fetching all 8 serially made the
# macro stage's wall time the sum of all eight. Four workers cut that roughly
# in half while capping the aggregate request rate against the shared API for
# rate-limit safety; pagination *within* a source stays serial (TLS/rate-limit
# tradeoff, see adapters/datagovsg.py).
_MACRO_FETCH_WORKERS = 4


def _load_macro_source(
    bronze_dir: Path, external_dir: Path, source: _MacroSource
) -> tuple[pd.DataFrame, str | None]:
    """Bronze-cache-first load of one macro indicator; empty on retrievable failure.

    Returns the loaded frame plus a failure record (``"<key>: <ExcType>: <msg>"``)
    when the source degraded to empty, or ``None`` when it loaded cleanly.
    Returning the failure instead of appending to a shared list keeps this
    worker free of cross-thread shared state: it runs concurrently, once per
    source, inside :func:`raw_macro_data`.
    """
    path = external_dir / source.filename
    cached = read_bronze_cache(bronze_dir, source.filename, subdir="external")
    if cached is not None:
        if cached.empty:
            # An empty cache file (e.g. left behind by an older run after upstream
            # schema drift) must never be treated as valid data -- it would
            # silently poison the indicator with NaNs on every subsequent run.
            logger.warning("Ignoring empty bronze cache: %s", path)
        else:
            return cached, None
    try:
        logger.info("Fetching %s from data.gov.sg...", source.label)
        raw = datagovsg.fetch_datagovsg_dataset(
            datagovsg.resource_url(source.resource_id), source.resource_id, use_cache=False
        )
        result = source.transform(raw)
        # Empty frames are never cached (helper empty-guard), so an empty parse
        # degrades to empty without seeding a poisoning 0-row cache file.
        write_bronze_cache(bronze_dir, result, source.filename, "datagov_api", subdir="external")
        logger.info("Fetched %s: %d records -> %s", source.label, len(result), path)
        return result, None
    except _RETRIEVABLE_EXCEPTIONS as exc:
        return pd.DataFrame(), f"{source.key}: {exc.__class__.__name__}: {exc}"


def _melt_pivot_monthly(
    df: pd.DataFrame, value_filter: str, value_col: str, label_col: str | None = None
) -> pd.DataFrame:
    """Melt a data.gov.sg pivot table with monthly columns (e.g. '2026Apr') into long format."""
    if label_col is None:
        label_col = _label_column(df, value_col)
    melted = df.melt(id_vars=[label_col], var_name="period", value_name=value_col)
    melted = melted[melted[label_col].astype(str).str.strip() == value_filter]
    melted["date"] = pd.to_datetime(melted["period"], format="%Y%b", errors="coerce")
    melted[value_col] = pd.to_numeric(melted[value_col], errors="coerce")
    return (
        melted[["date", value_col]]
        .dropna(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )


def _melt_pivot_quarterly(
    df: pd.DataFrame, value_filter: str, value_col: str, label_col: str | None = None
) -> pd.DataFrame:
    """Melt a data.gov.sg pivot table with quarterly columns (e.g. '20261Q') into long format.

    Quarter parsing goes through the strict module-level
    :func:`_parse_datagov_quarter` (same parser as the hdb_rpi/ura_ppi
    transforms): malformed period headers such as ``"2024Q"`` become NaT and
    their rows are dropped, instead of silently parsing to garbage years.
    """
    if label_col is None:
        label_col = _label_column(df, value_col)
    melted = df.melt(id_vars=[label_col], var_name="period", value_name=value_col)
    melted = melted[melted[label_col].astype(str).str.strip() == value_filter]
    melted[value_col] = pd.to_numeric(melted[value_col], errors="coerce")
    melted["quarter"] = _parse_datagov_quarter(melted["period"])
    return (
        melted[["quarter", value_col]]
        .dropna(subset=["quarter"])
        .sort_values("quarter")
        .reset_index(drop=True)
    )


def _parse_datagov_quarter(series: pd.Series) -> pd.Series:
    """Parse data.gov.sg quarter strings into quarter-end timestamps.

    Accepts exactly the two data.gov.sg layouts — ``"20261Q"`` (quarter
    suffix) and ``"2026Q1"`` / ``"2026-Q1"`` (separator stripped first).
    Anything else is NaT: malformed values must degrade to dropped rows,
    never to a silently wrong year (the retired lenient parser turned
    ``"2024Q"`` into year 202).
    """
    series_str = series.astype(str).str.strip().str.replace("-", "", regex=False)
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    def _quarter_end(year: int, quarter: int) -> pd.Timestamp:
        return pd.Timestamp(year=year, month=quarter * 3, day=1) + pd.offsets.QuarterEnd(0)

    for idx, quarter_text in series_str.items():
        try:
            if len(quarter_text) == 6 and quarter_text.endswith("Q"):
                parsed.at[idx] = _quarter_end(int(quarter_text[:4]), int(quarter_text[4]))
            elif len(quarter_text) == 6 and quarter_text[4] == "Q":
                parsed.at[idx] = _quarter_end(int(quarter_text[:4]), int(quarter_text[5]))
        except (ValueError, IndexError):
            continue

    return parsed


def raw_macro_data(bronze_dir: Path) -> dict[str, pd.DataFrame]:
    """Fetch and load macro economic indicators from data.gov.sg API + local SORA.

    Returns:
        Dictionary with keys: 'sora', 'cpi', 'gdp', 'unemployment',
        'bank_rates', 'hdb_rpi', 'ura_ppi', 'wage_growth'.
    """
    external_dir = bronze_dir / "external"
    external_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}
    failures: list[str] = []

    sora_df = read_bronze_cache(bronze_dir, "sora_rates.parquet", subdir="external")
    if sora_df is not None:
        result["sora"] = sora_df
        logger.info("Loaded SORA: %s records", len(sora_df))
    else:
        logger.warning("SORA data not found in bronze/external")
        result["sora"] = pd.DataFrame()

    # Fetch the 7 macro sources concurrently (see _MACRO_FETCH_WORKERS for the
    # bound rationale). Failure semantics match the former serial loop
    # exactly: retrievable failures are captured inside the worker and degrade
    # only their source, while programming defects escape the worker -- those
    # are collected here and re-raised after the pool drains so they surface
    # immediately instead of being swallowed into the failure list.
    outcomes: list[tuple[pd.DataFrame, str | None]] = []
    defect: BaseException | None = None
    with ThreadPoolExecutor(max_workers=_MACRO_FETCH_WORKERS) as executor:
        futures = [
            executor.submit(_load_macro_source, bronze_dir, external_dir, source)
            for source in _MACRO_SOURCES
        ]
        # Harvest futures in submission order (= source order), not completion
        # order, so result keys and the failure summary stay deterministic
        # regardless of which fetch finishes first.
        for future in futures:
            exc = future.exception()
            if exc is None:
                outcomes.append(future.result())
            elif defect is None:
                defect = exc
    if defect is not None:
        raise defect

    for source, (frame, failure) in zip(_MACRO_SOURCES, outcomes, strict=True):
        result[source.key] = frame
        if failure is not None:
            failures.append(failure)

    if failures:
        logger.warning(
            "Macro ingestion: %d indicator(s) failed and degraded to empty -- %s",
            len(failures),
            "; ".join(failures),
        )

    return result
