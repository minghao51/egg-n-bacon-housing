"""Macro economic indicator nodes for bronze layer.

Fetches CPI, GDP, unemployment, bank rates, HDB RPI, URA PPI, supply pipeline,
and wage growth from data.gov.sg pivot tables and melts them to long format.
SORA is loaded from a pre-built parquet in bronze/external.
"""

import logging
from pathlib import Path

import pandas as pd
import requests

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError

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

DATAGOVSG_API_BASE_URL = "https://data.gov.sg/api/action/datastore_search?resource_id="

CPI_RESOURCE_ID = "d_bdaff844e3ef89d39fceb962ff8f0791"
GDP_RESOURCE_ID = "d_a5ff719648a0e6d4b4c623ee383ab686"
UNEMPLOYMENT_RESOURCE_ID = "d_b0da22a41f952764376a2b7b5b0f2533"
HDB_RPI_RESOURCE_ID = "d_14f63e595975691e7c24a27ae4c07c79"
URA_PPI_RESOURCE_ID = "d_97f8a2e995022d311c6c68cfda6d034c"
SUPPLY_PIPELINE_RESOURCE_ID = "d_baa848bbdbf4af7b4d709f147fcf3c9b"
BANK_RATES_RESOURCE_ID = "d_5fe5a4bb4a1ecc4d8a56a095832e2b24"
WAGE_GROWTH_RESOURCE_ID = "d_64f98475cef1e94300362cb400a50012"


def _melt_pivot_monthly(df: pd.DataFrame, value_filter: str, value_col: str) -> pd.DataFrame:
    """Melt a data.gov.sg pivot table with monthly columns (e.g. '2026Apr') into long format."""
    label_col = "DataSeries" if "DataSeries" in df.columns else df.columns[1]
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


def _melt_pivot_quarterly(df: pd.DataFrame, value_filter: str, value_col: str) -> pd.DataFrame:
    """Melt a data.gov.sg pivot table with quarterly columns (e.g. '20261Q') into long format."""
    label_col = "DataSeries" if "DataSeries" in df.columns else df.columns[1]
    melted = df.melt(id_vars=[label_col], var_name="period", value_name=value_col)
    melted = melted[melted[label_col].astype(str).str.strip() == value_filter]
    melted[value_col] = pd.to_numeric(melted[value_col], errors="coerce")

    def _parse_quarter(p: str) -> pd.Timestamp | None:
        p = str(p)
        if len(p) >= 5 and p[-1] == "Q":
            try:
                year = int(p[:-2])
                qtr = int(p[-2])
                return pd.Timestamp(year=year, month=qtr * 3, day=1) + pd.offsets.QuarterEnd(0)
            except (ValueError, IndexError):
                return None
        if len(p) >= 6 and p[4] == "Q":
            try:
                year = int(p[:4])
                qtr = int(p[5])
                return pd.Timestamp(year=year, month=qtr * 3, day=1) + pd.offsets.QuarterEnd(0)
            except (ValueError, IndexError):
                return None
        return None

    melted["quarter"] = melted["period"].apply(_parse_quarter)
    return (
        melted[["quarter", value_col]]
        .dropna(subset=["quarter"])
        .sort_values("quarter")
        .reset_index(drop=True)
    )


