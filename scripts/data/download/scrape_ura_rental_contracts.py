#!/usr/bin/env python3
"""Scrape URA rental contracts from e-service.

This script scrapes individual rental contract details for private
residential properties from URA's e-service.

Usage:
    uv run python scripts/data/download/scrape_ura_rental_contracts.py
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.config import Config
from scripts.core.network_check import check_local_file_exists, require_network

logger = logging.getLogger(__name__)

OUTPUT_PATH = Config.PIPELINE_DIR / "L1" / "ura_rental_contracts.parquet"

POSTAL_DISTRICTS = list(range(1, 29))

PROPERTY_TYPES = [
    ("N", "Non-Landed Housing"),
    ("A", "Apartment"),
    ("EC", "Executive Condominium"),
]

YEARS = list(range(2021, 2027))
MONTHS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]


def setup_browser():
    """Initialize Playwright browser."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    page = context.new_page()
    return playwright, browser, page


def close_browser(playwright, browser):
    """Close browser and playwright."""
    browser.close()
    playwright.stop()


def scrape_district(
    page,
    district: int,
    property_type_code: str,
    property_type_name: str,
    start_year: int = 2021,
    end_year: int = 2026,
) -> pd.DataFrame:
    """Scrape rental contracts for a single district and property type."""
    from playwright.sync_api import TimeoutError

    url = "https://eservice.ura.gov.sg/property-market-information/pmiResidentialRentalSearch"

    all_data = []

    for year in range(start_year, end_year + 1):
        for month in MONTHS:
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(1500)

                page.select_option("#ddlPostalDistrict", str(district))
                page.select_option("#ddlPropertyType", property_type_code)

                page.select_option("#ddlLeaseStartYear", str(year))
                page.select_option("#ddlLeaseStartMonth", month)

                page.click("#btnSearch")

                page.wait_for_timeout(2000)

                table = page.locator("#gvContract").first
                if not table.is_visible():
                    continue

                rows = table.locator("tr").all()
                if len(rows) < 2:
                    continue

                for row in rows[1:]:
                    cols = row.locator("td").all()
                    if len(cols) >= 8:
                        try:
                            project_name = cols[0].inner_text().strip()
                            street = cols[1].inner_text().strip()
                            district_val = cols[2].inner_text().strip()
                            cols[3].inner_text().strip()
                            lease_start = cols[4].inner_text().strip()
                            monthly_rent = cols[5].inner_text().strip()
                            floor_area = cols[6].inner_text().strip()
                            rent_psf = cols[7].inner_text().strip()

                            if project_name:
                                data = {
                                    "project_name": project_name,
                                    "street_name": street,
                                    "postal_district": int(district_val)
                                    if district_val.isdigit()
                                    else district,
                                    "property_type": property_type_name,
                                    "lease_start": lease_start,
                                    "monthly_rent": float(
                                        monthly_rent.replace(",", "").replace("$", "")
                                    )
                                    if monthly_rent.replace(",", "")
                                    .replace("$", "")
                                    .replace(".", "")
                                    .isdigit()
                                    else None,
                                    "floor_area_sqft": float(floor_area.replace(",", ""))
                                    if floor_area.replace(",", "").replace(".", "").isdigit()
                                    else None,
                                    "rent_psf": float(rent_psf.replace(",", "").replace("$", ""))
                                    if rent_psf.replace(",", "")
                                    .replace("$", "")
                                    .replace(".", "")
                                    .isdigit()
                                    else None,
                                    "created_at": datetime.now(),
                                }
                                all_data.append(data)
                        except (ValueError, IndexError):
                            continue

            except TimeoutError:
                logger.warning(
                    f"Timeout for district {district}, type {property_type_name}, {year}-{month}"
                )
                continue
            except Exception as e:
                logger.debug(
                    f"Error for district {district}, type {property_type_name}, {year}-{month}: {e}"
                )
                continue

    return pd.DataFrame(all_data)


def scrape_all_districts(max_districts: int = None) -> pd.DataFrame:
    """Scrape rental contracts for all districts and property types."""
    districts_to_scrape = POSTAL_DISTRICTS[:max_districts] if max_districts else POSTAL_DISTRICTS

    all_data = []
    playwright, browser, page = setup_browser()

    try:
        total = len(districts_to_scrape) * len(PROPERTY_TYPES)
        current = 0

        for district in districts_to_scrape:
            for prop_code, prop_name in PROPERTY_TYPES:
                current += 1
                logger.info(f"Scraping district {district}, {prop_name} ({current}/{total})...")

                df = scrape_district(page, district, prop_code, prop_name)
                if not df.empty:
                    all_data.append(df)
                    logger.info(f"  Got {len(df)} contracts")

                time.sleep(1.5)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        close_browser(playwright, browser)

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def scrape_quick_stats(max_districts: int = 5) -> pd.DataFrame:
    """Quick scrape to get sample data for testing."""
    districts_to_scrape = POSTAL_DISTRICTS[:max_districts]

    all_data = []
    playwright, browser, page = setup_browser()

    try:
        for district in districts_to_scrape:
            for prop_code, prop_name in PROPERTY_TYPES[:1]:
                logger.info(f"Scraping district {district}, {prop_name}...")

                df = scrape_district(page, district, prop_code, prop_name, 2025, 2026)
                if not df.empty:
                    all_data.append(df)
                    logger.info(f"  Got {len(df)} contracts")

                time.sleep(1.5)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        close_browser(playwright, browser)

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def save_results(df: pd.DataFrame) -> bool:
    """Save scraped data to parquet."""
    if df.empty:
        logger.warning("No data to save")
        return False

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, compression="snappy", index=False)
    logger.info(f"Saved {len(df)} records to {OUTPUT_PATH}")
    return True


def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape URA rental contracts")
    parser.add_argument(
        "--quick", action="store_true", help="Quick scrape (5 districts, 1 prop type)"
    )
    parser.add_argument("--districts", type=int, help="Limit number of districts")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("URA Rental Contracts Scraper")
    logger.info("=" * 60)

    if check_local_file_exists(OUTPUT_PATH):
        logger.info(f"Local file already exists: {OUTPUT_PATH}")
        logger.info("To re-scrape, delete the local file first.")
        return

    if not require_network():
        logger.error("Network unavailable. Cannot scrape data. Exiting.")
        return

    if args.quick:
        logger.info("Running QUICK scrape (5 districts, 1 property type)...")
        df = scrape_quick_stats(max_districts=5)
    else:
        df = scrape_all_districts(max_districts=args.districts)

    if not df.empty:
        save_results(df)

        logger.info("\nSummary:")
        logger.info(f"  Total contracts: {len(df)}")
        logger.info(f"  Unique projects: {df['project_name'].nunique()}")
        logger.info(f"  Districts: {df['postal_district'].nunique()}")
        logger.info(f"  Property types: {df['property_type'].unique()}")
    else:
        logger.error("No data scraped")

    logger.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()