def _parse_datagov_quarter(series: pd.Series) -> pd.Series:
    """Parse data.gov.sg quarter strings into quarter-end timestamps."""
    series_str = series.astype(str).str.strip()
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
        'bank_rates', 'hdb_rpi', 'ura_ppi', 'supply_pipeline', 'wage_growth'.
    """
    external_dir = bronze_dir / "external"
    external_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}
    failures: list[str] = []

    sora_path = external_dir / "sora_rates.parquet"
    if sora_path.exists():
        result["sora"] = pd.read_parquet(sora_path)
        logger.info("Loaded SORA: %s records", len(result["sora"]))
    else:
        logger.warning("SORA data not found in bronze/external")
        result["sora"] = pd.DataFrame()

    cpi_path = external_dir / "cpi.parquet"
    if cpi_path.exists():
        result["cpi"] = pd.read_parquet(cpi_path)
    else:
        try:
            logger.info("Fetching CPI from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, CPI_RESOURCE_ID, use_cache=False
            )
            result["cpi"] = _melt_pivot_monthly(raw, "All Items", "cpi")
            result["cpi"].to_parquet(cpi_path, index=False)
            logger.info("Fetched CPI: %s records -> %s", len(result["cpi"]), cpi_path)
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"cpi: {exc.__class__.__name__}: {exc}")
            result["cpi"] = pd.DataFrame()

    unemployment_path = external_dir / "unemployment.parquet"
    if unemployment_path.exists():
        result["unemployment"] = pd.read_parquet(unemployment_path)
    else:
        try:
            logger.info("Fetching unemployment from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, UNEMPLOYMENT_RESOURCE_ID, use_cache=False
            )
            result["unemployment"] = _melt_pivot_quarterly(
                raw, "Total Unemployment Rate", "unemployment_rate"
            )
            result["unemployment"].to_parquet(unemployment_path, index=False)
            logger.info(
                "Fetched unemployment: %s records -> %s",
                len(result["unemployment"]),
                unemployment_path,
            )
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"unemployment: {exc.__class__.__name__}: {exc}")
            result["unemployment"] = pd.DataFrame()

    gdp_path = external_dir / "gdp.parquet"
    if gdp_path.exists():
        result["gdp"] = pd.read_parquet(gdp_path)
    else:
        try:
            logger.info("Fetching GDP from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, GDP_RESOURCE_ID, use_cache=False
            )
            result["gdp"] = _melt_pivot_quarterly(raw, "GDP In Chained (2015) Dollars", "gdp")
            if result["gdp"].empty:
                label_col = "DataSeries" if "DataSeries" in raw.columns else raw.columns[1]
                first_series = str(raw.iloc[0][label_col]).strip()
                result["gdp"] = _melt_pivot_quarterly(raw, first_series, "gdp")
            result["gdp"].to_parquet(gdp_path, index=False)
            logger.info("Fetched GDP: %s records -> %s", len(result["gdp"]), gdp_path)
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"gdp: {exc.__class__.__name__}: {exc}")
            result["gdp"] = pd.DataFrame()

    bank_rates_path = external_dir / "bank_rates.parquet"
    if bank_rates_path.exists():
        result["bank_rates"] = pd.read_parquet(bank_rates_path)
    else:
        try:
            logger.info("Fetching bank interest rates from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, BANK_RATES_RESOURCE_ID, use_cache=False
            )
            result["bank_rates"] = _melt_pivot_monthly(
                raw, "Compounded Singapore Overnight Rate Average (SORA) - 3 Month", "sora_3m"
            )
            result["bank_rates"].to_parquet(bank_rates_path, index=False)
            logger.info(
                "Fetched bank rates (SORA 3M): %s records -> %s",
                len(result["bank_rates"]),
                bank_rates_path,
            )
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"bank_rates: {exc.__class__.__name__}: {exc}")
            result["bank_rates"] = pd.DataFrame()

    hdb_rpi_path = external_dir / "hdb_rpi.parquet"
    if hdb_rpi_path.exists():
        result["hdb_rpi"] = pd.read_parquet(hdb_rpi_path)
    else:
        try:
            logger.info("Fetching HDB Resale Price Index from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, HDB_RPI_RESOURCE_ID, use_cache=False
            )
            rpi = raw[["quarter", "index"]].copy()
            rpi["index"] = pd.to_numeric(rpi["index"], errors="coerce")
            rpi = rpi.dropna(subset=["index"])
            rpi["quarter"] = _parse_datagov_quarter(rpi["quarter"])
            rpi = rpi.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
            result["hdb_rpi"] = rpi.rename(columns={"index": "hdb_rpi"})
            result["hdb_rpi"].to_parquet(hdb_rpi_path, index=False)
            logger.info("Fetched HDB RPI: %s records -> %s", len(result["hdb_rpi"]), hdb_rpi_path)
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"hdb_rpi: {exc.__class__.__name__}: {exc}")
            result["hdb_rpi"] = pd.DataFrame()

    ura_ppi_path = external_dir / "ura_ppi.parquet"
    if ura_ppi_path.exists():
        result["ura_ppi"] = pd.read_parquet(ura_ppi_path)
    else:
        try:
            logger.info("Fetching URA Property Price Index from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, URA_PPI_RESOURCE_ID, use_cache=False
            )
            ppi = raw[raw["property_type"].astype(str).str.strip() == "All Residential"].copy()
            ppi["index"] = pd.to_numeric(ppi["index"], errors="coerce")
            ppi = ppi.dropna(subset=["index"])
            ppi["quarter"] = _parse_datagov_quarter(ppi["quarter"])
            ppi = ppi.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
            result["ura_ppi"] = ppi[["quarter", "index"]].rename(columns={"index": "ura_ppi"})
            result["ura_ppi"].to_parquet(ura_ppi_path, index=False)
            logger.info("Fetched URA PPI: %s records -> %s", len(result["ura_ppi"]), ura_ppi_path)
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"ura_ppi: {exc.__class__.__name__}: {exc}")
            result["ura_ppi"] = pd.DataFrame()

    supply_path = external_dir / "supply_pipeline.parquet"
    if supply_path.exists():
        result["supply_pipeline"] = pd.read_parquet(supply_path)
    else:
        try:
            logger.info("Fetching private housing supply pipeline from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, SUPPLY_PIPELINE_RESOURCE_ID, use_cache=False
            )
            supply = raw.copy()
            supply["no_of_units"] = pd.to_numeric(supply["no_of_units"], errors="coerce")
            supply["quarter"] = _parse_datagov_quarter(supply["quarter"])
            supply = supply.dropna(subset=["quarter", "no_of_units"])
            supply = supply.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
            result["supply_pipeline"] = supply
            result["supply_pipeline"].to_parquet(supply_path, index=False)
            logger.info(
                "Fetched supply pipeline: %s records -> %s",
                len(result["supply_pipeline"]),
                supply_path,
            )
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"supply_pipeline: {exc.__class__.__name__}: {exc}")
            result["supply_pipeline"] = pd.DataFrame()

    wage_path = external_dir / "wage_growth.parquet"
    if wage_path.exists():
        result["wage_growth"] = pd.read_parquet(wage_path)
        if result["wage_growth"].empty:
            wage_path.unlink()
    if "wage_growth" not in result or result["wage_growth"].empty:
        try:
            logger.info("Fetching wage growth from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, WAGE_GROWTH_RESOURCE_ID, use_cache=False
            )
            label_col = "DataSeries" if "DataSeries" in raw.columns else raw.columns[-1]
            melted = raw.melt(id_vars=[label_col], var_name="year", value_name="wage_growth")
            melted = melted[melted[label_col].astype(str).str.strip() == "Overall Economy"]
            melted["wage_growth"] = pd.to_numeric(melted["wage_growth"], errors="coerce")
            melted["year"] = pd.to_numeric(melted["year"], errors="coerce")
            melted = melted.dropna(subset=["year", "wage_growth"])

            quarterly_rows = []
            for _, row in melted.iterrows():
                year = int(row["year"])
                for q in range(1, 5):
                    quarter_date = pd.Timestamp(
                        year=year, month=q * 3, day=1
                    ) + pd.offsets.QuarterEnd(0)
                    quarterly_rows.append(
                        {"quarter": quarter_date, "wage_growth": row["wage_growth"]}
                    )
            result["wage_growth"] = (
                pd.DataFrame(quarterly_rows).sort_values("quarter").reset_index(drop=True)
            )

            result["wage_growth"].to_parquet(wage_path, index=False)
            logger.info(
                "Fetched wage growth: %s annual records -> %s quarterly -> %s",
                len(melted),
                len(result["wage_growth"]),
                wage_path,
            )
        except _RETRIEVABLE_EXCEPTIONS as exc:
            failures.append(f"wage_growth: {exc.__class__.__name__}: {exc}")
            result["wage_growth"] = pd.DataFrame()

    if failures:
        logger.warning(
            "Macro ingestion: %d indicator(s) failed and degraded to empty -- %s",
            len(failures),
            "; ".join(failures),
        )

    return result
